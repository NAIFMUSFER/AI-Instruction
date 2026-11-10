"""محاذاة غرف النواة ليست إثباتاً للمشي بين الأدوار."""
import copy
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_bridge import existing_geometry_verifier
from acs_plan_review import PlanWorkspace
from test_plan_bridge_integration import fixture
import acs_plan_bridge as B
import acs_plan_review as R


def complete_objects(model):
    for floor in model['floors'].values():
        floor['rooms'][0]['objects'] = [{'id': 'flight', 'kind': 'stairs',
            'x': 1.5, 'z': 2, 'y': 0, 'w': 1.2, 'd': 3.8, 'h': 3.2,
            'count': 1, 'pitch': 1.2, 'dir': 'z'}]
    return model


class VerticalCoverage(unittest.TestCase):
    def coverage(self, model):
        return existing_geometry_verifier(model)['coverage']['vertical_circulation']

    def test_aligned_rooms_do_not_claim_physical_traversal(self):
        model = fixture()
        before = copy.deepcopy(model)
        report = existing_geometry_verifier(model)
        self.assertEqual(report['scopes']['vertical_circulation'], 'PASS')
        self.assertEqual(report['issues'], [])
        c = report['coverage']['vertical_circulation']
        self.assertEqual(c['core_alignment'], 'PASS')
        self.assertEqual(c['physical_traversal'], 'NOT_VERIFIED')
        self.assertEqual(c['geometry'], 'MISSING')
        self.assertEqual({v['level_index'] for v in c['missing_geometry']}, {0, 1})
        self.assertEqual({v['room_id'] for v in c['missing_geometry']}, {'stair_1'})
        self.assertEqual(model, before)
        self.assertEqual(report, existing_geometry_verifier(model))

    def test_explicit_core_objects_are_present_but_not_a_walkability_proof(self):
        c = self.coverage(complete_objects(fixture()))
        self.assertEqual(c['geometry'], 'PRESENT')
        self.assertEqual(c['missing_geometry'], [])
        self.assertEqual(c['physical_traversal'], 'NOT_VERIFIED')

    def test_missing_dimensions_and_unrelated_objects_do_not_fill_coverage(self):
        for change in ('kind', 'x', 'z', 'y', 'w', 'd', 'h'):
            with self.subTest(change=change):
                m = complete_objects(fixture())
                o = m['floors']['g']['rooms'][0]['objects'][0]
                if change == 'kind':
                    o['kind'] = 'table'
                else:
                    del o[change]
                self.assertEqual(self.coverage(m)['geometry'], 'MISSING')

    def test_invalid_dimensions_do_not_fill_coverage(self):
        for key, value in (('w', 0), ('d', -1), ('h', float('nan')), ('x', 'unknown')):
            with self.subTest(key=key):
                m = complete_objects(fixture())
                m['floors']['g']['rooms'][0]['objects'][0][key] = value
                self.assertEqual(self.coverage(m)['geometry'], 'MISSING')

    def test_core_mismatch_still_blocks_approval(self):
        m = fixture()
        m['floors']['f1']['rooms'][0]['rect'][0] += .5
        report = existing_geometry_verifier(m)
        self.assertEqual(report['scopes']['vertical_circulation'], 'FAIL')
        self.assertEqual(report['coverage']['vertical_circulation']['core_alignment'], 'FAIL')
        self.assertIn('VERTICAL_CORE_MISMATCH', [x['code'] for x in report['issues']])

    def test_lift_geometry_is_not_satisfied_by_stairs(self):
        m = complete_objects(fixture())
        for floor in m['floors'].values():
            floor['rooms'][0]['role'] = 'elevator'
        self.assertEqual(self.coverage(m)['geometry'], 'MISSING')
        for floor in m['floors'].values():
            floor['rooms'][0]['objects'][0]['kind'] = 'elevator'
        self.assertEqual(self.coverage(m)['geometry'], 'PRESENT')

    def test_object_based_cores_in_other_room_roles_are_not_reported_missing(self):
        m = complete_objects(fixture())
        for floor in m['floors'].values():
            floor['rooms'][0]['role'] = 'corridor'
        self.assertEqual(self.coverage(m)['geometry'], 'PRESENT')
        self.assertEqual(self.coverage(m)['missing_geometry'], [])

    def test_unmatched_object_elsewhere_does_not_prove_a_named_core_is_missing(self):
        m = complete_objects(fixture())
        for floor in m['floors'].values():
            floor['rooms'][1]['objects'] = floor['rooms'][0].pop('objects')
        self.assertEqual(self.coverage(m)['geometry'], 'NOT_VERIFIED')
        self.assertEqual(self.coverage(m)['missing_geometry'], [])

    def test_unspecified_core_intent_is_unknown_not_a_missing_geometry_defect(self):
        m = fixture()
        for floor in m['floors'].values():
            floor['rooms'][0]['role'] = 'corridor'
        self.assertEqual(self.coverage(m)['geometry'], 'NOT_VERIFIED')
        self.assertEqual(self.coverage(m)['missing_geometry'], [])

    def test_single_level_has_no_interlevel_geometry_requirement(self):
        m = fixture()
        m['levels'] = m['levels'][:1]
        del m['floors']['f1']
        c = self.coverage(m)
        self.assertEqual(c['geometry'], 'NOT_APPLICABLE')
        self.assertEqual(c['missing_geometry'], [])

    def test_legacy_levels_without_index_do_not_crash_coverage(self):
        m = fixture()
        for level in m['levels']:
            del level['index']
        c = self.coverage(m)
        self.assertEqual(c['geometry'], 'MISSING')
        self.assertEqual({v['level_index'] for v in c['missing_geometry']}, {None})

    def test_invalid_level_structures_do_not_turn_review_findings_into_exceptions(self):
        for levels in ('unknown', [None, None], [{}, {}], [{'template': []}, {'template': 'g'}]):
            with self.subTest(levels=levels):
                m = fixture()
                m['levels'] = levels
                ws = PlanWorkspace(existing_geometry_verifier)
                rev = ws.propose(m, brief='two levels', requirements=[], expected_head=None, note='invalid level control')
                r = ws.review(rev.id)
                self.assertFalse(r['can_approve'])
                self.assertEqual(r['coverage']['vertical_circulation']['geometry'], 'NOT_VERIFIED')

    def test_review_preserves_explicit_coverage_and_concept_approval(self):
        m = fixture()
        ws = PlanWorkspace(existing_geometry_verifier)
        revision = ws.propose(m, brief='two levels', requirements=[{
            'id': 'levels', 'metric': 'level_count', 'source': 'requested',
            'evidence': 'two levels', 'expected': 2}], expected_head=None, note='coverage test')
        review = ws.review(revision.id)
        self.assertTrue(review['can_approve'])
        self.assertEqual(review['coverage'], existing_geometry_verifier(m)['coverage'])
        self.assertEqual(review['scopes']['regulatory_compliance'], 'NOT_VERIFIED')

    def test_legacy_verifier_cannot_imply_physical_traversal(self):
        ws = PlanWorkspace(lambda m: {'scopes': {'topology': 'PASS', 'vertical_circulation': 'PASS'},
                                     'issues': []})
        r = ws.propose(fixture(), brief='two levels', requirements=[], expected_head=None, note='legacy test')
        c = ws.review(r.id)['coverage']['vertical_circulation']
        self.assertEqual(c['physical_traversal'], 'NOT_VERIFIED')
        self.assertEqual(c['geometry'], 'MISSING')

    def test_forged_provider_or_verifier_coverage_cannot_promote_traversal(self):
        fake = {'vertical_circulation': {'core_alignment': 'PASS',
                'physical_traversal': 'PASS', 'geometry': 'PRESENT', 'missing_geometry': []}}
        m = fixture()
        m['coverage'] = copy.deepcopy(fake)
        ws = PlanWorkspace(lambda _: {'scopes': {'topology': 'PASS', 'vertical_circulation': 'PASS'},
                                      'issues': [], 'coverage': fake})
        rev = ws.propose(m, brief='two levels', requirements=[], expected_head=None, note='forgery control')
        c = ws.review(rev.id)['coverage']['vertical_circulation']
        self.assertEqual(c['physical_traversal'], 'NOT_VERIFIED')
        self.assertEqual(c['geometry'], 'MISSING')
        self.assertEqual(rev.model, m)


def mutations():
    import inspect
    original = inspect.getsource(R.vertical_geometry_coverage)
    cases = [
        ('invent traversal', "'physical_traversal': 'NOT_VERIFIED'", "'physical_traversal': 'PASS'"),
        ('single-level scope', 'if len(levels) > 1 else []', 'if levels else []'),
        ('missing geometry', 'if not represented:', 'if False:'),
        ('object kind', 'represented = any(complete(obj) and _core_kind(obj) == kind for obj in objects_of(room))',
         'represented = any(complete(obj) for obj in objects_of(room))'),
        ('stated dimensions', "all(_number(obj.get(k)) for k in ('x', 'y', 'z', 'w', 'd', 'h'))", 'True'),
        ('positive dimensions', "all(obj[k] > 0 for k in ('w', 'd', 'h'))", 'True'),
        ('lift kind', "room['role'] == 'elevator'", 'False'),
        ('object-based core scope', 'if not cores:', 'if False:'),
        ('unmatched object is unknown', 'if any(complete(obj) and _core_kind(obj) == kind for obj in floor_objects):', 'if False:'),
        ('invalid level structure', 'if not valid_levels:', 'if False:'),
    ]
    for name, old, new in cases:
        assert original.count(old) == 1, name
        namespace = vars(R).copy()
        exec(original.replace(old, new), namespace)
        fn = namespace['vertical_geometry_coverage']
        with patch.object(R, 'vertical_geometry_coverage', fn), patch.object(B, 'vertical_geometry_coverage', fn):
            result = unittest.TextTestRunner(stream=io.StringIO()).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(VerticalCoverage))
        assert not result.wasSuccessful(), 'SURVIVED: ' + name
        print('KILLED', name)
    print('MUTATIONS', len(cases), 'killed')


if __name__ == '__main__':
    if '--mutations' in sys.argv:
        mutations()
    else:
        unittest.main(verbosity=2)
