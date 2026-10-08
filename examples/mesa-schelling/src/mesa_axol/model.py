from __future__ import annotations

from typing import Any

import mesa
from mesa.space import SingleGrid


class Resident(mesa.Agent):
    def __init__(self, model: SchellingModel, stable_id: str, group: int) -> None:
        super().__init__(model)
        self.stable_id = stable_id
        self.group = group

    def same_neighbor_fraction(self) -> float:
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, include_center=False)
        if not neighbors:
            return 1.0
        return sum(agent.group == self.group for agent in neighbors) / len(neighbors)

    def is_satisfied(self) -> bool:
        return self.same_neighbor_fraction() >= self.model.threshold

    def step(self) -> None:
        self.model.activation_trace.append(self.stable_id)
        if not self.is_satisfied() and self.model.grid.exists_empty_cells():
            self.model.grid.move_to_empty(self)
            self.model.moves_total += 1


class SchellingModel(mesa.Model):
    def __init__(
        self,
        width: int = 10,
        height: int = 10,
        density: float = 0.80,
        minority_fraction: float = 0.40,
        threshold: float = 0.50,
        seed: int = 20261007,
        agents: list[dict[str, Any]] | None = None,
        steps: int = 0,
        moves_total: int = 0,
        random_state: object | None = None,
        numpy_rng_state: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(rng=seed)
        self.width = width
        self.height = height
        self.density = density
        self.minority_fraction = minority_fraction
        self.threshold = threshold
        self.grid = SingleGrid(width, height, torus=True)
        self.steps_completed = steps
        self.moves_total = moves_total
        self.activation_trace: list[str] = []
        if agents is None:
            occupied = round(width * height * density)
            positions = self.random.sample(list(self.grid.coord_iter()), occupied)
            for ordinal, (_contents, position) in enumerate(positions):
                group = int(self.random.random() < minority_fraction)
                agent = Resident(self, f"resident-{ordinal:03d}", group)
                self.grid.place_agent(agent, position)
        else:
            for row in sorted(agents, key=lambda value: value["stable_id"]):
                agent = Resident(self, row["stable_id"], int(row["group"]))
                self.grid.place_agent(agent, tuple(row["position"]))
        if random_state is not None:
            self.random.setstate(_tuples(random_state))
        if numpy_rng_state is not None:
            self.rng.bit_generator.state = numpy_rng_state

    def step(self) -> None:
        self.activation_trace = []
        self.agents.shuffle_do("step")
        self.steps_completed += 1

    def agent_rows(self) -> list[dict[str, Any]]:
        return sorted((
            {"stable_id": agent.stable_id, "group": agent.group, "position": list(agent.pos)}
            for agent in self.agents
        ), key=lambda value: value["stable_id"])

    def metrics(self) -> dict[str, float | int]:
        agents = list(self.agents)
        return {
            "step": self.steps_completed,
            "moves_total": self.moves_total,
            "satisfied_fraction": sum(agent.is_satisfied() for agent in agents) / len(agents),
            "clustering": sum(agent.same_neighbor_fraction() for agent in agents) / len(agents),
        }

    def signature(self) -> dict[str, Any]:
        return {
            "agents": self.agent_rows(),
            "random_state": _lists(self.random.getstate()),
            "numpy_rng_state": self.rng.bit_generator.state,
            "activation_base_order": [agent.stable_id for agent in self.agents],
            "step": self.steps_completed,
            "moves_total": self.moves_total,
        }


def _lists(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_lists(item) for item in value]
    if isinstance(value, list):
        return [_lists(item) for item in value]
    return value


def _tuples(value: Any) -> Any:
    return tuple(_tuples(item) for item in value) if isinstance(value, list) else value
