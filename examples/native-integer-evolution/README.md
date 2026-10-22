# Native AxolDB integer mutation

This example imports integers `1×1, 4×1, 7×1`, creates a Fork, runs one native Evolution mutation
step with the built-in reference increment operator, reads successor membership and complete
lineage v2, and proves the source remains unchanged across a controlled managed restart.

`run_demo.py` uses only the public local `axol` CLI. It performs genotype insert, Population and
Fork reads, the real plugin trust lifecycle, Evolution create/start/step, typed Fork Query, lineage,
stop/start, and reload reads with one `AXOL_BIN`. Python validates the result but does not choose a
parent, mutate content, publish membership, or manufacture lineage.

## Current executed result: `5×2, 8×1`

The current WP-0096 bundle made three mutation winner requests. Complete lineage now identifies the
actual parent candidate instance for every offspring:

- output ordinal 0: parent candidate `29164412…f1a8de`, value 4 → value 5;
- output ordinal 1: parent candidate `79834ced…f0251`, value 7 → value 8;
- output ordinal 2: parent candidate `29164412…f1a8de`, value 4 → value 5.

There were three mutation invocations, three offspring candidate instances, and three producing
lineage records. They yielded two distinct immutable genotype contents. Membership therefore has
two hash rows: value 5 with multiplicity 2 and value 8 with multiplicity 1. `5×2` does not mean five
operations or two different value-5 genotypes; two candidate occurrences share one canonical
genotype hash.

Every lineage v2 row also contains the output candidate ID and genotype hash, Population and
source/output Fork Generations, publication operation, exact operator binding, derived seed, output
ordinal, and the single parent at ordinal 0/role `parent`. Mutation publication makes producing
genotypes, lineage, membership and Fork head visible atomically. A failed attempt may retain a
failed audit record, but not a query-visible successful partial result.

## Historical evidence

The preserved `results/history/` reports remain evidence of earlier runs:

- the original two-build run produced `5×1, 8×2`; its three outputs imply parent values 4, 7, 7,
  but the old public lineage projection did not expose candidate-instance parents;
- the earlier one-bundle WP-0095 run produced `8×3`; it likewise used legacy lineage rendering.

Those results are not regressions. Evolution Run ID participates in tournament RNG coordinates, so
the same root seed with a different Run ID does not promise identical parent selections. The
historical evidence also lacks participant draw pairs, so a draw-by-draw replay is impossible.

## Requirements and run

- Python 3.12+; no third-party Python packages.
- One local source-matched `linux-x64` bundle with CLI version
  `0.1.0-developer-preview+aea2edf8527114c49168bd71eeeabb47ee0445cd`.
- A fresh isolated PostgreSQL-backed managed instance and the documented local CLI environment.

```bash
export AXOL_BIN=/absolute/path/to/bundle/bin/axol
export AXOLDB_CONNECTION_STRING='Host=127.0.0.1;Port=PORT;Database=axoldb;Username=USER;Password=SECRET;SSL Mode=Disable;Pooling=false'
export AXOLDB_DEPLOYMENT_AUDIENCE='native-example'
export AXOLDB_CURSOR_SIGNING_KEY='64-hex-characters'
python3 run_demo.py --instance-root /absolute/path/to/the/isolated/managed-instance
```

The qualified bundle is a local WP-0096 artifact, not a public release. Do not direct this flow at
an older package lacking the canonical Population-ID correction and WP-0096 lineage/publication
path. Use a fresh database or override `--population` and `--fork-segment`. Reports retain public
identities and safe commands, never the connection string, password, signing key, private instance
path, or unrestricted logs.

```bash
python3 -m py_compile run_demo.py tests/test_run_demo.py
python3 -m unittest discover -s tests -v
```

[RUN-REPORT.md](RUN-REPORT.md) and `results/` contain retained execution evidence. Fresh runs create
different run/candidate/publication identities.

This is a mutation walkthrough. Native binary crossover is demonstrated separately in
[`../native-binary-crossover/`](../native-binary-crossover/). Neither example is a full genetic
algorithm, optimization-quality, performance, scalability, remote-Evolution, custom-loader, or
release claim. DEAP/Mesa manifests are application provenance, not native Evolution lineage.

The example is MIT-licensed; AxolDB and Python retain their own terms. See
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
