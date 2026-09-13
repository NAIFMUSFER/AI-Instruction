"""Read-only UI packet regressions; all data is synthetic and temporary."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError
from acs_plan_projection import project
from tools.acs_plan_review_packet import build_review_packet, write_review_packet, main
from test_plan_store import warehouse, verifier, element

BRIEF = 'أرض عرضها 30 متر. PRIVATE_BRIEF_SENTINEL'


def workspace(typology='warehouse'):
    model = warehouse()
    if typology == 'residential':
        model['meta']['type'] = 'residential'
        model['floors']['ground']['rooms'] = [
            {'id':'majlis','name':'المجلس','role':'majlis','walls':'none','rect':[0.,0.,20.,30.]},
            {'id':'elevator','name':'المصعد','role':'elevator','walls':'none','rect':[20.,0.,10.,30.]},
        ]
    first = model['floors']['ground']['rooms'][0]
    first['name'] = first.get('name', 'منطقة الاستلام')
    first['requirement_ids'] = ['width']
    start = BRIEF.index('30')
    req = [{'id':'width','source':'requested','evidence':'30','source_id':'brief-test',
            'source_span':{'start':start,'end':start+2},'metric':'site_width_m','expected':30.0}]
    ws = PlanLockWorkspace(verifier=verifier)
    r = ws.propose(model, brief=BRIEF, requirements=req, expected_head=None, note='PRIVATE_NOTE_SENTINEL')
    return ws, r


def payload(packet):
    return json.loads(packet['payload_json'])


class ReviewPacketTests(unittest.TestCase):
    def test_exact_canonical_projection_without_mutation_or_approval(self):
        ws, r = workspace(); before = ws.history()
        p = payload(build_review_packet(ws, r.id))
        self.assertEqual(p['projections'][0], project(r, 0))
        self.assertEqual(ws.history(), before)
        self.assertIsNone(ws.baseline)
        self.assertTrue(p['read_only'])
        self.assertNotIn('can_approve', p['review'])

    def test_receipt_hash_uses_exact_utf8_payload_bytes(self):
        ws, r = workspace(); packet=build_review_packet(ws,r.id)
        self.assertEqual(hashlib.sha256(packet['payload_json'].encode()).hexdigest(),packet['payload_sha256'])
        self.assertIn('منطقة الاستلام',packet['payload_json'])

    def test_raw_brief_evidence_and_notes_are_not_exported(self):
        ws,r=workspace();raw=json.dumps(build_review_packet(ws,r.id))
        self.assertNotIn('PRIVATE_BRIEF_SENTINEL',raw)
        self.assertNotIn('PRIVATE_NOTE_SENTINEL',raw)
        p=payload(build_review_packet(ws,r.id))
        self.assertNotIn('evidence',p['requirements'][0])
        self.assertIn('source_span',p['requirements'][0])

    def test_warehouse_semantic_locks_are_visible_but_not_changed(self):
        ws,r=workspace()
        r=ws.replace_semantic_locks([element('racks','rack_a','storage'),element('docks','dock_n1','receiving')], expected_head=r.id,note='lock anchors')
        p=payload(build_review_packet(ws,r.id))
        self.assertEqual(len(p['locks']['semantic']),2)
        self.assertEqual(p['scorecard']['typology'],'warehouse')
        self.assertEqual(ws.head,r.id)

    def test_residential_room_lock_and_historical_revision_are_preserved(self):
        ws,r=workspace('residential')
        locked=ws.set_room_lock(('ground','elevator'),locked=True,expected_head=r.id)
        self.assertEqual(payload(build_review_packet(ws,locked.id))['locks']['rooms'],[['ground','elevator']])
        old=payload(build_review_packet(ws,r.id))
        self.assertEqual(old['revision']['id'],r.id)
        self.assertEqual(old['locks']['rooms'],[])
        self.assertEqual(ws.head,locked.id)

    def test_invalid_geometry_is_not_silently_drawn(self):
        ws,r=workspace();bad=copy.deepcopy(r.model);bad['floors']['ground']['rooms'][1]['rect']=[0.,0.,20.,30.]
        draft=ws.propose(bad,brief=r.brief,requirements=json.loads(r.requirements_json),expected_head=r.id,note='invalid')
        with self.assertRaises(PlanError) as got: build_review_packet(ws,draft.id)
        self.assertEqual(got.exception.code,'INVALID_GEOMETRY')

    def test_failed_program_remains_visible_not_approved(self):
        ws,r=workspace();req=json.loads(r.requirements_json);req[0]['expected']=31.
        draft=ws.propose(r.model,brief=r.brief,requirements=req,expected_head=r.id,note='mismatch')
        p=payload(build_review_packet(ws,draft.id))
        self.assertEqual(p['review']['scopes']['program'],'FAIL')
        self.assertIn('REQUIREMENT_MISMATCH',[i['code'] for i in p['review']['issues']])
        self.assertIsNone(ws.baseline)

    def test_existing_output_is_never_overwritten(self):
        ws,r=workspace()
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'review.json';write_review_packet(ws,r.id,out);before=out.read_bytes()
            with self.assertRaises(FileExistsError):write_review_packet(ws,r.id,out)
            self.assertEqual(out.read_bytes(),before)

    def test_mismatched_review_receipt_fails_before_publication(self):
        ws,r=workspace();old=ws.review
        ws.review=lambda rid: dict(old(rid),model_hash='0'*64)
        with self.assertRaises(PlanError) as got:build_review_packet(ws,r.id)
        self.assertEqual(got.exception.code,'REVIEW_REVISION_CHANGED')

    def test_cli_uses_existing_validator_without_generating(self):
        ws,r=workspace()
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'input.json';out=Path(tmp)/'out.json'
            src.write_text(json.dumps({'building':r.model,'brief':r.brief,'requirements':json.loads(r.requirements_json)}))
            main([str(src),str(out)])
            self.assertTrue(payload(json.loads(out.read_text()))['read_only'])
            self.assertNotIn('acs_understand',sys.modules)


def fixtures(directory):
    directory.mkdir(parents=True,exist_ok=True)
    for kind in ('warehouse','residential'):
        ws,r=workspace(kind)
        if kind=='warehouse':r=ws.replace_semantic_locks([element('racks','rack_a','storage'),element('docks','dock_n1','receiving')],expected_head=r.id,note='lock anchors')
        else:r=ws.set_room_lock(('ground','elevator'),locked=True,expected_head=r.id)
        write_review_packet(ws,r.id,directory/(kind+'.acs-review.json'))


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--fixtures':fixtures(Path(sys.argv[2]))
    else:unittest.main(verbosity=2)
