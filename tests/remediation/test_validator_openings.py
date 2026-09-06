"""C07: invalid openings are diagnosed, without changing requested geometry."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_validate as V


def building():
    return {"site": {"w": 20, "d": 25}, "wall_h": 3,
        "meta": {"strict": True}, "levels": [{"index": 0, "template": "g"}],
        "floors": {"g": {"rooms": [{"id": "room", "rect": [1, 1, 6, 6],
            "doors": [{"edge": "N", "offset": 3}],
            "windows": [{"edge": "S", "offset": 3}]}]}}}


class ValidatorOpenings(unittest.TestCase):
    def test_each_invalid_opening_is_reported_with_its_identity(self):
        cases = [
            ("doors", {"edge": "Q"}, "OPENING_EDGE_INVALID"),
            ("doors", {"edge": None}, "OPENING_EDGE_INVALID"),
            ("doors", {"offset": None}, "OPENING_NUMBER_INVALID"),
            ("doors", {"offset": float("nan")}, "OPENING_NUMBER_INVALID"),
            ("doors", {"width": float("inf")}, "OPENING_NUMBER_INVALID"),
            ("doors", {"width": 0}, "OPENING_WIDTH_NON_POSITIVE"),
            ("windows", {"width": -1}, "OPENING_WIDTH_NON_POSITIVE"),
            ("doors", {"height": 0}, "OPENING_HEIGHT_NON_POSITIVE"),
            ("windows", {"height": -1}, "OPENING_HEIGHT_NON_POSITIVE"),
            ("doors", {"height": float("nan")}, "OPENING_NUMBER_INVALID"),
            ("windows", {"sill": -0.2}, "WINDOW_SILL_NEGATIVE"),
            ("windows", {"sill": float("nan")}, "OPENING_NUMBER_INVALID"),
            ("doors", {"height": 8}, "OPENING_ABOVE_WALL"),
            ("windows", {"sill": 2.5, "height": 2}, "OPENING_ABOVE_WALL"),
            ("doors", {"offset": 8}, "OPENING_OUTSIDE_WALL"),
        ]
        for kind, values, code in cases:
            with self.subTest(kind=kind, values=values):
                model = building()
                model["floors"]["g"]["rooms"][0][kind][0].update(values)
                before = repr(model)
                issues, _ = V.validate_building(model)
                self.assertTrue(any(code in s and "g/room/%s/0" % kind in s
                                    for s in issues), issues)
                self.assertEqual(repr(model), before)

    def test_uses_room_wall_height_and_reports_every_opening(self):
        model = building()
        room = model["floors"]["g"]["rooms"][0]
        room["wall_h"] = 2
        room["doors"] = [{"edge": "N", "offset": 2, "height": 2.4},
                         {"edge": "S", "offset": 2, "height": 2.8}]
        issues, _ = V.validate_building(model)
        self.assertTrue(any("doors/0" in s and "OPENING_ABOVE_WALL" in s for s in issues))
        self.assertTrue(any("doors/1" in s and "OPENING_ABOVE_WALL" in s for s in issues))

    def test_valid_edges_defaults_and_exact_boundaries_have_no_false_alerts(self):
        for edge in ("N", "S", "E", "W"):
            model = building()
            room = model["floors"]["g"]["rooms"][0]
            room["doors"] = [{"edge": edge, "offset": 0.5, "width": 1, "height": 3}]
            room["windows"] = [{"edge": edge, "offset": 5, "width": 2,
                                "height": 3, "sill": 0}]
            self.assertEqual(V.validate_building(model)[0], [])
        self.assertEqual(V.validate_building(building())[0], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
