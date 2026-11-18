"""Opt-in one-call local gateway binding. Never invoked by the deterministic example or tests."""
import argparse,asyncio,json,os,urllib.request
from pathlib import Path
from llm_gateway import Message,Request
from llm_gateway import native_stream as transport
from .proposal import evaluate,ProposalProvider
from .model import canonical,digest

DIGEST='a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a'
SCHEMA={'type':'object','additionalProperties':False,'required':['order'],'properties':{'order':{'type':'array','minItems':5,'maxItems':5,'items':{'type':'string','enum':['d1','d2','d3','d4','d5']}}}}
class LocalProvider:
 def __init__(self,directory):self.directory=Path(directory)
 def propose(self,request):
  directory=self.directory;directory.mkdir(parents=True,exist_ok=True)
  from llm_gateway.contract import parse_json
  if not isinstance(request,Request) or request.model_key!='ollama':raise ValueError('Explicit local gateway Request required')
  parameters=parse_json(request.parameters)
  if parameters.get('max_output_tokens')!=192 or parse_json(request.schema)!=SCHEMA:raise ValueError('Bounded proposal contract required')
  normalized={'messages':[{'role':m.role,'text':m.text} for m in request.messages],'parameters':parameters,'schema':SCHEMA}
  prompt='\n'.join(m.text for m in request.messages)
  if len(prompt.encode())>1856:raise ValueError('Prompt exceeds conservative byte/token reservation')
  reservation=directory/'reservation.json'
  with reservation.open('x') as f:json.dump({'model':'gemma3:4b','expectedDigest':DIGEST,'maximumCalls':1,'requestHash':digest(normalized),'retries':0},f);f.flush();os.fsync(f.fileno())
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  with opener.open('http://127.0.0.1:11434/api/tags',timeout=5) as response:models=json.load(response)['models']
  if not any(x['name']=='gemma3:4b' and x['digest']==DIGEST for x in models):raise ValueError('Exact installed model missing; no pull or fallback')
  body={'model':'gemma3:4b','prompt':prompt,'stream':True,'format':SCHEMA,'keep_alive':'30s','options':{'num_ctx':2048,'num_predict':192,'temperature':0,'seed':71011}}
  spec={'number':1,'body':body,'requestSha256':digest(body),'deadlineSeconds':180,'inactivitySeconds':90}
  result=asyncio.run(transport.consume(spec,'http://127.0.0.1:11434','gemma3:4b',directory/'response.json',directory/'CANCEL'))
  record={'model':'gemma3:4b','modelDigest':DIGEST,'spec':spec,'requestSha256':spec['requestSha256'],'result':result}
  # Private integrity key is created only in the caller-selected private directory; never public evidence.
  key=os.urandom(32);(directory/'recording.key').write_bytes(key);transport.c.atomic(directory/'response.json',transport.seal(record,key))
  if result['status']!='COMPLETE' or result['capture']['final'].get('done_reason')!='stop':raise ValueError('Provider failed; recording preserved, no retry')
  usage=transport.metrics(result,spec)
  if usage['providerInputTokens']>1856:raise ValueError('Input token ceiling exceeded; preserve recording and stop')
  proposal=evaluate(parse_json(result['capture']['text']))
  return dict(proposal,usage=usage,latencySeconds=result['elapsedSeconds'],liveReproducibilityClaim=False)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--allow-local-inference',action='store_true');parser.add_argument('--private-directory',type=Path,required=True);args=parser.parse_args()
 if not args.allow_local_inference:parser.error('One local inference call requires explicit opt-in')
 request=Request.build('ollama','public-permutation-1','public-permutation-1',(Message('user','Return only JSON with order: a permutation of d1,d2,d3,d4,d5, each exactly once. Two vehicles, capacity three each, both return to depot.'),),parameters={'max_output_tokens':192},schema=SCHEMA,required=('text','structured','usage'))
 result=LocalProvider(args.private_directory).propose(request)
 print(json.dumps({'feasible':result['feasible'],'independentlyComputedCost':result['cost'],'modelCalls':1}))
