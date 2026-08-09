# -*- coding: utf-8 -*-
import json, sys, copy
import os
import tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PHASE))
sys.path.insert(0, ROOT)
OUT = os.environ.get('ACS_PARITY_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_py_occ.json')
import acs_relations as REL, acs_navigation as NAV, acs_egress as EG, acs_distance as DIST
import acs_rules as RU, acs_occupancy as OCC
S=json.load(open(os.path.join(PHASE, 'fixtures', 'occ_scen.json'), encoding='utf-8'))
FX=json.load(open(os.path.join(PHASE, 'fixtures', 'fixtures.json'), encoding='utf-8'))
AT='T0'; WHO='explicit_manual_approval'
EV=[{'type':'manual_review','ref':'reviewer','detail':'synthetic verification'}]
def B():
    b=copy.deepcopy(FX['hotel']); b['wall_t']=0.20; return b
def ctx(): return OCC.new_code_context()
def act(store,project,pack_id,stop):
    p=OCC.pack(store,pack_id,'1')
    if stop!='DRAFT':
        OCC.verify_pack(p,'UNDER_REVIEW',None,AT,WHO,None)
        OCC.verify_pack(p,stop or 'VERIFIED_PARTIAL',None,AT,WHO,None)
    project['code_context']['classification_packs'].append(
        {'pack_id':pack_id,'version':'1','enabled':True})
    return OCC.active_packs(project,store)
def dec_ver(store,project,group,verify):
    c,why=OCC.declare('BUILDING:bld_0','BUILDING',group,store,project,None,None,AT,None)
    if c:
        OCC.add_classification(store,c)
        if verify: OCC.verify_classification(c,store,project,None,AT,WHO,EV,None)
    return [c,why]
def rule_run(rid,store,project,extra=None):
    b=B(); rels=REL.build_relationships(b,'bld_0')
    idx=OCC.occupancy_index(store,['BUILDING:bld_0'])
    s=RU.resolve_subject(b,rels,'BUILDING:bld_0','bld_0',nav=NAV,egress=EG,distance=DIST,
                         occupancy_index=idx)
    rs,rule=RU.rule_by_id(rid,None,'TEST_ONLY.CORE')
    c={'evaluated_at':AT}
    if extra: c.update(extra)
    return RU.evaluate_rule(rule,s,c,rs,None)
out={}
for q in S['steps']:
    store=OCC.fixture_store(); project=ctx(); op=q['op']; n=q['n']
    if op=='issues': out[n]=OCC.issues(store,project)
    elif op=='real_count': out[n]=OCC.real_classification_count(store)
    elif op=='new_ctx': out[n]={'ctx':OCC.new_code_context(),
                                'issues':OCC.validate_code_context(OCC.new_code_context())}
    elif op=='activate': out[n]=act(store,project,q['pack'],q.get('stop'))
    elif op=='suggest':
        if q.get('activate'): act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL')
        made=OCC.suggest_from_program('BUILDING:bld_0','BUILDING',q['program'],store,project,AT)
        for c in made: OCC.add_classification(store,c)
        out[n]={'made':made,'resolved':OCC.resolve_occupancy('BUILDING:bld_0',store)}
    elif op=='declare':
        act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL')
        d=dec_ver(store,project,q['group'],False)
        out[n]={'classification':d[0],'reason':d[1],
                'resolved':OCC.resolve_occupancy('BUILDING:bld_0',store)}
    elif op=='verify_suggested':
        act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL')
        made=OCC.suggest_from_program('BUILDING:bld_0','BUILDING','hotel',store,project,AT)
        for c in made: OCC.add_classification(store,c)
        r=list(OCC.verify_classification(made[0],store,project,None,AT,q.get('method') or WHO,
                                         None if q.get('no_evidence') else EV,None))
        out[n]={'result':r,'classification':made[0],
                'resolved':OCC.resolve_occupancy('BUILDING:bld_0',store)}
    elif op=='verify_declared':
        act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL')
        d=dec_ver(store,project,'TEST_OCC_A',True)
        out[n]={'classification':d[0],'resolved':OCC.resolve_occupancy('BUILDING:bld_0',store)}
    elif op=='resolve_plain': out[n]=OCC.resolve_occupancy('BUILDING:bld_0',store)
    elif op=='conflict':
        act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL')
        for g in ('TEST_OCC_A','TEST_OCC_B'): dec_ver(store,project,g,True)
        out[n]=OCC.resolve_occupancy('BUILDING:bld_0',store)
    elif op in ('mixed','audit_mixed','export_mixed'):
        act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL')
        sp=['SPACE:bld_0.t.guest_1','SPACE:bld_0.g.lobby']; gs=['TEST_OCC_A','TEST_OCC_B']
        for i,sid in enumerate(sp):
            c,_=OCC.declare(sid,'SPACE',gs[i],store,project,None,None,AT,None)
            OCC.add_classification(store,c)
            OCC.verify_classification(c,store,project,None,AT,WHO,EV,None)
        if op=='mixed': out[n]=[OCC.resolve_occupancy(sid,store) for sid in sp]
        elif op=='audit_mixed': out[n]=OCC.audit(store,sp+['BUILDING:bld_0'])
        else: out[n]=OCC.export(store,project)
    elif op=='rule':
        st=q.get('state')
        if st=='candidate':
            act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL')
            for c in OCC.suggest_from_program('BUILDING:bld_0','BUILDING','hotel',store,project,AT):
                OCC.add_classification(store,c)
        elif st=='verified':
            act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL'); dec_ver(store,project,'TEST_OCC_A',True)
        elif st=='conflict':
            act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL')
            for g in ('TEST_OCC_A','TEST_OCC_B'): dec_ver(store,project,g,True)
        elif st=='edition9':
            act(store,project,'TEST_ONLY.OCCPACK_ED9','VERIFIED_PARTIAL'); dec_ver(store,project,'TEST_OCC_A',True)
        out[n]=rule_run(q['rule'],store,project)
    elif op=='pack_security':
        p=OCC.pack(store,'TEST_ONLY.OCCPACK','1')
        dup=copy.deepcopy(p); dup['classifications'].append(copy.deepcopy(dup['classifications'][0]))
        bad=copy.deepcopy(p); bad['verification']['status']='TOTALLY_FINE'
        scr=copy.deepcopy(p); scr['classifications'][0]['title']='<script>x</script>'
        reg=copy.deepcopy(p); reg['regulatory']=True
        out[n]={'duplicate':OCC.validate_pack(dup),'unknown_state':OCC.validate_pack(bad),
                'script':OCC.validate_pack(scr),'regulatory':OCC.validate_pack(reg),
                'draft_to_verified':list(OCC.verify_pack(copy.deepcopy(p),'VERIFIED_PARTIAL',None,AT,WHO,None)),
                'ai_verify':list(OCC.verify_pack(copy.deepcopy(p),'UNDER_REVIEW',None,AT,'ai_suggestion',None))}
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('py occupancy steps:', len(out))
