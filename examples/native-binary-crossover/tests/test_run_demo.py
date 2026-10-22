from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "run_demo.py"
SPEC = importlib.util.spec_from_file_location("native_binary_demo", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
DEMO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEMO)


class DemoHelperTests(unittest.TestCase):
    def test_input_fixture_is_valid_and_distinct(self) -> None:
        data = DEMO.load_input(Path(__file__).resolve().parents[1] / "data" / "population.json")
        self.assertEqual(["00010203", "a0a1a2a3"],
                         [row["valueHex"] for row in data["candidates"]])

    def test_known_midpoint_vector_and_parent_order(self) -> None:
        self.assertEqual((2, "0001a2a3"), DEMO.midpoint("00010203", "a0a1a2a3"))
        self.assertEqual((2, "a0a10203"), DEMO.midpoint("a0a1a2a3", "00010203"))

    def test_fork_query_uses_public_typed_scope(self) -> None:
        query = DEMO.fork_query("axol://forks/ns/pop/run")
        self.assertEqual("fork-generation",
                         query["document"]["root"]["sourceScope"]["$kind"])


if __name__ == "__main__":
    unittest.main()
