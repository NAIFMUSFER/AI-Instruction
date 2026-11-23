"""Canonical object removal through real command/store/HTTP boundaries; no provider."""
from __future__ import annotations
import asyncio
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_plan_commands as C
import acs_plan_http as HTTP
import acs_workspace_service as S
from acs_plan_persisted_commands import execute_persisted_plan_command
from acs_plan_review import PlanError, digest
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from test_connected_workspace import model, command, PROJECT, ACTOR
from test_plan_http_command_boundary import _scope, _receive_for, _json_response


def object_model():
    building = model()
    building['meta']['acs_context_details'] = {'schema':'acs.context-details/1', 'source':'system_default', 'conceptual_only':True}
    building['floors']['ground']['rooms'][0]['objects'] = [
        {'id':'item-'+kind,'kind':kind,'x':1+index,'y':0,'z':1,'w':.4,'d':.4,'h':1,
         'rot':0,'count':1,'pitch':1,'dir':'x','requirement_ids':['width'],
         'context_detail_provenance':{'schema':'acs.context-detail/1','source':'system_default',
             'conceptual_only':True,'context':'courtyard','assumptions':['Synthetic fixture; no engineering claim.']}}
        for index,kind in enumerate(('column','railing','plant','planter'))]
    return building


class Fixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db = SQLitePlanStore(Path(self.temp.name)/'plans.sqlite3')
        self.db.create_project(PROJECT,owner_id=ACTOR);self.store = SQLitePlanStoreAdapter(self.db)
        self.first = self.seed(object_model())
        self.provider = self.enterContext(patch('acs_understand.call_llm',side_effect=AssertionError('paid call forbidden')))
        self.edit_provider = self.enterContext(patch('acs_understand.apply_notes',side_effect=AssertionError('paid edit forbidden')))
        self.runner = self.enterContext(patch('acs_generation_job.default_runner',side_effect=AssertionError('worker forbidden')))

    def seed(self, building):
        ws = S.workspace(self.store,PROJECT,ACTOR)
        expected = ws.head
        revision = ws.propose(building,brief=command()['brief'],requirements=command()['requirements'],expected_head=expected,note='Synthetic object fixture')
        self.store.save_revision(PROJECT,actor_id=ACTOR,revision=revision,expected_head=expected)
        return revision

    def body(self, **changes):
        return dict({'action':'remove_object','expected_head':self.first.id,'room_ref':['ground','a'],
                     'object_id':'item-plant','confirm_new_draft':False},**changes)

    def execute(self, body, actor=ACTOR):
        return execute_persisted_plan_command(self.store,PROJECT,body,actor_id=actor,verifier=S.existing_geometry_verifier)

    def unchanged_failure(self, code, body, actor=ACTOR):
        before = S.workspace(self.store,PROJECT,ACTOR);history = before.history();head = before.get(before.head).model
        with self.assertRaises(PlanError) as rejected:self.execute(body,actor)
        self.assertEqual(rejected.exception.code,code)
        after = S.workspace(self.store,PROJECT,ACTOR)
        self.assertEqual(after.history(),history);self.assertEqual(after.get(after.head).model,head)
        return rejected.exception

    def tearDown(self):
        self.provider.assert_not_called();self.edit_provider.assert_not_called();self.runner.assert_not_called()


class RemoveObjectCommands(Fixture,unittest.TestCase):
    def test_remove_is_exact_canonical_revision_with_diff_attribution_and_reopen(self):
        before = self.first.model;removed = before['floors']['ground']['rooms'][0]['objects'][2]
        out = self.execute(self.body())
        self.assertTrue(out['persistence']['revision_persisted']);self.assertFalse(out['persistence']['approval_persisted'])
        reopened = S.workspace(SQLitePlanStoreAdapter(SQLitePlanStore(self.db.path)),PROJECT,ACTOR)
        actual = reopened.get(out['head']).model;expected = copy.deepcopy(before)
        del expected['floors']['ground']['rooms'][0]['objects'][2]
        self.assertEqual(actual,expected);self.assertEqual(reopened.get(self.first.id).model,before)
        self.assertEqual(reopened.get(out['head']).requirements_json,self.first.requirements_json)
        changes = out['semantic_diff']['changes']
        deletion = next(row for row in changes if row.get('element_id')=='item-plant')
        self.assertEqual(deletion['change'],'removed');self.assertEqual(deletion['before_hash'],digest(removed))
        self.assertEqual(deletion['linked_requirement_ids'],['width'])
        self.assertNotEqual(reopened.get(out['head']).model_hash,self.first.model_hash)

    def test_all_four_supported_kinds_can_be_removed_without_geometry_defaults(self):
        head = self.first.id
        for kind in ('column','railing','plant','planter'):
            out = self.execute(self.body(expected_head=head,object_id='item-'+kind));head = out['head']
        self.assertEqual(S.workspace(self.store,PROJECT,ACTOR).get(head).model['floors']['ground']['rooms'][0]['objects'],[])

    def test_approved_head_requires_server_confirmation_and_keeps_old_approval(self):
        approved = self.execute({'action':'approve','expected_head':self.first.id,'confirmed':True,'acknowledge_concept_only':True})
        old = S.workspace(self.store,PROJECT,ACTOR).handoff(self.first.id)
        self.unchanged_failure('EXPLICIT_CONFIRMATION_REQUIRED',self.body())
        out = self.execute(self.body(confirm_new_draft=True))
        ws = S.workspace(self.store,PROJECT,ACTOR)
        self.assertEqual(ws.baseline,approved['baseline']);self.assertEqual(ws.handoff(self.first.id),old)
        self.assertEqual(next(r['state'] for r in ws.history() if r['revision_id']==out['head']),'DRAFT')
        with self.assertRaises(PlanError) as rejected:ws.handoff(out['head'])
        self.assertEqual(rejected.exception.code,'APPROVAL_REQUIRED')

    def test_unknown_typology_approved_model_removes_exact_object_with_explicit_comparison_limit(self):
        building=object_model();building['meta'].pop('type',None);building['meta'].pop('building_type',None)
        original=self.seed(building)
        state=S.view(self.store,PROJECT,ACTOR,original.id)
        self.assertTrue(state['authority']['can_approve_concept'])
        self.assertTrue(next(row for row in state['object_actions']['items'] if row['object_id']=='item-plant')['supported'])
        self.execute({'action':'approve','expected_head':original.id,'confirmed':True,'acknowledge_concept_only':True})
        approved=S.workspace(self.store,PROJECT,ACTOR).handoff(original.id)
        out=self.execute(self.body(expected_head=original.id,confirm_new_draft=True))
        reopened=S.workspace(SQLitePlanStoreAdapter(SQLitePlanStore(self.db.path)),PROJECT,ACTOR)
        expected=copy.deepcopy(building);del expected['floors']['ground']['rooms'][0]['objects'][2]
        self.assertEqual(reopened.get(out['head']).model,expected)
        self.assertEqual(reopened.get(original.id).model,building)
        self.assertEqual(reopened.handoff(original.id),approved)
        self.assertEqual(reopened.baseline,original.id)
        self.assertEqual(next(row['state'] for row in reopened.history() if row['revision_id']==out['head']),'DRAFT')
        deletion=next(row for row in out['semantic_diff']['changes'] if row.get('element_id')=='item-plant')
        self.assertEqual(deletion['change'],'removed')
        self.assertNotIn('revision_comparison',out)
        unavailable=out['revision_comparison_unavailable']
        self.assertEqual(unavailable['reason'],'OPTION_TYPOLOGY_UNKNOWN')
        self.assertEqual(unavailable['reference_revision_id'],original.id)
        self.assertEqual(unavailable['target_revision_id'],out['head'])
        self.assertIn('نوع المبنى',unavailable['message'])
        with self.assertRaises(PlanError) as rejected:reopened.compare_revisions(original.id,out['head'])
        self.assertEqual(rejected.exception.code,'OPTION_TYPOLOGY_UNKNOWN')

    def test_unrelated_comparison_failure_does_not_save_object_removal(self):
        with patch.object(C.PlanLockWorkspace,'compare_revisions',side_effect=PlanError('OPTION_TYPOLOGY_MISMATCH','Synthetic comparison failure')):
            self.unchanged_failure('OPTION_TYPOLOGY_MISMATCH',self.body())

    def test_unknown_typology_locks_and_restore_preserve_real_authority(self):
        building=object_model();building['meta'].pop('type',None);building['meta'].pop('building_type',None)
        original=self.seed(building)
        locked=self.execute({'action':'set_room_lock','expected_head':original.id,'room_ref':['ground','a'],'locked':True})
        self.assertEqual(locked['revision_comparison_unavailable']['reason'],'OPTION_TYPOLOGY_UNKNOWN')
        self.assertEqual(S.workspace(self.store,PROJECT,ACTOR).get(locked['head']).locked_rooms,(('ground','a'),))
        self.unchanged_failure('LOCK_VIOLATION',self.body(expected_head=locked['head']))
        unlocked=self.execute({'action':'set_room_lock','expected_head':locked['head'],'room_ref':['ground','a'],'locked':False})
        selector={'kind':'element','template':'ground','room_id':'a','collection':'objects','element_id':'item-plant'}
        semantic=self.execute({'action':'replace_semantic_locks','expected_head':unlocked['head'],'selectors':[selector],'note':'Synthetic lock'})
        self.assertEqual(semantic['revision_comparison_unavailable']['reason'],'OPTION_TYPOLOGY_UNKNOWN')
        self.unchanged_failure('LOCK_VIOLATION',self.body(expected_head=semantic['head']))
        cleared=self.execute({'action':'replace_semantic_locks','expected_head':semantic['head'],'selectors':[],'note':'Synthetic unlock'})
        removed=self.execute(self.body(expected_head=cleared['head']))
        restored=self.execute({'action':'restore','expected_head':removed['head'],'source_revision_id':original.id,'note':'Synthetic restore'})
        self.assertEqual(restored['revision_comparison_unavailable']['reason'],'OPTION_TYPOLOGY_UNKNOWN')
        self.assertTrue(restored['semantic_diff']['changes'])
        self.assertEqual(S.workspace(self.store,PROJECT,ACTOR).get(restored['head']).model,building)
        self.unchanged_failure('OPTION_TYPOLOGY_UNKNOWN',{'action':'compare','reference_revision_id':original.id,'target_revision_id':restored['head']})

    def test_unrelated_comparison_failure_does_not_save_room_lock(self):
        with patch.object(C.PlanLockWorkspace,'compare_revisions',side_effect=PlanError('OPTION_TYPOLOGY_MISMATCH','Synthetic comparison failure')):
            self.unchanged_failure('OPTION_TYPOLOGY_MISMATCH',{'action':'set_room_lock','expected_head':self.first.id,'room_ref':['ground','a'],'locked':True})

    def test_stale_duplicate_and_forged_object_identity_leave_history_unchanged(self):
        self.unchanged_failure('OBJECT_NOT_FOUND',self.body(object_id='another-project-object'))
        self.unchanged_failure('OBJECT_NOT_FOUND',self.body(room_ref=['ground','b']))
        out = self.execute(self.body())
        self.unchanged_failure('STALE_REVISION',self.body())
        self.unchanged_failure('OBJECT_NOT_FOUND',self.body(expected_head=out['head']))

    def test_room_whole_element_and_property_locks_block_deletion(self):
        for lock in ('room','element','property'):
            with self.subTest(lock=lock):
                ws = S.workspace(self.store,PROJECT,ACTOR);head=ws.head
                if lock=='room':
                    body={'action':'set_room_lock','expected_head':head,'room_ref':['ground','a'],'locked':True}
                else:
                    selector={'kind':'element','template':'ground','room_id':'a','collection':'objects','element_id':'item-plant'}
                    if lock=='property':selector['properties']=['w']
                    body={'action':'replace_semantic_locks','expected_head':head,'selectors':[selector],'note':'Synthetic object lock'}
                head=self.execute(body)['head']
                self.unchanged_failure('LOCK_VIOLATION',self.body(expected_head=head))
                if lock=='room':self.execute({'action':'set_room_lock','expected_head':head,'room_ref':['ground','a'],'locked':False})

    def test_shared_template_repetition_unsupported_and_ambiguous_ids_fail_closed(self):
        cases=[]
        shared=object_model();shared['levels'].append({'index':1,'template':'ground'});cases.append((shared,'OBJECT_TEMPLATE_SHARED'))
        repeated=object_model();repeated['floors']['ground']['rooms'][0]['objects'][2]['count']=2;cases.append((repeated,'OBJECT_REPETITION_UNSUPPORTED'))
        wrong=object_model();wrong['floors']['ground']['rooms'][0]['objects'][2]['kind']='stairs';cases.append((wrong,'OBJECT_REMOVAL_UNSUPPORTED'))
        duplicate=object_model();duplicate['floors']['ground']['rooms'][0]['objects'].append(copy.deepcopy(duplicate['floors']['ground']['rooms'][0]['objects'][2]));cases.append((duplicate,'OBJECT_ID_AMBIGUOUS'))
        for building,code in cases:
            with self.subTest(code=code):
                revision=self.seed(building);self.unchanged_failure(code,self.body(expected_head=revision.id))

    def test_payload_cannot_supply_model_actor_project_or_unknown_scope(self):
        for fields,code in [({'model':object_model()},'CLIENT_AUTHORITY_FIELD'),({'actor_id':'spoof'},'CLIENT_AUTHORITY_FIELD'),
                            ({'project_id':'other'},'CLIENT_PROJECT_AUTHORITY'),({'all_instances':True},'INVALID_PLAN_COMMAND'),
                            ({'confirm_new_draft':'true'},'INVALID_PLAN_COMMAND')]:
            with self.subTest(fields=list(fields)):self.unchanged_failure(code,self.body(**fields))

    def test_viewer_nonmember_and_other_project_owner_cannot_remove(self):
        self.db.grant_role(PROJECT,by_actor_id=ACTOR,actor_id='viewer',role='viewer')
        self.db.create_project('other-project',owner_id='other-owner')
        for actor in ('viewer','nonmember','other-owner'):
            with self.subTest(actor=actor):self.unchanged_failure('PROJECT_ACCESS_DENIED',self.body(),actor)

    def test_editor_can_remove_but_cas_race_preserves_the_winning_revision(self):
        self.db.grant_role(PROJECT,by_actor_id=ACTOR,actor_id='editor',role='editor')
        out=self.execute(self.body(object_id='item-column'),actor='editor');head=out['head']
        save=self.store.save_revision;winner=[]
        def racing_save(project_id,**kwargs):
            ws=S.workspace(self.store,PROJECT,ACTOR);building=ws.get(head).model
            building['floors']['ground']['rooms'][1]['rect'][2]=7
            won=ws.propose(building,brief=command()['brief'],requirements=command()['requirements'],expected_head=head,note='Synthetic concurrent winner')
            save(PROJECT,actor_id=ACTOR,revision=won,expected_head=head);winner.append(won.id)
            return save(project_id,**kwargs)
        with patch.object(self.store,'save_revision',side_effect=racing_save),self.assertRaises(PlanError) as rejected:
            self.execute(self.body(expected_head=head))
        self.assertEqual(rejected.exception.code,'STALE_REVISION')
        ws=S.workspace(self.store,PROJECT,ACTOR);self.assertEqual(ws.head,winner[0]);self.assertEqual(len(ws.history()),3)
        self.assertIn('item-plant',[o['id'] for o in ws.get(ws.head).model['floors']['ground']['rooms'][0]['objects']])

    def test_object_actions_are_bound_bounded_capabilities_and_follow_the_selected_revision(self):
        view=S.view(self.store,PROJECT,ACTOR);actions=view['object_actions']
        self.assertEqual(actions['revision_id'],self.first.id);self.assertEqual(actions['model_hash'],self.first.model_hash)
        self.assertFalse(actions['requires_new_draft']);self.assertFalse(actions['truncated'])
        self.assertEqual(len(actions['items']),4);self.assertTrue(all(row['supported'] for row in actions['items']))
        expected_provenance=self.first.model['floors']['ground']['rooms'][0]['objects'][0]['context_detail_provenance']
        self.assertTrue(all(row['context_detail_provenance']==expected_provenance for row in actions['items']))
        self.assertNotIn('model',actions)
        self.execute({'action':'approve','expected_head':self.first.id,'confirmed':True,'acknowledge_concept_only':True})
        self.assertTrue(S.view(self.store,PROJECT,ACTOR)['object_actions']['requires_new_draft'])
        out=self.execute(self.body(confirm_new_draft=True))
        self.assertEqual(out['object_actions']['revision_id'],out['head']);self.assertFalse(out['object_actions']['requires_new_draft'])
        self.assertNotIn('item-plant',[r['object_id'] for r in out['object_actions']['items']])
        old=S.view(self.store,PROJECT,ACTOR,self.first.id)['object_actions']
        self.assertEqual(old['model_hash'],self.first.model_hash);self.assertEqual(len(old['items']),4)
        many=object_model();sample=many['floors']['ground']['rooms'][0]['objects'][0]
        many['floors']['ground']['rooms'][0]['objects']=[dict(sample,id='o'+str(i)) for i in range(257)]
        head=self.seed(many).id;large=S.view(self.store,PROJECT,ACTOR,head)['object_actions']
        self.assertEqual(len(large['items']),256);self.assertTrue(large['truncated'])
        self.assertNotIn('o256',[r['object_id'] for r in large['items']])

    def test_object_action_summary_does_not_echo_oversized_untrusted_labels(self):
        building=object_model();obj=building['floors']['ground']['rooms'][0]['objects'][0]
        obj.update(id='i'*5000,kind='k'*5000,count=10**100);obj.pop('requirement_ids')
        revision=self.seed(building)
        row=C._object_actions(S.workspace(self.store,PROJECT,ACTOR),revision.id)['items'][0]
        self.assertFalse(row['supported']);self.assertIsNone(row['object_id']);self.assertIsNone(row['kind']);self.assertIsNone(row['count'])
        self.assertLess(len(json.dumps(row)),1000)

    def test_object_action_disclosure_omits_unvalidated_or_oversized_provenance(self):
        for change in ({'private_payload':'not a disclosure field'},{'assumptions':['x'*5000]}):
            building=object_model();building['floors']['ground']['rooms'][0]['objects'][0]['context_detail_provenance'].update(change)
            revision=self.seed(building);row=C._object_actions(S.workspace(self.store,PROJECT,ACTOR),revision.id)['items'][0]
            self.assertTrue(row['supported'],'invalid disclosure does not invent a geometry restriction')
            self.assertNotIn('context_detail_provenance',row)

    def test_unrelated_room_lock_is_retained_when_an_unlocked_object_is_removed(self):
        locked=self.execute({'action':'set_room_lock','expected_head':self.first.id,'room_ref':['ground','b'],'locked':True})
        out=self.execute(self.body(expected_head=locked['head']))
        revision=S.workspace(self.store,PROJECT,ACTOR).get(out['head'])
        self.assertEqual(revision.locked_rooms,(('ground','b'),))
        self.assertEqual(revision.model['floors']['ground']['rooms'][1],self.first.model['floors']['ground']['rooms'][1])


class RemoveObjectHTTP(Fixture,unittest.IsolatedAsyncioTestCase):
    async def invoke(self, body, *, actor=ACTOR, authorize=True, project=PROJECT):
        order=[]
        async def auth(scope,send):
            order.append('auth')
            if not authorize:
                await HTTP._send_json(scope,send,401,{'ok':False});return False
            scope.setdefault('state',{})['authenticated_user_id']=actor
            return True
        async def fallback(scope,receive,send):raise AssertionError('unexpected route')
        messages=[]
        async def send(message):messages.append(message)
        with patch.object(HTTP.AUTH,'authorize_asgi',side_effect=auth), \
             patch.object(HTTP.SESSION,'authenticated_supabase_plan_store',return_value=self.store), \
             patch('acs_workspace_http.WorkspaceMiddleware._start',side_effect=AssertionError('paid admission forbidden')):
            await HTTP.PlanCommandMiddleware(fallback)(_scope('/v1/projects/'+project+'/plan/commands'),
                _receive_for(body,on_read=lambda:order.append('body')),send)
        return _json_response(messages),order

    async def test_http_removal_uses_authenticated_command_store_without_paid_job(self):
        (status,body),order=await self.invoke(self.body())
        self.assertEqual(status,200);self.assertEqual(order[0],'auth');self.assertIn('body',order)
        self.assertEqual(body['result']['action'],'remove_object')
        self.assertTrue(body['result']['persistence']['revision_persisted'])
        self.assertEqual(len(S.workspace(self.store,PROJECT,ACTOR).history()),2)

    async def test_unauthenticated_request_is_denied_before_reading_body(self):
        (status,_),order=await self.invoke(self.body(),authorize=False)
        self.assertEqual(status,401);self.assertEqual(order,['auth'])
        self.assertEqual(len(S.workspace(self.store,PROJECT,ACTOR).history()),1)

    async def test_cross_project_and_viewer_requests_expose_no_model_or_history(self):
        self.db.grant_role(PROJECT,by_actor_id=ACTOR,actor_id='viewer',role='viewer')
        for actor in ('viewer','other-owner'):
            (status,body),_=await self.invoke(self.body(),actor=actor)
            self.assertEqual(status,403);self.assertEqual(body['error']['code'],'PROJECT_ACCESS_DENIED')
            self.assertNotIn('result',body);self.assertNotIn('floors',json.dumps(body))
        (status,body),_=await self.invoke(self.body(),project='99999999-9999-4999-8999-999999999999')
        self.assertEqual(status,404);self.assertNotIn('result',body)

    async def test_http_requires_confirmation_and_returns_conflict_for_stale_head(self):
        self.execute({'action':'approve','expected_head':self.first.id,'confirmed':True,'acknowledge_concept_only':True})
        (status,body),_=await self.invoke(self.body())
        self.assertEqual(status,400);self.assertEqual(body['error']['code'],'EXPLICIT_CONFIRMATION_REQUIRED')
        (status,_),_=await self.invoke(self.body(confirm_new_draft=True));self.assertEqual(status,200)
        (status,body),_=await self.invoke(self.body(confirm_new_draft=True))
        self.assertEqual(status,409);self.assertEqual(body['error']['code'],'STALE_REVISION')


if __name__=='__main__':unittest.main()
