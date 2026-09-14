"""Durable phase recovery without live identities or provider calls."""
import asyncio
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import acs_workspace_http as H
import acs_workspace_service as S
import acs_understand as U
from acs_workspace_progress import channel, resuming
from acs_generation_job import _classified_payload, _reraise_classified
from acs_plan_review import PlanError
from test_connected_workspace import command, model, PROJECT, ACTOR

class Store:
    def __init__(self):self.updates=[]
    def _request(self,method,path,payload=None,**kwargs):self.updates.append(copy.deepcopy(payload));return []

class Recovery(unittest.TestCase):
    def test_timeout_is_classified_and_does_not_report_success(self):
        store=Store()
        with patch.object(S,'generate_and_save',side_effect=TimeoutError):
            asyncio.run(H.WorkspaceMiddleware(None)._finish(store,PROJECT,ACTOR,command()))
        self.assertEqual(store.updates[-1]['error_code'],'ACS_TIMEOUT')
        self.assertEqual(store.updates[-1]['state'],'FAILED')

    def test_real_stage_events_are_saved_before_failure(self):
        store=Store()
        def generate(*args,on_progress):
            on_progress({'phase':'LAYOUT','checkpoint':{'kind':'outline'},'completed':2,'total':4,'provider_calls':1})
            raise TimeoutError()
        with patch.object(S,'generate_and_save',side_effect=generate):
            asyncio.run(H.WorkspaceMiddleware(None)._finish(store,PROJECT,ACTOR,command()))
        self.assertEqual(store.updates[0]['checkpoint'],{'kind':'outline'})
        self.assertEqual(store.updates[0]['provider_calls'],1)
        self.assertNotIn('checkpoint',store.updates[-1])
        self.assertTrue(H._job_view({'id':'x','state':'FAILED','checkpoint':{'kind':'outline'}})['job']['can_resume'])

    def test_outline_and_completed_geometry_are_not_called_again(self):
        zones=[{'id':'a','role':'living','template':'ground'}]
        checkpoint={'kind':'outline','zones':zones,'envelope':model(),'issues':[],
                    'results':[({'index':0,'template':'ground','zone_ids':['a']},[model()['floors']['ground']['rooms'][0]],[])],
                    'pending':[],'rate':150,'index':1}
        events=[]
        with channel(events.append),resuming(checkpoint),patch.object(U,'_outline') as outline,patch.object(U,'_plan_chunk_split') as chunk:
            result=U._plan_bounded('مبنى')
        outline.assert_not_called();chunk.assert_not_called()
        self.assertEqual(result['floors']['ground']['rooms'][0]['rect'],[0,0,8,8])
        self.assertEqual(events[-1]['phase'],'LAYOUT')

    def test_openings_resume_skips_completed_groups_and_preserves_rectangles(self):
        from acs_residential_generation import detail
        b=model();before=copy.deepcopy(b)
        with patch.object(U,'call_llm') as provider:
            result=detail(b,'مبنى',{'used':2},['ground:0'])
        provider.assert_not_called();self.assertEqual(result,before)
        with patch.object(U,'call_llm',return_value=json.dumps({'rooms':[{'id':'a','rect':[0,0,1,1],'doors':[],'windows':[],'points':[]},{'id':'b','doors':[],'windows':[],'points':[]}]})):
            with self.assertRaises(PlanError):detail(b,'مبنى',{'used':1})
        self.assertEqual(b,before)

    def test_domain_category_crosses_worker_boundary_without_private_text(self):
        payload=_classified_payload(PlanError('PLAN_DETAIL_INCOMPLETE','private user content'))
        self.assertNotIn('private',str(payload))
        with self.assertRaises(PlanError) as caught:_reraise_classified(payload)
        self.assertEqual(caught.exception.code,'PLAN_DETAIL_INCOMPLETE')

    def test_residential_shells_and_missing_vertical_core_are_rejected(self):
        from acs_residential_generation import check_rooms
        b=model();b['floors']['ground']['rooms'][0]['role']='apartment'
        with self.assertRaises(PlanError):check_rooms(b)

        b=model();b['levels'].append({'index':1,'template':'ground'})
        with self.assertRaises(PlanError):check_rooms(b)

    def test_layout_correction_preserves_site_and_cannot_change_envelope(self):
        from acs_residential_generation import prepare_layout
        b=model();b['floors']['ground']['rooms'][0]['role']='apartment'
        fixed=model()
        with patch.object(U,'call_llm',return_value=json.dumps({'floors':fixed['floors']})) as provider:
            result=prepare_layout(b,'مبنى',[],{'used':2,'limit':6})
        self.assertEqual(result['site'],b['site']);self.assertEqual(result['levels'],b['levels'])
        provider.assert_called_once()
        with patch.object(U,'call_llm',return_value=json.dumps({'floors':fixed['floors'],'site':{'w':99,'d':99}})):
            with self.assertRaises(PlanError):prepare_layout(b,'مبنى',[],{'used':2,'limit':6})

    def test_per_apartment_counts_do_not_pass_on_building_totals_alone(self):
        from acs_plan_review import _program
        b=model();rooms=b['floors']['ground']['rooms']
        for room,unit in zip(rooms,('one','two')):room.update(unit_id=unit,role='bedroom')
        req={'id':'rooms','metric':'room_count_per_unit','role':'bedroom','expected':1,'source':'requested','evidence':'غرفة','confirmed':True}
        self.assertEqual(_program(b,'غرفة',[req]),[])
        rooms[1]['role']='living'
        self.assertTrue(any(i['code']=='REQUIREMENT_NOT_MEASURABLE' for i in _program(b,'غرفة',[req])))

    def test_resumed_calls_share_the_original_budget(self):
        from acs_provider_budget import limited, consume
        import acs_api_errors as E
        with limited(3,used=2) as budget:
            consume()
            with self.assertRaises(E.AcsApiError):consume()
        self.assertEqual(budget['used'],3)

if __name__=='__main__':unittest.main()
