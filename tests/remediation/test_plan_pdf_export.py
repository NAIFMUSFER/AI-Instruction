#!/usr/bin/env python3
"""Frozen-Baseline PDF export regressions for ACS Plan-first v2.

Synthetic residential/warehouse canonical models only. No provider, production
data, regulation database or construction-compliance claim is used by these tests.
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
from tools import acs_plan_pdf_export as X

BRIEF = "موقع بعرض 20 متر مع مخطط معتمد للتصدير PDF"


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
        "meta": {"type": "residential", "name": "pdf-home"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 3.2, "wall_h": 3.0, "wall_t": 0.15,
        "levels": [
            {"index": 0, "template": "ground"},
            {"index": 1, "template": "upper"},
        ],
        "floors": {
            "ground": {"rooms": [
                {"id": "majlis", "name": "مجلس", "role": "living",
                 "rect": [0.0, 0.0, 7.0, 5.0], "requirement_ids": ["width"],
                 "doors": [], "windows": []},
                {"id": "lift", "name": "مصعد", "role": "elevator",
                 "rect": [7.0, 0.0, 2.0, 2.0], "doors": [], "windows": []},
            ]},
            "upper": {"rooms": [
                {"id": "bedroom", "name": "غرفة نوم", "role": "bedroom",
                 "rect": [0.0, 0.0, 6.0, 5.0], "doors": [], "windows": []},
            ]},
        },
    }


def warehouse_model():
    return {
        "meta": {"type": "warehouse", "name": "pdf-warehouse"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 8.0, "wall_h": 7.5, "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "storage", "name": "Storage", "role": "storage", "walls": "none",
             "rect": [0.0, 0.0, 20.0, 15.0], "requirement_ids": ["width"],
             "doors": [], "windows": [],
             "racks": [{"id": "rack_a", "kind": "pallet", "x": 1.0, "z": 1.0,
                        "w": 7.0, "d": 12.0, "dir": "z", "rows": 2,
                        "aisle": 3.4, "levels": 4, "h": 8.0,
                        "requirement_ids": ["width"]}],
             "docks": [{"id": "dock_n1", "edge": "N", "offset": 4.0,
                        "width": 3.6, "height": 4.2, "count": 1, "pitch": 5.4,
                        "requirement_ids": ["width"]}],
             "lanes": [{"id": "aisle_main", "kind": "forklift", "x": 9.0,
                        "z": 0.0, "w": 3.0, "d": 15.0, "dir": "z"}],
             "stations": []},
            {"id": "staging", "name": "Staging", "role": "staging", "walls": "none",
             "rect": [0.0, 15.0, 20.0, 5.0], "doors": [], "windows": [],
             "racks": [], "docks": [], "lanes": [], "stations": []},
        ]}},
    }


def approved_workspace(model, *, semantic_locks=None):
    ws = PlanLockWorkspace(verified)
    rev = ws.propose(copy.deepcopy(model), brief=BRIEF, requirements=program(),
                     expected_head=None, note="initial PDF review")
    if semantic_locks is not None:
        rev = ws.replace_semantic_locks(semantic_locks, expected_head=rev.id,
                                        note="engineer PDF lock set")
    ws.approve(rev.id, expected_head=rev.id, actor_label="test-engineer",
               confirmed=True, acknowledge_concept_only=True)
    return ws, rev


class ApprovedPdfExportTests(unittest.TestCase):
    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def test_draft_cannot_reach_pdf_projection(self):
        ws = PlanLockWorkspace(verified)
        rev = ws.propose(residential_model(), brief=BRIEF, requirements=program(),
                         expected_head=None, note="draft only")
        with tempfile.TemporaryDirectory() as td:
            self.assertCode("APPROVAL_REQUIRED", lambda: X.export_approved_pdf(
                ws, rev.id, Path(td) / "draft.pdf"))

    def test_residential_multilevel_pdf_is_exact_hash_bound_and_verifiable(self):
        ws, rev = approved_workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "approved.pdf"
            receipt = X.export_approved_pdf(ws, rev.id, out)
            raw = out.read_bytes()
            self.assertTrue(raw.startswith(b"%PDF-1.4"))
            self.assertTrue(raw.rstrip().endswith(b"%%EOF"))
            self.assertIn(rev.id.encode("ascii"), raw)
            self.assertIn(rev.model_hash.encode("ascii"), raw)
            self.assertEqual(receipt["revision_id"], rev.id)
            self.assertEqual(receipt["model_hash"], rev.model_hash)
            self.assertEqual(receipt["pdf_scope"], "SPACE_BOUNDARIES_ONLY")
            self.assertEqual(receipt["provider_calls"], 0)
            self.assertEqual(receipt["replanning_calls"], 0)
            self.assertFalse(receipt["construction_approved"])
            self.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")
            self.assertEqual(receipt["fire_life_safety_compliance"], "NOT_VERIFIED")
            self.assertEqual(len(receipt["pages"]), 2)
            self.assertEqual([p["level_index"] for p in receipt["pages"]], [0, 1])
            # UTF-8 human labels are preserved in the receipt rather than corrupted
            # through the base-14 ASCII PDF font.
            self.assertEqual(receipt["pages"][0]["spaces"][0]["label"], "مجلس")
            self.assertEqual(receipt["artifact_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertTrue(Path(str(out) + ".baseline.json").exists())
            checked = X.verify_pdf_export(out)
            self.assertTrue(checked["ok"])
            self.assertEqual(checked["page_count"], 2)

    def test_warehouse_rack_dock_locks_and_requirement_sources_survive_pdf_receipt(self):
        selectors = [
            {"kind": "element", "template": "ground", "room_id": "storage",
             "collection": "racks", "element_id": "rack_a"},
            {"kind": "element", "template": "ground", "room_id": "storage",
             "collection": "docks", "element_id": "dock_n1"},
        ]
        ws, rev = approved_workspace(warehouse_model(), semantic_locks=selectors)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "warehouse.pdf"
            receipt = X.export_approved_pdf(ws, rev.id, out)
            self.assertEqual(receipt["semantic_lock_count"], 2)
            self.assertIsNotNone(receipt["semantic_lock_manifest_hash"])
            entries = receipt["source_map"]
            rack = next(e for e in entries if e["source"].get("collection") == "racks")
            dock = next(e for e in entries if e["source"].get("collection") == "docks")
            for entry in (rack, dock):
                self.assertEqual(entry["requirement_refs"], [{
                    "requirement_id": "width", "source": "requested",
                    "source_id": "brief:user:site-width",
                    "source_span": program()[0]["source_span"],
                }])
            self.assertEqual(receipt["pages"][0]["space_count"], 2)
            self.assertTrue(X.verify_pdf_export(out)["ok"])

    def test_later_unapproved_draft_cannot_replace_exportable_frozen_baseline(self):
        ws, approved = approved_workspace(residential_model())
        changed = residential_model()
        changed["floors"]["ground"]["rooms"][0]["rect"] = [0.0, 0.0, 8.0, 5.0]
        draft = ws.propose(changed, brief=BRIEF, requirements=program(),
                           expected_head=ws.head, note="later unapproved majlis edit")
        with tempfile.TemporaryDirectory() as td:
            frozen = X.export_approved_pdf(ws, approved.id, Path(td) / "frozen.pdf")
            self.assertEqual(frozen["revision_id"], approved.id)
            self.assertNotEqual(draft.id, approved.id)
            self.assertCode("APPROVAL_REQUIRED", lambda: X.export_approved_pdf(
                ws, draft.id, Path(td) / "draft.pdf"))

    def test_artifact_and_receipt_tamper_are_detected(self):
        ws, rev = approved_workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "tamper.pdf"
            X.export_approved_pdf(ws, rev.id, out)
            out.write_bytes(out.read_bytes() + b"\n")
            self.assertCode("ARTIFACT_CHANGED", lambda: X.verify_pdf_export(out))

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "receipt.pdf"
            receipt = X.export_approved_pdf(ws, rev.id, out)
            receipt["pages"][0]["space_count"] += 1
            self.assertCode("PROVENANCE_MISMATCH", lambda: X.verify_pdf_export(out, receipt))

    def test_existing_output_is_not_overwritten_implicitly(self):
        ws, rev = approved_workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "once.pdf"
            X.export_approved_pdf(ws, rev.id, out)
            before = out.read_bytes()
            self.assertCode("OUTPUT_EXISTS", lambda: X.export_approved_pdf(ws, rev.id, out))
            self.assertEqual(out.read_bytes(), before)

    def test_receipt_json_is_canonical_and_contains_no_compliance_claim(self):
        ws, rev = approved_workspace(warehouse_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "warehouse.pdf"
            receipt = X.export_approved_pdf(ws, rev.id, out)
            sidecar = Path(str(out) + ".baseline.json")
            self.assertEqual(json.loads(sidecar.read_text(encoding="utf-8")), receipt)
            self.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")
            self.assertEqual(receipt["structural_safety"], "NOT_VERIFIED")
            self.assertEqual(receipt["fire_life_safety_compliance"], "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
