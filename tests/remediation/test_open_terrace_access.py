"""Open terraces and yard-only service rooms in the live owner plan (V1).

The owner's detailed brief, generated live (revision plan_43069357), was held
back by three findings that are not faults:
- the terrace lists only its two 1.2 m parapets (N, E); its door to the living
  room sits on the living room's full wall (S), yet it was measured against
  the parapet height;
- the office window looks onto that roofless terrace, yet the terrace counted
  as an enclosed room;
- the 3.2 m2 pump and filter room opens only to the east yard, as the brief
  asks, yet every room of the flat had to be reached from inside.
The strict cases stay strict: a door in a parapet, a window onto a real room,
a bedroom or a large room that opens only to a yard.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from acs_plan_bridge import existing_geometry_verifier
from acs_plan_review import PlanWorkspace
import acs_residential_access as A
import acs_validate as V

LIVE = json.loads((ROOT / 'tests' / 'remediation' / 'fixtures' / 'floor_program' / 'owner_v1_live.json')
                  .read_text(encoding='utf-8'))


def review(model):
    ws = PlanWorkspace(existing_geometry_verifier)
    rev = ws.propose(model, brief=LIVE['brief'], requirements=LIVE['requirements'], expected_head=None, note='t')
    return ws.review(rev.id)


def room(model, template, rid):
    return next(r for r in model['floors'][template]['rooms'] if r['id'] == rid)


def codes_for(model, rid):
    findings, _ = V.validate_building(model)
    return [f for f in findings if rid in str(f)] + [i for i in A.issues(model) if i['room_ref'][1] == rid]


class LiveOwnerPlan(unittest.TestCase):
    def test_the_live_plan_is_approvable(self):
        result = review(copy.deepcopy(LIVE['model']))
        self.assertTrue(result['can_approve'], [i.get('message') for i in result['issues']][:3])
        self.assertEqual(result['scopes']['topology'], 'PASS')
        self.assertEqual(result['scopes']['brief_program'], 'PASS')


class StillStrict(unittest.TestCase):
    def setUp(self):
        self.model = copy.deepcopy(LIVE['model'])

    def test_a_door_in_the_terrace_parapet_is_still_too_tall(self):
        terrace = room(self.model, 'level_2', 'level_2_terrace_1')
        terrace['doors'].append({'id': 'parapet_door', 'edge': 'N', 'width': 1, 'height': 2.2, 'offset': 1,
                                 'material': 'glass'})
        self.assertTrue(any('الفتحة تتجاوز ارتفاع الجدار' in str(f) for f in codes_for(self.model, 'level_2_terrace_1')))

    def test_a_window_onto_an_enclosed_room_is_still_internal(self):
        terrace = room(self.model, 'level_2', 'level_2_terrace_1')
        terrace.update(role='bedroom', walls=['N', 'S', 'E', 'W'], wall_h=None)
        self.assertTrue(any('جدار داخلي' in str(f) for f in codes_for(self.model, 'level_2_office_1')))

    def test_a_bedroom_that_opens_only_to_the_yard_is_still_disconnected(self):
        room(self.model, 'level_0', 'level_0_other_1')['role'] = 'bedroom'
        self.assertTrue(any(i['code'] == 'RESIDENTIAL_ACCESS_DISCONNECTED' for i in codes_for(self.model, 'level_0_other_1')
                            if isinstance(i, dict)))

    def test_a_large_yard_room_is_still_disconnected(self):
        rooms = self.model['floors']['level_0']['rooms']
        pump = room(self.model, 'level_0', 'level_0_other_1')
        self.assertTrue(A.yard_service(pump, rooms))
        large = dict(pump, rect=[pump['rect'][0], pump['rect'][1], 1.6, 4.4])   # 7 m2: needs a path from the flat
        self.assertFalse(A.yard_service(large, rooms))

    def test_a_yard_service_room_needs_a_door_to_the_outside(self):
        pump = room(self.model, 'level_0', 'level_0_other_1')
        pump['doors'] = []
        self.assertTrue(any(i['room_ref'][1] == 'level_0_other_1' for i in A.issues(self.model)))


if __name__ == '__main__':
    unittest.main()
