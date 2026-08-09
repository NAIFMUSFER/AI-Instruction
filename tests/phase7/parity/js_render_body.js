/* جانب جافاسكربت من تكافؤ المرحلة 7 — يعمل داخل شيفرة المتصفّح المستخرَجة من
   public/index.html، ويكرّر ما يفعله py_render.py حرفاً بحرف. */
const fs=require('fs'), path=require('path');
const HERE=__dirname, PHASE=path.resolve(HERE,'..'), ROOT=path.resolve(PHASE,'..','..');
const _tmp=(function(){ try{ return require('os').tmpdir(); }catch(e){ return '/tmp'; } })();
const OUT=(process.env&&process.env.ACS_PARITY_RENDER_JS)
  ||path.join(_tmp,'acs_parity_render_js.json');
const LIB=require(path.join(PHASE,'lib_render_fixtures.js'));
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';

const ALL=LIB.all();
const MODEL_KEYS=Object.keys(ALL).sort();
const CAMS=['FRONT_EXTERIOR','FRONT_CORNER','BIRDS_EYE','DOLLHOUSE','TOP',
  'STREET_VIEW','REAR_CORNER'];
const BUF_W=96, BUF_H=64;

const out={};
MODEL_KEYS.forEach(function(key){
  const model=C(ALL[key]);
  const before=JSON.stringify(model);
  const project=auCreateProject(C(model),'bld_0','IMPORT',null);
  const scene=compileVisualScene(C(model),'bld_0',null,0,{mode:'PRESENTATION'});
  const arch=compileArchitecture(C(model),'bld_0',null,0);

  const entry={model_hash:project.model_hash};
  const reqs={};
  RD_VIEW_TYPES.concat(['NOT_A_VIEW']).forEach(vt=>{
    reqs[vt]=rdRenderRequest(project,vt,{theme:'LUXURY',lighting:'GOLDEN_HOUR',
      quality:'HIGH'},'rreq_fixed'); });
  entry.requests=reqs;
  const cams={}; CAMS.forEach(c=>{ cams[c]=rdCameraFor(scene,c); }); entry.cameras=cams;
  const mats={}; RD_THEMES.forEach(t=>{ mats[t]=rdAssignMaterials(scene,t); });
  entry.materials=mats;
  const lig={}; RD_LIGHTING.forEach(p=>{ lig[p]=rdLighting(p); }); entry.lighting=lig;
  entry.lighting_oriented=rdLighting('DAY',30);
  const qual={}; RD_QUALITIES.forEach(q=>{ qual[q]=rdQualityProfile(q,false); });
  entry.quality=qual;
  entry.quality_constrained=rdQualityProfile('ULTRA',true);
  const env={}; RD_QUALITIES.forEach(q=>{ env[q]=rdEnvironment(q,false); });
  entry.environment=env;
  entry.transforms={
    ROOF_HIDE:rdVisualTransform(scene,'ROOF_HIDE'),
    WALL_CLIP:rdVisualTransform(scene,'WALL_CLIP',{height_m:1.4}),
    LEVEL_ISOLATION:rdVisualTransform(scene,'LEVEL_ISOLATION',{level_index:0}),
    CLIP_PLANE:rdVisualTransform(scene,'CLIP_PLANE',{axis:'x',offset_m:5}),
    LEVEL_EXPLODE:rdVisualTransform(scene,'LEVEL_EXPLODE',{gap_m:4}),
    BAD:rdVisualTransform(scene,'NOT_A_TRANSFORM')};
  const plans={}; [0,1].forEach(lv=>{ plans[String(lv)]=rdPlanDrawing(scene,arch,lv,'CLEAN'); });
  entry.plans=plans;
  const pst={}; ACS_RENDER_SPEC.plan_styles.forEach(st=>{
    pst[st]=rdPlanDrawing(scene,arch,0,st).drawing; }); entry.plan_styles=pst;
  const elv={}; ACS_RENDER_SPEC.elevation_faces.forEach(f=>{
    elv[f]=rdElevationDrawing(scene,f); }); entry.elevations=elv;
  const sec={}; ACS_RENDER_SPEC.section_axes.forEach(a=>{
    sec[a]=rdSectionDrawing(scene,a); }); entry.sections=sec;
  entry.plan_svg=rdPlanSvg(rdPlanDrawing(scene,arch,0,'CLEAN').drawing);
  entry.elevation_svg=rdElevationSvg(rdElevationDrawing(scene,'NORTH').drawing);
  entry.section_svg=rdSectionSvg(rdSectionDrawing(scene,'x').drawing);
  entry.separate=rdSeparateVisual(scene);

  const cam=rdCameraFor(scene,'FRONT_EXTERIOR').camera;
  const bufs=rdControlBuffers(scene,cam,BUF_W,BUF_H);
  entry.buffers=bufs;
  if(bufs.valid){
    entry.features=rdGeometryFeatures(bufs.buffers);
    const pl={}, ps={};
    RD_BUFFER_KINDS.forEach(k=>{
      const png=rdBufferPng(bufs.buffers,k)||[];
      pl[k]=png.length; ps[k]=_rdSha16(Array.prototype.slice.call(png)); });
    entry.png_len=pl; entry.png_sha=ps;
    entry.self_drift=rdDetectDrift(entry.features.features,entry.features.features); }

  const req=rdRenderRequest(project,'EXTERIOR',{theme:'MODERN'},'rreq_fixed');
  entry.descriptor=rdRenderDescriptor(req.request,cam,'DETERMINISTIC_RENDER',
    {created_at:AT});
  entry.staleness_current=rdStaleness(entry.descriptor,project);
  entry.variant=rdVariant(req.request,'Luxury',{floor:'r_marble_white'});
  entry.gallery=rdGallery([entry.descriptor],project);

  if(JSON.stringify(model)!==before)
    throw new Error('a render operation mutated the model: '+key);
  if(project.model_hash!==entry.model_hash)
    throw new Error('the project hash changed during rendering: '+key);
  out[key]=entry; });

/* ---- المواد والتجاوز */
const lookup={};
Object.keys(RD_MATERIALS).concat(['nope']).sort(_scmp).forEach(m=>{
  lookup[m]=rdMaterial(m); });
out.__materials__={library:rdMaterialLibrary(),lookup:lookup,
  override_ok:rdVisualOverride({},'SPACE','g.majlis','r_wood_oak'),
  override_spec:rdVisualOverride({},'SPACE','g.majlis','r_wood_oak',
    'PROJECT_SPECIFICATION'),
  override_bad_scope:rdVisualOverride({},'NOPE','x','r_wood_oak'),
  override_bad_mat:rdVisualOverride({},'SPACE','x','not_a_material'),
  override_markup:rdVisualOverride({},'SPACE','<script>x</script>','r_wood_oak')};

/* ---- الكاميرا الداخلية */
const _scene=compileVisualScene(C(ALL.villa_glazed),'bld_0',null,0,
  {mode:'PRESENTATION'});
out.__interior__={
  majlis:rdCameraFor(_scene,'INTERIOR_WIDE','bld_0.g.majlis'),
  eye:rdCameraFor(_scene,'INTERIOR_EYE_LEVEL','bld_0.g.majlis'),
  missing:rdCameraFor(_scene,'INTERIOR_WIDE','no.such.space'),
  bad_preset:rdCameraFor(_scene,'NOT_A_PRESET')};

/* ---- حدود الذكاء الاصطناعي */
const _proj=auCreateProject(C(ALL.villa_glazed),'bld_0','IMPORT',null);
const _req=rdRenderRequest(_proj,'EXTERIOR',{theme:'MODERN',ai_enhancement:true},
  'rreq_fixed').request;
const _cam=rdCameraFor(_scene,'FRONT_EXTERIOR').camera;
const _bufs=rdControlBuffers(_scene,_cam,BUF_W,BUF_H,null,_proj.model_hash).buffers;
const _desc=rdRenderDescriptor(_req,_cam,'DETERMINISTIC_RENDER',{created_at:AT});
const _contract=rdAiPromptContract(_req,{style:'warm',mood:'<script>x</script>'},
  [{reference_id:'ref_1',kind:'STYLE',scope:'PROJECT',
    uri:'https://example.invalid/a.png',caption:'ok'},
   {reference_id:'ref_bad',kind:'STYLE',scope:'PROJECT',
    uri:'javascript:alert(1)',caption:'x'}]);
out.__ai__={contract:_contract,
  request:rdAiRequest(_req,_desc,_bufs,_contract,'provider_x'),
  request_no_buffers:rdAiRequest(_req,_desc,null,_contract),
  request_no_base:rdAiRequest(_req,null,_bufs,_contract),
  adapter_off:rdProviderAdapter('provider_x',false),
  adapter_on:rdProviderAdapter('provider_x',true,30),
  enhance_unavailable:rdAiEnhance(rdProviderAdapter('provider_x',false),
    {base_render_id:_desc.render_id},null),
  enhance_ok:rdAiEnhance(rdProviderAdapter('provider_x',true),
    rdAiRequest(_req,_desc,_bufs,_contract,'provider_x').request,
    {provider_model:'model_y',generated_at:AT,image_ref:'img_1'})};

/* ---- كشف الانحراف */
const _ref=rdGeometryFeatures(_bufs).features;
const mut=(f,fn)=>{ const g=C(f); fn(g); return g; };
out.__drift__={
  identical:rdDetectDrift(_ref,C(_ref)),
  window_added:rdDetectDrift(_ref,mut(_ref,g=>{
    g.openings.push({cx:5,cy:5,w:4,h:4,px:16}); g.opening_count=g.opening_count+1; })),
  window_removed:rdDetectDrift(_ref,mut(_ref,g=>{
    g.openings.pop(); g.opening_count=g.opening_count-1; })),
  door_moved:rdDetectDrift(_ref,mut(_ref,g=>{ g.openings[0].cx=g.openings[0].cx+40; })),
  floor_drift:rdDetectDrift(_ref,mut(_ref,g=>{
    g.floor_band_count=g.floor_band_count+1; })),
  footprint_drift:rdDetectDrift(_ref,mut(_ref,g=>{
    g.footprint.area_px=Math.trunc(g.footprint.area_px*0.5); })),
  wall_drift:rdDetectDrift(_ref,mut(_ref,g=>{ g.wall_px=Math.trunc(g.wall_px*0.4); })),
  roof_drift:rdDetectDrift(_ref,mut(_ref,g=>{
    g.roof_line=g.roof_line.map(v=>v<0?-1:v+30); })),
  semantic_missing:rdDetectDrift(_ref,C(_ref),['bld_0.requested.car_1']),
  wrong_camera:rdDetectDrift(_ref,mut(_ref,g=>{ g.camera_id='cam_other'; })),
  wrong_model:rdDetectDrift(_ref,mut(_ref,g=>{ g.model_hash='other'; })),
  missing:rdDetectDrift(null,null)};

out.__alignment__={same:rdBuffersAligned(_bufs,_bufs),
  other_size:rdBuffersAligned(_bufs,rdControlBuffers(_scene,_cam,48,32).buffers),
  none:rdBuffersAligned(null,_bufs)};

const uns={};
['ok','javascript:alert(1)','<script>x</script>','<img onerror=x>',
 'data:text/html,x','vbscript:x','<!DOCTYPE x','eval(1)','',null,5]
  .forEach((v,i)=>{ uns[String(i)]=rdIsUnsafe(v); });
out.__unsafe__=uns;

out.__context__={
  default:rdRenderRequest(_proj,'EXTERIOR',{},'rreq_fixed').request.context_flags,
  industrial:rdRenderRequest(_proj,'EXTERIOR',
    {context_flags:['industrial_equipment']},'rreq_fixed').request.context_flags,
  bogus:rdRenderRequest(_proj,'EXTERIOR',{context_flags:['not_a_flag']},
    'rreq_fixed').request.context_flags};

out.__spec__={schema:RD_SCHEMA,version:ACS_RENDER_SPEC.version};

fs.writeFileSync(OUT,JSON.stringify(out),'utf8');
console.log('javascript render parity written: '+OUT+' ('+Object.keys(out).length+' keys)');
