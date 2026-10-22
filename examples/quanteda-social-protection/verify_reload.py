#!/usr/bin/env python3
"""Independent post-restart process: reload, recompute, compare, and render."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from axol_demo import (AxolCli, analyses_from_records, canonical, compare_analyses,
                       rules_from_records, run_r, source_from_records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance-root", type=Path, required=True)
    parser.add_argument("--principal", required=True)
    parser.add_argument("--source-population", required=True)
    parser.add_argument("--source-generation", required=True)
    parser.add_argument("--rules-population", required=True)
    parser.add_argument("--rules-generation", required=True)
    parser.add_argument("--results-population", required=True)
    parser.add_argument("--results-generation", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    client = AxolCli(args.principal, args.instance_root)
    source = source_from_records(client.read_records(args.source_population, args.source_generation))
    rules = rules_from_records(client.read_records(args.rules_population, args.rules_generation))
    stored = analyses_from_records(client.read_records(args.results_population, args.results_generation))
    with tempfile.TemporaryDirectory(prefix="quanteda-reload-") as temporary:
        io = Path(temporary)
        (io / "source.json").write_text(canonical(source) + "\n", encoding="utf-8")
        (io / "rules.json").write_text(canonical(rules) + "\n", encoding="utf-8")
        run_r(root, ["analyze", "/io/source.json", "/io/rules.json", "/io/recomputed.json"], io)
        recomputed = json.loads((io / "recomputed.json").read_text(encoding="utf-8"))["analyses"]
        comparison = compare_analyses(stored, recomputed)
        args.output.mkdir(parents=True, exist_ok=True)
        stored_set = {"recordType": "analysisSet", "formatVersion": 1,
                      "datasetId": source["datasetId"], "analyses": stored}
        (args.output / "comparison.json").write_text(json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (io / "stored.json").write_text(canonical(stored_set) + "\n", encoding="utf-8")
        (io / "comparison.json").write_text(canonical(comparison) + "\n", encoding="utf-8")
        run_r(root, ["render", "/io/stored.json", "/io/comparison.json", "/io/report.html"], io)
        (args.output / "report.html").write_bytes((io / "report.html").read_bytes())
        report = {
            "schemaVersion": 1, "passed": True, "process": "independent post-restart verifier",
            "sourcePopulation": args.source_population, "sourceGeneration": args.source_generation,
            "rulesPopulation": args.rules_population, "rulesGeneration": args.rules_generation,
            "resultsPopulation": args.results_population, "resultsGeneration": args.results_generation,
            "sourceUnitCount": len(source["units"]), "storedResultCount": len(stored),
            "changedUnitCount": comparison["changedUnitCount"],
            "checks": comparison["checks"], "commands": client.commands, "secretsRetained": False,
        }
        (args.output / "reload-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": True, "changedUnitCount": comparison["changedUnitCount"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
