"""A read is reviewed as a read: its name, its original beside it, its suggestions (U13).

Before: a read was saved as «البديل A», the review never showed the uploaded
original next to the draft, and the changes a «revise» read suggested
(meta.added) were not shown anywhere. No provider is called.
"""
import copy
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
from test_connected_workspace import ACTOR, PROJECT, Runner
from test_plan_read_transcription import SOURCE, Store, command, fixture, picture, read, row


class ReadReview(Store):
    def test_a_read_is_named_for_the_owner_and_shows_its_original_and_suggestions(self):
        case = fixture('a_cad_ground')
        building = copy.deepcopy(case['read'])
        building['meta'] = {'added': ['دمج المطبخ مع غرفة الطعام لتوسيع المطبخ.']}
        result, _ = read(case, 'revise', building)
        cmd = dict(command(case, 'revise'), source_read={'scale': {'kind': 'extent'}, 'north': 'arrow'})
        with patch.object(SRC, 'read_source', return_value=(row(), picture())):
            S.generate_and_save(self.store, PROJECT, ACTOR, cmd, runner=Runner(result['building']))
        view = S.view(self.store, PROJECT, ACTOR)
        self.assertTrue(view['history'][-1]['note'].startswith('مقروء من ملفك · task:'))
        info = view['plan_source']
        self.assertEqual(info['floors'], [{'source_id': SOURCE, 'page': 1, 'level': 0}])
        self.assertEqual((info['mode'], info['scale'], info['north']), ('revise', {'kind': 'extent'}, 'arrow'))
        self.assertEqual(info['suggested_changes'], ['دمج المطبخ مع غرفة الطعام لتوسيع المطبخ.'])

    def test_a_described_plan_has_no_read_review(self):
        from test_connected_workspace import command as described, model
        S.generate_and_save(self.store, PROJECT, ACTOR, described(), runner=Runner(model()))
        view = S.view(self.store, PROJECT, ACTOR)
        self.assertNotIn('plan_source', view)
        self.assertTrue(view['history'][-1]['note'].startswith('البديل A'))

    def test_the_preview_of_a_saved_source_is_served(self):
        class Rows:
            def _request(self, *args, **kwargs):
                return [dict(row(), preview_sha256=SRC.sha(picture()), preview_media_type='image/png')]
        with patch.object(SRC, 'object_request', return_value=picture()):
            out = SRC.preview_of(Rows(), PROJECT, SOURCE)
        self.assertEqual(out['media_type'], 'image/png')
        http = (ROOT / 'acs_workspace_http.py').read_text(encoding='utf-8')
        self.assertIn('elif action == "preview":', http)


class PageWording(unittest.TestCase):
    def test_step_two_dialog_progress_and_errors_speak_of_reading(self):
        page = (ROOT / 'public/app/ui/plan-upload.mjs').read_text(encoding='utf-8')
        cw = (ROOT / 'public/app/ui/connected-workspace.mjs').read_text(encoding='utf-8')
        self.assertIn("title:'قراءة مخططك'", page)
        self.assertIn('قراءة واحدة لكل دور', page)
        self.assertIn('من 20 إلى 30 ثانية', page)
        self.assertIn('سنتات', page)
        self.assertIn("LAYOUT:progressState.read?'قراءة المخطط'", cw)
        self.assertIn("onOk:()=>{if($('cwStatus').classList.contains('bad'))status('');}", cw)
        self.assertIn('planUpload?.review(data);', cw)
        self.assertIn("'التعديلات المقترحة على مخططك'", page)
        self.assertIn("'الأصل من ملفك'", page)


if __name__ == '__main__':
    unittest.main()
