#!/usr/bin/env python3
"""Warehouse-aware Program-of-Requirements regressions for Plan-first v2.

Synthetic canonical geometry only. These tests require deterministic measurements
already expressible by the warehouse scorecard; they do not assert regulatory,
fire-safety, throughput, equipment-clearance, or engineering compliance.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_review as P
from test_plan_scorecard import warehouse_model

BRIEF = "Warehouse requires storage, docks, racks, stations and forklift lanes."


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": []}


def requirement(rid, evidence, metric, expected, **extra):
    row = {"id": rid, "source": "requested", "evidence": evidence,
           "metric": metric, "expected": expected}
    row.update(extra)
    return row


def review(rows, model=None):
    ws = P.PlanWorkspace(verified)
    rev = ws.propose(model or warehouse_model(), brief=BRIEF, requirements=rows,
                     expected_head=None, note="warehouse program test")
    return ws.review(rev.id)


class WarehouseProgramTests(unittest.TestCase):
    @staticmethod
    def codes(result):
        return {item["code"] for item in result["issues"]}

    def test_min_zone_area_is_measured_from_declared_role_geometry(self):
        good = review([requirement("storage-area", "storage", "min_zone_area_m2",
                                   350.0, role="storage")])
        self.assertTrue(good["can_approve"])
        self.assertNotIn("REQUIREMENT_METRIC_NOT_SUPPORTED", self.codes(good))

        too_large = review([requirement("storage-area", "storage", "min_zone_area_m2",
                                        450.0, role="storage")])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(too_large))
        self.assertFalse(too_large["can_approve"])

    def test_dock_count_supports_total_edge_and_minimum_constraints(self):
        total = review([requirement("dock-total", "docks", "dock_count", 3)])
        north = review([requirement("dock-north", "docks", "dock_count", 2, edge="N")])
        minimum = review([requirement("dock-west", "docks", "min_dock_count", 2, edge="W")])
        self.assertTrue(total["can_approve"])
        self.assertTrue(north["can_approve"])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(minimum))

    def test_rack_station_and_lane_minimums_use_explicit_operational_geometry(self):
        rows = [
            requirement("racks", "racks", "min_rack_group_count", 2),
            requirement("stations", "stations", "min_station_count", 3),
            requirement("forklift", "forklift", "min_lane_area_m2", 25.0,
                        kind="forklift"),
        ]
        result = review(rows)
        self.assertTrue(result["can_approve"])
        self.assertFalse(self.codes(result))

        bad = review([requirement("forklift", "forklift", "min_lane_area_m2", 35.0,
                                  kind="forklift")])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(bad))

    def test_incomplete_dock_data_is_unknown_not_zero_or_partial(self):
        model = warehouse_model()
        model["floors"]["ground"]["rooms"][0]["docks"][0]["count"] = "2"
        result = review([requirement("dock-total", "docks", "dock_count", 3)], model=model)
        self.assertIn("REQUIREMENT_NOT_MEASURABLE", self.codes(result))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(result))

    def test_warehouse_metrics_do_not_apply_to_residential_models(self):
        model = warehouse_model()
        model["meta"]["type"] = "residential"
        result = review([requirement("dock-total", "docks", "dock_count", 3)], model=model)
        self.assertIn("REQUIREMENT_METRIC_NOT_APPLICABLE", self.codes(result))
        self.assertFalse(result["can_approve"])

    def test_invalid_operational_selector_fails_closed(self):
        result = review([requirement("dock-edge", "docks", "dock_count", 1, edge="Q")])
        self.assertIn("INVALID_REQUIREMENT_SELECTOR", self.codes(result))
        self.assertFalse(result["can_approve"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
