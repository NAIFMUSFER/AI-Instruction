#!/usr/bin/env python3
"""Red-first contract for semantic-lock-bound approved 3D handoff.

Synthetic warehouse only. The approved 3D boundary must accept PlanLockWorkspace
without weakening legacy PlanWorkspace support, and must carry the exact engineer
lock binding into both the hash-bound sidecar and embedded glTF marker.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_lock_binding import PlanLockWorkspace, SCHEMA as LOCK_SCHEMA
from tools.acs_plan_handoff import compile_approved_baseline, verify_compiled_artifact


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"}, "issues": []}


def warehouse():
    return {
        "meta": {"type": "warehouse", "name": "lock-bound-3d"},
        "site": {"w": 30.0, "d": 30.0},
        "floor_height": 8.0, "wall_h": 7.5, "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [{
            "id": "storage", "role": "storage", "walls": "none",
            "rect": [0.0, 0.0, 30.0, 30.0],
            "racks": [{
                "id": "rack_a", "kind": "pallet", "x": 1.0, "z": 1.0,
                "w": 10.0, "d": 24.0, "dir": "z", "rows": 2,
                "depth": 1.1, "bay": 2.7, "aisle": 3.4, "levels": 4, "h": 7.0,
            }],
            "docks": [], "lanes": [], "stations": [],
            "doors": [], "windows": [], "objects": [], "points": [], "furniture": [],
        }]}}
    }


def compiler(_building, out_path):
    Path(out_path).write_text(json.dumps({"asset": {"version": "2.0"}}), encoding="utf-8")
    return (1, 0)


class Approved3DLockBindingTests(unittest.TestCase):
    def test_lock_bound_workspace_reaches_3d_with_exact_lock_receipt(self):
        ws = PlanLockWorkspace(verified)
        rev = ws.propose(warehouse(), brief="مستودع مع رف مثبت",
                         requirements=[], expected_head=None, note="initial")
        rev = ws.replace_semantic_locks([{
            "kind": "element", "template": "ground", "room_id": "storage",
            "collection": "racks", "element_id": "rack_a",
        }], expected_head=rev.id, note="engineer locks rack A")
        ws.approve(rev.id, expected_head=rev.id, actor_label="test-engineer",
                   confirmed=True, acknowledge_concept_only=True)
        bound = ws.get(rev.id)

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "approved.gltf"
            receipt = compile_approved_baseline(ws, rev.id, out, compiler=compiler)
            self.assertEqual(receipt["lock_binding_schema"], LOCK_SCHEMA)
            self.assertEqual(receipt["bound_content_hash"], bound.bound_content_hash)
            self.assertEqual(receipt["semantic_lock_manifest_hash"], bound.semantic_lock_manifest_hash)
            self.assertEqual(receipt["semantic_lock_count"], 1)

            gltf = json.loads(out.read_text(encoding="utf-8"))
            marker = gltf["extras"]["acs_plan_baseline"]
            self.assertEqual(marker["lock_binding_schema"], LOCK_SCHEMA)
            self.assertEqual(marker["bound_content_hash"], bound.bound_content_hash)
            self.assertEqual(marker["semantic_lock_manifest_hash"], bound.semantic_lock_manifest_hash)
            self.assertEqual(marker["semantic_lock_count"], 1)
            self.assertTrue(verify_compiled_artifact(out)["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
