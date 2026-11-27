"""The healthcare instruction pack (acs_healthcare_program), before it is wired.

ACS plans only residential and warehouse buildings today. The owner wants
clinics and hospitals next, so this pack holds their room program, flow rules,
instruction texts and deterministic checks, and docs/research/
healthcare_integration_plan.md lists the steps that wire it in later.

Here: the tables are internally consistent and their numbers match the cited
sources; the instruction texts carry the table numbers and the residential JSON
contract, stay within a stated size and claim no compliance; a hand-designed
compliant polyclinic and small hospital pass every healthcare check (and the
generic validator and geometry review too); and each check catches a violation
seeded into a copy of those fixtures. The deliberately broken clinic is stored
as .unrepaired so test_validate_against_real_models never scans it as a model.
"""
import copy
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_healthcare_program as H  # noqa: E402
import acs_validate as V  # noqa: E402
from acs_plan_review import _geometry, _structure, canonical  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'healthcare'
RESEARCH = ROOT / 'docs' / 'research' / 'healthcare_planning.md'
PLAN = ROOT / 'docs' / 'research' / 'healthcare_integration_plan.md'
FT, FT2 = 0.3048, 0.09290304
ARABIC = re.compile('[؀-ۿ]')


def load(name):
    text = (FIXTURES / name).read_text(encoding='utf-8')
    return json.loads(text)


def clinic():
    return load('clinic_compliant.json')


def hospital():
    return load('hospital_compliant.json')


def room(building, template, rid):
    return next(r for r in building['floors'][template]['rooms'] if r['id'] == rid)


def codes(items):
    return {f['code'] for f in items}


def connect(building, template, a, b, width, height=2.14):
    """A matching door pair on the wall rooms a and b share (one global centre)."""
    ra, rb = room(building, template, a), room(building, template, b)
    for side, other in H.OPPOSITE.items():
        la, lo, hi = H._edge(ra['rect'], side)
        lb, lo2, hi2 = H._edge(rb['rect'], other)
        if abs(la - lb) < 1e-9 and min(hi, hi2) - max(lo, lo2) > width:
            centre = (max(lo, lo2) + min(hi, hi2)) / 2
            ra['doors'].append({'id': 'seed_' + b, 'edge': side, 'offset': centre - lo, 'width': width,
                                'height': height, 'material': 'wood'})
            rb['doors'].append({'id': 'seed_' + a, 'edge': other, 'offset': centre - lo2, 'width': width,
                                'height': height, 'material': 'wood'})
            return
    raise AssertionError('rooms do not share a wall')


def door_to(building, template, a, b):
    """The door of room a that opens into room b."""
    ra = room(building, template, a)
    floor = building['floors'][template]['rooms']
    return next(d for d in ra['doors'] if (H._across(floor, ra, d) or {}).get('id') == b)


class DataIntegrity(unittest.TestCase):

    def test_every_role_is_complete(self):
        for name, spec in H.ROOMS.items():
            self.assertRegex(name, r'^[a-z_]+$')
            self.assertLessEqual(len(name), 40, name)          # acs_plan_chunks keeps 40 role characters
            self.assertTrue(ARABIC.search(spec['ar']), name)
            self.assertIn(spec['group'], H.GROUPS, name)
            for key in ('area', 'width'):
                if spec[key] is not None:
                    value, source = spec[key]
                    self.assertGreater(value, 0, name)
                    self.assertIn(source, H.SOURCES, name)

    def test_neighbours_rules_and_programs_name_known_roles(self):
        known = set(H.ROOMS)
        for name, spec in H.ROOMS.items():
            for group in spec['adjacent']:
                self.assertTrue(group and set(group) <= known, name)
        for typology, program in H.PROGRAMS.items():
            self.assertIn(typology, H.TYPOLOGIES)
            self.assertLessEqual(set(program['required']), known)
            self.assertLessEqual(set(program['required']), H.TYPOLOGY_ROLES[typology])
        for name, needs, severity in H.STOREY_RULES:
            self.assertLessEqual({name, *needs}, known)
            self.assertIn(severity, ('error', 'advisory'))
        for _rule, kind, a, b, code, severity in H.FLOW_RULES:
            self.assertIn(kind, ('door', 'wall'))
            self.assertTrue(a and b and a | b <= known, code)
            self.assertTrue(code.startswith('HC_'))
        for group in (H.GROUND_ONLY, H.OR_SUITE, H.BED_SPACES, H.BED_ROUTES, H.CARE_ROLES, H.REFUGE_ROLES,
                      set(H.ROLE_ALIASES.values())):
            self.assertLessEqual(set(group), known)

    def test_flow_groups_never_overlap(self):
        self.assertFalse(H.CLEAN_ROLES & H.DIRTY_ROLES)
        self.assertFalse(H.STERILE_ROLES & H.DIRTY_ROLES)
        self.assertFalse(H.PUBLIC_ROLES & H.RESTRICTED_ROLES)
        self.assertFalse(H.PUBLIC_ROLES & H.DIRTY_ROLES)
        self.assertLessEqual(H.OR_SUITE_CORE, H.OR_SUITE)

    def test_corridor_widths_follow_the_constants(self):
        self.assertEqual(H.ROOMS['bed_corridor']['width'][0], H.BED_CORRIDOR_M)
        self.assertEqual(H.ROOMS['restricted_corridor']['width'][0], H.BED_CORRIDOR_M)
        self.assertEqual(H.ROOMS['corridor']['width'][0], H.PUBLIC_CORRIDOR_M)
        self.assertEqual(H.ROOMS['service_corridor']['width'][0], H.SERVICE_CORRIDOR_M)
        self.assertEqual(H.ROOMS['staff_corridor']['width'][0], H.STAFF_CORRIDOR_M)
        self.assertEqual(set(H.CORRIDORS), {r for r in H.ROOMS if r.endswith('corridor')})

    def test_numbers_match_the_imperial_sources_they_cite(self):
        """FGI and IBC figures are imperial; the metric value is never below them."""
        for metric, imperial in ((H.BED_CORRIDOR_M, 96 * 0.0254),            # IBC Table 1020.2, 96 in
                                 (H.ROOMS['exam_room']['area'][0], 120 * FT2),  # FGI hospital exam 120 ft2
                                 (H.ROOMS['exam_room']['width'][0], 10 * FT),    # 10 ft
                                 (H.ROOMS['operating_room']['area'][0], 400 * FT2),  # FGI OR 400 ft2
                                 (H.ROOMS['operating_room']['width'][0], 20 * FT),   # 20 ft
                                 (H.ROOMS['icu_room']['area'][0], 200 * FT2)):        # FGI ICU 200 ft2
            self.assertGreaterEqual(metric + 1e-9, round(imperial, 2) - 0.005, (metric, imperial))
            self.assertLess(metric - imperial, 0.06, (metric, imperial))
        self.assertAlmostEqual(H.ROOMS['icu_room']['width'][0], 13 * FT, delta=0.005)   # FGI 13 ft headwall
        self.assertAlmostEqual(H.COMPARTMENT_MAX_M2, 22500 * FT2, delta=1.0)           # 22,500 ft2
        self.assertAlmostEqual(H.COMPARTMENT_TRAVEL_M, 200 * FT, delta=0.05)           # 200 ft
        self.assertAlmostEqual(H.REFUGE_BED_M2, 30 * FT2, delta=0.02)                  # 30 ft2
        self.assertGreater(H.BED_DOOR_MIN_M, 41.5 * 0.0254)                           # NFPA 101 bed doors
        self.assertGreaterEqual(H.BED_DOOR_M, H.BED_DOOR_MIN_M)

    def test_sources_are_links_and_the_research_note_cites_them(self):
        note = RESEARCH.read_text(encoding='utf-8')
        for key, url in H.SOURCES.items():
            self.assertTrue(url.startswith(('https://', 'docs/')), key)
            self.assertIn('`' + key + '`', note, key)


class Instructions(unittest.TestCase):

    def test_an_unknown_typology_is_refused(self):
        for call in (H.planning_policy, H.openings_policy, H.repair_policy, H.room_program_text):
            with self.assertRaises(ValueError):
                call('residential')
        with self.assertRaises(ValueError):
            H.check(hospital(), 'warehouse')

    def test_every_instruction_is_bounded_and_the_bound_is_stated(self):
        sizes = H.instruction_sizes()
        for typology in H.TYPOLOGIES:
            for kind, size in sizes[typology].items():
                self.assertLessEqual(size, H.INSTRUCTION_MAX_CHARS[kind], (typology, kind, size))
        self.assertEqual({t: sizes[t] for t in ('clinic', 'hospital')}, H.MEASURED_INSTRUCTION_CHARS)
        self.assertEqual(sizes['polyclinic'], sizes['clinic'])
        plan = PLAN.read_text(encoding='utf-8')
        for kind, bound in H.INSTRUCTION_MAX_CHARS.items():
            self.assertIn('%s | %s' % (kind, format(bound, ',')), plan)

    def test_the_role_list_in_the_text_is_the_table(self):
        text = H.role_minimums_text('hospital')
        sized = dict(re.findall(r'([a-z_]+) ((?:[0-9]+(?:\.[0-9]+)?|-)(?: per bed)?/(?:[0-9]+(?:\.[0-9]+)?|-))', text))
        self.assertTrue(sized)
        for name, value in sized.items():
            area, width = value.replace(' per bed', '').split('/')
            spec = H.ROOMS[name]
            self.assertEqual(area, H._fmt(spec['area'][0]) if spec['area'] else '-', name)
            self.assertEqual(width, H._fmt(spec['width'][0]) if spec['width'] else '-', name)
        self.assertIn('bed_lift car 1.8x2.7', text)
        named = set(re.findall(r'[a-z_]+', text))
        self.assertLessEqual(H.TYPOLOGY_ROLES['hospital'], named)

    def test_the_texts_carry_the_key_numbers_and_rules(self):
        planning = H.planning_policy('hospital')
        for token in ('>= 1.85 m', 'bed_corridor >= 2.44 m', 'service_corridor >= 2 m', 'staff_corridor >= 1.5 m',
                      'at most 2090 m2', 'at least 1.2 m', 'more than 61 m', '1.8 x 2.7 m', '2 beds of 12 m2',
                      '"compartment":"A"', 'core_id'):
            self.assertIn(token, planning)
        openings = H.openings_policy('hospital')
        for token in ('1.4 m wide, never below 1.2 m', '2.14 m high', 'Ensuite doors\n1 m', 'at least 0.9 m',
                      '8% of the room floor area', 'its anteroom'):
            self.assertIn(token, openings)
        clinic_text = H.planning_policy('polyclinic')
        self.assertIn('at least 3 exam rooms', clinic_text)
        self.assertNotIn('compartment', clinic_text)

    def test_every_required_role_is_named_in_its_planning_text(self):
        for typology in H.TYPOLOGIES:
            text = H.planning_policy(typology)
            for name in H.PROGRAMS[typology]['required']:
                self.assertIn(name, text, (typology, name))

    def test_the_json_contracts_match_the_residential_stages(self):
        openings = H.openings_policy('clinic')
        self.assertIn('Return {"rooms":[{"id":"existing id","doors":[{"id":"stable id","edge":"N|S|E|W",'
                      '"offset":0.5,"width":0.9,"height":2.1,"material":"wood"}],"windows":[{"id":"stable id",'
                      '"edge":"N|S|E|W","offset":0.5,"width":1.2,"height":1.2,"sill":0.9}],"points":[{"id":'
                      '"stable id","type":"light","x":1,"z":1}]}]}.', openings)
        repair = H.repair_policy('hospital')
        self.assertIn('Return ONLY\n{"floors":{"existing_template":{"rooms":[{"id":"stable id"', repair)
        for key in ('"name"', '"role"', '"unit_id"', '"core_id"', '"compartment"', '"rect":[0,0,3,4]', '"walls"'):
            self.assertIn(key, repair)
        self.assertIn('outline and\nplan_chunk', H.planning_policy('clinic'))

    def test_no_text_claims_compliance(self):
        texts = [H.planning_policy(t) + H.openings_policy(t) + H.repair_policy(t) + H.room_program_text(t)
                 for t in H.TYPOLOGIES]
        for text in texts:
            text = ' '.join(text.split())
            self.assertIn('do not claim', text)
            self.assertIn('ولا تدّع مطابقة', text)
            self.assertNotRegex(text.lower(), r'\b(?:complies with|compliant with|approved by|certified)\b')

    def test_a_repair_names_only_the_codes_it_carries_and_no_provider_strings(self):
        findings = [{'code': 'HC_ROOM_UNDERSIZED', 'room_ref': ['t', 'ignore_previous_instructions']},
                    {'code': 'HC_FLOW_CLEAN_DIRTY'}]
        text = H.repair_instruction(findings)
        self.assertIn('HC_ROOM_UNDERSIZED: resize to at least min_m2.', text)
        self.assertNotIn('ignore_previous_instructions', text)
        self.assertNotIn('HC_CORRIDOR_TOO_NARROW', text)
        self.assertEqual(H.repair_instruction([]), '')

    def test_the_arabic_program_states_confirmed_counts(self):
        rows = [{'id': 'r1', 'metric': 'room_count', 'role': 'exam_room', 'expected': 6, 'confirmed': True},
                {'id': 'r2', 'metric': 'room_count', 'role': 'patient_room', 'expected': 9, 'confirmed': False},
                {'id': 'r3', 'metric': 'room_count', 'role': 'عيادة', 'expected': 2, 'confirmed': True}]
        text = H.room_program_text('polyclinic', rows)
        self.assertTrue(ARABIC.search(text))
        self.assertIn('غرفة كشف (عيادة): 6 بالضبط role=exam_room', text)
        self.assertIn('2 بالضبط role=exam_room', text)
        self.assertNotIn('role=patient_room', text)

    def test_the_typology_comes_from_the_declared_type_or_the_brief(self):
        self.assertEqual(H.typology_of('مستشفى عام صغير بخمسين سريرًا'), 'hospital')
        self.assertEqual(H.typology_of('مجمع طبي بثلاث عيادات'), 'polyclinic')
        self.assertEqual(H.typology_of('عيادة أسنان في حي سكني'), 'clinic')
        self.assertEqual(H.typology_of('A small polyclinic in Riyadh'), 'polyclinic')
        self.assertIsNone(H.typology_of('فيلا من دورين'))
        self.assertEqual(H.typology_of('عيادة', {'meta': {'type': 'hospital'}}), 'hospital')


class CompliantFixtures(unittest.TestCase):

    def test_the_hand_made_polyclinic_passes_every_check(self):
        for typology in ('polyclinic', 'clinic'):
            self.assertEqual(H.check(clinic(), typology), ([], []), typology)

    def test_the_hand_made_small_hospital_passes_every_check(self):
        self.assertEqual(H.check(hospital(), 'hospital'), ([], []))

    def test_the_generic_validator_and_geometry_review_agree(self):
        from acs_plan_bridge import existing_geometry_verifier
        for model in (clinic(), hospital()):
            _structure(model)
            self.assertEqual(_geometry(model)[0], [])
            issues, _stats, advisories = V.review_building(model)
            self.assertEqual((issues, advisories), ([], []))
            evidence = existing_geometry_verifier(model)
            self.assertEqual(evidence['scopes'], {'topology': 'PASS', 'vertical_circulation': 'PASS'})
            self.assertEqual(evidence['issues'], [])

    def test_checks_never_change_the_model(self):
        for model, typology in ((clinic(), 'polyclinic'), (hospital(), 'hospital')):
            before = canonical(model)
            H.check(model, typology)
            H.layout_findings(model, typology)
            H.opening_findings(model, typology)
            self.assertEqual(canonical(model), before)

    def test_a_layout_before_its_openings_is_not_blamed_for_doors(self):
        model = hospital()
        for floor in model['floors'].values():
            for r in floor['rooms']:
                r['doors'], r['windows'] = [], []
        self.assertFalse(H.has_openings(model))
        self.assertEqual(H.check(model, 'hospital'), ([], []))

    def test_explicit_arabic_role_synonyms_are_read(self):
        model = clinic()
        room(model, 'ground', 'exam_1')['role'] = 'غرفة كشف'
        self.assertEqual(H.check(model, 'polyclinic'), ([], []))

    def test_garbage_is_reported_not_raised(self):
        for value in (None, {}, {'floors': 3, 'levels': []}, {'floors': {'g': {'rooms': [{'id': 'x', 'rect': 'no'}]}},
                                                              'levels': [{'index': 0, 'template': 'g'}]}):
            blocking, _ = H.check(value, 'clinic')
            self.assertIsInstance(blocking, list)


class SeededLayoutViolations(unittest.TestCase):
    """Each check, one violation at a time, against the compliant fixtures."""

    def blocking(self, model, typology='hospital'):
        return codes(H.check(model, typology)[0])

    def advisory(self, model, typology='hospital'):
        return codes(H.check(model, typology)[1])

    def test_a_narrow_bed_corridor(self):
        model = hospital()
        room(model, 'ward', 'corridor_b')['rect'][3] = 2.0
        self.assertIn('HC_CORRIDOR_TOO_NARROW', self.blocking(model))

    def test_a_public_corridor_that_bed_rooms_open_onto(self):
        model = hospital()
        corridor = room(model, 'ward', 'corridor_b')
        corridor['role'], corridor['rect'][3] = 'corridor', 2.0
        self.assertIn('HC_BED_CORRIDOR_NARROW', self.blocking(model))

    def test_an_undersized_patient_room_blocks_and_its_assumed_width_advises(self):
        model = hospital()
        room(model, 'ward', 'room_1')['rect'] = [0, 0, 3.2, 5.0]
        blocking, advisory = H.check(model, 'hospital')
        self.assertIn('HC_ROOM_UNDERSIZED', codes(blocking))       # 18 m2: DHA standard component
        self.assertIn('HC_ROOM_TOO_NARROW', codes(advisory))       # 3.3 m: an ACS assumption
        self.assertNotIn('HC_ROOM_TOO_NARROW', codes(blocking))

    def test_an_exam_room_below_the_fgi_minimum(self):
        model = clinic()
        room(model, 'ground', 'exam_1')['rect'] = [0, 6, 2.8, 3.6]
        self.assertTrue({'HC_ROOM_UNDERSIZED', 'HC_ROOM_TOO_NARROW'} <= self.blocking(model, 'polyclinic'))

    def test_a_sterile_store_against_a_soiled_wall(self):
        model = hospital()
        room(model, 'ground', 'equip')['role'] = 'clean_up'
        self.assertIn('HC_FLOW_STERILE_DIRTY_WALL', self.blocking(model))

    def test_an_isolation_room_without_its_anteroom(self):
        model = hospital()
        room(model, 'ward', 'ante')['role'] = 'store'
        blocking = H.check(model, 'hospital')[0]
        self.assertIn('HC_ADJACENCY_MISSING', codes(blocking))
        self.assertIn(['anteroom'], [f.get('needs') for f in blocking if f['code'] == 'HC_ADJACENCY_MISSING'])
        self.assertIn('HC_ISOLATION_ENTRY', codes(blocking))

    def test_an_operating_room_without_scrub(self):
        model = hospital()
        room(model, 'ground', 'scrub_1')['role'] = 'store'
        blocking = H.check(model, 'hospital')[0]
        self.assertIn(['scrub'], [f.get('needs') for f in blocking if f['code'] == 'HC_ADJACENCY_MISSING'])
        self.assertIn('HC_STOREY_SUPPORT_MISSING', codes(blocking))

    def test_a_ward_storey_without_its_soiled_utility(self):
        model = hospital()
        room(model, 'ward', 'soiled_util_u')['role'] = 'store'
        blocking = H.check(model, 'hospital')[0]
        support = [f for f in blocking if f['code'] == 'HC_STOREY_SUPPORT_MISSING']
        self.assertEqual([f['needs'] for f in support], [['soiled_utility'], ['soiled_utility']])

    def test_recovery_too_small_for_its_operating_rooms(self):
        model = hospital()
        room(model, 'ground', 'recovery')['rect'] = [28.5, 16.5, 4, 4]
        found = [f for f in H.check(model, 'hospital')[0] if f['code'] == 'HC_RECOVERY_CAPACITY']
        self.assertEqual((found[0]['beds'], found[0]['min_beds']), (1, 2))

    def test_a_patient_room_with_no_exterior_wall(self):
        model = hospital()
        room(model, 'ward', 'ens_2')['role'] = 'patient_room'
        self.assertIn('HC_PATIENT_ROOM_INTERIOR', self.blocking(model))

    def test_a_missing_or_small_bed_lift(self):
        model = hospital()
        room(model, 'ward', 'bed_lift')['role'] = 'elevator'
        self.assertIn('HC_BED_LIFT_MISSING', self.blocking(model))
        model = hospital()
        for t in ('ground', 'ward'):
            room(model, t, 'bed_lift')['rect'] = [16, 8.5, 1.6, 5]
        self.assertIn('HC_BED_LIFT_SMALL', self.blocking(model))

    def test_a_clinic_over_two_storeys_needs_a_lift(self):
        model = clinic()
        model['levels'] = [{'index': i, 'id': 'L%d' % i, 'template': 'ground'} for i in range(3)]
        self.assertIn('HC_LIFT_MISSING', self.blocking(model, 'clinic'))

    def test_an_entrance_off_the_ground_storey(self):
        model = hospital()
        room(model, 'ward', 'office')['role'] = 'entrance'
        self.assertIn('HC_ENTRANCE_NOT_GROUND', self.blocking(model))

    def test_the_program_counts_rooms_per_typology(self):
        model = clinic()
        room(model, 'ground', 'exam_3')['role'] = 'office'
        self.assertEqual(self.blocking(model, 'clinic'), set())
        missing = [f for f in H.check(model, 'polyclinic')[0] if f['code'] == 'HC_PROGRAM_MISSING']
        self.assertEqual([(f['role'], f['min'], f['found']) for f in missing], [('exam_room', 3, 2)])

    def test_an_unknown_role_is_an_advisory(self):
        model = clinic()
        room(model, 'ground', 'lab')['role'] = 'spa'
        blocking, advisory = H.check(model, 'polyclinic')
        self.assertEqual(codes(blocking), set())
        self.assertEqual(codes(advisory), {'HC_ROLE_UNKNOWN'})


class SeededFireCompartments(unittest.TestCase):

    def test_a_care_storey_without_compartments(self):
        model = hospital()
        for r in model['floors']['ward']['rooms']:
            del r['compartment']
        self.assertIn('HC_COMPARTMENT_UNASSIGNED', codes(H.check(model, 'hospital')[0]))
        model = hospital()
        for r in model['floors']['ward']['rooms']:
            r['compartment'] = 'A'
        self.assertIn('HC_COMPARTMENT_COUNT', codes(H.check(model, 'hospital')[0]))

    def test_a_compartment_with_no_corridor_to_another(self):
        model = hospital()
        room(model, 'ward', 'corridor_b')['compartment'] = 'A'
        # Both corridors are now in A: neither compartment has a horizontal exit.
        found = [f for f in H.check(model, 'hospital')[0] if f['code'] == 'HC_COMPARTMENT_NO_EXIT']
        self.assertEqual([(f['template'], f['compartment']) for f in found], [('ward', 'A'), ('ward', 'B')])

    def ward(self, length):
        rooms = [{'id': 'corridor_a', 'role': 'bed_corridor', 'rect': [0, 6, 10, 2.5], 'compartment': 'A'},
                 {'id': 'corridor_b', 'role': 'bed_corridor', 'rect': [10, 6, length - 10, 2.5], 'compartment': 'B'},
                 {'id': 'far', 'role': 'patient_room', 'rect': [length - 4, 0, 4, 6], 'compartment': 'B'},
                 {'id': 'hall', 'role': 'store', 'rect': [10, 8.5, length - 10, 20], 'compartment': 'B'}]
        rooms += [{'id': 'bed_%d' % i, 'role': 'patient_room', 'rect': [10 + 4 * i, 0, 4, 6], 'compartment': 'B'}
                  for i in range(10)]
        return {'site': {'w': length, 'd': 30}, 'levels': [{'index': 0, 'template': 'w'}], 'floors': {'w': {'rooms': rooms}}}

    def test_a_compartment_too_large_too_deep_and_without_refuge(self):
        found = H.layout_findings(self.ward(140), 'hospital')
        by_code = {f['code']: f for f in found}
        self.assertGreater(by_code['HC_COMPARTMENT_TOO_LARGE']['area_m2'], H.COMPARTMENT_MAX_M2)
        self.assertGreater(by_code['HC_COMPARTMENT_TRAVEL']['distance_m'], H.COMPARTMENT_TRAVEL_M)
        self.assertEqual(by_code['HC_REFUGE_SMALL']['severity'], 'advisory')   # 25 m2 for 11 beds of 2.8 m2
        self.assertEqual(by_code['HC_REFUGE_SMALL']['beds'], 11)
        near = {f['code'] for f in H.layout_findings(self.ward(60), 'hospital')}
        self.assertFalse({'HC_COMPARTMENT_TOO_LARGE', 'HC_COMPARTMENT_TRAVEL'} & near)


class SeededOpeningViolations(unittest.TestCase):

    def test_a_bed_door_too_narrow_or_below_the_recommendation(self):
        for width, severity in ((1.0, 'error'), (1.3, 'advisory')):
            model = hospital()
            for a, b in (('room_1', 'corridor_a'), ('corridor_a', 'room_1')):
                door_to(model, 'ward', a, b)['width'] = width
            blocking, advisory = H.check(model, 'hospital')
            code = 'HC_DOOR_NOT_BED_CAPABLE' if severity == 'error' else 'HC_DOOR_BELOW_RECOMMENDED'
            self.assertIn(code, codes(blocking if severity == 'error' else advisory), width)

    def test_a_patient_door_too_narrow(self):
        model = clinic()
        for a, b in (('exam_1', 'corridor'), ('corridor', 'exam_1')):
            door_to(model, 'ground', a, b)['width'] = 0.8
        self.assertIn('HC_DOOR_TOO_NARROW', codes(H.check(model, 'polyclinic')[0]))

    def test_a_door_between_clean_and_soiled_rooms(self):
        model = hospital()
        connect(model, 'ward', 'soiled_util_u', 'medication', 0.9)
        found = [f for f in H.check(model, 'hospital')[0] if f['code'] == 'HC_FLOW_CLEAN_DIRTY']
        self.assertEqual(len(found), 1)

    def test_a_public_room_opening_into_the_or_suite(self):
        model = hospital()
        room(model, 'ground', 'spine')['role'] = 'waiting'
        self.assertIn('HC_FLOW_PUBLIC_RESTRICTED', codes(H.check(model, 'hospital')[0]))

    def test_an_operating_room_opening_outside_its_suite(self):
        model = hospital()
        connect(model, 'ground', 'or_1', 'spine', 1.6)
        self.assertIn('HC_OR_SUITE_DOOR', codes(H.check(model, 'hospital')[0]))

    def test_an_ensuite_opening_onto_the_corridor(self):
        model = hospital()
        connect(model, 'ward', 'ens_2', 'corridor_a', 1.0)
        self.assertIn('HC_ENSUITE_DOOR', codes(H.check(model, 'hospital')[0]))

    def test_an_isolation_room_entered_straight_from_the_corridor(self):
        model = hospital()
        for a, b in (('isolation', 'ante'), ('ante', 'isolation')):
            r = room(model, 'ward', a)
            r['doors'].remove(door_to(model, 'ward', a, b))
        self.assertEqual(codes(H.check(model, 'hospital')[0]), {'HC_ISOLATION_ENTRY'})

    def test_a_patient_room_window_below_eight_percent(self):
        model = hospital()
        room(model, 'ward', 'room_1')['windows'][0].update(width=0.6, height=1.0)
        found = [f for f in H.check(model, 'hospital')[0] if f['code'] == 'HC_WINDOW_AREA']
        self.assertEqual([f['room_ref'] for f in found], [['ward', 'room_1']])


class BrokenFixture(unittest.TestCase):

    def test_the_broken_clinic_is_not_a_scanned_model(self):
        path = FIXTURES / 'clinic_broken.unrepaired'
        self.assertTrue(path.exists())
        self.assertFalse(path.name.endswith('.json'))
        self.assertEqual(sorted(p.name for p in FIXTURES.glob('*.json')),
                         ['clinic_compliant.json', 'hospital_compliant.json'])

    def test_the_broken_clinic_is_caught_and_its_repair_names_each_fault(self):
        model = load('clinic_broken.unrepaired')
        blocking, _ = H.check(model, 'polyclinic')
        self.assertEqual(codes(blocking), {'HC_CORRIDOR_TOO_NARROW', 'HC_ROOM_UNDERSIZED', 'HC_ROOM_TOO_NARROW',
                                           'HC_FLOW_CLEAN_DIRTY', 'HC_PROGRAM_MISSING'})
        repair = H.repair_policy('polyclinic', H.layout_findings(model, 'polyclinic'))
        for code in ('HC_CORRIDOR_TOO_NARROW', 'HC_ROOM_UNDERSIZED', 'HC_ROOM_TOO_NARROW', 'HC_PROGRAM_MISSING'):
            self.assertIn('\n' + code + ': ', repair)
        self.assertLessEqual(len(repair), H.INSTRUCTION_MAX_CHARS['repair'])


class NotWiredYet(unittest.TestCase):
    """The owner approves wiring first (healthcare_integration_plan.md). Delete
    this class, and the STAGED_PACKS entry in tests/deploy/verify_deploy.py, in
    the commit that wires the pack in."""

    def test_no_production_module_imports_the_pack(self):
        users = [p.name for p in ROOT.glob('*.py')
                 if p.name != 'acs_healthcare_program.py' and 'acs_healthcare_program' in p.read_text(encoding='utf-8')]
        self.assertEqual(users, [])
        self.assertNotIn('hospital', (ROOT / 'public' / 'app' / 'core' / 'brief-program.mjs').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
