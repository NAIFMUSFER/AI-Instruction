#!/usr/bin/env python3
"""Regression contracts for measured plan-option comparison."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_options as O
from acs_plan_review import PlanError


def warehouse(storage_width=20.0, dock_count=2, rack_levels=4):
    return {
        "meta": {"type": "warehouse", "name": "Option"},
        "site": {"w": 40.0, "d": 25.0},
        "floor_height": 8.0,
        "wall_h": 7.5,
        "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "receiving", "role": "receiving", "rect": [0.0, 0.0, 10.0, 10.0],
             "docks": [{"edge": "N", "offset": 2.0, "count": dock_count}],
             "lanes": [{"kind": "forklift", "x": 0.0, "z": 0.0, "w": 3.0, "d": 10.0}]},
            {"id": "storage", "role": "storage", "rect": [10.0, 0.0, storage_width, 20.0],
             "racks": [{"kind": "pallet", "x": 1.0, "z": 1.0, "w": 8.0, "d": 18.0,
                        "dir": "z", "rows": 2, "levels": rack_levels, "h": 8.0}]},
            {"id": "shipping", "role": "shipping", "rect": [30.0, 0.0, 10.0, 10.0]},
        ]}},
    }


def residential():
    model = warehouse()
    model["meta"]["type"] = "residential"
    return model


class PlanOptionTests(unittest.TestCase):
    def test_measured_warehouse_deltas_use_first_option_as_reference(self):
        result = O.compare_options([
            {"id": "A", "model": warehouse(storage_width=18.0, dock_count=2, rack_levels=4)},
            {"id": "B", "model": warehouse(storage_width=20.0, dock_count=3, rack_levels=5)},
        ], declared_program_receipt="program:sha256:abc")
        self.assertEqual(result["schema"], "acs.plan-options/1.0")
        self.assertEqual(result["reference_option_id"], "A")
        self.assertEqual(result["typology"], "warehouse")
        self.assertFalse(result["claims_best_option"])
        b = result["options"][1]["delta_from_reference"]
        self.assertEqual(b["scalar"]["space_rect_area_m2"], 40.0)
        self.assertEqual(b["scalar"]["dock_count"], 1)
        self.assertEqual(b["scalar"]["rack_declared_level_sum"], 1)
        self.assertEqual(b["mapping"]["zone_area_by_role_m2"]["storage"], 40.0)
        self.assertEqual(b["mapping"]["dock_count_by_edge"]["N"], 1)

    def test_unavailable_metrics_are_not_converted_into_scores(self):
        result = O.compare_options([
            {"id": "A", "model": warehouse()},
            {"id": "B", "model": warehouse(storage_width=19.0)},
        ])
        for row in result["options"]:
            metrics = row["scorecard"]["metrics"]
            self.assertIsNone(metrics["storage_capacity_positions"])
            self.assertIsNone(metrics["throughput_per_hour"])
            self.assertIsNone(metrics["travel_distance_m"])
        self.assertNotIn("storage_capacity_positions",
                         result["options"][1]["delta_from_reference"]["scalar"])
        self.assertIn("PROGRAM_EQUIVALENCE_NOT_VERIFIED", result["disclosures"])

    def test_missing_complete_mapping_publishes_null_delta_not_partial_number(self):
        bad = warehouse()
        del bad["floors"]["ground"]["rooms"][0]["lanes"][0]["w"]
        result = O.compare_options([
            {"id": "A", "model": warehouse()},
            {"id": "B", "model": bad},
        ])
        self.assertIsNone(result["options"][1]["delta_from_reference"]["mapping"]["lane_area_by_kind_m2"])

    def test_new_mapping_key_is_compared_against_measured_zero(self):
        option_b = warehouse()
        option_b["floors"]["ground"]["rooms"][0]["lanes"].append(
            {"kind": "pedestrian", "x": 0.0, "z": 0.0, "w": 1.0, "d": 10.0})
        result = O.compare_options([
            {"id": "A", "model": warehouse()},
            {"id": "B", "model": option_b},
        ])
        self.assertEqual(result["options"][1]["delta_from_reference"]["mapping"]
                         ["lane_area_by_kind_m2"]["pedestrian"], 10.0)

    def test_different_typologies_are_rejected_instead_of_ranked(self):
        with self.assertRaises(PlanError) as ctx:
            O.compare_options([
                {"id": "A", "model": warehouse()},
                {"id": "B", "model": residential()},
            ])
        self.assertEqual(ctx.exception.code, "OPTION_TYPOLOGY_MISMATCH")

    def test_unknown_typology_is_rejected(self):
        model = warehouse()
        model["meta"].pop("type")
        with self.assertRaises(PlanError) as ctx:
            O.compare_options([{"id": "A", "model": model}, {"id": "B", "model": model}])
        self.assertEqual(ctx.exception.code, "OPTION_TYPOLOGY_UNKNOWN")

    def test_duplicate_ids_and_bad_counts_fail_closed(self):
        with self.assertRaises(PlanError) as ctx:
            O.compare_options([{"id": "A", "model": warehouse()}])
        self.assertEqual(ctx.exception.code, "OPTION_COUNT")
        with self.assertRaises(PlanError) as ctx:
            O.compare_options([
                {"id": "A", "model": warehouse()},
                {"id": "A", "model": warehouse()},
            ])
        self.assertEqual(ctx.exception.code, "DUPLICATE_OPTION")

    def test_site_and_level_differences_are_disclosed_not_scored_as_quality(self):
        b = warehouse()
        b["site"]["w"] = 42.0
        b["levels"].append({"index": 1, "template": "ground"})
        result = O.compare_options([
            {"id": "A", "model": warehouse()},
            {"id": "B", "model": b},
        ], declared_program_receipt="program:one")
        self.assertFalse(result["same_site_geometry"])
        self.assertFalse(result["same_level_count"])
        self.assertIn("SITE_CONSTRAINT_DIFFERS", result["disclosures"])
        self.assertIn("LEVEL_COUNT_DIFFERS", result["disclosures"])
        self.assertFalse(result["program_receipt_authenticated"])

    def test_input_models_are_not_mutated(self):
        a, b = warehouse(), warehouse(storage_width=19.0)
        before_a, before_b = copy.deepcopy(a), copy.deepcopy(b)
        result = O.compare_options([{"id": "A", "model": a}, {"id": "B", "model": b}])
        self.assertEqual(a, before_a)
        self.assertEqual(b, before_b)
        self.assertNotEqual(result["options"][0]["model_hash"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
