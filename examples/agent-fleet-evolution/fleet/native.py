"""Separate typed native fixture. Existing owner-approved trust is required, never self-granted."""
import base64,hashlib,json
from pathlib import Path
from uuid import UUID
from .config import connect,wire,name
from .model import require,digest
from .demo import save

def run(config,run_id,output):
 import axoldb as sdk
 from axoldb.contracts import parity as v2
 from . import codec
 from .storage import identity,authoring,scan_hashes
 require(output is not None,'Explicit private --output required')
 name(run_id)
 output=Path(output);guard=output.with_suffix('.reservation.json')
 require(not output.exists() and not guard.exists(),'Native one-shot fixture already reserved; inspect receipts, never retry implicitly')
 save(guard,{'format':'native-public-fixture/1','run':run_id,'state':'reserved; uncertain outcomes require operator review'})
 results=[]
 with connect(config,'native') as client:
  bindings={x.operator_id.split('/')[-1]:x for x in client.parity.capabilities_get().evolution_bindings}
  for kind,label,operator,evaluator,values,size in [
   ('integer','mutation','reference-increment-mutator','identity-integer-evaluator',[(sdk.Ace1Integer(value=sdk.CanonicalInteger(text='7')),2)],2),
   ('binary','crossover','reference-binary-midpoint-crossover','unsigned-big-endian-binary-evaluator',[(sdk.Ace1Binary(hex=bytes.fromhex(x)),1) for x in ['00010203','a0a1a2a3']],1)]:
   pop='axol://populations/public-fleet/'+run_id+'-native-'+kind;fork='axol://forks/public-fleet/'+run_id+'-native-'+kind+'/reference'
   require(client.populations.try_get_current_generation(sdk.PopulationGetRequest(population_id=pop)) is None,'Fresh native namespace required')
   binding=bindings[operator];client.parity.plugin_get(v2.PluginRef(plugin_id=binding.operator_id,package_hash_hex=binding.package_hash_hex))
   schema_id='axol://schemas/public-fleet/'+kind+'/1';schema=codec.schema_document(schema_id,kind);schema_hash=codec.schema_hash(schema_id,schema);members={}
   for value,count in values:
    key=codec.genotype_hash(schema_id,schema_hash,b'ACE1\0'+codec.nested(value));members[key]=str(count)
    inserted=client.parity.genotype_insert_v2(v2.GenotypeInsertV2Request(request=identity(pop,'native/genotype/'+key),payload=sdk.GenotypeInsertRequest(target_population_id=pop,genotype=sdk.Genotype(schema_id=schema_id,schema_hash_hex=schema_hash,value=value))))
    require(inserted.genotype_hash_hex==key,'Independent typed Genotype hash')
   content=v2.AuthoringContent(identity_mode='content',content_members=tuple(v2.ContentMember(genotype_hash_hex=k,multiplicity=v) for k,v in sorted(members.items())),generated_new=(),generated_retained=(),keyed_new=(),keyed_retained=())
   policy=v2.AuthoringPolicy(identity_mode='content',contract_id='axol://contracts/public-fleet/'+kind+'/1',contract_hash_hex=hashlib.sha256(schema).hexdigest(),canonical_schema_base64=base64.b64encode(schema).decode(),write_profile='content-counts',key_paths=(),lineage_profile='direct',lineage_minimum_duration_ticks='864000000000',forks_enabled=True)
   created=client.parity.population_create_v2(v2.PopulationCreateV2Request(request=identity(pop,'native/create'),population_id=pop,contract=policy,initial_generation=content))
   client.forks.create(sdk.ForkCreateRequest(fork_id=fork,source_population_id=pop,source_generation_id=UUID(created.generation_id)))
   birth=client.forks.try_get(sdk.ForkGetRequest(fork_id=fork));require(birth is not None,'Fork birth')
   profile=v2.ExecutionProfile(variation_kind=label,variation=binding,evaluator=bindings[evaluator],target_population_size=size,elite_count=0,tournament_size=1,objective_direction='Maximize',duplicate_policy='preserve-candidates',maximum_generations='1',checkpoint_frequency='1',mutation_maximum_attempts=1,mutation_failure_policy='reject-offspring',budget=v2.Budget(maximum_members=10000,maximum_genotype_bytes=1048576,maximum_logical_bytes=67108864,maximum_wall_milliseconds=30000,maximum_variation_attempts=32))
   request=v2.CreateRunRequest(request=identity(pop,'native/run'),fork_id=fork,expected_fork_generation_id=str(birth.current_fork_generation_id),root_seed_hex=('1' if kind=='integer' else 'd')*64,evaluation_context_hash_hex='0'*64,profile=profile)
   state=client.parity.evolution_create_run(request);require(state.status=='ready','Ready native Run')
   attempt=client.parity.evolution_start_or_resume(v2.StartAttemptRequest(request=identity(pop,'native/start'),run_id=state.run_id,expected_run_revision=state.revision,resume=False))
   state=client.parity.evolution_get_run(v2.RunRef(run_id=state.run_id))
   step=client.parity.evolution_execute_step(v2.StepRequest(request=identity(pop,'native/step'),run_id=state.run_id,expected_run_revision=state.revision,expected_attempt_id=attempt.attempt_id,expected_lease_epoch=attempt.lease_epoch,expected_parent_fork_generation_id=str(birth.current_fork_generation_id),evolution_step='0',candidate_generation='0'))
   require(step.outcome=='committed' and step.member_count==size,'Governed native publication')
   state=client.parity.evolution_get_run(v2.RunRef(run_id=state.run_id))
   terminal=client.parity.evolution_complete(v2.TerminalRequest(control=v2.RunControlRequest(request=identity(pop,'native/complete'),run_id=state.run_id,expected_run_revision=state.revision,expected_attempt_id=attempt.attempt_id,expected_lease_epoch=attempt.lease_epoch),expected_publication_operation_id=step.operation_id,reason='maximum-generations'))
   require(terminal.status=='completed','Completed native Run')
   lineage=client.parity.lineage_get_for_run(v2.LineageRef(run_id=state.run_id,page_size=10));require(lineage.cursor is None and len(lineage.events)==size,'Persisted producing lineage')
   receipt=client.parity.operation_resolve(v2.OperationIdLookup(operation_id=step.operation_id));require(receipt.outcome=='committed','Native receipt')
   results.append(dict(population=pop,fork=fork,runId=state.run_id,source=created.generation_id,birth=str(birth.current_fork_generation_id),published=step.fork_generation_id,receipt=wire(step),lineage=wire(lineage)))
 return {'format':'native-public-fixture/1','results':results,'crashRecoveryQualified':False}

def verify(config,record):
 import axoldb as sdk
 from axoldb.contracts import parity as v2
 from .storage import scan_hashes
 with connect(config,'native') as client:
  for fixture in record['results']:
   fork=client.forks.try_get(sdk.ForkGetRequest(fork_id=fixture['fork']));require(str(fork.current_fork_generation_id)==fixture['published'],'Persisted Fork head')
   lineage=client.parity.lineage_get_for_run(v2.LineageRef(run_id=fixture['runId'],page_size=10));require(wire(lineage)==fixture['lineage'],'Exact lineage readback')
   from .storage import query
   def values(generation):
    source=sdk.SourceForkGeneration(fork_id=fixture['fork'],fork_generation_id=generation,fork_generation_number=None)
    return {row.row.envelope.genotype_hash_hex.hex():next(f.value.value for f in row.row.fields if f.name=='value') for row in query(client,sdk.OperatorScan(source_alias='fixture',source_scope=source))}
   before,after=values(fixture['birth']),values(fixture['published'])
   for event in lineage.events:
    require(event.output_genotype_hash_hex in after,'Output membership')
    require(event.lineage_kind in ('mutation','crossover') and event.completeness=='complete-v2','Native lineage kind')
    parents=[before[p.genotype_hash_hex] for p in event.parents];child=after[event.output_genotype_hash_hex]
    if event.lineage_kind=='mutation':require(len(parents)==1 and int(parents[0].value.text)==7 and int(child.value.text)==8,'Native integer increment readback')
    else:require(len(parents)==2 and child.hex==parents[0].hex[:2]+parents[1].hex[2:],'Native midpoint against actual ordered parents')
 return {'exact':True,'fixtures':len(record['results']),'modelCalls':0,'nativeCrashRecoveryQualified':False}
