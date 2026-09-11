#!/usr/bin/env python3
"""Measured warehouse lane-conflict regressions for ACS Design Pipeline v2.

Synthetic canonical rectangles only. These tests measure overlap between explicitly
named lane kinds; they do not claim traffic-safety, fire-code, clearance or
regulatory compliance and do not invent a vehicle/pedestrian classification.
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

BRIEF = "Warehouse requires pedestrian and forklift lanes with no geometric overlap."
PAIR = "forklift|pedestrian"


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": []}


def requirement(expected=0.0, **extra):
    row = {"id": "lane-separation", "source": "requested", "evidence": "overlap",
           "metric": "max_lane_overlap_area_m2", "expected": expected,
           "kind_a": "forklift", "kind_b": "pedestrian"}
    row.update(extra)
    return row


def review(model, row=None):
    ws = P.PlanWorkspace(verified)
    rev = ws.propose(model, brief=BRIEF, requirements=[row or requirement()],
                     expected_head=None, note="measure lane conflict")
    return ws.review(rev.id)


def separated_model():
    model = warehouse_model()
    lanes = model["floors"]["ground"]["rooms"][0]["lanes"]
    lanes[1]["x"] = 4.0
    return model


class WarehouseLaneConflictTests(unittest.TestCase):
    @staticmethod
    def codes(result):
        return {item["code"] for item in result["issues"]}

    def test_scorecard_measures_pairwise_overlap_from_explicit_lane_rectangles(self):
        result = S.measure_plan(warehouse_model())
        self.assertEqual(result["metrics"]["lane_overlap_area_by_kind_pair_m2"], {PAIR: 10.0})
        self.assertFalse(result["claims_regulatory_compliance"])
        self.assertIsNone(result["metrics"]["pedestrian_vehicle_separation_compliance"])

    def test_separated_explicit_lane_kinds_measure_zero_overlap(self):
        result = S.measure_plan(separated_model())
        self.assertEqual(result["metrics"]["lane_overlap_area_by_kind_pair_m2"], {})

    def test_incomplete_lane_geometry_is_unknown_not_zero(self):
        model = warehouse_model()
        del model["floors"]["ground"]["rooms"][0]["lanes"][1]["w"]
        result = S.measure_plan(model)
        self.assertIsNone(result["metrics"]["lane_overlap_area_by_kind_pair_m2"])

    def test_program_can_require_maximum_overlap_without_claiming_compliance(self):
        bad = review(warehouse_model())
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(bad))
        self.assertFalse(bad["can_approve"])

        good = review(separated_model())
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(good))
        self.assertTrue(good["can_approve"])

    def test_program_overlap_constraint_fails_unknown_when_geometry_is_incomplete(self):
        model = warehouse_model()
        del model["floors"]["ground"]["rooms"][0]["lanes"][0]["d"]
        out = review(model)
        self.assertIn("REQUIREMENT_NOT_MEASURABLE", self.codes(out))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(out))

    def test_program_requires_two_distinct_explicit_lane_kind_selectors(self):
        same = review(warehouse_model(), requirement(kind_b="forklift"))
        missing = review(warehouse_model(), requirement(kind_b=None))
        self.assertIn("INVALID_REQUIREMENT_SELECTOR", self.codes(same))
        self.assertIn("INVALID_REQUIREMENT_SELECTOR", self.codes(missing))

    def test_option_comparison_exposes_measured_lane_conflict_delta(self):
        result = O.compare_options([
            {"id": "A", "model": warehouse_model()},
            {"id": "B", "model": separated_model()},
        ], declared_program_receipt="program-v1")
        delta = result["options"][1]["delta_from_reference"]["mapping"]
        self.assertEqual(delta["lane_overlap_area_by_kind_pair_m2"], {PAIR: -10.0})
        self.assertFalse(result["claims_best_option"])

    def test_non_warehouse_typology_does_not_receive_lane_conflict_metric(self):
        model = warehouse_model()
        model["meta"]["type"] = "residential"
        measured = S.measure_plan(model)
        self.assertNotIn("lane_overlap_area_by_kind_pair_m2", measured["metrics"])
        out = review(model)
        self.assertIn("REQUIREMENT_METRIC_NOT_APPLICABLE", self.codes(out))


if __name__ == "__main__":
    unittest.main(verbosity=2)
