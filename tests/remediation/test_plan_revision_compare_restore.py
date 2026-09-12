#!/usr/bin/env python3
"""Measured revision comparison and safe historical-restore regressions.

Synthetic canonical models only. These tests prove revision semantics and measured
comparison behavior; they do not claim architectural quality, regulation, or auth.
"""
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


def requirements():
    return [{"id": "site-width", "source": "requested", "evidence": "30",
             "metric": "site_width_m", "expected": 30.0}]


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


def rack_selector():
    return {"kind": "element", "template": "ground", "room_id": "storage",
            "collection": "racks", "element_id": "rack_a"}


class RevisionCompareRestoreTests(unittest.TestCase):
    def initial(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(warehouse(), brief="site width 30 warehouse",
                           requirements=requirements(), expected_head=None,
                           note="V1 initial")
        return ws, first

    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as caught:
            fn()
        self.assertEqual(caught.exception.code, code)

    def test_compare_revisions_uses_measured_scorecard_without_ranking(self):
        ws, first = self.initial()
        changed = copy.deepcopy(first.model)
        rooms = changed["floors"]["ground"]["rooms"]
        rooms[2]["rect"] = [20.0, 0.0, 10.0, 18.0]
        rooms[3]["rect"] = [20.0, 18.0, 10.0, 12.0]
        second = ws.propose(changed, brief=first.brief, requirements=requirements(),
                            expected_head=first.id, note="V2 expand staging")
        out = ws.compare_revisions(first.id, second.id)
        self.assertEqual(out["reference_revision_id"], first.id)
        self.assertEqual(out["target_revision_id"], second.id)
        self.assertFalse(out["claims_best_option"])
        self.assertFalse(out["claims_regulatory_compliance"])
        self.assertEqual(
            out["measured"]["options"][1]["delta_from_reference"]["mapping"]
            ["zone_area_by_role_m2"]["staging"], 30.0)
        self.assertEqual(
            out["measured"]["options"][1]["delta_from_reference"]["mapping"]
            ["zone_area_by_role_m2"]["shipping"], -30.0)

    def test_restore_creates_new_child_revision_and_does_not_rewind_history(self):
        ws, first = self.initial()
        changed = copy.deepcopy(first.model)
        changed["floors"]["ground"]["rooms"][2]["rect"] = [20.0, 0.0, 10.0, 16.0]
        changed["floors"]["ground"]["rooms"][3]["rect"] = [20.0, 16.0, 10.0, 14.0]
        second = ws.propose(changed, brief=first.brief, requirements=requirements(),
                            expected_head=first.id, note="V2")
        restored = ws.restore_revision(first.id, expected_head=second.id,
                                       note="restore V1 as new draft")
        self.assertEqual(restored.number, 3)
        self.assertEqual(restored.parent_id, second.id)
        self.assertNotEqual(restored.id, first.id)
        self.assertEqual(restored.model_hash, first.model_hash)
        self.assertEqual(ws.head, restored.id)
        self.assertEqual([r["version"] for r in ws.history()], [1, 2, 3])

    def test_restore_never_replaces_an_existing_frozen_baseline(self):
        ws, first = self.initial()
        ws.approve(first.id, expected_head=first.id, actor_label="engineer",
                   confirmed=True, acknowledge_concept_only=True)
        changed = copy.deepcopy(first.model)
        changed["floors"]["ground"]["rooms"][2]["rect"] = [20.0, 0.0, 10.0, 16.0]
        changed["floors"]["ground"]["rooms"][3]["rect"] = [20.0, 16.0, 10.0, 14.0]
        second = ws.propose(changed, brief=first.brief, requirements=requirements(),
                            expected_head=first.id, note="new draft after approval")
        restored = ws.restore_revision(first.id, expected_head=second.id,
                                       note="restore approved geometry as draft")
        self.assertEqual(ws.baseline, first.id)
        self.assertNotEqual(restored.id, first.id)
        self.assertEqual(ws.history()[0]["state"], "APPROVED")
        self.assertEqual(ws.history()[-1]["state"], "DRAFT")

    def test_restore_respects_current_server_semantic_locks(self):
        ws, first = self.initial()
        changed = copy.deepcopy(first.model)
        changed["floors"]["ground"]["rooms"][1]["racks"][0]["levels"] = 5
        second = ws.propose(changed, brief=first.brief, requirements=requirements(),
                            expected_head=first.id, note="V2 rack levels")
        locked = ws.replace_semantic_locks([rack_selector()], expected_head=second.id,
                                           note="lock current rack state")
        before = len(ws.history())
        self.assertCode("LOCK_VIOLATION", lambda: ws.restore_revision(
            first.id, expected_head=locked.id, note="attempt restore V1"))
        self.assertEqual(len(ws.history()), before)
        self.assertEqual(ws.head, locked.id)

    def test_stale_restore_is_rejected_before_history_extension(self):
        ws, first = self.initial()
        second = ws.propose(first.model, brief=first.brief, requirements=requirements(),
                            expected_head=first.id, note="V2 unchanged geometry")
        before = len(ws.history())
        self.assertCode("STALE_REVISION", lambda: ws.restore_revision(
            first.id, expected_head=first.id, note="stale restore"))
        self.assertEqual(len(ws.history()), before)
        self.assertEqual(ws.head, second.id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
