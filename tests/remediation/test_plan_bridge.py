"""Adapter behavior with synthetic providers/validator; no paid calls."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_bridge as B
from acs_plan_review import PlanError, PlanWorkspace
from test_plan_review import model, program, BRIEF, verified


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.u = SimpleNamespace(detect_type=Mock(return_value='residential'),
            _plan_bounded=Mock(return_value=model()), apply_notes=Mock(return_value=model()),
            understand=Mock(side_effect=AssertionError('full generation forbidden')),
            understand_deep=Mock(side_effect=AssertionError('detail stage forbidden')))
        self.patcher = patch.dict(sys.modules, {'acs_understand': self.u})
        self.patcher.start(); self.addCleanup(self.patcher.stop)
        self.ws = PlanWorkspace(verified)
        self.rev = self.ws.propose(model(), brief=BRIEF, requirements=program(), expected_head=None, note='fixture')

    def test_generate_stops_at_bounded_plan_stage(self):
        reply = B.generate_candidate(BRIEF, model='test-only-model', request_id='test-request')
        self.u._plan_bounded.assert_called_once()
        self.assertEqual(self.u._plan_bounded.call_args.kwargs['request_id'], 'test-request')
        self.assertEqual(reply['building'], model())
        self.assertEqual(reply['stage'], 'PLAN_DRAFT')
        self.assertFalse(reply['engineer_approved'])
        self.assertFalse(reply['model_compiled'])
        self.u.understand.assert_not_called(); self.u.understand_deep.assert_not_called()

    def test_empty_or_oversize_brief_rejected_before_provider(self):
        for text in (None, '', ' ', 'x' * 60_001):
            with self.assertRaises(PlanError): B.generate_candidate(text)
        self.u._plan_bounded.assert_not_called()

    def test_failed_provider_is_not_retried(self):
        self.u._plan_bounded.side_effect = RuntimeError('upstream')
        with self.assertRaises(RuntimeError): B.generate_candidate(BRIEF)
        self.u._plan_bounded.assert_called_once()

    def test_planner_disclosures_are_preserved(self):
        m = model(); m['floors']['g']['rooms'][0]['acs_unresolved'] = True
        self.u._plan_bounded.return_value = m
        self.assertTrue(B.generate_candidate(BRIEF)['building']['floors']['g']['rooms'][0]['acs_unresolved'])

    def test_edit_creates_draft_not_approved_replacement(self):
        self.ws.approve(self.rev.id, expected_head=self.ws.head, actor_label='fixture', confirmed=True, acknowledge_concept_only=True)
        new = B.propose_chat_edit(self.ws, [{'text': 'تعديل المجلس'}], expected_head=self.ws.head)
        self.assertNotEqual(new.id, self.rev.id)
        self.assertEqual(self.ws.baseline, self.rev.id)
        self.u.apply_notes.assert_called_once()
        with self.assertRaises(PlanError): self.ws.handoff(new.id)

    def test_stale_or_empty_edit_rejected_before_provider(self):
        for head, notes in [('stale', [{'text': 'edit'}]), (self.ws.head, []),
                            (self.ws.head, [{'text': ''}])]:
            with self.assertRaises(PlanError): B.propose_chat_edit(self.ws, notes, expected_head=head)
        self.u.apply_notes.assert_not_called()

    def test_provider_violating_lock_never_commits_or_retries(self):
        self.ws.set_room_lock(('g', 'bed'), locked=True, expected_head=self.ws.head)
        head = self.ws.head
        m = model(); m['floors']['g']['rooms'][0]['rect'][2] = 3
        self.u.apply_notes.return_value = m
        with self.assertRaises(PlanError) as got:
            B.propose_chat_edit(self.ws, [{'text': 'only change hall'}], expected_head=head)
        self.assertEqual(got.exception.code, 'LOCK_VIOLATION')
        self.assertEqual(self.ws.head, head)
        self.u.apply_notes.assert_called_once()

    def test_verifier_does_not_claim_missing_opening_or_core_intent(self):
        with patch.dict(sys.modules, {'acs_validate': SimpleNamespace(validate_building=lambda m: ([], {}))}):
            report = B.existing_geometry_verifier(model())
        self.assertEqual(report['scopes']['topology'], 'NOT_VERIFIED')
        self.assertEqual(report['scopes']['vertical_circulation'], 'NOT_VERIFIED')

    def test_verifier_includes_all_existing_findings(self):
        with patch.dict(sys.modules, {'acs_validate': SimpleNamespace(validate_building=lambda m: (['original issue'], {}))}):
            report = B.existing_geometry_verifier(model())
        self.assertEqual(report['issues'][0]['message'], 'original issue')

    def test_explicit_misaligned_core_is_rejected(self):
        m = model()
        for r in m['floors']['g']['rooms']:
            r.update(doors=[], windows=[])
        m['floors']['g']['rooms'][0].update(role='stair', core_id='core1')
        m['floors']['f'] = copy.deepcopy(m['floors']['g'])
        m['levels'][1]['template'] = 'f'
        m['floors']['f']['rooms'][0]['rect'][0] = .5
        with patch.dict(sys.modules, {'acs_validate': SimpleNamespace(validate_building=lambda m: ([], {}))}):
            report = B.existing_geometry_verifier(m)
        self.assertEqual(report['scopes']['vertical_circulation'], 'FAIL')
        self.assertEqual(report['issues'][0]['code'], 'VERTICAL_CORE_MISMATCH')


if __name__ == '__main__':
    unittest.main(verbosity=2)
