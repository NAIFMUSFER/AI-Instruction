#!/usr/bin/env python3
"""Durable/RBAC persistence regressions for ACS Plan-first v2."""
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
    evidence = "30" if width == 30.0 else str(int(width))
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


def element(collection, element_id, room_id):
    return {"kind": "element", "template": "ground", "room_id": room_id,
            "collection": collection, "element_id": element_id}


class PlanStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "plans.sqlite3"
        self.store = SQLitePlanStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def workspace(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(warehouse(), brief="site width 30 warehouse",
                           requirements=reqs(), expected_head=None, note="initial plan")
        return ws, first

    def create_and_save_first(self, project="p1", owner="owner-1"):
        self.store.create_project(project, owner_id=owner)
        ws, first = self.workspace()
        saved = self.store.save_revision(project, actor_id=owner,
                                         revision=first, expected_head=None)
        return ws, first, saved

    def test_revision_survives_store_reopen_with_exact_hashes(self):
        _ws, first, saved = self.create_and_save_first()
        reopened = SQLitePlanStore(self.db)
        loaded = reopened.load_revision("p1", actor_id="owner-1", revision_id=first.id)
        self.assertEqual(loaded, saved)
        state = reopened.project_state("p1", actor_id="owner-1")
        self.assertEqual(state["head_revision_id"], first.id)
        self.assertIsNone(state["baseline_revision_id"])

    def test_viewer_can_read_but_cannot_extend_history(self):
        ws, first, _ = self.create_and_save_first()
        self.store.grant_role("p1", by_actor_id="owner-1", actor_id="viewer-1", role="viewer")
        self.assertEqual(self.store.load_revision("p1", actor_id="viewer-1",
                                                 revision_id=first.id)["revision_id"], first.id)
        locked = ws.replace_semantic_locks([element("racks", "rack_a", "storage")],
                                           expected_head=first.id, note="lock rack")
        self.assertCode("PROJECT_ACCESS_DENIED", lambda: self.store.save_revision(
            "p1", actor_id="viewer-1", revision=locked, expected_head=first.id))
        self.assertEqual(self.store.project_state("p1", actor_id="owner-1")["head_revision_id"],
                         first.id)

    def test_editor_can_save_revision_but_cannot_admin_membership(self):
        ws, first, _ = self.create_and_save_first()
        self.store.grant_role("p1", by_actor_id="owner-1", actor_id="editor-1", role="editor")
        locked = ws.replace_semantic_locks([element("docks", "dock_n1", "receiving")],
                                           expected_head=first.id, note="lock dock")
        saved = self.store.save_revision("p1", actor_id="editor-1", revision=locked,
                                         expected_head=first.id)
        self.assertEqual(saved["semantic_lock_count"], 1)
        self.assertCode("PROJECT_ACCESS_DENIED", lambda: self.store.grant_role(
            "p1", by_actor_id="editor-1", actor_id="other", role="viewer"))

    def test_cross_project_membership_is_isolated(self):
        self.store.create_project("a", owner_id="alice")
        self.store.create_project("b", owner_id="bob")
        self.assertCode("PROJECT_ACCESS_DENIED", lambda: self.store.project_state(
            "a", actor_id="bob"))
        self.assertCode("PROJECT_ACCESS_DENIED", lambda: self.store.project_state(
            "b", actor_id="alice"))

    def test_stale_write_is_atomic_and_does_not_extend_persisted_history(self):
        ws, first, _ = self.create_and_save_first()
        locked = ws.replace_semantic_locks([element("racks", "rack_a", "storage")],
                                           expected_head=first.id, note="lock rack")
        self.assertCode("STALE_REVISION", lambda: self.store.save_revision(
            "p1", actor_id="owner-1", revision=locked, expected_head=None))
        state = self.store.project_state("p1", actor_id="owner-1")
        self.assertEqual(len(state["revisions"]), 1)
        self.assertEqual(state["head_revision_id"], first.id)

    def test_approved_lock_bound_baseline_survives_reopen_exactly(self):
        ws, first, _ = self.create_and_save_first()
        locked = ws.replace_semantic_locks(
            [element("racks", "rack_a", "storage"),
             element("docks", "dock_n1", "receiving")],
            expected_head=first.id, note="lock warehouse operating anchors")
        self.store.save_revision("p1", actor_id="owner-1", revision=locked,
                                 expected_head=first.id)
        approval = ws.approve(locked.id, expected_head=locked.id,
                              actor_label="Engineer A", confirmed=True,
                              acknowledge_concept_only=True)
        self.store.save_approval("p1", actor_id="owner-1", approval=approval,
                                 expected_head=locked.id)

        reopened = SQLitePlanStore(self.db)
        handoff = reopened.approved_handoff("p1", actor_id="owner-1")
        self.assertEqual(handoff["building"], locked.model)
        self.assertEqual(handoff["baseline"]["revision_id"], locked.id)
        self.assertEqual(handoff["baseline"]["bound_content_hash"], locked.bound_content_hash)
        self.assertEqual(handoff["baseline"]["semantic_lock_manifest_hash"],
                         locked.semantic_lock_manifest_hash)
        self.assertEqual(handoff["baseline"]["semantic_lock_count"], 2)
        self.assertEqual(len(handoff["semantic_lock_selectors"]), 2)
        self.assertEqual(len(handoff["source_map"]), 4)
        self.assertEqual(reopened.project_state("p1", actor_id="owner-1")["baseline_revision_id"],
                         locked.id)

    def test_later_draft_does_not_replace_persisted_approved_baseline(self):
        ws, first, _ = self.create_and_save_first()
        locked = ws.replace_semantic_locks([element("racks", "rack_a", "storage")],
                                           expected_head=first.id, note="lock rack")
        self.store.save_revision("p1", actor_id="owner-1", revision=locked,
                                 expected_head=first.id)
        approval = ws.approve(locked.id, expected_head=locked.id,
                              actor_label="Engineer A", confirmed=True,
                              acknowledge_concept_only=True)
        self.store.save_approval("p1", actor_id="owner-1", approval=approval,
                                 expected_head=locked.id)
        changed = copy.deepcopy(locked.model)
        changed["floors"]["ground"]["rooms"][2]["rect"] = [20.0, 0.0, 10.0, 17.0]
        changed["floors"]["ground"]["rooms"][3]["rect"] = [20.0, 17.0, 10.0, 13.0]
        draft = ws.propose(changed, brief=locked.brief, requirements=reqs(),
                           expected_head=locked.id, note="expand staging")
        self.store.save_revision("p1", actor_id="owner-1", revision=draft,
                                 expected_head=locked.id)
        state = self.store.project_state("p1", actor_id="owner-1")
        self.assertEqual(state["head_revision_id"], draft.id)
        self.assertEqual(state["baseline_revision_id"], locked.id)
        self.assertEqual(self.store.approved_handoff("p1", actor_id="owner-1")["building"],
                         locked.model)

    def test_revision_tamper_is_detected_on_read(self):
        _ws, first, _ = self.create_and_save_first()
        con = sqlite3.connect(self.db)
        raw = json.loads(con.execute(
            "SELECT revision_json FROM plan_revisions WHERE project_id='p1' AND revision_id=?",
            (first.id,)).fetchone()[0])
        raw["model"]["site"]["w"] = 31.0
        con.execute("UPDATE plan_revisions SET revision_json=? WHERE project_id='p1' AND revision_id=?",
                    (json.dumps(raw), first.id))
        con.commit(); con.close()
        self.assertCode("STORED_MODEL_TAMPERED", lambda: self.store.load_revision(
            "p1", actor_id="owner-1", revision_id=first.id))

    def test_approval_tamper_is_detected_before_handoff(self):
        ws, first, _ = self.create_and_save_first()
        approval = ws.approve(first.id, expected_head=first.id,
                              actor_label="Engineer A", confirmed=True,
                              acknowledge_concept_only=True)
        self.store.save_approval("p1", actor_id="owner-1", approval=approval,
                                 expected_head=first.id)
        con = sqlite3.connect(self.db)
        raw = json.loads(con.execute(
            "SELECT approval_json FROM plan_approvals WHERE project_id='p1' AND revision_id=?",
            (first.id,)).fetchone()[0])
        raw["bound_content_hash"] = "0" * 64
        con.execute("UPDATE plan_approvals SET approval_json=? WHERE project_id='p1' AND revision_id=?",
                    (json.dumps(raw), first.id))
        con.commit(); con.close()
        self.assertCode("STORED_APPROVAL_TAMPERED", lambda: self.store.approved_handoff(
            "p1", actor_id="owner-1"))

    def test_approval_requires_current_persisted_head(self):
        ws, first, _ = self.create_and_save_first()
        approval = ws.approve(first.id, expected_head=first.id,
                              actor_label="Engineer A", confirmed=True,
                              acknowledge_concept_only=True)
        locked = ws.replace_semantic_locks([], expected_head=first.id,
                                           note="version no semantic locks")
        self.store.save_revision("p1", actor_id="owner-1", revision=locked,
                                 expected_head=first.id)
        self.assertCode("STALE_REVISION", lambda: self.store.save_approval(
            "p1", actor_id="owner-1", approval=approval, expected_head=first.id))

    def test_owner_role_cannot_be_replaced_via_delegation(self):
        self.store.create_project("p1", owner_id="owner-1")
        self.assertCode("INVALID_PROJECT_ROLE", lambda: self.store.grant_role(
            "p1", by_actor_id="owner-1", actor_id="owner-1", role="viewer"))
        self.assertEqual(self.store.project_state("p1", actor_id="owner-1")["role"], "owner")

    def test_memory_database_is_rejected_as_non_durable(self):
        self.assertCode("DURABLE_STORE_REQUIRED", lambda: SQLitePlanStore(":memory:"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
