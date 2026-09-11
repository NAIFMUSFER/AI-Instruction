#!/usr/bin/env python3
"""Regression contracts for deterministic plan-first scorecards."""
from __future__ import annotations

import copy
import math
import unittest

import acs_plan_scorecard as S


def warehouse_model():
    return {
        "meta": {"type": "warehouse", "name": "Measured warehouse"},
        "site": {"w": 40.0, "d": 25.0},
        "floor_height": 8.0,
        "wall_h": 7.5,
        "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {
            "ground": {
                "rooms": [
                    {
                        "id": "receiving",
                        "role": "receiving",
                        "rect": [0.0, 0.0, 10.0, 10.0],
                        "docks": [
                            {"edge": "N", "offset": 2.0, "count": 2},
                            {"edge": "W", "offset": 4.0},
                        ],
                        "lanes": [
                            {"kind": "forklift", "x": 0.0, "z": 0.0, "w": 3.0, "d": 10.0},
                            {"kind": "pedestrian", "x": 0.0, "z": 0.0, "w": 1.0, "d": 10.0},
                        ],
                    },
                    {
                        "id": "storage",
                        "role": "storage",
                        "rect": [10.0, 0.0, 20.0, 20.0],
                        "racks": [
                            {"kind": "pallet", "x": 1.0, "z": 1.0, "w": 8.0, "d": 18.0,
                             "dir": "z", "rows": 2, "aisle": 3.4, "levels": 4, "h": 8.0},
                            {"kind": "shelf", "x": 10.0, "z": 1.0, "w": 8.0, "d": 18.0,
                             "dir": "z", "rows": 2, "aisle": 1.4, "levels": 5, "h": 2.4},
                        ],
                        "stations": [
                            {"kind": "inspect", "x": 1.0, "z": 1.0, "count": 2},
                            {"kind": "charger", "x": 3.0, "z": 1.0},
                        ],
                    },
                    {"id": "shipping", "role": "shipping", "rect": [30.0, 0.0, 10.0, 10.0]},
                ]
            }
        },
    }


class ScorecardTests(unittest.TestCase):
    def test_warehouse_measures_only_explicit_geometry(self):
        result = S.measure_plan(warehouse_model())
        m = result["metrics"]
        self.assertEqual(result["schema"], "acs.plan-scorecard/1.0")
        self.assertEqual(result["typology"], "warehouse")
        self.assertEqual(m["site_area_m2"], 1000.0)
        self.assertEqual(m["level_count"], 1)
        self.assertEqual(m["space_rect_area_m2"], 600.0)
        self.assertEqual(m["zone_area_by_role_m2"], {
            "receiving": 100.0, "shipping": 100.0, "storage": 400.0})
        self.assertEqual(m["dock_count"], 3)
        self.assertEqual(m["dock_count_by_edge"], {"N": 2, "W": 1})
        self.assertEqual(m["rack_group_count"], 2)
        self.assertEqual(m["rack_declared_level_sum"], 9)
        self.assertEqual(m["station_count"], 3)
        self.assertEqual(m["lane_area_by_kind_m2"], {"forklift": 30.0, "pedestrian": 10.0})
        self.assertIsNone(m["storage_capacity_positions"])
        self.assertIsNone(m["throughput_per_hour"])
        self.assertIsNone(m["travel_distance_m"])
        self.assertFalse(result["claims_regulatory_compliance"])
        self.assertFalse(result["claims_structural_safety"])

    def test_repeated_template_is_measured_per_level_instance(self):
        model = warehouse_model()
        model["levels"].append({"index": 1, "template": "ground"})
        m = S.measure_plan(model)["metrics"]
        self.assertEqual(m["level_count"], 2)
        self.assertEqual(m["space_rect_area_m2"], 1200.0)
        self.assertEqual(m["dock_count"], 6)
        self.assertEqual(m["rack_group_count"], 4)
        self.assertEqual(m["rack_declared_level_sum"], 18)
        self.assertEqual(m["station_count"], 6)
        self.assertEqual(m["zone_area_by_role_m2"]["storage"], 800.0)
        self.assertEqual(m["lane_area_by_kind_m2"]["forklift"], 60.0)

    def test_missing_rack_levels_does_not_invent_level_sum_or_capacity(self):
        model = warehouse_model()
        del model["floors"]["ground"]["rooms"][1]["racks"][0]["levels"]
        m = S.measure_plan(model)["metrics"]
        self.assertEqual(m["rack_group_count"], 2)
        self.assertIsNone(m["rack_declared_level_sum"])
        self.assertIsNone(m["storage_capacity_positions"])

    def test_invalid_dock_count_discloses_unknown_instead_of_coercing(self):
        model = warehouse_model()
        model["floors"]["ground"]["rooms"][0]["docks"][0]["count"] = "2"
        result = S.measure_plan(model)
        self.assertIsNone(result["metrics"]["dock_count"])
        self.assertIsNone(result["metrics"]["dock_count_by_edge"])

    def test_partial_lane_geometry_does_not_publish_partial_total(self):
        model = warehouse_model()
        del model["floors"]["ground"]["rooms"][0]["lanes"][0]["w"]
        self.assertIsNone(S.measure_plan(model)["metrics"]["lane_area_by_kind_m2"])

    def test_nonfinite_dimensions_are_not_reported_as_measurements(self):
        model = warehouse_model()
        model["site"]["w"] = math.inf
        result = S.measure_plan(model)
        self.assertIsNone(result["metrics"]["site_area_m2"])
        self.assertIn("SITE_AREA_NOT_MEASURABLE", result["warnings"])

    def test_missing_levels_fails_measurements_closed(self):
        model = warehouse_model()
        model["levels"] = []
        result = S.measure_plan(model)
        m = result["metrics"]
        self.assertIsNone(m["level_count"])
        self.assertIsNone(m["space_rect_area_m2"])
        self.assertIsNone(m["dock_count"])
        self.assertIsNone(m["rack_group_count"])
        self.assertIn("LEVELS_NOT_MEASURABLE", result["warnings"])

    def test_residential_does_not_receive_warehouse_operational_claims(self):
        model = warehouse_model()
        model["meta"]["type"] = "residential"
        result = S.measure_plan(model)
        self.assertEqual(result["typology"], "residential")
        self.assertNotIn("dock_count", result["metrics"])
        self.assertNotIn("storage_capacity_positions", result["metrics"])
        self.assertIsNone(result["metrics"]["gross_floor_area_m2"])
        self.assertIsNone(result["metrics"]["efficiency"])

    def test_model_is_not_mutated(self):
        model = warehouse_model()
        before = copy.deepcopy(model)
        S.measure_plan(model)
        self.assertEqual(model, before)

    def test_typology_is_not_guessed_from_room_role(self):
        model = warehouse_model()
        model["meta"].pop("type")
        result = S.measure_plan(model)
        self.assertEqual(result["typology"], "unknown")
        self.assertNotIn("dock_count", result["metrics"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
