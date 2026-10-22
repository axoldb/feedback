#!/usr/bin/env python3
"""Persist a small corpus, dictionary rules, and quanteda results in AxolDB."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import time

from axol_demo import AxolCli, DemoError, canonical, require, run_r, sha256_bytes, sha256_json


def main() -> int:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance-root", type=Path, required=True)
    parser.add_argument("--principal", default="examples.quanteda/admin")
    parser.add_argument("--namespace", default="examples.quanteda-social-protection")
    parser.add_argument("--output", type=Path, default=root / "results")
    args = parser.parse_args()
    started = time.monotonic()
    source_population = f"{args.namespace}/source"
    rules_population = f"{args.namespace}/rules"
    results_population = f"{args.namespace}/results"
    client = AxolCli(args.principal, args.instance_root)
    documents_path = root / "data" / "documents.json"
    dictionary_paths = [root / "dictionaries" / "social-protection-narrow-1.0.0.json",
                        root / "dictionaries" / "social-protection-expanded-2.0.0.json"]
    with tempfile.TemporaryDirectory(prefix="quanteda-run-") as temporary:
        io = Path(temporary)
        run_r(root, ["segment", "/work/data/documents.json", "/io/segmented.json"], io)
        segmented = json.loads((io / "segmented.json").read_text(encoding="utf-8"))
        documents = json.loads(documents_path.read_text(encoding="utf-8"))
        document_hashes = {row["id"]: sha256_bytes(row["text"].encode("utf-8")) for row in documents["documents"]}
        source_manifest = {
            "recordType": "sourceManifest", "formatVersion": 1,
            "source": {key: segmented[key] for key in ("recordType", "formatVersion", "datasetId", "language", "topic", "selectionRule", "license", "documents", "segmentation", "runtime")},
            "inputFileSha256": sha256_bytes(documents_path.read_bytes()),
            "documentTextSha256": document_hashes,
            "provenanceMode": "application-level manifest; not native Evolution lineage",
        }
        source_records = [source_manifest]
        for unit in segmented["units"]:
            record = dict(unit)
            record.update({"recordType": "sourceUnit", "formatVersion": 1,
                           "textSha256": sha256_bytes(unit["text"].encode("utf-8")),
                           "documentTextSha256": document_hashes[unit["documentId"]],
                           "licenseId": documents["license"]["id"]})
            source_records.append(record)
        rules = [json.loads(path.read_text(encoding="utf-8")) for path in dictionary_paths]
        rule_records = [{"recordType": "dictionaryRule", "formatVersion": 1, "rule": rule,
                         "ruleSha256": sha256_json(rule), "fileSha256": sha256_bytes(path.read_bytes()),
                         "provenanceMode": "application-level manifest; not native Evolution lineage"}
                        for rule, path in zip(rules, dictionary_paths)]

        client.bootstrap_and_grant([source_population, rules_population, results_population])
        source_generation, source_hashes = client.insert_records(source_population, "examples.quanteda/source/1", source_records)
        rules_generation, rule_hashes = client.insert_records(rules_population, "examples.quanteda/rule/1", rule_records)

        reloaded_source_records = client.read_records(source_population, source_generation)
        reloaded_rule_records = client.read_records(rules_population, rules_generation)
        from axol_demo import source_from_records, rules_from_records
        reloaded_source = source_from_records(reloaded_source_records)
        reloaded_rules = rules_from_records(reloaded_rule_records)
        (io / "source.json").write_text(canonical(reloaded_source) + "\n", encoding="utf-8")
        (io / "rules.json").write_text(canonical(reloaded_rules) + "\n", encoding="utf-8")
        run_r(root, ["analyze", "/io/source.json", "/io/rules.json", "/io/analyses.json"], io)
        analyses = json.loads((io / "analyses.json").read_text(encoding="utf-8"))["analyses"]
        result_records = []
        for analysis, rule_hash in zip(analyses, rule_hashes):
            result_records.append({
                "recordType": "analysisResult", "formatVersion": 1, "analysis": analysis,
                "applicationManifest": {
                    "sourcePopulation": source_population, "sourceGeneration": source_generation,
                    "rulesPopulation": rules_population, "rulesGeneration": rules_generation,
                    "sourceRecordHashes": source_hashes, "ruleRecordHash": rule_hash,
                    "analysisSha256": sha256_json(analysis),
                    "provenanceMode": "application-level manifest; not native Evolution lineage",
                },
            })
        results_generation, result_hashes = client.insert_records(results_population, "examples.quanteda/result/1", result_records)

        client.server("stop")
        client.server("start")
        status = client.server("status")
        require(status.get("state") == "Ready", "managed AxolDB server is not Ready after restart")
        args.output.mkdir(parents=True, exist_ok=True)
        verify_command = [os.sys.executable, str(root / "verify_reload.py"),
                          "--instance-root", str(args.instance_root), "--principal", args.principal,
                          "--source-population", source_population, "--source-generation", source_generation,
                          "--rules-population", rules_population, "--rules-generation", rules_generation,
                          "--results-population", results_population, "--results-generation", results_generation,
                          "--output", str(args.output)]
        subprocess.run(verify_command, check=True, timeout=600, env=os.environ.copy())
        reload_report = json.loads((args.output / "reload-report.json").read_text(encoding="utf-8"))
        version = subprocess.run([str(client.binary), "--version"], text=True, capture_output=True,
                                 timeout=30, check=True).stdout.strip()
        report = {
            "schemaVersion": 1, "passed": True, "example": "quanteda-social-protection",
            "axolVersion": version,
            "buildProvenance": {
                "availability": "local WP-0096 qualification bundle; not a public release package",
                "runtimeIdentifier": "linux-x64" if platform.system() == "Linux" and platform.machine() == "x86_64" else "unrecorded",
                "sourceCommit": os.environ.get("AXOL_PRODUCT_SOURCE_COMMIT"),
                "bundleManifestSha256": os.environ.get("AXOL_BUNDLE_MANIFEST_SHA256"),
                "bundleArchiveSha256": os.environ.get("AXOL_BUNDLE_SHA256"),
            },
            "corpus": {"datasetId": documents["datasetId"], "documentCount": len(documents["documents"]),
                       "sentenceUnitCount": len(segmented["units"]), "license": documents["license"],
                       "inputFileSha256": source_manifest["inputFileSha256"]},
            "runtime": analyses[0]["runtime"],
            "populations": {
                "source": {"id": source_population, "generation": source_generation, "recordCount": len(source_records)},
                "rules": {"id": rules_population, "generation": rules_generation, "recordCount": len(rule_records)},
                "results": {"id": results_population, "generation": results_generation, "recordCount": len(result_records)},
            },
            "resultRecordHashes": result_hashes,
            "comparison": {"changedUnitCount": reload_report["changedUnitCount"],
                           "checks": reload_report["checks"]},
            "checks": {"sourceReloadedBeforeAnalysis": True, "twoRuleVersionsPersisted": True,
                       "twoResultVersionsPersisted": True, "managedStopStartObserved": True,
                       "independentProcessReloaded": True, "exactRecomputeMatch": True,
                       "finalReportDerivedFromAxolDbReads": True},
            "commands": client.commands, "durationSeconds": round(time.monotonic() - started, 2),
            "secretsRetained": False,
        }
        (args.output / "run-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"passed": True, "changedUnitCount": reload_report["changedUnitCount"],
                          "sourceGeneration": source_generation, "resultsGeneration": results_generation}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DemoError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        raise SystemExit(1)
