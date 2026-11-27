"""A sliver of overlap between two rooms is trimmed for free before any repair call.

Live (the owner's corner duplex, jobs e53cc4f7 and 6beb400b): the saved
three-floor layout had one hard finding, a dressing room 0.6 m into the
laundry on the first floor. Two repair calls on Opus 5.5 each spent their
whole 16000-token cap thinking and returned no text, so the job failed after
about $1.2 more. Trimming the dressing room by 0.6 m clears every geometry
and access finding; prepare_layout now does that itself, without a call.
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
import acs_residential_generation as G
from acs_provider_budget import limited

# The provider's layout before any repair, deliberately with its overlap. It is
# not a reviewed model, so it is kept out of the *.json fixtures that
# test_validate_against_real_models scans for false positives.
LAYOUT = json.loads((ROOT / 'tests/remediation/fixtures/floor_program/corner_duplex_layout.unrepaired').read_text())
BRIEF = 'عمارة من ثلاثة أدوار: دوبلكس في الأرضي والأول وشقة مستقلة في الدور الثاني'


def room(building, level, rid):
    return next(r for r in building['floors'][level]['rooms'] if r['id'] == rid)


class TrimSliverOverlap(unittest.TestCase):
    def test_the_live_layout_has_one_overlap_and_trimming_clears_it(self):
        issues, _ = G._geometry(G._canonical_room_roles(copy.deepcopy(LAYOUT)))
        self.assertEqual([i['code'] for i in issues], ['ROOM_OVERLAP'])
        trimmed = G._trim_overlaps(LAYOUT, [tuple(issues[0]['path'][:3])])
        self.assertEqual(G._geometry(G._canonical_room_roles(trimmed))[0], [])
        dressing = room(trimmed, 'level_1', 'level_1_dressing_1')['rect']
        laundry = room(trimmed, 'level_1', 'level_1_laundry_1')['rect']
        self.assertEqual(dressing, [5.4, 16.8, 2.8, 2.6], 'the dressing room gives back 0.6 m on the side facing the laundry')
        regrown = G._regrow(LAYOUT, trimmed)
        self.assertEqual(room(regrown, 'level_1', 'level_1_dressing_1')['rect'], [5.4, 16.243, 2.8, 3.157],
                         'then grows back into the free space on its north side, to its 8.84 m2 (live: 18% short)')
        self.assertEqual(laundry, [8.2, 14.2, 2.2, 3.5], 'the other room is untouched')
        self.assertEqual(room(LAYOUT, 'level_1', 'level_1_dressing_1')['rect'], [5.4, 16.8, 3.4, 2.6], 'the input is not mutated')

    def test_prepare_layout_spends_no_provider_call_on_a_sliver(self):
        # The sliver is trimmed for free. The same layout also had five upper
        # rooms over open ground (the live V1's five «معلّق» findings): four
        # first-floor ones get a free covered porch below, and only the second-
        # floor bathroom over a first-floor void is left for one repair call.
        with limited(12, used=7) as budget, patch('acs_understand.call_llm', return_value='{}') as provider:
            out = G.prepare_layout(copy.deepcopy(LAYOUT), BRIEF, [], budget)
        self.assertEqual(provider.call_count, 1)
        context = json.loads(provider.call_args.args[0])
        self.assertEqual(context['findings'], [{'code': 'UNSUPPORTED_UPPER_ROOM', 'room_ref': ['level_2', 'level_2_bathroom_2'],
                                                'supported_share': 0.0, 'storey_below': 'level_1'}])
        self.assertEqual(G._geometry(G._canonical_room_roles(out))[0], [])
        self.assertTrue(any('تداخل صغير' in a for a in out['meta']['assumptions']), 'the trim is disclosed')

    def test_without_budget_for_a_repair_the_sliver_and_porches_are_still_free(self):
        with limited(12, used=11) as budget, patch('acs_understand.call_llm') as provider:
            out = G.prepare_layout(copy.deepcopy(LAYOUT), BRIEF, [], budget)
        provider.assert_not_called()
        self.assertEqual(budget['used'], 11)
        self.assertEqual(G._geometry(G._canonical_room_roles(out))[0], [])
        dressing = room(out, 'level_1', 'level_1_dressing_1')['rect']
        self.assertAlmostEqual(dressing[2] * dressing[3], 3.4 * 2.6, places=2)

    def test_deep_overlaps_and_cores_are_left_to_the_repair_call(self):
        deep = copy.deepcopy(LAYOUT)
        room(deep, 'level_1', 'level_1_dressing_1')['rect'] = [5.4, 16.8, 4.4, 2.6]   # 1.6 m into the laundry
        issues, _ = G._geometry(G._canonical_room_roles(deep))
        pairs = [tuple(i['path'][:3]) for i in issues if i['code'] == 'ROOM_OVERLAP']
        self.assertTrue(pairs)
        self.assertIsNone(G._trim_overlaps(deep, pairs), 'deeper than the trim limit: not guessed')
        core = copy.deepcopy(LAYOUT)
        room(core, 'level_0', 'level_0_dining_1')['rect'] = [8.2, 10.6, 4.6, 4.4]       # 0.4 m into the stairs
        issues, _ = G._geometry(G._canonical_room_roles(core))
        pairs = [tuple(i['path'][:3]) for i in issues if i['code'] == 'ROOM_OVERLAP']
        trimmed = G._trim_overlaps(core, pairs)
        self.assertEqual(room(trimmed, 'level_0', 'level_0_stairs')['rect'], [8.2, 6.0, 2.6, 5.0], 'a core never moves')
        self.assertEqual(G._geometry(G._canonical_room_roles(trimmed))[0], [])


if __name__ == '__main__':
    unittest.main()
