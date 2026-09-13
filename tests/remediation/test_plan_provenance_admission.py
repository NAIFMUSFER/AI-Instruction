#!/usr/bin/env python3
"""Admission-time provenance-link regressions for ACS Plan-first v2.

These tests exercise only the canonical revision boundary. They do not call a
provider, compiler, live datastore, or engineering verifier. The purpose is to
prove that malformed/ambiguous requirement links cannot enter revision history
while valid explicit residential/warehouse links are preserved exactly.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_review as P

BRIEF = "site width 30 warehouse; bedroom requested"


def requirements():
    return [
        {"id": "site-width", "metric": "site_width_m", "expected": 30.0,
         "source": "requested", "evidence": "site width 30"},
        {"id": "bedroom", "metric": "room_count", "role": "bedroom", "expected": 1,
         "source": "requested", "evidence": "bedroom requested"},
    ]


def residential():
    return {
        "meta": {"type": "residential"},
        "site": {"w": 30.0, "d": 20.0},
        "floor_height": 3.2, "wall_h": 3.0, "wall_t": 0.15,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "bed", "role": "bedroom", "rect": [0.0, 0.0, 4.0, 4.0]},
            {"id": "hall", "role": "corridor", "rect": [4.0, 0.0, 3.0, 4.0]},
        ]}},
    }


def warehouse():
    return {
        "meta": {"type": "warehouse"},
        "site": {"w": 30.0, "d": 30.0},
        "floor_height": 8.0, "wall_h": 7.5, "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {"id": "receiving", "role": "receiving", "walls": "none",
             "rect": [0.0, 0.0, 5.0, 30.0],
             "docks": [{"id": "dock_n1", "edge": "N", "offset": 2.0,
                         "width": 3.6, "height": 4.2}]},
            {"id": "storage", "role": "storage", "walls": "none",
             "rect": [5.0, 0.0, 25.0, 30.0],
             "racks": [{"id": "rack_a", "kind": "pallet", "x": 1.0, "z": 1.0,
                         "w": 12.0, "d": 28.0, "dir": "z", "rows": 2,
                         "levels": 4, "h": 8.0}]},
        ]}},
    }


class ProvenanceAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.ws = P.PlanWorkspace()

    def propose(self, model, reqs=None):
        return self.ws.propose(model, brief=BRIEF, requirements=requirements() if reqs is None else reqs,
                               expected_head=self.ws.head, note="provenance admission fixture")

    def assertCode(self, code, fn):
        with self.assertRaises(P.PlanError) as got:
            fn()
        self.assertEqual(got.exception.code, code)

    def test_unknown_room_requirement_link_is_rejected_before_history_extension(self):
        m = residential(); m["floors"]["ground"]["rooms"][0]["requirement_ids"] = ["missing"]
        self.assertCode("INVALID_PROVENANCE_LINK", lambda: self.propose(m))
        self.assertEqual(self.ws.history(), [])

    def test_duplicate_and_non_array_requirement_links_are_rejected(self):
        for links in (["bedroom", "bedroom"], "bedroom", [None]):
            with self.subTest(links=links):
                ws = P.PlanWorkspace(); m = residential()
                m["floors"]["ground"]["rooms"][0]["requirement_ids"] = links
                with self.assertRaises(P.PlanError) as got:
                    ws.propose(m, brief=BRIEF, requirements=requirements(), expected_head=None,
                               note="bad provenance fixture")
                self.assertEqual(got.exception.code, "INVALID_PROVENANCE_LINK")
                self.assertEqual(ws.history(), [])

    def test_linked_nested_element_requires_stable_explicit_identity(self):
        m = warehouse(); rack = m["floors"]["ground"]["rooms"][1]["racks"][0]
        rack.pop("id"); rack["requirement_ids"] = ["site-width"]
        self.assertCode("AMBIGUOUS_PROVENANCE_TARGET", lambda: self.propose(m))
        self.assertEqual(self.ws.history(), [])

    def test_nested_unknown_requirement_link_is_rejected(self):
        m = warehouse(); dock = m["floors"]["ground"]["rooms"][0]["docks"][0]
        dock["requirement_ids"] = ["unknown-dock-source"]
        self.assertCode("INVALID_PROVENANCE_LINK", lambda: self.propose(m))

    def test_invalid_optional_requirement_source_id_is_rejected_at_admission(self):
        reqs = requirements(); reqs[0]["source_id"] = ""
        self.assertCode("INVALID_PROVENANCE_SOURCE_ID", lambda: self.propose(residential(), reqs))
        self.assertEqual(self.ws.history(), [])

    def test_valid_residential_link_is_preserved_exactly(self):
        m = residential(); m["floors"]["ground"]["rooms"][0]["requirement_ids"] = ["bedroom"]
        rev = self.propose(m)
        self.assertEqual(rev.model, m)
        self.assertEqual(rev.model["floors"]["ground"]["rooms"][0]["requirement_ids"], ["bedroom"])

    def test_valid_warehouse_rack_and_dock_links_are_preserved_exactly(self):
        m = warehouse()
        m["floors"]["ground"]["rooms"][0]["docks"][0]["requirement_ids"] = ["site-width"]
        m["floors"]["ground"]["rooms"][1]["racks"][0]["requirement_ids"] = ["site-width"]
        rev = self.propose(m)
        self.assertEqual(rev.model, m)

    def test_unlinked_malformed_program_remains_review_issue_not_admission_crash(self):
        # Preserve the existing product boundary: malformed Program rows that are
        # not referenced by canonical entities remain review findings, so the
        # engineer can see/correct them rather than losing the draft silently.
        rev = self.propose(residential(), [None])
        self.assertIn("INVALID_REQUIREMENT", {x["code"] for x in self.ws.review(rev.id)["issues"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
