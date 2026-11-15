# Native integer mutation qualification — 2026-10-08

## Result

**PASS for one local single-package mutation, complete lineage v2, and controlled restart/reload.**

The run imported `1×1, 4×1, 7×1` and published membership `5×2, 8×1`. Evolution Run
`evolution-run-22520e94-5d7b-4731-96bc-030db34e6967` published Fork Generation
`4d776a29-b61f-7c52-965b-fa227dcd06c0`. The three native mutation records identify:

| Output ordinal | Parent candidate instance | Parent value | Child value |
| ---: | --- | ---: | ---: |
| 0 | `29164412…f1a8de` | 4 | 5 |
| 1 | `79834ced…f0251` | 7 | 8 |
| 2 | `29164412…f1a8de` | 4 | 5 |

The returned record order was 0, 2, 1; interpretation uses each stored output ordinal rather than
assuming list order. All three rows are format version 2, name the exact increment operator
binding, and contain output candidate/genotype identity, publication operation, derived seed,
Population/Fork references, and one parent at ordinal 0/role `parent`.

The source stayed at Generation 0 with exact membership `1×1, 4×1, 7×1`. After the same `AXOL_BIN`
performed a managed stop/start, source membership and summary, result membership, Fork head, and
all lineage data matched their pre-restart reads. Machine evidence is in `results/`.

## Bundle provenance

| Field | Value |
| --- | --- |
| Product source commit | `aea2edf8527114c49168bd71eeeabb47ee0445cd` |
| CLI version | `0.1.0-developer-preview+aea2edf8527114c49168bd71eeeabb47ee0445cd` |
| RID | `linux-x64` |
| Bundle manifest | 1,953/1,953 entries PASS |
| Bundle-manifest SHA-256 | `d3c62049506569ce0f93296aee03143500f05758a731ed360a0bdd46fb4aee33` |
| Local archive SHA-256 | `0814773f9f14209ff37ff37e95b3818d2854a391526608c4a4bc56192cba06df` |
| Runtime | PostgreSQL 16.15; .NET/ASP.NET Core 10.0.11; app-local ICU 74.2 / Unicode 15.1 |
| Availability | local WP-0096 qualification artifact only; not a public release |

The same immutable bundle also executed the sibling native crossover walkthrough. This does not
make it a public or multi-RID release qualification.

## Verification

- Python helper tests: 3/3 PASS; `py_compile` PASS.
- Real mutation/restart run: PASS in 81.66 seconds on Fedora Linux 44 x86-64 / Python 3.14.7.
- One `AXOL_BIN` for import, mutation, reads, lineage, stop/start, and reload: PASS.
- Source preservation, exact membership, lineage v2, and reload equality: PASS.
- Credentials retained: false.

## Historical comparison and boundaries

The original two-build report under `results/history/` produced `5×1, 8×2`; an earlier one-bundle
WP-0095 report produced `8×3`. All runs had the same input values and visible root seed, but distinct
Evolution Run IDs and therefore distinct RNG coordinate sets. The old reports did not expose parent
candidate IDs or tournament draws, so exact replay comparison is unavailable; different results do
not demonstrate a regression.

Native crossover is now the separate sibling example. Remote Evolution and external plugin loading
remain unavailable. DEAP/Mesa were not rerun. WP-0094 and overall Developer Preview release
qualification remain separate.
