"""A plan read from the owner's own file is approved as a disclosed transcription.

Replays the 2026-11-26 live paid reads (fixtures/plan_reads: a CAD ground
floor, a hand sketch, the upper floor of a two-page PDF). Before this fix every
room got «بلا باب» and «بلا إنارة» and none of them could be approved or
exported. The read now keeps the doors and windows it can see on each room's
own wall (a window on an interior wall or over a door is left out and counted,
never a blocking finding); lighting never blocks a
concept; on a transcription, unseen doors and paths are advisory notes with
the disclosure «المخطط مقروء من ملفك؛ الأبواب والنوافذ المرئية فقط مرسومة», and the
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

    def test_a_read_with_doors_approves_and_compiles_to_3d(self):
        # Live 2026-11-26 (the owner's photographed PDF): the read kept its
        # drawn doors without a material, the transcription was approved, and
        # «عرض 3D» failed with DOWNSTREAM_GEOMETRY_NOT_SPECIFIED. The recorded
        # fixtures carry no doors, so they never reached this check.
        case = fixture('a_cad_ground')
        building = copy.deepcopy(case['read'])
        rooms = building['floors']['ground']['rooms']
        rooms[0]['doors'] = [{'edge': 'S', 'offset': 3, 'width': 0.9}]
        rooms[2]['doors'] = [{'edge': 'E', 'offset': 2.5, 'width': 0.9}]
        rid = self.save(case, building=building)
        revision = S.workspace(self.store, PROJECT, ACTOR).get(rid)
        doors = [d for f in revision.model['floors'].values() for r in f['rooms'] for d in r['doors']]
        self.assertEqual(len(doors), 2)
        self.assertTrue(all(d['material'] == SRC.DOOR_MATERIAL and d['height'] == 2.1 for d in doors))
        self.assertIn(SRC.DOOR_DEFAULTS_NOTE, revision.model['meta']['assumptions'])
        self.approve(rid, acknowledge_transcription=True)
        out = S.artifact(self.store, PROJECT, ACTOR, {'action': 'artifact', 'revision_id': rid, 'format': 'gltf'})
        self.assertTrue(base64.b64decode(out['data_base64']))

    def test_a_read_with_doors_and_windows_approves_and_compiles_to_3d(self):
        # A read used to drop every window, so the plan compiled to 3D with
        # blank exterior walls. The windows drawn on a room's own outer wall
        # are kept with the stated sill and height; the rest are left out and
        # counted, never turned into a finding that blocks the transcription.
        case = fixture('a_cad_ground')
        building = copy.deepcopy(case['read'])
        rooms = {r['id']: r for r in building['floors']['ground']['rooms']}
        rooms['r1']['doors'] = [{'edge': 'S', 'offset': 3, 'width': 0.9}]
        rooms['r1']['windows'] = [
            {'edge': 'N', 'offset': 3, 'width': 1.5, 'sill': 0.2, 'height': 2.6, 'id': 'provider-w'},
            {'edge': 'W', 'offset': 2.75, 'width': 1.2},
            {'edge': 'E', 'offset': 2, 'width': 1.2},       # interior wall shared with the kitchen
            {'edge': 'N', 'offset': 7, 'width': 1.2}]       # beyond the 6 m wall
        rooms['r2']['windows'] = [{'edge': 'E', 'offset': 2.75, 'width': 1.2},
                                  {'edge': 'N', 'offset': 2.5, 'width': 0.2}]   # not a window width
        rooms['r6']['doors'] = [{'edge': 'S', 'offset': 5.5, 'width': 1.0}]
        rooms['r6']['windows'] = [{'edge': 'S', 'offset': 5.8, 'width': 1.6},   # over the door
                                  {'edge': 'S', 'offset': 9, 'width': 2},
                                  {'edge': 'E', 'offset': 3.5, 'width': 1.5}]
        rid = self.save(case, building=building)
        revision = S.workspace(self.store, PROJECT, ACTOR).get(rid)
        saved = {r['id']: r for f in revision.model['floors'].values() for r in f['rooms']}
        def drawn(rid):
            return [{k: w[k] for k in ('edge', 'offset', 'width', 'sill', 'height')} for w in saved[rid]['windows']]
        self.assertEqual(drawn('r1'), [{'edge': 'N', 'offset': 3, 'width': 1.5, 'sill': 0.9, 'height': 1.4},
                                       {'edge': 'W', 'offset': 2.75, 'width': 1.2, 'sill': 0.9, 'height': 1.4}])
        self.assertEqual(drawn('r2'), [{'edge': 'E', 'offset': 2.75, 'width': 1.2, 'sill': 0.9, 'height': 1.4}])
        self.assertEqual(drawn('r6'), [{'edge': 'S', 'offset': 9, 'width': 2, 'sill': 0.9, 'height': 1.4},
                                       {'edge': 'E', 'offset': 3.5, 'width': 1.5, 'sill': 0.9, 'height': 1.4}])
        self.assertEqual([w for r in ('r3', 'r4', 'r5') for w in saved[r]['windows']], [])
        ids = [w['id'] for r in saved.values() for w in r['windows']]
        self.assertNotIn('provider-w', ids)
        self.assertEqual(len(set(ids)), 5, 'every kept window has its own stable id')
        assumptions = revision.model['meta']['assumptions']
        self.assertEqual(assumptions.count(SRC.WINDOW_DEFAULTS_NOTE), 1, 'the defaults are disclosed once')
        self.assertIn(SRC.DOOR_DEFAULTS_NOTE, assumptions)
        self.assertTrue(any('تُركت 4 من النوافذ المقروءة' in a for a in assumptions), assumptions)
        view = S.view(self.store, PROJECT, ACTOR)
        self.assertEqual([f for f in view['review_findings'] if f.get('severity') != 'advisory'], [])
        self.assertFalse([f for f in view['review_findings'] if 'نافذة' in f['message']])
        self.assertTrue(view['authority']['can_approve_concept'])
        self.assertEqual(sum(1 for o in view['openings'] if o['kind'] == 'windows'), 5)
        self.approve(rid, acknowledge_transcription=True)
        out = S.artifact(self.store, PROJECT, ACTOR, {'action': 'artifact', 'revision_id': rid, 'format': 'gltf'})
        glazing = [n['name'] for n in json.loads(base64.b64decode(out['data_base64']))['nodes']
                   if str(n.get('name', '')).startswith('WINDOW|')]
        self.assertEqual(sorted(glazing), ['WINDOW|F0|r1|0', 'WINDOW|F0|r1|1', 'WINDOW|F0|r2|0',
                                           'WINDOW|F0|r6|0', 'WINDOW|F0|r6|1'], 'the 3D walls carry the windows')
        self.assertEqual(sorted(m['source']['element_id'] for m in out['receipt']['source_map']
                                if m['source'].get('collection') == 'windows'), sorted(ids))
        for fmt, extra in (('svg', {'level_index': 0}), ('dxf', {'level_index': 0}), ('pdf', {}), ('ifc', {})):
            out = S.artifact(self.store, PROJECT, ACTOR, dict({'action': 'artifact', 'revision_id': rid,
                                                               'format': fmt}, **extra))
            self.assertTrue(base64.b64decode(out['data_base64']), fmt)

    def test_the_upper_floor_alone_is_blocked_only_by_the_confirmed_floor_count(self):
        # Two floors confirmed, one page mapped: refused before the paid read
        # (it used to be read, paid, and then fail the floor-count check).
        case = fixture('d_upper_floor')
        with self.assertRaises(PlanError) as caught:
            self.save(case)
        self.assertEqual(caught.exception.code, 'SOURCE_FLOOR_COUNT_MISMATCH')
        # Read alone (one floor confirmed), only that count would still differ.
        one = copy.deepcopy(case)
        one['requirements'] = [r for r in one['requirements'] if r['metric'] != 'level_count']
        self.save(one)
        view = S.view(self.store, PROJECT, ACTOR)
        self.assertTrue(view['authority']['can_approve_concept'],
                        [f for f in view['review_findings'] if f.get('severity') != 'advisory'])

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

    def test_instruction_asks_for_drawn_windows_in_every_mode_and_invents_none(self):
        case = fixture('a_cad_ground')
        for mode in ('preserve', 'revise', 'complete'):
            with self.subTest(mode=mode):
                _, sent = read(case, mode)
                system = sent[0]['system_override']
                self.assertIn('النوافذ المرسومة في الصورة فقط', system)
                self.assertIn('لا تختلق نوافذ غير مرسومة', system)
                self.assertIn('windows=[]', system)
                self.assertNotIn('أو نوافذ', system, 'windows are no longer forbidden outright')

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
        self.assertEqual([{k: d[k] for k in ('edge', 'offset', 'width', 'height', 'material')} for d in out[0]['doors']],
                         [{'edge': 'S', 'offset': 3, 'width': 1.0, 'height': 2.1, 'material': 'wood'}])
        self.assertNotEqual(out[0]['doors'][0]['id'], 'provider-id')
        self.assertNotIn('points', out[0])
        # The window drawn on the kitchen's outer wall is kept as drawn, with
        # the stated sill and height; nothing else is added.
        self.assertEqual([{k: w[k] for k in ('edge', 'offset', 'width', 'sill', 'height')} for w in out[1]['windows']],
                         [{'edge': 'N', 'offset': 1, 'width': 1, 'sill': 0.9, 'height': 1.4}])
        self.assertEqual([w for r in out if r is not out[1] for w in r['windows']], [], 'no window is invented')
        self.assertTrue(any('تُركت 1 فتحة باب' in a for a in result['building']['meta']['assumptions']))
        self.assertEqual(result['building']['_opening_identity']['schema'], 'acs.opening-identity/1')
        # Every room has an explicit opening list, so topology is evaluated.
        review = existing_geometry_verifier(json.loads(json.dumps(result['building'])))
        self.assertIn(review['scopes']['topology'], ('PASS', 'NOT_VERIFIED', 'FAIL'))

    def test_the_stated_defaults_are_disclosed_once_across_floors(self):
        reads = []
        for level in (0, 1):
            building = copy.deepcopy(fixture('a_cad_ground')['read'])
            building['floors']['ground']['rooms'][0]['doors'] = [{'edge': 'S', 'offset': 3, 'width': 0.9}]
            building['floors']['ground']['rooms'][1]['windows'] = [{'edge': 'N', 'offset': 1, 'width': 1}]
            reads.append((level, SRC.read_rooms(building, ids=False)))
        assumptions = SRC.merge_floors(reads)['meta']['assumptions']
        self.assertEqual(assumptions.count(SRC.DOOR_DEFAULTS_NOTE), 1)
        self.assertEqual(assumptions.count(SRC.WINDOW_DEFAULTS_NOTE), 1)


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



class SeveralFloorsInOneRead(Store):
    """U4: the two pages of the PDF (fixture a is page 1, fixture d is page 2)."""
    UPPER = '66666666-6666-4666-8666-666666666666'

    def floors_command(self, **extra):
        case = fixture('d_upper_floor')     # confirms two floors
        return dict(command(case), source_read={'floors': [{'source_id': SOURCE, 'level': 0},
                                                           {'source_id': self.UPPER, 'level': 1}]}, **extra)

    def test_two_pages_are_read_once_each_and_merged_with_one_stair_core(self):
        import acs_understand as U
        ground, upper = fixture('a_cad_ground')['read'], fixture('d_upper_floor')['read']
        upper = dict(upper, levels=[{'index': 0, 'template': 'first'}])   # each page is read alone
        upper['floors']['first']['rooms'][1]['rect'] = [9.6, 6.9, 3, 5]  # 10 cm reading noise on the stair
        replies, sent = [ground, upper], []

        def provider(*args, **kwargs):
            consume()
            sent.append(kwargs)
            return json.dumps(replies[len(sent) - 1], ensure_ascii=False)
        image = base64.b64encode(picture()).decode()
        case = fixture('d_upper_floor')
        with patch.object(U, 'call_llm', side_effect=provider):
            result = SRC.candidate(case['brief'], case['requirements'], 'A', 4, {'mode': 'preserve', 'floors': [
                {'image': image, 'media_type': 'image/png', 'level': 0},
                {'image': image, 'media_type': 'image/png', 'level': 1}]})
        self.assertEqual(result['provider_calls'], 2, 'one vision call per floor')
        self.assertIn('الدور الأول', sent[1]['system_override'])
        self.assertIn('الدور الأرضي المقروء', sent[1]['content'][1]['text'], 'upper floor read in the ground frame')
        building = result['building']
        self.assertEqual([(l['index'], l['template']) for l in building['levels']], [(0, 'ground'), (1, 'floor_1')])
        cores = {t: [(r['core_id'], r['rect']) for r in building['floors'][t]['rooms'] if r.get('core_id')]
                 for t in ('ground', 'floor_1')}
        self.assertEqual(cores['ground'], [('stair_core_1', [9.5, 7, 3, 5])])
        self.assertEqual(cores['floor_1'], [('stair_core_1', [9.5, 7, 3, 5])], 'reading noise snapped, disclosed')
        self.assertTrue(any('وُحّد موضع الدرج' in a for a in building['meta']['assumptions']))
        # Saved, reviewed, approved as a transcription and exported per floor.
        rows = {SOURCE: row(), self.UPPER: dict(row(), id=self.UPPER, page=2, page_count=2)}
        with patch.object(SRC, 'read_source', side_effect=lambda s, p, sid, part='original': (rows[sid], picture())), \
                patch.object(SRC, 'source', side_effect=lambda s, p, sid: rows[sid]):
            rid = S.generate_and_save(self.store, PROJECT, ACTOR, self.floors_command(), runner=Runner(building))
        saved = S.workspace(self.store, PROJECT, ACTOR).get(rid).model
        self.assertEqual([f['level'] for f in saved['meta']['acs_plan_source']['floors']], [0, 1])
        view = S.view(self.store, PROJECT, ACTOR)
        self.assertTrue(view['authority']['can_approve_concept'], [f for f in view['review_findings'] if f.get('severity') != 'advisory'])
        scopes = json.loads(view['review_packet']['payload_json'])['review']['scopes']
        self.assertEqual(scopes['vertical_circulation'], 'PASS')
        self.approve(rid, acknowledge_transcription=True)
        for level in (0, 1):
            out = S.artifact(self.store, PROJECT, ACTOR, {'action': 'artifact', 'revision_id': rid, 'format': 'dxf', 'level_index': level})
            self.assertTrue(base64.b64decode(out['data_base64']))
        out = S.artifact(self.store, PROJECT, ACTOR, {'action': 'artifact', 'revision_id': rid, 'format': 'ifc'})
        self.assertTrue(base64.b64decode(out['data_base64']))

    def test_the_confirmed_floor_count_and_budget_are_checked_before_paying(self):
        single = dict(command(fixture('d_upper_floor')))
        with self.assertRaises(PlanError) as caught:
            S.generation_command(single)
        self.assertEqual(caught.exception.code, 'SOURCE_FLOOR_COUNT_MISMATCH')
        self.assertIn('أكدت 2', str(caught.exception))
        with self.assertRaises(PlanError) as caught:
            S.generation_command(self.floors_command(max_provider_calls=1))
        self.assertEqual(caught.exception.code, 'INVALID_BUDGET')
        for floors in ([{'source_id': SOURCE, 'level': 0}, {'source_id': SOURCE, 'level': 1}],
                       [{'source_id': self.UPPER, 'level': 0}, {'source_id': SOURCE, 'level': 1}],
                       [{'source_id': SOURCE, 'level': 0}, {'source_id': self.UPPER, 'level': 2}]):
            with self.assertRaises(PlanError):
                S.generation_command(dict(self.floors_command(), source_read={'floors': floors}))
        self.assertEqual(len(S.generation_command(self.floors_command())['source_read']['floors']), 2)


if __name__ == '__main__':
    unittest.main()
