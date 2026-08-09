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

const villa=RS('villa'), clash=RS('clash_full');
const lvl0=(s)=>s.walkability.surfaces.filter(x=>x.level_index===0)[0].elevation_m;
const walkState=(s)=>createRuntimeState(s,'WALK');
/* نقطتان على جانبَي عائق، عموديتان على وجهه الرقيق */
function across(bounds,y,d){
  const cx=(bounds[0]+bounds[3])/2, cz=(bounds[2]+bounds[5])/2;
  const thinX=(bounds[3]-bounds[0])<(bounds[5]-bounds[2]);
  return thinX?[[cx-d,y,cz],[cx+d,y,cz]]:[[cx,y,cz-d],[cx,y,cz+d]]; }

console.log('\n== PLAYER CAPSULE ==');
chk('the default capsule is valid', validateRuntimeCapsule(null).valid);
chk('the default capsule comes from the specification', (function(){
  const c=validateRuntimeCapsule(null).capsule;
  return c.radius_m===RT_CAPSULE_DEFAULTS.radius_m
    &&c.height_m===RT_CAPSULE_DEFAULTS.height_m
    &&c.eye_height_m===RT_CAPSULE_DEFAULTS.eye_height_m; })());
chk('the player is never a zero-volume point',
    RT_CAPSULE_DEFAULTS.radius_m>0&&RT_CAPSULE_DEFAULTS.height_m>0);
[['negative radius',{radius_m:-0.3}],['zero radius',{radius_m:0}],
 ['negative height',{height_m:-1.75}],['zero height',{height_m:0}],
 ['eye height above the capsule',{eye_height_m:2.5}],
 ['zero eye height',{eye_height_m:0}],['negative eye height',{eye_height_m:-1}],
 ['NaN radius',{radius_m:NaN}],['NaN height',{height_m:NaN}],
 ['NaN eye height',{eye_height_m:NaN}],
 ['Infinity radius',{radius_m:Infinity}],['Infinity height',{height_m:Infinity}],
 ['-Infinity height',{height_m:-Infinity}],
 ['height not exceeding twice the radius',{radius_m:1.0,height_m:1.9}],
 ['radius beyond the declared limit',{radius_m:9}],
 ['height beyond the declared limit',{height_m:9}]].forEach(pair=>{
  const c=Object.assign({},RT_CAPSULE_DEFAULTS,pair[1]);
  chk('capsule with '+pair[0]+' is rejected',
      codes(validateRuntimeCapsule(c)).indexOf('PLAYER_CAPSULE_INVALID')>=0,
      JSON.stringify(codes(validateRuntimeCapsule(c)))); });
chk('a non-object capsule is rejected',
    codes(validateRuntimeCapsule('tall')).indexOf('PLAYER_CAPSULE_INVALID')>=0);
chk('a movement query with an invalid capsule is refused', (function(){
  const s=walkState(villa); s.player_capsule={radius_m:-1,height_m:1.75,eye_height_m:1.6};
  const r=runtimeMoveQuery(villa,s,[0,0,0],[1,0,0]);
  return r.allowed===false&&codes(r).indexOf('PLAYER_CAPSULE_INVALID')>=0; })());

console.log('\n== SPATIAL BROAD PHASE ==');
chk('the index is built from obstacles and surfaces',
    villa.spatial_index.entries===villa.walkability.obstacles.length
      +villa.walkability.surfaces.length);
chk('a local query resolves far fewer candidates than the total', (function(){
  const q=queryRuntimeSpatialIndex(villa,[1,0,1,2,2,2]);
  return q.candidate_count<q.total_entries&&q.full_scan===false; })());
chk('a query never claims a full scan',
    queryRuntimeSpatialIndex(villa,[0,0,0,1,1,1]).full_scan===false);
chk('candidates are returned in a deterministic order',
    JSON.stringify(queryRuntimeSpatialIndex(villa,[0,0,0,8,4,8]).candidate_ids)===
    JSON.stringify(queryRuntimeSpatialIndex(villa,[0,0,0,8,4,8]).candidate_ids));
chk('an oversized entry is compared against everything rather than lost',
    typeof villa.spatial_index.oversized==='number'
    &&Array.isArray(villa.spatial_index.oversized_ids));
chk('a query far outside the building returns no candidates',
    queryRuntimeSpatialIndex(villa,[9000,0,9000,9001,1,9001]).candidate_count
      ===villa.spatial_index.oversized);

console.log('\n== COLLISION: WALLS BLOCK ==');
const doorHosts={};
villa.walkability.portals.forEach(p=>{doorHosts[p.host_wall_id]=true;});
const plainWall=villa.walkability.obstacles.filter(o=>o.kind==='WALL'
  &&!doorHosts[o.source_element_id]&&o.level_index===0)[0];
chk('a fixture with a doorless wall exists for the test', !!plainWall);
if(plainWall){
  const pts=across(plainWall.bounds,lvl0(villa),1.0);
  const r=runtimeMoveQuery(villa,walkState(villa),pts[0],pts[1]);
  chk('the player cannot walk through a wall',
      r.allowed===false&&r.blocked_kind==='WALL');
  chk('the blocking obstacle is named', r.blocked_by===plainWall.obstacle_id);
  chk('the query reports its candidate count', typeof r.candidate_count==='number'); }

console.log('\n== COLLISION: STRUCTURE BLOCKS ==');
const col=clash.walkability.obstacles.filter(o=>o.kind==='COLUMN')[0];
chk('the clash fixture contains a structural column', !!col);
if(col){
  /* عمود المنشأ قد يجاور جداراً، فيمنع الجدار أولاً. نثبت أنّ العمود نفسه
     مانع بفحص تقاطع الكبسولة عند مركزه: التحقّق يعدّد كل العوائق المتقاطعة. */
  const cx=(col.bounds[0]+col.bounds[3])/2, cz=(col.bounds[2]+col.bounds[5])/2;
  /* المنسوب يؤخذ من قاعدة العمود نفسه، لا من ترتيب قائمة الأسطح */
  const y=col.bounds[1];
  const sp=validateRuntimeSpawn(clash,[cx,y,cz],null,null);
  chk('the player cannot stand inside a structural column',
      sp.valid===false&&sp.issues.some(i=>i.code==='SPAWN_INSIDE_OBSTACLE'
        &&i.subject===col.obstacle_id));
  const pts=across(col.bounds,y,1.5);
  const r=runtimeMoveQuery(clash,walkState(clash),pts[0],pts[1]);
  chk('a movement through the column volume is blocked', r.allowed===false);
  chk('a column is a declared blocking obstacle',
      RT_COLLISION_POLICY.COLUMN.blocking===true&&col.blocking===true); }
const beam=clash.walkability.obstacles.filter(o=>o.kind==='BEAM')[0];
chk('a beam is a declared blocking obstacle when modelled',
    !beam||RT_COLLISION_POLICY.BEAM.blocking===true);

console.log('\n== COLLISION: FLOOR SUPPORT ==');
chk('a destination over a walkable surface is supported', (function(){
  const sp=villa.defaults.spawn.position;
  return runtimeMoveQuery(villa,walkState(villa),sp,sp).allowed===true; })());
chk('a destination with no walkable surface is refused in WALK', (function(){
  /* مشهد صغير بلا جدران يعزل فرع الدعم وحده: لا عائق يتدخّل في النتيجة */
  const bare=compileRuntimeScene({scene_id:'bare',model_hash:null,building_id:'bld_0',
    transform:{position:{x:0,z:0},rotation_deg:0},objects:[],
    spaces_index:[{id:'r@0',space_id:'r',name:'r',rect:[0,0,4,4],level_index:0,
      area_m2:16,_elev:0}]});
  const r=runtimeMoveQuery(bare,createRuntimeState(bare,'WALK'),[2,0,2],[50,0,50]);
  return r.allowed===false&&r.blocked_by===null&&/no walkable surface/.test(r.reason); })());
chk('FLY does not require a walkable surface', (function(){
  const sp=villa.defaults.spawn.position;
  return runtimeMoveQuery(villa,createRuntimeState(villa,'FLY'),sp,[900,20,900])
    .allowed===true; })());
chk('FLY reports that collision is disabled by its own contract',
    /collision disabled by contract/.test(
      runtimeMoveQuery(villa,createRuntimeState(villa,'FLY'),[0,0,0],[50,0,50]).reason));

console.log('\n== COLLISION: ROTATED GEOMETRY ==');
const rot=compileRuntimeScene(compileVisualScene(C(SC.models.villa),'bld_0',{x:-6,z:4},45,
  {mode:'ENGINEERING',at:AT}));
chk('a rotated building yields the same obstacle count',
    rot.walkability.obstacles.length===villa.walkability.obstacles.length);
chk('rotated obstacles carry a non-zero yaw',
    rot.walkability.obstacles.some(o=>Math.abs(o.obb.yaw)>1e-6));
chk('a rotated wall still blocks along its own normal', (function(){
  const hosts={}; rot.walkability.portals.forEach(p=>{hosts[p.host_wall_id]=true;});
  const w=rot.walkability.obstacles.filter(o=>o.kind==='WALL'&&!hosts[o.source_element_id]
    &&o.level_index===0)[0];
  if(!w) return false;
  const c=w.obb, n=[Math.sin(c.yaw),Math.cos(c.yaw)];   // ناظم الوجه الرقيق
  const y=rot.walkability.surfaces.filter(s=>s.level_index===0)[0].elevation_m;
  const a=[c.cx-n[0]*1.0,y,c.cz-n[1]*1.0], b=[c.cx+n[0]*1.0,y,c.cz+n[1]*1.0];
  const r=runtimeMoveQuery(rot,walkState(rot),a,b);
  return r.allowed===false&&r.blocked_kind==='WALL'; })());
chk('the oriented test is not a plain axis-aligned test', (function(){
  /* صندوق طويل مدار 45° وصندوق محوري: صندوقاهما المحاذيان يتقاطعان بينما
     اختبار المحور الفاصل يفصلهما — لو كان الفحص محاذياً لأخطأ هنا. */
  const a=_rtObb(0,0,0,6,2,0.2,Math.PI/4);
  const b=_rtObb(-2.25,0,-1.5,0.4,2,0.4,0);
  return _rtAabbOverlap(_rtAabbOf(a),_rtAabbOf(b))===true
    &&_rtObbOverlap(a,b)===false; })());

console.log('\n== DECORATION COLLISION IS EXPLICIT ==');
const deco=compileRuntimeScene(VS('villa_full',{include_decoration:true,
  layers:VIS_LAYERS.slice()}));
const decoBlock=compileRuntimeScene(VS('villa_full',{include_decoration:true,
  layers:VIS_LAYERS.slice()}),{decoration_collision:'BLOCKING'});
chk('the fixture actually contains decoration',
    deco.objects.filter(o=>o.discipline==='FURNITURE').length>0);
chk('decoration is non-blocking by default',
    deco.objects.filter(o=>o.discipline==='FURNITURE')
      .every(o=>o.collision.blocking===false));
chk('decoration becomes blocking only when explicitly declared',
    decoBlock.objects.filter(o=>o.discipline==='FURNITURE')
      .every(o=>o.collision.blocking===true));
chk('the declared decoration policy is recorded on the scene',
    deco.defaults.decoration_collision==='NON_BLOCKING'
    &&decoBlock.defaults.decoration_collision==='BLOCKING');
chk('an unknown decoration policy is refused and falls back', (function(){
  const s=compileRuntimeScene(VS('villa_full'),{decoration_collision:'SQUISHY'});
  return codes(s).indexOf('RUNTIME_CONFIG_INVALID')>=0
    &&s.defaults.decoration_collision==='NON_BLOCKING'; })());
chk('a visual-only non-furniture object is never blocking',
    deco.objects.filter(o=>o.visual_only&&o.discipline!=='FURNITURE')
      .every(o=>o.collision.blocking===false));
chk('decoration never becomes a walkable engineering surface',
    decoBlock.objects.filter(o=>o.discipline==='FURNITURE')
      .every(o=>o.collision.walkable===false));
chk('the collision basis is recorded for every object',
    villa.objects.every(o=>!!o.collision.basis));

console.log('\n== WALKABLE SURFACES AND OBSTACLES ==');
chk('walkable surfaces derive from canonical spaces',
    villa.walkability.surfaces.every(s=>s.basis==='space_rectangle'&&!!s.source_element_id));
chk('every surface carries its level and elevation',
    villa.walkability.surfaces.every(s=>s.level_index!==undefined
      &&typeof s.elevation_m==='number'));
chk('a surface records its supporting slab or an explicit null',
    villa.walkability.surfaces.every(s=>s.support_element_id===null
      ||typeof s.support_element_id==='string'));
chk('obstacles carry oriented bounds and a blocking flag',
    villa.walkability.obstacles.every(o=>o.blocking===true&&o.bounds.length===6
      &&typeof o.obb.yaw==='number'));
chk('an invalid space rectangle is refused', (function(){
  const adv=SC.adversarial.filter(a=>a[0]==='bad_space_rect')[0][1];
  return codes(compileRuntimeScene(LIB.hydrate(adv)))
    .indexOf('WALKABLE_SURFACE_INVALID')>=0; })());
chk('a space with no finite elevation is refused', (function(){
  const adv=SC.adversarial.filter(a=>a[0]==='space_without_elevation')[0][1];
  return codes(compileRuntimeScene(LIB.hydrate(adv)))
    .indexOf('WALKABLE_SURFACE_INVALID')>=0; })());

console.log('\n== THE BROAD PHASE IS BOUNDED, AND SAYS SO WHEN IT FALLS BACK ==');
(function(){
  const s=RS('villa');
  const cap=ACS_RUNTIME_SPEC.spatial_index.max_cells_per_entry;
  const bound=ACS_RUNTIME_SPEC.spatial_index.max_abs_coordinate_m;
  chk('the specification declares a cell cap and a coordinate bound',
      Number.isFinite(cap)&&cap>0&&Number.isFinite(bound)&&bound>0);
  const near=queryRuntimeSpatialIndex(s,[0,0,0,4,3,4]);
  chk('a local query stays on the cell path and reports no full scan',
      near.full_scan===false&&near.scanned_cells>0);
  chk('a local query narrows the candidate set below the entry count',
      near.candidate_count<near.total_entries, near.candidate_count+'/'+near.total_entries);
  const wide=queryRuntimeSpatialIndex(s,[-1e9,-1e9,-1e9,1e9,1e9,1e9]);
  chk('a query wider than the declared cap declares a full scan instead of counting cells',
      wide.full_scan===true&&wide.scanned_cells===0);
  chk('the declared full scan still returns only real identifiers',
      wide.candidate_ids.every(id=>
        s.walkability.obstacles.some(o=>o.obstacle_id===id)
        ||s.walkability.surfaces.some(x=>x.surface_id===id)));
  chk('the declared full scan never reports more candidates than there are entries',
      wide.candidate_count<=wide.total_entries);
  const huge=queryRuntimeSpatialIndex(s,[1e308,1e308,1e308,1e308,1e308,1e308]);
  chk('a coordinate beyond the declared bound is refused for indexing, not expanded',
      huge.full_scan===true&&huge.scanned_cells===0);
  [null,undefined,'',[],[0,0,0],[NaN,0,0,1,1,1],[0,0,0,Infinity,1,1]
  ].forEach(function(a){
    const q=queryRuntimeSpatialIndex(s,a);
    chk('a malformed query box '+JSON.stringify(a)+' falls back to a declared full scan',
        q.full_scan===true&&q.scanned_cells===0);
  });
  chk('a bounded sweep across the whole villa completes and reports finitely', (function(){
    const st=createRuntimeState(s,null,null,null);
    const r=runtimeMoveQuery(s,st,[1e9,1e9,1e9],[-1e9,-1e9,-1e9]);
    return !!r&&typeof r==='object'; })());
})();

console.log('\n──────────────────────────────────────────────');
console.log('COLLISION: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
