# -*- coding: utf-8 -*-
import json, sys, copy
import os
import tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PHASE))
sys.path.insert(0, ROOT)
OUT = os.environ.get('ACS_PARITY_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_py_rev.json')
import acs_revision as REV, acs_ingest as ING
S=json.load(open(os.path.join(PHASE, 'fixtures', 'rev_scen.json'), encoding='utf-8'))
out={}
for q in S['queries']:
    m=copy.deepcopy(S['models'][q['m']])
    canon=REV.canonical_project(m) if q['scope']=='project' else REV.canonical_building(m,'bld_0')
    out[q['n']]={'hash':REV.model_hash(m,q['scope']),
                 'canonical':ING.canonical_json(canon),
                 'revision':REV.revision(m,q['scope'],'bld_0','T0')}
out['__ctx__']={'hash':REV.code_context_hash({'jurisdiction':{'country':'TESTLAND','region':None,'authority':None},
  'code_context':{'standard':'S','edition':'1',
    'rulepacks':[{'rulepack_id':'B','version':'2','enabled':True},{'rulepack_id':'A','version':'1','enabled':True}],
    'classification_packs':[{'pack_id':'P','version':'1','enabled':True}]}})}
occ={'classifications':[
  {'subject_id':'BUILDING:bld_0','subject_type':'BUILDING','status':'VERIFIED','group':'TEST_OCC_A',
   'subgroup':None,'standard':'TEST_STANDARD','edition':'0','classification_system':'TEST_OCC',
   'pack_id':'P','pack_version':'1','jurisdiction':{'country':'TESTLAND','region':None,'authority':None}},
  {'subject_id':'SPACE:x','subject_type':'SPACE','status':'CANDIDATE','group':'TEST_OCC_B'}],'packs':[]}
out['__occ__']={'hash':REV.occupancy_hash(occ),'canonical':ING.canonical_json(REV.canonical_occupancy(occ))}
out['__diff__']=REV.revision_diff(copy.deepcopy(S['models']['villa']),copy.deepcopy(S['models']['moved']))
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('py revision steps:', len(out))
