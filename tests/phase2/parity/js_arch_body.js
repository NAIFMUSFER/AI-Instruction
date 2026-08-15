const fs=require('fs'), _np=require('path'), _os=require('os');
const HERE=__dirname, FIXD=_np.resolve(HERE,'..','fixtures');
const OUT=process.env.ACS_PARITY_JS||_np.join(_os.tmpdir(),'acs_parity_js_arch.json');
const S=JSON.parse(fs.readFileSync(_np.join(FIXD,'arch_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const out={};
S.queries.forEach(q=>{
  const m=C(S.models[q.m]);
  const before=JSON.stringify(m);
  const arch=compileArchitecture(m,q.bid,q.pos,q.rot);
  if(JSON.stringify(m)!==before) throw new Error('compiler mutated the model: '+q.n);
  const anchors={}, doors={};
  (arch.openings||[]).forEach(o=>{ anchors[o.id]=archOpeningAnchor(arch,o.id);
    if(o.type==='DOOR') doors[o.id]=archDoorConnectsConfirmed(arch,o.id); });
  const world=(arch.walls||[]).map(w=>[w.id,archToWorld(arch,w.start.x,w.start.z),
                                             archToWorld(arch,w.end.x,w.end.z)]);
  out[q.n]={arch:arch,summary:archSummary(arch),anchors:anchors,doors:doors,world:world,
    validate:validateArchitecture(arch)};
});
/* جدار مشترك بين فراغين محدّدين */
{ const a=compileArchitecture(C(S.models.shared),'bld_0',null,0);
  out['__shared__']={w:archSharedWallBetween(a,'bld_0.g.a','bld_0.g.b'),
    missing:archSharedWallBetween(a,'bld_0.g.a','nope'),
    byId:archElementById(a,'bld_0.flr_0.wall_0'),
    envelopeById:archElementById(a,'bld_0.envelope'),
    none:archElementById(a,'no_such_id')}; }
fs.writeFileSync(OUT,JSON.stringify(out));
console.log('js arch scenarios:',Object.keys(out).length);
