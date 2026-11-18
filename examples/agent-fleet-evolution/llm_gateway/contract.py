"""Immutable llm-gateway/1 contracts and bounded structured-output validation."""
from dataclasses import asdict, dataclass
import json
import math
import re

VERSION = "llm-gateway/1"
FEATURES = frozenset(("text","system","developer","structured","temperature","top_p","seed","reasoning","usage","tools"))
PARAMETERS = frozenset(("max_output_tokens","temperature","top_p","seed","reasoning"))


class GatewayError(Exception):
    """Safe taxonomy. Provider bodies, secrets and chained transport text stay private."""
    def __init__(self, code, *, attempts=0, uncertain_billing=False, history=(), usage=None, cost=None):
        self.code, self.attempts = code, attempts
        self.uncertain_billing, self.history = uncertain_billing, tuple(history)
        self.usage, self.cost = usage, cost
        super().__init__(f"Gateway {code} (attempts={attempts})")

    def receipt(self):
        return {"code":self.code,"attempts":self.attempts,"uncertain_billing":self.uncertain_billing,
                "history":list(self.history),"known_usage":asdict(self.usage) if self.usage is not None else None,
                "cost":parse_json(self.cost) if self.cost is not None else None}


def require(ok, code="invalid_request"):
    if not ok:
        raise GatewayError(code)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()


def parse_json(raw):
    def unique(pairs):
        output = {}
        for key,value in pairs:
            require(key not in output,"invalid_json")
            output[key]=value
        return output
    try:
        return json.loads(raw,object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(GatewayError("invalid_json")))
    except (ValueError,TypeError,UnicodeError,RecursionError):
        raise GatewayError("invalid_json") from None


@dataclass(frozen=True,repr=False)
class Message:
    role: str
    text: str

    def __post_init__(self):
        require(self.role in ("system","developer","user","assistant") and isinstance(self.text,str)
                and 0<len(self.text)<=131072)


@dataclass(frozen=True,repr=False)
class Request:
    model_key: str
    request_id: str
    correlation_id: str
    messages: tuple[Message,...]
    parameters: bytes
    schema: bytes|None = None
    required: frozenset[str] = frozenset(("text",))
    optional: frozenset[str] = frozenset()

    @classmethod
    def build(cls, model_key, request_id, correlation_id, messages, *, parameters, schema=None,
              required=("text",), optional=()):
        try:
            return cls(model_key,request_id,correlation_id,tuple(messages),canonical(parameters),
                       canonical(schema) if schema is not None else None,frozenset(required),frozenset(optional))
        except (ValueError,TypeError,RecursionError):
            raise GatewayError("invalid_request") from None

    def __post_init__(self):
        for value in (self.model_key,self.request_id,self.correlation_id):
            require(isinstance(value,str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}",value))
        require(isinstance(self.messages,tuple) and 1<=len(self.messages)<=32
                and all(isinstance(m,Message) for m in self.messages))
        require(self.required|self.optional<=FEATURES and not self.required&self.optional and "text" not in self.optional)
        p=parse_json(self.parameters)
        require(isinstance(p,dict) and p.keys()<=PARAMETERS)
        require(type(p.get("max_output_tokens")) is int and 1<=p["max_output_tokens"]<=65536)
        for name,upper in (("temperature",2),("top_p",1)):
            if name in p:
                require(type(p[name]) in (int,float) and math.isfinite(p[name]) and 0<=p[name]<=upper)
        if "seed" in p:
            require(type(p["seed"]) is int and 0<=p["seed"]<2**32)
        if "reasoning" in p:
            require(type(p["reasoning"]) in (str,int))
        require(any(m.role=="user" for m in self.messages))
        if self.schema is not None:
            check_schema(parse_json(self.schema))


# This explicitly versioned JSON Schema subset is the entire local validation language.
SCHEMA_KEYS = frozenset(("type","properties","required","additionalProperties","items","minItems","maxItems",
                         "minLength","maxLength","minimum","maximum","enum","description"))


def check_schema(schema, depth=0):
    require(isinstance(schema,dict) and depth<=12 and schema.keys()<=SCHEMA_KEYS,"invalid_schema")
    kind=schema.get("type")
    require(kind in ("object","array","string","integer","number","boolean","null"),"invalid_schema")
    if "description" in schema:
        require(isinstance(schema["description"],str) and len(schema["description"])<=1024,"invalid_schema")
    if "enum" in schema:
        require(isinstance(schema["enum"],list) and 1<=len(schema["enum"])<=256
                and all(type(x) in (str,int,float,bool,type(None)) for x in schema["enum"]),"invalid_schema")
    allowed={"type","description","enum"}
    if kind=="object":
        allowed|={"properties","required","additionalProperties"}
        props=schema.get("properties",{})
        required=schema.get("required",[])
        require(isinstance(props,dict) and len(props)<=128 and isinstance(required,list)
                and all(isinstance(x,str) for x in required) and len(required)==len(set(required))
                and set(required)<=props.keys() and schema.get("additionalProperties") is False,"invalid_schema")
        for value in props.values():
            check_schema(value,depth+1)
    if kind=="array":
        allowed|={"items","minItems","maxItems"}
        check_schema(schema.get("items"),depth+1)
    if kind=="string":
        allowed|={"minLength","maxLength"}
    if kind in ("integer","number"):
        allowed|={"minimum","maximum"}
    require(schema.keys()<=allowed,"invalid_schema")
    for lo,hi,integer in (("minItems","maxItems",True),("minLength","maxLength",True),("minimum","maximum",False)):
        for key in (lo,hi):
            if key in schema:
                value=schema[key]
                require(type(value) is int if integer else type(value) in (float,int),"invalid_schema")
                require(math.isfinite(value) and (value>=0 if integer else True),"invalid_schema")
        require(lo not in schema or hi not in schema or schema[lo]<=schema[hi],"invalid_schema")


def validate(value, schema):
    kind=schema["type"]
    good={"object":type(value) is dict,"array":type(value) is list,"string":type(value) is str,
          "integer":type(value) is int,"number":type(value) in (int,float) and math.isfinite(value),
          "boolean":type(value) is bool,"null":value is None}
    require(good[kind],"invalid_output")
    if "enum" in schema:
        require(any(type(value) is type(x) and value==x for x in schema["enum"]),"invalid_output")
    if kind=="object":
        props=schema.get("properties",{})
        require(set(schema.get("required",[]))<=value.keys() and value.keys()<=props.keys(),"invalid_output")
        for name,item in value.items():
            validate(item,props[name])
    if kind=="array":
        require(schema.get("minItems",0)<=len(value)<=schema.get("maxItems",65536),"invalid_output")
        for item in value:
            validate(item,schema["items"])
    if kind=="string":
        require(schema.get("minLength",0)<=len(value)<=schema.get("maxLength",131072),"invalid_output")
    if kind in ("integer","number"):
        require(schema.get("minimum",-math.inf)<=value<=schema.get("maximum",math.inf),"invalid_output")


@dataclass(frozen=True)
class Usage:
    input_tokens: int|None = None
    output_tokens: int|None = None
    total_tokens: int|None = None
    cached_tokens: int|None = None
    reasoning_tokens: int|None = None
    cache_creation_tokens: int|None = None

    def __post_init__(self):
        for count in asdict(self).values():
            require(count is None or (type(count) is int and 0<=count<2**63),"provider_protocol")
        if self.input_tokens is not None and self.cached_tokens is not None:
            require(self.cached_tokens<=self.input_tokens,"provider_protocol")
        if self.total_tokens is not None and self.input_tokens is not None and self.output_tokens is not None:
            require(self.total_tokens>=self.input_tokens+self.output_tokens,"provider_protocol")


@dataclass(frozen=True,repr=False)
class Result:
    request_id: str
    correlation_id: str
    provider: str
    model: str
    revision: str|None
    text: str
    usage: Usage
    latency_ms: float
    attempts: int
    omitted: tuple[str,...]
    effective: bytes
    request_fingerprint: str
    response_fingerprint: str
    registry_fingerprint: str
    cost: bytes
    provider_metadata: bytes
    attempt_history: tuple[str,...] = ()
    replayed: bool = False

    def structured(self):
        return parse_json(self.text)

    def receipt(self):
        # Caller explicitly consumes text/structured content. Routine receipts exclude both.
        return {"contract":VERSION,"request_id":self.request_id,"correlation_id":self.correlation_id,
                "provider":self.provider,"model":self.model,"revision":self.revision,"attempts":self.attempts,
                "latency_ms":self.latency_ms,"omitted":list(self.omitted),"replayed":self.replayed,
                "request_fingerprint":self.request_fingerprint,"response_fingerprint":self.response_fingerprint,
                "registry_fingerprint":self.registry_fingerprint,"usage":asdict(self.usage),"cost":parse_json(self.cost),
                "attempt_history":list(self.attempt_history)}
