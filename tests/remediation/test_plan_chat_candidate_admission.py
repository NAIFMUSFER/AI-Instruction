"""Canonical admission of precomputed Plan-first chat candidates; no provider calls."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import acs_plan_bridge as B
from acs_plan_review import PlanError
from acs_plan_lock_binding import PlanLockWorkspace
from test_plan_bridge import residential_reqs
from test_plan_lock_binding import (
    residential,
    warehouse,
    reqs,
    element,
    verifier,
)


class CandidateAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.provider = SimpleNamespace(
            apply_notes=Mock(side_effect=AssertionError('candidate admission must not call a provider'))
        )
        self.patcher = patch.dict(sys.modules, {'acs_understand': self.provider})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_precomputed_residential_candidate_preserves_locked_elevator_and_frozen_baseline(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(
            residential(), brief='site width 20 residential',
            requirements=residential_reqs(), expected_head=None, note='initial')
        locked = ws.replace_semantic_locks(
            [element('objects', 'lift_1', 'core')], expected_head=first.id,
            note='lock elevator')
        ws.approve(
            locked.id, expected_head=locked.id, actor_label='engineer',
            confirmed=True, acknowledge_concept_only=True)

        candidate = copy.deepcopy(locked.model)
        rooms = candidate['floors']['ground']['rooms']
        rooms[0]['rect'] = [0.0, 0.0, 8.0, 12.0]
        rooms[3]['rect'] = [0.0, 12.0, 20.0, 8.0]

        revised = B.admit_bound_chat_edit_candidate(
            ws, [{'text': 'كبّر المجلس مع إبقاء المصعد مقفلاً'}],
            expected_head=locked.id, candidate=candidate)

        self.assertEqual(revised.semantic_lock_count, 1)
        self.assertEqual(
            revised.model['floors']['ground']['rooms'][1]['objects'][0],
            locked.model['floors']['ground']['rooms'][1]['objects'][0])
        self.assertEqual(ws.baseline, locked.id)
        with self.assertRaises(PlanError):
            ws.handoff(revised.id)
        self.provider.apply_notes.assert_not_called()

    def test_precomputed_warehouse_candidate_cannot_change_locked_rack(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(
            warehouse(), brief='site width 30 warehouse', requirements=reqs(),
            expected_head=None, note='initial')
        locked = ws.replace_semantic_locks(
            [element('racks', 'rack_a', 'storage')], expected_head=first.id,
            note='lock rack')
        candidate = copy.deepcopy(locked.model)
        candidate['floors']['ground']['rooms'][1]['racks'][0]['levels'] = 5
        count = len(ws.history())

        with self.assertRaises(PlanError) as got:
            B.admit_bound_chat_edit_candidate(
                ws, [{'text': 'وسّع staging فقط'}], expected_head=locked.id,
                candidate=candidate)

        self.assertEqual(got.exception.code, 'LOCK_VIOLATION')
        self.assertEqual(ws.head, locked.id)
        self.assertEqual(len(ws.history()), count)
        self.provider.apply_notes.assert_not_called()

    def test_candidate_admission_rejects_stale_head_without_provider_work(self):
        ws = PlanLockWorkspace(verifier=verifier)
        first = ws.propose(
            residential(), brief='site width 20 residential',
            requirements=residential_reqs(), expected_head=None, note='initial')
        current = ws.replace_semantic_locks([], expected_head=first.id, note='new head')

        with self.assertRaises(PlanError) as got:
            B.admit_bound_chat_edit_candidate(
                ws, [{'text': 'تعديل'}], expected_head=first.id,
                candidate=copy.deepcopy(first.model))

        self.assertEqual(got.exception.code, 'STALE_REVISION')
        self.assertEqual(ws.head, current.id)
        self.provider.apply_notes.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
