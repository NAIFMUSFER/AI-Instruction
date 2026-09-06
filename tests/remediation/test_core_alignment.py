"""C02a: stated core identity must retain its world footprint across levels."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_validate as V


def building(kind="stairs"):
    model = {"site": {"w": 20, "d": 25}, "floor_height": 3.2,
        "meta": {"strict": True}, "levels": [], "floors": {}}
    for index in range(3):
        template = "f%d" % index
        model["levels"].append({"index": index, "template": template})
        model["floors"][template] = {"rooms": [{"id": "hall", "rect": [0, 0, 6, 6],
            "doors": [{"edge": "N", "offset": 3}], "objects": [
                {"id": "core-A", "kind": kind, "x": 2, "z": 3, "w": 2, "d": 2}]}]}
    return model


class CoreAlignment(unittest.TestCase):
    def test_shifted_stair_and_elevator_are_each_detected(self):
        for kind in ("stairs", "elevator"):
            with self.subTest(kind=kind):
                model = building(kind)
                model["floors"]["f1"]["rooms"][0]["objects"][0]["x"] = 3
                before = copy.deepcopy(model)
                issues, _ = V.validate_building(model)
                self.assertTrue(any("CORE_VERTICAL_MISALIGNMENT" in issue
                    and "core-A" in issue and "levels/1" in issue for issue in issues), issues)
                self.assertEqual(model, before)

    def test_changed_stated_footprint_is_detected(self):
        model = building("elevator")
        model["floors"]["f1"]["rooms"][0]["objects"][0]["w"] = 3
        self.assertTrue(any("CORE_FOOTPRINT_MISMATCH" in issue
                            for issue in V.validate_building(model)[0]))

    def test_coordinates_are_compared_in_building_not_room_space(self):
        model = building()
        room = model["floors"]["f1"]["rooms"][0]
        room["rect"][0] = 1
        room["objects"][0]["x"] = 1  # same building X=2
        self.assertEqual(V.validate_building(model)[0], [])

    def test_aligned_control_has_no_false_alerts_and_reports_scope(self):
        for kind in ("stairs", "elevator"):
            model = building(kind)
            issues, stats = V.validate_building(model)
            self.assertEqual(issues, [])
            self.assertEqual(stats["vertical_alignment"]["status"], "COMPLETED")
            self.assertEqual(stats["vertical_alignment"]["checked_groups"], 1)

    def test_unknown_core_identity_is_disclosed_without_inventing_a_match(self):
        model = building()
        for floor in model["floors"].values():
            floor["rooms"][0]["objects"][0].pop("id")
        issues, stats = V.validate_building(model)
        self.assertEqual(issues, [])
        self.assertEqual(stats["vertical_alignment"]["status"], "NOT_EVALUATED")
        self.assertEqual(len(stats["vertical_alignment"]["unresolved"]), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
