#!/usr/bin/env python3
"""Warehouse-only measured operational scorecard/option regressions.

These contracts use explicit canonical geometry only. They do not claim routed
travel, storage capacity, throughput, regulatory compliance, or safety approval.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_options as O
import acs_plan_scorecard as S


def warehouse(*, rack_width=8.0, forklift_length=20.0, include_lane_dir=True):
    forklift = {
        "id": "forklift_main", "kind": "forklift",
        "x": 0.0, "z": 0.0, "w": forklift_length, "d": 3.0,
    }
    pedestrian = {
        "id": "pedestrian_main", "kind": "pedestrian",
        "x": 30.0, "z": 0.0, "w": 1.2, "d": 18.0,
    }
    if include_lane_dir:
        forklift["dir"] = "x"
        pedestrian["dir"] = "z"
    return {
        "meta": {"type": "warehouse", "name": "operational-metrics"},
        "site": {"w": 50.0, "d": 30.0},
        "floor_height": 9.0,
        "wall_h": 8.5,
        "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {
                "id": "receiving", "role": "receiving",
                "rect": [0.0, 0.0, 15.0, 12.0],
                "docks": [{"id": "dock_n", "edge": "N", "offset": 3.0, "count": 2}],
                "lanes": [forklift, pedestrian],
            },
            {
                "id": "storage", "role": "storage",
                "rect": [15.0, 0.0, 25.0, 24.0],
                "racks": [
                    {"id": "rack_a", "kind": "pallet", "x": 16.0, "z": 1.0,
                     "w": rack_width, "d": 18.0, "dir": "z", "rows": 2,
                     "aisle": 3.4, "levels": 4, "h": 8.0},
                    {"id": "rack_b", "kind": "shelf", "x": 27.0, "z": 1.0,
                     "w": 4.0, "d": 10.0, "dir": "z", "rows": 1,
                     "aisle": 1.4, "levels": 5, "h": 2.4},
                ],
            },
            {"id": "shipping", "role": "shipping", "rect": [40.0, 0.0, 10.0, 12.0]},
        ]}},
    }


class WarehouseOperationalMetricTests(unittest.TestCase):
    def test_declared_rack_footprint_and_lane_centerline_are_measured(self):
        result = S.measure_plan(warehouse())
        metrics = result["metrics"]
        self.assertEqual(metrics["rack_declared_footprint_area_m2"], 184.0)
        self.assertEqual(metrics["lane_centerline_length_by_kind_m"], {
            "forklift": 20.0, "pedestrian": 18.0,
        })
        self.assertEqual(metrics["lane_area_by_kind_m2"], {
            "forklift": 60.0, "pedestrian": 21.6,
        })
        self.assertIsNone(metrics["travel_distance_m"])
        self.assertIn("not routed origin/destination travel paths",
                      result["unavailable"]["travel_distance_m"])
        self.assertFalse(result["claims_regulatory_compliance"])
        self.assertFalse(result["claims_structural_safety"])

    def test_missing_lane_orientation_fails_centerline_closed_but_keeps_area(self):
        metrics = S.measure_plan(warehouse(include_lane_dir=False))["metrics"]
        self.assertIsNone(metrics["lane_centerline_length_by_kind_m"])
        self.assertEqual(metrics["lane_area_by_kind_m2"]["forklift"], 60.0)
        self.assertIsNone(metrics["travel_distance_m"])

    def test_missing_rack_dimensions_do_not_publish_partial_footprint(self):
        model = warehouse()
        del model["floors"]["ground"]["rooms"][1]["racks"][1]["d"]
        metrics = S.measure_plan(model)["metrics"]
        self.assertEqual(metrics["rack_group_count"], 2)
        self.assertIsNone(metrics["rack_declared_footprint_area_m2"])
        self.assertIsNone(metrics["storage_capacity_positions"])

    def test_options_compare_only_measured_operational_geometry(self):
        a = warehouse(rack_width=8.0, forklift_length=20.0)
        b = warehouse(rack_width=10.0, forklift_length=25.0)
        result = O.compare_options([
            {"id": "A", "model": a},
            {"id": "B", "model": b},
        ], declared_program_receipt="program:warehouse:measured")
        delta = result["options"][1]["delta_from_reference"]
        self.assertEqual(delta["scalar"]["rack_declared_footprint_area_m2"], 36.0)
        self.assertEqual(delta["mapping"]["lane_centerline_length_by_kind_m"]["forklift"], 5.0)
        self.assertEqual(delta["mapping"]["lane_centerline_length_by_kind_m"]["pedestrian"], 0.0)
        self.assertFalse(result["claims_best_option"])
        self.assertFalse(result["claims_regulatory_compliance"])

    def test_residential_does_not_gain_warehouse_operational_metrics(self):
        model = warehouse()
        model["meta"]["type"] = "residential"
        metrics = S.measure_plan(model)["metrics"]
        self.assertNotIn("rack_declared_footprint_area_m2", metrics)
        self.assertNotIn("lane_centerline_length_by_kind_m", metrics)

    def test_measurement_does_not_mutate_canonical_model(self):
        model = warehouse()
        before = copy.deepcopy(model)
        S.measure_plan(model)
        self.assertEqual(model, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
