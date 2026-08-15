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
   المرحلة 4 — المدخلات الخصومية
   لا انهيار، ولا استثناء غير ملتقط، ولا قبول صامت، ولا قيمة مخترعة.
   كل رفض يحمل رمزاً معلناً من acs_runtime.json وترتيباً حتمياً.
   ========================================================================== */
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_runtime.json'),'utf8'));
const DECO_OPTS={include_decoration:true,layers:VIS_LAYERS.slice()};
const good=compileRuntimeScene(VS('fls_full',DECO_OPTS),null);
const stG=()=>createRuntimeState(good,null,null,null);
const ADV={}; SC.adversarial.forEach(a=>{ ADV[a[0]]=a[1]; });
const safe=(label,fn)=>{ try{ return {ok:true,v:fn()}; }
  catch(e){ chk('no exception escapes from '+label, false, e&&e.message);
    return {ok:false,v:null}; } };
const declared=cs=>cs.every(c=>CANON.validation_codes.indexOf(c)>=0);

console.log('\n== §34 — ADVERSARIAL VISUAL SCENES ==');
Object.keys(ADV).sort().forEach(function(k){
  const r=safe('the scene '+k,()=>compileRuntimeScene(LIB.hydrate(ADV[k]),null));
  if(!r.ok) return;
  const s=r.v;
  chk(k+': compilation returns a result object instead of throwing',
      !!s&&typeof s==='object');
  chk(k+': the result carries an issue list', Array.isArray(s.issues));
  chk(k+': every reported code is declared in the canonical specification',
      declared(codes(s)), JSON.stringify(codes(s)));
  chk(k+': every issue carries a declared severity',
      s.issues.every(i=>CANON.severities.indexOf(i.severity)>=0));
  chk(k+': the issue list is deterministically ordered', (function(){
    const t=compileRuntimeScene(LIB.hydrate(ADV[k]),null);
    return JSON.stringify(codes(t))===JSON.stringify(codes(s)); })());
  chk(k+': the result is byte-identical when recompiled', (function(){
    const t=compileRuntimeScene(LIB.hydrate(ADV[k]),null);
    return JSON.stringify(t)===JSON.stringify(s); })());
  chk(k+': no non-finite number survives into the compiled scene',
      (s.objects||[]).every(o=>[o.obb.cx,o.obb.cy,o.obb.cz,o.obb.hx,o.obb.hy,
        o.obb.hz,o.obb.yaw].every(Number.isFinite))
      &&(s.objects||[]).every(o=>o.aabb.every(Number.isFinite)));
  chk(k+': the scene never claims to write to the model', s.writes_to_model!==true);
});

console.log('\n== SPECIFIC ADVERSARIAL EXPECTATIONS ==');
(function(){
  const nul=compileRuntimeScene(LIB.hydrate(ADV.null_scene),null);
  chk('a null scene is refused, not compiled',
      nul.accepted===false&&codes(nul).indexOf('RUNTIME_SOURCE_SCENE_MISSING')>=0,
      JSON.stringify(codes(nul)));
  const str=compileRuntimeScene(LIB.hydrate(ADV.string_scene),null);
  chk('a string scene is refused',
      str.accepted===false&&declared(codes(str))&&codes(str).length>0,
      JSON.stringify(codes(str)));
  const arr=compileRuntimeScene(LIB.hydrate(ADV.objects_not_array),null);
  chk('an objects field that is not an array is refused',
      arr.accepted===false&&codes(arr).indexOf('RUNTIME_SOURCE_SCENE_INVALID')>=0,
      JSON.stringify(codes(arr)));
  const nan=compileRuntimeScene(LIB.hydrate(ADV.nan_geometry),null);
  chk('a NaN in the geometry is refused, never rounded to zero',
      codes(nan).indexOf('RUNTIME_SOURCE_OBJECT_INVALID')>=0,
      JSON.stringify(codes(nan)));
  chk('the NaN object does not appear in the compiled object list',
      (nan.objects||[]).every(o=>[o.obb.cx,o.obb.hx].every(Number.isFinite)));
  const inf=compileRuntimeScene(LIB.hydrate(ADV.infinite_geometry),null);
  chk('an infinite extent is refused',
      codes(inf).indexOf('RUNTIME_SOURCE_OBJECT_INVALID')>=0,
      JSON.stringify(codes(inf)));
  const nr=compileRuntimeScene(LIB.hydrate(ADV.nan_rotation),null);
  chk('a NaN rotation is refused, never treated as zero',
      codes(nr).indexOf('RUNTIME_SOURCE_OBJECT_INVALID')>=0,
      JSON.stringify(codes(nr)));
  const dup=compileRuntimeScene(LIB.hydrate(ADV.duplicate_object_id),null);
  chk('a duplicate object identifier is reported',
      codes(dup).indexOf('RUNTIME_ID_DUPLICATE')>=0, JSON.stringify(codes(dup)));
  const wf=compileRuntimeScene(VS('villa'),{writes_to_model:true});
  chk('a configuration requesting a model write is refused',
      codes(wf).indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0, JSON.stringify(codes(wf)));
})();

console.log('\n== ADVERSARIAL RUNTIME CONFIGURATIONS ==');
[['a null configuration',null],['an undefined configuration',undefined],
 ['a string configuration','fast'],['a numeric configuration',7],
 ['an array configuration',[1,2]],['a boolean configuration',true],
 ['an unknown decoration policy',{decoration_collision:'SQUISHY'}],
 ['a numeric decoration policy',{decoration_collision:5}],
 ['an array decoration policy',{decoration_collision:['BLOCKING']}],
 ['a null decoration policy',{decoration_collision:null}],
 ['an unknown key',{turbo:true}]
].forEach(function(p){
  const r=safe('the configuration '+p[0],()=>compileRuntimeScene(VS('villa'),p[1]));
  if(!r.ok) return;
  chk('the configuration '+p[0]+' produces a result without throwing',
      !!r.v&&Array.isArray(r.v.issues));
  chk('the configuration '+p[0]+' never yields an undeclared code',
      declared(codes(r.v)), JSON.stringify(codes(r.v)));
  chk('the configuration '+p[0]+' still yields a declared decoration policy',
      RT_DECORATION_OPTIONS.indexOf(r.v.defaults.decoration_collision)>=0);
});

console.log('\n== ADVERSARIAL NAVIGATION AND CAPSULES ==');
[null,undefined,'','TELEPORT','walk ',42,{mode:'WALK'},['WALK'],true,'WALK '
].forEach(function(m){
  const r=safe('the navigation mode '+JSON.stringify(m),
    ()=>validateRuntimeNavigation(m,null,good));
  if(!r.ok) return;
  chk('the navigation mode '+JSON.stringify(m)+' is refused with a declared code',
      r.v.valid===false&&codes(r.v).indexOf('NAVIGATION_MODE_INVALID')>=0,
      JSON.stringify(codes(r.v)));
});
[null,'',{},[],'capsule',42,true,
 {radius_m:0},{radius_m:-1,height_m:1.8,eye_height_m:1.6},
 {radius_m:NaN,height_m:1.8,eye_height_m:1.6},
 {radius_m:Infinity,height_m:1.8,eye_height_m:1.6},
 {radius_m:0.3,height_m:0,eye_height_m:1.6},
 {radius_m:0.3,height_m:1.8,eye_height_m:99},
 {radius_m:1e9,height_m:1e9,eye_height_m:1e9}
].forEach(function(c){
  const r=safe('the capsule '+JSON.stringify(c),()=>validateRuntimeCapsule(c));
  if(!r.ok) return;
  chk('the capsule '+JSON.stringify(c)+' is judged without throwing',
      typeof r.v.valid==='boolean');
  chk('the capsule '+JSON.stringify(c)+' never yields an undeclared code',
      declared(codes(r.v)), JSON.stringify(codes(r.v)));
  if(!r.v.valid) chk('the refused capsule '+JSON.stringify(c)+' names the capsule code',
      codes(r.v).indexOf('PLAYER_CAPSULE_INVALID')>=0);
  else chk('the accepted capsule '+JSON.stringify(c)+' is finite in every field',
      [r.v.capsule.radius_m,r.v.capsule.height_m,r.v.capsule.eye_height_m]
        .every(Number.isFinite));
});

console.log('\n== ADVERSARIAL SPAWNS AND MOVEMENT ==');
[null,undefined,'',[],[0,0],[0,0,0,0],'0,0,0',{x:0,y:0,z:0},
 [NaN,0,0],[0,Infinity,0],[0,0,-Infinity],[null,0,0],['a','b','c'],
 [true,false,true],[1e308,1e308,1e308]
].forEach(function(p){
  const r=safe('the spawn '+JSON.stringify(p),
    ()=>validateRuntimeSpawn(good,p,null,null));
  if(!r.ok) return;
  chk('the spawn '+JSON.stringify(p)+' is judged without throwing',
      typeof r.v.valid==='boolean');
  chk('the spawn '+JSON.stringify(p)+' never yields an undeclared code',
      declared(codes(r.v)), JSON.stringify(codes(r.v)));
});
[[null,null],[[0,0,0],null],[null,[0,0,0]],[[NaN,0,0],[0,0,0]],
 [[0,0,0],[Infinity,0,0]],['a','b'],[[0,0],[0,0,0]],[{},{}],
 [[0,0,0],[0,0,0]],[[1e9,1e9,1e9],[-1e9,-1e9,-1e9]]
].forEach(function(p){
  const r=safe('the move '+JSON.stringify(p),
    ()=>runtimeMoveQuery(good,stG(),p[0],p[1]));
  if(!r.ok) return;
  chk('the move '+JSON.stringify(p)+' is judged without throwing',
      !!r.v&&typeof r.v==='object');
  chk('the move '+JSON.stringify(p)+' never yields an undeclared code',
      declared(codes(r.v)), JSON.stringify(codes(r.v)));
});

console.log('\n== ADVERSARIAL PORTAL TRANSITIONS ==');
[[null,null],['',''],[good.walkability.portals[0].portal_id,'AJAR'],
 [good.walkability.portals[0].portal_id,null],
 [good.walkability.portals[0].portal_id,42],
 [good.walkability.portals[0].portal_id,['OPEN']],
 ['no_such_portal','OPEN'],[42,'OPEN'],[{p:1},'OPEN'],[['p'],'OPEN']
].forEach(function(p){
  const st=stG();
  const r=safe('the portal transition '+JSON.stringify(p),
    ()=>setPortalState(st,good,p[0],p[1]));
  if(!r.ok) return;
  chk('the portal transition '+JSON.stringify(p)+' is refused with a declared code',
      r.v.valid===false&&declared(codes(r.v))&&codes(r.v).length>0,
      JSON.stringify(codes(r.v)));
  chk('a refused portal transition writes nothing into runtime state',
      Object.keys(st.portal_states).length===0);
});

console.log('\n== ADVERSARIAL SIMULATION TIME ==');
[null,undefined,'',-1,-0.001,NaN,Infinity,-Infinity,'5',{d:1},[1],true,1e308
].forEach(function(d){
  const st=stG();
  const before=st.simulation_time;
  const r=safe('the time delta '+JSON.stringify(d),()=>advanceSimulationTime(st,d));
  if(!r.ok) return;
  chk('the time delta '+JSON.stringify(d)+' is judged without throwing',
      typeof r.v.valid==='boolean');
  chk('the time delta '+JSON.stringify(d)+' never yields an undeclared code',
      declared(codes(r.v)), JSON.stringify(codes(r.v)));
  chk('the simulation clock is finite after the attempt',
      Number.isFinite(st.simulation_time));
  if(!r.v.valid) chk('a refused time delta leaves the clock exactly where it was',
      st.simulation_time===before);
});

console.log('\n== ADVERSARIAL ACTIONS ==');
[[null,null],['',''],['FLY_AWAY','OBJECT'],[42,'OBJECT'],[['SELECT'],'OBJECT'],
 [{a:'SELECT'},'OBJECT'],['SELECT','GALAXY'],['SELECT',42],['SELECT',['OBJECT']],
 ['SELECT',{k:'OBJECT'}]
].forEach(function(p){
  const r=safe('the action '+JSON.stringify(p),
    ()=>validateRuntimeAction(p[0],p[1],'x',null));
  if(!r.ok) return;
  chk('the action '+JSON.stringify(p)+' is refused, never silently accepted',
      r.v.valid===false&&declared(codes(r.v))&&codes(r.v).length>0,
      JSON.stringify(codes(r.v)));
});
[null,'','payload',42,[],[{set_geometry:1}],true
].forEach(function(pl){
  const r=safe('the payload '+JSON.stringify(pl),
    ()=>validateRuntimeAction('SELECT','OBJECT','x',pl));
  if(!r.ok) return;
  chk('the payload '+JSON.stringify(pl)+' is judged without throwing',
      typeof r.v.valid==='boolean');
  chk('the payload '+JSON.stringify(pl)+' never yields an undeclared code',
      declared(codes(r.v)), JSON.stringify(codes(r.v)));
});

console.log('\n== ADVERSARIAL SPATIAL QUERIES ==');
[null,undefined,'',[],[0,0,0],[0,0,0,0,0,0,0],'0,0,0,1,1,1',
 [NaN,0,0,1,1,1],[0,0,0,Infinity,1,1],[1,1,1,0,0,0],
 [1e308,1e308,1e308,1e308,1e308,1e308]
].forEach(function(a){
  const r=safe('the query box '+JSON.stringify(a),
    ()=>queryRuntimeSpatialIndex(good,a));
  if(!r.ok) return;
  chk('the query box '+JSON.stringify(a)+' returns a result without throwing',
      !!r.v&&typeof r.v==='object');
  chk('the query box '+JSON.stringify(a)+' returns only known identifiers',
      (r.v.candidates||[]).every(id=>
        good.walkability.obstacles.some(o=>o.obstacle_id===id)
        ||good.walkability.surfaces.some(s=>s.surface_id===id)));
});

console.log('\n== A HOSTILE SCENE NEVER PRODUCES A CONFIDENT ANSWER ==');
Object.keys(ADV).sort().forEach(function(k){
  const s=compileRuntimeScene(LIB.hydrate(ADV[k]),null);
  const st=createRuntimeState(s,null,null,null);
  chk(k+': a runtime state is still constructible and finite',
      Number.isFinite(st.simulation_time)&&st.writes_to_model===false);
  chk(k+': the summary answers without throwing and invents no count', (function(){
    try{ const sm=runtimeSummary(s);
      return Object.keys(sm).every(key=>typeof sm[key]!=='number'
        ||Number.isFinite(sm[key])); }catch(e){ return false; } })());
  chk(k+': the connectivity graph answers without inventing an edge', (function(){
    try{ const g=roomConnectivityGraph(s);
      return Array.isArray(g.spaces)&&Array.isArray(g.edges)
        &&g.edges.every(e=>g.spaces.indexOf(e[0])>=0||e[1]===RT_EXTERIOR
          ||g.spaces.indexOf(e[1])>=0); }catch(e){ return false; } })());
  chk(k+': validation of the compiled scene answers without throwing', (function(){
    try{ const v=validateRuntimeScene(s); return declared(codes(v)); }
    catch(e){ return false; } })());
});

console.log('\n== ERROR ORDERING IS STABLE AND SEVERITY-RANKED ==');
(function(){
  const s=compileRuntimeScene(LIB.hydrate(ADV.nan_geometry),null);
  const rank=c=>RT_SEVERITIES.indexOf(rtSeverityOf(c));
  chk('a scene with several issues was produced for this check', s.issues.length>0);
  chk('issues are ordered by severity, then code, then subject', (function(){
    for(let i=1;i<s.issues.length;i++){
      const a=s.issues[i-1], b=s.issues[i];
      const ra=rank(a.code), rb=rank(b.code);
      if(ra!==rb){ if(ra>rb) return false; continue; }
      if(a.code!==b.code){ if(a.code>b.code) return false; continue; }
      if(String(a.subject)>String(b.subject)) return false; }
    return true; })());
  chk('every issue names the code, the severity and a subject',
      s.issues.every(i=>typeof i.code==='string'&&typeof i.severity==='string'
        &&'subject' in i));
  chk('the same hostile scene yields the same order every time', (function(){
    const a=JSON.stringify(compileRuntimeScene(LIB.hydrate(ADV.nan_geometry),null).issues);
    const b=JSON.stringify(compileRuntimeScene(LIB.hydrate(ADV.nan_geometry),null).issues);
    return a===b; })());
})();

console.log('\n== NOTHING HOSTILE REACHES THE ENGINEERING MODEL ==');
(function(){
  const mBefore=JSON.stringify(SC.models);
  Object.keys(ADV).sort().forEach(function(k){
    const s=compileRuntimeScene(LIB.hydrate(ADV[k]),null);
    const st=createRuntimeState(s,null,null,null);
    setRuntimeVisibility(st,s,'HIDE_OBJECT','anything');
    selectRuntimeObject(st,s,'anything');
    createRuntimeMeasurement(s,'OBJECT_WIDTH',{target_id:'anything'});
    setPortalState(st,s,'anything','OPEN'); });
  chk('every fixture model is byte-identical after the whole adversarial sweep',
      JSON.stringify(SC.models)===mBefore);
})();

console.log('\n──────────────────────────────────────────────');
console.log('ADVERSARIAL: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
