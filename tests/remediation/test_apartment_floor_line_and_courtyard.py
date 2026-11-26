# -*- coding: utf-8 -*-
"""Physical floor line and courtyard of generated local apartments.

Reads the compiled glTF independently (accessor bounds, no viewer code):
  * every storey's walls meet the slab above (no slit at the floor line) and the
    slab reaches the outer wall faces of the stated building size;
  * a revised central courtyard stays open through every slab and the roof, is a
    declared COURTYARD void of the architectural model with its size provenance,
    and the roof carries the facade parapet on every edge of the opening.

Synthetic local generation only. No provider call. Not a structural or code check.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

import acs_arch                                                    # noqa: E402
from acs_compiler import compile_building                          # noqa: E402
from acs_roof import with_default_roof                             # noqa: E402

TOL = 1e-4
BASE = 'أبغى عمارة عرض المبنى ٢٤ متر وعمقه ٢٨ متر، أربعة أدوار شاملة الأرضي، شقتين في كل دور'
COURT = 'خلّ وسط العمارة فناء مفتوح للسماء وحافظ على عدد الشقق'
GIVEN = 'عمارة سكنية ٢٤×٢٨ م، أربعة أدوار، شقتين في كل دور، وفيها فناء مركزي مفتوح للسماء ٥ × ٦ م'


def generate(script):
    source = ("import {apartmentFromBrief as B,apartmentFromRevision as R,apartmentSample as S} "
              "from './public/app/core/local-apartment.mjs';\n"
              "const json=(" + script + ");process.stdout.write(JSON.stringify(json));")
    out = subprocess.run(['node', '--no-warnings', '--input-type=module', '-e', source], cwd=ROOT,
                         check=True, capture_output=True, text=True).stdout
    model, _, error = with_default_roof(json.loads(out))
    assert error is None, error
    return model


def boxes(model):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'm.gltf')
        compile_building(model, path)
        with open(path, encoding='utf-8') as handle:
            gltf = json.load(handle)
    out = []
    for node in gltf['nodes']:
        if 'mesh' not in node:
            continue
        for prim in gltf['meshes'][node['mesh']]['primitives']:
            acc = gltf['accessors'][prim['attributes']['POSITION']]
            out.append((node['name'], acc['min'], acc['max']))
    return out


def covered(slabs, x, z):
    return any(lo[0] - TOL <= x <= hi[0] + TOL and lo[2] - TOL <= z <= hi[2] + TOL for _, lo, hi in slabs)


class FloorLine(unittest.TestCase):
    def check_floor_line(self, model):
        parts = boxes(model)
        levels = sorted(model['levels'], key=lambda l: l['index'])
        w, d = model['site']['w'], model['site']['d']
        for below, above in zip(levels, levels[1:]):
            walls = [p for p in parts if p[0].startswith('WALL|F%d|' % below['index'])]
            slabs = [p for p in parts if p[0].startswith('FLOOR|F%d|slab|' % above['index'])]
            self.assertTrue(walls and slabs)
            wall_top = max(hi[1] for _, _, hi in walls)
            slab_bottom = min(lo[1] for _, lo, _ in slabs)
            self.assertAlmostEqual(wall_top, below['elevation'] + model['wall_h'], delta=TOL)
            # Agent 08-14 measured walls ending at +3.22 m and the slab above starting at 3.25 m.
            self.assertLessEqual(slab_bottom, wall_top + TOL,
                                 'slit between storey %d walls and the slab above' % below['index'])
            self.assertAlmostEqual(max(hi[1] for _, _, hi in slabs), above['elevation'], delta=TOL)
            # The slab reaches the outer wall faces, not the wall centreline.
            self.assertAlmostEqual(min(lo[0] for _, lo, _ in slabs), 0.0, delta=TOL)
            self.assertAlmostEqual(min(lo[2] for _, lo, _ in slabs), 0.0, delta=TOL)
            self.assertAlmostEqual(max(hi[0] for _, _, hi in slabs), w, delta=TOL)
            self.assertAlmostEqual(max(hi[2] for _, _, hi in slabs), d, delta=TOL)
            for x, z in ((0.03, d / 2), (w - 0.03, d / 2), (w / 2, 0.03), (w / 2, d - 0.03)):
                self.assertTrue(covered(slabs, x, z), (above['index'], x, z))
        return parts

    def test_sample_walls_meet_the_slab_above_out_to_the_outer_faces(self):
        self.check_floor_line(generate('S()'))

    def test_courtyard_is_open_declared_and_guarded_on_every_level_and_the_roof(self):
        model = generate('R(%s,B(%s))' % (json.dumps(COURT), json.dumps(BASE)))
        court = model['meta']['acs_apartment']['courtyard']
        self.assertEqual((court['rect_m'], court['size_source']), ([10, 11.5, 4, 5], 'default_assumption'))
        cx, cz, cw, cd = court['rect_m']
        parts = self.check_floor_line(model)
        for level in model['levels']:
            slabs = [p for p in parts if p[0].startswith('FLOOR|F%d|slab|' % level['index'])]
            for fx in (0.02, 0.5, 0.98):
                for fz in (0.02, 0.5, 0.98):
                    self.assertFalse(covered([(n, [lo[0] + 2 * TOL, 0, lo[2] + 2 * TOL], [hi[0] - 2 * TOL, 0, hi[2] - 2 * TOL])
                                              for n, lo, hi in slabs], cx + cw * fx, cz + cd * fz))
            # ...and the slab carries the courtyard walls up to their faces.
            for x, z in ((cx - 0.05, cz + cd / 2), (cx + cw + 0.05, cz + cd / 2), (cx + cw / 2, cz - 0.05), (cx + cw / 2, cz + cd + 0.05)):
                self.assertTrue(covered(slabs, x, z), (level['index'], x, z))
        arch = acs_arch.compile_architecture(model)
        voids = [v for v in arch['voids'] if v.get('void_type') == 'COURTYARD']
        self.assertEqual([v['level_index'] for v in voids], [l['index'] for l in model['levels']])
        for v in voids:
            self.assertEqual((v['rect'], v['open_to_sky'], v['size_source']), ([10, 11.5, 4, 5], True, 'default_assumption'))
            self.assertEqual((v['clear_width_m'], v['clear_depth_m'], v['clear_area_m2']), (4, 5, 20.0))
        for element in arch['slabs'] + arch['roofs']:
            self.assertEqual(element['outline_basis'], 'bounding_box_minus_declared_voids')
            self.assertFalse(any(acs_arch._overlap_area(p, court['rect_m']) > 0 for p in element['pieces']))
            area = sum(p[2] * p[3] for p in element['pieces'])
            self.assertAlmostEqual(area, element['outline'][2] * element['outline'][3] - 20.0, places=4)
        self.assertNotIn('SLAB_OUTLINE_IS_BOUNDING_BOX', [a['reason'] for a in arch['approximations']])
        # The roof guards every stretch over the opening with the facade parapet.
        roof = next(l for l in model['levels'] if l.get('kind') == 'roof')
        fx, fz, fw, fd = court['footprint_void_m']
        guarded = {'N': 0.0, 'S': 0.0, 'W': 0.0, 'E': 0.0}
        for r in model['floors'][roof['template']]['rooms']:
            x, z, w, d = r['rect']
            self.assertEqual(r['roof_provenance']['parapet_gaps'], [])
            if 'S' in r['walls'] and abs(z + d - fz) < TOL and fx - TOL <= x and x + w <= fx + fw + TOL:
                guarded['N'] += w
            if 'N' in r['walls'] and abs(z - fz - fd) < TOL and fx - TOL <= x and x + w <= fx + fw + TOL:
                guarded['S'] += w
            if 'E' in r['walls'] and abs(x + w - fx) < TOL:
                guarded['W'] += d
            if 'W' in r['walls'] and abs(x - fx - fw) < TOL:
                guarded['E'] += d
            if r['walls']:
                self.assertEqual(r['wall_h'], 0.9)
        self.assertEqual({k: round(v, 3) for k, v in guarded.items()}, {'N': 4.18, 'S': 4.18, 'W': 5.18, 'E': 5.18})

    def test_courtyard_size_from_the_brief_is_recorded_as_the_clients(self):
        model = generate('B(%s)' % json.dumps(GIVEN))
        arch = acs_arch.compile_architecture(model)
        sources = {v['size_source'] for v in arch['voids'] if v.get('void_type') == 'COURTYARD'}
        self.assertEqual(sources, {'client_stated'})
        self.assertEqual(model['meta']['acs_apartment']['courtyard']['rect_m'][2:], [5, 6])


if __name__ == '__main__':
    unittest.main()
