from __future__ import annotations

import argparse
import json
from pathlib import Path

from .axol_api import AxolClient
from .checkpoint import restore, save


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--population-id", required=True)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    client = AxolClient.from_environment()
    reference = json.loads(args.checkpoint.read_text(encoding="utf-8"))
    model, _manifest = restore(client, reference)
    initial_signature = model.signature()
    model.threshold = args.threshold
    start_moves = model.moves_total
    provenance = {"mode": "application-level", "native_fork": False,
                  "source_population_id": reference["population_id"],
                  "source_generation_id": reference["generation_id"],
                  "source_state_root": reference["state_root"]}
    history = [model.metrics()]
    branch_reference = save(client, args.population_id, None, model, provenance)
    parent = branch_reference["generation_id"]
    for _step in range(31, 61):
        model.step()
        history.append(model.metrics())
        branch_reference = save(client, args.population_id, parent, model, provenance)
        parent = branch_reference["generation_id"]
    final_metrics = model.metrics()
    final_metrics["moves_since_checkpoint"] = model.moves_total - start_moves
    result = {"population_id": args.population_id, "threshold": args.threshold,
              "initial_source": reference, "initial_signature": initial_signature,
              "final_reference": branch_reference, "history": history,
              "final_agents": model.agent_rows(), "final_signature": model.signature(),
              "final_metrics": final_metrics}
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
