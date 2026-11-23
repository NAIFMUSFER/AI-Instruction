"""Bounded authoring defaults; no paid calls or structural certification."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from acs_context_details import with_context_details, get_actual_bounds, list_context_details

def fixture():
    return {'wall_t':.2,'wall_h':3,'floor_height':3.2,
            'levels':[{'index':0,'template':'g','elevation':0}],
            'floors':{'g':{'rooms':[
                {'id':'porch','role':'porch','covered':True,'rect':[0,0,6,5],'walls':['S'],'doors':[]},
                {'id':'balcony','role':'balcony','rect':[10,0,5,4],'walls':['S','E','W'],'doors':[]},
                {'id':'court','role':'courtyard','outdoor':True,'rect':[20,0,6,6],'walls':'none','doors':[]}]}}}

class ContextDetails(unittest.TestCase):
    def test_explicit_context_adds_all_three_without_mutating_source(self):
        model=fixture(); before=copy.deepcopy(model)
        out,report,reason=with_context_details(model)
        self.assertIsNone(reason);self.assertEqual(model,before)
        rows=list_context_details(out)
        self.assertEqual({row['kind'] for row in rows},{'column','railing','plant'})
        self.assertLessEqual(len(rows),12)
        self.assertEqual(out['meta']['acs_context_details'],{'schema':'acs.context-details/1','source':'system_default','conceptual_only':True})
        self.assertIs(with_context_details(out)[0],out)
        self.assertTrue(report['added']);self.assertTrue(all(row['context_detail_provenance']['conceptual_only'] for row in rows))
    def test_no_name_inference_or_malformed_generic_boundary(self):
        for change in ('name','objects'):
            m=fixture()
            if change=='name':
                for room in m['floors']['g']['rooms']:room['name']=room.pop('role')
            else:m['floors']['g']['rooms'][0]['objects']={}
            self.assertIs(with_context_details(m)[0],m)
    def test_actual_railing_extents_include_posts_and_top(self):
        box=get_actual_bounds({'kind':'railing','x':0,'z':0,'y':0,'w':2.75,'d':.06,'h':1.1,'rot':0,'count':1,'pitch':1,'dir':'x'})
        self.assertEqual(len(box['parts']),4)
        self.assertAlmostEqual(box['max'][0]-box['min'][0],2.8)
        self.assertAlmostEqual(box['max'][1],1.13)
    def test_compiler_retains_actual_source_for_every_object_part(self):
        from acs_compiler import Builder, build_objects
        import json,tempfile
        obj={'id':'authored-rail','kind':'railing','x':0,'z':0,'y':0,'w':2.75,'d':.06,'h':1.1,'rot':90,'count':2,'pitch':2,'dir':'z'}
        bld=Builder();bld._object_context={'template':'shared','level_index':-2}
        build_objects(bld,{'id':'r','rect':[10,20,6,6],'objects':[obj]},'F-2',-3.2)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'objects.gltf';bld.export_gltf(path);doc=json.loads(path.read_text())
        expected={'kind':'element','template':'shared','level_index':-2,'room_id':'r','collection':'objects','element_id':'authored-rail'}
        self.assertEqual(len(doc['nodes']),8)
        self.assertTrue(all(node.get('extras',{}).get('acs_object_source')==expected for node in doc['nodes']))
        self.assertEqual([n['extras']['acs_object_repeat_index'] for n in doc['nodes']],[0]*4+[1]*4)
    def test_door_shared_edge_and_full_route_remain_clear(self):
        m=fixture();r=m['floors']['g']['rooms'][1]
        r['doors']=[{'edge':'N','offset':2.5,'width':1}]
        out,report,_=with_context_details(m)
        self.assertFalse(out['floors']['g']['rooms'][1].get('objects'))
        self.assertIn('NO_CLEAR_SUPPORTED_PLACEMENT',[s['reason'] for s in report['skipped']])
        m=fixture();m['floors']['g']['rooms'].append({'id':'neighbor','rect':[10,-4,5,4],'doors':[]})
        out,_,_=with_context_details(m)
        self.assertFalse(out['floors']['g']['rooms'][1].get('objects'))
        m=fixture();m['floors']['g']['rooms'][0]['doors']=[{'edge':'N','offset':3,'width':5.8}]
        out,_,_=with_context_details(m)
        for obj in out['floors']['g']['rooms'][0].get('objects',[]):
            self.assertGreater(get_actual_bounds(obj)['min'][2],1.2)
    def test_no_shared_template_duplication_and_roof_is_excluded(self):
        m=fixture();m['levels'].append({'index':-2,'template':'g','elevation':-7})
        out,report,_=with_context_details(m)
        self.assertIs(out,m);self.assertTrue(all(s['reason']=='SHARED_TEMPLATE' for s in report['skipped']))
        m=fixture();m['levels'][0]['kind']='roof';self.assertIs(with_context_details(m)[0],m)
    def test_unknown_obstacle_lane_and_small_room_omit_without_resize(self):
        for key,value in [('objects',[{'id':'unknown','kind':'chair','x':1}]),('lanes',[{'id':'lane'}]),('rect',[0,0,1,1])]:
            m=fixture();m['floors']['g']['rooms'][0][key]=value;before=copy.deepcopy(m)
            out,report,_=with_context_details(m)
            room=out['floors']['g']['rooms'][0]
            self.assertEqual(room.get('objects',[]),before['floors']['g']['rooms'][0].get('objects',[]))
            self.assertEqual(room['rect'],before['floors']['g']['rooms'][0]['rect'])
            self.assertTrue(report['skipped']);self.assertEqual(m,before)
    def test_existing_rotated_object_reserves_real_extents(self):
        m=fixture();room=m['floors']['g']['rooms'][0]
        room['objects']=[{'id':'rail','kind':'railing','x':.475,'z':1,'y':0,'w':2.75,'d':.06,'h':1.1,'rot':90,'count':1,'pitch':1,'dir':'x'}]
        out,_,_=with_context_details(m);objects=out['floors']['g']['rooms'][0]['objects']
        self.assertEqual(objects[0],room['objects'][0])
        self.assertTrue(all(o['x']>.475 or get_actual_bounds(o)['min'][2]>2.4 for o in objects[1:]))
    def test_ids_unicode_collision_and_delete_do_not_repopulate(self):
        m=fixture();m['floors']['g']['rooms'][0]['id']='رواق🌿'*32
        first=with_context_details(m)[0]['floors']['g']['rooms'][0]['objects'][0]['id']
        m['floors']['g']['rooms'][0]['points']=[{'id':first,'type':'light','x':2,'z':2}]
        out,_,_=with_context_details(m)
        self.assertEqual(out['floors']['g']['rooms'][0]['objects'][0]['id'],first+'_2')
        self.assertTrue(all(len(r['element_id'])<=160 for r in list_context_details(out)))
        out['floors']['g']['rooms'][0]['objects']=[]
        self.assertIs(with_context_details(out)[0],out)
        self.assertFalse(out['floors']['g']['rooms'][0]['objects'])
    def test_fixed_marker_and_bounded_disclosure_do_not_trust_counts(self):
        out=with_context_details(fixture())[0]
        nonboolean=copy.deepcopy(out);nonboolean['meta']['acs_context_details']['conceptual_only']=1
        self.assertEqual(with_context_details(nonboolean)[2],'CONTEXT_DETAILS_PROVENANCE_INVALID')
        out['meta']['acs_context_details']['count']=999
        self.assertEqual(with_context_details(out)[2],'CONTEXT_DETAILS_PROVENANCE_INVALID')
        self.assertEqual(len(list_context_details(out)),5)
        obj=out['floors']['g']['rooms'][0]['objects'][0]
        obj['context_detail_provenance']['payload']='private-looking-untrusted-text'
        self.assertNotIn(obj['id'],[r['element_id'] for r in list_context_details(out)])
    def test_resource_bound_before_copy_and_twelve_object_cap(self):
        from unittest.mock import patch
        m=fixture();m['meta']={'note':'x'*100001}
        with patch('acs_context_details.copy.deepcopy',side_effect=AssertionError('must not copy')):
            self.assertEqual(with_context_details(m)[2],'CONTEXT_DETAILS_RESOURCE_LIMIT')
        m=fixture();rooms=m['floors']['g']['rooms'];rooms.clear()
        for i in range(9):rooms.append({'id':'c'+str(i),'role':'courtyard','outdoor':True,'rect':[i*10,0,6,6],'walls':'none','doors':[]})
        out,report,reason=with_context_details(m)
        self.assertIsNone(reason);self.assertEqual(len(report['added']),12);self.assertEqual(len(list_context_details(out)),12)
    def test_unbounded_height_is_unknown_not_raw_geometry_exception(self):
        m=fixture();m['floors']['g']['rooms'][0]['wall_h']=2000
        out,report,reason=with_context_details(m)
        self.assertIsNone(reason);self.assertFalse(out['floors']['g']['rooms'][0].get('objects'))
        self.assertIn('DIMENSION_UNKNOWN',[row['reason'] for row in report['skipped']])
    def test_unpaired_unicode_keeps_canonical_admission_boundary(self):
        for placement in ('value','key','room_id'):
            m=fixture()
            if placement=='value':m['meta']={'note':'\ud800'}
            elif placement=='key':m['meta']={'\udfff':'note'}
            else:m['floors']['g']['rooms'][0]['id']='porch\ud800'
            before=copy.deepcopy(m)
            out,report,reason=with_context_details(m)
            self.assertIs(out,m);self.assertIsNone(report)
            self.assertEqual(reason,'CONTEXT_DETAILS_INPUT_UNSUPPORTED');self.assertEqual(m,before)
    def test_existing_parts_are_expanded_once_per_level_even_when_all_contexts_blocked(self):
        import acs_context_details as details
        from unittest.mock import patch
        m=fixture();rooms=m['floors']['g']['rooms'];rooms.clear()
        for i in range(4):
            rooms.append({'id':'c'+str(i),'role':'courtyard','outdoor':True,'rect':[i*10,0,6,6],'walls':'none','objects':[{'id':'blocker'+str(i),'kind':'planter','x':3,'z':3,'y':0,'w':6,'d':6,'h':1,'rot':0,'count':1,'pitch':1,'dir':'x'}]})
        calls=[];original=details._footprints
        def counted(obj,room):
            if obj.get('id','').startswith('blocker'):calls.append(obj['id'])
            return original(obj,room)
        with patch.object(details,'_footprints',side_effect=counted):out,report,reason=details.with_context_details(m)
        self.assertIs(out,m);self.assertIsNone(reason);self.assertEqual(len(report['skipped']),4)
        self.assertEqual(sorted(calls),['blocker0','blocker1','blocker2','blocker3'])
    def test_aggregate_part_limit_is_checked_before_bounds_allocation(self):
        from unittest.mock import patch
        m=fixture();room=m['floors']['g']['rooms'][0];room['rect']=[0,0,250,6]
        m['floors']['g']['rooms']=[room]
        room['objects']=[{'id':'rail'+str(i),'kind':'railing','x':3,'z':i+1,'y':0,'w':3,'d':.06,'h':1.1,'rot':0,'count':200,'pitch':1,'dir':'x'} for i in range(5)]
        before=copy.deepcopy(m)
        with patch('acs_context_details.get_actual_bounds',side_effect=AssertionError('expanded before admission')):
            out,report,reason=with_context_details(m)
        self.assertIs(out,m);self.assertIsNone(report);self.assertEqual(reason,'CONTEXT_DETAILS_RESOURCE_LIMIT');self.assertEqual(m,before)

if __name__=='__main__':unittest.main()
