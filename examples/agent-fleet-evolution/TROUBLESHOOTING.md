# Troubleshooting and limitations

- Missing axoldb import: install the verified official 0.1.2.dev1 wheel into the interpreter actually running the command. Do not substitute an arbitrary package with a similar name.
- HTTPS/CA failure: verify the intended isolated instance and its CA. Never disable TLS or change a historical instance.
- Authorization refusal: check the exact Population/Fork resource strings and the four/eight scoped grants. Do not use an owner credential to hide missing application permissions. Cross-actor operation audit is deliberately unavailable to the viewer.
- Missing configuration/token: keep safe JSON outside source and inject the selected scoped token privately. No token is accepted on a command line.
- Uncertain mutation result: preserve the original request and resolve the operation using supported APIs. A timeout does not mean rollback. Do not delete staging objects or issue a new request identity to obtain a clean run.
- Inconsistent checkpoint or changed source: stop and compare hashes/input versions. Never repair accepted experimental data to make replay pass.
- Dashboard 503: actual persisted data did not validate. The API intentionally provides no fixture fallback.
- Native fixture denial: the owner must prepare exact trusted bindings and scoped permissions. Registration is not executable installation; this example does not self-activate plugins.
- Native reservation already exists: do not retry or delete it. Review the actual public request receipts and committed effects. Native crash recovery is not qualified here.
- Local model absent/wrong digest: stop; no automatic pull, update or fallback. A valid JSON response still may be infeasible or useless.
- Replay equality: proves stored-response evaluation, not identical future inference.
- Browser tooling absent: use existing local Playwright/Chromium or report browser acceptance unavailable. The example does not install browsers automatically.

Do not use this Preview for a live operational process under the evaluation license. The bounded synthetic routes are not production fleet dispatch, an optimality certificate or evidence of general LLM inferiority.
