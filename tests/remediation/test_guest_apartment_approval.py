"""The four guest reference apartments pass the production approval gate and
reach every approved export.

The local generator and the gate used to disagree in four ways: rooms had no
declared light, the foyer used the role ``entry`` instead of ``entrance``,
paired door leaves were up to 1 mm apart, and the gate treated the open entrance
porch (a space with no walls) as an enclosed room. The generator now emits the
first three correctly; the gate now treats a wall-less space as exterior, as its
own adjacency rule (``shared``) already did.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from acs_plan_bridge import existing_geometry_verifier
from acs_plan_lock_binding import PlanLockWorkspace
from acs_residential_access import issues as access_issues
from acs_validate import validate_building
from tools.acs_plan_cad_export import export_approved_cad
from tools.acs_plan_handoff import compile_approved_baseline
from tools.acs_plan_ifc_export import export_approved_ifc
from tools.acs_plan_pdf_export import export_approved_pdf

CASES = {
    'riyadh-20x25': 'riyadh-apartment-ar.txt',
    'riyadh-24x28': 'riyadh-apartment-24x28-ar.txt',
    'central-courtyard': 'riyadh-apartment-courtyard-ar.txt',
    'saudi-west-entry': 'saudi-apartment-west-ar.txt',
}
SCRIPT = """import {apartmentFromBrief} from './public/app/core/local-apartment.mjs';
import {withDefaultRoof} from './public/app/core/roof.mjs';import fs from 'node:fs';
console.log(JSON.stringify(withDefaultRoof(apartmentFromBrief(fs.readFileSync(process.argv[1],'utf8')))[0]));"""


def generated(brief):
    out = subprocess.check_output(['node', '--input-type=module', '-e', SCRIPT,
                                   str(ROOT / 'tests/fixtures/briefs' / brief)], cwd=ROOT)
    return json.loads(out)


def approve(model):
    occupied = [level for level in model['levels'] if level.get('kind') != 'roof']
    area = sum(r['rect'][2] * r['rect'][3] for level in occupied
               for r in model['floors'][level['template']]['rooms'])
    ws = PlanLockWorkspace(existing_geometry_verifier)
    rev = ws.propose(model, brief=f'Synthetic total canonical room area {area} square metres.',
                     requirements=[{'id': 'area', 'metric': 'building_target_area_m2', 'expected': area,
                                    'source': 'requested', 'evidence': str(area)}],
                     expected_head=None, note='Guest reference apartment approval')
    return ws, rev, ws.review(rev.id)


class GuestApartmentApproval(unittest.TestCase):
    def test_reference_apartments_are_approved_and_export_every_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for name, brief in CASES.items():
                with self.subTest(case=name):
                    model = generated(brief)
                    ws, rev, review = approve(model)
                    self.assertTrue(review['can_approve'], review['issues'][:5])
                    ws.approve(rev.id, expected_head=rev.id, confirmed=True,
                               acknowledge_concept_only=True, actor_label='guest-reference-test')
                    compile_approved_baseline(ws, rev.id, out / f'{name}.gltf')
                    export_approved_ifc(ws, rev.id, out / f'{name}.ifc')
                    export_approved_pdf(ws, rev.id, out / f'{name}.pdf')
                    for level in model['levels']:
                        for ext in ('svg', 'dxf'):
                            export_approved_cad(ws, rev.id, level['index'],
                                                out / f"{name}-F{level['index']}.{ext}")
                    self.assertTrue((out / f'{name}.ifc').stat().st_size > 0)

    def test_wall_less_porch_is_exterior_but_an_enclosed_room_is_not(self):
        model = generated(CASES['riyadh-20x25'])
        self.assertEqual(access_issues(model), [])
        findings, _ = validate_building(model)
        self.assertFalse([f for f in findings if 'جدار داخلي' in f], 'a window onto the open porch is a facade window')
        ground = model['floors'][model['levels'][0]['template']]['rooms']
        porch = next(r for r in ground if r['id'] == 'entrance_porch')
        self.assertEqual(porch['walls'], [])
        porch['walls'] = ['N', 'S', 'E', 'W']  # the same space, enclosed
        self.assertTrue(access_issues(model), 'a lobby that only opens into an enclosed room has no exterior door')
        findings, _ = validate_building(model)
        self.assertTrue([f for f in findings if 'جدار داخلي' in f and 'entrance_porch' in f])


if __name__ == '__main__':
    unittest.main()
