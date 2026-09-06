"""C05: inspect actual exported vertex bounds, not a mirrored formula."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_arch
import acs_compiler


def building(elevation=None):
    level = {"index": 1, "template": "upper"}
    if elevation is not None:
        level["elevation"] = elevation
    return {"site": {"w": 20, "d": 25}, "floor_height": 3.2, "wall_h": 3,
            "wall_t": .15, "levels": [level], "meta": {"strict": True},
            "floors": {"upper": {"rooms": [{
                "id": "room", "rect": [1, 2, 6, 6], "walls": "full",
                "doors": [{"edge": "N", "offset": 3, "width": 1, "height": 2.1}],
                "windows": [{"edge": "S", "offset": 3, "width": 1.2,
                             "height": 1.2, "sill": 1.1}],
                "furniture": [{"name": "desk", "x": 2, "z": 2, "w": 1,
                               "d": 1, "h": .8}]}]}}}


def bounds(model):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "model.gltf"
        acs_compiler.compile_building(model, str(p))
        doc = json.loads(p.read_text())
    result = {}
    for node in doc["nodes"]:
        if "|F1|" not in node.get("name", ""):
            continue
        mesh = doc["meshes"][node["mesh"]]["primitives"][0]
        pos = doc["accessors"][mesh["attributes"]["POSITION"]]
        result[node["name"]] = {"min": pos["min"], "max": pos["max"]}
    return result


class LevelElevation(unittest.TestCase):
    def test_explicit_elevation_moves_all_exported_geometry(self):
        original, raised = building(), building(7.5)
        before = copy.deepcopy(raised)
        a, b = bounds(original), bounds(raised)
        self.assertEqual(set(a), set(b))
        self.assertTrue(a)
        self.assertEqual({"FLOOR", "WALL", "DOOR", "WINDOW", "FURN"},
                         {n.split("|")[0] for n in b})
        for name in a:
            for extent in ("min", "max"):
                self.assertAlmostEqual(b[name][extent][1] - a[name][extent][1], 4.3, places=5, msg=name)
                self.assertEqual(b[name][extent][0], a[name][extent][0], name)
                self.assertEqual(b[name][extent][2], a[name][extent][2], name)
        self.assertEqual(raised, before, "export must not change Building")
        self.assertEqual(acs_arch.compile_architecture(raised)["levels"][0]["elevation_m"], 7.5)

    def test_explicit_zero_and_basement_and_legacy_fallback(self):
        for stated, expected in ((0, 0), (-3.5, -3.5), (None, 3.2)):
            with self.subTest(elevation=stated):
                actual = bounds(building(stated))
                floor = [v for n,v in actual.items() if n.startswith("FLOOR|")]
                self.assertTrue(floor)
                self.assertTrue(all(abs(v["max"][1] - expected) < 1e-5 for v in floor))


if __name__ == "__main__":
    unittest.main(verbosity=2)
