#!/usr/bin/env python3
"""Frozen-Baseline SVG export regressions for ACS Design Pipeline v2.

Synthetic canonical models only. SVG is a derived review artifact: the Canonical
ACS Model remains Source of Truth, drafts cannot cross the export boundary, and
no provider, replanning, regulation or construction-compliance claim is allowed.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError
from tools import acs_plan_svg_export as X

BRIEF = "موقع بعرض 20 متر ومخطط معتمد للتصدير SVG"


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"}, "issues": []}


def program():
    start = BRIEF.index("20")
    return [{
        "id": "site-width", "metric": "site_width_m", "expected": 20.0,
        "source": "requested", "evidence": "20",
        "source_id": "brief:user:site-width",
        "source_span": {"start": start, "end": start + 2},
    }]


def residential_model():
    return {
        "meta": {"type": "residential", "name": "svg-home"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 3.2, "wall_h": 3.0, "wall_t": 0.15,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "majlis", "name": "مجلس", "role": "living",
             "rect": [0.0, 0.0, 8.0, 6.0], "requirement_ids": ["site-width"],
             "doors": [], "windows": []},
            {"id": "lift", "name": "مصعد", "role": "elevator",
             "rect": [8.0, 0.0, 2.0, 2.0], "doors": [], "windows": []},
        ]}},
    }


def warehouse_model():
    return {
        "meta": {"type": "warehouse", "name": "svg-warehouse"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 8.0, "wall_h": 7.5, "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "receiving", "name": "Receiving", "role": "receiving", "walls": "none",
             "rect": [0.0, 0.0, 20.0, 5.0], "requirement_ids": ["site-width"],
             "doors": [], "windows": [], "racks": [], "lanes": [], "stations": [],
             "docks": [{"id": "dock_n1", "edge": "N", "offset": 4.0,
                        "width": 3.6, "height": 4.2, "count": 1, "pitch": 5.4,
                        "requirement_ids": ["site-width"]}]},
            {"id": "storage", "name": "Storage", "role": "storage", "walls": "none",
             "rect": [0.0, 5.0, 20.0, 10.0], "doors": [], "windows": [], "docks": [],
             "lanes": [], "stations": [],
             "racks": [{"id": "rack_a", "kind": "pallet", "x": 1.0, "z": 6.0,
                        "w": 7.0, "d": 8.0, "dir": "z", "rows": 2,
                        "aisle": 3.4, "levels": 4, "h": 7.5,
                        "requirement_ids": ["site-width"]}]},
            {"id": "staging", "name": "Staging", "role": "staging", "walls": "none",
             "rect": [0.0, 15.0, 20.0, 5.0], "doors": [], "windows": [],
             "racks": [], "docks": [], "lanes": [], "stations": []},
        ]}},
    }


def approved_workspace(model, *, selectors=None):
    ws = PlanLockWorkspace(verified)
    rev = ws.propose(copy.deepcopy(model), brief=BRIEF, requirements=program(),
                     expected_head=None, note="initial SVG review")
    if selectors:
        rev = ws.replace_semantic_locks(selectors, expected_head=rev.id,
                                        note="engineer SVG lock set")
    ws.approve(rev.id, expected_head=rev.id, actor_label="test-engineer",
               confirmed=True, acknowledge_concept_only=True)
    return ws, rev


class ApprovedSvgExportTests(unittest.TestCase):
    def assertCode(self, code, fn):
        with self.assertRaises(PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def test_draft_cannot_reach_svg_export(self):
        ws = PlanLockWorkspace(verified)
        rev = ws.propose(residential_model(), brief=BRIEF, requirements=program(),
                         expected_head=None, note="draft only")
        with tempfile.TemporaryDirectory() as td:
            self.assertCode("APPROVAL_REQUIRED", lambda: X.export_approved_svg(
                ws, rev.id, 0, Path(td) / "draft.svg"))

    def test_approved_residential_svg_is_hash_bound_utf8_and_derived_only(self):
        ws, rev = approved_workspace(residential_model())
        before = copy.deepcopy(rev.model)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "approved.svg"
            receipt = X.export_approved_svg(ws, rev.id, 0, out)
            raw = out.read_bytes()
            self.assertIn("مجلس", raw.decode("utf-8"))
            root = ET.fromstring(raw)
            self.assertTrue(root.tag.endswith("svg"))
            self.assertEqual(receipt["schema"], "acs.plan-svg-export/1.0")
            self.assertEqual(receipt["revision_id"], rev.id)
            self.assertEqual(receipt["model_hash"], rev.model_hash)
            self.assertEqual(receipt["level_index"], 0)
            self.assertEqual(receipt["svg_scope"], "SPACE_BOUNDARIES_ONLY")
            self.assertTrue(receipt["canonical_model_is_source_of_truth"])
            self.assertFalse(receipt["svg_is_source_of_truth"])
            self.assertEqual(receipt["provider_calls"], 0)
            self.assertEqual(receipt["replanning_calls"], 0)
            self.assertFalse(receipt["construction_approved"])
            self.assertEqual(receipt["regulatory_compliance"], "NOT_VERIFIED")
            self.assertEqual(receipt["artifact_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(ws.get(rev.id).model, before)
            self.assertTrue(X.verify_svg_export(out)["ok"])

    def test_warehouse_lock_binding_and_nested_requirement_provenance_survive(self):
        selectors = [
            {"kind": "element", "template": "ground", "room_id": "receiving",
             "collection": "docks", "element_id": "dock_n1"},
            {"kind": "element", "template": "ground", "room_id": "storage",
             "collection": "racks", "element_id": "rack_a"},
        ]
        ws, rev = approved_workspace(warehouse_model(), selectors=selectors)
        baseline = ws.handoff(rev.id)["baseline"]
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "warehouse.svg"
            receipt = X.export_approved_svg(ws, rev.id, 0, out)
            self.assertEqual(receipt["lock_binding_schema"], baseline["lock_binding_schema"])
            self.assertEqual(receipt["bound_content_hash"], baseline["bound_content_hash"])
            self.assertEqual(receipt["semantic_lock_manifest_hash"], baseline["semantic_lock_manifest_hash"])
            self.assertEqual(receipt["semantic_lock_count"], 2)
            entries = receipt["source_map"]
            rack = next(e for e in entries if e["source"].get("collection") == "racks")
            dock = next(e for e in entries if e["source"].get("collection") == "docks")
            for entry in (rack, dock):
                self.assertEqual(entry["requirement_refs"][0]["source_id"],
                                 "brief:user:site-width")
            self.assertTrue(X.verify_svg_export(out)["ok"])

    def test_later_draft_cannot_be_exported_in_place_of_frozen_baseline(self):
        ws, approved = approved_workspace(residential_model())
        changed = residential_model()
        changed["floors"]["ground"]["rooms"][0]["rect"] = [0.0, 0.0, 9.0, 6.0]
        draft = ws.propose(changed, brief=BRIEF, requirements=program(),
                           expected_head=ws.head, note="later unapproved edit")
        with tempfile.TemporaryDirectory() as td:
            frozen = X.export_approved_svg(ws, approved.id, 0, Path(td) / "frozen.svg")
            self.assertEqual(frozen["revision_id"], approved.id)
            self.assertCode("APPROVAL_REQUIRED", lambda: X.export_approved_svg(
                ws, draft.id, 0, Path(td) / "draft.svg"))

    def test_artifact_and_receipt_tamper_are_detected_and_no_implicit_overwrite(self):
        ws, rev = approved_workspace(residential_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "once.svg"
            receipt = X.export_approved_svg(ws, rev.id, 0, out)
            before = out.read_bytes()
            self.assertCode("OUTPUT_EXISTS", lambda: X.export_approved_svg(ws, rev.id, 0, out))
            self.assertEqual(out.read_bytes(), before)
            out.write_bytes(before + b"\n")
            self.assertCode("ARTIFACT_CHANGED", lambda: X.verify_svg_export(out, receipt))

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "receipt.svg"
            receipt = X.export_approved_svg(ws, rev.id, 0, out)
            receipt["canonical_model_is_source_of_truth"] = False
            self.assertCode("INVALID_BASELINE_RECEIPT", lambda: X.verify_svg_export(out, receipt))

    def test_sidecar_is_canonical_and_contains_no_unverified_compliance_claim(self):
        ws, rev = approved_workspace(warehouse_model())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "warehouse.svg"
            receipt = X.export_approved_svg(ws, rev.id, 0, out)
            sidecar = Path(str(out) + ".baseline.json")
            self.assertEqual(json.loads(sidecar.read_text(encoding="utf-8")), receipt)
            self.assertEqual(receipt["structural_safety"], "NOT_VERIFIED")
            self.assertEqual(receipt["fire_life_safety_compliance"], "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
