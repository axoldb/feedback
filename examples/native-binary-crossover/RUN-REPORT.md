# Native binary midpoint crossover qualification — 2026-10-08

## Result

**PASS for one local single-package crossover, complete lineage v2, and controlled restart/reload.**

One `linux-x64` bundle and one `AXOL_BIN` performed every operation. The run imported
`00010203×1` and `a0a1a2a3×1`, preserved that source Generation, used two bounded tournaments, and
published one child. Persisted lineage—not input order—shows:

| Role | Candidate-instance ID | Genotype hash | Bytes |
| --- | --- | --- | --- |
| A / prefix | `2d7372fa…fb94ac9` | `bd38f34c…adf3e06` | `00010203` |
| B / suffix | `b5e78bb9…bd48d7e` | `e71566cc…a00746c` | `a0a1a2a3` |
| child | `b0ee6573…446daa5` | `2bb7bb2f…f758a2` | `0001a2a3` |

The cut is `floor(4 / 2) = 2` bytes, so the operator emitted A's `0001` prefix plus B's `a2a3`
suffix. Result membership is `0001a2a3×1`. The lineage record has format version 2, operator
`axol://operators/axol/reference-binary-midpoint-crossover` version `1.0.0`, package hash
`f6c9ff8c74a4454b5fac2c925d3b3a7993cb51ce9dcd4476c521350c5618f137`, publication operation,
derived seed, output ordinal 0, and ordered `parent-a`/`parent-b` references.

Evolution Run `evolution-run-6b611133-bd1a-4346-a894-7ebc55473942` published Fork Generation
`e648696e-bd9f-6f5f-806e-0142f84b5b91`. After a managed stop/start, source membership, result
membership, Fork head, and the full lineage projection were byte-for-byte equal to the pre-restart
reads. The final task-owned stop passed. Machine evidence is under `results/`.

## Bundle provenance

| Field | Value |
| --- | --- |
| Product source commit | `aea2edf8527114c49168bd71eeeabb47ee0445cd` |
| Branch | `codex/wp0096-binary-midpoint-crossover` |
| CLI version | `0.1.0-developer-preview+aea2edf8527114c49168bd71eeeabb47ee0445cd` |
| RID | `linux-x64` |
| Build tools | .NET SDK `10.0.400`; Node `22.23.1`; npm `12.0.2`; Vite `8.2.2` |
| Runtime closure | .NET/ASP.NET Core `10.0.11`; PostgreSQL `16.15`; app-local ICU `74.2`, Unicode `15.1` |
| PostgreSQL input archive SHA-256 | `94429282232dc5c5bcc55ae40e35743796121d65dd73ed1ffc6daef706024d40` |
| Bundle manifest | 1,953/1,953 entries PASS |
| Bundle-manifest file SHA-256 | `d3c62049506569ce0f93296aee03143500f05758a731ed360a0bdd46fb4aee33` |
| CLI executable SHA-256 | `a5fb1c150912163fa00744de62b642e632c4ec6e799ce2415d9b9263b09d2fcd` |
| Local bundle archive SHA-256 | `0814773f9f14209ff37ff37e95b3818d2854a391526608c4a4bc56192cba06df` |
| Availability | local qualification artifact only; not a public release |

The Studio/client assets were rebuilt from the same clean commit before assembly. The existing
`assemble-native-bundle.sh` and `create-native-release-artifact.sh` paths were used with the
manifest-verified PostgreSQL and ICU inputs. Archive checksum, every bundle-manifest entry, packaged
licenses, runtime metadata, and direct packaged `--version` passed.

## Checks and limits

- Python helper tests: 3/3 PASS; `py_compile` PASS.
- Real run: PASS in 58.88 seconds on Fedora Linux 44 x86-64 / Python 3.14.7.
- Exact source unchanged before/after and after reload: PASS.
- Different ordered candidate-instance parents: PASS.
- Child matches the actual persisted A/B order: PASS.
- Atomic result membership and producing lineage visible together: PASS.
- Controlled stop/start and durable reread: PASS.
- Credentials retained: false.

This is one explanatory step, not a claim about GA optimization quality. The local bundle is not a
public release, multi-RID qualification, WP-0094 closure, or overall Developer Preview release
qualification. Remote Evolution and general external plugin loading remain out of scope. A failed
publication may retain a failed audit attempt, but cannot appear as a successful partial result.
