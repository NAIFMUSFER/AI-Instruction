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
from test_plan_warehouse_operational_metrics import warehouse as operational_warehouse

BRIEF = "Warehouse requires storage, docks, racks, stations, forklift lanes and an expansion reserve."


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

    def test_mep_and_fire_safety_zone_minimums_use_only_explicit_declared_geometry(self):
        model = warehouse_model()
        model["floors"]["ground"]["rooms"].extend([
            {"id": "mep_service", "role": "mep", "rect": [30.0, 10.0, 5.0, 4.0]},
            {"id": "fire_safety_zone", "role": "fire_safety", "rect": [35.0, 10.0, 5.0, 4.0]},
        ])
        good = review([
            requirement("mep-zone", "explicit MEP zone", "min_zone_area_m2", 20.0, role="mep"),
            requirement("fire-zone", "explicit fire-safety zone", "min_zone_area_m2", 20.0,
                        role="fire_safety"),
        ], model=model)
        self.assertTrue(good["can_approve"])
        self.assertNotIn("REQUIREMENT_METRIC_NOT_SUPPORTED", self.codes(good))

        too_large = review([
            requirement("fire-zone", "explicit fire-safety zone", "min_zone_area_m2", 21.0,
                        role="fire_safety")
        ], model=model)
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(too_large))
        self.assertFalse(too_large["can_approve"])

        incomplete = copy.deepcopy(model)
        del incomplete["floors"]["ground"]["rooms"][-1]["rect"]
        unknown = review([
            requirement("fire-zone", "explicit fire-safety zone", "min_zone_area_m2", 20.0,
                        role="fire_safety")
        ], model=incomplete)
        self.assertIn("REQUIREMENT_NOT_MEASURABLE", self.codes(unknown))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(unknown))

        residential = copy.deepcopy(model)
        residential["meta"]["type"] = "residential"
        not_applicable = review([
            requirement("mep-zone", "explicit MEP zone", "min_zone_area_m2", 20.0, role="mep")
        ], model=residential)
        self.assertIn("REQUIREMENT_METRIC_NOT_APPLICABLE", self.codes(not_applicable))
        self.assertFalse(not_applicable["can_approve"])

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

    def test_geometric_rack_positions_requirement_uses_only_explicit_bay_level_geometry(self):
        model = operational_warehouse()
        good = review([
            requirement("rack-positions", "racks", "min_rack_geometric_bay_level_positions", 98)
        ], model=model)
        self.assertTrue(good["can_approve"])
        self.assertNotIn("REQUIREMENT_METRIC_NOT_SUPPORTED", self.codes(good))

        too_large = review([
            requirement("rack-positions", "racks", "min_rack_geometric_bay_level_positions", 99)
        ], model=model)
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(too_large))
        self.assertFalse(too_large["can_approve"])

        incomplete = operational_warehouse()
        del incomplete["floors"]["ground"]["rooms"][1]["racks"][0]["bay"]
        unknown = review([
            requirement("rack-positions", "racks", "min_rack_geometric_bay_level_positions", 98)
        ], model=incomplete)
        self.assertIn("REQUIREMENT_NOT_MEASURABLE", self.codes(unknown))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(unknown))

        residential = operational_warehouse()
        residential["meta"]["type"] = "residential"
        not_applicable = review([
            requirement("rack-positions", "racks", "min_rack_geometric_bay_level_positions", 98)
        ], model=residential)
        self.assertIn("REQUIREMENT_METRIC_NOT_APPLICABLE", self.codes(not_applicable))
        self.assertFalse(not_applicable["can_approve"])

    def test_pedestrian_vehicle_lane_overlap_requirement_uses_only_explicit_lane_geometry(self):
        separated = operational_warehouse()
        good = review([
            requirement("pedestrian-vehicle-separation", "forklift", "max_lane_overlap_area_m2",
                        0.0, kind_a="forklift", kind_b="pedestrian")
        ], model=separated)
        self.assertTrue(good["can_approve"])
        self.assertNotIn("REQUIREMENT_METRIC_NOT_SUPPORTED", self.codes(good))

        overlapping = operational_warehouse()
        overlapping["floors"]["ground"]["rooms"][0]["lanes"][1]["x"] = 10.0
        conflict = review([
            requirement("pedestrian-vehicle-separation", "forklift", "max_lane_overlap_area_m2",
                        0.0, kind_a="forklift", kind_b="pedestrian")
        ], model=overlapping)
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(conflict))
        self.assertFalse(conflict["can_approve"])

        incomplete = operational_warehouse()
        del incomplete["floors"]["ground"]["rooms"][0]["lanes"][1]["w"]
        unknown = review([
            requirement("pedestrian-vehicle-separation", "forklift", "max_lane_overlap_area_m2",
                        0.0, kind_a="forklift", kind_b="pedestrian")
        ], model=incomplete)
        self.assertIn("REQUIREMENT_NOT_MEASURABLE", self.codes(unknown))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(unknown))

        residential = operational_warehouse()
        residential["meta"]["type"] = "residential"
        not_applicable = review([
            requirement("pedestrian-vehicle-separation", "forklift", "max_lane_overlap_area_m2",
                        0.0, kind_a="forklift", kind_b="pedestrian")
        ], model=residential)
        self.assertIn("REQUIREMENT_METRIC_NOT_APPLICABLE", self.codes(not_applicable))
        self.assertFalse(not_applicable["can_approve"])

    def test_configured_route_maximum_uses_only_explicit_polyline(self):
        model = warehouse_model()
        model["routes"] = [{
            "id": "inbound_main",
            "kind": "forklift",
            "from_role": "receiving",
            "to_role": "storage",
            "points": [[2.0, 2.0], [12.0, 2.0], [12.0, 7.0]],
        }]
        within = review([
            requirement("inbound-route", "forklift", "max_configured_route_length_m",
                        15.0, route_id="inbound_main")
        ], model=model)
        self.assertTrue(within["can_approve"])
        self.assertNotIn("REQUIREMENT_METRIC_NOT_SUPPORTED", self.codes(within))

        too_short = review([
            requirement("inbound-route", "forklift", "max_configured_route_length_m",
                        14.0, route_id="inbound_main")
        ], model=model)
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(too_short))
        self.assertFalse(too_short["can_approve"])

        missing_selector = review([
            requirement("inbound-route", "forklift", "max_configured_route_length_m", 15.0)
        ], model=model)
        self.assertIn("INVALID_REQUIREMENT_SELECTOR", self.codes(missing_selector))
        self.assertFalse(missing_selector["can_approve"])

        unknown_route = review([
            requirement("inbound-route", "forklift", "max_configured_route_length_m",
                        15.0, route_id="not_configured")
        ], model=model)
        self.assertIn("REQUIREMENT_NOT_MEASURABLE", self.codes(unknown_route))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(unknown_route))

        invalid = copy.deepcopy(model)
        invalid["routes"][0]["points"] = [[2.0, 2.0]]
        unknown = review([
            requirement("inbound-route", "forklift", "max_configured_route_length_m",
                        15.0, route_id="inbound_main")
        ], model=invalid)
        self.assertIn("REQUIREMENT_NOT_MEASURABLE", self.codes(unknown))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(unknown))

        residential = copy.deepcopy(model)
        residential["meta"]["type"] = "residential"
        not_applicable = review([
            requirement("inbound-route", "forklift", "max_configured_route_length_m",
                        15.0, route_id="inbound_main")
        ], model=residential)
        self.assertIn("REQUIREMENT_METRIC_NOT_APPLICABLE", self.codes(not_applicable))
        self.assertFalse(not_applicable["can_approve"])

    def test_expansion_reserve_minimum_uses_only_explicit_canonical_geometry(self):
        model = warehouse_model()
        model["floors"]["ground"]["rooms"].append({
            "id": "future_expansion",
            "role": "expansion",
            "rect": [0.0, 10.0, 10.0, 12.0],
        })
        good = review([
            requirement("expansion-area", "expansion", "min_expansion_reserve_area_m2", 120.0)
        ], model=model)
        self.assertTrue(good["can_approve"])
        self.assertNotIn("REQUIREMENT_METRIC_NOT_SUPPORTED", self.codes(good))

        too_large = review([
            requirement("expansion-area", "expansion", "min_expansion_reserve_area_m2", 121.0)
        ], model=model)
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(too_large))
        self.assertFalse(too_large["can_approve"])

        absent = review([
            requirement("expansion-area", "expansion", "min_expansion_reserve_area_m2", 1.0)
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(absent))
        self.assertNotIn("REQUIREMENT_NOT_MEASURABLE", self.codes(absent))

        residential = copy.deepcopy(model)
        residential["meta"]["type"] = "residential"
        not_applicable = review([
            requirement("expansion-area", "expansion", "min_expansion_reserve_area_m2", 120.0)
        ], model=residential)
        self.assertIn("REQUIREMENT_METRIC_NOT_APPLICABLE", self.codes(not_applicable))
        self.assertFalse(not_applicable["can_approve"])

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
