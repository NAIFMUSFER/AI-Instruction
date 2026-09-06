"""C02b: door connectivity includes every physical room, even in strict mode."""
import copy
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_validate as V
import acs_arch as AR


def room(name, x, doors=None):
    return {"id": name, "rect": [x, 0, 4, 4], "walls": "full", "doors": doors or [],
            "points": [{"type": "light", "x": 2, "z": 2},
                       {"type": "smoke", "x": 2, "z": 2}]}


def model(rooms, strict=True):
    return {"site": {"w": 20, "d": 25}, "meta": {"strict": strict},
            "levels": [{"index": 0, "template": "g"}], "floors": {"g": {"rooms": rooms}}}


class RoomAccess(unittest.TestCase):
    def test_enclosed_room_without_door_is_not_hidden_by_strict(self):
        building = model([room("isolated", 0)])
        before = copy.deepcopy(building)
        issues, stats = V.validate_building(building)
        self.assertTrue(any("ROOM_UNREACHABLE" in issue and "isolated@0" in issue for issue in issues), issues)
        self.assertEqual(stats["access"]["status"], "COMPLETED")
        self.assertEqual(building, before)

    def test_neighbor_can_declare_the_shared_door(self):
        for strict in (True, False):
            building = model([room("entry", 0, [{"edge": "N", "offset": 2},
                {"edge": "E", "offset": 2}]), room("target", 4)], strict)
            self.assertEqual(V.validate_building(building)[0], [])

    def test_connected_pair_without_access_to_any_entry_is_unreachable(self):
        building = model([room("entry", 0, [{"edge": "N", "offset": 2}]),
            room("a", 5, [{"edge": "E", "offset": 2}]), room("b", 9)])
        issues, _ = V.validate_building(building)
        for name in ("a", "b"):
            self.assertTrue(any("ROOM_UNREACHABLE" in issue and ".%s@0" % name in issue
                                for issue in issues), issues)
        self.assertFalse(any("ROOM_UNREACHABLE" in issue and "entry@0" in issue for issue in issues))

    def test_window_is_not_an_access_edge(self):
        r = room("window_only", 0); r["windows"] = [{"edge": "N", "offset": 2}]
        self.assertTrue(any("ROOM_UNREACHABLE" in issue for issue in V.validate_building(model([r]))[0]))

    def test_explicit_open_areas_do_not_require_doors(self):
        rooms = [room("zone_a", 0), room("zone_b", 4)]
        for r in rooms:
            r["walls"] = "none"
        self.assertEqual(V.validate_building(model(rooms))[0], [])

    def test_nested_envelope_and_docks_are_not_falsely_declared_isolated(self):
        shell = room("envelope", 0); shell["rect"] = [0, 0, 12, 4]
        dock = room("dock_area", 0); dock.update(rect=[0, 0, 8, 4], walls="none",
            docks=[{"edge": "N", "offset": 2, "count": 1}])
        office = room("office", 8, [{"edge": "W", "offset": 2}])
        issues, stats = V.validate_building(model([shell, dock, office]))
        self.assertFalse(any("ROOM_UNREACHABLE" in issue for issue in issues), issues)
        self.assertIn(stats["access"]["status"], ("PARTIAL", "NOT_EVALUATED"))

    def test_unsupported_shape_and_compiler_failure_are_explicitly_unevaluated(self):
        r = room("polygon", 0); r["polygon"] = [[0, 0], [4, 0], [0, 4]]
        issues, stats = V.validate_building(model([r]))
        self.assertFalse(any("ROOM_UNREACHABLE" in issue for issue in issues))
        self.assertEqual(stats["access"]["status"], "NOT_EVALUATED")
        with patch.object(AR, "compile_architecture", side_effect=ValueError("private-input")):
            issues, stats = V.validate_building(model([room("entry", 0, [{"edge": "N", "offset": 2}])]))
        self.assertEqual(stats["access"]["status"], "NOT_EVALUATED")
        self.assertNotIn("private-input", repr(stats))

    def test_api_does_not_label_an_unevaluated_access_check_complete(self):
        import acs_understand_api as API
        import acs_cpu_pool as CPU
        building = model([room("entry", 0, [{"edge": "N", "offset": 2}])])
        async def run():
            async def dispatch(target, args):
                worker = CPU._worker(target, args, {})
                self.assertTrue(worker["ok"])
                return worker["value"]
            with patch.object(API, "_engineering_authority", AsyncMock(return_value=({"proposals": []}, building))), \
                 patch.object(CPU, "run", AsyncMock(side_effect=dispatch)), \
                 patch.object(AR, "compile_architecture", side_effect=ValueError("private-input")):
                return await API._understand_payload(building)
        result = asyncio.run(run())
        self.assertEqual(result["model_validation"]["status"], "PARTIAL")
        self.assertIn("access", result["model_validation"]["incomplete_scopes"])
        self.assertNotIn("private-input", repr(result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
