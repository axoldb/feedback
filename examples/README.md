# AxolDB integration examples

These runnable examples cover both external integrations through public AxolDB HTTP/JSON v1 and a
small native Evolution workflow through the public local `axol` CLI.

- [DEAP knapsack](deap-knapsack/README.md): one generation-20 checkpoint, two mutation strategies
  continued to generation 50.
- [Mesa Schelling](mesa-schelling/README.md): one step-30 checkpoint, two satisfaction thresholds
  continued to step 60.
- [Native integer evolution](native-integer-evolution/README.md): import three integers, execute the
  packaged AxolDB mutation operator, inspect Fork membership and lineage, and prove the source is
  preserved.

Server v1 cannot publish descendants of a native Fork from an external DEAP or Mesa process:
fork advancement requires an Evolution Run, while remote Evolution execution is not public in this
preview. Both examples therefore use two ordinary Populations plus application-level provenance
stored in every branch checkpoint. They do not claim native Fork lineage.

The native example is intentionally an integer problem rather than knapsack: the Preview ships one
invocable integer mutation operator and no public crossover/custom-plugin loading path. Its real
run passed using two storage-compatible CLI builds because no one preserved package spans both the
qualified Evolution surface and the later typed Fork Query surface; see its run report for the
exact blocker. This limitation is not hidden with local evolutionary code.

Versioned archives and checksums are under [`downloads/`](downloads/). Website-ready copy prepared
earlier is under [`site-copy/`](site-copy/) and was not changed or deployed by this task. Example
code and documentation are MIT-licensed; AxolDB and third-party dependencies retain their separate
licenses and notices.
