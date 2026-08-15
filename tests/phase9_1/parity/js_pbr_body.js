/* جانب جافاسكربت من تكافؤ المرحلة 9.1 — يكرّر py_pbr.py حرفاً بحرف. */
const fs=require('fs'), path=require('path');
const _tmp=(function(){ try{ return require('os').tmpdir(); }catch(e){ return '/tmp'; } })();
const OUT=(process.env&&process.env.ACS_PARITY_PBR_JS)
  ||path.join(_tmp,'acs_parity_pbr_js.json');
const CAPS=[
  {webgl2:true,max_texture_size:16384,device_pixel_ratio:2},
  {webgl2:true,max_texture_size:8192,device_pixel_ratio:3},
  {webgl2:true,max_texture_size:4096,device_pixel_ratio:1.5},
  {webgl2:false,max_texture_size:2048,device_pixel_ratio:1},
  {},null];
const BOUNDS=[
  {cx:7,cy:3,cz:6.5,radius:12,min_y:0},
  {cx:20,cy:15,cz:12,radius:60,min_y:0},
  {cx:0,cy:0,cz:0,radius:0},{},null];
const out={};
out.materials={};
Object.keys(PQ_MATERIALS).sort(_scmp).forEach(m=>{ out.materials[m]=pqMaterial(m); });
out.material_bad=[pqMaterial('nope'),
  pqMaterial('plaster',JSON.parse('{"__proto__":1}')),
  pqMaterial('plaster',{roughness:99}),
  pqMaterial('plaster',{base_color:'red'}),
  pqMaterial('plaster',{roughness:0.31,base_color:'#A1B2C3'}),
  pqMaterial('glass_clear',{transmission:0.9})];
out.map={};
Object.keys(PQ_MAT_MAP).concat(['robot','skin','nope']).sort(_scmp)
  .forEach(n=>{ out.map[n]=pqMaterialForEngineering(n); });
out.lighting={};
Object.keys(PQ_LIGHTING).sort(_scmp).forEach(k=>{ out.lighting[k]=pqLighting(k); });
out.lighting_bad=pqLighting('DISCO');
out.exposure=[0.1,0.5,1.0,1.8,9.0,-1,null,'x'].map(v=>pqExposureClamp(v));
out.shadows=[];
['LOW','MEDIUM','HIGH','ULTRA','NOPE'].forEach(t=>{
  BOUNDS.forEach(b=>{ out.shadows.push(pqShadowConfig(t,b)); }); });
out.quality=[];
['PERFORMANCE','BALANCED','HIGH','ULTRA','NOPE'].forEach(pr=>{
  CAPS.forEach(c=>{ out.quality.push(pqQuality(pr,c)); }); });
out.auto=CAPS.map(c=>pqAutoProfile(c));
out.cameras=[];
Object.keys(PQ_CAMERAS).sort(_scmp).forEach(pr=>{
  BOUNDS.forEach(b=>{ out.cameras.push(pqCamera(pr,b)); }); });
out.cameras.push(pqCamera('NOPE',BOUNDS[0]));
out.environments=['NEUTRAL','SKY','STUDIO','HDRI_URL'].map(m=>pqEnvironment(m));
out.textures=['https://cdn.evil/x.png','//evil/x.png','../x.png',
  'assets/materials/../../.env','/etc/passwd','assets/materials/brick.png',
  'assets/materials/x.svg','assets/materials/'+new Array(201).join('a')+'.png',
  'javascript:alert(1)','','assets/other/x.png']
  .map(x=>[x,pqTexturePathOk(x)]);
out.configs=[
  pqConfig('HIGH','GOLDEN_HOUR','REALISTIC','SKY',1.2,
    {plaster:{roughness:0.5},glass_clear:{transmission:0.9}},CAPS[0],BOUNDS[0]),
  pqConfig('ULTRA','INTERIOR_NIGHT','ENGINEERING',null,null,null,CAPS[3],BOUNDS[1]),
  pqConfig('BALANCED','WAREHOUSE','REALISTIC','NEUTRAL',0.9,
    {nope:{roughness:1}},null,null),
  pqConfig('NOPE',null,null,null,null,null,null,null),
  pqConfig(null,null,'CARTOON',null,null,null,null,null)];
out.captures=[[1280,720],[1920,1080],[2560,1440],[99999,10],[0,0],[null,null]]
  .map(wh=>pqCaptureMetadata(
    out.configs[0].valid?out.configs[0].config:null,'hash_abc',wh[0],wh[1],null));
const SKY={name:'SKY_DOME',is_mesh:true,parent_names:[],
  box:{min:[-22500,-22500,-22500],max:[22500,22500,22500]}};
const UNNAMED_SKY={name:'',is_mesh:true,parent_names:[],box:SKY.box};
const WALL={name:'WALL|F0|r1|s0',is_mesh:true,parent_names:['BUILDING'],
  box:{min:[0,0,0],max:[12,3,9]}};
const TAGGED={name:'FLOOR|F0|r1|plate',is_mesh:true,parent_names:[],
  box:{min:[-2,-0.1,-2],max:[14,0.1,11]}};
const CTX={name:'AD_CONTEXT_PLANE0',is_mesh:true,
  parent_names:['AD_CONTEXT'],user_data:{visual_only:true},
  box:{min:[-200,-1,-200],max:[200,-0.9,200]}};
const DBG={name:'COORD_DEBUG_MARKER',is_mesh:true,parent_names:[],
  user_data:{acs_debug_only:true},box:{min:[0,0,0],max:[1,1,1]}};
const NOTMESH={name:'PLAYER',is_mesh:false,parent_names:[]};
const OBJS=[SKY,UNNAMED_SKY,WALL,TAGGED,CTX,DBG,NOTMESH];
out.bounds_member=OBJS.map(pqBoundsMember)
  .concat([pqBoundsMember({}),pqBoundsMember(null)]);
out.bounds_sets=[OBJS,[WALL],[SKY,CTX],[],null,
  [Object.assign({},WALL,{box:{min:['a',0,0],max:[1,1,1]}})]]
  .map(pqBoundsFromDescriptors);
out.camera_clip=[];
[{cx:6,cy:1.5,cz:4.5,radius:7.5},{cx:0,cy:0,cz:0,radius:0},{},null]
  .forEach(b=>{ [[0,20000,54000],[6,20,30],[6,1.5,4.5],null].forEach(pos=>{
    out.camera_clip.push(pqCameraClip(b,pos)); }); });
out.frustum=[];
[{position:[0,20000,54000],target:[6,1.5,4.5],fov:45,aspect:1.6,near:0.05,
  far:6000},
 {position:[30,20,30],target:[6,1.5,4.5],fov:45,aspect:1.6,near:0.1,far:500},
 {position:[6,1.5,4.5],target:[60,1.5,4.5],fov:60,aspect:1.6,near:0.05,
  far:500},{},null].forEach(c=>{
  [{cx:6,cy:1.5,cz:4.5,radius:7.5},{},null].forEach(b=>{
    out.frustum.push(pqFrustumContains(c,b)); }); });
out.material_safe=Object.keys(PQ_MATERIALS).sort(_scmp)
  .map(m=>pqMaterialSafe(pqMaterial(m).material))
  .concat([{id:'a',base_color:'#ffffff',opacity:0.0},
    {id:'b',base_color:'red'},{id:'c',base_color:'#ffffff',metalness:9},
    {id:'d',base_color:'#ffffff',roughness:null},{},null]
    .map(pqMaterialSafe));
const ROOMS_A=[[2,2,8,6],[12,2,6,6]];
const SITE_A=[0,0,40,30];
const ROOM_A=[10.0,6.0,20.0,12.0];
out.level_base_y=[];
[0,1,2,5,-1].forEach(i=>{ [3.2,0,null,NaN].forEach(fh=>{
  out.level_base_y.push(pqLevelBaseY(i,fh)); }); });
out.plate_rect=[];
[ROOMS_A,[],[[0,0,0,0]],null].forEach(r=>{ [SITE_A,null].forEach(s2=>{
  out.plate_rect.push(pqPlateRect(r,s2)); }); });
out.rack_block=[];
[ROOM_A,null].forEach(rr=>{
  [{x:5,z:0},{x:0,z:4},{x:15,w:99},{x:25},{},null].forEach(rk=>{
    out.rack_block.push(pqRackBlock(rr,rk)); }); });
out.containment=[];
[{min:[12,0,8],max:[14,2,10]},{min:[29,0,17],max:[33,2,20]},
 {min:[40,0,8],max:[42,2,10]},null].forEach(c=>{
  [{min:[10,0,6],max:[30,3,18]},null].forEach(h=>{
    [null,0.5].forEach(t=>{ out.containment.push(pqContainment(c,h,t)); }); }); });
out.roof_alignment=[];
[0,1,2,5].forEach(t=>{ [3.2,6.4,9.6,12.8,null].forEach(y=>{
  out.roof_alignment.push(pqRoofAlignment(t,3.2,y)); }); });
out.resolve_transform=[
  {coordinate_space:'HOST_LOCAL',local:[1,0,2],host_origin:[10,0,6],
   level_index:2,floor_height:3.2,host_id:'r1',level_id:'F2',
   source_element_id:'FURN|F2|r1|0'},
  {coordinate_space:'HOST_LOCAL',local:[1,0,2],host_origin:[10,6.4,6],
   host_origin_includes_level:true,level_index:2,floor_height:3.2},
  {coordinate_space:'SITE',local:[1,0,2]},
  {coordinate_space:'HOST_LOCAL',local:[1,0,1]},
  {coordinate_space:'NOWHERE',local:[1,0,1]},
  {coordinate_space:'SITE'},
  {coordinate_space:'SITE',local:[1,Infinity,1]},
  {},null].map(pqResolveTransform);

/* ── تكافؤ عقد استرداد العرض (render-recovery/1.0.0) ─────────────────────── */
const RR_BOXES=[
  {min:[0,0,0],max:[1,3,6]},
  {min:[0,0,0],max:[400,18,300]},
  {min:[99999.0,0,0],max:[99999.2,0.2,0.2]},
  {min:[0,0,0],max:[99999.0,1,1]},
  {min:[5,5,5],max:[1,1,1]},
  {min:[0,0,0],max:[0,0,0]},
  null];
out.element_valid=RR_BOXES.map(b=>pqElementValid(b?{box:b}:{}))
  .concat([pqElementValid(null)]);
const RR_SETS=[
  [{is_mesh:true,parent_names:['BUILDING'],name:'WALL|F0|a',
    box:{min:[0,0,0],max:[10,3,8]}}],
  [{is_mesh:true,parent_names:['BUILDING'],name:'WALL|F0|a',
    box:{min:[0,0,0],max:[10,3,8]}},
   {is_mesh:true,parent_names:['BUILDING'],name:'ELEC|F0|p',
    box:{min:[99999,0,0],max:[99999.2,0.2,0.2]}}],
  (function(){const a=[];for(let i=0;i<8;i++)a.push({is_mesh:true,
     parent_names:['BUILDING'],name:'WALL|F0|a',box:{min:[0,0,0],max:[1,1,1]}});
   a.push({is_mesh:true,parent_names:['BUILDING'],name:'WALL|F0|big',
     box:{min:[0,0,0],max:[400,10,10]}}); return a;})(),
  [{is_mesh:true,name:'SKY_DOME',parent_names:[],
    box:{min:[-45000,-45000,-45000],max:[45000,45000,45000]}}],
  []];
out.robust_bounds=RR_SETS.map(pqRobustBounds);
out.fit_distance=[];
[0.5,20,84,1902,46000,null].forEach(r=>{ [40,52,75].forEach(f=>{
  [0.6,1.6,3.2].forEach(a=>{ out.fit_distance.push(pqFitDistance(r,f,a)); }); }); });
out.camera_fit=[];
[15,84,500,1902,20000].forEach(r=>{ [42,52].forEach(f=>{ [0.6,1.6].forEach(a=>{
  out.camera_fit.push(pqCameraFit({cx:0,cy:0,cz:0,radius:r},f,a)); }); }); });
out.camera_fit.push(pqCameraFit({radius:0},52,1.6));
out.camera_fit.push(pqCameraFit(null,52,1.6));
out.recovery_plan=[
  {canonical_meshes:1500,draw_calls:212,viewport_black:true,
   composer_active:true,materials_replaced:true},
  {canonical_meshes:1500,draw_calls:212,viewport_black:true,
   composer_active:false,materials_replaced:false},
  {canonical_meshes:0,draw_calls:0,viewport_black:true},
  {canonical_meshes:10,draw_calls:0,viewport_black:true},
  {canonical_meshes:10,draw_calls:5,viewport_black:false},
  {},null].map(pqRecoveryPlan);

out.spec_view={schema:ACS_PBR_SPEC.schema,
  chain:ACS_PBR_SPEC.quality_fallback_chain,
  auto_max:ACS_PBR_SPEC.auto_max_profile,
  provenance:ACS_PBR_SPEC.provenance_classes,
  tone:ACS_PBR_SPEC.tone_mapping,limits:ACS_PBR_SPEC.limits};
fs.writeFileSync(OUT,JSON.stringify(out),'utf8');
console.log('parity written: '+Object.keys(out).length+' groups');
