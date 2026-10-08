# Quanteda social-protection dictionary comparison with AxolDB

This small English-language example answers one reproducible question: **how much does a dictionary
change the result, and which source sentence units explain the difference?** It compares two
explicitly versioned, illustrative social-protection dictionaries over eight fixed GOV.UK benefit
guide snapshots. It trains no model, calls no LLM, and makes no claim about political positions.

The analysis unit is a sentence produced by `quanteda::tokens(text, what = "sentence")`. The
denominator is the number of those sentence units in each document. Word matching uses quanteda's
fixed, case-insensitive phrase matching after word tokenization. Both dictionaries are demonstration
vocabularies, not validated sociological instruments.

## What quanteda and AxolDB do

Quanteda segments the documents, tokenizes each sentence, applies dictionary versions `1.0.0` and
`2.0.0`, and calculates sentence labels and per-document shares. Local R also computes the changed
unit table and renders the static HTML. AxolDB does not perform those analytical operations.

AxolDB durably stores three application-level datasets:

| Population suffix | Contents |
| --- | --- |
| `source` | one source manifest plus stable sentence records, source URLs, licence and checksums |
| `rules` | the two complete versioned dictionary records and their checksums |
| `results` | both complete result records, each linked to exact source/rule generations and hashes |

These links are **application-level manifests, not native Evolution lineage**. The runner reads
source and rules back from AxolDB before analysis. It then restarts the managed server and starts a
new Python process, which reads source, rules and both saved results from AxolDB, recomputes with R,
requires an exact match of labels/counts/aggregates, and builds `results/report.html` from the
AxolDB-loaded results.

## Corpus and licences

`data/documents.json` contains eight short snapshots from named GOV.UK benefit guides, retrieved
through the GOV.UK Content API on 2026-10-08. The selection was fixed before analysis: the API
description followed by the first paragraph of the first content part. IDs, page/API URLs, public
timestamps and attribution are retained. The data is under Open Government Licence v3.0; see
`DATA-LICENSE.md`. Example code and documentation are MIT-licensed separately.

Manifesto Project was the preferred source but was excluded: its API requires an account/key and
its official terms do not allow redistribution without written authorization. No credential was
requested, embedded or bypassed.

## Requirements and run

- Python 3.12+ (standard library only).
- Docker and the R image built from this directory (`R 4.5.2`, `quanteda 4.5.0`, `jsonlite 2.0.0`).
- The source-matched local `linux-x64` WP-0096 qualification bundle, CLI version
  `0.1.0-developer-preview+aea2edf8527114c49168bd71eeeabb47ee0445cd`.
- A fresh PostgreSQL-backed managed AxolDB instance and its documented local CLI environment.

Build the declared R environment once (network is used only while building dependencies):

```bash
docker build -t axoldb-quanteda-example:wp0096 .
```

Run-time R containers use `--network none`. Start a fresh managed AxolDB instance according to the
bundle README, then export its local settings and run:

```bash
export AXOL_BIN=/absolute/path/to/wp0096-bundle/bin/axol
export AXOLDB_CONNECTION_STRING='Host=127.0.0.1;Port=PORT;Database=axoldb;Username=USER;Password=SECRET;SSL Mode=Disable;Pooling=false'
export AXOLDB_DEPLOYMENT_AUDIENCE='quanteda-example'
export AXOLDB_CURSOR_SIGNING_KEY='64-hex-characters'
export QUANTEDA_R_IMAGE=axoldb-quanteda-example:wp0096
python3 run_demo.py --instance-root /absolute/path/to/fresh/managed-instance
```

Use a fresh database or change `--namespace`. The script bootstraps one example principal and grants
only the public local operations needed for the three populations. It performs a controlled
stop/start itself. Secret values, instance paths and connection strings are not written to reports.
The required bundle is a local qualification artifact, not a publicly released AxolDB package; an
older Developer Preview bundle is not a supported substitute.

Quick checks:

```bash
python3 -m py_compile axol_demo.py run_demo.py verify_reload.py tests/test_example.py
python3 -m unittest discover -s tests -v
```

## Demonstrated result

The retained run has 8 documents and 20 sentence units. The narrow dictionary labels 16 units; the
expanded dictionary labels 18. Exactly two units change from `none` to `social_protection`:

- `govuk-carers-allowance:u03`, through `care` and `benefits`;
- `govuk-disability-living-allowance-children:u01`, through `disabilities` and `children`.

Both result versions remain in AxolDB. After managed restart, a new process loaded all three
populations and exact recomputation matched saved labels, counts and aggregates. See
`RUN-REPORT.md`, `results/run-report.json`, `results/reload-report.json`,
`results/comparison.json`, and the self-contained `results/report.html`.

## Where this could be useful

This pattern is useful when reviewers need to see how a transparent coding-rule revision changes a
small document set, retain exact source/rule/result identities, trace every changed label back to
text and matching expressions, and later reproduce the comparison from durable records.

## Limits

The corpus is small and English-only. The snapshots are not a statistically representative sample.
Dictionary hits are lexical matches, not evidence of intent, stance, eligibility or policy quality.
The example does not validate either dictionary, test inference, benchmark performance, demonstrate
native Evolution lineage, or qualify a public AxolDB release. GOV.UK pages may change after the
included dated snapshot. AxolDB, R, Docker and R packages retain their own terms.
