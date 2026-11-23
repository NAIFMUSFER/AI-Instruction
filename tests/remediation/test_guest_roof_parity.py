"""Actual JS/Python roof parity; bounded synthetic inputs, no browser/provider.

The worker evaluates shipped declarations and their real numeric/hash helpers.
Missing modules, crashes and malformed evidence fail; there is no skip/fallback.
Raw-helper coercion outside canonical admission is separately identified below.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import acs_roof as roof
from acs_plan_scorecard import measure_plan
from acs_plan_review import _geometry


def building():
    return {'meta':{'type':'residential','name':'Synthetic roof parity'},
            'site':{'w':40,'d':40},'wall_h':3,'wall_t':.2,'floor_height':3.2,
            'levels':[{'index':0,'template':'g'}],
            'floors':{'g':{'rooms':[
                {'id':'bar','rect':[0,0,4,2],'walls':'none','doors':[], 'windows':[], 'points':[]},
                {'id':'leg','rect':[0,2,2,2],'walls':'none','doors':[], 'windows':[], 'points':[]}]}}}


METHODS={'add':roof.add_flat_roof_level,'default':roof.with_default_roof,
         'carry':roof.carry_auto_roof,'remove':roof.remove_auto_roof,
         'restore':roof.restore_default_roof,'removed':roof.roof_removed_by_user,
         'disclosure':roof.roof_disclosure,'is_roof':roof.is_roof_level,
         'has_roof':roof.has_roof_level}


def reference(case):
    args=copy.deepcopy(case['args']);before=copy.deepcopy(args)
    try:
        value=METHODS[case['op']](*args)
        model=value[0] if case['op'] in ('add','default') else value
        result={'outcome':'return','value':value,'same_input':model is args[0]}
    except Exception as error:
        result={'outcome':'error','error':str(error)}
    # Python's ordinary equality treats True==1 and 1==1.0; input immutability
    # must also catch those type changes in the original JSON document.
    encode=lambda value:json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False)
    return {'id':case['id'],**result,'mutated':encode(args)!=encode(before)}


def node(payload):
    result=subprocess.run(['node','tests/remediation/guest_roof_parity.mjs'],
        cwd=ROOT,input=json.dumps(payload,ensure_ascii=False,allow_nan=False),
        text=True,capture_output=True,timeout=120)
    if result.returncode:
        raise AssertionError('Shipped JS roof worker failed:\n'+result.stderr[-6000:])
    try:return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError('Roof worker emitted malformed evidence: '+result.stdout[:500]) from error


class GuestRoofParity(unittest.TestCase):
    maxDiff=None

    def equal_json(self,actual,expected,path='result'):
        if isinstance(expected,(list,tuple)):
            self.assertIsInstance(actual,list,path);self.assertEqual(len(actual),len(expected),path)
            for i,(a,b) in enumerate(zip(actual,expected)):self.equal_json(a,b,path+'.'+str(i))
        elif isinstance(expected,dict):
            self.assertIsInstance(actual,dict,path);self.assertEqual(set(actual),set(expected),path)
            for key,value in expected.items():self.equal_json(actual[key],value,path+'.'+key)
        elif type(expected) in (int,float):
            self.assertIn(type(actual),(int,float),path)
            self.assertEqual(actual,expected,f'{path}: JS={actual!r}, Python={expected!r}')
        elif type(expected) is bool:
            self.assertIs(type(actual),bool,path);self.assertEqual(actual,expected,path)
        else:self.assertEqual(actual,expected,path)

    def compare(self,cases):
        results=node({'cases':cases});self.assertEqual(len(results),len(cases))
        for case,actual in zip(cases,results):
            with self.subTest(case=case['id']):
                expected=reference(case)
                self.assertFalse(expected['mutated'],'Python mutated '+case['id'])
                self.assertFalse(actual['mutated'],'JS mutated '+case['id'])
                self.equal_json(actual,expected,case['id'])
        return results

    def test_elevation_indices_heights_and_template_ties(self):
        cases=[]
        for name,levels,wall in [
            ('implicit-negative',[{'index':-2,'template':'g'},{'index':-1,'template':'g'}],3),
            ('explicit-nonuniform',[{'index':-1,'template':'g','elevation':7.5},
                                    {'index':4,'template':'low','elevation':-3.8}],4.05),
            ('tall-warehouse',[{'index':0,'template':'g','elevation':0}],12),
            ('tie-forward',[{'index':-1,'template':'g','elevation':4.2},
                            {'index':2,'template':'low','elevation':4.2}],3),
            ('tie-reverse',[{'index':2,'template':'low','elevation':4.2},
                            {'index':-1,'template':'g','elevation':4.2}],3)]:
            b=building();b['levels']=levels;b['wall_h']=wall
            b['floors']['low']={'rooms':[{'id':'low','rect':[12,0,3,4],'wall_h':wall}]}
            cases.append({'id':name,'op':'add','args':[b]})
        results=self.compare(cases)
        self.equal_json(results[-1]['value'][1],results[-2]['value'][1])
        self.assertEqual(results[1]['value'][1]['level_index'],5)
        self.assertEqual(results[1]['value'][1]['elevation_m'],11.7)
        self.assertEqual(results[2]['value'][1]['elevation_m'],12.15)

    def test_explicit_kind_and_authored_shared_template(self):
        bare=building();auto=roof.with_default_roof(bare)[0]
        shared=copy.deepcopy(auto)
        shared['levels'].append({'index':2,'template':'roof','kind':'floor','elevation':7})
        authored=copy.deepcopy(auto);authored['levels'][-1]['auto']=False
        cases=[{'id':'kind-'+str(i),'op':'is_roof','args':[level]} for i,level in enumerate([
            None,{}, {'template':'roof','name':'السطح'}, {'kind':'ROOF'},
            {'kind':'floor','template':'roof'}, {'kind':'roof','template':'ordinary'}])]
        cases += [
            {'id':'remove-shared','op':'remove','args':[shared]},
            {'id':'carry-shared','op':'carry','args':[auto,shared]},
            {'id':'preserve-authored','op':'carry','args':[auto,authored]},
            {'id':'refuse-remove-authored','op':'remove','args':[authored]},
            {'id':'refuse-double-roof','op':'default','args':[authored]},
            {'id':'refuse-restore-present','op':'restore','args':[authored]}]
        results=self.compare(cases)
        removed=next(x['value'] for x in results if x['id']=='remove-shared')
        self.assertIn('roof',removed['floors'])
        self.assertEqual(removed['levels'][-1],shared['levels'][-1])

    def test_six_decimal_rounding_and_unicode_template_ties(self):
        cases=[]
        for i,value in enumerate((3.2345665,3.2345675,4.0000005,4.0000015,7.5000005)):
            b=building();b['floor_height']=value
            cases.append({'id':f'round-elevation-{i}','op':'add','args':[b]})
            b=building();b['floors']['g']['rooms'][0]['rect'][2]=value
            cases.append({'id':f'round-area-gap-{i}','op':'add','args':[b]})
        b=building();b['floors']={'\ue000':{'rooms':[{'id':'a','rect':[0,0,2,2]}]},
                                  '🏠':{'rooms':[{'id':'b','rect':[0,0,3,3]}]}}
        b['levels']=[{'index':0,'template':name,'elevation':0} for name in b['floors']]
        cases.append({'id':'unicode-template-tie','op':'add','args':[b]})
        results=self.compare(cases)
        self.assertEqual(results[-1]['value'][1]['deck_area_m2'],9)

    def test_unicode_bounded_ids_hash_and_collision_suffixes(self):
        b=building();ids=['ش'*160,'🏠'*160,'🏠'*159+'أ','duplicate','duplicate','roof_deck','🏠'*160]
        b['floors']['g']['rooms']=[{'id':rid,'rect':[i*5,0,4,4]} for i,rid in enumerate(ids)]
        results=self.compare([{'id':'unicode-identities','op':'add','args':[b]}])
        generated=[r['id'] for r in results[0]['value'][0]['floors']['roof']['rooms']]
        self.assertTrue(all(len(rid)<=160 for rid in generated));self.assertEqual(len(set(generated)),len(ids))
        original='roof_'+ids[1]
        self.assertEqual(generated[1],original[:139]+'_'+hashlib.sha256(original.encode()).hexdigest()[:20])
        self.assertEqual(generated[4],'roof_duplicate_2')
        self.assertEqual(generated[6],generated[1][:158]+'_2')

    def test_partial_gaps_parapet_heights_and_revision_caveats(self):
        cases=[]
        for height in (0,.9,2):
            b,report=roof.add_flat_roof_level(building(),height)
            cases.extend([
                {'id':'parapet-'+str(height),'op':'add','args':[building(),height]},
                {'id':'disclose-'+str(height),'op':'disclosure','args':[b,b['levels'][-1]]}])
        bad=roof.with_default_roof(building())[0]
        bad['floors']['roof']['rooms'][0]['roof_provenance']['parapet_gaps']=['unknown']
        cases.append({'id':'untrusted-caveat','op':'disclosure','args':[bad,bad['levels'][-1]]})
        results=self.compare(cases);report=results[2]['value'][1]
        self.assertEqual(report['deck_area_m2'],12)
        self.assertEqual(report['parapet_gaps'],[{'room_id':'bar','edge':'S','open_length_m':2}])
        self.assertEqual(results[0]['value'][1]['parapet_length_m'],0)
        self.assertEqual(results[-1]['value']['gap_coverage'],'NOT_VERIFIED')

    def test_defined_python_number_coercions_remain_distinct_from_unknowns(self):
        cases=[{'id':'parapet-coercion-'+str(i),'op':'add','args':[building(),value]}
               for i,value in enumerate((True,False,'0.9',' 0.9 '))]
        numeric=building();numeric['floors']['g']['rooms'][0]['rect']=['0','0','4','2']
        cases.append({'id':'numeric-rectangle','op':'add','args':[numeric]})
        cases.extend({'id':'bad-rect-component-'+str(i),'op':'default','args':[dict(
            building(),floors={'g':{'rooms':[{'id':'bad','rect':[0,0,value,2]}]}})]}
            for i,value in enumerate((None,'',{},[])))
        results=self.compare(cases)
        self.assertEqual(results[0]['value'][1]['parapet_height_m'],1)
        self.assertEqual(results[1]['value'][1]['parapet_height_m'],0)
        for row in results[-4:]:self.assertEqual(row['value'][2],'ROOF_TOP_LEVEL_HAS_NO_ROOMS')
        extended=[]
        for i,text in enumerate(('1_0','١٠','𝟙𝟘','1__0','_10','1._0')):
            b=building();b['floors']['g']['rooms']=[{'id':'numeric','rect':[0,0,text,2]}]
            extended.append({'id':'raw-float-rect-'+str(i),'op':'default','args':[b]})
        for i,text in enumerate(('٠.٩','0_0.9')):
            extended.append({'id':'raw-float-parapet-'+str(i),'op':'add','args':[building(),text]})
        self.compare(extended)
        # Python float also accepts these strings, but neither canonical
        # geometry admission nor the actual local renderer accepts them.
        # Raw-helper parity never changes that admission boundary.
        unsupported=[]
        for text in ('1_0','١٠'):
            b=building();b['floors']['g']['rooms'][0]['rect'][2]=text
            self.assertTrue(any(i['code']=='INVALID_RECT' for i in _geometry(b)[0]))
            self.assertIsNone(roof.with_default_roof(b)[2])
            unsupported.append(b['floors']['g']['rooms'][0])
        self.assertEqual(node({'rendererRects':unsupported}),[None,None])

    def test_invalid_models_and_unknown_dimensions_fail_without_invention(self):
        cases=[]
        for i,b in enumerate((None,[],42,'building',{}, {'levels':[],'floors':{}})):
            for op in ('add','default'):cases.append({'id':f'bad-model-{i}-{op}','op':op,'args':[b]})
        for field in ('wall_h','floor_height'):
            for i,value in enumerate((None,0,-1,False,'3',{},[])):
                b=building();b[field]=value;cases.append({'id':f'height-{field}-{i}','op':'default','args':[b]})
        for i,value in enumerate((None,0,-1,True,'4',{})):
            b=building();b['floors']['g']['rooms'][0]['wall_h']=value
            cases.append({'id':f'room-height-{i}','op':'default','args':[b]})
        for i,level in enumerate(({'template':'g'}, {'index':None,'template':'g'},
                {'index':True,'template':'g'}, {'index':.5,'template':'g'},
                {'index':0,'template':'g','elevation':None},
                {'index':0,'template':'g','elevation':'7.5'})):
            b=building();b['levels']=[level];cases.append({'id':f'level-{i}','op':'default','args':[b]})
        for i,value in enumerate((None,-.1,2.1,'','bad',{})):
            cases.append({'id':f'parapet-invalid-{i}','op':'add','args':[building(),value]})
        for i,rect in enumerate((None,[],[0,0,0,2],[0,0,-1,2],['bad',0,2,2])):
            b=building();b['floors']['g']['rooms']=[{'id':'invalid','rect':rect}]
            cases.append({'id':f'rect-{i}','op':'default','args':[b]})
        results=self.compare(cases)
        for row in results:
            if row['outcome']=='return':
                self.assertIsNone(row['value'][1],row['id']);self.assertTrue(row['value'][2].startswith('ROOF_'),row['id'])
                self.assertTrue(row['same_input'],row['id'])
            else:self.assertTrue(row['error'].startswith('ROOF_'),row)

    def test_lifecycle_idempotence_removal_regeneration_and_restore(self):
        bare=building();auto=roof.with_default_roof(bare)[0];removed=roof.remove_auto_roof(auto)
        zero=roof.with_default_roof(bare,0)[0]
        edited=copy.deepcopy(auto);edited['floors']['g']['rooms'][1]['rect'][2]=3
        unknown=copy.deepcopy(edited);unknown['wall_h']=None
        cases=[
            {'id':'first-default','op':'default','args':[bare]},
            {'id':'second-default','op':'default','args':[auto]},
            {'id':'edit-rebuild','op':'carry','args':[auto,edited]},
            {'id':'remove','op':'remove','args':[auto]},
            {'id':'removed-marker','op':'removed','args':[removed]},
            {'id':'respect-removed','op':'carry','args':[removed,bare]},
            {'id':'reject-override','op':'carry','args':[removed,auto]},
            {'id':'restore','op':'restore','args':[removed]},
            {'id':'remove-again','op':'remove','args':[removed]},
            {'id':'carry-zero-parapet','op':'carry','args':[zero,bare]},
            {'id':'carry-unknown-height','op':'carry','args':[auto,unknown]}]
        rows={r['id']:r for r in self.compare(cases)}
        self.assertEqual(rows['second-default']['value'][2],'ROOF_LEVEL_EXISTS');self.assertTrue(rows['second-default']['same_input'])
        self.equal_json(rows['restore']['value'],auto)
        self.assertTrue(rows['respect-removed']['value']['meta']['acs_roof']['removed_by_user'])
        self.assertEqual(rows['reject-override']['error'],'ROOF_PREFERENCE_CONFLICT')
        rebuilt=rows['edit-rebuild']['value'];self.assertEqual(rebuilt['meta'],auto['meta'])
        self.assertEqual(rebuilt['levels'],auto['levels']);self.assertEqual(rebuilt['floors']['roof']['rooms'][1]['rect'][2],3)
        self.equal_json(rows['carry-zero-parapet']['value'],zero)
        omitted=rows['carry-unknown-height']['value'];self.assertEqual(omitted['meta']['acs_roof']['omitted'],'ROOF_HEIGHT_NOT_SPECIFIED')
        self.assertIsNone(omitted['wall_h']);self.assertFalse(any(l.get('kind')=='roof' for l in omitted['levels']))

    def test_repeated_floor_metrics_exclude_the_explicit_roof(self):
        b=building();b['levels']=[{'index':-1,'template':'g','elevation':-3.8},
                                 {'index':0,'template':'g','elevation':0},{'index':1,'template':'g','elevation':4.2}]
        rows=self.compare([{'id':'repeated-floors','op':'default','args':[b]}])
        before=measure_plan(b)['metrics'];after=measure_plan(rows[0]['value'][0])['metrics']
        self.assertEqual(before['level_count'],3);self.assertEqual(before['space_rect_area_m2'],36)
        for key in ('level_count','space_rect_area_m2'):self.assertEqual(after[key],before[key],key)
        self.assertEqual(_geometry(rows[0]['value'][0])[1]['space_instance_count'],6)
        self.assertEqual(node({'counts':[b,rows[0]['value'][0]]}),[
            {'occupied_levels':3,'occupied_rooms':6,'roof_levels':0,'roof_decks':0},
            {'occupied_levels':3,'occupied_rooms':6,'roof_levels':1,'roof_decks':2}])

    def test_actual_residential_sample_and_warehouse_generator(self):
        samples=node({'samples':True});self.assertEqual(set(samples),{'residential','warehouse'})
        self.assertEqual(samples['residential']['site'],{'w':30,'d':25});self.assertEqual(samples['warehouse']['site'],{'w':120,'d':80})
        self.assertEqual(set(samples['residential']['floors']),{'ground','typical'});self.assertEqual(len(samples['residential']['levels']),5)
        cases=[{'id':'shipped-'+name,'op':'default','args':[model]} for name,model in samples.items()]
        for row in self.compare(cases):
            name=row['id'].removeprefix('shipped-');before=samples[name];after=row['value'][0]
            self.assertEqual(sum(l.get('kind')=='roof' for l in after['levels']),1)
            pre=measure_plan(before)['metrics'];post=measure_plan(after)['metrics']
            for metric in ('level_count','space_rect_area_m2'):self.assertEqual(pre[metric],post[metric],(name,metric))
            self.assertEqual(_geometry(before)[1]['space_instance_count'],_geometry(after)[1]['space_instance_count'],name)
            counts=node({'counts':[before,after]})
            for key in ('occupied_levels','occupied_rooms'):self.assertEqual(counts[0][key],counts[1][key],(name,key))
            self.assertEqual(counts[1]['occupied_levels'],post['level_count'])
            self.assertEqual(counts[1]['occupied_rooms'],_geometry(after)[1]['space_instance_count'])
            self.assertEqual(counts[1]['roof_levels'],1)
            self.assertEqual(counts[1]['roof_decks'],sum(len(after['floors'][l['template']]['rooms'])
                                  for l in after['levels'] if l.get('kind')=='roof'))


if __name__=='__main__':unittest.main()
