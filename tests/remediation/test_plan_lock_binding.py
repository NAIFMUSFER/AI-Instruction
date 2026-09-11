#!/usr/bin/env python3
"""Revision/approval binding regressions for semantic plan locks."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError


def verifier(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": []}


def reqs(width=30.0):
    return [{"id": "site-width", "source": "requested", "evidence": "30",
             "metric": "site_width_m", "expected": width}]


def warehouse():
    return {
        "meta": {"type": "warehouse"},
        "site": {"w": 30.0, "d": 30.0},
        "floor_height": 8.0, "wall_h": 7.5, "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "receiving", "role": "receiving", "walls": "none",
             "rect": [0.0, 0.0, 5.0, 30.0],
             "docks": [{"id": "dock_n1", "edge": "N", "offset": 2.0,
                         "width": 3.6, "height": 4.2}]},
            {"id": "storage", "role": "storage", "walls": "none",
             "rect": [5.0, 0.0, 15.0, 30.0],
             "racks": [{"id": "rack_a", "kind": "pallet", "x": 1.0, "z": 1.0,
                         "w": 12.0, "d": 28.0, "dir": "z", "rows": 2,
                         "levels": 4, "h": 8.0}]},
            {"id": "staging", "role": "staging", "walls": "none",
             "rect": [20.0, 0.0, 10.0, 15.0]},
            {"id": "shipping", "role": "shipping", "walls": "none",
             "rect": [20.0, 15.0, 10.0, 15.0]},
        ]}},
    }


def residential():
    return {
        "meta": {"type": "residential"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 3.2, "wall_h": 3.0, "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "majlis", "role": "living", "rect": [0.0, 0.0, 8.0, 10.0]},
            {"id": "core", "role": "circulation", "rect": [8.0, 0.0, 4.0, 10.0],
             "objects": [{"id": "lift_1", "kind": "elevator", "x": 1.0, "z": 2.0,
                           "w": 2.0, "d": 2.0, "h": 3.0}]},
            {"id": "bedroom", "role": "bedroom", "rect": [12.0, 0.0, 8.0, 10.0]},
            {"id": "lounge", "role": "living", "rect": [0.0, 10.0, 20.0, 10.0]},
        ]}},
    }


def element(collection, element_id, room_id):
    return {"kind": "element", "template": "ground", "room_id": room_id,
            "collection": collection, "element_id": element_id}


class PlanLockBindingTests(unittest.TestCase):
    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def initial(self, model=None):
        ws = PlanLockWorkspace(verifier=verifier)
        rev = ws.propose(model or warehouse(), brief="site width 30 warehouse",
                         requirements=reqs(), expected_head=None, note="initial plan")
        return ws, rev

    def test_lock_set_change_is_a_new_revision_and_bound_hash_changes(self):
        ws, first = self.initial()
        locked = ws.replace_semantic_locks(
            [element("racks", "rack_a", "storage"),
             element("docks", "dock_n1", "receiving")],
            expected_head=first.id, note="lock rack A and north dock")
        self.assertEqual(locked.number, 2)
        self.assertEqual(locked.semantic_lock_count, 2)
        self.assertNotEqual(first.bound_content_hash, locked.bound_content_hash)
        self.assertEqual(locked.semantic_lock_manifest["source_model_hash"], locked.model_hash)
        self.assertEqual(ws.history()[-1]["semantic_lock_count"], 2)

    def test_locked_warehouse_elements_block_candidate_before_history_extension(self):
        ws, first = self.initial()
        locked = ws.replace_semantic_locks(
            [element("racks", "rack_a", "storage"),
             element("docks", "dock_n1", "receiving")],
            expected_head=first.id, note="lock operating anchors")
        changed = copy.deepcopy(locked.model)
        changed["floors"]["ground"]["rooms"][1]["racks"][0]["levels"] = 5
        count = len(ws.history())
        self.assertCode("LOCK_VIOLATION", lambda: ws.propose(
            changed, brief=locked.brief, requirements=reqs(),
            expected_head=locked.id, note="change locked rack"))
        self.assertEqual(len(ws.history()), count)

    def test_expand_staging_preserves_locked_dock_and_rack_and_rebinds_manifest(self):
        ws, first = self.initial()
        locked = ws.replace_semantic_locks(
            [element("racks", "rack_a", "storage"),
             element("docks", "dock_n1", "receiving")],
            expected_head=first.id, note="lock dock and rack")
        changed = copy.deepcopy(locked.model)
        rooms = changed["floors"]["ground"]["rooms"]
        rooms[2]["rect"] = [20.0, 0.0, 10.0, 17.0]
        rooms[3]["rect"] = [20.0, 17.0, 10.0, 13.0]
        revised = ws.propose(changed, brief=locked.brief, requirements=reqs(),
                             expected_head=locked.id, note="expand staging by two metres")
        self.assertEqual(revised.semantic_lock_count, 2)
        self.assertEqual(revised.semantic_lock_manifest["source_model_hash"], revised.model_hash)
        self.assertNotEqual(locked.model_hash, revised.model_hash)
        self.assertNotEqual(locked.semantic_lock_manifest_hash,
                            revised.semantic_lock_manifest_hash)

    def test_lock_context_prevents_moving_locked_dock_room(self):
        ws, first = self.initial()
        locked = ws.replace_semantic_locks(
            [element("docks", "dock_n1", "receiving")],
            expected_head=first.id, note="lock receiving dock")
        changed = copy.deepcopy(locked.model)
        changed["floors"]["ground"]["rooms"][0]["rect"][2] = 6.0
        self.assertCode("LOCK_CONTEXT_CHANGED", lambda: ws.propose(
            changed, brief=locked.brief, requirements=reqs(),
            expected_head=locked.id, note="move dock host room"))

    def test_approval_and_handoff_bind_same_semantic_receipt(self):
        ws, first = self.initial()
        locked = ws.replace_semantic_locks(
            [element("racks", "rack_a", "storage")],
            expected_head=first.id, note="lock rack before approval")
        review = ws.review(locked.id)
        self.assertTrue(review["can_approve"])
        self.assertEqual(review["semantic_lock_manifest_hash"],
                         locked.semantic_lock_manifest_hash)
        approval = ws.approve(locked.id, expected_head=locked.id,
                              actor_label="engineer-reviewer", confirmed=True,
                              acknowledge_concept_only=True)
        self.assertEqual(approval.bound_content_hash, locked.bound_content_hash)
        self.assertEqual(approval.semantic_lock_manifest_hash,
                         locked.semantic_lock_manifest_hash)
        handoff = ws.handoff(locked.id)
        self.assertEqual(handoff["baseline"]["bound_content_hash"],
                         approval.bound_content_hash)
        self.assertEqual(handoff["baseline"]["semantic_lock_manifest_hash"],
                         approval.semantic_lock_manifest_hash)
        self.assertEqual(handoff["baseline"]["semantic_lock_count"], 1)
        self.assertEqual(handoff["semantic_lock_selectors"],
                         [element("racks", "rack_a", "storage")])

    def test_later_lock_revision_does_not_rewrite_old_approved_baseline(self):
        ws, first = self.initial()
        locked = ws.replace_semantic_locks(
            [element("racks", "rack_a", "storage")],
            expected_head=first.id, note="lock rack")
        approval = ws.approve(locked.id, expected_head=locked.id,
                              actor_label="engineer-reviewer", confirmed=True,
                              acknowledge_concept_only=True)
        newer = ws.replace_semantic_locks([], expected_head=locked.id,
                                          note="explicitly unlock semantic elements")
        self.assertIsNone(newer.semantic_lock_manifest_hash)
        handoff = ws.handoff(locked.id)
        self.assertEqual(handoff["baseline"]["bound_content_hash"],
                         approval.bound_content_hash)
        self.assertEqual(handoff["baseline"]["semantic_lock_count"], 1)

    def test_clearing_locks_is_versioned_and_stale_operation_fails(self):
        ws, first = self.initial()
        locked = ws.replace_semantic_locks(
            [element("racks", "rack_a", "storage")], expected_head=first.id,
            note="lock rack")
        cleared = ws.replace_semantic_locks([], expected_head=locked.id,
                                            note="unlock rack by engineer request")
        self.assertEqual(cleared.number, 3)
        self.assertEqual(cleared.semantic_lock_count, 0)
        self.assertIsNone(cleared.semantic_lock_manifest)
        self.assertCode("STALE_REVISION", lambda: ws.replace_semantic_locks(
            [], expected_head=locked.id, note="stale unlock"))

    def test_room_lock_revision_preserves_semantic_manifest(self):
        ws, first = self.initial()
        locked = ws.replace_semantic_locks(
            [element("racks", "rack_a", "storage")], expected_head=first.id,
            note="lock rack")
        room_locked = ws.set_room_lock(("ground", "receiving"), locked=True,
                                       expected_head=locked.id)
        self.assertEqual(room_locked.semantic_lock_count, 1)
        self.assertEqual(room_locked.semantic_lock_manifest["source_model_hash"],
                         room_locked.model_hash)
        self.assertIn(("ground", "receiving"), room_locked.locked_rooms)

    def test_residential_elevator_lock_allows_other_room_change(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(residential(), brief="site width 20 residential",
                           requirements=reqs(20.0), expected_head=None, note="initial")
        locked = ws.replace_semantic_locks(
            [element("objects", "lift_1", "core")], expected_head=first.id,
            note="lock elevator core equipment")
        changed = copy.deepcopy(locked.model)
        changed["floors"]["ground"]["rooms"][2]["rect"] = [12.0, 1.0, 8.0, 9.0]
        revised = ws.propose(changed, brief=locked.brief, requirements=reqs(20.0),
                             expected_head=locked.id, note="adjust bedroom only")
        self.assertEqual(revised.semantic_lock_count, 1)
        self.assertEqual(revised.model["floors"]["ground"]["rooms"][1]["objects"][0]["id"],
                         "lift_1")

    def test_residential_elevator_change_is_rejected(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(residential(), brief="site width 20 residential",
                           requirements=reqs(20.0), expected_head=None, note="initial")
        locked = ws.replace_semantic_locks(
            [element("objects", "lift_1", "core")], expected_head=first.id,
            note="lock elevator")
        changed = copy.deepcopy(locked.model)
        changed["floors"]["ground"]["rooms"][1]["objects"][0]["x"] = 1.5
        self.assertCode("LOCK_VIOLATION", lambda: ws.propose(
            changed, brief=locked.brief, requirements=reqs(20.0),
            expected_head=locked.id, note="move locked elevator"))

    def test_stored_manifest_tamper_fails_closed(self):
        ws, first = self.initial()
        locked = ws.replace_semantic_locks(
            [element("racks", "rack_a", "storage")], expected_head=first.id,
            note="lock rack")
        raw = locked.semantic_lock_manifest
        raw["locks"][0]["value_hash"] = "0" * 64
        ws._manifests[locked.id] = __import__("json").dumps(raw, sort_keys=True,
                                                            separators=(",", ":"))
        self.assertCode("LOCK_MANIFEST_TAMPERED", lambda: ws.get(locked.id))


if __name__ == "__main__":
    unittest.main(verbosity=2)
