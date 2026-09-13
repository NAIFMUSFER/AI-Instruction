"""Connected lifecycle on temporary stores; no production identity or provider."""
from __future__ import annotations
import asyncio
import base64
import copy
import json
from pathlib import Path
import sys
import tempfile
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

    def test_declared_opening_dimensions_are_accepted_but_conflicts_are_not(self):
        from acs_plan_bridge import existing_geometry_verifier
        building=model();room=building['floors']['ground']['rooms'][0];room.pop('walls')
        room['doors']=[{'id':'entry','edge':'S','offset':2,'width':1,'height':2.2,'material':'wood'}]
        self.assertEqual(existing_geometry_verifier(building)['scopes']['topology'],'PASS')
        room['doors'][0]['w']=2
        self.assertEqual(existing_geometry_verifier(building)['scopes']['topology'],'NOT_VERIFIED')


class JobsHTTP(unittest.IsolatedAsyncioTestCase):
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
