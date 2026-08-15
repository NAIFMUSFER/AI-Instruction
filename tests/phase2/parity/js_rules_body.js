const fs=require('fs'), _np=require('path'), _os=require('os');
const HERE=__dirname, FIXD=_np.resolve(HERE,'..','fixtures');
const OUT=process.env.ACS_PARITY_JS||_np.join(_os.tmpdir(),'acs_parity_js_rules.json');
const S=JSON.parse(fs.readFileSync(_np.join(FIXD,'rule_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const out={};
const subj=(b,rels,id)=>resolveSubject(b,rels,id,'bld_0');
S.queries.forEach(q=>{
  const b=C(S.models[q.m]), rels=buildRelationships(b,'bld_0');
  const ctx=C(q.ctx||{});
  if(q.buildingSubject) ctx.subjects={BUILDING:subj(b,rels,'BUILDING:bld_0')};
  const pair=ruleById(q.rule,[],q.rs);
  out[q.n]=evaluateRule(pair[1],subj(b,rels,q.subj),ctx,pair[0],[]);
});
S.sets.forEach(q=>{
  const b=C(S.models[q.m]), rels=buildRelationships(b,'bld_0');
  const ctx={evaluated_at:'T0'};
  if(q.buildingSubject) ctx.subjects={BUILDING:subj(b,rels,'BUILDING:bld_0')};
  const subs=q.subjects.map(x=>subj(b,rels,x)).filter(Boolean);
  const run=evaluateRuleSet(q.ruleset,subs,ctx,[]);
  out[q.n]={run:run,agg:aggregateRuleResults(run.results,ruleSetById(q.ruleset,[]))};
});
out['__meta__']={engine:RULE_ENGINE_VERSION,regulatory:regulatoryRuleCount([]),issues:ruleIssues([])};
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('js rule scenarios:', Object.keys(out).length-1);
