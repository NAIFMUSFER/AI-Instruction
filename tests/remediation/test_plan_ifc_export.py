#!/usr/bin/env python3
"""Approved-baseline IFC export regressions for Plan-first v2.

These tests use synthetic canonical residential/warehouse models and the repository's
real IFC exporter. They do not call a provider, claim code compliance, or touch
production data.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError
from tools import acs_plan_ifc_export as X

BRIEF = "أرض بعرض 20 متر ومخطط معتمد للتصدير BIM/IFC"


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
        "meta": {"type": "residential", "name": "ifc-home"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 3.2, "wall_h": 3.0, "wall_t": 0.15,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "living", "role": "living", "rect": [0.0, 0.0, 6.0, 5.0],
             "requirement_ids": ["width"], "doors": [], "windows": []},
            {"id": "bed", "role": "bedroom", "rect": [6.0, 0.0, 4.0, 4.0],
             "doors": [], "windows": []},
        ]}},
    }


def warehouse_model():
    return {
        "meta": {"type": "warehouse", "name": "ifc-warehouse"},
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


def approved_workspace(model, *, semantic_locks=None):
    ws = PlanLockWorkspace(verified)
    rev = ws.propose(copy.deepcopy(model), brief=BRIEF, requirements=program(),
                     expected_head=None, note="initial IFC review")
    if semantic_locks is not None:
        rev = ws.replace_semantic_locks(semantic_locks, expected_head=rev.id,
                                        note="engineer IFC lock set")
    ws.approve(rev.id, expected_head=rev.id, actor_label="test-engineer",
               confirmed=True, acknowledge_concept_only=True)
    return ws, rev


class ApprovedIfcExportTests(unittest.TestCase):
    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def test_draft_fails_before_bim_exporter_import(self):
        ws = PlanLockWorkspace(verified)
        rev = ws.propose(residential_model(), brief=BRIEF, requirements=program(),
                         expected_head=None, note="draft only")
        sys.modules.pop("acs_bim", None)
        with tempfile.TemporaryDirectory() as td:
            self.assertCode("APPROVAL_REQUIRED", lambda: X.export_approved_ifc(
                ws, rev.id, Path(td) / "draft.ifc"))
        self.assertNotIn("acs_bim", sys.modules)

    def test_exact_approved_residential_ifc_is_hash_bound_and_verifiable(self):
        ws, rev = approved_workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "approved.ifc"
            receipt = X.export_approved_ifc(ws, rev.id, out)
            text = out.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("ISO-10303-21;"))
            self.assertIn("IFCSPACE", text)
            self.assertEqual(receipt["revision_id"], rev.id)
            self.assertEqual(receipt["model_hash"], rev.model_hash)
            self.assertEqual(receipt["provider_calls"], 0)
            self.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")
            self.assertEqual(receipt["structural_safety"], "NOT_VERIFIED")
            self.assertEqual(receipt["ifc_manifest"]["revision_id"], rev.id)
            self.assertEqual(receipt["ifc_manifest"]["model_hash"], rev.model_hash)
            self.assertEqual(receipt["ifc_manifest"]["space_count"], 2)
            self.assertEqual(receipt["artifact_sha256"], hashlib.sha256(out.read_bytes()).hexdigest())
            self.assertTrue(Path(str(out) + ".baseline.json").exists())
            self.assertTrue(X.verify_ifc_export(out)["ok"])

    def test_warehouse_rack_dock_provenance_and_locks_reach_export_receipt(self):
        selectors = [
            {"kind": "element", "template": "ground", "room_id": "storage",
             "collection": "racks", "element_id": "rack_a"},
            {"kind": "element", "template": "ground", "room_id": "storage",
             "collection": "docks", "element_id": "dock_n1"},
        ]
        ws, rev = approved_workspace(warehouse_model(), semantic_locks=selectors)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "warehouse.ifc"
            receipt = X.export_approved_ifc(ws, rev.id, out)
            entries = receipt["source_map"]
            rack = next(e for e in entries if e["source"].get("collection") == "racks")
            dock = next(e for e in entries if e["source"].get("collection") == "docks")
            for entry in (rack, dock):
                self.assertEqual(entry["requirement_refs"], [{
                    "requirement_id": "width", "source": "requested",
                    "source_id": "brief:user:site-width",
                    "source_span": program()[0]["source_span"],
                }])
                self.assertNotIn("evidence", entry["requirement_refs"][0])
            self.assertEqual(receipt["semantic_lock_count"], 2)
            self.assertIsNotNone(receipt["semantic_lock_manifest_hash"])
            self.assertEqual(receipt["ifc_manifest"]["space_count"], 1)
            self.assertTrue(X.verify_ifc_export(out)["ok"])

    def test_new_draft_does_not_replace_exportable_frozen_baseline(self):
        ws, approved = approved_workspace(residential_model())
        changed = residential_model()
        changed["floors"]["ground"]["rooms"][1]["rect"] = [6.0, 0.0, 5.0, 4.0]
        draft = ws.propose(changed, brief=BRIEF, requirements=program(),
                           expected_head=ws.head, note="later unapproved draft")
        self.assertNotEqual(draft.id, approved.id)
        with tempfile.TemporaryDirectory() as td:
            receipt = X.export_approved_ifc(ws, approved.id, Path(td) / "baseline.ifc")
            self.assertEqual(receipt["revision_id"], approved.id)
            self.assertCode("APPROVAL_REQUIRED", lambda: X.export_approved_ifc(
                ws, draft.id, Path(td) / "draft.ifc"))

    def test_artifact_tamper_is_detected(self):
        ws, rev = approved_workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "tamper.ifc"
            X.export_approved_ifc(ws, rev.id, out)
            out.write_text(out.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            self.assertCode("ARTIFACT_CHANGED", lambda: X.verify_ifc_export(out))

    def test_existing_output_is_not_overwritten_implicitly(self):
        ws, rev = approved_workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "once.ifc"
            X.export_approved_ifc(ws, rev.id, out)
            self.assertCode("OUTPUT_EXISTS", lambda: X.export_approved_ifc(ws, rev.id, out))


if __name__ == "__main__":
    unittest.main(verbosity=2)
