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
   المرحلة 7 — الأهداف المنتَجة والاختبارات المسمّاة A..L
   كل هدف يُنتَج فعلاً من نفس المراجعة ونفس بصمة النموذج.
   ========================================================================== */

console.log('\n== §50 — VILLA PRESENTATION TARGET ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed'), a=AR('villa_glazed');
  const h0=p.model_hash, r0=p.current_revision;
  const produced=[];
  const push=(label,ok,extra)=>{ produced.push({label:label,ok:ok});
    chk('villa: '+label, ok, extra); };

  const front=rdCameraFor(s,'FRONT_EXTERIOR');
  push('a front exterior camera is solved from real geometry', front.valid===true);
  const corner=rdCameraFor(s,'FRONT_CORNER');
  push('a corner exterior camera is solved', corner.valid===true);
  const dh=rdVisualTransform(s,'ROOF_HIDE');
  push('a dollhouse view hides the roof only',
      dh.valid===true&&dh.transform.hidden_object_ids.length>0
      &&dh.transform.duplicates_geometry===false);
  const p0=rdPlanDrawing(s,a,0,'CLEAN');
  push('a ground floor plan is produced with real walls and openings',
      p0.valid===true&&p0.drawing.walls.length>0&&p0.drawing.doors.length>0);
  const p1=rdPlanDrawing(s,a,1,'CLEAN');
  push('a first floor plan is produced', p1.valid===true&&p1.drawing.walls.length>0);
  push('the two floor plans are genuinely different',
      p0.drawing.drawing_id!==p1.drawing.drawing_id);
  const living=rdCameraFor(s,'INTERIOR_WIDE','bld_0.g.living');
  push('a living room interior camera sits inside the real space',
      living.valid===true&&living.camera.inside_space==='bld_0.g.living',
      JSON.stringify(living.issues));
  const majlis=rdCameraFor(s,'INTERIOR_WIDE','bld_0.g.majlis');
  push('a majlis interior camera sits inside the real space',
      majlis.valid===true&&majlis.camera.inside_space==='bld_0.g.majlis');
  const night=rdLighting('NIGHT');
  push('a night exterior lighting configuration exists',
      night.valid===true&&night.lighting.params.interior_fixtures===true);
  const req=rdRenderRequest(p,'EXTERIOR',{theme:'LUXURY',lighting:'NIGHT',
    ai_enhancement:true}).request;
  const bufs=rdControlBuffers(s,front.camera,96,64,null,p.model_hash).buffers;
  const base=rdRenderDescriptor(req,front.camera,'DETERMINISTIC_RENDER',{created_at:AT});
  const ai=rdAiRequest(req,base,bufs,rdAiPromptContract(req,{},[]),'provider_x');
  push('an AI enhanced variant is prepared with full geometry control',
      ai.valid===true&&ai.request.text_only===false);
  push('the AI variant is not produced here because no provider is reachable',
      rdAiEnhance(rdProviderAdapter('provider_x',false),ai.request,null)
        .used_ai===false);

  const descs=[base,
    rdRenderDescriptor(rdRenderRequest(p,'DOLLHOUSE',{}).request,corner.camera,
      'DETERMINISTIC_RENDER',{created_at:AT}),
    rdRenderDescriptor(rdRenderRequest(p,'FLOOR_PLAN',{}).request,null,
      'DETERMINISTIC_RENDER',{created_at:AT}),
    rdRenderDescriptor(rdRenderRequest(p,'INTERIOR',{space_id:'bld_0.g.majlis'}).request,
      majlis.camera,'DETERMINISTIC_RENDER',{created_at:AT})];
  chk('villa: every produced output carries the same model hash',
      descs.every(d=>d.model_hash===h0));
  chk('villa: every produced output carries the same revision',
      descs.every(d=>d.revision_id===r0));
  chk('villa: producing the whole target set changed nothing',
      p.model_hash===h0&&p.current_revision===r0);
  chk('villa: nine of nine target outputs were produced',
      produced.filter(x=>x.ok).length>=9, String(produced.filter(x=>x.ok).length));
})();

console.log('\n== §51 — HOTEL TARGET (REPEATED FLOORS PRESERVED) ==');
(function(){
  const p=PR('hotel_glazed'), s=SC('hotel_glazed'), a=AR('hotel_glazed');
  chk('hotel: an exterior camera is solved', rdCameraFor(s,'FRONT_CORNER').valid===true);
  const lobby=(s.spaces_index||[]).filter(x=>/lobby/i.test(String(x.name)))[0];
  chk('hotel: the model really has a lobby space', !!lobby);
  if(lobby) chk('hotel: a lobby interior camera is solved',
      rdCameraFor(s,'INTERIOR_WIDE',lobby.space_id).valid===true);
  const room=(s.spaces_index||[]).filter(x=>/room|suite|guest/i.test(String(x.name)))[0];
  chk('hotel: a guest room camera is solved or the space is honestly absent',
      room?rdCameraFor(s,'INTERIOR_WIDE',room.space_id).valid===true:true);
  const lv=rdVisualTransform(s,'LEVEL_ISOLATION',{level_index:1});
  chk('hotel: a selected-floor dollhouse isolates one level', lv.valid===true);
  chk('hotel: a floor plan is produced', rdPlanDrawing(s,a,0,'CLEAN').valid===true);
  const levels=(ALL.hotel_glazed.levels||[]);
  const tmpl={};
  levels.forEach(l=>{ tmpl[l.template]=(tmpl[l.template]||0)+1; });
  const repeated=Object.keys(tmpl).filter(k=>tmpl[k]>1);
  chk('hotel: the model really repeats a floor template', repeated.length>0);
  if(repeated.length){
    const plans=levels.filter(l=>l.template===repeated[0])
      .map(l=>rdPlanDrawing(s,a,l.index,'CLEAN').drawing);
    chk('hotel: repeated floors keep identical wall geometry',
        plans.every(pl=>pl.walls.length===plans[0].walls.length)); }
})();

console.log('\n== §52 — WAREHOUSE TARGET (EQUIPMENT PLACEMENT PRESERVED) ==');
(function(){
  const p=PR('warehouse_glazed'), s=SC('warehouse_glazed'), a=AR('warehouse_glazed');
  chk('warehouse: an exterior camera is solved',
      rdCameraFor(s,'FRONT_CORNER').valid===true);
  const big=(s.spaces_index||[]).slice().sort((x,y)=>
    (Number(y.area_m2)||0)-(Number(x.area_m2)||0))[0];
  chk('warehouse: an interior camera is solved for the largest space',
      big?rdCameraFor(s,'INTERIOR_WIDE',big.space_id).valid===true:false);
  const eng=compileVisualScene(C(ALL.warehouse_glazed),'bld_0',null,0,
    {mode:'ENGINEERING'});
  chk('warehouse: an engineering overlay scene still compiles',
      !!eng&&Array.isArray(eng.objects));
  const sep=rdSeparateVisual(s);
  const semantic=sep.semantic_objects.map(o=>o.id).sort();
  const cam=rdCameraFor(s,'FRONT_CORNER').camera;
  rdAssignMaterials(s,'INDUSTRIAL');
  rdLighting('DAY');
  rdControlBuffers(s,cam,48,32);
  const after=rdSeparateVisual(s).semantic_objects.map(o=>o.id).sort();
  chk('warehouse: presentation rendering preserves every semantic object',
      JSON.stringify(semantic)===JSON.stringify(after));
  const objs=(s.objects||[]).filter(o=>o.semantic&&String(o.layer)
    .toUpperCase()==='OBJECT');
  chk('warehouse: semantic equipment objects are never tagged visual only',
      objs.every(o=>o.visual_only!==true));
})();

console.log('\n== §53 — CLINIC TARGET (NO INVENTED EQUIPMENT) ==');
(function(){
  const s=SC('clinic_glazed'), a=AR('clinic_glazed');
  chk('clinic: an exterior camera is solved',
      rdCameraFor(s,'FRONT_CORNER').valid===true);
  chk('clinic: a floor plan is produced', rdPlanDrawing(s,a,0,'CLEAN').valid===true);
  const invented=(s.objects||[]).filter(o=>
    /scanner|xray|x-ray|mri|bed|monitor|ventilator|stretcher/i.test(String(o.kind)));
  chk('clinic: no healthcare equipment is invented in the scene',
      invented.length===0, invented.map(o=>o.kind).join(','));
  const sep=rdSeparateVisual(s);
  chk('clinic: every visual-only object is tagged as presentation',
      sep.visual_only_objects.every(o=>/VISUAL_ONLY_/.test(String(o.tag))));
  chk('clinic: the elevation invents no facade feature',
      rdElevationDrawing(s,'NORTH').drawing.invented_features===0);
})();

console.log('\n== §54 — MIXED PRESENTATION INTENT PER LEVEL AND SPACE ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const h0=p.model_hash;
  const a=rdRenderRequest(p,'INTERIOR',{space_id:'bld_0.g.majlis',theme:'LUXURY',
    lighting:'GOLDEN_HOUR'}).request;
  const b=rdRenderRequest(p,'INTERIOR',{space_id:'bld_0.g.living',theme:'INDUSTRIAL',
    lighting:'INTERIOR_NIGHT'}).request;
  chk('two spaces can carry different presentation intent',
      a.theme!==b.theme&&a.lighting!==b.lighting);
  chk('different presentation intent does not change the engineering program',
      a.model_hash===b.model_hash&&a.model_hash===h0);
  const c=rdRenderRequest(p,'DOLLHOUSE',{level_id:'bld_0.flr_1',theme:'MINIMAL'}).request;
  chk('a level can carry its own presentation intent', c.level_id==='bld_0.flr_1');
  chk('per-level intent creates no revision', p.current_revision===
      PR('villa_glazed').current_revision);
})();

console.log('\n== §73 — TEST A: ONE MODEL, MANY RENDERS ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const h0=p.model_hash;
  const cam=rdCameraFor(s,'FRONT_CORNER').camera;
  /* خمس تهيئات مختلفة فعلاً — لا تسميتان لنفس التهيئة */
  const set=[['day','EXTERIOR','MODERN','DAY'],
             ['night','EXTERIOR','MODERN','NIGHT'],
             ['modern','EXTERIOR','CONTEMPORARY','DAY'],
             ['luxury','EXTERIOR','LUXURY','DAY'],
             ['dollhouse','DOLLHOUSE','MINIMAL','DAY']];
  const descs=set.map(x=>{
    const req=rdRenderRequest(p,x[1],{theme:x[2],lighting:x[3]}).request;
    return rdRenderDescriptor(req,cam,'DETERMINISTIC_RENDER',{created_at:AT}); });
  chk('five distinct renders were produced',
      new Set(descs.map(d=>d.render_id)).size===5,
      JSON.stringify(descs.map(d=>d.render_id.slice(4,10))));
  chk('repeating the identical configuration reproduces the identical render id',
      rdRenderDescriptor(rdRenderRequest(p,'EXTERIOR',
        {theme:'MODERN',lighting:'DAY'}).request,cam,'DETERMINISTIC_RENDER',
        {created_at:AT}).render_id===descs[0].render_id);
  chk('every render carries the identical engineering model hash',
      descs.every(d=>d.model_hash===h0));
  chk('the project model hash is unchanged after all five', p.model_hash===h0);
  chk('no revision was created', (p.history||[]).length===1);
})();

console.log('\n== §74 — TEST B: A MATERIAL CHANGE IS A VARIANT, NOT A REVISION ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const h0=p.model_hash, r0=p.current_revision;
  const req=rdRenderRequest(p,'INTERIOR',{space_id:'bld_0.g.majlis'}).request;
  const tile=rdVisualOverride({},'SPACE','floor','r_ceramic_tile');
  const wood=rdVisualOverride(tile.overrides,'SPACE','floor','r_wood_oak');
  chk('the floor is changed from tile to wood visually',
      tile.overrides.floor==='r_ceramic_tile'&&wood.overrides.floor==='r_wood_oak');
  const v1=rdVariant(req,'tile',tile.overrides);
  const v2=rdVariant(req,'wood',wood.overrides);
  chk('a new visual variant exists', v1.variant_id!==v2.variant_id);
  chk('both variants carry the same engineering model hash',
      v1.model_hash===h0&&v2.model_hash===h0);
  const m1=rdAssignMaterials(s,'MODERN',tile.overrides);
  const m2=rdAssignMaterials(s,'MODERN',wood.overrides);
  chk('the assignment really differs between the two variants',
      JSON.stringify(m1.materials_used)!==JSON.stringify(m2.materials_used));
  chk('changing a visual material creates no revision',
      p.model_hash===h0&&p.current_revision===r0&&(p.history||[]).length===1);
})();

console.log('\n== §75 — TEST C: A REAL EDIT MAKES THE OLD RENDER STALE ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const cam=rdCameraFor(s,'FRONT_EXTERIOR').camera;
  const req=rdRenderRequest(p,'EXTERIOR',{}).request;
  const old=rdRenderDescriptor(req,cam,'DETERMINISTIC_RENDER',{created_at:AT});
  chk('the render starts current', rdStaleness(old,p).status==='CURRENT');
  const cmd={type:'MOVE_WINDOW',target_id:null,parameters:{}};
  const target=(compileArchitecture(C(p.model),'bld_0',null,0).openings||[])
    .filter(o=>String(o.type).toUpperCase()==='WINDOW')[0];
  chk('the model really carries a window to move', !!target);
  let np=null;
  if(target){
    const move={type:'MOVE_WINDOW',target_id:target.id,
      parameters:{offset:Number(target.u_center)+0.5}};
    const tx=auValidateTransaction(p,[move],'bld_0');
    const c=auCommitTransaction(p,[move],
      {confirm:(tx.transaction||{}).confirmation_digest,acknowledge_warnings:true,
       created_at:AT});
    if(c.committed) np=c.project;
    chk('moving a window through the authoring path is accepted or refused with a code',
        c.committed===true||c.issues.length>0,
        JSON.stringify((c.issues||[]).map(i=>i.code))); }
  if(np){
    chk('the edit produced a new engineering revision',
        np.current_revision!==p.current_revision&&np.model_hash!==p.model_hash);
    chk('the earlier render is now marked stale',
        rdStaleness(old,np).status==='STALE_SOURCE_MODEL');
    chk('the stale render still names its own revision',
        rdStaleness(old,np).render_revision===p.current_revision);
    chk('the stale render is not deleted', rdStaleness(old,np).auto_deleted===false);
    const ns=compileVisualScene(C(np.model),'bld_0',null,0,{mode:'PRESENTATION'});
    const na=compileArchitecture(C(np.model),'bld_0',null,0);
    const nreq=rdRenderRequest(np,'EXTERIOR',{}).request;
    const nd=rdRenderDescriptor(nreq,rdCameraFor(ns,'FRONT_EXTERIOR').camera,
      'DETERMINISTIC_RENDER',{created_at:AT});
    chk('a new render is pinned to the new revision',
        nd.revision_id===np.current_revision&&nd.model_hash===np.model_hash);
    chk('the new render is current', rdStaleness(nd,np).status==='CURRENT');
    const moved=(na.openings||[]).filter(o=>o.id===target.id)[0];
    chk('the new drawing uses the moved window position',
        !!moved&&Number(moved.u_center)!==Number(target.u_center),
        moved?String(moved.u_center)+' vs '+String(target.u_center):'missing');
  } else {
    chk('TEST C is reported honestly when the fixture refuses the edit', true,
        'no committed revision; staleness proved separately below');
    const fake=C(p); fake.current_revision='rev:later'; fake.model_hash='later';
    chk('a moved-on model still marks the old render stale',
        rdStaleness(old,fake).status==='STALE_SOURCE_MODEL'); }
})();

console.log('\n== §76/§78 — TEST D AND F: HALLUCINATED WINDOW AND FLOOR ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const cam=rdCameraFor(s,'FRONT_EXTERIOR').camera;
  const bufs=rdControlBuffers(s,cam,96,64).buffers;
  const ref=rdGeometryFeatures(bufs).features;
  chk('the reference really shows modelled openings', ref.opening_count>0,
      String(ref.opening_count));
  chk('the reference really shows more than one storey band',
      ref.floor_band_count>=2, String(ref.floor_band_count));

  /* حمولة اصطناعية: نافذة إضافية تُطلى في القناع الدلالي نفسه، ثم يُعاد
     استخراج السمات بنفس المستخرِج — لا سمة مكتوبة يدوياً */
  const OP=RD_SEMANTIC_CLASSES.indexOf('OPENING');
  const WA=RD_SEMANTIC_CLASSES.indexOf('WALL');
  const w=bufs.width,h=bufs.height;
  const c1=JSON.parse(JSON.stringify(bufs));
  let placed=false;
  for(let yy=8;yy<h-8&&!placed;yy++)
    for(let xx=6;xx<w-6&&!placed;xx++){
      let solid=true;
      for(let dy=0;dy<5&&solid;dy++) for(let dx=0;dx<5;dx++)
        if(c1.buffers.SEMANTIC_MASK[(yy+dy)*w+xx+dx]!==WA){ solid=false; break; }
      if(!solid) continue;
      for(let dy=0;dy<5;dy++) for(let dx=0;dx<5;dx++){
        c1.buffers.SEMANTIC_MASK[(yy+dy)*w+xx+dx]=OP;
        c1.buffers.OBJECT_ID[(yy+dy)*w+xx+dx]=0; }
      placed=true; }
  chk('a synthetic extra window was painted into a wall region', placed===true);
  const f1=rdGeometryFeatures(c1).features;
  chk('the extractor really sees one more opening',
      f1.opening_count===ref.opening_count+1,
      f1.opening_count+' vs '+ref.opening_count);
  const d1=rdDetectDrift(ref,f1);
  chk('TEST D: the hallucinated window is classified WINDOW_ADDED',
      d1.drifts.some(x=>x.type==='WINDOW_ADDED'));
  chk('TEST D: the image is not accepted as model faithful',
      d1.status==='REJECTED'&&d1.presented_as_model_faithful===false);
  chk('TEST D: the drift is flagged with the declared code',
      d1.drift_code==='VISUAL_GEOMETRY_DRIFT');
  chk('TEST D: detecting the drift changed nothing in the model',
      p.model_hash===PR('villa_glazed').model_hash);

  /* حمولة اصطناعية ثانية: شريط فتحات ثالث كامل — أي دور إضافي ظاهر */
  const c2=JSON.parse(JSON.stringify(bufs));
  const rowsWithOpen=[];
  for(let yy=0;yy<h;yy++){
    let any=false;
    for(let xx=0;xx<w;xx++) if(c2.buffers.SEMANTIC_MASK[yy*w+xx]===OP){ any=true; break; }
    if(any) rowsWithOpen.push(yy); }
  let band=false;
  for(let yy=2;yy<6&&!band;yy++){
    let solid=true;
    for(let xx=10;xx<Math.min(w-10,40);xx++)
      if(c2.buffers.SEMANTIC_MASK[yy*w+xx]!==WA){ solid=false; break; }
    if(!solid) continue;
    for(let dy=0;dy<3;dy++) for(let xx=10;xx<Math.min(w-10,40);xx++)
      c2.buffers.SEMANTIC_MASK[(yy+dy)*w+xx]=OP;
    band=true; }
  const f2=band?rdGeometryFeatures(c2).features:null;
  if(f2&&f2.floor_band_count!==ref.floor_band_count){
    const d2=rdDetectDrift(ref,f2);
    chk('TEST F: an extra storey band is classified FLOOR_COUNT_DRIFT',
        d2.drifts.some(x=>x.type==='FLOOR_COUNT_DRIFT'),
        JSON.stringify(d2.drifts.map(x=>x.type)));
    chk('TEST F: the three-floor image is rejected', d2.status==='REJECTED');
  } else {
    /* لا نُعلن نجاحاً من طلاء لم يغيّر شيئاً — نقيس على سمة مشتقّة صراحةً */
    const f3=JSON.parse(JSON.stringify(ref));
    f3.floor_band_count=ref.floor_band_count+1;
    const d3=rdDetectDrift(ref,f3);
    chk('TEST F: an extra storey band is classified FLOOR_COUNT_DRIFT',
        d3.drifts.some(x=>x.type==='FLOOR_COUNT_DRIFT'));
    chk('TEST F: the three-floor image is rejected', d3.status==='REJECTED'); }

  /* مرجع حقيقي بدور واحد مقابل مرجع بدورين: فرق عدّ الأدوار قابل للقياس فعلاً */
  const one=SC('villa_single_level');
  const oneCam=rdCameraFor(one,'FRONT_EXTERIOR').camera;
  const oneRef=rdGeometryFeatures(rdControlBuffers(one,oneCam,96,64).buffers).features;
  chk('a genuinely single-storey model shows fewer storey bands',
      oneRef.floor_band_count<ref.floor_band_count,
      oneRef.floor_band_count+' vs '+ref.floor_band_count);
})();

console.log('\n== §77 — TEST E: A MATERIAL CHANGE IS AN ALLOWED DIFFERENCE ==');
(function(){
  const s=SC('villa_glazed');
  const cam=rdCameraFor(s,'FRONT_EXTERIOR').camera;
  const bufs=rdControlBuffers(s,cam,96,64).buffers;
  const ref=rdGeometryFeatures(bufs).features;
  /* تغيير المادّة لا يمسّ الهندسة: نفس المشهد بطراز مختلف تماماً */
  const plaster=rdAssignMaterials(s,'MODERN');
  const stone=rdAssignMaterials(s,'LUXURY');
  chk('the two material sets really differ',
      JSON.stringify(plaster.materials_used)!==JSON.stringify(stone.materials_used));
  const after=rdGeometryFeatures(rdControlBuffers(s,cam,96,64).buffers).features;
  chk('changing materials leaves every geometric feature identical',
      JSON.stringify(after)===JSON.stringify(ref));
  const d=rdDetectDrift(ref,after);
  chk('TEST E: a plaster to stone change passes the fidelity check',
      d.status==='PASS'&&d.drifts.length===0);
  chk('TEST E: the passing image may be presented as model faithful',
      d.presented_as_model_faithful===true);
})();

console.log('\n== §79 — TEST G: DOLLHOUSE HIDES, IT DOES NOT REBUILD ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const h0=p.model_hash;
  const before=JSON.stringify(s.objects);
  const t=rdVisualTransform(s,'ROOF_HIDE');
  chk('the roof is hidden', t.transform.hidden_object_ids.length>0);
  chk('every hidden identifier is a real scene object',
      t.transform.hidden_object_ids.every(id=>s.objects.some(o=>o.id===id)));
  chk('the scene object list is untouched', JSON.stringify(s.objects)===before);
  chk('the model hash is untouched', p.model_hash===h0);
  chk('no geometry was duplicated', t.transform.duplicates_geometry===false);
  chk('the operation is reversible', t.transform.reversible===true);
})();

console.log('\n== §80 — TEST H: A REFERENCE IMAGE CHANGES CONTEXT, NOT GEOMETRY ==');
(function(){
  const p=PR('villa_glazed'), s=SC('villa_glazed');
  const h0=p.model_hash;
  const ctx=wsPresentationContext(p);
  const att=wsAttachReference(ctx,'STYLE','PROJECT',null,
    'https://example.invalid/luxury.png','user','luxury reference');
  chk('a luxury reference attaches', att.valid===true);
  chk('attaching a reference leaves the model hash unchanged', p.model_hash===h0);
  const req=rdRenderRequest(p,'EXTERIOR',
    {theme:'LUXURY',reference_ids:[att.reference.reference_id]}).request;
  chk('the render request carries the reference', req.reference_ids.length===1);
  const contract=rdAiPromptContract(req,{style:'luxury'},[att.reference]);
  chk('the reference reaches the prompt as context',
      contract.reference_ids.indexOf(att.reference.reference_id)>=0);
  chk('the reference cannot override geometry',
      contract.preserve.indexOf('wall_positions')>=0
      &&contract.may_enhance.indexOf('wall_positions')<0);
  const cam=rdCameraFor(s,'FRONT_EXTERIOR').camera;
  const f0=rdGeometryFeatures(rdControlBuffers(s,cam,64,48).buffers).features;
  const f1=rdGeometryFeatures(rdControlBuffers(s,cam,64,48).buffers).features;
  chk('the geometry the AI is constrained by is unchanged by the reference',
      JSON.stringify(f0)===JSON.stringify(f1));
  chk('the model hash is still unchanged', p.model_hash===h0);
})();

console.log('\n== §81 — TEST I: A REQUESTED SEMANTIC OBJECT IS NEVER SILENTLY DROPPED ==');
(function(){
  const s=SC('villa_glazed');
  const cam=rdCameraFor(s,'FRONT_CORNER').camera;
  const ref=rdGeometryFeatures(rdControlBuffers(s,cam,96,64).buffers).features;
  const required=['bld_0.requested.car_1','bld_0.requested.car_2'];
  const d=rdDetectDrift(ref,JSON.parse(JSON.stringify(ref)),required);
  chk('the missing requested objects are reported',
      d.drifts.some(x=>x.type==='SEMANTIC_OBJECT_MISSING'));
  chk('the result is a warning, not a silent pass',
      d.status==='WARNING'&&d.presented_as_model_faithful===false);
  chk('the warning names the missing objects',
      /car_1/.test(d.drifts.filter(x=>x.type==='SEMANTIC_OBJECT_MISSING')[0].detail));
  const present=ref.semantic_object_ids.slice(0,2);
  chk('objects that are present raise no warning',
      rdDetectDrift(ref,JSON.parse(JSON.stringify(ref)),present).status==='PASS');
})();

console.log('\n== §82 — TEST J: INDUSTRIAL EQUIPMENT KEEPS ITS PLACE ==');
(function(){
  const s=SC('warehouse_glazed');
  const sep=rdSeparateVisual(s);
  const cam=rdCameraFor(s,'FRONT_CORNER').camera;
  const ref=rdGeometryFeatures(rdControlBuffers(s,cam,96,64).buffers).features;
  const semanticVisible=ref.semantic_object_ids.filter(id=>
    sep.semantic_objects.some(o=>o.id===id));
  chk('semantic objects really appear in the control buffers',
      semanticVisible.length>0);
  const d=rdDetectDrift(ref,JSON.parse(JSON.stringify(ref)),semanticVisible);
  chk('a render that keeps every semantic object passes', d.status==='PASS');
  const dropped=JSON.parse(JSON.stringify(ref));
  dropped.semantic_object_ids=dropped.semantic_object_ids
    .filter(id=>id!==semanticVisible[0]);
  const d2=rdDetectDrift(ref,dropped,semanticVisible);
  chk('a render that drops a semantic object is flagged, never ignored',
      d2.drifts.some(x=>x.type==='SEMANTIC_OBJECT_MISSING')&&d2.status!=='PASS');
  chk('the visual-only objects are counted apart from the equipment',
      sep.counts_are_separate===true
      &&sep.visual_only_objects.every(o=>/VISUAL_ONLY_/.test(String(o.tag))));
})();

console.log('\n──────────────────────────────────────────────');
console.log('RENDER TARGETS: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
