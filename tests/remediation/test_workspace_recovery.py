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

def connected_apartments(zones):
    """Two private units around a common corridor and a north-facing lobby."""
    rooms=[]
    positions={}
    for zone in zones:
        r={**zone,'name':zone['role'],'walls':['N','S','E','W'],
           'doors':[],'windows':[],'points':[]}
        unit=r.get('unit_id')
        if unit:
            side=1 if unit.endswith('_1') else 2
            if r['role']=='corridor':
                r['rect']=[6 if side==1 else 12,4,2,21]
            else:
                i=positions.get(unit,0);positions[unit]=i+1
                r['rect']=[0 if side==1 else 14,4+i*3.5,6,3.5]
        else:
            r['rect']={'entrance':[4,0,12,4],'corridor':[8,4,4,21],
                       'stairs':[0,0,4,4],'elevator':[16,0,4,4]}[r['role']]
        r['points']=[{'id':'light_'+r['id'],'type':'light','x':r['rect'][2]/2,'z':r['rect'][3]/2}]
        rooms.append(r)
    def door(room,side,offset):
        room['doors'].append({'id':room['id']+'_door_'+str(len(room['doors'])),
                            'edge':side,'offset':offset,'width':.9,'height':2.1})
    common=next(r for r in rooms if not r.get('unit_id') and r['role']=='corridor')
    lobby=next(r for r in rooms if r['role']=='entrance')
    for unit in ('apartment_1','apartment_2'):
        own=[r for r in rooms if r.get('unit_id')==unit]
        corridor=next(r for r in own if r['role']=='corridor')
        left=unit.endswith('_1')
        for r in own:
            if r==corridor:continue
            door(r,'E' if left else 'W',1.75)
            door(corridor,'W' if left else 'E',r['rect'][1]-4+1.75)
        door(corridor,'E' if left else 'W',10.5)
        door(common,'W' if left else 'E',10.5)
    door(common,'N',2);door(lobby,'S',6);door(lobby,'N',6)
    door(lobby,'W',2);door(lobby,'E',2)
    for role,side in [('stairs','E'),('elevator','W')]:
        door(next(r for r in rooms if r['role']==role),side,2)
    return rooms


def apartment_fixture():
    from acs_residential_manifest import manifest
    specs=[('site_width_m',None,20),('site_depth_m',None,25),
           ('level_count',None,2),('unit_count',None,4)]
    for role,count in [('bedroom',2),('living',1),('kitchen',1),('bathroom',2),('majlis',0)]:
        specs.extend([('room_count',role,count*4),('room_count_per_unit',role,count)])
    rows=[{'id':str(i),'metric':metric,'role':role,'expected':n,
           'confirmed':True,'source':'inferred'} for i,(metric,role,n) in enumerate(specs)]
    cp=manifest('عمارة بدرج ومصعد',rows)
    b=copy.deepcopy(cp['envelope'])
    b['floors']={'residential_2':{'rooms':connected_apartments(cp['zones'])}}
    return b,rows

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
                rooms=connected_apartments(zones)
                stages=[];events=[]
                def provider(text,**kw):
                    stage=kw['stage'];stages.append(stage);consume()
                    if stage=='plan_chunk':
                        self.assertEqual(planning_system(stage),PLANNING_SYSTEM)
                        return json.dumps({'rooms':[{k:v for k,v in r.items() if k not in ('doors','windows','points')} for r in rooms]})
                    self.assertEqual(stage,'detail','The confirmed apartment manifest must skip outline')
                    return json.dumps({'rooms':[{k:r[k] for k in ('id','doors','windows','points')} for r in rooms]})
                with channel(events.append),patch.object(U,'call_llm',side_effect=provider):
                    result=S.generate_plan_candidate(brief,rows,'A',6,used_calls=1)
                self.assertEqual(stages,['plan_chunk','detail'])
                self.assertEqual(result['provider_calls'],3)
                self.assertEqual(_program(result['building'],brief,rows),[])
                self.assertEqual(len(result['building']['floors']['residential_2']['rooms']),18)
                self.assertTrue(all(r['doors'] for r in result['building']['floors']['residential_2']['rooms']))
                self.assertTrue(any(e.get('checkpoint',{}).get('kind')=='details' for e in events))

    def test_private_unit_access_requires_connected_geometry_and_paired_doors(self):
        from acs_residential_access import issues
        from acs_plan_bridge import existing_geometry_verifier
        b,_=apartment_fixture()
        self.assertEqual(issues(b,False),[])
        self.assertEqual(issues(b),[])
        self.assertEqual(existing_geometry_verifier(b)['scopes']['topology'],'PASS')
        broken=copy.deepcopy(b)
        next(r for r in broken['floors']['residential_2']['rooms'] if r['role']=='stairs')['rect'][2]=3.8
        self.assertTrue(issues(broken,False))
        broken=copy.deepcopy(b)
        bedroom=broken['floors']['residential_2']['rooms'][0]
        bedroom['doors'][0]['offset']+=1
        self.assertEqual(issues(broken,False),[])
        self.assertTrue(any(i['room_ref'][1]==bedroom['id'] for i in issues(broken)))
        self.assertEqual(existing_geometry_verifier(broken)['scopes']['topology'],'FAIL')
        # A door on every room is insufficient if one apartment cannot enter.
        broken=copy.deepcopy(b)
        corridor=next(r for r in broken['floors']['residential_2']['rooms'] if r.get('unit_id')=='apartment_1' and r['role']=='corridor')
        corridor['doors']=[d for d in corridor['doors'] if d['edge']!='E']
        self.assertTrue(issues(broken))

    def test_common_access_cannot_cross_another_apartment(self):
        from acs_residential_access import issues
        b,_=apartment_fixture()
        common=next(r for r in b['floors']['residential_2']['rooms'] if r['role']=='corridor' and not r.get('unit_id'))
        common['unit_id']='apartment_1'
        self.assertTrue(any('apartment_2' in i['room_ref'][1] for i in issues(b)))

    def test_disconnected_layout_is_repaired_before_openings(self):
        from acs_residential_generation import prepare_layout
        from acs_residential_access import issues
        from acs_provider_budget import limited,consume
        good,rows=apartment_fixture();bad=copy.deepcopy(good)
        next(r for r in bad['floors']['residential_2']['rooms'] if r['role']=='stairs')['rect'][2]=3.8
        before=copy.deepcopy(bad)
        def provider(text,**kw):
            consume();self.assertEqual(kw['stage'],'repair')
            self.assertTrue(any(i['code']=='RESIDENTIAL_ACCESS_DISCONNECTED' for i in json.loads(text)['findings']))
            return json.dumps({'floors':good['floors']})
        with limited(6) as budget,patch.object(U,'call_llm',side_effect=provider) as call:
            result=prepare_layout(bad,'عمارة',rows,budget)
        self.assertEqual(issues(result,False),[]);self.assertEqual(call.call_count,1)
        self.assertEqual(bad,before);self.assertEqual(result['site'],before['site'])
        self.assertEqual(result['levels'],before['levels'])

    def test_valid_completed_apartments_resume_without_provider_calls(self):
        from acs_residential_generation import detail
        b,_=apartment_fixture();before=copy.deepcopy(b)
        with patch.object(U,'call_llm') as provider:
            result=detail(b,'عمارة',{'used':3,'limit':6},['residential_2:0'])
        provider.assert_not_called();self.assertEqual(result,before)

    def test_opening_correction_is_bounded_preserves_geometry_and_counts_calls(self):
        from acs_residential_generation import detail
        from acs_residential_access import detail_issues
        from acs_provider_budget import limited,consume
        b,_=apartment_fixture();good=copy.deepcopy(b)
        rooms=b['floors']['residential_2']['rooms']
        rooms[0]['windows']=[{'id':'internal','edge':'E','offset':1.75,'width':.6,'height':.6,'sill':1}]
        bad=copy.deepcopy(b)
        self.assertTrue(detail_issues(b))
        def provider(text,**kw):
            consume()
            value=good if 'findings_to_correct' in json.loads(text) else bad
            return json.dumps({'rooms':[{k:r[k] for k in ('id','doors','windows','points')} for r in value['floors']['residential_2']['rooms']]})
        with limited(6) as budget,patch.object(U,'call_llm',side_effect=provider) as call:
            result=detail(b,'عمارة',budget)
        self.assertEqual(budget['used'],2);self.assertEqual(call.call_count,2)
        self.assertEqual(result,good);self.assertEqual(detail_issues(result),[])
        def never_fix(text,**kw):
            consume()
            return json.dumps({'rooms':[{k:r[k] for k in ('id','doors','windows','points')} for r in bad['floors']['residential_2']['rooms']]})
        with limited(6) as budget,patch.object(U,'call_llm',side_effect=never_fix) as call:
            with self.assertRaises(PlanError) as caught:detail(copy.deepcopy(bad),'عمارة',budget)
        self.assertEqual(caught.exception.code,'PLAN_DETAIL_INCOMPLETE')
        self.assertEqual(call.call_count,2)

    def test_cross_kind_opening_overlap_respects_vertical_separation(self):
        from acs_residential_access import opening_collisions
        b,_=apartment_fixture()
        r=b['floors']['residential_2']['rooms'][0]
        r['windows']=[{'id':'w','edge':'E','offset':1.75,'width':.6,'height':.6,'sill':1.5}]
        self.assertTrue(opening_collisions(b))
        r['windows'][0]['sill']=2.2
        self.assertEqual(opening_collisions(b),[])

    def test_warehouse_does_not_enter_the_residential_pipeline(self):
        from acs_workspace_progress import planning_system
        def plan(*args,**kwargs):
            self.assertIsNone(planning_system('plan_chunk'))
            return model('warehouse')
        with patch.object(U,'_plan_bounded',side_effect=plan),patch('acs_residential_generation.detail') as detail:
            S.generate_plan_candidate('مستودع',[], 'A',3)
        detail.assert_not_called()

if __name__=='__main__':unittest.main()
