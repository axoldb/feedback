from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
from deap import base, creator, tools


def load_dataset(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def toolbox_for(dataset: dict[str, Any], numpy_rng: np.random.Generator) -> base.Toolbox:
    if not hasattr(creator, "KnapsackFitness"):
        creator.create("KnapsackFitness", base.Fitness, weights=(1.0,))
    if not hasattr(creator, "KnapsackIndividual"):
        creator.create("KnapsackIndividual", list, fitness=creator.KnapsackFitness)

    def evaluate(individual: list[int]) -> tuple[float]:
        weight = sum(item["weight"] * selected for item, selected in zip(dataset["items"], individual))
        value = sum(item["value"] * selected for item, selected in zip(dataset["items"], individual))
        return (float(value if weight <= dataset["capacity"] else 0),)

    toolbox = base.Toolbox()
    toolbox.register("attr_bool", lambda: int(numpy_rng.integers(0, 2)))
    toolbox.register("individual", tools.initRepeat, creator.KnapsackIndividual, toolbox.attr_bool,
                     n=len(dataset["items"]))
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", evaluate)
    toolbox.register("mate", tools.cxTwoPoint)
    toolbox.register("mutate", tools.mutFlipBit, indpb=0.05)
    toolbox.register("select", tools.selTournament, tournsize=3)
    toolbox.register("clone", copy.deepcopy)
    return toolbox


def evaluate_missing(population: list[Any], toolbox: base.Toolbox) -> None:
    for individual in population:
        if not individual.fitness.valid:
            individual.fitness.values = toolbox.evaluate(individual)


def advance(population: list[Any], toolbox: base.Toolbox, cxpb: float, mutpb: float) -> list[Any]:
    offspring = list(map(toolbox.clone, toolbox.select(population, len(population))))
    for left, right in zip(offspring[::2], offspring[1::2]):
        if random.random() < cxpb:
            toolbox.mate(left, right)
            del left.fitness.values, right.fitness.values
    for individual in offspring:
        if random.random() < mutpb:
            toolbox.mutate(individual)
            del individual.fitness.values
    evaluate_missing(offspring, toolbox)
    return offspring


def candidate_payload(individual: Any) -> dict[str, Any]:
    return {"bits": list(map(int, individual)), "fitness": list(map(float, individual.fitness.values))}


def metrics(population: list[Any], generation: int) -> dict[str, float | int]:
    values = [float(ind.fitness.values[0]) for ind in population]
    unique = {tuple(ind) for ind in population}
    return {
        "generation": generation,
        "best": max(values),
        "average": sum(values) / len(values),
        "diversity": len(unique) / len(population),
    }


def canonical_population(population: list[Any]) -> list[dict[str, Any]]:
    return [candidate_payload(individual) for individual in population]
