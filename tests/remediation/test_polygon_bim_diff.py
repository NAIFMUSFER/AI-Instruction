"""C09g: import proposals compare the true region, including its voids."""
import copy
import unittest
from test_polygon_gltf import model, L
import acs_authoring as A
import acs_bim as B
import acs_polygon as G


def inputs(building=None):
    project = A.create_project(model() if building is None else building)
    exported = B.export_ifc(project)
    assert exported['valid'], exported['issues']
    staged = B.stage_import(exported['file'])
    assert staged['valid'], staged['issues']
    return project, staged['staging']


def change_space(staging, ring):
    space = next(e for e in staging['entities'] if e['canonical_kind'] == 'space')
    space['geometry'].update(polygon=ring, cells=G.cells([ring]), area_m2=-999)


def parity_cases():
    result = []
    for label in ('identical', 'area', 'shape'):
        p, s = inputs()
        if label == 'area':
            change_space(s, [[0, 0], [6, 0], [6, 3], [3, 3], [3, 6], [0, 6]])
        elif label == 'shape':
            change_space(s, [[6-x, z] for x, z in L])
        result.append({'label': label, 'project': p, 'staging': s, 'result': B.import_diff(p, s)})
    return result


class PolygonBimDiff(unittest.TestCase):
    def entries(self, project, staging):
        before = copy.deepcopy((project, staging))
        result = B.import_diff(project, staging)
        self.assertTrue(result['valid'], result['issues'])
        self.assertEqual((project, staging), before)
        return result['diff']['entries']

    def test_identical_rectangle_l_and_negative_origin_have_no_proposal(self):
        rectangle = model()
        del rectangle['floors']['plan']['rooms'][0]['polygon']
        for b in (rectangle, model(), model([[x-100, z+230] for x, z in L])):
            with self.subTest(origin=b['floors']['plan']['rooms'][0]['rect']):
                self.assertEqual(self.entries(*inputs(b)), [])

    def test_changed_area_is_measured_from_the_profile_not_the_box_or_metadata(self):
        p, s = inputs()
        change_space(s, [[0, 0], [6, 0], [6, 3], [3, 3], [3, 6], [0, 6]])
        entries = self.entries(p, s)
        self.assertEqual(len(entries), 1)
        self.assertEqual([entries[0][k] for k in ('type', 'field', 'old_value', 'proposed_value')],
                         ['OBJECT_RESIZED', 'area_m2', 20, 27])

    def test_equal_area_different_shape_is_still_a_geometry_change(self):
        p, s = inputs()
        change_space(s, [[6-x, z] for x, z in L])
        entries = self.entries(p, s)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['type'], 'OBJECT_RESIZED')
        self.assertEqual(entries[0]['field'], 'footprint')
        self.assertNotEqual(entries[0]['old_value'], entries[0]['proposed_value'])

    def test_equivalent_winding_and_cell_partition_do_not_create_a_change(self):
        p, s = inputs()
        for product in s['entities']:
            g = product.get('geometry') or {}
            if 'polygon' in g:
                g['polygon'] = list(reversed(g['polygon']))
            if 'cells' in g:
                g['cells'] = [list(reversed(L))]
        self.assertEqual(self.entries(p, s), [])

    def test_filled_upper_core_void_targets_its_slab(self):
        b = model(objects=[{'kind': 'stairs', 'core_id': 'A', 'x': 1, 'z': 3, 'w': 1, 'd': 1}])
        b['levels'].append({'index': 1, 'template': 'plan', 'elevation': 10.2})
        p, s = inputs(b)
        slab = max((e for e in s['entities'] if e['canonical_kind'] == 'slab'),
                   key=lambda e: e['geometry']['elevation'])
        slab['geometry']['cells'] = [copy.deepcopy(L)]
        entries = self.entries(p, s)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['canonical_id'], 'bld_0.flr_1.slab')
        self.assertEqual([entries[0]['type'], entries[0]['field']], ['OBJECT_RESIZED', 'footprint'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
