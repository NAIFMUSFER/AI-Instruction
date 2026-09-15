#!/usr/bin/env python3
"""Cross-format Frozen-Baseline provenance parity for ACS Design Pipeline v2.

Synthetic warehouse and residential geometry only. The tests prove that
SVG/DXF/PDF/IFC/glTF are all derived from the same approved canonical revision and
retain the same explicit plan/requirement identities. They do not claim that the
formats are semantically identical beyond the asserted provenance contract, nor any
engineering/regulatory compliance. No provider, network, production data, or
external CAD service is used.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from acs_plan_lock_binding import PlanLockWorkspace
from tools import acs_plan_cad_export as CAD
from tools import acs_plan_handoff as HANDOFF
from tools import acs_plan_ifc_export as IFC
from tools import acs_plan_pdf_export as PDF


BRIEF = "Warehouse site width 30 m; approved plan export provenance."
RESIDENTIAL_BRIEF = "Residential site width 20 m; approved plan export provenance."


def verified(_model):
    return {
        "scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
        "issues": [],
    }


def program():
    start = BRIEF.index("30")
    return [{
        "id": "site-width",
        "metric": "site_width_m",
        "expected": 30.0,
        "source": "requested",
        "evidence": "30",
        "source_id": "brief:user:site-width",
        "source_span": {"start": start, "end": start + 2},
    }]


def residential_program():
    start = RESIDENTIAL_BRIEF.index("20")
    return [{
        "id": "site-width",
        "metric": "site_width_m",
        "expected": 20.0,
        "source": "requested",
        "evidence": "20",
        "source_id": "brief:user:residential-site-width",
        "source_span": {"start": start, "end": start + 2},
    }]


def warehouse():
    return {
        "meta": {"type": "warehouse", "name": "export-provenance-parity"},
        "site": {"w": 30.0, "d": 30.0},
        "floor_height": 8.0,
        "wall_h": 7.5,
        "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [{
            "id": "storage",
            "role": "storage",
            "walls": "none",
            "rect": [0.0, 0.0, 30.0, 30.0],
            "requirement_ids": ["site-width"],
            "doors": [],
            "windows": [],
            "racks": [{
                "id": "rack_a",
                "kind": "pallet",
                "x": 1.0,
                "z": 1.0,
                "w": 8.0,
                "d": 18.0,
                "dir": "z",
                "rows": 2,
                "depth": 1.10,
                "bay": 2.70,
                "aisle": 3.4,
                "levels": 4,
                "h": 8.0,
                "requirement_ids": ["site-width"],
            }],
            "docks": [{
                "id": "dock_n1",
                "edge": "N",
                "offset": 4.0,
                "width": 3.6,
                "height": 4.2,
                "count": 1,
                "pitch": 5.4,
                "requirement_ids": ["site-width"],
            }],
            "lanes": [{
                "id": "aisle_main",
                "kind": "forklift",
                "x": 10.0,
                "z": 0.0,
                "w": 3.0,
                "d": 30.0,
                "dir": "z",
                "requirement_ids": ["site-width"],
            }],
            "stations": [],
        }]}}
    }


def residential():
    return {
        "meta": {"type": "residential", "name": "residential-export-provenance-parity"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 3.2,
        "wall_h": 3.0,
        "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {
                "id": "majlis",
                "role": "living",
                "rect": [0.0, 0.0, 8.0, 10.0],
                "requirement_ids": ["site-width"],
                "doors": [],
                "windows": [],
            },
            {
                "id": "core",
                "role": "circulation",
                "rect": [8.0, 0.0, 4.0, 10.0],
                "requirement_ids": ["site-width"],
                "doors": [],
                "windows": [],
                "objects": [{
                    "id": "lift_1",
                    "kind": "elevator",
                    "x": 1.0,
                    "z": 2.0,
                    "w": 2.0,
                    "d": 2.0,
                    "h": 3.0,
                    "requirement_ids": ["site-width"],
                }],
            },
            {
                "id": "bedroom",
                "role": "bedroom",
                "rect": [12.0, 0.0, 8.0, 10.0],
                "doors": [],
                "windows": [],
            },
            {
                "id": "lounge",
                "role": "living",
                "rect": [0.0, 10.0, 20.0, 10.0],
                "doors": [],
                "windows": [],
            },
        ]}},
    }


def selector(collection: str, element_id: str, room_id: str = "storage") -> dict:
    return {
        "kind": "element",
        "template": "ground",
        "room_id": room_id,
        "collection": collection,
        "element_id": element_id,
    }


def approved_workspace():
    ws = PlanLockWorkspace(verified)
    first = ws.propose(
        copy.deepcopy(warehouse()),
        brief=BRIEF,
        requirements=program(),
        expected_head=None,
        note="V1 warehouse export parity",
    )
    locked = ws.replace_semantic_locks(
        [
            selector("racks", "rack_a"),
            selector("docks", "dock_n1"),
            selector("lanes", "aisle_main"),
        ],
        expected_head=first.id,
        note="Lock explicit warehouse operational anchors",
    )
    ws.approve(
        locked.id,
        expected_head=locked.id,
        actor_label="test-engineer",
        confirmed=True,
        acknowledge_concept_only=True,
    )
    return ws, locked


def approved_residential_workspace():
    ws = PlanLockWorkspace(verified)
    first = ws.propose(
        copy.deepcopy(residential()),
        brief=RESIDENTIAL_BRIEF,
        requirements=residential_program(),
        expected_head=None,
        note="V1 residential export parity",
    )
    locked = ws.replace_semantic_locks(
        [selector("objects", "lift_1", "core")],
        expected_head=first.id,
        note="Lock explicit residential elevator",
    )
    ws.approve(
        locked.id,
        expected_head=locked.id,
        actor_label="test-engineer",
        confirmed=True,
        acknowledge_concept_only=True,
    )
    return ws, locked


def fake_gltf_compiler(_building, path):
    Path(path).write_text('{"asset":{"version":"2.0"}}', encoding="utf-8")
    return 1, 12


def export_receipts(ws, approved, root: Path):
    paths = {
        "svg": root / "plan.svg",
        "dxf": root / "plan.dxf",
        "pdf": root / "plan.pdf",
        "ifc": root / "plan.ifc",
        "gltf": root / "plan.gltf",
    }
    receipts = {
        "svg": CAD.export_approved_cad(ws, approved.id, 0, paths["svg"]),
        "dxf": CAD.export_approved_cad(ws, approved.id, 0, paths["dxf"]),
        "pdf": PDF.export_approved_pdf(ws, approved.id, paths["pdf"]),
        "ifc": IFC.export_approved_ifc(ws, approved.id, paths["ifc"]),
        "gltf": HANDOFF.compile_approved_baseline(
            ws, approved.id, paths["gltf"], compiler=fake_gltf_compiler
        ),
    }
    self_checks = {
        "svg": CAD.verify_cad_export(paths["svg"]),
        "dxf": CAD.verify_cad_export(paths["dxf"]),
        "pdf": PDF.verify_pdf_export(paths["pdf"]),
        "ifc": IFC.verify_ifc_export(paths["ifc"]),
        "gltf": HANDOFF.verify_compiled_artifact(paths["gltf"]),
    }
    return receipts, self_checks


def assert_common_receipt_contract(testcase, receipts, checks, approved, lock_count):
    for fmt, check in checks.items():
        testcase.assertTrue(check["ok"], fmt)
    reference = receipts["svg"]
    common_keys = (
        "revision_id",
        "model_hash",
        "requirements_hash",
        "provenance_hash",
        "source_map_hash",
        "source_map",
        "semantic_lock_manifest_hash",
        "semantic_lock_count",
    )
    for fmt, receipt in receipts.items():
        with testcase.subTest(format=fmt):
            for key in common_keys:
                testcase.assertEqual(receipt[key], reference[key], key)
            testcase.assertEqual(receipt["revision_id"], approved.id)
            testcase.assertEqual(receipt["model_hash"], approved.model_hash)
            testcase.assertEqual(receipt["provider_calls"], 0)
            testcase.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")
            testcase.assertEqual(receipt["structural_safety"], "NOT_VERIFIED")
    testcase.assertEqual(reference["semantic_lock_count"], lock_count)
    return reference


class WarehouseExportProvenanceParityTests(unittest.TestCase):
    def test_all_derived_formats_share_exact_frozen_baseline_provenance(self):
        ws, approved = approved_workspace()
        with tempfile.TemporaryDirectory() as td:
            receipts, checks = export_receipts(ws, approved, Path(td))
            reference = assert_common_receipt_contract(
                self, receipts, checks, approved, lock_count=3
            )
            by_identity = {
                (
                    row["source"].get("kind"),
                    row["source"].get("collection"),
                    row["source"].get("element_id"),
                ): row
                for row in reference["source_map"]
            }
            expected = [
                ("space", None, None),
                ("element", "racks", "rack_a"),
                ("element", "docks", "dock_n1"),
                ("element", "lanes", "aisle_main"),
            ]
            for identity in expected:
                self.assertIn(identity, by_identity)
                row = by_identity[identity]
                self.assertTrue(row["source_id"].startswith("plan_"))
                self.assertEqual(row["requirement_refs"], [{
                    "requirement_id": "site-width",
                    "source": "requested",
                    "source_id": "brief:user:site-width",
                    "source_span": program()[0]["source_span"],
                }])
                self.assertNotIn("evidence", row["requirement_refs"][0])


class ResidentialExportProvenanceParityTests(unittest.TestCase):
    def test_residential_elevator_and_spaces_share_frozen_baseline_provenance_across_formats(self):
        ws, approved = approved_residential_workspace()
        with tempfile.TemporaryDirectory() as td:
            receipts, checks = export_receipts(ws, approved, Path(td))
            reference = assert_common_receipt_contract(
                self, receipts, checks, approved, lock_count=1
            )
            by_identity = {
                (
                    row["source"].get("kind"),
                    row["source"].get("room_id"),
                    row["source"].get("collection"),
                    row["source"].get("element_id"),
                ): row
                for row in reference["source_map"]
            }
            expected_with_requirement = [
                ("space", "majlis", None, None),
                ("space", "core", None, None),
                ("element", "core", "objects", "lift_1"),
            ]
            expected_ref = [{
                "requirement_id": "site-width",
                "source": "requested",
                "source_id": "brief:user:residential-site-width",
                "source_span": residential_program()[0]["source_span"],
            }]
            for identity in expected_with_requirement:
                self.assertIn(identity, by_identity)
                row = by_identity[identity]
                self.assertTrue(row["source_id"].startswith("plan_"))
                self.assertEqual(row["requirement_refs"], expected_ref)
                self.assertNotIn("evidence", row["requirement_refs"][0])

            for room_id in ("bedroom", "lounge"):
                identity = ("space", room_id, None, None)
                self.assertIn(identity, by_identity)
                self.assertEqual(by_identity[identity]["requirement_refs"], [])

            lift = by_identity[("element", "core", "objects", "lift_1")]
            self.assertEqual(lift["source"]["template"], "ground")
            self.assertEqual(lift["source"]["level_index"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
