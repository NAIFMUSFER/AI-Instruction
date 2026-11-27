#!/usr/bin/env python3
"""DXF and PDF drawing-standard regressions for approved ACS plan exports.

Reads the produced files back with independent readers (ezdxf, pypdf, zlib):
NCS layer names with ByLayer properties, metre units and dimension style, real
DIMENSION entities that measure the canonical chains, door swing arcs bound to
their canonical door identities, ISO paper and a standard scale on the PDF, and
the Arabic title block. Synthetic models only; no provider or network call.
"""
from __future__ import annotations

from collections import Counter
import io
from pathlib import Path
import re
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "remediation"))
import ezdxf  # mandatory for this dedicated suite; do not silently skip it
from pypdf import PdfReader

import acs_drafting_standards as STD
import acs_plan_drafting as D
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_projection import project
from test_plan_drafting import BRIEF, home, program, stair_home, verified
from tools.acs_plan_cad_export import export_approved_cad, verify_cad_export
from tools.acs_plan_pdf_export import export_approved_pdf, verify_pdf_export


def approved(model):
    ws = PlanLockWorkspace(verified)
    rev = ws.propose(model, brief=BRIEF, requirements=program(), expected_head=None, note="drawing standards")
    ws.approve(rev.id, expected_head=rev.id, actor_label="test-engineer", confirmed=True,
               acknowledge_concept_only=True)
    return ws, rev


class DxfStandardsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.ws, cls.rev = approved(home())
        cls.path = Path(cls.tmp.name) / "home.dxf"
        cls.receipt = export_approved_cad(cls.ws, cls.rev.id, 0, cls.path)
        cls.doc = ezdxf.readfile(cls.path)
        cls.msp = cls.doc.modelspace()
        p = project(cls.ws.get(cls.rev.id).revision, 0)
        cls.draft = D.level_drafting(cls.ws.get(cls.rev.id).revision.model, 0, p["primitives"], p["source_map"])
        cls.sheet = D.sheet_for(cls.ws.get(cls.rev.id).revision.model)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_dxf_is_valid_metric_and_receipt_bound(self):
        self.assertEqual(self.doc.audit().errors, [])
        header = self.doc.header
        self.assertEqual(header["$INSUNITS"], 6)
        self.assertEqual(header["$MEASUREMENT"], 1)
        self.assertEqual(header["$LUNITS"], 2)
        self.assertEqual(header["$LWDISPLAY"], 1)
        self.assertEqual(header["$DIMSCALE"], float(self.sheet["scale"]))
        self.assertTrue(verify_cad_export(self.path)["ok"])
        self.assertEqual(self.receipt["drafting"]["scale"], self.sheet["scale"])
        self.assertFalse(self.receipt["native_dwg"])

    def test_ncs_layers_with_iso_lineweights_and_bylayer_entities(self):
        for name, spec in STD.LAYERS.items():
            layer = self.doc.layers.get(name)
            self.assertEqual(layer.dxf.color, spec["aci"])
            self.assertEqual(layer.dxf.lineweight, int(round(spec["lw"] * 100)))
            expected_lt = "Continuous" if spec["lt"] == "CONTINUOUS" else spec["lt"]
            self.assertEqual(layer.dxf.linetype, expected_lt)
        self.assertEqual(self.doc.layers.get("A-AREA").dxf.plot, 0, "room rectangles do not plot")
        used = Counter(e.dxf.layer for e in self.msp)
        for name in used:
            self.assertIn(name, STD.LAYERS, "every model-space entity sits on an NCS layer")
        for entity in self.msp:
            self.assertEqual(entity.dxf.color, 256, "colour ByLayer (EXPRO)")
            self.assertEqual(entity.dxf.linetype.upper(), "BYLAYER")
            self.assertEqual(entity.dxf.lineweight, -1)
        dashed = self.doc.linetypes.get("DASHED")
        # Patterns are pre-scaled to the sheet: 3 mm dash + 1.5 mm gap on paper.
        total = next(tag.value for tag in dashed.pattern_tags.tags if tag.code == 40)
        self.assertAlmostEqual(total, 4.5 * self.sheet["scale"] / 1000.0, places=6)

    def test_walls_are_lines_plus_one_solid_poche_hatch(self):
        hatches = list(self.msp.query('HATCH[layer=="A-WALL-PATT"]'))
        self.assertEqual(len(hatches), 1)
        self.assertEqual(hatches[0].dxf.solid_fill, 1)
        self.assertEqual(len(hatches[0].paths), len(self.draft["walls"]["cut"]))
        edges = sum(len(loop) for loop in self.draft["walls"]["cut"])
        self.assertEqual(len(self.msp.query('LINE[layer=="A-WALL"]')), edges)
        # The pinned boundary contract is unchanged: one LWPOLYLINE per space.
        self.assertEqual(len(self.msp.query("LWPOLYLINE")), len(self.draft["tags"]))

    def test_door_swings_are_arcs_with_door_identity(self):
        arcs = list(self.msp.query('ARC[layer=="A-DOOR-SWNG"]'))
        leaves = [leaf for door in self.draft["doors"] for leaf in door["leaves"]]
        self.assertEqual(len(arcs), len(leaves))
        self.assertEqual(sorted(round(a.dxf.radius, 6) for a in arcs), sorted(round(l["radius"], 6) for l in leaves))
        for arc in arcs:
            span = (arc.dxf.end_angle - arc.dxf.start_angle) % 360.0
            self.assertAlmostEqual(span, 90.0, places=6)
        shared = next(d for d in self.draft["doors"] if d["rooms"] == ["bed", "living"])
        tagged = [a for a in arcs if a.has_xdata("ACS_PLAN")]
        ids = {tag.value for a in tagged for tag in a.get_xdata("ACS_PLAN")}
        self.assertTrue(set(shared["source_ids"]) <= ids)

    def test_dimensions_are_real_dimension_entities_measuring_the_chains(self):
        dims = list(self.msp.query("DIMENSION"))
        expected = sorted(round(b - a, 4) for c in self.draft["chains"] for a, b in zip(c["points"], c["points"][1:]))
        measured = sorted(round(d.get_measurement(), 4) for d in dims)
        self.assertEqual(measured, expected)
        self.assertEqual({d.dxf.layer for d in dims}, {"A-ANNO-DIMS"})
        self.assertEqual({d.dxf.dimstyle for d in dims}, {"ACS-ARCH"})
        style = self.doc.dimstyles.get("ACS-ARCH")
        self.assertEqual(style.dxf.dimdec, 2)
        self.assertGreater(style.dxf.dimtsz, 0, "architectural ticks, not arrows")

    def test_texts_use_one_arabic_capable_style_and_iso_heights(self):
        style = self.doc.styles.get("ACS-ARABIC")
        self.assertEqual(style.dxf.font, "arial.ttf")
        texts = list(self.msp.query("TEXT"))
        self.assertEqual({t.dxf.style for t in texts}, {"ACS-ARABIC"})
        scale = self.sheet["scale"]
        names = {t.dxf.text: t for t in texts if t.dxf.layer == "A-FLOR-IDEN"}
        self.assertAlmostEqual(names["صالة"].dxf.height, STD.TEXT_HEIGHT_MM["room_name"] * scale / 1000.0)
        for text in texts:
            self.assertGreaterEqual(text.dxf.height + 1e-9, 1.4 * scale / 1000.0)
        areas = [t.dxf.text for t in texts if t.dxf.layer == "A-AREA-IDEN"]
        self.assertIn("S1 · 27.84 m2", areas)

    def test_dxf_output_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            again = Path(td) / "again.dxf"
            export_approved_cad(self.ws, self.rev.id, 0, again)
            strip = lambda text: re.sub(r"\n\$TD[A-Z]+\n[^\n]*\n[^\n]*", "", text)
            self.assertEqual(strip(again.read_text(encoding="utf-8")).count("\n"),
                             strip(self.path.read_text(encoding="utf-8")).count("\n"))


class PdfSheetTests(unittest.TestCase):
    def test_pdf_pages_are_iso_sheets_at_a_standard_scale(self):
        ws, rev = approved(stair_home())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "set.pdf"
            receipt = export_approved_pdf(ws, rev.id, out)
            sheet = D.sheet_for(ws.get(rev.id).revision.model)
            reader = PdfReader(out)
            self.assertEqual(len(reader.pages), 2)
            pw, ph = STD.PAPER_MM[sheet["paper"]]
            for page in reader.pages:
                box = page.mediabox
                self.assertAlmostEqual(float(box.width), pw * 72 / 25.4, places=1)
                self.assertAlmostEqual(float(box.height), ph * 72 / 25.4, places=1)
            self.assertEqual(receipt["sheet"]["scale"], sheet["scale"])
            self.assertIn(sheet["scale"], STD.PREFERRED_SCALES)
            self.assertEqual([p["sheet"]["sheet_number"] for p in receipt["pages"]], ["A-101", "A-102"])
            self.assertEqual(receipt["pages"][0]["drafting"]["counts"]["stairs"], 1)
            self.assertAlmostEqual(receipt["pages"][0]["scale_points_per_m"],
                                   1000.0 / sheet["scale"] * 72 / 25.4, places=6)
            spaces = receipt["pages"][0]["spaces"]
            self.assertEqual([s["number"] for s in spaces], ["S1", "S2", "S3"])
            self.assertTrue(all("net_area_m2" in s and "clear_size_m" in s for s in spaces))
            text = "\n".join(page.extract_text() for page in reader.pages)
            for needle in ("1:%d" % sheet["scale"], "A-101", "A-102", "Level 1 floor plan", "NOT FOR CONSTRUCTION"):
                self.assertIn(needle, text)
            raw = out.read_bytes()
            self.assertIn(b"/FlateDecode", raw)
            content = reader.pages[0].get_contents().get_data()
            self.assertIn(b" f*", content, "wall poche filled with the even-odd rule")
            self.assertIn(b" c ", content, "door swings and the north arrow are curves")
            title = ("﻿" + "مخطط الدور الأرضي").encode("utf-16-be").hex().upper().encode()
            self.assertIn(title, content)
            self.assertTrue(verify_pdf_export(out)["ok"])

    def test_cosmetic_project_name_never_blocks_the_drawing(self):
        model = home()
        model["meta"]["name"] = "مشروع 🦄"
        ws, rev = approved(model)
        with tempfile.TemporaryDirectory() as td:
            receipt = export_approved_pdf(ws, rev.id, Path(td) / "a.pdf")
            self.assertTrue(receipt["pages"][0]["spaces"])

    def test_shaping_is_cached_per_font_without_changing_output(self):
        from acs_pdf_text import PdfUnicodeFont
        font = PdfUnicodeFont()
        first = font.shape("مخطط الدور الأرضي 1:100")
        reshaper = font._reshaper
        self.assertEqual(font.shape("مخطط الدور الأرضي 1:100"), first)
        self.assertIs(font._reshaper, reshaper)
        fresh = PdfUnicodeFont().shape("مخطط الدور الأرضي 1:100")
        self.assertEqual(fresh, first)


class PageStreamUnitTests(unittest.TestCase):
    def test_compressed_content_round_trips(self):
        ws, rev = approved(home())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "one.pdf"
            export_approved_pdf(ws, rev.id, out)
            raw = out.read_bytes()
        streams = re.findall(rb"/Filter /FlateDecode >>\nstream\n(.*?)\nendstream", raw, re.S)
        self.assertTrue(streams)
        page = zlib.decompress(streams[0])
        self.assertTrue(page.startswith(b"q\n") and page.rstrip().endswith(b"Q"))
        self.assertIn(b"/F2 ", page)


if __name__ == "__main__":
    unittest.main(verbosity=2)
