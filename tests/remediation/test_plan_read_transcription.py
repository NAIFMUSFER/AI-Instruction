"""A plan read from the owner's own file is approved as a disclosed transcription.

Replays the 2026-11-26 live paid reads (fixtures/plan_reads: a CAD ground
floor, a hand sketch, the upper floor of a two-page PDF). Before this fix every
room got «بلا باب» and «بلا إنارة» and none of them could be approved or
exported. The read now keeps the doors it can see; lighting never blocks a
concept; on a transcription, unseen doors and paths are advisory notes with
the disclosure «المخطط مقروء من ملفك؛ الأبواب المرئية فقط مرسومة», and the
approval states that it approves a transcription. No provider is called.
"""
import base64
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
from PIL import Image

import acs_plan_sources as SRC
import acs_workspace_service as S
from acs_plan_bridge import TRANSCRIPTION_NOTE, existing_geometry_verifier
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_persisted_commands import execute_persisted_plan_command
from acs_plan_review import PlanError
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from acs_provider_budget import consume
from test_connected_workspace import ACTOR, PROJECT, Runner, model

SOURCE = '44444444-4444-4444-8444-444444444444'
FIXTURES = HERE / 'fixtures' / 'plan_reads'
JOB = '55555555-5555-4555-8555-555555555555'


def fixture(name):
    return json.loads((FIXTURES / (name + '.json')).read_text(encoding='utf-8'))


def picture():
    out = io.BytesIO()
    Image.new('RGB', (64, 64), 'white').save(out, format='PNG')
    return out.getvalue()


def read(case, mode='preserve', building=None):
    """Run the real vision-read admission with the recorded provider reply."""
    import acs_understand as U
    reply = json.dumps(building if building is not None else case['read'], ensure_ascii=False)
    sent = []

    def provider(*args, **kwargs):
        consume()
        sent.append(kwargs)
        return reply
    with patch.object(U, 'call_llm', side_effect=provider):
        result = SRC.candidate(case['brief'], case['requirements'], 'A', 2, {
            'image': base64.b64encode(picture()).decode(), 'media_type': 'image/png', 'mode': mode})
    return result, sent


def row():
    return {'id': SOURCE, 'project_id': PROJECT, 'created_by': ACTOR, 'name': 'plan.png',
            'media_type': 'image/png', 'byte_size': 10, 'sha256': 'a' * 64, 'page': 1,
            'page_count': 1, 'preview_sha256': 'b' * 64, 'preview_media_type': 'image/png'}


def command(case, mode='preserve'):
    return {'action': 'generate', 'job_id': JOB, 'brief': case['brief'], 'requirements': case['requirements'],
            'expected_head': None, 'option': 'A', 'confirmed': True, 'max_provider_calls': 2,
            'source_id': SOURCE, 'source_mode': mode}


class Store(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = SQLitePlanStore(Path(self.temp.name) / 'plans.sqlite3')
        self.db.create_project(PROJECT, owner_id=ACTOR)
        self.store = SQLitePlanStoreAdapter(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, case, mode='preserve', building=None):
        result, _ = read(case, mode, building)
        with patch.object(SRC, 'read_source', return_value=(row(), picture())):
            return S.generate_and_save(self.store, PROJECT, ACTOR, command(case, mode),
                                       runner=Runner(result['building']))

    def approve(self, rid, **extra):
        return execute_persisted_plan_command(self.store, PROJECT, dict(
            {'action': 'approve', 'expected_head': rid, 'confirmed': True, 'acknowledge_concept_only': True},
            **extra), actor_id=ACTOR, verifier=S.existing_geometry_verifier)


class TranscribedReadsAreApprovedAndExported(Store):
    def test_recorded_reads_approve_as_transcriptions_and_export_every_format(self):
        for name in ('a_cad_ground', 'c_hand_sketch'):
            with self.subTest(case=name):
                self.tearDown(); self.setUp()
                case = fixture(name)
                rid = self.save(case)
                view = S.view(self.store, PROJECT, ACTOR)
                blocking = [f for f in view['review_findings'] if f.get('severity') != 'advisory']
                self.assertEqual(blocking, [], 'only advisory notes remain on a transcription')
                self.assertTrue(view['authority']['can_approve_concept'])
                self.assertTrue(view['authority']['source_transcription'])
                text = ' '.join(f['message'] for f in view['review_findings'])
                self.assertIn(TRANSCRIPTION_NOTE, text)
                self.assertNotIn('light أو spot', text)
                self.assertNotIn('أضِف باباً', text, 'no repair demand for a door the file does not show')
                # The approval itself must say it approves a transcription.
                with self.assertRaises(PlanError) as caught:
                    self.approve(rid)
                self.assertEqual(caught.exception.code, 'TRANSCRIPTION_ACKNOWLEDGEMENT_REQUIRED')
                approved = self.approve(rid, acknowledge_transcription=True)
                self.assertEqual(approved['baseline'], rid)
                self.assertEqual(approved['approval']['source'], 'transcription')
                revision = S.workspace(self.store, PROJECT, ACTOR).get(rid)
                for level in revision.model['levels']:
                    for fmt in ('svg', 'dxf'):
                        out = S.artifact(self.store, PROJECT, ACTOR, {'action': 'artifact', 'revision_id': rid,
                                                                      'format': fmt, 'level_index': level['index']})
                        self.assertTrue(base64.b64decode(out['data_base64']))
                for fmt in ('pdf', 'ifc', 'gltf'):
                    out = S.artifact(self.store, PROJECT, ACTOR, {'action': 'artifact', 'revision_id': rid, 'format': fmt})
                    self.assertTrue(base64.b64decode(out['data_base64']), fmt)

    def test_the_upper_floor_alone_is_blocked_only_by_the_confirmed_floor_count(self):
        case = fixture('d_upper_floor')
        self.save(case)
        view = S.view(self.store, PROJECT, ACTOR)
        self.assertFalse(view['authority']['can_approve_concept'])
        blocking = [f for f in view['review_findings'] if f.get('severity') != 'advisory']
        self.assertTrue(blocking)
        self.assertTrue(all(f['requirement_id'] == 'brief-2' for f in blocking), blocking)

    def test_villa_livability_notes_are_advisory_on_a_transcription(self):
        case = fixture('a_cad_ground')   # a ground floor with no bathroom drawn
        self.save(case)
        ws = S.workspace(self.store, PROJECT, ACTOR)
        review = ws.review(ws.head)
        self.assertTrue(review['transcription'])
        self.assertEqual(review['scopes']['dwelling_program'], 'PASS')
        self.assertIn('VILLA_NO_BATHROOM', {a['code'] for a in review['advisories']})
        self.assertFalse([i for i in review['issues'] if i['code'].startswith('VILLA_')])

    def test_full_design_mode_keeps_doors_blocking(self):
        case = fixture('a_cad_ground')
        self.save(case, mode='complete')
        view = S.view(self.store, PROJECT, ACTOR)
        self.assertFalse(view['authority']['can_approve_concept'])
        self.assertNotIn('source_transcription', view['authority'])
        self.assertTrue(any('بلا باب' in f['message'] for f in view['review_findings']
                            if f.get('severity') != 'advisory'))


class VisibleDoors(unittest.TestCase):
    def test_instruction_asks_for_drawn_doors_and_invents_none(self):
        case = fixture('a_cad_ground')
        _, sent = read(case)
        system = sent[0]['system_override']
        self.assertIn('الأبواب المرسومة في الصورة فقط', system)
        self.assertIn('لا تختلق أبوابًا غير مرسومة', system)
        self.assertIn('doors=[]', system)
        _, sent = read(case, 'complete')
        self.assertNotIn('لا تختلق أبوابًا', sent[0]['system_override'])
        self.assertIn('meta.added', sent[0]['system_override'])

    def test_read_doors_use_the_generator_contract_and_off_wall_doors_are_dropped(self):
        case = fixture('a_cad_ground')
        building = copy.deepcopy(case['read'])
        rooms = building['floors']['ground']['rooms']
        rooms[0]['doors'] = [{'edge': 'S', 'offset': 3, 'width': 1.0, 'id': 'provider-id'},
                             {'edge': 'S', 'offset': 9, 'width': 1.0}]           # beyond the 6 m wall
        rooms[0]['points'] = [{'type': 'socket', 'x': 1, 'z': 1}]
        rooms[1]['windows'] = [{'edge': 'N', 'offset': 1, 'width': 1}]
        result, _ = read(case, building=building)
        out = result['building']['floors']['ground']['rooms']
        self.assertEqual([{k: d[k] for k in ('edge', 'offset', 'width', 'height')} for d in out[0]['doors']],
                         [{'edge': 'S', 'offset': 3, 'width': 1.0, 'height': 2.1}])
        self.assertNotEqual(out[0]['doors'][0]['id'], 'provider-id')
        self.assertNotIn('points', out[0])
        self.assertEqual(out[1]['windows'], [], 'no window is invented or kept from the provider')
        self.assertTrue(any('تُركت 1 فتحة باب' in a for a in result['building']['meta']['assumptions']))
        self.assertEqual(result['building']['_opening_identity']['schema'], 'acs.opening-identity/1')
        # Every room has an explicit opening list, so topology is evaluated.
        review = existing_geometry_verifier(json.loads(json.dumps(result['building'])))
        self.assertIn(review['scopes']['topology'], ('PASS', 'NOT_VERIFIED', 'FAIL'))


class LightingNeverBlocks(unittest.TestCase):
    def test_a_generated_plan_without_lighting_points_is_approvable_with_one_note(self):
        building = model()
        for room in building['floors']['ground']['rooms']:
            room.pop('points')
        ws = PlanLockWorkspace(existing_geometry_verifier)
        rev = ws.propose(building, brief='موقع بعرض 20 متر', expected_head=None, note='lighting',
                         requirements=[{'id': 'width', 'metric': 'site_width_m', 'expected': 20,
                                        'source': 'requested', 'evidence': '20'}])
        review = ws.review(rev.id)
        self.assertTrue(review['can_approve'], review['issues'])
        self.assertNotIn('transcription', review)
        notes = [a for a in review['advisories'] if a['code'] == 'LIGHTING_NOT_DECLARED']
        self.assertEqual(len(notes), 1)
        self.assertIn('لا تمنع الاعتماد', notes[0]['message'])
        self.assertNotRegex(notes[0]['message'], '[A-Za-z]')


if __name__ == '__main__':
    unittest.main()
