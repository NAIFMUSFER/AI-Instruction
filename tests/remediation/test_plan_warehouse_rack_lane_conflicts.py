#!/usr/bin/env python3
"""Measured rack/lane conflict regressions for ACS Design Pipeline v2.

Only explicit canonical rectangles inside the same warehouse room are measured.
The resulting overlap areas are geometric conflict indicators, not proof of safe
clearance, traffic separation, fire-code compliance, storage capacity or throughput.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_options as O
import acs_plan_review as P
import acs_plan_scorecard as S
from test_plan_scorecard import warehouse_model

BRIEF = "Warehouse racks and forklift lanes must not geometrically overlap."


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": []}


def with_storage_lane(*, x=0.0, z=0.0, w=10.0, d=3.0):
    model = warehouse_model()
    storage = model["floors"]["ground"]["rooms"][1]
    storage["lanes"] = [{"id": "forklift_storage", "kind": "forklift",
                         "x": x, "z": z, "w": w, "d": d, "dir": "x"}]
    return model


def review(model, requirements):
    ws = P.PlanWorkspace(verified)
    rev = ws.propose(model, brief=BRIEF, requirements=requirements,
                     expected_head=None, note="measure rack/lane conflicts")
    return ws.review(rev.id)


def req(rid, metric, expected, **extra):
    row = {"id": rid, "source": "requested", "evidence": "overlap",
           "metric": metric, "expected": expected}
    row.update(extra)
    return row


class WarehouseRackLaneConflictTests(unittest.TestCase):
    @staticmethod
    def codes(result):
        return {item["code"] for item in result["issues"]}

    def test_scorecard_measures_rack_lane_overlap_from_explicit_room_relative_rectangles(self):
        result = S.measure_plan(with_storage_lane())
        metrics = result["metrics"]
        self.assertEqual(metrics["rack_lane_overlap_area_by_lane_kind_m2"], {"forklift": 16.0})
        self.assertEqual(metrics["rack_overlap_area_m2"], 0.0)
        self.assertFalse(result["claims_regulatory_compliance"])
        self.assertIsNone(metrics["pedestrian_vehicle_separation_compliance"])

    def test_scorecard_measures_pairwise_rack_overlap_without_calling_it_clearance(self):
        model = with_storage_lane(x=18.0, w=2.0)
        model["floors"]["ground"]["rooms"][1]["racks"][1]["x"] = 8.0
        metrics = S.measure_plan(model)["metrics"]
        self.assertEqual(metrics["rack_overlap_area_m2"], 18.0)
        self.assertEqual(metrics["rack_lane_overlap_area_by_lane_kind_m2"], {})

    def test_incomplete_rack_position_fails_conflict_measurements_closed(self):
        model = with_storage_lane()
        del model["floors"]["ground"]["rooms"][1]["racks"][0]["x"]
        metrics = S.measure_plan(model)["metrics"]
        self.assertIsNone(metrics["rack_overlap_area_m2"])
        self.assertIsNone(metrics["rack_lane_overlap_area_by_lane_kind_m2"])
        self.assertEqual(metrics["rack_declared_footprint_area_m2"], 288.0)

    def test_program_can_constrain_explicit_rack_lane_overlap_without_claiming_compliance(self):
        bad = review(with_storage_lane(), [
            req("rack-lane", "max_rack_lane_overlap_area_m2", 0.0, kind="forklift"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(bad))
        self.assertFalse(bad["can_approve"])

        good = review(with_storage_lane(x=18.0, w=2.0), [
            req("rack-lane", "max_rack_lane_overlap_area_m2", 0.0, kind="forklift"),
        ])
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(good))
        self.assertTrue(good["can_approve"])

    def test_program_can_constrain_pairwise_rack_overlap(self):
        model = with_storage_lane(x=18.0, w=2.0)
        model["floors"]["ground"]["rooms"][1]["racks"][1]["x"] = 8.0
        out = review(model, [req("rack-rack", "max_rack_overlap_area_m2", 0.0)])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(out))
        self.assertFalse(out["can_approve"])

    def test_unknown_geometry_is_not_treated_as_zero_by_program(self):
        model = with_storage_lane()
        del model["floors"]["ground"]["rooms"][1]["racks"][0]["z"]
        out = review(model, [
            req("rack-lane", "max_rack_lane_overlap_area_m2", 0.0, kind="forklift"),
        ])
        self.assertIn("REQUIREMENT_NOT_MEASURABLE", self.codes(out))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(out))

    def test_option_comparison_exposes_only_measured_conflict_deltas(self):
        a = with_storage_lane()
        b = with_storage_lane(x=18.0, w=2.0)
        b["floors"]["ground"]["rooms"][1]["racks"][1]["x"] = 8.0
        result = O.compare_options([
            {"id": "A", "model": a},
            {"id": "B", "model": b},
        ], declared_program_receipt="warehouse-program-v1")
        delta = result["options"][1]["delta_from_reference"]
        self.assertEqual(delta["mapping"]["rack_lane_overlap_area_by_lane_kind_m2"], {"forklift": -16.0})
        self.assertEqual(delta["scalar"]["rack_overlap_area_m2"], 18.0)
        self.assertFalse(result["claims_best_option"])

    def test_residential_typology_does_not_gain_warehouse_conflict_metrics(self):
        model = with_storage_lane()
        model["meta"]["type"] = "residential"
        metrics = S.measure_plan(model)["metrics"]
        self.assertNotIn("rack_overlap_area_m2", metrics)
        self.assertNotIn("rack_lane_overlap_area_by_lane_kind_m2", metrics)

    def test_measurement_does_not_mutate_canonical_model(self):
        model = with_storage_lane()
        before = copy.deepcopy(model)
        S.measure_plan(model)
        self.assertEqual(model, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
