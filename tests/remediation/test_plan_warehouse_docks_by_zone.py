#!/usr/bin/env python3
"""Warehouse dock allocation regressions for ACS Design Pipeline v2.

These contracts count only explicitly declared dock quantities grouped by the
canonical role of their owning warehouse zone. They do not infer dock capacity,
throughput, queuing, apron geometry, traffic safety, or regulatory compliance.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_options as O
import acs_plan_scorecard as S
from test_plan_warehouse_operational_metrics import warehouse


def with_shipping_docks(model: dict, count: int = 3) -> dict:
    shipping = model["floors"]["ground"]["rooms"][2]
    shipping["docks"] = [
        {"id": "dock_s", "edge": "S", "offset": 2.0, "count": count},
    ]
    return model


class WarehouseDockByZoneTests(unittest.TestCase):
    def test_explicit_docks_are_counted_by_owning_zone_role(self):
        model = with_shipping_docks(warehouse())
        result = S.measure_plan(model)
        metrics = result["metrics"]
        self.assertEqual(metrics["dock_count"], 5)
        self.assertEqual(metrics["dock_count_by_edge"], {"N": 2, "S": 3})
        self.assertEqual(metrics["dock_count_by_zone_role"], {
            "receiving": 2,
            "shipping": 3,
        })
        self.assertFalse(result["claims_regulatory_compliance"])
        self.assertFalse(result["claims_structural_safety"])

    def test_unclassified_dock_owner_fails_role_mapping_closed(self):
        model = warehouse()
        receiving = model["floors"]["ground"]["rooms"][0]
        del receiving["role"]
        result = S.measure_plan(model)
        metrics = result["metrics"]
        self.assertEqual(metrics["dock_count"], 2)
        self.assertIsNone(metrics["dock_count_by_zone_role"])
        self.assertIn("DOCK_ZONE_ROLE_NOT_CLASSIFIED", result["warnings"])
        self.assertIn("owning zone role", result["unavailable"]["dock_count_by_zone_role"])

    def test_malformed_falsey_dock_collection_fails_all_dock_measurements_closed(self):
        model = warehouse()
        model["floors"]["ground"]["rooms"][0]["docks"] = {}
        result = S.measure_plan(model)
        metrics = result["metrics"]
        self.assertIsNone(metrics["dock_count"])
        self.assertIsNone(metrics["dock_count_by_edge"])
        self.assertIsNone(metrics["dock_count_by_zone_role"])
        self.assertIn("dock_count_by_zone_role", result["unavailable"])

    def test_design_options_compare_measured_dock_allocation(self):
        a = warehouse()
        b = with_shipping_docks(warehouse())
        result = O.compare_options([
            {"id": "A", "model": a},
            {"id": "B", "model": b},
        ], declared_program_receipt="program:warehouse:dock-allocation")
        delta = result["options"][1]["delta_from_reference"]
        self.assertEqual(delta["scalar"]["dock_count"], 3)
        self.assertEqual(delta["mapping"]["dock_count_by_zone_role"], {
            "receiving": 0,
            "shipping": 3,
        })
        self.assertFalse(result["claims_best_option"])
        self.assertFalse(result["claims_regulatory_compliance"])

    def test_residential_does_not_gain_warehouse_dock_allocation_metric(self):
        model = with_shipping_docks(warehouse())
        model["meta"]["type"] = "residential"
        metrics = S.measure_plan(model)["metrics"]
        self.assertNotIn("dock_count_by_zone_role", metrics)

    def test_measurement_does_not_mutate_canonical_model(self):
        model = with_shipping_docks(warehouse())
        before = copy.deepcopy(model)
        S.measure_plan(model)
        self.assertEqual(model, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
