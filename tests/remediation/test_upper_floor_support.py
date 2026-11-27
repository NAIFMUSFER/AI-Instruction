"""The owner's corner duplex (live V1): floating rooms, a pool bathroom and a far majlis.

The saved layout (fixtures/floor_program/corner_duplex_layout.unrepaired) is a
24 x 30 m corner plot: a ground + first floor duplex and a separate flat on
the second floor. After the free overlap trim its V1 still had seven blocking
findings: five upper rooms «معلّق» over open ground or a void of the floor
below, a pool bathroom whose only door opens to the yard, and a majlis 6.87 m
from the family entrance although the brief brings guests in from the east.

Covered here, offline (every provider call is a stub):
- the layout stage now reports floating rooms before any opening exists, the
  same five the review finds, and carries the first-floor ones on a covered
  ground porch for free; only the second-floor one buys one repair call;
- the trimmed dressing room grows back to its area in free space;
- upper-floor planning calls see the storey below (extent and open areas);
- a small room the brief opens to the yard is reached from outside;
- a ground guest door into the majlis or its guest lobby serves the majlis,
  and a majlis far from every entrance gets that door for free when the
  brief asks for a guest entrance;
- rooms narrower than the absolute floor for their role are an advisory;
- the instruction growth per call stays small.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests' / 'remediation'))
import acs_floor_program as F
import acs_plot_rules as P
import acs_residential_access as A
import acs_residential_generation as G
import acs_understand as U
import acs_validate as V
from acs_plan_bridge import existing_geometry_verifier
from acs_provider_budget import limited

FIXTURES = ROOT / 'tests' / 'remediation' / 'fixtures'
LAYOUT = json.loads((FIXTURES / 'floor_program' / 'corner_duplex_layout.unrepaired').read_text())
BRIEF = (FIXTURES / 'brief_reader' / 'corner_duplex_brief.txt').read_text(encoding='utf-8')
ROWS = [{'id': m, 'metric': m, 'expected': v, 'confirmed': True, 'source': 'inferred'}
        for m, v in (('site_width_m', 24), ('site_depth_m', 30), ('level_count', 3))]
PLOT = {'streets': ['N', 'E'], 'setbacks_m': {'N': 6, 'S': 6, 'W': 2.5, 'E': 5.5},
        'parking': {'placement': 'front_setback', 'count': 3}}
FLOATING = [('level_1', 'level_1_bedroom_1'), ('level_1', 'level_1_bedroom_3'), ('level_1', 'level_1_bedroom_4'),
            ('level_1', 'level_1_bathroom_3'), ('level_2', 'level_2_bathroom_2')]


def trimmed():
    """The live layout after the free trim (the V1 geometry)."""
    return G._trim_overlaps(LAYOUT, [('level_1', 'level_1_dressing_1', 'level_1_laundry_1')])


def room(building, level, rid):
    return next(r for r in building['floors'][level]['rooms'] if r['id'] == rid)


def rules():
    return P.resolve(PLOT, BRIEF, ROWS, 'A')


def door(edge, offset, width=0.9):
    return {'id': 'd_' + edge + str(offset), 'edge': edge, 'offset': offset, 'width': width, 'height': 2.1,
            'material': 'wood'}


class FloatingRooms(unittest.TestCase):
    def test_the_layout_stage_finds_the_five_rooms_the_review_calls_floating(self):
        value = trimmed()
        found = [tuple(f['room_ref']) for f in G._unsupported_findings(value)]
        self.assertEqual(found, FLOATING)
        review = [i for i in V.validate_building(value)[0] if 'معلّق' in i]
        self.assertEqual(len(review), 5)
        for template, rid in FLOATING:
            self.assertTrue(any('[%s/%s]' % (template, rid) in i for i in review), rid)

    def test_first_floor_rooms_over_open_ground_get_a_covered_porch_for_free(self):
        value = trimmed()
        porched = G._support_porches(value, G._unsupported_findings(value))
        porches = [r for r in porched['floors']['level_0']['rooms'] if r['role'] == 'porch']
        self.assertEqual([p['rect'] for p in porches],
                         [[14.2, 14.0, 4.3, 6.8], [6.8, 20.0, 2.0, 4.0], [5.0, 19.6, 1.8, 2.2], [14.2, 12.8, 2.3, 1.2]])
        for p in porches:
            self.assertEqual((p['walls'], p['covered'], p['name']), ('none', True, 'رواق مظلل'))
            self.assertTrue(P._inside(p['rect'], rules()['envelope']), 'inside the buildable envelope')
        self.assertFalse(any(r['role'] == 'porch' for t in ('level_1', 'level_2')
                             for r in porched['floors'][t]['rooms']), 'never on an upper storey')
        self.assertEqual(G._geometry(porched)[0], [], 'no overlap with the ground rooms')
        self.assertEqual([tuple(f['room_ref']) for f in G._unsupported_findings(porched)],
                         [('level_2', 'level_2_bathroom_2')], 'a void of the first floor is left to the repair')
        self.assertTrue(any('رواق مظلل' in a for a in porched['meta']['assumptions']), 'disclosed')
        self.assertNotIn('meta', value, 'the input is not mutated')

    def test_a_shared_ground_template_gets_no_porch(self):
        value = trimmed()
        value['levels'].append({'id': 'L3', 'name': 'L3', 'index': 3, 'template': 'level_0'})
        self.assertIsNone(G._support_porches(value, G._unsupported_findings(trimmed())))

    def test_one_repair_call_carries_the_last_floating_room_and_its_answer_is_kept(self):
        calls = []
        def provider(text, **kw):
            calls.append((kw['stage'], json.loads(text), kw['system_override']))
            floors = copy.deepcopy(json.loads(text)['building']['floors'])
            # A linen store on the first floor under the flat's bathroom; the
            # ground under it is open, so the free porch step carries it too.
            floors['level_1']['rooms'].append({'id': 'level_1_storage_2', 'name': 'مخزن', 'role': 'storage',
                                               'rect': [16.2, 20.8, 2.3, 3.2], 'walls': ['N', 'S', 'E', 'W'],
                                               'unit_id': 'apartment_1'})
            return json.dumps({'floors': floors}, ensure_ascii=False)
        with limited(12, used=7) as budget, patch.object(U, 'call_llm', side_effect=provider):
            out = G.prepare_layout(copy.deepcopy(LAYOUT), 'عمارة: دوبلكس وشقة', [], budget)
        self.assertEqual([c[0] for c in calls], ['repair'])
        _, context, system = calls[0]
        self.assertEqual([f['code'] for f in context['findings']], ['UNSUPPORTED_UPPER_ROOM'])
        self.assertIn('UNSUPPORTED_UPPER_ROOM: that upper room', system)
        self.assertIn('STACKING: every room of an upper storey', system)
        self.assertEqual(V.unsupported_rooms(out), [])
        self.assertFalse([i for i in V.validate_building(out)[0] if 'معلّق' in i])
        self.assertIn([16.2, 20.8, 2.3, 3.2], [r['rect'] for r in out['floors']['level_0']['rooms'] if r['role'] == 'porch'])

    def test_a_porch_needs_no_door_and_is_reached_from_the_yard(self):
        value = trimmed()
        porched = G._support_porches(value, G._unsupported_findings(value))
        findings = V.validate_building(porched)[0]
        self.assertFalse([i for i in findings if 'porch' in i and 'بلا باب' in i])
        self.assertFalse([i for i in A.issues(porched, doors=True) if 'porch' in i['room_ref'][1]])
        enclosed = copy.deepcopy(porched)
        room(enclosed, 'level_0', 'level_0_porch_1')['walls'] = ['N', 'S', 'E', 'W']
        self.assertTrue([i for i in A.issues(enclosed, doors=True) if i['room_ref'][1] == 'level_0_porch_1'],
                        'a walled room still needs a door path')


class TrimKeepsArea(unittest.TestCase):
    def test_the_trimmed_dressing_room_grows_back_into_free_space(self):
        dressing = room(G._regrow(LAYOUT, trimmed()), 'level_1', 'level_1_dressing_1')['rect']
        self.assertEqual(dressing, [5.4, 16.243, 2.8, 3.157])
        self.assertAlmostEqual(dressing[2] * dressing[3], 3.4 * 2.6, places=2)

    def test_no_regrow_into_another_room(self):
        before, blocked = copy.deepcopy(LAYOUT), trimmed()
        for value in (before, blocked):      # a store fills the free strip north of the dressing room
            value['floors']['level_1']['rooms'].append({'id': 'store', 'role': 'storage', 'rect': [5.4, 15.5, 2.8, 1.3]})
        self.assertIsNone(G._regrow(before, blocked), 'and south of it lies the parents\' bedroom')

    def test_the_trim_never_leaves_a_bedroom_below_its_floor(self):
        rooms = {'floors': {'f': {'rooms': [
            {'id': 'a', 'role': 'bedroom', 'rect': [0, 0, 2.5, 4]},
            {'id': 'b', 'role': 'storage', 'rect': [2.0, 0, 1.25, 4]}]}}, 'levels': []}
        out = G._trim_overlaps(rooms, [('f', 'a', 'b')])
        self.assertIsNone(out, 'the bedroom would drop to 2.0 m and the store to 0.75 m: left to the repair')


class StoreyBelowContext(unittest.TestCase):
    def setUp(self):
        self.envelope = {'site': LAYOUT['site'], 'levels': LAYOUT['levels']}
        self.zones = {r['id']: {'id': r['id'], 'role': r['role'], 'template': t}
                      for t, f in LAYOUT['floors'].items() for r in f['rooms']}
        ground = [dict(r) for r in LAYOUT['floors']['level_0']['rooms']]
        self.results = [({'index': 0, 'template': 'level_0'}, ground, [])]

    def test_an_upper_storey_sees_the_extent_and_open_areas_below(self):
        context = U._plan_spatial_context(self.envelope, self.zones, self.results, 'level_1', support=True)
        below = context['below']
        self.assertEqual(below['template'], 'level_0')
        self.assertEqual(below['extent'], [2.5, 6.0, 16.0, 18.0])
        self.assertIn([6.8, 20.0, 11.7, 4.0], below['open'], 'the open strip along the garden')
        self.assertIn([14.2, 14.0, 4.3, 6.0], below['open'], 'the void east of the living room')

    def test_a_storey_below_still_being_planned_is_not_offered(self):
        partial = [({'index': 0, 'template': 'level_0'}, self.results[0][1][:5], [])]
        self.assertNotIn('below', U._plan_spatial_context(self.envelope, self.zones, partial, 'level_1', support=True))

    def test_the_ground_storey_and_other_buildings_get_no_below(self):
        self.assertNotIn('below', U._plan_spatial_context(self.envelope, self.zones, self.results, 'level_0',
                                                           support=True))
        self.assertNotIn('below', U._plan_spatial_context(self.envelope, self.zones, self.results, 'level_1'))

    def test_the_residential_planning_calls_carry_it(self):
        from test_floor_program import Provider, generate
        provider = Provider()
        generate(provider)
        contexts = [json.loads(text.split('سياق التخطيط المشترك:\n', 1)[1].split('\n\n', 1)[0])
                    for _, text, _ in provider.stage('plan_chunk')]
        self.assertEqual([c.get('below', {}).get('template') for c in contexts], [None, 'level_0', 'level_1'])
        for _, _, system in provider.stage('plan_chunk'):
            self.assertIn('context.below', system)


class YardRooms(unittest.TestCase):
    def ground(self, role='bathroom', rect=None):
        value = copy.deepcopy(trimmed())
        pool = room(value, 'level_0', 'level_0_bathroom_4')
        pool['role'] = role
        if rect:
            pool['rect'] = rect
        pool['doors'] = [door('S', pool['rect'][2] / 2, 0.8)]
        return value

    def flagged(self, value, dwelling=None):
        return [i for i in A.issues(value, dwelling=dwelling) if i['room_ref'][1] == 'level_0_bathroom_4']

    def test_the_pool_bathroom_opening_to_the_yard_is_reached(self):
        self.assertFalse(self.flagged(self.ground()))
        self.assertFalse(self.flagged(self.ground(), A.SINGLE_DWELLING), 'a villa too')

    def test_a_bedroom_or_a_large_bathroom_opening_only_to_the_yard_is_not(self):
        self.assertTrue(self.flagged(self.ground('bedroom')))
        large = self.ground(rect=[2.5, 21.0, 2.1, 3.0])                                   # 6.3 m2
        room(large, 'level_0', 'level_0_bathroom_2')['rect'] = [2.5, 19.6, 2.5, 1.4]
        self.assertTrue(self.flagged(large))


class GuestEntrance(unittest.TestCase):
    """The ground floor of the live layout with the openings the V1 needed."""
    def model(self, guest_lobby_door=False, kitchen_door=False):
        value = copy.deepcopy(trimmed())
        room(value, 'level_0', 'level_0_entrance_1').update(doors=[door('N', 1.95, 1.1), door('E', 1.3)])
        room(value, 'level_0', 'level_0_majlis_1')['doors'] = [door('S', 2.85)]
        lobby = room(value, 'level_0', 'level_0_entrance_2')
        lobby['doors'] = [door('N', 2.85)] + ([door('E', 0.8, 1.0)] if guest_lobby_door else [])
        if kitchen_door:
            room(value, 'level_0', 'level_0_kitchen_1')['doors'] = [door('W', 2.1)]
        return value

    def far(self, value):
        hard, soft = [], []
        P._zoning(value, rules(), hard, soft)
        return [i for i in hard + soft if i['code'] == 'PLOT_ZONING_MAJLIS_FAR']

    def test_the_family_entrance_alone_is_too_far_from_the_majlis(self):
        found = self.far(self.model())
        self.assertEqual(len(found), 1)
        self.assertIn('8.23 م', found[0]['message'])

    def test_a_guest_lobby_door_to_the_yard_serves_the_majlis(self):
        self.assertEqual(self.far(self.model(guest_lobby_door=True)), [])

    def test_a_kitchen_service_door_is_not_an_entrance(self):
        self.assertEqual(len(self.far(self.model(kitchen_door=True))), 1)

    def test_the_brief_asks_for_a_guest_entrance_so_the_majlis_gets_one_for_free(self):
        self.assertTrue(P.guest_entrance_requested(BRIEF))
        self.assertEqual(P.guest_entrance_side(BRIEF), 'E')
        value = self.model()
        self.assertTrue(G._guest_doors(value, BRIEF, rules(), A.APARTMENTS))
        majlis = room(value, 'level_0', 'level_0_majlis_1')
        self.assertEqual(majlis['doors'][-1], {'id': 'level_0_majlis_1_guest_door', 'edge': 'E', 'offset': 2.4,
                                               'width': 1.0, 'height': 2.2, 'material': 'wood'})
        self.assertEqual(self.far(value), [])
        self.assertTrue(any('باب ضيوف' in a for a in value['meta']['assumptions']))

    def test_no_door_the_brief_did_not_ask_for(self):
        value = self.model()
        self.assertFalse(G._guest_doors(value, 'عمارة: دوبلكس وشقة', rules(), A.APARTMENTS))
        self.assertEqual(len(room(value, 'level_0', 'level_0_majlis_1')['doors']), 1)

    def test_no_door_on_a_neighbours_plot_line(self):
        value = self.model()
        tight = dict(rules(), streets=['S'], land={'w': 18.5, 'd': 30.0})   # the majlis' east wall on the line
        majlis = room(value, 'level_0', 'level_0_majlis_1')
        before = copy.deepcopy(majlis['doors'])
        G._guest_doors(value, BRIEF.replace('من الشرق', 'من الجنوب'), tight, A.APARTMENTS)
        self.assertFalse([d for d in majlis['doors'] if d not in before and d['edge'] == 'E'])


class RoomWidths(unittest.TestCase):
    def test_a_room_below_the_floor_for_its_role_is_an_advisory(self):
        value = copy.deepcopy(trimmed())
        room(value, 'level_2', 'level_2_bedroom_2')['rect'] = [2.5, 20.8, 4.0, 1.9]
        notes = [n for n in A.narrow_rooms(value)]
        self.assertEqual([tuple(n['room_ref']) for n in notes], [('level_2', 'level_2_bedroom_2')])
        self.assertEqual(notes[0]['severity'], 'advisory')
        self.assertIn('1.9 م', notes[0]['message'])
        self.assertFalse(A.narrow_rooms(trimmed()), 'the live rooms are all wide enough')

    def test_the_verifier_reports_it_without_blocking(self):
        value = copy.deepcopy(trimmed())
        room(value, 'level_2', 'level_2_bedroom_2')['rect'] = [2.5, 20.8, 4.0, 1.9]
        evidence = existing_geometry_verifier(value)
        self.assertIn('ROOM_TOO_NARROW', {n['code'] for n in evidence['advisories']})
        self.assertNotIn('ROOM_TOO_NARROW', {i['code'] for i in evidence['issues']})

    def test_the_planning_targets_are_never_below_the_check(self):
        text = G.PLANNING_SYSTEM.split('sizes the room (m):', 1)[1]
        for phrase in ('bedroom 2.7', 'maid/driver\n2.1', 'living/majlis/dining 3.0', 'kitchen 2.1', 'bathroom 1.5',
                       'corridor 1.2', 'entrance 1.5'):
            self.assertIn(phrase, text)
        pairs = {'bedroom': 2.7, 'maid_room': 2.1, 'driver_room': 2.1, 'living': 3.0, 'majlis': 3.0, 'dining': 3.0,
                 'kitchen': 2.1, 'bathroom': 1.2, 'corridor': 1.2, 'entrance': 1.5}
        for role, target in pairs.items():
            self.assertGreaterEqual(target, A.MIN_SHORT_SIDE_M[role], role)


class InstructionBudget(unittest.TestCase):
    """Every added character is paid on every call; the growth is bounded."""
    def test_growth_per_call(self):
        self.assertLess(len(G.PLANNING_SYSTEM), 2400)        # +~0.9 k chars on outline/plan/repair calls
        self.assertLess(len(G.OPENINGS_SYSTEM), 2100)        # +~0.3 k chars on openings calls
        self.assertLess(len(G.STACK_REPAIR), 300)            # only when a room floats
        self.assertNotIn('Stack upper bathrooms', F.PLANNING_ADDENDUM, 'stated once, in PLANNING_SYSTEM')
        self.assertNotIn('ADVISORY_REPAIR', dir(G))


if __name__ == '__main__':
    unittest.main(verbosity=2)
