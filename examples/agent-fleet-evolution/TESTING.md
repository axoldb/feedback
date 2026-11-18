# Test execution

Run from the example directory. Choose new output paths outside source.

~~~sh
# Standard-library deterministic tests, no SDK or network:
python -B tests/run.py unit --output /private/unit.json
# Installed public SDK/gateway contracts, network blocked:
python -B tests/run.py sdk --output /private/sdk-contract.json
~~~

After completing the two-Generation run and separate native fixture in new resources:

~~~sh
python private_run.py /private/config.json viewer,native test --run my-first-run --native-record /private/native.json --output /private/live-tests.json
~~~

The seven live tests are read-only. They verify authenticated fresh readback, native Generation membership, exact replay, checkpoint continuity, repeat reads and native lineage/value readback. They do not stop AxolDB, mutate an earlier study or perform inference. The writer's own publication receipt checks occur during the run; the dashboard viewer deliberately lacks cross-actor operation-audit access.

Real browser qualification requires existing Playwright Core and Chromium/Edge, external test tooling not bundled with this runtime. tests/browser.cjs takes Python executable, Playwright module directory, browser executable, safe config, run ID and a new output directory. Inject the scoped viewer credential privately into that process's environment using your operating system's private mechanism. It launches and terminates only its owned read-only backend. Never download a browser or invoke a model as an implicit test dependency.

~~~sh
node tests/browser.cjs /path/to/python /path/to/playwright-core /path/to/chromium /private/config.json my-first-run /private/new-browser-results
~~~

Machine-readable counts and screenshots are output locally. Unit and contract tests must not be described as real-browser acceptance. This distribution was tested on the qualification Windows host, including a fresh source export and dependency-free virtual environment for the deterministic portion; a completely new machine was not qualified.

No model request is made by any default test. The optional local prompt/streaming binding is a new public recipe, not a rerun of a frozen historical study. Use authored synthetic transports for parser, deadline and recording faults. Native runtime/trust failures are blockers, not reasons to add broad permissions or disable security.
