"""Generation context/geometry regressions; no network or model-quality claim.

Controlled provider replies exercise the actual staged pipeline. The real
geometry compiler measures walls, and a cooperative planner demonstrates the
effect of carrying already accepted rectangles across calls and split retries.
"""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_api_errors as E
import acs_compiler as C
import acs_generation as G
import acs_plan_chunks as PC
import acs_understand as U
import acs_validate as V


def section_json(body, marker, default=None):
    if marker not in body:
        return default
    return json.JSONDecoder().raw_decode(body.split(marker, 1)[1].lstrip())[0]


def wall_meshes(room, industrial=False):
    builder = C.Builder()
    C.build_room(builder, copy.deepcopy(room), "F0", 0,
                 dict(wall_h=3, wall_t=0.15, industrial=industrial))
    return [part for part in builder.parts if part[5].startswith("WALL|")]


def admitted_room(**fields):
    room = dict(id="bed", rect=[0, 0, 4, 4], role="bedroom", **fields)
    rooms, issues = PC.validate_chunk(dict(zone_ids=["bed"], index=0),
                                      dict(rooms=[room]))
    assert not issues, issues
    return rooms[0]


def floor_plan():
    return dict(site=dict(w=20, d=12), floor_height=3.5, wall_h=3, wall_t=0.15,
                meta=dict(type="residential"), levels=[
                    dict(index=0, name="Ground", template="ground"),
                    dict(index=1, name="First", template="typical")], floors={
                    template: dict(rooms=[dict(id="bed", rect=[x, 0, 4, 4],
                        role="bedroom", walls="full", wall_h=2.8,
                        wall_color="#aabbcc", source="user", brief="bedroom")])
                    for template, x in (("ground", 0), ("typical", 8))})


class GenerationSpatialTests(unittest.TestCase):
    def setUp(self):
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()
        self.addCleanup(self.quiet.__exit__, None, None, None)

    def test_missing_wall_mode_does_not_erase_residential_walls(self):
        room = admitted_room()
        self.assertEqual(len(wall_meshes(room)), 4)
        self.assertNotIn("walls", room)  # omission retains compiler semantics

    def test_explicit_open_zones_stay_open(self):
        room = admitted_room(walls="none")
        self.assertEqual(wall_meshes(room), [])
        self.assertEqual(room["walls"], "none")

    def test_industrial_defaults_still_distinguish_offices_from_storage(self):
        room = admitted_room()
        room["role"] = "office"
        self.assertEqual(len(wall_meshes(room, industrial=True)), 4)
        room["role"] = "storage"
        self.assertEqual(wall_meshes(room, industrial=True), [])

    def test_plan_preserves_explicit_wall_height_in_real_mesh(self):
        walls = wall_meshes(admitted_room(walls="full", wall_h=1.1))
        self.assertEqual(len(walls), 4)
        for positions, *_ in walls:
            self.assertAlmostEqual(float(positions[:, 1].max()), 1.1, places=5)

    def test_invalid_wall_height_is_reported_and_not_forwarded(self):
        for height in (None, "bad", -1, 0, float("inf")):
            rooms, issues = PC.validate_chunk(dict(zone_ids=["bed"], index=0),
                dict(rooms=[dict(id="bed", rect=[0, 0, 4, 4], wall_h=height)]))
            self.assertNotIn("wall_h", rooms[0])
            self.assertEqual(issues[0]["code"], "PLAN_CHUNK_BAD_WALL_HEIGHT")

    def run_bounded(self, split=False, fail_first=False):
        outline = floor_plan()
        outline.pop("floors")
        outline["zones"] = [dict(id=f"{t}_{i}", template=t, role="bedroom")
                            for t in ("ground", "typical") for i in range(8)]
        contexts, asks, budgets = [], [], []

        def provider(body, **kw):
            if kw.get("stage") == PC.STAGE_OUTLINE:
                return json.dumps(outline)
            ask_section = body.split("المناطق المطلوب هندستها الآن", 1)[1].split("\n", 1)[1]
            ask = json.JSONDecoder().raw_decode(ask_section.lstrip())[0]
            context = section_json(body, "سياق التخطيط المشترك:\n", {})
            contexts.append(context)
            asks.append(ask)
            budgets.append(kw["max_tokens"])
            if len(contexts) == 1 and (split or fail_first):
                kw["telemetry"].update(stop_reason="max_tokens" if split else "end_turn")
                raise E.AcsApiError(E.ACS_UPSTREAM_TRUNCATED if split
                                    else E.ACS_UPSTREAM_INVALID_JSON, "controlled reply")
            template = context.get("target_template")
            occupied = [r for r in context.get("planned_rooms", [])
                        if r.get("template") == template]
            # This deliberate double can avoid prior rooms only if it receives
            # them. It is not evidence that a live model will obey the context.
            start_x = max((r["rect"][0] + r["rect"][2] for r in occupied), default=0)
            return json.dumps(dict(rooms=[dict(id=z["id"],
                rect=[start_x + i * 2, 0, 2, 4], role="bedroom", walls="full")
                for i, z in enumerate(ask)]))

        with patch.object(U, "call_llm", side_effect=provider), \
                patch.object(PC, "MAX_CHUNK_ZONES", 8 if split else 4), \
                patch.object(PC, "needs_pilot", return_value=False):
            building = U._plan_bounded("Synthetic two-floor building",
                                       btype="residential")
        return building, contexts, asks, budgets, outline

    def test_later_chunks_receive_accepted_geometry_and_complete_manifest(self):
        building, contexts, asks, budgets, outline = self.run_bounded()
        self.assertEqual(len(contexts), 4)
        for template, fdef in building["floors"].items():
            rooms = fdef["rooms"]
            self.assertEqual(len(rooms), 8)
            self.assertFalse(any(V._overlap(a["rect"], b["rect"])
                for i, a in enumerate(rooms) for b in rooms[i+1:]), template)
            self.assertEqual(rooms[0]["rect"][0], 0)  # floors may share XY
        self.assertEqual(contexts[0]["site"], outline["site"])
        self.assertEqual(contexts[0]["levels"], outline["levels"])
        self.assertEqual(len(contexts[0]["zones"]), 16)
        self.assertEqual(len(contexts[1]["planned_rooms"]), 4)
        self.assertEqual(len(contexts[2]["planned_rooms"]), 8)
        self.assertTrue(all(z["template"] == c["target_template"]
                            for c, ask in zip(contexts, asks) for z in ask))
        self.assertEqual(set(budgets), {G.stage_budget("plan")})

    def test_split_second_half_sees_first_half_accepted_geometry(self):
        building, contexts, _, _, _ = self.run_bounded(split=True)
        self.assertEqual(contexts[1]["planned_rooms"], [])
        self.assertEqual(len(contexts[2]["planned_rooms"]), 4)
        ground = building["floors"]["ground"]["rooms"]
        self.assertEqual([r["rect"][0] for r in ground], list(range(0, 16, 2)))
        self.assertTrue(any(i["code"] == "PLAN_CHUNK_SPLIT" for i in
                            building["meta"]["acs_stage_diagnostics"]))

    def test_failed_chunks_are_not_advertised_as_accepted_geometry(self):
        building, contexts, _, _, _ = self.run_bounded(fail_first=True)
        self.assertEqual(contexts[1]["planned_rooms"], [])
        unresolved = [r for f in building["floors"].values() for r in f["rooms"]
                      if r.get("acs_unresolved")]
        self.assertEqual(len(unresolved), 4)
        failed_ids = {r["id"] for r in unresolved}
        self.assertFalse(any(r["id"] in failed_ids for c in contexts
                             for r in c["planned_rooms"]))

    def run_detail(self, reply, plan=None):
        plan, contexts = plan or floor_plan(), []
        before = copy.deepcopy(plan)

        def provider(body, **kw):
            self.assertEqual(kw["stage"], "detail")
            context = section_json(body, "سياق الخطة (للاتّساق فقط):\n")
            rooms = section_json(body, "المناطق المطلوب تفصيلها الآن:\n")
            contexts.append(context)
            return json.dumps(dict(rooms=reply(context, rooms)))

        with patch.object(U, "_plan", return_value=copy.deepcopy(plan)), \
                patch.object(U, "call_llm", side_effect=provider):
            building = U.understand_deep("Two bedrooms", btype="residential",
                group_size=1, workers=1, strategy_plan=dict(estimated_zones=2))
        self.assertEqual(plan, before)
        return building, contexts

    def test_detail_context_disambiguates_same_id_on_different_floors(self):
        def reply(ctx, rooms):
            target = ctx.get("target_template")
            return [dict(r, points=[dict(type="light", x=2, z=2)],
                         furniture=[dict(name=target or "ambiguous", x=1, z=1,
                                         w=1, d=1, h=1, mat="furn")]) for r in rooms]
        building, contexts = self.run_detail(reply)
        self.assertEqual([c["target_template"] for c in contexts], ["ground", "typical"])
        for c in contexts:
            self.assertEqual({z["template"] for z in c["zones"]}, {"ground", "typical"})
            self.assertEqual(len(c["levels"]), 2)
        for template, floor in building["floors"].items():
            self.assertEqual(floor["rooms"][0]["furniture"][0]["name"], template)

    def test_partial_details_preserve_plan_geometry_and_metadata(self):
        building, _ = self.run_detail(lambda ctx, rs: [dict(id=r["id"],
            rect=r["rect"], points=[dict(type="light", x=2, z=2)]) for r in rs])
        for t, floor in building["floors"].items():
            room, planned = floor["rooms"][0], floor_plan()["floors"][t]["rooms"][0]
            for key, value in planned.items():
                if key != "brief":
                    self.assertEqual(room.get(key), value, key)
            self.assertNotIn("brief", room)
            self.assertEqual(len(room["points"]), 1)

    def test_detail_cannot_rewrite_planned_walls_height_or_role(self):
        building, _ = self.run_detail(lambda ctx, rs: [dict(r, rect=[1, 1, 2, 2],
            walls="none", role="storage", wall_h=9, points=[]) for r in rs])
        for t, floor in building["floors"].items():
            room, planned = floor["rooms"][0], floor_plan()["floors"][t]["rooms"][0]
            for key in ("rect", "walls", "role", "wall_h"):
                self.assertEqual(room[key], planned[key], key)
            self.assertEqual(len(wall_meshes(room)), 4)
        diagnostics = building["meta"]["acs_stage_diagnostics"]
        self.assertTrue(any(d["code"] == "STAGE_RECT_OVERRIDE_REJECTED" for d in diagnostics))
        self.assertEqual({d["field"] for d in diagnostics
                          if d["code"] == "STAGE_FIELD_OVERRIDE_REJECTED"},
                         {"walls", "role", "wall_h"})

    def test_detail_can_supply_properties_missing_from_plan(self):
        plan = floor_plan()
        for floor in plan["floors"].values():
            room = floor["rooms"][0]
            room["role"] = ""
            room.pop("walls")
            room.pop("wall_h")
        building, _ = self.run_detail(lambda ctx, rs: [dict(r, role="bedroom",
            walls="full", wall_h=2.8) for r in rs], plan=plan)
        for floor in building["floors"].values():
            room = floor["rooms"][0]
            self.assertEqual((room["role"], room["walls"], room["wall_h"]),
                             ("bedroom", "full", 2.8))


class ResidentialQualityCompanionGates(unittest.TestCase):
    """Keep the residential fix inside an already mandatory CI target."""

    def _run(self, cmd):
        import subprocess
        root = Path(__file__).resolve().parents[2]
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, (proc.stdout or "") + "\n" + (proc.stderr or ""))

    def test_residential_massing_contract_remains_green(self):
        self._run([sys.executable, "tests/remediation/test_residential_quality.py"])

    def test_residential_presentation_contract_remains_green(self):
        self._run(["node", "tests/remediation/test_residential_presentation.js"])

    def test_native_openai_provider_contract_remains_green(self):
        self._run([sys.executable, "tests/remediation/test_openai_provider.py"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
