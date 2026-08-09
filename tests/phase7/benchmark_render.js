/* المرحلة 7 §66 — قياس أداء خطّ العرض (جافاسكربت).
   أرقام حقيقية من هذه الآلة. لا ادّعاء إطارات في الثانية ولا أداء بطاقة
   رسوميات ولا زمن تصريف مظلّلات — لا شيء منه مقيس هنا. */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const LIB=require(_np.join(HERE,'lib_render_fixtures.js'));
const ALL=LIB.all();
const C=o=>JSON.parse(JSON.stringify(o));
const SPEC=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_render.json'),'utf8'));
const t=(fn,reps)=>{ const n=reps||1; const t0=Date.now();
  for(let i=0;i<n;i++) fn(i); return Date.now()-t0; };

const rows=[];
['villa_glazed','hotel_glazed','warehouse_glazed','clinic_glazed'].forEach(function(key){
  const model=C(ALL[key]);
  const project=auCreateProject(C(model),'bld_0','IMPORT',null);
  const h0=project.model_hash;
  const scene_ms=t(()=>compileVisualScene(C(model),'bld_0',null,0,{mode:'PRESENTATION'}));
  const scene=compileVisualScene(C(model),'bld_0',null,0,{mode:'PRESENTATION'});
  const arch=compileArchitecture(C(model),'bld_0',null,0);
  rdAssignMaterials(scene,'MODERN');                              /* إحماء */
  const mat_ms=t(()=>rdAssignMaterials(scene,'LUXURY'),10);
  const cam_ms=t(()=>rdCameraFor(scene,'FRONT_CORNER'),10);
  const cam=rdCameraFor(scene,'FRONT_CORNER').camera;
  const buf96=t(()=>rdControlBuffers(scene,cam,96,64));
  const buf320=t(()=>rdControlBuffers(scene,cam,320,200));
  const bufs=rdControlBuffers(scene,cam,320,200).buffers;
  const feat_ms=t(()=>rdGeometryFeatures(bufs));
  const png_ms=t(()=>rdBufferPng(bufs,'DEPTH'));
  const plan_ms=t(()=>rdPlanDrawing(scene,arch,0,'CLEAN'),10);
  const plan=rdPlanDrawing(scene,arch,0,'CLEAN').drawing;
  const svg_ms=t(()=>rdPlanSvg(plan),10);
  const elev_ms=t(()=>rdElevationDrawing(scene,'NORTH'),10);
  const sect_ms=t(()=>rdSectionDrawing(scene,'x'),10);
  const req=rdRenderRequest(project,'EXTERIOR',{ai_enhancement:true}).request;
  const desc=rdRenderDescriptor(req,cam,'DETERMINISTIC_RENDER',{});
  const ab=rdControlBuffers(scene,cam,96,64,null,h0).buffers;
  const ai_ms=t(()=>rdAiRequest(req,desc,ab,rdAiPromptContract(req,{},[]),'p'),10);
  rows.push({case:key,objects:(scene.objects||[]).length,
    scene_build_ms:scene_ms,
    material_assignment_ms_per_10:mat_ms,
    camera_solve_ms_per_10:cam_ms,
    control_buffer_96x64_ms:buf96,
    control_buffer_320x200_ms:buf320,
    feature_extract_ms:feat_ms,
    buffer_png_ms:png_ms,
    plan_build_ms_per_10:plan_ms,
    plan_svg_ms_per_10:svg_ms,
    elevation_ms_per_10:elev_ms,
    section_ms_per_10:sect_ms,
    ai_request_prepare_ms_per_10:ai_ms,
    model_hash_unchanged:project.model_hash===h0});
});

console.log(JSON.stringify(rows,null,1));
console.log('RENDER BENCHMARK ROWS: '+rows.length);
console.log('declared measurable metrics: '+JSON.stringify(SPEC.performance_metrics));
console.log(SPEC.performance_note);
console.log('measured on this machine: scene build, material assignment, camera solve, '
  +'control-buffer rasterisation, feature extraction, image encoding, drawing build, '
  +'vector serialisation and AI request preparation. NOT MEASURED: frames per second, '
  +'GPU behaviour, shader compilation, pixel output — no such claim is made anywhere.');
const ok=rows.every(r=>r.model_hash_unchanged===true&&r.objects>0);
console.log('every benchmarked case left the model hash unchanged: '+ok);
if(!ok) process.exit(1);
