# Existing examples: publication recovery review

## Why main did not contain the examples

The feedback default branch remained at `7d3890e31373079e0e069446dba70e49c8e5cf77`.
All five examples were already publicly readable at accepted source
`c36eb378f53355a004edbdaad787499ea0f7294e` on `codex/public-integration-examples`.
The subsequent integration head `c19ccce389e0ac2b8be8354790361897b98619b9` was left in
[PR #1](https://github.com/axoldb/feedback/pull/1), opened on October 22, 2026.
Its scope explicitly prepared review without a merge. No deletion or lost implementation
was found in main's two-commit history. This recovery continues the existing dedicated PR
rather than reimplementing the examples or opening a duplicate integration PR.

## Authoritative versions and retained evidence

| Example | Accepted source history | Qualification evidence |
|---|---|---|
| DEAP Knapsack | Original `0e777510`; license/acceptance closure `135f1bf220d65281da7d75482fba9e73841e0b91`; retained in `c36eb378` | [QUALIFICATION.md](QUALIFICATION.md); `results/results.json`, branch results and comparison plot |
| Mesa Schelling | Same original/closure commits; retained in `c36eb378` | [QUALIFICATION.md](QUALIFICATION.md); `results/results.json`, branch results and scenario plot |
| Native Integer Evolution | Implementation `93a6088b`; accepted single-bundle update `02935b7fd7c97e831b26f923da4666751c6ac419` | [RUN-REPORT.md](native-integer-evolution/RUN-REPORT.md); current run/reload JSON; older two-build results retained under history |
| Native Binary Crossover | `76bcc1cd9e4ffafb8dbb0839fe680ea2ef0f81e5` | [RUN-REPORT.md](native-binary-crossover/RUN-REPORT.md); current run/reload JSON |
| Quanteda Social Protection | `c36eb378f53355a004edbdaad787499ea0f7294e` | [RUN-REPORT.md](quanteda-social-protection/RUN-REPORT.md); run/reload/comparison JSON and HTML |

The final MIT grant and notices supersede the earlier DEAP/Mesa license-blocked versions.
Integer Evolution's accepted current result is `5×2, 8×1`; its older two-build result is
historical evidence, not the selected implementation. The accepted source pin includes all five
final versions. Full original Git blob and SHA-256 identities are recorded in
[PUBLICATION-PROVENANCE.json](PUBLICATION-PROVENANCE.json).

No algorithm, fixture, dependency lock, license, measured result or original archive changed.
Five source READMEs received only an introductory compatibility/security notice. The
version-1.0.0 ZIPs retain their original READMEs and exact SHA-256 sidecars; no archive was
silently repackaged. The index, publication notes and standard-library verification script
are new review/discoverability material.

## Checks executed on 2026-11-15

Windows, CPython 3.14.8, isolated test environment using the original DEAP/Mesa dependency locks:

| Check | Result |
|---|---|
| DEAP model/helper tests | 2 PASS |
| Mesa state/identity tests | 2 PASS |
| Native integer helper tests | 3 PASS |
| Native binary helper tests | 3 PASS |
| Quanteda Python projection/comparison tests | 4 PASS |
| Total selected helper tests | **14 PASS / 0 FAIL / 0 SKIP** |
| Original Python source parsing | 28 files PASS |
| Original ZIP checksums, structure and member safety | All five PASS |
| ZIP member bytes versus accepted Git source | All 85 files PASS |
| Current accepted payloads | 80 unchanged files; five README-only overlays |
| High-confidence credential/private-key/private-user-path pattern scan | No findings; manual source/fixture/result review also performed |

These were helper tests, not five new real-server campaigns. No AxolDB instance was started,
stopped or used. No fresh 0.1.1 example, Windows full-workflow, R/Docker execution or performance
qualification is claimed. The existing Server-backed results keep their original product pins.
Reproduction of helper tests follows each README; `verify_publication.py` reproduces original
archive/source checks from a Git clone without a server or network.

## Publication gates

All five are eligible for publication as **historically qualified examples** with explicit
compatibility boundaries. Their original code/docs carry the owner-adopted MIT text. Dependencies
are not vendored and retain separate licenses. Quanteda's eight public GOV.UK extracts carry
OGL v3.0 attribution and provenance; no restricted Manifesto Project corpus is included.
No product binary, private database, credential, private key or private execution capture is
included. [Availability notes](PUBLICATION-STATUS.md) scope historical `SSL Mode=Disable`
strictly to disposable loopback qualification and direct users to current managed setup.

The current website's five example cards were independently fetched over HTTPS. All 16 feedback
links (README/report anchors, ZIPs, checksum sidecars and source index) resolve correctly to the
accepted immutable revision. Archive/checksum response bytes match the accepted Git objects.
Those pinned historical links remain correct after main integration, so no website correction
or deployment is required for this recovery.

Normal PR merge remains the publication boundary. A local checkout, this review document or a
successful branch update is not proof of default-branch publication; main and its actual public
source files must be independently verified after merge. No product/SDK implementation, native
release artifact or historical native manifest is part of this change.
