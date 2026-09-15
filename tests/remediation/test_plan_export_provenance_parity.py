#!/usr/bin/env python3
"""Cross-format Frozen-Baseline provenance parity for ACS Design Pipeline v2.

Synthetic warehouse geometry only. The test proves that SVG/DXF/PDF/IFC/glTF are
all derived from the same approved canonical revision and retain the same explicit
plan/requirement identities. It does not claim that the formats are semantically
identical beyond the asserted provenance contract, nor any engineering/regulatory
compliance. No provider, network, production data, or external CAD service is used.
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


def selector(collection: str, element_id: str) -> dict:
    return {
        "kind": "element",
        "template": "ground",
        "room_id": "storage",
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


def fake_gltf_compiler(_building, path):
    Path(path).write_text('{"asset":{"version":"2.0"}}', encoding="utf-8")
    return 1, 12


class WarehouseExportProvenanceParityTests(unittest.TestCase):
    def test_all_derived_formats_share_exact_frozen_baseline_provenance(self):
        ws, approved = approved_workspace()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
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

            self.assertTrue(CAD.verify_cad_export(paths["svg"])["ok"])
            self.assertTrue(CAD.verify_cad_export(paths["dxf"])["ok"])
            self.assertTrue(PDF.verify_pdf_export(paths["pdf"])["ok"])
            self.assertTrue(IFC.verify_ifc_export(paths["ifc"])["ok"])
            self.assertTrue(HANDOFF.verify_compiled_artifact(paths["gltf"])["ok"])

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
                with self.subTest(format=fmt):
                    for key in common_keys:
                        self.assertEqual(receipt[key], reference[key], key)
                    self.assertEqual(receipt["revision_id"], approved.id)
                    self.assertEqual(receipt["model_hash"], approved.model_hash)
                    self.assertEqual(receipt["provider_calls"], 0)
                    self.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")
                    self.assertEqual(receipt["structural_safety"], "NOT_VERIFIED")

            self.assertEqual(reference["semantic_lock_count"], 3)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
