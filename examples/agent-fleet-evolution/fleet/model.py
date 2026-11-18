"""Pure deterministic fleet model. This module has no AxolDB dependency."""
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from heapq import heappop, heappush
from itertools import combinations, permutations
import json
from typing import Protocol

TIE_POLICY = "lexicographic-node-vehicle-delivery-v1"
AGENTS = (("agent-a", "greedy-nearest-next", 1), ("agent-b", "bounded-cost-aware", 1))


class Invalid(ValueError):
    """The input violates a scenario, plan, or persisted checkpoint invariant."""


def require(condition, reason):
    if not condition:
        raise Invalid(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(value):
    return sha256(canonical(value)).hexdigest()


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    version: int
    depot: str
    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str, int], ...]
    deliveries: tuple[tuple[str, str], ...]
    vehicles: tuple[tuple[str, int], ...]

    @classmethod
    def load(cls, data):
        require(isinstance(data, dict) and set(data) ==
                {"id","version","depot","nodes","edges","deliveries","vehicles"}, "scenario fields")
        require(data["version"] == 1 and type(data["version"]) is int, "scenario version")
        require(isinstance(data["id"], str) and bool(data["id"]), "scenario identity")
        nodes = tuple(sorted(data["nodes"]))
        require(all(isinstance(n, str) and n for n in nodes) and len(set(nodes)) == len(nodes)
                and data["depot"] in nodes, "scenario node/depot IDs")
        edges = []
        seen = set()
        for left, right, cost in data["edges"]:
            require(left in nodes and right in nodes and left != right
                    and type(cost) is int and cost > 0, "positive, nonloop road edges")
            pair = tuple(sorted((left, right)))
            require(pair not in seen, "duplicate road edge")
            seen.add(pair)
            edges.append((*pair, cost))
        deliveries = tuple(sorted(tuple(x) for x in data["deliveries"]))
        vehicles = tuple(sorted(tuple(x) for x in data["vehicles"]))
        require(len(deliveries) == len({d for d,_ in deliveries}) == 5
                and all(isinstance(d,str) and d and n in nodes and n != data["depot"]
                        for d,n in deliveries), "exactly five single-unit requests")
        require(len(vehicles) == len({v for v,_ in vehicles}) == 2
                and all(isinstance(v,str) and v and type(c) is int and 0 < c < 5
                        for v,c in vehicles), "two named vehicles with finite capacity")
        require(sum(c for _,c in vehicles) >= 5, "insufficient total capacity")
        value = cls(data["id"], 1, data["depot"], nodes, tuple(sorted(edges)), deliveries, vehicles)
        for node in nodes:
            shortest(value, value.depot, node)
        return value

    def data(self):
        return {"id":self.scenario_id, "version":self.version, "depot":self.depot,
                "nodes":list(self.nodes), "edges":[list(x) for x in self.edges],
                "deliveries":[list(x) for x in self.deliveries],
                "vehicles":[list(x) for x in self.vehicles]}

    def record(self):
        value = self.data()
        return {"record_type":"Scenario", "schema_version":1, "id":self.scenario_id,
                "graph_sha256":digest(value), "scenario":value, "tie_policy":TIE_POLICY,
                "agents":[{"id":a,"strategy":s,"version":v} for a,s,v in AGENTS]}


@lru_cache(maxsize=4096)
def shortest(scenario, start, end):
    require(start in scenario.nodes and end in scenario.nodes, "unknown shortest-path node")
    adjacency = {node: [] for node in scenario.nodes}
    for a,b,cost in scenario.edges:
        adjacency[a].append((b,cost))
        adjacency[b].append((a,cost))
    queue = [(0, (start,), start)]
    best = {}
    while queue:
        cost, path, node = heappop(queue)
        if node in best:
            continue
        best[node] = (cost, path)
        if node == end:
            return best[node]
        for other, weight in adjacency[node]:
            if other not in best:
                heappush(queue, (cost+weight, (*path,other), other))
    raise Invalid("unreachable shortest-path node")


@dataclass(frozen=True)
class State:
    agent_id: str
    state_id: str
    generation: int
    last_orders: tuple[tuple[str, ...], ...]
    last_cost: int


@dataclass(frozen=True)
class GenerationContext:
    number: int
    parent_plan_id: str | None = None
    rank: int | None = None
    move: tuple[str, ...] = ()
    varied_orders: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class Candidate:
    # Canonical bytes make the returned state and plan immutable at the interface.
    plan: bytes
    state: bytes


class Agent(Protocol):
    def propose(self, scenario: Scenario, context: GenerationContext, previous: State | None,
                tie_policy: str) -> Candidate: ...


def routes_for(scenario, orders):
    require(len(orders) == len(scenario.vehicles), "one order per vehicle")
    delivery_nodes = dict(scenario.deliveries)
    assigned = [d for order in orders for d in order]
    require(Counter(assigned) == Counter(delivery_nodes.keys()), "every delivery exactly once")
    routes = {}
    for (vehicle,capacity),order in zip(scenario.vehicles, orders, strict=True):
        require(len(order) <= capacity, "vehicle capacity exceeded")
        stops = (scenario.depot, *(delivery_nodes[d] for d in order), scenario.depot)
        nodes = [scenario.depot]
        legs = []
        for start,end in zip(stops, stops[1:]):
            cost,path = shortest(scenario,start,end)
            nodes.extend(path[1:])
            legs.append({"from":start,"to":end,"path":list(path),"cost":cost})
        routes[vehicle] = {"path":nodes,"legs":legs,"cost":sum(leg["cost"] for leg in legs)}
    return routes


def validate_plan(scenario, plan):
    vehicles = tuple(v for v,_ in scenario.vehicles)
    require(tuple(sorted(plan["ordered_delivery_routes"])) == vehicles, "vehicle route keys")
    orders = tuple(tuple(plan["ordered_delivery_routes"][v]) for v in vehicles)
    routes = routes_for(scenario, orders)
    expected_assignments = {d:v for v,order in zip(vehicles, orders, strict=True) for d in order}
    require(plan["vehicle_assignments"] == expected_assignments, "route/assignment disagreement")
    require(plan["route_paths"] == routes, "invalid graph edges, depot endpoints, shortest paths or leg costs")
    total = sum(r["cost"] for r in routes.values())
    metrics = {"total_cost":total, "vehicles_used":sum(bool(order) for order in orders)}
    require(plan["total_cost"] == total and plan["objective_metrics"] == metrics, "scoring mismatch")
    require(plan["feasible"] is True and plan["constraint_violations"] == [], "invalid feasibility assertion")
    require(plan["graph_id"] == scenario.scenario_id and plan["graph_sha256"] == digest(scenario.data()),
            "graph reference mismatch")
    return total


def greedy(scenario):
    remaining = dict(scenario.deliveries)
    orders = []
    for _,capacity in scenario.vehicles:
        node = scenario.depot
        order = []
        for _ in range(min(capacity, len(remaining))):
            delivery = min(remaining, key=lambda d: (shortest(scenario,node,remaining[d])[0],d))
            node = remaining.pop(delivery)
            order.append(delivery)
        orders.append(tuple(order))
    return tuple(orders)


def route_cost(scenario, orders):
    return sum(r["cost"] for r in routes_for(scenario, orders).values())


def cost_aware(scenario):
    starts = tuple(d for d,_ in scenario.deliveries)
    (_,cap1),(_,cap2) = scenario.vehicles
    candidates = ((order[:i], order[i:]) for order in permutations(starts)
                  for i in range(len(starts)-cap2,cap1+1))
    return min(candidates, key=lambda orders: (route_cost(scenario,orders),orders))


class Planner:
    def __init__(self, definition):
        self.agent_id, self.strategy, self.version = definition

    def propose(self, scenario, context, previous, tie_policy):
        require(tie_policy == TIE_POLICY, "unsupported tie policy")
        number = context.number
        if number == 0:
            require(previous is None and context.parent_plan_id is None, "unexpected initial parent")
            orders = greedy(scenario) if self.agent_id == "agent-a" else cost_aware(scenario)
        else:
            require(number == 1 and previous is not None and previous.generation == 0
                    and previous.agent_id == self.agent_id and context.parent_plan_id
                    and context.varied_orders, "invalid variation context")
            orders = context.varied_orders
        routes = routes_for(scenario,orders)
        total = sum(r["cost"] for r in routes.values())
        key = f"{scenario.scenario_id}/g{number}/{self.agent_id}"
        state_id,plan_id = key+"/state",key+"/plan"
        provenance = {"agent_id":self.agent_id,"strategy":self.strategy,"strategy_version":self.version,
            "tie_policy":tie_policy,"mechanism":"initial-planner" if number == 0 else "application-variation",
            "rank":context.rank,"move":list(context.move)}
        state = {"record_type":"AgentState","schema_version":2,"state_id":state_id,
                 "agent_id":self.agent_id,"state_version":number+1,"strategy_type":self.strategy,
                 "strategy_parameters":{"strategy_version":self.version},
                 "memory_summary":f"Completed bounded planning round {number}",
                 "generation":number,"parent_state_id":previous.state_id if previous else None,
                 "deterministic_seed":0,"tie_policy":tie_policy,
                 "memory":{"last_orders":[list(x) for x in orders],"last_cost":total},
                 "provenance":provenance}
        vehicles = tuple(v for v,_ in scenario.vehicles)
        plan = {"record_type":"FleetPlan","schema_version":2,"plan_id":plan_id,
                "plan_version":number+1,"agent_state_id":state_id,"graph_id":scenario.scenario_id,
                "graph_sha256":digest(scenario.data()),"generation":number,
                "vehicle_assignments":{d:v for v,order in zip(vehicles,orders,strict=True) for d in order},
                "ordered_delivery_routes":{v:list(order) for v,order in zip(vehicles,orders,strict=True)},
                "route_paths":routes,"total_cost":total,"feasible":True,"constraint_violations":[],
                "objective_metrics":{"total_cost":total,"vehicles_used":sum(bool(o) for o in orders)},
                "parent_plan_ids":[context.parent_plan_id] if context.parent_plan_id else [],
                "provenance":provenance}
        validate_plan(scenario,plan)
        return Candidate(canonical(plan),canonical(state))


def orders_of(scenario, plan):
    return tuple(tuple(plan["ordered_delivery_routes"][v]) for v,_ in scenario.vehicles)


def neighbors(orders):
    positions = [(vehicle,index) for vehicle,order in enumerate(orders) for index in range(len(order))]
    for (v1,i),(v2,j) in combinations(positions,2):
        copy = [list(x) for x in orders]
        first,second = copy[v1][i],copy[v2][j]
        copy[v1][i],copy[v2][j] = second,first
        yield tuple(tuple(x) for x in copy),("swap",first,second)


def record_id(record):
    return record[{"Scenario":"id","FleetPlan":"plan_id","AgentState":"state_id",
                   "Checkpoint":"checkpoint_id"}[record["record_type"]]]


def generation_records(scenario, number, previous=()):
    require(number in (0,1), "exactly two application generations")
    planners = {a:Planner(defn) for defn in AGENTS for a in (defn[0],)}
    candidates = []
    if number == 0:
        require(not previous,"initial generation has no previous records")
        candidates = [planner.propose(scenario,GenerationContext(0),None,TIE_POLICY)
                      for planner in planners.values()]
    else:
        states = {r["state_id"]:r for r in previous if r["record_type"] == "AgentState"}
        plans = [r for r in previous if r["record_type"] == "FleetPlan"]
        require(len(plans) == len(states) == 2, "variation requires two persisted plans and states")
        ranked = sorted(plans,key=lambda p:(validate_plan(scenario,p), orders_of(scenario,p), p["plan_id"]))
        def signature(orders):
            return tuple(min(order, order[::-1]) for order in orders)
        excluded = {signature(orders_of(scenario,p)) for p in ranked}
        for rank,plan in enumerate(ranked,1):
            parent = states[plan["agent_state_id"]]
            orders = orders_of(scenario,plan)
            require(parent["memory"] == {"last_orders":[list(x) for x in orders],"last_cost":plan["total_cost"]},
                    "previous agent memory/plan mismatch")
            candidates_for_parent = ((order,move) for order,move in neighbors(orders) if signature(order) not in excluded)
            varied,move = min(candidates_for_parent,key=lambda pair:(route_cost(scenario,pair[0]),*pair))
            excluded.add(signature(varied))
            prior = State(parent["agent_id"],parent["state_id"],parent["generation"],orders,plan["total_cost"])
            context = GenerationContext(1,plan["plan_id"],rank,move,varied)
            candidates.append(planners[prior.agent_id].propose(scenario,context,prior,TIE_POLICY))
    docs = [scenario.record(),*(json.loads(raw) for c in candidates for raw in (c.plan,c.state))]
    return sorted(docs,key=record_id)


def verify_records(scenario, number, records, previous=()):
    require(len(records) == 5 and len({record_id(r) for r in records}) == 5, "five distinct payload records")
    for record in records:
        if record["record_type"] == "FleetPlan":
            validate_plan(scenario,record)
    expected = generation_records(scenario,number,previous)
    require(canonical(sorted(records,key=record_id)) == canonical(expected),
            "persisted records, scores, references or deterministic provenance differ")
    return expected
