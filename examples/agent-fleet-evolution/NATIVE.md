# Separate native Evolution fixture

This optional fixture is distinct from FleetPlan mutation/crossover. It uses public axoldb-client 0.1.2.dev1 parity operations, trusted installed integer/binary bindings, governed Fork publication and actual native lineage.

An instance owner must prepare two fresh resource pairs and a separate native principal. The fixture reads existing plugin metadata; it never registers, approves, activates or grants capabilities to a plugin and never installs executable code. Refuse if trust or permissions are absent. Do not substitute an owner token for the application credential.

For run my-first-run, the resource pairs are:

- axol://populations/public-fleet/my-first-run-native-integer and axol://forks/public-fleet/my-first-run-native-integer/reference
- axol://populations/public-fleet/my-first-run-native-binary and axol://forks/public-fleet/my-first-run-native-binary/reference

The native principal requires, for each pair: Insert/Read/Export/PublishGeneration/CreateFork on that Population; Insert/Read on IndividualGenotype scoped to that Population; Read/Insert/PublishGeneration on its Fork; and Read on MaterializationProvenanceLineage scoped to that Population. The qualified metadata access also uses ExecuteQuery(Query, query), Read(PopulationContractSchema), and Read(PluginRegistrationCapability) on each exact operator/package identity. The latter resource key is the operator ID, a literal newline, then the package hash. A backslash followed by n is not the same identity. Inspect the official contracts and owner trust setup; no administrative mutation permission belongs on the native app principal.

Supply the separate native token at hidden input:

~~~sh
python private_run.py /private/config.json native native --run my-first-run --output /private/native.json
python private_run.py /private/config.json native native-read --recorded /private/native.json --output /private/native-read.json
~~~

The first command creates typed source Populations and Forks, inserts integer 7 with multiplicity two and two four-byte binary parents, creates/starts/steps/completes one governed Run per fixture, verifies publication receipts and records lineage. The second command starts a fresh process and verifies the persisted Fork heads, exact lineage, integer 7 → 8 and binary midpoint against the actual ordered parents. Native selection coordinates include Run identity; fixed root seed alone does not guarantee identical selected parents across newly created Runs. A midpoint can legitimately equal a parent if selection supplies equal values. The verifier checks the actual operation rather than inventing distinct parents.

A one-shot reservation prevents duplicate execution. On failure preserve it and resolve the original operation/committed effects with supported interfaces; never delete it and rerun automatically. This fixture does not qualify native interrupted-run, power-loss or crash recovery. It does not advance the FleetPlan reference Fork or optimize arbitrary JSON.
