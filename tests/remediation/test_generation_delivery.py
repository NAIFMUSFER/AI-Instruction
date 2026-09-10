"""Receipt isolation, one admission/work invocation, expiry and actual ASGI routes.

No provider calls. Simulate a lost acknowledgement with a detached generation
and recover the exact payload through subsequent independent HTTP requests.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_api_errors as E
from acs_generation_delivery import DeliveryStore

ID = 'a' * 32
TOKEN = 'b' * 64
FP = hashlib.sha256(b'request').digest()


class Receipts(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = DeliveryStore(ttl=.05)
        self.admissions = self.calls = 0

    async def asyncTearDown(self):
        await self.store.close()

    def admit(self):
        self.admissions += 1

    async def work(self):
        self.calls += 1
        await asyncio.sleep(.002)
        return {'ok': True, 'building': {'label': 'original result'}}

    def submit(self, **kw):
        args = dict(operation_id=ID, token=TOKEN, fingerprint=FP,
                    request_id='req_' + ID, admit=self.admit, run=self.work)
        args.update(kw)
        return self.store.submit(**args)

    async def test_lost_ack_can_poll_result_without_new_work(self):
        rec = self.submit()  # Deliberately discard the acknowledgement.
        self.assertEqual(self.store.get(ID, TOKEN).status, 202)
        await rec.task
        self.assertEqual(self.store.get(ID, TOKEN).status, 200)
        self.assertEqual(json.loads(rec.body)['building']['label'], 'original result')
        self.assertEqual((self.admissions, self.calls), (1, 1))

    async def test_duplicate_running_and_complete_charge_once(self):
        rec = self.submit()
        self.assertIs(rec, self.submit())
        await rec.task
        self.assertIs(rec, self.submit())
        self.assertEqual((self.admissions, self.calls), (1, 1))

    async def test_payload_conflict_does_not_start_again(self):
        rec = self.submit()
        with self.assertRaises(E.AcsApiError) as error:
            self.submit(fingerprint=hashlib.sha256(b'changed').digest())
        self.assertEqual(error.exception.status, 409)
        await rec.task
        self.assertEqual(self.calls, 1)

    async def test_wrong_token_and_missing_receipt_are_indistinguishable(self):
        rec = self.submit()
        codes=[]
        for operation_id, token in [(ID, 'c'*64), ('d'*32, TOKEN)]:
            with self.assertRaises(E.AcsApiError) as error:
                self.store.get(operation_id, token)
            codes.append((error.exception.status, error.exception.message))
        self.assertEqual(codes[0], codes[1])
        self.assertEqual(codes[0][0], 404)
        await rec.task
        self.assertEqual(self.calls, 1)

    async def test_wrong_token_cannot_resubmit(self):
        rec=self.submit()
        with self.assertRaises(E.AcsApiError) as error:
            self.submit(token='c'*64)
        self.assertEqual(error.exception.status, 404)
        await rec.task
        self.assertEqual(self.admissions, 1)

    async def test_invalid_receipt_rejected_before_admission(self):
        for args in [dict(operation_id='bad'),dict(token='short'),dict(token='A'*64)]:
            with self.assertRaises(E.AcsApiError): self.submit(**args)
        self.assertEqual(self.admissions, 0)
        self.assertFalse(self.store._items)

    async def test_active_capacity_refuses_before_admission(self):
        self.store.active_limit=1
        rec=self.submit()
        with self.assertRaises(E.AcsApiError) as error:
            self.submit(operation_id='c'*32)
        self.assertEqual(error.exception.status, 429)
        self.assertEqual(self.admissions, 1)
        await rec.task

    async def test_retained_capacity_never_evicts_an_unexpired_result(self):
        self.store.capacity=1
        rec=self.submit(); await rec.task
        with self.assertRaises(E.AcsApiError): self.submit(operation_id='c'*32)
        self.assertIs(self.store.get(ID,TOKEN), rec)

    async def test_quota_denial_does_not_retain_or_invoke(self):
        def deny(): raise E.AcsApiError(E.ACS_RATE_LIMITED, retry_after=60)
        with self.assertRaises(E.AcsApiError): self.submit(admit=deny)
        await asyncio.sleep(.003)
        self.assertEqual(self.calls,0); self.assertFalse(self.store._items)

    async def test_timer_purges_sensitive_result_even_without_reads(self):
        rec=self.submit(); await rec.task
        self.assertIsNotNone(rec.body)
        await asyncio.sleep(.08)
        self.assertFalse(self.store._items); self.assertIsNone(rec.body)

    async def test_original_error_envelope_is_retained(self):
        async def reject(): raise E.AcsApiError(E.ACS_UPSTREAM_BILLING)
        rec=self.submit(run=reject); await rec.task
        payload=json.loads(rec.body)
        self.assertEqual(payload['error']['code'], E.ACS_UPSTREAM_BILLING)
        self.assertEqual(payload['error']['request_id'], 'req_'+ID)
        self.assertNotEqual(rec.status,200)

    async def test_exception_text_not_retained_and_no_secret_repr(self):
        async def fail(): raise RuntimeError('PRIVATE-DESCRIPTION-TOKEN')
        rec=self.submit(run=fail); await rec.task
        self.assertNotIn(b'PRIVATE-DESCRIPTION-TOKEN',rec.body)
        self.assertNotIn(TOKEN,repr(rec))
        self.assertEqual(rec.status,500)

    async def test_oversized_result_is_explicit_error_not_partial_success(self):
        self.store.max_result_bytes=20
        rec=self.submit(); await rec.task
        self.assertEqual(rec.status,413)
        self.assertFalse(json.loads(rec.body)['ok'])


class RouteIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import httpx
        import acs_understand_api as API
        self.API=API
        self.env=patch.dict(os.environ, {'ACS_GENERATION_DELIVERY':'1',
                                        'ACS_SINGLE_INSTANCE':'1', 'WEB_CONCURRENCY':'1'})
        self.env.start()
        self.store=DeliveryStore(ttl=60)
        self.store_patch=patch.object(API,'_DELIVERY',self.store); self.store_patch.start()
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=API.app),base_url='http://test')
        self.headers={'X-ACS-Operation-ID':ID,'X-ACS-Operation-Token':TOKEN,
                      'Origin':'https://sprightly-selkie-d906c3.netlify.app'}

    async def asyncTearDown(self):
        await self.client.aclose(); await self.store.close()
        self.store_patch.stop(); self.env.stop()

    async def test_independent_http_polls_deliver_same_result_and_guard_once(self):
        done=asyncio.Event()
        async def work(*args,**kwargs):
            await done.wait()
            return {'floors':{},'levels':[], 'meta':{}}
        payload={'ok':True,'building':{'floors':{},'levels':[], 'label':'RECOVERED'}}
        with patch.object(self.API,'guard') as guard, \
             patch.object(self.API,'run_job',side_effect=work) as run, \
             patch.object(self.API,'_understand_payload',new=AsyncMock(return_value=payload)):
            r=await self.client.post('/v1/understand/jobs',headers=self.headers,json={'text':'A room'})
            self.assertEqual(r.status_code,202)
            # The browser may lose this acknowledgement; identity was generated
            # before submission, so a separate read does not need its body.
            r=await self.client.get('/v1/understand/jobs/'+ID,headers=self.headers)
            self.assertEqual(r.status_code,202)
            again=await self.client.post('/v1/understand/jobs',headers=self.headers,json={'text':'A room'})
            self.assertEqual(again.status_code,202)
            done.set(); await self.store.get(ID,TOKEN).task
            r=await self.client.get('/v1/understand/jobs/'+ID,headers=self.headers)
            self.assertEqual(r.status_code,200);self.assertEqual(r.json(),payload)
            self.assertEqual(r.headers['x-request-id'],'req_'+ID)
            self.assertEqual(r.headers['cache-control'],'no-store')
            self.assertEqual(r.headers['access-control-allow-origin'],self.headers['Origin'])
            self.assertEqual(guard.call_count,1);self.assertEqual(run.call_count,1)

    async def test_validation_and_feature_gate_do_not_start_jobs(self):
        with patch.object(self.API,'run_job') as run:
            r=await self.client.post('/v1/understand/jobs',headers=self.headers,json={})
            self.assertEqual(r.status_code,422)
            with patch.dict(os.environ, {'ACS_GENERATION_DELIVERY':'0'}):
                r=await self.client.post('/v1/understand/jobs',headers=self.headers,json={'text':'x'})
                self.assertEqual(r.status_code,503)
            self.assertEqual(run.call_count,0);self.assertFalse(self.store._items)

    async def test_admission_failure_has_no_receipt(self):
        with patch.object(self.API,'guard',side_effect=E.AcsApiError(E.ACS_RATE_LIMITED)):
            r=await self.client.post('/v1/understand/jobs',headers=self.headers,json={'text':'room'})
            self.assertEqual(r.status_code,429);self.assertFalse(self.store._items)

    async def test_client_cannot_spoof_private_admission_flag(self):
        with patch.object(self.API,'guard',side_effect=E.AcsApiError(E.ACS_RATE_LIMITED)) as guard:
            r=await self.client.post('/v1/understand',headers={'acs_delivery_admitted':'true'},
                json={'text':'room','acs_delivery_admitted':True})
            self.assertEqual(r.status_code,429);self.assertEqual(guard.call_count,1)

    async def test_capability_disabled_for_multiple_processes(self):
        with patch.dict(os.environ,{'WEB_CONCURRENCY':'2'}):
            r=await self.client.get('/v1/generation-delivery')
            self.assertFalse(r.json()['enabled'])
            self.assertFalse(r.json()['survives_server_restart'])


if __name__=='__main__':
    unittest.main(verbosity=2)
