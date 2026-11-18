"""Application fixture encoding, not a replacement SDK or transport.

Only the ACE-1 subset needed for one binary Schema and JSON payload hash framing.
Framing: Spec04 sections 14, 64-74, 77-80, 97, 134 and 134.1. No product code is
imported. Tests compare the two normative vectors before any network mutation.
"""
import base64,hashlib,json,unicodedata
import axoldb as sdk

def canonical_json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def uvarint(value):
    result=bytearray()
    while True:
        part=value&127;value>>=7;result.append(part|(128 if value else 0))
        if not value:return bytes(result)

def string(value):
    data=unicodedata.normalize('NFC',value).encode();return uvarint(len(data))+data

def record(values):
    return sdk.Ace1Record(fields=tuple(sdk.RecordField(name=k,value=v) for k,v in sorted(values.items())))

def nested(value):
    if isinstance(value,sdk.Ace1Bool):return b'\x02' if value.value else b'\x01'
    if isinstance(value,sdk.Ace1Integer):
        number=int(value.value.text);size=(abs(number).bit_length()+7)//8
        return b'\x10'+bytes([0 if number==0 else 1 if number>0 else 2])+uvarint(size)+abs(number).to_bytes(size,'big')
    if isinstance(value,sdk.Ace1String):return b'\x12'+string(value.value)
    if isinstance(value,sdk.Ace1Binary):return b'\x14'+uvarint(len(value.hex))+value.hex
    if isinstance(value,sdk.Ace1Record):return b'\x20'+uvarint(len(value.fields))+b''.join(string(f.name)+nested(f.value) for f in value.fields)
    if isinstance(value,sdk.Ace1Sequence):return b'\x21'+uvarint(len(value.elements))+b''.join(nested(v) for v in value.elements)
    if isinstance(value,sdk.Ace1Map) and not value.entries:return b'\x22\x00'
    if isinstance(value,sdk.Ace1Union):return b'\x23'+string(value.variant_name)+nested(value.value)
    raise ValueError('Not part of this bounded application fixture codec')

def schema_document(schema_id,kind='binary'):
    return b'ACE1\0'+nested(record({'definitions':sdk.Ace1Map(entries=()),'dependencies':sdk.Ace1Sequence(elements=()),'extensions':sdk.Ace1Map(entries=()),'rootType':sdk.Ace1Union(variant_name='inline',value=record({'constraints':record({}),'kind':sdk.Ace1String(value=kind),'nullable':sdk.Ace1Bool(value=False),'parameters':record({})})),'schemaId':sdk.Ace1String(value=schema_id),'schemaLanguageVersion':sdk.Ace1String(value='axol-schema/1'),'schemaVersion':sdk.Ace1Integer(value=sdk.CanonicalInteger(text='1'))}))

def schema_hash(schema_id,document):
    return hashlib.sha256(b'AXOL-SCHEMA\0\0\1'+string(schema_id)+uvarint(len(document))+document).hexdigest()

def genotype_hash(schema_id,schema_digest,ace1):
    return hashlib.sha256(b'AXOL-GENOTYPE\0\0\1'+string(schema_id)+bytes.fromhex(schema_digest)+uvarint(len(ace1))+ace1).hexdigest()

def self_test():
    integer_doc=schema_document('axol://schemas/test/integer/1','integer')
    assert schema_hash('axol://schemas/test/integer/1',integer_doc)=='ad3f8d5e3b755db3ea4b004b4ee8656d0a07e298e6061a89575ab93d08042169'
    integer=b'ACE1\0'+nested(sdk.Ace1Integer(value=sdk.CanonicalInteger(text='1')))
    assert genotype_hash('axol://schemas/test/scalar/1',bytes(range(32)).hex(),integer)=='12fbf2a24fb9feef1aca028549b07fec406b91dca3c1fe31629ccb602c44c369'
    return {'schemaHashVector':'PASS','genotypeHashVector':'PASS'}

SCHEMA_ID='axol://schemas/agent-fleet-evolution/canonical-json/1'
SCHEMA_DOCUMENT=schema_document(SCHEMA_ID)
SCHEMA_HASH=schema_hash(SCHEMA_ID,SCHEMA_DOCUMENT)

def genotype(payload):
    raw=canonical_json(payload);value=sdk.Ace1Binary(hex=raw)
    digest=genotype_hash(SCHEMA_ID,SCHEMA_HASH,b'ACE1\0'+nested(value))
    return sdk.Genotype(schema_id=SCHEMA_ID,schema_hash_hex=SCHEMA_HASH,value=value,genotype_hash_hex=digest)

if __name__=='__main__':print(json.dumps(self_test()))
