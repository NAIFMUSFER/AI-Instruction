#!/usr/bin/env python3
"""Approved-baseline warehouse station geometry must never be invented downstream."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_review import PlanError, PlanWorkspace
from tools import acs_plan_handoff as H

BRIEF = "مستودع بعرض 20 متر ومحطة تشغيل محددة هندسياً قبل اعتماد المخطط"


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"}, "issues": []}


def warehouse_model():
    return {
        "meta": {"type": "warehouse", "name": "explicit-station-baseline"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 8.0,
        "wall_h": 7.5,
        "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [{
            "id": "packing",
            "role": "packing",
            "walls": "none",
            "rect": [0.0, 0.0, 20.0, 20.0],
            "doors": [],
            "windows": [],
            "racks": [],
            "lanes": [],
            "stations": [{
                "id": "station-a",
                "kind": "pack",
                "x": 2.0,
                "z": 3.0,
                "w": 1.8,
                "d": 0.9,
                "h": 0.9,
                "pitch": 2.6,
                "dir": "x",
                "count": 2,
            }],
            "docks": [],
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
        note="approved explicit station geometry",
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


class ApprovedWarehouseStationGeometryTests(unittest.TestCase):
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

    def station(self, model):
        return model["floors"]["ground"]["rooms"][0]["stations"][0]

    def test_complete_explicit_station_geometry_passes_unchanged(self):
        model = warehouse_model()
        receipt, calls = self.compile(model)
        self.assertEqual(calls, [model])
        self.assertEqual(receipt["provider_calls"], 0)
        self.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")

    def test_missing_station_defaults_fail_before_compiler(self):
        for key in ("kind", "x", "z", "w", "d", "h", "pitch", "dir", "count"):
            with self.subTest(key=key):
                model = warehouse_model()
                del self.station(model)[key]
                self.assertFailsBeforeCompiler(model)

    def test_station_count_clamping_is_not_allowed(self):
        for value in (0, 61):
            with self.subTest(count=value):
                model = warehouse_model()
                self.station(model)["count"] = value
                self.assertFailsBeforeCompiler(model, expected="DOWNSTREAM_GEOMETRY_INVALID")

    def test_unknown_station_kind_and_implicit_direction_are_not_allowed(self):
        model = warehouse_model()
        self.station(model)["kind"] = "future-unknown-kind"
        self.assertFailsBeforeCompiler(model, expected="DOWNSTREAM_GEOMETRY_INVALID")
        model = warehouse_model()
        self.station(model)["dir"] = "north"
        self.assertFailsBeforeCompiler(model, expected="DOWNSTREAM_GEOMETRY_INVALID")

    def test_invalid_station_collection_fails_before_compiler(self):
        model = warehouse_model()
        model["floors"]["ground"]["rooms"][0]["stations"] = {"station-a": self.station(model)}
        self.assertFailsBeforeCompiler(model, expected="DOWNSTREAM_GEOMETRY_INVALID")


if __name__ == "__main__":
    unittest.main(verbosity=2)
