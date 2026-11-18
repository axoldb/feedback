"""Two deterministic agents, two nonempty Generations, independent persisted replay."""
import json,os
from pathlib import Path
from .model import Scenario,canonical,digest,generation_records,verify_records
from .config import HERE,load

def offline():
 scenario=Scenario.load(load(HERE/'scenario.json'));first=generation_records(scenario,0);second=generation_records(scenario,1,first)
 return {'format':'fleet-public/1','source':'fresh deterministic application computation; not database evidence','scenario':scenario.data(),
  'generations':[{'number':0,'payloads':first},{'number':1,'payloads':second}],'scientificHash':digest([first,second])}
def replay(value):
 scenario=Scenario.load(value['scenario']);previous=[];frames=[]
 if len(value['generations'])!=2:raise ValueError('Exactly two Generations are required')
 for number,g in enumerate(value['generations']):
  if g['number']!=number:raise ValueError('Generation continuity')
  records=verify_records(scenario,number,g['payloads'],previous);frames.append(records);previous=records
 if value['scientificHash']!=digest(frames):raise ValueError('Scientific hash differs')
 return {'exact':True,'generations':2,'scientificHash':value['scientificHash'],'modelCalls':0}
def read(config,run):
 from .config import connect
 from .storage import Store
 with connect(config,'viewer') as client:
  store=Store(client,run,verify_receipts=False);frames=store.read_run()
  if len(frames)!=2:raise ValueError('Run not complete; no visualization fallback')
  fork=store.reference_fork(frames[0]);scenario=next(r['scenario'] for r in frames[0]['payloads'] if r['record_type']=='Scenario')
  result={'format':'fleet-public/1','source':'fresh authenticated AxolDB read','scenario':scenario,
   'population':store.pop,'fork':fork,'generations':[{'number':n,'native':f['generation'],'payloads':f['payloads'],'checkpoint':f['checkpoint'],'checkpointHash':f['checkpoint_sha256']} for n,f in enumerate(frames)],
   'scientificHash':digest([f['payloads'] for f in frames])}
 replay(result);return result
def run(config,run_id,through):
 from .config import connect
 from .storage import Store
 scenario=Scenario.load(load(HERE/'scenario.json'))
 with connect(config,'writer') as client:
  store=Store(client,run_id);frames=store.read_run()
  for number in range(len(frames),through+1):
   old=frames[-1] if frames else None
   frames.append(store.publish(scenario,number,old['generation']['generation_id'] if old else None,old))
  store.reference_fork(frames[0],create=True)
 if through==0:return {'status':'Generation 0 durably committed; exit and resume in a fresh process','generations':len(frames)}
 # A new client and distinct viewer credential must establish success.
 return read(config,run_id)
def save(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);raw=canonical(value)+b'\n'
 if path.exists():
  if path.read_bytes()!=raw:raise ValueError('Refuse to overwrite different evidence')
  return
 with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
