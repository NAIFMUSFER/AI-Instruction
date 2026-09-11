#!/usr/bin/env python3
"""Regression evidence for explicit canonical nested-element provenance.

No provider, compiler, CAD library, network, production data, or regulatory
verifier is used. These contracts prove plan identity only; an empty
``requirement_refs`` array must never be interpreted as requirement evidence.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_projection as C
from acs_plan_review import PlanError, PlanWorkspace

BRIEF = "warehouse with receiving and storage"
REQUIREMENTS = [
    {"id": "warehouse", "metric": "typology", "expected": "warehouse",
     "source": "requested", "evidence": "warehouse"},
]


def warehouse():
    return {
        "meta": {"type": "warehouse"},
        "site": {"w": 30.0, "d": 30.0},
        "floor_height": 8.0,
        "wall_h": 7.5,
        "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [
            {
                "id": "receiving",
                "role": "receiving",
                "walls": "none",
                "rect": [0.0, 0.0, 5.0, 30.0],
                "docks": [
                    {"id": "dock_n1", "edge": "N", "offset": 2.0,
                     "width": 3.6, "height": 4.2},
                    {"edge": "N", "offset": 8.0, "width": 3.6, "height": 4.2},
                ],
            },
            {
                "id": "storage",
                "role": "storage",
                "walls": "none",
                "rect": [5.0, 0.0, 25.0, 30.0],
                "racks": [
                    {"id": "rack_a", "kind": "pallet", "x": 1.0, "z": 1.0,
                     "w": 12.0, "d": 28.0, "dir": "z", "rows": 2,
                     "levels": 4, "h": 8.0},
                ],
                "lanes": [
                    {"id": "lane_main", "x": 14.0, "z": 1.0,
                     "w": 3.0, "d": 28.0},
                ],
            },
        ]}},
    }


class ExplicitElementProvenanceTests(unittest.TestCase):
    def setUp(self):
        ws = PlanWorkspace()
        self.rev = ws.propose(
            warehouse(), brief=BRIEF, requirements=REQUIREMENTS,
            expected_head=None, note="explicit element provenance fixture",
        )

    def element_entries(self):
        return [
            row for row in C.provenance_map(self.rev)["entries"]
            if row["source"]["kind"] == "element"
        ]

    def test_unlinked_explicit_warehouse_elements_keep_stable_plan_identity(self):
        first = self.element_entries()
        second = self.element_entries()
        by_identity = {
            (row["source"]["collection"], row["source"]["element_id"]): row
            for row in first
        }
        self.assertEqual(set(by_identity), {
            ("docks", "dock_n1"),
            ("racks", "rack_a"),
            ("lanes", "lane_main"),
        })
        self.assertTrue(all(row["requirement_refs"] == [] for row in first))
        self.assertEqual(
            [row["source_id"] for row in first],
            [row["source_id"] for row in second],
        )
        self.assertTrue(all(row["source_id"].startswith("plan_") for row in first))

    def test_unidentified_unlinked_nested_geometry_is_not_promoted_to_identity(self):
        # The second dock has geometry but no explicit canonical id. Preserve the
        # existing fail-closed boundary: never turn its array index into source_id.
        dock_ids = {
            row["source"]["element_id"] for row in self.element_entries()
            if row["source"]["collection"] == "docks"
        }
        self.assertEqual(dock_ids, {"dock_n1"})

    def test_duplicate_explicit_id_cannot_create_two_identical_source_ids(self):
        # Revision admission currently permits two unlinked nested elements with
        # the same explicit id. Once PR #51 gives every explicit nested element a
        # provenance identity, silently emitting the same plan_<sha256> twice
        # would make downstream 3D/export selection ambiguous. Projection must
        # fail closed rather than choose by array position or collapse the rows.
        model = copy.deepcopy(warehouse())
        model["floors"]["ground"]["rooms"][1]["racks"].append({
            "id": "rack_a", "kind": "pallet", "x": 16.0, "z": 1.0,
            "w": 7.0, "d": 28.0, "dir": "z", "rows": 1,
            "levels": 4, "h": 8.0,
        })
        ws = PlanWorkspace()
        rev = ws.propose(
            model, brief=BRIEF, requirements=REQUIREMENTS,
            expected_head=None, note="duplicate nested provenance identity fixture",
        )
        with self.assertRaises(PlanError) as ctx:
            C.provenance_map(rev)
        self.assertEqual(ctx.exception.code, "AMBIGUOUS_PROVENANCE_TARGET")


if __name__ == "__main__":
    unittest.main(verbosity=2)
