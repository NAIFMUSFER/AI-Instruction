#!/usr/bin/env python3
"""Drafting-layer regressions for ACS plan drawings (stdlib only; runs with python -S).

Synthetic canonical models only. The drafting layer may draw only what the
canonical model states (walls at the model thickness, doors, windows, docks,
explicit stairs) plus disclosed conventions (door swing side/hand). These tests
pin the professional-drawing rules (merged walls, cut openings, swing choice,
dimension chains that close, net areas to wall faces, standard scale and paper,
NCS layer names) and that the provenance-bound projection contract is untouched.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_drafting_standards as STD
import acs_plan_drafting as D
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_projection import project, render_svg, to_svg
from acs_plan_review import PlanWorkspace, canonical

BRIEF = "شقة تجريبية بعرض 12 متر"
SVG = "{http://www.w3.org/2000/svg}"


def program():
    start = BRIEF.index("12")
    return [{"id": "width", "metric": "site_width_m", "expected": 12.0, "source": "requested",
             "evidence": "12", "source_span": {"start": start, "end": start + 2}}]


def verified(_model):
    return {"scopes": {"topology": "PASS", "vertical_circulation": "PASS"}, "issues": []}


def door(i, edge, offset, width=0.9, **extra):
    return dict({"id": i, "edge": edge, "offset": offset, "width": width, "height": 2.1, "material": "wood"}, **extra)


def home():
    """Living + bedroom side by side over a corridor; centre-line rectangles, 0.2 m walls."""
    return {
        "meta": {"type": "residential", "name": "drafting-home"},
        "site": {"w": 12.0, "d": 10.0}, "wall_h": 3.0, "wall_t": 0.2, "floor_height": 3.2,
        "levels": [{"index": 0, "template": "g"}],
        "floors": {"g": {"rooms": [
            {"id": "living", "name": "صالة", "role": "living", "rect": [0.1, 0.1, 6.0, 5.0],
             "doors": [door("living_bed", "E", 2.5), door("living_hall", "S", 1.5, 1.6)],
             "windows": [{"id": "living_win", "edge": "N", "offset": 3.0, "width": 2.0, "sill": 0.9, "height": 1.5}]},
            {"id": "bed", "name": "غرفة نوم", "role": "bedroom", "rect": [6.1, 0.1, 4.0, 5.0],
             "doors": [door("bed_living", "W", 2.5), door("bed_hall", "S", 3.0)], "windows": []},
            {"id": "hall", "name": "ممر", "role": "corridor", "rect": [0.1, 5.1, 10.0, 1.5],
             "doors": [door("hall_bed", "N", 9.0), door("hall_entry", "W", 0.75, 1.0)], "windows": []},
            {"id": "porch", "name": "رواق", "role": "porch", "walls": [], "rect": [0.1, 6.6, 3.0, 1.4],
             "doors": [], "windows": []},
        ]}},
    }


def stair_home():
    """Two storeys with an explicit U stair (the same contract the planner authors)."""
    stair = {"id": "st_0_1", "kind": "stairs", "form": "u_return", "x": 1.2, "z": 2.0, "y": 0, "w": 1.9,
             "d": 3.8, "h": 3.4, "rot": 0, "count": 1, "pitch": 1, "dir": "x",
             "stair": {"schema": "acs.stair/1", "source_level_index": 0, "target_level_index": 1,
                       "source_elevation_m": 0, "target_elevation_m": 3.4, "flight_width_m": 0.9,
                       "gap_m": 0.1, "tread_m": 0.25, "risers_per_flight": 9, "entry_landing_m": 0.9,
                       "mid_landing_m": 0.9, "landing_thickness_m": 0.15}}

    def rooms(stairs):
        return [
            {"id": "hall", "name": "ممر", "role": "corridor", "rect": [0.1, 0.1, 6.0, 1.5],
             "doors": [door("hall_core", "S", 1.2)], "windows": []},
            {"id": "core", "name": "الدرج", "role": "stairs", "core_id": "c1", "rect": [0.1, 1.6, 2.4, 4.0],
             "doors": [door("core_hall", "N", 1.2)], "windows": [], "objects": stairs},
            {"id": "living", "name": "صالة", "role": "living", "rect": [2.5, 1.6, 3.6, 4.0],
             "doors": [door("living_hall", "N", 1.8)], "windows": []},
        ]
    return {"meta": {"type": "residential"}, "site": {"w": 12.0, "d": 6.0}, "wall_h": 3.2, "wall_t": 0.2,
            "floor_height": 3.4,
            "levels": [{"index": 0, "template": "g", "elevation": 0}, {"index": 1, "template": "f", "elevation": 3.4}],
            "floors": {"g": {"rooms": rooms([stair])}, "f": {"rooms": rooms([])}}}


def warehouse():
    return {"meta": {"type": "warehouse", "name": "drafting-warehouse"}, "site": {"w": 30.0, "d": 20.0},
            "wall_h": 7.5, "wall_t": 0.2, "floor_height": 8.0,
            "levels": [{"index": 0, "template": "g"}],
            "floors": {"g": {"rooms": [
                {"id": "store", "name": "Storage", "role": "storage", "rect": [0.0, 0.0, 18.0, 16.0],
                 "walls": ["N", "S", "W"], "doors": [], "windows": [], "racks": [], "lanes": [], "stations": [],
                 "docks": []},
                {"id": "ship", "name": "Shipping", "role": "outbound", "rect": [18.0, 0.0, 6.0, 16.0],
                 "walls": ["N", "S", "E"], "doors": [], "windows": [], "racks": [], "lanes": [], "stations": [],
                 "docks": [{"id": "dock_e", "edge": "E", "offset": 4.0, "width": 3.6, "height": 4.2,
                            "count": 2, "pitch": 6.0}]},
            ]}}}


def draft_revision(model):
    ws = PlanWorkspace()
    return ws.propose(copy.deepcopy(model), brief=BRIEF, requirements=program(), expected_head=None,
                      note="drafting fixture")


def drafting(model, level=0):
    rev = draft_revision(model)
    p = project(rev, level)
    return rev, p, D.level_drafting(rev.model, level, p["primitives"], p["source_map"])


def inside(loops, x, z):
    """Even-odd point test over all outline loops (holes included)."""
    hit = False
    for loop in loops:
        for (x1, z1), (x2, z2) in zip(loop, loop[1:] + loop[:1]):
            if (z1 > z) != (z2 > z) and x < x1 + (z - z1) * (x2 - x1) / (z2 - z1):
                hit = not hit
    return hit


class WallTests(unittest.TestCase):
    def test_walls_use_canonical_thickness_and_outer_faces(self):
        _, _, d = drafting(home())
        self.assertEqual(d["wall_thickness_m"], 0.2)
        # Room rectangles are wall centre lines, so the outer faces sit 0.1 m outside them.
        x0, z0, x1, z1 = d["bounds"]
        self.assertAlmostEqual(x0, 0.0)
        self.assertAlmostEqual(z0, 0.0)
        self.assertAlmostEqual(x1, 10.2)
        self.assertAlmostEqual(z1, 8.0)  # the open porch reaches further south than the walls

    def test_shared_wall_is_drawn_once_and_corners_close(self):
        _, _, d = drafting(home())
        loops = d["walls"]["cut"]
        self.assertTrue(inside(loops, 6.1, 1.0), "shared living/bedroom wall")
        self.assertTrue(inside(loops, 6.05, 1.0) and inside(loops, 6.15, 1.0))
        self.assertTrue(inside(loops, 0.03, 0.03), "outer north-west corner is filled")
        self.assertTrue(inside(loops, 10.17, 6.67), "outer south-east corner is filled")
        self.assertFalse(inside(loops, 3.0, 3.0), "room interior is not poche")
        # No double outline: the shared wall's centre line is never an outline edge.
        for loop in loops:
            for (xa, za), (xb, zb) in zip(loop, loop[1:] + loop[:1]):
                self.assertFalse(abs(xa - 6.1) < 1e-9 and abs(xb - 6.1) < 1e-9 and 0.2 < min(za, zb) < 4.0)

    def test_openings_cut_the_wall(self):
        _, _, d = drafting(home())
        loops = d["walls"]["cut"]
        self.assertFalse(inside(loops, 6.1, 2.6), "door through the shared wall")
        self.assertFalse(inside(loops, 3.1, 0.1), "window in the north wall")
        self.assertTrue(inside(loops, 1.0, 0.1), "north wall beside the window")

    def test_low_walls_are_drawn_uncut(self):
        model = home()
        model["floors"]["g"]["rooms"][3]["walls"] = ["W"]
        model["floors"]["g"]["rooms"][3]["wall_h"] = 0.9
        _, _, d = drafting(model)
        self.assertTrue(d["walls"]["low"], "a parapet below the 1.2 m cut plane is an outline")
        self.assertFalse(inside(d["walls"]["cut"], 0.1, 7.5))
        self.assertTrue(inside(d["walls"]["low"], 0.1, 7.5))


class OpeningTests(unittest.TestCase):
    def test_paired_door_is_one_symbol_swinging_into_the_private_room(self):
        _, _, d = drafting(home())
        shared = [o for o in d["doors"] if o["axis"] == "z" and abs(o["fixed"] - 6.1) < 1e-9]
        self.assertEqual(len(shared), 1)
        door_row = shared[0]
        self.assertEqual(door_row["rooms"], ["bed", "living"])
        self.assertEqual(door_row["swing_room"], "bed")
        self.assertEqual(door_row["swing_basis"], "DRAFTING_DEFAULT")
        self.assertEqual(len(door_row["source_ids"]), 2, "both canonical door records keep their identity")
        leaf = door_row["leaves"][0]
        self.assertAlmostEqual(leaf["radius"], 0.9)
        # Swings east into the bedroom from the bedroom face of the wall (x = 6.2).
        self.assertAlmostEqual(leaf["hinge"][0], 6.2)
        self.assertAlmostEqual(leaf["open"][0], 6.2 + 0.9)
        # Hinge on the jamb nearer the bedroom's north corner, so the leaf rests on a wall.
        self.assertAlmostEqual(leaf["hinge"][1], 0.1 + 2.5 - 0.45)

    def test_corridor_door_swings_into_the_room(self):
        _, _, d = drafting(home())
        row = next(o for o in d["doors"] if o["axis"] == "x" and abs(o["fixed"] - 5.1) < 1e-9
                   and abs((o["a"] + o["b"]) / 2 - 9.1) < 1e-6)
        self.assertEqual(row["swing_room"], "bed")
        self.assertLess(row["leaves"][0]["open"][1], 5.1, "opens north, into the bedroom")

    def test_wide_opening_is_a_double_door(self):
        _, _, d = drafting(home())
        row = next(o for o in d["doors"] if abs(o["width"] - 1.6) < 1e-9)
        self.assertEqual(row["kind"], "double")
        self.assertEqual(len(row["leaves"]), 2)
        self.assertAlmostEqual(row["leaves"][0]["radius"], 0.8)

    def test_window_symbol_has_sill_and_glazing_lines(self):
        rev, _, d = drafting(home())
        self.assertEqual(len(d["windows"]), 1)
        sheet = D.sheet_for(rev.model)
        ops = D.plan_ops(d, D.Paper(sheet))
        glaz = [op for op in ops["lines"] if op["layer"] == "A-GLAZ"]
        self.assertEqual(len(glaz), 4)
        zs = sorted(round(op["a"][1], 4) for op in glaz)
        self.assertEqual(zs[0], 0.0)
        self.assertEqual(zs[-1], 0.2)

    def test_warehouse_docks_are_overhead_openings_and_zones_separate(self):
        _, _, d = drafting(warehouse())
        self.assertEqual(len(d["docks"]), 2)
        self.assertEqual({dock["kind"] for dock in d["docks"]}, {"overhead"})
        self.assertFalse(inside(d["walls"]["cut"], 24.0, 4.0), "dock opening in the east wall")
        self.assertTrue(inside(d["walls"]["cut"], 24.0, 7.0), "wall between the two docks")
        # The two zones share an open edge (no wall): it is drawn as a separation line.
        self.assertIn([[18.0, 0.0], [18.0, 16.0]], d["separations"])


class StairTests(unittest.TestCase):
    def test_departing_stair_has_up_arrow_cut_line_and_overhead_flights(self):
        _, _, d = drafting(stair_home(), 0)
        self.assertEqual(len(d["stairs"]), 1)
        stair = d["stairs"][0]
        self.assertEqual(stair["role"], "up")
        self.assertEqual([a["kind"] for a in stair["arrows"]], ["up"])
        self.assertEqual(stair["arrows"][0]["label"], "صعود")
        self.assertIsNotNone(stair["break"], "the 1.2 m plan cut crosses the first flight")
        self.assertTrue(stair["overhead"], "treads above the cut are dashed")
        tag = next(t for t in d["tags"] if t["label"] == "الدرج")
        self.assertEqual(tag["center"], stair["landing_center"], "the stair tag sits on the landing")

    def test_arriving_stair_is_drawn_from_above_with_down_arrow(self):
        _, _, d = drafting(stair_home(), 1)
        self.assertEqual([s["role"] for s in d["stairs"]], ["down"])
        stair = d["stairs"][0]
        self.assertEqual(stair["arrows"][0]["kind"], "down")
        self.assertEqual(stair["overhead"], [])
        self.assertIsNone(stair["break"])


class AnnotationTests(unittest.TestCase):
    def test_room_tags_report_net_area_to_wall_faces(self):
        _, p, d = drafting(home())
        living = next(t for t in d["tags"] if t["label"] == "صالة")
        self.assertAlmostEqual(living["clear_w_m"], 5.8)
        self.assertAlmostEqual(living["clear_d_m"], 4.8)
        self.assertAlmostEqual(living["net_area_m2"], 27.84)
        self.assertAlmostEqual(living["axis_area_m2"], 30.0)
        porch = next(t for t in d["tags"] if t["label"] == "رواق")
        # Only the porch edge shared with the corridor wall has a wall face to deduct.
        self.assertAlmostEqual(porch["net_area_m2"], 3.0 * 1.3, places=6)
        self.assertEqual(porch["walls_present"], ["N"])
        self.assertEqual([t["number"] for t in d["tags"]], ["S1", "S2", "S3", "S4"])
        self.assertEqual([t["source_id"] for t in d["tags"]], [x["source_id"] for x in p["primitives"]])

    def test_dimension_chains_close_on_the_overall_dimension(self):
        _, _, d = drafting(home())
        sides = {c["side"] for c in d["chains"]}
        self.assertEqual(sides, {"N", "S", "W", "E"})
        for chain in d["chains"]:
            overall = next(c for c in d["chains"] if c["side"] == chain["side"] and c["kind"] == "overall")
            self.assertEqual(chain["points"][0], overall["points"][0])
            self.assertEqual(chain["points"][-1], overall["points"][-1])
            segments = [b - a for a, b in zip(chain["points"], chain["points"][1:])]
            self.assertAlmostEqual(sum(segments), overall["points"][-1] - overall["points"][0], places=6)
        north = {c["kind"]: c["points"] for c in d["chains"] if c["side"] == "N"}
        self.assertEqual(north["overall"], [0.0, 10.2])
        self.assertIn(6.1, north["walls"], "interior wall dimensioned to its centre line")
        self.assertIn(2.1, north["openings"])
        self.assertIn(4.1, north["openings"])
        ranks = [c["rank"] for c in d["chains"] if c["side"] == "N"]
        self.assertEqual(ranks, [0, 1, 2], "openings inside, walls, then overall outermost")

    def test_dimension_text_is_metres_to_the_centimetre(self):
        self.assertEqual(D.fmt_length(3.568), "3.57")
        self.assertEqual(D.fmt_length(4.0), "4.00")
        self.assertEqual(D.fmt_area(27.8449), "27.84 m2")

    def test_gross_area_is_measured_to_outer_faces(self):
        _, _, d = drafting(home())
        # Walled footprint 10.2 x 6.7 plus the recessed porch inside its west wall.
        self.assertGreater(d["gross_area_outer_faces_m2"], 10.2 * 6.7)
        self.assertLess(d["gross_area_outer_faces_m2"], 10.2 * 8.0)


class SheetTests(unittest.TestCase):
    def test_standard_paper_and_scale_choice(self):
        self.assertEqual({k: STD.choose_sheet(20, 25)[k] for k in ("paper", "scale")}, {"paper": "A2", "scale": 100})
        self.assertEqual({k: STD.choose_sheet(18, 15)[k] for k in ("paper", "scale")}, {"paper": "A3", "scale": 100})
        self.assertEqual({k: STD.choose_sheet(8, 6)[k] for k in ("paper", "scale")}, {"paper": "A3", "scale": 50})
        self.assertEqual({k: STD.choose_sheet(120, 80)[k] for k in ("paper", "scale")}, {"paper": "A1", "scale": 200})
        huge = STD.choose_sheet(5000, 3000)
        self.assertFalse(huge["standard_scale"])
        for paper, scale in STD.SHEET_CANDIDATES:
            self.assertIn(scale, STD.PREFERRED_SCALES)
            self.assertIn(paper, STD.PAPER_MM)

    def test_svg_is_a_true_scale_sheet_that_keeps_the_projection_contract(self):
        rev = draft_revision(home())
        p = project(rev, 0)
        out = render_svg(rev, 0)
        root = ET.fromstring(out["svg_text"])
        sheet = D.sheet_for(rev.model)
        pw, ph = sheet["paper_mm"]
        self.assertEqual(root.attrib["width"], "%gmm" % pw)
        self.assertEqual(root.attrib["viewBox"], "0 0 %g %g" % (pw, ph))
        self.assertEqual(root.attrib["data-acs-scale"], "1:%d" % sheet["scale"])
        self.assertEqual(root.attrib["data-acs-drafting-hash"], out["drafting"]["drafting_hash"])
        metadata = json.loads(root.find(SVG + "metadata").text)
        self.assertEqual(canonical(metadata), canonical({k: v for k, v in p.items() if k != "primitives"}))
        groups = root.findall(SVG + "g")
        self.assertEqual(len(groups), len(p["primitives"]), "only room groups are top-level groups")
        paper = D.Paper(sheet)
        for g, prim in zip(groups, p["primitives"]):
            self.assertEqual(g.attrib["data-source-id"], prim["source_id"])
            rect = g.find(SVG + "rect")
            x, z, w, dd = prim["rect_xz_m"]
            px, py = paper.to_paper((x, z))
            self.assertAlmostEqual(float(rect.get("x")), px, places=2)
            self.assertAlmostEqual(float(rect.get("y")), py, places=2)
            self.assertAlmostEqual(float(rect.get("width")), w * paper.k, places=2)
        classes = {e.get("class") for e in root.iter() if e.get("class")}
        for layer in ("A-WALL", "A-WALL-PATT", "A-DOOR", "A-DOOR-SWNG", "A-GLAZ", "A-ANNO-DIMS", "A-AREA-BNDY"):
            self.assertIn(layer, classes)
        text = out["svg_text"]
        self.assertIn("Not construction documents", text)
        self.assertIn("1:%d" % sheet["scale"], text)
        self.assertIn("27.84 m2", text, "net room area in the tag")
        self.assertIn("6 × 5 m", text, "canonical axis size stays in the room description")
        self.assertEqual(out["drafting"]["counts"]["doors"], 4)

    def test_drawing_is_deterministic_and_does_not_mutate_the_model(self):
        rev = draft_revision(home())
        before = rev.model_json
        first = to_svg(rev, 0)
        self.assertEqual(first, to_svg(rev, 0))
        self.assertEqual(rev.model_json, before)

    def test_title_block_carries_scale_units_and_disclaimer(self):
        rev = draft_revision(home())
        text = to_svg(rev, 0)
        for needle in ("المقياس", "الأبعاد بالمتر", "NOT FOR CONSTRUCTION", "جدول المساحات", "A-101"):
            self.assertIn(needle, text)


class StandardsTableTests(unittest.TestCase):
    def test_layer_names_follow_ncs_pattern_and_plot_widths_are_iso(self):
        import re
        for name, spec in STD.LAYERS.items():
            self.assertRegex(name, r"^[ACM]-[A-Z]{4}(-[A-Z]{4})?$")
            self.assertIn(spec["lw"], STD.ISO_LINE_WIDTHS_MM)
            self.assertIn(spec["lt"], STD.LINETYPE_MM)
            self.assertTrue(re.fullmatch(r"#[0-9a-f]{6}", spec["svg"]))
        for height in STD.TEXT_HEIGHT_MM.values():
            self.assertGreaterEqual(height, 1.8)

    def test_dimensional_rules_carry_their_basis(self):
        for table in (STD.DOOR_CLEAR_WIDTH_MIN_M, STD.DOOR_NOMINAL_LEAF_M, STD.WALL_THICKNESS_M,
                      STD.CORRIDOR_WIDTH_MIN_M, STD.HABITABLE_ROOM_MIN, STD.STAIR["general"], STD.STAIR["dwelling"]):
            for row in table.values():
                self.assertIn(row["basis"], ("CODE_REFERENCE", "PRACTICE"))
                self.assertIn(row["source"], STD.SOURCES)
        self.assertTrue(STD.door_clear_width_ok(0.82))
        self.assertFalse(STD.door_clear_width_ok(0.76))
        self.assertTrue(STD.corridor_ok(1.2, "within_dwelling"))
        self.assertFalse(STD.corridor_ok(0.85, "within_dwelling"))
        good = STD.stair_ok(0.17, 0.28, "general")
        self.assertTrue(good["riser_ok"] and good["tread_ok"] and good["comfort_ok"])
        self.assertFalse(STD.stair_ok(0.20, 0.24, "dwelling")["riser_ok"])
        self.assertEqual(STD.model_size_m(2.5, 100), 0.25)
        self.assertEqual(STD.scale_bar_length_m(100), (5.0, 5))


class RuntimePackagingTests(unittest.TestCase):
    PROBE = '''
import json, sys
from pathlib import Path
import acs_plan_drafting, acs_plan_projection
assert Path(acs_plan_drafting.__file__).resolve().parent == Path.cwd()
from acs_plan_review import PlanWorkspace
model = json.loads(sys.argv[1])
rev = PlanWorkspace().propose(model, brief="b 12", requirements=[{"id": "w", "metric": "site_width_m",
    "expected": 12.0, "source": "requested", "evidence": "12"}], expected_head=None, note="probe")
svg = acs_plan_projection.to_svg(rev, 0)
assert "A-WALL" in svg and "1:" in svg
print("DRAFTING RUNTIME PACKAGING PASS")
'''

    def test_image_copy_set_can_draw_a_plan_sheet(self):
        copied = []
        for line in (ROOT / "Dockerfile").read_text().splitlines():
            words = shlex.split(line, comments=True)
            if words and words[0] == "COPY":
                copied += [(Path(s), Path(words[-1])) for s in words[1:-1] if (ROOT / s).is_file()]
        names = {source.name for source, _ in copied}
        self.assertIn("acs_plan_drafting.py", names)
        self.assertIn("acs_drafting_standards.py", names)
        with tempfile.TemporaryDirectory(prefix="acs-image-copy-") as tmp:
            for source, destination in copied:
                dest = Path(tmp) / destination
                if not destination.suffix:
                    dest /= source.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / source, dest)
            run = subprocess.run([sys.executable, "-I", "-S", "-c",
                                  "import sys; sys.path.insert(0, %r)\n" % tmp + self.PROBE, json.dumps(home())],
                                 cwd=tmp, capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 0, run.stderr[-2000:])
        self.assertIn("DRAFTING RUNTIME PACKAGING PASS", run.stdout)


class ApprovedReceiptTests(unittest.TestCase):
    def test_approved_svg_and_cad_receipts_describe_the_drafting(self):
        from tools import acs_plan_cad_export, acs_plan_svg_export
        ws = PlanLockWorkspace(verified)
        rev = ws.propose(home(), brief=BRIEF, requirements=program(), expected_head=None, note="approved")
        ws.approve(rev.id, expected_head=rev.id, actor_label="test-engineer", confirmed=True,
                   acknowledge_concept_only=True)
        with tempfile.TemporaryDirectory() as td:
            svg_receipt = acs_plan_svg_export.export_approved_svg(ws, rev.id, 0, Path(td) / "a.svg")
            cad_receipt = acs_plan_cad_export.export_approved_cad(ws, rev.id, 0, Path(td) / "b.svg")
            for receipt in (svg_receipt, cad_receipt):
                drafting_row = receipt["drafting"]
                self.assertEqual(drafting_row["schema"], D.SCHEMA)
                self.assertEqual(drafting_row["scope"], D.SCOPE)
                self.assertIn("door_swing_side", drafting_row["drafting_defaults"])
                self.assertIn("structural_grid", drafting_row["not_drawn"])
            self.assertEqual(svg_receipt["drafting"]["drafting_hash"], cad_receipt["drafting"]["drafting_hash"])
            self.assertTrue(acs_plan_svg_export.verify_svg_export(Path(td) / "a.svg")["ok"])
            self.assertTrue(acs_plan_cad_export.verify_cad_export(Path(td) / "b.svg")["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
