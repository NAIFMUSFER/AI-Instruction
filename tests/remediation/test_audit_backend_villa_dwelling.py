"""A signed-in villa brief is one dwelling, not an apartment building.

Replays the layout saved before the failed production repair of the «فيلا
عائلية» starter (villa_failed_layout_fixture.py). It had
three causes of PLAN_LAYOUT_INCOMPLETE: Arabic roles left unknown, apartment
shared-corridor rules applied to a single dwelling, and a genuinely
misaligned stair core. Only the last one is a design error. Every provider
call here is a fake; no key or network is used.
"""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import acs_residential_access as A
import acs_residential_generation as R
import acs_understand as U
import acs_workspace_service as S
from acs_plan_bridge import existing_geometry_verifier
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError
from acs_provider_budget import consume, limited
from test_workspace_recovery import apartment_fixture
from villa_failed_layout_fixture import layout as saved

BRIEF = ('أبغى فيلا عائلية في جدة. عرض الأرض ١٨ متر وعمق الأرض ٢٨ متر. عدد الأدوار ٢ شاملة الأرضي.\n'
         'أبغى مجلس الضيوف قريب من المدخل، وصالة الأسرة تطل على الحديقة. خلّ غرف النوم في الدور '
         'العلوي والمطبخ قريب من غرفة الطعام.')
APARTMENT_BRIEF = 'عمارة سكنية من دورين، في الدور العلوي شقة.'
CANONICAL = {'bedroom', 'living', 'kitchen', 'bathroom', 'majlis', 'corridor',
             'entrance', 'lobby', 'stairs', 'elevator'}
GROUND_STAIRS = [0, 20, 4.2, 6]


def requirements():
    """What brief-review.mjs extracts from the starter, after confirmation."""
    rows = [('site_width_m', 18, 'عرض الأرض ١٨ متر'), ('site_depth_m', 28, 'عمق الأرض ٢٨ متر'),
            ('level_count', 2, 'عدد الأدوار ٢')]
    out = []
    for metric, expected, evidence in rows:
        start = BRIEF.index(evidence)
        out.append({'id': 'text-%d-%s' % (start, metric), 'metric': metric, 'expected': expected,
                    'source': 'requested', 'source_id': 'brief:text', 'evidence': evidence,
                    'source_span': {'start': start, 'end': start + len(evidence)}, 'confirmed': True})
    return out


def room(building, template, rid):
    return next(r for r in building['floors'][template]['rooms'] if r['id'] == rid)


def aligned_floors():
    """A repair that copies the ground stair rectangle and keeps every upper
    room over built space. Roles stay Arabic, as the provider writes them."""
    floors = copy.deepcopy(saved()['floors'])
    moves = {'stairs_upper': GROUND_STAIRS, 'uf_corridor': [0, 5, 15, 2.2], 'bedroom_2': [7.2, 0, 3.6, 5],
             'bedroom_3': [4.2, 7.2, 5.4, 5], 'upper_living': [9.6, 7.2, 5.4, 8.8]}
    for r in floors['villa_upper']['rooms']:
        r['rect'] = moves.get(r['id'], r['rect'])
    floors['villa_upper']['rooms'].append({
        'id': 'upper_hall', 'name': 'ممر الدرج', 'role': 'ممر', 'rect': [0, 7.2, 4.2, 12.8],
        'walls': ['north', 'east', 'south', 'west'], 'wall_h': 3, 'unit_id': 'villa_upper_unit'})
    return floors


class Provider:
    """Fake provider: answers repair and detail stages and spends the budget."""
    def __init__(self, *repairs):
        self.repairs = list(repairs)
        self.calls = []

    def __call__(self, text, **kwargs):
        self.calls.append((kwargs['stage'], json.loads(text), kwargs['system_override']))
        consume()
        if kwargs['stage'] == 'repair':
            return json.dumps({'floors': self.repairs.pop(0)}, ensure_ascii=False)
        context = json.loads(text)
        rooms = []
        for rid in context['requested_ids']:
            w, d = next(r for r in context['all_rooms'] if r['id'] == rid)['rect'][2:]
            rooms.append({'id': rid, 'windows': [],
                          'doors': [{'id': rid + '_door', 'edge': 'N', 'offset': w / 2, 'width': .9,
                                     'height': 2.1, 'material': 'wood'}],
                          'points': [{'id': rid + '_light', 'type': 'light', 'x': w / 2, 'z': d / 2}]})
        return json.dumps({'rooms': rooms})


def first_repair_request(building, brief=BRIEF, rows=None):
    """Run prepare_layout up to its first repair call and return that request."""
    seen = []
    def refuse(text, **kwargs):
        seen.append((json.loads(text), kwargs['system_override']))
        return '{}'
    with patch.object(U, 'call_llm', side_effect=refuse):
        with unittest.TestCase().assertRaises(PlanError) as raised:
            R.prepare_layout(building, brief, requirements() if rows is None else rows, {'used': 3, 'limit': 6})
    assert raised.exception.code == 'PLAN_LAYOUT_INCOMPLETE', raised.exception.code
    assert len(seen) == 1
    return seen[0]


class SavedVillaRegression(unittest.TestCase):
    def test_the_form_category_line_does_not_turn_a_villa_into_apartments(self):
        # Every signed-in brief ends with this line; its «عمارة» must not win.
        line = '\nنوع المشروع: سكني / عمارة / فيلا'
        self.assertEqual(A._brief_says('أبغى فيلا عائلية في جدة.' + line), A.SINGLE_DWELLING)
        self.assertEqual(A._brief_says('أبغى عمارة سكنية بشقتين في كل دور.' + line), A.APARTMENTS)
        self.assertIsNone(A._brief_says('مبنى من دورين.' + line))

    def test_only_the_core_misalignment_remains_and_it_is_stated_exactly(self):
        building = saved()
        before = copy.deepcopy(building)
        context, system = first_repair_request(building)
        self.assertEqual(building, before, 'the saved layout is not mutated')
        findings = context['findings']
        self.assertEqual([f['code'] for f in findings], ['RESIDENTIAL_CORE_MISSING'])
        core = findings[0]
        self.assertEqual(core['ground_template'], 'villa_ground')
        self.assertEqual(core['ground_cores'], [{'core_id': 'core_stairs', 'role': 'stairs', 'rect': GROUND_STAIRS}])
        self.assertEqual(core['misaligned'], [{
            'template': 'villa_upper', 'room_id': 'stairs_upper', 'core_id': 'core_stairs',
            'rect': [0, 5, 4.2, 6], 'copy_rect': GROUND_STAIRS, 'copy_core_id': 'core_stairs'}])
        self.assertEqual(core['missing'], [])
        # Snapping alone would strand the upper floor, so it is reported, not applied.
        self.assertIn('not applied', core['deterministic_alignment'])
        self.assertIn('RESIDENTIAL_ACCESS_DISCONNECTED', core['deterministic_alignment'])
        self.assertIn('stairs rect [0, 20, 4.2, 6]', system)
        self.assertIn('ONE single-family dwelling', system)
        # The upper bedroom over open ground was a real defect (the review blocks
        # it as «معلّق»); it is now carried on a covered ground porch, for free,
        # so it is no longer a finding and the repair sees the porch.
        self.assertNotIn('advisories', context)
        porch = [r for r in context['building']['floors']['villa_ground']['rooms'] if r['role'] == 'porch']
        self.assertEqual(porch, [{'id': 'villa_ground_porch_1', 'name': 'رواق مظلل', 'role': 'porch',
                                  'rect': [11.8, 0, 6.2, 5], 'walls': 'none', 'covered': True}])
        self.assertNotIn('UNSUPPORTED_UPPER_ROOM', system)

    def test_arabic_roles_are_canonical_and_villa_access_passes(self):
        building = R._canonical_room_roles(saved())
        unknown = {r['role'] for f in building['floors'].values() for r in f['rooms']} - CANONICAL
        self.assertEqual(unknown, {'غرفة طعام'}, 'dining has no canonical backend role')
        self.assertEqual(A.dwelling_kind(building, BRIEF, requirements()), A.SINGLE_DWELLING)
        self.assertEqual(A.issues(building, doors=False, dwelling=A.SINGLE_DWELLING), [])
        with A.dwelling_context(BRIEF, requirements()):
            self.assertEqual(A.issues(building, doors=False), [])

    def test_the_same_geometry_under_apartment_rules_still_needs_a_shared_corridor(self):
        building = R._canonical_room_roles(saved())
        self.assertEqual(A.dwelling_kind(building), A.APARTMENTS, 'no brief: today\'s rules')
        for brief, rows in [(None, None), (APARTMENT_BRIEF, requirements()),
                            (BRIEF, requirements() + [{'id': 'units', 'metric': 'unit_count', 'expected': 2}])]:
            with self.subTest(brief=brief, rows=rows and len(rows)):
                found = A.issues(building, doors=False, dwelling=A.dwelling_kind(building, brief, rows))
                self.assertEqual(sorted(i['room_ref'][1] for i in found),
                                 sorted(r['id'] for r in building['floors']['villa_upper']['rooms']))
                self.assertTrue(all('الممر المشترك' in i['message'] for i in found))

    def test_a_fake_aligned_repair_completes_prepare_layout(self):
        provider = Provider(aligned_floors())
        with limited(6, 3) as budget, patch.object(U, 'call_llm', side_effect=provider):
            result = R.prepare_layout(saved(), BRIEF, requirements(), budget)
        self.assertEqual([c[0] for c in provider.calls], ['repair'])
        self.assertEqual(budget['used'], 4)
        self.assertEqual(room(result, 'villa_upper', 'stairs_upper')['rect'], GROUND_STAIRS)
        self.assertEqual(room(result, 'villa_upper', 'upper_hall')['role'], 'corridor')
        self.assertEqual(room(result, 'villa_upper', 'upper_living')['role'], 'living')
        self.assertEqual(room(result, 'villa_upper', 'stairs_upper')['unit_id'], 'villa_upper_unit')

    def test_the_signed_in_job_resumed_from_this_layout_reaches_an_approvable_review(self):
        provider = Provider(aligned_floors())
        with patch.object(U, 'call_llm', side_effect=provider):
            out = S.generate_plan_candidate(BRIEF, requirements(), 'A', 6,
                                            resume={'kind': 'layout', 'building': saved()}, used_calls=3)
        self.assertEqual([c[0] for c in provider.calls], ['repair', 'detail', 'detail'])
        self.assertEqual(out['provider_calls'], 6)
        self.assertIn('ONE single-family dwelling', provider.calls[1][2], 'openings policy knows it is a villa')
        verdicts = {}
        for brief in (BRIEF, APARTMENT_BRIEF):
            ws = PlanLockWorkspace(existing_geometry_verifier)
            rev = ws.propose(out['building'], brief=brief, requirements=requirements(),
                             expected_head=None, note='villa replay')
            verdicts[brief] = ws.review(rev.id)
        self.assertTrue(verdicts[BRIEF]['can_approve'], verdicts[BRIEF]['issues'][:3])
        self.assertEqual(verdicts[BRIEF]['scopes']['topology'], 'PASS')
        self.assertEqual(verdicts[APARTMENT_BRIEF]['scopes']['topology'], 'FAIL')


def snappable():
    """Upper stair off-axis, its ground rectangle free and next to circulation."""
    building = saved()
    upper = building['floors']['villa_upper']['rooms']
    room(building, 'villa_upper', 'stairs_upper')['rect'] = [13.8, 13.2, 4.2, 6]
    upper.append({'id': 'upper_hall', 'name': 'ممر الدرج', 'role': 'corridor', 'rect': [0, 7.2, 7.2, 12.8],
                  'walls': ['N', 'S', 'E', 'W'], 'unit_id': 'villa_upper_unit'})
    return building


class DeterministicStairAlignment(unittest.TestCase):
    def test_free_connected_ground_rectangle_is_copied_without_a_paid_call(self):
        building = snappable()
        with limited(6, 3) as budget, patch.object(U, 'call_llm', side_effect=AssertionError('no paid call')):
            result = R.prepare_layout(building, BRIEF, requirements(), budget)
        self.assertEqual(budget['used'], 3)
        self.assertEqual(room(result, 'villa_upper', 'stairs_upper')['rect'], GROUND_STAIRS)
        self.assertEqual(room(building, 'villa_upper', 'stairs_upper')['rect'], [13.8, 13.2, 4.2, 6])
        self.assertTrue(any('مستطيل درج الدور الأرضي' in a for a in result['meta']['assumptions']))

    def test_an_overlapping_copy_is_refused_and_reported(self):
        building = snappable()
        room(building, 'villa_upper', 'upper_hall')['rect'] = [0, 7.2, 7.2, 14]
        context, _ = first_repair_request(building)
        core = context['findings'][-1]
        self.assertEqual(core['code'], 'RESIDENTIAL_CORE_MISSING')
        self.assertEqual(core['deterministic_alignment'],
                         'not applied: the ground stair rectangle would overlap upper_hall')
        self.assertEqual(room(context['building'], 'villa_upper', 'stairs_upper')['rect'], [13.8, 13.2, 4.2, 6])

    def test_different_stair_sizes_or_core_ids_are_left_alone(self):
        for change, reason in [({'rect': [13.8, 13.2, 4.2, 5.8]}, 'differ in width or depth'),
                               ({'core_id': 'other_core'}, 'do not share one core_id')]:
            building = snappable()
            room(building, 'villa_upper', 'stairs_upper').update(change)
            with self.subTest(reason=reason):
                context, _ = first_repair_request(building)
                core = next(f for f in context['findings'] if f['code'] == 'RESIDENTIAL_CORE_MISSING')
                self.assertIn(reason, core['deterministic_alignment'])

    def test_apartment_buildings_never_snap(self):
        context, system = first_repair_request(snappable(), APARTMENT_BRIEF)
        core = next(f for f in context['findings'] if f['code'] == 'RESIDENTIAL_CORE_MISSING')
        self.assertNotIn('deterministic_alignment', core)
        self.assertNotIn('single-family', system)
        self.assertIn('stairs rect [0, 20, 4.2, 6]', system, 'the exact rectangle is stated for apartments too')


def with_disconnected_kitchen():
    building = saved()
    room(building, 'villa_ground', 'kitchen')['rect'] = [11, 22.5, 7, 5]
    return building


class SecondRepair(unittest.TestCase):
    def test_an_improving_first_repair_gets_one_more_call_when_the_budget_covers_openings(self):
        provider = Provider(saved()['floors'], aligned_floors())
        with limited(8, 3) as budget, patch.object(U, 'call_llm', side_effect=provider):
            result = R.prepare_layout(with_disconnected_kitchen(), BRIEF, requirements(), budget)
        self.assertEqual([c[0] for c in provider.calls], ['repair', 'repair'])
        self.assertEqual(budget['used'], 5)
        self.assertEqual(len(provider.calls[0][1]['findings']), 2)
        self.assertEqual([f['code'] for f in provider.calls[1][1]['findings']], ['RESIDENTIAL_CORE_MISSING'])
        self.assertEqual(room(result, 'villa_upper', 'stairs_upper')['rect'], GROUND_STAIRS)

    def test_no_second_call_when_it_would_starve_the_openings_stage(self):
        # 6 calls, 4 used after the first repair: the two opening groups need both.
        provider = Provider(saved()['floors'], aligned_floors())
        with limited(6, 3) as budget, patch.object(U, 'call_llm', side_effect=provider):
            with self.assertRaises(PlanError) as raised:
                R.prepare_layout(with_disconnected_kitchen(), BRIEF, requirements(), budget)
        self.assertEqual(raised.exception.code, 'PLAN_LAYOUT_INCOMPLETE')
        self.assertEqual(budget['used'], 4)
        self.assertEqual(len(provider.calls), 1)

    def test_no_second_call_without_progress(self):
        provider = Provider(saved()['floors'], aligned_floors())
        with limited(12, 3) as budget, patch.object(U, 'call_llm', side_effect=provider):
            with self.assertRaises(PlanError) as raised:
                R.prepare_layout(saved(), BRIEF, requirements(), budget)
        self.assertEqual(raised.exception.code, 'PLAN_LAYOUT_INCOMPLETE')
        self.assertEqual((budget['used'], len(provider.calls)), (4, 1))


class ArabicRoles(unittest.TestCase):
    def test_production_and_common_arabic_roles_map_to_canonical_roles(self):
        expected = {
            'غرفة نوم رئيسية': 'bedroom', 'غرفة النوم الرئيسية': 'bedroom', 'غرفة نوم الأطفال': 'bedroom',
            'حمام رئيسي': 'bathroom', 'حمام رئيسى': 'bathroom', 'حمام مشترك': 'bathroom',
            'دورة مياه الضيوف': 'bathroom', 'صالة أسرة': 'living', 'صالة الأسرة': 'living',
            'صالة علوية': 'living', 'الصالة العلوية': 'living', 'صالة عائلية': 'living',
            'مجلس ضيوف': 'majlis', 'مجلس الضيوف': 'majlis', 'مجلس رجال': 'majlis',
            'المطبخ': 'kitchen', 'الممر': 'corridor', 'موزع': 'corridor', 'المدخل الرئيسي': 'entrance',
            'البهو': 'lobby', 'الدرج': 'stairs', 'السلم': 'stairs', 'المصعد': 'elevator',
            ' غُرفة  نوم ': 'bedroom'}
        for role, canonical in expected.items():
            with self.subTest(role=role):
                self.assertEqual(R._canonical_role(role), canonical)
                self.assertIn(canonical, CANONICAL)

    def test_dining_and_unknown_roles_stay_unknown(self):
        # The backend residential contract has no dining role (acs_validate and
        # the repair schema list ten roles), so dining is not invented here.
        self.assertNotIn('dining', R.REPAIR_SYSTEM)
        for role in ('غرفة طعام', 'غرفة الطعام', 'مقلط', 'خزانة غرفة نوم', 'بيت الدرج',
                     'درج خارجي مقترح', 'غرفة', 'ال', ''):
            with self.subTest(role=role):
                self.assertIsNone(R._canonical_role(role))

    def test_canonicalization_is_idempotent_on_the_saved_villa(self):
        once = R._canonical_room_roles(saved())
        self.assertEqual(R._canonical_room_roles(once), once)
        self.assertEqual({r['id']: r['role'] for f in once['floors'].values() for r in f['rooms']
                          if r['role'] not in CANONICAL}, {'dining': 'غرفة طعام'})


class DwellingDetection(unittest.TestCase):
    def test_apartment_evidence_always_wins(self):
        villa = R._canonical_room_roles(saved())
        two_units = copy.deepcopy(villa)
        room(two_units, 'villa_upper', 'bedroom_3')['unit_id'] = 'second_unit'
        repeated = copy.deepcopy(villa)
        repeated['levels'].append({'id': 'L2', 'index': 2, 'template': 'villa_upper'})
        for building, brief, rows in [
                (villa, 'فيلا فيها شقة للإيجار', []),
                (villa, BRIEF, [{'metric': 'unit_count', 'expected': 2}]),
                (villa, BRIEF, [{'metric': 'unit_count_per_level', 'expected': 1}]),
                (two_units, BRIEF, []), (repeated, BRIEF, []),
                (villa, 'بيت الدرج على السطح', [])]:
            with self.subTest(brief=brief, rows=rows):
                self.assertEqual(A.dwelling_kind(building, brief, rows), A.APARTMENTS)

    def test_single_dwelling_evidence(self):
        villa = R._canonical_room_roles(saved())
        for brief, rows in [(BRIEF, []), ('بيت دورين في الرياض', []), ('my house', []),
                            ('سكني', [{'metric': 'unit_count', 'expected': 1}])]:
            with self.subTest(brief=brief):
                self.assertEqual(A.dwelling_kind(villa, brief, rows), A.SINGLE_DWELLING)
        whole = copy.deepcopy(villa)
        for r in whole['floors']['villa_ground']['rooms']:
            r['unit_id'] = 'villa_upper_unit'
        self.assertEqual(A.dwelling_kind(whole), A.SINGLE_DWELLING, 'one unit_id spanning the whole house')
        self.assertEqual(A.issues(whole, doors=False), [])

    def test_the_apartment_fixture_keeps_apartment_rules(self):
        model, rows = apartment_fixture()
        self.assertEqual(A.dwelling_kind(model, 'عمارة', rows), A.APARTMENTS)
        self.assertEqual(A.dwelling_kind(model), A.APARTMENTS)
        self.assertEqual(A.issues(model), [])


if __name__ == '__main__':
    unittest.main()
