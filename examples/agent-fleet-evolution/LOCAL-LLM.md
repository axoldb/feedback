# Optional local model proposals

The deterministic walkthrough never invokes a model. Its public authored recording can be replayed without Ollama:

~~~sh
python -B -m fleet proposal --recorded synthetic-recording.json
~~~

llm_gateway supplies the accepted version-1 provider-neutral Request/Result, capability, error and adapter boundaries. Its three families are OpenAI-compatible, Anthropic and Gemini. The bundled model template is disabled; no public cloud model is configured, probed or claimed compatible by this package. The optional native Ollama streaming binding uses the same Request contract and validates a minimal permutation independently.

For a user-owned local request, first obtain and verify the model yourself under its separate terms. This example never downloads, pulls, updates or replaces a model. The opt-in command requires an already installed gemma3:4b with digest a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a on the standard loopback endpoint:

~~~sh
python -B -m fleet.local_llm --allow-local-inference --private-directory /private/new-permutation-request
~~~

This makes **at most one inference call**. A durable reservation prevents another call in that directory. There is no retry, repair or provider fallback. It uses context 2048, at most 192 output tokens, a conservative 1856-byte prompt bound, socket inactivity timeout 90 seconds and total deadline 180 seconds. Concurrency is one. Hard CPU/GPU memory partitioning is not provided. Use an owner-private directory and conservative hardware headroom; Ctrl+C terminates only the owned client, never shared Ollama.

The simplified optional public prompt is not the frozen historical pilot prompt. This command was syntax/contract tested with synthetic transports; it was not invoked as another model study during publication. Historical local qualification does not prove all future requests or an OpenAI-compatible Ollama endpoint behave identically.

Raw bytes, partial progress, request identity, actual provider token counters, timing and result are saved locally. They are private evidence. A separate local recording key authenticates their integrity; this is not third-party attestation. Do not publish private prompts, responses or the key.

Recorded streaming replay, without provider access, can be invoked in a private Python process:

~~~python
from pathlib import Path
from llm_gateway.native_stream import replay
folder = Path("/private/new-permutation-request")
result = replay(folder / "response.json", (folder / "recording.key").read_bytes())
assert result["exact"] and result["providerCalls"] == 0
~~~

An incomplete or unanswered request remains evidence and must not be retried implicitly. Exact recorded replay does not promise byte-identical future live inference. Model-provided costs are rejected; valid proposals are decoded with capacity-three vehicle allocation and scored independently. No proposal is inserted into the two-agent Population automatically. A larger competitive admission experiment requires its own frozen design and scoped persistence.
