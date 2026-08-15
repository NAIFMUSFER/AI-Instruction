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

console.log('\n== §1 — CANONICAL RUNTIME VOCABULARY AND DRIFT ==');
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_runtime.json'),'utf8'));
chk('browser spec is byte-identical to acs_runtime.json',
    JSON.stringify(CANON)===JSON.stringify(ACS_RUNTIME_SPEC));
chk('schema, version and compiler version are pinned',
    RT_SCHEMA==='acs.runtime/1'&&RT_VERSION==='1.0.0'
    &&/^acs-runtime-compiler\//.test(RT_COMPILER_VERSION));
chk('the six navigation modes are declared', RT_NAVIGATION_MODES.length===6
    &&['ORBIT','FIRST_PERSON','WALK','FLY','PLAN','DOLLHOUSE']
      .every(m=>RT_NAVIGATION_MODES.indexOf(m)>=0));
chk('the eleven interaction actions are declared', RT_ACTIONS.length===11
    &&['SELECT','DESELECT','FOCUS','ISOLATE','HIDE','SHOW','INSPECT','MEASURE','TELEPORT',
       'ENTER_ROOM','EXIT_ROOM'].every(a=>RT_ACTIONS.indexOf(a)>=0));
chk('portal states are exactly OPEN and CLOSED',
    JSON.stringify(RT_PORTAL_STATES)===JSON.stringify(['OPEN','CLOSED']));
chk('the twelve visibility modes are declared', RT_VISIBILITY_MODES.length===12);
chk('the five measurement types are declared', RT_MEASUREMENT_TYPES.length===5
    &&['POINT_TO_POINT','OBJECT_WIDTH','OBJECT_HEIGHT','CLEARANCE','ROOM_DIMENSION']
      .every(t=>RT_MEASUREMENT_TYPES.indexOf(t)>=0));
chk('every validation code has a declared severity',
    RT_VALIDATION_CODES.every(c=>RT_SEVERITIES.indexOf(RT_CODE_SEVERITY[c])>=0));
chk('the model-write refusal code is canonical',
    RT_VALIDATION_CODES.indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0
    &&RT_CODE_SEVERITY.RUNTIME_MODEL_WRITE_ATTEMPT==='ERROR');
chk('an unknown code never silently becomes a warning',
    rtSeverityOf('NOT_A_CODE')==='ERROR');
chk('the runtime reuses the canonical visual discipline vocabulary',
    JSON.stringify(RT_DISCIPLINES)===JSON.stringify(ACS_VISUAL_SPEC.visual_layers));
chk('capsule defaults live in the specification, not in code',
    RT_CAPSULE_DEFAULTS.radius_m>0&&RT_CAPSULE_DEFAULTS.height_m>0
    &&RT_CAPSULE_DEFAULTS.eye_height_m>0);
chk('the spec forbids simulation and model-write claims',
    ['runtime_is_model_truth','simulated_evacuation','simulated_fire','simulated_crowd',
     'physics_accurate','pathfinding_agent','elevator_simulated','runtime_write_to_model']
      .every(w=>ACS_RUNTIME_SPEC.forbidden_claims.indexOf(w)>=0));
chk('collision behaviour is declared per kind, never inferred',
    Object.keys(RT_COLLISION_POLICY).every(k=>
      typeof RT_COLLISION_POLICY[k].blocking==='boolean'
      &&typeof RT_COLLISION_POLICY[k].walkable==='boolean'
      &&!!RT_COLLISION_POLICY[k].basis));

console.log('\n== §2 — DETERMINISTIC RUNTIME SCENE ==');
const NAMES=Object.keys(SC.models);
const villa=RS('villa');
chk('the same input produces a byte-identical runtime scene',
    JSON.stringify(RS('villa'))===JSON.stringify(RS('villa')));
chk('every fixture compiles to a valid runtime scene',
    NAMES.every(n=>validateRuntimeScene(RS(n)).valid),
    NAMES.filter(n=>!validateRuntimeScene(RS(n)).valid).join(','));
chk('the runtime scene references its visual source',
    villa.source_scene===VS('villa').scene_id&&!!villa.source_signature);
chk('the runtime id derives from the source scene id',
    villa.runtime_id==='runtime:'+villa.source_scene);
chk('writes_to_model is structurally false on every scene',
    NAMES.every(n=>RS(n).writes_to_model===false));
chk('a configuration requesting writes_to_model is refused',
    codes(RS('villa',null,{writes_to_model:true}) &&
      {issues:RS('villa',null,{writes_to_model:true}).issues})
      .indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0);
chk('compiling does not mutate the visual scene', (function(){
  const vs=VS('villa'); const before=JSON.stringify(vs);
  compileRuntimeScene(vs); return JSON.stringify(vs)===before; })());
chk('compiling does not mutate the source model', (function(){
  const m=C(SC.models.villa); const before=JSON.stringify(m);
  compileRuntimeScene(compileVisualScene(m,'bld_0',null,0,{mode:'ENGINEERING',at:AT}));
  return JSON.stringify(m)===before; })());
chk('the runtime scene carries no timestamp',
    JSON.stringify(villa).indexOf('generated_at')<0
    &&JSON.stringify(villa).indexOf('created_at')<0);
chk('runtime ids are deterministic and prefixed by kind',
    villa.objects.every(o=>/^runtime:obj:/.test(o.runtime_object_id))
    &&villa.rooms.every(r=>/^runtime:room:/.test(r.runtime_room_id))
    &&villa.walkability.surfaces.every(s=>/^walk:space:/.test(s.surface_id))
    &&villa.walkability.obstacles.every(o=>/^obstacle:/.test(o.obstacle_id))
    &&villa.walkability.portals.every(p=>/^portal:/.test(p.portal_id)));
chk('runtime object ids are unique',
    new Set(villa.objects.map(o=>o.runtime_object_id)).size===villa.objects.length);
chk('objects are sorted deterministically',
    JSON.stringify(villa.objects.map(o=>o.runtime_object_id))===
    JSON.stringify(villa.objects.map(o=>o.runtime_object_id).slice().sort()));
chk('a duplicate source object id is rejected, not merged', (function(){
  const adv=SC.adversarial.filter(a=>a[0]==='duplicate_object_id')[0][1];
  return codes(compileRuntimeScene(LIB.hydrate(adv)))
    .indexOf('RUNTIME_ID_DUPLICATE')>=0; })());
chk('a missing source scene is rejected',
    codes(compileRuntimeScene(null)).indexOf('RUNTIME_SOURCE_SCENE_MISSING')>=0);
chk('an invalid source scene is rejected',
    codes(compileRuntimeScene({})).indexOf('RUNTIME_SOURCE_SCENE_INVALID')>=0
    &&codes(compileRuntimeScene('nope')).indexOf('RUNTIME_SOURCE_SCENE_INVALID')>=0);
chk('a failed compile still returns a well-formed empty scene', (function(){
  const r=compileRuntimeScene(null);
  return r.objects.length===0&&r.walkability.portals.length===0
    &&r.writes_to_model===false&&r.counts.objects===0; })());

console.log('\n== §3 — SOURCE TRACEABILITY ==');
chk('every model-derived runtime object names its source element',
    NAMES.every(n=>RS(n).objects.filter(o=>!o.visual_only)
      .every(o=>!!o.source_element_id)));
chk('every runtime object records its source scene',
    villa.objects.every(o=>o.source_scene===villa.source_scene));
chk('a visual-only object gains no engineering source', (function(){
  const s=RS('villa_full',{include_decoration:true,layers:VIS_LAYERS.slice()});
  const v=s.objects.filter(o=>o.visual_only);
  return v.length>0&&v.every(o=>o.source_element_id===null); })());
chk('every obstacle traces back to a runtime object',
    villa.walkability.obstacles.every(o=>
      villa.objects.some(x=>x.runtime_object_id===o.runtime_object_id)));
chk('every walkable surface traces back to a canonical space',
    villa.walkability.surfaces.every(s=>
      villa.rooms.some(r=>r.runtime_room_id===s.runtime_room_id)));
chk('every portal traces back to a modelled door',
    villa.walkability.portals.every(p=>!!p.source_element_id||!!p.visual_object_id));

console.log('\n== §4 — RUNTIME SCENE AND RUNTIME STATE ARE SEPARATE ==');
const st=createRuntimeState(villa,'WALK');
chk('the state is a distinct object with its own fields',
    st.navigation_mode==='WALK'&&Array.isArray(st.measurements)
    &&st.selection===null&&typeof st.portal_states==='object');
chk('the state carries no compiled geometry',
    st.objects===undefined&&st.walkability===undefined);
chk('the state declares writes_to_model false', st.writes_to_model===false);
chk('the state references the scene by id only',
    st.runtime_id===villa.runtime_id&&st.source_scene===villa.source_scene);
chk('mutating the state does not touch the scene', (function(){
  const s=RS('villa'); const before=JSON.stringify(s);
  const t=createRuntimeState(s,'WALK');
  t.selection={runtime_object_id:'x'}; t.simulation_time=99;
  t.visibility.hidden_object_ids.push('x'); t.portal_states['p']='CLOSED';
  t.measurements.push({});
  return JSON.stringify(s)===before; })());
chk('simulation time starts at zero and advances deterministically', (function(){
  const t=createRuntimeState(villa,'WALK');
  const a=advanceSimulationTime(t,1.5), b=advanceSimulationTime(t,0.25);
  return t.simulation_time===1.75&&a.valid&&b.valid; })());
chk('a negative or non-finite time delta is refused',
    codes(advanceSimulationTime(createRuntimeState(villa,'WALK'),-1))
      .indexOf('SIMULATION_TIME_INVALID')>=0
    &&codes(advanceSimulationTime(createRuntimeState(villa,'WALK'),NaN))
      .indexOf('SIMULATION_TIME_INVALID')>=0);
chk('no simulation engine is attached to the clock',
    ACS_RUNTIME_SPEC.simulation_time_note.indexOf('no evacuation')>=0);

console.log('\n== §5 — RULE INPUTS AND SUMMARY ==');
chk('rule inputs are runtime counts only',
    Object.keys(runtimeRuleInputs(villa).building).every(k=>k.indexOf('runtime.')===0));
chk('no runtime count is compared to a threshold',
    JSON.stringify(runtimeRuleInputs(villa)).indexOf('limit')<0
    &&JSON.stringify(runtimeRuleInputs(villa)).indexOf('threshold')<0);
chk('the summary declares no engineering geometry was modified',
    NAMES.every(n=>runtimeSummary(RS(n)).engineering_geometry_modified===false
      &&runtimeSummary(RS(n)).writes_to_model===false));
chk('the summary declares compliance NOT_EVALUATED',
    runtimeSummary(villa).compliance==='NOT_EVALUATED');
chk('counts agree with the compiled collections',
    villa.counts.objects===villa.objects.length
    &&villa.counts.obstacles===villa.walkability.obstacles.length
    &&villa.counts.surfaces===villa.walkability.surfaces.length
    &&villa.counts.portals===villa.walkability.portals.length
    &&villa.counts.rooms===villa.rooms.length);

console.log('\n──────────────────────────────────────────────');
console.log('RUNTIME SCENE: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
