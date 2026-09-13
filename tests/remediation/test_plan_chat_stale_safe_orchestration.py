#!/usr/bin/env python3
"""Stale-safe orchestration regressions for isolated Plan-first chat edits.

The tests use a temporary SQLite PlanStore only. Provider work is represented by
an injected runner so no network, production identity, or production data is used.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acs_plan_chat_orchestration import execute_isolated_persisted_chat_edit
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_persisted_commands import execute_persisted_plan_command
from acs_plan_review import PlanError
from acs_plan_store import SQLitePlanStore
from acs_plan_store_reload import load_workspace
from test_plan_bridge import residential_reqs
from test_plan_lock_binding import element, reqs, residential, verifier, warehouse


class FakeRunner:
    def __init__(self, candidate_factory):
        self.candidate_factory = candidate_factory
        self.calls = []

    def run(self, target, kwargs, *, timeout_s=None, request_id=None):
        self.calls.append({
            "target": target,
            "kwargs": copy.deepcopy(kwargs),
            "timeout_s": timeout_s,
            "request_id": request_id,
        })
        return self.candidate_factory(copy.deepcopy(kwargs["building"]))


class StaleSafeChatOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def seed(self, project_id, model, *, requirements, brief):
        store = SQLitePlanStore(Path(self.tmp.name) / f"{project_id}.sqlite3")
        store.create_project(project_id, owner_id="owner-1")
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(
            model,
            brief=brief,
            requirements=requirements,
            expected_head=None,
            note="initial",
        )
        store.save_revision(
            project_id,
            actor_id="owner-1",
            revision=first,
            expected_head=None,
        )
        return store, first

    def persisted(self, store, project_id, command):
        return execute_persisted_plan_command(
            store,
            project_id,
            command,
            actor_id="owner-1",
            provider_model="test-model",
            verifier=verifier,
        )

    def isolated(self, store, project_id, command, runner):
        return execute_isolated_persisted_chat_edit(
            store,
            project_id,
            command,
            actor_id="owner-1",
            provider_model="test-model",
            verifier=verifier,
            runner=runner,
            request_id="req-regression",
            timeout_s=30.0,
        )

    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def test_warehouse_edit_reloads_then_persists_with_dock_and_rack_locks(self):
        store, first = self.seed(
            "warehouse-iso", warehouse(), requirements=reqs(),
            brief="site width 30 warehouse",
        )
        locked = self.persisted(store, "warehouse-iso", {
            "action": "replace_semantic_locks",
            "expected_head": first.id,
            "selectors": [
                element("racks", "rack_a", "storage"),
                element("docks", "dock_n1", "receiving"),
            ],
            "note": "lock operating anchors",
        })
        lock_head = locked["head"]
        before = store.load_revision(
            "warehouse-iso", actor_id="owner-1", revision_id=lock_head,
        )["model"]

        def expand_staging(candidate):
            rooms = candidate["floors"]["ground"]["rooms"]
            rooms[2]["rect"] = [20.0, 0.0, 10.0, 17.0]
            rooms[3]["rect"] = [20.0, 17.0, 10.0, 13.0]
            return candidate

        runner = FakeRunner(expand_staging)
        out = self.isolated(store, "warehouse-iso", {
            "action": "chat_edit",
            "expected_head": lock_head,
            "notes": [{"text": "وسّع staging مع قفل docks والرفوف المحددة"}],
        }, runner)

        self.assertTrue(out["persistence"]["revision_persisted"])
        self.assertFalse(out["persistence"]["approval_persisted"])
        reopened = load_workspace(
            store, "warehouse-iso", actor_id="owner-1", verifier=verifier,
        )
        revised = reopened.get(out["head"])
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
        self.assertEqual(len(runner.calls), 1)
        call = runner.calls[0]
        self.assertEqual(set(call["kwargs"]), {"building", "notes", "model"})
        serialized = repr(call["kwargs"]).lower()
        for forbidden in ("bearer", "authorization", "actor_id", "project_id", "planstore", "token"):
            self.assertNotIn(forbidden, serialized)

    def test_provider_race_reloads_current_head_and_rejects_stale_candidate(self):
        store, first = self.seed(
            "warehouse-race", warehouse(), requirements=reqs(),
            brief="site width 30 warehouse",
        )
        # Reconstruct from the real persisted identity so the competing revision
        # has the exact parent/hash chain accepted by the store.
        live = load_workspace(
            store, "warehouse-race", actor_id="owner-1", verifier=verifier,
        )
        competing = live.replace_semantic_locks(
            [], expected_head=first.id, note="competing engineer revision",
        )

        def race(candidate):
            store.save_revision(
                "warehouse-race",
                actor_id="owner-1",
                revision=competing,
                expected_head=first.id,
            )
            rooms = candidate["floors"]["ground"]["rooms"]
            rooms[2]["rect"] = [20.0, 0.0, 10.0, 16.0]
            rooms[3]["rect"] = [20.0, 16.0, 10.0, 14.0]
            return candidate

        runner = FakeRunner(race)
        self.assertCode("STALE_REVISION", lambda: self.isolated(
            store,
            "warehouse-race",
            {
                "action": "chat_edit",
                "expected_head": first.id,
                "notes": [{"text": "expand staging"}],
            },
            runner,
        ))
        state = store.project_state("warehouse-race", actor_id="owner-1")
        self.assertEqual(state["head_revision_id"], competing.id)
        self.assertEqual(len(state["revisions"]), 2)
        self.assertEqual(len(runner.calls), 1)

    def test_residential_edit_keeps_approved_baseline_frozen_and_elevator_locked(self):
        store, first = self.seed(
            "residential-iso", residential(), requirements=residential_reqs(),
            brief="site width 20 residential",
        )
        locked = self.persisted(store, "residential-iso", {
            "action": "replace_semantic_locks",
            "expected_head": first.id,
            "selectors": [element("objects", "lift_1", "core")],
            "note": "lock elevator",
        })
        baseline = locked["head"]
        approved = self.persisted(store, "residential-iso", {
            "action": "approve",
            "expected_head": baseline,
            "confirmed": True,
            "acknowledge_concept_only": True,
        })
        self.assertEqual(approved["persistence"]["baseline_revision_id"], baseline)
        before = store.load_revision(
            "residential-iso", actor_id="owner-1", revision_id=baseline,
        )["model"]

        def enlarge_majlis(candidate):
            rooms = candidate["floors"]["ground"]["rooms"]
            rooms[0]["rect"] = [0.0, 0.0, 8.0, 12.0]
            rooms[3]["rect"] = [0.0, 12.0, 20.0, 8.0]
            return candidate

        runner = FakeRunner(enlarge_majlis)
        out = self.isolated(store, "residential-iso", {
            "action": "chat_edit",
            "expected_head": baseline,
            "notes": [{"text": "كبّر المجلس مع قفل المصعد"}],
        }, runner)
        self.assertEqual(out["persistence"]["baseline_revision_id"], baseline)
        self.assertNotEqual(out["head"], baseline)
        reopened = load_workspace(
            store, "residential-iso", actor_id="owner-1", verifier=verifier,
        )
        revised = reopened.get(out["head"])
        self.assertEqual(reopened.baseline, baseline)
        self.assertEqual(
            revised.model["floors"]["ground"]["rooms"][1]["objects"][0],
            before["floors"]["ground"]["rooms"][1]["objects"][0],
        )
        with self.assertRaises(PlanError):
            reopened.handoff(revised.id)

    def test_stale_expected_head_is_rejected_before_worker_runs(self):
        store, first = self.seed(
            "warehouse-preflight", warehouse(), requirements=reqs(),
            brief="site width 30 warehouse",
        )
        newer = self.persisted(store, "warehouse-preflight", {
            "action": "replace_semantic_locks",
            "expected_head": first.id,
            "selectors": [],
            "note": "new head",
        })
        runner = FakeRunner(lambda building: building)
        self.assertCode("STALE_REVISION", lambda: self.isolated(
            store,
            "warehouse-preflight",
            {
                "action": "chat_edit",
                "expected_head": first.id,
                "notes": [{"text": "stale change"}],
            },
            runner,
        ))
        self.assertEqual(runner.calls, [])
        self.assertEqual(
            store.project_state("warehouse-preflight", actor_id="owner-1")["head_revision_id"],
            newer["head"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
