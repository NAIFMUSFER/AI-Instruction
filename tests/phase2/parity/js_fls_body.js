const fs=require('fs'), _np=require('path'), _os=require('os');
const HERE=__dirname, FIXD=_np.resolve(HERE,'..','fixtures');
const OUT=process.env.ACS_PARITY_JS||_np.join(_os.tmpdir(),'acs_parity_js_fls.json');
const S=JSON.parse(fs.readFileSync(_np.join(FIXD,'fls_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const out={};
S.queries.forEach(q=>{
  const m=C(S.models[q.m]);
  const before=JSON.stringify(m);
  const f=compileFls(m,q.bid,q.pos,q.rot);
  if(JSON.stringify(m)!==before) throw new Error('compiler mutated the model: '+q.n);
  out[q.n]={fls:f, summary:flsSummary(f), audit:flsAudit(f), render:flsRenderItems(f),
    rule_inputs:flsRuleInputs(f), validate:validateFls(f)};
});
const v=compileFls(C(S.models.villa_fls),'bld_0');
out['__lookup__']={byId:flsElementById(v,'bld_0.fls.d_sd1'),
  none:flsElementById(v,'nope'),
  world:flsToWorld(compileFls(C(S.models.villa_fls),'bld_0',{x:6,z:-2},18),5,4),
  egress:flsEgressFacts(C(S.models.villa_fls),'bld_0','bld_0.g.majlis'),
  egress_missing:flsEgressFacts(C(S.models.villa_fls),'bld_0','nope')};
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('js fls scenarios:', Object.keys(out).length);
