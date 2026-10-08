from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import matplotlib.colors as colors
import matplotlib.pyplot as plt
import numpy as np

from .axol_api import AxolClient
from .checkpoint import restore, save, write_reference
from .model import SchellingModel

BASELINE = "axol://populations/examples.mesa-schelling/baseline"
BRANCH_A = "axol://populations/examples.mesa-schelling/branch-a"
BRANCH_B = "axol://populations/examples.mesa-schelling/branch-b"


def _grid(rows: list[dict], width: int, height: int) -> np.ndarray:
    result = np.zeros((height, width), dtype=int)
    for row in rows:
        x, y = row["position"]
        result[y, x] = int(row["group"]) + 1
    return result


def _plot(checkpoint_rows: list[dict], branch_a: dict, branch_b: dict, output: Path) -> None:
    cmap = colors.ListedColormap(["#f5f5f5", "#2b6cb0", "#dd6b20"])
    figure, axes = plt.subplots(1, 3, figsize=(11, 4))
    panels = [("Shared state — step 30", checkpoint_rows),
              ("A — threshold 0.50, step 60", branch_a["final_agents"]),
              ("B — threshold 0.70, step 60", branch_b["final_agents"])]
    for axis, (title, rows) in zip(axes, panels):
        axis.imshow(_grid(rows, 10, 10), cmap=cmap, vmin=0, vmax=2, interpolation="nearest")
        axis.set_title(title, fontsize=10)
        axis.set_xticks([])
        axis.set_yticks([])
    figure.suptitle("Same AxolDB checkpoint, different Mesa futures (illustrative model)")
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def run(output_dir: Path) -> dict:
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    client = AxolClient.from_environment()
    version = client.version()
    namespace = os.environ.get("AXOL_EXAMPLE_NAMESPACE", "examples.mesa-schelling")
    baseline = f"axol://populations/{namespace}/baseline"
    branch_a_id = f"axol://populations/{namespace}/branch-a"
    branch_b_id = f"axol://populations/{namespace}/branch-b"
    model = SchellingModel(seed=20261007)
    provenance = {"mode": "application-level", "native_fork": False, "source": None}
    history = [model.metrics()]
    reference = save(client, baseline, None, model, provenance)
    parent = reference["generation_id"]
    for _step in range(1, 31):
        model.step()
        history.append(model.metrics())
        reference = save(client, baseline, parent, model, provenance)
        parent = reference["generation_id"]
    checkpoint_path = output_dir / "checkpoint-ref.json"
    write_reference(checkpoint_path, reference)
    checkpoint_signature = model.signature()
    checkpoint_summary_before = client.generation(baseline, reference["generation_id"])
    checkpoint_manifest_before = client.read_json(baseline, reference["generation_id"],
                                                  reference["manifest_hash"])

    control = SchellingModel(width=model.width, height=model.height, density=model.density,
                             minority_fraction=model.minority_fraction, threshold=0.50,
                             agents=model.agent_rows(), steps=model.steps_completed,
                             moves_total=model.moves_total,
                             random_state=checkpoint_signature["random_state"],
                             numpy_rng_state=checkpoint_signature["numpy_rng_state"])
    for _step in range(31, 61):
        control.step()
    continuous_signature = control.signature()

    for name, population_id, threshold in (
        ("branch-a", branch_a_id, 0.50), ("branch-b", branch_b_id, 0.70)
    ):
        subprocess.run([
            sys.executable, "-m", "mesa_axol.worker", "--checkpoint", str(checkpoint_path),
            "--population-id", population_id, "--threshold", str(threshold),
            "--output", str(output_dir / f"{name}.json"),
        ], check=True, env=os.environ.copy())
    branch_a = json.loads((output_dir / "branch-a.json").read_text(encoding="utf-8"))
    branch_b = json.loads((output_dir / "branch-b.json").read_text(encoding="utf-8"))
    if branch_a["final_signature"] != continuous_signature:
        raise AssertionError("uninterrupted and AxolDB-restored scenario A differ")
    if branch_a["initial_signature"] != branch_b["initial_signature"]:
        raise AssertionError("scenario continuations did not start from identical state")
    restored, _manifest = restore(client, reference)
    if restored.signature() != checkpoint_signature:
        raise AssertionError("agent identities, positions, RNG, activation order, or metrics differ")
    checkpoint_summary_after = client.generation(baseline, reference["generation_id"])
    checkpoint_manifest_after = client.read_json(baseline, reference["generation_id"],
                                                 reference["manifest_hash"])
    if checkpoint_summary_before != checkpoint_summary_after or checkpoint_manifest_before != checkpoint_manifest_after:
        raise AssertionError("source checkpoint changed after scenario continuation")

    result = {
        "example": "mesa-schelling",
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
            "compared": "stable agent IDs, groups, positions, RNG state, activation base order, move count, and metrics",
            "same_branch_start": True,
            "source_checkpoint_unchanged": True,
            "earlier_generation_preserved": client.generation(baseline, reference["generation_id"]) is not None,
        },
        "duration_seconds": time.perf_counter() - started,
        "scope": {"grid": "10x10 torus", "agents": len(model.agent_rows()),
                  "saved_baseline_generations": 31, "saved_generations_per_branch": 31},
        "limitations": ["This is an illustrative model, not an empirical prediction of real cities.",
                        "One seed demonstrates the workflow; it does not rank thresholds.",
                        "Windows execution was not run."],
    }
    (output_dir / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    _plot(model.agent_rows(), branch_a, branch_b, output_dir / "scenarios.png")
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
