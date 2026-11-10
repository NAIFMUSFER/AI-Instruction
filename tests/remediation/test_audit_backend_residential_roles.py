"""الأدوار العربية الصريحة تمر بعقود العدّ والنواة والوصول نفسها."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_residential_generation as R
import acs_residential_access as A
import acs_understand as U
import acs_workspace_service as S
from acs_plan_review import PlanError, _geometry, _program
from test_workspace_recovery import apartment_fixture
from test_audit_backend_corpus import corpus

ARABIC = {'bedroom': 'غرفة نوم', 'bathroom': 'دورة مياه', 'living': 'صالة',
          'kitchen': 'مطبخ', 'majlis': 'مجلس', 'corridor': 'ممر',
          'entrance': 'مدخل', 'stairs': 'درج داخلي', 'elevator': 'مصعد'}


def arabic(model, bedroom='غرفة نوم'):
    model = copy.deepcopy(model)
    for floor in model['floors'].values():
        for room in floor['rooms']:
            room['role'] = bedroom if room['role'] == 'bedroom' else ARABIC.get(room['role'], room['role'])
    return model


def simple(connected=True, translated=False):
    model = {'site': {'w': 20, 'd': 25}, 'floor_height': 3.2, 'wall_h': 3, 'wall_t': .2,
             'levels': [{'index': 0, 'template': 'g'}], 'floors': {'g': {'rooms': [
                 {'id': 'entry', 'role': 'entrance', 'name': 'المدخل', 'rect': [0, 0, 2, 2]},
                 {'id': 'hall', 'role': 'corridor', 'name': 'الممر', 'unit_id': 'one', 'rect': [2, 0, 2, 2]},
                 {'id': 'bed', 'role': 'bedroom', 'name': 'غرفة النوم', 'unit_id': 'one',
                  'rect': [4 if connected else 7, 0, 2, 2]}]}}}
    return arabic(model) if translated else model


def bedroom_requirement(count=1):
    return [{'id': 'beds', 'metric': 'room_count', 'role': 'bedroom', 'expected': count,
             'source': 'inferred', 'confirmed': True}]


def assert_sound_translation(test):
    original, requirements = apartment_fixture()
    for floor in original['floors'].values():
        for room in floor['rooms']:
            room['name'] = ARABIC.get(room['role'], room['name'])
    for alias in ('غرفة نوم', 'غرف نوم'):
        candidate = arabic(original, alias)
        before = copy.deepcopy(candidate)
        with patch.object(U, 'call_llm') as paid:
            result = R.prepare_layout(candidate, 'عمارة', requirements, {'used': 6, 'limit': 6})
            paid.assert_not_called()
        test.assertEqual(result, original)
        test.assertEqual(candidate, before)
        test.assertEqual(_program(result, 'عمارة', requirements), [])
        test.assertEqual(A.issues(result, doors=False), [])
        R.check_rooms(result)


class ResidentialRoles(unittest.TestCase):
    def test_sound_arabic_cores_access_and_counts_pass_without_paid_repair(self):
        assert_sound_translation(self)

    def test_arabic_bedroom_does_not_bypass_disconnected_access(self):
        model = simple(connected=False, translated=True)
        before = copy.deepcopy(model)
        with patch.object(U, 'call_llm', return_value=json.dumps({'floors': model['floors']})) as paid:
            with self.assertRaises(PlanError) as raised:
                R.prepare_layout(model, 'فيلا', [], {'used': 2, 'limit': 6})
        self.assertEqual(raised.exception.code, 'PLAN_LAYOUT_INCOMPLETE')
        findings = json.loads(paid.call_args.args[0])['findings']
        self.assertIn('RESIDENTIAL_ACCESS_DISCONNECTED', [i['code'] for i in findings])
        self.assertEqual(model, before)

    def test_arabic_repair_response_is_normalized_before_program_and_access(self):
        initial = simple(connected=False)
        corrected = simple(connected=True, translated=True)
        with patch.object(U, 'call_llm', return_value=json.dumps({'floors': corrected['floors']})) as paid:
            result = R.prepare_layout(initial, 'فيلا', bedroom_requirement(), {'used': 2, 'limit': 6})
        self.assertEqual(paid.call_count, 1)
        self.assertEqual(result, simple())
        self.assertEqual(A.issues(result, doors=False), [])
        self.assertEqual(_program(result, 'فيلا', bedroom_requirement()), [])

    def test_repaired_arabic_bedroom_cannot_hide_a_remaining_access_defect(self):
        initial = simple(connected=False)
        still_bad = simple(connected=False, translated=True)
        with patch.object(U, 'call_llm', return_value=json.dumps({'floors': still_bad['floors']})):
            with self.assertRaises(PlanError) as raised:
                R.prepare_layout(initial, 'فيلا', [], {'used': 2, 'limit': 6})
        self.assertEqual(raised.exception.code, 'PLAN_LAYOUT_INCOMPLETE')

    def test_confirmed_total_counts_template_instances_after_normalization(self):
        model, _ = apartment_fixture()
        model = arabic(model)
        requirements = bedroom_requirement(4)  # The shared template has 8 actual instances.
        with patch.object(U, 'call_llm', return_value=json.dumps({'floors': model['floors']})) as paid:
            with self.assertRaises(PlanError):
                R.prepare_layout(model, 'عمارة', requirements, {'used': 2, 'limit': 6})
        findings = json.loads(paid.call_args.args[0])['findings']
        self.assertEqual(findings, [{'code': 'REQUIREMENT_MISMATCH', 'requirement_id': 'beds', 'severity': 'error'}])

    def test_a_missing_or_misaligned_core_stays_rejected(self):
        for kind in ('missing', 'misaligned'):
            model, rows = apartment_fixture()
            model = arabic(model)
            model['floors']['upper'] = copy.deepcopy(model['floors']['residential_2'])
            model['levels'][1]['template'] = 'upper'
            rooms = model['floors']['upper']['rooms']
            if kind == 'missing':
                model['floors']['upper']['rooms'] = [r for r in rooms if r['role'] != 'درج داخلي']
            else:
                next(r for r in rooms if r['role'] == 'درج داخلي')['rect'][0] = .25
            with self.subTest(kind=kind), patch.object(U, 'call_llm', return_value=json.dumps({'floors': model['floors']})) as paid:
                with self.assertRaises(PlanError):
                    R.prepare_layout(model, 'عمارة', rows, {'used': 2, 'limit': 6})
                self.assertIn('RESIDENTIAL_CORE_MISSING', [i['code'] for i in json.loads(paid.call_args.args[0])['findings']])

    def test_only_exact_explicit_roles_change_unknowns_and_names_do_not(self):
        for unknown in ('قبو', 'بدون درج', 'درج خارجي مقترح', 'خزانة غرفة نوم',
                        'مقلط', ' custom role ', '', None, 7, {'role': 'غرفة نوم'}):
            model = simple()
            room = model['floors']['g']['rooms'][-1]
            room.update(role=unknown, name='غرفة نوم', brief='درج داخلي')
            before = copy.deepcopy(model)
            with self.subTest(role=unknown):
                self.assertEqual(R._canonical_room_roles(model), before)
                self.assertEqual(model, before)
        known = simple(translated=True)
        known['floors']['g']['rooms'][-1]['role'] = ' غرفة نوم '
        before = copy.deepcopy(known)
        self.assertEqual(R._canonical_room_roles(known), simple())
        self.assertEqual(known, before)

    def test_normalization_is_idempotent_and_changes_only_roles_over_real_corpus(self):
        models = list(corpus())
        self.assertGreaterEqual(len(models), 165)
        for name, model in models:
            with self.subTest(model=name):
                before = copy.deepcopy(model)
                result = R._canonical_room_roles(model)
                self.assertEqual(model, before)
                self.assertEqual(R._canonical_room_roles(result), result)
                restored = copy.deepcopy(result)
                for template, floor in before['floors'].items():
                    for index, room in enumerate(floor.get('rooms', [])):
                        if 'role' in room:
                            restored['floors'][template]['rooms'][index]['role'] = copy.deepcopy(room['role'])
                self.assertEqual(restored, before)
                self.assertEqual(_geometry(result), _geometry(model))

    def test_mutant_disabling_normalization_is_detected(self):
        with patch.object(R, '_canonical_room_roles', side_effect=lambda value: value):
            with self.assertRaises((AssertionError, PlanError)):
                assert_sound_translation(self)

    def test_mutant_skipping_only_repair_normalization_is_detected(self):
        normalize = R._canonical_room_roles
        calls = []
        def skip_repair(value):
            calls.append(None)
            return normalize(value) if len(calls) == 1 else value
        with patch.object(R, '_canonical_room_roles', side_effect=skip_repair):
            with self.assertRaises(AssertionError):
                self.test_repaired_arabic_bedroom_cannot_hide_a_remaining_access_defect()

    def test_mutant_guessing_an_unknown_role_is_detected(self):
        model = simple()
        model['floors']['g']['rooms'][-1]['role'] = 'قبو'
        before = copy.deepcopy(model)
        with patch.dict(R._ROLE_ALIASES, {'قبو': 'parking'}):
            with self.assertRaises(AssertionError):
                self.assertEqual(R._canonical_room_roles(model), before)

    def test_resumed_valid_arabic_details_do_not_spend_another_call(self):
        model, requirements = apartment_fixture()
        saved = arabic(model)
        before = copy.deepcopy(saved)
        with patch.object(U, 'call_llm', side_effect=AssertionError('Completed details must not be regenerated')) as paid:
            result = S.generate_plan_candidate('عمارة', requirements, 'A', 6,
                resume={'kind': 'details', 'building': saved, 'done': ['residential_2:0']}, used_calls=3)
            paid.assert_not_called()
        self.assertEqual(result['building'], model)
        self.assertEqual(result['provider_calls'], 3)
        self.assertEqual(saved, before)

    def test_resumed_details_are_regenerated_when_layout_geometry_changes(self):
        from acs_provider_budget import consume
        model, requirements = apartment_fixture()
        saved = arabic(model)
        bedroom = next(r for r in saved['floors']['residential_2']['rooms'] if r['role'] == 'غرفة نوم')
        bedroom['rect'][:2] = [8, 4]  # Overlap the common corridor, requiring a real layout repair.
        before = copy.deepcopy(saved)
        stages = []
        def provider(text, **kwargs):
            stages.append(kwargs['stage']); consume()
            if kwargs['stage'] == 'repair':
                return json.dumps({'floors': model['floors']})
            self.assertEqual(kwargs['stage'], 'detail')
            return json.dumps({'rooms': [{k: r[k] for k in ('id', 'doors', 'windows', 'points')}
                              for r in model['floors']['residential_2']['rooms']]})
        with patch.object(U, 'call_llm', side_effect=provider):
            result = S.generate_plan_candidate('عمارة', requirements, 'A', 6,
                resume={'kind': 'details', 'building': saved, 'done': ['residential_2:0']}, used_calls=3)
        self.assertEqual(stages, ['repair', 'detail'])
        self.assertEqual(result['provider_calls'], 5)
        self.assertEqual(result['building'], model)
        self.assertEqual(saved, before)

    def test_mutant_skipping_resume_comparison_normalization_is_detected(self):
        normalize = R._canonical_room_roles
        calls = []
        def skip_comparison(value):
            calls.append(None)
            return value if len(calls) == 1 else normalize(value)
        with patch.object(R, '_canonical_room_roles', side_effect=skip_comparison):
            with self.assertRaises(AssertionError):
                self.test_resumed_valid_arabic_details_do_not_spend_another_call()


if __name__ == '__main__':
    unittest.main()
