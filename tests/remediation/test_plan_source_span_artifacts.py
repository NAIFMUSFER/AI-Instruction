#!/usr/bin/env python3
"""Source-span provenance regressions for CAD/3D artifacts.

Synthetic fixtures only. These tests verify traceability metadata; they do not
claim semantic extraction quality, code compliance, or architectural approval.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_projection import provenance_map
from acs_plan_review import PlanError, PlanWorkspace, digest
from tools.acs_plan_handoff import compile_approved_baseline

BRIEF = "مستودع بعرض 30 متر مع استلام وشحن، وثبت رصيف الاستلام والرف A."


def verifier(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": []}


def span(text: str):
    start = BRIEF.index(text)
    return {"start": start, "end": start + len(text)}


def requirements(*, include_spans=True):
    rows = [
        {"id": "site-width", "source": "requested", "evidence": "30",
         "metric": "site_width_m", "expected": 30.0, "source_id": "brief-main"},
        {"id": "receiving-zone", "source": "requested", "evidence": "استلام",
         "metric": "room_count", "expected": 1, "role": "receiving"},
        {"id": "dock-anchor", "source": "requested", "evidence": "رصيف الاستلام",
         "metric": "room_count", "expected": 1, "role": "receiving",
         "source_id": "brief-main"},
        {"id": "rack-anchor", "source": "requested", "evidence": "الرف A",
         "metric": "room_count", "expected": 1, "role": "storage",
         "source_id": "brief-main"},
    ]
    if include_spans:
        for row in rows:
            row["source_span"] = span(row["evidence"])
    return rows


def warehouse():
    return {
        "meta": {"type": "warehouse"},
        "site": {"w": 30.0, "d": 30.0},
        "floor_height": 8.0, "wall_h": 7.5, "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "receiving", "role": "receiving", "walls": "none",
             "rect": [0.0, 0.0, 5.0, 30.0],
             "requirement_ids": ["receiving-zone"],
             "docks": [{"id": "dock_n1", "edge": "N", "offset": 2.0,
                         "width": 3.6, "height": 4.2, "count": 1, "pitch": 5.4,
                         "requirement_ids": ["dock-anchor"]}]},
            {"id": "storage", "role": "storage", "walls": "none",
             "rect": [5.0, 0.0, 25.0, 30.0],
             "racks": [{"id": "rack_a", "kind": "pallet", "x": 1.0, "z": 1.0,
                         "w": 20.0, "d": 28.0, "dir": "z", "rows": 2,
                         "depth": 1.10, "bay": 2.70, "aisle": 3.40,
                         "levels": 4, "h": 8.0,
                         "requirement_ids": ["rack-anchor"]}]},
        ]}},
    }


def workspace(reqs=None, *, brief=BRIEF):
    ws = PlanWorkspace(verifier)
    rev = ws.propose(warehouse(), brief=brief,
                     requirements=reqs if reqs is not None else requirements(),
                     expected_head=None, note="artifact provenance fixture")
    return ws, rev


def refs_by_requirement(provenance):
    out = {}
    for entry in provenance["entries"]:
        for ref in entry["requirement_refs"]:
            out.setdefault(ref["requirement_id"], []).append(ref)
    return out


class SourceSpanArtifactTests(unittest.TestCase):
    def assertCode(self, code, call):
        with self.assertRaises(PlanError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def test_space_requirement_ref_preserves_exact_span_without_evidence_text(self):
        _ws, rev = workspace()
        refs = refs_by_requirement(provenance_map(rev))["receiving-zone"]
        self.assertEqual(refs, [{
            "requirement_id": "receiving-zone",
            "source": "requested",
            "source_id": None,
            "source_span": span("استلام"),
        }])
        self.assertNotIn("evidence", refs[0])

    def test_warehouse_rack_and_dock_refs_preserve_span_and_external_source_id(self):
        _ws, rev = workspace()
        refs = refs_by_requirement(provenance_map(rev))
        self.assertEqual(refs["dock-anchor"][0]["source_id"], "brief-main")
        self.assertEqual(refs["dock-anchor"][0]["source_span"], span("رصيف الاستلام"))
        self.assertEqual(refs["rack-anchor"][0]["source_id"], "brief-main")
        self.assertEqual(refs["rack-anchor"][0]["source_span"], span("الرف A"))

    def test_legacy_requirement_does_not_receive_fabricated_span(self):
        _ws, rev = workspace(requirements(include_spans=False))
        refs = refs_by_requirement(provenance_map(rev))
        self.assertNotIn("source_span", refs["receiving-zone"][0])
        self.assertNotIn("source_span", refs["dock-anchor"][0])

    def test_mismatched_explicit_span_fails_projection_provenance_closed(self):
        reqs = requirements()
        reqs[1]["source_span"] = span("شحن")
        _ws, rev = workspace(reqs)
        self.assertCode("INVALID_PROVENANCE", lambda: provenance_map(rev))

    def test_malformed_explicit_span_fails_projection_provenance_closed(self):
        reqs = requirements()
        reqs[1]["source_span"] = {"start": True, "end": 4}
        _ws, rev = workspace(reqs)
        self.assertCode("INVALID_PROVENANCE", lambda: provenance_map(rev))

    def test_approved_3d_receipt_carries_exact_source_spans_and_hash_binding(self):
        ws, rev = workspace()
        ws.approve(rev.id, expected_head=rev.id, actor_label="Test engineer",
                   confirmed=True, acknowledge_concept_only=True)

        def compiler(_building, out_path):
            Path(out_path).write_text(json.dumps({"asset": {"version": "2.0"}}), encoding="utf-8")
            return (1, 0)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "approved.gltf"
            receipt = compile_approved_baseline(ws, rev.id, out, compiler=compiler)
            refs = refs_by_requirement({"entries": receipt["source_map"]})
            self.assertEqual(refs["dock-anchor"][0]["source_span"], span("رصيف الاستلام"))
            self.assertEqual(refs["rack-anchor"][0]["source_span"], span("الرف A"))
            self.assertEqual(receipt["source_map_hash"], digest(receipt["source_map"]))
            self.assertEqual(receipt["provider_calls"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
