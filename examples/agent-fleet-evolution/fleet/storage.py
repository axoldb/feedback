"""Public AxolDB storage adapter for an immutable two-generation run."""
import importlib.util
import json
from uuid import NAMESPACE_URL, UUID, uuid5

import axoldb as sdk
from axoldb.contracts import parity as v2

from .model import Scenario, canonical, digest, generation_records, record_id, require, verify_records
from .config import HERE, load, name, wire

from . import codec as CODEC
STORAGE = load(HERE/"storage-contract.json")
CODEC.self_test()



def identity(publication, suffix):
    key = uuid5(NAMESPACE_URL,f"{publication}#gate02-v1/{suffix}")
    return v2.RequestIdentity(request_id=str(key),idempotency_key=key.hex)


def checkpoint(pop, fork, number, parent, previous, docs):
    committed_id = identity(pop,f"publish/{number}")
    entries = [{"id":record_id(doc), "sha256":digest(doc),
                "genotype":CODEC.genotype(doc).genotype_hash_hex}
               for doc in sorted(docs,key=record_id)]
    return {"record_type":"Checkpoint","schema_version":1,"protocol":"atomic-membership-v1",
            "checkpoint_id":f"{pop}/checkpoint/{number}","ordinal":number,"population":pop,
            "fork":fork,"expected_parent":parent,"previous_checkpoint_sha256":previous,
            "request_id":committed_id.request_id,"idempotency_key":committed_id.idempotency_key,
            "payloads":entries}


def verify_checkpoint(value, pop, fork, number, parent, previous, docs):
    require(canonical(value) == canonical(checkpoint(pop,fork,number,parent,previous,docs)),
            "checkpoint manifest, request identity, or predecessor is inconsistent")


def query(client, root):
    doc = sdk.CanonicalQueryDocument(declared_parameters=(),root=root)
    page = client.queries.execute(sdk.QueryExecuteRequest(document=doc,parameter_values=(),page_size=16))
    require(page.cursor is None,"unexpected paging in bounded fixture")
    return page.relation.rows


def scan_hashes(client, source):
    output = {}
    for row in query(client,sdk.OperatorScan(source_alias="member",source_scope=source)):
        require(row.row.envelope is not None and row.row.envelope.genotype_hash_hex is not None,
                "missing native membership envelope")
        key = row.row.envelope.genotype_hash_hex.hex()
        require(key not in output,"duplicate membership row")
        output[key] = int(row.multiplicity.text)
    return output


def authoring(members):
    return v2.AuthoringContent(identity_mode="content",
        content_members=tuple(v2.ContentMember(genotype_hash_hex=key,multiplicity="1") for key in sorted(members)),
        generated_new=(),generated_retained=(),keyed_new=(),keyed_retained=())


class Store:
    def __init__(self, client, run, *, verify_receipts=True):
        self.client = client
        self.p = client.parity
        self.pop,self.fork = name(run)
        self.verify_receipts = verify_receipts

    def head(self):
        return self.client.populations.try_get_current_generation(sdk.PopulationGetRequest(population_id=self.pop))

    def exact(self, generation):
        return self.client.populations.try_get_generation(sdk.PopulationGetGenerationRequest(
            population_id=self.pop,generation_id=UUID(generation)))

    def resolution(self, resolver, *, missing=False):
        try:
            receipt = self.p.operation_resolve(resolver)
        except sdk.AxolDbClientError as error:
            if missing and error.http_status in (403,404) and error.canonical_code == "AXOL-PARITY-UNAVAILABLE-OR-DENIED":
                return None
            raise
        require(receipt.outcome == "committed",f"operation resolution requires operator review ({receipt.outcome})")
        return receipt

    def ensure_effect(self, request, resolver, send):
        # The original identity and payload are deterministic. An unresolved/indeterminate
        # operation refuses. A positively absent receipt permits the same exact request.
        lookup = resolver(original_request=request)
        known = self.resolution(lookup,missing=True)
        if known is not None:
            return known
        send(request)
        return self.resolution(lookup)

    def publish_request(self, number, parent, members):
        if number == 0:
            contract = v2.AuthoringPolicy(identity_mode="content",
                contract_id="axol://contracts/fleet-gate02/canonical-json/2",
                contract_hash_hex=digest({"format":"fleet-gate02/v2","storage":STORAGE}),
                canonical_schema_base64=STORAGE["canonicalSchemaBase64"],
                write_profile=STORAGE["writeProfile"],key_paths=(),
                lineage_profile=STORAGE["lineageProfile"],
                lineage_minimum_duration_ticks=str(STORAGE["lineageMinimumDurationTicks"]),
                forks_enabled=True)
            return (v2.PopulationCreateV2Request(request=identity(self.pop,"publish/0"),
                population_id=self.pop,contract=contract,initial_generation=authoring(members)),
                v2.ResolvePopulationCreateV2,self.p.population_create_v2)
        return (v2.TransactionV2Request(request=identity(self.pop,"publish/1"),operations=(
            v2.PopulationOperationV2(population_id=self.pop,expected_parent_generation_id=parent,
                                    content=authoring(members)),),
            isolation_level="serializable",durability_level="synchronous"),
            v2.ResolveTransactionSubmitV2,self.p.transaction_submit_v2)

    def publish(self, scenario, number, parent=None, old=None):
        docs = generation_records(scenario,number,old["payloads"] if old else ())
        check = checkpoint(self.pop,self.fork,number,parent,digest(old["checkpoint"]) if old else None,docs)
        members = {}
        for doc in (*docs,check):
            value = CODEC.genotype(doc)
            key = value.genotype_hash_hex
            require(key not in members,"duplicate Genotype in checkpoint")
            request = v2.GenotypeInsertV2Request(request=identity(self.pop,f"genotype/{key}"),
                payload=sdk.GenotypeInsertRequest(target_population_id=self.pop,genotype=value))
            receipt = self.ensure_effect(request,v2.ResolveGenotypeInsertV2,self.p.genotype_insert_v2)
            require(receipt.genotype is not None and receipt.genotype.genotype_hash_hex == key
                    and receipt.genotype.schema_hash_hex == STORAGE["schemaHash"],"invalid staged insert receipt")
            members[key] = doc
        request,resolver,send = self.publish_request(number,parent,members)
        self.ensure_effect(request,resolver,send)
        head = self.head()
        require(head is not None and head.generation_number == number,"publication failed to advance to exact head")
        return self.read_generation(head,old)

    def read_generation(self, summary, old=None):
        number = summary.generation_number
        require(number in (0,1) and (number == 0) == (old is None),"unexpected generation ordinal")
        parent = old["generation"]["generation_id"] if old else None
        require(tuple(map(str,summary.parent_generation_ids)) == ((parent,) if old else ()),
                "native parent link mismatch")
        hashes = scan_hashes(self.client,sdk.SourceExactBaseGeneration(population_resource_id=self.pop,
                            generation_id=summary.generation_id,generation_number=None))
        require(summary.member_count == len(hashes) == 6 and set(hashes.values()) == {1},
                "membership must contain six distinct payloads at multiplicity one")
        records = []
        for key in sorted(hashes):
            result = self.client.genotypes.try_get(sdk.GenotypeGetRequest(population_id=self.pop,
                generation_id=summary.generation_id,genotype_hash_hex=key))
            require(result is not None and isinstance(result.value,sdk.Ace1Binary)
                    and result.schema_id == STORAGE["schemaId"] and result.schema_hash_hex == STORAGE["schemaHash"],
                    "missing base member or wrong native schema")
            raw = result.value.hex
            record = json.loads(raw)
            require(canonical(record) == raw and CODEC.genotype(record).genotype_hash_hex == key,
                    "noncanonical payload or Genotype hash mismatch")
            records.append(record)
        checks = [r for r in records if r["record_type"] == "Checkpoint"]
        scenarios = [r for r in records if r["record_type"] == "Scenario"]
        require(len(checks) == len(scenarios) == 1,"expected immutable scenario and checkpoint")
        docs = [r for r in records if r["record_type"] != "Checkpoint"]
        scenario = Scenario.load(scenarios[0]["scenario"])
        if old:
            require(scenario.record() in old["payloads"],"scenario or agent configuration changed")
        docs = verify_records(scenario,number,docs,old["payloads"] if old else ())
        verify_checkpoint(checks[0],self.pop,self.fork,number,parent,digest(old["checkpoint"]) if old else None,docs)
        if not self.verify_receipts:
            # A viewer verifies authoritative committed Generation membership and payloads.
            # Cross-actor operation receipts require separate audit authority; never add it
            # merely to render a dashboard. The writer verifies its own receipt below.
            return {"generation":wire(summary),"membership":hashes,"payloads":docs,
                    "checkpoint":checks[0],"checkpoint_sha256":digest(checks[0]),
                    "operation_id":None,"receipt_verified":False,"committed":True}
        request,resolver,_ = self.publish_request(number,parent,hashes)
        receipt = self.resolution(resolver(original_request=request))
        if number == 0:
            actual = receipt.population
            require(actual is not None and actual.population_id == self.pop
                    and actual.generation_id == str(summary.generation_id)
                    and actual.state_root_hex == summary.state_root_hex
                    and actual.commit_id == str(summary.created_commit_id)
                    and int(actual.commit_sequence) == summary.created_commit_sequence,
                    "initial authoring receipt does not attest this Generation")
        else:
            require(receipt.transaction is not None,"missing transaction receipt")
            actual = receipt.transaction.result
            require(actual.outcome == "committed" and actual.result_generations[self.pop] == summary.generation_id
                    and actual.commit_id == summary.created_commit_id and actual.commit_sequence == summary.created_commit_sequence,
                    "transaction receipt does not attest this Generation")
        return {"generation":wire(summary),"membership":hashes,"payloads":docs,
                "checkpoint":checks[0],"checkpoint_sha256":digest(checks[0]),
                "operation_id":receipt.operation_id,"committed":True}

    def read_run(self):
        head = self.head()
        if head is None:
            return []
        require(head.generation_number in (0,1),"unexpected third population generation")
        if head.generation_number == 0:
            result = [self.read_generation(head)]
        else:
            require(len(head.parent_generation_ids) == 1,"missing unique predecessor")
            first = self.exact(str(head.parent_generation_ids[0]))
            require(first is not None and first.generation_number == 0,"missing initial Generation")
            initial = self.read_generation(first)
            result = [initial,self.read_generation(head,initial)]
        history = query(self.client,sdk.OperatorGenerationHistory(population_resource_id=self.pop,
                        from_generation_number=None,to_generation_number=None))
        require(len(history) == len(result),"Generation history row count differs from exact parent chain")
        return result

    def reference_fork(self, initial, *, create=False):
        source = initial["generation"]["generation_id"]
        request = sdk.ForkGetRequest(fork_id=self.fork)
        fork = self.client.forks.try_get(request)
        if fork is None and create:
            try:
                self.client.forks.create(sdk.ForkCreateRequest(fork_id=self.fork,
                    source_population_id=self.pop,source_generation_id=UUID(source)))
            except sdk.AxolDbClientError:
                # Preserve an uncertain write. Only a matching public birth witness can resolve it.
                if self.client.forks.try_get(request) is None:
                    raise
            fork = self.client.forks.try_get(request)
        require(fork is not None and fork.source_population_id == self.pop
                and fork.current_fork_generation_number == 0,"missing or advanced reference Fork")
        history = self.client.forks.get_history(request)
        require(len(history) == 1 and str(history[0].source_base_generation_id) == source
                and history[0].id == fork.current_fork_generation_id and history[0].member_count == 6,
                "Fork birth is not a copy of Generation 0")
        birth = scan_hashes(self.client,sdk.SourceForkGeneration(fork_id=self.fork,
                            fork_generation_id=str(fork.current_fork_generation_id),fork_generation_number=None))
        require(birth == initial["membership"],"Fork birth membership differs from Generation 0")
        return {"fork":wire(fork),"birth":wire(history[0]),"membership":birth}
