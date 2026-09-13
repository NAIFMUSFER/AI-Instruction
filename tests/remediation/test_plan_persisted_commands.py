#!/usr/bin/env python3
"""Durable trusted-host command regressions for ACS Plan-first v2.

All projects/provider replies are synthetic.  The adapter remains non-HTTP and
does not authenticate identities; tests supply the host-resolved actor explicitly.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_persisted_commands import execute_persisted_plan_command
from acs_plan_review import PlanError
from acs_plan_store import SQLitePlanStore
from acs_plan_store_reload import load_workspace
from test_plan_lock_binding import warehouse, reqs, element, verifier


class PersistedPlanCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLitePlanStore(Path(self.tmp.name) / "plans.sqlite3")
        self.store.create_project("warehouse-1", owner_id="owner-1")

        self.seed = PlanLockWorkspace(verifier=verifier)
        self.first = self.seed.propose(
            warehouse(),
            brief="site width 30 warehouse",
            requirements=reqs(),
            expected_head=None,
            note="initial warehouse plan",
        )
        self.store.save_revision(
            "warehouse-1",
            actor_id="owner-1",
            revision=self.first,
            expected_head=None,
        )

        self.u = SimpleNamespace(apply_notes=Mock())
        self.patcher = patch.dict(sys.modules, {"acs_understand": self.u})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def command(self, value, *, actor="owner-1"):
        return execute_persisted_plan_command(
            self.store,
            "warehouse-1",
            value,
            actor_id=actor,
            provider_model="test-model",
            verifier=verifier,
        )

    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def test_lock_revision_is_persisted_and_restored_exactly(self):
        out = self.command({
            "action": "replace_semantic_locks",
            "expected_head": self.first.id,
            "selectors": [
                element("racks", "rack_a", "storage"),
                element("docks", "dock_n1", "receiving"),
            ],
            "note": "lock selected rack and dock",
        })
        self.assertTrue(out["persistence"]["revision_persisted"])
        self.assertFalse(out["persistence"]["approval_persisted"])

        reopened = load_workspace(
            SQLitePlanStore(self.store.path),
            "warehouse-1",
            actor_id="owner-1",
            verifier=verifier,
        )
        restored = reopened.get(out["head"])
        self.assertEqual(restored.semantic_lock_count, 2)
        selectors = restored.semantic_lock_manifest["locks"]
        self.assertEqual(len(selectors), 2)
        self.assertEqual(reopened.head, out["persistence"]["head_revision_id"])

    def test_warehouse_chat_edit_persists_without_moving_locked_dock_or_rack(self):
        locked = self.command({
            "action": "replace_semantic_locks",
            "expected_head": self.first.id,
            "selectors": [
                element("racks", "rack_a", "storage"),
                element("docks", "dock_n1", "receiving"),
            ],
            "note": "lock operating anchors",
        })
        lock_head = locked["head"]
        before = self.store.load_revision(
            "warehouse-1", actor_id="owner-1", revision_id=lock_head,
        )["model"]

        changed = copy.deepcopy(before)
        rooms = changed["floors"]["ground"]["rooms"]
        rooms[2]["rect"] = [20.0, 0.0, 10.0, 17.0]
        rooms[3]["rect"] = [20.0, 17.0, 10.0, 13.0]
        self.u.apply_notes.return_value = changed

        edited = self.command({
            "action": "chat_edit",
            "expected_head": lock_head,
            "notes": [{"text": "وسّع staging مع قفل docks والرفوف المحددة"}],
        })
        self.assertTrue(edited["persistence"]["revision_persisted"])

        reopened = load_workspace(
            self.store, "warehouse-1", actor_id="owner-1", verifier=verifier,
        )
        revised = reopened.get(edited["head"])
        self.assertEqual(revised.semantic_lock_count, 2)
        self.assertEqual(
            revised.model["floors"]["ground"]["rooms"][0]["docks"],
            before["floors"]["ground"]["rooms"][0]["docks"],
        )
        self.assertEqual(
            revised.model["floors"]["ground"]["rooms"][1]["racks"],
            before["floors"]["ground"]["rooms"][1]["racks"],
        )
        self.assertEqual(
            revised.model["floors"]["ground"]["rooms"][2]["rect"],
            [20.0, 0.0, 10.0, 17.0],
        )

    def test_approval_is_persisted_as_frozen_lock_bound_baseline(self):
        locked = self.command({
            "action": "replace_semantic_locks",
            "expected_head": self.first.id,
            "selectors": [element("docks", "dock_n1", "receiving")],
            "note": "freeze receiving dock",
        })
        approved = self.command({
            "action": "approve",
            "expected_head": locked["head"],
            "confirmed": True,
            "acknowledge_concept_only": True,
        })
        self.assertFalse(approved["persistence"]["revision_persisted"])
        self.assertTrue(approved["persistence"]["approval_persisted"])
        self.assertEqual(approved["persistence"]["baseline_revision_id"], locked["head"])

        handoff = self.store.approved_handoff(
            "warehouse-1", actor_id="owner-1",
        )
        stored = self.store.load_revision(
            "warehouse-1", actor_id="owner-1", revision_id=locked["head"],
        )
        self.assertEqual(handoff["building"], stored["model"])
        self.assertEqual(handoff["baseline"]["revision_id"], locked["head"])
        self.assertEqual(
            handoff["baseline"]["bound_content_hash"],
            stored["bound_content_hash"],
        )
        self.assertEqual(handoff["baseline"]["semantic_lock_count"], 1)

    def test_viewer_never_receives_mutable_persisted_command_workspace(self):
        self.store.grant_role(
            "warehouse-1",
            by_actor_id="owner-1",
            actor_id="viewer-1",
            role="viewer",
        )
        self.assertCode("PROJECT_ACCESS_DENIED", lambda: self.command({
            "action": "review",
            "revision_id": self.first.id,
        }, actor="viewer-1"))
        state = self.store.project_state("warehouse-1", actor_id="owner-1")
        self.assertEqual(len(state["revisions"]), 1)

    def test_client_cannot_select_project_or_workspace_authority(self):
        for field in ("project_id", "project", "workspace_id", "tenant_id"):
            with self.subTest(field=field):
                self.assertCode("CLIENT_PROJECT_AUTHORITY", lambda field=field: self.command({
                    "action": "review",
                    "revision_id": self.first.id,
                    field: "other-project",
                }))
        self.assertEqual(
            self.store.project_state("warehouse-1", actor_id="owner-1")["head_revision_id"],
            self.first.id,
        )

    def test_concurrent_winner_causes_stale_failure_without_lost_update(self):
        competing = self.seed.replace_semantic_locks(
            [],
            expected_head=self.first.id,
            note="competing warehouse revision",
        )

        def race(before_model, _notes, *, model=None):
            self.store.save_revision(
                "warehouse-1",
                actor_id="owner-1",
                revision=competing,
                expected_head=self.first.id,
            )
            candidate = copy.deepcopy(before_model)
            rooms = candidate["floors"]["ground"]["rooms"]
            rooms[2]["rect"] = [20.0, 0.0, 10.0, 16.0]
            rooms[3]["rect"] = [20.0, 16.0, 10.0, 14.0]
            return candidate

        self.u.apply_notes.side_effect = race
        self.assertCode("STALE_REVISION", lambda: self.command({
            "action": "chat_edit",
            "expected_head": self.first.id,
            "notes": [{"text": "expand staging"}],
        }))
        state = self.store.project_state("warehouse-1", actor_id="owner-1")
        self.assertEqual(state["head_revision_id"], competing.id)
        self.assertEqual(len(state["revisions"]), 2)

    def test_read_only_review_does_not_append_revision(self):
        before = self.store.project_state("warehouse-1", actor_id="owner-1")
        out = self.command({"action": "review", "revision_id": self.first.id})
        after = self.store.project_state("warehouse-1", actor_id="owner-1")
        self.assertEqual(before["revisions"], after["revisions"])
        self.assertFalse(out["persistence"]["revision_persisted"])
        self.assertFalse(out["persistence"]["approval_persisted"])
        self.u.apply_notes.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
