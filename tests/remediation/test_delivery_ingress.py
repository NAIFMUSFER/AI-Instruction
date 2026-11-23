"""Exercise ASGI bytes before framework parsing, using no paid provider."""
import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import acs_async_jobs as ASYNC

class Ingress(unittest.TestCase):
    def invoke(self,path,messages,headers=(),prod=False):
        sent=[];calls=[];received=[]
        async def app(scope,receive,send):
            calls.append(path)
            received.append(await receive())
            await send({'type':'http.response.start','status':200,'headers':[]})
            await send({'type':'http.response.body','body':b'{}'})
        source=iter(messages)
        async def receive():return next(source,{'type':'http.disconnect'})
        async def send(item):sent.append(item)
        async def authorized(*args):return True
        scope={'type':'http','method':'POST','path':path,'headers':list(headers),'state':{}}
        with patch.object(ASYNC.AUTH,'authorize_asgi',side_effect=authorized),patch.dict(os.environ,{'ACS_ENV':'production' if prod else 'test'}):
            asyncio.run(ASYNC.AsyncGenerationMiddleware(app,max_input=32)(scope,receive,send))
        return sent,calls,received

    def test_direct_chunked_oversize_never_reaches_parser(self):
        for path in ['/v1/understand','/v1/understand/image','/v1/understand/pdf','/v1/edit']:
            sent,calls,_=self.invoke(path,[{'type':'http.request','body':b'x'*20,'more_body':True},{'type':'http.request','body':b'x'*20}])
            self.assertEqual(calls,[])
            self.assertEqual(sent[0]['status'],413)

    def test_disconnect_does_not_reach_framework_or_provider(self):
        sent,calls,_=self.invoke('/v1/understand',[{'type':'http.request','body':b'abc','more_body':True},{'type':'http.disconnect'}])
        self.assertEqual(calls,[])
        self.assertEqual(sent,[])

    def test_declared_oversize_rejected_before_receive(self):
        sent,calls,_=self.invoke('/v1/understand/pdf',[],[(b'content-length',b'33')])
        self.assertEqual(calls,[])
        self.assertEqual(sent[0]['status'],413)

    def test_small_body_replayed_exactly(self):
        sent,calls,received=self.invoke('/v1/understand',[{'type':'http.request','body':b'{','more_body':True},{'type':'http.request','body':b'}'}])
        self.assertEqual(calls,['/v1/understand'])
        self.assertEqual(received[0]['body'],b'{}')

    def test_production_legacy_paid_routes_require_durable_workspace(self):
        for path in list(ASYNC.SUBMIT_PATHS)+list(ASYNC.AUTH.DIRECT_PROTECTED_PATHS):
            sent,calls,_=self.invoke(path,[],prod=True)
            self.assertEqual(calls,[])
            self.assertEqual(sent[0]['status'],409)
            self.assertIn(b'PAID_WORKSPACE_REQUIRED',sent[1]['body'])

    def test_async_chunked_json_and_multipart_are_bounded_before_job_reservation(self):
        headers=[(b'x-acs-job-id',b'job_'+b'a'*32),(b'x-acs-job-token',b'b'*64)]
        for path in ASYNC.SUBMIT_PATHS:
            sent,calls,_=self.invoke(path,[{'type':'http.request','body':b'x'*20,'more_body':True},{'type':'http.request','body':b'x'*20}],headers)
            self.assertEqual(calls,[])
            self.assertEqual(sent[0]['status'],413)

    def test_slow_upload_has_total_deadline(self):
        import acs_ingress as ingress
        import acs_api_errors as errors
        async def receive():await asyncio.sleep(.05);return {'type':'http.request','body':b'x','more_body':True}
        async def run():
            with self.assertRaises(errors.AcsApiError) as caught:
                await ingress.bounded_body({},receive,100,deadline_seconds=.01)
            self.assertEqual(caught.exception.status,408)
        asyncio.run(run())

if __name__=='__main__':unittest.main()
