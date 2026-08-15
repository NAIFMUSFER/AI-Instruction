const fs=require('fs'), _np=require('path'), _os=require('os');
const HERE=__dirname, FIXD=_np.resolve(HERE,'..','fixtures');
const OUT=process.env.ACS_PARITY_JS||_np.join(_os.tmpdir(),'acs_parity_js_mep.json');
const S=JSON.parse(fs.readFileSync(_np.join(FIXD,'mep_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const out={};
S.queries.forEach(q=>{
  const m=C(S.models[q.m]);
  const before=JSON.stringify(m);
  const mep=compileMep(m,q.bid,q.pos,q.rot);
  if(JSON.stringify(m)!==before) throw new Error('compiler mutated the model: '+q.n);
  out[q.n]={mep:mep, summary:mepSummary(mep), render:mepRenderItems(mep),
    rule_inputs:mepRuleInputs(mep), interferences:mepInterferences(mep),
    validate:validateMep(mep)};
});
const v=compileMep(C(S.models.villa_mep),'bld_0');
out['__lookup__']={byId:mepElementById(v,'bld_0.mep.eq_db'),
  sys:mepSystemById(v,'sys_cw'), none:mepElementById(v,'nope'),
  world:mepToWorld(compileMep(C(S.models.villa_mep),'bld_0',{x:4,z:-6},33),3,7),
  no_adapter:mepSummary(compileMep(C(S.models.phase1_points),'bld_0',null,0,null,null,false))};
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('js mep scenarios:', Object.keys(out).length);
