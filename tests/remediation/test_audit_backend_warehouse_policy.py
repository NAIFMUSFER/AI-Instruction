"""عقد مخطط المستودع المتصل: لا يطلب غلافاً يتداخل مع غرفه ثم يرفضه."""
import copy
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_understand as U
import acs_workspace_service as S
import acs_workspace_progress as P
from acs_plan_review import PlanError, _geometry
from acs_plan_overlap_repair import repair_overlap
from test_audit_backend_provider import provider

BRIEF = 'مستودع دور واحد على أرض ٤٠×٦٠ متر، منطقة تخزين رئيسية ومنطقة استلام ومنطقة شحن ومكتب ودورة مياه، مدخل منفصل للموظفين.'


def warehouse(envelope=False):
    # أبعاد مناطق مشروع التدقيق الاصطناعي؛ لا حسابات أو بيانات عميل.
    rows = [('receiving', [0, 0, 40, 13]), ('storage', [0, 13, 40, 28]),
            ('shipping', [0, 41, 40, 13]), ('office', [30, 54, 8, 6]),
            ('staff', [22, 54, 4, 6]), ('circulation', [26, 54, 4, 6])]
    rooms = [{'id': role, 'role': role, 'rect': rect, 'walls': 'none'} for role, rect in rows]
    if envelope:
        rooms.insert(0, {'id': 'envelope', 'role': 'envelope', 'rect': [0, 0, 40, 60], 'walls': 'full'})
    return {'site': {'w': 40, 'd': 60}, 'floor_height': 12, 'wall_h': 12, 'wall_t': .3,
            'levels': [{'id': 'L0', 'index': 0, 'template': 'warehouse'}],
            'floors': {'warehouse': {'rooms': rooms}}}


def run_worker():
    """Capture the actual SDK request through outline, chunk and worker admission."""
    building = warehouse()
    outline = {k: v for k, v in building.items() if k != 'floors'}
    rooms = building['floors']['warehouse']['rooms']
    outline['zones'] = [{'id': r['id'], 'role': r['role'], 'template': 'warehouse'} for r in rooms]
    replies = iter([outline, {'rooms': rooms}])
    requests = []
    class Stream:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get_final_message(self):
            return types.SimpleNamespace(
                content=[types.SimpleNamespace(type='text', text=json.dumps(next(replies)))],
                stop_reason='end_turn', usage=types.SimpleNamespace(input_tokens=100, output_tokens=100))
    class Messages:
        def __init__(self, calls, fail): pass
        def stream(self, *, model, max_tokens, messages, system=None):
            requests.append({'system': system, 'messages': copy.deepcopy(messages)})
            return Stream()
    with provider(Messages):
        result = S.generate_plan_candidate(BRIEF, [], 'A', 6)
    return result, requests


def assert_worker_contract(test):
    result, requests = run_worker()
    test.assertEqual(result['provider_calls'], 2)
    test.assertEqual(len(requests), 2)
    test.assertEqual(_geometry(result['building'])[0], [])
    for request in requests:
        # This is the exact contradictory instruction measured in production.
        test.assertNotIn('قاعدة الغلاف: أضِف منطقة id="envelope"', request['system'])
        test.assertIn('non-overlapping', request['system'])
        test.assertIn('Do not add an envelope', request['system'])


class WarehousePolicy(unittest.TestCase):
    def test_workspace_outline_and_chunk_use_canonical_policy(self):
        assert_worker_contract(self)

    def test_reconstructed_live_overlap_is_not_hidden_or_deleted(self):
        building = warehouse(envelope=True)
        before = copy.deepcopy(building)
        issues, _ = _geometry(building)
        self.assertEqual([i['code'] for i in issues], ['ROOM_OVERLAP'] * 6)
        self.assertEqual(sum(r['rect'][2]*r['rect'][3] for r in building['floors']['warehouse']['rooms']), 4656)
        with patch.object(U, 'call_llm') as paid:
            with self.assertRaises(PlanError) as caught:
                repair_overlap(building, BRIEF, {'used': 2, 'limit': 6})
            self.assertEqual(caught.exception.code, 'PLAN_GEOMETRY_AREA_EXCEEDS_SITE')
            paid.assert_not_called()
        self.assertEqual(building, before)

    def test_sound_disjoint_zones_pass_without_paid_repair(self):
        building = warehouse()
        self.assertEqual(_geometry(building)[1]['space_rect_area_m2'], 2256)
        with patch.object(U, 'call_llm') as paid:
            self.assertEqual(repair_overlap(building, BRIEF, {'used': 2, 'limit': 6}), building)
            paid.assert_not_called()

    def test_genuine_excess_remains_blocked_without_envelope(self):
        building = warehouse()
        for r in building['floors']['warehouse']['rooms']:
            r['rect'] = [0, 0, 40, 60]
        with self.assertRaises(PlanError) as caught:
            repair_overlap(building, BRIEF, {'used': 2, 'limit': 6})
        self.assertEqual(caught.exception.code, 'PLAN_GEOMETRY_AREA_EXCEEDS_SITE')

    def test_policy_does_not_leak_to_legacy_calls_or_later_stages(self):
        legacy = U.system_prompt('warehouse')
        assert_worker_contract(self)
        self.assertEqual(U.system_prompt('warehouse'), legacy)
        self.assertIsNone(P.planning_system('outline'))
        self.assertIsNone(P.planning_system('plan_chunk'))
        with P.planning_policy('synthetic plan policy'):
            self.assertIsNone(P.planning_system('repair'))
            self.assertIsNone(P.planning_system('detail'))

    def test_mutating_policy_wiring_restores_the_measured_failure(self):
        # Mutate the boundary in memory; never edit a production file to test it.
        original = P.planning_policy
        with patch.object(P, 'planning_policy', side_effect=lambda policy: original(None)):
            with self.assertRaises(AssertionError):
                assert_worker_contract(self)


if __name__ == '__main__':
    unittest.main()
