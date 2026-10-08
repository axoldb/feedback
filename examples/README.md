# AxolDB integration examples

These runnable examples show external tools persisting complete, resumable state through the
public AxolDB HTTP/JSON v1 API.

- [DEAP knapsack](deap-knapsack/README.md): one generation-20 checkpoint, two mutation strategies
  continued to generation 50.
- [Mesa Schelling](mesa-schelling/README.md): one step-30 checkpoint, two satisfaction thresholds
  continued to step 60.

Server v1 cannot publish descendants of a native Fork from an external DEAP or Mesa process:
fork advancement requires an Evolution Run, while remote Evolution execution is not public in this
preview. Both examples therefore use two ordinary Populations plus application-level provenance
stored in every branch checkpoint. They do not claim native Fork lineage.

Versioned archives and checksums are under [`downloads/`](downloads/). Website-ready copy is under
[`site-copy/`](site-copy/). The repository currently has no code license and its contributor
guidance says it does not accept code contributions; see each archive's `LICENSE-STATUS.md`. The
examples are locally complete, but public distribution is blocked pending an owner license and
repository-policy decision.
