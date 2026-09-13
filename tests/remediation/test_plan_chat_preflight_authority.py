#!/usr/bin/env python3
"""Provider must not start when a chat command smuggles server authority."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acs_plan_chat_orchestration import execute_isolated_persisted_chat_edit
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError
from acs_plan_store import SQLitePlanStore
from test_plan_lock_binding import reqs, verifier, warehouse


class ForbiddenRunner:
    def __init__(self):
        self.calls = 0

    def run(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("authority-invalid command must not start provider work")


class ChatAuthorityPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLitePlanStore(Path(self.tmp.name) / "plans.sqlite3")
        self.store.create_project("warehouse-authz", owner_id="owner-1")
        ws = PlanLockWorkspace(verifier=verifier)
        self.first = ws.propose(
            warehouse(), brief="site width 30 warehouse", requirements=reqs(),
            expected_head=None, note="initial",
        )
        self.store.save_revision(
            "warehouse-authz", actor_id="owner-1", revision=self.first,
            expected_head=None,
        )

    def call(self, extra):
        runner = ForbiddenRunner()
        command = {
            "action": "chat_edit",
            "expected_head": self.first.id,
            "notes": [{"text": "expand staging"}],
            **extra,
        }
        with self.assertRaises(PlanError) as got:
            execute_isolated_persisted_chat_edit(
                self.store,
                "warehouse-authz",
                command,
                actor_id="owner-1",
                provider_model="test-model",
                verifier=verifier,
                runner=runner,
            )
        self.assertEqual(runner.calls, 0)
        return got.exception.code

    def test_actor_and_model_authority_are_rejected_before_worker(self):
        for field, value in (
            ("actor_id", "attacker"),
            ("canonical_model", warehouse()),
            ("semantic_lock_manifest", {"locks": []}),
        ):
            with self.subTest(field=field):
                self.assertEqual(self.call({field: value}), "CLIENT_AUTHORITY_FIELD")

    def test_project_authority_is_rejected_before_worker(self):
        for field in ("project_id", "project", "workspace_id", "tenant_id"):
            with self.subTest(field=field):
                self.assertEqual(self.call({field: "other-project"}), "CLIENT_PROJECT_AUTHORITY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
