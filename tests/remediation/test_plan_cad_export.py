#!/usr/bin/env python3
"""Approved Frozen-Baseline SVG/DXF export regressions for Plan-first v2.

Fixtures are synthetic canonical residential/warehouse models. The suite never
calls a provider, production route, regulator, or external CAD service.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError
from tools import acs_plan_cad_export as X

BRIEF = "أرض بعرض 20 متر ومخطط معتمد للتصدير CAD"


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"}, "issues": []}


def program():
    start = BRIEF.index("20")
    return [{
        "id": "width", "metric": "site_width_m", "expected": 20.0,
        "source": "requested", "evidence": "20",
        "source_id": "brief:user:site-width",
        "source_span": {"start": start, "end": start + 2},
    }]


def residential_model():
    return {
        "meta": {"type": "residential", "name": "cad-home"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 3.2, "wall_h": 3.0, "wall_t": 0.15,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "living", "name": "مجلس", "role": "living",
             "rect": [0.0, 0.0, 6.0, 5.0], "requirement_ids": ["width"],
             "doors": [], "windows": []},
            {"id": "bed", "role": "bedroom", "rect": [6.0, 0.0, 4.0, 4.0],
             "doors": [], "windows": []},
        ]}},
    }


def warehouse_model():
    return {
        "meta": {"type": "warehouse", "name": "cad-warehouse"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 8.0, "wall_h": 7.5, "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "storage", "role": "storage", "walls": "none",
             "rect": [0.0, 0.0, 20.0, 20.0], "requirement_ids": ["width"],
             "doors": [], "windows": [],
             "racks": [{"id": "rack_a", "kind": "pallet", "x": 1.0, "z": 1.0,
                        "w": 8.0, "d": 18.0, "dir": "z", "rows": 2,
                        "aisle": 3.4, "levels": 4, "h": 8.0,
                        "requirement_ids": ["width"]}],
             "docks": [{"id": "dock_n1", "edge": "N", "offset": 4.0,
                        "width": 3.6, "height": 4.2, "count": 1, "pitch": 5.4,
                        "requirement_ids": ["width"]}],
             "lanes": [{"id": "aisle_main", "kind": "forklift", "x": 8.5,
                        "z": 0.0, "w": 3.0, "d": 20.0, "dir": "z"}],
             "stations": []},
        ]}},
    }


def workspace(model, *, approve=True, semantic_locks=None):
    ws = PlanLockWorkspace(verified)
    rev = ws.propose(copy.deepcopy(model), brief=BRIEF, requirements=program(),
                     expected_head=None, note="initial CAD review")
    if semantic_locks is not None:
        rev = ws.replace_semantic_locks(semantic_locks, expected_head=rev.id,
                                        note="engineer CAD lock set")
    if approve:
        ws.approve(rev.id, expected_head=rev.id, actor_label="test-engineer",
                   confirmed=True, acknowledge_concept_only=True)
    return ws, rev


class ApprovedCadExportTests(unittest.TestCase):
    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def test_approved_svg_is_hash_bound_and_keeps_canonical_authority(self):
        ws, rev = workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "approved.svg"
            receipt = X.export_approved_cad(ws, rev.id, 0, out)
            root = ET.fromstring(out.read_text(encoding="utf-8"))
            self.assertTrue(root.tag.endswith("svg"))
            self.assertEqual(receipt["format"], "SVG")
            self.assertEqual(receipt["revision_id"], rev.id)
            self.assertEqual(receipt["model_hash"], rev.model_hash)
            self.assertTrue(receipt["canonical_model_is_source_of_truth"])
            self.assertFalse(receipt["cad_is_source_of_truth"])
            self.assertFalse(receipt["construction_document"])
            self.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")
            self.assertEqual(receipt["provider_calls"], 0)
            self.assertEqual(receipt["replanning_calls"], 0)
            self.assertEqual(receipt["artifact_sha256"], hashlib.sha256(out.read_bytes()).hexdigest())
            self.assertTrue(Path(str(out) + ".baseline.json").exists())
            verified_receipt = X.verify_cad_export(out)
            self.assertTrue(verified_receipt["ok"])
            self.assertEqual(verified_receipt["projection_scope"], "SPACE_BOUNDARIES_ONLY")

    def test_approved_dxf_roundtrips_without_dwg_or_autocad_claim(self):
        import ezdxf

        ws, rev = workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "approved.dxf"
            receipt = X.export_approved_cad(ws, rev.id, 0, out)
            doc = ezdxf.read(io.StringIO(out.read_text(encoding="utf-8")))
            self.assertEqual(doc.units, 6)
            self.assertFalse(doc.audit().has_errors)
            self.assertFalse(receipt["native_dwg"])
            self.assertFalse(receipt["autocad_verified"])
            self.assertTrue(X.verify_cad_export(out)["ok"])

    def test_draft_fails_before_optional_dxf_dependency_is_reached(self):
        ws, rev = workspace(residential_model(), approve=False)
        with tempfile.TemporaryDirectory() as td, patch.dict(sys.modules, {"ezdxf": None}):
            self.assertCode("APPROVAL_REQUIRED", lambda: X.export_approved_cad(
                ws, rev.id, 0, Path(td) / "draft.dxf"))

    def test_new_draft_cannot_replace_exportable_frozen_baseline(self):
        ws, approved = workspace(residential_model())
        changed = residential_model()
        changed["floors"]["ground"]["rooms"][1]["rect"] = [6.0, 0.0, 5.0, 4.0]
        draft = ws.propose(changed, brief=BRIEF, requirements=program(),
                           expected_head=ws.head, note="later unapproved draft")
        with tempfile.TemporaryDirectory() as td:
            receipt = X.export_approved_cad(ws, approved.id, 0, Path(td) / "baseline.svg")
            self.assertEqual(receipt["revision_id"], approved.id)
            self.assertCode("APPROVAL_REQUIRED", lambda: X.export_approved_cad(
                ws, draft.id, 0, Path(td) / "draft.svg"))

    def test_warehouse_rack_dock_provenance_and_locks_reach_cad_receipt(self):
        selectors = [
            {"kind": "element", "template": "ground", "room_id": "storage",
             "collection": "racks", "element_id": "rack_a"},
            {"kind": "element", "template": "ground", "room_id": "storage",
             "collection": "docks", "element_id": "dock_n1"},
        ]
        ws, rev = workspace(warehouse_model(), semantic_locks=selectors)
        with tempfile.TemporaryDirectory() as td:
            receipt = X.export_approved_cad(ws, rev.id, 0, Path(td) / "warehouse.svg")
            rack = next(e for e in receipt["source_map"] if e["source"].get("collection") == "racks")
            dock = next(e for e in receipt["source_map"] if e["source"].get("collection") == "docks")
            for entry in (rack, dock):
                self.assertEqual(entry["requirement_refs"], [{
                    "requirement_id": "width", "source": "requested",
                    "source_id": "brief:user:site-width",
                    "source_span": program()[0]["source_span"],
                }])
            self.assertEqual(receipt["semantic_lock_count"], 2)
            self.assertIsNotNone(receipt["semantic_lock_manifest_hash"])
            self.assertTrue(X.verify_cad_export(Path(td) / "warehouse.svg")["ok"])

    def test_artifact_tamper_and_bad_extension_fail_closed(self):
        ws, rev = workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "tamper.svg"
            X.export_approved_cad(ws, rev.id, 0, out)
            out.write_text(out.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            self.assertCode("ARTIFACT_CHANGED", lambda: X.verify_cad_export(out))
            self.assertCode("INVALID_OUTPUT_PATH", lambda: X.export_approved_cad(
                ws, rev.id, 0, Path(td) / "not-cad.pdf"))

    def test_existing_output_and_non_integer_level_are_rejected(self):
        ws, rev = workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "once.svg"
            X.export_approved_cad(ws, rev.id, 0, out)
            self.assertCode("OUTPUT_EXISTS", lambda: X.export_approved_cad(ws, rev.id, 0, out))
            self.assertCode("INVALID_LEVEL", lambda: X.export_approved_cad(
                ws, rev.id, True, Path(td) / "bad.svg"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
