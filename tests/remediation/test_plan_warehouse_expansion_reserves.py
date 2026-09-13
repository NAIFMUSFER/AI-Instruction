#!/usr/bin/env python3
"""Explicit warehouse expansion-reserve regressions for ACS Design Pipeline v2.

The reserve is a canonical warehouse room with the exact role ``expansion``. These
checks use only explicit room/rack/lane rectangles. Rack/lane coordinates are the
existing canonical room-relative coordinates and are projected to site coordinates
using their owning room rectangle before reserve overlap is measured. The checks do
not infer future demand, capacity, regulatory compliance, fire clearance, equipment
envelopes or safety.
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


def with_reserve(*, rect=None):
    model = warehouse()
    model["floors"]["ground"]["rooms"].append({
        "id": "future_expansion",
        "role": "expansion",
        "rect": list(rect or [40.0, 12.0, 10.0, 12.0]),
    })
    return model


def add_intrusions(model):
    storage = model["floors"]["ground"]["rooms"][1]
    # Storage begins at site x=15. Nested x=24 therefore projects to site x=39.
    storage["racks"].append({
        "id": "rack_intrusion", "kind": "pallet",
        "x": 24.0, "z": 14.0, "w": 4.0, "d": 4.0,
        "dir": "x", "rows": 1, "depth": 1.0, "bay": 2.0,
        "aisle": 3.0, "levels": 1, "h": 4.0,
    })
    storage["lanes"] = [{
        "id": "lane_intrusion", "kind": "forklift",
        "x": 24.0, "z": 16.0, "w": 5.0, "d": 2.0, "dir": "x",
    }]
    return model


class WarehouseExpansionReserveTests(unittest.TestCase):
    def test_clean_explicit_reserve_is_measured_and_passes(self):
        result = S.measure_plan(with_reserve())
        metrics = result["metrics"]
        self.assertEqual(metrics["expansion_reserve_area_m2"], 120.0)
        self.assertEqual(metrics["expansion_reserve_zone_overlap_area_m2"], 0.0)
        self.assertEqual(metrics["expansion_reserve_rack_overlap_area_m2"], 0.0)
        self.assertEqual(metrics["expansion_reserve_lane_overlap_area_by_kind_m2"], {})
        check = result["checks"]["expansion_reserve_preservation"]
        self.assertEqual(check["status"], "PASS")
        self.assertEqual(check["measurement_basis"], "explicit_rectangles")
        self.assertFalse(result["claims_regulatory_compliance"])

    def test_room_relative_rack_and_lane_intrusions_use_owner_origin(self):
        result = S.measure_plan(add_intrusions(with_reserve()))
        metrics = result["metrics"]
        self.assertEqual(metrics["expansion_reserve_rack_overlap_area_m2"], 12.0)
        self.assertEqual(metrics["expansion_reserve_lane_overlap_area_by_kind_m2"], {
            "forklift": 8.0,
        })
        check = result["checks"]["expansion_reserve_preservation"]
        self.assertEqual(check["status"], "FAIL")
        self.assertEqual(
            {(row["element_kind"], row["element_id"], row["overlap_area_m2"])
             for row in check["intrusions"]},
            {("rack", "rack_intrusion", 12.0),
             ("lane:forklift", "lane_intrusion", 8.0)},
        )

    def test_explicit_zone_intrusion_is_measured_separately(self):
        model = with_reserve()
        model["floors"]["ground"]["rooms"][2]["rect"] = [40.0, 10.0, 10.0, 4.0]
        result = S.measure_plan(model)
        self.assertEqual(result["metrics"]["expansion_reserve_zone_overlap_area_m2"], 20.0)
        check = result["checks"]["expansion_reserve_preservation"]
        self.assertEqual(check["status"], "FAIL")
        self.assertIn(
            ("zone", "shipping", 20.0),
            {(row["element_kind"], row["element_id"], row["overlap_area_m2"])
             for row in check["intrusions"]},
        )

    def test_no_declared_reserve_is_not_applicable_not_a_fake_pass(self):
        result = S.measure_plan(warehouse())
        self.assertEqual(result["metrics"]["expansion_reserve_area_m2"], 0.0)
        self.assertEqual(result["checks"]["expansion_reserve_preservation"]["status"],
                         "NOT_APPLICABLE")

    def test_incomplete_intruder_geometry_fails_reserve_check_closed(self):
        model = with_reserve()
        rack = model["floors"]["ground"]["rooms"][1]["racks"][0]
        del rack["x"]
        result = S.measure_plan(model)
        self.assertIsNone(result["metrics"]["expansion_reserve_rack_overlap_area_m2"])
        self.assertEqual(result["checks"]["expansion_reserve_preservation"]["status"],
                         "NOT_VERIFIED")

    def test_options_compare_measured_reserve_area_without_ranking(self):
        a = with_reserve(rect=[40.0, 12.0, 10.0, 12.0])
        b = with_reserve(rect=[42.0, 12.0, 8.0, 12.0])
        result = O.compare_options([
            {"id": "A", "model": a},
            {"id": "B", "model": b},
        ], declared_program_receipt="program:warehouse:expansion")
        delta = result["options"][1]["delta_from_reference"]["scalar"]
        self.assertEqual(delta["expansion_reserve_area_m2"], -24.0)
        self.assertEqual(delta["expansion_reserve_rack_overlap_area_m2"], 0.0)
        self.assertFalse(result["claims_best_option"])
        self.assertFalse(result["claims_regulatory_compliance"])

    def test_residential_does_not_gain_warehouse_reserve_metrics_or_check(self):
        model = with_reserve()
        model["meta"]["type"] = "residential"
        result = S.measure_plan(model)
        self.assertNotIn("expansion_reserve_area_m2", result["metrics"])
        self.assertNotIn("expansion_reserve_preservation", result.get("checks", {}))

    def test_measurement_does_not_mutate_canonical_model(self):
        model = add_intrusions(with_reserve())
        before = copy.deepcopy(model)
        S.measure_plan(model)
        self.assertEqual(model, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
