#!/usr/bin/env python3
"""Generic measured role-area Program constraints for ACS Design Pipeline v2.

These regressions consume only deterministic ``space_area_by_role_m2`` measurements.
They do not infer missing geometry, invent target areas, or claim regulatory,
structural, accessibility, daylight, fire/life-safety, or architectural compliance.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_review as P
from test_plan_residential_scorecard import residential

BRIEF = (
    "Measured role-area targets under review: majlis 25 m2, majlis 20 m2, "
    "majlis 15 m2, office-majlis 20 m2, missing-role 1 m2, invalid-target"
)


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": []}


def req(rid, metric, expected, role, evidence):
    return {"id": rid, "source": "requested", "evidence": evidence,
            "metric": metric, "expected": expected, "role": role}


def review(model, requirements):
    ws = P.PlanWorkspace(verified)
    rev = ws.propose(model, brief=BRIEF, requirements=requirements,
                     expected_head=None, note="measured role-area constraints")
    return ws.review(rev.id)


class RoleAreaConstraintTests(unittest.TestCase):
    @staticmethod
    def codes(result):
        return {item["code"] for item in result["issues"]}

    def test_minimum_role_area_uses_complete_measured_role_total(self):
        failing = review(residential(), [
            req("majlis-min", "min_space_area_by_role_m2", 25.0, "majlis", "majlis 25 m2"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(failing))
        self.assertFalse(failing["can_approve"])

        passing = review(residential(), [
            req("majlis-min", "min_space_area_by_role_m2", 20.0, "majlis", "majlis 20 m2"),
        ])
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(passing))
        self.assertTrue(passing["can_approve"])

    def test_maximum_role_area_uses_complete_measured_role_total(self):
        failing = review(residential(), [
            req("majlis-max", "max_space_area_by_role_m2", 15.0, "majlis", "majlis 15 m2"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(failing))

        passing = review(residential(), [
            req("majlis-max", "max_space_area_by_role_m2", 20.0, "majlis", "majlis 20 m2"),
        ])
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(passing))
        self.assertTrue(passing["can_approve"])

    def test_absent_role_is_zero_only_when_complete_area_is_measurable(self):
        out = review(residential(), [
            req("missing-min", "min_space_area_by_role_m2", 1.0, "study", "missing-role 1 m2"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(out))
        self.assertNotIn("REQUIREMENT_NOT_MEASURABLE", self.codes(out))

    def test_incomplete_geometry_fails_closed_instead_of_using_partial_role_area(self):
        model = residential()
        del model["floors"]["ground"]["rooms"][1]["rect"]
        out = review(model, [
            req("majlis-min", "min_space_area_by_role_m2", 20.0, "majlis", "majlis 20 m2"),
        ])
        self.assertIn("REQUIREMENT_NOT_MEASURABLE", self.codes(out))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(out))

    def test_role_area_constraints_are_not_residential_only(self):
        model = residential()
        model["meta"]["type"] = "office"
        out = review(model, [
            req("office-majlis-min", "min_space_area_by_role_m2", 20.0, "majlis", "office-majlis 20 m2"),
        ])
        self.assertNotIn("REQUIREMENT_METRIC_NOT_APPLICABLE", self.codes(out))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(out))
        self.assertTrue(out["can_approve"])

    def test_invalid_role_selector_is_rejected(self):
        out = review(residential(), [
            req("bad-role", "min_space_area_by_role_m2", 20.0, "", "majlis 20 m2"),
        ])
        self.assertIn("INVALID_REQUIREMENT_SELECTOR", self.codes(out))

    def test_expectation_must_be_a_nonnegative_real_area(self):
        for expected in (-0.01, True, "20"):
            with self.subTest(expected=expected):
                out = review(residential(), [
                    req("bad-area", "min_space_area_by_role_m2", expected, "majlis", "invalid-target"),
                ])
                self.assertIn("INVALID_EXPECTATION", self.codes(out))


if __name__ == "__main__":
    unittest.main(verbosity=2)
