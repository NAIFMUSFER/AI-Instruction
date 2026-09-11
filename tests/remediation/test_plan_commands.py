#!/usr/bin/env python3
"""Authenticated-host command boundary regressions for Plan-first UI actions.

Synthetic workspaces/provider only. These tests do not expose a public route and do
not claim that ``actor_id`` has been authenticated; the future host must resolve it
before calling the command boundary.
"""
from __future__ import annotations
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_commands as C
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError
from test_plan_lock_binding import (
    residential, warehouse, reqs, element, verifier,
)


def residential_reqs():
    return [{"id": "site-width", "source": "requested", "evidence": "20",
             "metric": "site_width_m", "expected": 20.0}]


class PlanCommandTests(unittest.TestCase):
    def setUp(self):
        self.u = SimpleNamespace(apply_notes=Mock())
        self.patcher = patch.dict(sys.modules, {"acs_understand": self.u})
        self.patcher.start(); self.addCleanup(self.patcher.stop)
        self.ws = PlanLockWorkspace(verifier=verifier)
        self.first = self.ws.propose(
            residential(), brief="site width 20 residential",
            requirements=residential_reqs(), expected_head=None, note="initial")

    def run_cmd(self, command, actor="actor-123"):
        return C.execute_plan_command(self.ws, command, actor_id=actor,
                                      provider_model="test-model")

    def test_authenticated_actor_is_required_before_any_action(self):
        before = len(self.ws.history())
        for actor in (None, "", "  ", 7):
            with self.assertRaises(PlanError) as got:
                C.execute_plan_command(self.ws, {"action": "review",
                    "revision_id": self.first.id}, actor_id=actor)
            self.assertEqual(got.exception.code, "AUTHENTICATED_ACTOR_REQUIRED")
        self.assertEqual(len(self.ws.history()), before)
        self.u.apply_notes.assert_not_called()

    def test_client_cannot_supply_authority_or_detached_lock_fields(self):
        forbidden = [
            {"action": "review", "revision_id": self.first.id, "actor_id": "spoof"},
            {"action": "approve", "expected_head": self.first.id,
             "actor_label": "spoof", "confirmed": True,
             "acknowledge_concept_only": True},
            {"action": "chat_edit", "expected_head": self.first.id,
             "notes": [{"text": "edit"}], "semantic_lock_manifest": {}},
            {"action": "chat_edit", "expected_head": self.first.id,
             "notes": [{"text": "edit"}], "building": residential()},
        ]
        for command in forbidden:
            with self.subTest(command=command["action"]):
                with self.assertRaises(PlanError) as got:
                    self.run_cmd(command)
                self.assertEqual(got.exception.code, "CLIENT_AUTHORITY_FIELD")
        self.u.apply_notes.assert_not_called()

    def test_review_returns_read_only_packet_without_raw_brief(self):
        out = self.run_cmd({"action": "review", "revision_id": self.first.id})
        self.assertEqual(out["schema"], "acs.plan-command-result/1.0")
        self.assertEqual(out["action"], "review")
        self.assertEqual(out["head"], self.first.id)
        self.assertIsNone(out["baseline"])
        packet = out["review_packet"]
        self.assertEqual(packet["schema"], "acs.plan-review-file/1.0")
        self.assertNotIn("site width 20 residential", packet["payload_json"])
        self.assertNotIn("actor-123", packet["payload_json"])
        self.assertNotIn("evidence", packet["payload_json"])

    def test_residential_chat_edit_uses_server_held_elevator_lock_and_keeps_baseline(self):
        locked = self.run_cmd({"action": "replace_semantic_locks",
            "expected_head": self.first.id,
            "selectors": [element("objects", "lift_1", "core")],
            "note": "lock elevator"})
        lock_head = locked["head"]
        approved = self.run_cmd({"action": "approve", "expected_head": lock_head,
            "confirmed": True, "acknowledge_concept_only": True})
        self.assertEqual(approved["baseline"], lock_head)
        before = self.ws.get(lock_head)
        changed = copy.deepcopy(before.model)
        rooms = changed["floors"]["ground"]["rooms"]
        rooms[0]["rect"] = [0.0, 0.0, 8.0, 12.0]
        rooms[3]["rect"] = [0.0, 12.0, 20.0, 8.0]
        self.u.apply_notes.return_value = changed
        out = self.run_cmd({"action": "chat_edit", "expected_head": lock_head,
            "notes": [{"text": "كبّر المجلس مع إبقاء المصعد مقفلاً"}]})
        self.assertNotEqual(out["head"], lock_head)
        self.assertEqual(out["baseline"], lock_head)
        revised = self.ws.get(out["head"])
        self.assertEqual(revised.semantic_lock_count, 1)
        self.assertEqual(revised.model["floors"]["ground"]["rooms"][1]["objects"][0],
                         before.model["floors"]["ground"]["rooms"][1]["objects"][0])

    def test_warehouse_chat_edit_preserves_server_held_dock_and_rack(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(warehouse(), brief="site width 30 warehouse",
                           requirements=reqs(), expected_head=None, note="initial")
        def cmd(value):
            return C.execute_plan_command(ws, value, actor_id="warehouse-user",
                                          provider_model="test-model")
        locked = cmd({"action": "replace_semantic_locks", "expected_head": first.id,
            "selectors": [element("racks", "rack_a", "storage"),
                          element("docks", "dock_n1", "receiving")],
            "note": "lock selected dock and rack"})
        bound = ws.get(locked["head"])
        changed = copy.deepcopy(bound.model)
        rooms = changed["floors"]["ground"]["rooms"]
        rooms[2]["rect"] = [20.0, 0.0, 10.0, 17.0]
        rooms[3]["rect"] = [20.0, 17.0, 10.0, 13.0]
        self.u.apply_notes.return_value = changed
        out = cmd({"action": "chat_edit", "expected_head": bound.id,
            "notes": [{"text": "وسّع staging مع قفل docks والرفوف المحددة"}]})
        revised = ws.get(out["head"])
        self.assertEqual(revised.semantic_lock_count, 2)
        self.assertEqual(revised.model["floors"]["ground"]["rooms"][0]["docks"],
                         bound.model["floors"]["ground"]["rooms"][0]["docks"])
        self.assertEqual(revised.model["floors"]["ground"]["rooms"][1]["racks"],
                         bound.model["floors"]["ground"]["rooms"][1]["racks"])

    def test_lock_violation_and_stale_head_never_extend_history(self):
        locked = self.run_cmd({"action": "replace_semantic_locks",
            "expected_head": self.first.id,
            "selectors": [element("objects", "lift_1", "core")],
            "note": "lock elevator"})
        head = locked["head"]
        before_count = len(self.ws.history())
        bad = copy.deepcopy(self.ws.get(head).model)
        bad["floors"]["ground"]["rooms"][1]["objects"][0]["x"] += 1
        self.u.apply_notes.return_value = bad
        with self.assertRaises(PlanError) as got:
            self.run_cmd({"action": "chat_edit", "expected_head": head,
                          "notes": [{"text": "move it"}]})
        self.assertEqual(got.exception.code, "LOCK_VIOLATION")
        self.assertEqual(len(self.ws.history()), before_count)
        with self.assertRaises(PlanError) as stale:
            self.run_cmd({"action": "restore", "expected_head": "stale",
                          "source_revision_id": self.first.id, "note": "restore"})
        self.assertEqual(stale.exception.code, "STALE_REVISION")
        self.assertEqual(len(self.ws.history()), before_count)

    def test_compare_and_restore_are_revisioned_without_provider(self):
        changed = copy.deepcopy(self.first.model)
        changed["floors"]["ground"]["rooms"][0]["rect"] = [0.0, 0.0, 8.0, 12.0]
        second = self.ws.propose(changed, brief=self.first.brief,
            requirements=residential_reqs(), expected_head=self.first.id, note="V2")
        self.u.apply_notes.reset_mock()
        compared = self.run_cmd({"action": "compare",
            "reference_revision_id": self.first.id,
            "target_revision_id": second.id})
        self.assertEqual(compared["comparison"]["reference_revision_id"], self.first.id)
        self.assertEqual(compared["comparison"]["target_revision_id"], second.id)
        restored = self.run_cmd({"action": "restore", "expected_head": second.id,
            "source_revision_id": self.first.id, "note": "restore V1 as new draft"})
        self.assertNotEqual(restored["head"], self.first.id)
        self.assertEqual(self.ws.get(restored["head"]).parent_id, second.id)
        self.u.apply_notes.assert_not_called()

    def test_unsupported_action_fails_closed(self):
        with self.assertRaises(PlanError) as got:
            self.run_cmd({"action": "handoff_3d", "expected_head": self.first.id})
        self.assertEqual(got.exception.code, "PLAN_COMMAND_NOT_SUPPORTED")
        self.u.apply_notes.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
