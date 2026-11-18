# Architecture and invariants

1. fleet/model.py is pure application logic: immutable Scenario, deterministic shortest paths, agent contract, common validation and scoring, two Generation recipes, AgentState and provenance.
2. fleet/storage.py and codec.py use official public SDK contracts. The bounded ACE1 codec is application fixture encoding validated against normative vectors; it is not a replacement SDK or transport.
3. fleet/demo.py coordinates explicit writes and fresh authenticated reads. Model generation and durable publication are different steps.
4. fleet/web.py exposes GET/HEAD on loopback with a scoped viewer. Its browser model comes only from committed SDK data. Mutation methods return 405 and cross-origin requests are rejected.
5. Optional llm_gateway contracts/adapters and fleet/local_llm.py provide a local proposal boundary. fleet/operators.py demonstrates independently evaluated application permutation operators. Neither can write directly to AxolDB.
6. fleet/native.py uses separate typed resources for trusted native integer and binary operations. Its lineage is real server evidence, not application parent metadata.

A Generation checkpoint contains expected parent, previous checkpoint hash, exact payload IDs/hashes, Genotype hashes and request identity. Staged Genotypes are not committed membership. The complete checkpoint and membership are published in the same native authoring/transaction operation; the writer verifies its receipt. Reads verify all payloads and deterministic replay independently, rather than treating a method return as durability proof.

Fresh-process resume first reconstructs committed state from the SDK, validates the exact predecessor and recipe, and publishes only a missing Generation. A completed run has exactly two Generations; rerunning returns the same facts. Source inputs are fixed, so a changed recipe or inconsistent checkpoint refuses instead of repairing history.

Private recorded-response replay reparses stored streaming bytes and validates integrity without calling a provider. Public authored synthetic replay is explicitly labelled and demonstrates plumbing only. No private historical model recordings are distributed.

The two-agent walkthrough is intentionally small. The original larger benchmark and LLM studies are preserved as reviewed aggregate findings, not automatically rerun or fabricated from example fixture data. Equal candidate counts never imply equal model computation. Road replay is synthetic cost-based animation, not telemetry.
