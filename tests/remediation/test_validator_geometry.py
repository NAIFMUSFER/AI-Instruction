"""C01 counterexamples; these are not the missing independent 22-issue fixture."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_validate as V


def building():
    return {"site": {"w": 20, "d": 25}, "wall_h": 3, "floor_height": 3.2,
        "meta": {"strict": True}, "levels": [{"index": 0, "template": "g"}],
        "floors": {"g": {"rooms": [{"id": "room", "rect": [1, 1, 6, 6],
            "doors": [{"edge": "N", "offset": 3}]}]}}}


class ValidatorGeometry(unittest.TestCase):
    def check_code(self, model, code, identity=""):
        before = repr(model)
        issues, _ = V.validate_building(model)
        self.assertTrue(any(code in issue and identity in issue for issue in issues), issues)
        self.assertEqual(repr(model), before, "validation must not repair or drop input")

    def test_nonfinite_site_and_floor_values(self):
        for field, value in (("w", float("nan")), ("d", float("inf")),
                             ("w", -1), ("d", "bad")):
            with self.subTest(field=field, value=value):
                model = building(); model["site"][field] = value
                self.check_code(model, "SITE_DIMENSIONS_INVALID")
        for field in ("wall_h", "wall_t", "floor_height"):
            model = building(); model[field] = float("nan")
            self.check_code(model, "BUILDING_NUMBER_INVALID", field)
        model = building(); model["levels"][0]["elevation"] = float("inf")
        self.check_code(model, "LEVEL_ELEVATION_INVALID")

    def test_invalid_room_rectangles(self):
        for rect, code in (([3, 3, -2, -2], "ROOM_DIMENSIONS_INVALID"),
                ([0, 0, 0, 2], "ROOM_DIMENSIONS_INVALID"),
                ([float("nan"), 0, 6, 6], "ROOM_RECT_NONFINITE"),
                (["bad", 0, 6, 6], "ROOM_RECT_NONFINITE"),
                ([0, 0, 6], "ROOM_RECT_INVALID")):
            with self.subTest(rect=rect):
                model = building(); model["floors"]["g"]["rooms"][0]["rect"] = rect
                self.check_code(model, code, "g/room")

    def test_duplicate_room_and_level_identity(self):
        model = building()
        model["floors"]["g"]["rooms"].append({"id": "room", "rect": [9, 1, 6, 6]})
        self.check_code(model, "ROOM_ID_DUPLICATE", "g/room")
        model = building(); model["levels"].append(copy.deepcopy(model["levels"][0]))
        self.check_code(model, "LEVEL_INDEX_DUPLICATE")

    def test_furniture_and_objects_check_footprints_not_just_centres(self):
        for kind in ("furniture", "objects"):
            for item in ({"x": 14, "z": 14, "w": 2, "d": 1},
                         {"x": 5.5, "z": 3, "w": 2, "d": 1}):
                with self.subTest(kind=kind, item=item):
                    model = building(); model["floors"]["g"]["rooms"][0][kind] = [item]
                    self.check_code(model, "ITEM_OUTSIDE_ROOM", "g/room/%s/0" % kind)
            model = building()
            model["floors"]["g"]["rooms"][0][kind] = [{"x": 3, "z": 3, "w": -2, "d": 1}]
            self.check_code(model, "ITEM_DIMENSION_INVALID", "g/room/%s/0" % kind)

    def test_each_point_and_repeated_object_is_checked(self):
        model = building(); room = model["floors"]["g"]["rooms"][0]
        room["points"] = [{"type": "light", "x": 20, "z": 1},
                          {"type": "light", "x": 30, "z": 1},
                          {"type": "light", "x": float("nan"), "z": 1}]
        room["objects"] = [{"kind": "box", "x": 1, "z": 2, "w": 1, "d": 1,
                            "count": 3, "pitch": 4, "dir": "x"}]
        for i in (0, 1):
            self.check_code(model, "POINT_OUTSIDE_ROOM", "points/%d" % i)
        self.check_code(model, "POINT_NUMBER_INVALID", "points/2")
        self.check_code(model, "ITEM_OUTSIDE_ROOM", "objects/0/instance/2")

    def test_valid_control_is_unchanged_with_no_false_alerts(self):
        model = building(); room = model["floors"]["g"]["rooms"][0]
        room["furniture"] = [{"name": "desk", "x": 1, "z": 2, "w": 2, "d": 1}]
        room["objects"] = [{"kind": "box", "x": 1, "z": 4, "w": 1, "d": 1,
                            "count": 3, "pitch": 1.5}]
        room["points"] = [{"type": "light", "x": 3, "z": 3}]
        model["levels"][0]["elevation"] = -3.2
        before = copy.deepcopy(model)
        self.assertEqual(V.validate_building(model)[0], [])
        self.assertEqual(model, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
