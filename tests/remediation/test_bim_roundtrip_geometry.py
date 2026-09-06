"""C19: a round-trip report must compare actual space and slab geometry."""
import copy
import unittest
from test_polygon_gltf import model, L
from test_polygon_ifc import exported
import acs_authoring as A
import acs_bim as B
import acs_polygon as G


def inputs(building=None):
    building = model() if building is None else building
    result, _ = exported(building)
    staged = B.stage_import(result['file'])
    assert staged['valid'], staged['issues']
    return A.create_project(building), staged['staging']


def entity(staging, kind):
    return next(e for e in staging['entities'] if e['canonical_kind'] == kind)


class RoundtripGeometry(unittest.TestCase):
    def report(self, project, staging):
        before = copy.deepcopy((project, staging))
        result = B.roundtrip_report(project, staging)
        self.assertTrue(result['valid'], result['issues'])
        self.assertEqual((project, staging), before)
        return result['report']

    def failed_geometry(self, report):
        self.assertEqual(report['status'], 'FAIL')
        self.assertGreater(report['critical_loss_count'], 0)
        self.assertLess(report['geometry_fidelity'], 1)

    def test_valid_rectangle_and_polygon_have_no_false_loss(self):
        rectangle = model()
        del rectangle['floors']['plan']['rooms'][0]['polygon']
        for building in (rectangle, model()):
            with self.subTest(polygon='polygon' in building['floors']['plan']['rooms'][0]):
                report = self.report(*inputs(building))
                self.assertEqual(report['status'], 'PASS')
                self.assertEqual(report['geometry_fidelity'], 1)
                self.assertEqual(report['critical_loss_count'], 0)

    def test_missing_or_only_bounding_space_and_slab_cannot_pass(self):
        for kind in ('space', 'slab'):
            for missing in (True, False):
                with self.subTest(kind=kind, missing=missing):
                    project, staging = inputs()
                    product = entity(staging, kind)
                    if missing:
                        product['geometry'] = {}
                    else:
                        product['mapping_class'] = 'BOUNDING_GEOMETRY_ONLY'
                    self.failed_geometry(self.report(project, staging))

    def test_changed_shape_with_same_area_name_and_box_is_a_critical_loss(self):
        project, staging = inputs()
        g = entity(staging, 'space')['geometry']
        mirrored = [[6-x, z] for x, z in L]
        self.assertEqual(abs(G.signed_area(mirrored)), 20)
        g['polygon'] = mirrored
        g['cells'] = G.cells([mirrored])
        self.failed_geometry(self.report(project, staging))

    def test_filled_upper_core_hole_cannot_pass(self):
        building = model(objects=[{'kind': 'stairs', 'core_id': 'A',
                                  'x': 1, 'z': 3, 'w': 1, 'd': 1}])
        building['levels'].append({'index': 1, 'template': 'plan', 'elevation': 10.2})
        project, staging = inputs(building)
        slab = max((e for e in staging['entities'] if e['canonical_kind'] == 'slab'),
                   key=lambda e: e['geometry']['elevation'])
        slab['geometry']['cells'] = [copy.deepcopy(L)]
        self.failed_geometry(self.report(project, staging))

    def test_space_height_and_slab_elevation_are_checked(self):
        for kind, field in (('space', 'height'), ('slab', 'elevation')):
            with self.subTest(kind=kind):
                project, staging = inputs()
                entity(staging, kind)['geometry'][field] += 1
                self.failed_geometry(self.report(project, staging))

    def test_equivalent_winding_partition_and_external_ids_are_preserved(self):
        project, staging = inputs()
        for product in staging['entities']:
            product['external_global_id'] = None
        space = entity(staging, 'space')['geometry']
        space['polygon'] = list(reversed(space['polygon']))
        slab = entity(staging, 'slab')['geometry']
        slab['cells'] = [list(reversed(L))]
        report = self.report(project, staging)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['geometry_fidelity'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
