# AxolDB integration examples

These runnable examples cover both external integrations through public AxolDB HTTP/JSON v1 and a
small native Evolution workflow through the public local `axol` CLI.

- [DEAP knapsack](deap-knapsack/README.md): one generation-20 checkpoint, two mutation strategies
  continued to generation 50.
- [Mesa Schelling](mesa-schelling/README.md): one step-30 checkpoint, two satisfaction thresholds
  continued to step 60.
- [Native integer evolution](native-integer-evolution/README.md): import three integers, execute the
  built-in AxolDB mutation operator, inspect complete native lineage, and prove the source is
  preserved across restart.
- [Native binary crossover](native-binary-crossover/README.md): run two bounded tournaments over
  distinct binary candidate instances, execute the built-in midpoint operator, and verify the child
  against the actual persisted A/B parent order.

Server v1 cannot publish descendants of a native Fork from an external DEAP or Mesa process:
fork advancement requires an Evolution Run, while remote Evolution execution is not public in this
preview. Both examples therefore use two ordinary Populations plus application-level provenance
stored in every branch checkpoint. They do not claim native Fork lineage.

The two native examples use one locally qualified source-matched bundle and the public local CLI.
They demonstrate the built-in increment mutation and binary midpoint crossover separately; they do
not claim a general plugin loader, remote Evolution, optimization quality, or a public release.
Historical two-build mutation evidence remains under the integer example's `results/history/`.
DEAP crossover executes in external Python and its manifest provenance is not native lineage.

Quanteda remains a possible future integration; no Quanteda example is included or qualified here.

Versioned archives and checksums are under [`downloads/`](downloads/). Website-ready copy prepared
earlier is under [`site-copy/`](site-copy/) and was not changed or deployed by this task. Example
code and documentation are MIT-licensed; AxolDB and third-party dependencies retain their separate
licenses and notices.
