#!/usr/bin/env python3
"""Run one native AxolDB binary midpoint crossover and verify durable lineage."""

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


PLUGIN_ID = "EvolutionaryOperator/axol/reference-binary-midpoint-crossover"
PLUGIN_HASH = hashlib.sha256(b"axol-cli-reference-binary-midpoint-crossover-v1").hexdigest()
PLUGIN_OPERATOR = "axol://operators/axol/reference-binary-midpoint-crossover"
DEFAULT_PRINCIPAL = "examples.native-binary/admin"
DEFAULT_POPULATION = "examples.native-binary/candidates"
DEFAULT_FORK_SEGMENT = "midpoint-run"


class DemoError(RuntimeError):
    """A safe, actionable example failure."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DemoError(message)


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=here / "data" / "population.json")
    parser.add_argument("--result", type=Path, default=here / "results" / "run-report.json")
    parser.add_argument("--reload-result", type=Path, default=here / "results" / "reload-report.json")
    parser.add_argument("--principal", default=DEFAULT_PRINCIPAL)
    parser.add_argument("--population", default=DEFAULT_POPULATION)
    parser.add_argument("--fork-segment", default=DEFAULT_FORK_SEGMENT)
    parser.add_argument("--instance-root", type=Path, required=True)
    return parser.parse_args()


def load_input(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "input must be a JSON object")
    require(re.fullmatch(r"[^/]+/[^/]+/[^/]+", data.get("schemaId", "")) is not None,
            "schemaId must have three slash-separated segments")
    for name in ("schemaHashHex", "contractHashHex"):
        require(re.fullmatch(r"[0-9a-fA-F]{64}", data.get(name, "")) is not None,
                f"{name} must contain exactly 64 hexadecimal characters")
    candidates = data.get("candidates")
    require(isinstance(candidates, list) and len(candidates) == 2,
            "candidates must contain exactly two entries")
    lengths: set[int] = set()
    values: set[str] = set()
    for candidate in candidates:
        value = candidate.get("valueHex", "")
        require(re.fullmatch(r"(?:[0-9a-fA-F]{2}){2,}", value) is not None,
                "each valueHex must contain at least two complete bytes")
        require(candidate.get("multiplicity") == 1, "each input multiplicity must be exactly one")
        lengths.add(len(value))
        values.add(value.lower())
    require(len(lengths) == 1, "binary parents must have equal byte length")
    require(len(values) == 2, "the example requires two different binary values")
    evolution = data.get("evolution")
    require(isinstance(evolution, dict), "evolution must be an object")
    require(evolution.get("targetPopulationSize") == 1, "targetPopulationSize must be one")
    require(evolution.get("eliteCount") == 0, "eliteCount must be zero")
    require(evolution.get("tournamentSize") == 1,
            "tournamentSize one makes both real bounded tournaments observable with two inputs")
    for name in ("rootSeedHex", "evaluationContextHashHex"):
        require(re.fullmatch(r"[0-9a-fA-F]{64}", evolution.get(name, "")) is not None,
                f"evolution.{name} must contain exactly 64 hexadecimal characters")
    return data


def canonical_population(population: str) -> str:
    require(population.count("/") == 1 and not population.startswith("/")
            and not population.endswith("/"),
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


def normalized_binary_rows(rows: list[dict[str, Any]]) -> list[tuple[str, int]]:
    normalized: list[tuple[str, int]] = []
    for row in rows:
        literal = row.get("value")
        require(isinstance(literal, str) and literal.startswith("bin:hex:"),
                f"expected a binary query row, got {literal!r}")
        normalized.append((literal[8:].lower(), int(row["multiplicity"])))
    return sorted(normalized)


def midpoint(parent_a_hex: str, parent_b_hex: str) -> tuple[int, str]:
    parent_a = bytes.fromhex(parent_a_hex)
    parent_b = bytes.fromhex(parent_b_hex)
    require(len(parent_a) == len(parent_b) and len(parent_a) >= 2,
            "midpoint parents must have equal length of at least two bytes")
    cut = len(parent_a) // 2
    return cut, (parent_a[:cut] + parent_b[cut:]).hex()


def main() -> int:
    args = parse_args()
    data = load_input(args.input)
    axol = os.environ.get("AXOL_BIN")
    require(bool(axol), "set AXOL_BIN to the public packaged axol executable")
    axol_path = Path(axol).expanduser().resolve()
    require(axol_path.is_file() and os.access(axol_path, os.X_OK), "AXOL_BIN is not executable")
    bundle_root = axol_path.parent.parent
    instance_root = args.instance_root.expanduser().resolve()
    for name in ("AXOLDB_CONNECTION_STRING", "AXOLDB_DEPLOYMENT_AUDIENCE", "AXOLDB_CURSOR_SIGNING_KEY"):
        require(bool(os.environ.get(name)), f"set {name}; see README.md")

    commands: list[str] = []

    def invoke(arguments: list[str], principal: str | None = args.principal,
               stdin_json: dict[str, Any] | None = None) -> Any:
        command = [str(axol_path), *arguments, "--local", "--output", "json"]
        display = ["axol", *arguments, "--local", "--output", "json"]
        if principal is not None:
            command += ["--as", principal]
            display += ["--as", principal]
        result = subprocess.run(command, input=None if stdin_json is None else json.dumps(stdin_json),
                                text=True, capture_output=True, timeout=120, check=False)
        commands.append(" ".join(display))
        try:
            envelope = json.loads([line for line in result.stdout.splitlines() if line.strip()][-1])
        except (json.JSONDecodeError, IndexError) as exc:
            detail = (result.stderr.strip() or result.stdout.strip() or "no output")[-500:]
            raise DemoError(f"axol returned invalid output for {' '.join(arguments[:2])}: {detail}") from exc
        if result.returncode != 0 or envelope.get("success") is not True:
            error = envelope.get("error") or {}
            raise DemoError(f"{' '.join(arguments[:2])} failed: {error.get('code', 'unknown')} - {error.get('message', '')}")
        return envelope.get("data")

    def invoke_server(action: str) -> Any:
        command = [str(axol_path), "server", action, "--instance-root", str(instance_root),
                   "--bundle-root", str(bundle_root), "--output", "json"]
        result = subprocess.run(command, text=True, capture_output=True, timeout=180, check=False)
        commands.append(f"axol server {action} --instance-root <isolated-instance> "
                        "--bundle-root <local-qualification-bundle> --output json")
        try:
            envelope = json.loads([line for line in result.stdout.splitlines() if line.strip()][-1])
        except (json.JSONDecodeError, IndexError) as exc:
            detail = (result.stderr.strip() or result.stdout.strip() or "no output")[-500:]
            raise DemoError(f"axol server {action} returned invalid output: {detail}") from exc
        if result.returncode != 0 or envelope.get("success") is not True:
            error = envelope.get("error") or {}
            raise DemoError(f"axol server {action} failed: {error.get('code', 'unknown')} - {error.get('message', '')}")
        return envelope.get("data")

    started = time.monotonic()
    version = subprocess.run([str(axol_path), "--version"], text=True, capture_output=True,
                             timeout=30, check=True).stdout.strip()
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
    genotype_values: dict[str, str] = {}
    input_membership: list[tuple[str, int]] = []
    for candidate in data["candidates"]:
        value_hex = candidate["valueHex"].lower()
        inserted = invoke([
            "genotype", "insert", "--schema-id", data["schemaId"],
            "--schema-hash", data["schemaHashHex"], "--value", f"bin:hex:{value_hex}",
            "--population-id", args.population,
        ])
        genotype_hash = inserted["genotypeHash"]
        genotype_values[genotype_hash] = value_hex
        members.append(f"{genotype_hash}:{candidate['multiplicity']}")
        input_membership.append((value_hex, candidate["multiplicity"]))

    create_args = ["population", "create", "--id", args.population,
                   "--contract-hash", data["contractHashHex"]]
    for member in members:
        create_args += ["--member", member]
    population = invoke(create_args)
    initial_generation = population["generation"]
    source_before = invoke(["query", "submit", "--population", args.population,
                            "--generation", initial_generation])
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
        "--plan-id", "axol://plans/examples.native-binary/1",
        "--root-seed", evolution["rootSeedHex"],
        "--evaluation-context-hash", evolution["evaluationContextHashHex"],
        "--variation-kind", "crossover", "--crossover-plugin-id", PLUGIN_ID,
        "--crossover-package-hash", PLUGIN_HASH,
    ])
    run_id = run["run"]
    require(run_id.startswith("evolution-run-"), "evolve create did not return an EvolutionRunId")
    invoke(["evolve", "start", "--run", run_id, "--worker", "native-binary-example"])
    step = invoke([
        "evolve", "step", "--run", run_id, "--evolution-step", "1",
        "--candidate-generation", "0", "--variation-kind", "crossover",
        "--crossover-plugin-id", PLUGIN_ID, "--crossover-package-hash", PLUGIN_HASH,
        "--target-population-size", "1", "--elite-count", "0",
        "--tournament-size", "1", "--max-generations", "1",
    ])

    fork_after = invoke(["fork", "inspect", "--id", fork_name])
    child_query = invoke(["query", "submit", "--input", "-"], stdin_json=fork_query(fork_id))
    lineage_rows = invoke(["fork", "lineage", "--id", fork_name, "--run", run_id])
    source_after = invoke(["query", "submit", "--population", args.population,
                           "--generation", initial_generation])
    source_summary_after = invoke(["generation", "inspect", "--population", args.population,
                                   "--id", initial_generation])
    population_after = invoke(["population", "describe", "--id", args.population])

    before_rows = normalized_binary_rows(source_before["rows"])
    after_rows = normalized_binary_rows(source_after["rows"])
    child_rows = normalized_binary_rows(child_query["rows"])
    require(before_rows == sorted(input_membership) == after_rows, "source membership changed")
    require(source_summary_before == source_summary_after, "source Generation summary changed")
    require(population_after["currentGeneration"] == initial_generation
            and population_after["currentGenerationNumber"] == 0,
            "source Population advanced unexpectedly")
    require(step.get("variationKind") == "crossover", "step did not report crossover")
    require(fork_after["currentForkGenerationNumber"] == 1 and fork_after["historyCount"] == 2,
            "Evolution did not publish exactly one successor Fork Generation")
    require(step["publishedGeneration"] == fork_after["currentForkGeneration"],
            "step output and Fork head disagree")
    require(len(lineage_rows) == 1, "expected exactly one producing lineage record")
    lineage = lineage_rows[0]
    parents = lineage.get("parentReferences")
    require(lineage.get("formatVersion") == 2 and lineage.get("lineageKind") == "crossover",
            "lineage is not crossover v2")
    require(lineage.get("operatorId") == PLUGIN_OPERATOR
            and lineage.get("operatorVersion") == "1.0.0"
            and lineage.get("operatorPackageHash") == PLUGIN_HASH,
            "lineage operator binding differs from the invoked binding")
    require(isinstance(lineage.get("publicationOperationId"), str)
            and isinstance(lineage.get("derivedSeed"), str)
            and lineage.get("outputOrdinal") == 0,
            "lineage lacks publication/seed/output coordinates")
    require(isinstance(parents, list) and len(parents) == 2,
            "lineage does not expose exactly two parents")
    require(parents[0].get("parentOrdinal") == 0 and parents[0].get("parentRole") == "parent-a"
            and parents[1].get("parentOrdinal") == 1 and parents[1].get("parentRole") == "parent-b",
            "lineage parent order/roles are not A then B")
    require(parents[0].get("parentCandidateInstanceId") != parents[1].get("parentCandidateInstanceId"),
            "the two tournaments selected the same candidate instance")
    parent_a = genotype_values[parents[0]["parentGenotypeHash"]]
    parent_b = genotype_values[parents[1]["parentGenotypeHash"]]
    cut, expected_child = midpoint(parent_a, parent_b)
    require(child_rows == [(expected_child, 1)], "published child does not match recorded A/B midpoint")
    require(re.fullmatch(r"[0-9a-f]{64}", lineage.get("outputGenotypeHash", "")) is not None,
            "lineage lacks the canonical child genotype hash")

    invoke_server("stop")
    invoke_server("start")
    restart_status = invoke_server("status")
    require(restart_status.get("state") == "Ready", "managed Server is not Ready after restart")
    source_reloaded = invoke(["query", "submit", "--population", args.population,
                              "--generation", initial_generation])
    child_reloaded = invoke(["query", "submit", "--input", "-"],
                            stdin_json=fork_query(fork_id, step["publishedGeneration"]))
    fork_reloaded = invoke(["fork", "inspect", "--id", fork_name])
    lineage_reloaded = invoke(["fork", "lineage", "--id", fork_name, "--run", run_id])
    population_reloaded = invoke(["population", "describe", "--id", args.population])
    require(normalized_binary_rows(source_reloaded["rows"]) == before_rows,
            "source membership changed after restart")
    require(normalized_binary_rows(child_reloaded["rows"]) == child_rows,
            "result membership changed after restart")
    require(fork_reloaded["currentForkGeneration"] == step["publishedGeneration"],
            "Fork head changed after restart")
    require(lineage_reloaded == lineage_rows, "lineage changed after restart")
    require(population_reloaded["currentGeneration"] == initial_generation,
            "source Population changed after restart")

    provenance = {
        "availability": "local WP-0096 qualification bundle; not a public release package",
        "runtimeIdentifier": "linux-x64" if platform.system() == "Linux" and platform.machine() == "x86_64" else "unrecorded",
        "sourceCommit": os.environ.get("AXOL_PRODUCT_SOURCE_COMMIT"),
        "bundleManifestSha256": os.environ.get("AXOL_BUNDLE_MANIFEST_SHA256"),
        "bundleArchiveSha256": os.environ.get("AXOL_BUNDLE_SHA256"),
    }
    report = {
        "schemaVersion": 1,
        "passed": True,
        "axolVersion": version,
        "singlePackage": True,
        "buildProvenance": provenance,
        "platform": {"system": platform.system(), "machine": platform.machine(),
                     "python": platform.python_version()},
        "publicPath": "local Application-backed axol CLI",
        "inputFile": args.input.name,
        "population": args.population,
        "sourceGeneration": initial_generation,
        "sourceMembershipBefore": before_rows,
        "sourceMembershipAfter": after_rows,
        "inputGenotypes": genotype_values,
        "fork": fork_id,
        "evolutionRunId": run_id,
        "publishedForkGeneration": step["publishedGeneration"],
        "resultMembership": child_rows,
        "actualCombination": {
            "parentAHex": parent_a,
            "parentBHex": parent_b,
            "cutByteOffset": cut,
            "childHex": expected_child,
        },
        "lineage": lineage_rows,
        "checks": {
            "inputImported": True,
            "twoRealBoundedTournaments": True,
            "distinctParentCandidateInstances": True,
            "nativeCrossoverExecuted": True,
            "childMatchesRecordedParentOrder": True,
            "atomicLineageAndMembershipVisible": True,
            "sourcePopulationPreserved": True,
            "sourceReloadMatches": True,
            "forkHeadReloadMatches": True,
            "lineageReloadMatches": True,
            "managedStopStartObserved": True,
        },
        "limitations": {
            "remoteEvolution": "BLOCKED: Server v1 does not expose Evolution or plugin lifecycle operations",
            "customPluginLoading": "not demonstrated; the operator is built in",
            "determinismClaimedAcrossRunIds": False,
        },
        "commands": commands,
        "durationSeconds": round(time.monotonic() - started, 2),
        "secretsRetained": False,
    }
    reload_report = {
        "schemaVersion": 1,
        "passed": True,
        "singlePackage": True,
        "axolVersion": version,
        "managedRestart": True,
        "managedStatusAfterRestart": {
            key: restart_status.get(key)
            for key in ("state", "serverVersion", "postgresqlVersion", "failureCode")
        },
        "sourceMembershipReloaded": normalized_binary_rows(source_reloaded["rows"]),
        "resultMembershipReloaded": normalized_binary_rows(child_reloaded["rows"]),
        "forkGenerationReloaded": fork_reloaded["currentForkGeneration"],
        "lineageReloaded": lineage_reloaded,
        "buildProvenance": provenance,
        "secretsRetained": False,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.reload_result.parent.mkdir(parents=True, exist_ok=True)
    args.reload_result.write_text(json.dumps(reload_report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": True, "evolutionRunId": run_id,
                      "actualCombination": report["actualCombination"],
                      "resultMembership": child_rows, "singlePackage": True}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DemoError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        raise SystemExit(1)
