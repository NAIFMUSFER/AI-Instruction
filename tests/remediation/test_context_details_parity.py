"""Actual native ESM/Python parity; canonical outputs compare exactly, no tolerance."""
import copy,json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from acs_context_details import with_context_details,get_actual_bounds,list_context_details
from test_context_details import fixture

class ContextParity(unittest.TestCase):
    def test_native_modules_match_exact_authoring_and_bounds(self):
        cases=[]
        def add(value,op='apply'):cases.append({'op':op,'value':value})
        add(fixture());out=with_context_details(fixture())[0];add(out);add(out,'list')
        deleted=copy.deepcopy(out);deleted['floors']['g']['rooms'][0]['objects']=[];add(deleted)
        for field,value in [('role',None),('covered',False),('wall_h',None),('walls',None),('objects',{}),('rect',[0,0,2,2])]:
            m=fixture();m['floors']['g']['rooms'][0][field]=value;add(m)
        for edge in ('N','E','S','W'):
            m=fixture();m['floors']['g']['rooms'][1]['walls']=[v for v in ('N','E','S','W') if v!=edge];add(m)
            m=fixture();m['floors']['g']['rooms'][1]['doors']=[{'edge':edge,'offset':2,'width':1}];add(m)
        m=fixture();m['levels'].append({'index':2,'template':'g','elevation':7.5});add(m)
        m=fixture();m['levels'][0]['kind']='roof';add(m)
        m=fixture();m['floors']['g']['rooms'][1]['id']='شرفة🌿'*40;add(m)
        m=fixture();m['floors']['g']['rooms'][0]['objects']=[{'id':'chair','kind':'chair'}];add(m)
        m=fixture();m['floors']['g']['rooms'][0]['lanes']=[{'id':'lane','x':1,'z':1,'w':2,'d':3}];add(m)
        m=fixture();m['meta']={'acs_context_details':dict(out['meta']['acs_context_details'],count=999)};add(m)
        m=fixture();m['meta']={'acs_context_details':dict(out['meta']['acs_context_details'],conceptual_only=1)};add(m)
        for meta in ({'note':'\ud800'},{'\udfff':'note'},{'note':'valid 🌿'}):
            m=fixture();m['meta']=meta;add(m)
        m=fixture();m['floors']['g']['rooms'][0]['id']='porch\ud800';add(m)
        for last_count in (96,97):
            m=fixture();room=m['floors']['g']['rooms'][0];room['rect']=[0,0,250,6];m['floors']['g']['rooms']=[room]
            room['objects']=[{'id':'rail'+str(i),'kind':'railing','x':3,'z':i+1,'y':0,'w':3,'d':.06,'h':1.1,'rot':0,'count':200,'pitch':1,'dir':'x'} for i in range(4)]
            room['objects'].append({'id':'columns','kind':'column','x':2,'z':3,'y':0,'w':.45,'d':.45,'h':3,'rot':0,'count':last_count,'pitch':1,'dir':'x'})
            result=with_context_details(m)
            self.assertEqual(result[2],None if last_count==96 else 'CONTEXT_DETAILS_RESOURCE_LIMIT','4096/4097 aggregate parts threshold')
            add(m)
        m=fixture();m['meta']={'note':'x'*100001};add(m)
        m=fixture();m['floors']['g']['rooms'][0]['id']=m['floors']['g']['rooms'][1]['id'];add(m)
        first=with_context_details(fixture())[0]['floors']['g']['rooms'][0]['objects'][0]['id']
        m=fixture();m['floors']['g']['rooms'][0]['lights']=[{'id':first}];add(m)
        m=copy.deepcopy(out);m['floors']['g']['rooms'][0]['objects'][0]['context_detail_provenance']['payload']='x'*10000;add(m,'list')
        for kind in ('column','railing','plant','planter'):
            for rotation in (0,45,90,180,270,-90):
                add({'kind':kind,'x':0,'z':2,'y':-.2,'w':2.75 if kind=='railing' else .6,'d':.06 if kind=='railing' else .6,'h':1.1,'rot':rotation,'count':2,'pitch':1,'dir':'z'},'bounds')
        for bad in (None,False,'0',[],1e100):
            obj={'kind':'column','x':bad,'z':0,'y':0,'w':.45,'d':.45,'h':3,'rot':0,'count':1,'pitch':1,'dir':'x'};add(obj,'bounds')
        py=[]
        for case in cases:
            value=case['value'];before=copy.deepcopy(value)
            try:
                result=get_actual_bounds(value) if case['op']=='bounds' else list_context_details(value) if case['op']=='list' else with_context_details(value)
                py.append({'value':json.loads(json.dumps(result)),'same':result[0] is value if case['op']=='apply' else None})
            except ValueError as error:py.append({'error':str(error)})
            self.assertEqual(value,before)
        run=subprocess.run(['node','tests/remediation/context_details_runner.mjs'],input=json.dumps(cases),text=True,capture_output=True,cwd=ROOT)
        self.assertEqual(run.returncode,0,run.stderr);js=json.loads(run.stdout)
        self.assertEqual(len(js),len(py))
        for index,(a,b) in enumerate(zip(py,js)):
            with self.subTest(case=index,op=cases[index]['op']):self.assertEqual(a,b)
        print('Exact Python/native ESM parity:',len(cases),'cases')

if __name__=='__main__':unittest.main()
