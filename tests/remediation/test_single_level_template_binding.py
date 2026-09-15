#!/usr/bin/env python3
import unittest

from acs_plan_chunks import merge_plan
from acs_plan_review import _geometry


def envelope(levels):
    return {
        "site": {"w": 50.0, "d": 100.0},
        "floor_height": 8.0,
        "wall_h": 7.5,
        "wall_t": 0.2,
        "levels": levels,
        "meta": {"type": "warehouse"},
    }


def zones():
    return [
        {"id": "receiving", "role": "receiving", "template": "t", "order": 0},
        {"id": "storage", "role": "storage", "template": "t", "order": 1},
    ]


def chunks():
    chunk = {"index": 0, "template": "t", "zone_ids": ["receiving", "storage"]}
    rooms = [
        {"id": "receiving", "role": "receiving", "rect": [0.0, 0.0, 10.0, 20.0]},
        {"id": "storage", "role": "storage", "rect": [10.0, 0.0, 30.0, 20.0]},
    ]
    return [(chunk, rooms, [])]


class SingleLevelTemplateBinding(unittest.TestCase):
    def test_single_explicit_level_owns_template_identity(self):
        levels = [{"index": 0, "id": "L0", "template": "ground", "elevation": 0.0}]
        building, issues = merge_plan(zones(), chunks(), envelope(levels))
        self.assertEqual(list(building["floors"]), ["ground"])
        self.assertEqual([r["id"] for r in building["floors"]["ground"]["rooms"]],
                         ["receiving", "storage"])
        self.assertEqual([r["rect"] for r in building["floors"]["ground"]["rooms"]],
                         [[0.0, 0.0, 10.0, 20.0], [10.0, 0.0, 30.0, 20.0]])
        self.assertIn("PLAN_SINGLE_LEVEL_TEMPLATE_REBOUND", [i.get("code") for i in issues])
        self.assertNotIn("UNREFERENCED_TEMPLATE", [i.get("code") for i in _geometry(building)[0]])

    def test_multi_level_mismatch_stays_fail_closed(self):
        levels = [
            {"index": 0, "id": "L0", "template": "ground", "elevation": 0.0},
            {"index": 1, "id": "L1", "template": "upper", "elevation": 8.0},
        ]
        building, _ = merge_plan(zones(), chunks(), envelope(levels))
        codes = [i.get("code") for i in _geometry(building)[0]]
        self.assertIn("UNREFERENCED_TEMPLATE", codes)
        self.assertIn("INVALID_LEVEL", codes)


if __name__ == "__main__":
    unittest.main()
