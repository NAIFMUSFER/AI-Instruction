"""Security witnesses: no real identity, database or model calls."""
import asyncio
import copy
import json
import os
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_auth as AUTH
import acs_plan_http as PLAN
import acs_workspace_http as WORK

PROJECT = '11111111-1111-4111-8111-111111111111'
ACTOR = '22222222-2222-4222-8222-222222222222'
JOB = '33333333-3333-4333-8333-333333333333'


def scope(path, token='synthetic-invalid', peer='test-peer'):
    return {'type':'http','method':'POST','path':path,'headers':[(b'authorization',('Bearer '+token).encode())],
            'client':(peer,123),'state':{}}


class DeliveryAdmission(unittest.TestCase):
    def test_legacy_plan_chat_cannot_skip_confirmation_and_budget(self):
        sent=[]
        async def auth(s,send): s['state']['authenticated_user_id']=ACTOR; return True
        async def receive(): return {'type':'http.request','body':json.dumps({'action':'chat_edit','expected_head':'r1','notes':[{'text':'edit'}]}).encode()}
        async def send(v): sent.append(v)
        with patch.object(AUTH,'authorize_asgi',side_effect=auth), patch.object(PLAN.SESSION,'authenticated_supabase_plan_store',return_value=object()), patch.object(PLAN.CHAT,'execute_isolated_persisted_chat_edit',return_value={}) as provider:
            asyncio.run(PLAN.PlanCommandMiddleware(None)(scope(f'/v1/projects/{PROJECT}/plan/commands'),receive,send))
        self.assertEqual(provider.call_count,0,'unauthorized paid orchestration reached')
        self.assertEqual(sent[0]['status'],400)
        self.assertIn(b'EXPLICIT_CONFIRMATION_REQUIRED',sent[1]['body'])

    def test_polling_other_worker_does_not_abandon_healthy_job(self):
        row={'id':JOB,'state':'RUNNING','worker_id':'other-worker','lease_expires_at':'2999-01-01T00:00:00+00:00','checkpoint':{'kind':'layout'}}
        result=WORK._job_view(row)['job']
        self.assertEqual(result['state'],'RUNNING')
        self.assertFalse(result['can_resume'])

    def test_uncertain_provider_outcome_cannot_resume_and_duplicate_paid_work(self):
        row={'id':JOB,'state':'FAILED','error_code':'ACS_UPSTREAM_TIMEOUT','checkpoint':{'kind':'outline'}}
        self.assertFalse(WORK._job_view(row)['job']['can_resume'])

    def test_storage_transport_and_unknown_errors_never_enable_paid_resume(self):
        for code in [None,'STORE_UNAVAILABLE','GENERATION_FAILED','GENERATION_WORKER_FAILED','ACS_UPSTREAM_CONNECTION','UNKNOWN']:
            row={'id':JOB,'state':'FAILED','error_code':code,'checkpoint':{'kind':'outline'}}
            self.assertFalse(WORK._job_view(row)['job']['can_resume'],code)
        row={'id':JOB,'state':'FAILED','error_code':'PLAN_DETAIL_INCOMPLETE','checkpoint':{'kind':'outline'}}
        self.assertTrue(WORK._job_view(row)['job']['can_resume'])

    def test_identity_verification_concurrency_is_bounded_before_thread_work(self):
        running=0; maximum=0; lock=threading.Lock()
        def slow(token):
            nonlocal running,maximum
            with lock: running+=1; maximum=max(maximum,running)
            time.sleep(.12)
            with lock: running-=1
            raise AUTH.AuthRejected()
        async def burst():
            async def call(i):
                sent=[]
                async def send(v):sent.append(v)
                await AUTH.authorize_asgi(scope('/v1/understand',str(i),'burst-peer'),send)
                return sent[0]['status']
            return await asyncio.gather(*(call(i) for i in range(40)))
        with patch.dict(os.environ,{'ACS_ENV':'test','ACS_AUTH_MODE':'oidc','ACS_AUTH_PROVIDER':'oidc','ACS_AUTH_USERINFO_URL':'https://identity.invalid/userinfo','ACS_AUTH_CACHE_TTL_S':'0'}), patch.object(AUTH,'_verify_oidc_userinfo',side_effect=slow):
            statuses=asyncio.run(burst())
        self.assertLessEqual(maximum,16)
        self.assertIn(503,statuses)
        self.assertTrue(set(statuses)<={401,429,503})

    def test_plan_alias_and_workspace_share_concurrency_pool(self):
        self.assertIs(WORK.WorkspaceMiddleware(None).tasks,WORK.WorkspaceMiddleware(None).tasks)

    def test_paid_quota_uses_verified_actor_not_forwarded_peer(self):
        from types import SimpleNamespace
        command={'action':'chat_edit','job_id':JOB,'confirmed':True,'max_provider_calls':3,'expected_head':None,'notes':[{'text':'edit'}]}
        class Store:
            def _request(self,method,path,payload=None,**kw):
                if method=='GET':return []
                return [payload]
            def _signed_rpc(self,*args):return {'created':True,'job':{'id':JOB,'state':'RUNNING'}}
        async def exercise():
            middleware=WORK.WorkspaceMiddleware(None)
            request=scope('/workspace');request['headers'].append((b'x-forwarded-for',b'forged'))
            async def finish(*args):pass
            with patch.object(WORK.SERVICE,'job_command',return_value=command),patch.object(WORK.SERVICE,'workspace',return_value=SimpleNamespace(head=None)),patch.object(WORK.RL,'default_limiter') as limiter,patch.object(middleware,'_finish',side_effect=finish):
                limiter.return_value.check.return_value={'allowed':True}
                await middleware._start(request,Store(),PROJECT,ACTOR,command)
                await asyncio.gather(*list(middleware.tasks))
                limiter.return_value.check.assert_called_once_with('actor:'+ACTOR,'edit')
        asyncio.run(exercise())

    def test_different_invalid_tokens_share_cheap_peer_quota(self):
        from acs_request_admission import AdmissionGate, AdmissionRejected
        gate=AdmissionGate(concurrency=1,per_minute=2,global_per_minute=20,max_peers=2)
        for token in ['first','second']:
            gate.acquire(scope('/v1/understand',token))()
        with self.assertRaises(AdmissionRejected) as caught:
            gate.acquire(scope('/v1/understand','third'))
        self.assertEqual(caught.exception.status,429)
        self.assertEqual(len(gate.peers),1)

    def test_disconnected_auth_caller_does_not_release_running_outbound_slot(self):
        import acs_request_admission as admission
        gate=admission.AdmissionGate(concurrency=1)
        began=threading.Event();finish=threading.Event()
        def blocked():began.set();finish.wait(2);return True
        async def exercise():
            task=asyncio.create_task(admission.run(scope('/v1/auth/signin'),blocked))
            await asyncio.to_thread(began.wait,1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
            self.assertEqual(gate.active,1)
            with self.assertRaises(admission.AdmissionRejected) as caught:
                await admission.run(scope('/v1/auth/signin'),lambda:True)
            self.assertEqual(caught.exception.status,503)
            finish.set()
            for _ in range(100):
                if gate.active==0:break
                await asyncio.sleep(.002)
            self.assertEqual(gate.active,0)
        with patch.object(admission,'GATE',gate):asyncio.run(exercise())

    def test_duplicate_bearer_fields_never_reach_verifier(self):
        sent=[]
        async def send(v):sent.append(v)
        request=scope('/v1/understand')
        request['headers'].append((b'Authorization',b'Bearer different-synthetic'))
        with patch.dict(os.environ,{'ACS_ENV':'test','ACS_AUTH_MODE':'test','ACS_AUTH_TEST_TOKEN':'synthetic-invalid'}),patch.object(AUTH,'_verify') as verify:
            asyncio.run(AUTH.authorize_asgi(request,send))
            verify.assert_not_called()
        self.assertEqual(sent[0]['status'],401)


if __name__=='__main__':unittest.main()
