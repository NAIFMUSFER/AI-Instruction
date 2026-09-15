#!/usr/bin/env python3
"""Regression contracts for warehouse structural-column semantic locks.

A warehouse column represented explicitly in canonical room ``objects`` is a
stable design anchor.  These tests do not infer a section, clearance, load,
structural adequacy or code requirement; they only prove exact lock
preservation during targeted plan edits.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError


BRIEF = "Warehouse with a fixed declared structural column; staging may expand without moving it."


def warehouse() -> dict:
    return {
        "meta": {"type": "warehouse", "name": "column-lock-regression"},
        "site": {"w": 30.0, "d": 30.0},
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {
                "id": "storage",
                "role": "storage",
                "rect": [0.0, 0.0, 20.0, 20.0],
                "objects": [{
                    "id": "column-c01",
                    "kind": "column",
                    "x": 6.0,
                    "z": 7.0,
                    "w": 0.5,
                    "d": 0.5,
                    "h": 8.0,
                }],
            },
            {
                "id": "staging",
                "role": "staging",
                "rect": [20.0, 0.0, 6.0, 12.0],
            },
        ]}},
    }


def column_selector() -> dict:
    return {
        "kind": "element",
        "template": "ground",
        "room_id": "storage",
        "collection": "objects",
        "element_id": "column-c01",
    }


class WarehouseColumnLockTests(unittest.TestCase):
    def setUp(self):
        self.ws = PlanLockWorkspace()
        first = self.ws.propose(
            warehouse(), brief=BRIEF, requirements=[], expected_head=None,
            note="V1 explicit warehouse column",
        )
        self.locked = self.ws.replace_semantic_locks(
            [column_selector()], expected_head=first.id,
            note="Lock the engineer-selected structural column",
        )

    def test_unrelated_staging_expansion_preserves_column_and_rebinds_lock(self):
        candidate = copy.deepcopy(self.locked.model)
        candidate["floors"]["ground"]["rooms"][1]["rect"] = [20.0, 0.0, 8.0, 12.0]

        revised = self.ws.propose(
            candidate, brief=BRIEF, requirements=[], expected_head=self.locked.id,
            note="Expand staging without moving the locked column",
        )

        self.assertEqual(revised.semantic_lock_count, 1)
        self.assertIsNotNone(revised.semantic_lock_manifest_hash)
        self.assertNotEqual(revised.id, self.locked.id)
        self.assertEqual(
            revised.model["floors"]["ground"]["rooms"][0]["objects"][0],
            self.locked.model["floors"]["ground"]["rooms"][0]["objects"][0],
        )
        selector = revised.semantic_lock_manifest["locks"][0]["selector"]
        self.assertEqual(selector, column_selector())

    def test_moving_locked_column_fails_before_revision_history_is_extended(self):
        candidate = copy.deepcopy(self.locked.model)
        candidate["floors"]["ground"]["rooms"][0]["objects"][0]["x"] = 6.5
        before = len(self.ws.history())

        with self.assertRaises(PlanError) as ctx:
            self.ws.propose(
                candidate, brief=BRIEF, requirements=[], expected_head=self.locked.id,
                note="Attempt to move locked column",
            )

        self.assertEqual(ctx.exception.code, "LOCK_VIOLATION")
        self.assertEqual(len(self.ws.history()), before)
        self.assertEqual(self.ws.head, self.locked.id)

    def test_column_kind_does_not_create_structural_or_regulatory_claims(self):
        # The semantic-lock layer protects declared canonical bytes only.  It has
        # no authority to infer a column section, load, clearance or compliance.
        item = self.locked.model["floors"]["ground"]["rooms"][0]["objects"][0]
        self.assertEqual(item["kind"], "column")
        self.assertNotIn("load_capacity", item)
        self.assertNotIn("code_compliance", item)
        self.assertNotIn("required_clearance", item)


if __name__ == "__main__":
    unittest.main()
