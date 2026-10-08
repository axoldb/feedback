import json
import random
from pathlib import Path

import numpy as np

from deap_axol.model import advance, canonical_population, evaluate_missing, load_dataset, toolbox_for


def test_model_is_deterministic() -> None:
    dataset = load_dataset(Path(__file__).parents[1] / "data/items.json")
    snapshots = []
    for _ in range(2):
        random.seed(123)
        rng = np.random.default_rng(123)
        toolbox = toolbox_for(dataset, rng)
        population = toolbox.population(n=12)
        evaluate_missing(population, toolbox)
        for _generation in range(4):
            population = advance(population, toolbox, 0.7, 0.2)
        snapshots.append(json.dumps(canonical_population(population), sort_keys=True))
    assert snapshots[0] == snapshots[1]


def test_dataset_capacity_and_identity() -> None:
    dataset = load_dataset(Path(__file__).parents[1] / "data/items.json")
    assert dataset["capacity"] == 45
    assert len({item["id"] for item in dataset["items"]}) == len(dataset["items"])
