from __future__ import annotations

import copy
import hashlib
import importlib.resources
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .axol_api import AxolClient, canonical_bytes
from .checkpoint import restore, save, write_reference
from .model import advance, canonical_population, evaluate_missing, load_dataset, metrics, toolbox_for

BASELINE = "axol://populations/examples.deap-knapsack/baseline"
BRANCH_A = "axol://populations/examples.deap-knapsack/branch-a"
BRANCH_B = "axol://populations/examples.deap-knapsack/branch-b"


def _plot(result: dict, output: Path) -> None:
    baseline = result["baseline_history"]
    branches = [("A: mutation 0.20", result["branch_a"], "tab:blue"),
                ("B: mutation 0.60", result["branch_b"], "tab:orange")]
    figure, axes = plt.subplots(1, 3, figsize=(13, 4))
    for index, field in enumerate(("best", "average", "diversity")):
        axes[index].plot([row["generation"] for row in baseline],
                         [row[field] for row in baseline], color="black", label="shared baseline")
        for label, branch, color in branches:
            axes[index].plot([row["generation"] for row in branch["history"]],
                             [row[field] for row in branch["history"]], color=color, label=label)
        axes[index].set(title=field.title(), xlabel="Generation")
        axes[index].grid(alpha=0.25)
    axes[0].set_ylabel("Fitness value")
    axes[2].set_ylabel("Unique bit strings / population size")
    axes[0].legend(fontsize=8)
    figure.suptitle("One AxolDB checkpoint, two DEAP continuations (one seed; not a ranking)")
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def run(output_dir: Path) -> dict:
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = Path(os.environ["AXOL_EXAMPLE_DATASET"]) if os.environ.get("AXOL_EXAMPLE_DATASET") else Path(str(importlib.resources.files("deap_axol").joinpath("data/items.json")))
    dataset = load_dataset(dataset_path)
    dataset_hash = hashlib.sha256(canonical_bytes(dataset)).hexdigest()
    parameters = {
        "seed": 20261007,
        "population_size": 40,
        "checkpoint_generation": 20,
        "final_generation": 50,
        "crossover_probability": 0.70,
        "mutation_probability": 0.20,
        "gene_mutation_probability": 0.05,
        "tournament_size": 3,
    }
    namespace = os.environ.get("AXOL_EXAMPLE_NAMESPACE", "examples.deap-knapsack")
    baseline = f"axol://populations/{namespace}/baseline"
    branch_a_id = f"axol://populations/{namespace}/branch-a"
    branch_b_id = f"axol://populations/{namespace}/branch-b"
    random.seed(parameters["seed"])
    numpy_rng = np.random.default_rng(parameters["seed"])
    toolbox = toolbox_for(dataset, numpy_rng)
    population = toolbox.population(n=parameters["population_size"])
    evaluate_missing(population, toolbox)
    client = AxolClient.from_environment()
    version = client.version()
    provenance = {"mode": "application-level", "native_fork": False, "source": None}
    history = [metrics(population, 0)]
    reference = save(client, baseline, None, population, 0, numpy_rng, parameters,
                     dataset_hash, provenance)
    parent = reference["generation_id"]
    for generation in range(1, 21):
        population = advance(population, toolbox, parameters["crossover_probability"],
                             parameters["mutation_probability"])
        history.append(metrics(population, generation))
        reference = save(client, baseline, parent, population, generation, numpy_rng,
                         parameters, dataset_hash, provenance)
        parent = reference["generation_id"]
    checkpoint_path = output_dir / "checkpoint-ref.json"
    write_reference(checkpoint_path, reference)
    checkpoint_summary_before = client.generation(baseline, reference["generation_id"])
    checkpoint_manifest_before = client.read_json(baseline, reference["generation_id"],
                                                  reference["manifest_hash"])

    control_population = copy.deepcopy(population)
    control_numpy = np.random.default_rng()
    control_numpy.bit_generator.state = copy.deepcopy(numpy_rng.bit_generator.state)
    control_toolbox = toolbox_for(dataset, control_numpy)
    for _generation in range(21, 51):
        control_population = advance(control_population, control_toolbox,
                                     parameters["crossover_probability"], 0.20)
    continuous_final = canonical_population(control_population)

    for name, population_id, mutation in (
        ("branch-a", branch_a_id, 0.20), ("branch-b", branch_b_id, 0.60)
    ):
        subprocess.run([
            sys.executable, "-m", "deap_axol.worker", "--checkpoint", str(checkpoint_path),
            "--dataset", str(dataset_path), "--population-id", population_id,
            "--mutation", str(mutation), "--output", str(output_dir / f"{name}.json"),
        ], check=True, env=os.environ.copy())
    branch_a = json.loads((output_dir / "branch-a.json").read_text(encoding="utf-8"))
    branch_b = json.loads((output_dir / "branch-b.json").read_text(encoding="utf-8"))
    if branch_a["final_population"] != continuous_final:
        raise AssertionError("uninterrupted and restored branch A populations differ")

    restored, _, manifest = restore(client, reference, dataset)
    if canonical_population(restored) != canonical_population(population):
        raise AssertionError("checkpoint membership, order, fitness, or candidate values differ")
    checkpoint_summary_after = client.generation(baseline, reference["generation_id"])
    checkpoint_manifest_after = client.read_json(baseline, reference["generation_id"],
                                                 reference["manifest_hash"])
    if checkpoint_summary_before != checkpoint_summary_after or checkpoint_manifest_before != checkpoint_manifest_after:
        raise AssertionError("source checkpoint changed after branch continuation")
    if branch_a["initial_source"] != branch_b["initial_source"] or manifest["generation"] != 20:
        raise AssertionError("branches did not restore the same generation-20 checkpoint")

    result = {
        "example": "deap-knapsack",
        "axoldb_version": version,
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "lineage_mode": "application-level provenance (two Populations; not native Fork)",
        "population_ids": {"baseline": baseline, "branch_a": branch_a_id, "branch_b": branch_b_id},
        "checkpoint": reference,
        "baseline_history": history,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "checks": {
            "restored_from_axoldb": True,
            "uninterrupted_equals_restored": True,
            "compared": "ordered candidate bits, fitness values, membership hashes, and final metrics",
            "same_branch_start": True,
            "source_checkpoint_unchanged": True,
            "earlier_generation_preserved": client.generation(baseline, reference["generation_id"]) is not None,
        },
        "duration_seconds": time.perf_counter() - started,
        "scope": {"population_size": 40, "saved_baseline_generations": 21,
                  "saved_generations_per_branch": 31},
        "limitations": ["One seed demonstrates the workflow; it does not establish strategy superiority.",
                        "Windows execution was not run."],
    }
    (output_dir / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    _plot(result, output_dir / "comparison.png")
    print(json.dumps({
        "checkpoint_generation_id": reference["generation_id"],
        "baseline_population_id": baseline,
        "branch_a_population_id": branch_a_id,
        "branch_b_population_id": branch_b_id,
        "branch_a_final": branch_a["final_metrics"],
        "branch_b_final": branch_b["final_metrics"],
        "uninterrupted_equals_restored": True,
        "native_fork": False,
    }, indent=2))
    return result


def main() -> None:
    run(Path(os.environ.get("AXOL_EXAMPLE_OUTPUT", "results")))


if __name__ == "__main__":
    main()
