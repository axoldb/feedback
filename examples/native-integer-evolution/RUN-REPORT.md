# Native integer evolution qualification — 2026-10-08

## Result

**PASS for the implemented native mutation workflow and restart/reload checks. PARTIALLY BLOCKED
for one-package reproduction and crossover.**

The real run imported integer membership `1×1, 4×1, 7×1`, created Fork
`axol://forks/examples.native-integer/candidates/native-run`, obtained Evolution Run
`evolution-run-56bb5067-ba1a-48d1-a75b-c376634fd316` from `evolve create`, and published Fork
Generation `72da408f-114b-4ea9-bc0d-9aec2f951639`.

The resulting authoritative Fork membership was `5×1, 8×2`. Three native lineage records name
`axol://operators/axol/reference-increment-mutator` and kind `mutation`; two records share the
genotype hash for value 8 because candidate instances remain distinct in lineage while
content-identity membership records multiplicity 2. Every result value is a selected input value
plus one, matching the public built-in operator contract.

More precisely, the step used target size 3, elite count 0, tournament size 2, maximize direction,
the identity evaluator and the recorded root seed. It requested three tournament winners; each
tournament sampled with replacement. From the saved outputs and the operator's exact `parent + 1`
contract, the selected parent values were `7`, `7`, and `4`, producing `8`, `8`, and `5`. The
returned lineage order maps as follows:

| Lineage record | Output hash | Output value | Reconstructable parent |
| --- | --- | ---: | ---: |
| 1 | `fa3a1e…a01764` | 8 | value 7 |
| 2 | `fa3a1e…a01764` | 8 | value 7 |
| 3 | `094347…d1564` | 5 | value 4 |

Only parent values are reconstructable. The retained public lineage rendering contains no parent
candidate-instance IDs, and the report did not preserve tournament participants or draws. It is
therefore not possible to recover the exact parent instance references, each two-participant
tournament, or draw ordering from this evidence.

There were three mutation operator invocations, three offspring candidate instances, and three
emitted genotype results, but only two distinct genotype contents/hashes. Content-identity
membership aggregates equal hashes into two rows: `5×1` and `8×2`; the multiplicities sum to
logical population size 3. Thus `8×2` means two candidate occurrences reference the same
canonical value-8 genotype. It is not an operation count, not two different value-8 genotypes, and
does not collapse the two corresponding lineage events.

The source Population remained at Generation 0. Its exact Generation summary and membership were
unchanged before/after the step. After a controlled managed stop/start, the source membership,
result membership, Fork head and all three lineage records were read again and matched.

Machine-readable evidence is in `results/run-report.json` and `results/reload-report.json`.

## Environment

- Fedora Linux 44, x86-64; Python 3.14.7.
- PostgreSQL 16.15 from the existing self-contained native bundle.
- Native import/plugin/Fork/Evolution CLI:
  `0.1.0-developer-preview+8299e9d0a7bd52c8c1acab1f2fdb5a4f18e94f80`.
- Typed source/Fork Query CLI:
  `0.1.0-developer-preview+88e7d71571c0b04641d46b7f699dbab84fe463a3`.
- Public execution boundary: local Application-backed `axol` CLI only; no direct PostgreSQL read or
  write, no product edit, and no local mutation/crossover implementation.

The example process took 33.23 seconds. That is run scope, not a performance claim.

## Exact blockers

1. The preserved qualified `+8299e9d…` bundle has the real native Evolution/plugin surface but
   predates structured `query --input`; it cannot submit a `fork-generation` scan.
2. The available `+88e7d…` CLI has typed Fork Query, but its local flag-based `genotype insert`
   path converts the already-canonical request Population a second time. The observed authorization
   target was `axol://populations/axol%3A/%2Fpopulations%2Fexamples.native-integer%2Fcandidates`,
   so the valid grant for `axol://populations/examples.native-integer/candidates` did not match.
3. No public packaged crossover operator, crossover option on `evolve step`, or external plugin
   loading mechanism exists. Server v1 also deliberately omits remote Evolution and plugin
   lifecycle operations.

For evidence only, the retained run used `AXOL_QUERY_BIN` to combine those two storage-compatible
public CLI builds: all mutation and publication occurred through the qualified Evolution build;
the later build performed read-only typed Queries. The example defaults both variables to the same
executable for a future compatible package. No claim is made that a currently preserved single
package completes the whole script.

This remains a native-mutation-only result. Crossover was neither available nor demonstrated in
the used public path. It is also not qualification of a single distributive package because two
different CLI builds were necessary. The provenance manifests retained by the separate DEAP and
Mesa integrations are application-level records, not native AxolDB Evolution lineage.

## Safety and cleanup

The run and reload reports contain no connection string, password, cursor-signing key, CA private
key, instance archive or unrestricted log. The task-owned managed Server was stopped after the run
and again after the restart check. No workflow, release, tag, deployment, product commit or push was
performed.
