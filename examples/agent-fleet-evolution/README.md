# Agent Fleet Evolution — Persistent Multi-Agent Experiments with AxolDB

A small runnable example of deterministic agents, explicit persistence and replay. It is useful without a model, cloud account, Node, Docker or AxolDB credentials: start with the pure Python workflow below. AxolDB persistence and local inference are separate opt-in layers.

This distribution is a bounded two-agent walkthrough, not a release of the internal research lab or its complete benchmark campaign. It contains no product source/binary, private recording, credential, certificate or database.

## Start without a database

Use conventional CPython 3.12–3.14. From this directory:

~~~sh
python -B -m fleet offline --output /your/private/run/deterministic.json
python -B -m fleet replay --recorded /your/private/run/deterministic.json
python -B -m fleet proposal --recorded synthetic-recording.json
python -B tests/run.py unit --output /your/private/run/unit.json
~~~

Choose an unused output location; the example refuses to overwrite different evidence. The supplied recording is explicitly authored synthetic data, not a private model response. The deterministic core has no third-party dependencies. Fresh-process replay recomputes routes, costs, plans and references. Expected costs are Agent A 24 → 24 and Agent B 22 → 22; order changes do not imply a cost improvement.

The abstract, undirected graph has positive integer costs, one depot, five single-unit deliveries and two capacity-three vehicles. Every delivery is assigned exactly once, every route returns to the depot, and full-path lexical tie-breaking makes shortest paths stable. Passing a delivery node in transit does not serve it. The graph and every plan have canonical content hashes. Agents receive immutable inputs and return complete FleetPlans and AgentStates.

## Persist with the official public SDK

Install and initialize a fresh, isolated **AxolDB 0.1.2 Developer Preview** instance using the [official guide](https://axoldb.com/documentation/setup/0.1.2-developer-preview/). Native packages are Windows x64 and Linux x64; no macOS native package is published for this release. The SDK itself is separate.

Download and personally accept the official [Python SDK](https://axoldb.com/downloads/#client-sdks), verify the [0.1.2 SDK checksums](https://axoldb.com/releases/0.1.2-sdk-preview.1/SHA256SUMS), then install its 0.1.2.dev1 wheel into a virtual environment. No PyPI availability is implied:

~~~sh
python -m venv .venv
# Activate .venv using your shell.
python -m pip install /verified/path/axoldb_client-0.1.2.dev1-py3-none-any.whl
python -m pip check
~~~

The verified SDK dependency pins used here include HTTPX 0.28.1 and HTTPcore 1.0.9. requirements.txt is a compatibility constraint list, not a promise that pip can find AxolDB on a public index. Install the official wheel first. No .NET, Node, system PostgreSQL or cloud model is needed by the Python client. The native distribution supplies its managed PostgreSQL runtime.

Copy config.example.json outside source, configure the actual HTTPS endpoint and instance CA, and arrange the exact [scoped credentials](PERMISSIONS.md). Keep separate writer/viewer tokens. private_run.py reads each selected token at hidden input and passes it only through the child process environment; no token is put in a command line or config file.

~~~sh
python private_run.py /private/config.json writer,viewer run --run my-first-run --through 0 --output /private/generation0.json
# The application exits. Start a fresh process:
python private_run.py /private/config.json writer,viewer run --run my-first-run --output /private/completed.json
python private_run.py /private/config.json viewer read --run my-first-run --output /private/fresh-read.json
python -B -m fleet replay --recorded /private/completed.json
# Completed-run resume must not add a third Generation:
python private_run.py /private/config.json writer,viewer run --run my-first-run --output /private/idempotent.json
python private_run.py /private/config.json viewer serve --run my-first-run --port 8765
~~~

Open http://127.0.0.1:8765/. The visualization reads actual persisted data with the viewer credential. It has no data fallback and no write/model endpoint. Select Generation, agent and vehicle; inspect costs, routes, checkpoints and application provenance; play, pause, reset or step the deterministic replay. Edge cost is abstract travel cost; playback maps one cost unit to 400 ms of synthetic time. It is not live vehicle tracking.

The dedicated resources are axol://populations/public-fleet/my-first-run and axol://forks/public-fleet/my-first-run/reference. Choose a new run ID for an independent experiment. Never repoint at historical data, delete a database for a clean run or disable TLS. Stop the owned visualization with Ctrl+C.

## What is persisted

Each of two native Generations contains Scenario, two FleetPlans, two AgentStates and one checkpoint. Values are staged as canonical binary Genotypes; one explicit synchronous serializable publication makes the complete membership and checkpoint visible together. A reference Fork copies Generation 0 and remains at its birth state.

The writer verifies its own operation receipt and authoritative commit witness. A distinct read-only viewer verifies committed Generation records, membership, references, canonical payload hashes and checkpoint continuity. Cross-principal operation receipt detail needs separate audit authority; the dashboard does not acquire that authority.

Generation 1 resumes from persisted AgentStates and plans, ranks candidates deterministically and applies bounded application-level variation. Application parent references are not native Evolution lineage. Optional ordered crossover and swap operators in fleet/operators.py provide a separate permutation boundary with independently recomputed paths, costs and loads; the two-agent walkthrough does not silently substitute those operators into its accepted Generation 1 recipe.

## Optional local LLM gateway

See [the optional gateway](LOCAL-LLM.md). The provider-neutral gateway has typed requests, capability declarations, structured validation and explicit recording/replay. Three adapter families are included; cloud compatibility is not inferred from offline tests. Only the local opt-in binding is configured in this example.

Model outputs contain delivery order only. The application rejects duplicate, missing or unknown deliveries and extra model cost fields, computes fitness independently and never repairs silently or admits a proposal automatically. The LLM cannot mutate the database.

The accepted historical pilot returned 15 valid permutations, all the same cost-28 plan. **Zero were admitted and no optimization benefit was measured.** [Historical results and limitations](RESULTS.md) also preserve the earlier deterministic study and representation comparison. These summaries are not hardcoded runtime results or fixtures replacing AxolDB.

## Separate native Evolution fixture

See [native typed mutation and crossover](NATIVE.md). The optional fixture uses public 0.1.2 SDK parity operations and existing owner-approved trusted bindings. It never registers/activates plugins or grants its own permissions. It runs integer increment and binary midpoint crossover, then verifies actual persisted lineage and parent order through fresh reads. It is separate from FleetPlan JSON evolution.

## Tests, provenance and limits

Unit tests use no SDK/network. The SDK-contract suite uses the installed public artifact with network blocked. Live integration is read-only and expects a newly completed walkthrough plus native fixture. [TESTING.md](TESTING.md) lists exact commands and browser prerequisites.

The deterministic portion was executed from a fresh source export and new dependency-free virtual environment on the qualification host. Live scoped SDK and real Chromium checks were also run. This is not a full clean-host, cross-platform or cloud-provider qualification. No hard-kill, power-loss or native interrupted Evolution recovery is claimed.

[Architecture](ARCHITECTURE.md) · [Recorded findings](RESULTS.md) · [Troubleshooting](TROUBLESHOOTING.md) · [MIT license](LICENSE) · [Dependency notices](THIRD-PARTY-NOTICES.md)

AxolDB remains proprietary, with its unchanged separate [Developer Preview license](https://axoldb.com/license/). This example's MIT license does not grant Production Use, redistribution of the native product or broader SDK redistribution rights.
