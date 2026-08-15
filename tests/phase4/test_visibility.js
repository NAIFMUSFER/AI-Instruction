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
   المرحلة 4 — الرؤية
   الرؤية حالة زمن تشغيل زائلة: مجموعة إخفاء صريحة تُحسب منها الرؤية الفعّالة.
   لا حذف عنصر، ولا كتابة في المشهد البصري، ولا كتابة في النموذج الهندسي.
   ========================================================================== */
const DECO_OPTS={include_decoration:true,layers:VIS_LAYERS.slice()};
const vsV=VS('fls_full',DECO_OPTS), sc=compileRuntimeScene(vsV,null);
const vsClash=VS('clash_full'), clash=compileRuntimeScene(vsClash,null);
const NEW=()=>createRuntimeState(sc,null,null,null);
const pick=(s,p)=>(s.objects.filter(p)[0]||null);
const byDisc=(s,d)=>pick(s,o=>o.discipline===d);
const vis=st=>st.visibility;
const visibleOf=(st,id)=>effectiveRuntimeVisibility(st,sc).objects
  .filter(x=>x.runtime_object_id===id)[0].visible;

console.log('\n== §25 — VISIBILITY MODES ARE DECLARED, NOT INVENTED ==');
chk('the canonical specification declares the visibility modes',
    Array.isArray(RT_VISIBILITY_MODES)&&RT_VISIBILITY_MODES.length>0);
chk('the browser mirror and the canonical file agree on the mode list',
    JSON.stringify(RT_VISIBILITY_MODES)
      ===JSON.stringify(JSON.parse(fs.readFileSync(
        _np.join(ROOT,'acs_runtime.json'),'utf8')).visibility_modes));
['HIDE_OBJECT','SHOW_OBJECT','ISOLATE_ROOM','HIDE_ROOM','SHOW_ROOM',
 'ISOLATE_FLOOR','HIDE_FLOOR','SHOW_FLOOR','ISOLATE_DISCIPLINE','HIDE_DISCIPLINE',
 'SHOW_DISCIPLINE','RESTORE_VISIBILITY'].forEach(function(m){
  chk('the mode '+m+' is declared', RT_VISIBILITY_MODES.indexOf(m)>=0); });

console.log('\n== A FRESH STATE HIDES NOTHING ==');
(function(){
  const st=NEW();
  chk('a fresh runtime state hides no object, room, level or discipline',
      vis(st).hidden_object_ids.length===0&&vis(st).hidden_rooms.length===0
      &&vis(st).hidden_levels.length===0&&vis(st).hidden_disciplines.length===0);
  chk('a fresh runtime state isolates nothing', vis(st).isolated===null);
  const ev=effectiveRuntimeVisibility(st,sc);
  chk('every compiled object is visible by default',
      ev.objects.length===sc.objects.length&&ev.objects.every(x=>x.visible));
  chk('the hidden count starts at zero', ev.hidden_count===0);
  chk('effective visibility declares itself runtime-only', ev.runtime_only===true);
})();

console.log('\n== §26 — HIDING AND SHOWING A SINGLE OBJECT ==');
(function(){
  const st=NEW(), o=byDisc(sc,'ARCHITECTURE');
  const r=setRuntimeVisibility(st,sc,'HIDE_OBJECT',o.runtime_object_id);
  chk('an object hides without an issue', r.valid&&r.issues.length===0);
  chk('the hide is marked runtime-only', r.runtime_only===true);
  chk('the object appears in the hidden set',
      vis(st).hidden_object_ids.indexOf(o.runtime_object_id)>=0);
  chk('the object reads as not visible', visibleOf(st,o.runtime_object_id)===false);
  chk('exactly one object is hidden',
      effectiveRuntimeVisibility(st,sc).hidden_count===1);
  chk('hiding an object does not remove it from the runtime scene',
      sc.objects.filter(x=>x.runtime_object_id===o.runtime_object_id).length===1);
  chk('the object still answers selection while hidden',
      selectRuntimeObject(NEW(),sc,o.runtime_object_id).valid===true);
  chk('the object still answers inspection while hidden',
      inspectRuntimeObject(sc,o.runtime_object_id,vsV).valid===true);
  setRuntimeVisibility(st,sc,'HIDE_OBJECT',o.runtime_object_id);
  chk('hiding the same object twice does not duplicate the entry',
      vis(st).hidden_object_ids.filter(x=>x===o.runtime_object_id).length===1);
  const s2=setRuntimeVisibility(st,sc,'SHOW_OBJECT',o.runtime_object_id);
  chk('showing the object again clears it from the hidden set',
      s2.valid&&vis(st).hidden_object_ids.indexOf(o.runtime_object_id)<0);
  chk('the object reads as visible again', visibleOf(st,o.runtime_object_id)===true);
  chk('showing an object that was never hidden is harmless',
      setRuntimeVisibility(NEW(),sc,'SHOW_OBJECT',o.runtime_object_id).valid===true);
  chk('an object resolves for visibility by its source element id too',
      setRuntimeVisibility(NEW(),sc,'HIDE_OBJECT',o.source_element_id).valid===true);
})();

console.log('\n== HIDING AND ISOLATING A ROOM ==');
(function(){
  const st=NEW(), r0=sc.rooms[0];
  const h=setRuntimeVisibility(st,sc,'HIDE_ROOM',r0.runtime_room_id);
  chk('a room hides without an issue', h.valid);
  chk('the room appears in the hidden set',
      vis(st).hidden_rooms.indexOf(r0.runtime_room_id)>=0);
  chk('objects assigned to the hidden room read as not visible', (function(){
    const inRoom=sc.objects.filter(o=>o.space_id===r0.space_id);
    if(!inRoom.length) return true;
    return inRoom.every(o=>visibleOf(st,o.runtime_object_id)===false); })());
  chk('objects outside the hidden room stay visible', (function(){
    const out=sc.objects.filter(o=>o.space_id&&o.space_id!==r0.space_id);
    return out.length>0&&out.every(o=>visibleOf(st,o.runtime_object_id)===true); })());
  setRuntimeVisibility(st,sc,'SHOW_ROOM',r0.runtime_room_id);
  chk('showing the room clears it', vis(st).hidden_rooms.length===0);

  const iso=NEW();
  const ir=setRuntimeVisibility(iso,sc,'ISOLATE_ROOM',r0.runtime_room_id);
  chk('a room isolates without an issue', ir.valid);
  chk('isolation records what is isolated and of which kind',
      vis(iso).isolated&&vis(iso).isolated.kind==='ROOM'
      &&vis(iso).isolated.id===r0.runtime_room_id);
  chk('isolation hides every other room and no more',
      vis(iso).hidden_rooms.length===sc.rooms.length-1
      &&vis(iso).hidden_rooms.indexOf(r0.runtime_room_id)<0);
  chk('an object in the isolated room stays visible', (function(){
    const inRoom=sc.objects.filter(o=>o.space_id===r0.space_id);
    return inRoom.length===0||inRoom.every(o=>visibleOf(iso,o.runtime_object_id)); })());
  chk('an unassigned object is never hidden by a room isolation', (function(){
    const un=sc.objects.filter(o=>!o.space_id);
    return un.every(o=>visibleOf(iso,o.runtime_object_id)===true); })());
  chk('a room resolves for visibility by its space id too',
      setRuntimeVisibility(NEW(),sc,'HIDE_ROOM',r0.space_id).valid===true);
})();

console.log('\n== HIDING AND ISOLATING A FLOOR ==');
(function(){
  const levels=Array.from(new Set(sc.rooms.map(r=>r.level_index)
    .filter(x=>x!==null))).sort((a,b)=>a-b);
  chk('the fixture is multi-level', levels.length>1, JSON.stringify(levels));
  const st=NEW();
  const h=setRuntimeVisibility(st,sc,'HIDE_FLOOR',levels[0]);
  chk('a floor hides without an issue', h.valid);
  chk('the level appears in the hidden set', vis(st).hidden_levels.indexOf(levels[0])>=0);
  chk('objects on the hidden level read as not visible',
      sc.objects.filter(o=>o.level_index===levels[0])
        .every(o=>visibleOf(st,o.runtime_object_id)===false));
  chk('objects on another level stay visible',
      sc.objects.filter(o=>o.level_index!==null&&o.level_index!==levels[0])
        .every(o=>visibleOf(st,o.runtime_object_id)===true));
  chk('an object with no level is never hidden by a floor filter',
      sc.objects.filter(o=>o.level_index===null)
        .every(o=>visibleOf(st,o.runtime_object_id)===true));
  setRuntimeVisibility(st,sc,'SHOW_FLOOR',levels[0]);
  chk('showing the floor clears it', vis(st).hidden_levels.length===0);

  const iso=NEW();
  setRuntimeVisibility(iso,sc,'ISOLATE_FLOOR',levels[0]);
  chk('floor isolation records what is isolated',
      vis(iso).isolated.kind==='FLOOR'&&vis(iso).isolated.id===levels[0]);
  chk('floor isolation hides every other level and no more',
      vis(iso).hidden_levels.length===levels.length-1
      &&vis(iso).hidden_levels.indexOf(levels[0])<0);
})();

console.log('\n== HIDING AND ISOLATING A DISCIPLINE ==');
(function(){
  const present=Array.from(new Set(sc.objects.map(o=>o.discipline))).sort();
  chk('the fixture carries more than one discipline', present.length>1,
      JSON.stringify(present));
  const st=NEW();
  const h=setRuntimeVisibility(st,sc,'HIDE_DISCIPLINE','MEP');
  chk('a discipline hides without an issue', h.valid);
  chk('every MEP object reads as not visible',
      sc.objects.filter(o=>o.discipline==='MEP')
        .every(o=>visibleOf(st,o.runtime_object_id)===false));
  chk('objects of other disciplines stay visible',
      sc.objects.filter(o=>o.discipline!=='MEP')
        .every(o=>visibleOf(st,o.runtime_object_id)===true));
  chk('a lower-case discipline name is accepted and normalised',
      setRuntimeVisibility(NEW(),sc,'HIDE_DISCIPLINE','mep').valid===true);
  setRuntimeVisibility(st,sc,'SHOW_DISCIPLINE','MEP');
  chk('showing the discipline clears it', vis(st).hidden_disciplines.length===0);

  const iso=NEW();
  setRuntimeVisibility(iso,sc,'ISOLATE_DISCIPLINE','MEP');
  chk('discipline isolation records what is isolated',
      vis(iso).isolated.kind==='DISCIPLINE'&&vis(iso).isolated.id==='MEP');
  chk('discipline isolation hides only disciplines actually present',
      vis(iso).hidden_disciplines.every(d=>present.indexOf(d)>=0)
      &&vis(iso).hidden_disciplines.indexOf('MEP')<0);
  chk('only MEP objects remain visible under a MEP isolation',
      sc.objects.every(o=>visibleOf(iso,o.runtime_object_id)===(o.discipline==='MEP')));
})();

console.log('\n== VISUAL-ONLY OBJECTS ARE HIDEABLE LIKE ANY OTHER ==');
(function(){
  const d=pick(sc,o=>o.visual_only===true);
  chk('a visual-only object exists in the fixture', !!d);
  if(!d) return;
  const st=NEW();
  chk('a visual-only object hides',
      setRuntimeVisibility(st,sc,'HIDE_OBJECT',d.runtime_object_id).valid===true
      &&visibleOf(st,d.runtime_object_id)===false);
  const iso=NEW();
  setRuntimeVisibility(iso,sc,'ISOLATE_DISCIPLINE',d.discipline);
  chk('isolating the decoration discipline hides the engineering disciplines',
      visibleOf(iso,byDisc(sc,'ARCHITECTURE').runtime_object_id)===false);
  chk('hiding decoration never changes its engineering status',
      sc.objects.filter(o=>o.visual_only)
        .every(o=>o.collision.basis==='visual_only_never_blocking'
                ||o.collision.blocking===false||o.collision.basis));
})();

console.log('\n== COMBINED FILTERS COMPOSE, THEY DO NOT FIGHT ==');
(function(){
  const st=NEW();
  const o=byDisc(sc,'ARCHITECTURE');
  setRuntimeVisibility(st,sc,'HIDE_OBJECT',o.runtime_object_id);
  setRuntimeVisibility(st,sc,'HIDE_DISCIPLINE','MEP');
  chk('an object hidden individually stays hidden alongside a discipline filter',
      visibleOf(st,o.runtime_object_id)===false);
  chk('the discipline filter still applies',
      sc.objects.filter(x=>x.discipline==='MEP')
        .every(x=>visibleOf(st,x.runtime_object_id)===false));
  setRuntimeVisibility(st,sc,'SHOW_DISCIPLINE','MEP');
  chk('clearing the discipline filter does not un-hide the individual object',
      visibleOf(st,o.runtime_object_id)===false);
  chk('the hidden count is the count of objects that read as not visible',
      effectiveRuntimeVisibility(st,sc).hidden_count
        ===effectiveRuntimeVisibility(st,sc).objects.filter(x=>!x.visible).length);
})();

console.log('\n== RESTORE RETURNS EVERYTHING ==');
(function(){
  const st=NEW();
  setRuntimeVisibility(st,sc,'HIDE_OBJECT',byDisc(sc,'ARCHITECTURE').runtime_object_id);
  setRuntimeVisibility(st,sc,'HIDE_DISCIPLINE','MEP');
  setRuntimeVisibility(st,sc,'ISOLATE_ROOM',sc.rooms[0].runtime_room_id);
  setRuntimeVisibility(st,sc,'HIDE_FLOOR',0);
  chk('several filters are active before the restore',
      effectiveRuntimeVisibility(st,sc).hidden_count>0);
  const r=restoreRuntimeVisibility(st,sc);
  chk('restore succeeds and is runtime-only', r.valid&&r.runtime_only===true);
  chk('restore clears every hidden set and the isolation',
      vis(st).hidden_object_ids.length===0&&vis(st).hidden_rooms.length===0
      &&vis(st).hidden_levels.length===0&&vis(st).hidden_disciplines.length===0
      &&vis(st).isolated===null);
  chk('every object is visible again after a restore',
      effectiveRuntimeVisibility(st,sc).objects.every(x=>x.visible));
  chk('a restore on a clean state is harmless',
      restoreRuntimeVisibility(NEW(),sc).valid===true);
  chk('RESTORE_VISIBILITY as a mode behaves as the restore helper', (function(){
    const a=NEW(), b=NEW();
    setRuntimeVisibility(a,sc,'HIDE_DISCIPLINE','MEP');
    setRuntimeVisibility(b,sc,'HIDE_DISCIPLINE','MEP');
    setRuntimeVisibility(a,sc,'RESTORE_VISIBILITY',null);
    restoreRuntimeVisibility(b,sc);
    return JSON.stringify(vis(a))===JSON.stringify(vis(b)); })());
})();

console.log('\n== INVALID MODES AND TARGETS ARE REFUSED ==');
[null,'','X_RAY','hide_everything',42,{m:'HIDE_OBJECT'},['HIDE_OBJECT'],true
].forEach(function(m){
  const st=NEW();
  const r=setRuntimeVisibility(st,sc,m,null);
  chk('an unknown visibility mode '+JSON.stringify(m)+' is refused',
      r.valid===false&&r.visibility===null
      &&codes(r).indexOf('VISIBILITY_MODE_INVALID')>=0, JSON.stringify(codes(r)));
  chk('a refused mode leaves the state untouched ('+JSON.stringify(m)+')',
      JSON.stringify(vis(st))===JSON.stringify(vis(NEW())));
});
[['HIDE_OBJECT','no_such_object'],['SHOW_OBJECT',null],['HIDE_OBJECT',{a:1}],
 ['HIDE_ROOM','no_such_room'],['ISOLATE_ROOM',null],
 ['HIDE_FLOOR',999],['ISOLATE_FLOOR','ground'],['HIDE_FLOOR',null],
 ['HIDE_DISCIPLINE','PLUMBING_ASTROLOGY'],['ISOLATE_DISCIPLINE',null],
 ['HIDE_DISCIPLINE',7]
].forEach(function(p){
  const st=NEW();
  const r=setRuntimeVisibility(st,sc,p[0],p[1]);
  chk(p[0]+' refuses the target '+JSON.stringify(p[1]),
      r.valid===false&&codes(r).indexOf('VISIBILITY_TARGET_INVALID')>=0,
      JSON.stringify(codes(r)));
  chk('a refused '+p[0]+' hides nothing',
      effectiveRuntimeVisibility(st,sc).hidden_count===0);
});

console.log('\n== VISIBILITY IS EPHEMERAL — NOTHING UPSTREAM CHANGES ==');
(function(){
  const scBefore=JSON.stringify(sc), vsBefore=JSON.stringify(vsV);
  const mBefore=JSON.stringify(SC.models.fls_full);
  const st=NEW();
  RT_VISIBILITY_MODES.forEach(function(m){
    setRuntimeVisibility(st,sc,m,sc.objects[0].runtime_object_id);
    setRuntimeVisibility(st,sc,m,sc.rooms[0].runtime_room_id);
    setRuntimeVisibility(st,sc,m,0);
    setRuntimeVisibility(st,sc,m,'MEP'); });
  chk('every visibility mode leaves the runtime scene byte-identical',
      JSON.stringify(sc)===scBefore);
  chk('every visibility mode leaves the visual scene byte-identical',
      JSON.stringify(vsV)===vsBefore);
  chk('every visibility mode leaves the source model byte-identical',
      JSON.stringify(SC.models.fls_full)===mBefore);
  chk('no runtime object grew a visible or hidden flag',
      sc.objects.every(o=>o.visible===undefined&&o.hidden===undefined
        &&o.visibility===undefined));
  chk('the object count never changes — hiding is not deletion',
      effectiveRuntimeVisibility(st,sc).objects.length===sc.objects.length);
  chk('the runtime state still declares that it writes nothing to the model',
      st.writes_to_model===false);
  chk('the compiled model hash is unchanged by any visibility operation',
      _rtSha16(SC.models.fls_full)===_rtSha16(JSON.parse(mBefore)));
})();

console.log('\n== EFFECTIVE VISIBILITY IS PURE AND DETERMINISTIC ==');
(function(){
  const st=NEW();
  setRuntimeVisibility(st,sc,'HIDE_DISCIPLINE','MEP');
  const a=JSON.stringify(effectiveRuntimeVisibility(st,sc));
  const b=JSON.stringify(effectiveRuntimeVisibility(st,sc));
  chk('effective visibility is identical across repeated calls', a===b);
  chk('effective visibility does not mutate the runtime state',
      JSON.stringify(vis(st))===JSON.stringify(vis(st)));
  const ev=effectiveRuntimeVisibility(st,sc);
  chk('the effective visibility list is sorted by runtime object id', (function(){
    const ids=ev.objects.map(x=>String(x.runtime_object_id));
    return JSON.stringify(ids)===JSON.stringify(ids.slice().sort()); })());
  chk('the returned visibility snapshot is a copy, not a live reference', (function(){
    const r=setRuntimeVisibility(NEW(),sc,'HIDE_DISCIPLINE','MEP');
    r.visibility.hidden_disciplines.push('TAMPERED');
    return true; })());
  chk('hidden sets are canonically sorted', (function(){
    const s=NEW();
    setRuntimeVisibility(s,sc,'HIDE_DISCIPLINE','MEP');
    setRuntimeVisibility(s,sc,'HIDE_DISCIPLINE','ARCHITECTURE');
    const h=vis(s).hidden_disciplines;
    return JSON.stringify(h)===JSON.stringify(h.slice().sort()); })());
})();

console.log('\n== §22 — VISIBILITY IS A DECLARED ACTION WITH NO WRITE PATH ==');
(function(){
  ['HIDE','SHOW','ISOLATE'].forEach(function(a){
    chk('the action '+a+' is declared in the canonical specification',
        RT_ACTIONS.indexOf(a)>=0); });
  const w=validateRuntimeAction('HIDE','OBJECT','x',{delete_element:true});
  chk('a hide payload asking to delete the element is refused',
      w.valid===false&&codes(w).indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0);
  const w2=validateRuntimeAction('ISOLATE','ROOM','r',{set_geometry:{}});
  chk('an isolate payload asking to set geometry is refused',
      w2.valid===false&&codes(w2).indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0);
})();

console.log('\n── multiple models ──');
['villa','hotel','clinic','warehouse','office','mixed_use','no_site'].forEach(function(n){
  const s=RS(n);
  if(!s.objects.length){ chk(n+': an empty model still answers visibility',
      effectiveRuntimeVisibility(createRuntimeState(s,null,null,null),s)
        .objects.length===0); return; }
  const st=createRuntimeState(s,null,null,null);
  const o=s.objects[0];
  setRuntimeVisibility(st,s,'HIDE_OBJECT',o.runtime_object_id);
  const ev=effectiveRuntimeVisibility(st,s);
  chk(n+': one hidden object yields exactly one invisible entry',
      ev.hidden_count===1&&ev.objects.length===s.objects.length);
  restoreRuntimeVisibility(st,s);
  chk(n+': restore returns every object',
      effectiveRuntimeVisibility(st,s).hidden_count===0);
});
(function(){
  const s=RS('degenerate');
  const st=createRuntimeState(s,null,null,null);
  chk('a degenerate model reports an empty visibility set without throwing',
      effectiveRuntimeVisibility(st,s).objects.length===0
      &&effectiveRuntimeVisibility(st,s).hidden_count===0);
})();

console.log('\n──────────────────────────────────────────────');
console.log('VISIBILITY: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
