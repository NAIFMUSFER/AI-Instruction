/* ======================================================================
   المرحلة 3 — اختبارات خصومية دائمة لثوابت العرض البصري.
   تُثبت أنّ القواعد تُرفَض عند خرقها فعلاً، لا أنّها موصوفة فقط:
   قاعدة المصدر المتناظرة · عقد ممرّات التحكّم · انحراف الذكاء الاصطناعي ·
   المادة البصرية · بيانات الأصل · السمة · العرض الهندسي.
   ====================================================================== */
const fs=require('fs'), path=require('path');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const SC=JSON.parse(fs.readFileSync(path.join(HERE,'fixtures','visual_scenarios.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const V=(name,opts)=>compileVisualScene(C(SC.models[name]),'bld_0',null,0,
  Object.assign({at:AT},opts||{}));
const AR=(name)=>compileArchitecture(C(SC.models[name]),'bld_0',null,0);
const codes=s=>visValidateScene(s).map(i=>i.code).sort();
/* جسم بصريّ صالح تماماً عدا ما يعبث به كل اختبار */
const visualObj=(over)=>Object.assign({
  id:'vo_1',kind:'TREE',layer:'LANDSCAPE',
  geometry:{type:'box',cx:0,cy:1,cz:0,ex:1,ey:2,ez:1,rot_y:0},
  material:'grass',material_provenance:'SYSTEM_DEFAULT',
  semantic:false,visual_only:true,source_element_id:null},over||{});
const modelObj=(over)=>Object.assign({
  id:'mo_1',kind:'WALL',layer:'ARCHITECTURE',
  geometry:{type:'box',cx:0,cy:1.5,cz:0,ex:6,ey:3,ez:0.2,rot_y:0},
  material:'paint_white',material_provenance:'SYSTEM_DEFAULT',
  semantic:true,visual_only:false,source_element_id:'bld_0.flr_0.wall_0'},over||{});
const sceneOf=(objs)=>({materials:[],objects:objs});

console.log('\n== A — visual_only WITH a source element must be REJECTED ==');
/* القاعدة عامة: لا تعتمد على أي تصنيف أو مادة أو سمة أو أصل أو تخصّص */
const CLASSES=[
  ['generic visual object', {}],
  ['landscape-classed object', {visual_class:VIS_LANDSCAPE_CLASS}],
  ['entourage-classed object', {visual_class:VIS_ENTOURAGE_CLASS}],
  ['decoration-classed object', {visual_class:VIS_DECORATION_CLASS,layer:'FURNITURE'}],
  ['asset-based object', {asset_id:'asset.proc.tree',asset_fallback:false}],
  ['system-generated roof cap', {kind:'ROOF_CAP',layer:'ARCHITECTURE',
    material:'concrete',geometry_source:'display_fallback'}],
  ['theme-generated object', {material:'marble',material_provenance:'VISUAL_THEME'}],
  ['AI-suggested-material object', {material:'stone',material_provenance:'AI_SUGGESTED'}],
  ['instanced object', {instance_key:'LANDSCAPE|asset.proc.tree|grass'}],
  ['simplified-LOD object', {lod:'SIMPLIFIED'}],
  ['MEP-layered visual object', {layer:'MEP',kind:'MEP_MARKER'}],
  ['FLS-layered visual object', {layer:'FLS',kind:'FLS_MARKER'}],
  ['site ground plane', {kind:'GROUND',layer:'SITE',geometry_source:'display_fallback'}]];
CLASSES.forEach(pair=>{
  const o=visualObj(Object.assign({source_element_id:'wall-123'},pair[1]));
  const c=codes(sceneOf([o]));
  chk('A · '+pair[0]+' with a source element is rejected',
      c.indexOf('VISUAL_ONLY_OBJECT_WITH_SOURCE')>=0, JSON.stringify(c));
});
chk('A · the decoration specialisation is reported IN ADDITION, never instead',
    JSON.stringify(codes(sceneOf([visualObj({visual_class:VIS_DECORATION_CLASS,
      source_element_id:'wall-123'})])))===
    JSON.stringify(['DECORATION_LINKED_TO_MODEL_ELEMENT','VISUAL_ONLY_OBJECT_WITH_SOURCE']));
chk('A · the rejection code is part of the declared vocabulary',
    VIS_VALIDATION_CODES.indexOf('VISUAL_ONLY_OBJECT_WITH_SOURCE')>=0);
chk('A · an empty-string source is still a source and is rejected',
    codes(sceneOf([visualObj({source_element_id:''})]))
      .indexOf('VISUAL_ONLY_OBJECT_WITH_SOURCE')>=0);
chk('A · validation is deterministic across repeated runs',
    JSON.stringify(codes(sceneOf([visualObj({source_element_id:'wall-123'})])))===
    JSON.stringify(codes(sceneOf([visualObj({source_element_id:'wall-123'})]))));

console.log('\n== B — visual_only=false WITHOUT a source element must be REJECTED ==');
[['architecture wall',{}],
 ['structure member',{layer:'STRUCTURE',kind:'COLUMN'}],
 ['MEP segment',{layer:'MEP',kind:'SEGMENT'}],
 ['FLS device',{layer:'FLS',kind:'DEVICE'}]].forEach(pair=>{
  const o=modelObj(Object.assign({source_element_id:null},pair[1]));
  chk('B · modelled '+pair[0]+' with no source is rejected',
      codes(sceneOf([o])).indexOf('MODELLED_OBJECT_WITHOUT_SOURCE')>=0);
});
chk('B · a modelled object with an absent source key is rejected', (function(){
  const o=modelObj(); delete o.source_element_id;
  return codes(sceneOf([o])).indexOf('MODELLED_OBJECT_WITHOUT_SOURCE')>=0; })());

console.log('\n== ACCEPTANCE — the two valid shapes must pass cleanly ==');
chk('visual_only:true + source_element_id:null is accepted',
    codes(sceneOf([visualObj()])).length===0);
chk('visual_only:true with the source key absent is accepted', (function(){
  const o=visualObj(); delete o.source_element_id;
  return codes(sceneOf([o])).length===0; })());
chk('visual_only:false + a valid source element is accepted',
    codes(sceneOf([modelObj()])).length===0);
chk('a mixed valid scene is accepted',
    codes(sceneOf([visualObj(),modelObj()])).length===0);

console.log('\n== FULL PATH — the compiler never emits a violating object ==');
const NAMES=Object.keys(SC.models);
chk('no compiled scene in any mode violates the source-reference invariant',
    NAMES.every(n=>VIS_MODES.every(md=>{
      const s=V(n,{mode:md,include_decoration:true,include_entourage:true,
        entourage_count:4});
      return visValidateScene(s).length===0; })));
chk('every compiled visual-only object has a null source across every fixture',
    NAMES.every(n=>V(n,{mode:'PRESENTATION',include_decoration:true,include_entourage:true,
      entourage_count:4}).objects.filter(o=>o.visual_only)
      .every(o=>o.source_element_id===null)));
chk('every compiled modelled object has a non-null source across every fixture',
    NAMES.every(n=>V(n,{mode:'ENGINEERING'}).objects.filter(o=>!o.visual_only)
      .every(o=>!!o.source_element_id)));
chk('injecting a violation into a compiled scene is caught by the validator', (function(){
  const s=V('villa',{mode:'PRESENTATION'});
  const tampered=C(s);
  const target=tampered.objects.filter(o=>o.visual_only)[0];
  target.source_element_id=AR('villa').walls[0].id;
  return visValidateScene(s).length===0
    && visValidateScene(tampered).some(i=>i.code==='VISUAL_ONLY_OBJECT_WITH_SOURCE'); })());
chk('stripping a source from a compiled modelled object is caught', (function(){
  const t=C(V('villa',{mode:'PRESENTATION'}));
  t.objects.filter(o=>!o.visual_only)[0].source_element_id=null;
  return visValidateScene(t).some(i=>i.code==='MODELLED_OBJECT_WITHOUT_SOURCE'); })());

console.log('\n== C — AI response with a changed geometry signature ==');
const scene=V('villa',{mode:'PRESENTATION'});
const req=visAiEnhancementRequest(scene,'evening light',null,0.4,AR('villa'));
const sig=req.geometry_signature;
[['door count',{door_count:sig.door_count+7}],
 ['window count',{window_count:sig.window_count+3}],
 ['wall count',{wall_count:1}],
 ['stair location implied by a changed stair count',{stair_count:sig.stair_count+2}],
 ['floor count',{floor_count:sig.floor_count+4}],
 ['room count',{room_count:sig.room_count+11}],
 ['building footprint',{footprint:[0,0,999,999]}],
 ['source model hash',{model_hash:'deadbeefdeadbeef'}]].forEach(pair=>{
  const r=visCheckConsistency(req,pair[1]);
  chk('C · a changed '+pair[0]+' raises VISUAL_GEOMETRY_DRIFT',
      r.drift===true&&r.findings.some(f=>f.code==='VISUAL_GEOMETRY_DRIFT'));
  chk('C · that drift reports model_modified:false',
      r.model_modified===false&&r.image_accepted_as_geometry===false);
});
chk('C · a faithful image raises no drift',
    visCheckConsistency(req,{door_count:sig.door_count,window_count:sig.window_count,
      wall_count:sig.wall_count,stair_count:sig.stair_count,floor_count:sig.floor_count,
      room_count:sig.room_count,footprint:sig.footprint,
      model_hash:sig.model_hash}).drift===false);
chk('C · drift never rewrites the scene it was checked against', (function(){
  const before=JSON.stringify(scene.objects);
  visCheckConsistency(req,{door_count:999,footprint:[0,0,9,9]});
  return JSON.stringify(scene.objects)===before; })());
chk('C · drift never rewrites the canonical model', (function(){
  const m=C(SC.models.villa); const before=JSON.stringify(m);
  const r2=visAiEnhancementRequest(compileVisualScene(m,'bld_0',null,0,{at:AT}),'x',null,0.4,
    compileArchitecture(m,'bld_0',null,0));
  visCheckConsistency(r2,{door_count:999,floor_count:99});
  return JSON.stringify(m)===before; })());

console.log('\n== D — an AI request missing its geometry signature is REJECTED ==');
[['no signature key',{requested_control_buffers:['depth']}],
 ['null signature',{requested_control_buffers:['depth'],geometry_signature:null}],
 ['empty signature',{requested_control_buffers:['depth'],geometry_signature:{}}],
 ['nothing at all',{}]].forEach(pair=>{
  const r=visCheckConsistency(pair[1],{door_count:5});
  chk('D · '+pair[0]+' is rejected with VISUAL_SIGNATURE_MISSING',
      r.drift===true&&r.findings.some(f=>f.code==='VISUAL_SIGNATURE_MISSING'),
      JSON.stringify(r.findings.map(f=>f.code)));
});
chk('D · the missing-signature code is ERROR severity and declared',
    VIS_DRIFT_CODES.indexOf('VISUAL_SIGNATURE_MISSING')>=0
    &&VIS_DRIFT_SEVERITY.VISUAL_SIGNATURE_MISSING==='ERROR');
chk('D · a real request always carries a signature',
    !!visAiEnhancementRequest(scene,'x',null,0.4,AR('villa')).geometry_signature.model_hash);

console.log('\n== CONTROL BUFFER CONTRACT ==');
chk('an AI request declares the buffers it requested, in order',
    Array.isArray(req.requested_control_buffers)
    &&req.requested_control_buffers.length===VIS_CONTROL_BUFFERS.length);
chk('every requested buffer travels with a deterministic descriptor',
    req.requested_control_buffers.every(k=>req.control_buffers[k]
      &&req.control_buffers[k].deterministic===true
      &&req.control_buffers[k].from_model===true));
chk('the object-id descriptor carries the real modelled object ids', (function(){
  const d=req.control_buffers.object_id;
  const ids={}; scene.objects.forEach(o=>{ids[o.id]=o;});
  return d.ids.length>0&&d.ids.every(id=>ids[id]&&!ids[id].visual_only); })());
/* الفراغ يحمل معرّفين قانونيين: id بلاحقة المستوى و space_id بدونها.
   الممرّ يحمل المرجع الذي تحمله الأجسام فعلاً، ويجب أن يُحلّ إلى أحدهما. */
chk('the room-id descriptor carries real space ids', (function(){
  const d=req.control_buffers.room_id;
  const spaces={};
  (AR('villa').spaces||[]).forEach(s=>{spaces[s.id]=true; spaces[s.space_id]=true;});
  return d.ids.length>0&&d.ids.every(id=>spaces[id]); })());
chk('the semantic-mask descriptor carries real object classes',
    req.control_buffers.semantic_mask.classes.every(k=>
      scene.objects.some(o=>o.kind===k&&!o.visual_only)));
chk('no descriptor claims to be a rendered pixel buffer',
    Object.keys(req.control_buffers).every(k=>
      req.control_buffers[k].pixels===undefined
      &&req.control_buffers[k].image===undefined
      &&req.control_buffers[k].data===undefined));
chk('a request for a subset carries only that subset', (function(){
  const r=visAiEnhancementRequest(scene,'x',['depth','object_id'],0.4,AR('villa'));
  return r.requested_control_buffers.length===2
    &&Object.keys(r.control_buffers).length===2; })());
chk('an unknown buffer name is dropped rather than fabricated', (function(){
  const r=visAiEnhancementRequest(scene,'x',['depth','xray'],0.4,AR('villa'));
  return r.requested_control_buffers.indexOf('xray')<0; })());
chk('a request with no buffers at all is flagged',
    visCheckConsistency({geometry_signature:sig,requested_control_buffers:[]},
      {door_count:sig.door_count}).findings
      .some(f=>f.code==='VISUAL_CONTROL_BUFFER_MISSING'));

console.log('\n== AI SAFETY INVARIANTS REMAIN ==');
chk('writes_to_model is false on every request shape',
    [null,'x'].every(p=>visAiEnhancementRequest(scene,p,null,0.4,AR('villa'))
      .writes_to_model===false));
chk('generator_shipped is false', req.generator_shipped===false);
chk('network_call is false', req.network_call===false);
chk('an AI image is authorised VISUALISATION, never the model',
    req.authority==='VISUALISATION'
    &&visRenderMetadata(scene,null,'AI_ENHANCED_VISUALISATION',AT,{}).is_engineering_model
      ===false);
chk('the may-not-change list still covers every layout feature',
    ['wall_positions','door_count','window_count','floor_count','stair_location',
     'building_footprint','room_count','level_elevations']
      .every(k=>req.may_not_change.indexOf(k)>=0));

console.log('\n== E — a visual material cannot be made structural ==');
chk('E · every library material denies structural, fire and thermal properties',
    Object.keys(VIS_MATERIALS).map(k=>visMaterial(k)).every(m=>
      m.structural_material===false&&m.fire_rating===null&&m.thermal_property===null));
chk('E · a tampered material is rejected by the validator',
    codes({materials:[Object.assign(visMaterial('concrete'),{structural_material:true})],
      objects:[]}).indexOf('MATERIAL_CARRIES_ENGINEERING_PROPERTY')>=0);
chk('E · a material claiming a fire rating is rejected',
    codes({materials:[Object.assign(visMaterial('concrete'),{fire_rating:120})],
      objects:[]}).indexOf('MATERIAL_CARRIES_ENGINEERING_PROPERTY')>=0);
chk('E · a material claiming a thermal property is rejected',
    codes({materials:[Object.assign(visMaterial('glass_clear'),{thermal_property:0.9})],
      objects:[]}).indexOf('MATERIAL_CARRIES_ENGINEERING_PROPERTY')>=0);
chk('E · a material outside the library is rejected on an object',
    codes(sceneOf([modelObj({material:'unobtanium'})]))
      .indexOf('MATERIAL_NOT_IN_LIBRARY')>=0);
chk('E · an invalid provenance is rejected',
    codes(sceneOf([modelObj({material_provenance:'ENGINEERING_FACT'})]))
      .indexOf('MATERIAL_PROVENANCE_INVALID')>=0);
chk('E · an AI-suggested finish cannot become an authoritative property',
    V('villa',{materials:{wall:{material:'concrete',provenance:'AI_SUGGESTED'}}})
      .materials.every(m=>m.structural_material===false&&m.fire_rating===null));

console.log('\n== F — executable asset metadata is refused, never executed ==');
['script','code','eval','onload','src','url','href','exec'].forEach(k=>{
  const a={id:'x',type:'tree',asset_class:'VISUAL_ONLY',license:'CC0',
    dimensions_m:{w:1,d:1,h:1},source:'s'};
  a[k]='alert(1)';
  chk('F · asset metadata field "'+k+'" is refused',
      visValidateAsset(a).some(i=>i.indexOf('ASSET_METADATA_MUST_NOT_CARRY_CODE')===0));
});
chk('F · an unknown-license asset is refused',
    visValidateAsset({id:'x',type:'tree',asset_class:'VISUAL_ONLY',license:'UNKNOWN',
      dimensions_m:{w:1,d:1,h:1},source:'s'})
      .indexOf('ASSET_LICENSE_UNKNOWN_NOT_EMITTED')>=0);
chk('F · no shipped asset carries an unknown license or a remote source',
    visAssetLibrary().every(a=>a.license!=='UNKNOWN'&&!/^https?:/i.test(String(a.source))));
chk('F · a non-object asset is refused rather than coerced',
    visValidateAsset('alert(1)').indexOf('ASSET_NOT_AN_OBJECT')>=0);

console.log('\n== G — a theme leaves canonical geometry and hash unchanged ==');
chk('G · the compiled architecture is identical across every theme', (function(){
  const base=JSON.stringify(AR('villa'));
  return VIS_THEMES.every(t=>{ V('villa',{mode:'ARCHITECTURAL',theme:t});
    return JSON.stringify(AR('villa'))===base; }); })());
chk('G · the model hash is identical across every theme',
    new Set(VIS_THEMES.map(t=>V('villa',{theme:t}).model_hash)).size===1);
chk('G · modelled object geometry is identical across every theme', (function(){
  const g=t=>JSON.stringify(V('villa',{theme:t}).objects.filter(o=>!o.visual_only)
    .map(o=>[o.id,o.geometry,o.source_element_id]));
  return VIS_THEMES.every(t=>g(t)===g('Neutral')); })());
chk('G · a theme changes only material and provenance', (function(){
  const a=V('villa',{theme:'Neutral'}).objects.filter(o=>o.kind==='WALL')[0];
  const b=V('villa',{theme:'Luxury'}).objects.filter(o=>o.kind==='WALL')[0];
  return a.material!==b.material&&JSON.stringify(a.geometry)===JSON.stringify(b.geometry); })());

console.log('\n== H — the engineering view cannot hide a discipline ==');
['ARCHITECTURE','STRUCTURE','MEP','FLS'].forEach(l=>{
  const s=V('villa_full',{mode:'ENGINEERING'});
  const r=visSetLayerVisible(s,l,false);
  chk('H · hiding '+l+' in the engineering view is refused',
      r[0]===false&&r[1]==='ENGINEERING_VIEW_MUST_NOT_HIDE_A_DISCIPLINE');
  chk('H · '+l+' remains visible after the refused attempt',
      s.presentation.layer_visibility[l]===true);
});
chk('H · requesting a reduced layer set in the engineering view still shows all four',
    ['ARCHITECTURE','STRUCTURE','MEP','FLS'].every(l=>
      V('villa_full',{mode:'ENGINEERING',layers:['ARCHITECTURE']})
        .presentation.layers.indexOf(l)>=0));
chk('H · a presentation view may still hide a technical layer',
    visSetLayerVisible(V('villa_full',{mode:'PRESENTATION',
      layers:['ARCHITECTURE','MEP']}),'MEP',false)[0]===true);

console.log('\n== DECORATION SAFETY (regression) ==');
const deco=V('villa',{mode:'DOLLHOUSE',include_decoration:true});
chk('decoration is OFF by default',
    V('villa',{mode:'DOLLHOUSE'}).counts.decoration_objects===0);
chk('decoration is visual_only with no canonical source',
    deco.objects.filter(o=>o.visual_class===VIS_DECORATION_CLASS)
      .every(o=>o.visual_only===true&&o.semantic===false&&o.source_element_id===null));
chk('decoration is excluded from the engineering export',
    visExportScene(deco,false).objects.every(o=>o.visual_only===false));
chk('decoration reaches no occupancy, coverage, load or FLS input', (function(){
  const m=C(SC.models.villa);
  const a=compileArchitecture(m,'bld_0',null,0);
  const st=compileStructure(m,'bld_0',null,0,a);
  const p=compileMep(m,'bld_0',null,0,a,st);
  const f=compileFls(m,'bld_0',null,0,a,p);
  const before=JSON.stringify([a,st,p,f]);
  compileVisualScene(m,'bld_0',null,0,{mode:'DOLLHOUSE',include_decoration:true,at:AT});
  const a2=compileArchitecture(m,'bld_0',null,0);
  const st2=compileStructure(m,'bld_0',null,0,a2);
  const p2=compileMep(m,'bld_0',null,0,a2,st2);
  const f2=compileFls(m,'bld_0',null,0,a2,p2);
  return JSON.stringify([a2,st2,p2,f2])===before; })());
chk('decoration never appears in a rule input',
    Object.keys(visRuleInputs(deco).building).every(k=>k.indexOf('visual.')===0));

console.log('\n== SITE / SNAPSHOT / VR SAFETY (regression) ==');
chk('a model with no site states its ground plane is not a boundary', (function(){
  const g=V('no_site').objects.filter(o=>o.kind==='GROUND')[0];
  return g.visual_only===true&&g.site_dimensions_stated===false
    &&/not a stated site boundary/.test(g.note); })());
chk('no boundary, setback, road or parking is invented anywhere',
    Object.keys(SC.models).every(n=>V(n).objects.every(o=>
      ['PROPERTY_BOUNDARY','SETBACK','ROAD','PARKING','FENCE','GATE'].indexOf(o.kind)<0)));
chk('water appears only for a represented feature',
    V('villa_pool').objects.filter(o=>o.kind==='WATER').length===1
    &&Object.keys(SC.models).filter(n=>n!=='villa_pool')
      .every(n=>V(n).objects.filter(o=>o.kind==='WATER').length===0));
chk('the snapshot pixel ceiling still clamps',
    visSnapshotRequest(scene,{width:99999,height:99999}).issues
      .indexOf('SNAPSHOT_EXCEEDS_MAX_PIXELS')>=0);
chk('an unsupported snapshot format fails rather than silently switching', (function(){
  const r=visSnapshotRequest(scene,{format:'TIFF'});
  return r.issues.indexOf('SNAPSHOT_FORMAT_UNSUPPORTED')>=0; })());
chk('the render id stays deterministic and carries the model hash', (function(){
  const q=visSnapshotRequest(scene,{width:1920,height:1080});
  const a=visRenderMetadata(scene,q,'DETERMINISTIC_RENDER',AT,null);
  const b=visRenderMetadata(scene,q,'DETERMINISTIC_RENDER',AT,null);
  return a.render_id===b.render_id&&a.model_hash===scene.model_hash; })());
chk('VR remains 1:1 unless scaling is explicit',
    V('villa',{mode:'VR'}).presentation.scale===1
    &&V('villa',{mode:'VR',scale:0.02}).presentation.scale_is_explicit===true);
chk('a visualisation scale never mutates canonical dimensions', (function(){
  const base=JSON.stringify(AR('villa').spaces.map(s=>[s.id,s.rect]));
  V('villa',{mode:'VR',scale:0.02});
  return JSON.stringify(AR('villa').spaces.map(s=>[s.id,s.rect]))===base; })());

console.log('\n──────────────────────────────────────────────');
console.log('VISUAL ADVERSARIAL: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
