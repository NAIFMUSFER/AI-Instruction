#!/usr/bin/env python3
"""Warehouse dock-by-zone Program constraint regressions for ACS Design Pipeline v2.

These constraints consume only the measured ``dock_count_by_zone_role`` contract.
They do not infer dock capacity, throughput, queuing, apron geometry, traffic safety,
fire/life-safety compliance, or regulatory compliance. Missing ownership/count data
must remain unmeasurable rather than being converted into a guessed zero.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_review as P
from test_plan_warehouse_operational_metrics import warehouse
from test_plan_warehouse_docks_by_zone import with_shipping_docks

BRIEF = (
    "Warehouse dock allocation targets under review: receiving 3 docks, receiving 2 docks, "
    "shipping 2 docks, shipping 3 docks, expansion 1 docks, invalid-target."
)


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": []}


def req(rid, metric, expected, role):
    valid = type(expected) is int and expected >= 0
    evidence = f"{role} {expected} docks" if valid and role else "invalid-target"
    return {"id": rid, "source": "requested", "evidence": evidence,
            "metric": metric, "expected": expected, "role": role}


def review(model, requirements):
    ws = P.PlanWorkspace(verified)
    rev = ws.propose(model, brief=BRIEF, requirements=requirements,
                     expected_head=None, note="warehouse dock-zone constraints")
    return ws.review(rev.id)


class WarehouseDockZoneConstraintTests(unittest.TestCase):
    @staticmethod
    def codes(result):
        return {item["code"] for item in result["issues"]}

    def test_minimum_dock_count_uses_measured_owning_zone_role(self):
        failing = review(warehouse(), [
            req("receiving-min", "min_dock_count_by_zone_role", 3, "receiving"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(failing))
        self.assertFalse(failing["can_approve"])

        passing = review(warehouse(), [
            req("receiving-min", "min_dock_count_by_zone_role", 2, "receiving"),
        ])
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(passing))
        self.assertTrue(passing["can_approve"])

    def test_maximum_dock_count_uses_measured_owning_zone_role(self):
        model = with_shipping_docks(warehouse())
        failing = review(model, [
            req("shipping-max", "max_dock_count_by_zone_role", 2, "shipping"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(failing))

        passing = review(model, [
            req("shipping-max", "max_dock_count_by_zone_role", 3, "shipping"),
        ])
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(passing))
        self.assertTrue(passing["can_approve"])

    def test_absent_zone_role_is_measured_zero_only_when_mapping_is_complete(self):
        out = review(warehouse(), [
            req("expansion-min", "min_dock_count_by_zone_role", 1, "expansion"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(out))
        self.assertNotIn("REQUIREMENT_NOT_MEASURABLE", self.codes(out))

    def test_unclassified_nonzero_dock_owner_fails_requirement_closed(self):
        model = warehouse()
        del model["floors"]["ground"]["rooms"][0]["role"]
        out = review(model, [
            req("receiving-min", "min_dock_count_by_zone_role", 2, "receiving"),
        ])
        self.assertIn("REQUIREMENT_NOT_MEASURABLE", self.codes(out))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(out))

    def test_expectation_must_be_nonnegative_integer(self):
        for expected in (-1, True, "2"):
            with self.subTest(expected=expected):
                out = review(warehouse(), [
                    req("receiving-min", "min_dock_count_by_zone_role", expected, "receiving"),
                ])
                self.assertIn("INVALID_EXPECTATION", self.codes(out))

    def test_invalid_zone_role_selector_is_rejected(self):
        out = review(warehouse(), [
            req("receiving-min", "min_dock_count_by_zone_role", 2, ""),
        ])
        self.assertIn("INVALID_REQUIREMENT_SELECTOR", self.codes(out))

    def test_dock_zone_constraints_are_warehouse_only(self):
        model = warehouse()
        model["meta"]["type"] = "residential"
        out = review(model, [
            req("receiving-min", "min_dock_count_by_zone_role", 2, "receiving"),
        ])
        self.assertIn("REQUIREMENT_METRIC_NOT_APPLICABLE", self.codes(out))

    def test_constraint_does_not_create_capacity_throughput_or_compliance_claims(self):
        out = review(warehouse(), [
            req("receiving-min", "min_dock_count_by_zone_role", 2, "receiving"),
        ])
        self.assertIsNone(out["metrics"].get("storage_capacity_positions"))
        self.assertIsNone(out["metrics"].get("throughput_per_hour"))
        self.assertEqual(out["scopes"]["regulatory_compliance"], "NOT_VERIFIED")
        self.assertEqual(out["scopes"]["structural_safety"], "NOT_VERIFIED")

    def test_review_does_not_mutate_canonical_model(self):
        model = with_shipping_docks(warehouse())
        before = copy.deepcopy(model)
        review(model, [
            req("shipping-max", "max_dock_count_by_zone_role", 3, "shipping"),
        ])
        self.assertEqual(model, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
