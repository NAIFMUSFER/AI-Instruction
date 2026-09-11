"""Async delivery regression: no provider calls, controlled original handlers."""
import asyncio
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import httpx
import acs_async_jobs as J

JOB = 'job_' + '1'*32
TOKEN = 'a'*64
HEADERS = {'X-ACS-Job-ID': JOB, 'X-ACS-Job-Token': TOKEN}
RESULT = {'ok': True, 'building': {'meta': {'type': 'villa'}, 'levels': [], 'floors': {}}}


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = 0
        self.release = asyncio.Event()
        self.clock = [1000.0]
        self.store = J.JobStore(clock=lambda: self.clock[0])
        async def inner(scope, receive, send):
            self.calls += 1
            self.scope = scope
            self.input = await receive()
            await self.release.wait()
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': J._json(RESULT)})
        self.app = J.AsyncGenerationMiddleware(inner, store=self.store)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://test')

    async def asyncTearDown(self):
        self.release.set()
        if self.app.tasks:
            await asyncio.gather(*list(self.app.tasks), return_exceptions=True)
        if self.app.janitor:
            self.app.janitor.cancel()
            await self.app.janitor
        await self.client.aclose()

    async def submit(self, headers=None, content=b'{"text":"one room"}'):
        return await self.client.post('/v1/jobs/understand', headers=headers or HEADERS, content=content)

    async def poll(self, token=TOKEN, suffix=''):
        return await self.client.get('/v1/jobs/'+JOB+suffix, headers={'X-ACS-Job-Token': token})

    async def finish(self):
        self.release.set()
        await asyncio.gather(*list(self.app.tasks))

    async def test_receipt_does_not_wait_for_generation_and_legacy_route_receives_input(self):
        res = await asyncio.wait_for(self.submit(), 1)
        self.assertEqual(res.status_code, 202)
        self.assertNotIn('building', res.json())
        self.assertNotIn(TOKEN, res.text)
        await asyncio.sleep(0.01)
        self.assertEqual(self.scope['path'], '/v1/understand')
        self.assertEqual(self.input['body'], b'{"text":"one room"}')
        self.assertNotIn(b'x-acs-job-token', dict(self.scope['headers']))
        self.assertIn((await self.poll()).json()['job']['state'], J.ACTIVE)
        await self.finish()
        self.assertEqual((await self.poll()).json()['job']['state'], 'SUCCEEDED')
        self.assertEqual((await self.poll(suffix='/result')).json(), RESULT)

    async def test_parallel_replays_are_one_job_and_changed_input_is_rejected(self):
        results = await asyncio.gather(*(self.submit() for _ in range(8)))
        self.assertTrue(all(r.status_code == 202 for r in results))
        await asyncio.sleep(0.01)
        self.assertEqual(self.calls, 1)
        self.assertEqual((await self.submit(content=b'{"text":"different"}')).status_code, 409)
        self.assertEqual(self.calls, 1)

    async def test_lost_receipt_does_not_cancel_worker_or_require_another_post(self):
        scope = {'type':'http', 'method':'POST', 'path':'/v1/jobs/understand',
                 'headers':[(b'x-acs-job-id', JOB.encode()), (b'x-acs-job-token', TOKEN.encode())]}
        async def receive(): return {'type':'http.request', 'body':b'{}', 'more_body':False}
        async def disconnected_send(message): raise asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.app(scope, receive, disconnected_send)
        await self.finish()
        self.assertEqual((await self.poll(suffix='/result')).json(), RESULT)
        self.assertEqual(self.calls, 1)

    async def test_capability_required_for_status_result_and_replay(self):
        await self.submit(); await self.finish()
        self.assertEqual((await self.poll('b'*64)).status_code, 404)
        self.assertEqual((await self.poll('b'*64, '/result')).status_code, 404)
        self.assertEqual((await self.submit(headers={**HEADERS, 'X-ACS-Job-Token':'b'*64})).status_code, 404)
        leaked = await self.client.get('/v1/jobs/'+JOB+'?token='+TOKEN)
        self.assertEqual(leaked.status_code, 400)
        self.assertEqual(self.calls, 1)

    async def test_result_can_be_read_again_after_download_connection_loss(self):
        await self.submit(); await self.finish()
        a, b = await self.poll(suffix='/result'), await self.poll(suffix='/result')
        self.assertEqual(a.content, b.content)
        self.assertEqual(a.headers['cache-control'], 'no-store, private')
        self.assertEqual(self.calls, 1)

    async def test_expiry_removes_payload_not_idempotency_tombstone(self):
        await self.submit(); await self.finish()
        self.clock[0] += 1801
        self.assertEqual((await self.poll(suffix='/result')).status_code, 410)
        self.assertEqual(self.store.records[JOB].body, b'')
        self.assertEqual((await self.submit()).json()['job']['state'], 'EXPIRED')
        self.assertEqual(self.calls, 1)

    async def test_capacity_and_body_size_bounds(self):
        self.store.capacity = 1
        await self.submit()
        self.assertEqual((await self.submit(headers={**HEADERS,'X-ACS-Job-ID':'job_'+'2'*32})).status_code,429)
        self.app.max_input = 1
        self.assertEqual((await self.submit(content=b'{}')).status_code, 413)

    async def test_declared_errors_and_retry_after_survive_result_transport(self):
        async def rejected(scope, receive, send):
            await send({'type':'http.response.start','status':429,'headers':[(b'retry-after',b'30')]})
            await send({'type':'http.response.body','body':b'{"ok":false,"error":{"code":"ACS_RATE_LIMITED"}}'})
        self.app.app = rejected
        await self.submit(); await self.finish()
        self.assertEqual((await self.poll()).json()['job']['state'], 'FAILED')
        result = await self.poll(suffix='/result')
        self.assertEqual(result.status_code,429)
        self.assertEqual(result.headers['retry-after'],'30')
        self.assertEqual(result.json()['error']['code'],'ACS_RATE_LIMITED')

    async def test_deadline_is_terminal_not_false_success(self):
        self.app.execution_timeout = 0.01
        await self.submit()
        await asyncio.gather(*list(self.app.tasks))
        self.assertEqual((await self.poll()).json()['job']['state'], 'FAILED')
        self.assertEqual((await self.poll(suffix='/result')).status_code,504)

    async def test_oversized_result_fails_instead_of_retaining_truncated_json(self):
        self.store.max_body = 2
        await self.submit(); await self.finish()
        self.assertEqual((await self.poll()).json()['job']['state'], 'FAILED')
        self.assertEqual((await self.poll(suffix='/result')).status_code, 413)

    async def test_original_routes_bypass_adapter(self):
        self.release.set()
        r = await self.client.post('/v1/understand', content=b'{}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), RESULT)
        self.assertEqual(len(self.store.records), 0)

    async def test_cors_wraps_receipts_status_results_and_denials(self):
        from starlette.middleware.cors import CORSMiddleware
        wrapped = CORSMiddleware(self.app, allow_origins=['https://trusted.example'],
            allow_methods=['*'], allow_headers=['*'])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=wrapped), base_url='http://test') as c:
            for origin, status in [('https://trusted.example',200),('https://other.example',400)]:
                r = await c.options('/v1/jobs/understand', headers={
                    'Origin':origin,'Access-Control-Request-Method':'POST',
                    'Access-Control-Request-Headers':'content-type,x-acs-job-id,x-acs-job-token'})
                self.assertEqual(r.status_code, status)
            r = await c.post('/v1/jobs/understand', headers={**HEADERS,'Origin':'https://trusted.example'}, content=b'{}')
            self.assertEqual(r.status_code,202)
            self.assertEqual(r.headers['access-control-allow-origin'],'https://trusted.example')
            await self.finish()
            r = await c.get('/v1/jobs/'+JOB+'/result', headers={'X-ACS-Job-Token':TOKEN,'Origin':'https://trusted.example'})
            self.assertEqual(r.headers['access-control-allow-origin'],'https://trusted.example')

    async def test_original_api_validation_quota_and_payload_remain_in_use(self):
        import acs_understand_api as A
        from fastapi import FastAPI, Request
        original = FastAPI()
        original.add_api_route('/v1/understand', A.understand, methods=['POST'])
        original.add_exception_handler(J.E.AcsApiError, A._h_acs)
        async def run_job(*args, **kwargs):
            await self.release.wait()
            return RESULT['building']
        async def payload(building): return {'ok':True, 'building':building}
        self.app.app = original
        with patch.object(A,'guard') as guard, patch.object(A,'run_job',run_job), patch.object(A,'_understand_payload',payload):
            headers = {**HEADERS,'Content-Type':'application/json'}
            res = await self.submit(headers=headers)
            self.assertEqual(res.status_code,202)
            await asyncio.sleep(0.01)
            self.assertEqual(guard.call_count,1)
            await self.submit(headers=headers)
            self.assertEqual(guard.call_count,1)
            await self.finish()
            self.assertEqual((await self.poll(suffix='/result')).json(),RESULT)


if __name__ == '__main__':
    unittest.main(verbosity=2)
