const fs=require('fs'), _np=require('path'), _os=require('os');
const HERE=__dirname, FIXD=_np.resolve(HERE,'..','fixtures');
const OUT=process.env.ACS_PARITY_JS||_np.join(_os.tmpdir(),'acs_parity_js_struct.json');
const S=JSON.parse(fs.readFileSync(_np.join(FIXD,'struct_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const out={};
S.queries.forEach(q=>{
  const m=C(S.models[q.m]);
  const before=JSON.stringify(m);
  const st=compileStructure(m,q.bid,q.pos,q.rot);
  if(JSON.stringify(m)!==before) throw new Error('compiler mutated the model: '+q.n);
  const world=(st.grid_systems||[]).map(gs=>gs.grids.map(g=>structGridToWorld(st,gs,g,50)));
  out[q.n]={struct:st, summary:structSummary(st), render:structRenderItems(st),
    rule_inputs:structRuleInputs(st), grids_world:world,
    validate:validateStructure(st)};
});
out['__suggest__']={
  none:suggestStructuralGrid(C(S.models.no_struct),null,null,'bld_0'),
  xz:suggestStructuralGrid(C(S.models.no_struct),5,4,'bld_0'),
  x_only:suggestStructuralGrid(C(S.models.no_struct),6,null,'bld_0'),
  empty:suggestStructuralGrid({levels:[],floors:{}},5,5,'bld_0')};
out['__lookup__']={
  byId:structElementById(compileStructure(C(S.models.villa_struct),'bld_0'),'bld_0.C_A1'),
  grid:structElementById(compileStructure(C(S.models.villa_struct),'bld_0'),'bld_0.grid_x_A'),
  none:structElementById(compileStructure(C(S.models.villa_struct),'bld_0'),'nope'),
  world:structToWorld(compileStructure(C(S.models.villa_struct),'bld_0',{x:3,z:-2},60),4,5)};
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('js structural scenarios:', Object.keys(out).length);
