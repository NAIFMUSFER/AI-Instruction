#!/usr/bin/env python3
"""Residential revision comparison and safe historical-restore regressions.

Synthetic canonical geometry only. These tests prove that residential V1/V2/...
comparison and restore remain measured, lock-aware, and baseline-safe. They do not
claim architectural quality, structural safety, or regulatory compliance.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError


BRIEF = "Residential site width 20 m; enlarge the majlis while keeping the elevator fixed."


def verifier(_model):
    return {
        "scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
        "issues": [],
    }


def requirements():
    start = BRIEF.index("20")
    return [{
        "id": "site-width",
        "source": "requested",
        "evidence": "20",
        "metric": "site_width_m",
        "expected": 20.0,
        "source_id": "brief:user:residential-site-width",
        "source_span": {"start": start, "end": start + 2},
    }]


def residential():
    return {
        "meta": {"type": "residential", "name": "revision-compare-restore"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 3.2,
        "wall_h": 3.0,
        "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {
                "id": "majlis",
                "role": "majlis",
                "rect": [0.0, 0.0, 5.0, 4.0],
                "requirement_ids": ["site-width"],
            },
            {
                "id": "bedroom",
                "role": "bedroom",
                "rect": [5.0, 0.0, 5.0, 4.0],
            },
            {
                "id": "core",
                "role": "circulation",
                "rect": [10.0, 0.0, 4.0, 4.0],
                "objects": [{
                    "id": "lift_1",
                    "kind": "elevator",
                    "x": 1.0,
                    "z": 1.0,
                    "w": 2.0,
                    "d": 2.0,
                    "h": 3.0,
                }],
            },
            {
                "id": "lounge",
                "role": "living",
                "rect": [0.0, 4.0, 14.0, 6.0],
            },
        ]}},
    }


def elevator_selector():
    return {
        "kind": "element",
        "template": "ground",
        "room_id": "core",
        "collection": "objects",
        "element_id": "lift_1",
    }


def resize_majlis(model):
    changed = copy.deepcopy(model)
    rooms = changed["floors"]["ground"]["rooms"]
    rooms[0]["rect"] = [0.0, 0.0, 6.0, 4.0]
    rooms[1]["rect"] = [6.0, 0.0, 4.0, 4.0]
    return changed


class ResidentialRevisionCompareRestoreTests(unittest.TestCase):
    def initial(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(
            residential(),
            brief=BRIEF,
            requirements=requirements(),
            expected_head=None,
            note="V1 residential",
        )
        return ws, first

    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as caught:
            fn()
        self.assertEqual(caught.exception.code, code)

    def test_compare_revisions_measures_majlis_reallocation_with_locked_elevator(self):
        ws, first = self.initial()
        locked = ws.replace_semantic_locks(
            [elevator_selector()],
            expected_head=first.id,
            note="lock elevator before conversational edit",
        )
        revised = ws.propose(
            resize_majlis(locked.model),
            brief=locked.brief,
            requirements=requirements(),
            expected_head=locked.id,
            note="V2 enlarge majlis while elevator remains locked",
        )

        out = ws.compare_revisions(locked.id, revised.id)
        delta = out["measured"]["options"][1]["delta_from_reference"]
        self.assertEqual(delta["scalar"]["space_rect_area_m2"], 0.0)
        self.assertEqual(delta["mapping"]["space_area_by_role_m2"]["majlis"], 4.0)
        self.assertEqual(delta["mapping"]["space_area_by_role_m2"]["bedroom"], -4.0)
        self.assertFalse(out["claims_best_option"])
        self.assertFalse(out["claims_regulatory_compliance"])
        self.assertEqual(revised.semantic_lock_count, 1)
        self.assertEqual(
            revised.model["floors"]["ground"]["rooms"][2]["objects"][0]["x"],
            1.0,
        )

    def test_restore_rejects_old_geometry_that_would_move_current_locked_elevator(self):
        ws, first = self.initial()
        moved = copy.deepcopy(first.model)
        moved["floors"]["ground"]["rooms"][2]["objects"][0]["x"] = 1.5
        second = ws.propose(
            moved,
            brief=first.brief,
            requirements=requirements(),
            expected_head=first.id,
            note="V2 engineer moves elevator before lock",
        )
        locked = ws.replace_semantic_locks(
            [elevator_selector()],
            expected_head=second.id,
            note="lock current elevator position",
        )
        before = len(ws.history())

        self.assertCode(
            "LOCK_VIOLATION",
            lambda: ws.restore_revision(
                first.id,
                expected_head=locked.id,
                note="attempt restore V1 with different elevator position",
            ),
        )
        self.assertEqual(len(ws.history()), before)
        self.assertEqual(ws.head, locked.id)

    def test_restore_approved_residential_revision_creates_draft_without_replacing_baseline(self):
        ws, first = self.initial()
        ws.approve(
            first.id,
            expected_head=first.id,
            actor_label="engineer",
            confirmed=True,
            acknowledge_concept_only=True,
        )
        second = ws.propose(
            resize_majlis(first.model),
            brief=first.brief,
            requirements=requirements(),
            expected_head=first.id,
            note="V2 majlis option after approval",
        )
        restored = ws.restore_revision(
            first.id,
            expected_head=second.id,
            note="restore V1 geometry as a new draft",
        )

        self.assertEqual(ws.baseline, first.id)
        self.assertNotEqual(restored.id, first.id)
        self.assertEqual(restored.model_hash, first.model_hash)
        self.assertEqual(restored.parent_id, second.id)
        self.assertEqual(ws.history()[0]["state"], "APPROVED")
        self.assertEqual(ws.history()[-1]["state"], "DRAFT")
        self.assertEqual([row["version"] for row in ws.history()], [1, 2, 3])


if __name__ == "__main__":
    unittest.main(verbosity=2)
