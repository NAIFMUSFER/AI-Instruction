# -*- coding: utf-8 -*-
import json, sys, copy
import os
import tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PHASE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PHASE))
sys.path.insert(0, ROOT)
OUT = os.environ.get('ACS_PARITY_PY') or os.path.join(
    tempfile.gettempdir(), 'acs_parity_py_ing.json')
import acs_relations as REL, acs_navigation as NAV, acs_egress as EG, acs_distance as DIST
import acs_rules as RU, acs_ingest as ING
S=json.load(open(os.path.join(PHASE, 'fixtures', 'ing_scen.json'), encoding='utf-8'))
AT='T0'; WHO='explicit_manual_approval'
LONG={"meta":{"type":"office"},"site":{"w":60,"d":20},"wall_h":3,"wall_t":0.2,"floor_height":3.2,
 "levels":[{"index":0,"template":"g"}],"floors":{"g":{"rooms":[
  {"id":"r1","rect":[0,0,4,4],"doors":[{"edge":"E","offset":2,"width":0.9}]},
  {"id":"hall","rect":[4,0,24,4],"doors":[{"edge":"W","offset":2,"width":0.9},{"edge":"E","offset":2,"width":0.9}]},
  {"id":"r2","rect":[28,0,4,4],"doors":[{"edge":"W","offset":2,"width":0.9}]}]}}}
def subj():
    b=copy.deepcopy(LONG); rels=REL.build_relationships(b,'bld_0')
    return [RU.resolve_subject(b,rels,'ROUTE:bld_0.g.r1>bld_0.g.r2','bld_0',nav=NAV,egress=EG,distance=DIST)]
def cv(st,d):
    doc=ING.document(st,d)
    ING.transition_document(doc,'SOURCE_IDENTIFIED',WHO,{'note':'id'},AT,None)
    return ING.transition_document(doc,'CONTENT_VERIFIED',WHO,{'note':'content'},AT,None)
def pack_flow(st,doc,cand,pack,stop):
    cv(st,doc); ING.verify_candidate(ING.candidate(st,cand),st,None,AT,WHO,None)
    p=ING.rulepack(st,pack,'1'); p['candidate_ids']=[cand]
    if stop!='DRAFT':
        ING.verify_pack(p,st,'UNDER_REVIEW',None,AT,WHO,None)
        ING.verify_pack(p,st,stop,None,AT,WHO,None)
    return ING.resolve_active_rules({'jurisdiction':None,
        'rulepacks':[{'rulepack_id':pack,'version':'1','enabled':True}]},st)
out={}
for s in S['steps']:
    st=ING.fixture_store(); op=s['op']; n=s['n']
    if op=='store_issues': out[n]=ING.store_issues(st)
    elif op=='regulatory_count': out[n]=ING.regulatory_rule_count(st)
    elif op=='doc_bytes':
        d=ING.document(st,s['doc']); out[n]=list(ING.verify_document_bytes(d,d['synthetic_content']))
    elif op=='doc_bytes_mod':
        d=ING.document(st,s['doc']); out[n]=list(ING.verify_document_bytes(d,d['synthetic_content']+' X'))
    elif op=='rule_hash': out[n]=ING.rule_definition_hash(ING.candidate(st,s['cand'])['proposed_rule'])
    elif op=='transition':
        d=ING.document(st,s['doc']); m=WHO if 'method' not in s else s['method']
        out[n]=list(ING.transition_document(d,s['to'],m,{'note':'e'},AT,None))
    elif op=='seq_official':
        d=ING.document(st,s['doc'])
        ING.transition_document(d,'SOURCE_IDENTIFIED',WHO,{'note':'e'},AT,None)
        out[n]=list(ING.transition_document(d,'OFFICIAL_SOURCE_VERIFIED',WHO,{'note':'e'},AT,None))
    elif op=='verify_cand':
        c=ING.candidate(st,s['cand'])
        out[n]={'result':list(ING.verify_candidate(c,st,None,AT,WHO,None)),'status':c['status']}
    elif op=='content_then_verify':
        cv(st,s['doc']); c=ING.candidate(st,s['cand'])
        r=list(ING.verify_candidate(c,st,None,AT,s.get('method') or WHO,None))
        out[n]={'result':r,'status':c['status'],'still_valid':list(ING.verification_still_valid(c,st))}
    elif op=='assess_all':
        cv(st,s['doc']); out[n]=[[c['candidate_id'],ING.assess_candidate(c,st)[0]] for c in st['candidates']]
    elif op=='pack_flow': out[n]=pack_flow(st,s['doc'],s['cand'],s['pack'],s['stop'])
    elif op=='project_eval':
        for d in s['docs']: cv(st,d)
        refs=[]
        for pk in s['packs']:
            for c in pk['cands']: ING.verify_candidate(ING.candidate(st,c),st,None,AT,WHO,None)
            p=ING.rulepack(st,pk['pack'],'1'); p['candidate_ids']=pk['cands']
            ING.verify_pack(p,st,'UNDER_REVIEW',None,AT,WHO,None)
            ING.verify_pack(p,st,'VERIFIED_PARTIAL',None,AT,WHO,None)
            refs.append({'rulepack_id':pk['pack'],'version':'1','enabled':True})
        out[n]=ING.evaluate_project({'jurisdiction':None,'rulepacks':refs},subj(),st,{'evaluated_at':AT})
    elif op=='project_conflict':
        for d in ('SYNDOC-ED1','SYNDOC-ED2'): cv(st,d)
        a=ING.candidate(st,'SYNCAND-ED1-T1'); b=ING.candidate(st,'SYNCAND-ED2-T1')
        b['proposed_rule']['rule_id']=a['proposed_rule']['rule_id']
        ING.verify_candidate(a,st,None,AT,WHO,None); ING.verify_candidate(b,st,None,AT,WHO,None)
        p1=ING.rulepack(st,'TEST_ONLY.SYNPACK','1'); p1['candidate_ids']=['SYNCAND-ED1-T1']
        p2=ING.rulepack(st,'TEST_ONLY.SYNPACK_ED2','1'); p2['candidate_ids']=['SYNCAND-ED2-T1']
        for p in (p1,p2):
            ING.verify_pack(p,st,'UNDER_REVIEW',None,AT,WHO,None)
            ING.verify_pack(p,st,'VERIFIED_PARTIAL',None,AT,WHO,None)
        out[n]=ING.evaluate_project({'jurisdiction':None,'rulepacks':[
            {'rulepack_id':'TEST_ONLY.SYNPACK','version':'1','enabled':True},
            {'rulepack_id':'TEST_ONLY.SYNPACK_ED2','version':'1','enabled':True}]},subj(),st,{'evaluated_at':AT})
    elif op=='audit':
        pack_flow(st,s['doc'],s['cand'],s['pack'],'VERIFIED_PARTIAL')
        out[n]=ING.audit_export(st,{'jurisdiction':None,
            'rulepacks':[{'rulepack_id':s['pack'],'version':'1','enabled':True}]})
    elif op=='import_dup':
        out[n]=ING.validate_import({'documents':[copy.deepcopy(st['documents'][0]),
            copy.deepcopy(st['documents'][0])],'fragments':[],'candidates':[],'rulepacks':[]})
    elif op=='import_badhash':
        d=copy.deepcopy(st['documents'][0]); d['integrity']['sha256']='nope'; out[n]=ING.validate_document(d)
    elif op=='import_script':
        d=copy.deepcopy(st['documents'][0]); d['title']='<script>x</script>'; out[n]=ING.validate_document(d)
    elif op=='import_httpurl':
        d=copy.deepcopy(st['documents'][0])
        d['origin']={'type':'official_url','url':'http://x.invalid/a','filename':None}
        out[n]=ING.validate_document(d)
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('py ingest steps:', len(out))
