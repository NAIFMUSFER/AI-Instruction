"""A malformed read is retried once, and the owner sees the calls used (U11).

Before: one malformed provider reply (not JSON, two objects, a reply without
rooms) failed the paid read outright. Now a floor gets one more reading with a
short correction, never beyond the request budget and never using a call a
later floor needs; the success status names the calls used. No provider.
"""
import base64
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import acs_plan_sources as SRC
import acs_workspace_service as S
from acs_plan_review import PlanError
from acs_provider_budget import consume
from test_plan_read_transcription import fixture, picture

CASE = fixture('a_cad_ground')
GOOD = json.dumps(CASE['read'], ensure_ascii=False)


def run(replies, limit=2, floors=1):
    import acs_understand as U
    sent = []

    def provider(*args, **kwargs):
        consume()
        sent.append(kwargs)
        return replies[len(sent) - 1]
    image = base64.b64encode(picture()).decode()
    plan = {'mode': 'preserve', 'floors': [{'image': image, 'media_type': 'image/png', 'level': i} for i in range(floors)]}
    with patch.object(U, 'call_llm', side_effect=provider):
        try:
            return SRC.candidate(CASE['brief'], CASE['requirements'], 'A', limit, plan), sent
        except PlanError as exc:
            return exc, sent


class MalformedReplies(unittest.TestCase):
    def test_each_malformed_shape_is_read_again_once(self):
        for bad in ('لا أستطيع قراءة هذا المخطط.', GOOD + GOOD, '{"site": {"w": 18', '[]',
                    json.dumps({'site': {'w': 18, 'd': 28}, 'floors': []})):
            with self.subTest(bad=bad[:30]):
                result, sent = run([bad, GOOD])
                self.assertEqual(result['provider_calls'], 2)
                self.assertIn('كائن JSON واحدًا', sent[1]['content'][1]['text'])
                self.assertEqual(sent[0]['content'][0], sent[1]['content'][0], 'the same image is read again')

    def test_two_malformed_replies_fail_in_arabic_without_a_third_call(self):
        result, sent = run(['x', 'y', GOOD], limit=6)
        self.assertEqual(len(sent), 2)
        self.assertEqual(result.code, 'PLAN_SOURCE_READ_MALFORMED')
        self.assertTrue(S.geometry_failure_message('PLAN_SOURCE_READ_MALFORMED'))

    def test_a_retry_never_spends_the_call_a_later_floor_needs(self):
        result, sent = run(['x', GOOD], limit=2, floors=2)
        self.assertEqual(len(sent), 1, 'the second call belongs to the upper floor')
        self.assertEqual(result.code, 'PLAN_SOURCE_READ_MALFORMED')

    def test_the_page_names_the_calls_used(self):
        cw = (ROOT / 'public/app/ui/connected-workspace.mjs').read_text(encoding='utf-8')
        self.assertIn("' القراءات المستخدمة: '", cw)
        self.assertIn('job.provider_calls', cw)


if __name__ == '__main__':
    unittest.main()
