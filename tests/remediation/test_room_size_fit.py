"""A room drawn far from its confirmed size is brought to it for free at the layout stage.

Live (job 624d60f2, the owner's corner duplex on main 00425ff): the plan came
out with one blocking finding only, PROGRAM_ROOM_SIZE_OFF: the second-floor
flat's laundry was drawn 1.7 x 1.4 m (2.4 m2) against 2.2 x 1.8 m (3.96 m2),
with free floor right beside it. prepare_layout now moves one or two of its
sides into that free space, without a provider call, and keeps the change
only if it clears that finding and adds no other.
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
sys.path.insert(0, str(ROOT / 'tests/remediation'))
import acs_residential_generation as G
from acs_brief_reader import validate_program
from acs_provider_budget import limited
import test_door_match as T

FIX = ROOT / 'tests/remediation/fixtures/floor_program'
LIVE = json.loads((FIX / 'corner_duplex_live5.program').read_text())
ROWS = json.loads((FIX / 'corner_duplex_live5_layout.rows').read_text())


def layout():
    saved, T.ROWS = T.ROWS, ROWS
    try:
        m = T.model()
    finally:
        T.ROWS = saved
    for f in m['floors'].values():
        for r in f['rooms']:
            for k in ('doors', 'windows', 'points'):
                r.pop(k, None)
    return m


def run(m, used=6):
    calls = []
    def provider(text, **kw):
        calls.append(json.loads(text).get('findings'))
        return '{}'
    with limited(12, used=used) as budget, patch('acs_understand.call_llm', side_effect=provider):
        out = G.prepare_layout(m, LIVE['brief'], LIVE['requirements'], budget, plot=T.PLOT,
                               program=validate_program(LIVE['program']))
    return out, calls


def rect(m, template, rid):
    return next(r for r in m['floors'][template]['rooms'] if r['id'] == rid)['rect']


class FitRoomSize(unittest.TestCase):
    def test_the_live_laundry_reaches_its_size_without_a_call(self):
        out, calls = run(copy.deepcopy(layout()))
        self.assertEqual(calls, [], 'no repair call is bought for it')
        x, z, w, d = rect(out, 'level_2', 'level_2_laundry_1')
        self.assertEqual((x, z, w), (11.1, 15, 1.7), 'it keeps its place and width')
        self.assertAlmostEqual(w * d, 3.96, delta=0.4)
        self.assertTrue(any('مقاس' in a and 'م²' in a for a in out['meta']['assumptions']), 'disclosed')

    def test_candidates_move_one_or_two_sides_smallest_change_first(self):
        found = G._size_candidates([11.1, 15, 1.7, 1.4], 3.96, [2.2, 1.8])
        self.assertEqual(found[0], [11.1, 15, 1.7, 2.329])
        self.assertTrue(all(min(r[2], r[3]) >= 1.0 for r in found))
        self.assertIn([11.1, 15, 2.2, 1.8], found)
        shrink = G._size_candidates([2.5, 6, 4.2, 2.4], 7.8, [3.0, 2.6])
        self.assertAlmostEqual(shrink[0][2] * shrink[0][3], 7.8, places=2)

    def test_a_grow_into_another_room_is_refused(self):
        m = layout()
        # Fill the free floor south of the laundry: no candidate may overlap it.
        m['floors']['level_2']['rooms'].append({'id': 'level_2_store_x', 'name': 'x', 'role': 'storage',
                                                'rect': [10.9, 16.4, 1.9, 1.0], 'walls': ['N', 'S', 'E', 'W'],
                                                'unit_id': 'apartment_1', 'wall_h': 3.0})
        out, _ = run(m)
        x, z, w, d = rect(out, 'level_2', 'level_2_laundry_1')
        self.assertLessEqual(z + d, 16.4 + 1e-6)


if __name__ == '__main__':
    unittest.main()
