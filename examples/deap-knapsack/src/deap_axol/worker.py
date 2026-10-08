from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .axol_api import AxolClient, canonical_bytes
from .checkpoint import restore, save
from .model import advance, canonical_population, load_dataset, metrics, toolbox_for


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--population-id", required=True)
    parser.add_argument("--mutation", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    client = AxolClient.from_environment()
    dataset = load_dataset(args.dataset)
    reference = json.loads(args.checkpoint.read_text(encoding="utf-8"))
    population, numpy_rng, source_manifest = restore(client, reference, dataset)
    parameters = dict(source_manifest["parameters"])
    parameters["mutation_probability"] = args.mutation
    provenance = {
        "mode": "application-level",
        "source_population_id": reference["population_id"],
        "source_generation_id": reference["generation_id"],
        "source_state_root": reference["state_root"],
        "native_fork": False,
    }
    dataset_hash = hashlib.sha256(canonical_bytes(dataset)).hexdigest()
    history = [metrics(population, 20)]
    branch_ref = save(client, args.population_id, None, population, 20, numpy_rng,
                      parameters, dataset_hash, provenance)
    parent = branch_ref["generation_id"]
    toolbox = toolbox_for(dataset, numpy_rng)
    for generation in range(21, 51):
        population = advance(population, toolbox, parameters["crossover_probability"], args.mutation)
        history.append(metrics(population, generation))
        branch_ref = save(client, args.population_id, parent, population, generation, numpy_rng,
                          parameters, dataset_hash, provenance)
        parent = branch_ref["generation_id"]
    result = {
        "population_id": args.population_id,
        "initial_source": reference,
        "final_reference": branch_ref,
        "history": history,
        "final_population": canonical_population(population),
        "final_metrics": history[-1],
        "mutation_probability": args.mutation,
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
