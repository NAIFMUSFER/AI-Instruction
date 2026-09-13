#!/usr/bin/env python3
"""Explicit warehouse expansion-reserve regressions for ACS Design Pipeline v2.

The reserve is a canonical warehouse room with the exact role ``expansion``. These
checks use only explicit room/rack/lane rectangles. They do not infer future demand,
capacity, regulatory compliance, fire clearance, equipment envelopes or safety.
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
from test_plan_warehouse_operational_metrics import warehouse

BRIEF = "Warehouse future expansion reserve requested; site width 50 m."
REQUIREMENTS = [
    {"id": "site-width", "source": "requested", "evidence": "50 m",
     "metric": "site_width_m", "expected": 50.0},
]


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": []}


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
    storage["racks"].append({
        "id": "rack_intrusion", "kind": "pallet",
        "x": 39.0, "z": 14.0, "w": 4.0, "d": 4.0,
        "dir": "x", "rows": 1, "depth": 1.0, "bay": 2.0,
        "aisle": 3.0, "levels": 1, "h": 4.0,
    })
    storage["lanes"] = [{
        "id": "lane_intrusion", "kind": "forklift",
        "x": 39.0, "z": 16.0, "w": 5.0, "d": 2.0, "dir": "x",
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

    def test_explicit_rack_and_lane_intrusions_fail_with_measured_evidence(self):
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

    def test_review_blocks_known_reserve_occupation(self):
        ws = P.PlanWorkspace(verified)
        rev = ws.propose(add_intrusions(with_reserve()), brief=BRIEF,
                         requirements=REQUIREMENTS, expected_head=None,
                         note="intrude future expansion reserve")
        out = ws.review(rev.id)
        self.assertIn("EXPANSION_RESERVE_OCCUPIED",
                      {item["code"] for item in out["issues"]})
        self.assertEqual(out["scopes"]["warehouse_expansion_reserve"], "FAIL")
        self.assertFalse(out["can_approve"])

    def test_clean_reserve_can_pass_concept_review_without_compliance_claim(self):
        ws = P.PlanWorkspace(verified)
        rev = ws.propose(with_reserve(), brief=BRIEF, requirements=REQUIREMENTS,
                         expected_head=None, note="preserve future expansion reserve")
        out = ws.review(rev.id)
        self.assertEqual(out["scopes"]["warehouse_expansion_reserve"], "PASS")
        self.assertTrue(out["can_approve"])
        self.assertEqual(out["scopes"]["regulatory_compliance"], "NOT_VERIFIED")

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
