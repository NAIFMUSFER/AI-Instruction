import copy
import unittest

from acs_plan_review import PlanError
from acs_plan_semantic_diff import diff_models


def residential():
    return {
        "site": {"w": 20.0, "d": 25.0},
        "floor_height": 3.2,
        "levels": [{"name": "G", "template": "ground"}],
        "floors": {
            "ground": {
                "rooms": [
                    {"id": "majlis", "name": "Majlis", "rect": {"x": 0.0, "z": 0.0, "w": 5.0, "d": 4.0}},
                    {"id": "elevator", "name": "Elevator", "rect": {"x": 5.5, "z": 0.0, "w": 2.0, "d": 2.0}},
                ]
            }
        },
    }


def warehouse():
    return {
        "site": {"w": 80.0, "d": 100.0},
        "levels": [{"name": "G", "template": "warehouse"}],
        "floors": {
            "warehouse": {
                "rooms": [
                    {
                        "id": "staging",
                        "role": "staging",
                        "rect": {"x": 0.0, "z": 0.0, "w": 20.0, "d": 20.0},
                        "racks": [
                            {"id": "rack-a", "x": 2.0, "z": 2.0, "w": 1.2, "d": 8.0, "levels": 4}
                        ],
                        "docks": [
                            {"id": "dock-1", "edge": "south", "x": 3.0, "z": 0.0, "w": 3.0, "d": 1.0}
                        ],
                        "lanes": [
                            {"id": "aisle-a", "kind": "forklift", "dir": "z", "x": 6.0, "z": 1.0, "w": 3.0, "d": 15.0}
                        ],
                    },
                    {"id": "storage", "role": "storage", "rect": {"x": 20.0, "z": 0.0, "w": 40.0, "d": 40.0}},
                ]
            }
        },
    }


class SemanticDiffTests(unittest.TestCase):
    def test_residential_room_geometry_change_is_explicit(self):
        before = residential()
        after = copy.deepcopy(before)
        after["floors"]["ground"]["rooms"][0]["rect"]["w"] = 6.0
        result = diff_models(before, after)
        self.assertEqual(result["schema"], "acs.plan-semantic-diff/1.0")
        self.assertEqual(result["change_count"], 1)
        change = result["changes"][0]
        self.assertEqual(change["kind"], "room")
        self.assertEqual(change["template"], "ground")
        self.assertEqual(change["room_id"], "majlis")
        self.assertEqual(change["change"], "modified")
        self.assertEqual(change["changed_fields"], ["rect"])
        self.assertFalse(result["claims_best_option"])
        self.assertFalse(result["claims_regulatory_compliance"])

    def test_warehouse_staging_change_does_not_invent_rack_or_dock_changes(self):
        before = warehouse()
        after = copy.deepcopy(before)
        after["floors"]["warehouse"]["rooms"][0]["rect"]["d"] = 24.0
        result = diff_models(before, after)
        self.assertEqual(result["change_count"], 1)
        change = result["changes"][0]
        self.assertEqual((change["kind"], change["room_id"]), ("room", "staging"))
        self.assertNotIn("racks", change["changed_fields"])
        self.assertNotIn("docks", change["changed_fields"])
        self.assertNotIn("lanes", change["changed_fields"])

    def test_nested_warehouse_element_change_uses_stable_identity(self):
        before = warehouse()
        after = copy.deepcopy(before)
        after["floors"]["warehouse"]["rooms"][0]["racks"][0]["w"] = 1.4
        result = diff_models(before, after)
        self.assertEqual(result["change_count"], 1)
        change = result["changes"][0]
        self.assertEqual(change["kind"], "element")
        self.assertEqual(change["collection"], "racks")
        self.assertEqual(change["element_id"], "rack-a")
        self.assertEqual(change["changed_fields"], ["w"])

    def test_array_reorder_is_not_a_semantic_change(self):
        before = warehouse()
        after = copy.deepcopy(before)
        after["floors"]["warehouse"]["rooms"].reverse()
        result = diff_models(before, after)
        self.assertEqual(result["change_count"], 0)
        self.assertEqual(result["changes"], [])

    def test_added_and_removed_stable_rooms_are_reported(self):
        before = residential()
        after = copy.deepcopy(before)
        after["floors"]["ground"]["rooms"] = [after["floors"]["ground"]["rooms"][0]]
        after["floors"]["ground"]["rooms"].append(
            {"id": "dining", "rect": {"x": 6.0, "z": 2.0, "w": 4.0, "d": 4.0}}
        )
        result = diff_models(before, after)
        summary = {(row["kind"], row.get("room_id"), row["change"]) for row in result["changes"]}
        self.assertIn(("room", "elevator", "removed"), summary)
        self.assertIn(("room", "dining", "added"), summary)

    def test_duplicate_room_identity_fails_closed(self):
        before = residential()
        after = copy.deepcopy(before)
        after["floors"]["ground"]["rooms"].append(copy.deepcopy(after["floors"]["ground"]["rooms"][0]))
        with self.assertRaises(PlanError) as ctx:
            diff_models(before, after)
        self.assertEqual(ctx.exception.code, "INVALID_DIFF_IDENTITY")

    def test_duplicate_nested_element_identity_fails_closed(self):
        before = warehouse()
        after = copy.deepcopy(before)
        after["floors"]["warehouse"]["rooms"][0]["racks"].append(
            copy.deepcopy(after["floors"]["warehouse"]["rooms"][0]["racks"][0])
        )
        with self.assertRaises(PlanError) as ctx:
            diff_models(before, after)
        self.assertEqual(ctx.exception.code, "INVALID_DIFF_IDENTITY")


if __name__ == "__main__":
    unittest.main()
