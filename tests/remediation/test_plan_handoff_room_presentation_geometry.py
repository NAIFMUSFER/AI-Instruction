#!/usr/bin/env python3
"""Red-first proof for approved-baseline room presentation geometry.

The legacy compiler defaults door/window dimensions, point placement/type/height,
and furniture dimensions/material/name. After engineer approval those values must
not be invented by downstream 3D. This test intentionally fails until the handoff
boundary rejects such implicit geometry/semantics before compiler invocation.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import acs_plan_handoff as H
from acs_plan_review import PlanError


def residential():
    return {
        "meta": {"type": "residential", "name": "explicit-room-presentation"},
        "site": {"w": 20.0, "d": 20.0},
        "floor_height": 3.2, "wall_h": 3.0, "wall_t": 0.15,
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [{
            "id": "majlis", "role": "majlis", "rect": [0.0, 0.0, 8.0, 6.0],
            "doors": [{"id": "d1", "edge": "S", "offset": 2.0, "width": 1.0, "height": 2.2, "material": "wood"}],
            "windows": [{"id": "w1", "edge": "N", "offset": 2.5, "width": 1.5, "sill": 0.9, "height": 1.4}],
            "points": [{"id": "p1", "type": "outlet", "x": 1.0, "z": 1.0, "height": 0.4}],
            "furniture": [{"id": "f1", "name": "table", "x": 3.0, "z": 3.0, "w": 1.2, "d": 0.8, "h": 0.75, "mat": "furn"}],
        }]}}
    }


class ApprovedRoomPresentationGeometryTests(unittest.TestCase):
    def test_explicit_control_is_accepted_without_mutation(self):
        model = residential(); before = copy.deepcopy(model)
        H._require_explicit_approved_room_presentation_geometry(model)
        self.assertEqual(model, before)

    def test_downstream_defaults_are_rejected(self):
        cases = [
            ("door width", "doors", "width"), ("door height", "doors", "height"),
            ("window width", "windows", "width"), ("window sill", "windows", "sill"),
            ("window height", "windows", "height"), ("point type", "points", "type"),
            ("point x", "points", "x"), ("point z", "points", "z"),
            ("point height", "points", "height"), ("furniture w", "furniture", "w"),
            ("furniture d", "furniture", "d"), ("furniture h", "furniture", "h"),
            ("furniture mat", "furniture", "mat"), ("furniture name", "furniture", "name"),
        ]
        for label, collection, key in cases:
            with self.subTest(label=label):
                model = residential(); del model["floors"]["ground"]["rooms"][0][collection][0][key]
                with self.assertRaises(PlanError):
                    H._require_explicit_approved_room_presentation_geometry(model)

    def test_unknown_point_type_is_rejected_instead_of_becoming_outlet(self):
        model = residential(); model["floors"]["ground"]["rooms"][0]["points"][0]["type"] = "mystery"
        with self.assertRaises(PlanError):
            H._require_explicit_approved_room_presentation_geometry(model)


if __name__ == "__main__":
    unittest.main(verbosity=2)
