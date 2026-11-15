from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "run_demo.py"
SPEC = importlib.util.spec_from_file_location("native_demo", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
DEMO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEMO)


class DemoHelperTests(unittest.TestCase):
    def test_input_fixture_is_valid(self) -> None:
        data = DEMO.load_input(Path(__file__).resolve().parents[1] / "data" / "population.json")
        self.assertEqual([1, 4, 7], [row["value"] for row in data["candidates"]])

    def test_fork_query_uses_public_typed_scope(self) -> None:
        query = DEMO.fork_query("axol://forks/ns/pop/run")
        scope = query["document"]["root"]["sourceScope"]
        self.assertEqual("fork-generation", scope["$kind"])
        self.assertEqual("axol://forks/ns/pop/run", scope["forkId"])

    def test_rows_are_compared_independent_of_order(self) -> None:
        rows = [
            {"value": "int:7", "multiplicity": "2"},
            {"value": "int:2", "multiplicity": "1"},
        ]
        self.assertEqual([(2, 1), (7, 2)], DEMO.normalized_rows(rows))


if __name__ == "__main__":
    unittest.main()
