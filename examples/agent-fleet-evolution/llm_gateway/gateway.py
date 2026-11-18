"""Policy-bound HTTP execution and authenticated recorded-response replay."""
from dataclasses import asdict, dataclass
from decimal import Decimal
import hashlib
import hmac
import math
import os
import threading
import time

import httpx

from . import adapters
from .contract import GatewayError, Request, Result, Usage, canonical, parse_json, require, validate
from .registry import endpoint, negotiate


@dataclass(frozen=True)
class Policy:
    endpoints: tuple[str,...] = ()
    allow_network: bool = False
    minimum_verification: str = "declared"
    timeout_seconds: float = 10
    total_timeout_seconds: float = 30
    max_retries: int = 0
    backoff_seconds: float = .1
    max_request_bytes: int = 65536
    max_response_bytes: int = 262144

    def __post_init__(self):
        require(isinstance(self.endpoints,tuple) and all(isinstance(s,str) for s in self.endpoints),"policy")
        require(type(self.allow_network) is bool and self.minimum_verification in ("declared","probed","live_verified"),"policy")
        require(type(self.max_retries) is int and 0<=self.max_retries<=2,"policy")
        for key,lo,hi in (("timeout_seconds",.01,120),("total_timeout_seconds",.01,360),
                          ("backoff_seconds",0,2)):
            value=getattr(self,key)
            require(type(value) in (int,float) and math.isfinite(value) and lo<=value<=hi,"policy")
        for key,hi in (("max_request_bytes",1048576),("max_response_bytes",4194304)):
            value=getattr(self,key)
            require(type(value) is int and 1<=value<=hi,"policy")


def classify(status):
    if status in (401,403):
        return "authentication" if status==401 else "permission"
    if status==429:
        return "rate_limit"
    if status in (408,504):
        return "timeout"
    if status>=500:
        return "provider_unavailable"
    if 300<=status<400:
        return "redirect"
    return "provider_request"


def estimate(usage, price, family, attempts):
    # Cache tiers and Gemini thought billing need separate verified prices.
    value={"status":"unknown","currency":None,"amount":None,"source":None,"as_of":None,
           "scope":"successful response only","invoice":False,"failed_attempts_unpriced":max(0,attempts-1)}
    if price is not None:
        value.update(currency=price["currency"],source=price["source"],as_of=price["as_of"])
        if (usage.input_tokens is not None and usage.output_tokens is not None
            and usage.cached_tokens==0 and (family!="gemini" or usage.reasoning_tokens==0)
            and (family!="anthropic" or usage.cache_creation_tokens==0)):
            amount=(Decimal(usage.input_tokens)*Decimal(price["input_per_million"])
                    +Decimal(usage.output_tokens)*Decimal(price["output_per_million"]))/Decimal(1_000_000)
            value.update(status="configured-rate estimate",amount=format(amount,"f"))
    return canonical(value)


class Gateway:
    def __init__(self, registry, policy, *, fingerprint_key, transport=None):
        require(isinstance(policy,Policy) and type(fingerprint_key) is bytes and len(fingerprint_key)>=32,"policy")
        require(transport is None or isinstance(transport,httpx.MockTransport),"policy")
        require(policy.allow_network or isinstance(transport,httpx.MockTransport),"network_disabled")
        self.registry,self.policy,self.transport=registry,policy,transport
        self._key=fingerprint_key

    def fingerprint(self, value):
        return hmac.new(self._key,canonical(value),hashlib.sha256).hexdigest()

    def prepare(self, request):
        require(isinstance(request,Request))
        config=self.registry.get(request.model_key)
        require(config["enabled"],"model_disabled")
        endpoint(config["endpoint"],config["local"])
        require(config["endpoint"] in self.policy.endpoints,"endpoint_denied")
        effective,omitted=negotiate(request,config,self.policy.minimum_verification)
        effective=dict(effective,endpoint=config["endpoint"],wire=config["wire"],
                       capability_evidence=config["capabilities"],execution_policy=asdict(self.policy),
                       required_features=sorted(request.required),optional_features=sorted(request.optional),
                       negotiated_omissions=list(omitted))
        url,body=adapters.encode(effective,config)
        raw=canonical(body)
        require(len(raw)<=self.policy.max_request_bytes,"request_size")
        descriptor={"request_id":request.request_id,"correlation_id":request.correlation_id,
                    "effective":effective,"registry_sha256":hashlib.sha256(canonical(config)).hexdigest()}
        return config,effective,omitted,url,raw,self.fingerprint(descriptor),descriptor["registry_sha256"]

    def generate(self, request, *, cancel=None):
        require(cancel is None or isinstance(cancel,threading.Event),"policy")
        require(self.policy.allow_network or isinstance(self.transport,httpx.MockTransport),"network_disabled")
        config,effective,omitted,url,raw,fp,registry_fp=self.prepare(request)
        secret=None
        if config["auth_env"] is not None:
            secret=os.environ.get(config["auth_env"])
            require(isinstance(secret,str) and bool(secret) and len(secret)<=8192
                    and all(33<=ord(c)<=126 for c in secret),"missing_secret")
        headers=adapters.auth(config,secret)
        headers.update({"Content-Type":"application/json","Accept":"application/json",
                        "Accept-Encoding":"identity","X-Request-ID":request.request_id,
                        "X-Correlation-ID":request.correlation_id})
        start=time.monotonic()
        deadline=start+self.policy.total_timeout_seconds
        history=[]
        attempts=0
        while attempts<=self.policy.max_retries:
            if cancel is not None and cancel.is_set():
                raise GatewayError("cancelled",attempts=attempts,uncertain_billing=attempts>0,history=history)
            remaining=deadline-time.monotonic()
            if remaining<=0:
                raise GatewayError("timeout",attempts=attempts,uncertain_billing=attempts>0,history=history)
            attempts+=1
            known_usage=None
            known_cost=None
            try:
                timeout=httpx.Timeout(min(self.policy.timeout_seconds,remaining))
                with httpx.Client(transport=self.transport,timeout=timeout,verify=True,trust_env=False,
                                  follow_redirects=False) as client:
                    with client.stream("POST",url,content=raw,headers=headers) as response:
                        require(response.status_code==200,classify(response.status_code))
                        require(response.headers.get("content-encoding","identity")=="identity","provider_protocol")
                        length=response.headers.get("content-length")
                        if length is not None:
                            require(length.isdecimal() and int(length)<=self.policy.max_response_bytes,"response_size")
                        output=bytearray()
                        for chunk in response.iter_bytes():
                            require(time.monotonic()<deadline,"timeout")
                            require(cancel is None or not cancel.is_set(),"cancelled")
                            require(len(output)+len(chunk)<=self.policy.max_response_bytes,"response_size")
                            output.extend(chunk)
                require(time.monotonic()<deadline,"timeout")
                require(cancel is None or not cancel.is_set(),"cancelled")
                document=parse_json(output)
                try:
                    text,usage,metadata=adapters.decode(document,config["family"])
                except (KeyError,TypeError,ValueError,AttributeError,IndexError):
                    raise GatewayError("provider_protocol") from None
                known_usage=usage
                known_cost=estimate(usage,config["pricing"],config["family"],attempts)
                require(usage.output_tokens is None or usage.output_tokens<=effective["parameters"]["max_output_tokens"],"provider_limit")
                if effective["schema"] is not None:
                    validate(parse_json(text),effective["schema"])
                if "usage" in request.required:
                    require(usage.input_tokens is not None and usage.output_tokens is not None,"missing_usage")
                if ("usage" in request.optional and "usage" not in omitted
                    and (usage.input_tokens is None or usage.output_tokens is None)):
                    omitted=tuple(sorted((*omitted,"usage")))
                history.append("success")
                return Result(request.request_id,request.correlation_id,config["provider"],config["model"],config["revision"],
                              text,usage,round((time.monotonic()-start)*1000,6),attempts,omitted,canonical(effective),fp,
                              self.fingerprint({"text":text,"usage":asdict(usage),"metadata":metadata}),registry_fp,
                              estimate(usage,config["pricing"],config["family"],attempts),canonical(metadata),tuple(history))
            except httpx.TimeoutException:
                code="timeout"
            except httpx.TransportError:
                code="network"
            except GatewayError as error:
                code=error.code
            history.append(code)
            retryable=code in ("timeout","network","rate_limit","provider_unavailable")
            if not retryable or attempts>self.policy.max_retries:
                raise GatewayError(code,attempts=attempts,uncertain_billing=True,history=history,
                                   usage=known_usage,cost=known_cost) from None
            delay=min(self.policy.backoff_seconds*2**(attempts-1),max(0,deadline-time.monotonic()))
            if cancel is not None:
                if cancel.wait(delay):
                    raise GatewayError("cancelled",attempts=attempts,uncertain_billing=True,history=history)
            else:
                time.sleep(delay)
        raise AssertionError("Bounded retry loop exhausted")

    def record_synthetic(self, result, *, reviewed_synthetic=False):
        require(reviewed_synthetic is True and isinstance(self.transport,httpx.MockTransport)
                and isinstance(result,Result) and not result.replayed,"replay_policy")
        data={"version":"llm-recording/1","source":"reviewed-synthetic-mock","result":{
            "request_fingerprint":result.request_fingerprint,"response_fingerprint":result.response_fingerprint,
            "registry_fingerprint":result.registry_fingerprint,"text":result.text,"usage":asdict(result.usage),
            "omitted":list(result.omitted),
            "attempts":result.attempts,"latency_ms":result.latency_ms,"cost":parse_json(result.cost),
            "provider_metadata":parse_json(result.provider_metadata),"attempt_history":list(result.attempt_history)}}
        return canonical({"record":data,"signature":self.fingerprint(data)})

    def replay(self, request, recording):
        require(type(recording) is bytes and len(recording)<=self.policy.max_response_bytes*2,"replay_policy")
        config,effective,omitted,_,_,fp,registry_fp=self.prepare(request)
        document=parse_json(recording)
        require(isinstance(document,dict) and set(document)=={"record","signature"},"replay_mismatch")
        data=document["record"]
        require(isinstance(document["signature"],str) and hmac.compare_digest(document["signature"],self.fingerprint(data)),
                "replay_mismatch")
        require(data["version"]=="llm-recording/1" and data["source"]=="reviewed-synthetic-mock","replay_policy")
        r=data["result"]
        require(r["request_fingerprint"]==fp and r["registry_fingerprint"]==registry_fp,"replay_mismatch")
        observed=tuple(r["omitted"])
        require(set(omitted)<=set(observed)<=request.optional and set(observed)-set(omitted)<={"usage"}
                and observed==tuple(sorted(set(observed))),"replay_mismatch")
        usage=Usage(**r["usage"])
        require(r["response_fingerprint"]==self.fingerprint({"text":r["text"],"usage":r["usage"],"metadata":r["provider_metadata"]}),
                "replay_mismatch")
        if effective["schema"] is not None:
            validate(parse_json(r["text"]),effective["schema"])
        return Result(request.request_id,request.correlation_id,config["provider"],config["model"],config["revision"],
                      r["text"],usage,r["latency_ms"],r["attempts"],observed,canonical(effective),fp,
                      r["response_fingerprint"],registry_fp,canonical(r["cost"]),canonical(r["provider_metadata"]),
                      tuple(r["attempt_history"]),True)
