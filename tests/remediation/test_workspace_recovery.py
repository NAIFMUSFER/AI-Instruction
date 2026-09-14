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

    def test_confirmed_apartment_program_compiles_without_a_provider(self):
        from acs_residential_manifest import manifest
        rows=[]
        def add(metric,expected,role=None):
            rows.append({'metric':metric,'expected':expected,'role':role,'confirmed':True,'source':'requested'})
        for metric,expected in [('site_width_m',20),('site_depth_m',25),('level_count',2),('unit_count',4)]:add(metric,expected)
        for role,count in [('bedroom',2),('living',1),('kitchen',1),('bathroom',2),('majlis',0)]:
            add('room_count_per_unit',count,role);add('room_count',count*4,role)
        with patch.object(U,'call_llm') as provider:
            result=manifest('عمارة بدرج ومصعد',rows)
        provider.assert_not_called()
        self.assertEqual(result['envelope']['site'],{'w':20,'d':25})
        self.assertEqual(len(result['envelope']['levels']),2)
        self.assertEqual(len(set(l['template'] for l in result['envelope']['levels'])),1)
        self.assertEqual(sum(z['role']=='bedroom' for z in result['zones'])*2,8)
        self.assertEqual(sum(z['role']=='stairs' for z in result['zones']),1)
        self.assertEqual(sum(z['role']=='elevator' for z in result['zones']),1)
        self.assertEqual(len({z['id'] for z in result['zones']}),len(result['zones']))
        self.assertEqual(result['pending'],result['zones'])
        self.assertIsNone(manifest('ارتفاع الدور 4 متر',rows))
        self.assertIsNone(manifest('بدون مصعد',rows))
        self.assertIsNone(manifest('no elevator',rows))
        self.assertIsNone(manifest('مصعد غير مطلوب',rows))
        self.assertIsNone(manifest('لكل شقة غرفة غسيل وشرفة',rows))
        self.assertIsNone(manifest('توزيع الشقق من الأرضي إلى الأعلى: 3، 1.',rows))
        changed=copy.deepcopy(rows);changed[-1]['expected']=1
        self.assertIsNone(manifest('عمارة',changed))

    def test_failed_first_stage_keeps_a_bounded_resume_path(self):
        row={'id':'x','state':'FAILED','provider_calls':1,'resume_command':command()}
        view=H._job_view(row)['job']
        self.assertTrue(view['can_resume']);self.assertEqual(view['provider_calls'],1)
        self.assertFalse(H._job_view(dict(row,state='SUCCEEDED'))['job']['can_resume'])
        self.assertFalse(H._job_view(dict(row,resume_command=None))['job']['can_resume'])
        self.assertFalse(H._job_view(dict(row,resume_command=dict(command(),source_id='source')))['job']['can_resume'])

    def test_incomplete_upstream_stream_is_a_connection_error(self):
        import httpx
        import acs_api_errors as E
        error=E.classify_upstream(httpx.RemoteProtocolError('incomplete chunked read'))
        self.assertEqual(error.code,E.ACS_UPSTREAM_CONNECTION)
        self.assertIn('انقطع اتصال',S.geometry_failure_message(error.code))

    def test_residential_subtypes_run_manifest_geometry_and_openings(self):
        from acs_residential_manifest import manifest
        from acs_residential_generation import PLANNING_SYSTEM
        from acs_workspace_progress import planning_system
        from acs_provider_budget import consume
        from acs_plan_review import _program
        specs=[('site_width_m',None,20),('site_depth_m',None,25),
               ('level_count',None,2),('unit_count',None,4)]
        for role,count in [('bedroom',2),('living',1),('kitchen',1),('bathroom',2),('majlis',0)]:
            specs.extend([('room_count',role,count*4),('room_count_per_unit',role,count)])
        rows=[{'id':str(i),'metric':metric,'role':role,'expected':n,
               'confirmed':True,'source':'inferred'} for i,(metric,role,n) in enumerate(specs)]
        for label,kind in [('عمارة سكنية','apartment'),('فيلا','villa'),('سكني','residential')]:
            with self.subTest(kind=kind):
                brief=label+' بدرج ومصعد'
                self.assertEqual(U.detect_type(brief),kind)
                zones=manifest(brief,rows)['zones']
                rooms=[{**z,'name':'فراغ '+str(i),'rect':[(i%5)*4,(i//5)*4,4,4],
                        'walls':['N','S','E','W']} for i,z in enumerate(zones)]
                stages=[];events=[]
                def provider(text,**kw):
                    stage=kw['stage'];stages.append(stage);consume()
                    if stage=='plan_chunk':
                        self.assertEqual(planning_system(stage),PLANNING_SYSTEM)
                        return json.dumps({'rooms':rooms})
                    self.assertEqual(stage,'detail','The confirmed apartment manifest must skip outline')
                    return json.dumps({'rooms':[{'id':r['id'],
                        'doors':[{'id':'d_'+r['id'],'edge':'N','offset':2,'width':.9,'height':2.1}],
                        'windows':[],'points':[{'id':'p_'+r['id'],'type':'light','x':2,'z':2}]} for r in rooms]})
                with channel(events.append),patch.object(U,'call_llm',side_effect=provider):
                    result=S.generate_plan_candidate(brief,rows,'A',6,used_calls=1)
                self.assertEqual(stages,['plan_chunk','detail'])
                self.assertEqual(result['provider_calls'],3)
                self.assertEqual(_program(result['building'],brief,rows),[])
                self.assertEqual(len(result['building']['floors']['residential_2']['rooms']),17)
                self.assertTrue(all(r['doors'] for r in result['building']['floors']['residential_2']['rooms']))
                self.assertTrue(any(e.get('checkpoint',{}).get('kind')=='details' for e in events))

    def test_warehouse_does_not_enter_the_residential_pipeline(self):
        from acs_workspace_progress import planning_system
        def plan(*args,**kwargs):
            self.assertIsNone(planning_system('plan_chunk'))
            return model('warehouse')
        with patch.object(U,'_plan_bounded',side_effect=plan),patch('acs_residential_generation.detail') as detail:
            S.generate_plan_candidate('مستودع',[], 'A',3)
        detail.assert_not_called()

if __name__=='__main__':unittest.main()
