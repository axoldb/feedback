from __future__ import annotations

import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any

from .axol_api import AxolClient
from .model import SchellingModel, _lists

SCHEMA_AGENT = "axol://schemas/examples.mesa-schelling/resident/1"
SCHEMA_MANIFEST = "axol://schemas/examples.mesa-schelling/checkpoint/1"
CONTRACT_ID = "axol://contracts/examples.mesa-schelling/checkpoint/1"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def save(client: AxolClient, population_id: str, parent_generation_id: str | None,
         model: SchellingModel, provenance: dict[str, Any]) -> dict[str, Any]:
    agent_hashes: dict[str, str] = {}
    for row in model.agent_rows():
        agent_hashes[row["stable_id"]] = client.insert_json(
            population_id, SCHEMA_AGENT, digest(SCHEMA_AGENT), row
        )
    manifest = {
        "kind": "mesa-schelling-checkpoint",
        "format_version": 1,
        "example_version": "1.0.0",
        "step": model.steps_completed,
        "width": model.width,
        "height": model.height,
        "torus": True,
        "density": model.density,
        "minority_fraction": model.minority_fraction,
        "threshold": model.threshold,
        "moves_total": model.moves_total,
        "random_state": _lists(model.random.getstate()),
        "numpy_rng_state": model.rng.bit_generator.state,
        "activation_base_order": [agent.stable_id for agent in model.agents],
        "stable_agent_hashes": agent_hashes,
        "runtime": {"python": sys.version.split()[0], "mesa": importlib.metadata.version("mesa")},
        "provenance": provenance,
    }
    manifest_hash = client.insert_json(population_id, SCHEMA_MANIFEST, digest(SCHEMA_MANIFEST), manifest)
    members = list(agent_hashes.values()) + [manifest_hash]
    if parent_generation_id is None:
        generation_id = client.create_population(population_id, CONTRACT_ID, digest(CONTRACT_ID), members)
    else:
        generation_id = client.publish(population_id, parent_generation_id, members,
                                       f"mesa-s{model.steps_completed}-{digest(population_id)[:12]}")
    summary = client.generation(population_id, generation_id)
    return {"population_id": population_id, "generation_id": generation_id,
            "step": model.steps_completed, "manifest_hash": manifest_hash,
            "member_hashes": sorted(set(members)), "state_root": summary["stateRootHex"]}


def restore(client: AxolClient, reference: dict[str, Any]) -> tuple[SchellingModel, dict[str, Any]]:
    population_id, generation_id = reference["population_id"], reference["generation_id"]
    if client.generation(population_id, generation_id) is None:
        raise RuntimeError("checkpoint generation no longer exists")
    manifest = client.read_json(population_id, generation_id, reference["manifest_hash"])
    rows = [client.read_json(population_id, generation_id, digest_)
            for _stable_id, digest_ in sorted(manifest["stable_agent_hashes"].items())]
    model = SchellingModel(width=manifest["width"], height=manifest["height"],
                           density=manifest["density"], minority_fraction=manifest["minority_fraction"],
                           threshold=manifest["threshold"], agents=rows, steps=manifest["step"],
                           moves_total=manifest["moves_total"], random_state=manifest["random_state"],
                           numpy_rng_state=manifest["numpy_rng_state"])
    if [agent.stable_id for agent in model.agents] != manifest["activation_base_order"]:
        raise RuntimeError("activation base order was not restored")
    return model, manifest


def write_reference(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
