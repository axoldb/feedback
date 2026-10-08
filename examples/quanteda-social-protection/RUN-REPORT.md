# Quanteda social-protection example — qualification report

Status: **PASS for this bounded local example** (2026-10-08).

## Qualified inputs

- Corpus: 8 English GOV.UK benefit-guide snapshots, 20 quanteda sentence units.
- Data licence: Open Government Licence v3.0 with retained attribution.
- Rules: `social-protection-narrow` 1.0.0 and `social-protection-expanded` 2.0.0.
- R 4.5.2; quanteda 4.5.0; jsonlite 2.0.0.
- Container base: `rocker/r-ver:4.5.2` at digest
  `sha256:fd4ccdd3a4a6f7ef805e2daeee2a0fe3bf126bc231f36351223baecf5a595a4c`.
- Qualified local container image ID:
  `sha256:013343a53f68bb873deaadddee0bcee09a61d50df611ed5afd9519c56d2d11ee`.
- AxolDB: local `linux-x64` WP-0096 qualification bundle, version
  `0.1.0-developer-preview+aea2edf8527114c49168bd71eeeabb47ee0445cd`.
- Product source commit: `aea2edf8527114c49168bd71eeeabb47ee0445cd`.
- Bundle manifest SHA-256: `d3c62049506569ce0f93296aee03143500f05758a731ed360a0bdd46fb4aee33`.
- Bundle archive SHA-256: `0814773f9f14209ff37ff37e95b3818d2854a391526608c4a4bc56192cba06df`.

The AxolDB artifact is local and is not a public release package.

## Observed result

The narrow dictionary labeled 16/20 sentence units; the expanded dictionary labeled 18/20. Two
units changed:

1. `govuk-carers-allowance:u03`: `none` → `social_protection`; matches `care`, `benefits`.
2. `govuk-disability-living-allowance-children:u01`: `none` → `social_protection`; matches
   `disabilities`, `children`.

Per-document denominators and shares are preserved in `results/report.html` and the AxolDB result
records. The dictionaries were fixed before this run; input was not edited after seeing the output.

## Persistence and recovery evidence

The first process stored 21 source records, 2 rule records and 2 result records in separate AxolDB
populations. It read source and rules from AxolDB before running both analyses. It then performed a
managed stop/start. A new `verify_reload.py` process read the named generations for source, rules
and results, recomputed with quanteda, and compared the complete analytical structures. Labels,
matched expressions, counts, denominators and shares matched exactly. The final comparison and HTML
were generated from the AxolDB-loaded result records.

The source/rule/result links are application-level manifests. They are not native Evolution
lineage. Reports retain public IDs, checksums and safe command shapes, but no database password,
cursor-signing key, connection string or private path.

## Checks

- Python compilation and 4 focused unit tests: PASS.
- Real PostgreSQL-backed AxolDB execution: PASS.
- Same AxolDB source generation used for both rule versions: PASS.
- Both rules and both result versions reloadable: PASS.
- Managed restart plus independent-process reload: PASS.
- Exact recomputation from AxolDB source/rules: PASS.
- Static HTML escaping and self-contained rendering: PASS.
- ZIP integrity/path safety plus fresh extraction, 4 tests and full AxolDB rerun: PASS; the fresh run
  again reported 2 changed units and an exact post-restart recomputation match.

This is qualification of the bounded example only, not release qualification, sociological
validation, a native-lineage demonstration, or a performance/scalability claim.
