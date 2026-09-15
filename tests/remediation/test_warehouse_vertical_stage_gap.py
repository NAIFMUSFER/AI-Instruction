#!/usr/bin/env python3
"""RED evidence for the live warehouse vertical-stage admission gap.

This regression intentionally targets the current shared validator contract. It
must stay RED until draft-stage admission can distinguish unresolved vertical
engineering data from invalid horizontal layout geometry.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_review import _geometry


def warehouse_without_final_vertical_engineering():
    return {
        "meta": {"type": "warehouse", "name": "live-stage-gap"},
        "site": {"w": 50.0, "d": 100.0},
        "levels": [{"index": 0, "template": "ground"}],
        "floors": {"ground": {"rooms": [{
            "id": "storage",
            "role": "storage",
            "walls": "none",
            "rect": [5.0, 10.0, 40.0, 50.0],
            "doors": [], "windows": [], "racks": [], "lanes": [],
            "stations": [], "docks": [],
        }]}},
    }


class WarehouseVerticalStageGap(unittest.TestCase):
    def test_horizontal_layout_is_valid_while_vertical_values_are_unresolved(self):
        issues, metrics = _geometry(warehouse_without_final_vertical_engineering())
        codes = [row.get("code") for row in issues]
        self.assertEqual(codes, ["DIMENSION_NOT_SPECIFIED"] * 3)
        self.assertNotIn("OUTSIDE_SITE", codes)
        self.assertNotIn("ROOM_OVERLAP", codes)
        self.assertNotIn("INVALID_RECT", codes)
        # RED acceptance target: the service needs a stage-aware admission path
        # that keeps these as unresolved constraints instead of a fatal draft
        # generation error. This assertion deliberately fails on current main.
        self.assertEqual(
            [c for c in codes if c == "DIMENSION_NOT_SPECIFIED"],
            [],
            "RED: pre-approval warehouse draft currently treats unknown vertical engineering values as fatal geometry",
        )
        self.assertIsNone(metrics["space_rect_area_m2"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
