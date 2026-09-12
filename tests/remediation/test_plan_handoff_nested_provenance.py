#!/usr/bin/env python3
"""Red-first contract for Frozen-Baseline nested-element provenance.

Approved 3D may contain geometry from rooms' nested collections only when every
renderable canonical element has a stable explicit identity.  The identity is
what acs_plan_projection.provenance_map() uses to derive a deterministic
source_id.  Missing identities must therefore fail before compiler invocation;
they must never be invented from array position.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import acs_plan_handoff as H
from acs_plan_review import PlanError


COLLECTIONS = (
    "racks", "docks", "lanes", "stations", "doors", "windows",
    "objects", "points", "furniture",
)


def building() -> dict:
    room = {"id": "zone-a", "rect": [0.0, 0.0, 20.0, 15.0]}
    for collection in COLLECTIONS:
        room[collection] = [{"id": f"{collection}-1"}]
    return {
        "meta": {"type": "warehouse"},
        "site": {"w": 30.0, "d": 25.0},
        "floor_height": 6.0,
        "wall_h": 5.5,
        "wall_t": 0.2,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [room]}},
    }


class ApprovedNestedProvenanceTests(unittest.TestCase):
    def test_all_explicit_nested_identities_pass_without_mutation(self):
        model = building()
        before = copy.deepcopy(model)
        H._require_traceable_approved_nested_elements(model)
        self.assertEqual(model, before)

    def test_every_renderable_nested_collection_requires_explicit_identity(self):
        for collection in COLLECTIONS:
            with self.subTest(collection=collection):
                model = building()
                del model["floors"]["ground"]["rooms"][0][collection][0]["id"]
                with self.assertRaises(PlanError):
                    H._require_traceable_approved_nested_elements(model)

    def test_blank_or_unbounded_identity_fails_closed(self):
        for bad_id in ("", "   ", "x" * 161):
            with self.subTest(bad_id=repr(bad_id)):
                model = building()
                model["floors"]["ground"]["rooms"][0]["objects"][0]["id"] = bad_id
                with self.assertRaises(PlanError):
                    H._require_traceable_approved_nested_elements(model)

    def test_missing_collection_is_not_invented(self):
        model = building()
        del model["floors"]["ground"]["rooms"][0]["furniture"]
        before = copy.deepcopy(model)
        H._require_traceable_approved_nested_elements(model)
        self.assertEqual(model, before)
        self.assertNotIn("furniture", model["floors"]["ground"]["rooms"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
