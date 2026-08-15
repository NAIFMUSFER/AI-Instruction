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
   المرحلة 4 — القياس
   القياس زمن تشغيل فقط: مسافة تُحسب من إحداثيات مُتحقَّق منها.
   ليس فحص مطابقة، ولا اشتراط خلوص، ولا قراراً هندسياً.
   ========================================================================== */
const DECO_OPTS={include_decoration:true,layers:VIS_LAYERS.slice()};
const vsV=VS('fls_full',DECO_OPTS), sc=compileRuntimeScene(vsV,null);
const rot=RS('villa',{position:{x:-6,z:4},rotation_deg:45});
const NEW=s=>createRuntimeState(s||sc,null,null,null);
const pick=(s,p)=>(s.objects.filter(p)[0]||null);
const byDisc=(s,d)=>pick(s,o=>o.discipline===d);
const M=(t,o)=>createRuntimeMeasurement(sc,t,o||{});

console.log('\n== §27 — THE FIVE MEASUREMENT TYPES ARE DECLARED ==');
chk('the canonical specification declares the measurement types',
    Array.isArray(RT_MEASUREMENT_TYPES)&&RT_MEASUREMENT_TYPES.length===5);
chk('the browser mirror and the canonical file agree on the type list',
    JSON.stringify(RT_MEASUREMENT_TYPES)
      ===JSON.stringify(JSON.parse(fs.readFileSync(
        _np.join(ROOT,'acs_runtime.json'),'utf8')).measurement_types));
['POINT_TO_POINT','OBJECT_WIDTH','OBJECT_HEIGHT','ROOM_DIMENSION','CLEARANCE']
  .forEach(function(t){
  chk('the type '+t+' is declared', RT_MEASUREMENT_TYPES.indexOf(t)>=0); });
chk('the action MEASURE is declared', RT_ACTIONS.indexOf('MEASURE')>=0);

console.log('\n== POINT TO POINT ==');
(function(){
  const r=M('POINT_TO_POINT',{start:[0,0,0],end:[3,4,0]});
  chk('a point-to-point measurement succeeds', r.valid&&!!r.measurement);
  chk('the distance is the euclidean distance, computed not trusted',
      r.measurement.distance_m===5);
  chk('a three-dimensional distance is computed over all three axes',
      M('POINT_TO_POINT',{start:[0,0,0],end:[1,2,2]}).measurement.distance_m===3);
  chk('a zero-length measurement is legal and reports zero',
      M('POINT_TO_POINT',{start:[2,2,2],end:[2,2,2]}).measurement.distance_m===0);
  chk('the measurement echoes the verified endpoints',
      JSON.stringify(r.measurement.start)===JSON.stringify([0,0,0])
      &&JSON.stringify(r.measurement.end)===JSON.stringify([3,4,0]));
  chk('a caller-supplied distance is never trusted', (function(){
    const f=createRuntimeMeasurement(sc,'POINT_TO_POINT',
      {start:[0,0,0],end:[3,4,0],distance_m:999});
    return f.measurement.distance_m===5; })());
  chk('negative coordinates are handled',
      M('POINT_TO_POINT',{start:[-3,-4,0],end:[0,0,0]}).measurement.distance_m===5);
})();

console.log('\n== OBJECT WIDTH AND HEIGHT COME FROM THE COMPILED BOX ==');
(function(){
  const o=byDisc(sc,'ARCHITECTURE');
  const w=M('OBJECT_WIDTH',{target_id:o.runtime_object_id});
  const h=M('OBJECT_HEIGHT',{target_id:o.runtime_object_id});
  chk('an object width measurement succeeds', w.valid&&!!w.measurement);
  chk('the width equals twice the compiled half-extent exactly',
      w.measurement.distance_m===_rtQ(o.obb.hx*2));
  chk('the height equals twice the compiled half-extent exactly',
      h.measurement.distance_m===_rtQ(o.obb.hy*2));
  chk('a width measurement declares its axis', w.measurement.axis==='WIDTH');
  chk('a height measurement declares its axis', h.measurement.axis==='HEIGHT');
  chk('the measurement names the source element behind the object',
      w.measurement.source_element_id===o.source_element_id);
  chk('the measurement names the runtime object it measured',
      w.measurement.target_id===o.runtime_object_id);
  chk('every object in the fixture measures to a finite non-negative width',
      sc.objects.every(function(x){
        const m=M('OBJECT_WIDTH',{target_id:x.runtime_object_id});
        return m.valid&&Number.isFinite(m.measurement.distance_m)
            &&m.measurement.distance_m>=0; }));
  chk('an object resolves for measurement by its source element id too',
      M('OBJECT_WIDTH',{target_id:o.source_element_id}).valid===true);
})();

console.log('\n== ROTATED GEOMETRY MEASURES ITS OWN EXTENT, NOT ITS SHADOW ==');
(function(){
  const plain=RS('villa');
  const yawed=rot.objects.filter(o=>Math.abs(o.obb.yaw)>1e-9);
  chk('the rotated fixture actually carries yawed boxes', yawed.length>0);
  const o=yawed[0];
  const m=createRuntimeMeasurement(rot,'OBJECT_WIDTH',{target_id:o.runtime_object_id});
  chk('a yawed object still measures its own local width',
      m.valid&&m.measurement.distance_m===_rtQ(o.obb.hx*2));
  chk('the yawed width is not the axis-aligned bounding width', (function(){
    const aabbW=_rtQ(o.aabb[3]-o.aabb[0]);
    return aabbW!==m.measurement.distance_m; })());
  chk('rotating the whole building does not change a member width', (function(){
    const src=o.source_element_id;
    const p=plain.objects.filter(x=>x.source_element_id===src)[0];
    if(!p) return false;
    const a=createRuntimeMeasurement(plain,'OBJECT_WIDTH',{target_id:p.runtime_object_id});
    return a.measurement.distance_m===m.measurement.distance_m; })());
  chk('every measurement on the rotated scene is finite',
      rot.objects.every(function(x){
        const r=createRuntimeMeasurement(rot,'OBJECT_HEIGHT',
          {target_id:x.runtime_object_id});
        return r.valid&&Number.isFinite(r.measurement.distance_m); }));
})();

console.log('\n== ROOM DIMENSION COMES FROM THE CANONICAL RECTANGLE ==');
(function(){
  const r0=sc.rooms[0];
  const m=M('ROOM_DIMENSION',{target_id:r0.runtime_room_id});
  chk('a room dimension measurement succeeds', m.valid&&!!m.measurement);
  chk('the width and depth equal the canonical rectangle exactly',
      m.measurement.width_m===_rtQ(r0.rect_local[2])
      &&m.measurement.depth_m===_rtQ(r0.rect_local[3]));
  chk('the reported distance is the longer of the two sides',
      m.measurement.distance_m===_rtQ(Math.max(r0.rect_local[2],r0.rect_local[3])));
  chk('the measurement names the canonical space instance',
      m.measurement.source_element_id===r0.space_instance_id);
  chk('every room in the fixture measures finite and non-negative',
      sc.rooms.every(function(r){
        const x=M('ROOM_DIMENSION',{target_id:r.runtime_room_id});
        return x.valid&&Number.isFinite(x.measurement.distance_m)
            &&x.measurement.distance_m>=0; }));
  chk('a room resolves for measurement by its space id too',
      M('ROOM_DIMENSION',{target_id:r0.space_id}).valid===true);
  chk('a room dimension never claims an occupancy or an egress width',
      Object.keys(m.measurement).every(k=>
        !/occupan|egress|exit|capacity|compliance|code/i.test(k)));
})();

console.log('\n== CLEARANCE IS A MEASURED GAP, NEVER A REQUIREMENT ==');
(function(){
  const a=byDisc(sc,'ARCHITECTURE'), b=byDisc(sc,'MEP');
  chk('two distinct objects exist to measure between', !!a&&!!b);
  const m=M('CLEARANCE',{target_id:a.runtime_object_id,other_id:b.runtime_object_id});
  chk('a clearance measurement succeeds', m.valid&&!!m.measurement);
  chk('the clearance is finite and non-negative',
      Number.isFinite(m.measurement.distance_m)&&m.measurement.distance_m>=0);
  chk('the clearance names both runtime objects and both source elements',
      m.measurement.target_id===a.runtime_object_id
      &&m.measurement.other_id===b.runtime_object_id
      &&m.measurement.source_element_id===a.source_element_id
      &&m.measurement.other_source_element_id===b.source_element_id);
  chk('the clearance between an object and itself is zero',
      M('CLEARANCE',{target_id:a.runtime_object_id,
        other_id:a.runtime_object_id}).measurement.distance_m===0);
  chk('two overlapping objects report a zero gap, never a negative one', (function(){
    const overlapping=sc.objects.filter(function(x){
      return sc.objects.some(function(y){
        return y.runtime_object_id!==x.runtime_object_id
          &&_rtAabbOverlap(x.aabb,y.aabb); }); });
    if(!overlapping.length) return true;
    const x=overlapping[0];
    const y=sc.objects.filter(z=>z.runtime_object_id!==x.runtime_object_id
      &&_rtAabbOverlap(x.aabb,z.aabb))[0];
    return M('CLEARANCE',{target_id:x.runtime_object_id,
      other_id:y.runtime_object_id}).measurement.distance_m===0; })());
  chk('clearance is symmetric', (function(){
    const f=M('CLEARANCE',{target_id:a.runtime_object_id,other_id:b.runtime_object_id});
    const r=M('CLEARANCE',{target_id:b.runtime_object_id,other_id:a.runtime_object_id});
    return f.measurement.distance_m===r.measurement.distance_m; })());
  chk('a clearance measurement states that it is not a code check',
      /never a code check/.test(String(m.measurement.note)));
  chk('a clearance measurement declares no required or minimum value',
      Object.keys(m.measurement).every(k=>!/required|minimum|min_|allow|limit/i.test(k)));
})();

console.log('\n== MULTI-LEVEL MEASUREMENT ==');
(function(){
  const levels=Array.from(new Set(sc.objects.map(o=>o.level_index)
    .filter(x=>x!==null))).sort((a,b)=>a-b);
  chk('the fixture spans more than one level', levels.length>1, JSON.stringify(levels));
  const lo=pick(sc,o=>o.level_index===levels[0]);
  const hi=pick(sc,o=>o.level_index===levels[levels.length-1]);
  const m=M('CLEARANCE',{target_id:lo.runtime_object_id,other_id:hi.runtime_object_id});
  chk('a clearance across two levels is computed', m.valid
      &&Number.isFinite(m.measurement.distance_m));
  chk('a vertical point-to-point measurement crosses levels correctly', (function(){
    const a=[0,lo.obb.cy,0], b=[0,hi.obb.cy,0];
    const r=M('POINT_TO_POINT',{start:a,end:b});
    return r.valid&&r.measurement.distance_m===_rtQ(Math.abs(hi.obb.cy-lo.obb.cy)); })());
  chk('a measurement never claims which level it belongs to as a fact', (function(){
    const r=M('OBJECT_WIDTH',{target_id:hi.runtime_object_id});
    return r.measurement.level_index===undefined; })());
})();

console.log('\n== MALFORMED VECTORS AND UNKNOWN SOURCES ARE REFUSED ==');
[['a missing start',{end:[1,1,1]}],
 ['a missing end',{start:[1,1,1]}],
 ['a two-component vector',{start:[1,1],end:[0,0,0]}],
 ['a four-component vector',{start:[1,1,1,1],end:[0,0,0]}],
 ['a string vector',{start:'1,1,1',end:[0,0,0]}],
 ['an object vector',{start:{x:1,y:1,z:1},end:[0,0,0]}],
 ['a null vector',{start:null,end:[0,0,0]}],
 ['a vector of strings',{start:['a','b','c'],end:[0,0,0]}],
 ['a vector carrying null',{start:[1,null,1],end:[0,0,0]}],
 ['a vector carrying NaN',{start:[1,NaN,1],end:[0,0,0]}],
 ['a vector carrying Infinity',{start:[1,Infinity,1],end:[0,0,0]}],
 ['a vector carrying negative Infinity',{start:[0,0,0],end:[-Infinity,0,0]}],
 ['a nested vector',{start:[[1],[1],[1]],end:[0,0,0]}],
 ['a boolean vector',{start:[true,false,true],end:[0,0,0]}]
].forEach(function(p){
  const r=M('POINT_TO_POINT',p[1]);
  chk('point-to-point refuses '+p[0],
      r.valid===false&&r.measurement===null
      &&codes(r).indexOf('MEASUREMENT_INVALID')>=0, JSON.stringify(codes(r)));
});
[null,'','AREA','VOLUME','ANGLE',42,{t:'OBJECT_WIDTH'},['OBJECT_WIDTH'],true
].forEach(function(t){
  const r=createRuntimeMeasurement(sc,t,{start:[0,0,0],end:[1,1,1]});
  chk('an unknown measurement type '+JSON.stringify(t)+' is refused',
      r.valid===false&&r.measurement===null
      &&codes(r).indexOf('MEASUREMENT_INVALID')>=0, JSON.stringify(codes(r)));
});
[['OBJECT_WIDTH',{target_id:'no_such_object'}],
 ['OBJECT_HEIGHT',{target_id:null}],
 ['OBJECT_WIDTH',{target_id:{a:1}}],
 ['ROOM_DIMENSION',{target_id:'no_such_room'}],
 ['ROOM_DIMENSION',{target_id:null}],
 ['ROOM_DIMENSION',{target_id:sc.objects[0].runtime_object_id}],
 ['OBJECT_WIDTH',{target_id:sc.rooms[0].runtime_room_id}],
 ['CLEARANCE',{target_id:'nope',other_id:sc.objects[0].runtime_object_id}],
 ['CLEARANCE',{target_id:sc.objects[0].runtime_object_id,other_id:'nope'}],
 ['CLEARANCE',{target_id:null,other_id:null}],
 ['CLEARANCE',{target_id:sc.objects[0].runtime_object_id}]
].forEach(function(p){
  const r=M(p[0],p[1]);
  chk(p[0]+' refuses an unknown source '+JSON.stringify(p[1]),
      r.valid===false&&r.measurement===null
      &&codes(r).indexOf('MEASUREMENT_TARGET_INVALID')>=0, JSON.stringify(codes(r)));
});

console.log('\n== EVERY ACCEPTED RESULT IS FINITE AND NON-NEGATIVE ==');
(function(){
  const all=[];
  sc.objects.forEach(function(o){
    all.push(M('OBJECT_WIDTH',{target_id:o.runtime_object_id}));
    all.push(M('OBJECT_HEIGHT',{target_id:o.runtime_object_id})); });
  sc.rooms.forEach(r=>all.push(M('ROOM_DIMENSION',{target_id:r.runtime_room_id})));
  for(let i=0;i+1<sc.objects.length;i+=7)
    all.push(M('CLEARANCE',{target_id:sc.objects[i].runtime_object_id,
      other_id:sc.objects[i+1].runtime_object_id}));
  chk('a broad sweep of measurements was actually executed', all.length>50,
      String(all.length));
  chk('every accepted measurement is finite',
      all.filter(x=>x.valid).every(x=>Number.isFinite(x.measurement.distance_m)));
  chk('no accepted measurement is negative',
      all.filter(x=>x.valid).every(x=>x.measurement.distance_m>=0));
  chk('every accepted measurement validates against its own validator',
      all.filter(x=>x.valid).every(x=>validateRuntimeMeasurement(x.measurement).valid));
  chk('every accepted measurement declares runtime_only',
      all.filter(x=>x.valid).every(x=>x.measurement.runtime_only===true));
  chk('every accepted measurement names the scene it came from',
      all.filter(x=>x.valid).every(x=>x.measurement.source_scene===sc.source_scene));
})();

console.log('\n== THE VALIDATOR REFUSES A FORGED MEASUREMENT ==');
[['a non-object',null],['a string','5 m'],['an array',[1,2,3]],
 ['an unknown type',{type:'AREA',runtime_only:true,distance_m:1}],
 ['a missing runtime_only flag',{type:'OBJECT_WIDTH',distance_m:1}],
 ['runtime_only set to false',{type:'OBJECT_WIDTH',runtime_only:false,distance_m:1}],
 ['runtime_only set to a truthy string',
  {type:'OBJECT_WIDTH',runtime_only:'yes',distance_m:1}],
 ['a negative distance',{type:'OBJECT_WIDTH',runtime_only:true,distance_m:-1}],
 ['a NaN distance',{type:'OBJECT_WIDTH',runtime_only:true,distance_m:NaN}],
 ['an infinite distance',{type:'OBJECT_WIDTH',runtime_only:true,distance_m:Infinity}],
 ['a string distance',{type:'OBJECT_WIDTH',runtime_only:true,distance_m:'3'}],
 ['a missing distance',{type:'OBJECT_WIDTH',runtime_only:true}]
].forEach(function(p){
  const r=validateRuntimeMeasurement(p[1]);
  chk('the validator refuses '+p[0],
      r.valid===false&&codes(r).indexOf('MEASUREMENT_INVALID')>=0,
      JSON.stringify(codes(r)));
});

console.log('\n== MEASUREMENT IDENTITY IS DETERMINISTIC ==');
(function(){
  const o=byDisc(sc,'ARCHITECTURE');
  const a=M('OBJECT_WIDTH',{target_id:o.runtime_object_id}).measurement;
  const b=M('OBJECT_WIDTH',{target_id:o.runtime_object_id}).measurement;
  chk('the same measurement twice yields the same identifier',
      a.measurement_id===b.measurement_id);
  chk('the whole measurement is byte-identical across repeated calls',
      JSON.stringify(a)===JSON.stringify(b));
  chk('a different type yields a different identifier',
      M('OBJECT_HEIGHT',{target_id:o.runtime_object_id})
        .measurement.measurement_id!==a.measurement_id);
  chk('a different target yields a different identifier',
      M('OBJECT_WIDTH',{target_id:byDisc(sc,'MEP').runtime_object_id})
        .measurement.measurement_id!==a.measurement_id);
  chk('the identifier follows the declared runtime identifier shape',
      /^measure:[0-9a-f]{16}$/.test(a.measurement_id));
  chk('the identifier carries no timestamp and no random component',
      a.measurement_id===M('OBJECT_WIDTH',
        {target_id:o.runtime_object_id}).measurement.measurement_id);
})();

console.log('\n== MEASUREMENTS ACCUMULATE IN RUNTIME STATE ONLY ==');
(function(){
  const st=NEW();
  const scBefore=JSON.stringify(sc), vsBefore=JSON.stringify(vsV);
  const mBefore=JSON.stringify(SC.models.fls_full);
  chk('a fresh runtime state carries no measurement', st.measurements.length===0);
  const o=byDisc(sc,'ARCHITECTURE');
  const r=addRuntimeMeasurement(st,sc,'OBJECT_WIDTH',{target_id:o.runtime_object_id});
  chk('adding a measurement succeeds', r.valid);
  chk('the measurement lands in runtime state', st.measurements.length===1);
  addRuntimeMeasurement(st,sc,'POINT_TO_POINT',{start:[0,0,0],end:[1,0,0]});
  chk('a second measurement accumulates', st.measurements.length===2);
  const bad=addRuntimeMeasurement(st,sc,'OBJECT_WIDTH',{target_id:'nope'});
  chk('a refused measurement is not stored',
      bad.valid===false&&st.measurements.length===2);
  chk('the runtime scene is byte-identical after every measurement',
      JSON.stringify(sc)===scBefore);
  chk('the visual scene is byte-identical after every measurement',
      JSON.stringify(vsV)===vsBefore);
  chk('the source model is byte-identical after every measurement',
      JSON.stringify(SC.models.fls_full)===mBefore);
  chk('no runtime object grew a measurement field',
      sc.objects.every(x=>x.measurements===undefined&&x.measured===undefined));
  chk('the stored measurement is a copy, not a live reference', (function(){
    const s2=NEW();
    const rr=addRuntimeMeasurement(s2,sc,'POINT_TO_POINT',
      {start:[0,0,0],end:[1,0,0]});
    rr.measurement.distance_m=999;
    return s2.measurements[0].distance_m===1; })());
  chk('the runtime state still declares that it writes nothing to the model',
      st.writes_to_model===false);
})();

console.log('\n== A MEASUREMENT IS NEVER A COMPLIANCE STATEMENT ==');
(function(){
  const FORBIDDEN=new RegExp(['\\bsbc\\b','\\bibc\\b','nfpa','\\bada\\b','\\baci\\b',
    'asce','aisc','eurocode','\\bnec\\b','\\biec\\b','ashrae','compliance',
    'code_check','conform','approved','certified','required_clearance',
    'minimum_clearance','egress_width','occupancy_load','pass','fail'].join('|'),'i');
  const NOTE_KEYS=['note','notes','detail','reason','basis','disclaimer'];
  const scan=root=>{ const hits=[];
    const walk=(v,p)=>{ if(Array.isArray(v)) return v.forEach((x,n)=>walk(x,p+'['+n+']'));
      if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
        if(NOTE_KEYS.indexOf(k)>=0) return;
        if(FORBIDDEN.test(k)) hits.push(p+'.'+k);
        if(typeof v[k]==='string'&&FORBIDDEN.test(v[k])) hits.push(p+'.'+k+'='+v[k]);
        walk(v[k],p+'.'+k); }); };
    walk(root,''); return hits; };
  const hits=sc.objects.map(o=>scan(M('OBJECT_WIDTH',
    {target_id:o.runtime_object_id}).measurement||{}))
    .concat(sc.rooms.map(r=>scan(M('ROOM_DIMENSION',
      {target_id:r.runtime_room_id}).measurement||{})))
    .reduce((a,b)=>a.concat(b),[]);
  if(hits.length) console.log('     hits:',JSON.stringify(hits.slice(0,4)));
  chk('no measurement anywhere carries a code or compliance value', hits.length===0);
  chk('the forbidden pattern is not vacuous',
      scan({compliance:'PASS'}).length>0&&scan({egress_width:1.2}).length>0);
  chk('every measurement denies being a code check in its own words',
      sc.rooms.every(r=>/never a code check, a clearance requirement or a compliance/
        .test(String(M('ROOM_DIMENSION',{target_id:r.runtime_room_id})
          .measurement.note))));
  const w=validateRuntimeAction('MEASURE','OBJECT','x',{set_dimension:1});
  chk('a measure payload asking to set a dimension is refused',
      w.valid===false&&codes(w).indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0);
})();

console.log('\n── multiple models ──');
['villa','hotel','clinic','warehouse','office','mixed_use','villa_windows']
  .forEach(function(n){
  const s=RS(n);
  const o=s.objects[0], r=s.rooms[0];
  const a=createRuntimeMeasurement(s,'OBJECT_WIDTH',{target_id:o.runtime_object_id});
  const b=createRuntimeMeasurement(s,'ROOM_DIMENSION',{target_id:r.runtime_room_id});
  chk(n+': an object and a room both measure finite and non-negative',
      a.valid&&b.valid&&a.measurement.distance_m>=0&&b.measurement.distance_m>=0
      &&Number.isFinite(a.measurement.distance_m)
      &&Number.isFinite(b.measurement.distance_m));
});
(function(){
  const s=RS('degenerate');
  chk('a degenerate model refuses a measurement instead of inventing one',
      createRuntimeMeasurement(s,'OBJECT_WIDTH',{target_id:'anything'}).valid===false);
  chk('a degenerate model still measures between two literal points',
      createRuntimeMeasurement(s,'POINT_TO_POINT',
        {start:[0,0,0],end:[0,0,1]}).measurement.distance_m===1);
})();

console.log('\n──────────────────────────────────────────────');
console.log('MEASUREMENT: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
