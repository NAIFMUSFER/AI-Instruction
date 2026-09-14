"""Connected lifecycle on temporary stores; no production identity or provider."""
from __future__ import annotations
import asyncio
import base64
import copy
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_workspace_service as S
import acs_workspace_http as H
from acs_plan_review import PlanError
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from acs_plan_persisted_commands import execute_persisted_plan_command
from acs_provider_budget import limited, consume

PROJECT = '11111111-1111-4111-8111-111111111111'
ACTOR = '22222222-2222-4222-8222-222222222222'
JOB = '33333333-3333-4333-8333-333333333333'


def model(kind='residential'):
    return {'meta': {'type': kind, 'name': 'Synthetic acceptance'},
        'site': {'w': 20, 'd': 20}, 'floor_height': 4, 'wall_h': 3.8, 'wall_t': .2,
        'levels': [{'index': 0, 'template': 'ground'}],
        'floors': {'ground': {'rooms': [
            {'id': 'a', 'role': 'storage' if kind == 'warehouse' else 'living', 'name': 'A', 'walls': 'none',
             'rect': [0, 0, 8, 8], 'doors': [] if kind=='warehouse' else [{'id':'d-a','edge':'S','offset':2,'width':1,'height':2.2,'material':'wood'}], 'windows': [],
             'points': [{'id':'light-a','type':'light','x':4,'z':4}]},
            {'id': 'b', 'role': 'staging' if kind == 'warehouse' else 'bedroom', 'name': 'B', 'walls': 'none',
             'rect': [10, 0, 8, 8], 'doors': [] if kind=='warehouse' else [{'id':'d-b','edge':'S','offset':2,'width':1,'height':2.2,'material':'wood'}], 'windows': [],
             'points': [{'id':'light-b','type':'light','x':4,'z':4}]},
        ]}}}


def command():
    return {'action': 'generate', 'job_id': JOB, 'brief': 'موقع بعرض 20 متر',
            'requirements': [{'id': 'width', 'metric': 'site_width_m', 'expected': 20, 'source': 'requested', 'evidence': '20', 'confirmed': True}],
            'expected_head': None, 'option': 'A', 'confirmed': True, 'max_provider_calls': 3}


class Runner:
    def __init__(self, building):
        self.building, self.calls = building, []

    def run(self, target, kwargs, **controls):
        self.calls.append((target, kwargs, controls))
        return {'building': copy.deepcopy(self.building), 'provider_calls': 1}


class WorkspaceLifecycle(unittest.TestCase):
    def test_overlap_repair_is_position_only_bounded_and_validated(self):
        from acs_plan_overlap_repair import repair_overlap
        import acs_understand as U
        original = model('warehouse')
        for r in original['floors']['ground']['rooms']:
            r['points'] = []
        original['floors']['ground']['rooms'][1]['rect'][:2] = [2, 0]
        saved = copy.deepcopy(original)
        good = {'positions': [{'template':'ground','id':'a','x':0,'z':0},
                              {'template':'ground','id':'b','x':10,'z':0}]}
        def call(reply):
            def run(*args, **kwargs):
                consume()
                return json.dumps(reply)
            return run
        with limited(2) as budget, patch.object(U, 'call_llm', side_effect=call(good)) as provider:
            consume()  # initial planning already spent one approved call
            fixed = repair_overlap(original, 'مستودع صناعي', budget)
            self.assertEqual(budget['used'], 2)
            self.assertEqual(provider.call_count, 1)
            self.assertEqual(S._geometry(fixed)[0], [])
            restored = copy.deepcopy(fixed)
            restored['floors']['ground']['rooms'][1]['rect'][:2] = [2, 0]
            self.assertEqual(restored, original)
        self.assertEqual(original, saved)
        with limited(1) as budget, patch.object(U, 'call_llm') as provider:
            consume()
            self.assertEqual(repair_overlap(original, 'مستودع', budget), original)
            provider.assert_not_called()
        for bad in [ {'positions':good['positions'][:1]},
                     {'positions':good['positions']+[good['positions'][0]]},
                     {'positions':[dict(good['positions'][0], id='foreign'),good['positions'][1]]},
                     {'positions':[dict(good['positions'][0], width=1),good['positions'][1]]} ]:
            with limited(2) as budget, patch.object(U, 'call_llm', side_effect=call(bad)):
                with self.assertRaises(PlanError): repair_overlap(original, 'مستودع', budget)
        for x in [2, 50]:
            invalid = copy.deepcopy(good); invalid['positions'][1]['x'] = x
            with limited(2) as budget, patch.object(U, 'call_llm', side_effect=call(invalid)) as provider:
                self.assertEqual(repair_overlap(original, 'مستودع', budget), original)
                self.assertEqual(provider.call_count, 1)
        for candidate in [model('warehouse'), dict(original, site={'w':1,'d':1})]:
            with limited(2) as budget, patch.object(U, 'call_llm') as provider:
                self.assertEqual(repair_overlap(candidate, 'مستودع', budget), candidate)
                provider.assert_not_called()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = SQLitePlanStore(Path(self.temp.name) / 'plans.sqlite3')
        self.db.create_project(PROJECT, owner_id=ACTOR)
        self.store = SQLitePlanStoreAdapter(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def generate(self, kind='residential'):
        runner = Runner(model(kind))
        rid = S.generate_and_save(self.store, PROJECT, ACTOR, command(), runner=runner)
        self.assertEqual(set(runner.calls[0][1]), {'brief', 'requirements', 'option', 'max_provider_calls'})
        return rid

    def test_residential_and_warehouse_save_review_lock_approve_export_reopen(self):
        for kind in ['residential', 'warehouse']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                db = SQLitePlanStore(Path(directory) / 'plans.sqlite3');db.create_project(PROJECT, owner_id=ACTOR)
                store = SQLitePlanStoreAdapter(db)
                rid = S.generate_and_save(store, PROJECT, ACTOR, command(), runner=Runner(model(kind)))
                self.assertTrue(S.view(store, PROJECT, ACTOR)['authority']['can_approve_concept'])
                with self.assertRaises(PlanError) as caught:
                    S.artifact(store, PROJECT, ACTOR, {'action':'artifact','revision_id':rid,'format':'gltf'})
                self.assertEqual(caught.exception.code, 'APPROVAL_REQUIRED')
                locked = execute_persisted_plan_command(store, PROJECT, {'action':'set_room_lock','expected_head':rid,'room_ref':['ground','a'],'locked':True}, actor_id=ACTOR, verifier=S.existing_geometry_verifier)
                head = locked['head']
                with self.assertRaises(PlanError):
                    S.edit_geometry(store, PROJECT, ACTOR, {'action':'edit_geometry','expected_head':head,'room_ref':['ground','a'],'rect':[0,0,7,8]})
                approved = execute_persisted_plan_command(store, PROJECT, {'action':'approve','expected_head':head,'confirmed':True,'acknowledge_concept_only':True}, actor_id=ACTOR, verifier=S.existing_geometry_verifier)
                self.assertEqual(approved['baseline'], head)
                for fmt in ['svg', 'dxf', 'pdf', 'ifc', 'gltf']:
                    result=S.artifact(store, PROJECT, ACTOR, {'action':'artifact','revision_id':head,'format':fmt,'level_index':0})
                    self.assertTrue(base64.b64decode(result['data_base64']))
                    self.assertEqual(result['receipt']['revision_id'],head)
                    self.assertEqual(result['receipt']['provider_calls'],0)
                edited=S.edit_geometry(store,PROJECT,ACTOR,{'action':'edit_geometry','expected_head':head,'room_ref':['ground','b'],'rect':[10,0,7,8]})
                self.assertNotEqual(edited['head'],head)
                reloaded=SQLitePlanStoreAdapter(SQLitePlanStore(Path(directory)/'plans.sqlite3'))
                reopened=S.view(reloaded,PROJECT,ACTOR)
                self.assertEqual(reopened['head'],edited['head']);self.assertEqual(reopened['baseline'],head)
                old=S.artifact(reloaded,PROJECT,ACTOR,{'action':'artifact','revision_id':head,'format':'svg','level_index':0})
                self.assertEqual(old['receipt']['revision_id'],head)

    def test_changed_head_during_generation_does_not_overwrite_winner(self):
        first = self.generate()
        next_command = dict(command(), expected_head=first)
        class RacingRunner(Runner):
            def run(inner, target, kwargs, **controls):
                S.edit_geometry(self.store,PROJECT,ACTOR,{'action':'edit_geometry','expected_head':first,'room_ref':['ground','b'],'rect':[10,0,7,8]})
                return super().run(target,kwargs,**controls)
        with self.assertRaises(PlanError) as caught:
            S.generate_and_save(self.store,PROJECT,ACTOR,next_command,runner=RacingRunner(model()))
        self.assertEqual(caught.exception.code,'STALE_REVISION')
        self.assertEqual(len(S.view(self.store,PROJECT,ACTOR)['history']),2)

    def test_invalid_generated_geometry_names_reason_without_saving_or_retrying(self):
        first = self.generate()
        cases = []
        overlap = model();overlap['floors']['ground']['rooms'][1]['rect']=[1,1,8,8]
        cases.append((overlap,'ROOM_OVERLAP'))
        outside = model();outside['floors']['ground']['rooms'][1]['rect']=[19,0,8,8]
        cases.append((outside,'OUTSIDE_SITE'))
        unresolved = model();unresolved['floors']['ground']['rooms'][0]['acs_unresolved']=True
        cases.append((unresolved,'UNRESOLVED_SPACE'))
        for building, reason in cases:
            with self.subTest(reason=reason):
                runner=Runner(building)
                with self.assertRaises(PlanError) as caught:
                    S.generate_and_save(self.store,PROJECT,ACTOR,dict(command(),expected_head=first),runner=runner)
                self.assertEqual(caught.exception.code,'PLAN_GEOMETRY_'+reason)
                self.assertEqual(len(runner.calls),1)
                reopened=S.view(self.store,PROJECT,ACTOR)
                self.assertEqual(reopened['head'],first)
                self.assertEqual(len(reopened['history']),1)

    def test_browser_program_unicode_evidence_survives_cloud_reload_and_review(self):
        # Real shipped producer + real Python consumer: JS offsets must count
        # Unicode code points, including emoji, rather than UTF-16 code units.
        source = """
          import {buildBriefProgram} from './public/app/core/brief-program.mjs';
          console.log(JSON.stringify(buildBriefProgram({
            brief:'🏡 موقع سكني؛ عرض الموقع ٢٠ متر؛ عمق الموقع ٢٠ متر؛ عدد الأدوار ١؛ 1 bedroom',
            type:'residential',width:'20',depth:'20',levels:'1',
            rows:[{metric:'room_count',role:'bedroom',expected:'1'}]
          })));
        """
        program=json.loads(subprocess.check_output(['node','--input-type=module','-e',source],cwd=Path(__file__).resolve().parents[2],text=True))
        runner=Runner(model())
        rid=S.generate_and_save(self.store,PROJECT,ACTOR,{**command(),**program},runner=runner)
        reopened=SQLitePlanStoreAdapter(SQLitePlanStore(Path(self.temp.name)/'plans.sqlite3'))
        view=S.view(reopened,PROJECT,ACTOR)
        self.assertEqual(view['revision_id'],rid)
        self.assertEqual(view['requirements'],program['requirements'])
        self.assertTrue(view['authority']['can_approve_concept'])
        for r in view['requirements']:
            self.assertEqual(view['brief'][r['source_span']['start']:r['source_span']['end']],r['evidence'])

    def test_stale_source_span_is_rejected_before_provider_execution(self):
        cmd=command();cmd['requirements'][0]['source_span']={'start':0,'end':2}
        runner=Runner(model())
        with self.assertRaises(PlanError) as caught:
            S.generate_and_save(self.store,PROJECT,ACTOR,cmd,runner=runner)
        self.assertEqual(caught.exception.code,'INVALID_PROVENANCE')
        self.assertEqual(runner.calls,[])

    def test_other_actor_cannot_read_or_export(self):
        rid=self.generate()
        with self.assertRaises(PlanError): S.view(self.store,PROJECT,'other-actor')
        with self.assertRaises(PlanError): S.artifact(self.store,PROJECT,'other-actor',{'action':'artifact','revision_id':rid,'format':'review'})

    def test_artifact_validation_survives_worker_boundary(self):
        rid=self.generate()
        snapshot=self.store.workspace_snapshot(PROJECT,actor_id=ACTOR)
        result=S.artifact_from_snapshot(snapshot,{'action':'artifact','revision_id':rid,'format':'gltf'})
        self.assertEqual(result['artifact_error']['code'],'APPROVAL_REQUIRED')
        with patch('acs_generation_job.default_runner') as factory:
            factory.return_value.run.return_value=result
            with self.assertRaises(PlanError) as caught:
                S.isolated_artifact(self.store,PROJECT,ACTOR,{'action':'artifact','revision_id':rid,'format':'gltf'})
        self.assertEqual(caught.exception.code,'APPROVAL_REQUIRED')

    def test_client_model_and_approval_fields_are_rejected_before_worker(self):
        for key in ['model','building','actor_id','approval_receipt','project_id']:
            with self.subTest(key=key), self.assertRaises(PlanError): S.generation_command(dict(command(),**{key:{}}))

    def test_provider_budget_stops_before_an_additional_request(self):
        import acs_api_errors as E
        with limited(2) as budget:
            consume();consume()
            with self.assertRaises(E.AcsApiError): consume()
            self.assertEqual(budget['used'],2)
        consume()  # no change to legacy calls outside the explicit worker budget

    def test_exhausted_budget_is_terminal_before_unresolved_chunk_fallback(self):
        import acs_understand as U
        import acs_api_errors as E
        import acs_generation_job as J
        results=[];stages=[]
        chunk={'index':0,'count':1,'chunk_count':2,'template':'ground','budget':100}
        with limited(1) as budget:
            consume()
            with patch.object(U,'_plan_spatial_context',return_value={}), patch.object(U,'_plan_chunk',side_effect=lambda *a,**kw: consume()) as provider:
                with self.assertRaises(E.AcsApiError) as caught:
                    U._plan_chunk_split('synthetic',chunk,{},None,'residential',results,stages)
            self.assertEqual(budget['used'],1)
        self.assertEqual(caught.exception.code,E.ACS_PROVIDER_BUDGET_EXHAUSTED)
        self.assertFalse(caught.exception.retryable)
        self.assertEqual(provider.call_count,1)
        self.assertEqual(results,[])
        with self.assertRaises(E.AcsApiError) as transported:
            J._reraise_classified(J._classified_payload(caught.exception))
        self.assertEqual(transported.exception.code,E.ACS_PROVIDER_BUDGET_EXHAUSTED)
        self.assertIn('حد الاستدعاءات',S.geometry_failure_message(transported.exception.code))

    def test_declared_opening_dimensions_are_accepted_but_conflicts_are_not(self):
        from acs_plan_bridge import existing_geometry_verifier
        building=model();room=building['floors']['ground']['rooms'][0];room.pop('walls')
        room['doors']=[{'id':'entry','edge':'S','offset':2,'width':1,'height':2.2,'material':'wood'}]
        self.assertEqual(existing_geometry_verifier(building)['scopes']['topology'],'PASS')
        room['doors'][0]['w']=2
        self.assertEqual(existing_geometry_verifier(building)['scopes']['topology'],'NOT_VERIFIED')


class JobsHTTP(unittest.IsolatedAsyncioTestCase):
    async def test_geometry_reason_survives_receipt_reload_without_raw_provider_details(self):
        row={'id':JOB,'state':'RUNNING'}
        class Store:
            def _request(self,method,path,payload=None,**kwargs):
                self_case.assertEqual(method,'PATCH');row.update(payload)
        self_case=self
        middleware=H.WorkspaceMiddleware(None)
        with patch.object(H.SERVICE,'generate_and_save',side_effect=PlanError('PLAN_GEOMETRY_ROOM_OVERLAP','private provider content')):
            await middleware._finish(Store(),PROJECT,ACTOR,command())
        receipt=H._job_view(json.loads(json.dumps(row)))['job']
        self.assertEqual(receipt['state'],'FAILED')
        self.assertIn('متداخلة',receipt['error_message'])
        self.assertNotIn('private',json.dumps(row))
        self.assertNotIn('private',json.dumps(receipt))
        self.assertIsNone(H._job_view({'id':JOB,'state':'FAILED','error_code':'unknown'})['job']['error_message'])
        self.assertIn('غير محفوظة',H._job_view({'id':JOB,'state':'FAILED','error_code':'INVALID_GEOMETRY'})['job']['error_message'])

    async def test_auth_runs_before_body_and_duplicate_job_only_starts_once(self):
        jobs={};started=[];gate=asyncio.Event()
        class Store:
            def _request(self, method,path,payload=None,**kwargs):
                if method=='GET':return list(jobs.values())
                if method=='POST':
                    if payload['id'] in jobs:return []
                    jobs[payload['id']]=dict(payload);return [dict(payload)]
                if method=='PATCH':jobs[JOB].update(payload)
        store=Store()
        async def execute(*args):
            started.append(1);await gate.wait();return 'plan_saved'
        async def fallback(*args):raise AssertionError('unexpected fallback')
        middleware=H.WorkspaceMiddleware(fallback)
        async def authorize(scope,send):scope['state']['authenticated_user_id']=ACTOR;return True
        async def call(payload):
            scope={'type':'http','path':'/v1/projects/'+PROJECT+'/workspace','method':'POST','headers':[],'state':{},'client':('127.0.0.1',1)}
            events=[]
            async def receive():
                self.assertEqual(scope['state']['authenticated_user_id'],ACTOR)
                return {'type':'http.request','body':json.dumps(payload).encode(),'more_body':False}
            async def send(msg):events.append(msg)
            await middleware(scope,receive,send)
            return json.loads(events[1]['body'])
        async def finish(*args):
            started.append(1);await gate.wait()
        with patch.object(H.AUTH,'authorize_asgi',authorize),patch.object(H.SESSION,'authenticated_supabase_plan_store',return_value=store),patch.object(H.SERVICE,'workspace',return_value=type('W',(),{'head':None})()),patch.object(middleware,'_finish',finish):
            result=await call(command());await asyncio.sleep(0)
            duplicate=await call(command());await asyncio.sleep(0)
            self.assertEqual(result['job']['id'],duplicate['job']['id']);self.assertEqual(len(started),1)
            self.assertEqual(H._job_view(dict(jobs[JOB],worker_id='old-process'))['job']['state'],'INTERRUPTED')
            gate.set();await asyncio.gather(*middleware.tasks)


if __name__=='__main__':unittest.main(verbosity=2)
