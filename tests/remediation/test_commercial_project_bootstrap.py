#!/usr/bin/env python3
"""Atomic first-project persistence regressions for commercial ACS.

The first durable project state must never expose an empty project between project
creation and revision #1 persistence. These tests use only local SQLite and
synthetic canonical geometry; no provider, network, auth service or production data.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError
from acs_plan_store import SQLitePlanStore
from test_plan_store import verifier, warehouse, reqs


class CommercialProjectBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "plans.sqlite3"
        self.store = SQLitePlanStore(self.db)

    def first(self):
        ws = PlanLockWorkspace(verifier=verifier)
        return ws.propose(
            warehouse(),
            brief="site width 30 warehouse",
            requirements=reqs(),
            expected_head=None,
            note="initial plan",
        )

    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def raw_counts(self):
        con = sqlite3.connect(self.db)
        try:
            return tuple(con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                         for table in ("projects", "project_members", "plan_revisions"))
        finally:
            con.close()

    def test_project_owner_and_first_revision_commit_together(self):
        first = self.first()
        saved = self.store.create_project_with_revision(
            "project-1", owner_id="owner-1", revision=first)
        self.assertEqual(saved["project_id"], "project-1")
        self.assertEqual(saved["owner_id"], "owner-1")
        self.assertEqual(saved["head_revision_id"], first.id)
        self.assertIsNone(saved["baseline_revision_id"])
        state = self.store.project_state("project-1", actor_id="owner-1")
        self.assertEqual(state["role"], "owner")
        self.assertEqual(state["head_revision_id"], first.id)
        self.assertEqual([row["revision_id"] for row in state["revisions"]], [first.id])
        loaded = self.store.load_revision(
            "project-1", actor_id="owner-1", revision_id=first.id)
        self.assertEqual(loaded["revision_id"], first.id)
        self.assertEqual(self.raw_counts(), (1, 1, 1))

    def test_non_initial_revision_fails_before_any_project_row_exists(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(warehouse(), brief="site width 30 warehouse",
                           requirements=reqs(), expected_head=None, note="initial")
        second = ws.replace_semantic_locks([], expected_head=first.id, note="second")
        self.assertCode("INVALID_REVISION_CHAIN", lambda: self.store.create_project_with_revision(
            "project-1", owner_id="owner-1", revision=second))
        self.assertEqual(self.raw_counts(), (0, 0, 0))

    def test_invalid_revision_receipt_leaves_no_orphan_project(self):
        self.assertCode("INVALID_REVISION_RECEIPT", lambda: self.store.create_project_with_revision(
            "project-1", owner_id="owner-1", revision=object()))
        self.assertEqual(self.raw_counts(), (0, 0, 0))

    def test_duplicate_project_failure_preserves_original_aggregate(self):
        first = self.first()
        self.store.create_project_with_revision("project-1", owner_id="owner-1", revision=first)
        before = self.store.project_state("project-1", actor_id="owner-1")
        other = self.first()
        self.assertCode("PROJECT_EXISTS", lambda: self.store.create_project_with_revision(
            "project-1", owner_id="owner-2", revision=other))
        after = self.store.project_state("project-1", actor_id="owner-1")
        self.assertEqual(after, before)
        self.assertEqual(self.raw_counts(), (1, 1, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
