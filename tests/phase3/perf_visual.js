/* قياس أداء بناء المشهد البصري — أرقام حقيقية من هذه الآلة.
   بناء المشهد لا رسم البكسل: البكسل يحتاج WebGL حقيقياً وهو خارج هذه البيئة. */
const fs=require('fs'), path=require('path');
const HERE=__dirname;
const FX=JSON.parse(fs.readFileSync(path.join(HERE,'fixtures','base_fixtures.json'),'utf8'));
function genProject(n){
  const cols=Math.ceil(Math.sqrt(n)), rooms=[];
  for(let i=0;i<n;i++){ const r=Math.floor(i/cols), c=i%cols;
    rooms.push({id:'sp_'+i,rect:[c*6,r*5,6,5],height:3,
      doors:[{edge:'N',offset:3,width:1,height:2.1}],
      windows:(i%3===0)?[{edge:'S',offset:3,width:1.4,height:1.4,sill:0.9}]:[]}); }
  return {meta:{type:'office',name:'big'},wall_h:3,wall_t:0.2,floor_height:3.2,
    site:{w:cols*6,d:Math.ceil(n/cols)*5},
    levels:[{index:0,template:'g'},{index:1,template:'g'}],
    floors:{g:{rooms:rooms}}};
}
const CASES=[['villa',FX.villa],['hotel',FX.hotel],['warehouse',FX.warehouse],
             ['project_1000',genProject(1000)]];
const rows=[];
CASES.forEach(cs=>{
  const name=cs[0], m=cs[1];
  const arch=compileArchitecture(JSON.parse(JSON.stringify(m)),'bld_0',null,0);
  compileVisualScene(JSON.parse(JSON.stringify(m)),'bld_0',null,0,{mode:'PRESENTATION'});
  const t0=Date.now();
  const s=compileVisualScene(JSON.parse(JSON.stringify(m)),'bld_0',null,0,
    {mode:'PRESENTATION',quality:'HIGH'});
  const t1=Date.now();
  const d0=Date.now();
  const dec=compileVisualScene(JSON.parse(JSON.stringify(m)),'bld_0',null,0,
    {mode:'DOLLHOUSE',include_decoration:true,quality:'HIGH'});
  const d1=Date.now();
  const p0=Date.now(); visFloorPlan(arch,0,'TECHNICAL','bld_0'); const p1=Date.now();
  const x0=Date.now(); visSection(arch,'x',null,'bld_0'); const x1=Date.now();
  const e0=Date.now(); visElevation(arch,'NORTH','bld_0'); const e1=Date.now();
  const i0=Date.now(); visInstancingPlan(dec); const i1=Date.now();
  const l0=Date.now(); visLodPlan(dec,null); const l1=Date.now();
  const s0=Date.now();
  const req=visSnapshotRequest(s,{width:3840,height:2160});
  visRenderMetadata(s,req,'DETERMINISTIC_RENDER',null,null);
  const s1=Date.now();
  const b0=Date.now(); visControlBuffers(s,null); const b1=Date.now();
  const inst=visInstancingPlan(dec);
  rows.push({model:name,spaces:arch.spaces.length,
    scene_objects:s.counts.objects,modelled:s.counts.semantic_objects,
    visual_only:s.counts.visual_only_objects,
    materials:s.counts.materials,lights:s.counts.lights,cameras:s.counts.cameras,
    draw_calls_estimate:s.counts.objects-inst.instanced_objects+inst.groups.length,
    instance_groups:inst.groups.length,instanced_objects:inst.instanced_objects,
    scene_build_ms:t1-t0,dollhouse_with_decor_ms:d1-d0,
    plan_ms:p1-p0,section_ms:x1-x0,elevation_ms:e1-e0,
    instancing_ms:i1-i0,lod_ms:l1-l0,snapshot_metadata_ms:s1-s0,
    control_buffers_ms:b1-b0,
    fps:'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED (no WebGL context)',
    texture_memory:'NOT MEASURABLE — materials are parametric, no textures are loaded',
    snapshot_pixels_ms:'NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED'});
});
console.log(JSON.stringify(rows,null,1));
console.log('VISUAL PERF ROWS:',rows.length);
