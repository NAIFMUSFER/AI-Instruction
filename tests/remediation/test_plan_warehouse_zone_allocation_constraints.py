#!/usr/bin/env python3
"""Warehouse zone-allocation Program constraint regressions for ACS Design Pipeline v2.

Constraints consume only the measured ``zone_area_ratio_by_role`` contract. They do
not infer missing geometry, invent target ratios, or claim efficiency, safety,
regulatory compliance, storage capacity or throughput.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_review as P
from test_plan_scorecard import warehouse_model

BRIEF = (
    "Warehouse allocation targets under review: storage 70%, storage 60%, "
    "shipping 15%, shipping 20%, expansion 1%. invalid-target"
)


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": []}


def req(rid, metric, expected, role):
    if type(expected) in (int, float) and 0.0 <= expected <= 1.0:
        evidence = f"{expected * 100:g}%"
    else:
        evidence = "invalid-target"
    return {"id": rid, "source": "requested", "evidence": evidence,
            "metric": metric, "expected": expected, "role": role}


def review(model, requirements):
    ws = P.PlanWorkspace(verified)
    rev = ws.propose(model, brief=BRIEF, requirements=requirements,
                     expected_head=None, note="warehouse allocation constraints")
    return ws.review(rev.id)


class WarehouseZoneAllocationConstraintTests(unittest.TestCase):
    @staticmethod
    def codes(result):
        return {item["code"] for item in result["issues"]}

    def test_minimum_zone_ratio_uses_measured_role_share(self):
        failing = review(warehouse_model(), [
            req("storage-min", "min_zone_area_ratio", 0.70, "storage"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(failing))
        self.assertFalse(failing["can_approve"])

        passing = review(warehouse_model(), [
            req("storage-min", "min_zone_area_ratio", 0.60, "storage"),
        ])
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(passing))
        self.assertTrue(passing["can_approve"])

    def test_maximum_zone_ratio_uses_measured_role_share(self):
        failing = review(warehouse_model(), [
            req("shipping-max", "max_zone_area_ratio", 0.15, "shipping"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(failing))

        passing = review(warehouse_model(), [
            req("shipping-max", "max_zone_area_ratio", 0.20, "shipping"),
        ])
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(passing))
        self.assertTrue(passing["can_approve"])

    def test_absent_role_is_measured_zero_only_when_denominator_is_complete(self):
        out = review(warehouse_model(), [
            req("expansion-min", "min_zone_area_ratio", 0.01, "expansion"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(out))
        self.assertNotIn("REQUIREMENT_NOT_MEASURABLE", self.codes(out))

    def test_incomplete_geometry_fails_requirement_closed_instead_of_using_zero(self):
        model = warehouse_model()
        del model["floors"]["ground"]["rooms"][2]["rect"]
        out = review(model, [
            req("storage-min", "min_zone_area_ratio", 0.60, "storage"),
        ])
        self.assertIn("REQUIREMENT_NOT_MEASURABLE", self.codes(out))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(out))

    def test_ratio_expectation_must_be_a_real_fraction(self):
        for expected in (-0.01, 1.01, True, "0.6"):
            with self.subTest(expected=expected):
                out = review(warehouse_model(), [
                    req("storage-min", "min_zone_area_ratio", expected, "storage"),
                ])
                self.assertIn("INVALID_EXPECTATION", self.codes(out))

    def test_invalid_role_selector_is_rejected(self):
        out = review(warehouse_model(), [
            req("storage-min", "min_zone_area_ratio", 0.60, ""),
        ])
        self.assertIn("INVALID_REQUIREMENT_SELECTOR", self.codes(out))

    def test_ratio_constraints_are_warehouse_only(self):
        model = warehouse_model()
        model["meta"]["type"] = "residential"
        out = review(model, [
            req("storage-min", "min_zone_area_ratio", 0.60, "storage"),
        ])
        self.assertIn("REQUIREMENT_METRIC_NOT_APPLICABLE", self.codes(out))

    def test_constraint_does_not_create_regulatory_or_safety_claims(self):
        out = review(warehouse_model(), [
            req("storage-min", "min_zone_area_ratio", 0.60, "storage"),
        ])
        self.assertEqual(out["scopes"]["regulatory_compliance"], "NOT_VERIFIED")
        self.assertEqual(out["scopes"]["structural_safety"], "NOT_VERIFIED")
        self.assertNotIn("storage_capacity_positions", {
            key for key, value in out["metrics"].items() if value not in (None, {}, [])
        })


if __name__ == "__main__":
    unittest.main(verbosity=2)
