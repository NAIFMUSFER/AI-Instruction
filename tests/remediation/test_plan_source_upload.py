"""Plan upload contracts using small synthetic files; no provider or live users."""
import base64
import asyncio
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from PIL import Image
from pypdf import PdfWriter
import acs_plan_sources as S
import acs_workspace_service as W
from acs_plan_review import PlanError
from acs_provider_budget import consume
from test_connected_workspace import model,command,Runner,PROJECT,ACTOR
import test_connected_workspace as fixtures

SOURCE='44444444-4444-4444-8444-444444444444'

def picture():
    out=io.BytesIO();Image.new('RGB',(64,64),'white').save(out,format='PNG');return out.getvalue()

def upload():
    return {'action':'upload','source_id':SOURCE,'name':'drawing.png','media_type':'image/png',
            'data_base64':base64.b64encode(picture()).decode(),'page':1}

class UploadTests(unittest.TestCase):
    def test_large_file_route_preserves_narrow_command_limit(self):
        import acs_plan_http as HTTP
        body=json.dumps(dict(upload(),data_base64='a'*950000)).encode()
        async def read(**kwargs):
            async def receive():return {'type':'http.request','body':body,'more_body':False}
            return await HTTP._read_json(receive,**kwargs)
        with self.assertRaises(PlanError):asyncio.run(read())
        parsed=asyncio.run(read(max_body_bytes=S.MAX_BODY,file_fields=('data_base64','preview_base64')))
        self.assertEqual(len(parsed['data_base64']),950000)

    def test_provider_cannot_change_source_receipt(self):
        from acs_plan_bridge import _reject_provider_authority_changes
        before=model();before['meta']['acs_plan_source']={'id':SOURCE,'sha256':'a'*64}
        _reject_provider_authority_changes(before,copy.deepcopy(before))
        changed=copy.deepcopy(before);changed['meta']['acs_plan_source']['sha256']='b'*64
        with self.assertRaises(PlanError):_reject_provider_authority_changes(before,changed)
    def test_original_preserved_and_metadata_checked(self):
        checked=S.validate_upload(upload())
        self.assertEqual(checked['original'],picture())
        self.assertEqual(checked['row']['sha256'],S.sha(picture()))
        self.assertEqual(checked['row']['page_count'],1)
        self.assertTrue(checked['preview'])
        for changes in [{'media_type':'image/jpeg'},{'page':2},{'source_id':'bad'},
                        {'media_type':'text/plain'},{'data_base64':'invalid'}, {'approval':True}]:
            self.assertIn('error',S.validate_upload(dict(upload(),**changes)))

    def test_pdf_page_is_explicit_and_bounded(self):
        writer=PdfWriter();writer.add_blank_page(width=200,height=300);writer.add_blank_page(width=200,height=300)
        buf=io.BytesIO();writer.write(buf)
        preview=io.BytesIO();Image.new('RGB',(60,90),'white').save(preview,format='JPEG')
        cmd=dict(upload(),media_type='application/pdf',name='drawing.pdf',page=2,
                 data_base64=base64.b64encode(buf.getvalue()).decode(),preview_base64=base64.b64encode(preview.getvalue()).decode())
        checked=S.validate_upload(cmd)
        self.assertEqual(checked['row']['page_count'],2);self.assertEqual(checked['row']['page'],2)
        self.assertEqual(checked['original'],buf.getvalue())
        self.assertIn('error',S.validate_upload(dict(cmd,page=3)))
        self.assertIn('error',S.validate_upload(dict(cmd,preview_base64='')))

    def test_source_command_requires_explicit_mode(self):
        with self.assertRaises(PlanError):W.generation_command(dict(command(),source_id=SOURCE))
        with self.assertRaises(PlanError):W.generation_command(dict(command(),source_mode='preserve'))
        self.assertEqual(W.generation_command(dict(command(),source_id=SOURCE,source_mode='preserve'))['source_id'],SOURCE)

    def test_vision_uses_actual_image_and_does_not_relayout(self):
        import acs_understand as U
        checked=S.validate_upload(upload());seen=[]
        def provider(*args,**kwargs):consume();seen.append(kwargs);return json.dumps(model())
        with patch.object(U,'call_llm',side_effect=provider),patch('acs_plan_overlap_repair.repair_overlap') as repair:
            result=S.candidate('مخطط تجريبي',command()['requirements'],'A',1,
                {'image':base64.b64encode(checked['preview']).decode(),'media_type':checked['row']['preview_media_type'],'mode':'preserve'})
        self.assertEqual(result['provider_calls'],1);repair.assert_not_called()
        self.assertEqual(seen[0]['content'][0]['type'],'image')
        self.assertIn('لا تغيّر',seen[0]['content'][1]['text'])
        self.assertFalse(seen[0]['truncate'])

    def test_stored_hash_and_project_binding(self):
        row=dict(S.validate_upload(upload())['row'],project_id=PROJECT,created_by=ACTOR)
        class Store:
            def _request(self,*args,**kwargs):return [row]
        with patch.object(S,'object_request',return_value=picture()):
            self.assertEqual(S.read_source(Store(),PROJECT,SOURCE)[1],picture())
        with patch.object(S,'object_request',return_value=b'changed'):
            with self.assertRaises(PlanError):S.read_source(Store(),PROJECT,SOURCE)
        row['project_id']=SOURCE
        with self.assertRaises(PlanError):S.source(Store(),PROJECT,SOURCE)

class SourceLifecycle(unittest.TestCase):
    def test_source_receipt_is_bound_to_saved_revision(self):
        fixture=fixtures.WorkspaceLifecycle();fixture.setUp()
        try:
            checked=S.validate_upload(upload());row=dict(checked['row'],project_id=PROJECT,created_by=ACTOR)
            runner=Runner(model());cmd=dict(command(),source_id=SOURCE,source_mode='preserve')
            with patch.object(S,'read_source',return_value=(row,checked['preview'])):
                rid=W.generate_and_save(fixture.store,PROJECT,ACTOR,cmd,runner=runner)
            self.assertEqual(runner.calls[0][0],'acs_plan_sources:candidate')
            self.assertNotIn('actor_id',runner.calls[0][1]);self.assertNotIn('project_id',runner.calls[0][1])
            saved=W.workspace(fixture.store,PROJECT,ACTOR).get(rid).model
            self.assertEqual(saved['meta']['acs_plan_source']['sha256'],row['sha256'])
            self.assertEqual(saved['meta']['acs_plan_source']['measurement_status'],'needs_review')
            self.assertIsNone(W.view(fixture.store,PROJECT,ACTOR)['baseline'])
        finally:fixture.tearDown()

if __name__=='__main__':unittest.main()
