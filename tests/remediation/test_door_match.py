"""Free door fixes after the openings stage, replayed on the live corner duplex.

Live (job 6cd7137f, revision plan_c84cbbcbf7af4dbba568e59a385d7ec0): the layout
passed every check, but after the openings stage 17 blocking findings stood:
- floor 2: the flat's lobby door sat 0.4 m from the landing's door on their
  shared wall, so the whole flat was cut off from the stair;
- floor 2: the open terrace touched only the flat's majlis, which had no door;
- ground: the guest wing (majlis, guest lobby, guest WC) is entered from the
  east street as the brief asks, but only a path from the stair lobby counted;
- floor 1: a bedroom door 2.72 m from the flat's door (the rule asks 3 m).
All four are fixed here without a provider call.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_plot_rules as P
import acs_residential_access as A
import acs_residential_generation as G

ROWS = json.loads((ROOT / 'tests/remediation/fixtures/floor_program/corner_duplex_live3_openings.rows').read_text())
PLOT = {"land": {"d": 30, "w": 24}, "units": 3, "levels": 3, "schema": "acs.plot-rules/1",
        "parking": {"depth_m": 5.5, "stall_m": [2.8, 5.5], "required": 3, "placement": "front_setback"},
        "streets": ["N", "E"], "dwelling": "apartments", "envelope": [2.5, 6, 16, 18],
        "setbacks_m": {"E": 5.5, "N": 6, "S": 6, "W": 2.5}, "max_coverage": 0.65, "window_min_m": 2,
        "street_width_m": 15, "landing_entries": True, "zoning_requested": True,
        "building_footprint": [2.5, 6, 16, 18], "unit_area_target_m2": None, "unit_area_tolerance": 0.25,
        "assumptions": []}


def model():
    floors = {}
    for t, i, role, u, rect, walls, doors in ROWS:
        r = {'id': i, 'name': i, 'role': role, 'rect': list(rect),
             'walls': 'none' if walls == 'none' else list(walls), 'wall_h': 3.0,
             'doors': [{'id': i + '_d%d' % k, 'edge': e, 'offset': o, 'width': w, 'height': 2.1, 'material': 'wood'}
                       for k, (e, o, w) in enumerate(doors)], 'windows': [], 'points': []}
        if u.startswith('core:'):
            r['core_id'] = u[5:]
        else:
            r['unit_id'] = u
        if role in ('stairs', 'elevator'):
            r.pop('wall_h')
        if role == 'porch':
            r['covered'] = True
        floors.setdefault(t, {'rooms': []})['rooms'].append(r)
    return {'site': {'w': 24.0, 'd': 30.0}, 'floors': floors, 'wall_h': 3.0, 'wall_t': 0.2, 'floor_height': 3.2,
            'levels': [{'id': 'L%d' % i, 'name': 'L%d' % i, 'index': i, 'template': 'level_%d' % i} for i in range(3)],
            'meta': {'type': 'residential', 'acs_plot_rules': copy.deepcopy(PLOT)}}


def room(m, template, rid):
    return next(r for r in m['floors'][template]['rooms'] if r['id'] == rid)


def zoning(m):
    hard, soft = [], []
    P._zoning(m, PLOT, hard, soft)
    return hard


class LiveOpenings(unittest.TestCase):
    def test_the_live_openings_left_the_flat_cut_off_and_a_bedroom_at_the_door(self):
        m = model()
        cut = {tuple(i['room_ref']) for i in A.issues(m, doors=True)}
        self.assertIn(('level_2', 'level_2_entrance_1'), cut)
        self.assertIn(('level_2', 'level_2_terrace_1'), cut)
        self.assertEqual([(f['code'], f['room_ref'][1]) for f in zoning(m)],
                         [('PLOT_ZONING_BEDROOM_AT_ENTRY', 'level_1_bedroom_2')])

    def test_all_free_steps_together_clear_every_blocking_finding(self):
        m = model()
        dwelling = A.dwelling_kind(m)
        self.assertEqual(G._match_doors(m), 1)
        self.assertTrue(G._support_doors(m, PLOT, dwelling))
        self.assertEqual(G._ease_bedroom_doors(m, PLOT, dwelling), 1)
        self.assertEqual(A.detail_issues(m, dwelling), [])
        self.assertEqual(zoning(m), [])
        self.assertEqual(P.opening_findings(m, PLOT), [])
        notes = m['meta']['assumptions']
        self.assertTrue(any('level_2_terrace_1' in n for n in notes), 'the terrace door is disclosed')
        self.assertTrue(any('باب غرفة نوم' in n for n in notes), 'the bedroom door move is disclosed')


class MatchDoors(unittest.TestCase):
    def test_the_lobby_and_landing_doors_meet_at_their_common_centre(self):
        m = model()
        lobby, landing = room(m, 'level_2', 'level_2_entrance_1'), room(m, 'level_2', 'level_2_landing')
        self.assertEqual(G._match_doors(m), 1)
        n = next(d for d in lobby['doors'] if d['edge'] == 'N')
        s = next(d for d in landing['doors'] if d['edge'] == 'S')
        self.assertAlmostEqual(lobby['rect'][0] + n['offset'], landing['rect'][0] + s['offset'], places=6)
        self.assertAlmostEqual(lobby['rect'][0] + n['offset'], 9.6, places=6)
        self.assertNotIn(('level_2', 'level_2_entrance_1'), {tuple(i['room_ref']) for i in A.issues(m, doors=True)})

    def test_doors_already_meeting_or_far_apart_are_left_alone(self):
        m = model()
        G._match_doors(m)
        before = json.dumps(m, sort_keys=True)
        self.assertEqual(G._match_doors(m), 0, 'idempotent')
        self.assertEqual(json.dumps(m, sort_keys=True), before)
        far = model()
        s = next(d for d in room(far, 'level_2', 'level_2_landing')['doors'] if d['edge'] == 'S')
        s['offset'] = 3.4                      # 1.4 m away from the lobby door: two doorways, not one
        G._match_doors(far)
        self.assertEqual(s['offset'], 3.4)

    def test_a_move_onto_another_opening_is_refused(self):
        m = model()
        lobby = room(m, 'level_2', 'level_2_entrance_1')
        lobby['windows'] = [{'id': 'w', 'edge': 'N', 'offset': 1.0, 'width': 0.6, 'height': 1.2, 'sill': 0.9}]
        self.assertEqual(G._match_doors(m), 0)


class GroundStreetDoor(unittest.TestCase):
    def test_a_guest_wing_entered_from_the_street_is_reached(self):
        m = model()
        cut = {i['room_ref'][1] for i in A.issues(m, doors=True)}
        for rid in ('level_0_majlis_1', 'level_0_entrance_2', 'level_0_bathroom_1'):
            self.assertNotIn(rid, cut)

    def test_without_its_street_door_the_guest_wing_is_still_cut_off(self):
        m = model()
        lobby = room(m, 'level_0', 'level_0_entrance_2')
        lobby['doors'] = [d for d in lobby['doors'] if d['edge'] != 'E']
        cut = {i['room_ref'][1] for i in A.issues(m, doors=True)}
        self.assertIn('level_0_majlis_1', cut)

    def test_an_upper_flat_still_needs_its_path_from_the_stair(self):
        m = model()
        self.assertIn('level_2_entrance_1', {i['room_ref'][1] for i in A.issues(m, doors=True)})


class TerraceDoor(unittest.TestCase):
    def test_walls_none_spelled_as_a_list_is_wall_less(self):
        self.assertTrue(A.wall_less({'walls': ['none']}))
        self.assertTrue(A.wall_less({'walls': []}))
        self.assertFalse(A.wall_less({'walls': ['N']}))

    def test_the_terrace_gets_a_glass_door_from_the_majlis(self):
        m = model()
        G._match_doors(m)
        self.assertTrue(G._support_doors(m, PLOT, A.dwelling_kind(m)))
        door = next(d for d in room(m, 'level_2', 'level_2_majlis_1')['doors'] if d['id'].endswith('_porch_door'))
        self.assertEqual((door['edge'], door['material']), ('N', 'glass'))
        self.assertNotIn(('level_2', 'level_2_terrace_1'), {tuple(i['room_ref']) for i in A.issues(m, doors=True)})


class BedroomDoor(unittest.TestCase):
    def test_both_halves_of_the_bedroom_doorway_slide_to_three_metres(self):
        m = model()
        dwelling = A.dwelling_kind(m)
        self.assertEqual(G._ease_bedroom_doors(m, PLOT, dwelling), 1)
        bed, hall = room(m, 'level_1', 'level_1_bedroom_2'), room(m, 'level_1', 'level_1_entrance')
        w = next(d for d in bed['doors'] if d['edge'] == 'W')
        e = next(d for d in hall['doors'] if d['edge'] == 'E')
        self.assertAlmostEqual(bed['rect'][1] + w['offset'], hall['rect'][1] + e['offset'], places=6)
        self.assertEqual(zoning(m), [])

    def test_no_plot_rules_no_move(self):
        m = model()
        self.assertEqual(G._ease_bedroom_doors(m, None, A.dwelling_kind(m)), 0)



class AfterCorrectiveCall(unittest.TestCase):
    """Live (job 1b0eb00e): the free step opened the upper lounge onto its
    balcony, then the corrective openings call rewrote that storey's rooms
    and the door was gone. The free steps now run again after that call."""

    def test_doors_the_corrective_call_drops_are_restored(self):
        from unittest.mock import patch
        from acs_provider_budget import limited
        m = model()
        # A finding no free step can fix sends level_2 to the corrective call:
        # its second bedroom has lost its door.
        room(m, 'level_2', 'level_2_bedroom_2')['doors'] = []
        # The corrective call answers with the live openings: the bedroom door
        # is back, but the lobby door is 0.4 m off again and the terrace is closed.
        live = {r['id']: {k: copy.deepcopy(r.get(k) or []) for k in ('doors', 'windows', 'points')}
                for f in model()['floors'].values() for r in f['rooms']}
        calls = []
        def provider(text, **kw):
            ctx = json.loads(text)
            calls.append(ctx['target_template'])
            return json.dumps({'rooms': [dict(id=i, **live[i]) for i in ctx['requested_ids']]})
        done = ['level_0:0', 'level_1:0', 'level_2:0']
        with limited(12, used=0) as budget, patch('acs_understand.call_llm', side_effect=provider):
            out = G.detail(m, 'brief', budget, done=done, plot=PLOT, keep_unresolved=True)
        self.assertIn('level_2', calls, 'the corrective call covers level_2')
        self.assertEqual(A.issues(out, doors=True), [], 'the lobby door and the terrace door are restored')


ROWS4 = json.loads((ROOT / 'tests/remediation/fixtures/floor_program/corner_duplex_live4_openings.rows').read_text())


def model4():
    global ROWS
    saved, ROWS = ROWS, ROWS4
    try:
        return model()
    finally:
        ROWS = saved


class MajlisAtLayout(unittest.TestCase):
    """Live (job 1b0eb00e): the second-floor flat's majlis was drawn 5.8 m from
    the flat's door, found only after openings. It is now a layout finding the
    layout repair already pays for."""

    def test_the_far_majlis_is_found_before_openings(self):
        found = G._majlis_far_findings(model4(), PLOT)
        self.assertEqual([(f['code'], f['room_ref']) for f in found],
                         [('LAYOUT_MAJLIS_FAR', ['level_2', 'level_2_majlis_1'])])
        self.assertGreater(found[0]['nearest_m'], 5.0)

    def test_a_majlis_beside_the_landing_is_not(self):
        self.assertEqual(G._majlis_far_findings(model(), PLOT), [])

    def test_only_when_zoning_is_asked_and_never_for_a_villa(self):
        self.assertEqual(G._majlis_far_findings(model4(), dict(PLOT, zoning_requested=False)), [])
        self.assertEqual(G._majlis_far_findings(model4(), dict(PLOT, dwelling='villa')), [])
        self.assertEqual(G._majlis_far_findings(model4(), None), [])

    def test_the_lift_is_not_the_flats_door(self):
        m = model4()
        lift = room(m, 'level_2', 'level_2_elevator')
        self.assertTrue(lift['rect'][0] + lift['rect'][2] == room(m, 'level_2', 'level_2_entrance_1')['rect'][0])
        self.assertTrue(G._majlis_far_findings(m, PLOT), 'the lift touching the lobby does not count as the entry')

    def test_the_layout_repair_receives_it(self):
        from unittest.mock import patch
        from acs_provider_budget import limited
        m = model4()
        for f in m['floors'].values():
            for r in f['rooms']:
                r.pop('doors', None); r.pop('windows', None); r.pop('points', None)
        with limited(12, used=0) as budget, patch('acs_understand.call_llm', return_value='{}') as provider:
            G.prepare_layout(m, 'brief', [], budget, plot=PLOT)
        self.assertTrue(provider.called, 'a repair call is made')
        context = json.loads(provider.call_args.args[0])
        self.assertIn('LAYOUT_MAJLIS_FAR', [f.get('code') for f in context['findings']])

if __name__ == '__main__':
    unittest.main()
