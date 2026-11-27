"""A reply cut at the output cap after a saved stage can be resumed from that stage.

Live job 71b2cf13 (the owner's detailed brief) paid for three plan chunks and
then lost its first openings call to the 7000-token cap: the model's thinking
counts against the cap and left 3378 characters of an unfinished reply. The job
failed as ACS_UPSTREAM_TRUNCATED with its ``details`` checkpoint saved, but the
truncation was not resumable, so the only way on was to pay for every stage
again. Now the repair and openings calls have room for thinking, and a
truncation with a checkpoint offers a resume. Without a checkpoint it does not:
a restart would repeat every paid stage and meet the same cap.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests' / 'remediation'))
import acs_residential_generation as G
import acs_workspace_http as H


def row(code, checkpoint=None, **extra):
    return {'id': '71b2cf13-8b2e-40be-813e-eb7142dbfff6', 'state': 'FAILED', 'error_code': code,
            'checkpoint': checkpoint, 'provider_calls': 4, 'phase': 'ROOM_DETAILS',
            'resume_command': {'action': 'generate', 'brief': 'x', 'option': 'C'}, **extra}


class ResumeAfterTruncation(unittest.TestCase):
    def test_truncation_after_a_saved_stage_offers_a_resume(self):
        view = H._job_view(row('ACS_UPSTREAM_TRUNCATED', {'kind': 'details', 'building': {}, 'done': []}))
        self.assertTrue(view['job']['can_resume'])

    def test_truncation_without_a_checkpoint_does_not_restart_every_stage(self):
        self.assertFalse(H._job_view(row('ACS_UPSTREAM_TRUNCATED'))['job']['can_resume'])
        self.assertFalse(H._resumable_failure('ACS_UPSTREAM_TRUNCATED'))

    def test_a_job_stopped_at_the_deadline_after_a_saved_layout_offers_a_resume(self):
        # Live job e53cc4f7 (the owner's corner duplex): six paid calls, the full
        # layout saved, then the 840 s worker deadline before the repair stage.
        view = H._job_view(row('ACS_TIMEOUT', {'kind': 'layout', 'building': {}}))
        self.assertTrue(view['job']['can_resume'])
        self.assertFalse(H._job_view(row('ACS_TIMEOUT'))['job']['can_resume'], 'no checkpoint: no paid restart offered')
        self.assertFalse(H._job_view(row('ACS_TIMEOUT', {'kind': 'layout'}, resumed_by='x'))['job']['can_resume'])

    def test_other_upstream_failures_stay_final_and_known_resumable_codes_are_unchanged(self):
        checkpoint = {'kind': 'details'}
        self.assertFalse(H._job_view(row('ACS_UPSTREAM_REFUSED', checkpoint))['job']['can_resume'])
        self.assertTrue(H._job_view(row('PLAN_DETAIL_INCOMPLETE', checkpoint))['job']['can_resume'])
        self.assertTrue(H._job_view(row('PLAN_LAYOUT_INCOMPLETE'))['job']['can_resume'], 'a generate restart, as before')
        self.assertFalse(H._job_view(row('ACS_UPSTREAM_TRUNCATED', checkpoint, resumed_by='x'))['job']['can_resume'])


class WorkspaceDeadline(unittest.TestCase):
    def test_a_long_job_on_another_worker_is_not_called_orphaned_before_its_own_deadline(self):
        from datetime import datetime, timedelta, timezone
        from acs_generation_job import WORKSPACE_JOB_TIMEOUT_S
        now = datetime.now(timezone.utc)
        def running(age_s):
            return {'id': 'other-job', 'state': 'RUNNING', 'worker_id': 'another-worker',
                    'created_at': (now - timedelta(seconds=age_s)).isoformat()}
        # Twenty-five minutes in: still inside a 30-minute workspace job.
        self.assertFalse(H._orphaned(running(1500), now))
        self.assertTrue(H._orphaned(running(WORKSPACE_JOB_TIMEOUT_S + H.ORPHAN_GRACE_S + 60), now))


class OutputCaps(unittest.TestCase):
    def test_openings_and_repair_calls_leave_room_for_thinking(self):
        self.assertGreaterEqual(G.DETAIL_MAX_TOKENS, 16000)
        self.assertGreaterEqual(G.REPAIR_MAX_TOKENS, 16000)

    def test_the_openings_call_sends_the_cap(self):
        seen = []

        class Stop(Exception):
            pass

        def call(text, **kw):
            seen.append((kw.get('stage'), kw.get('max_tokens')))
            raise Stop()

        building = {'site': {'w': 10, 'd': 10}, 'levels': [{'index': 0, 'template': 'ground'}],
                    'floors': {'ground': {'rooms': [{'id': 'r1', 'role': 'living', 'rect': [0, 0, 5, 5]}]}}}
        import acs_understand as U
        with patch.object(U, 'call_llm', side_effect=call), patch.object(G, 'emit'):
            with self.assertRaises(Stop):
                G.detail(building, 'عمارة سكنية', {'limit': 3, 'used': 0})
        self.assertEqual(seen, [('detail', G.DETAIL_MAX_TOKENS)])


if __name__ == '__main__':
    unittest.main()
