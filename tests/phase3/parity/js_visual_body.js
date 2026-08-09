const fs=require('fs'), path=require('path');
const HERE=__dirname, PHASE=path.resolve(HERE,'..');
const OUT=process.env.ACS_PARITY_JS||path.join(require('os').tmpdir(),'acs_parity_js.json');
const S=JSON.parse(fs.readFileSync(path.join(PHASE,'fixtures','visual_scenarios.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const out={};
S.queries.forEach(q=>{
  const m=C(S.models[q.m]);
  const before=JSON.stringify(m);
  const s=compileVisualScene(m,q.bid,q.pos,q.rot,{mode:q.mode,theme:q.theme,
    lighting:q.light,quality:q.quality,include_decoration:!!q.deco,
    include_entourage:!!q.ent,entourage_count:q.entn||0,
    clash_overlay:!!q.clash,at:AT});
  if(JSON.stringify(m)!==before) throw new Error('compiler mutated the model: '+q.n);
  out[q.n]={scene:s,summary:visSummary(s),rule_inputs:visRuleInputs(s),
    validate:visValidateScene(s),instancing:visInstancingPlan(s),
    lod:visLodPlan(s,null),block:visPresentationBlock(s),
    export_eng:visExportScene(s,false),export_pres:visExportScene(s,true),
    buffers:visControlBuffers(s,null),
    signature:visGeometrySignature(s,compileArchitecture(C(S.models[q.m]),q.bid,q.pos,q.rot)),
    snapshot:visSnapshotRequest(s,{width:2560,height:1440,format:'PNG'}),
    render:visRenderMetadata(s,visSnapshotRequest(s,{width:2560,height:1440,format:'PNG'}),
      'DETERMINISTIC_RENDER',AT,null)};
});
S.drawings.forEach(d=>{
  const arch=compileArchitecture(C(S.models[d.m]),'bld_0',null,0);
  if(d.kind==='plan') out['draw:'+d.n]=visFloorPlan(arch,d.level,d.style||null,'bld_0');
  else if(d.kind==='section')
    out['draw:'+d.n]=visSection(arch,d.axis,(d.position===undefined)?null:d.position,'bld_0');
  else out['draw:'+d.n]=visElevation(arch,d.face,'bld_0');
});
const v=compileVisualScene(C(S.models.villa),'bld_0',null,0,{mode:'PRESENTATION',at:AT});
const arch=compileArchitecture(C(S.models.villa),'bld_0',null,0);
const req=visAiEnhancementRequest(v,'warm evening light',null,0.4,arch);
out['__ops__']={
  frame:VIS_CAMERA_PRESETS.map(p=>visFrameCamera(v,p,null)),
  frame_room:visFrameCamera(v,'INTERIOR_ROOM','bld_0.g.majlis@0'),
  frame_unknown:visFrameCamera(v,'NOPE',null),
  object:visObjectById(v,v.objects[0].id), object_missing:visObjectById(v,'nope'),
  by_layer:visObjectsByLayer(v,'ARCHITECTURE').length,
  ai:req,
  ai_ok:visCheckConsistency(req,{door_count:req.geometry_signature.door_count,
    floor_count:req.geometry_signature.floor_count,
    footprint:req.geometry_signature.footprint,
    model_hash:req.geometry_signature.model_hash}),
  ai_drift:visCheckConsistency(req,{door_count:99,window_count:7,floor_count:5,
    room_count:100,stair_count:9,wall_count:2,footprint:[0,0,999,999],
    model_hash:'deadbeef'},0.5),
  ai_no_buffers:visCheckConsistency({geometry_signature:req.geometry_signature,
    control_buffers:[]},{door_count:req.geometry_signature.door_count}),
  currency:visCheckRenderCurrency(visRenderMetadata(v,null,null,AT,null),
    C(S.models.villa),'bld_0'),
  currency_stale:visCheckRenderCurrency(visRenderMetadata(v,null,null,AT,null),
    C(S.models.hotel),'bld_0'),
  currency_nohash:visCheckRenderCurrency({},C(S.models.villa),'bld_0'),
  snapshot_huge:visSnapshotRequest(v,{width:20000,height:20000,format:'TIFF',
    camera:'NOPE',quality:5}),
  snapshot_zero:visSnapshotRequest(v,{width:0,height:0}),
  render_ai:visRenderMetadata(v,null,'AI_ENHANCED_VISUALISATION',AT,{model:'none'}),
  render_bogus:visRenderMetadata(v,null,'MAGIC',AT,null),
  assets:visAssetLibrary(), asset_one:visAssetById('asset.proc.tree'),
  asset_missing:visAssetById('nope'),
  asset_bad:visValidateAsset({id:'x',type:'y',asset_class:'NOPE',license:'UNKNOWN',
    dimensions_m:{w:0,d:1,h:1},source:'s',script:'alert(1)'}),
  asset_good:visValidateAsset(visAssetById('asset.proc.tree')),
  asset_not_object:visValidateAsset('nope'),
  material:visMaterial('marble'), material_missing:visMaterial('nope'),
  lod_tight:visLodPlan(v,10),
  layer_eng:(function(){const e=compileVisualScene(C(S.models.villa),'bld_0',null,0,
    {mode:'ENGINEERING',at:AT}); return visSetLayerVisible(e,'MEP',false).slice(0,2);})(),
  layer_pres:(function(){const p=compileVisualScene(C(S.models.villa),'bld_0',null,0,
    {mode:'PRESENTATION',at:AT}); return visSetLayerVisible(p,'MEP',false).slice(0,2);})(),
  layer_unknown:visSetLayerVisible(C(v),'NOPE',false).slice(0,2),
  bad_mode:compileVisualScene(C(S.models.villa),'bld_0',null,0,{mode:'NOPE',theme:'NOPE',
    lighting:'NOPE',quality:'NOPE',at:AT}).summary};

/* ---- حالات خصومية: مشاهد صالحة وباطلة متطابقة تمرّ على المدقّقَين ---- */
const advVisual=(over)=>Object.assign({id:'vo_1',kind:'TREE',layer:'LANDSCAPE',
  geometry:{type:'box',cx:0,cy:1,cz:0,ex:1,ey:2,ez:1,rot_y:0},
  material:'grass',material_provenance:'SYSTEM_DEFAULT',semantic:false,visual_only:true,
  source_element_id:null},over||{});
const advModel=(over)=>Object.assign({id:'mo_1',kind:'WALL',layer:'ARCHITECTURE',
  geometry:{type:'box',cx:0,cy:1.5,cz:0,ex:6,ey:3,ez:0.2,rot_y:0},
  material:'paint_white',material_provenance:'SYSTEM_DEFAULT',semantic:true,
  visual_only:false,source_element_id:'bld_0.flr_0.wall_0'},over||{});
const ADV=[
 ['valid_visual', {materials:[],objects:[advVisual()]}],
 ['valid_model', {materials:[],objects:[advModel()]}],
 ['valid_mixed', {materials:[],objects:[advVisual(),advModel()]}],
 ['visual_with_source', {materials:[],objects:[advVisual({source_element_id:'wall-123'})]}],
 ['visual_with_empty_source', {materials:[],objects:[advVisual({source_element_id:''})]}],
 ['visual_decoration_with_source', {materials:[],
   objects:[advVisual({visual_class:VIS_DECORATION_CLASS,layer:'FURNITURE',
     source_element_id:'wall-123'})]}],
 ['visual_landscape_with_source', {materials:[],
   objects:[advVisual({visual_class:VIS_LANDSCAPE_CLASS,source_element_id:'wall-123'})]}],
 ['visual_entourage_with_source', {materials:[],
   objects:[advVisual({visual_class:VIS_ENTOURAGE_CLASS,source_element_id:'wall-123'})]}],
 ['visual_asset_with_source', {materials:[],
   objects:[advVisual({asset_id:'asset.proc.tree',source_element_id:'wall-123'})]}],
 ['visual_theme_with_source', {materials:[],
   objects:[advVisual({material:'marble',material_provenance:'VISUAL_THEME',
     source_element_id:'wall-123'})]}],
 ['model_without_source', {materials:[],objects:[advModel({source_element_id:null})]}],
 ['visual_marked_semantic', {materials:[],objects:[advVisual({semantic:true})]}],
 ['material_not_in_library', {materials:[],objects:[advModel({material:'unobtanium'})]}],
 ['bad_provenance', {materials:[],objects:[advModel({material_provenance:'ENGINEERING'})]}],
 ['structural_material', {materials:[Object.assign(visMaterial('concrete'),
   {structural_material:true})],objects:[]}],
 ['fire_rated_material', {materials:[Object.assign(visMaterial('concrete'),
   {fire_rating:120})],objects:[]}]];
out['__adversarial__']={};
ADV.forEach(pair=>{ out['__adversarial__'][pair[0]]={
  accepted:visValidateScene(pair[1]).length===0, issues:visValidateScene(pair[1])}; });
const advScene=compileVisualScene(C(S.models.villa),'bld_0',null,0,{mode:'PRESENTATION',at:AT});
const advArch=compileArchitecture(C(S.models.villa),'bld_0',null,0);
const advReq=visAiEnhancementRequest(advScene,'evening',null,0.4,advArch);
out['__ai_contract__']={
  requested:advReq.requested_control_buffers,
  descriptors:advReq.control_buffers,
  subset:visAiEnhancementRequest(advScene,'x',['depth','object_id'],0.4,advArch),
  unknown_dropped:visAiEnhancementRequest(advScene,'x',['depth','xray'],0.4,advArch)
    .requested_control_buffers,
  no_signature:visCheckConsistency({requested_control_buffers:['depth']},{door_count:9}),
  null_signature:visCheckConsistency({requested_control_buffers:['depth'],
    geometry_signature:null},{door_count:9}),
  empty_signature:visCheckConsistency({requested_control_buffers:['depth'],
    geometry_signature:{}},{door_count:9}),
  nothing:visCheckConsistency({},{door_count:9}),
  no_buffers:visCheckConsistency({geometry_signature:advReq.geometry_signature,
    requested_control_buffers:[]},{door_count:advReq.geometry_signature.door_count}),
  legacy_list_buffers:visCheckConsistency({geometry_signature:advReq.geometry_signature,
    control_buffers:['depth','edge']},{door_count:advReq.geometry_signature.door_count})};

fs.writeFileSync(OUT, JSON.stringify(out));
console.log('js visual scenarios:', Object.keys(out).length);
