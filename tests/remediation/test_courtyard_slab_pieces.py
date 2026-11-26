"""Slabs and roofs that declare ``pieces`` are drawn as their pieces.

``compile_architecture`` keeps ``outline`` as the bounding extent of a level and
lists the real slab as ``pieces`` (outline minus a courtyard open to the sky).
The visual scene, its section and the documentation plan used to draw the
outline, i.e. a slab straight across the courtyard on every level. This test
reads every drawn slab/roof box and checks it against the declared courtyard,
in Python and in the shipped browser twin. It does not depend on how many
pieces the architecture layer produces.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import acs_authoring as AU
import acs_docs as D
from acs_arch import compile_architecture
from acs_visual import compile_visual_scene, section_view

GENERATE = """import {apartmentFromBrief} from './public/app/core/local-apartment.mjs';
import {withDefaultRoof} from './public/app/core/roof.mjs';import fs from 'node:fs';
console.log(JSON.stringify(withDefaultRoof(apartmentFromBrief(fs.readFileSync(process.argv[1],'utf8')))[0]));"""
JS_DUMP = """const M=JSON.parse(require('fs').readFileSync(process.env.ACS_MODEL,'utf8'));
const s=compileVisualScene(JSON.parse(JSON.stringify(M)),'bld_0',null,0,{mode:'ENGINEERING'});
const arch=compileArchitecture(JSON.parse(JSON.stringify(M)),'bld_0',null,0);
require('fs').writeFileSync(process.env.ACS_OUT,JSON.stringify({
  objects:s.objects.filter(o=>['SLAB','ROOF','ROOF_CAP'].includes(o.kind)).map(o=>({id:o.id,kind:o.kind,geometry:o.geometry})),
  section:visSection(arch,'x',null).slabs}));"""


def overlap(a, b):
    return (max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])) *
            max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])))


def box_rect(g):
    return [g["cx"] - g["ex"] / 2, g["cz"] - g["ez"] / 2, g["ex"], g["ez"]]


class CourtyardSlabPieces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        brief = ROOT / "tests/fixtures/briefs/riyadh-apartment-courtyard-ar.txt"
        cls.model = json.loads(subprocess.check_output(
            ["node", "--input-type=module", "-e", GENERATE, str(brief)], cwd=ROOT))
        cls.court = cls.model["meta"]["acs_apartment"]["courtyard"]["rect_m"]
        arch = compile_architecture(json.loads(json.dumps(cls.model)))
        cls.pieced = [s for s in arch["slabs"] if isinstance(s.get("pieces"), list)]

    def test_architecture_declares_pieces_for_the_courtyard(self):
        self.assertTrue(self.pieced, "the courtyard levels declare slab pieces")
        for s in self.pieced:
            self.assertGreater(overlap(s["outline"], self.court), 0, "outline stays the full extent")

    def test_python_visual_section_and_docs_leave_the_courtyard_open(self):
        scene = compile_visual_scene(json.loads(json.dumps(self.model)), mode="ENGINEERING")
        drawn = [o for o in scene["objects"] if o["kind"] in ("SLAB", "ROOF", "ROOF_CAP")]
        self.assertTrue(drawn)
        for o in drawn:
            self.assertLessEqual(overlap(box_rect(o["geometry"]), self.court), 1e-6, o["id"])
        arch = compile_architecture(json.loads(json.dumps(self.model)))
        cut = section_view(arch, "x", None)
        self.assertTrue(cut["slabs"])
        x, _, w, _ = self.court
        for s in cut["slabs"]:
            self.assertFalse(s["u0"] < x + w - 1e-6 and s["u1"] > x + 1e-6, s["id"])
        project = AU.create_project(json.loads(json.dumps(self.model)), "bld_0", "IMPORT", None)
        src = D.sources(project)
        for level in src["arch"]["levels"]:
            plan = D.plan_geometry(project, {"level_id": level["id"], "visible_categories": ["SLAB"]}, src)
            elems = plan["elements"] if isinstance(plan, dict) else plan
            for e in (e for e in elems if e.get("category") == "SLAB"):
                self.assertLessEqual(overlap(e["rect"], self.court), 1e-6, e["id"])

    def test_browser_twin_draws_the_same_pieces(self):
        with tempfile.TemporaryDirectory() as tmp:
            model, out, body = Path(tmp) / "m.json", Path(tmp) / "out.json", Path(tmp) / "dump.js"
            model.write_text(json.dumps(self.model), encoding="utf-8")
            body.write_text(JS_DUMP, encoding="utf-8")
            env = dict(os.environ, ACS_MODEL=str(model), ACS_OUT=str(out), TMPDIR=tmp)
            subprocess.check_call(["node", str(ROOT / "tests/phase3/lib/run.js"), str(body)], cwd=ROOT, env=env,
                                  stdout=subprocess.DEVNULL)
            js = json.loads(out.read_text(encoding="utf-8"))
        scene = compile_visual_scene(json.loads(json.dumps(self.model)), mode="ENGINEERING")
        py = [{"id": o["id"], "kind": o["kind"], "geometry": o["geometry"]}
              for o in scene["objects"] if o["kind"] in ("SLAB", "ROOF", "ROOF_CAP")]
        self.assertEqual(js["objects"], py)
        self.assertEqual(js["section"], section_view(compile_architecture(json.loads(json.dumps(self.model))), "x", None)["slabs"])


if __name__ == "__main__":
    unittest.main()
