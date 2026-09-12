#!/usr/bin/env python3
"""Residential Design Scorecard regressions; geometry only, no compliance claims."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_options as O
import acs_plan_scorecard as S


def residential(majlis_w=5.0, bedroom_w=5.0):
    return {
        "meta": {"type": "residential", "name": "Measured residence"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 3.2,
        "wall_h": 3.0,
        "wall_t": 0.15,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "majlis", "role": "majlis", "rect": [0.0, 0.0, majlis_w, 4.0]},
            {"id": "bedroom", "role": "bedroom", "rect": [majlis_w, 0.0, bedroom_w, 4.0]},
        ]}},
    }


class ResidentialMeasuredScorecardTests(unittest.TestCase):
    def test_residential_publishes_only_measured_role_distribution(self):
        model = residential()
        before = copy.deepcopy(model)
        result = S.measure_plan(model)
        metrics = result["metrics"]
        self.assertEqual(result["typology"], "residential")
        self.assertEqual(metrics["space_rect_area_m2"], 40.0)
        self.assertEqual(metrics["space_area_by_role_m2"], {"bedroom": 20.0, "majlis": 20.0})
        self.assertEqual(metrics["space_count_by_role"], {"bedroom": 1, "majlis": 1})
        self.assertEqual(metrics["unclassified_space_area_m2"], 0.0)
        self.assertEqual(metrics["unclassified_space_count"], 0)
        self.assertNotIn("dock_count", metrics)
        self.assertNotIn("storage_capacity_positions", metrics)
        self.assertFalse(result["claims_regulatory_compliance"])
        self.assertFalse(result["claims_structural_safety"])
        self.assertEqual(model, before)

    def test_repeated_residential_template_counts_each_level_instance(self):
        model = residential()
        model["levels"].append({"index": 1, "template": "ground"})
        metrics = S.measure_plan(model)["metrics"]
        self.assertEqual(metrics["space_rect_area_m2"], 80.0)
        self.assertEqual(metrics["space_area_by_role_m2"], {"bedroom": 40.0, "majlis": 40.0})
        self.assertEqual(metrics["space_count_by_role"], {"bedroom": 2, "majlis": 2})

    def test_incomplete_area_fails_role_area_closed_but_does_not_invent_zero(self):
        model = residential()
        del model["floors"]["ground"]["rooms"][0]["rect"]
        metrics = S.measure_plan(model)["metrics"]
        self.assertIsNone(metrics["space_rect_area_m2"])
        self.assertIsNone(metrics["space_area_by_role_m2"])
        self.assertIsNone(metrics["unclassified_space_area_m2"])
        self.assertEqual(metrics["space_count_by_role"], {"bedroom": 1, "majlis": 1})

    def test_warehouse_role_area_alias_never_publishes_partial_measurement(self):
        # The warehouse alias and the generic role-area metric describe the same
        # explicit room rectangles. If one room is unmeasurable, publishing only
        # the other role would let option comparison mistake unknown area for zero.
        model = residential()
        model["meta"]["type"] = "warehouse"
        del model["floors"]["ground"]["rooms"][0]["rect"]
        metrics = S.measure_plan(model)["metrics"]
        self.assertIsNone(metrics["space_area_by_role_m2"])
        self.assertIsNone(metrics["zone_area_by_role_m2"])
        self.assertIsNone(metrics["unclassified_zone_area_m2"])

    def test_option_comparison_exposes_majlis_reallocation_with_same_total_area(self):
        # A = 20 m² majlis + 20 m² bedroom; B = 24 + 16. Total measured area
        # remains 40 m², so a total-only scorecard would hide this user-visible edit.
        result = O.compare_options([
            {"id": "A", "model": residential(5.0, 5.0)},
            {"id": "B", "model": residential(6.0, 4.0)},
        ], declared_program_receipt="program:residential:test")
        delta = result["options"][1]["delta_from_reference"]
        self.assertEqual(delta["scalar"]["space_rect_area_m2"], 0.0)
        self.assertEqual(delta["mapping"]["space_area_by_role_m2"]["majlis"], 4.0)
        self.assertEqual(delta["mapping"]["space_area_by_role_m2"]["bedroom"], -4.0)
        self.assertEqual(delta["mapping"]["space_count_by_role"], {"bedroom": 0, "majlis": 0})
        self.assertFalse(result["claims_best_option"])
        self.assertFalse(result["claims_regulatory_compliance"])
        self.assertFalse(result["claims_structural_safety"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
