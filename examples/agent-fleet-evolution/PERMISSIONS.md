# Explicit application authority

An instance owner creates service principals and issues private credentials using supported security/credential interfaces. Neither the example nor a model self-grants authority. Use fresh resources and separate writer/viewer credentials. Follow [official security setup](https://axoldb.com/documentation/security/) and the installed CLI help; do not invent token-issuance flags.

For run my-first-run:

| Principal | Action | Resource | Exact scope |
|---|---|---|---|
| Viewer | ExecuteQuery | Query | query |
| Viewer | Read | Population | axol://populations/public-fleet/my-first-run |
| Viewer | Read | IndividualGenotype | the same Population ID |
| Viewer | Read | Fork | axol://forks/public-fleet/my-first-run/reference |
| Writer | all four viewer permissions | same resources | same scopes |
| Writer | Insert | Population | the Population ID |
| Writer | Insert | IndividualGenotype | the Population ID |
| Writer | PublishGeneration | Population | the Population ID |
| Writer | CreateFork | Population | the Population ID |

The viewer has four grants, the writer eight. Do not add ChangeSecurityPolicy, credential issuance, plugin administration or cross-actor audit access to either. The writer resolves its own operation receipts; the viewer validates committed state without accessing those details. A denied call is a blocker to inspect, not permission to fall back to an owner credential.

Safe config contains endpoint, public CA path and credential environment-variable names only. Tokens remain in private process memory/environment. The SDK uses CaFile and strict HTTPS. Clearing a Python reference is not secure zeroization or server-side revocation.

The optional native fixture needs its own credential and two fresh native resource pairs; see NATIVE.md. No historical namespace is part of these grants. Cleanup of example resources and revocation of credentials are explicit owner operations; no automatic database or directory deletion is provided.
