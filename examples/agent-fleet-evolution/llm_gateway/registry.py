"""Strict registry parsing. Model capabilities always have explicit evidence status."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
from urllib.parse import urlsplit

from .contract import FEATURES, GatewayError, canonical, parse_json, require

FAMILIES = {"openai":FEATURES-{"tools"}, "anthropic":FEATURES-{"developer","seed","tools"},
            "gemini":FEATURES-{"developer","tools"}}
KNOWLEDGE = frozenset(("declared","probed","live_verified"))
MODEL_KEYS = frozenset(("key","provider","model","revision","family","endpoint","local","enabled","auth_env",
                        "capabilities","context_limit","output_limit","pricing","wire","provenance"))


def endpoint(url, local):
    try:
        parsed=urlsplit(url)
        port=parsed.port
    except (ValueError,AttributeError):
        raise GatewayError("registry") from None
    require(isinstance(url,str) and not any(c.isspace() for c in url)
            and parsed.username is None and parsed.password is None
            and not parsed.query and not parsed.fragment and parsed.hostname and not url.endswith("/"),
            "registry")
    require(parsed.scheme=="https" or (local and parsed.scheme=="http"),"registry")
    if local:
        require(parsed.hostname in ("localhost","127.0.0.1","::1"),"registry")
    if port is not None:
        require(1<=port<=65535,"registry")
    require(".." not in parsed.path and "%" not in parsed.path and "\\" not in url,"registry")
    return url


@dataclass(frozen=True)
class Model:
    raw: bytes

    @property
    def config(self):
        return parse_json(self.raw)


class Registry:
    def __init__(self, document):
        require(isinstance(document,dict) and set(document)=={"version","models"}
                and document["version"]=="llm-registry/1" and isinstance(document["models"],list)
                and 1<=len(document["models"])<=128,"registry")
        models={}
        for config in document["models"]:
            self.check(config)
            require(config["key"] not in models,"registry")
            models[config["key"]]=Model(canonical(config))
        self._models=models

    @classmethod
    def load(cls, path):
        with open(path,"rb") as f:
            raw=f.read(262145)
        require(len(raw)<=262144,"registry")
        return cls(parse_json(raw))

    def get(self,key):
        require(key in self._models,"registry")
        return self._models[key].config

    def keys(self):
        return tuple(sorted(self._models))

    @staticmethod
    def check(c):
        require(isinstance(c,dict) and set(c)==MODEL_KEYS,"registry")
        for k in ("key","provider","model"):
            require(isinstance(c[k],str) and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}",c[k]),"registry")
        require(re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}",c["key"]),"registry")
        require(c["revision"] is None or (isinstance(c["revision"],str) and len(c["revision"])<=128),"registry")
        require(c["family"] in FAMILIES and type(c["local"]) is type(c["enabled"]) is bool,"registry")
        endpoint(c["endpoint"],c["local"])
        require(c["auth_env"] is None or (isinstance(c["auth_env"],str)
                and re.fullmatch(r"[A-Z][A-Z0-9_]{2,127}",c["auth_env"])),"registry")
        require(c["local"] or c["auth_env"] is not None,"registry")
        caps=c["capabilities"]
        require(isinstance(caps,dict) and set(caps)==FEATURES,"registry")
        for entry in caps.values():
            require(isinstance(entry,dict) and set(entry)=={"support","status","source"}
                    and (entry["support"] is None or type(entry["support"]) is bool)
                    and entry["status"] in KNOWLEDGE and isinstance(entry["source"],str)
                    and 1<=len(entry["source"])<=1024,"registry")
        for name in ("context_limit","output_limit"):
            limit=c[name]
            require(limit is None or (isinstance(limit,dict) and set(limit)=={"tokens","status","source"}
                    and type(limit["tokens"]) is int and limit["tokens"]>0 and limit["status"] in KNOWLEDGE
                    and isinstance(limit["source"],str) and bool(limit["source"])),"registry")
        require(isinstance(c["provenance"],str) and 1<=len(c["provenance"])<=1024,"registry")
        w=c["wire"]
        require(isinstance(w,dict) and set(w)=={"max_tokens_field","anthropic_version","reasoning_values","routing"},"registry")
        require(w["max_tokens_field"] in ("max_tokens","max_completion_tokens"),"registry")
        require(isinstance(w["anthropic_version"],str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}",w["anthropic_version"]),"registry")
        require(isinstance(w["reasoning_values"],list) and len(w["reasoning_values"])<=16
                and all(type(v) in (str,int) for v in w["reasoning_values"]),"registry")
        route=w["routing"]
        if route is not None:
            require(c["provider"]=="openrouter" and isinstance(route,dict)
                    and set(route)=={"order","only","allow_fallbacks","require_parameters"}
                    and route["allow_fallbacks"] is False and route["require_parameters"] is True
                    and isinstance(route["order"],list) and len(route["order"])==1
                    and isinstance(route["order"][0],str) and re.fullmatch(r"[A-Za-z0-9_./-]{1,128}",route["order"][0])
                    and route["only"]==route["order"],"registry")
        require(not c["enabled"] or c["provider"]!="openrouter" or route is not None,"registry")
        price=c["pricing"]
        if price is not None:
            require(isinstance(price,dict) and set(price)=={"currency","input_per_million","output_per_million","source","as_of"}
                    and price["currency"]=="USD" and isinstance(price["source"],str) and bool(price["source"]),"registry")
            try:
                datetime.fromisoformat(price["as_of"])
                for key in ("input_per_million","output_per_million"):
                    require(isinstance(price[key],str) and Decimal(price[key]).is_finite() and Decimal(price[key])>=0,"registry")
            except (TypeError,ValueError,InvalidOperation):
                raise GatewayError("registry") from None


def negotiate(request, config, minimum="declared"):
    require(minimum in KNOWLEDGE,"capability")
    tiers={"declared":0,"probed":1,"live_verified":2}
    params=parse_json(request.parameters)
    needed=set(request.required)|{"text"}|{m.role for m in request.messages if m.role in ("system","developer")}
    needed |= params.keys()-{"max_output_tokens"}
    if request.schema is not None:
        needed.add("structured")
    needed|=request.optional
    omitted=[]
    for feature in sorted(needed):
        entry=config["capabilities"][feature]
        available=(feature in FAMILIES[config["family"]] and entry["support"] is True
                   and tiers[entry["status"]]>=tiers[minimum])
        if not available:
            require(feature in request.optional,"capability")
            omitted.append(feature)
    if "reasoning" in params and "reasoning" not in omitted:
        require((type(params["reasoning"]) is int and params["reasoning"]>=0) if config["family"]=="gemini"
                else isinstance(params["reasoning"],str),"capability")
        require(any(type(v) is type(params["reasoning"]) and v==params["reasoning"]
                    for v in config["wire"]["reasoning_values"]),"capability")
    limit=config["output_limit"]
    if limit is not None and tiers[limit["status"]]>=tiers[minimum]:
        require(params["max_output_tokens"]<=limit["tokens"],"limit")
    messages=[{"role":m.role,"content":m.text} for m in request.messages if m.role not in omitted]
    require(any(m["role"]=="user" for m in messages),"invalid_request")
    if config["family"]!="openai":
        require(sum(m["role"]=="system" for m in messages)<=1 and messages[-1]["role"]=="user"
                and all(m["role"]!="system" or i==0 for i,m in enumerate(messages)),"capability")
    effective={"contract":"llm-gateway/1","provider":config["provider"],"model":config["model"],"revision":config["revision"],
               "family":config["family"],"messages":messages,"parameters":{k:v for k,v in params.items() if k not in omitted},
               "schema":parse_json(request.schema) if request.schema is not None and "structured" not in omitted else None}
    return effective,tuple(omitted)


def mocked_probe(gateway, request, feature):
    """Exercise one configured contract through a mock, without changing model knowledge."""
    import httpx
    require(feature in FEATURES and isinstance(gateway.transport,httpx.MockTransport),"capability")
    result=gateway.generate(request)
    require(feature not in result.omitted,"capability")
    effective=parse_json(result.effective)
    exercised={"text"} | (effective["parameters"].keys()-{"max_output_tokens"})
    exercised|={m["role"] for m in effective["messages"] if m["role"] in ("system","developer")}
    if effective["schema"] is not None:
        exercised.add("structured")
    if result.usage.input_tokens is not None and result.usage.output_tokens is not None:
        exercised.add("usage")
    require(feature in exercised,"capability")
    config=gateway.registry.get(request.model_key)
    return {"provider":config["provider"],"model":config["model"],"feature":feature,"status":"probed",
            "verification":"mock-only","live_verified":False,"source":"synthetic httpx.MockTransport",
            "request_fingerprint":result.request_fingerprint}
