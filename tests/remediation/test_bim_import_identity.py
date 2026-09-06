"""C20: identical X/Z on different storeys must not redirect an import edit."""
import copy
import unittest
from test_polygon_gltf import model
import acs_authoring as A
import acs_bim as B


def building():
    b = model()
    room = b['floors']['plan']['rooms'][0]
    del room['polygon']
    room.update(name='Ground room', doors=[{'wall': 'N', 'offset': 2, 'width': 1}])
    b['floors']['upper'] = copy.deepcopy(b['floors']['plan'])
    b['floors']['upper']['rooms'][0]['name'] = 'Upper room'
    b['floors']['upper']['rooms'][0]['doors'][0]['width'] = 2
    b['levels'].append({'index': 1, 'template': 'upper', 'elevation': 10.2})
    return b


def inputs(b=None):
    b = building() if b is None else b
    project = A.create_project(b)
    exported = B.export_ifc(project)
    assert exported['valid'], exported['issues']
    staged = B.stage_import(exported['file'])
    assert staged['valid'], staged['issues']
    return project, staged['staging']


def ground(staging, kind='space'):
    return min((e for e in staging['entities'] if e['canonical_kind'] == kind),
               key=lambda e: e['world']['xyz'][2])


def parity_cases():
    cases = []
    for label in ('identical', 'rename', 'external_rename'):
        project, staging = inputs()
        if label != 'identical':
            ground(staging)['name'] = 'Edited ground'
        if label == 'external_rename':
            for e in staging['entities']:
                e['external_global_id'] = None
        cases.append({'label': label, 'project': project, 'staging': staging,
                      'result': B.import_diff(project, staging)})
    return cases


class ImportIdentity(unittest.TestCase):
    def diff(self, project, staging):
        before = copy.deepcopy((project, staging))
        result = B.import_diff(project, staging)
        self.assertTrue(result['valid'], result['issues'])
        self.assertEqual((project, staging), before)
        return result['diff']

    def test_identical_two_storey_file_has_no_false_edit(self):
        self.assertEqual(self.diff(*inputs())['entries'], [])

    def test_retained_global_id_renames_only_its_own_storey(self):
        project, staging = inputs()
        ground(staging)['name'] = 'Edited ground'
        entries = self.diff(project, staging)['entries']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['canonical_id'], 'bld_0.flr_0.plan.polygon')
        self.assertEqual(entries[0]['authoring_id'], 'plan.polygon')
        self.assertEqual(entries[0]['mapping_basis'], 'SOURCE_GLOBAL_ID')
        self.assertEqual(entries[0]['old_value'], 'Ground room')
        proposals = B.import_proposals(self.diff(project, staging), staging)
        accepted = B.set_proposal_state(proposals, proposals['proposals'][0]['proposal_id'], 'ACCEPTED')
        committed = B.commit_import(project, accepted['proposals'], A)
        self.assertTrue(committed['committed'], committed['issues'])
        self.assertEqual(committed['changed_objects'], ['plan.polygon'])
        self.assertEqual(committed['project']['model']['floors']['upper']['rooms'][0]['name'], 'Upper room')

    def test_reexported_name_change_uses_unique_geometry_and_storey(self):
        project, _ = inputs()
        changed = building()
        changed['floors']['plan']['rooms'][0]['name'] = 'Edited ground'
        _, staging = inputs(changed)
        entries = self.diff(project, staging)['entries']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['canonical_id'], 'bld_0.flr_0.plan.polygon')
        self.assertEqual(entries[0]['mapping_basis'], 'SEMANTIC_AND_GEOMETRY')

    def test_opening_edit_uses_its_storey_even_at_the_same_xz(self):
        project, staging = inputs()
        ground(staging, 'door')['geometry']['width'] = 1.5
        entries = self.diff(project, staging)['entries']
        self.assertEqual(len(entries), 1)
        self.assertIn('.flr_0.', entries[0]['canonical_id'])
        self.assertEqual([entries[0]['field'], entries[0]['old_value'], entries[0]['proposed_value']],
                         ['width', 1, 1.5])

    def test_ambiguous_geometry_without_identity_cannot_prepare_a_rename(self):
        b = building()
        duplicate = copy.deepcopy(b['floors']['plan']['rooms'][0])
        duplicate.update(id='duplicate', name='Same position')
        b['floors']['plan']['rooms'].append(duplicate)
        project, staging = inputs(b)
        for e in staging['entities']:
            e['external_global_id'] = None
        diff = self.diff(project, staging)
        self.assertFalse(any(e['type'] == 'PROPERTY_CHANGED' for e in diff['entries']))
        unmatched = [e for e in diff['entries'] if e['type'] in ('OBJECT_ADDED', 'OBJECT_REMOVED')]
        self.assertTrue(unmatched)
        self.assertTrue(all(e['mapping_basis'] == 'UNMATCHED' for e in unmatched))
        proposals = B.import_proposals(diff, staging)
        self.assertTrue(all(p['state'] == 'BLOCKED' for p in proposals['proposals']))

    def test_missing_coordinates_are_not_the_origin(self):
        project, staging = inputs()
        space = ground(staging)
        space.update(name='Unknown placement', geometry={}, world=None)
        entries = self.diff(project, staging)['entries']
        self.assertFalse(any(e['type'] == 'PROPERTY_CHANGED' for e in entries))
        self.assertTrue(any(e['type'] == 'OBJECT_ADDED' and e['source_entity_id'] == space['source_entity_id']
                            for e in entries))

    def test_moved_identity_keeps_the_existing_unmatched_geometry_guard(self):
        project, staging = inputs()
        space = ground(staging)
        space['geometry']['x'] += 20
        space['name'] = 'Moved ground'
        entries = self.diff(project, staging)['entries']
        self.assertFalse(any(e['type'] == 'PROPERTY_CHANGED' for e in entries))
        self.assertTrue(any(e['type'] == 'OBJECT_ADDED' and e['source_entity_id'] == space['source_entity_id']
                            for e in entries))


if __name__ == '__main__':
    unittest.main(verbosity=2)
