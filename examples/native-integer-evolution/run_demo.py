#!/usr/bin/env python3
"""Run one public AxolDB CLI Evolution cycle over a JSON integer population."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import time
from typing import Any

PLUGIN_ID = "EvolutionaryOperator/axol/reference-increment-mutator"
PLUGIN_HASH = hashlib.sha256(b"axol-cli-reference-mutator-v1").hexdigest()
PLUGIN_OPERATOR = "axol://operators/axol/reference-increment-mutator"
DEFAULT_PRINCIPAL = "examples.native-integer/admin"
DEFAULT_POPULATION = "examples.native-integer/candidates"
DEFAULT_FORK_SEGMENT = "native-run"


class DemoError(RuntimeError):
    """A safe, actionable example failure."""


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=here / "data" / "population.json")
    parser.add_argument("--result", type=Path, default=here / "results" / "run-report.json")
    parser.add_argument("--principal", default=DEFAULT_PRINCIPAL)
    parser.add_argument("--population", default=DEFAULT_POPULATION)
    parser.add_argument("--fork-segment", default=DEFAULT_FORK_SEGMENT)
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DemoError(message)


def load_input(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "input must be a JSON object")
    require(re.fullmatch(r"[^/]+/[^/]+/[^/]+", data.get("schemaId", "")) is not None,
            "schemaId must have three slash-separated segments")
    for name in ("schemaHashHex", "contractHashHex"):
        require(re.fullmatch(r"[0-9a-fA-F]{64}", data.get(name, "")) is not None,
                f"{name} must contain exactly 64 hexadecimal characters")
    candidates = data.get("candidates")
    require(isinstance(candidates, list) and candidates, "candidates must be a non-empty array")
    for candidate in candidates:
        require(isinstance(candidate, dict), "each candidate must be an object")
        require(isinstance(candidate.get("value"), int) and not isinstance(candidate.get("value"), bool),
                "candidate value must be an integer")
        require(isinstance(candidate.get("multiplicity"), int) and candidate["multiplicity"] > 0,
                "candidate multiplicity must be a positive integer")
    evolution = data.get("evolution")
    require(isinstance(evolution, dict), "evolution must be an object")
    for name in ("targetPopulationSize", "tournamentSize"):
        require(isinstance(evolution.get(name), int) and evolution[name] > 0,
                f"evolution.{name} must be a positive integer")
    require(isinstance(evolution.get("eliteCount"), int) and evolution["eliteCount"] >= 0,
            "evolution.eliteCount must be a non-negative integer")
    for name in ("rootSeedHex", "evaluationContextHashHex"):
        require(re.fullmatch(r"[0-9a-fA-F]{64}", evolution.get(name, "")) is not None,
                f"evolution.{name} must contain exactly 64 hexadecimal characters")
    return data


def canonical_population(population: str) -> str:
    require(population.count("/") == 1 and not population.startswith("/") and not population.endswith("/"),
            "--population must have the form <namespace>/<name>")
    return f"axol://populations/{population}"


def fork_query(fork_id: str, generation_id: str | None = None) -> dict[str, Any]:
    return {
        "document": {
            "declaredParameters": [],
            "root": {
                "$kind": "scan",
                "sourceAlias": "candidates",
                "sourceScope": {
                    "$kind": "fork-generation",
                    "forkId": fork_id,
                    "forkGenerationId": generation_id,
                    "forkGenerationNumber": None,
                },
            },
        },
        "parameterValues": [],
        "pageSize": None,
    }


def normalized_rows(rows: list[dict[str, Any]]) -> list[tuple[int, int]]:
    normalized: list[tuple[int, int]] = []
    for row in rows:
        literal = row.get("value")
        require(isinstance(literal, str) and literal.startswith("int:"),
                f"expected an integer query row, got {literal!r}")
        normalized.append((int(literal[4:]), int(row["multiplicity"])))
    return sorted(normalized)


def main() -> int:
    args = parse_args()
    data = load_input(args.input)
    axol = os.environ.get("AXOL_BIN")
    require(bool(axol), "set AXOL_BIN to the public packaged axol executable")
    axol_path = Path(axol).expanduser().resolve()
    require(axol_path.is_file() and os.access(axol_path, os.X_OK), "AXOL_BIN is not executable")
    query_axol_path = Path(os.environ.get("AXOL_QUERY_BIN", str(axol_path))).expanduser().resolve()
    require(query_axol_path.is_file() and os.access(query_axol_path, os.X_OK),
            "AXOL_QUERY_BIN is not executable")
    for name in ("AXOLDB_CONNECTION_STRING", "AXOLDB_DEPLOYMENT_AUDIENCE", "AXOLDB_CURSOR_SIGNING_KEY"):
        require(bool(os.environ.get(name)), f"set {name}; see README.md")

    commands: list[str] = []

    def invoke(arguments: list[str], principal: str | None = args.principal,
               stdin_json: dict[str, Any] | None = None,
               executable: Path = axol_path) -> Any:
        command = [str(executable), *arguments, "--local", "--output", "json"]
        display = ["axol", *arguments, "--local", "--output", "json"]
        if principal is not None:
            command += ["--as", principal]
            display += ["--as", principal]
        result = subprocess.run(
            command,
            input=None if stdin_json is None else json.dumps(stdin_json),
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        commands.append(" ".join(display))
        try:
            lines = [line for line in result.stdout.splitlines() if line.strip()]
            envelope = json.loads(lines[-1])
        except json.JSONDecodeError as exc:
            detail = (result.stderr.strip() or result.stdout.strip() or "no output")[-500:]
            raise DemoError(
                f"axol returned non-JSON output for {' '.join(arguments[:2])}: {detail}"
            ) from exc
        except IndexError as exc:
            detail = (result.stderr.strip() or "no output")[-500:]
            raise DemoError(f"axol returned no JSON for {' '.join(arguments[:2])}: {detail}") from exc
        if result.returncode != 0 or envelope.get("success") is not True:
            error = envelope.get("error") or {}
            raise DemoError(f"{' '.join(arguments[:2])} failed: {error.get('code', 'unknown')} - {error.get('message', '')}")
        return envelope.get("data")

    started = time.monotonic()
    version = subprocess.run([str(axol_path), "--version"], text=True, capture_output=True,
                             timeout=30, check=True).stdout.strip()
    query_version = subprocess.run([str(query_axol_path), "--version"], text=True,
                                   capture_output=True, timeout=30, check=True).stdout.strip()
    population_ref = canonical_population(args.population)

    invoke(["security", "bootstrap", "--principal", args.principal, "--kind", "human"], principal=None)
    grants = [
        ("Insert", "Population", None),
        ("Read", "Population", population_ref),
        ("Insert", "IndividualGenotype", population_ref),
        ("Read", "IndividualGenotype", population_ref),
        ("PublishGeneration", "Population", population_ref),
        ("CreateFork", "Population", population_ref),
        ("ExecuteQuery", "Query", "query"),
    ]
    for action, resource, resource_id in grants:
        command = ["security", "grant", "--principal", args.principal,
                   "--action", action, "--resource", resource]
        if resource_id is not None:
            command += ["--resource-id", resource_id]
        invoke(command)

    members: list[str] = []
    source_values: set[int] = set()
    for candidate in data["candidates"]:
        source_values.add(candidate["value"])
        inserted = invoke([
            "genotype", "insert",
            "--schema-id", data["schemaId"],
            "--schema-hash", data["schemaHashHex"],
            "--value", f"int:{candidate['value']}",
            "--population-id", args.population,
        ])
        members.append(f"{inserted['genotypeHash']}:{candidate['multiplicity']}")

    create_args = ["population", "create", "--id", args.population,
                   "--contract-hash", data["contractHashHex"]]
    for member in members:
        create_args += ["--member", member]
    population = invoke(create_args)
    initial_generation = population["generation"]
    source_before = invoke([
        "query", "submit", "--population", args.population, "--generation", initial_generation,
    ], executable=query_axol_path)
    source_summary_before = invoke(["generation", "inspect", "--population", args.population,
                                    "--id", initial_generation])

    invoke(["plugin", "register", "--id", PLUGIN_ID, "--package-hash", PLUGIN_HASH,
            "--version", "1.0.0", "--capability", "WriteData"])
    invoke(["plugin", "approve", "--id", PLUGIN_ID, "--package-hash", PLUGIN_HASH])
    invoke(["plugin", "grant-capability", "--id", PLUGIN_ID, "--package-hash", PLUGIN_HASH,
            "--capability", "WriteData"])
    invoke(["plugin", "activate", "--id", PLUGIN_ID, "--package-hash", PLUGIN_HASH])

    fork_name = f"{args.population}/{args.fork_segment}"
    created_fork = invoke(["fork", "create", "--id", fork_name,
                           "--source-generation", initial_generation])
    fork_id = created_fork["fork"]
    for action in ("Read", "PublishGeneration", "Insert"):
        invoke(["security", "grant", "--principal", args.principal, "--action", action,
                "--resource", "Fork", "--resource-id", fork_id])

    evolution = data["evolution"]
    run = invoke([
        "evolve", "create", "--fork", fork_name,
        "--plan-id", "axol://plans/examples.native-integer/1",
        "--root-seed", evolution["rootSeedHex"],
        "--evaluation-context-hash", evolution["evaluationContextHashHex"],
    ])
    run_id = run["run"]
    require(run_id.startswith("evolution-run-"), "evolve create did not return an EvolutionRunId")
    invoke(["evolve", "start", "--run", run_id, "--worker", "native-integer-example"])
    step = invoke([
        "evolve", "step", "--run", run_id,
        "--evolution-step", "1", "--candidate-generation", "0",
        "--mutation-plugin-id", PLUGIN_ID, "--mutation-package-hash", PLUGIN_HASH,
        "--target-population-size", str(evolution["targetPopulationSize"]),
        "--elite-count", str(evolution["eliteCount"]),
        "--tournament-size", str(evolution["tournamentSize"]),
    ])

    fork_after = invoke(["fork", "inspect", "--id", fork_name])
    child_query = invoke(["query", "submit", "--input", "-"], stdin_json=fork_query(fork_id),
                         executable=query_axol_path)
    lineage = invoke(["fork", "lineage", "--id", fork_name, "--run", run_id])
    source_after = invoke([
        "query", "submit", "--population", args.population, "--generation", initial_generation,
    ], executable=query_axol_path)
    source_summary_after = invoke(["generation", "inspect", "--population", args.population,
                                   "--id", initial_generation])
    population_after = invoke(["population", "describe", "--id", args.population])

    before_rows = normalized_rows(source_before["rows"])
    after_rows = normalized_rows(source_after["rows"])
    child_rows = normalized_rows(child_query["rows"])
    require(before_rows == after_rows, "source Generation membership changed")
    require(source_summary_before == source_summary_after, "source Generation summary changed")
    require(population_after["currentGeneration"] == initial_generation and
            population_after["currentGenerationNumber"] == 0,
            "source Population advanced unexpectedly")
    require(fork_after["currentForkGenerationNumber"] == 1 and fork_after["historyCount"] == 2,
            "Evolution did not publish exactly one successor Fork Generation")
    require(step["publishedGeneration"] == fork_after["currentForkGeneration"],
            "step output and Fork head disagree")
    require(sum(multiplicity for _, multiplicity in child_rows) == evolution["targetPopulationSize"],
            "successor membership size differs from targetPopulationSize")
    require(all(value - 1 in source_values for value, _ in child_rows),
            "a successor value is not the reference mutator's parent + 1 result")
    require(isinstance(lineage, list) and lineage, "native lineage is empty")
    require(all(row.get("operator") == PLUGIN_OPERATOR and row.get("lineageKind") == "mutation"
                for row in lineage), "lineage does not identify the built-in mutation operator")

    report = {
        "schemaVersion": 1,
        "passed": True,
        "axolVersion": version,
        "queryAxolVersion": query_version,
        "platform": {"system": platform.system(), "machine": platform.machine(),
                     "python": platform.python_version()},
        "publicPath": "local Application-backed axol CLI",
        "inputFile": str(args.input.name),
        "population": args.population,
        "sourceGeneration": initial_generation,
        "sourceMembershipBefore": before_rows,
        "sourceMembershipAfter": after_rows,
        "fork": fork_id,
        "evolutionRunId": run_id,
        "publishedForkGeneration": step["publishedGeneration"],
        "resultMembership": child_rows,
        "lineage": lineage,
        "checks": {
            "inputImported": True,
            "nativeMutationExecuted": True,
            "childValuesAreSelectedParentPlusOne": True,
            "lineageReturned": True,
            "sourcePopulationPreserved": True,
            "sourceReloadMatches": True,
        },
        "limitations": {
            "crossover": "BLOCKED: no public built-in crossover operator or external plugin loading path",
            "remoteEvolution": "BLOCKED: Server v1 does not expose Evolution or plugin lifecycle operations",
            "determinismClaimed": False,
        },
        "commands": commands,
        "durationSeconds": round(time.monotonic() - started, 2),
        "secretsRetained": False,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": True, "result": str(args.result),
                      "evolutionRunId": run_id, "childMembership": child_rows}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DemoError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        raise SystemExit(1)
