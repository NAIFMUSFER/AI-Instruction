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
out.spec_view={schema:ACS_PBR_SPEC.schema,
  chain:ACS_PBR_SPEC.quality_fallback_chain,
  auto_max:ACS_PBR_SPEC.auto_max_profile,
  provenance:ACS_PBR_SPEC.provenance_classes,
  tone:ACS_PBR_SPEC.tone_mapping,limits:ACS_PBR_SPEC.limits};
fs.writeFileSync(OUT,JSON.stringify(out),'utf8');
console.log('parity written: '+Object.keys(out).length+' groups');
