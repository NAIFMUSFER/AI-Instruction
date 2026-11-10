"""2026-11-10 geometry regressions; synthetic, no network/provider calls."""
import copy, json, math, tempfile, unittest
from pathlib import Path
import numpy as np
import acs_arch as A
import acs_bim as B
import acs_compiler as C
import acs_pbr as P
import acs_runtime as R
import acs_visual as V
from acs_plan_review import PlanWorkspace
from acs_plan_semantic_diff import diff_models
from acs_plan_options import compare_options
from warehouse_program_feasibility import generated_indoor_area

def model():
    return {'meta':{'type':'warehouse'},'site':{'w':20,'d':20},'wall_h':3,'wall_t':.2,'floor_height':3.2,
      'levels':[{'index':1,'template':'f','elevation':7.5}],
      'floors':{'f':{'rooms':[{'id':'a','rect':[0,0,5,5],'walls':'none','doors':[],'windows':[],'points':[]}]}}}

def exchange(b): return B.build_exchange({'model':b,'model_hash':'abc','current_revision':'r','building_id':'b'})['exchange']

class GeometryDelivery(unittest.TestCase):
    def test_explicit_elevations_and_basement(self):
        b=model(); b['levels']=[{'index':i,'template':'f','elevation':h} for i,h in [(-1,-3.8),(0,0),(1,7.5)]]
        with tempfile.TemporaryDirectory() as d:
            C.compile_building(b, str(Path(d)/'x.gltf')); g=json.loads((Path(d)/'x.gltf').read_text())
        for lv in b['levels']:
            nodes=[n for n in g['nodes'] if n['name'].startswith(f"FLOOR|F{lv['index']}|slab")]
            self.assertTrue(nodes)
            for n in nodes:
                a=g['accessors'][g['meshes'][n['mesh']]['primitives'][0]['attributes']['POSITION']]
                self.assertAlmostEqual(a['max'][1],lv['elevation'],places=5)
    def test_original_unequal_elevation_fixture_does_not_invent_fill(self):
        from acs_plan_review import digest
        b=json.loads((Path(__file__).parent/'fixtures/geometry/villa_unequal_elevation.json').read_text())
        self.assertEqual(digest(b),'0783c360f208c143ee97d6bdbbd37a26a32362631af325c852782fea555499a0')
        c=C.Builder();C.build_level(c,b['levels'][0],b['floors']['home'],0,
            {'site':b['site'],'wall_h':b['wall_h'],'wall_t':b['wall_t']},'F0')
        wall_top=max(float(p[0][:,1].max()) for p in c.parts if p[5].startswith('WALL|F0|'))
        self.assertAlmostEqual(wall_top,3,places=5)
        self.assertAlmostEqual(b['levels'][1]['elevation']-.15-wall_top,1.05,places=5)
    def test_primary_villa_wall_meets_declared_upper_slab(self):
        from tools.generate_delivery_fixtures import fixtures
        b=fixtures()['villa'];c=C.Builder()
        defaults={'site':b['site'],'wall_h':b['wall_h'],'wall_t':b['wall_t']}
        for level in b['levels']:
            C.build_level(c,level,b['floors'][level['template']],level['elevation'],defaults,'F'+str(level['index']))
        wall_top=max(float(p[0][:,1].max()) for p in c.parts if p[5].startswith('WALL|F0|'))
        slab_bottom=min(float(p[0][:,1].min()) for p in c.parts if p[5].startswith('FLOOR|F1|slab'))
        self.assertAlmostEqual(wall_top,slab_bottom,places=5)
        self.assertAlmostEqual(wall_top,4.05,places=5)
    def test_rotation_vertices(self):
        for angle in (0,45,90,180):
            a=C.Builder(); C.build_object(a,{'w':2,'d':1,'h':1,'rot':angle},'box',10,20,0,'F0','a',0)
            p=np.concatenate([part[0] for part in a.parts]); r=math.radians(angle)
            self.assertAlmostEqual(float(np.ptp(p[:,0])),2*abs(math.cos(r))+abs(math.sin(r)),places=5)
            self.assertAlmostEqual(float(np.ptp(p[:,2])),2*abs(math.sin(r))+abs(math.cos(r)),places=5)
    def test_open_and_partial_walls(self):
        for walls,count in [('none',0),('line',0),(['N','E'],2)]:
            b=model(); b['floors']['f']['rooms'][0]['walls']=walls
            self.assertEqual(len(A.compile_architecture(b)['walls']),count)
            self.assertEqual(len(exchange(b)['walls']),count)
    def test_stair_identity_contains_room(self):
        b=model(); b['floors']['f']['rooms']=[{'id':k,'rect':[i*5,0,5,5],'objects':[{'id':'stair','kind':'stairs','w':1,'d':2,'h':4}]} for i,k in enumerate(['a','b'])]
        ids=[s['canonical_id'] for s in exchange(b)['stairs']]; self.assertEqual(len(set(ids)),2)
    def test_rotated_portals(self):
        b=model(); b['meta']['type']='residential'; b['levels']=[{'index':0,'template':'f','elevation':0}]
        b['floors']['f']['rooms']=[{'id':'a','rect':[0,0,5,5],'doors':[{'edge':'E','offset':2.5,'width':1.2,'height':2.1}]},{'id':'b','rect':[5,0,5,5],'doors':[{'edge':'W','offset':2.5,'width':1.2,'height':2.1}]}]
        for angle in (0,45,90,180):
            ps=R.compile_runtime_scene(V.compile_visual_scene(b,'b',{'x':7,'z':-3},angle))['walkability']['portals']
            self.assertTrue(ps); self.assertTrue(all(p['connectivity_resolved'] for p in ps),angle)
    def test_union_slab_area(self):
        p=P.plate_rect([[0,0,4,2],[0,2,2,2]],[0,0,10,10])
        self.assertAlmostEqual(p['area_m2'],12); self.assertAlmostEqual(sum(r[2]*r[3] for r in p['rectangles']),12)
        b=model(); b['floors']['f']['rooms']=[{'id':'a','rect':[0,0,4,2],'walls':'none'},{'id':'b','rect':[0,2,2,2],'walls':'none'}]
        c=C.Builder(); C.build_level(c,b['levels'][0],b['floors']['f'],0,{'site':b['site'],'wall_h':3,'wall_t':.2},'F1')
        slabs=[p[0] for p in c.parts if p[5].startswith('FLOOR|F1|slab')]
        self.assertAlmostEqual(sum(float(np.ptp(p[:,0])*np.ptp(p[:,2])) for p in slabs),12)
    def test_repeated_instances_and_unused_templates(self):
        b=model(); b['levels']=[{'index':i,'template':'f'} for i in range(3)]; b['floors']['unused']={'rooms':[{'id':'x','rect':[0,0,10,10]}]}
        self.assertEqual(generated_indoor_area(b),75)
    def test_soft_fit_counts_repeated_physical_levels_once_per_instance(self):
        from warehouse_soft_area_fit import fit_soft_area
        b=model();b['levels']=[{'index':i,'template':'f'} for i in range(2)]
        fitted=fit_soft_area(b,[],32)
        self.assertAlmostEqual(generated_indoor_area(fitted),32,places=4)
        self.assertEqual(b['floors']['f']['rooms'][0]['rect'],[0,0,5,5])
    def test_critical_architecture_failure_cannot_publish_gltf(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'rejected.gltf'
            with patch('acs_arch.compile_architecture',side_effect=RuntimeError('synthetic')):
                with self.assertRaisesRegex(ValueError,'ARCHITECTURE_COMPILE_FAILED'):
                    C.compile_building(model(),str(output))
            self.assertFalse(output.exists())
    def test_accepted_id_diff(self):
        b=model(); b['floors']['f']['rooms'][0]['id']='a'*128
        self.assertFalse(diff_models(b,copy.deepcopy(b))['changes'])
    def test_two_valid_large_options(self):
        b=model(); b['meta']['notes']='n'*500000
        result=compare_options([{'id':'a','model':b},{'id':'b','model':copy.deepcopy(b)}])
        self.assertTrue(result)
    def test_target_area_review(self):
        b=model(); q=[{'id':'area','metric':'building_target_area_m2','expected':25,'source':'requested','evidence':'25'}]
        ws=PlanWorkspace(); rev=ws.propose(b,brief='area 25',requirements=q,expected_head=None,note='synthetic regression')
        self.assertNotIn('REQUIREMENT_METRIC_NOT_SUPPORTED',[i['code'] for i in ws.review(rev.id)['issues']])
    def test_capsule_clearance(self):
        for width,allowed in [(.2,False),(1.2,True)]:
            scene={'scene_id':'door','objects':[{'id':'wall','kind':'WALL','layer':'ARCHITECTURE','source_element_id':'wall','level_index':0,'exposure':'interior','geometry':{'cx':0,'cy':1.5,'cz':0,'ex':.2,'ey':3,'ez':10,'rot_y':0}},{'id':'door','kind':'DOOR','layer':'ARCHITECTURE','source_element_id':'door','host_wall_id':'wall','level_index':0,'geometry':{'cx':0,'cy':1.05,'cz':0,'ex':.12,'ey':2.1,'ez':width,'rot_y':0}}],'spaces_index':[{'id':'a@0','space_id':'a','rect':[-5,-5,5,10],'_elev':0,'level_index':0},{'id':'b@0','space_id':'b','rect':[0,-5,5,10],'_elev':0,'level_index':0}]}
            rt=R.compile_runtime_scene(scene); st=R.create_runtime_state(rt,navigation_mode='WALK')
            self.assertEqual(R.move_query(rt,st,[-1,0,0],[1,0,0])['allowed'],allowed)
if __name__=='__main__': unittest.main()
