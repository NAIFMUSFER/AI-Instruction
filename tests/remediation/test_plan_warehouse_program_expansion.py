#!/usr/bin/env python3
"""Program-of-Requirements regression for explicit warehouse expansion reserve area.

The requirement is measured only from canonical rooms explicitly assigned role
``expansion``. These tests do not infer future demand, capacity, clearance, safety,
or regulatory compliance.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from test_plan_scorecard import warehouse_model
from test_plan_warehouse_program import requirement, review


def with_expansion_reserve():
    model = warehouse_model()
    model["floors"]["ground"]["rooms"].append({
        "id": "future_expansion",
        "role": "expansion",
        "rect": [0.0, 10.0, 10.0, 12.0],
    })
    return model


class WarehouseExpansionProgramTests(unittest.TestCase):
    @staticmethod
    def codes(result):
        return {item["code"] for item in result["issues"]}

    def test_min_expansion_reserve_area_uses_only_explicit_canonical_geometry(self):
        good = review([
            requirement("expansion-area", "expansion", "min_expansion_reserve_area_m2", 120.0)
        ], model=with_expansion_reserve())
        self.assertTrue(good["can_approve"])
        self.assertNotIn("REQUIREMENT_METRIC_NOT_SUPPORTED", self.codes(good))

        too_large = review([
            requirement("expansion-area", "expansion", "min_expansion_reserve_area_m2", 121.0)
        ], model=with_expansion_reserve())
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(too_large))
        self.assertFalse(too_large["can_approve"])

        absent = review([
            requirement("expansion-area", "expansion", "min_expansion_reserve_area_m2", 1.0)
        ], model=warehouse_model())
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(absent))
        self.assertNotIn("REQUIREMENT_NOT_MEASURABLE", self.codes(absent))

        residential = with_expansion_reserve()
        residential["meta"]["type"] = "residential"
        not_applicable = review([
            requirement("expansion-area", "expansion", "min_expansion_reserve_area_m2", 120.0)
        ], model=residential)
        self.assertIn("REQUIREMENT_METRIC_NOT_APPLICABLE", self.codes(not_applicable))
        self.assertFalse(not_applicable["can_approve"])

    def test_program_measurement_does_not_mutate_model(self):
        model = with_expansion_reserve()
        before = copy.deepcopy(model)
        review([
            requirement("expansion-area", "expansion", "min_expansion_reserve_area_m2", 120.0)
        ], model=model)
        self.assertEqual(model, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
