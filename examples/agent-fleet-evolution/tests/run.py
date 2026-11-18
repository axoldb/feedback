"""Machine-readable unit/SDK-contract/live suites. Live suite is read-only."""
import argparse,copy,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fleet import model as m,demo,proposal
from fleet.config import load,name
class Unit(unittest.TestCase):
 def setUp(self):self.value=demo.offline();self.scenario=m.Scenario.load(self.value['scenario'])
 def test_canonical_graph(self):self.assertEqual(m.digest(self.scenario.data()),'1acacbbfa8df146502938a12c18341524d7c8aadfccd9d3b893bb224f68c4ffa')
 def test_graph_order_irrelevant(self):
  raw=copy.deepcopy(self.value['scenario']);raw['edges'].reverse();raw['nodes'].reverse();self.assertEqual(m.digest(m.Scenario.load(raw).data()),m.digest(self.scenario.data()))
 def test_negative_edge_rejected(self):
  raw=copy.deepcopy(self.value['scenario']);raw['edges'][0][2]=-1
  with self.assertRaises(m.Invalid):m.Scenario.load(raw)
 def test_disconnected_graph_rejected(self):
  raw=copy.deepcopy(self.value['scenario']);raw['edges']=[]
  with self.assertRaises(m.Invalid):m.Scenario.load(raw)
 def test_shortest_tie(self):self.assertEqual(m.shortest(self.scenario,'depot','e'),(4,('depot','d','e')))
 def test_agents_repeat(self):self.assertEqual(demo.offline(),demo.offline())
 def test_scenario_immutable(self):
  raw=self.scenario.data();m.generation_records(self.scenario,0);self.assertEqual(raw,self.scenario.data())
 def test_two_generations(self):self.assertEqual([x['number'] for x in self.value['generations']],[0,1])
 def test_costs_are_computed(self):
  for frame in self.value['generations']:
   plans=[x for x in frame['payloads'] if x['record_type']=='FleetPlan'];self.assertEqual([m.validate_plan(self.scenario,x) for x in plans],[24,22])
 def test_routes_change_without_claimed_improvement(self):
  a,b=([x for x in g['payloads'] if x['record_type']=='FleetPlan'] for g in self.value['generations']);self.assertTrue(all(x['ordered_delivery_routes']!=y['ordered_delivery_routes'] for x,y in zip(a,b)))
 def test_missing_delivery_rejected(self):
  with self.assertRaises(ValueError):proposal.evaluate({'order':['d1','d2']})
 def test_duplicate_delivery_rejected(self):
  with self.assertRaises(ValueError):proposal.evaluate({'order':['d1','d2','d3','d4','d4']})
 def test_model_cost_rejected(self):
  with self.assertRaises(ValueError):proposal.evaluate({'order':['d1','d2','d3','d4','d5'],'cost':1})
 def test_independent_capacity_decoder(self):self.assertEqual({v:len(x) for v,x in proposal.evaluate({'order':['d1','d2','d3','d4','d5']})['orders'].items()},{'v1':3,'v2':2})
 def test_replay_exact(self):self.assertTrue(demo.replay(self.value)['exact'])
 def test_replay_tamper_rejected(self):
  self.value['generations'][1]['payloads'][0]['memory']={'bad':1}
  with self.assertRaises(m.Invalid):demo.replay(self.value)
 def test_authored_recording_no_calls(self):self.assertEqual(proposal.recorded(ROOT/'synthetic-recording.json')['modelCalls'],0)
 def test_core_needs_no_sdk(self):
  original=__import__
  def guarded(name,*args,**kwargs):
   if name.split('.')[0] in ['axoldb','httpx','llm_gateway']:raise AssertionError('Optional dependency imported')
   return original(name,*args,**kwargs)
  with patch('builtins.__import__',guarded):self.assertEqual(demo.offline(),self.value)
 def test_fresh_process_replay(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'record.json';p.write_bytes(m.canonical(self.value))
   result=subprocess.run([sys.executable,'-B','-m','fleet','replay','--recorded',str(p)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
 def test_output_refuses_changed_evidence(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'evidence.json';demo.save(p,{'x':1});demo.save(p,{'x':1})
   with self.assertRaises(ValueError):demo.save(p,{'x':2})
 def test_namespace_validation(self):
  self.assertTrue(name('portable-example')[0].startswith('axol://populations/public-fleet/'))
  with self.assertRaises(ValueError):name('../existing')
 def test_application_mutation(self):
  from fleet.operators import swap
  value=swap(['d1','d2','d3','d4','d5'],0,4);self.assertTrue(value['feasible']);self.assertEqual(value['order'][0],'d5')
 def test_application_crossover(self):
  from fleet.operators import crossover
  value=crossover(['d1','d2','d3','d4','d5'],['d5','d4','d3','d2','d1'],1,3);self.assertEqual(set(value['order']),{'d1','d2','d3','d4','d5'});self.assertEqual(len(set(value['order'])),5)
 def test_application_operator_provenance(self):
  from fleet.operators import crossover
  value=crossover(['d1','d2','d3','d4','d5'],['d5','d4','d3','d2','d1'],1,3);self.assertEqual(value['provenance']['operator'],'application-ordered-crossover');self.assertFalse(value['modelCostTrusted'])
class SDK(unittest.TestCase):
 def test_encoding_vectors(self):
  from fleet import codec
  self.assertEqual(set(codec.self_test().values()),{'PASS'})
 def test_record_genotype_hash(self):
  from fleet import codec
  self.assertEqual(codec.genotype({'x':1}),codec.genotype({'x':1}))
 def test_pending_receipt_no_retry(self):
  from fleet.storage import Store
  from types import SimpleNamespace
  sent=[];store=Store(SimpleNamespace(parity=SimpleNamespace(operation_resolve=lambda _:SimpleNamespace(outcome='pending'))),'unit')
  with self.assertRaises(m.Invalid):store.ensure_effect(object(),lambda **x:x,sent.append)
  self.assertEqual(sent,[])
 def test_checkpoint_hashes(self):
  from fleet.storage import checkpoint,verify_checkpoint
  docs=demo.offline()['generations'][0]['payloads'];pop,fork=name('unit');value=checkpoint(pop,fork,0,None,None,docs)
  verify_checkpoint(value,pop,fork,0,None,None,docs)
  with self.assertRaises(m.Invalid):verify_checkpoint(dict(value,payloads=[]),pop,fork,0,None,None,docs)
 def test_gateway_model_registry(self):
  from llm_gateway import Registry
  Registry(load(ROOT/'llm_gateway/model.example.json'))
 def test_gateway_request_contract(self):
  from llm_gateway import Request,Message
  from fleet.local_llm import SCHEMA
  request=Request.build('ollama','unit','unit',(Message('user','Order'),),parameters={'max_output_tokens':192},schema=SCHEMA,required=('text','structured','usage'));self.assertEqual(request.model_key,'ollama')
 def test_strict_https(self):
  from fleet.config import connect
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'config.json';path.write_text(json.dumps({'endpoint':'http://localhost:1'}))
   with self.assertRaisesRegex(ValueError,'HTTPS'):
    with connect(path,'viewer'):pass
 def test_stream_recorded_replay(self):
  from llm_gateway import native_stream as t
  body={'model':'gemma3:4b','stream':True};spec={'number':1,'body':body,'requestSha256':t.sha(t.canonical(body))}
  raw=t.canonical({'model':'gemma3:4b','response':'OK','done':True})+b'\n';cap=t.Capture('gemma3:4b',131072);cap.feed(raw[:4],.1);cap.feed(raw[4:],.2);cap.finish(.3)
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'record.json';p.with_suffix('.wire').write_bytes(raw);key=b'authored-public-synthetic-replay-key'
   t.c.atomic(p,t.seal({'model':'gemma3:4b','spec':spec,'requestSha256':spec['requestSha256'],'result':{'status':'COMPLETE','capture':cap.view(),'wireSha256':t.sha(raw),'error':None}},key))
   self.assertTrue(t.replay(p,key)['exact'])
 def test_stream_model_identity(self):
  from llm_gateway import native_stream as t
  with self.assertRaises(t.GatewayError):t.Capture('gemma3:4b',1000).feed(t.canonical({'model':'other','response':'x','done':True})+b'\n',.1)
 def test_stream_partial_not_complete(self):
  from llm_gateway import native_stream as t
  cap=t.Capture('gemma3:4b',1000);cap.feed(t.canonical({'model':'gemma3:4b','response':'partial','done':False})+b'\n',.1)
  with self.assertRaises(t.GatewayError):cap.finish(.2)
class Live(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.snapshot=demo.read(os.environ['FLEET_TEST_CONFIG'],os.environ['FLEET_TEST_RUN'])
 def test_authenticated_read(self):self.assertEqual(self.snapshot['source'],'fresh authenticated AxolDB read')
 def test_exact_replay(self):self.assertTrue(demo.replay(self.snapshot)['exact'])
 def test_native_generation_inventory(self):self.assertEqual([x['native']['generation_number'] for x in self.snapshot['generations']],[0,1])
 def test_membership(self):self.assertTrue(all(x['native']['member_count']==6 for x in self.snapshot['generations']))
 def test_checkpoint_links(self):self.assertEqual(self.snapshot['generations'][1]['checkpoint']['previous_checkpoint_sha256'],self.snapshot['generations'][0]['checkpointHash'])
 def test_readback_again(self):self.assertEqual(demo.read(os.environ['FLEET_TEST_CONFIG'],os.environ['FLEET_TEST_RUN']),self.snapshot)
 def test_native_typed_readback(self):
  from fleet.native import verify
  value=verify(os.environ['FLEET_TEST_CONFIG'],load(os.environ['FLEET_NATIVE_RECORD']));self.assertEqual(value['fixtures'],2)
class Result(unittest.TestResult):
 def __init__(self):super().__init__();self.cases=[]
 def addSuccess(self,test):super().addSuccess(test);self.cases.append({'name':test.id(),'status':'PASS'})
 def addFailure(self,test,error):super().addFailure(test,error);self.cases.append({'name':test.id(),'status':'FAIL','reason':str(error[1])})
 def addError(self,test,error):super().addError(test,error);self.cases.append({'name':test.id(),'status':'FAIL','reason':str(error[1])})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('suite',choices=['unit','sdk','integration']);p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=Result();attempts=[]
 def block(*args,**kwargs):attempts.append(1);raise AssertionError('Unexpected offline network')
 suite=unittest.defaultTestLoader.loadTestsFromTestCase({'unit':Unit,'sdk':SDK,'integration':Live}[a.suite])
 if a.suite=='integration':suite.run(result)
 else:
  with patch('socket.socket.connect',block),patch('socket.getaddrinfo',block):suite.run(result)
 value={'suite':a.suite,'planned':result.testsRun,'passed':sum(x['status']=='PASS' for x in result.cases),'failed':len(result.failures)+len(result.errors),'networkAttempts':len(attempts),'cases':result.cases}
 a.output.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in value.items() if k!='cases'}));sys.exit(not result.wasSuccessful())
