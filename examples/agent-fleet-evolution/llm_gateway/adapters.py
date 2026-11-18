"""Bounded non-streaming wire bindings. No tools, multimodal data or fallback."""
import re
from urllib.parse import quote

from .contract import GatewayError, Usage, require


def encode(effective, config):
    family=config["family"]
    params=effective["parameters"]
    schema=effective["schema"]
    messages=effective["messages"]
    model=config["model"]
    if family=="openai":
        body={"model":model,"messages":messages,config["wire"]["max_tokens_field"]:params["max_output_tokens"],
              "stream":False,"n":1}
        for key in ("temperature","top_p","seed"):
            if key in params:
                body[key]=params[key]
        if "reasoning" in params:
            body["reasoning_effort"]=params["reasoning"]
        if schema is not None:
            body["response_format"]={"type":"json_schema","json_schema":{"name":"gateway_output","strict":True,"schema":schema}}
        if config["wire"]["routing"] is not None:
            body["provider"]=config["wire"]["routing"]
        return config["endpoint"],body
    system=[m["content"] for m in messages if m["role"]=="system"]
    ordinary=[m for m in messages if m["role"]!="system"]
    if family=="anthropic":
        body={"model":model,"messages":ordinary,"max_tokens":params["max_output_tokens"]}
        if system:
            body["system"]=system[0]
        for key in ("temperature","top_p"):
            if key in params:
                body[key]=params[key]
        output={}
        if schema is not None:
            output["format"]={"type":"json_schema","schema":schema}
        if "reasoning" in params:
            output["effort"]=params["reasoning"]
        if output:
            body["output_config"]=output
        if config["wire"]["routing"] is not None:
            body["provider"]=config["wire"]["routing"]
        return config["endpoint"],body
    generation={"maxOutputTokens":params["max_output_tokens"],"candidateCount":1}
    for key,dest in (("temperature","temperature"),("top_p","topP"),("seed","seed")):
        if key in params:
            generation[dest]=params[key]
    if "reasoning" in params:
        require(type(params["reasoning"]) is int and params["reasoning"]>=0,"capability")
        generation["thinkingConfig"]={"thinkingBudget":params["reasoning"]}
    if schema is not None:
        generation.update(responseMimeType="application/json",responseJsonSchema=schema)
    body={"contents":[{"role":"model" if m["role"]=="assistant" else "user","parts":[{"text":m["content"]}]}
                      for m in ordinary],"generationConfig":generation}
    if system:
        body["systemInstruction"]={"parts":[{"text":system[0]}]}
    url=config["endpoint"]+"/models/"+quote(model,safe="")+":generateContent"
    return url,body


def auth(config, secret):
    headers={}
    if config["family"]=="anthropic":
        headers["anthropic-version"]=config["wire"]["anthropic_version"]
        if secret is not None:
            headers["x-api-key"]=secret
    elif config["family"]=="gemini":
        if secret is not None:
            headers["x-goog-api-key"]=secret
    elif secret is not None:
        headers["Authorization"]="Bearer "+secret
    return headers


def count(value):
    require(value is None or (type(value) is int and 0<=value<2**63),"provider_protocol")
    return value


def usage_fields(document, family):
    require(document is None or isinstance(document,dict),"provider_protocol")
    doc=document or {}
    if family=="openai":
        cached=doc.get("prompt_tokens_details") or {}
        reasoning=doc.get("completion_tokens_details") or {}
        require(isinstance(cached,dict) and isinstance(reasoning,dict),"provider_protocol")
        return Usage(*map(count,(doc.get("prompt_tokens"),doc.get("completion_tokens"),doc.get("total_tokens"),
                                cached.get("cached_tokens"),reasoning.get("reasoning_tokens"))))
    if family=="anthropic":
        cached=doc.get("cache_read_input_tokens")
        created=doc.get("cache_creation_input_tokens")
        base=doc.get("input_tokens")
        for value in (cached,created,base):
            count(value)
        # Anthropic input_tokens excludes cache-hit and cache-creation input tokens.
        total_input=None if base is None else base+(cached or 0)+(created or 0)
        return Usage(total_input,count(doc.get("output_tokens")),None,count(cached),None,count(created))
    return Usage(*map(count,(doc.get("promptTokenCount"),doc.get("candidatesTokenCount"),doc.get("totalTokenCount"),
                             doc.get("cachedContentTokenCount"),doc.get("thoughtsTokenCount"))))


def decode(document, family):
    require(isinstance(document,dict),"provider_protocol")
    # Whitelisted metadata stays separate from normalized usage and generated content.
    if family=="openai":
        choices=document.get("choices")
        require(isinstance(choices,list) and len(choices)==1,"provider_protocol")
        choice=choices[0]
        message=choice.get("message")
        require(isinstance(message,dict),"provider_protocol")
        require(not message.get("tool_calls") and not message.get("function_call"),"unsupported_response")
        require(not message.get("refusal"),"refused")
        finish=choice.get("finish_reason")
        require(finish=="stop","truncated" if finish=="length" else "refused")
        text=message.get("content")
        usage=usage_fields(document.get("usage"),family)
    elif family=="anthropic":
        finish=document.get("stop_reason")
        require(finish=="end_turn","truncated" if finish=="max_tokens" else "refused")
        parts=document.get("content")
        require(isinstance(parts,list) and parts,"provider_protocol")
        require(all(isinstance(p,dict) and p.get("type") in ("text","thinking","redacted_thinking") for p in parts),
                "unsupported_response")
        require(all(isinstance(p.get("text"),str) for p in parts if p["type"]=="text"),"provider_protocol")
        text="".join(p["text"] for p in parts if p["type"]=="text")
        usage=usage_fields(document.get("usage"),family)
    else:
        require(not document.get("promptFeedback",{}).get("blockReason"),"refused")
        candidates=document.get("candidates")
        require(isinstance(candidates,list) and len(candidates)==1,"provider_protocol")
        candidate=candidates[0]
        finish=candidate.get("finishReason")
        require(finish=="STOP","truncated" if finish=="MAX_TOKENS" else "refused")
        parts=candidate.get("content",{}).get("parts")
        require(isinstance(parts,list) and parts,"provider_protocol")
        require(all(isinstance(p,dict) and isinstance(p.get("text"),str) and not (p.keys()-{"text","thought","thoughtSignature"})
                    for p in parts),"unsupported_response")
        text="".join(p["text"] for p in parts if not p.get("thought",False))
        usage=usage_fields(document.get("usageMetadata"),family)
    require(isinstance(text,str) and bool(text),"provider_protocol")
    actual_model=document.get("modelVersion" if family=="gemini" else "model")
    require(actual_model is None or (isinstance(actual_model,str) and
            re.fullmatch(r"[A-Za-z0-9_./:-]{1,256}",actual_model)),"provider_protocol")
    return text,usage,{"finish":finish,"reported_model":actual_model}
