#!/usr/bin/env python3
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
from test_plan_lock_binding import residential, warehouse, reqs, element, verifier


def residential_reqs():
    return [{"id": "site-width", "source": "requested", "evidence": "20",
             "metric": "site_width_m", "expected": 20.0}]


class SemanticDiffCommandTests(unittest.TestCase):
    def setUp(self):
        self.u = SimpleNamespace(apply_notes=Mock())
        self.patcher = patch.dict(sys.modules, {"acs_understand": self.u})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_compare_command_returns_exact_revision_semantic_diff(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(residential(), brief="site width 20 residential",
                           requirements=residential_reqs(), expected_head=None,
                           note="V1")
        changed = copy.deepcopy(first.model)
        changed["floors"]["ground"]["rooms"][0]["rect"] = [0.0, 0.0, 8.0, 12.0]
        second = ws.propose(changed, brief=first.brief,
                            requirements=residential_reqs(), expected_head=first.id,
                            note="V2")
        out = C.execute_plan_command(ws, {
            "action": "compare",
            "reference_revision_id": first.id,
            "target_revision_id": second.id,
        }, actor_id="engineer")
        diff = out["semantic_diff"]
        self.assertEqual(diff["reference_revision_id"], first.id)
        self.assertEqual(diff["target_revision_id"], second.id)
        self.assertEqual(diff["change_count"], 1)
        self.assertEqual(diff["changes"][0]["room_id"], "majlis")
        self.assertEqual(diff["changes"][0]["changed_fields"], ["rect"])

    def test_residential_chat_edit_returns_visible_diff_while_elevator_stays_locked(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(residential(), brief="site width 20 residential",
                           requirements=residential_reqs(), expected_head=None,
                           note="initial")
        locked = C.execute_plan_command(ws, {
            "action": "replace_semantic_locks",
            "expected_head": first.id,
            "selectors": [element("objects", "lift_1", "core")],
            "note": "lock elevator",
        }, actor_id="engineer")
        locked_head = locked["head"]
        before = ws.get(locked_head)
        changed = copy.deepcopy(before.model)
        changed["floors"]["ground"]["rooms"][0]["rect"] = [0.0, 0.0, 8.0, 12.0]
        changed["floors"]["ground"]["rooms"][3]["rect"] = [0.0, 12.0, 20.0, 8.0]
        self.u.apply_notes.return_value = changed
        out = C.execute_plan_command(ws, {
            "action": "chat_edit",
            "expected_head": locked_head,
            "notes": [{"text": "كبّر المجلس مع قفل المصعد"}],
        }, actor_id="engineer", provider_model="test-model")
        diff = out["semantic_diff"]
        self.assertEqual(diff["reference_revision_id"], locked_head)
        changed_rooms = {(row.get("room_id"), row["change"])
                         for row in diff["changes"] if row["kind"] == "room"}
        self.assertEqual(changed_rooms, {("majlis", "modified"), ("lounge", "modified")})
        self.assertFalse(any(row.get("element_id") == "lift_1" for row in diff["changes"]))
        self.assertEqual(ws.get(out["head"]).semantic_lock_count, 1)

    def test_warehouse_chat_edit_reports_staging_geometry_not_locked_rack_or_dock(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(warehouse(), brief="site width 30 warehouse",
                           requirements=reqs(), expected_head=None, note="initial")
        locked = C.execute_plan_command(ws, {
            "action": "replace_semantic_locks",
            "expected_head": first.id,
            "selectors": [element("racks", "rack_a", "storage"),
                          element("docks", "dock_n1", "receiving")],
            "note": "lock rack and dock",
        }, actor_id="engineer")
        head = locked["head"]
        before = ws.get(head)
        changed = copy.deepcopy(before.model)
        rooms = changed["floors"]["ground"]["rooms"]
        rooms[2]["rect"] = [20.0, 0.0, 10.0, 17.0]
        rooms[3]["rect"] = [20.0, 17.0, 10.0, 13.0]
        self.u.apply_notes.return_value = changed
        out = C.execute_plan_command(ws, {
            "action": "chat_edit",
            "expected_head": head,
            "notes": [{"text": "وسّع staging مع قفل docks والرفوف المحددة"}],
        }, actor_id="engineer", provider_model="test-model")
        diff = out["semantic_diff"]
        changed_rooms = {(row.get("room_id"), row["change"])
                         for row in diff["changes"] if row["kind"] == "room"}
        self.assertEqual(changed_rooms, {("staging", "modified"), ("shipping", "modified")})
        self.assertFalse(any(row.get("element_id") in {"rack_a", "dock_n1"}
                             for row in diff["changes"]))
        self.assertEqual(ws.get(out["head"]).semantic_lock_count, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
