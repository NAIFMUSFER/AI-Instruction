# -*- coding: utf-8 -*-
"""Canonical roof level: model data, measured separately, approved and compiled.

Synthetic models only. No provider call. Not a structural or code check.
"""
import copy
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests', 'remediation'))

import acs_arch                                                    # noqa: E402
import acs_roof                                                    # noqa: E402
from acs_plan_bridge import existing_geometry_verifier              # noqa: E402
from acs_plan_lock_binding import PlanLockWorkspace                 # noqa: E402
from acs_plan_scorecard import measure_plan                         # noqa: E402
from tools.acs_plan_handoff import compile_approved_baseline, verify_compiled_artifact  # noqa: E402
from tools.generate_delivery_fixtures import fixtures               # noqa: E402


def room(rid, rect):
    return {"id": rid, "name": rid, "role": "living", "rect": rect,
            "walls": ["N", "S", "W", "E"], "doors": [], "windows": [], "points": []}


def model(rooms, **extra):
    m = {"meta": {"type": "residential"}, "site": {"w": 40, "d": 40}, "wall_h": 3,
         "wall_t": 0.2, "floor_height": 3.2,
         "levels": [{"index": 0, "template": "g"}], "floors": {"g": {"rooms": rooms}}}
    m.update(extra)
    return m


class RoofLevel(unittest.TestCase):
    def test_single_room_gets_a_full_parapet_and_the_input_is_untouched(self):
        src = model([room("a", [2, 2, 10, 6])])
        before = copy.deepcopy(src)
        out, report = acs_roof.add_flat_roof_level(src)
        self.assertEqual(src, before)
        level = out["levels"][-1]
        self.assertEqual((level["kind"], level["auto"], level["index"]), ("roof", True, 1))
        self.assertAlmostEqual(level["elevation"], 3.2)
        deck = out["floors"][level["template"]]["rooms"][0]
        self.assertEqual(deck["id"], "roof_a")
        self.assertEqual(sorted(deck["walls"]), ["E", "N", "S", "W"])
        self.assertEqual(deck["wall_h"], 0.9)
        self.assertEqual((deck["doors"], deck["windows"]), ([], []))
        self.assertAlmostEqual(report["parapet_length_m"], 32.0)
        self.assertAlmostEqual(report["deck_area_m2"], 60.0)
        self.assertEqual(report["parapet_gaps"], [])
        self.assertFalse(report["occupied_floor"])

    def test_shared_edges_carry_no_parapet(self):
        out, report = acs_roof.add_flat_roof_level(
            model([room("a", [0, 0, 6, 5]), room("b", [6, 0, 4, 5])]))
        decks = {r["id"]: r for r in out["floors"]["roof"]["rooms"]}
        self.assertNotIn("E", decks["roof_a"]["walls"])
        self.assertNotIn("W", decks["roof_b"]["walls"])
        self.assertAlmostEqual(report["parapet_length_m"], 2 * (10 + 5))

    def test_l_shape_keeps_its_recess_open_and_reports_the_partial_edge(self):
        # 12 m² L: a 4x2 bar with a 2x2 leg under its west half.
        out, report = acs_roof.add_flat_roof_level(
            model([room("bar", [0, 0, 4, 2]), room("leg", [0, 2, 2, 2])]))
        self.assertAlmostEqual(report["deck_area_m2"], 12.0)
        decks = {r["id"]: r for r in out["floors"]["roof"]["rooms"]}
        self.assertNotIn("S", decks["roof_bar"]["walls"])   # half shared: never guessed
        self.assertNotIn("N", decks["roof_leg"]["walls"])   # fully shared
        self.assertEqual(report["parapet_gaps"],
                         [{"room_id": "bar", "edge": "S", "open_length_m": 2.0}])

    def test_elevation_follows_the_storey_convention_or_sits_on_the_walls(self):
        tall = model([room("a", [0, 0, 5, 5])], wall_h=8, floor_height=3.2)
        out, _ = acs_roof.add_flat_roof_level(tall)
        self.assertAlmostEqual(out["levels"][-1]["elevation"], 8.15)
        explicit = model([room("a", [0, 0, 5, 5])])
        explicit["levels"] = [{"index": 0, "template": "g", "elevation": 0},
                              {"index": 1, "template": "g", "elevation": 4.2}]
        out, report = acs_roof.add_flat_roof_level(explicit)
        self.assertAlmostEqual(out["levels"][-1]["elevation"], 7.4)
        self.assertEqual(report["level_index"], 2)

    def test_refusals_are_explicit(self):
        out, _ = acs_roof.add_flat_roof_level(model([room("a", [0, 0, 5, 5])]))
        for bad, code in ((out, "ROOF_LEVEL_EXISTS"),
                          (model([]), "ROOF_TOP_LEVEL_HAS_NO_ROOMS"),
                          ({"levels": [], "floors": {}}, "ROOF_NO_OCCUPIED_LEVEL")):
            with self.assertRaises(ValueError) as caught:
                acs_roof.add_flat_roof_level(bad)
            self.assertEqual(str(caught.exception), code)
        with self.assertRaises(ValueError):
            acs_roof.add_flat_roof_level(model([room("a", [0, 0, 5, 5])]), parapet_h=5)

    def test_zero_parapet_is_an_open_deck(self):
        out, report = acs_roof.add_flat_roof_level(model([room("a", [0, 0, 5, 5])]), parapet_h=0)
        deck = out["floors"]["roof"]["rooms"][0]
        self.assertEqual(deck["walls"], "none")
        self.assertNotIn("wall_h", deck)
        self.assertEqual(report["parapet_length_m"], 0.0)

    def test_architecture_reports_a_default_unoccupied_roof(self):
        out, _ = acs_roof.add_flat_roof_level(model([room("a", [0, 0, 5, 5])]))
        roofs = acs_arch.compile_architecture(out, "bld_0", None, 0)["roofs"]
        self.assertEqual(len(roofs), 1)
        self.assertEqual((roofs[0]["source"], roofs[0]["occupied_floor"], roofs[0]["form"]),
                         ("system_default", False, "flat"))

    def test_review_measures_the_roof_separately_and_approves_the_compiled_artifact(self):
        for name, base in fixtures().items():
            with self.subTest(fixture=name):
                area = sum(r["rect"][2] * r["rect"][3] for l in base["levels"]
                           for r in base["floors"][l["template"]]["rooms"])
                roofed, report = acs_roof.add_flat_roof_level(base)
                # Programme measurements are identical with and without the roof.
                plain, with_roof = measure_plan(base)["metrics"], measure_plan(roofed)["metrics"]
                for key in ("level_count", "space_rect_area_m2"):
                    self.assertEqual(plain[key], with_roof[key], key)
                requirement = [{"id": "area", "metric": "building_target_area_m2", "expected": area,
                                "source": "requested", "evidence": str(area)}]
                brief = "Synthetic total canonical room area %s square metres." % area
                reviews = {}
                for label, candidate in (("plain", base), ("roofed", roofed)):
                    ws = PlanLockWorkspace(existing_geometry_verifier)
                    rev = ws.propose(candidate, brief=brief, requirements=requirement,
                                     expected_head=None, note="synthetic roof regression")
                    reviews[label] = (ws, rev, ws.review(rev.id))
                plain_review, roof_review = reviews["plain"][2], reviews["roofed"][2]
                self.assertTrue(roof_review["can_approve"], roof_review["issues"])
                self.assertEqual(roof_review["scopes"], plain_review["scopes"])
                self.assertEqual(roof_review["metrics"]["level_count"], len(base["levels"]))
                self.assertEqual(roof_review["metrics"]["space_rect_area_m2"], area)
                self.assertEqual(roof_review["metrics"]["roof_level_count"], 1)
                self.assertAlmostEqual(roof_review["metrics"]["roof_deck_rect_area_m2"],
                                       report["deck_area_m2"])
                self.assertEqual(plain_review["metrics"]["roof_level_count"], 0)
                ws, rev, _ = reviews["roofed"]
                ws.approve(rev.id, expected_head=rev.id, actor_label="synthetic-roof-test",
                           confirmed=True, acknowledge_concept_only=True)
                with tempfile.TemporaryDirectory() as folder:
                    target = os.path.join(folder, name + ".gltf")
                    compile_approved_baseline(ws, rev.id, target)
                    self.assertTrue(verify_compiled_artifact(target)["ok"])
                    with open(target, encoding="utf-8") as handle:
                        nodes = [n.get("name", "") for n in json.load(handle)["nodes"]]
                key = "F%d" % report["level_index"]
                roof_nodes = [n for n in nodes if n.split("|")[1:2] == [key]]
                self.assertTrue(any(n.startswith("FLOOR|%s|slab|" % key) for n in roof_nodes))
                walls = [n for n in roof_nodes if n.startswith("WALL|")]
                self.assertTrue(walls and all(n.split("|")[2].startswith("roof_") for n in walls))
                self.assertFalse([n for n in roof_nodes if n.split("|")[0] in ("DOOR", "WINDOW")])

    # ---- generation and editing journey -------------------------------------
    def test_default_roof_is_added_once_and_disclosed_as_a_system_default(self):
        src = model([room("a", [0, 0, 6, 5])])
        out, report, reason = acs_roof.with_default_roof(src)
        self.assertIsNone(reason)
        self.assertEqual(out["meta"]["acs_roof"],
                         {"schema": "acs.roof/1", "source": "system_default", "form": "flat",
                          "parapet_height_m": 0.9, "occupied_floor": False})
        again, report2, reason2 = acs_roof.with_default_roof(out)
        self.assertIs(again, out)
        self.assertEqual((report2, reason2), (None, "ROOF_LEVEL_EXISTS"))
        self.assertEqual(acs_roof.with_default_roof(model([]))[2], "ROOF_TOP_LEVEL_HAS_NO_ROOMS")

    def test_an_edit_keeps_the_automatic_roof_over_the_top_storey(self):
        before, _, _ = acs_roof.with_default_roof(model([room("a", [0, 0, 6, 5])]))
        edited = copy.deepcopy(before)
        edited["floors"]["g"]["rooms"][0]["rect"] = [0, 0, 9, 5]
        after = acs_roof.carry_auto_roof(before, edited)
        self.assertEqual(after["floors"]["roof"]["rooms"][0]["rect"], [0, 0, 9, 5])
        # Everything outside ``floors`` is unchanged, so room locks stay valid.
        outside = lambda m: {k: v for k, v in m.items() if k != "floors"}
        self.assertEqual(outside(after), outside(before))
        # A provider reply that silently dropped the roof gets it back.
        dropped = copy.deepcopy(edited)
        dropped["levels"] = dropped["levels"][:1]
        dropped["floors"].pop("roof")
        self.assertEqual(acs_roof.carry_auto_roof(before, dropped), after)

    def test_an_edit_never_re_adds_a_removed_roof_or_touches_an_authored_one(self):
        plain = model([room("a", [0, 0, 6, 5])])
        self.assertIs(acs_roof.carry_auto_roof(plain, plain), plain)
        authored, _ = acs_roof.add_flat_roof_level(plain)
        authored["levels"][-1].pop("auto")
        edited = copy.deepcopy(authored)
        edited["floors"]["g"]["rooms"][0]["rect"] = [0, 0, 9, 5]
        self.assertIs(acs_roof.carry_auto_roof(authored, edited), edited)
        self.assertTrue(acs_roof.is_auto_roof_template(acs_roof.with_default_roof(plain)[0], "roof"))
        self.assertFalse(acs_roof.is_auto_roof_template(authored, "roof"))

    def test_a_locked_room_does_not_block_an_edit_that_carries_the_roof(self):
        villa = fixtures()["villa"]
        roofed, _, _ = acs_roof.with_default_roof(villa)
        ws = PlanLockWorkspace(existing_geometry_verifier)
        first = ws.propose(roofed, brief="Synthetic lock regression.", requirements=[],
                           expected_head=None, note="synthetic")
        locked = ws.set_room_lock(("home", "living"), locked=True, expected_head=first.id)
        candidate = locked.model
        stairs = next(r for r in candidate["floors"]["home"]["rooms"] if r["id"] == "stairs")
        stairs["rect"] = [8, 0, 5, 8]
        candidate = acs_roof.carry_auto_roof(locked.model, candidate)
        second = ws.propose(candidate, brief="Synthetic lock regression.", requirements=[],
                            expected_head=locked.id, note="synthetic edit")
        deck = next(r for r in second.model["floors"]["roof"]["rooms"] if r["id"] == "roof_stairs")
        self.assertEqual(deck["rect"], [8, 0, 5, 8])


if __name__ == "__main__":
    unittest.main(verbosity=1)
