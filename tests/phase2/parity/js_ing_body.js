const fs=require('fs'), _np=require('path'), _os=require('os');
const HERE=__dirname, FIXD=_np.resolve(HERE,'..','fixtures');
const OUT=process.env.ACS_PARITY_JS||_np.join(_os.tmpdir(),'acs_parity_js_ing.json');
const S=JSON.parse(fs.readFileSync(_np.join(FIXD,'ing_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const AT='T0', WHO='explicit_manual_approval';
const LONG={meta:{type:'office'},site:{w:60,d:20},wall_h:3,wall_t:0.2,floor_height:3.2,
  levels:[{index:0,template:'g'}],floors:{g:{rooms:[
    {id:'r1',rect:[0,0,4,4],doors:[{edge:'E',offset:2,width:0.9}]},
    {id:'hall',rect:[4,0,24,4],doors:[{edge:'W',offset:2,width:0.9},{edge:'E',offset:2,width:0.9}]},
    {id:'r2',rect:[28,0,4,4],doors:[{edge:'W',offset:2,width:0.9}]}]}}};
const subj=()=>[resolveSubject(C(LONG),buildRelationships(C(LONG),'bld_0'),'ROUTE:bld_0.g.r1>bld_0.g.r2','bld_0')];
const cv=(st,d)=>{const doc=ingDocument(st,d);
  transitionDocument(doc,'SOURCE_IDENTIFIED',WHO,{note:'id'},AT,null);
  return transitionDocument(doc,'CONTENT_VERIFIED',WHO,{note:'content'},AT,null);};
function packFlow(st,doc,cand,pack,stop){
  cv(st,doc); verifyCandidate(ingCandidate(st,cand),st,null,AT,WHO,null);
  const p=ingRulePack(st,pack,'1'); p.candidate_ids=[cand];
  if(stop!=='DRAFT'){ verifyPack(p,st,'UNDER_REVIEW',null,AT,WHO,null);
                      verifyPack(p,st,stop,null,AT,WHO,null); }
  return resolveActiveRules({jurisdiction:null,rulepacks:[{rulepack_id:pack,version:'1',enabled:true}]},st); }
const out={};
S.steps.forEach(s=>{
  const st=ingestFixtureStore();
  if(s.op==='store_issues') out[s.n]=ingestStoreIssues(st);
  else if(s.op==='regulatory_count') out[s.n]=ingestRegulatoryRuleCount(st);
  else if(s.op==='doc_bytes'){ const d=ingDocument(st,s.doc); out[s.n]=verifyDocumentBytes(d,d.synthetic_content); }
  else if(s.op==='doc_bytes_mod'){ const d=ingDocument(st,s.doc); out[s.n]=verifyDocumentBytes(d,d.synthetic_content+' X'); }
  else if(s.op==='rule_hash') out[s.n]=ruleDefinitionHash(ingCandidate(st,s.cand).proposed_rule);
  else if(s.op==='transition'){ const d=ingDocument(st,s.doc);
    out[s.n]=transitionDocument(d,s.to,(s.method===undefined?WHO:s.method),{note:'e'},AT,null); }
  else if(s.op==='seq_official'){ const d=ingDocument(st,s.doc);
    transitionDocument(d,'SOURCE_IDENTIFIED',WHO,{note:'e'},AT,null);
    out[s.n]=transitionDocument(d,'OFFICIAL_SOURCE_VERIFIED',WHO,{note:'e'},AT,null); }
  else if(s.op==='verify_cand'){ const c=ingCandidate(st,s.cand);
    out[s.n]={result:verifyCandidate(c,st,null,AT,WHO,null),status:c.status}; }
  else if(s.op==='content_then_verify'){ cv(st,s.doc); const c=ingCandidate(st,s.cand);
    const r=verifyCandidate(c,st,null,AT,(s.method||WHO),null);
    out[s.n]={result:r,status:c.status,still_valid:verificationStillValid(c,st)}; }
  else if(s.op==='assess_all'){ cv(st,s.doc);
    out[s.n]=st.candidates.map(c=>[c.candidate_id,assessCandidate(c,st)[0]]); }
  else if(s.op==='pack_flow') out[s.n]=packFlow(st,s.doc,s.cand,s.pack,s.stop);
  else if(s.op==='project_eval'){
    s.docs.forEach(d=>cv(st,d));
    const refs=[];
    s.packs.forEach(pk=>{ pk.cands.forEach(c=>verifyCandidate(ingCandidate(st,c),st,null,AT,WHO,null));
      const p=ingRulePack(st,pk.pack,'1'); p.candidate_ids=pk.cands;
      verifyPack(p,st,'UNDER_REVIEW',null,AT,WHO,null); verifyPack(p,st,'VERIFIED_PARTIAL',null,AT,WHO,null);
      refs.push({rulepack_id:pk.pack,version:'1',enabled:true}); });
    out[s.n]=evaluateProject({jurisdiction:null,rulepacks:refs},subj(),st,{evaluated_at:AT}); }
  else if(s.op==='project_conflict'){
    ['SYNDOC-ED1','SYNDOC-ED2'].forEach(d=>cv(st,d));
    const a=ingCandidate(st,'SYNCAND-ED1-T1'), b=ingCandidate(st,'SYNCAND-ED2-T1');
    b.proposed_rule.rule_id=a.proposed_rule.rule_id;
    verifyCandidate(a,st,null,AT,WHO,null); verifyCandidate(b,st,null,AT,WHO,null);
    const p1=ingRulePack(st,'TEST_ONLY.SYNPACK','1'); p1.candidate_ids=['SYNCAND-ED1-T1'];
    const p2=ingRulePack(st,'TEST_ONLY.SYNPACK_ED2','1'); p2.candidate_ids=['SYNCAND-ED2-T1'];
    [p1,p2].forEach(p=>{verifyPack(p,st,'UNDER_REVIEW',null,AT,WHO,null);
                        verifyPack(p,st,'VERIFIED_PARTIAL',null,AT,WHO,null);});
    out[s.n]=evaluateProject({jurisdiction:null,rulepacks:[
      {rulepack_id:'TEST_ONLY.SYNPACK',version:'1',enabled:true},
      {rulepack_id:'TEST_ONLY.SYNPACK_ED2',version:'1',enabled:true}]},subj(),st,{evaluated_at:AT}); }
  else if(s.op==='audit'){ packFlow(st,s.doc,s.cand,s.pack,'VERIFIED_PARTIAL');
    out[s.n]=ingestAuditExport(st,{jurisdiction:null,
      rulepacks:[{rulepack_id:s.pack,version:'1',enabled:true}]}); }
  else if(s.op==='import_dup') out[s.n]=validateImport({documents:[C(st.documents[0]),C(st.documents[0])],
    fragments:[],candidates:[],rulepacks:[]});
  else if(s.op==='import_badhash'){ const d=C(st.documents[0]); d.integrity.sha256='nope';
    out[s.n]=validateDocument(d); }
  else if(s.op==='import_script'){ const d=C(st.documents[0]); d.title='<script>x</script>';
    out[s.n]=validateDocument(d); }
  else if(s.op==='import_httpurl'){ const d=C(st.documents[0]);
    d.origin={type:'official_url',url:'http://x.invalid/a',filename:null};
    out[s.n]=validateDocument(d); }
});
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('js ingest steps:', Object.keys(out).length);
