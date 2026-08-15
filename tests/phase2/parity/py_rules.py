# -*- coding: utf-8 -*-
import json, sys, copy
import os
import tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PHASE))
sys.path.insert(0, ROOT)
OUT = os.environ.get('ACS_PARITY_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_py_rules.json')
import acs_relations as REL, acs_navigation as NAV, acs_egress as EG, acs_distance as DIST, acs_rules as RU
S=json.load(open(os.path.join(PHASE, 'fixtures', 'rule_scen.json'), encoding='utf-8'))
out={}
def subj(b,rels,i): return RU.resolve_subject(b,rels,i,'bld_0',nav=NAV,egress=EG,distance=DIST)
for q in S['queries']:
    b=copy.deepcopy(S['models'][q['m']]); rels=REL.build_relationships(b,'bld_0')
    ctx=copy.deepcopy(q.get('ctx') or {})
    if q.get('buildingSubject'): ctx['subjects']={'BUILDING':subj(b,rels,'BUILDING:bld_0')}
    rs,rule=RU.rule_by_id(q['rule'],None,q.get('rs'))
    out[q['n']]=RU.evaluate_rule(rule,subj(b,rels,q['subj']),ctx,rs,None)
for q in S['sets']:
    b=copy.deepcopy(S['models'][q['m']]); rels=REL.build_relationships(b,'bld_0')
    ctx={'evaluated_at':'T0'}
    if q.get('buildingSubject'): ctx['subjects']={'BUILDING':subj(b,rels,'BUILDING:bld_0')}
    subs=[x for x in (subj(b,rels,i) for i in q['subjects']) if x]
    run=RU.evaluate_ruleset(q['ruleset'],subs,ctx,None)
    out[q['n']]={'run':run,'agg':RU.aggregate(run['results'],RU.ruleset_by_id(q['ruleset']))}
out['__meta__']={'engine':RU.ENGINE_VERSION,'regulatory':RU.regulatory_rule_count(),'issues':RU.rule_issues()}
# لا نصدّر مراجع النموذج داخل المواضيع — النتائج فقط
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('py rule scenarios:', len(out)-1)
