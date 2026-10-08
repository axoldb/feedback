# Native AxolDB integer evolution

This is the smallest public, executable native-population example supported by the AxolDB
Developer Preview. It imports three integers from `data/population.json`, creates an exact Fork,
runs one AxolDB Evolution cycle with the built-in reference mutation operator, reads the resulting
Fork membership and native lineage, and proves that the source Population remains unchanged.

The example uses integers instead of knapsack candidates because the packaged Preview exposes one
invocable operator: `EvolutionaryOperator/axol/reference-increment-mutator`. It accepts a scalar
integer and emits that integer plus one. Encoding knapsack crossover or mutation in local Python
would make Python—not AxolDB—the evolutionary engine and would not satisfy this example's purpose.

## What is native here

`run_demo.py` maps the human-readable input file to public `genotype insert` and `population
create` commands. It then uses the local, Application-backed public `axol` CLI to perform the real
plugin trust lifecycle, Fork creation, Evolution Run creation/start, and `evolve step`. The
mutation implementation executes inside `axol` through the Plugin Runtime; the script does not
calculate child values or publish a successor itself.

After the step, a typed public Query scans the current `fork-generation` scope. The script verifies
that the total membership matches the requested target size and every observed child value is one
greater than an input value. `fork lineage` must return non-empty `mutation` records naming the
built-in operator. Finally, it rereads the exact source Generation and checks both membership and
summary against the pre-step reads.

The returned `EvolutionRunId` is not guessed or constructed: `evolve create --output json` returns
it in `data.run`, and the script passes that exact value to `evolve start`, `evolve step`, and
`fork lineage`.

## Current single-package result: `1×1, 4×1, 7×1` to `8×3`

The current retained run used one locally assembled corrective `linux-x64` bundle for every
command. It imported `1×1, 4×1, 7×1`, made three parent-winner requests, invoked the reference
mutator three times, and returned three lineage records for the value-8 genotype hash. Because the
operator contract is exactly `child = parent + 1`, each reconstructable parent value was 7.

The resulting membership has one distinct content hash, `8×3`. This means that three offspring
candidate occurrences refer to the same immutable value-8 genotype content. It means neither
three distinct genotype contents nor eight operations. There were three operations, three
offspring candidate instances and three lineage records, but one distinct genotype/hash and one
membership row whose multiplicity is 3.

The public lineage result still does not expose parent candidate-instance IDs, tournament
participants or draw order. Those details cannot be reconstructed from the saved evidence; only
the three parent values can be inferred from the output and the operator contract.

## Historical two-build result: `1×1, 4×1, 7×1` to `5×1, 8×2`

The step requested target size 3, no elites, tournament size 2, maximize direction, and the
identity evaluator. AxolDB therefore made three parent-winner requests. Each tournament sampled
from the source pool with replacement under the run's fixed root seed; the better sampled integer
won because its own value was the objective. The selected values that can be reconstructed from
the results were `7`, `7`, and `4`. The built-in operator emitted one integer equal to its parent
plus one for each invocation, producing `8`, `8`, and `5`. Input value `1` was not selected.

The three returned mutation lineage records correspond, in returned order, to:

1. output hash `fa3a1e…a01764`, value `8`, hence parent value `7`;
2. output hash `fa3a1e…a01764`, value `8`, hence parent value `7`;
3. output hash `094347…d1564`, value `5`, hence parent value `4`.

This maps parent *values*, not durable parent candidate-instance identities. The retained public
`fork lineage` result does not expose `ParentCandidateInstanceIds`, and the report did not retain
the individual tournament participant draws. Exact parent instance IDs, participant pairs, and
draw order therefore cannot be reconstructed from the saved evidence.

These counts describe different things:

- three mutation invocations produced three offspring candidate instances and three emitted
  genotype results;
- those results contain only two distinct genotype contents/hashes: value `5` and value `8`;
- content-identity membership coalesces equal hashes, so the two distinct membership rows are
  `5×1` and `8×2`, whose multiplicities sum to the logical population size 3;
- `8×2` means two candidate occurrences refer to the same canonical genotype content. It does
  not mean eight operations, two different value-8 genotypes, or one lineage record with a count.

Lineage is deliberately not deduplicated by genotype hash, which is why the two historical value-8
candidate instances still have two separate mutation records even though membership aggregates
them. The original machine reports are retained under `results/history/` and are not the current
single-package qualification result.

## Public capability review

The checked public product contracts, CLI help, documentation and implementation establish:

| Need | Public path in this Preview |
| --- | --- |
| Import candidates | No bulk domain-file importer. This adapter validates JSON and calls public `genotype insert`, then `population create --member` for each candidate/multiplicity. |
| Population identity and membership | `population describe`, `generation inspect`, and ordered `query submit` against an exact base Generation. |
| Native mutation | Local `axol evolve step` with the packaged reference increment mutator after `plugin register/approve/grant-capability/activate`. |
| Evaluation | The CLI's documented identity evaluator evaluates each integer's own logical value; the step uses the requested objective/selection parameters. |
| Result membership | Typed `query submit --input -` with the public `fork-generation` source scope. |
| Native lineage | `fork lineage --run <EvolutionRunId>` returns output genotype hash, operator, candidate generation and lineage kind. |
| `EvolutionRunId` | Created by AxolDB and returned by `evolve create`; it has the canonical `evolution-run-<UUID>` form. |
| Crossover | **BLOCKED.** No packaged public crossover operator, crossover flag on `evolve step`, or external plugin-loading path exists. |
| Remote Evolution | **BLOCKED.** Server v1's 34-capability catalog deliberately omits Evolution execution/reads, plugin lifecycle, fork publication and `Fork.GetLineageForRunAsync`. |

This is therefore a complete native mutation example and an explicit partial result for the wider
“crossover/mutation” request. It does not conceal the missing crossover capability with local code.

## Requirements and run

- Python 3.12 or later; there are no third-party Python packages.
- One AxolDB `axol` executable from a package that contains both structured Fork Query and the
  local genotype-insert canonical-ID correction.
- A fresh, isolated PostgreSQL-backed local AxolDB deployment selected through the documented
  `AXOLDB_CONNECTION_STRING`, `AXOLDB_DEPLOYMENT_AUDIENCE`, and `AXOLDB_CURSOR_SIGNING_KEY`
  variables. The example never writes these values to its report.
- The matching isolated managed instance root, used only for the controlled stop/start/reload
  check.

```bash
export AXOL_BIN=/absolute/path/to/bundle/bin/axol
export AXOLDB_CONNECTION_STRING='Host=127.0.0.1;Port=PORT;Database=axoldb;Username=USER;Password=SECRET;SSL Mode=Disable;Pooling=false'
export AXOLDB_DEPLOYMENT_AUDIENCE='native-example'
export AXOLDB_CURSOR_SIGNING_KEY='64-hex-characters'
python3 run_demo.py --instance-root /absolute/path/to/the/isolated/managed-instance
```

There is no `AXOL_QUERY_BIN`: `AXOL_BIN` performs import, Population/Generation/Fork reads,
structured Fork Query, plugin/Evolution operations, lineage, managed stop/start and every reload
read. The retained evidence used a local corrective build from base commit `88e7d715…` plus the
reviewable one-line genotype-insert handler diff. Its tar.gz SHA-256 is
`1e86fa638b161195a6c7439f3fe2f3b077105ccfccee5c8cd0b4038e42f65198`.

That corrective bundle is **not publicly released**. Do not use the older public/preserved package
for this walkthrough: it still has the local insert bug. Until a reviewed package containing the
correction is published, reproduction requires a locally assembled source-matched bundle.

Use a fresh database or override `--population` and `--fork-segment`; public v1 has no Population
delete operation. The example bootstraps its synthetic administrator and grants only the scopes it
uses. It does not stop or delete an instance it did not create.

The run writes sanitized `results/run-report.json` and `results/reload-report.json` files containing
AxolDB identities, memberships, lineage, safe commands and assertions. It retains no connection
string, password, signing key or private instance material. The script itself performs a controlled
`server stop`, `server start`, `server status`, then repeats exact source/Fork/lineage reads before
returning success.

## Verify the example code

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile run_demo.py tests/test_run_demo.py
```

The retained real-run evidence is summarized in `RUN-REPORT.md` and recorded in
`results/run-report.json`. Fresh runs create different database/run identities. No deterministic
output guarantee is claimed.

## Scope and possible uses

**Demonstrated:** one-package import of a small human-readable integer population; authoritative
source reads; one genuine native mutation cycle; structured successor membership Query; native
mutation lineage; controlled managed restart; and source/Fork/lineage reload equality.

**Not demonstrated:** crossover. The used public path has no packaged crossover implementation or
CLI option. The current run qualifies one local corrective bundle, not any publicly distributed
release. The older two-build result remains historical evidence only. The DEAP/Mesa manifest
provenance in the sibling examples is application data and is not AxolDB native Evolution lineage.

**Potential uses:** this small pattern can serve as a starting point for understanding AxolDB Fork,
Evolution Run, operator governance and lineage semantics before a future public custom-operator or
crossover surface exists. It is not a performance, scalability, optimization-quality, production,
or collaboration demonstration. For a one-off integer transformation, a local file or short script
would be simpler.

The example code and documentation are available under the [MIT license](LICENSE). AxolDB and
Python retain their separate terms; see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
