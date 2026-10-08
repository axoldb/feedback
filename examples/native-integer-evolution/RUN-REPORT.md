# Native integer evolution qualification — 2026-10-08

## Result

**PASS for the single-package native mutation walkthrough and controlled restart/reload. Crossover
remains BLOCKED and was not demonstrated.**

One locally assembled `linux-x64` bundle performed every public operation: import, source
Population/Generation reads, Fork creation/inspection, plugin lifecycle, Evolution create/start/step,
structured Fork Query, lineage, managed stop/start/status and all reload reads. `AXOL_QUERY_BIN` was
not set or used.

The run imported `1×1, 4×1, 7×1`, created Fork
`axol://forks/examples.native-integer/candidates/native-run`, obtained Evolution Run
`evolution-run-07e86ea8-a9fb-4f4b-b159-df5bb468e03f` from `evolve create`, and published Fork
Generation `4f333d31-acff-46f8-a561-09a9ed37c55a`.

The authoritative result membership was `8×3`. Three mutation lineage records name
`axol://operators/axol/reference-increment-mutator`, all with output hash
`fa3a1e7d…e6a01764` and lineage kind `mutation`. The step used target size 3, elite count 0,
tournament size 2, maximize direction, the identity evaluator and the recorded root seed. From the
saved outputs and the operator's exact `parent + 1` contract, all three reconstructable parent
values were 7.

Only parent values are reconstructable. The public lineage rendering does not expose parent
candidate-instance IDs, and the report does not retain tournament participant pairs or draw order.
Those details therefore cannot be recovered from this evidence.

These counts are distinct:

- three mutation invocations produced three offspring candidate instances and three lineage rows;
- all three emitted the same immutable value-8 genotype content/hash;
- content-identity membership coalesced that hash into one `8×3` row;
- the multiplicity 3 is the number of logical member occurrences, not an operation count or three
  different genotypes.

The source Population stayed at Generation 0 with exact membership `1×1, 4×1, 7×1`. After the same
`AXOL_BIN` performed a controlled managed stop/start, the source membership and summary, result
membership, Fork head and all three lineage records matched their pre-restart values. A final
task-owned stop also succeeded.

Machine-readable evidence is in `results/run-report.json` and `results/reload-report.json`.

## Bundle provenance

| Field | Retained value |
| --- | --- |
| Product base commit | `88e7d71571c0b04641d46b7f699dbab84fe463a3` |
| Product source diff | one local handler substitution: `PopulationCommand.ParsePopulationId(request.TargetPopulationId)` → `PopulationId.Parse(request.TargetPopulationId)` |
| Executable source-diff SHA-256 | `19f3aa9f1a18c82e34579e6a657ae487fd0f16a4be4d6fea45427321b244e6f7` |
| CLI version string | `0.1.0-developer-preview+88e7d71571c0b04641d46b7f699dbab84fe463a3` |
| RID | `linux-x64` |
| PostgreSQL | 16.15; 1,865/1,865 runtime-manifest files verified before repackaging |
| Repacked PostgreSQL input SHA-256 | `94429282232dc5c5bcc55ae40e35743796121d65dd73ed1ffc6daef706024d40` |
| Globalization | exact app-local ICU 74.2 / Unicode 15.1 closure verified |
| Bundle manifest | 1,953 entries, all verified |
| Bundle-manifest file SHA-256 | `88eb45f01734d67106305c3ece5794027448ba1393746cf7008afb9d76d1c329` |
| Local tar.gz SHA-256 | `1e86fa638b161195a6c7439f3fe2f3b077105ccfccee5c8cd0b4038e42f65198` |
| Availability | local corrective artifact only; not a public release package |

The bundle was assembled before the correction was committed, so its version string identifies the
base commit. The later source commit does not retroactively turn this into a build of that commit:
the base commit plus executable source-diff digest and archive checksum uniquely bind the tested
local artifact. This is not overall release qualification and does not close WP-0094.

## Environment and executable checks

- Fedora Linux 44, x86-64; Python 3.14.7.
- Public execution boundary: local Application-backed `axol` CLI plus its public managed Server
  lifecycle commands; no direct PostgreSQL read/write and no local mutation implementation.
- Example helper tests: 3 passed, 0 failed, 0 skipped.
- Example duration: 47.89 seconds; this is run scope, not a performance claim.
- Sanitized reports retain no connection string, password, cursor-signing key, private key or
  private instance path.

## Historical two-build evidence

The prior run is preserved under `results/history/`. It used the `+8299e9d…` Evolution build and
the `+88e7d…` Query build and produced `5×1, 8×2`. In that historical result, the three output
lineage rows map by the exact `parent + 1` operator contract to parent values 7, 7 and 4. Two value-8
candidate occurrences shared one canonical genotype hash, hence membership `8×2`, while the value-5
content had multiplicity 1. Exact parent candidate IDs and tournament draws were not retained.

That evidence remains valid for what it observed, but it is not the current standard flow and does
not qualify one package.

The two runs used the same input values and genotype hashes (`1`, `4`, `7`, each multiplicity 1),
root seed, evaluation-context hash, plan ID, step/candidate-generation coordinates, target size,
elite count, tournament size, maximize direction, identity evaluator, mutation operator identity,
version and package hash, and the CLI defaults for duplicate/failure/checkpoint policy. Their
persisted source Generation IDs, Fork Generation IDs and Evolution Run IDs differ; the historical
Evolution executable was also `+8299e9d…`, whereas the current single-package run used the local
`+88e7d…` base-plus-diff bundle.

The Evolution Run ID is an explicit coordinate in tournament RNG derivation, so the differing run
IDs are sufficient to produce different participant draws even with the same root seed and visible
selection parameters. Candidate-instance IDs also include the run ID. The saved public evidence
does not contain participant pairs, draw order, parent candidate-instance IDs, or a separately
rendered execution profile, so a full decision-by-decision replay comparison is impossible. The
historical `5×1, 8×2` and current `8×3` results are therefore compatible outcomes of two different
RNG coordinate sets, not evidence of a regression or a claim of deterministic replay.

## Remaining blockers and boundaries

1. No public built-in crossover operator, crossover option on `evolve step`, or external plugin
   loading mechanism exists. Crossover remains unavailable and untested.
2. The verified single-package result is a local corrective bundle, not a public release. The older
   package with the double-parse bug must not be used for this walkthrough.
3. Server v1 still deliberately omits remote Evolution and plugin lifecycle operations; remote
   lifecycle work is outside this example.
4. DEAP/Mesa manifest provenance is application-level provenance, not native AxolDB Evolution
   lineage. Those examples and their campaigns were not changed or rerun.

## Safety and cleanup

The run and reload reports contain no connection string, password, signing key, CA private key,
instance archive or unrestricted log. The task-owned managed Server was stopped after the reload
check. No workflow, commit, push, merge, tag, public release, upload, deployment or website change
was performed.
