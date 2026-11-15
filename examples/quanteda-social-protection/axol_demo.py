"""Small local-CLI adapter used only by the quanteda example."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


class DemoError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DemoError(message)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical(value).encode("utf-8"))


class AxolCli:
    def __init__(self, principal: str, instance_root: Path) -> None:
        raw = os.environ.get("AXOL_BIN")
        require(bool(raw), "set AXOL_BIN to the WP-0096 local qualification bundle executable")
        self.binary = Path(raw).expanduser().resolve()
        require(self.binary.is_file() and os.access(self.binary, os.X_OK), "AXOL_BIN is not executable")
        for name in ("AXOLDB_CONNECTION_STRING", "AXOLDB_DEPLOYMENT_AUDIENCE", "AXOLDB_CURSOR_SIGNING_KEY"):
            require(bool(os.environ.get(name)), f"set {name}; see README.md")
        self.principal = principal
        self.instance_root = instance_root.resolve()
        self.bundle_root = self.binary.parent.parent
        self.commands: list[str] = []

    def invoke(self, arguments: list[str], *, principal: str | None = None) -> Any:
        actual_principal = self.principal if principal is None else principal
        command = [str(self.binary), *arguments, "--local", "--output", "json"]
        display = ["axol", *arguments, "--local", "--output", "json"]
        if actual_principal:
            command += ["--as", actual_principal]
            display += ["--as", actual_principal]
        result = subprocess.run(command, text=True, capture_output=True, timeout=120, check=False)
        self.commands.append(" ".join(display))
        try:
            envelope = json.loads([line for line in result.stdout.splitlines() if line.strip()][-1])
        except (IndexError, json.JSONDecodeError) as exc:
            detail = (result.stderr.strip() or result.stdout.strip() or "no output")[-500:]
            raise DemoError(f"invalid AxolDB output for {' '.join(arguments[:2])}: {detail}") from exc
        if result.returncode != 0 or envelope.get("success") is not True:
            error = envelope.get("error") or {}
            raise DemoError(f"{' '.join(arguments[:2])} failed: {error.get('code', 'unknown')} - {error.get('message', '')}")
        return envelope.get("data")

    def server(self, action: str) -> Any:
        command = [str(self.binary), "server", action, "--instance-root", str(self.instance_root),
                   "--bundle-root", str(self.bundle_root), "--output", "json"]
        result = subprocess.run(command, text=True, capture_output=True, timeout=180, check=False)
        self.commands.append(f"axol server {action} --instance-root <isolated-instance> --bundle-root <qualification-bundle> --output json")
        try:
            envelope = json.loads([line for line in result.stdout.splitlines() if line.strip()][-1])
        except (IndexError, json.JSONDecodeError) as exc:
            detail = (result.stderr.strip() or result.stdout.strip() or "no output")[-500:]
            raise DemoError(f"server {action} returned invalid output: {detail}") from exc
        if result.returncode != 0 or envelope.get("success") is not True:
            error = envelope.get("error") or {}
            raise DemoError(f"server {action} failed: {error.get('code', 'unknown')} - {error.get('message', '')}")
        return envelope.get("data")

    def bootstrap_and_grant(self, populations: list[str]) -> None:
        self.invoke(["security", "bootstrap", "--principal", self.principal, "--kind", "human"], principal="")
        self.invoke(["security", "grant", "--principal", self.principal, "--action", "Insert", "--resource", "Population"])
        self.invoke(["security", "grant", "--principal", self.principal, "--action", "ExecuteQuery", "--resource", "Query", "--resource-id", "query"])
        for population in populations:
            canonical_id = f"axol://populations/{population}"
            for action, resource in (("Read", "Population"), ("Insert", "IndividualGenotype"),
                                     ("Read", "IndividualGenotype"), ("PublishGeneration", "Population")):
                self.invoke(["security", "grant", "--principal", self.principal, "--action", action,
                             "--resource", resource, "--resource-id", canonical_id])

    def insert_records(self, population: str, schema_id: str, records: list[dict[str, Any]]) -> tuple[str, list[str]]:
        schema_hash = sha256_bytes(schema_id.encode())
        hashes: list[str] = []
        for record in records:
            inserted = self.invoke(["genotype", "insert", "--schema-id", schema_id,
                                    "--schema-hash", schema_hash, "--value", "str:" + canonical(record),
                                    "--population-id", population])
            hashes.append(inserted["genotypeHash"])
        contract_hash = sha256_bytes(("contract:" + schema_id).encode())
        arguments = ["population", "create", "--id", population, "--contract-hash", contract_hash]
        for digest, count in sorted(Counter(hashes).items()):
            arguments += ["--member", f"{digest}:{count}"]
        created = self.invoke(arguments)
        return created["generation"], hashes

    def read_records(self, population: str, generation: str) -> list[dict[str, Any]]:
        data = self.invoke(["query", "submit", "--population", population, "--generation", generation])
        records: list[dict[str, Any]] = []
        for row in data["rows"]:
            value = row.get("value")
            require(isinstance(value, str) and value.startswith("str:"), "expected a string record from AxolDB")
            multiplicity = int(row.get("multiplicity", 1))
            require(multiplicity == 1, "application records must have multiplicity one")
            records.append(json.loads(value[4:]))
        return records


def run_r(example_root: Path, arguments: list[str], io_dir: Path) -> None:
    image = os.environ.get("QUANTEDA_R_IMAGE", "axoldb-quanteda-example:wp0096")
    io_dir.mkdir(parents=True, exist_ok=True)
    command = ["docker", "run", "--rm", "--network", "none", "--user", f"{os.getuid()}:{os.getgid()}",
               "-e", "HOME=/tmp", "-v", f"{example_root.resolve()}:/work:ro",
               "-v", f"{io_dir.resolve()}:/io:rw", image, "Rscript", "/work/analysis.R", *arguments]
    subprocess.run(command, check=True, timeout=300)


def source_from_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    manifests = [row for row in records if row.get("recordType") == "sourceManifest"]
    units = [row for row in records if row.get("recordType") == "sourceUnit"]
    require(len(manifests) == 1, "AxolDB source must contain exactly one source manifest")
    units.sort(key=lambda row: (row["documentId"], row["ordinal"]))
    result = dict(manifests[0]["source"])
    result["units"] = units
    return result


def rules_from_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules = [row["rule"] for row in records if row.get("recordType") == "dictionaryRule"]
    rules.sort(key=lambda row: row["version"])
    require(len(rules) == 2, "AxolDB rules must contain exactly two dictionary versions")
    return rules


def analyses_from_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = [row["analysis"] for row in records if row.get("recordType") == "analysisResult"]
    results.sort(key=lambda row: row["dictionaryVersion"])
    require(len(results) == 2, "AxolDB results must contain exactly two analyses")
    return results


def compare_analyses(stored: list[dict[str, Any]], recomputed: list[dict[str, Any]]) -> dict[str, Any]:
    require(canonical(stored) == canonical(recomputed), "recomputed labels, counts, or aggregates differ")
    old, new = stored
    old_units = {row["unitId"]: row for row in old["units"]}
    changed = []
    for row in new["units"]:
        previous = old_units[row["unitId"]]
        if previous["label"] != row["label"]:
            changed.append({
                "unitId": row["unitId"], "documentId": row["documentId"],
                "documentTitle": row["documentTitle"], "text": row["text"],
                "oldLabel": previous["label"], "newLabel": row["label"],
                "oldMatchedExpressions": previous["matchedExpressions"],
                "newMatchedExpressions": row["matchedExpressions"],
            })
    return {
        "recordType": "dictionaryComparison", "formatVersion": 1,
        "dictionaryVersions": [old["dictionaryVersion"], new["dictionaryVersion"]],
        "changedUnitCount": len(changed), "changedUnits": changed,
        "checks": {"loadedFromAxolDb": True, "exactRecomputeMatch": True,
                   "sameSourceForBothAnalyses": old["datasetId"] == new["datasetId"]},
    }
