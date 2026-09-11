#!/usr/bin/env python3
"""Requirement-evidence regressions for the Plan-first canonical review boundary.

Synthetic fixtures only. These tests prove brief-span provenance integrity; they do
not claim semantic extraction quality, regulatory compliance, or live provider use.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_review as P

BRIEF = "أرض 20 في 25، دورين، ومستودع به منطقة استلام وشحن."


def model():
    return {
        "site": {"w": 20.0, "d": 25.0},
        "floor_height": 8.0,
        "wall_h": 7.5,
        "wall_t": 0.2,
        "meta": {"type": "warehouse"},
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "receiving", "role": "receiving", "walls": "none",
             "rect": [0.0, 0.0, 10.0, 25.0]},
            {"id": "shipping", "role": "shipping", "walls": "none",
             "rect": [10.0, 0.0, 10.0, 25.0]},
        ]}},
    }


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"},
            "issues": []}


def requested(rid: str, evidence: str, metric: str, expected, *, span=True, source_id=None):
    row = {"id": rid, "source": "requested", "evidence": evidence,
           "metric": metric, "expected": expected}
    if span is True:
        start = BRIEF.index(evidence)
        row["source_span"] = {"start": start, "end": start + len(evidence)}
    elif span is not False:
        row["source_span"] = span
    if source_id is not None:
        row["source_id"] = source_id
    return row


def review(requirements, *, brief=BRIEF):
    ws = P.PlanWorkspace(verified)
    rev = ws.propose(model(), brief=brief, requirements=requirements,
                     expected_head=None, note="evidence test")
    return ws, rev, ws.review(rev.id)


class RequirementEvidenceTests(unittest.TestCase):
    def codes(self, result):
        return {x["code"] for x in result["issues"]}

    def test_exact_numeric_brief_span_is_accepted(self):
        _ws, _rev, out = review([requested("width", "20", "site_width_m", 20.0)])
        self.assertNotIn("INVALID_SOURCE_SPAN", self.codes(out))
        self.assertNotIn("SOURCE_SPAN_MISMATCH", self.codes(out))
        self.assertNotIn("MISSING_SOURCE_EVIDENCE", self.codes(out))

    def test_exact_arabic_brief_span_is_accepted_by_character_offsets(self):
        row = requested("floors", "دورين", "level_count", 1)
        # Metric mismatch is expected because this warehouse fixture has one level;
        # the source-evidence contract itself must still validate independently.
        _ws, _rev, out = review([row])
        self.assertNotIn("INVALID_SOURCE_SPAN", self.codes(out))
        self.assertNotIn("SOURCE_SPAN_MISMATCH", self.codes(out))
        self.assertIn("REQUIREMENT_MISMATCH", self.codes(out))

    def test_out_of_bounds_span_is_rejected(self):
        row = requested("width", "20", "site_width_m", 20.0,
                        span={"start": len(BRIEF) + 1, "end": len(BRIEF) + 3})
        _ws, _rev, out = review([row])
        self.assertIn("INVALID_SOURCE_SPAN", self.codes(out))

    def test_negative_reversed_and_boolean_offsets_are_rejected(self):
        bad = [
            {"start": -1, "end": 1},
            {"start": 5, "end": 4},
            {"start": True, "end": 2},
        ]
        for span in bad:
            with self.subTest(span=span):
                row = requested("width", "20", "site_width_m", 20.0, span=span)
                _ws, _rev, out = review([row])
                self.assertIn("INVALID_SOURCE_SPAN", self.codes(out))

    def test_span_must_resolve_to_exact_evidence_text(self):
        start = BRIEF.index("25")
        row = requested("width", "20", "site_width_m", 20.0,
                        span={"start": start, "end": start + 2})
        _ws, _rev, out = review([row])
        self.assertIn("SOURCE_SPAN_MISMATCH", self.codes(out))

    def test_span_bound_to_old_brief_cannot_be_reused_after_brief_change(self):
        row = requested("width", "20", "site_width_m", 20.0)
        changed = "أرض عشرون في 25، دورين، ومستودع به منطقة استلام وشحن."
        _ws, _rev, out = review([row], brief=changed)
        self.assertIn("SOURCE_SPAN_MISMATCH", self.codes(out))

    def test_external_source_id_does_not_bypass_brief_span_validation(self):
        start = BRIEF.index("25")
        row = requested("width", "20", "site_width_m", 20.0,
                        span={"start": start, "end": start + 2}, source_id="brief-upload-7")
        _ws, _rev, out = review([row])
        self.assertIn("SOURCE_SPAN_MISMATCH", self.codes(out))

    def test_malformed_span_shape_is_rejected(self):
        bad = [None, [1, 3], {"start": 1}, {"start": 1, "end": 3, "page": 1}]
        for span in bad:
            with self.subTest(span=span):
                row = requested("width", "20", "site_width_m", 20.0, span=span)
                _ws, _rev, out = review([row])
                self.assertIn("INVALID_SOURCE_SPAN", self.codes(out))

    def test_legacy_requested_evidence_without_span_remains_reviewable(self):
        # Existing callers are not silently upgraded to a stronger provenance claim.
        row = requested("width", "20", "site_width_m", 20.0, span=False)
        _ws, _rev, out = review([row])
        self.assertNotIn("INVALID_SOURCE_SPAN", self.codes(out))
        self.assertNotIn("SOURCE_SPAN_MISMATCH", self.codes(out))
        self.assertNotIn("MISSING_SOURCE_EVIDENCE", self.codes(out))

    def test_invalid_span_blocks_conceptual_approval(self):
        row = requested("width", "20", "site_width_m", 20.0,
                        span={"start": 0, "end": 2})
        ws, rev, out = review([row])
        self.assertIn("SOURCE_SPAN_MISMATCH", self.codes(out))
        with self.assertRaises(P.PlanError) as caught:
            ws.approve(rev.id, expected_head=rev.id, actor_label="Engineer",
                       confirmed=True, acknowledge_concept_only=True)
        self.assertEqual(caught.exception.code, "APPROVAL_BLOCKED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
