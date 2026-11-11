"""Legacy IFC must refuse declared stair forms it cannot represent faithfully.

Synthetic local fixtures only. JavaScript runs the shipped engine through the
existing Node harness; this does not claim browser rendering or IFC interoperability.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_bim as bim


def project():
    room = {'id': 'core', 'name': 'درج', 'rect': [0, 0, 8, 8], 'walls': 'none',
            'doors': [], 'windows': [], 'objects': [{
                'id': 'main_stair', 'kind': 'stairs', 'form': 'u_return',
                'x': 4, 'z': 4, 'w': 3, 'd': 6, 'h': 4.5, 'rot': 90,
                'stair': {'schema': 'acs.stair/1'},
            }]}
    model = {'meta': {'type': 'residential'}, 'site': {'w': 20, 'd': 20},
             'wall_h': 3, 'wall_t': .2, 'floor_height': 4.5,
             'levels': [{'index': -1, 'template': 'core', 'elevation': -3.8},
                        {'index': 1, 'template': 'core', 'elevation': 7.5},
                        {'index': 2, 'template': 'empty', 'elevation': 12}],
             'floors': {'core': {'rooms': [room]}, 'empty': {'rooms': [
                 {'id': 'living', 'rect': [0, 0, 8, 8], 'walls': 'none'}]}}}
    digest = hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()
    return {'model': model, 'building_id': 'building', 'model_hash': digest, 'current_revision': 'r1'}


def stair(proj):
    return proj['model']['floors']['core']['rooms'][0]['objects'][0]


def cases():
    rows = []
    for scope in ('ALL', 'LEVELS', 'ENVELOPE_ONLY'):
        for rotation in (0, 90, 180, 270):
            p = project()
            stair(p)['rot'] = rotation
            rows.append({'project': p, 'options': {'scope': scope}, 'valid': False})
    for form in (' U_RETURN ', 'u_ReTuRn', 'spiral', '', '  ', None, False, 0, {}, ['u_return']):
        p = project()
        stair(p)['form'] = form
        rows.append({'project': p, 'options': {}, 'valid': False})
    p = project()
    stair(p)['kind'] = 'STAIR'
    rows.append({'project': p, 'options': {}, 'valid': False})
    for options, valid in [({'scope': 'SPACES_ONLY'}, True),
                           ({'scope': 'SPACES_ONLY', 'levels': [-1]}, True),
                           ({'scope': 'LEVELS', 'levels': [2]}, True),
                           ({'scope': 'ALL', 'levels': []}, True),
                           ({'scope': 'LEVELS', 'levels': [1]}, False),
                           ({'scope': 'ENVELOPE_ONLY', 'levels': [-1]}, False)]:
        rows.append({'project': project(), 'options': options, 'valid': valid})
    p = project()
    del stair(p)['form']
    rows.append({'project': p, 'options': {}, 'valid': True})
    return rows


class StairIfcBoundary(unittest.TestCase):
    def test_export_refuses_u_return_without_a_file_or_manifest(self):
        for scope in ('ALL', 'LEVELS', 'ENVELOPE_ONLY'):
            with self.subTest(scope=scope):
                p = project()
                before = copy.deepcopy(p)
                result = bim.export_ifc(p, {'scope': scope})
                self.assertFalse(result['valid'], 'U-return must never become a straight prism')
                self.assertIsNone(result['file'])
                self.assertIsNone(result['manifest'])
                self.assertEqual(p, before)
                self.assertEqual([i['entity_id'] for i in result['issues']], [
                    'building.flr_-1.core.core.obj_main_stair',
                    'building.flr_1.core.core.obj_main_stair'])
                self.assertTrue(all(i['code'] == 'BIM_EXPORT_VALIDATION_FAILED' and i['blocking']
                                    for i in result['issues']))

    def test_invalid_declared_forms_fail_closed(self):
        for row in cases():
            with self.subTest(options=row['options'], form=stair(row['project']).get('form')):
                before = copy.deepcopy(row['project'])
                built = bim.build_exchange(row['project'], row['options'])
                self.assertEqual(built['valid'], row['valid'])
                if not row['valid']:
                    self.assertIsNone(built['exchange'])
                self.assertEqual(row['project'], before)

    def test_selected_levels_report_only_the_exported_physical_instance(self):
        result = bim.export_ifc(project(), {'scope': 'LEVELS', 'levels': [1]})
        self.assertFalse(result['valid'])
        self.assertEqual([i['entity_id'] for i in result['issues']], ['building.flr_1.core.core.obj_main_stair'])

    def test_spaces_only_and_unselected_stair_levels_still_export(self):
        for options, spaces in [({'scope': 'SPACES_ONLY'}, 3),
                                ({'scope': 'SPACES_ONLY', 'levels': [-1]}, 1),
                                ({'scope': 'LEVELS', 'levels': [2]}, 1)]:
            result = bim.export_ifc(project(), options)
            self.assertTrue(result['valid'], result['issues'])
            self.assertEqual(result['manifest']['stair_count'], 0)
            self.assertEqual(result['manifest']['space_count'], spaces)
            self.assertNotIn('=IFCSTAIR(', result['file'])
            self.assertEqual(result['file'].count('=IFCSPACE('), spaces)

    def test_legacy_absent_form_preserves_existing_exchange(self):
        p = project()
        del stair(p)['form']
        result = bim.export_ifc(p)
        self.assertTrue(result['valid'], result['issues'])
        self.assertEqual(result['manifest']['stair_count'], 2)
        self.assertEqual(result['file'].count('=IFCSTAIR('), 2)

    def test_shipped_browser_python_boundary_parity(self):
        rows = cases()
        result = subprocess.run(['node', str(ROOT / 'tests/lib/run.js'),
                                 str(ROOT / 'tests/remediation/stair_ifc_exchange_parity.js')],
                                input=json.dumps(rows), capture_output=True, text=True,
                                cwd=ROOT, timeout=30, check=True)
        browser = json.loads(result.stdout)
        expected = []
        for row in rows:
            built = bim.build_exchange(row['project'], row['options'])
            expected.append({'valid': built['valid'], 'issues': built['issues'],
                             'stair_ids': [s['canonical_id'] for s in (built['exchange'] or {}).get('stairs', [])],
                             'level_ids': [s['canonical_id'] for s in (built['exchange'] or {}).get('levels', [])]})
        self.assertEqual(browser, expected)

    def test_shipped_panel_clears_old_success_and_explains_refusal(self):
        subprocess.run(['node', str(ROOT / 'tests/lib/run.js'),
                        str(ROOT / 'tests/remediation/test_stair_ifc_panel.js')],
                       capture_output=True, text=True, cwd=ROOT, timeout=30, check=True)


if __name__ == '__main__':
    unittest.main()
