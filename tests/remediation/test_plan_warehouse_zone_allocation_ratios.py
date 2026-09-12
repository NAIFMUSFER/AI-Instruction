#!/usr/bin/env python3
"""Measured warehouse zone-allocation ratio regressions for ACS Design Pipeline v2.

Ratios are descriptive shares of the complete measured canonical room-rectangle area.
They are not GFA/NFA, utilization, efficiency, code compliance or an AI quality score.
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

BRIEF = "Warehouse storage allocation ratio must remain measurable from the approved plan."


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": []}


def review(model, requirements):
    ws = P.PlanWorkspace(verified)
    rev = ws.propose(model, brief=BRIEF, requirements=requirements,
                     expected_head=None, note="measure warehouse zone allocation ratios")
    return ws.review(rev.id)


def req(rid, metric, expected, **extra):
    row = {"id": rid, "source": "requested", "evidence": "ratio",
           "metric": metric, "expected": expected}
    row.update(extra)
    return row


class WarehouseZoneAllocationRatioTests(unittest.TestCase):
    @staticmethod
    def codes(result):
        return {item["code"] for item in result["issues"]}

    def test_scorecard_measures_role_share_from_complete_canonical_area(self):
        result = S.measure_plan(warehouse_model())
        ratios = result["metrics"]["zone_area_ratio_by_role"]
        self.assertEqual(ratios, {
            "receiving": 0.166667,
            "shipping": 0.166667,
            "storage": 0.666667,
        })
        self.assertFalse(result["claims_regulatory_compliance"])

    def test_repeated_template_preserves_same_allocation_ratios(self):
        model = warehouse_model()
        model["levels"].append({"index": 1, "template": "ground"})
        self.assertEqual(
            S.measure_plan(model)["metrics"]["zone_area_ratio_by_role"],
            S.measure_plan(warehouse_model())["metrics"]["zone_area_ratio_by_role"],
        )

    def test_incomplete_space_geometry_fails_ratio_closed_instead_of_publishing_partial_share(self):
        model = warehouse_model()
        del model["floors"]["ground"]["rooms"][2]["rect"]
        result = S.measure_plan(model)
        self.assertIsNone(result["metrics"]["space_rect_area_m2"])
        self.assertIsNone(result["metrics"]["zone_area_by_role_m2"])
        self.assertIsNone(result["metrics"]["zone_area_ratio_by_role"])

    def test_unclassified_area_remains_in_denominator_and_is_not_silently_redistributed(self):
        model = warehouse_model()
        del model["floors"]["ground"]["rooms"][2]["role"]
        metrics = S.measure_plan(model)["metrics"]
        self.assertEqual(metrics["unclassified_zone_area_m2"], 100.0)
        self.assertEqual(metrics["zone_area_ratio_by_role"], {
            "receiving": 0.166667,
            "storage": 0.666667,
        })

    def test_program_can_constrain_explicit_minimum_zone_allocation_ratio(self):
        good = review(warehouse_model(), [
            req("storage-ratio", "min_zone_area_ratio", 0.60, role="storage"),
        ])
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(good))
        self.assertTrue(good["can_approve"])

        bad = review(warehouse_model(), [
            req("storage-ratio", "min_zone_area_ratio", 0.70, role="storage"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(bad))
        self.assertFalse(bad["can_approve"])

    def test_program_can_constrain_explicit_maximum_zone_allocation_ratio(self):
        out = review(warehouse_model(), [
            req("storage-ratio", "max_zone_area_ratio", 0.60, role="storage"),
        ])
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(out))
        self.assertFalse(out["can_approve"])

    def test_unknown_ratio_is_not_treated_as_zero_by_program(self):
        model = warehouse_model()
        del model["floors"]["ground"]["rooms"][0]["rect"]
        out = review(model, [
            req("storage-ratio", "min_zone_area_ratio", 0.60, role="storage"),
        ])
        self.assertIn("REQUIREMENT_NOT_MEASURABLE", self.codes(out))
        self.assertNotIn("REQUIREMENT_MISMATCH", self.codes(out))

    def test_option_comparison_exposes_measured_allocation_ratio_deltas(self):
        a = warehouse_model()
        b = warehouse_model()
        b["floors"]["ground"]["rooms"][1]["rect"] = [10.0, 0.0, 15.0, 20.0]
        b["floors"]["ground"]["rooms"][2]["rect"] = [25.0, 0.0, 15.0, 20.0]
        result = O.compare_options([
            {"id": "A", "model": a},
            {"id": "B", "model": b},
        ], declared_program_receipt="warehouse-program-v1")
        delta = result["options"][1]["delta_from_reference"]["mapping"]
        self.assertAlmostEqual(delta["zone_area_ratio_by_role"]["storage"], -0.166667, places=6)
        self.assertAlmostEqual(delta["zone_area_ratio_by_role"]["shipping"], 0.333333, places=6)
        self.assertFalse(result["claims_best_option"])

    def test_residential_typology_does_not_gain_warehouse_allocation_ratio_metric(self):
        model = warehouse_model()
        model["meta"]["type"] = "residential"
        self.assertNotIn("zone_area_ratio_by_role", S.measure_plan(model)["metrics"])

    def test_measurement_does_not_mutate_canonical_model(self):
        model = warehouse_model()
        before = copy.deepcopy(model)
        S.measure_plan(model)
        self.assertEqual(model, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
