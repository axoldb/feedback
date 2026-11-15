# Example availability and compatibility

These are the original accepted examples from feedback commit
[`c36eb378f53355a004edbdaad787499ea0f7294e`](https://github.com/axoldb/feedback/commit/c36eb378f53355a004edbdaad787499ea0f7294e).
Their default-branch integration had remained in [PR #1](https://github.com/axoldb/feedback/pull/1)
since October 22, 2026. The recovery preserves their algorithms, inputs, dependency locks,
licenses, measured results and original version-1.0.0 archives. It does not recreate them.

## Qualification boundaries

| Example | Retained real-server qualification | Current published 0.1.1 |
|---|---|---|
| [DEAP Knapsack](deap-knapsack/README.md) | Fedora Linux; HTTP/JSON v1; product source `88e7d71571c0b04641d46b7f699dbab84fe463a3`; checkpoint restoration and two continuations | Not freshly qualified |
| [Mesa Schelling](mesa-schelling/README.md) | Same historical product source; stable simulation state, restoration and comparison | Not freshly qualified |
| [Native Integer Evolution](native-integer-evolution/README.md) | Local Linux bundle from `aea2edf8527114c49168bd71eeeabb47ee0445cd`; native mutation, complete lineage and restart | Not freshly qualified; historical local CLI recipe |
| [Native Binary Crossover](native-binary-crossover/README.md) | Same historical local Linux bundle; bounded selection, native midpoint crossover, lineage and restart | Not freshly qualified; historical local CLI recipe |
| [Quanteda Social Protection](quanteda-social-protection/README.md) | Same historical local Linux bundle; R/quanteda analysis, persisted inputs/rules/results and exact restart/recomputation | Not freshly qualified; historical local CLI/Docker recipe |

See [QUALIFICATION.md](QUALIFICATION.md) and each example's run report for exact results.
Historical source-matched local bundles are not official public downloads. If the pinned build
is unavailable, source and results remain inspectable, but do not silently substitute 0.1.1 or
claim a runnable, verified 0.1.1 installation. No new database campaign, Windows full-example
qualification or performance benchmark is implied by recovery/publication.

DEAP and Mesa keep their example-specific HTTP adapters; they are not the official Python SDK.
Official Python, .NET and TypeScript SDKs are available separately through
[AxolDB Downloads](https://axoldb.com/downloads/) and the
[SDK documentation](https://axoldb.com/documentation/sdks/).
Those SDK releases do not retroactively qualify these adapters or examples.

## Historical local connection settings

The three historical local-CLI recipes show a PostgreSQL connection string containing
`SSL Mode=Disable`. It describes an **isolated, disposable, loopback-only qualification setup**.
It is not a managed/remote connection recommendation, an SDK TLS setting or a current 0.1.1
bootstrap recipe. Never disable HTTPS certificate/hostname verification, reuse production
credentials or direct a restart-capable example at an existing development/production instance.
Use the release-specific [installation guide](https://axoldb.com/documentation/installation/)
for current managed setup; adapting a historical example requires separate qualification.

## Integrity and licenses

Code/documentation retain their included MIT licenses. Dependencies remain external and keep
their separate terms. Quanteda's dated GOV.UK extracts retain OGL v3.0 attribution in
[DATA-LICENSE.md](quanteda-social-protection/DATA-LICENSE.md); they are not relicensed as MIT.
No product binaries, private database snapshots, credentials or private execution captures are
included. The [GOV.UK reuse guidance](https://www.gov.uk/help/reuse-govuk-content) identifies OGL
conditions for reuse.

The ZIPs and adjacent SHA-256 sidecars under [downloads](downloads/) remain the original accepted
bytes. Their READMEs are historical snapshots. Source-tree READMEs have a short publication note
pointing here; that documentation overlay does not change an algorithm or repackage a ZIP.
The current review and original source hashes are in
[PUBLICATION-REVIEW-20261115.md](PUBLICATION-REVIEW-20261115.md) and
[PUBLICATION-PROVENANCE.json](PUBLICATION-PROVENANCE.json).

From a Git clone, independently verify all original archives/payloads without a server:

```text
python examples/verify_publication.py --output /outside/repository/audit.json
```

Run each example's documented helper tests in an isolated environment with its dependency lock.
Helper tests and archive checks do not replace the retained real-server qualification or establish
fresh release compatibility. Do not run database/restart tests against a shared lab by default.
