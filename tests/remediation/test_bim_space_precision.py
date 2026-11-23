"""Numeric regression for the serialized rectangular profile, without a mesher.

This reads STEP literals using the repository parser and reconstructs the simple
axis-aligned placement. It supplements, never replaces, the required independent
IfcOpenShell reader whose six-decimal bounds assertion remains unchanged.
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
    # The depth/start reproduce CI12's 6.8372085 versus 6.837209302325586 bound.
    room = {'id': 'fractional_room', 'rect': [0.123456789012345, 6.837209302325586,
            1.23456789012345, 3.4186046511627914], 'wall_h': 3.10000098765432,
            'walls': 'none', 'doors': [], 'windows': []}
    model = {'site': {'w': 20, 'd': 20}, 'wall_t': .2, 'wall_h': 3.2, 'floor_height': 3.4,
             'levels': [{'index': -1, 'template': 'f', 'elevation': -3.20000012345678}],
             'floors': {'f': {'rooms': [room]}}}
    model_hash = hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()
    return {'model': model, 'model_hash': model_hash, 'current_revision': 'r1', 'building_id': 'b'}


def serialized_space_bounds(text):
    parsed = bim.parse_step(text)
    if not parsed['valid']:
        raise AssertionError(parsed['issues'])
    entities = parsed['step']['entities']
    def entity(ref):
        return entities[ref.n]
    def coordinates(axis_ref):
        return entity(entity(axis_ref)['args'][0])['args'][0]
    def placement(ref):
        if ref is None:
            return [0., 0., 0.]
        parent, axis = entity(ref)['args']
        return [a + b for a, b in zip(placement(parent), coordinates(axis))]
    space = next(e for e in entities.values() if e['type'] == 'IFCSPACE')
    origin = placement(space['args'][5])
    product_shape = entity(space['args'][6])
    representation = entity(product_shape['args'][2][0])
    solid = entity(representation['args'][3][0])
    profile = entity(solid['args'][0])
    profile_center = coordinates(profile['args'][2])
    solid_origin = coordinates(solid['args'][1])
    width, depth = profile['args'][3:5]
    return ((origin[0] + solid_origin[0] + profile_center[0] - width / 2,
             origin[0] + solid_origin[0] + profile_center[0] + width / 2),
            (origin[1] + solid_origin[1] + profile_center[1] - depth / 2,
             origin[1] + solid_origin[1] + profile_center[1] + depth / 2),
            (origin[2] + solid_origin[2], origin[2] + solid_origin[2] + solid['args'][3]))


class ExactSpaceGeometry(unittest.TestCase):
    def test_serialized_profile_preserves_canonical_bounds_without_cumulative_rounding(self):
        p = project()
        before = copy.deepcopy(p)
        exported = bim.export_ifc(p, {'scope': 'SPACES_ONLY'})
        self.assertTrue(exported['valid'], exported['issues'])
        room = p['model']['floors']['f']['rooms'][0]
        x, z, width, depth = room['rect']
        elevation = p['model']['levels'][0]['elevation']
        expected = ((x, x + width), (z, z + depth), (elevation, elevation + room['wall_h']))
        actual = serialized_space_bounds(exported['file'])
        for actual_axis, expected_axis in zip(actual, expected):
            for value, canonical_value in zip(actual_axis, expected_axis):
                self.assertAlmostEqual(value, canonical_value, places=6)
        self.assertEqual(p, before)
        self.assertEqual(exported['manifest']['model_hash'], p['model_hash'])
        self.assertEqual(bim.step_real(1.23456789), '1.234568', 'legacy default formatting is unchanged')

    def test_shared_exchange_keeps_exact_space_values_in_python_and_shipped_javascript(self):
        p = project()
        exchange = bim.build_exchange(p, {'scope': 'SPACES_ONLY'})['exchange']
        room = p['model']['floors']['f']['rooms'][0]
        self.assertEqual(exchange['spaces'][0]['footprint'], room['rect'])
        self.assertEqual(exchange['spaces'][0]['height'], room['wall_h'])
        self.assertEqual(exchange['levels'][0]['elevation'], p['model']['levels'][0]['elevation'])
        result = subprocess.run(['node', str(ROOT / 'tests/lib/run.js'),
                                 str(ROOT / 'tests/remediation/bim_space_precision_parity.js')],
                                input=json.dumps(p), capture_output=True, text=True,
                                cwd=ROOT, timeout=30, check=True)
        self.assertEqual(json.loads(result.stdout), exchange)


if __name__ == '__main__':
    unittest.main()
