/* جانب جافاسكربت من تكافؤ المرحلة 4 — يعمل داخل شيفرة المتصفّح المستخرَجة من
   public/index.html، ويكرّر ما يفعله py_runtime.py حرفاً بحرف على نفس التجهيزات. */
const fs=require('fs'), path=require('path');
const HERE=__dirname, PHASE=path.resolve(HERE,'..'), ROOT=path.resolve(PHASE,'..','..');
/* يعمل تحت Node وداخل المتصفّح معاً: نفس الجسم، ولا نسخة ثانية من المنطق. */
const _tmp=(function(){ try{ return require('os').tmpdir(); }catch(e){ return '/tmp'; } })();
const OUT=(process.env&&process.env.ACS_PARITY_RUNTIME_JS)
  ||path.join(_tmp,'acs_parity_runtime_js.json');
const LIB=require(path.join(PHASE,'lib_runtime_fixtures.js'));
const SC=LIB.load();
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const DECO_LAYERS=VIS_LAYERS.slice();

function visual(q){
  const m=C(SC.models[q.m]);
  return compileVisualScene(m,q.bid,q.pos,q.rot||0,{mode:q.mode,
    include_decoration:!!q.deco,layers:q.deco?DECO_LAYERS:null,at:AT}); }

const out={};
SC.queries.forEach(function(q){
  const before=JSON.stringify(SC.models[q.m]);
  const vs=visual(q);
  const vsBefore=JSON.stringify(vs);
  const scene=compileRuntimeScene(vs,q.cfg||null);
  if(JSON.stringify(SC.models[q.m])!==before)
    throw new Error('the runtime compiler mutated the model: '+q.n);
  if(JSON.stringify(vs)!==vsBefore)
    throw new Error('the runtime compiler mutated the visual scene: '+q.n);

  const state=createRuntimeState(scene,null,null,null);
  const objects=scene.objects, rooms=scene.rooms, portals=scene.walkability.portals;
  const firstObj=objects.length?objects[0].runtime_object_id:'none';
  const firstRoom=rooms.length?rooms[0].runtime_room_id:'none';
  const firstPortal=portals.length?portals[0].portal_id:'none';
  const spawn=((scene.defaults.spawn||{}).position)||[0,0,0];

  const selState=createRuntimeState(scene,null,null,null);
  const visState=createRuntimeState(scene,null,null,null);
  const measState=createRuntimeState(scene,null,null,null);
  const portalState=createRuntimeState(scene,null,null,null);

  const nav={};
  RT_NAVIGATION_MODES.forEach(m=>{ nav[m]=validateRuntimeNavigation(m,null,scene); });

  const entry={
    scene:scene,
    summary:runtimeSummary(scene),
    rule_inputs:runtimeRuleInputs(scene),
    validate:validateRuntimeScene(scene),
    state:state,
    connectivity:roomConnectivityGraph(scene),
    nav:nav,
    nav_bad:validateRuntimeNavigation('TELEPORT',null,scene),
    capsule_default:validateRuntimeCapsule(null),
    capsule_bad:validateRuntimeCapsule({radius_m:-1,height_m:0,eye_height_m:99}),
    spawn_default:validateRuntimeSpawn(scene,spawn,null,null),
    spawn_far:validateRuntimeSpawn(scene,[999,0,999],null,null),
    spawn_nearest:findNearestValidSpawn(scene,[0,0,0],null,null,undefined,undefined),
    query_local:queryRuntimeSpatialIndex(scene,[0,0,0,4,3,4]),
    query_wide:queryRuntimeSpatialIndex(scene,[-1e9,-1e9,-1e9,1e9,1e9,1e9]),
    query_bad:queryRuntimeSpatialIndex(scene,[NaN,0,0,1,1,1]),
    move_short:runtimeMoveQuery(scene,state,[0,0.9,0],[1,0.9,1]),
    move_long:runtimeMoveQuery(scene,state,[0,0.9,0],[20,0.9,20]),
    move_bad:runtimeMoveQuery(scene,state,null,[0,0,0]),
    select:selectRuntimeObject(selState,scene,firstObj),
    select_bad:selectRuntimeObject(selState,scene,'no_such_object'),
    select_null:selectRuntimeObject(selState,scene,null),
    inspect:inspectRuntimeObject(scene,firstObj,vs),
    inspect_no_visual:inspectRuntimeObject(scene,firstObj,null),
    inspect_room:inspectRuntimeObject(scene,firstRoom,vs),
    inspect_bad:inspectRuntimeObject(scene,'no_such_object',vs),
    hide_object:setRuntimeVisibility(visState,scene,'HIDE_OBJECT',firstObj),
    isolate_room:setRuntimeVisibility(visState,scene,'ISOLATE_ROOM',firstRoom),
    hide_discipline:setRuntimeVisibility(visState,scene,'HIDE_DISCIPLINE','MEP'),
    visibility_bad_mode:setRuntimeVisibility(visState,scene,'X_RAY',null),
    visibility_bad_target:setRuntimeVisibility(visState,scene,'HIDE_ROOM','nope'),
    effective:effectiveRuntimeVisibility(visState,scene),
    restore:restoreRuntimeVisibility(visState,scene),
    effective_after_restore:effectiveRuntimeVisibility(visState,scene),
    measure_points:createRuntimeMeasurement(scene,'POINT_TO_POINT',
      {start:[0,0,0],end:[3,4,0]}),
    measure_width:createRuntimeMeasurement(scene,'OBJECT_WIDTH',{target_id:firstObj}),
    measure_height:createRuntimeMeasurement(scene,'OBJECT_HEIGHT',{target_id:firstObj}),
    measure_room:createRuntimeMeasurement(scene,'ROOM_DIMENSION',{target_id:firstRoom}),
    measure_clearance:createRuntimeMeasurement(scene,'CLEARANCE',
      {target_id:firstObj,
       other_id:objects.length?objects[objects.length-1].runtime_object_id:'none'}),
    measure_bad_type:createRuntimeMeasurement(scene,'AREA',{start:[0,0,0],end:[1,1,1]}),
    measure_bad_vector:createRuntimeMeasurement(scene,'POINT_TO_POINT',
      {start:[0,0],end:[1,1,1]}),
    measure_bad_target:createRuntimeMeasurement(scene,'OBJECT_WIDTH',{target_id:'nope'}),
    portal_open:setPortalState(portalState,scene,firstPortal,'OPEN'),
    portal_closed:setPortalState(portalState,scene,firstPortal,'CLOSED'),
    portal_bad_state:setPortalState(portalState,scene,firstPortal,'AJAR'),
    portal_bad_id:setPortalState(portalState,scene,'nope','OPEN'),
    portal_states_after:portalState.portal_states,
    time_ok:advanceSimulationTime(measState,1.5),
    time_bad:advanceSimulationTime(measState,-1.0),
    time_after:measState.simulation_time,
    sel_state_after:selState,
    vis_state_after:visState};
  entry.add_measure=addRuntimeMeasurement(measState,scene,'OBJECT_WIDTH',
    {target_id:firstObj});
  entry.meas_state_after=measState;
  out[q.n]=entry;
});

const adv={};
SC.adversarial.forEach(function(pair){
  const name=pair[0];
  const s=compileRuntimeScene(LIB.hydrate(pair[1]),null);
  const st=createRuntimeState(s,null,null,null);
  adv[name]={
    scene:s, accepted:s.accepted, issues:s.issues,
    summary:runtimeSummary(s),
    validate:validateRuntimeScene(s),
    connectivity:roomConnectivityGraph(s),
    state:st,
    select:selectRuntimeObject(st,s,'anything'),
    visibility:setRuntimeVisibility(st,s,'HIDE_OBJECT','anything'),
    measure:createRuntimeMeasurement(s,'OBJECT_WIDTH',{target_id:'anything'}),
    portal:setPortalState(st,s,'anything','OPEN')};
});
out.__adversarial__=adv;

const baseScene=compileRuntimeScene(visual(SC.queries[0]),null);
out.__ops__={
  navigation_modes:RT_NAVIGATION_MODES.slice(),
  navigation_contracts:RT_NAVIGATION_CONTRACTS,
  visibility_modes:RT_VISIBILITY_MODES.slice(),
  measurement_types:RT_MEASUREMENT_TYPES.slice(),
  actions:RT_ACTIONS.slice(),
  validation_codes:RT_VALIDATION_CODES.slice(),
  capsules:[null,{},{radius_m:0.3,height_m:1.8,eye_height_m:1.6},
    {radius_m:0,height_m:1.8,eye_height_m:1.6},
    {radius_m:0.3,height_m:1.8,eye_height_m:99},
    {radius_m:1e9,height_m:1e9,eye_height_m:1e9}].map(validateRuntimeCapsule),
  navigation:[null,'','WALK','walk','TELEPORT','FLY']
    .map(m=>validateRuntimeNavigation(m,null,null)),
  actions_checked:[['SELECT','OBJECT',null],['SELECT','OBJECT',{set_geometry:1}],
    ['INSPECT','OBJECT',{writes_to_model:true}],['MEASURE','OBJECT',null],
    ['FLY_AWAY','OBJECT',null],['SELECT','GALAXY',null],[null,null,null]]
    .map(t=>validateRuntimeAction(t[0],t[1],'x',t[2])),
  measurements_validated:[null,'x',
    {type:'AREA',runtime_only:true,distance_m:1},
    {type:'OBJECT_WIDTH',runtime_only:false,distance_m:1},
    {type:'OBJECT_WIDTH',runtime_only:true,distance_m:-1},
    {type:'OBJECT_WIDTH',runtime_only:true,distance_m:'3'},
    {type:'OBJECT_WIDTH',runtime_only:true,distance_m:2.5}]
    .map(validateRuntimeMeasurement),
  times:[0,1,-1,NaN,Infinity,'5'].map(d=>advanceSimulationTime(
    createRuntimeState(baseScene,null,null,null),d))};

fs.writeFileSync(OUT,JSON.stringify(out),'utf8');
console.log('javascript runtime parity written: '+OUT+' ('+Object.keys(out).length+' keys)');
