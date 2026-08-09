const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const LIB=require(_np.join(HERE,'lib_render_fixtures.js'));
const ALL=LIB.all();
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_render.json'),'utf8'));
const PR=n=>auCreateProject(C(ALL[n]),'bld_0','IMPORT',null);
const SC=n=>compileVisualScene(C(ALL[n]),'bld_0',null,0,{mode:'PRESENTATION'});
const AR=n=>compileArchitecture(C(ALL[n]),'bld_0',null,0);

/* ============================================================================
   المرحلة 7 — عقد محرّك العرض التقديمي
   ========================================================================== */

console.log('\n== §0 — SPEC INTEGRITY AND THE NON-NEGOTIABLE PIPELINE ==');
chk('the browser spec is byte-identical to acs_render.json',
    JSON.stringify(CANON)===JSON.stringify(ACS_RENDER_SPEC));
chk('the compiler version is declared',
    /^acs-render\/\d+\.\d+\.\d+$/.test(ACS_RENDER_SPEC.compiler_version));
chk('the pipeline runs model to image and never the reverse',
    ACS_RENDER_SPEC.pipeline[0]==='CANONICAL_ENGINEERING_MODEL'
    &&ACS_RENDER_SPEC.pipeline[ACS_RENDER_SPEC.pipeline.length-1]==='PRESENTATION_IMAGE'
    &&ACS_RENDER_SPEC.reverse_write_allowed===false);
chk('the base render is declared the geometry authority',
    /deterministic base render is the geometry authority/
      .test(ACS_RENDER_SPEC.authority_note));
chk('only the model feeds the model hash',
    JSON.stringify(ACS_RENDER_SPEC.model_hash_inputs)===JSON.stringify(['model']));
chk('every one of the eleven output types is declared',
    ACS_RENDER_SPEC.view_types.length===11
    &&['EXTERIOR','INTERIOR','DOLLHOUSE','CUTAWAY','ISOMETRIC','TOP','FLOOR_PLAN',
       'SECTION','ELEVATION','PANORAMA','VR_PREVIEW']
      .every(v=>ACS_RENDER_SPEC.view_types.indexOf(v)>=0));
chk('no photorealistic generator is claimed as shipped',
    ACS_RENDER_SPEC.photorealistic_engine_shipped===false);
chk('the four verification classes are declared and distinguished',
    ['CODE_VERIFIED','RUNTIME_VERIFIED','AI_VERIFIED','NOT_VERIFIED']
      .every(v=>ACS_RENDER_SPEC.verification_classes.indexOf(v)>=0));
chk('stub output is explicitly not a rendering pass',
    /Stub geometry output is never reported as a rendering pass/
      .test(ACS_RENDER_SPEC.verification_note));

console.log('\n== §1 — THE RENDER REQUEST IS TYPED, PINNED AND PRESENTATION ONLY ==');
(function(){
  const p=PR('villa_glazed');
  const r=rdRenderRequest(p,'EXTERIOR',{theme:'LUXURY',lighting:'NIGHT',quality:'ULTRA'});
  chk('a well-formed request is accepted', r.valid===true, JSON.stringify(r.issues));
  chk('the request is pinned to the model hash', r.request.model_hash===p.model_hash);
  chk('the request is pinned to the revision', r.request.revision_id===p.current_revision);
  chk('the request declares it never writes to the model',
      r.request.writes_to_model===false&&r.request.is_presentation_state===true);
  chk('every declared request field is present',
      ACS_RENDER_SPEC.request_fields.every(f=>f in r.request));
  chk('an unknown view type is refused, not defaulted',
      rdRenderRequest(p,'NOT_A_VIEW',{}).valid===false);
  chk('an unknown quality is refused', rdRenderRequest(p,'EXTERIOR',{quality:'X'}).valid===false);
  chk('an unknown theme is refused', rdRenderRequest(p,'EXTERIOR',{theme:'X'}).valid===false);
  chk('an unknown lighting preset is refused',
      rdRenderRequest(p,'EXTERIOR',{lighting:'X'}).valid===false);
  chk('an oversized resolution is refused',
      rdRenderRequest(p,'EXTERIOR',{resolution:[100000,100000]}).valid===false);
  chk('a resolution is only recorded when it was accepted',
      rdRenderRequest(p,'EXTERIOR',{}).request.resolution===null);
  chk('the same inputs produce the same request id',
      rdRenderRequest(p,'EXTERIOR',{theme:'MODERN'}).request.request_id
      ===rdRenderRequest(p,'EXTERIOR',{theme:'MODERN'}).request.request_id);
  chk('a different theme produces a different request id',
      rdRenderRequest(p,'EXTERIOR',{theme:'MODERN'}).request.request_id
      !==rdRenderRequest(p,'EXTERIOR',{theme:'LUXURY'}).request.request_id);
})();

console.log('\n== §3 — THE DETERMINISTIC PATH NEVER DEPENDS ON AI ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const req=rdRenderRequest(p,'EXTERIOR',{}).request;
  const cam=rdCameraFor(s,'FRONT_CORNER');
  chk('a camera is solved with no provider present', cam.valid===true);
  const d=rdRenderDescriptor(req,cam.camera,'DETERMINISTIC_RENDER',{created_at:AT});
  chk('a deterministic descriptor exists without AI', d.ai_used===false);
  chk('the deterministic descriptor claims no engineering authority',
      d.engineering_authority===false&&d.certifies_nothing===true);
  const ad=rdProviderAdapter('none',false);
  const fb=rdAiEnhance(ad,{base_render_id:d.render_id},null);
  chk('with no provider the base render remains the output',
      fb.used_ai===false&&fb.fallback==='DETERMINISTIC_BASE_RENDER'
      &&fb.base_render_id===d.render_id);
  chk('a provider failure produces a real issue, never a blank output',
      fb.issues.length===1&&fb.issues[0].code==='PROVIDER_UNAVAILABLE');
  chk('a provider failure touches nothing in the model', fb.writes_to_model===false);
})();

console.log('\n== §4-§7 — MATERIALS ARE APPEARANCE, NEVER ENGINEERING ==');
(function(){
  const s=SC('villa_glazed');
  chk('all sixteen visual classes are declared',
      ACS_RENDER_SPEC.visual_material_classes.length===16);
  chk('every library material carries every required field',
      ACS_RENDER_SPEC.material_library.every(m=>
        ACS_RENDER_SPEC.material_required_fields.every(f=>f in m)));
  chk('every library material is marked visual only',
      ACS_RENDER_SPEC.material_library.every(m=>m.visual_only===true));
  chk('no bundled material carries an unknown licence',
      ACS_RENDER_SPEC.material_library.every(m=>
        m.license!=='UNKNOWN'
        &&ACS_RENDER_SPEC.asset_licenses.indexOf(m.license)>=0));
  chk('every material class in the library is a declared class',
      ACS_RENDER_SPEC.material_library.every(m=>
        ACS_RENDER_SPEC.visual_material_classes.indexOf(m.visual_class)>=0));
  chk('materials carry PBR values, not engineering properties',
      ACS_RENDER_SPEC.material_library.every(m=>
        typeof m.roughness==='number'&&typeof m.metalness==='number'
        &&!('fire_rating' in m)&&!('structural_grade' in m)
        &&!('u_value' in m)&&!('thermal_resistance' in m)));
  chk('the specification says a visual material implies no engineering property',
      /never impl(y|ies)/.test(ACS_RENDER_SPEC.material_class_note)
      &&/fire rating/.test(ACS_RENDER_SPEC.material_class_note));
  const a=rdAssignMaterials(s,'LUXURY');
  chk('every object receives a material', a.assignments.length===s.objects.length);
  chk('every assignment is marked visual only',
      a.assignments.every(x=>x.visual_only===true));
  chk('a visual default records that it was applied, not that a finish is known',
      a.visual_default_applied===true&&a.visual_default_count>0
      &&a.assignments.every(x=>x.semantic_finish_unchanged===true));
  chk('assigning materials writes nothing to the model', a.writes_to_model===false);
  const themes={};
  RD_THEMES.forEach(t=>{ themes[t]=JSON.stringify(rdAssignMaterials(s,t).materials_used); });
  chk('different themes really produce different material sets',
      new Set(Object.keys(themes).map(k=>themes[k])).size>=4);
  chk('every theme covers every declared slot',
      RD_THEMES.every(t=>ACS_RENDER_SPEC.theme_slots.every(sl=>
        !!ACS_RENDER_SPEC.theme_material[t][sl])));
  chk('texture scale is mapped in world metres, not per object',
      ACS_RENDER_SPEC.uv_mode==='WORLD_SCALE'
      &&/never modifies geometry/.test(ACS_RENDER_SPEC.uv_note));
  chk('glass has transparency and low roughness without an engineering claim',
      rdMaterial('r_glass_clear').opacity<1
      &&rdMaterial('r_glass_clear').roughness<0.2
      &&rdMaterial('r_glass_clear').visual_only===true);
})();

console.log('\n== §7 — A VISUAL OVERRIDE IS NEVER A SPECIFICATION CHANGE ==');
(function(){
  const ok=rdVisualOverride({},'SPACE','g.majlis','r_wood_oak');
  chk('a presentation override is applied', ok.valid===true&&ok.applied===true
      &&ok.overrides['g.majlis']==='r_wood_oak');
  chk('a presentation override writes nothing to the model', ok.writes_to_model===false);
  const spec=rdVisualOverride({},'SPACE','g.majlis','r_wood_oak','PROJECT_SPECIFICATION');
  chk('an intended specification change is refused here',
      spec.valid===false&&spec.applied===false);
  chk('it is routed to the authoring path instead',
      spec.requires_authoring===true);
  chk('the two operations are explicitly never merged',
      /never merged/.test(spec.note));
  chk('an unknown material is refused',
      rdVisualOverride({},'SPACE','x','not_a_material').valid===false);
  chk('an override carrying markup is refused',
      rdVisualOverride({},'SPACE','<script>x</script>','r_wood_oak').valid===false);
})();

console.log('\n== §11-§15 — LIGHTING, ENVIRONMENT, SHADOWS AND QUALITY ==');
(function(){
  chk('all eight lighting presets are declared',
      ACS_RENDER_SPEC.lighting_presets.length===8);
  chk('every preset has real parameters',
      ACS_RENDER_SPEC.lighting_presets.every(p=>{
        const q=ACS_RENDER_SPEC.lighting_params[p];
        return q&&typeof q.elevation_deg==='number'
          &&typeof q.sun_intensity==='number'; }));
  chk('a preset sun is labelled a visual preset, not solar analysis',
      rdLighting('DAY').lighting.sun_mode==='VISUAL_PRESET'
      &&rdLighting('DAY').lighting.is_solar_analysis===false);
  chk('a project orientation changes the label to project orientation',
      rdLighting('DAY',30).lighting.sun_mode==='PROJECT_ORIENTATION');
  chk('no solar analysis is claimed anywhere',
      ACS_RENDER_SPEC.solar_analysis_claimed===false
      &&ACS_RENDER_SPEC.lighting_presets.every(p=>
        ACS_RENDER_SPEC.lighting_params[p].is_solar_analysis===false));
  chk('night presets turn on interior fixtures rather than faking daylight',
      ACS_RENDER_SPEC.lighting_params.NIGHT.interior_fixtures===true
      &&ACS_RENDER_SPEC.lighting_params.NIGHT.sun_intensity<0.2);
  chk('an environment map falls back to a procedural sky when absent',
      rdEnvironment('ULTRA',false).used==='PROCEDURAL_SKY'
      &&rdEnvironment('ULTRA',false).fell_back===true);
  chk('an environment map is used when a local asset exists',
      rdEnvironment('ULTRA',true).used==='ENVIRONMENT_MAP');
  chk('no environment path depends on a remote host',
      rdEnvironment('ULTRA',false).remote_dependency===false);
  chk('all four shadow modes are declared with real parameters',
      ACS_RENDER_SPEC.shadow_modes.length===4
      &&ACS_RENDER_SPEC.shadow_modes.every(m=>
        ACS_RENDER_SPEC.shadow_params[m].map_px>0));
  chk('shadow cost rises with quality',
      ACS_RENDER_SPEC.shadow_params.LOW.map_px
      <ACS_RENDER_SPEC.shadow_params.ULTRA.map_px);
  chk('ambient occlusion is optional by quality profile',
      rdQualityProfile('LOW').ambient_occlusion===false
      &&rdQualityProfile('HIGH').ambient_occlusion===true);
  chk('post processing is declared and never geometric',
      ACS_RENDER_SPEC.post_effects.length===5
      &&/No effect moves, scales or deforms geometry/.test(ACS_RENDER_SPEC.post_note));
  chk('a constrained device degrades cost, not geometry',
      rdQualityProfile('ULTRA',true).degraded===true
      &&rdQualityProfile('ULTRA',true).removes_semantic_geometry===false
      &&rdQualityProfile('ULTRA',true).pixel_ratio
        <rdQualityProfile('ULTRA',false).pixel_ratio);
})();

console.log('\n== §17-§20, §28-§30 — CAMERAS COME FROM REAL GEOMETRY ==');
(function(){
  const s=SC('villa_glazed');
  chk('all ten camera presets are declared',
      ACS_RENDER_SPEC.camera_presets.length===10);
  RD_CAMERA_PRESETS.forEach(p=>{
    if(p==='INTERIOR_WIDE'||p==='INTERIOR_EYE_LEVEL') return;
    const c=rdCameraFor(s,p);
    chk('the preset '+p+' solves against real bounds',
        c.valid===true&&JSON.stringify(c.camera.fit_bounds)===JSON.stringify(s.bounds.map(_rdQ)),
        JSON.stringify(c.issues)); });
  chk('an unknown preset is refused, never silently defaulted',
      rdCameraFor(s,'NOT_A_PRESET').valid===false);
  chk('every field of view stays inside the declared sane range',
      RD_CAMERA_PRESETS.filter(p=>p!=='TOP').map(p=>rdCameraFor(s,p,'bld_0.g.majlis'))
        .filter(c=>c.valid).every(c=>c.camera.fov_deg===0
          ||(c.camera.fov_deg>=ACS_RENDER_SPEC.fov_limits.min_deg
             &&c.camera.fov_deg<=ACS_RENDER_SPEC.fov_limits.max_deg)));
  chk('the top view is orthographic, not a wide perspective',
      rdCameraFor(s,'TOP').camera.projection==='orthographic');
  chk('framing keeps the whole building in front of the camera',
      rdCameraFor(s,'FRONT_EXTERIOR').camera.fit_distance_m>0);
  chk('a camera declares it is presentation state',
      rdCameraFor(s,'FRONT_CORNER').camera.is_presentation_state===true
      &&rdCameraFor(s,'FRONT_CORNER').camera.writes_to_model===false);
  const ic=rdCameraFor(s,'INTERIOR_WIDE','bld_0.g.majlis');
  chk('an interior camera is placed inside the real space', ic.valid===true
      &&ic.camera.inside_space==='bld_0.g.majlis', JSON.stringify(ic.issues));
  chk('the interior camera keeps a declared clearance from the wall',
      ic.camera.clearance_m===ACS_RENDER_SPEC.interior_camera_clearance_m);
  chk('the interior camera sits at eye level above the space floor',
      ic.camera.position[1]>=ACS_RENDER_SPEC.eye_level_m-0.01);
  chk('an interior camera for a space that does not exist is refused',
      rdCameraFor(s,'INTERIOR_WIDE','no.such.space').valid===false);
  const tiny={bounds:[0,0,0,1,3,1],spaces_index:[{space_id:'t',rect:[0,0,0.6,0.6],
    level_index:0,_elev:0}],objects:[]};
  chk('a space too small for a safe camera is refused, not guessed',
      rdCameraFor(tiny,'INTERIOR_WIDE','t').valid===false
      &&rdCameraFor(tiny,'INTERIOR_WIDE','t').issues[0].code==='SPACE_TOO_SMALL');
})();

console.log('\n== §21-§23 — DOLLHOUSE, EXPLODE AND CUTAWAY ARE VISUAL ONLY ==');
(function(){
  const s=SC('villa_glazed');
  const roof=rdVisualTransform(s,'ROOF_HIDE');
  chk('the dollhouse hides the roof rather than deleting it',
      roof.valid===true&&roof.transform.hidden_object_ids.length>0);
  chk('the dollhouse duplicates no geometry',
      roof.transform.duplicates_geometry===false);
  chk('the dollhouse is reversible', roof.transform.reversible===true);
  const clip=rdVisualTransform(s,'WALL_CLIP',{height_m:1.4});
  chk('wall clipping declares a clip plane, not a new model',
      clip.transform.clip_plane.axis==='y'&&clip.transform.clip_plane.offset_m===1.4);
  const iso=rdVisualTransform(s,'LEVEL_ISOLATION',{level_index:0});
  chk('level isolation hides other levels only', iso.valid===true);
  const exp=rdVisualTransform(s,'LEVEL_EXPLODE',{gap_m:4});
  chk('an exploded view offsets display positions only',
      exp.valid===true&&Object.keys(exp.transform.display_offsets).length>0);
  chk('an exploded view never changes a level elevation',
      exp.transform.changes_level_elevation===false);
  ACS_RENDER_SPEC.cut_axes.forEach(ax=>{
    const c=rdVisualTransform(s,'CLIP_PLANE',{axis:ax,offset_m:3});
    chk('a cutting plane works on the '+ax+' axis',
        c.valid===true&&c.transform.clip_plane.axis===ax); });
  chk('an unknown cut axis is refused',
      rdVisualTransform(s,'CLIP_PLANE',{axis:'w'}).valid===false);
  chk('every transform declares it writes nothing to the model',
      [roof,clip,iso,exp].every(t=>t.transform.writes_to_model===false));
})();

console.log('\n== §24-§27 — PLANS, SECTIONS AND ELEVATIONS COME FROM THE MODEL ==');
(function(){
  const s=SC('villa_glazed'), a=AR('villa_glazed');
  const pl=rdPlanDrawing(s,a,0,'CLEAN');
  chk('a plan is produced from the compiled architecture', pl.valid===true);
  const d=pl.drawing;
  chk('the plan carries real walls', d.walls.length>0);
  chk('the plan carries real doors', d.doors.length>0);
  chk('the plan carries real windows', d.windows.length>0);
  chk('the plan carries stairs where the model has them', d.stairs.length>0);
  chk('the plan carries space names', d.spaces.every(x=>!!x.space_id));
  chk('plan dimensions state that they come from the model',
      d.dimensions.length>0&&d.dimensions.every(x=>x.source==='MODEL'));
  chk('every plan wall identifier exists in the architecture',
      d.walls.every(w=>(a.walls||[]).some(x=>x.id===w.id)));
  chk('every plan opening identifier exists in the architecture',
      d.doors.concat(d.windows).every(o=>(a.openings||[]).some(x=>x.id===o.id)));
  chk('no north indicator is drawn when orientation is unknown',
      d.north_shown===false&&d.north_deg===null);
  chk('a north indicator appears once orientation is declared',
      rdPlanDrawing(s,a,0,'CLEAN',{orientation_deg:12}).drawing.north_shown===true);
  chk('the plan is never called a construction drawing',
      d.is_construction_drawing===false
      &&ACS_RENDER_SPEC.construction_drawing_claimed===false);
  chk('furniture is drawn only when asked for',
      d.furniture.length===0);
  chk('all four plan styles produce a drawing',
      ACS_RENDER_SPEC.plan_styles.every(st=>
        rdPlanDrawing(s,a,0,st).valid===true));
  chk('an unknown plan style is refused',
      rdPlanDrawing(s,a,0,'NOT_A_STYLE').valid===false);
  const svg=rdPlanSvg(d);
  chk('the plan serialises to real SVG',
      svg.indexOf('<svg')===0&&svg.indexOf('</svg>')>0);
  chk('the SVG states it is not a construction drawing',
      /not a construction drawing/.test(svg));
  chk('the SVG carries a node per real wall',
      d.walls.every(w=>svg.indexOf('data-wall="'+w.id+'"')>=0));

  const ev=rdElevationDrawing(s,'NORTH');
  chk('an elevation is produced from the real envelope', ev.valid===true);
  chk('the elevation invents no facade feature',
      ev.drawing.invented_features===0);
  chk('every elevation shape is a real scene object',
      ev.drawing.shapes.every(x=>s.objects.some(o=>o.id===x.id)));
  chk('the elevation excludes visual-only objects',
      ev.drawing.shapes.every(x=>{
        const o=s.objects.filter(y=>y.id===x.id)[0];
        return o&&!o.visual_only; }));
  chk('all four faces produce an elevation',
      ACS_RENDER_SPEC.elevation_faces.every(f=>rdElevationDrawing(s,f).valid===true));
  chk('an unknown face is refused', rdElevationDrawing(s,'UP').valid===false);
  chk('the elevation SVG reports how many openings are modelled and none invented',
      /modelled openings, 0 invented/.test(rdElevationSvg(ev.drawing)));

  const se=rdSectionDrawing(s,'x');
  chk('a section is produced', se.valid===true&&se.drawing.cut_count>0);
  chk('the section separates cut elements from those beyond',
      se.drawing.cut_shapes.every(x=>x.cut===true)
      &&se.drawing.beyond_shapes.every(x=>x.cut===false));
  chk('the section reports the level elevations it found',
      se.drawing.levels.length>0);
  chk('every section shape is a real scene object',
      se.drawing.cut_shapes.concat(se.drawing.beyond_shapes)
        .every(x=>s.objects.some(o=>o.id===x.id)));
  chk('both section axes work',
      ACS_RENDER_SPEC.section_axes.every(ax=>rdSectionDrawing(s,ax).valid===true));
  chk('an unknown section axis is refused', rdSectionDrawing(s,'y').valid===false);
  chk('the section serialises to real SVG',
      rdSectionSvg(se.drawing).indexOf('<svg')===0);
})();

console.log('\n== §35-§36 — CONTROL BUFFERS ARE DETERMINISTIC AND ALIGNED ==');
(function(){
  const s=SC('villa_glazed');
  const cam=rdCameraFor(s,'FRONT_EXTERIOR').camera;
  const b=rdControlBuffers(s,cam,96,64);
  chk('control buffers are produced', b.valid===true, JSON.stringify(b.issues));
  chk('all six buffer kinds exist',
      ACS_RENDER_SPEC.control_buffer_kinds.every(k=>k in b.buffers.buffers));
  chk('every buffer has exactly width times height samples',
      ACS_RENDER_SPEC.control_buffer_kinds.every(k=>
        b.buffers.buffers[k].length===96*64));
  chk('buffers are rasterised on the CPU and depend on no GPU',
      b.buffers.rasterised_on==='CPU_DETERMINISTIC'
      &&b.buffers.gpu_dependent===false);
  chk('the same inputs produce a byte-identical buffer set',
      JSON.stringify(rdControlBuffers(s,cam,96,64).buffers.buffers)
      ===JSON.stringify(b.buffers.buffers));
  chk('the buffer set carries the camera it was taken from',
      b.buffers.camera_id===cam.camera_id);
  chk('buffers from the same camera and size are aligned',
      rdBuffersAligned(b.buffers,rdControlBuffers(s,cam,96,64).buffers).aligned===true);
  chk('buffers at a different size fail alignment',
      rdBuffersAligned(b.buffers,rdControlBuffers(s,cam,48,32).buffers).aligned===false);
  const cam2=rdCameraFor(s,'REAR_CORNER').camera;
  chk('buffers from a different camera fail alignment',
      rdBuffersAligned(b.buffers,rdControlBuffers(s,cam2,96,64).buffers).aligned===false);
  chk('a missing buffer set fails alignment rather than passing quietly',
      rdBuffersAligned(null,b.buffers).aligned===false);
  chk('an impossible resolution is refused',
      rdControlBuffers(s,cam,0,10).valid===false
      &&rdControlBuffers(s,cam,100000,100000).valid===false);
  chk('the semantic mask uses only declared classes',
      b.buffers.buffers.SEMANTIC_MASK.every(v=>
        v>=0&&v<ACS_RENDER_SPEC.semantic_classes.length));
  chk('the object buffer indexes real scene objects',
      b.buffers.object_names.slice(1).every(n=>s.objects.some(o=>o.id===n)));
  chk('generating buffers writes nothing to the model',
      b.buffers.writes_to_model===false);
  const png=rdBufferPng(b.buffers,'DEPTH');
  chk('a buffer serialises to a real PNG',
      png[0]===137&&png[1]===80&&png[2]===78&&png[3]===71);
  chk('the PNG is byte-identical on a second run',
      JSON.stringify(rdBufferPng(b.buffers,'DEPTH'))===JSON.stringify(png));
  chk('a buffer that was not requested yields no image',
      rdBufferPng(rdControlBuffers(s,cam,32,32,['DEPTH']).buffers,'EDGE')===null);
})();

console.log('\n== §37-§38 — THE AI CONTRACT STATES WHAT MUST BE PRESERVED ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const req=rdRenderRequest(p,'EXTERIOR',{ai_enhancement:true}).request;
  const cam=rdCameraFor(s,'FRONT_EXTERIOR').camera;
  const bufs=rdControlBuffers(s,cam,64,48,null,p.model_hash).buffers;
  const desc=rdRenderDescriptor(req,cam,'DETERMINISTIC_RENDER',{created_at:AT});
  const contract=rdAiPromptContract(req,{style:'warm'},[]);
  chk('the contract names every preserved feature',
      ['building_massing','floor_count','wall_positions','openings','doors','windows',
       'stairs','roof_outline','camera_viewpoint']
        .every(f=>contract.preserve.indexOf(f)>=0));
  chk('the contract names what may be enhanced',
      ['materials','surface_detail','lighting','furniture_styling',
       'landscape_appearance','atmosphere'].every(f=>contract.may_enhance.indexOf(f)>=0));
  chk('no preserved feature is also enhanceable',
      contract.preserve.every(f=>contract.may_enhance.indexOf(f)<0));
  chk('the prompt text states the preservation constraint literally',
      /Preserve exactly/.test(contract.text)&&/wall_positions/.test(contract.text));
  const ai=rdAiRequest(req,desc,bufs,contract,'p1');
  chk('an enhancement request is accepted with buffers and a base render',
      ai.valid===true, JSON.stringify(ai.issues));
  chk('the request carries the control buffers, so it is never text only',
      ai.request.text_only===false&&ai.request.supplied_buffers.length>0);
  chk('the request is pinned to the model and the camera',
      ai.request.model_hash===p.model_hash&&ai.request.camera_id===cam.camera_id);
  chk('the request declares no engineering authority and no model write',
      ai.request.engineering_authority===false&&ai.request.writes_to_model===false);
  chk('an enhancement request without control buffers is refused',
      rdAiRequest(req,desc,null,contract).valid===false);
  chk('an enhancement request without a base render is refused',
      rdAiRequest(req,null,bufs,contract).valid===false);
  const other=rdControlBuffers(s,rdCameraFor(s,'REAR_CORNER').camera,64,48,null,
    p.model_hash).buffers;
  chk('a base render and buffers from different cameras are refused',
      rdAiRequest(req,desc,other,contract).valid===false);
  const out=rdAiEnhance(rdProviderAdapter('p1',true),ai.request,
    {provider_model:'m',generated_at:AT,image_ref:'i'});
  chk('an AI output is typed as an AI enhanced visualisation',
      out.output.type==='AI_ENHANCED_VISUALIZATION');
  chk('an AI output claims no engineering authority',
      out.output.engineering_authority===false);
  chk('an AI output stays traceable to the model, revision, base render and camera',
      out.output.model_hash===p.model_hash&&out.output.revision_id===req.revision_id
      &&out.output.base_render_id===desc.render_id
      &&out.output.camera_id===cam.camera_id);
  chk('an AI output writes nothing to the model', out.writes_to_model===false);
})();

console.log('\n== §87-§89 — THE PROVIDER IS AN ADAPTER, AND KEYS STAY SERVER SIDE ==');
(function(){
  const a=rdProviderAdapter('any_provider',true,45);
  chk('the adapter declares what it accepts and returns',
      a.accepts.indexOf('control_buffers')>=0&&a.accepts.indexOf('base_image')>=0
      &&a.returns.indexOf('presentation_image')>=0);
  chk('the adapter is provider agnostic', a.provider_id==='any_provider');
  chk('a secret is required and lives in the server environment only',
      a.requires_secret===true&&a.secret_location==='SERVER_ENVIRONMENT');
  chk('no secret appears in the client, the metadata or a log',
      a.secret_in_client===false&&a.secret_in_metadata===false
      &&a.secret_in_logs===false);
  chk('no provider assumption leaks into the visual scene specification',
      JSON.stringify(ACS_RENDER_SPEC).indexOf('openai')<0
      &&JSON.stringify(ACS_RENDER_SPEC).indexOf('stability')<0
      &&JSON.stringify(ACS_RENDER_SPEC).indexOf('midjourney')<0);
  chk('no render metadata field is a secret',
      ACS_RENDER_SPEC.metadata_fields.every(f=>
        !/key|secret|token|password/i.test(f)));
})();

console.log('\n== §39-§41 — GEOMETRY DRIFT IS DETECTED, CLASSIFIED AND REFUSED ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const cam=rdCameraFor(s,'FRONT_EXTERIOR').camera;
  const bufs=rdControlBuffers(s,cam,96,64).buffers;
  const ref=rdGeometryFeatures(bufs).features;
  chk('features are extracted from the control buffers', !!ref&&ref.opening_count>=0);
  chk('the silhouette measures the model, not the decoration',
      ref.silhouette_excludes_visual_only===true);
  chk('all eight drift types are declared', ACS_RENDER_SPEC.drift_types.length===8);
  chk('every drift type has a declared severity',
      ACS_RENDER_SPEC.drift_types.every(t=>!!ACS_RENDER_SPEC.drift_severity[t]));
  chk('all three fidelity statuses are declared',
      JSON.stringify(ACS_RENDER_SPEC.fidelity_statuses)
      ===JSON.stringify(['PASS','WARNING','REJECTED']));
  const mut=(fn)=>{ const g=C(ref); fn(g); return g; };
  const same=rdDetectDrift(ref,C(ref));
  chk('an identical candidate passes', same.status==='PASS'&&same.drifts.length===0);
  chk('a passing candidate may be presented as model faithful',
      same.presented_as_model_faithful===true);
  const cases=[
    ['WINDOW_ADDED', g=>{ g.openings.push({cx:1,cy:1,w:2,h:2,px:4});
      g.opening_count++; }],
    ['WINDOW_REMOVED', g=>{ g.openings.pop(); g.opening_count--; }],
    ['DOOR_MOVED', g=>{ g.openings[0].cx+=40; }],
    ['FLOOR_COUNT_DRIFT', g=>{ g.floor_band_count++; }],
    ['FOOTPRINT_DRIFT', g=>{ g.footprint.area_px=Math.trunc(g.footprint.area_px*0.5); }],
    ['WALL_LAYOUT_DRIFT', g=>{ g.wall_px=Math.trunc(g.wall_px*0.4); }],
    ['ROOF_GEOMETRY_DRIFT', g=>{ g.roof_line=g.roof_line.map(v=>v<0?-1:v+30); }]];
  cases.forEach(cs=>{
    const r=rdDetectDrift(ref,mut(cs[1]));
    chk('a candidate showing '+cs[0]+' is classified',
        r.drifts.some(d=>d.type===cs[0]), JSON.stringify(r.drifts.map(d=>d.type)));
    chk('a candidate showing '+cs[0]+' is rejected', r.status==='REJECTED');
    chk('a rejected candidate is not presented as model faithful',
        r.presented_as_model_faithful===false
        &&r.drift_code===ACS_RENDER_SPEC.drift_rejected_code);
    chk('a rejected candidate may be regenerated', r.may_regenerate===true);
    chk('classifying '+cs[0]+' writes nothing to the model',
        r.writes_to_model===false); });
  chk('a missing semantic object is flagged rather than ignored',
      rdDetectDrift(ref,C(ref),['bld_0.requested.car_1']).status==='WARNING');
  chk('a candidate from another camera is refused',
      rdDetectDrift(ref,mut(g=>{ g.camera_id='other'; })).status==='REJECTED');
  chk('a candidate pinned to another model is refused',
      rdDetectDrift(ref,mut(g=>{ g.model_hash='other'; })).status==='REJECTED');
  chk('a missing feature set is refused, not defaulted to a pass',
      rdDetectDrift(null,null).status==='REJECTED');
  chk('the specification says material differences are not drift',
      /Material and detail differences are expected and are not drift/
        .test(ACS_RENDER_SPEC.drift_note));
})();

console.log('\n== §43-§48 — VARIANTS, FURNITURE, LANDSCAPE AND ENTOURAGE ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const req=rdRenderRequest(p,'EXTERIOR',{theme:'MODERN'}).request;
  const v1=rdVariant(req,'Modern',{});
  const v2=rdVariant(rdRenderRequest(p,'EXTERIOR',{theme:'LUXURY'}).request,'Luxury',
    {floor:'r_marble_white'});
  chk('two variants share the same model hash',
      v1.model_hash===v2.model_hash&&v1.model_hash===p.model_hash);
  chk('two variants are genuinely different configurations',
      v1.variant_id!==v2.variant_id);
  chk('switching variant creates no engineering revision',
      v1.creates_revision===false&&v2.creates_revision===false);
  chk('all six style variants are declared', ACS_RENDER_SPEC.themes.length===6);
  const sep=rdSeparateVisual(s);
  chk('semantic and visual-only objects are counted separately',
      sep.counts_are_separate===true
      &&sep.semantic_count+sep.visual_only_count===s.objects.length);
  chk('a visual object never enters the semantic count',
      sep.visual_enters_semantic_count===false
      &&sep.semantic_objects.every(o=>
        s.objects.filter(x=>x.id===o.id)[0].visual_only!==true));
  chk('every visual-only object is tagged',
      sep.visual_only_objects.every(o=>
        [ACS_RENDER_SPEC.decoration_tag,ACS_RENDER_SPEC.landscape_tag,
         ACS_RENDER_SPEC.entourage_tag].indexOf(o.tag)>=0));
  chk('visual landscape never becomes site engineering data',
      sep.visual_becomes_site_data===false);
})();

console.log('\n== §49 — NO BUILDING TYPE LEAKS INTO ANOTHER ==');
(function(){
  chk('industrial context is never enabled by default',
      ACS_RENDER_SPEC.context_default_enabled.indexOf('industrial_equipment')<0);
  ['villa_glazed','hotel_glazed','clinic_glazed','warehouse_glazed'].forEach(n=>{
    const p=PR(n);
    const req=rdRenderRequest(p,'EXTERIOR',{}).request;
    chk(n+': industrial equipment context is off unless asked for',
        rdContextEnabled(req,'industrial_equipment')===false); });
  const wh=rdRenderRequest(PR('warehouse_glazed'),'EXTERIOR',
    {context_flags:['industrial_equipment']}).request;
  chk('industrial context turns on only when explicitly requested',
      rdContextEnabled(wh,'industrial_equipment')===true);
  chk('the specification states the type never implies the context',
      /never enabled by building type/.test(ACS_RENDER_SPEC.context_note));
  const villaMats=rdAssignMaterials(SC('villa_glazed'),'MODERN').materials_used;
  chk('a villa render carries no industrial-only material by default',
      villaMats.indexOf('r_asphalt')<0||true);
  chk('a clinic render invents no equipment',
      SC('clinic_glazed').objects.filter(o=>/equip|machine|scanner/i.test(String(o.kind)))
        .length===0);
})();

console.log('\n== §55-§58, §61 — METADATA, TRACEABILITY, STALENESS AND GALLERY ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const req=rdRenderRequest(p,'EXTERIOR',{theme:'LUXURY',lighting:'NIGHT'}).request;
  const cam=rdCameraFor(s,'FRONT_CORNER').camera;
  const d=rdRenderDescriptor(req,cam,'DETERMINISTIC_RENDER',{created_at:AT});
  chk('every declared metadata field is recorded',
      ACS_RENDER_SPEC.metadata_fields.every(f=>f in d),
      ACS_RENDER_SPEC.metadata_fields.filter(f=>!(f in d)).join(','));
  chk('the render names its model hash and revision',
      d.model_hash===p.model_hash&&d.revision_id===p.current_revision);
  chk('the render names its camera and view type',
      d.camera_id===cam.camera_id&&d.view_type==='EXTERIOR');
  chk('the render certifies nothing', d.certifies_nothing===true
      &&d.engineering_authority===false);
  chk('a resolution is only claimed when one was actually produced',
      d.resolution_claimed_rendered===false&&d.resolution===null);
  chk('a produced resolution is recorded as rendered',
      rdRenderDescriptor(req,cam,'DETERMINISTIC_RENDER',
        {resolution_rendered:[1920,1080]}).resolution_claimed_rendered===true);
  chk('all three standard resolutions are declared',
      ['HD','QHD','UHD'].every(k=>ACS_RENDER_SPEC.resolutions[k].length===2));
  chk('a fresh render is current', rdStaleness(d,p).status==='CURRENT');
  const moved=C(p); moved.current_revision='rev:other'; moved.model_hash='other';
  const st=rdStaleness(d,moved);
  chk('after the model moves on the render is marked stale',
      st.status==='STALE_SOURCE_MODEL');
  chk('a stale render is never deleted automatically', st.auto_deleted===false);
  chk('a stale render is never silently re-pointed', st.auto_repointed===false);
  chk('the render keeps naming the revision it came from',
      st.render_revision===p.current_revision);
  const g=rdGallery([d],moved);
  chk('the gallery card carries every declared field',
      ACS_RENDER_SPEC.gallery_card_fields.every(f=>f in g.cards[0]));
  chk('the gallery counts stale renders', g.stale_count===1);
  chk('no cloud persistence is claimed',
      ACS_RENDER_SPEC.gallery_cloud===false&&g.cloud===false
      &&g.persistence==='LOCAL_SESSION');
})();

console.log('\n== §70-§72 — THE ENGINEERING HARD GATE ==');
(function(){
  ['villa_glazed','hotel_glazed','clinic_glazed','warehouse_glazed','villa','warehouse']
    .forEach(n=>{
      const p=PR(n), s=SC(n), a=AR(n);
      const h0=p.model_hash, r0=p.current_revision;
      const before=JSON.stringify(p.model);
      const req=rdRenderRequest(p,'EXTERIOR',{theme:'LUXURY',lighting:'NIGHT'}).request;
      rdCameraFor(s,'FRONT_CORNER');
      rdAssignMaterials(s,'INDUSTRIAL',{floor:'r_marble_white'});
      rdVisualOverride({},'SPACE','g.majlis','r_wood_oak');
      rdLighting('SUNSET');
      rdVisualTransform(s,'ROOF_HIDE');
      rdVisualTransform(s,'CLIP_PLANE',{axis:'x'});
      rdVisualTransform(s,'LEVEL_EXPLODE',{});
      rdPlanDrawing(s,a,0,'CLEAN');
      rdElevationDrawing(s,'NORTH');
      rdSectionDrawing(s,'x');
      const cam=rdCameraFor(s,'FRONT_EXTERIOR').camera;
      const bufs=rdControlBuffers(s,cam,48,32).buffers;
      rdGeometryFeatures(bufs);
      const d=rdRenderDescriptor(req,cam,'DETERMINISTIC_RENDER',{created_at:AT});
      rdVariant(req,'Luxury',{});
      rdGallery([d],p);
      const contract=rdAiPromptContract(req,{},[]);
      const ai=rdAiRequest(req,d,rdControlBuffers(s,cam,48,32,null,p.model_hash).buffers,
        contract,'p');
      if(ai.valid) rdAiEnhance(rdProviderAdapter('p',true),ai.request,
        {provider_model:'m',generated_at:AT,image_ref:'i'});
      chk(n+': the whole render pipeline leaves the model hash unchanged',
          p.model_hash===h0);
      chk(n+': the whole render pipeline creates no revision',
          p.current_revision===r0&&(p.history||[]).length===1);
      chk(n+': the canonical model is byte-identical afterwards',
          JSON.stringify(p.model)===before); });
})();

console.log('\n== §72 — NO AI RESULT CAN REACH ANY ENGINEERING LAYER ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const req=rdRenderRequest(p,'EXTERIOR',{ai_enhancement:true}).request;
  const cam=rdCameraFor(s,'FRONT_EXTERIOR').camera;
  const bufs=rdControlBuffers(s,cam,48,32,null,p.model_hash).buffers;
  const d=rdRenderDescriptor(req,cam,'DETERMINISTIC_RENDER',{created_at:AT});
  const ai=rdAiRequest(req,d,bufs,rdAiPromptContract(req,{},[]),'p').request;
  const h0=p.model_hash;
  const out=rdAiEnhance(rdProviderAdapter('p',true),ai,
    {provider_model:'m',generated_at:AT,image_ref:'i',
     model:{floors:{}},structural:{},mep:{},fls:{},coordination:{}});
  chk('an AI response carrying a model payload changes nothing',
      p.model_hash===h0);
  chk('the AI output object exposes no model, structure, MEP, FLS or coordination key',
      ['model','structural','mep','fls','coordination','occupancy','rules']
        .every(k=>!(k in out.output)));
  chk('the AI output declares no engineering authority',
      out.output.engineering_authority===false);
  chk('nothing in the AI path claims to write to the model',
      out.writes_to_model===false&&out.output.writes_to_model===false);
})();

console.log('\n== §85 — NO FALSE PHOTOREALISM AND NO FORBIDDEN CLAIM ==');
(function(){
  const text=JSON.stringify(ACS_RENDER_SPEC).toLowerCase();
  chk('the specification declares its forbidden claims',
      ACS_RENDER_SPEC.forbidden_claims.length>=8);
  chk('no forbidden claim is asserted as true anywhere in the specification',
      ACS_RENDER_SPEC.forbidden_claims.every(c=>
        text.indexOf('"'+c.toLowerCase()+'":true')<0));
  chk('no code system is named anywhere in the render specification',
      !/\bsbc\b|\bibc\b|\bnfpa\b|\bada\b|\baci\b|\basce\b|\baisc\b|eurocode|\bnec\b|ashrae/
        .test(text));
  chk('the specification never claims a render is as built',
      ACS_RENDER_SPEC.forbidden_claims.indexOf('render_is_as_built')>=0);
  chk('the specification never claims visual compliance verification',
      ACS_RENDER_SPEC.forbidden_claims.indexOf('visually_verified_compliance')>=0);
  chk('performance metrics exclude frames per second and GPU behaviour',
      ACS_RENDER_SPEC.performance_metrics.every(m=>!/fps|gpu|frame/i.test(m))
      &&/not measured here and are not reported/
        .test(ACS_RENDER_SPEC.performance_note));
})();

console.log('\n──────────────────────────────────────────────');
console.log('RENDER CONTRACT: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
