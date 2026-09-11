#!/usr/bin/env python3
"""Restart/reload regressions for durable ACS Plan-first workspaces.

These tests prove a persisted project can be reconstructed as the same lock-bound
revision aggregate after a process restart.  They use temporary SQLite only; no
production data, provider call, authentication claim, or cloud durability claim.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError
from acs_plan_store import SQLitePlanStore


def verifier(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": []}


def reqs(width=30.0):
    evidence = str(int(width))
    return [{"id": "site-width", "source": "requested", "evidence": evidence,
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
            {"id": "majlis", "role": "living", "walls": "none",
             "rect": [0.0, 0.0, 8.0, 10.0]},
            {"id": "core", "role": "circulation", "walls": "none",
             "rect": [8.0, 0.0, 4.0, 10.0],
             "objects": [{"id": "lift_1", "kind": "elevator", "x": 1.0,
                           "z": 2.0, "w": 2.0, "d": 2.0, "h": 3.0}]},
            {"id": "bedroom", "role": "bedroom", "walls": "none",
             "rect": [12.0, 0.0, 8.0, 10.0]},
            {"id": "lounge", "role": "living", "walls": "none",
             "rect": [0.0, 10.0, 20.0, 10.0]},
        ]}},
    }


def element(collection, element_id, room_id):
    return {"kind": "element", "template": "ground", "room_id": room_id,
            "collection": collection, "element_id": element_id}


class PersistedWorkspaceReloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "plans.sqlite3"
        self.store = SQLitePlanStore(self.db)
        self.store.create_project("p1", owner_id="owner-1")

    def tearDown(self):
        self.tmp.cleanup()

    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def saved_warehouse(self, *, approve=False):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(warehouse(), brief="site width 30 warehouse",
                           requirements=reqs(), expected_head=None, note="initial warehouse")
        self.store.save_revision("p1", actor_id="owner-1", revision=first,
                                 expected_head=None)
        locked = ws.replace_semantic_locks(
            [element("racks", "rack_a", "storage"),
             element("docks", "dock_n1", "receiving")],
            expected_head=first.id, note="lock warehouse operating anchors")
        self.store.save_revision("p1", actor_id="owner-1", revision=locked,
                                 expected_head=first.id)
        approval = None
        if approve:
            approval = ws.approve(locked.id, expected_head=locked.id,
                                  actor_label="Engineer A", confirmed=True,
                                  acknowledge_concept_only=True)
            self.store.save_approval("p1", actor_id="owner-1", approval=approval,
                                     expected_head=locked.id)
        return ws, first, locked, approval

    def test_restart_reloads_exact_revision_ids_history_and_frozen_baseline(self):
        original, _first, locked, approval = self.saved_warehouse(approve=True)
        reopened = SQLitePlanStore(self.db)
        loaded = reopened.load_workspace("p1", actor_id="owner-1", verifier=verifier)
        self.assertEqual(loaded.head, original.head)
        self.assertEqual(loaded.baseline, original.baseline)
        self.assertEqual(loaded.history(), original.history())
        self.assertEqual(loaded.get(locked.id).bound_content_hash, locked.bound_content_hash)
        handoff = loaded.handoff(locked.id)
        self.assertEqual(handoff["baseline"]["bound_content_hash"], approval.bound_content_hash)
        self.assertEqual(handoff["baseline"]["semantic_lock_count"], 2)

    def test_reloaded_warehouse_semantic_locks_still_block_anchor_mutation(self):
        _original, _first, locked, _ = self.saved_warehouse()
        loaded = SQLitePlanStore(self.db).load_workspace(
            "p1", actor_id="owner-1", verifier=verifier)
        changed = copy.deepcopy(locked.model)
        changed["floors"]["ground"]["rooms"][1]["racks"][0]["levels"] = 5
        count = len(loaded.history())
        self.assertCode("LOCK_VIOLATION", lambda: loaded.propose(
            changed, brief=locked.brief, requirements=reqs(), expected_head=locked.id,
            note="attempt to change reloaded locked rack"))
        self.assertEqual(len(loaded.history()), count)

    def test_reloaded_workspace_can_extend_history_and_persist_new_draft(self):
        _original, _first, locked, _ = self.saved_warehouse()
        reopened = SQLitePlanStore(self.db)
        loaded = reopened.load_workspace("p1", actor_id="owner-1", verifier=verifier)
        changed = copy.deepcopy(locked.model)
        rooms = changed["floors"]["ground"]["rooms"]
        rooms[2]["rect"] = [20.0, 0.0, 10.0, 17.0]
        rooms[3]["rect"] = [20.0, 17.0, 10.0, 13.0]
        draft = loaded.propose(changed, brief=locked.brief, requirements=reqs(),
                               expected_head=locked.id, note="expand staging after restart")
        saved = reopened.save_revision("p1", actor_id="owner-1", revision=draft,
                                       expected_head=locked.id)
        self.assertEqual(saved["revision_id"], draft.id)
        self.assertEqual(saved["number"], 3)
        self.assertEqual(reopened.project_state("p1", actor_id="owner-1")["head_revision_id"],
                         draft.id)

    def test_residential_elevator_lock_survives_reload(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(residential(), brief="site width 20 residential",
                           requirements=reqs(20.0), expected_head=None, note="initial residential")
        self.store.save_revision("p1", actor_id="owner-1", revision=first,
                                 expected_head=None)
        locked = ws.replace_semantic_locks(
            [element("objects", "lift_1", "core")], expected_head=first.id,
            note="lock elevator")
        self.store.save_revision("p1", actor_id="owner-1", revision=locked,
                                 expected_head=first.id)
        loaded = SQLitePlanStore(self.db).load_workspace(
            "p1", actor_id="owner-1", verifier=verifier)
        changed = copy.deepcopy(locked.model)
        changed["floors"]["ground"]["rooms"][1]["objects"][0]["x"] = 1.5
        self.assertCode("LOCK_VIOLATION", lambda: loaded.propose(
            changed, brief=locked.brief, requirements=reqs(20.0), expected_head=locked.id,
            note="attempt to move reloaded elevator"))

    def test_later_draft_after_reload_does_not_replace_frozen_baseline(self):
        _original, _first, locked, _ = self.saved_warehouse(approve=True)
        reopened = SQLitePlanStore(self.db)
        loaded = reopened.load_workspace("p1", actor_id="owner-1", verifier=verifier)
        changed = copy.deepcopy(locked.model)
        rooms = changed["floors"]["ground"]["rooms"]
        rooms[2]["rect"] = [20.0, 0.0, 10.0, 17.0]
        rooms[3]["rect"] = [20.0, 17.0, 10.0, 13.0]
        draft = loaded.propose(changed, brief=locked.brief, requirements=reqs(),
                               expected_head=locked.id, note="new draft after approved restart")
        reopened.save_revision("p1", actor_id="owner-1", revision=draft,
                               expected_head=locked.id)
        state = reopened.project_state("p1", actor_id="owner-1")
        self.assertEqual(state["head_revision_id"], draft.id)
        self.assertEqual(state["baseline_revision_id"], locked.id)
        self.assertEqual(loaded.handoff(locked.id)["building"], locked.model)

    def test_reload_fails_closed_on_tampered_persisted_lock_receipt(self):
        _original, _first, locked, _ = self.saved_warehouse()
        con = sqlite3.connect(self.db)
        raw = json.loads(con.execute(
            "SELECT revision_json FROM plan_revisions WHERE project_id='p1' AND revision_id=?",
            (locked.id,)).fetchone()[0])
        raw["semantic_lock_manifest"]["locks"][0]["value_hash"] = "0" * 64
        con.execute("UPDATE plan_revisions SET revision_json=? WHERE project_id='p1' AND revision_id=?",
                    (json.dumps(raw), locked.id))
        con.commit(); con.close()
        self.assertCode("STORED_LOCK_RECEIPT_TAMPERED", lambda: SQLitePlanStore(
            self.db).load_workspace("p1", actor_id="owner-1", verifier=verifier))


if __name__ == "__main__":
    unittest.main(verbosity=2)
