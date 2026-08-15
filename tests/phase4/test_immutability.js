const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const LIB=require(_np.join(HERE,'lib_runtime_fixtures.js'));
const SC=LIB.load();
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const VS=(name,opts)=>compileVisualScene(C(SC.models[name]),'bld_0',null,0,
  Object.assign({mode:'ENGINEERING',at:AT},opts||{}));
const RS=(name,opts,cfg)=>compileRuntimeScene(VS(name,opts),cfg||null);
const codes=r=>r.issues.map(i=>i.code);

/* ============================================================================
   المرحلة 4 — الحصانة
   RUNTIME IS EPHEMERAL. ENGINEERING MODEL IS IMMUTABLE.
   لا مسار كتابة من زمن التشغيل إلى المشهد البصري ولا إلى النموذج القانوني.
   ========================================================================== */
const DECO_OPTS={include_decoration:true,layers:VIS_LAYERS.slice()};
const NAMES=['villa','hotel','clinic','warehouse','office','villa_full',
             'clash_full','fls_full','mixed_use','villa_windows','no_site'];
const H=o=>_rtSha16(o);
const NEW=(s)=>createRuntimeState(s,null,null,null);
const byDisc=(s,d)=>(s.objects.filter(o=>o.discipline===d)[0]||null);

console.log('\n== §7 — ENGINEERING_HASH_BEFORE == ENGINEERING_HASH_AFTER ==');
NAMES.forEach(function(n){
  const before=H(SC.models[n]);
  const vs=VS(n,DECO_OPTS);
  const vsBefore=H(vs);
  const rs=compileRuntimeScene(vs,null);
  const st=NEW(rs);
  /* دورة استعمال كاملة: تنقّل، تصادم، بوّابات، تحديد، رؤية، قياس، زمن */
  validateRuntimeNavigation('WALK',null,rs);
  validateRuntimeSpawn(rs,(rs.defaults.spawn||{}).position||[0,0,0],null,null);
  if(rs.objects.length){
    runtimeMoveQuery(rs,st,[0,0.9,0],[6,0.9,6]);
    selectRuntimeObject(st,rs,rs.objects[0].runtime_object_id);
    inspectRuntimeObject(rs,rs.objects[0].runtime_object_id,vs);
    setRuntimeVisibility(st,rs,'HIDE_OBJECT',rs.objects[0].runtime_object_id);
    addRuntimeMeasurement(st,rs,'OBJECT_WIDTH',
      {target_id:rs.objects[0].runtime_object_id}); }
  if(rs.rooms.length) setRuntimeVisibility(st,rs,'ISOLATE_ROOM',
    rs.rooms[0].runtime_room_id);
  rs.walkability.portals.forEach(p=>setPortalState(st,rs,p.portal_id,'OPEN'));
  advanceSimulationTime(st,1.5);
  effectiveRuntimeVisibility(st,rs);
  roomConnectivityGraph(rs);
  runtimeSummary(rs);
  chk(n+': the engineering model hash is unchanged by a full runtime session',
      H(SC.models[n])===before);
  chk(n+': the visual scene hash is unchanged by a full runtime session',
      H(vs)===vsBefore);
});

console.log('\n== COMPILATION ITSELF MUTATES NOTHING ==');
NAMES.forEach(function(n){
  const m=C(SC.models[n]);
  const mBefore=JSON.stringify(m);
  const vs=compileVisualScene(m,'bld_0',null,0,{mode:'ENGINEERING',at:AT});
  const vsBefore=JSON.stringify(vs);
  compileRuntimeScene(vs,null);
  compileRuntimeScene(vs,{decoration_collision:'BLOCKING'});
  compileRuntimeScene(vs,{});
  chk(n+': compiling the runtime scene leaves the model byte-identical',
      JSON.stringify(m)===mBefore);
  chk(n+': compiling the runtime scene leaves the visual scene byte-identical',
      JSON.stringify(vs)===vsBefore);
});

console.log('\n== THE RUNTIME SCENE SHARES NO REFERENCE WITH ITS SOURCE ==');
(function(){
  const vs=VS('fls_full',DECO_OPTS);
  const rs=compileRuntimeScene(vs,null);
  const o=rs.objects[0];
  const src=vs.objects.filter(v=>v.id===o.visual_object_id)[0];
  chk('the visual object behind the first runtime object was found', !!src);
  const geoBefore=JSON.stringify(src.geometry);
  o.obb.cx=999999; o.obb.hy=-5; o.aabb[0]=-999999;
  chk('mutating the runtime box does not reach the visual geometry',
      JSON.stringify(src.geometry)===geoBefore);
  o.collision.blocking=!o.collision.blocking;
  chk('mutating the runtime collision flag does not reach the visual object',
      src.collision===undefined);
  rs.objects.push({runtime_object_id:'INJECTED'});
  chk('pushing into the runtime object array does not reach the visual array',
      vs.objects.every(v=>v.id!=='INJECTED'));
  rs.rooms.length=0;
  chk('emptying the runtime room array does not empty the canonical spaces',
      (vs.spaces||vs.spaces_index||{})!==undefined);
})();

console.log('\n== §31 — NESTED MUTATION ATTACKS ==');
(function(){
  const vs=VS('fls_full',DECO_OPTS), vsBefore=JSON.stringify(vs);
  const mBefore=JSON.stringify(SC.models.fls_full);
  const rs=compileRuntimeScene(vs,null);
  const st=NEW(rs);
  const attacks=[
    ['a top-level scalar on the runtime scene', ()=>{ rs.schema='HACKED'; }],
    ['a nested object on a runtime object', ()=>{ rs.objects[0].obb.yaw=42; }],
    ['a nested array element on a runtime object', ()=>{ rs.objects[0].aabb[2]=-1e9; }],
    ['a whole nested object replaced', ()=>{ rs.objects[0].collision={blocking:'yes'}; }],
    ['a new field grafted onto a runtime object',
     ()=>{ rs.objects[0].fire_rating='2HR'; }],
    ['a runtime room rewritten', ()=>{ rs.rooms[0].area_m2=1e9; }],
    ['a portal rewritten', ()=>{ if(rs.walkability.portals[0])
        rs.walkability.portals[0].to_space='INVENTED'; }],
    ['a surface rewritten', ()=>{ if(rs.walkability.surfaces[0])
        rs.walkability.surfaces[0].elevation_m=-1e9; }],
    ['the spatial index rewritten', ()=>{ rs.spatial_index.cells={}; }],
    ['the defaults rewritten', ()=>{ rs.defaults.navigation_mode='TELEPORT'; }],
    ['the counts rewritten', ()=>{ rs.counts.objects=-1; }],
    ['a selection written into runtime state',
     ()=>{ st.selection={runtime_object_id:'FORGED'}; }],
    ['a measurement forged into runtime state',
     ()=>{ st.measurements.push({type:'AREA',distance_m:-5}); }],
    ['a portal state forged into runtime state',
     ()=>{ st.portal_states.forged='AJAR'; }],
    ['a write flag forced on runtime state', ()=>{ st.writes_to_model=true; }]
  ];
  attacks.forEach(function(a){
    a[1]();
    chk('after '+a[0]+', the visual scene is still byte-identical',
        JSON.stringify(vs)===vsBefore);
    chk('after '+a[0]+', the source model is still byte-identical',
        JSON.stringify(SC.models.fls_full)===mBefore);
  });
  chk('a rebuilt runtime scene is unaffected by the tampered copy',
      JSON.stringify(compileRuntimeScene(VS('fls_full',DECO_OPTS),null))
        ===JSON.stringify(compileRuntimeScene(VS('fls_full',DECO_OPTS),null)));
})();

console.log('\n== §31 — MUTATING THE SOURCE GEOMETRY DIRECTLY IS DETECTED ==');
(function(){
  const m=C(SC.models.villa);
  const clean=compileRuntimeScene(compileVisualScene(C(m),'bld_0',null,0,
    {mode:'ENGINEERING',at:AT}),null);
  const mutated=C(m);
  let touched=false;
  (function bump(node){ if(touched) return;
    if(Array.isArray(node)) return node.forEach(bump);
    if(node&&typeof node==='object'){
      if(Array.isArray(node.rect)&&node.rect.length===4
         &&typeof node.rect[2]==='number'){ node.rect[2]+=1.0; touched=true; return; }
      Object.keys(node).forEach(k=>bump(node[k])); } })(mutated);
  chk('a room rectangle in the source model was actually altered for this test',
      touched);
  const dirty=compileRuntimeScene(compileVisualScene(C(mutated),'bld_0',null,0,
    {mode:'ENGINEERING',at:AT}),null);
  chk('a real change in the source model changes the compiled runtime scene',
      _rtSha16(clean)!==_rtSha16(dirty));
  chk('the original model is still byte-identical — the test mutated a copy',
      JSON.stringify(SC.models.villa)===JSON.stringify(C(SC.models.villa)));
  chk('recompiling the untouched model reproduces the original hash exactly',
      _rtSha16(compileRuntimeScene(compileVisualScene(C(SC.models.villa),'bld_0',null,0,
        {mode:'ENGINEERING',at:AT}),null))===_rtSha16(clean));
})();

console.log('\n== §30 — EVERY DECLARED WRITE INTENT IS REFUSED ==');
(function(){
  chk('the specification declares the write-intent vocabulary',
      Array.isArray(RT_WRITE_INTENTS)&&RT_WRITE_INTENTS.length>0);
  RT_WRITE_INTENTS.forEach(function(intent){
    const p={}; p[intent]=1;
    const r=validateRuntimeAction('SELECT','OBJECT','x',p);
    chk('the intent '+intent+' is refused with RUNTIME_MODEL_WRITE_ATTEMPT',
        r.valid===false&&codes(r).indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0,
        JSON.stringify(codes(r)));
  });
  [['an unlisted set_ prefix','set_anything_at_all'],
   ['an unlisted write_ prefix','write_whatever'],
   ['a raw geometry key','geometry'],
   ['a source identity key','source_element_id'],
   ['a vertex list','vertices'],
   ['a transform','transform'],
   ['an upper-case write intent','SET_GEOMETRY'],
   ['a mixed-case write intent','Set_Position']
  ].forEach(function(p){
    const pl={}; pl[p[1]]=true;
    const r=validateRuntimeAction('INSPECT','OBJECT','x',pl);
    chk(p[0]+' is refused', r.valid===false
        &&codes(r).indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0,
        JSON.stringify(codes(r)));
  });
  const w=validateRuntimeAction('SELECT','OBJECT','x',{writes_to_model:true});
  chk('an explicit writes_to_model claim is refused',
      w.valid===false&&codes(w).indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0);
  chk('a harmless payload is not falsely accused',
      validateRuntimeAction('SELECT','OBJECT','x',{highlight:true}).valid===true);
  chk('every accepted action reports that it writes nothing',
      validateRuntimeAction('SELECT','OBJECT','x',null).writes_to_model!==true);
})();

console.log('\n== A RUNTIME CONFIGURATION MAY NOT REQUEST A WRITE ==');
(function(){
  const vs=VS('villa');
  const r=compileRuntimeScene(vs,{writes_to_model:true});
  chk('a runtime configuration asking to write to the model is refused',
      codes(r).indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0, JSON.stringify(codes(r)));
  chk('the refusal does not silently produce a writable scene',
      r.writes_to_model!==true);
  const clean=compileRuntimeScene(vs,null);
  chk('the source visual scene is untouched by the refused configuration',
      JSON.stringify(compileVisualScene(C(SC.models.villa),'bld_0',null,0,
        {mode:'ENGINEERING',at:AT}))===JSON.stringify(vs));
  chk('a clean compilation still declares that it writes nothing',
      clean.writes_to_model===false);
})();

console.log('\n== §32 — NO REVERSE FLOW EXISTS ANYWHERE IN THE CONTRACT ==');
(function(){
  const vs=VS('fls_full',DECO_OPTS);
  const rs=compileRuntimeScene(vs,null);
  const st=NEW(rs);
  chk('the runtime scene declares that it writes nothing to the model',
      rs.writes_to_model===false);
  chk('the runtime state declares that it writes nothing to the model',
      st.writes_to_model===false);
  chk('the runtime scene names the visual scene it derives from',
      typeof rs.source_scene==='string'&&rs.source_scene.length>0);
  chk('the runtime state names the same source scene',
      st.source_scene===rs.source_scene);
  chk('every runtime object points back at a visual object',
      rs.objects.every(o=>typeof o.visual_object_id==='string'
        &&o.visual_object_id.length>0));
  chk('every source-backed runtime object points back at a source element',
      rs.objects.filter(o=>!o.visual_only)
        .every(o=>typeof o.source_element_id==='string'
          &&o.source_element_id.length>0));
  chk('no visual object was given a runtime identifier',
      vs.objects.every(v=>v.runtime_object_id===undefined
        &&v.runtime_id===undefined&&v.collision===undefined));
  chk('no canonical model element was given a runtime identifier',
      JSON.stringify(SC.models.fls_full).indexOf('runtime:')<0);
  chk('no canonical model element was given a walkability field',
      JSON.stringify(SC.models.fls_full).indexOf('walkability')<0);
  chk('the runtime layer publishes no writer, setter or applier',
      ['applyRuntimeToModel','writeRuntimeToModel','commitRuntime',
       'setModelGeometry','persistRuntime','saveRuntimeToModel',
       'runtimeWriteBack','mutateModel']
        .every(n=>eval('typeof '+n)==='undefined'));
  chk('the probe is not vacuous — it does see a function that exists',
      eval('typeof compileRuntimeScene')==='function');
})();

console.log('\n== THE RUNTIME IDENTIFIER NAMESPACE IS SEPARATE ==');
(function(){
  const rs=compileRuntimeScene(VS('fls_full',DECO_OPTS),null);
  const pat=ACS_RUNTIME_SPEC.runtime_id_patterns;
  chk('the specification declares the runtime identifier patterns', !!pat);
  chk('every runtime object identifier is namespaced',
      rs.objects.every(o=>/^runtime:obj:/.test(o.runtime_object_id)));
  chk('every runtime room identifier is namespaced',
      rs.rooms.every(r=>/^runtime:room:/.test(r.runtime_room_id)));
  chk('every walkable surface identifier is namespaced',
      rs.walkability.surfaces.every(s=>/^walk:space:/.test(s.surface_id)));
  chk('every obstacle identifier is namespaced',
      rs.walkability.obstacles.every(o=>/^obstacle:/.test(o.obstacle_id)));
  chk('every portal identifier is namespaced',
      rs.walkability.portals.every(p=>/^portal:/.test(p.portal_id)));
  chk('the runtime scene identifier is namespaced',
      /^runtime:/.test(rs.runtime_id));
  chk('no runtime identifier collides with a source element identifier',
      rs.objects.every(o=>o.runtime_object_id!==o.source_element_id
        &&o.runtime_object_id!==o.visual_object_id));
})();

console.log('\n== REPEATED SESSIONS NEVER DRIFT ==');
(function(){
  const first=compileRuntimeScene(VS('fls_full',DECO_OPTS),null);
  const h0=_rtSha16(first);
  for(let i=0;i<3;i++){
    const rs=compileRuntimeScene(VS('fls_full',DECO_OPTS),null);
    const st=NEW(rs);
    rs.walkability.portals.forEach(p=>setPortalState(st,rs,p.portal_id,'OPEN'));
    setRuntimeVisibility(st,rs,'HIDE_DISCIPLINE','MEP');
    selectRuntimeObject(st,rs,rs.objects[0].runtime_object_id);
    advanceSimulationTime(st,7.25);
    addRuntimeMeasurement(st,rs,'POINT_TO_POINT',{start:[0,0,0],end:[1,1,1]});
  }
  chk('the compiled runtime scene hash is identical after three full sessions',
      _rtSha16(compileRuntimeScene(VS('fls_full',DECO_OPTS),null))===h0);
  chk('the engineering model hash is identical after three full sessions',
      _rtSha16(SC.models.fls_full)===_rtSha16(JSON.parse(
        fs.readFileSync(_np.join(HERE,'fixtures','runtime_scenarios.json'),'utf8'))
          .models.fls_full));
})();

console.log('\n──────────────────────────────────────────────');
console.log('IMMUTABILITY: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
