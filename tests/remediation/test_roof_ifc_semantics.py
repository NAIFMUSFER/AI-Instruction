"""Synthetic IFC roof reference semantics and shipped Python/JS exchange parity.

Internal STEP inspection here supplements the mandatory independent readers;
it does not claim external-tool validation. No provider, network or model writes.
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
import acs_roof


def project():
    room = {'id': 'ordinary_id', 'name': 'مسطح مرجعي', 'rect': [1.123456789,
            6.837209302325586, 4.123456789, 3.4186046511627914],
            'wall_h': .900000123, 'walls': 'none', 'doors': [], 'windows': []}
    model = {'site': {'w': 20, 'd': 20}, 'wall_h': 3, 'wall_t': .2, 'floor_height': 3.2,
             'levels': [{'index': -2, 'template': 'shared', 'elevation': -6.7},
                        {'index': -1, 'template': 'shared', 'kind': 'roof', 'elevation': -2.345678901},
                        {'index': 7, 'template': 'shared', 'kind': 'roof', 'elevation': 12.345678901}],
             'floors': {'shared': {'rooms': [room]}}}
    return {'model': model, 'model_hash': hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest(),
            'current_revision': 'roof-r1', 'building_id': 'bld_0'}


def rows():
    result = [{'project': project(), 'options': {'scope': 'SPACES_ONLY'}, 'valid': True}]
    for name in ('roof', 'ROOF', None, ''):
        p = project()
        for level in p['model']['levels']:
            level.pop('kind', None)
            level.update({'template': 'roof', 'name': 'السطح'})
            if name != 'roof':
                level['kind'] = name
        p['model']['floors']['roof'] = p['model']['floors'].pop('shared')
        result.append({'project': p, 'options': {'scope': 'SPACES_ONLY'}, 'valid': True})
    for levels in ([-2], [-1], [7], [-1, 7], []):
        result.append({'project': project(), 'options': {'scope': 'SPACES_ONLY', 'levels': levels}, 'valid': True})
    for scope in ('ALL', 'LEVELS', 'ENVELOPE_ONLY'):
        result.append({'project': project(), 'options': {'scope': scope}, 'valid': False})
        result.append({'project': project(), 'options': {'scope': scope, 'levels': [-2]}, 'valid': True})
    result.append({'project': project(), 'options': {'scope': 'SPACES_ONLY', 'include_spaces': False}, 'valid': False})
    for value in (None, False, 'unknown', -1):
        p = project(); p['model']['floors']['shared']['rooms'][0]['wall_h'] = value
        result.append({'project': p, 'options': {'scope': 'SPACES_ONLY'}, 'valid': False})
    for value in (None, False, 'unknown'):
        p = project(); p['model']['levels'][1]['elevation'] = value
        result.append({'project': p, 'options': {'scope': 'SPACES_ONLY'}, 'valid': False})
    p = project(); del p['model']['floors']['shared']['rooms'][0]['wall_h']
    result.append({'project': p, 'options': {'scope': 'SPACES_ONLY'}, 'valid': False})
    p = project(); del p['model']['levels'][1]['elevation']
    result.append({'project': p, 'options': {'scope': 'SPACES_ONLY'}, 'valid': False})
    p = project(); p['model']['floors']['shared']['rooms'][0]['rect'][2] = None
    result.append({'project': p, 'options': {'scope': 'SPACES_ONLY'}, 'valid': False})
    p = project(); p['model']['floors']['shared']['rooms'][0]['height'] = p['model']['floors']['shared']['rooms'][0].pop('wall_h')
    result.append({'project': p, 'options': {'scope': 'SPACES_ONLY'}, 'valid': True})
    p = project(); p['model']['floors']['shared']['rooms'] = []
    result.append({'project': p, 'options': {'scope': 'SPACES_ONLY'}, 'valid': False})
    p = project(); p['model']['floors']['shared']['rooms'][0]['wall_h'] = 0
    result.append({'project': p, 'options': {'scope': 'SPACES_ONLY'}, 'valid': True})
    p = project(); p['model']['levels'] = [p['model']['levels'][0]]
    p['model'], _ = acs_roof.add_flat_roof_level(p['model'], parapet_h=0)
    result.append({'project': p, 'options': {'scope': 'SPACES_ONLY'}, 'valid': True})
    return result


class RoofIfcSemantics(unittest.TestCase):
    def test_roof_is_reference_zone_not_storey_space_or_floor_area(self):
        p = project(); before = copy.deepcopy(p)
        result = bim.export_ifc(p, {'scope': 'SPACES_ONLY'})
        self.assertTrue(result['valid'], result['issues'])
        entities = list(bim.parse_step(result['file'])['step']['entities'].values())
        typed = lambda kind: [e for e in entities if e['type'] == kind]
        self.assertEqual(len(typed('IFCBUILDINGSTOREY')), 1)
        self.assertEqual(len(typed('IFCSPACE')), 1)
        self.assertEqual(len(typed('IFCSPATIALZONE')), 2)
        for kind in ('IFCROOF', 'IFCSLAB', 'IFCELEMENTQUANTITY', 'IFCQUANTITYAREA'):
            self.assertEqual(len(typed(kind)), 0)
        self.assertEqual(result['manifest']['level_count'], 1)
        self.assertEqual(result['manifest']['space_count'], 1)
        self.assertEqual(result['manifest']['roof_level_count'], 2)
        self.assertEqual(result['manifest']['roof_reference_count'], 2)
        self.assertEqual(result['manifest']['content_scope'], 'SPACES_AND_UNOCCUPIED_ROOF_REFERENCES')
        self.assertIn('ACS_UNOCCUPIED_ROOF_REFERENCE', result['file'])
        self.assertEqual(len(typed('IFCRELREFERENCEDINSPATIALSTRUCTURE')), 1)
        self.assertEqual(len(typed('IFCPROPERTYSET')), 2)
        for prop in ('LevelKind', 'IsOccupied', 'CountsInFloorArea', 'CanonicalId', 'CanonicalLevelId',
                     'ReferenceGeometry', 'CanonicalHeightDeclared'):
            self.assertIn("'" + prop + "'", result['file'])
        self.assertEqual(p, before)
        self.assertEqual(result['manifest']['model_hash'], p['model_hash'])
        refs = result['exchange']['roof_references']
        self.assertEqual(len({r['canonical_id'] for r in refs}), 2)
        for ref in refs:
            self.assertEqual(ref['footprint'], p['model']['floors']['shared']['rooms'][0]['rect'])
            self.assertFalse(ref['occupied'])
            self.assertFalse(ref['counts_in_floor_area'])
            expected = bim.ifc_guid({'m': p['model_hash'], 'id': ref['canonical_id'], 's': 'IFC4'})
            self.assertIn(expected, [z['args'][0] for z in typed('IFCSPATIALZONE')])

    def test_selected_scopes_unknown_values_and_exact_kind_share_python_js_contract(self):
        cases = rows(); expected = []
        for case in cases:
            with self.subTest(options=case['options'], valid=case['valid']):
                p = case['project']; before = copy.deepcopy(p)
                built = bim.build_exchange(p, case['options'])
                self.assertEqual(built['valid'], case['valid'], built)
                self.assertEqual(p, before)
                if not case['valid']:
                    self.assertIsNone(built['exchange'])
                    self.assertTrue(all(i['blocking'] and i['code'] == 'BIM_EXPORT_VALIDATION_FAILED' for i in built['issues']))
                    out = bim.export_ifc(p, case['options'])
                    self.assertIsNone(out['file']); self.assertIsNone(out['manifest'])
                else:
                    selected = case['options'].get('levels')
                    levels = [l for l in p['model']['levels'] if selected is None or l['index'] in selected]
                    ex = built['exchange']
                    self.assertEqual(len(ex['levels']), sum(l.get('kind') != 'roof' for l in levels))
                    self.assertEqual(len(ex['roof_references']), sum(l.get('kind') == 'roof' for l in levels))
                manifest = bim.export_ifc(p, case['options'])['manifest'] if built['valid'] else None
                keys = ('level_count','space_count','roof_level_count','roof_reference_count',
                        'object_count','content_scope','roof_policy','roof_reference_metadata',
                        'roof_reference_height_policy')
                expected.append({'built':built,'metadata':{k:manifest[k] for k in keys} if manifest else None})
        run = subprocess.run(['node', str(ROOT / 'tests/lib/run.js'),
                              str(ROOT / 'tests/remediation/roof_ifc_exchange_parity.js')],
                             input=json.dumps(cases), capture_output=True, text=True, cwd=ROOT,
                             check=True, timeout=30)
        self.assertEqual(json.loads(run.stdout), expected)

    def test_unknown_nonfinite_geometry_is_refused_instead_of_defaulted(self):
        for value in (float('inf'), float('nan'), 10 ** 400):
            p = project(); p['model']['levels'][1]['elevation'] = value
            result = bim.export_ifc(p, {'scope': 'SPACES_ONLY'})
            self.assertFalse(result['valid'])
            self.assertIsNone(result['file'])

    def test_serialized_negative_and_nonuniform_repeated_roof_bounds(self):
        p = project()
        result = bim.export_ifc(p, {'scope': 'SPACES_ONLY'})
        self.assertTrue(result['valid'], result['issues'])
        entities = bim.parse_step(result['file'])['step']['entities']
        def args(ref):
            return entities[ref.n]['args']
        def coordinates(axis):
            return args(args(axis)[0])[0]
        def placement(ref):
            if ref is None:
                return [0., 0., 0.]
            parent, axis = args(ref)
            return [a+b for a,b in zip(placement(parent), coordinates(axis))]
        expected = {bim.ifc_guid({'m':p['model_hash'],'id':r['canonical_id'],'s':'IFC4'}):r
                    for r in result['exchange']['roof_references']}
        for zone in (e for e in entities.values() if e['type']=='IFCSPATIALZONE'):
            record = expected[zone['args'][0]]
            origin = placement(zone['args'][5])
            shape = args(args(zone['args'][6])[2][0])
            solid = args(shape[3][0]); profile = args(solid[0])
            center = coordinates(profile[2]); offset = coordinates(solid[1])
            width, depth = profile[3:5]
            actual = ((origin[0]+offset[0]+center[0]-width/2, origin[0]+offset[0]+center[0]+width/2),
                      (origin[1]+offset[1]+center[1]-depth/2, origin[1]+offset[1]+center[1]+depth/2),
                      (origin[2]+offset[2],origin[2]+offset[2]+solid[3]))
            x,z,w,d = record['footprint']; elevation = record['elevation']
            wanted = ((x,x+w),(z,z+d),(elevation,elevation+record['height']))
            for actual_axis, expected_axis in zip(actual,wanted):
                for value, expected_value in zip(actual_axis,expected_axis):
                    self.assertAlmostEqual(value,expected_value,places=6)


if __name__ == '__main__':
    unittest.main()
