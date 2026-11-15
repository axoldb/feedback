from __future__ import annotations

import hashlib
import importlib.metadata
import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np

from .axol_api import AxolClient, canonical_bytes
from .model import candidate_payload, toolbox_for

SCHEMA_CANDIDATE = "axol://schemas/examples.deap-knapsack/candidate/1"
SCHEMA_MANIFEST = "axol://schemas/examples.deap-knapsack/checkpoint/1"
CONTRACT_ID = "axol://contracts/examples.deap-knapsack/checkpoint/1"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _lists(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_lists(item) for item in value]
    if isinstance(value, list):
        return [_lists(item) for item in value]
    if isinstance(value, dict):
        return {key: _lists(item) for key, item in value.items()}
    return value


def _tuples(value: Any) -> Any:
    return tuple(_tuples(item) for item in value) if isinstance(value, list) else value


def save(
    client: AxolClient,
    population_id: str,
    parent_generation_id: str | None,
    population: list[Any],
    generation: int,
    numpy_rng: np.random.Generator,
    parameters: dict[str, Any],
    dataset_hash: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    candidate_hashes: list[str] = []
    for individual in population:
        candidate_hashes.append(client.insert_json(
            population_id, SCHEMA_CANDIDATE, digest(SCHEMA_CANDIDATE), candidate_payload(individual)
        ))
    manifest = {
        "kind": "deap-knapsack-checkpoint",
        "format_version": 1,
        "example_version": "1.0.0",
        "generation": generation,
        "ordered_candidate_hashes": candidate_hashes,
        "python_random_state": _lists(random.getstate()),
        "numpy_rng_state": _lists(numpy_rng.bit_generator.state),
        "parameters": parameters,
        "dataset_sha256": dataset_hash,
        "runtime": {
            "python": sys.version.split()[0],
            "deap": importlib.metadata.version("deap"),
            "numpy": importlib.metadata.version("numpy"),
        },
        "provenance": provenance,
    }
    manifest_hash = client.insert_json(
        population_id, SCHEMA_MANIFEST, digest(SCHEMA_MANIFEST), manifest
    )
    members = candidate_hashes + [manifest_hash]
    if parent_generation_id is None:
        generation_id = client.create_population(population_id, CONTRACT_ID, digest(CONTRACT_ID), members)
    else:
        generation_id = client.publish(
            population_id, parent_generation_id, members, f"deap-g{generation}-{digest(population_id)[:12]}"
        )
    summary = client.generation(population_id, generation_id)
    return {
        "population_id": population_id,
        "generation_id": generation_id,
        "generation": generation,
        "manifest_hash": manifest_hash,
        "member_hashes": sorted(set(members)),
        "state_root": summary["stateRootHex"],
    }


def restore(client: AxolClient, reference: dict[str, Any], dataset: dict[str, Any]) -> tuple[list[Any], np.random.Generator, dict[str, Any]]:
    population_id = reference["population_id"]
    generation_id = reference["generation_id"]
    if client.generation(population_id, generation_id) is None:
        raise RuntimeError("checkpoint generation no longer exists")
    manifest = client.read_json(population_id, generation_id, reference["manifest_hash"])
    if manifest["dataset_sha256"] != hashlib.sha256(canonical_bytes(dataset)).hexdigest():
        raise RuntimeError("dataset identity differs from checkpoint")
    unique = set(manifest["ordered_candidate_hashes"])
    payloads = {digest_: client.read_json(population_id, generation_id, digest_) for digest_ in unique}
    numpy_rng = np.random.default_rng()
    numpy_rng.bit_generator.state = manifest["numpy_rng_state"]
    toolbox = toolbox_for(dataset, numpy_rng)
    population = []
    for digest_ in manifest["ordered_candidate_hashes"]:
        payload = payloads[digest_]
        individual = toolbox.individual()
        individual[:] = payload["bits"]
        individual.fitness.values = tuple(payload["fitness"])
        population.append(individual)
    random.setstate(_tuples(manifest["python_random_state"]))
    return population, numpy_rng, manifest


def write_reference(path: Path, reference: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(reference, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
