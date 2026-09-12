#!/usr/bin/env python3
"""Warehouse lane-centerline Program constraint regressions for ACS Design Pipeline v2.

These constraints consume only the already-measured
``lane_centerline_length_by_kind_m`` geometry. They do not reinterpret declared
lane centerlines as routed travel, clearance, traffic-safety, egress, throughput,
or regulatory compliance.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_review as P
from test_plan_warehouse_operational_metrics import warehouse

BRIEF = (
    "Warehouse lane geometry targets under review: forklift 21 m, forklift 20 m, "
    "forklift 19 m, expansion 1 m, invalid-target."
)


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": []}


def req(rid, metric, expected, kind):
    evidence = f"{expected:g} m" if type(expected) in (int, float) and not isinstance(expected, bool) else "invalid-target"
    return {"id": rid, "source": "requested", "evidence": evidence,
            "metric": metric, "expected": expected, "kind": kind}


def review(model, requirements):
    ws = P.PlanWorkspace(verified)
    rev = ws.propose(model, brief=BRIEF, requirements=requirements,
                     expected_head=None, note="warehouse lane-length constraints")
    return ws.review(rev.id)


class WarehouseLaneLengthConstraintTests(unittest.TestCase):
    @staticmethod
    def codes(result):
        return {item["code"] for item in result["issues"]}

    def test_minimum_lane_centerline_uses_measured_kind_total(self):
        failing = review(warehouse(), [
            req("forklift-min", "min_lane_centerline_length_m", 21.0, "forklift"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(failing))
        self.assertFalse(failing["can_approve"])

        passing = review(warehouse(), [
            req("forklift-min", "min_lane_centerline_length_m", 20.0, "forklift"),
        ])
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(passing))
        self.assertTrue(passing["can_approve"])

    def test_maximum_lane_centerline_uses_measured_kind_total(self):
        failing = review(warehouse(), [
            req("forklift-max", "max_lane_centerline_length_m", 19.0, "forklift"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(failing))

        passing = review(warehouse(), [
            req("forklift-max", "max_lane_centerline_length_m", 20.0, "forklift"),
        ])
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(passing))
        self.assertTrue(passing["can_approve"])

    def test_absent_kind_is_measured_zero_only_when_lane_geometry_is_complete(self):
        out = review(warehouse(), [
            req("expansion-min", "min_lane_centerline_length_m", 1.0, "expansion"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(out))
        self.assertNotIn("REQUIREMENT_NOT_MEASURABLE", self.codes(out))

    def test_missing_lane_orientation_fails_closed_instead_of_using_partial_total(self):
        out = review(warehouse(include_lane_dir=False), [
            req("forklift-min", "min_lane_centerline_length_m", 20.0, "forklift"),
        ])
        self.assertIn("REQUIREMENT_NOT_MEASURABLE", self.codes(out))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(out))

    def test_expectation_must_be_finite_nonnegative_number(self):
        for expected in (-0.01, True, "20"):
            with self.subTest(expected=expected):
                out = review(warehouse(), [
                    req("forklift-min", "min_lane_centerline_length_m", expected, "forklift"),
                ])
                self.assertIn("INVALID_EXPECTATION", self.codes(out))

    def test_invalid_lane_kind_selector_is_rejected(self):
        out = review(warehouse(), [
            req("forklift-min", "min_lane_centerline_length_m", 20.0, ""),
        ])
        self.assertIn("INVALID_REQUIREMENT_SELECTOR", self.codes(out))

    def test_lane_centerline_constraints_are_warehouse_only(self):
        model = warehouse()
        model["meta"]["type"] = "residential"
        out = review(model, [
            req("forklift-min", "min_lane_centerline_length_m", 20.0, "forklift"),
        ])
        self.assertIn("REQUIREMENT_METRIC_NOT_APPLICABLE", self.codes(out))

    def test_constraint_does_not_turn_lane_geometry_into_travel_or_compliance_claim(self):
        out = review(warehouse(), [
            req("forklift-min", "min_lane_centerline_length_m", 20.0, "forklift"),
        ])
        self.assertIsNone(out["metrics"].get("travel_distance_m"))
        self.assertEqual(out["scopes"]["regulatory_compliance"], "NOT_VERIFIED")
        self.assertEqual(out["scopes"]["structural_safety"], "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
