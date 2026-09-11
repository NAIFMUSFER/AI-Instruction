#!/usr/bin/env python3
"""Approved-baseline 3D handoff contracts; no provider or network calls."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_handoff as H
from acs_plan_review import PlanError, PlanWorkspace

BRIEF = "أرض بعرض 20 متر ومخطط معتمد قبل التوليد ثلاثي الأبعاد"


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"}, "issues": []}


def residential_model():
    return {
        "meta": {"type": "residential", "name": "baseline-home"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 3.2, "wall_h": 3.0, "wall_t": 0.15,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "living", "role": "living", "rect": [0.0, 0.0, 6.0, 5.0],
             "doors": [], "windows": []},
            {"id": "bed", "role": "bedroom", "rect": [6.0, 0.0, 4.0, 4.0],
             "doors": [], "windows": []},
        ]}},
    }


def warehouse_model():
    return {
        "meta": {"type": "warehouse", "name": "baseline-warehouse"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 8.0, "wall_h": 7.5, "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "storage", "role": "storage", "walls": "none",
             "rect": [0.0, 0.0, 20.0, 20.0],
             "doors": [], "windows": [],
             "racks": [{"id": "rack_a", "kind": "pallet", "x": 1.0, "z": 1.0,
                        "w": 8.0, "d": 18.0, "dir": "z", "rows": 2,
                        "aisle": 3.4, "levels": 4, "h": 8.0}],
             "docks": [{"id": "dock_n1", "edge": "N", "offset": 4.0,
                        "width": 3.6, "height": 4.2, "count": 1, "pitch": 5.4}],
             "lanes": [{"id": "aisle_main", "kind": "forklift", "x": 8.5,
                        "z": 0.0, "w": 3.0, "d": 20.0, "dir": "z"}],
             "stations": []},
        ]}},
    }


def program():
    return [{"id": "width", "metric": "site_width_m", "expected": 20.0,
             "source": "requested", "evidence": "20"}]


def workspace_with(model, approve=True):
    ws = PlanWorkspace(verified)
    rev = ws.propose(model, brief=BRIEF, requirements=program(), expected_head=None,
                     note="initial reviewed plan")
    if approve:
        ws.approve(rev.id, expected_head=rev.id, actor_label="test-engineer",
                   confirmed=True, acknowledge_concept_only=True)
    return ws, rev


class Approved3DHandoffTests(unittest.TestCase):
    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def test_draft_fails_before_compiler_call(self):
        ws, rev = workspace_with(residential_model(), approve=False)
        called = []
        def fake(_building, _path):
            called.append(True)
            return 0, 0
        with tempfile.TemporaryDirectory() as td:
            self.assertCode("APPROVAL_REQUIRED", lambda: H.compile_approved_baseline(
                ws, rev.id, Path(td) / "draft.gltf", compiler=fake))
        self.assertEqual(called, [])

    def test_exact_approved_model_is_compiled_and_receipted(self):
        ws, rev = workspace_with(residential_model())
        seen = []
        def fake(building, path):
            seen.append(copy.deepcopy(building))
            Path(path).write_text(json.dumps({"asset": {"version": "2.0"}, "nodes": []}),
                                  encoding="utf-8")
            return 7, 1234
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "approved.gltf"
            receipt = H.compile_approved_baseline(ws, rev.id, out, compiler=fake)
            self.assertEqual(seen, [residential_model()])
            self.assertEqual(receipt["revision_id"], rev.id)
            self.assertEqual(receipt["model_hash"], rev.model_hash)
            self.assertEqual(receipt["provider_calls"], 0)
            self.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")
            self.assertEqual(receipt["structural_safety"], "NOT_VERIFIED")
            self.assertTrue(Path(str(out) + ".baseline.json").exists())
            marker = json.loads(out.read_text(encoding="utf-8"))["extras"]["acs_plan_baseline"]
            self.assertEqual(marker["model_hash"], rev.model_hash)
            self.assertTrue(H.verify_compiled_artifact(out)["ok"])

    def test_compiler_mutation_fails_closed_and_publishes_nothing(self):
        ws, rev = workspace_with(residential_model())
        def mutating(building, path):
            building["site"]["w"] = 999
            Path(path).write_text('{"asset":{"version":"2.0"}}', encoding="utf-8")
            return 1, 1
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "mutated.gltf"
            self.assertCode("COMPILER_MUTATED_BASELINE", lambda: H.compile_approved_baseline(
                ws, rev.id, out, compiler=mutating))
            self.assertFalse(out.exists())
            self.assertFalse(Path(str(out) + ".baseline.json").exists())

    def test_artifact_tamper_is_detected(self):
        ws, rev = workspace_with(residential_model())
        def fake(_building, path):
            Path(path).write_text('{"asset":{"version":"2.0"}}', encoding="utf-8")
            return 1, 12
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "artifact.gltf"
            H.compile_approved_baseline(ws, rev.id, out, compiler=fake)
            out.write_text(out.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            self.assertCode("ARTIFACT_CHANGED", lambda: H.verify_compiled_artifact(out))

    def test_existing_output_requires_explicit_overwrite(self):
        ws, rev = workspace_with(residential_model())
        def fake(_building, path):
            Path(path).write_text('{"asset":{"version":"2.0"}}', encoding="utf-8")
            return 1, 12
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "artifact.gltf"
            H.compile_approved_baseline(ws, rev.id, out, compiler=fake)
            self.assertCode("OUTPUT_EXISTS", lambda: H.compile_approved_baseline(
                ws, rev.id, out, compiler=fake))
            second = H.compile_approved_baseline(ws, rev.id, out, compiler=fake, overwrite=True)
            self.assertEqual(second["revision_id"], rev.id)

    def test_previous_approved_baseline_survives_new_draft(self):
        ws, rev = workspace_with(residential_model())
        changed = residential_model()
        changed["floors"]["ground"]["rooms"][1]["rect"] = [6.0, 0.0, 5.0, 4.0]
        new = ws.propose(changed, brief=BRIEF, requirements=program(), expected_head=ws.head,
                         note="unapproved bedroom enlargement")
        self.assertNotEqual(new.id, rev.id)
        def fake(_building, path):
            Path(path).write_text('{"asset":{"version":"2.0"}}', encoding="utf-8")
            return 1, 12
        with tempfile.TemporaryDirectory() as td:
            receipt = H.compile_approved_baseline(ws, rev.id, Path(td) / "old.gltf", compiler=fake)
        self.assertEqual(receipt["revision_id"], rev.id)
        self.assertCode("APPROVAL_REQUIRED", lambda: ws.handoff(new.id))

    def test_real_residential_compiler_accepts_exact_approved_baseline(self):
        ws, rev = workspace_with(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "residential.gltf"
            receipt = H.compile_approved_baseline(ws, rev.id, out)
            gltf = json.loads(out.read_text(encoding="utf-8"))
            self.assertGreater(receipt["compiler_node_count"], 0)
            self.assertEqual(gltf["extras"]["acs_plan_baseline"]["model_hash"], rev.model_hash)
            self.assertTrue(H.verify_compiled_artifact(out)["ok"])

    def test_real_warehouse_compiler_keeps_industrial_rack_dock_geometry(self):
        ws, rev = workspace_with(warehouse_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "warehouse.gltf"
            receipt = H.compile_approved_baseline(ws, rev.id, out)
            gltf = json.loads(out.read_text(encoding="utf-8"))
            names = [str(n.get("name", "")) for n in gltf.get("nodes", []) if isinstance(n, dict)]
            self.assertGreater(receipt["compiler_node_count"], 0)
            self.assertTrue(any("rack" in name for name in names), names[:20])
            self.assertTrue(any("dock" in name for name in names), names[:20])
            self.assertEqual(gltf["extras"]["acs_plan_baseline"]["revision_id"], rev.id)
            self.assertTrue(H.verify_compiled_artifact(out)["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
