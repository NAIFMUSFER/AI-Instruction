#!/usr/bin/env python3
"""Semantic lock regressions: stable IDs only, no provider/network calls."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_bridge as B
import acs_plan_semantic_locks as L
from acs_plan_review import PlanError, PlanWorkspace


def model():
    return {
        "meta": {"type": "warehouse"},
        "site": {"w": 40.0, "d": 25.0},
        "floor_height": 8.0, "wall_h": 7.5, "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "receiving", "role": "receiving", "rect": [0.0, 0.0, 10.0, 10.0],
             "docks": [
                 {"id": "dock_n1", "edge": "N", "offset": 2.0, "width": 3.6, "height": 4.2},
                 {"id": "dock_n2", "edge": "N", "offset": 6.0, "width": 3.6, "height": 4.2}],
             "stations": [{"id": "qa_1", "kind": "qa", "x": 2.0, "z": 5.0}]},
            {"id": "storage", "role": "storage", "rect": [10.0, 0.0, 20.0, 20.0],
             "racks": [
                 {"id": "rack_a", "kind": "pallet", "x": 1.0, "z": 1.0,
                  "w": 8.0, "d": 18.0, "dir": "z", "rows": 2, "levels": 4, "h": 8.0},
                 {"id": "rack_b", "kind": "pallet", "x": 10.0, "z": 1.0,
                  "w": 8.0, "d": 18.0, "dir": "z", "rows": 2, "levels": 4, "h": 8.0}],
             "lanes": [
                 {"id": "aisle_main", "kind": "forklift", "x": 8.5, "z": 0.0,
                  "w": 3.0, "d": 20.0, "dir": "z"},
                 {"id": "ped_1", "kind": "pedestrian", "x": 0.0, "z": 0.0,
                  "w": 1.0, "d": 20.0, "dir": "z"}]},
        ]}},
    }


def selector(collection, element_id, room_id="storage"):
    return {"kind": "element", "template": "ground", "room_id": room_id,
            "collection": collection, "element_id": element_id}


class SemanticLockTests(unittest.TestCase):
    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def test_rack_dock_and_aisle_locks_survive_array_reordering(self):
        source = model()
        manifest = L.build_lock_manifest(source, [
            selector("racks", "rack_a"), selector("lanes", "aisle_main"),
            selector("docks", "dock_n1", "receiving")])
        candidate = copy.deepcopy(source)
        candidate["floors"]["ground"]["rooms"][1]["racks"].reverse()
        candidate["floors"]["ground"]["rooms"][0]["docks"].reverse()
        result = L.verify_lock_manifest(source, candidate, manifest)
        self.assertTrue(result["ok"])
        self.assertEqual(result["lock_count"], 3)

    def test_locked_rack_change_is_rejected(self):
        source = model()
        manifest = L.build_lock_manifest(source, [selector("racks", "rack_a")])
        candidate = copy.deepcopy(source)
        candidate["floors"]["ground"]["rooms"][1]["racks"][0]["levels"] = 5
        self.assertCode("LOCK_VIOLATION",
                        lambda: L.verify_lock_manifest(source, candidate, manifest))

    def test_locked_dock_removal_is_rejected(self):
        source = model()
        manifest = L.build_lock_manifest(source, [selector("docks", "dock_n1", "receiving")])
        candidate = copy.deepcopy(source)
        candidate["floors"]["ground"]["rooms"][0]["docks"].pop(0)
        self.assertCode("LOCK_VIOLATION",
                        lambda: L.verify_lock_manifest(source, candidate, manifest))

    def test_enclosing_room_geometry_cannot_move_locked_element(self):
        source = model()
        manifest = L.build_lock_manifest(source, [selector("lanes", "aisle_main")])
        candidate = copy.deepcopy(source)
        candidate["floors"]["ground"]["rooms"][1]["rect"][0] = 11.0
        self.assertCode("LOCK_CONTEXT_CHANGED",
                        lambda: L.verify_lock_manifest(source, candidate, manifest))

    def test_global_geometry_context_cannot_move_locked_element(self):
        source = model()
        manifest = L.build_lock_manifest(source, [selector("racks", "rack_a")])
        candidate = copy.deepcopy(source)
        candidate["site"]["w"] = 41.0
        self.assertCode("LOCK_CONTEXT_CHANGED",
                        lambda: L.verify_lock_manifest(source, candidate, manifest))

    def test_unrelated_sibling_element_can_change(self):
        source = model()
        manifest = L.build_lock_manifest(source, [selector("racks", "rack_a")])
        candidate = copy.deepcopy(source)
        candidate["floors"]["ground"]["rooms"][1]["racks"][1]["levels"] = 6
        self.assertTrue(L.verify_lock_manifest(source, candidate, manifest)["ok"])

    def test_site_lock_is_exact_and_independent_of_room_edit(self):
        source = model()
        manifest = L.build_lock_manifest(source, [{"kind": "site"}])
        candidate = copy.deepcopy(source)
        candidate["floors"]["ground"]["rooms"][1]["rect"][2] = 19.0
        self.assertTrue(L.verify_lock_manifest(source, candidate, manifest)["ok"])
        candidate["site"]["d"] = 26.0
        self.assertCode("LOCK_VIOLATION",
                        lambda: L.verify_lock_manifest(source, candidate, manifest))

    def test_nested_lock_requires_explicit_unique_id(self):
        source = model()
        del source["floors"]["ground"]["rooms"][1]["racks"][0]["id"]
        self.assertCode("LOCK_TARGET_NOT_FOUND", lambda: L.build_lock_manifest(
            source, [selector("racks", "rack_a")]))
        source = model()
        source["floors"]["ground"]["rooms"][1]["racks"][1]["id"] = "rack_a"
        self.assertCode("LOCK_TARGET_NOT_FOUND", lambda: L.build_lock_manifest(
            source, [selector("racks", "rack_a")]))

    def test_manifest_tamper_and_wrong_source_fail_closed(self):
        source = model()
        manifest = L.build_lock_manifest(source, [selector("racks", "rack_a")])
        tampered = copy.deepcopy(manifest)
        tampered["locks"][0]["value_hash"] = "0" * 64
        self.assertCode("LOCK_MANIFEST_TAMPERED",
                        lambda: L.verify_lock_manifest(source, source, tampered))
        wrong = copy.deepcopy(source)
        wrong["meta"]["name"] = "other revision"
        self.assertCode("LOCK_SOURCE_CHANGED",
                        lambda: L.verify_lock_manifest(wrong, wrong, manifest))

    def test_duplicate_selectors_rejected(self):
        source = model()
        ref = selector("racks", "rack_a")
        self.assertCode("DUPLICATE_LOCK",
                        lambda: L.build_lock_manifest(source, [ref, copy.deepcopy(ref)]))

    def test_chat_edit_enforces_semantic_manifest_before_revision_admission(self):
        source = model()
        ws = PlanWorkspace(lambda _: {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
                                      "issues": []})
        rev = ws.propose(source, brief="warehouse", requirements=[], expected_head=None,
                         note="initial")
        manifest = L.build_lock_manifest(rev.model, [selector("racks", "rack_a")])
        changed = copy.deepcopy(source)
        changed["floors"]["ground"]["rooms"][1]["racks"][0]["levels"] = 5
        fake = SimpleNamespace(apply_notes=lambda *_args, **_kwargs: changed)
        with patch.dict(sys.modules, {"acs_understand": fake}):
            self.assertCode("LOCK_VIOLATION", lambda: B.propose_chat_edit(
                ws, [{"text": "وسع staging فقط"}], expected_head=rev.id,
                semantic_lock_manifest=manifest))
        self.assertEqual(len(ws.history()), 1)

    def test_chat_edit_can_change_unlocked_element_with_manifest(self):
        source = model()
        ws = PlanWorkspace(lambda _: {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
                                      "issues": []})
        rev = ws.propose(source, brief="warehouse", requirements=[], expected_head=None,
                         note="initial")
        manifest = L.build_lock_manifest(rev.model, [selector("racks", "rack_a")])
        changed = copy.deepcopy(source)
        changed["floors"]["ground"]["rooms"][1]["racks"][1]["levels"] = 6
        fake = SimpleNamespace(apply_notes=lambda *_args, **_kwargs: changed)
        with patch.dict(sys.modules, {"acs_understand": fake}):
            new = B.propose_chat_edit(ws, [{"text": "عدل الرف B فقط"}],
                                      expected_head=rev.id,
                                      semantic_lock_manifest=manifest)
        self.assertEqual(new.number, 2)
        self.assertEqual(new.model["floors"]["ground"]["rooms"][1]["racks"][1]["levels"], 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
