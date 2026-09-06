"""C12: a forklift cannot create a lift shaft, slab void or vertical path."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_arch as AR
import acs_relations as REL
import acs_distance as DIST


def building(kind):
    return {"site": {"w": 20, "d": 25}, "floor_height": 3.2,
        "levels": [{"index": i, "template": "g"} for i in (0, 1)],
        "floors": {"g": {"rooms": [{"id": "store", "rect": [0, 0, 10, 10],
            "walls": "none", "objects": [{"kind": kind, "x": 3, "z": 3,
                                           "w": 1.2, "d": 2.2}]}]}}}


class CoreClassification(unittest.TestCase):
    def test_forklift_is_not_vertical_transport_in_any_consumer(self):
        for name in ("forklift", "electric forklift", "forklift_A"):
            with self.subTest(name=name):
                obj = {"kind": name}
                self.assertIsNone(AR._core_kind(obj))
                self.assertIsNone(REL._kind_of(obj))
                self.assertIsNone(DIST._find_object({"objects": [obj]}, "elevator"))

    def test_two_storeys_with_forklifts_have_no_false_void_or_vertical_edge(self):
        model = building("forklift"); before = copy.deepcopy(model)
        arch = AR.compile_architecture(model)
        self.assertEqual(arch["cores"], [])
        self.assertEqual(arch["voids"], [])
        self.assertEqual([edge for edge in REL.build_relationships(model)
                          if edge["type"] == "VERTICAL_CONNECTS"], [])
        self.assertEqual(model, before)

    def test_real_stairs_and_lifts_keep_their_voids_and_connections(self):
        for kind in ("stairs", "staircase", "درج", "elevator", "lift", "service_lift", "مصعد"):
            with self.subTest(kind=kind):
                model = building(kind)
                self.assertEqual(len(AR.compile_architecture(model)["voids"]), 1)
                self.assertEqual(len([edge for edge in REL.build_relationships(model)
                                     if edge["type"] == "VERTICAL_CONNECTS"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
