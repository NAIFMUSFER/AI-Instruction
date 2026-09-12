#!/usr/bin/env python3
"""Approved-baseline generic object geometry must never be invented downstream.

This applies to every typology because ``room.objects`` is a shared compiler path.
The tests intentionally exercise only fields consumed by the current 3D compiler;
they do not assert regulatory, structural, accessibility, clearance, or safety rules.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_review import PlanError, PlanWorkspace
from tools import acs_plan_handoff as H

BRIEF = "فيلا بعرض 20 متر وبها كنبة محددة هندسياً قبل اعتماد المخطط"


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"}, "issues": []}


def residential_model():
    return {
        "meta": {"type": "residential", "name": "explicit-object-baseline"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 3.2,
        "wall_h": 3.0,
        "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [{
            "id": "majlis",
            "role": "majlis",
            "rect": [0.0, 0.0, 10.0, 8.0],
            "doors": [],
            "windows": [],
            "objects": [{
                "id": "sofa-a",
                "kind": "sofa",
                "x": 2.0,
                "z": 2.5,
                "y": 0.0,
                "w": 2.2,
                "d": 0.9,
                "h": 0.8,
                "count": 1,
                "pitch": 1.2,
                "dir": "x",
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
        note="approved explicit generic object geometry",
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


class ApprovedObjectGeometryTests(unittest.TestCase):
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
                Path(td) / "building.gltf",
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
                    Path(td) / "building.gltf",
                    compiler=fake_compiler(calls),
                ),
            )
        self.assertEqual(calls, [])

    @staticmethod
    def obj(model):
        return model["floors"]["ground"]["rooms"][0]["objects"][0]

    def test_complete_explicit_object_geometry_passes_unchanged(self):
        model = residential_model()
        receipt, calls = self.compile(model)
        self.assertEqual(calls, [model])
        self.assertEqual(receipt["provider_calls"], 0)
        self.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")

    def test_shared_compiler_defaults_fail_before_3d(self):
        for key in ("kind", "x", "z", "y", "w", "d", "h", "count", "pitch", "dir"):
            with self.subTest(key=key):
                model = residential_model()
                del self.obj(model)[key]
                self.assertFailsBeforeCompiler(model)

    def test_invalid_direction_and_count_fail_before_3d(self):
        for field, value in (("dir", "north"), ("count", 0), ("count", 201)):
            with self.subTest(field=field, value=value):
                model = residential_model()
                self.obj(model)[field] = value
                self.assertFailsBeforeCompiler(model, expected="DOWNSTREAM_GEOMETRY_INVALID")

    def test_nonfinite_geometry_is_already_rejected_before_approval(self):
        for field, value in (("x", float("inf")), ("z", float("nan"))):
            with self.subTest(field=field, value=value):
                model = residential_model()
                self.obj(model)[field] = value
                self.assertCode("NON_FINITE", lambda: workspace(model))

    def test_nonpositive_geometry_fails_before_3d(self):
        for field, value in (("w", 0.0), ("d", -1.0), ("h", 0.0), ("pitch", 0.0)):
            with self.subTest(field=field, value=value):
                model = residential_model()
                self.obj(model)[field] = value
                self.assertFailsBeforeCompiler(model, expected="DOWNSTREAM_GEOMETRY_INVALID")

    def test_panel_vertical_position_must_be_explicit(self):
        for kind in ("tv", "rug", "curtain", "sign"):
            with self.subTest(kind=kind):
                model = residential_model()
                obj = self.obj(model)
                obj["kind"] = kind
                obj["w"], obj["d"], obj["h"] = 1.3, 0.08, 0.75
                # Current compiler otherwise invents a panel vertical position.
                self.assertFailsBeforeCompiler(model)

    def test_malformed_object_collection_remains_provenance_error(self):
        model = residential_model()
        model["floors"]["ground"]["rooms"][0]["objects"] = {"sofa-a": self.obj(model)}
        self.assertFailsBeforeCompiler(model, expected="INVALID_PROVENANCE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
