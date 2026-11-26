"""A villa from the form is a livable Saudi villa, or the review says why not.

Live job bc82d27f (QA project, villa starter, street W, parking in the front
setback) succeeded with no finding and could be approved, yet its upper floor
was one 77 m² room named «غرف النوم» and the house had no bathroom. Villas had
no structured program, nothing forced separate bedrooms or bathrooms, and the
large generic-space check in acs_validate skips any room whose role is bedroom.

Here: the sanitized live model now produces blocking findings, a livable villa
on the same plot passes, and each livability check is exercised on its own.
The generation side is in test_villa_generation.py.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_validate as V
import acs_villa_program as VP
import acs_workspace_service as S
from acs_plan_bridge import existing_geometry_verifier
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from acs_plan_store_reload import load_workspace

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'villa_program'
PROJECT = '11111111-1111-4111-8111-111111111111'
ACTOR = '22222222-2222-4222-8222-222222222222'
# The signed-in form's villa starter (brief-review.mjs), as the QA job sent it.
STARTER = ('أبغى فيلا عائلية في جدة. عرض الأرض ١٨ متر وعمق الأرض ٢٨ متر. عدد الأدوار ٢ شاملة الأرضي.\n'
           'أبغى مجلس الضيوف قريب من المدخل، وصالة الأسرة تطل على الحديقة. خلّ غرف النوم في الدور '
           'العلوي والمطبخ قريب من غرفة الطعام.\n\nنوع المشروع: سكني / عمارة / فيلا')
PLOT = {'streets': ['W'], 'parking': {'placement': 'front_setback'}}


def starter_rows():
    """The rows the QA job confirmed from the starter text (brief-review.mjs)."""
    out = []
    for i, (metric, expected, evidence) in enumerate((('site_width_m', 18, 'عرض الأرض ١٨ متر'),
                                                      ('site_depth_m', 28, 'عمق الأرض ٢٨ متر'),
                                                      ('level_count', 2, 'عدد الأدوار ٢'))):
        start = STARTER.index(evidence)
        out.append({'id': 'brief-%d' % i, 'metric': metric, 'expected': expected, 'source': 'requested',
                    'source_id': 'brief:text', 'evidence': evidence, 'confirmed': True,
                    'source_span': {'start': start, 'end': start + len(evidence)}})
    return out


def fixture(name):
    return json.loads((FIXTURES / (name + '.json')).read_text(encoding='utf-8'))


def review(model, brief, requirements):
    ws = PlanLockWorkspace(existing_geometry_verifier)
    rev = ws.propose(model, brief=brief, requirements=requirements, expected_head=None, note='villa program')
    return ws.review(rev.id)


def codes(items):
    return sorted(i['code'] for i in items)


def with_program(brief, requirements, bedrooms=4, bathrooms=5, ensuite=1):
    """Append the rows the step-01 villa fields send (residential-options.mjs)."""
    rows = [dict(r) for r in requirements]
    for metric, role, expected, label in (('room_count', 'bedroom', bedrooms, 'غرف النوم في الفيلا'),
                                          ('ensuite_bedroom_count', None, ensuite, 'غرف نوم بحمام خاص'),
                                          ('room_count', 'bathroom', bathrooms, 'الحمامات ودورات المياه في الفيلا')):
        evidence = label + ': ' + str(expected)
        start = len(brief) + 1
        brief += '\n' + evidence
        row = {'id': 'villa-' + metric + '-' + (role or 'all'), 'metric': metric, 'expected': expected,
               'source': 'inferred', 'source_id': VP.VILLA_PROGRAM_SOURCE, 'evidence': evidence,
               'source_span': {'start': start, 'end': len(brief)}, 'confirmed': True}
        if role:
            row['role'] = role
        rows.append(row)
    return brief, rows


def room(model, template, rid):
    return next(r for r in model['floors'][template]['rooms'] if r['id'] == rid)


class LiveVilla(unittest.TestCase):
    def setUp(self):
        self.case = fixture('job_bc82d27f')

    def test_the_sanitized_live_model_is_now_blocked(self):
        for brief, rows in ((self.case['brief'], self.case['requirements']), (STARTER, starter_rows())):
            with self.subTest(brief=brief[:20]):
                result = review(self.case['model'], brief, rows)
                self.assertFalse(result['can_approve'])
                self.assertEqual(result['scopes']['dwelling_program'], 'FAIL')
                self.assertEqual(codes(result['issues']), ['VILLA_AGGREGATE_ROOM', 'VILLA_NO_BATHROOM'])
                merged = next(i for i in result['issues'] if i['code'] == 'VILLA_AGGREGATE_ROOM')
                self.assertEqual(merged['room_ref'], ['upper', 'bedrooms'])
                self.assertIn('«غرف النوم»', merged['message'])
                self.assertIn('77 م²', merged['message'])
                self.assertTrue(all(i['severity'] == 'error' for i in result['issues']))
                # Every other scope passed: before this change the plan was approvable.
                self.assertEqual({k: v for k, v in result['scopes'].items() if v != 'NOT_VERIFIED'},
                                 {'rectangular_geometry': 'PASS', 'program': 'PASS', 'topology': 'PASS',
                                  'vertical_circulation': 'PASS', 'plot_rules': 'PASS', 'dwelling_program': 'FAIL'})

    def test_why_the_existing_checks_missed_it(self):
        model = self.case['model']
        bedrooms = room(model, 'upper', 'bedrooms')
        self.assertEqual((bedrooms['name'], bedrooms['role'], bedrooms['rect'][2] * bedrooms['rect'][3]),
                         ('غرف النوم', 'bedroom', 77.0))
        findings, _ = V.validate_building(model)
        self.assertFalse([f for f in findings if 'حيّز عام' in f], 'role bedroom is exempt from the generic-space check')
        self.assertEqual(existing_geometry_verifier(model)['issues'], [])
        self.assertFalse([r for f in model['floors'].values() for r in f['rooms'] if VP.role(r) in VP.BATH_ROLES])

    def test_with_the_confirmed_villa_program_the_counts_fail_too(self):
        brief, rows = with_program(self.case['brief'], self.case['requirements'])
        result = review(self.case['model'], brief, rows)
        mismatched = sorted(i['requirement_id'] for i in result['issues'] if i['code'] == 'REQUIREMENT_MISMATCH')
        self.assertEqual(mismatched, ['villa-ensuite_bedroom_count-all', 'villa-room_count-bathroom',
                                      'villa-room_count-bedroom'])
        self.assertEqual(result['scopes']['program'], 'FAIL')
        self.assertIn('VILLA_AGGREGATE_ROOM', codes(result['issues']))
        self.assertIn('VILLA_NO_BATHROOM', codes(result['issues']))

    def test_the_saved_workspace_shows_arabic_findings_and_refuses_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SQLitePlanStore(Path(tmp) / 'plans.sqlite3')
            db.create_project(PROJECT, owner_id=ACTOR)
            store = SQLitePlanStoreAdapter(db)
            ws = load_workspace(store, PROJECT, actor_id=ACTOR, verifier=S.existing_geometry_verifier)
            ws.propose(self.case['model'], brief=self.case['brief'], requirements=self.case['requirements'],
                       expected_head=None, note='live villa replay')
            store.save_revision(PROJECT, actor_id=ACTOR, revision=ws.get(ws.head), expected_head=None)
            view = S.view(store, PROJECT, ACTOR)
        self.assertFalse(view['authority']['can_approve_concept'])
        blocking = [f for f in view['review_findings'] if f.get('severity') != 'advisory']
        self.assertEqual(codes(blocking), ['VILLA_AGGREGATE_ROOM', 'VILLA_NO_BATHROOM'])
        self.assertTrue(all(any('؀' <= c <= 'ۿ' for c in f['message']) for f in blocking))


class LivableVilla(unittest.TestCase):
    def setUp(self):
        self.case = fixture('villa_livable')

    def check(self, model=None, brief=None, rows=None):
        return review(model or self.case['model'], self.case['brief'] if brief is None else brief,
                      self.case['requirements'] if rows is None else rows)

    def test_the_livable_villa_passes_with_its_program(self):
        result = self.check()
        self.assertTrue(result['can_approve'], result['issues'][:4])
        self.assertEqual(result['scopes']['dwelling_program'], 'PASS')
        self.assertEqual(result['advisories'], [])
        self.assertEqual(VP.confirmed_program(self.case['requirements']),
                         {'bedroom': 4, 'bathroom': 5, 'maid_room': 0, 'driver_room': 0, 'ensuite': 1})
        self.assertEqual(VP.ensuite_bedroom_count(self.case['model']), 1)

    def test_an_aggregate_bedroom_blocks(self):
        model = copy.deepcopy(self.case['model'])
        room(model, 'upper', 'bedroom_3').update(name='غرف النوم', rect=[5.5, 9.5, 3.5, 9.5])
        model['floors']['upper']['rooms'].remove(room(model, 'upper', 'bedroom_4'))
        room(model, 'upper', 'spine')['doors'].pop()
        result = self.check(model)
        self.assertIn('VILLA_AGGREGATE_ROOM', codes(result['issues']))
        self.assertIn('REQUIREMENT_MISMATCH', codes(result['issues']), 'three bedrooms, not four')
        self.assertFalse(result['can_approve'])

    def test_an_oversized_bedroom_blocks_with_the_program_and_advises_without_it(self):
        model = copy.deepcopy(self.case['model'])
        room(model, 'upper', 'master_bedroom')['rect'] = [5.5, 1.5, 5.0, 6.5]   # 32.5 m²
        room(model, 'upper', 'master_bath')['rect'] = [10.5, 1.5, 2.5, 5.5]
        with patch.object(VP, 'BEDROOM_MAX_M2', 30.0):
            found = VP.check(model, self.case['brief'], self.case['requirements'])
            self.assertIn('VILLA_BEDROOM_OVERSIZED', codes(found[0]))
            old = VP.check(model, 'villa', [])
            self.assertIn('VILLA_BEDROOM_OVERSIZED', codes(old[1]), 'an old revision gets advice, not a block')
            room(model, 'upper', 'master_bedroom')['rect'] = [5.5, 1.5, 7.0, 7.0]   # 49 m²: several rooms
            self.assertIn('VILLA_BEDROOM_OVERSIZED', codes(VP.check(model, 'villa', [])[0]))

    def test_an_upper_floor_without_a_bathroom(self):
        model = copy.deepcopy(self.case['model'])
        for rid in ('master_bath', 'bath_1', 'bath_2'):
            room(model, 'upper', rid)['role'] = 'storage'
        blocking, advisory = VP.check(model, self.case['brief'], self.case['requirements'])
        floor = next(i for i in blocking if i['code'] == 'VILLA_FLOOR_WITHOUT_BATHROOM')
        self.assertEqual(floor['room_ref'][0], 'upper')
        self.assertIn('الدور الأول', floor['message'])
        self.assertIn('VILLA_FLOOR_WITHOUT_BATHROOM', codes(VP.check(model, 'villa', [])[1]))
        self.assertEqual(VP.ensuite_bedroom_count(model), 0)

    def test_a_house_without_any_bathroom_always_blocks(self):
        model = copy.deepcopy(self.case['model'])
        for floor in model['floors'].values():
            for r in floor['rooms']:
                if r.get('role') == 'bathroom':
                    r['role'] = 'storage'
        self.assertEqual(codes(VP.check(model, 'villa', [])[0]), ['VILLA_NO_BATHROOM'])

    def test_the_guest_wc(self):
        model = copy.deepcopy(self.case['model'])
        for rid in ('guest_wc', 'family_bath'):
            room(model, 'ground', rid)['role'] = 'storage'
        blocking, _ = VP.check(model, self.case['brief'], self.case['requirements'])
        self.assertIn('VILLA_GUEST_WC_MISSING', codes(blocking), 'the confirmed bathroom count includes it')
        blocking, advisory = VP.check(model, 'villa', [])
        self.assertNotIn('VILLA_GUEST_WC_MISSING', codes(blocking))
        self.assertIn('VILLA_GUEST_WC_MISSING', codes(advisory))
        blocking, _ = VP.check(model, 'فيلا مع دورة مياه للضيوف', [])
        self.assertIn('VILLA_GUEST_WC_MISSING', codes(blocking), 'the brief asked for it')

    def test_an_ensuite_that_opens_to_the_corridor_is_not_private(self):
        model = copy.deepcopy(self.case['model'])
        bath = room(model, 'upper', 'master_bath')
        bath['doors'].append({'id': 'mb_corridor', 'edge': 'S', 'offset': 2.0, 'width': .8, 'height': 2.1, 'material': 'wood'})
        room(model, 'upper', 'corridor_n')['doors'].append(
            {'id': 'cn_mb', 'edge': 'N', 'offset': 2.0, 'width': .8, 'height': 2.1, 'material': 'wood'})
        self.assertEqual(VP.ensuite_bedroom_count(model), 0)
        result = self.check(model)
        self.assertEqual([i['requirement_id'] for i in result['issues'] if i['code'] == 'REQUIREMENT_MISMATCH'],
                         ['villa-ensuite_bedroom_count-all'])

    def test_kitchen_on_an_interior_wall_and_majlis_far_from_the_entrance(self):
        door = lambda e, o: {'id': e + str(o), 'edge': e, 'offset': o, 'width': .9, 'height': 2.1, 'material': 'wood'}
        r = lambda rid, role, rect, doors: {'id': rid, 'role': role, 'name': rid, 'rect': rect, 'doors': doors,
                                            'windows': [], 'walls': 'all', 'unit_id': 'villa'}
        rooms = [r('hall', 'entrance', [0, 0, 10, 2], [door('W', 1), door('S', 5), door('E', 1)]),
                 r('kitchen', 'kitchen', [3, 2, 4, 4], [door('N', 2)]),
                 r('west', 'living', [0, 2, 3, 10], []), r('east', 'living', [7, 2, 3, 10], []),
                 r('south', 'dining', [3, 6, 4, 6], [door('N', 2)]),
                 r('majlis', 'majlis', [10, 0, 5, 12], [door('W', 11)]),
                 r('wc', 'bathroom', [0, 12, 3, 2], [door('N', 1)])]
        rooms[1]['doors'] = [door('N', 2)]
        b = {'site': {'w': 15, 'd': 14}, 'levels': [{'index': 0, 'template': 'g'}], 'floors': {'g': {'rooms': rooms}}}
        blocking, advisory = VP.check(b, 'فيلا', [])
        self.assertIn('VILLA_KITCHEN_INTERIOR', codes(advisory))
        self.assertIn('VILLA_MAJLIS_FAR', codes(advisory))
        blocking, _ = VP.check(b, 'فيلا، المطبخ على جدار خارجي، والمجلس قريب من المدخل', [])
        self.assertEqual(codes(blocking), ['VILLA_KITCHEN_INTERIOR', 'VILLA_MAJLIS_FAR'])
        # With plot rules the plot check reports the majlis (PLOT_ZONING_MAJLIS_FAR) instead.
        self.assertNotIn('VILLA_MAJLIS_FAR', codes(sum(VP.check(b, 'فيلا', [], plot={'any': 1}), [])))

    def test_aggregate_names_and_roles(self):
        for name in ('غرف النوم', 'الغُرف', 'الحمامات', 'دورات المياه', 'منطقة النوم', 'جناح غرف النوم', 'Bedrooms',
                     'sleeping area'):
            with self.subTest(name=name):
                self.assertTrue(VP.aggregate({'name': name, 'role': 'bedroom'}))
        for name in ('غرفة النوم الرئيسية', 'غرفة نوم ٢', 'حمام مشترك', 'دورة مياه الضيوف', 'مجلس الرجال',
                     'صالة الأسرة', 'Master bedroom', 'جناح الضيوف'):
            with self.subTest(name=name):
                self.assertFalse(VP.aggregate({'name': name, 'role': 'bedroom'}))
        self.assertTrue(VP.aggregate({'name': 'x', 'role': 'bedrooms'}))
        self.assertTrue(VP.aggregate({'name': 'x', 'role': 'غرف نوم'}))


class Compatibility(unittest.TestCase):
    def test_apartment_revisions_review_as_before(self):
        case = json.loads((Path(__file__).resolve().parent / 'fixtures' / 'notes_job' / 'job_1b21c5d2.json')
                          .read_text(encoding='utf-8'))
        result = review(case['model'], case['brief'], case['requirements'])
        self.assertNotIn('dwelling_program', result['scopes'])
        self.assertNotIn('advisories', result)
        self.assertFalse([i for i in result['issues'] if i['code'].startswith('VILLA_')])

    def test_the_metric_is_unknown_before_openings(self):
        model = copy.deepcopy(fixture('villa_livable')['model'])
        for floor in model['floors'].values():
            for r in floor['rooms']:
                r['doors'] = []
        self.assertIsNone(VP.ensuite_bedroom_count(model))


if __name__ == '__main__':
    unittest.main()
