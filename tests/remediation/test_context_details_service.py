"""Fresh-only default object admission on synthetic provider results and stores."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import acs_workspace_service as S
import acs_workspace_http as H
from acs_plan_review import PlanError
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from acs_plan_persisted_commands import execute_persisted_plan_command
from test_connected_workspace import model, stair_core_model, command, Runner, PROJECT, ACTOR


def porch_model():
    building=model()
    building['floors']['ground']['rooms'][0].update(role='porch',covered=True)
    return building


class ContextDetailsService(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db=SQLitePlanStore(Path(self.temp.name)/'plans.sqlite3');self.db.create_project(PROJECT,owner_id=ACTOR)
        self.store=SQLitePlanStoreAdapter(self.db)
        self.provider=self.enterContext(patch('acs_understand.call_llm',side_effect=AssertionError('paid provider forbidden')))

    def tearDown(self):self.provider.assert_not_called()

    def seed(self, building):
        ws=S.workspace(self.store,PROJECT,ACTOR);head=ws.head
        revision=ws.propose(building,brief=command()['brief'],requirements=command()['requirements'],expected_head=head,note='Synthetic existing context')
        self.store.save_revision(PROJECT,actor_id=ACTOR,revision=revision,expected_head=head)
        return revision

    def test_fresh_context_objects_enter_canonical_revision_with_source_and_one_runner_call(self):
        original=porch_model();runner=Runner(original)
        rid=S.generate_and_save(self.store,PROJECT,ACTOR,command(),runner=runner)
        built=S.workspace(self.store,PROJECT,ACTOR).get(rid).model
        objects=built['floors']['ground']['rooms'][0].get('objects',[])
        self.assertTrue(objects,'fresh covered porch needs explicit canonical context objects')
        self.assertTrue(any(obj.get('kind')=='column' for obj in objects))
        self.assertEqual(built['meta']['acs_context_details'],{'schema':'acs.context-details/1','source':'system_default','conceptual_only':True})
        self.assertTrue(all(obj.get('id') and obj.get('context_detail_provenance',{}).get('conceptual_only') is True for obj in objects))
        for before,after in zip(original['floors']['ground']['rooms'],built['floors']['ground']['rooms']):
            for key,value in before.items():self.assertEqual(after[key],value)
        self.assertEqual(original,porch_model());self.assertEqual(len(runner.calls),1)
        revision=S.workspace(self.store,PROJECT,ACTOR).get(rid)
        self.assertEqual(json.loads(revision.requirements_json),command()['requirements'])
        review=S.workspace(self.store,PROJECT,ACTOR).review(rid)
        self.assertTrue(review['can_approve'],review['issues'])
        execute_persisted_plan_command(self.store,PROJECT,
            {'action':'approve','expected_head':rid,'confirmed':True,'acknowledge_concept_only':True},
            actor_id=ACTOR,verifier=S.existing_geometry_verifier)
        artifact=S.artifact(self.store,PROJECT,ACTOR,{'action':'artifact','revision_id':rid,'format':'gltf'})
        self.assertEqual(artifact['receipt']['model_hash'],revision.model_hash)
        self.assertEqual(artifact['receipt']['provider_calls'],0)
        reopened=S.workspace(SQLitePlanStoreAdapter(SQLitePlanStore(self.db.path)),PROJECT,ACTOR)
        self.assertEqual(reopened.get(rid).model,built)
        self.assertEqual(reopened.handoff(rid)['baseline']['model_hash'],revision.model_hash)
        self.assertEqual(len(runner.calls),1)

    def test_context_helper_runs_after_stairs_and_roof_with_no_second_provider_request(self):
        import acs_context_details
        candidate=stair_core_model()
        for floor in candidate['floors'].values():floor['rooms'][0].update(role='porch',covered=True)
        seen=[];real=acs_context_details.with_context_details
        def after_structure(building):
            self.assertTrue(any(level.get('kind')=='roof' for level in building['levels']))
            self.assertTrue(any(obj.get('form')=='u_return' for floor in building['floors'].values() for room in floor['rooms'] for obj in room.get('objects',[])))
            seen.append(True);return real(building)
        runner=Runner(candidate)
        with patch('acs_context_details.with_context_details',side_effect=after_structure):
            S.generate_and_save(self.store,PROJECT,ACTOR,command(),runner=runner)
        self.assertEqual(seen,[True]);self.assertEqual(len(runner.calls),1)

    def test_provider_cannot_forge_reserved_report_or_object_provenance_before_any_helper(self):
        cases=[]
        for report in (None,{'schema':'acs.context-details/1','source':'system_default','conceptual_only':True}):
            candidate=porch_model();candidate['meta']['acs_context_details']=report;cases.append(candidate)
        for field in ('kind','name'):
            candidate=porch_model();candidate['floors']['ground']['rooms'][0]['objects']=[
                {'id':'forged',field:'column','context_detail_provenance':None}];cases.append(candidate)
        for index,candidate in enumerate(cases):
            with self.subTest(case=index):
                project='forged-'+str(index);self.db.create_project(project,owner_id=ACTOR);runner=Runner(candidate)
                with patch('acs_stairs.with_default_stairs') as stairs,patch('acs_context_details.with_context_details') as context:
                    with self.assertRaises(PlanError) as rejected:S.generate_and_save(self.store,project,ACTOR,command(),runner=runner)
                    stairs.assert_not_called();context.assert_not_called()
                self.assertEqual(rejected.exception.code,'PROVIDER_AUTHORITY_FIELD')
                ws=S.workspace(self.store,project,ACTOR);self.assertIsNone(ws.head);self.assertEqual(ws.history(),[])
                self.assertEqual(len(runner.calls),1)

    def test_source_preserve_and_revise_never_add_default_objects(self):
        source='44444444-4444-4444-8444-444444444444'
        row={'id':source,'sha256':'a'*64,'page':1,'page_count':1,'preview_sha256':'b'*64,'preview_media_type':'image/png'}
        for mode in ('preserve','revise'):
            with self.subTest(mode=mode):
                self.db.create_project(mode,owner_id=ACTOR);candidate=porch_model();runner=Runner(candidate)
                with patch('acs_plan_sources.read_source',return_value=(row,b'synthetic-preview')),patch('acs_context_details.with_context_details') as helper:
                    rid=S.generate_and_save(self.store,mode,ACTOR,dict(command(),source_id=source,source_mode=mode),runner=runner)
                    helper.assert_not_called()
                built=S.workspace(self.store,mode,ACTOR).get(rid).model
                self.assertEqual(built['floors']['ground'],candidate['floors']['ground']);self.assertNotIn('acs_context_details',built['meta'])
                self.assertEqual(len(runner.calls),1)

    def test_existing_generation_and_resumed_initial_job_keep_original_context(self):
        candidate=porch_model();first=self.seed(candidate);runner=Runner(candidate)
        with patch('acs_context_details.with_context_details') as helper:
            rid=S.generate_and_save(self.store,PROJECT,ACTOR,dict(command(),expected_head=first.id),runner=runner);helper.assert_not_called()
        built=S.workspace(self.store,PROJECT,ACTOR).get(rid).model
        self.assertEqual(built['floors']['ground'],candidate['floors']['ground']);self.assertNotIn('acs_context_details',built['meta'])
        self.db.create_project('resumed',owner_id=ACTOR);runner=Runner(candidate)
        prior={'resume_command':command(),'checkpoint':{'kind':'outline'},'provider_calls':1}
        with patch.object(H,'_read_job',return_value=prior),patch('acs_context_details.with_context_details') as helper:
            rid=S.generate_and_save(self.store,'resumed',ACTOR,dict(command(),resume_job_id='55555555-5555-4555-8555-555555555555'),runner=runner);helper.assert_not_called()
        built=S.workspace(self.store,'resumed',ACTOR).get(rid).model
        self.assertEqual(built['floors']['ground'],candidate['floors']['ground']);self.assertEqual(runner.calls[0][1]['used_calls'],1)

    def test_remove_edit_and_restore_keep_removed_default_absent_without_reauthoring(self):
        rid=S.generate_and_save(self.store,PROJECT,ACTOR,command(),runner=Runner(porch_model()))
        first=S.workspace(self.store,PROJECT,ACTOR).get(rid).model
        oid=first['floors']['ground']['rooms'][0]['objects'][0]['id']
        def execute(body):return execute_persisted_plan_command(self.store,PROJECT,body,actor_id=ACTOR,verifier=S.existing_geometry_verifier)
        with patch('acs_context_details.with_context_details') as helper:
            removed=execute({'action':'remove_object','expected_head':rid,'room_ref':['ground','a'],'object_id':oid,'confirm_new_draft':False})['head']
            snapshot=S.workspace(self.store,PROJECT,ACTOR).get(removed).model
            edited=S.edit_geometry(self.store,PROJECT,ACTOR,{'action':'edit_geometry','expected_head':removed,'room_ref':['ground','b'],'rect':[10,0,7,8]})['head']
            restored=execute({'action':'restore','expected_head':edited,'source_revision_id':removed,'note':'Restore exact removed-object draft'})['head']
            helper.assert_not_called()
        current=S.workspace(self.store,PROJECT,ACTOR).get(restored).model
        self.assertEqual(current,snapshot)
        self.assertNotIn(oid,[obj['id'] for obj in current['floors']['ground']['rooms'][0]['objects']])
        self.assertEqual(current['meta']['acs_context_details'],first['meta']['acs_context_details'])

    def test_resource_failure_does_not_save_or_retry_and_async_polling_is_actionable(self):
        candidate=porch_model();runner=Runner(candidate)
        with patch('acs_context_details.with_context_details',return_value=(candidate,None,'CONTEXT_DETAILS_RESOURCE_LIMIT')):
            with self.assertRaises(PlanError) as rejected:S.generate_and_save(self.store,PROJECT,ACTOR,command(),runner=runner)
        self.assertEqual(rejected.exception.code,'CONTEXT_DETAILS_RESOURCE_LIMIT');self.assertIn('قلّل',str(rejected.exception))
        self.assertEqual(H._job_view({'id':'job','state':'FAILED','error_code':rejected.exception.code})['job']['error_message'],str(rejected.exception))
        ws=S.workspace(self.store,PROJECT,ACTOR);self.assertIsNone(ws.head);self.assertEqual(ws.history(),[]);self.assertEqual(len(runner.calls),1)

    def test_malformed_rooms_retain_original_canonical_error(self):
        candidate=stair_core_model();candidate['floors']['ground']['rooms']=[None]
        with self.assertRaises(PlanError) as rejected:S.generate_and_save(self.store,PROJECT,ACTOR,command(),runner=Runner(candidate))
        self.assertEqual(rejected.exception.code,'AMBIGUOUS_ROOM_ID')

    def test_malformed_unicode_retains_canonical_error_without_saving_or_retry(self):
        candidate=porch_model();candidate['meta']['note']='\ud800';runner=Runner(candidate)
        with self.assertRaises(PlanError) as rejected:
            S.generate_and_save(self.store,PROJECT,ACTOR,command(),runner=runner)
        self.assertEqual(rejected.exception.code,'INVALID_JSON_VALUE')
        self.assertEqual(len(runner.calls),1)
        self.assertEqual(S.workspace(self.store,PROJECT,ACTOR).history(),[])
        self.assertIsNone(S.workspace(self.store,PROJECT,ACTOR).head)

    def test_stale_initial_response_never_calls_context_helper(self):
        parent=self
        class Race(Runner):
            def run(self,*args,**kwargs):parent.seed(model());return super().run(*args,**kwargs)
        runner=Race(porch_model())
        with patch('acs_context_details.with_context_details') as helper,self.assertRaises(PlanError) as rejected:
            S.generate_and_save(self.store,PROJECT,ACTOR,command(),runner=runner)
        helper.assert_not_called();self.assertEqual(rejected.exception.code,'STALE_REVISION')
        self.assertEqual(len(S.workspace(self.store,PROJECT,ACTOR).history()),1);self.assertEqual(len(runner.calls),1)


if __name__=='__main__':unittest.main()
