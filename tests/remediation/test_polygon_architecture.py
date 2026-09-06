"""C09c: canonical architecture must retain actual boundaries and topology."""
import copy
import math
import json
from pathlib import Path
import unittest
from test_polygon_gltf import model, L
import acs_arch as A


def adjacent_triangles():
    b = model([[0,0],[6,0],[0,6]],
              doors=[{"edge_index":1,"offset":math.sqrt(18),"width":1,"height":2.1}])
    other = model([[6,0],[6,6],[0,6]])["floors"]["plan"]["rooms"][0]
    other["id"] = "other"
    b["floors"]["plan"]["rooms"].append(other)
    return b


class PolygonArchitecture(unittest.TestCase):
    def test_concave_boundary_walls_area_and_slab(self):
        b=model(); before=copy.deepcopy(b); arch=A.compile_architecture(b)
        self.assertEqual(arch["spaces"][0]["area_m2"],20)
        self.assertEqual(arch["spaces"][0]["boundary_basis"],"polygon_edges")
        self.assertEqual(arch["spaces"][0]["polygon"],L)
        self.assertEqual(len(arch["walls"]),6)
        self.assertAlmostEqual(sum(w["length_m"] for w in arch["walls"]),24)
        self.assertEqual(arch["slabs"][0]["outline_basis"],"polygon_union")
        self.assertEqual(arch["slabs"][0]["area_m2"],20)
        self.assertFalse(any(i["code"]=="SPACE_SHAPE_UNSUPPORTED" for i in arch["issues"]))
        self.assertEqual(b,before)

    def test_diagonal_shared_wall_door_and_no_false_overlap(self):
        arch=A.compile_architecture(adjacent_triangles())
        shared=[w for w in arch["walls"] if w["shared"]]
        self.assertEqual(len(shared),1)
        self.assertAlmostEqual(shared[0]["length_m"],math.sqrt(72),places=5)
        self.assertEqual(len(arch["walls"]),5)
        door=arch["openings"][0]
        self.assertEqual(door["host_status"],"resolved")
        self.assertEqual(door["host_wall_id"],shared[0]["id"])
        self.assertEqual(A.opening_anchor(arch,door["id"]),[3,3])
        self.assertEqual(len(A.door_connects_confirmed(arch,door["id"])["spaces"]),2)
        self.assertFalse(any(i["code"] in ("SPACE_OVERLAP","SPACE_CONTAINED") for i in arch["issues"]))

    def test_actual_overlap_area(self):
        b=model([[0,0],[6,0],[0,6]])
        other=model([[0,2],[6,2],[6,8]])["floors"]["plan"]["rooms"][0];other["id"]="other"
        b["floors"]["plan"]["rooms"].append(other)
        arch=A.compile_architecture(b)
        overlaps=[i for i in arch["issues"] if i["code"]=="SPACE_OVERLAP"]
        self.assertEqual(len(overlaps),1)
        self.assertAlmostEqual(overlaps[0]["overlap_m2"],4,places=5)
        self.assertAlmostEqual(arch["slabs"][0]["area_m2"],32,places=5)

    def test_partial_shared_wall_mixed_rectangle_and_polygon(self):
        b=model();b["floors"]["plan"]["rooms"].append({"id":"rectangular","rect":[6,0,3,1]})
        arch=A.compile_architecture(b)
        shared=[w for w in arch["walls"] if w["shared"]]
        self.assertEqual(len(shared),1)
        self.assertEqual(shared[0]["length_m"],1)
        self.assertEqual(shared[0]["exposure"],"interior")

    def test_void_updates_canonical_slab_area(self):
        b=model(objects=[{"kind":"stairs","core_id":"A","x":1,"z":3,"w":1,"d":1}])
        b["levels"].append({"index":1,"template":"plan","elevation":10.2})
        arch=A.compile_architecture(b)
        self.assertEqual([s["area_m2"] for s in arch["slabs"]],[20,19])
        self.assertEqual(len(arch["voids"]),1)

    def test_polygon_does_not_promote_uncertain_courtyard_exposure(self):
        scenarios=json.loads((Path(__file__).parents[1]/"phase2/fixtures/arch_scen.json").read_text())
        b=scenarios["models"]["court"]
        room=b["floors"]["g"]["rooms"][0]
        x,z,w,d=room["rect"]
        room["polygon"]=[[x,z],[x+w,z],[x+w,z+d],[x,z+d]]
        arch=A.compile_architecture(b)
        uncertain=[w for w in arch["walls"] if w["exposure"]=="unresolved"]
        self.assertEqual(len(uncertain),4)
        self.assertTrue(all(w["exposure_basis"]=="opposite_side_is_void_inside_the_footprint" for w in uncertain))


if __name__=="__main__":unittest.main(verbosity=2)
