# Example integration review — 2026-10-23

The release-preparation branch integrates completed examples from
`c36eb378f53355a004edbdaad787499ea0f7294e` into feedback main
`7d3890e31373079e0e069446dba70e49c8e5cf77`. Merge is reserved for maintainer review.
The examples remain in this public feedback repository; they are not copied into
the private product source repository or product native archives.

## Verified inputs

All five existing version-1.0.0 ZIPs match their adjacent SHA-256 sidecars.
Every archived file matches this source tree. There are no duplicate/escaping
paths or bundled product binaries/certificate/private-key files. Each ZIP includes
its MIT code license and third-party notices. Exact counts and hashes are in
[`release-archive-audit-20261023.json`](release-archive-audit-20261023.json).

| Archive basename (under `downloads/`) | SHA-256 |
| --- | --- |
| `axoldb-deap-knapsack-1.0.0.zip` | `ddae83bd983ba6f586912254d86a87a1f9b7c287a557b157549955670ea1b95a` |
| `axoldb-mesa-schelling-1.0.0.zip` | `12f9d6fff641b84cbaa79438496c038c99dc11cedf3d7c851a5b2131b494a439` |
| `axoldb-native-integer-evolution-1.0.0.zip` | `91ce5e3f1d7009b545c94131e55ad7c8cdcefc2bc162aa9bd852f2f7290ebf47` |
| `axoldb-native-binary-crossover-1.0.0.zip` | `fcd7a94f8a9fc7548d05f9f4d403d9a60fc44ccd746630b595123665347cdcfd` |
| `axoldb-quanteda-social-protection-1.0.0.zip` | `2b936f9b0830637c33f2769251d82e5ba939c27a110968a84f4704f5beaf7bad` |

## Executed checks and evidence boundary

Helper/unit tests executed on Fedora: DEAP **2 PASS**, Mesa **2 PASS**, native integer
**3 PASS**, native binary **3 PASS**, quanteda **4 PASS**; total **14 PASS / 0 FAIL / 0 SKIP**.
The existing dependency locks were used in a separate test environment. No dependency
version, example model, result file or existing archive was changed.

The retained database campaigns in [`QUALIFICATION.md`](QUALIFICATION.md) and each
example's run report keep their original product pins. DEAP/Mesa used product
`88e7d71571c0b04641d46b7f699dbab84fe463a3`; the native examples used
`aea2edf8527114c49168bd71eeeabb47ee0445cd`, archive `0814773f9f14209ff37ff37e95b3818d2854a391526608c4a4bc56192cba06df`.
They are not tests of a newly built release candidate. No completed database campaign
or Windows qualification was repeated or rebranded by this integration review.

DEAP/Mesa run outside AxolDB and persist ordinary Populations with application-level
checkpoint provenance; their branches are not native Fork lineage. The native examples
use the public local CLI, not remote Evolution. Quanteda analysis and R remain external
prerequisites; GOV.UK source extracts retain the stated Open Government Licence v3.0.
MIT example terms do not grant rights to AxolDB or override dependency/data terms.

## Publication boundary

The source branch and commit-pinned example links are already publicly readable.
This PR prepares their integration into the feedback default branch. It does not
publish a product release/tag/registry package, deploy the website or promise
platform support, production suitability, future compatibility or a support SLA.
