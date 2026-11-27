"""A second-floor room over a first-floor void that is itself over open ground.

The owner's corner duplex, live run 2 (fixtures/floor_program/
corner_duplex_live2.rooms: the rooms of the saved layout, no openings or
roof). The brief asks the second-floor flat for about 190 m2 plus a terrace,
more than the duplex's first floor builds (about 200 m2 with its own open
side to the garden). The flat put its kitchen, laundry and pantry over the
south-east of the plan, open on the first floor and on the ground: three rooms
«معلّق» at 0%, and its corridor at exactly half, reported «50%» by float noise.
All eight provider calls were spent, none on a stacking repair.

Covered here, offline (no provider call is allowed):
- exactly half of a room's area over the storey below is supported;
- the layout stage carries the three rooms for free: a covered porch on the
  first floor under them, entered from the upper living room it touches, and
  a porch under that on the ground, so the column line reaches the ground;
- the support is a porch (covered, wall-less, no program room), never a
  terrace or balcony (open to the sky, counted per floor by a confirmed
  program); it adds no overlap, access, envelope or door finding, and the
  CAD drafting and the 3D compiler draw it without walls;
- it is not added when no first-floor room can be entered from it, on a
  shared template, or past the plot's coverage;
- after the openings, an upper porch whose room was left without a door to
  it gets that door for free;
- no short free shift of the flat's rooms back over built space exists here.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_compiler as C
import acs_floor_program as F
import acs_plan_drafting as D
import acs_plot_rules as P
import acs_residential_access as A
import acs_residential_generation as G
import acs_understand as U
import acs_validate as V
from acs_provider_budget import limited

FIXTURES = ROOT / 'tests' / 'remediation' / 'fixtures'
LIVE = json.loads((FIXTURES / 'floor_program' / 'corner_duplex_live2.rooms').read_text(encoding='utf-8'))
BRIEF = (FIXTURES / 'brief_reader' / 'corner_duplex_brief.txt').read_text(encoding='utf-8')
ROWS = [{'id': m, 'metric': m, 'expected': v, 'confirmed': True, 'source': 'inferred'}
        for m, v in (('site_width_m', 24), ('site_depth_m', 30), ('level_count', 3))]
PLOT = {'streets': ['N', 'E'], 'setbacks_m': {'N': 6, 'S': 6, 'W': 2.5, 'E': 5.5},
        'parking': {'placement': 'front_setback', 'count': 3}}
FLOATING = ['level_2_kitchen_1', 'level_2_laundry_1', 'level_2_pantry_1']


def rules():
    return P.resolve(PLOT, BRIEF, ROWS, 'A')


def room(building, level, rid):
    return next(r for r in building['floors'][level]['rooms'] if r['id'] == rid)


def porches(building, level):
    return [r for r in building['floors'][level]['rooms'] if r.get('role') == 'porch']


def prepared(layout=None, plot=True, used=4):
    """prepare_layout as the live job ran it (8 calls, 4 spent), with no paid call."""
    with limited(8, used=used) as budget, patch.object(U, 'call_llm', side_effect=AssertionError('paid call')):
        out = G.prepare_layout(copy.deepcopy(layout or LIVE), BRIEF, ROWS, budget, plot=rules() if plot else None)
    assert budget['used'] == used
    return out


class LiveBefore(unittest.TestCase):
    def test_three_rooms_float_and_the_corridor_at_exactly_half_does_not(self):
        found = G._unsupported_findings(G._canonical_room_roles(LIVE))
        self.assertEqual([f['room_ref'] for f in found], [['level_2', rid] for rid in FLOATING])
        self.assertEqual({f['supported_share'] for f in found}, {0.0})
        corridor = room(LIVE, 'level_2', 'level_2_corridor')['rect']
        below = [r['rect'] for r in LIVE['floors']['level_1']['rooms']]
        held = sum(max(0, G._span(corridor, b, 0)) * max(0, G._span(corridor, b, 1)) for b in below)
        self.assertAlmostEqual(held / (corridor[2] * corridor[3]), 0.5, places=9, msg='8.0 of 16.0 m')
        self.assertFalse([i for i in V.validate_building(LIVE)[0] if 'level_2_corridor' in i and 'معلّق' in i])

    def test_just_under_half_still_floats(self):
        value = copy.deepcopy(LIVE)
        room(value, 'level_2', 'level_2_corridor')['rect'] = [2.5, 15.8, 16.1, 1.2]   # 8.0 of 16.1 m
        self.assertIn(['level_2', 'level_2_corridor'], [f['room_ref'] for f in G._unsupported_findings(value)])


class LiveAfter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = prepared()

    def test_no_room_floats_and_no_provider_call_is_spent(self):
        self.assertEqual(G._unsupported_findings(self.out), [])
        self.assertFalse([i for i in V.validate_building(self.out)[0] if 'معلّق' in i])

    def test_a_covered_porch_on_the_first_floor_entered_from_the_upper_living_room(self):
        upper = porches(self.out, 'level_1')
        self.assertEqual(len(upper), 1)
        porch = upper[0]
        self.assertEqual({k: porch[k] for k in ('id', 'name', 'role', 'rect', 'walls', 'covered', 'unit_id')},
                         {'id': 'level_1_porch_1', 'name': 'شرفة مغطاة', 'role': 'porch', 'rect': [11.6, 15.5, 6.9, 5.3],
                          'walls': 'none', 'covered': True, 'unit_id': 'apartment_1'})
        living = room(self.out, 'level_1', 'level_1_living_1')['rect']
        self.assertAlmostEqual(G._contact(porch['rect'], living), 3.5, msg='the living room\'s east wall')
        self.assertAlmostEqual(G._contact(porch['rect'], room(self.out, 'level_1', 'level_1_office_1')['rect']), 3.2)
        for rid in FLOATING + ['level_2_corridor']:
            self.assertTrue(G._overlaps(room(self.out, 'level_2', rid)['rect'], porch['rect']), rid)

    def test_the_column_line_reaches_the_ground(self):
        ground = [p for p in porches(self.out, 'level_0') if p['id'] != 'level_0_porch_1']
        self.assertEqual([(p['name'], p['rect'], p['walls'], p['covered']) for p in ground],
                         [('رواق مظلل', [11.6, 15.5, 6.9, 5.3], 'none', True)])
        self.assertEqual(V.unsupported_rooms(self.out), [], 'the first-floor porch stands on the ground porch')

    def test_it_is_disclosed_in_arabic(self):
        note = [a for a in self.out['meta']['assumptions'] if 'شرفة مغطاة' in a]
        self.assertEqual(note, ['أُضيفت شرفة مغطاة بأعمدة في الدور الأول (1) ورواق مظلل في الدور الأرضي (1) تحت غرف '
                                'الدور الثاني التي كانت فوق فراغ، لتُحمل عليها ويصل خط الأعمدة إلى الأرض؛ تُدخل الشرفة '
                                'المغطاة من الغرفة المجاورة لها. عدّلها أو حرّك الغرف فوقها.'])

    def test_it_adds_no_overlap_access_envelope_or_door_finding(self):
        before = G._canonical_room_roles(LIVE)
        self.assertEqual(G._geometry(self.out)[0], [])
        self.assertEqual(P.envelope_findings(self.out, rules()), [])
        self.assertEqual(A.issues(self.out, doors=False), [])
        new = set(V.validate_building(self.out)[0]) - set(V.validate_building(before)[0])
        self.assertFalse([i for i in new if 'porch' in i], 'a porch needs no door of its own')
        self.assertFalse([i for i in new if 'معلّق' not in i and 'porch' not in i])
        blocking, _ = P.check(self.out, rules())
        self.assertNotIn('PLOT_COVERAGE_EXCEEDED', {i['code'] for i in blocking})

    def test_the_input_is_not_mutated(self):
        self.assertNotIn('assumptions', LIVE['meta'])
        self.assertFalse(porches(LIVE, 'level_1'))

    def test_the_drafting_and_the_compiler_draw_it_without_walls(self):
        for template in ('level_0', 'level_1'):
            self.assertEqual(D._wall_runs(self.out, porches(self.out, template), D._Snap()), [])
        for index in (0, 1, 2):
            self.assertEqual(D.level_drafting(self.out, index, [], [])['level_index'], index)
        with tempfile.TemporaryDirectory() as tmp:
            parts, _ = C.compile_building(copy.deepcopy(self.out), os.path.join(tmp, 'live.gltf'))
        self.assertGreater(parts, 0)


class RoleChoice(unittest.TestCase):
    """A porch is covered and wall-less; a terrace or balcony is open to the sky."""
    def test_the_review_and_the_program_read_the_roles_as_stated(self):
        self.assertFalse(V._open_air({'role': 'porch'}), 'covered')
        self.assertTrue(V._open_air({'role': 'terrace'}) and V._open_air({'role': 'balcony'}), 'open to the sky')
        self.assertNotIn('porch', F.COUNTED_ROLES, 'no confirmed program counts a porch')
        self.assertIn('terrace', F.COUNTED_ROLES)
        self.assertIn('balcony', F.COUNTED_ROLES)

    def test_an_upper_porch_over_open_ground_is_itself_floating(self):
        out = prepared()
        value = copy.deepcopy(out)
        value['floors']['level_0']['rooms'] = [r for r in value['floors']['level_0']['rooms']
                                               if r['id'] != 'level_0_porch_2']
        self.assertIn(['level_1', 'level_1_porch_1'], [f['room_ref'] for f in G._unsupported_findings(value)],
                      'the column line must reach the ground')


class Guards(unittest.TestCase):
    def test_no_room_of_the_first_floor_to_enter_it_from(self):
        with patch.object(G, 'STACK_ACCESS_M', 50.0):
            out = prepared(used=8)                       # with calls left, the repair call would carry them
        self.assertEqual([f['room_ref'][1] for f in G._unsupported_findings(out)], FLOATING)
        self.assertFalse(porches(out, 'level_1'))

    def test_a_wet_room_is_no_way_in(self):
        value = copy.deepcopy(LIVE)
        for rid in ('level_1_living_1', 'level_1_office_1'):
            room(value, 'level_1', rid)['role'] = 'bathroom'
        self.assertEqual(G._stacked_supports(value, G._unsupported_findings(value)), [])

    def test_a_shared_first_floor_template_gets_no_porch(self):
        value = copy.deepcopy(LIVE)
        value['levels'].append({'id': 'L3', 'name': 'L3', 'index': 3, 'template': 'level_1'})
        self.assertEqual(G._stacked_supports(value, G._unsupported_findings(LIVE)), [])

    def test_a_typical_upper_template_over_a_first_floor_of_its_own_is_carried(self):
        value = copy.deepcopy(LIVE)
        value['levels'].append({'id': 'L3', 'name': 'L3', 'index': 3, 'template': 'level_2'})
        chains = G._stacked_supports(value, G._unsupported_findings(value))
        self.assertEqual([[t for t, _ in c] for c in chains], [['level_1', 'level_0']])

    def test_never_past_the_plot_coverage(self):
        tight = dict(rules(), max_coverage=0.3)          # 216 m2 of 720: the ground floor has 202 m2
        with limited(8, used=8) as budget, patch.object(U, 'call_llm', side_effect=AssertionError('paid call')):
            out = G.prepare_layout(copy.deepcopy(LIVE), BRIEF, ROWS, budget, plot=tight)
        self.assertFalse(porches(out, 'level_1'))
        self.assertEqual(len(G._unsupported_findings(out)), 3)

    def test_built_ground_under_it_needs_no_ground_porch(self):
        value = copy.deepcopy(LIVE)
        value['floors']['level_0']['rooms'].append({'id': 'level_0_store_9', 'name': 'مستودع', 'role': 'storage',
                                                    'rect': [11.6, 15.5, 6.9, 5.3], 'walls': ['N', 'S', 'E', 'W'],
                                                    'unit_id': 'apartment_1'})
        chains = G._stacked_supports(value, G._unsupported_findings(value))
        self.assertEqual([[t for t, _ in c] for c in chains], [['level_1']])

    def test_a_two_storey_building_is_left_to_the_ground_porch(self):
        value = copy.deepcopy(LIVE)
        value['levels'] = value['levels'][:2]
        self.assertEqual(G._stacked_supports(value, G._unsupported_findings(LIVE)), [])


def door(edge, offset, width=0.9):
    return {'id': 'd_' + edge + str(offset), 'edge': edge, 'offset': offset, 'width': width, 'height': 2.1,
            'material': 'wood'}


def house():
    """Three storeys of one house: the second floor's kitchen stands over a void."""
    def floor(extra=()):
        return {'rooms': [
            {'id': 'stairs', 'name': 'الدرج', 'role': 'stairs', 'core_id': 'core', 'rect': [0, 0, 3, 5], 'unit_id': 'h'},
            {'id': 'bed', 'name': 'غرفة نوم', 'role': 'bedroom', 'rect': [0, 5, 3, 3.5], 'unit_id': 'h'},
            *extra]}
    rooms = {
        'g': floor([{'id': 'entry', 'name': 'المدخل', 'role': 'entrance', 'rect': [3, 0, 4, 3], 'unit_id': 'h'},
                    {'id': 'living', 'name': 'الصالة', 'role': 'living', 'rect': [3, 3, 4, 5.5], 'unit_id': 'h'}]),
        'f1': floor([{'id': 'living', 'name': 'الصالة العلوية', 'role': 'living', 'rect': [3, 0, 4, 8.5], 'unit_id': 'h'}]),
        'f2': floor([{'id': 'living', 'name': 'صالة الشقة', 'role': 'living', 'rect': [3, 0, 4, 5], 'unit_id': 'h'},
                     {'id': 'kitchen', 'name': 'المطبخ', 'role': 'kitchen', 'rect': [7, 0, 3, 4], 'unit_id': 'h'}]),
    }
    return {'site': {'w': 20.0, 'd': 20.0}, 'wall_h': 3.0, 'wall_t': 0.2, 'floor_height': 3.2, 'meta': {},
            'levels': [{'id': 'L%d' % i, 'name': 'L%d' % i, 'index': i, 'template': t} for i, t in enumerate(('g', 'f1', 'f2'))],
            'floors': rooms}


def with_doors(building):
    """The openings a model would give, except a door from the upper living room to its porch."""
    pairs = {'g': [('entry', 'N', 2.0), ('entry', 'W', 1.5), ('stairs', 'E', 1.5), ('entry', 'S', 2.0),
                   ('living', 'N', 2.0), ('stairs', 'S', 1.5), ('bed', 'N', 1.5)],
             'f1': [('stairs', 'E', 2.5), ('living', 'W', 2.5), ('stairs', 'S', 1.5), ('bed', 'N', 1.5)],
             'f2': [('stairs', 'E', 2.5), ('living', 'W', 2.5), ('stairs', 'S', 1.5), ('bed', 'N', 1.5),
                    ('living', 'E', 2.0), ('kitchen', 'W', 2.0)]}
    for template, items in pairs.items():
        for rid, edge, offset in items:
            room(building, template, rid).setdefault('doors', []).append(door(edge, offset))
    for template, floor in building['floors'].items():
        for r in floor['rooms']:
            r.setdefault('doors', []); r.setdefault('windows', []); r.setdefault('points', [])
    return building


class SupportDoor(unittest.TestCase):
    def setUp(self):
        with limited(8, used=7) as budget, patch.object(U, 'call_llm', side_effect=AssertionError('paid call')):
            self.layout = G.prepare_layout(house(), 'فيلا', [], budget)
        self.dwelling = A.dwelling_kind(self.layout, 'فيلا', [])

    def test_the_house_gets_its_porches_for_free(self):
        self.assertEqual([(p['id'], p['rect']) for p in porches(self.layout, 'f1')], [('f1_porch_1', [7, 0, 3, 4])])
        self.assertEqual([(p['id'], p['rect']) for p in porches(self.layout, 'g')], [('g_porch_1', [7, 0, 3, 4])])
        self.assertEqual(G._unsupported_findings(self.layout), [])

    def test_the_living_room_gets_the_door_its_porch_is_entered_by(self):
        value = with_doors(copy.deepcopy(self.layout))
        self.assertEqual([i['room_ref'] for i in A.issues(value, doors=True, dwelling=self.dwelling)], [['f1', 'f1_porch_1']])
        self.assertTrue(G._support_doors(value, None, self.dwelling))
        self.assertEqual(A.issues(value, doors=True, dwelling=self.dwelling), [])
        self.assertEqual(room(value, 'f1', 'living')['doors'][-1],
                         {'id': 'living_porch_door', 'edge': 'E', 'offset': 2.0, 'width': 1.0, 'height': 2.2,
                          'material': 'glass'})
        self.assertTrue(any('أُضيف باب إلى شرفة مغطاة من «الصالة العلوية»' in a for a in value['meta']['assumptions']))
        self.assertFalse([i for i in V.validate_building(value)[0] if 'porch' in i])

    def test_the_door_keeps_clear_of_a_window_on_that_wall(self):
        value = with_doors(copy.deepcopy(self.layout))
        room(value, 'f1', 'living')['windows'].append({'id': 'w', 'edge': 'E', 'offset': 1.0, 'width': 1.2,
                                                       'height': 1.2, 'sill': 0.9})
        self.assertTrue(G._support_doors(value, None, self.dwelling))
        added = room(value, 'f1', 'living')['doors'][-1]
        self.assertGreaterEqual(added['offset'] - added['width'] / 2, 1.0 + 0.6 + 0.1 - 1e-9)

    def test_nothing_when_the_openings_already_reach_it(self):
        value = with_doors(copy.deepcopy(self.layout))
        room(value, 'f1', 'living')['doors'].append(door('E', 1.0))
        self.assertFalse(G._support_doors(value, None, self.dwelling))

    def test_the_detail_stage_adds_it_before_any_corrective_call(self):
        value = copy.deepcopy(self.layout)
        openings = with_doors(copy.deepcopy(self.layout))
        def provider(text, **kw):
            context = json.loads(text)
            rooms = {r['id']: r for r in openings['floors'][context['target_template']]['rooms']}
            return json.dumps({'rooms': [{'id': i, **{k: rooms[i][k] for k in ('doors', 'windows', 'points')}}
                                         for i in context['requested_ids']]})
        with limited(3, used=0) as budget, patch.object(U, 'call_llm', side_effect=provider) as call:
            out = G.detail(value, 'فيلا', budget, requirements=[])
        self.assertEqual(call.call_count, 3, 'one openings call per floor and no corrective call')
        self.assertEqual(A.issues(out, doors=True, dwelling=self.dwelling), [])


class RepairInstruction(unittest.TestCase):
    def test_the_repair_puts_the_porch_on_the_storey_below_too(self):
        """Paid only on a repair call with a floating room (the free fix could not apply)."""
        self.assertIn('stands over a void of storey_below', G.STACK_REPAIR)
        self.assertIn('on storey_below and each open storey beneath', G.STACK_REPAIR)
        self.assertNotIn('on the ground storey', G.STACK_REPAIR, 'a second-floor room needs it on the first floor')
        self.assertLess(len(G.STACK_REPAIR), 300)


class Alternatives(unittest.TestCase):
    def test_no_short_free_shift_puts_the_flat_back_over_built_space(self):
        group = set(FLOATING)
        env = rules()['envelope']
        for dx in [i / 10 for i in range(-30, 31)]:
            for dz in [i / 10 for i in range(-30, 31)]:
                value = copy.deepcopy(LIVE)
                rooms = value['floors']['level_2']['rooms']
                for r in rooms:
                    if r['id'] in group:
                        r['rect'] = [round(r['rect'][0] + dx, 2), round(r['rect'][1] + dz, 2)] + r['rect'][2:]
                moved = [r for r in rooms if r['id'] in group]
                if any(G._overlaps(m['rect'], o['rect']) for m in moved for o in rooms if o['id'] not in group):
                    continue
                if not all(P._inside(m['rect'], env) for m in moved):
                    continue
                self.assertTrue({f[1] for f in V.unsupported_rooms(value)} & group, (dx, dz))


if __name__ == '__main__':
    unittest.main(verbosity=2)
