"""Plot rules: buildable envelope, parking and Saudi residential basics, offline.

The failing fixture is the reconstructed 20 × 25 m Riyadh building from the
architect review (100 % coverage, windows on the neighbours' lines, no
parking, lobby and its street door repeated on the upper floors, bedrooms at
the flat door). No provider or network is used: the generation test stubs the
model and checks what the model is told.
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

import acs_plot_rules as P
import acs_plot_layout as L
import acs_understand as U
import acs_workspace_service as S
from acs_plan_review import PlanError, _geometry, _program
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_bridge import existing_geometry_verifier, admit_bound_chat_edit_candidate
from acs_provider_budget import consume
from acs_residential_access import detail_issues

FIXTURES = ROOT / 'tests' / 'fixtures' / 'plot_rules'
REVIEW_MODEL = json.loads((FIXTURES / 'riyadh_20x25_review_model.json').read_text(encoding='utf-8'))
REVIEW_REQUIREMENTS = json.loads((FIXTURES / 'riyadh_20x25_review_requirements.json').read_text(encoding='utf-8'))
# The brief of the reviewed generation (offsets match the requirement spans).
REVIEW_BRIEF = ('أبغى عمارة سكنية في الرياض. عرض الأرض ٢٠ متر وعمق الأرض ٢٥ متر. عدد الأدوار ٣ شاملة الأرضي.\n'
                'أبغى شقتين في كل دور، ومدخل كل شقة من بسطة الدرج المشترك. خلّ غرف النوم بعيدة عن مدخل الضيوف.\n\n'
                'نوع المشروع: سكني / عمارة / فيلا\nإجمالي الشقق: 6\nعدد الشقق في كل دور: 2\nإجمالي غرف النوم: 12\n'
                'غرف النوم في كل شقة: 2\nإجمالي الصالات: 6\nالصالات في كل شقة: 1\nإجمالي المطابخ: 6\n'
                'المطابخ في كل شقة: 1\nإجمالي دورات المياه: 12\nدورات المياه في كل شقة: 2\nإجمالي المجالس: 6\n'
                'المجالس في كل شقة: 1\nالخيار المختار: خصوصية الضيوف؛ لكل شقة 2 غرف نوم وصالة ومطبخ و2 دورات مياه و1 مجلس مستقل.\n'
                'توزيع الشقق من الأرضي إلى الأعلى: 2، 2، 2.\nالمدينة: غير محددة؛ جهة الشارع: لا أعرف الآن.')
NO_PARKING = {'streets': ['N'], 'parking': {'placement': 'none'}}


def requirement(rid, metric, expected, role=None):
    row = {'id': rid, 'metric': metric, 'expected': expected, 'confirmed': True, 'source': 'inferred'}
    if role:
        row['role'] = role
    return row


def program(width=20, depth=25, levels=3, units=6, per_level=None, beds=2, baths=2, majlis=1):
    rows = [requirement('w', 'site_width_m', width), requirement('d', 'site_depth_m', depth),
            requirement('l', 'level_count', levels), requirement('u', 'unit_count', units)]
    if per_level is not None:
        rows.append(requirement('pl', 'unit_count_per_level', per_level))
    for role, n in (('bedroom', beds), ('living', 1), ('kitchen', 1), ('bathroom', baths), ('majlis', majlis)):
        rows += [requirement('t-' + role, 'room_count', n * units, role),
                 requirement('u-' + role, 'room_count_per_unit', n, role)]
    return rows


def codes(findings):
    return {f['code'] for f in findings}


class Envelope(unittest.TestCase):
    def test_defaults_are_labelled_assumptions_with_the_cited_clause(self):
        rules = P.resolve(NO_PARKING, 'عمارة سكنية', program(), 'C')
        self.assertEqual(rules['setbacks_m'], {'N': 3.0, 'E': 2.0, 'S': 2.0, 'W': 2.0})
        self.assertEqual(rules['setback_sources'], {s: 'default' for s in P.SIDES})
        self.assertEqual(rules['envelope'], [2.0, 3.0, 16.0, 20.0])
        self.assertEqual(rules['max_coverage'], 0.65)
        self.assertEqual(rules['source']['url'], P.MOMAH_URL)
        text = '\n'.join(rules['assumptions'])
        self.assertIn('افتراض: ارتداد جانبي (الغرب) 2 م', text)
        self.assertIn('§4-2-4 (4)', text)
        self.assertIn('عدّله حسب اشتراطات أمانة منطقتك', text)
        self.assertIn('عرض الشارع 15 م لأنه غير محدد', text)

    def test_unknown_street_side_is_an_assumed_north_not_a_silent_default(self):
        rules = P.resolve({'parking': {'placement': 'none'}}, 'عمارة', program(), 'C')
        self.assertEqual((rules['streets'], rules['street_source']), (['N'], 'assumed'))
        self.assertTrue(any('غير محددة' in a and 'الشمال' in a for a in rules['assumptions']))

    def test_street_width_sets_the_front_setback_and_tall_buildings_widen_side_setbacks(self):
        rules = P.resolve({'streets': ['S'], 'street_width_m': 20, 'parking': {'placement': 'none'}},
                          'عمارة', program(levels=6, units=12), 'C')
        self.assertEqual(rules['setbacks_m']['S'], 4.0)            # 20 / 5
        self.assertEqual(rules['setbacks_m']['N'], 3.0)            # neighbour, more than five floors
        villa = P.resolve({'streets': ['N'], 'street_width_m': 30, 'parking': {'placement': 'none'}},
                          'فيلا سكنية', program(levels=2, units=1), None)
        self.assertEqual((villa['dwelling'], villa['setbacks_m']['N'], villa['setbacks_m']['E']), ('villa', 6.0, 1.5))
        self.assertEqual(villa['max_coverage'], 0.75)

    def test_corner_plot_and_user_values_override_defaults(self):
        rules = P.resolve({'streets': ['N', 'E'], 'setbacks_m': {'W': 0, 'S': 1.5}, 'max_coverage': 0.7,
                           'parking': {'placement': 'none'}}, 'عمارة', program(), 'C')
        self.assertEqual(rules['setbacks_m'], {'N': 3.0, 'E': 3.0, 'S': 1.5, 'W': 0.0})
        self.assertEqual(rules['setback_sources']['W'], 'user')
        self.assertEqual(rules['envelope'], [0.0, 3.0, 17.0, 20.5])
        self.assertEqual(rules['coverage_source'], 'user')

    def test_coverage_trims_the_rear_of_a_large_plot(self):
        rules = P.resolve(NO_PARKING, 'عمارة', program(width=30, depth=40), 'C')
        x, z, w, d = rules['envelope']
        self.assertEqual((x, z, w), (2.0, 3.0, 26.0))
        self.assertLessEqual(w * d, 0.65 * 30 * 40 + 1e-6)
        self.assertTrue(any('قُصّت' in a for a in rules['assumptions']))

    def test_front_setback_parking_deepens_the_front_and_must_fit(self):
        rules = P.resolve({'streets': ['N'], 'parking': {'placement': 'front_setback'}}, 'عمارة',
                          program(levels=2, units=4, per_level=2), 'C')
        self.assertEqual(rules['envelope'][1], 5.5)
        self.assertEqual(rules['parking']['required'], 6)                      # ceil(1.5 × 4)
        with self.assertRaises(PlanError) as caught:
            P.resolve({'streets': ['N'], 'parking': {'placement': 'front_setback'}}, 'عمارة', program(), 'C')
        self.assertEqual(caught.exception.code, 'PLOT_PARKING_DOES_NOT_FIT')
        self.assertIn('بيلوتي', str(caught.exception))

    def test_pilotis_needs_floors_above_and_a_consistent_program(self):
        rules = P.resolve({'streets': ['N'], 'parking': {'placement': 'pilotis'}}, 'عمارة',
                          program(levels=3, units=4, per_level=2), 'C')
        self.assertEqual(rules['parking']['capacity_estimate'], 11)
        with self.assertRaises(PlanError) as caught:
            P.resolve({'streets': ['N'], 'parking': {'placement': 'pilotis'}}, 'عمارة',
                      program(levels=3, units=6, per_level=2), 'C')
        self.assertEqual(caught.exception.code, 'PLOT_PILOTIS_PROGRAM_CONFLICT')
        with self.assertRaises(PlanError) as caught:
            P.resolve({'streets': ['N'], 'parking': {'placement': 'pilotis'}}, 'عمارة', program(levels=1, units=2), 'C')
        self.assertEqual(caught.exception.code, 'PLOT_PILOTIS_NEEDS_LEVELS')

    def test_too_small_envelopes_and_buildings_are_explained_before_any_call(self):
        with self.assertRaises(PlanError) as caught:
            P.resolve({'streets': ['N'], 'setbacks_m': {'E': 9, 'W': 9}, 'parking': {'placement': 'none'}},
                      'عمارة', program(), 'C')
        self.assertEqual(caught.exception.code, 'PLOT_ENVELOPE_EMPTY')
        with self.assertRaises(PlanError) as caught:
            P.resolve(NO_PARKING, 'عمارة\nالخيار المختار: x', program(width=12, depth=15, units=9, beds=4, baths=3), 'C')
        self.assertEqual(caught.exception.code, 'PLOT_ENVELOPE_TOO_SMALL')
        self.assertIn('م²', str(caught.exception))
        rows = program() + [requirement('bw', 'building_width_m', 18), requirement('bd', 'building_depth_m', 10)]
        with self.assertRaises(PlanError) as caught:
            P.resolve(NO_PARKING, 'عمارة', rows, 'C')
        self.assertEqual(caught.exception.code, 'PLOT_BUILDING_EXCEEDS_ENVELOPE')
        with self.assertRaises(PlanError) as caught:
            P.resolve(NO_PARKING, 'عمارة', program()[2:], 'C')
        self.assertEqual(caught.exception.code, 'PLOT_SITE_REQUIRED')

    def test_confirmed_building_size_is_anchored_on_the_street_inside_the_envelope(self):
        rows = program() + [requirement('bw', 'building_width_m', 12), requirement('bd', 'building_depth_m', 15)]
        rules = P.resolve({'streets': ['N'], 'parking': {'placement': 'none'}}, 'عمارة', rows, 'C')
        self.assertEqual(rules['envelope'], [4.0, 3.0, 12.0, 15.0])
        rules = P.resolve({'streets': ['E'], 'parking': {'placement': 'none'}}, 'عمارة', rows, 'C')
        self.assertEqual(rules['envelope'], [5.0, 5.0, 12.0, 15.0])

    def test_client_plot_blocks_are_strict(self):
        for bad in [{'colour': 'red'}, {'streets': ['N', 'E', 'S']}, {'streets': ['N', 'N']}, {'streets': ['up']},
                    {'setbacks_m': {'N': -1}}, {'setbacks_m': {'X': 1}}, {'max_coverage': 1.5},
                    {'parking': {'placement': 'roof'}}, {'parking': {'count': -1}}, {'parking': {'count': 2.5}},
                    {'street_width_m': 'wide'}, {'landing_entries': 'yes'}, []]:
            with self.subTest(bad=bad), self.assertRaises(PlanError) as caught:
                P.validate_input(bad)
            self.assertEqual(caught.exception.code, 'INVALID_PLOT_RULES')

    def test_option_estimate_is_the_card_formula(self):
        self.assertEqual(P.unit_area_estimate('C', REVIEW_REQUIREMENTS, REVIEW_BRIEF), 102)
        self.assertIsNone(P.unit_area_estimate('C', REVIEW_REQUIREMENTS, 'بلا خيار'))
        self.assertEqual(P.unit_area_estimate('A', program(beds=3, baths=3, majlis=0), 'الخيار المختار'), 108)


class FailingReviewFixture(unittest.TestCase):
    """The reviewed Riyadh building must now report B1–B4 and M1–M3."""

    def rules(self, **parking):
        rules = P.resolve({'streets': ['N'], 'parking': {'placement': 'front_setback', 'count': 6}},
                          REVIEW_BRIEF, REVIEW_REQUIREMENTS, 'C')
        rules['parking'].update(parking)
        return rules

    def test_b1_setbacks_coverage_and_windows_on_the_neighbours_lines(self):
        blocking, _ = P.check(REVIEW_MODEL, self.rules())
        self.assertTrue({'PLOT_OUTSIDE_ENVELOPE', 'PLOT_COVERAGE_EXCEEDED', 'PLOT_OPENING_ON_BOUNDARY'} <= codes(blocking))
        sides = {f['message'] for f in blocking if f['code'] == 'PLOT_OPENING_ON_BOUNDARY'}
        self.assertTrue(any('الغرب' in m for m in sides) and any('الشرق' in m for m in sides))
        coverage = next(f for f in blocking if f['code'] == 'PLOT_COVERAGE_EXCEEDED')
        self.assertIn('100٪', coverage['message'])

    def test_b2_six_flats_with_no_parking(self):
        blocking, _ = P.check(REVIEW_MODEL, self.rules())
        shortfall = next(f for f in blocking if f['code'] == 'PLOT_PARKING_SHORTFALL')
        self.assertIn('6', shortfall['message'])
        self.assertEqual(P.parking_capacity(REVIEW_MODEL, self.rules()), 0)
        _, advisory = P.check(REVIEW_MODEL, self.rules(placement='none', required=0, regulatory_default=9))
        self.assertIn('PLOT_PARKING_NOT_PROVIDED', codes(advisory))

    def test_b3_reversed_guest_family_zoning_blocks_when_the_brief_asked(self):
        blocking, _ = P.check(REVIEW_MODEL, self.rules())
        self.assertTrue({'PLOT_ZONING_MAJLIS_FAR', 'PLOT_ZONING_BEDROOM_AT_ENTRY'} <= codes(blocking))
        bedroom = next(f for f in blocking if f['code'] == 'PLOT_ZONING_BEDROOM_AT_ENTRY')
        self.assertIn('1.82', bedroom['message'])
        quiet = dict(self.rules(), zoning_requested=False)
        blocking, advisory = P.check(REVIEW_MODEL, quiet)
        self.assertFalse(codes(blocking) & {'PLOT_ZONING_MAJLIS_FAR', 'PLOT_ZONING_BEDROOM_AT_ENTRY'})
        self.assertTrue({'PLOT_ZONING_MAJLIS_FAR', 'PLOT_ZONING_BEDROOM_AT_ENTRY'} <= codes(advisory))

    def test_b4_upper_floor_street_door_opens_onto_the_void(self):
        blocking, advisory = P.check(REVIEW_MODEL, self.rules())
        doors = [f for f in blocking if f['code'] == 'PLOT_UPPER_EXTERIOR_DOOR']
        self.assertEqual(len(doors), 1)                     # floors 1 and 2 share one layout
        self.assertIn('الأدوار 1، 2', doors[0]['message'])
        self.assertEqual(doors[0]['room_ref'][1], 'residential_2_lobby')
        self.assertIn('PLOT_UPPER_ENTRANCE_LOBBY', codes(advisory))

    def test_minor_findings_landing_dead_end_and_flat_area(self):
        blocking, advisory = P.check(REVIEW_MODEL, self.rules())
        self.assertIn('PLOT_ENTRY_NOT_ON_LANDING', codes(blocking))
        dead = next(f for f in advisory if f['code'] == 'PLOT_DEAD_END_CORRIDOR')
        self.assertIn('17.5', dead['message'])
        area = next(f for f in advisory if f['code'] == 'PLOT_UNIT_AREA_OFF_TARGET')
        self.assertIn('212.5', area['message'])
        self.assertIn('102', area['message'])

    def test_full_review_blocks_approval_with_arabic_messages(self):
        model = copy.deepcopy(REVIEW_MODEL)
        P.stamp(model, self.rules())
        ws = PlanLockWorkspace(verifier=existing_geometry_verifier)
        rev = ws.propose(model, brief=REVIEW_BRIEF, requirements=REVIEW_REQUIREMENTS, expected_head=None, note='مراجعة')
        review = ws.review(rev.id)
        self.assertFalse(review['can_approve'])
        self.assertEqual(review['scopes']['plot_rules'], 'FAIL')
        plot = [i for i in review['issues'] if i['code'].startswith('PLOT_')]
        self.assertTrue(plot and all(any('؀' <= ch <= 'ۿ' for ch in i['message']) for i in plot))
        self.assertTrue(all(a['severity'] == 'advisory' for a in review['advisories']))


class PassingLayouts(unittest.TestCase):
    def test_envelope_fallback_passes_every_plot_check_for_each_frontage(self):
        for street in ('N', 'S'):
            with self.subTest(street=street):
                rules = P.resolve({'streets': [street], 'parking': {'placement': 'none'}},
                                  REVIEW_BRIEF, REVIEW_REQUIREMENTS, 'C')
                b = L.propose(REVIEW_BRIEF, REVIEW_REQUIREMENTS, rules)
                self.assertIsNotNone(b)
                self.assertEqual(P.check(b, rules)[0], [])
                self.assertEqual(detail_issues(b), [])
                templates = [l['template'] for l in b['levels']]
                self.assertEqual(templates, ['residential_2_ground', 'residential_2', 'residential_2'])
                ground = b['floors']['residential_2_ground']['rooms']
                typical = b['floors']['residential_2']['rooms']
                self.assertTrue(any(r['role'] == 'entrance' and not r.get('unit_id') for r in ground))
                self.assertFalse(any(r['role'] == 'entrance' and not r.get('unit_id') for r in typical))
                street_doors = [d for r in ground for d in r['doors'] if d['edge'] == street
                                and P._across(ground, r, d)[0] is None]
                self.assertEqual(len(street_doors), 1)

    def test_fallback_review_is_approvable_and_reports_only_advisories(self):
        rules = P.resolve(NO_PARKING, REVIEW_BRIEF, REVIEW_REQUIREMENTS, 'C')
        b = L.propose(REVIEW_BRIEF, REVIEW_REQUIREMENTS, rules)
        ws = PlanLockWorkspace(verifier=existing_geometry_verifier)
        rev = ws.propose(b, brief=REVIEW_BRIEF, requirements=REVIEW_REQUIREMENTS, expected_head=None, note='بديل')
        review = ws.review(rev.id)
        self.assertEqual([i['code'] for i in review['issues']], [])
        self.assertTrue(review['can_approve'])
        self.assertEqual(review['scopes']['plot_rules'], 'PASS')
        self.assertEqual(codes(review['advisories']), {'PLOT_PARKING_NOT_PROVIDED', 'PLOT_UNIT_AREA_OFF_TARGET'})

    def test_front_setback_stalls_fit_beside_the_entrance_path(self):
        rows = program(levels=2, units=4, per_level=2)
        brief = 'عمارة سكنية\nتوزيع الشقق من الأرضي إلى الأعلى: 2، 2.'
        rules = P.resolve({'streets': ['N'], 'parking': {'placement': 'front_setback'}}, brief, rows, 'C')
        b = L.propose(brief, rows, rules)
        self.assertIsNotNone(b)
        stalls = P.stalls(b, rules)
        self.assertEqual(len(stalls), 6)
        self.assertTrue(all(s[1] == 0.0 and s[3] == P.STALL_D for s in stalls))
        self.assertEqual(P.check(b, rules)[0], [])
        summary = P.summary(b, rules)
        self.assertEqual(summary['parking']['stalls'], stalls)
        self.assertEqual(summary['envelope'], rules['envelope'])

    def test_pilotis_ground_floor_holds_the_parking_and_no_flats(self):
        rows = program(levels=3, units=4, per_level=2)
        brief = 'عمارة سكنية\nتوزيع الشقق من الأرضي إلى الأعلى: 2، 2.'
        rules = P.resolve({'streets': ['N'], 'parking': {'placement': 'pilotis'}}, brief, rows, 'C')
        b = L.propose(brief, rows, rules)
        self.assertIsNotNone(b)
        ground = b['floors'][b['levels'][0]['template']]['rooms']
        self.assertFalse(any(r.get('unit_id') for r in ground))
        self.assertTrue(any(r['role'] == 'parking' for r in ground))
        self.assertGreaterEqual(P.parking_capacity(b, rules), 6)
        self.assertEqual(_program(b, brief, rows), [])          # two flats per residential floor
        self.assertEqual(P.check(b, rules)[0], [])

    def test_landing_entries_pass_on_the_compact_landing(self):
        rules = P.resolve(dict(NO_PARKING, landing_entries=True), 'عمارة', REVIEW_REQUIREMENTS, 'C')
        b = L.propose(REVIEW_BRIEF, REVIEW_REQUIREMENTS, rules)
        blocking, advisory = P.check(b, rules)
        self.assertNotIn('PLOT_ENTRY_NOT_ON_LANDING', codes(blocking))
        self.assertNotIn('PLOT_DEAD_END_CORRIDOR', codes(advisory))

    def test_party_wall_and_short_setback_windows(self):
        rules = P.resolve({'streets': ['N'], 'setbacks_m': {'S': 0, 'E': 1}, 'max_coverage': 1.0,
                           'parking': {'placement': 'none'}},
                          REVIEW_BRIEF, REVIEW_REQUIREMENTS, 'C')
        b = L.propose(REVIEW_BRIEF, REVIEW_REQUIREMENTS, rules)
        self.assertIsNotNone(b)
        blocking, advisory = P.check(b, rules)
        self.assertEqual(blocking, [])                          # no window was put on the party wall
        self.assertIn('PLOT_WINDOW_BELOW_DEFAULT', codes(advisory))
        rear = next(r for r in b['floors']['residential_2']['rooms']
                    if abs(r['rect'][1] + r['rect'][3] - 25) < 1e-6 and r['role'] == 'bedroom')
        rear['windows'].append({'id': 'w_party', 'edge': 'S', 'offset': 1, 'width': 1, 'height': 1, 'sill': .9})
        self.assertIn('PLOT_OPENING_ON_BOUNDARY', codes(P.check(b, rules)[0]))
        moved = copy.deepcopy(b)
        for template in moved['floors']:
            for room in moved['floors'][template]['rooms']:
                room['rect'][0] += 0.4                          # 0.6 m from the east line
        self.assertIn('PLOT_WINDOW_TOO_CLOSE', codes(P.check(moved, rules)[0]))

    def test_upper_door_to_a_lower_roof_is_a_terrace_and_to_the_void_blocks(self):
        rules = P.resolve(NO_PARKING, 'عمارة', program(levels=2, units=2), None)
        room = lambda rid, rect, doors: {'id': rid, 'role': 'living', 'rect': rect, 'doors': doors, 'windows': []}
        b = {'site': {'w': 20, 'd': 25}, 'levels': [{'index': 0, 'template': 'g'}, {'index': 1, 'template': 'u'}],
             'floors': {'g': {'rooms': [room('a', [2, 3, 10, 10], [])]},
                        'u': {'rooms': [room('b', [2, 3, 10, 5], [{'edge': 'S', 'offset': 5, 'width': .9},
                                                                    {'edge': 'N', 'offset': 5, 'width': .9}])]}}}
        blocking, advisory = P.check(b, rules)
        self.assertIn('PLOT_UPPER_TERRACE_DOOR', codes(advisory))
        self.assertEqual([f['code'] for f in blocking if f['code'].startswith('PLOT_UPPER')], ['PLOT_UPPER_EXTERIOR_DOOR'])

    def test_villa_majlis_with_its_own_street_door_counts_as_next_to_the_entry(self):
        rules = P.resolve({'streets': ['N'], 'parking': {'placement': 'none'}}, 'فيلا', program(levels=1, units=1), None)
        r = lambda rid, role, rect, doors: {'id': rid, 'role': role, 'rect': rect, 'doors': doors, 'windows': [],
                                            'unit_id': 'villa'}
        door = lambda edge, offset: {'edge': edge, 'offset': offset, 'width': .9}
        b = {'site': {'w': 20, 'd': 25}, 'levels': [{'index': 0, 'template': 'g'}], 'floors': {'g': {'rooms': [
            r('hall', 'entrance', [6, 6, 4, 2], [door('N', 2), door('S', 2)]),
            r('majlis', 'majlis', [10, 6, 5, 5], [door('N', 2.5)]),
            r('bed', 'bedroom', [6, 8, 4, 4], [door('N', 2)])]}}}
        _, advisory = P.check(b, rules)
        self.assertNotIn('PLOT_ZONING_MAJLIS_FAR', codes(advisory))      # the majlis has its own street door
        self.assertIn('PLOT_ZONING_BEDROOM_AT_ENTRY', codes(advisory))   # bedroom door 2 m from the front door


class Compatibility(unittest.TestCase):
    def test_old_revisions_without_plot_rules_review_exactly_as_before(self):
        ws = PlanLockWorkspace(verifier=existing_geometry_verifier)
        rev = ws.propose(REVIEW_MODEL, brief=REVIEW_BRIEF, requirements=REVIEW_REQUIREMENTS, expected_head=None, note='قديم')
        review = ws.review(rev.id)
        self.assertNotIn('plot_rules', review['scopes'])
        self.assertNotIn('advisories', review)
        self.assertFalse(any(i['code'].startswith('PLOT_') for i in review['issues']))

    def test_stamp_never_adds_meta_without_rules_and_removes_provider_blocks(self):
        bare = {'floors': {}}
        self.assertEqual(P.stamp(bare, None), {'floors': {}})
        forged = {'meta': {P.META_KEY: {'envelope': [0, 0, 99, 99]}}}
        self.assertNotIn(P.META_KEY, P.stamp(forged, None)['meta'])

    def test_malformed_stamped_rules_block_instead_of_passing(self):
        blocking, _ = P.check(REVIEW_MODEL, {'schema': P.SCHEMA, 'envelope': 'all'})
        self.assertEqual(codes(blocking), {'PLOT_RULES_INVALID'})

    def test_chat_edits_keep_the_revision_rules_whatever_the_provider_returns(self):
        rules = P.resolve(NO_PARKING, REVIEW_BRIEF, REVIEW_REQUIREMENTS, 'C')
        b = L.propose(REVIEW_BRIEF, REVIEW_REQUIREMENTS, rules)
        ws = PlanLockWorkspace(verifier=existing_geometry_verifier)
        rev = ws.propose(b, brief=REVIEW_BRIEF, requirements=REVIEW_REQUIREMENTS, expected_head=None, note='بديل')
        for change in ('drop', 'forge'):
            with self.subTest(change=change):
                candidate = copy.deepcopy(ws.get(ws.head).model)
                if change == 'drop':
                    del candidate['meta'][P.META_KEY]
                else:
                    candidate['meta'][P.META_KEY]['envelope'] = [0, 0, 20, 25]
                edited = admit_bound_chat_edit_candidate(ws, [{'text': 'غيّر اسم المجلس'}],
                                                         expected_head=ws.head, candidate=candidate)
                self.assertEqual(edited.model['meta'][P.META_KEY], rules)


def command(**extra):
    out = {'action': 'generate', 'job_id': '11111111-1111-4111-8111-111111111111', 'brief': REVIEW_BRIEF,
           'requirements': REVIEW_REQUIREMENTS, 'expected_head': None, 'option': 'C', 'confirmed': True,
           'max_provider_calls': 12}
    out.update(extra)
    return out


class Contract(unittest.TestCase):
    def test_generation_command_accepts_a_plot_block_and_preflights_it(self):
        self.assertEqual(S.generation_command(command(plot=NO_PARKING))['plot'], NO_PARKING)
        self.assertNotIn('plot', S.generation_command(command()))
        with self.assertRaises(PlanError) as caught:
            S.generation_command(command(plot={'streets': ['N'], 'parking': {'placement': 'front_setback'}}))
        self.assertEqual(caught.exception.code, 'PLOT_PARKING_DOES_NOT_FIT')
        with self.assertRaises(PlanError) as caught:
            S.generation_command(command(plot={'streets': ['N'], 'unknown': 1}))
        self.assertEqual(caught.exception.code, 'INVALID_PLOT_RULES')
        with self.assertRaises(PlanError):
            S.generation_command(command(brief='مستودع بعرض 20 متر', plot=NO_PARKING))

    def test_parent_stamps_the_rules_from_the_command_not_from_the_worker(self):
        from test_connected_workspace import WorkspaceLifecycle, Runner, PROJECT, ACTOR
        rules = P.resolve(NO_PARKING, REVIEW_BRIEF, REVIEW_REQUIREMENTS, 'C')
        b = L.propose(REVIEW_BRIEF, REVIEW_REQUIREMENTS, rules)
        b['meta'][P.META_KEY] = dict(rules, envelope=[0, 0, 20, 25])   # a forged worker/provider block
        fixture = WorkspaceLifecycle()
        fixture.setUp()
        try:
            runner = Runner(b)
            rid = S.generate_and_save(fixture.store, PROJECT, ACTOR, command(plot=NO_PARKING), runner=runner)
            self.assertEqual(runner.calls[0][1]['plot'], NO_PARKING)
            view = S.view(fixture.store, PROJECT, ACTOR)
            self.assertEqual(view['head'], rid)
            self.assertEqual(fixture.store.workspace_snapshot(PROJECT, actor_id=ACTOR) and
                             S.workspace(fixture.store, PROJECT, ACTOR).get(rid).model['meta'][P.META_KEY], rules)
            self.assertTrue(view['authority']['can_approve_concept'])
            self.assertEqual(view['plot_rules']['envelope'], rules['envelope'])
            advisories = [f for f in view['review_findings'] if f.get('severity') == 'advisory']
            self.assertTrue(advisories and all(f['message'].startswith('ملاحظة استشارية') for f in advisories))
            for text in rules['assumptions']:
                self.assertIn(text, view['planning_assumptions'])
        finally:
            fixture.tearDown()


class GenerationPipeline(unittest.TestCase):
    """The model is stubbed: it answers like a planner that followed the prompt."""

    def setUp(self):
        self.rules = P.resolve(NO_PARKING, REVIEW_BRIEF, REVIEW_REQUIREMENTS, 'C')
        self.reference = L.propose(REVIEW_BRIEF, REVIEW_REQUIREMENTS, self.rules)
        self.rooms = {(t, r['id']): r for t, f in self.reference['floors'].items() for r in f['rooms']}
        self.calls = []

    def provider(self, offset=(0.0, 0.0)):
        from acs_workspace_progress import planning_system
        def call(text, **kw):
            consume()
            stage = kw.get('stage')
            self.calls.append({'stage': stage, 'text': text,
                               'system': kw.get('system_override') or planning_system(stage) or ''})
            if stage == 'plan_chunk':
                asked = json.loads(text.split('منطقة):\n', 1)[1].split('\n\n', 1)[0])
                out = []
                for zone in asked:
                    room = copy.deepcopy(self.rooms[(zone['template'], zone['id'])])
                    room['rect'] = [room['rect'][0] - offset[0], room['rect'][1] - offset[1]] + room['rect'][2:]
                    out.append({k: room[k] for k in ('id', 'rect', 'role', 'walls', 'unit_id', 'core_id', 'name')
                                if k in room})
                return json.dumps({'rooms': out}, ensure_ascii=False)
            if stage == 'detail':
                context = json.loads(text)
                return json.dumps({'rooms': [{k: self.rooms[(context['target_template'], rid)][k]
                                              for k in ('id', 'doors', 'windows', 'points')}
                                             for rid in context['requested_ids']]}, ensure_ascii=False)
            raise AssertionError('unexpected stage ' + str(stage))
        return call

    def run_pipeline(self, offset=(0.0, 0.0)):
        with patch.object(U, 'call_llm', side_effect=self.provider(offset)):
            return S.generate_plan_candidate(REVIEW_BRIEF, REVIEW_REQUIREMENTS, 'C', 12, plot=NO_PARKING)

    def test_prompt_states_the_envelope_and_the_ground_and_typical_templates(self):
        result = self.run_pipeline()
        chunks = [c for c in self.calls if c['stage'] == 'plan_chunk']
        self.assertTrue(chunks)
        for call in chunks:
            self.assertIn('المساحة القابلة للبناء: x من 2 إلى 18 وz من 3 إلى 23', call['text'])
            self.assertIn('قالب الدور الأرضي (residential_2_ground) مستقل عن قالب الدور المتكرر (residential_2)', call['text'])
            self.assertIn('اشتراطات الأرض', call['text'])
            self.assertNotIn('لا تضف مصعداً أو ارتدادات أو موقفاً', call['text'])
            self.assertIn('PLOT RULES', call['system'])
        templates = {json.loads(c['text'].split('منطقة):\n', 1)[1].split('\n\n', 1)[0])[0]['template'] for c in chunks}
        self.assertEqual(templates, {'residential_2_ground', 'residential_2'})
        details = [c for c in self.calls if c['stage'] == 'detail']
        self.assertTrue(details and all('context.plot' in c['system'] for c in details))
        self.assertTrue(all(json.loads(c['text'])['plot']['streets'] == ['N'] for c in details))
        building = result['building']
        self.assertEqual(building['meta'][P.META_KEY], self.rules)
        self.assertEqual(building['site'], {'w': 20.0, 'd': 25.0})
        self.assertEqual(P.check(building, self.rules)[0], [])
        self.assertNotEqual(building['meta'].get('acs_layout_method'), 'bounded_plot_envelope_fallback_v1')

    def test_a_layout_drawn_at_the_land_origin_is_moved_into_the_envelope(self):
        result = self.run_pipeline(offset=(2.0, 3.0))
        self.assertFalse(any(c['stage'] == 'repair' for c in self.calls))
        self.assertEqual(P.envelope_findings(result['building'], self.rules), [])
        self.assertTrue(any('إزاحةً واحدة' in a for a in result['building']['meta']['assumptions']))

    def test_layout_outside_the_envelope_is_repaired_with_the_numbers(self):
        from acs_workspace_progress import planning_system
        bad = copy.deepcopy(self.reference)
        for floor in bad['floors'].values():
            for room in floor['rooms']:
                if abs(room['rect'][0] + room['rect'][2] - 18) < 1e-6:
                    room['rect'][2] += 0.5                            # east rooms cross the side setback
        calls = []
        def provider(text, **kw):
            consume()
            calls.append(kw.get('stage'))
            if kw.get('stage') == 'repair':
                self.assertIn('BUILDABLE ENVELOPE: every room rect must satisfy x >= 2, z >= 3, x + w <= 18, z + d <= 23',
                              kw['system_override'])
                self.assertIn('PLOT_OUTSIDE_ENVELOPE', text)
                return json.dumps({'floors': {t: {'rooms': [{k: r[k] for k in ('id', 'name', 'role', 'unit_id', 'core_id', 'rect', 'walls') if k in r}
                                                             for r in f['rooms']]} for t, f in self.reference['floors'].items()}},
                                  ensure_ascii=False)
            context = json.loads(text)
            return json.dumps({'rooms': [{k: self.rooms[(context['target_template'], rid)][k]
                                          for k in ('id', 'doors', 'windows', 'points')} for rid in context['requested_ids']]})
        layout = {'kind': 'layout', 'building': {k: v for k, v in bad.items() if k != 'meta'}}
        layout['building']['meta'] = {'assumptions': []}
        for floor in layout['building']['floors'].values():
            for room in floor['rooms']:
                for key in ('doors', 'windows', 'points'):
                    room.pop(key, None)
        with patch.object(U, 'call_llm', side_effect=provider):
            result = S.generate_plan_candidate(REVIEW_BRIEF, REVIEW_REQUIREMENTS, 'C', 12, layout, used_calls=2, plot=NO_PARKING)
        self.assertEqual(calls[0], 'repair')
        self.assertEqual(P.check(result['building'], self.rules)[0], [])

    def test_failed_openings_fall_back_inside_the_envelope(self):
        with patch('acs_residential_generation.detail', side_effect=PlanError('PLAN_DETAIL_INCOMPLETE', 'bad')):
            result = S.generate_plan_candidate(REVIEW_BRIEF, REVIEW_REQUIREMENTS, 'C', 12,
                                               {'kind': 'layout', 'building': self.reference}, used_calls=2,
                                               plot=NO_PARKING)
        self.assertEqual(result['building']['meta']['acs_layout_method'], 'bounded_plot_envelope_fallback_v1')
        self.assertEqual(P.check(result['building'], self.rules)[0], [])

    def test_legacy_generation_without_plot_keeps_the_old_program_text(self):
        seen = []
        def provider(text, **kw):
            seen.append(text)
            raise PlanError('STOP', 'stop')
        with patch.object(U, 'call_llm', side_effect=provider), self.assertRaises(PlanError):
            S.generate_plan_candidate(REVIEW_BRIEF, REVIEW_REQUIREMENTS, 'C', 3)
        self.assertIn('لا تضف مصعداً أو ارتدادات أو موقفاً', seen[0])
        self.assertNotIn('اشتراطات الأرض', seen[0])


if __name__ == '__main__':
    unittest.main()
