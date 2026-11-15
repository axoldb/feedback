from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from axol_demo import analyses_from_records, canonical, compare_analyses, rules_from_records, source_from_records


class ProjectionTests(unittest.TestCase):
    def test_source_units_are_restored_in_stable_order(self) -> None:
        records = [
            {"recordType": "sourceUnit", "documentId": "b", "ordinal": 1, "unitId": "b:2"},
            {"recordType": "sourceManifest", "source": {"datasetId": "d"}},
            {"recordType": "sourceUnit", "documentId": "a", "ordinal": 0, "unitId": "a:1"},
        ]
        self.assertEqual(["a:1", "b:2"], [row["unitId"] for row in source_from_records(records)["units"]])

    def test_rule_and_result_versions_are_sorted(self) -> None:
        rules = [{"recordType": "dictionaryRule", "rule": {"version": "2.0.0"}},
                 {"recordType": "dictionaryRule", "rule": {"version": "1.0.0"}}]
        results = [{"recordType": "analysisResult", "analysis": {"dictionaryVersion": "2.0.0"}},
                   {"recordType": "analysisResult", "analysis": {"dictionaryVersion": "1.0.0"}}]
        self.assertEqual(["1.0.0", "2.0.0"], [row["version"] for row in rules_from_records(rules)])
        self.assertEqual(["1.0.0", "2.0.0"], [row["dictionaryVersion"] for row in analyses_from_records(results)])

    def test_comparison_requires_exact_recomputation_and_traces_change(self) -> None:
        base = {"datasetId": "d", "dictionaryVersion": "1.0.0", "units": [
            {"unitId": "d:u01", "documentId": "d", "documentTitle": "D", "text": "x < y",
             "label": "none", "matchedExpressions": []}]}
        expanded = {"datasetId": "d", "dictionaryVersion": "2.0.0", "units": [
            {"unitId": "d:u01", "documentId": "d", "documentTitle": "D", "text": "x < y",
             "label": "social_protection", "matchedExpressions": ["x"]}]}
        comparison = compare_analyses([base, expanded], [base, expanded])
        self.assertEqual(1, comparison["changedUnitCount"])
        self.assertEqual("d:u01", comparison["changedUnits"][0]["unitId"])
        with self.assertRaisesRegex(RuntimeError, "recomputed"):
            compare_analyses([base, expanded], [base, base])

    def test_canonical_json_is_key_order_independent(self) -> None:
        self.assertEqual(canonical({"b": 2, "a": 1}), canonical({"a": 1, "b": 2}))


if __name__ == "__main__":
    unittest.main()
