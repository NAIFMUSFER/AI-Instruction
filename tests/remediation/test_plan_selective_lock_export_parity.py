#!/usr/bin/env python3
"""Selective-property lock parity across approved ACS v2 derived artifacts.

This regression intentionally reuses the existing cross-format Frozen-Baseline
fixture and changes only the semantic-lock selectors. It proves that a bounded
property lock (rather than a whole-element lock) remains cryptographically bound
to the approved canonical revision consumed by SVG/DXF/PDF/IFC/glTF exports.

The test does not claim regulatory/structural compliance and does not call an AI
provider or external CAD service.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from acs_plan_lock_binding import PlanLockWorkspace
import test_plan_export_provenance_parity as PARITY


def selective_selector(
    collection: str,
    element_id: str,
    properties: list[str],
    room_id: str = "storage",
) -> dict:
    return {
        "kind": "element",
        "template": "ground",
        "room_id": room_id,
        "collection": collection,
        "element_id": element_id,
        "properties": properties,
    }


def approve_selective_warehouse():
    ws = PlanLockWorkspace(PARITY.verified)
    first = ws.propose(
        copy.deepcopy(PARITY.warehouse()),
        brief=PARITY.BRIEF,
        requirements=PARITY.program(),
        expected_head=None,
        note="V1 warehouse selective-lock export parity",
    )
    locked = ws.replace_semantic_locks(
        [
            selective_selector("racks", "rack_a", ["x", "z"]),
            selective_selector("docks", "dock_n1", ["edge", "offset"]),
            selective_selector("lanes", "aisle_main", ["w", "d"]),
        ],
        expected_head=first.id,
        note="Lock only explicit warehouse operational properties",
    )
    ws.approve(
        locked.id,
        expected_head=locked.id,
        actor_label="test-engineer",
        confirmed=True,
        acknowledge_concept_only=True,
    )
    return ws, locked


def approve_selective_residential():
    ws = PlanLockWorkspace(PARITY.verified)
    first = ws.propose(
        copy.deepcopy(PARITY.residential()),
        brief=PARITY.RESIDENTIAL_BRIEF,
        requirements=PARITY.residential_program(),
        expected_head=None,
        note="V1 residential selective-lock export parity",
    )
    locked = ws.replace_semantic_locks(
        [selective_selector("objects", "lift_1", ["x", "z"], room_id="core")],
        expected_head=first.id,
        note="Lock only the explicit residential elevator position",
    )
    ws.approve(
        locked.id,
        expected_head=locked.id,
        actor_label="test-engineer",
        confirmed=True,
        acknowledge_concept_only=True,
    )
    return ws, locked


def manifest_properties(approved) -> dict[tuple[str, str], tuple[str, ...]]:
    manifest = approved.semantic_lock_manifest
    if not isinstance(manifest, dict):
        raise AssertionError("approved revision has no semantic lock manifest")
    result = {}
    for record in manifest.get("locks", []):
        selector = record.get("selector", {})
        result[(selector.get("collection"), selector.get("element_id"))] = tuple(
            selector.get("properties", [])
        )
    return result


class SelectiveWarehouseExportParityTests(unittest.TestCase):
    def test_selective_warehouse_lock_manifest_is_bound_to_every_derived_format(self):
        ws, approved = approve_selective_warehouse()
        manifest = approved.semantic_lock_manifest
        self.assertIsInstance(manifest, dict)
        self.assertEqual(
            manifest_properties(approved),
            {
                ("racks", "rack_a"): ("x", "z"),
                ("docks", "dock_n1"): ("edge", "offset"),
                ("lanes", "aisle_main"): ("d", "w"),
            },
        )

        with tempfile.TemporaryDirectory() as td:
            receipts, checks = PARITY.export_receipts(ws, approved, Path(td))
            reference = PARITY.assert_common_receipt_contract(
                self, receipts, checks, approved, lock_count=3
            )

        self.assertEqual(reference["semantic_lock_manifest_hash"], manifest["manifest_hash"])
        for fmt, receipt in receipts.items():
            with self.subTest(format=fmt):
                self.assertEqual(receipt["semantic_lock_manifest_hash"], manifest["manifest_hash"])
                self.assertEqual(receipt["semantic_lock_count"], 3)
                self.assertEqual(receipt["provider_calls"], 0)
                self.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")
                self.assertEqual(receipt["structural_safety"], "NOT_VERIFIED")


class SelectiveResidentialExportParityTests(unittest.TestCase):
    def test_selective_elevator_position_lock_is_bound_to_every_derived_format(self):
        ws, approved = approve_selective_residential()
        manifest = approved.semantic_lock_manifest
        self.assertIsInstance(manifest, dict)
        self.assertEqual(
            manifest_properties(approved),
            {("objects", "lift_1"): ("x", "z")},
        )

        with tempfile.TemporaryDirectory() as td:
            receipts, checks = PARITY.export_receipts(ws, approved, Path(td))
            reference = PARITY.assert_common_receipt_contract(
                self, receipts, checks, approved, lock_count=1
            )

        self.assertEqual(reference["semantic_lock_manifest_hash"], manifest["manifest_hash"])
        for fmt, receipt in receipts.items():
            with self.subTest(format=fmt):
                self.assertEqual(receipt["semantic_lock_manifest_hash"], manifest["manifest_hash"])
                self.assertEqual(receipt["semantic_lock_count"], 1)
                self.assertEqual(receipt["provider_calls"], 0)
                self.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")
                self.assertEqual(receipt["structural_safety"], "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
