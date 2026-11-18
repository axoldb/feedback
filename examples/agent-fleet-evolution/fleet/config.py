"""Explicit portable configuration. No owner credential or machine identity is assumed."""
from contextlib import contextmanager
from dataclasses import asdict,is_dataclass
from pathlib import Path
from uuid import UUID
import json,os,re
HERE=Path(__file__).resolve().parents[1]
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def name(run):
 if not re.fullmatch(r'[a-z][a-z0-9-]{0,39}',run):raise ValueError('Use a new lowercase run identifier')
 return 'axol://populations/public-fleet/'+run,'axol://forks/public-fleet/'+run+'/reference'
def wire(value):
 if is_dataclass(value):return wire(asdict(value))
 if isinstance(value,UUID):return str(value)
 if isinstance(value,bytes):return value.hex()
 if isinstance(value,dict):return {k:wire(v) for k,v in value.items()}
 if isinstance(value,(list,tuple)):return [wire(v) for v in value]
 return value
@contextmanager
def connect(config,role):
 import axoldb as sdk
 from importlib.metadata import version
 if version('axoldb-client')!='0.1.2.dev1':raise ValueError('Use official axoldb-client 0.1.2.dev1')
 cfg=load(config)
 if not cfg['endpoint'].startswith('https://'):raise ValueError('Strict HTTPS is required')
 variable=cfg[role+'TokenEnvironment'];token=os.environ.get(variable)
 if not token:raise ValueError('Missing scoped '+role+' credential environment variable')
 provider=sdk.InMemoryCredentialProvider(sdk.AxolDbCredential(access_token=token))
 try:
  with sdk.AxolDbClient(cfg['endpoint'],trust=sdk.CaFile(path=Path(cfg['caFile'])),credential_provider=provider) as client:
   if not client.operational.get_version().startswith('0.1.2-developer-preview'):raise ValueError('Server version differs')
   yield client
 finally:provider.set_credential(None)
