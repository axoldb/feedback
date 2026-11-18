"""Versioned diagnostic streaming transport; existing Phase 1 adapter remains unchanged."""
import asyncio
import base64
import hashlib
import hmac
import json
from pathlib import Path
import time
import sys

from . import recording as c
from .contract import parse_json,canonical,validate,require,GatewayError


def sha(raw):return hashlib.sha256(raw).hexdigest()


def seal(data,key):
    return {"data":data,"signature":hmac.new(key,canonical(data),hashlib.sha256).hexdigest()}


def read_signed(path,key):
    obj=parse_json(Path(path).read_bytes())
    require(set(obj)=={"data","signature"} and hmac.compare_digest(obj["signature"],seal(obj["data"],key)["signature"]),"recording_integrity")
    return obj["data"]


class Capture:
    def __init__(self,model,limit):
        self.model=model;self.limit=limit;self.bytes=0;self.buffer=b""
        self.text="";self.final=None;self.events=0
        self.firstByte=None;self.firstText=None;self.chunks=[];self.finishedAt=None

    def feed(self,raw,seconds):
        require(self.bytes+len(raw)<=self.limit,"response_limit")
        if raw and self.firstByte is None:self.firstByte=seconds
        self.chunks.append({"offset":self.bytes,"length":len(raw),"seconds":seconds})
        self.bytes+=len(raw);self.buffer+=raw
        while b"\n" in self.buffer:
            line,self.buffer=self.buffer.split(b"\n",1)
            if line.strip():self.event(parse_json(line),seconds)

    def event(self,event,seconds):
        require(self.final is None and isinstance(event,dict) and not event.get("error"),"provider_protocol")
        require(event.get("model")==self.model,"model_identity")
        require(isinstance(event.get("response",""),str) and not event.get("thinking"),"provider_protocol")
        if event.get("response"):
            if self.firstText is None:self.firstText=seconds
            self.text+=event["response"]
        self.events+=1
        if event.get("done") is True:self.final=event

    def finish(self,seconds):
        self.finishedAt=seconds
        if self.buffer.strip():
            self.event(parse_json(self.buffer),seconds);self.buffer=b""
        require(self.final is not None,"incomplete_response")

    def view(self):
        return {"bytes":self.bytes,"events":self.events,"firstBodyByteSeconds":self.firstByte,
                "firstTextDeltaSeconds":self.firstText,"text":self.text,"final":self.final,
                "pendingBytes":len(self.buffer),"chunks":self.chunks,"finishSeconds":self.finishedAt}


async def consume(spec,endpoint,model,output,cancel_file,*,transport=None):
    import httpx
    capture=Capture(model,131072);started=time.monotonic();headers=None
    result={"status":None,"httpStatus":None,"headersSeconds":None,"capture":None,"error":None}
    wire=Path(output).with_suffix(".wire")
    with wire.open("xb") as rawfile:
        async def request():
            nonlocal headers
            timeout=httpx.Timeout(connect=5,read=spec["inactivitySeconds"],write=10,pool=2)
            async with httpx.AsyncClient(base_url=endpoint,timeout=timeout,transport=transport,
                                        trust_env=False,follow_redirects=False) as client:
                async with client.stream("POST","/api/generate",content=canonical(spec["body"]),
                            headers={"Content-Type":"application/json","Accept-Encoding":"identity"}) as response:
                    headers=time.monotonic()-started;result["headersSeconds"]=headers;result["httpStatus"]=response.status_code
                    require(response.status_code==200,"provider_http")
                    require(response.headers.get("content-encoding","identity")=="identity","provider_protocol")
                    async for block in response.aiter_bytes():
                        require(capture.bytes+len(block)<=capture.limit,"response_limit")
                        seconds=time.monotonic()-started
                        rawfile.write(block);rawfile.flush()
                        import os
                        os.fsync(rawfile.fileno())
                        capture.feed(block,seconds)
                        c.atomic(Path(output).with_suffix(".progress.json"),
                                 {"headersSeconds":headers,"capture":capture.view()})
                    capture.finish(time.monotonic()-started)
        async def cancelled():
            while not Path(cancel_file).exists():await asyncio.sleep(.05)
        task=asyncio.create_task(request());monitor=asyncio.create_task(cancelled())
        try:
            done,_=await asyncio.wait((task,monitor),timeout=spec["deadlineSeconds"],return_when=asyncio.FIRST_COMPLETED)
            if task in done:
                await task;result["status"]="COMPLETE"
            else:
                result["status"]="CANCELLED" if monitor in done else "TIMEOUT_TOTAL"
        except httpx.ReadTimeout:result["status"]="TIMEOUT_INACTIVITY"
        except httpx.TimeoutException:result["status"]="TIMEOUT_IO"
        except httpx.HTTPError:result["status"]="NETWORK_ERROR"
        except GatewayError as exc:result["status"]="PROTOCOL_ERROR";result["error"]=exc.code
        except (ValueError,UnicodeError):result["status"]="PROTOCOL_ERROR";result["error"]="invalid_json"
        finally:
            for job in (task,monitor):
                if not job.done():job.cancel()
            await asyncio.gather(task,monitor,return_exceptions=True)
    result.update(elapsedSeconds=time.monotonic()-started,capture=capture.view(),wireSha256=sha(wire.read_bytes()))
    return result


def metrics(result,spec):
    final=result["capture"]["final"]
    out={"providerInputTokens":None,"providerOutputTokens":None,"loadSeconds":None,
         "promptSeconds":None,"generationSeconds":None,"providerTotalSeconds":None,
         "providerGeneratedTokensPerSecond":None}
    if final is None:return out
    i,o=final.get("prompt_eval_count"),final.get("eval_count")
    require(type(i)is int and type(o)is int and min(i,o)>=0 and o<=spec["body"]["options"]["num_predict"]
            and i<=spec["body"]["options"]["num_ctx"],"token_accounting")
    out.update(providerInputTokens=i,providerOutputTokens=o)
    for dest,key in (("loadSeconds","load_duration"),("promptSeconds","prompt_eval_duration"),
                     ("generationSeconds","eval_duration"),("providerTotalSeconds","total_duration")):
        n=final.get(key)
        require(n is None or type(n)is int and n>=0,"duration_accounting")
        if n is not None:out[dest]=n/1e9
    if out["generationSeconds"]:out["providerGeneratedTokensPerSecond"]=o/out["generationSeconds"]
    return out


def replay(receipt_path,key):
    receipt=read_signed(receipt_path,key);data=receipt["result"]
    raw=Path(receipt_path).with_suffix(".wire").read_bytes()
    require(sha(raw)==data["wireSha256"],"recording_integrity")
    capture=Capture(receipt["model"],131072)
    parse_error=None
    try:
        for chunk in data["capture"]["chunks"]:
            section=raw[chunk["offset"]:chunk["offset"]+chunk["length"]]
            require(len(section)==chunk["length"],"recording_integrity")
            capture.feed(section,chunk["seconds"])
        if data["capture"]["finishSeconds"] is not None:capture.finish(data["capture"]["finishSeconds"])
    except GatewayError as exc:parse_error=exc.code
    require(parse_error is None or (data["status"]=="PROTOCOL_ERROR" and parse_error==data["error"]),"replay_mismatch")
    require(capture.view()==data["capture"],"replay_mismatch")
    require(receipt["requestSha256"]==sha(canonical(receipt["spec"]["body"])),"replay_mismatch")
    return {"status":"PASS","probe":receipt["spec"]["number"],"providerCalls":0,
            "wireSha256":data["wireSha256"],"receiptSha256":sha(canonical(receipt)),
            "originalOutcome":data["status"],"exact":True}
