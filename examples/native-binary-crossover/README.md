# Native AxolDB binary midpoint crossover

This is a deliberately small, one-step native AxolDB crossover walkthrough. It imports two
four-byte `BinaryValue` candidates with the same schema, creates a Fork, runs two real bounded
tournaments through the public local Evolution CLI, invokes the built-in midpoint operator through
the ordinary plugin lifecycle, and reads the atomically published membership and complete lineage
v2. The script does not choose parents, calculate a child for publication, or write a successor.

The input is readable JSON:

```text
00010203 × 1
a0a1a2a3 × 1
```

There are exactly two candidate instances and `tournamentSize` is one. AxolDB therefore runs the
first tournament over both instances, removes the selected `CandidateInstanceId` from the stable
pool, and runs the second tournament over the remaining finite pool. This reliably demonstrates
two different instances without replacing selection with example code. It does not assume which
input becomes parent A. The saved run selected:

```text
A = 00010203
B = a0a1a2a3
cut = floor(4 / 2) = 2 bytes
child = prefix(A, 2) + suffix(B, 2) = 0001a2a3
```

If another Evolution Run selects the reverse order, the valid result is `a0a10203`. The script
derives its assertion from the persisted `parent-a`/`parent-b` references and genotype hashes.

## What the identities mean

A genotype hash identifies immutable canonical content. A candidate-instance ID identifies one
occurrence participating in this run. Population/Fork membership aggregates equal genotype hashes
with a multiplicity. Producing lineage remains per offspring candidate instance and retains ordered
parent-instance references. Thus two different candidate instances may legitimately contain the
same genotype, and duplicate children may coalesce into one membership row with multiplicity greater
than one. This run has two source contents at multiplicity one and one child content at multiplicity
one.

Lineage records the output candidate-instance ID and genotype hash, Population and source/output
Fork Generations, publication operation, exact operator ID/version/package hash, derived seed,
output ordinal, and ordered parent references. Parent ordinal 0/role `parent-a` supplies the prefix;
ordinal 1/role `parent-b` supplies the suffix. Parents are never re-sorted by hash or ID.

The publication path makes genotype, producing lineage, membership, and Fork head visible together.
A failed attempt may still leave an audit record explicitly marked as failed; it must not leave a
query-visible successful partial Evolution result.

## Requirements and execution

- Python 3.12+; no third-party Python package.
- One source-matched local `linux-x64` AxolDB bundle with CLI version
  `0.1.0-developer-preview+aea2edf8527114c49168bd71eeeabb47ee0445cd`.
- A fresh isolated PostgreSQL-backed managed instance and the documented local CLI environment
  variables. Never place their secret values in a report or archive.

```bash
export AXOL_BIN=/absolute/path/to/bundle/bin/axol
export AXOLDB_CONNECTION_STRING='Host=127.0.0.1;Port=PORT;Database=axoldb;Username=USER;Password=SECRET;SSL Mode=Disable;Pooling=false'
export AXOLDB_DEPLOYMENT_AUDIENCE='native-example'
export AXOLDB_CURSOR_SIGNING_KEY='64-hex-characters'
python3 run_demo.py --instance-root /absolute/path/to/the/isolated/managed-instance
```

One `AXOL_BIN` performs import, source/Fork reads, plugin registration/approval/capability grant and
activation, Evolution, typed Fork Query, lineage, controlled stop/start, and all reload reads. The
qualified artifact is local and is not a publicly released package; do not substitute an older
Developer Preview bundle that lacks the WP-0096 crossover/lineage path.

Use a fresh database or override `--population` and `--fork-segment`. The script creates only the
synthetic principal and exact scopes it needs. Reports contain commands and public identities but
not credentials, connection strings, private keys, instance paths, or unrestricted logs.

## Verification and scope

```bash
python3 -m py_compile run_demo.py tests/test_run_demo.py
python3 -m unittest discover -s tests -v
```

`results/run-report.json` and `results/reload-report.json` are retained evidence from a real run;
[RUN-REPORT.md](RUN-REPORT.md) records its package provenance and checks. Fresh runs create fresh
run/candidate/publication identities. The same root seed with a different Evolution Run ID does not
promise the same parent selection because the run ID participates in RNG derivation.

This demonstrates one native built-in deterministic crossover step, not a general plugin loader,
remote Evolution, a full genetic algorithm, optimization quality, performance, scalability, or
release qualification. DEAP's crossover in the sibling knapsack example executes in external
Python and stores application provenance; it is not this native Evolution lineage.

The code and documentation are MIT-licensed; AxolDB and Python retain their own terms. See
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
