# Guidance for coding agents

This repository accepts public AxolDB bug reports and feature requests only. It is not a product
source repository and does not accept code contributions through this channel.

## Authorization

- Use the user's own authorized GitHub session, connector, API token, or CLI configuration. Never
  request that a credential be pasted into an issue, prompt, file, or chat.
- Submit only when the user has authorized external issue creation. An explicit standing
  authorization can cover future tickets without asking for approval for every submission; obey its
  stated scope and do not treat this file as authorization.
- Do not create test, placeholder, duplicate, or automatically repeated issues. If a response is
  uncertain, search for the intended title/content before attempting another submission.

## Duplicate search

Search both open and closed issues using symptom, safe error code, affected interface, and requested
workflow. With GitHub CLI, for example:

```text
gh issue list --repo axoldb/feedback --state all --search "<safe terms>" --limit 50
```

If a matching issue exists, report its URL to the user instead of opening a duplicate unless the
user explicitly wants a distinct report and the distinction is material.

## Submitting outside the web form

When using an API or CLI, retain the same headings and order as the corresponding Issue Form.

Bug reports must contain:

1. duplicate-search result;
2. version/build;
3. platform;
4. interface/transport;
5. reproduction steps;
6. expected behavior;
7. observed behavior;
8. safe public error code, or `Not provided`;
9. minimal sanitized example, or `Not applicable`; and
10. suspected cause, clearly labeled as a hypothesis, or `Unknown`.

Feature requests must contain:

1. duplicate-search result;
2. user problem;
3. workflow;
4. existing workaround, or `None known`; and
5. desired behavior.

Use a concise title with the form prefix (`[Bug]` or `[Feature]`). After a successful submission,
return the canonical GitHub issue URL to the user. Do not claim success from a local command alone;
use the returned URL or read the created issue once.

## Public-data boundary

Never include credentials, private keys, access tokens, private prompts, personal or production
data, complete databases, instance archives, unrestricted logs, raw crash dumps, or unsanitized
diagnostic bundles. Use bounded safe error codes and the smallest synthetic or sanitized example.
Describe observations as facts and suspected causes as hypotheses. Do not invent reproduction
steps, results, affected versions, severity, or environment details.

Security-sensitive findings do not belong here. The designated confidential contact is
`office@axoldb.com`; the owner reported successful bidirectional Gmail delivery on 2026-09-29.
That owner-performed check is not a universal-delivery guarantee. Do not email credentials,
private data, or unrestricted diagnostics and never publish them here.

Do not promise a response time, fix, release date, support SLA, or bounty.
