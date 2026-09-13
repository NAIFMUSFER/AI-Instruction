#!/usr/bin/env python3
"""Approved-baseline warehouse rack geometry must never be invented downstream."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_review import PlanError, PlanWorkspace
from tools import acs_plan_handoff as H

BRIEF = "مستودع بعرض 20 متر وبرفوف محددة هندسياً قبل اعتماد المخطط"


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"}, "issues": []}


def warehouse_model():
    return {
        "meta": {"type": "warehouse", "name": "explicit-rack-baseline"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 8.0,
        "wall_h": 7.5,
        "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [{
            "id": "storage",
            "role": "storage",
            "walls": "none",
            "rect": [0.0, 0.0, 20.0, 20.0],
            "doors": [],
            "windows": [],
            "racks": [{
                "id": "rack-a",
                "kind": "pallet",
                "x": 1.0,
                "z": 1.0,
                "w": 8.0,
                "d": 18.0,
                "dir": "z",
                "rows": 2,
                "depth": 1.10,
                "bay": 2.70,
                "aisle": 3.40,
                "levels": 4,
                "h": 8.0,
            }],
            "lanes": [],
            "stations": [],
            "docks": [{
                "id": "dock-n1",
                "edge": "N",
                "offset": 4.0,
                "width": 3.6,
                "height": 4.2,
                "count": 1,
                "pitch": 5.4,
            }],
        }]}},
    }


def workspace(model):
    ws = PlanWorkspace(verified)
    rev = ws.propose(
        model,
        brief=BRIEF,
        requirements=[{
            "id": "site-width",
            "metric": "site_width_m",
            "expected": 20.0,
            "source": "requested",
            "evidence": "20 متر",
        }],
        expected_head=None,
        note="approved explicit rack geometry",
    )
    ws.approve(
        rev.id,
        expected_head=rev.id,
        actor_label="test-engineer",
        confirmed=True,
        acknowledge_concept_only=True,
    )
    return ws, rev


def fake_compiler(calls):
    def compile_(building, path):
        calls.append(copy.deepcopy(building))
        Path(path).write_text('{"asset":{"version":"2.0"}}', encoding="utf-8")
        return 1, 12
    return compile_


class ApprovedWarehouseRackGeometryTests(unittest.TestCase):
    def assertCode(self, expected, fn):
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, expected)

    def compile(self, model):
        ws, rev = workspace(model)
        calls = []
        with tempfile.TemporaryDirectory() as td:
            receipt = H.compile_approved_baseline(
                ws,
                rev.id,
                Path(td) / "warehouse.gltf",
                compiler=fake_compiler(calls),
            )
        return receipt, calls

    def assertFailsBeforeCompiler(self, model, expected="DOWNSTREAM_GEOMETRY_NOT_SPECIFIED"):
        ws, rev = workspace(model)
        calls = []
        with tempfile.TemporaryDirectory() as td:
            self.assertCode(
                expected,
                lambda: H.compile_approved_baseline(
                    ws,
                    rev.id,
                    Path(td) / "warehouse.gltf",
                    compiler=fake_compiler(calls),
                ),
            )
        self.assertEqual(calls, [])

    def test_complete_explicit_rack_geometry_passes_unchanged(self):
        model = warehouse_model()
        receipt, calls = self.compile(model)
        self.assertEqual(calls, [model])
        self.assertEqual(receipt["provider_calls"], 0)
        self.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")

    def test_missing_rack_dimension_fails_before_compiler(self):
        for key in ("depth", "bay", "h", "aisle"):
            with self.subTest(key=key):
                model = warehouse_model()
                del model["floors"]["ground"]["rooms"][0]["racks"][0][key]
                self.assertFailsBeforeCompiler(model)

    def test_missing_rack_placement_or_extent_fails_before_compiler(self):
        for key in ("x", "z", "w", "d", "dir", "rows", "levels"):
            with self.subTest(key=key):
                model = warehouse_model()
                del model["floors"]["ground"]["rooms"][0]["racks"][0][key]
                self.assertFailsBeforeCompiler(model)

    def test_compiler_clamping_is_not_allowed_for_approved_racks(self):
        cases = (("levels", 12), ("rows", 45), ("w", 25.0), ("d", 25.0))
        for key, value in cases:
            with self.subTest(key=key):
                model = warehouse_model()
                model["floors"]["ground"]["rooms"][0]["racks"][0][key] = value
                self.assertFailsBeforeCompiler(model, expected="DOWNSTREAM_GEOMETRY_INVALID")


if __name__ == "__main__":
    unittest.main(verbosity=2)
