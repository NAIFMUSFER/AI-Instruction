"""Replay failed geometry without a live provider or production credentials."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from test_workspace_recovery import apartment_fixture
from acs_residential_layout import propose
from acs_residential_manifest import manifest
from acs_residential_access import detail_issues
from acs_plan_review import _geometry,_program,PlanError
from acs_plan_bridge import existing_geometry_verifier
from acs_workspace_progress import channel
from acs_provider_budget import consume
import acs_understand as U
import acs_workspace_service as S


def program(beds=3,baths=3,majlis=1):
    _,rows=apartment_fixture()
    for r in rows:
        if r.get('role') in {'bedroom','bathroom','majlis'}:
            n={'bedroom':beds,'bathroom':baths,'majlis':majlis}[r['role']]
            r['expected']=n*(4 if r['metric']=='room_count' else 1)
    return rows

class LayoutFallback(unittest.TestCase):
    def test_dense_two_unit_program_has_real_access_and_adequate_proposed_bed_depth(self):
        rows=program();brief='عمارة دورين، كل دور شقتين. جهة الشارع: جنوب'
        b=propose(brief,rows)
        self.assertIsNotNone(b);self.assertEqual(_geometry(b)[0],[])
        self.assertEqual(_program(b,brief,rows),[]);self.assertEqual(detail_issues(b),[])
        rooms=b['floors']['residential_2']['rooms']
        self.assertEqual(len(rooms),25)
        self.assertTrue(all(min(r['rect'][2:])>=2.7 for r in rooms if r['role']=='bedroom'))
        self.assertEqual(existing_geometry_verifier(b)['scopes'],{'topology':'PASS','vertical_circulation':'PASS'})
        self.assertTrue(any('بديل محسوب' in s for s in b['meta']['assumptions']))
        self.assertTrue(any('تهوية' in s for s in b['meta']['assumptions']))

    def test_four_frontages_keep_paired_openings_inside_site(self):
        for front,edge in [('شمال','N'),('جنوب','S'),('شرق','E'),('غرب','W')]:
            for beds,baths,majlis in [(2,2,0),(3,3,1)]:
                with self.subTest(front=front,beds=beds):
                    rows=program(beds,baths,majlis)
                    b=propose('عمارة بدرج ومصعد. جهة الشارع: '+front,rows)
                    self.assertIsNotNone(b);self.assertEqual(detail_issues(b),[])
                    self.assertEqual(_geometry(b)[0],[])
                    lobby=next(r for r in b['floors']['residential_2']['rooms'] if r['role']=='entrance' and not r.get('unit_id'))
                    self.assertTrue(any(o['edge']==edge for o in lobby['doors']))
                    self.assertTrue(all(r.get('core_id') for r in b['floors']['residential_2']['rooms'] if r['role'] in {'stairs','elevator'}))

    def test_confirmed_building_size_is_the_envelope_inside_a_larger_plot(self):
        # Owner decision 3: plot 25x30 with a confirmed 20x25 building draws 20x25.
        rows=program()
        for r in rows:
            if r['metric']=='site_width_m':r['expected']=25
            if r['metric']=='site_depth_m':r['expected']=30
        rows+= [{'id':'bw','metric':'building_width_m','expected':20,'confirmed':True,'source':'inferred'},
                {'id':'bd','metric':'building_depth_m','expected':25,'confirmed':True,'source':'inferred'}]
        brief='عمارة على أرض 25×30 والمبنى 20×25. جهة الشارع: شمال'
        cp=manifest(brief,rows)
        self.assertEqual(cp['envelope']['site'],{'w':20,'d':25})
        self.assertEqual(cp['envelope']['meta']['acs_plot'],{'w':25,'d':30})
        b=propose(brief,rows)
        self.assertIsNotNone(b);self.assertEqual(b['site'],{'w':20,'d':25})
        rooms=[r for f in b['floors'].values() for r in f['rooms']]
        self.assertLessEqual(max(r['rect'][0]+r['rect'][2] for r in rooms),20+1e-9)
        self.assertLessEqual(max(r['rect'][1]+r['rect'][3] for r in rooms),25+1e-9)
        self.assertEqual(_program(b,brief,rows),[])
        # The land must contain the building, and the building must be the envelope.
        larger=copy.deepcopy(b);larger['site']={'w':26,'d':25}
        codes={(i['code'],i.get('requirement_id')) for i in _program(larger,brief,rows)}
        self.assertIn(('REQUIREMENT_MISMATCH','bw'),codes);self.assertIn(('REQUIREMENT_MISMATCH','0'),codes)
        oversized=copy.deepcopy(rows);next(r for r in oversized if r['id']=='bw')['expected']=26
        self.assertIsNone(manifest(brief,oversized),'a building wider than its land is not planned')

    def test_fallback_is_not_used_to_override_special_constraints_or_infeasible_program(self):
        rows=program()
        for brief in ['غرفة نوم 5×4 متر','درج 3×5 متر','عمارة مع منور','عمارة بغرفة ماستر','عمارة مع ارتداد 3 متر']:
            self.assertIsNone(propose(brief,rows))
        small=copy.deepcopy(rows)
        next(r for r in small if r['metric']=='site_width_m')['expected']=9
        self.assertIsNone(propose('عمارة',small))
        uncertain=copy.deepcopy(rows);uncertain[0]['confirmed']=False
        self.assertIsNone(propose('عمارة',uncertain))
        more=copy.deepcopy(rows);more.append({'metric':'minimum_area_m2','expected':40,'confirmed':True,'source':'requested'})
        self.assertIsNone(propose('عمارة',more))

    def test_failed_layout_resume_uses_no_extra_calls_for_computed_fallback(self):
        brief='عمارة دورين، كل دور شقتين. جهة الشارع: جنوب';rows=program()
        cp=manifest(brief,rows);bad=copy.deepcopy(cp['envelope'])
        bad['floors']={'residential_2':{'rooms':[{**z,'rect':[0,0,3,4],'walls':['N','S','E','W']} for z in cp['zones']]}}
        events=[]
        def provider(text,**kw):
            consume();self.assertEqual(kw['stage'],'repair')
            return json.dumps({'floors':bad['floors']})
        with channel(events.append),patch.object(U,'call_llm',side_effect=provider) as call:
            out=S.generate_plan_candidate(brief,rows,'A',6,{'kind':'layout','building':bad},used_calls=3)
        self.assertEqual(call.call_count,1);self.assertEqual(out['provider_calls'],4)
        self.assertEqual(detail_issues(out['building']),[])
        last=next(e['checkpoint'] for e in reversed(events) if e.get('checkpoint'))
        self.assertEqual(last['kind'],'details');self.assertEqual(len(last['done']),2)
        with patch.object(U,'call_llm') as call:
            resumed=S.generate_plan_candidate(brief,rows,'A',6,last,used_calls=4)
        call.assert_not_called();self.assertEqual(resumed['provider_calls'],4)
        self.assertEqual(resumed['building'],out['building'])

    def test_computed_plan_saves_reopens_and_exports_through_normal_approval(self):
        from test_connected_workspace import WorkspaceLifecycle,Runner,command,PROJECT,ACTOR
        from acs_plan_persisted_commands import execute_persisted_plan_command
        import base64
        rows=program();brief='عمارة دورين، كل دور شقتين. جهة الشارع: جنوب'
        b=propose(brief,rows)
        fixture=WorkspaceLifecycle();fixture.setUp()
        try:
            cmd=dict(command(),brief=brief,requirements=rows,max_provider_calls=6)
            rid=S.generate_and_save(fixture.store,PROJECT,ACTOR,cmd,runner=Runner(b))
            view=S.view(fixture.store,PROJECT,ACTOR)
            self.assertEqual(view['head'],rid)
            self.assertTrue(view['authority']['can_approve_concept'])
            self.assertEqual(view['planning_assumptions'],b['meta']['assumptions'])
            self.assertTrue(view['openings'])
            with self.assertRaises(PlanError):
                S.artifact(fixture.store,PROJECT,ACTOR,{'action':'artifact','revision_id':rid,'format':'svg'})
            approved=execute_persisted_plan_command(fixture.store,PROJECT,
                {'action':'approve','expected_head':rid,'confirmed':True,'acknowledge_concept_only':True},
                actor_id=ACTOR,verifier=S.existing_geometry_verifier)
            self.assertEqual(approved['baseline'],rid)
            for fmt in ['svg','pdf','dxf','ifc','gltf']:
                result=S.artifact(fixture.store,PROJECT,ACTOR,{'action':'artifact','revision_id':rid,'format':fmt,'level_index':0})
                self.assertTrue(base64.b64decode(result['data_base64']))
                self.assertEqual(result['receipt']['revision_id'],rid)
            self.assertEqual(S.view(fixture.store,PROJECT,ACTOR)['head'],rid)
        finally:fixture.tearDown()

    def test_3d_compiler_preserves_explicit_partial_and_empty_wall_lists(self):
        import acs_compiler as C
        for edges in [['N','S'],[]]:
            builder=C.Builder()
            C.build_room(builder,{'id':'room','rect':[0,0,4,5],'walls':edges},'ground',0,{'wall_h':3,'wall_t':.2})
            names=[p[-1] for p in builder.parts if p[-1].startswith('WALL|')]
            self.assertEqual(len(names),len(edges))
            for edge in edges:self.assertTrue(any('w'+edge in name for name in names))

    def test_failed_openings_also_have_a_valid_disclosed_fallback(self):
        b,rows=apartment_fixture()
        with patch('acs_residential_generation.detail',side_effect=PlanError('PLAN_DETAIL_INCOMPLETE','bad')):
            result=S.generate_plan_candidate('عمارة بدرج ومصعد',rows,'A',6,{'kind':'layout','building':b},used_calls=2)
        self.assertEqual(result['provider_calls'],2)
        self.assertEqual(detail_issues(result['building']),[])
        self.assertEqual(result['building']['meta']['acs_layout_method'],'bounded_rectangular_fallback_v1')

if __name__=='__main__':unittest.main()
