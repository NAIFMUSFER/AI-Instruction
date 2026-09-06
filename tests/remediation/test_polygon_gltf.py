"""C09a: assert geometry from exported binary buffers, including the missing notch."""
import base64
import copy
import json
import math
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_compiler as C

L = [[0, 0], [6, 0], [6, 2], [2, 2], [2, 6], [0, 6]]


def model(points=L, **room_fields):
    xs, zs = zip(*points)
    room = {"id": "polygon", "rect": [min(xs), min(zs), max(xs)-min(xs), max(zs)-min(zs)],
            "polygon": copy.deepcopy(points), "walls": "full", **room_fields}
    return {"site": {"w": 20, "d": 25}, "wall_h": 3, "wall_t": .15,
            "floor_height": 3.2, "levels": [{"index": 0, "template": "plan", "elevation": 7}],
            "floors": {"plan": {"rooms": [room]}}}


def exported(building):
    before = copy.deepcopy(building)
    with tempfile.TemporaryDirectory() as td:
        path = Path(td)/"building.gltf"
        C.compile_building(building, str(path))
        doc = json.loads(path.read_text())
    assert building == before, "compilation must not alter the input"
    data = base64.b64decode(doc["buffers"][0]["uri"].split(",", 1)[1])

    def read(index):
        a = doc["accessors"][index]
        v = doc["bufferViews"][a["bufferView"]]
        width = {"VEC3": 3, "SCALAR": 1}[a["type"]]
        fmt = {5126: "f", 5125: "I"}[a["componentType"]]
        flat = struct.unpack_from("<"+fmt*a["count"]*width, data,
                                  v.get("byteOffset", 0)+a.get("byteOffset", 0))
        return [flat[i:i+width] for i in range(0, len(flat), width)]

    result = {}
    for node in doc["nodes"]:
        primitive = doc["meshes"][node["mesh"]]["primitives"][0]
        vertices = read(primitive["attributes"]["POSITION"])
        indices = [v[0] for v in read(primitive["indices"])]
        result[node["name"]] = [tuple(vertices[j] for j in indices[i:i+3])
                                for i in range(0, len(indices), 3)]
    return result


def top_triangles(meshes, token="|slab|", elevation=7):
    return [t for name, triangles in meshes.items() if token in name for t in triangles
            if all(abs(p[1]-elevation) < 1e-5 for p in t)]


def area(triangles):
    return sum(abs((b[0]-a[0])*(c[2]-a[2])-(b[2]-a[2])*(c[0]-a[0]))/2
               for a, b, c in triangles)


def covers(triangle, x, z):
    cross = [(b[0]-a[0])*(z-a[2])-(b[2]-a[2])*(x-a[0])
             for a, b in zip(triangle, triangle[1:]+triangle[:1])]
    return all(v >= -1e-6 for v in cross) or all(v <= 1e-6 for v in cross)


class PolygonGltf(unittest.TestCase):
    def test_concave_slab_area_and_notch(self):
        triangles = top_triangles(exported(model()))
        self.assertTrue(triangles)
        self.assertAlmostEqual(area(triangles), 20, places=5)
        self.assertFalse(any(covers(t, 4, 4) for t in triangles))
        self.assertTrue(any(covers(t, 1, 5) for t in triangles))

    def test_diagonal_wall_opening_keeps_position_and_width(self):
        b = model([[3, 4], [9, 4], [3, 10]],
                  doors=[{"edge_index": 1, "offset": math.sqrt(18), "width": 1, "height": 2.1}])
        meshes = exported(b)
        door = next(t for n, t in meshes.items() if n.startswith("DOOR|"))
        points = [p for t in door for p in t]
        for axis, expected in ((0, 6), (2, 7)):
            self.assertAlmostEqual((max(p[axis] for p in points)+min(p[axis] for p in points))/2,
                                   expected, places=5)
        self.assertAlmostEqual(max(p[1] for p in points)-min(p[1] for p in points), 2.1, places=5)
        # Door plane follows the sloping edge; it is not an axis-aligned substitute.
        along = [(-p[0]+p[2])/math.sqrt(2) for p in points]
        self.assertAlmostEqual(max(along)-min(along), 1, places=5)
        self.assertAlmostEqual(area(top_triangles(meshes)), 18, places=5)

    def test_core_void_and_coloured_finishes_keep_the_notch(self):
        b = model(floor_color="#ff0000", ceiling_color="#00ff00",
                  objects=[{"kind": "stairs", "core_id": "A", "x": 1, "z": 3,
                            "w": 1, "d": 1, "h": 3}])
        b["levels"].insert(0, {"index": -1, "template": "plan", "elevation": 3.8})
        meshes = exported(b)
        slab = top_triangles(meshes)
        self.assertAlmostEqual(area(slab), 19, places=5)
        self.assertFalse(any(covers(t, 1, 3) for t in slab))
        for token, y in (("|plate", 7.024), ("|ceil", 9.995)):
            finish = top_triangles(meshes, token, y)
            self.assertTrue(finish, token)
            self.assertFalse(any(covers(t, 4, 4) for t in finish))
            self.assertFalse(any(covers(t, 1, 3) for t in finish))

    def test_invalid_ring_fails_before_file_is_written(self):
        for points in ([[0,0],[6,6],[0,6],[6,0]], [[0,0],[6,0],[6,0],[0,6]]):
            with self.subTest(points=points), tempfile.TemporaryDirectory() as td:
                path = Path(td)/"wrong.gltf"
                with self.assertRaisesRegex(ValueError, "POLYGON"):
                    C.compile_building(model(points), str(path))
                self.assertFalse(path.exists())

    def test_union_diagonal_intersections_and_winding(self):
        # Intersection is [(0,2),(2,4),(4,2)], area 4: union=18+18-4=32.
        b = model([[0,0],[6,0],[0,6]])
        b["floors"]["plan"]["rooms"].append(model([[0,2],[6,2],[6,8]])["floors"]["plan"]["rooms"][0])
        b["floors"]["plan"]["rooms"][1]["id"] = "other"
        self.assertAlmostEqual(area(top_triangles(exported(b))), 32, places=5)
        clockwise = model(list(reversed(L)), walls="none")
        meshes = exported(clockwise)
        self.assertAlmostEqual(area(top_triangles(meshes)), 20, places=5)
        label = top_triangles(meshes, "|label", 7.017)
        self.assertTrue(label)
        self.assertFalse(any(covers(t, 4, 4) for t in label))

    def test_offset_origin_is_preserved(self):
        shifted = [[x-100,z+230] for x,z in L]
        triangles = top_triangles(exported(model(shifted)))
        self.assertAlmostEqual(area(triangles), 20, places=5)
        self.assertTrue(any(covers(t, -99, 235) for t in triangles))
        self.assertFalse(any(covers(t, -96, 234) for t in triangles))


if __name__ == "__main__":
    unittest.main(verbosity=2)
