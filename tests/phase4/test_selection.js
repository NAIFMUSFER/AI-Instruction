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
   المرحلة 4 — التحديد والفحص
   التحديد حالة زمن تشغيل زائلة. الفحص يعرض ما ينصّ عليه المصدر فقط،
   والغائب يُعلَن NOT_SPECIFIED ولا يُستبدَل بقيمة تبدو حقيقة هندسية.
   ========================================================================== */
/* الديكور لا يظهر إلا بطلب صريح، والانضباطات موزّعة على تجهيزات مختلفة،
   فيُختار لكل انضباط المشهد الذي يثبت وجوده فعلاً بدل افتراضه. */
const DECO_OPTS={include_decoration:true,layers:VIS_LAYERS.slice()};
const vsV=VS('fls_full',DECO_OPTS), villa=compileRuntimeScene(vsV,null);
const vsClash=VS('clash_full'), clash=compileRuntimeScene(vsClash,null);
const stV=createRuntimeState(villa,null,null,null);
const pick=(sc,pred)=>(sc.objects.filter(pred)[0]||null);
const byDisc=(sc,d)=>pick(sc,o=>o.discipline===d);
const SRC={ARCHITECTURE:[villa,vsV],MEP:[villa,vsV],FLS:[villa,vsV],
           STRUCTURE:[clash,vsClash],FURNITURE:[villa,vsV]};

console.log('\n== §23 — SELECTION ACROSS EVERY DISCIPLINE ==');
['ARCHITECTURE','STRUCTURE','MEP','FLS','FURNITURE'].forEach(function(d){
  const sc=SRC[d][0], o=byDisc(sc,d);
  chk('an object of discipline '+d+' exists in the fixtures', !!o);
  if(!o) return;
  const st=createRuntimeState(sc,null,null,null);
  const r=selectRuntimeObject(st,sc,o.runtime_object_id);
  chk(d+' object is selectable', r.valid&&!!r.selection&&r.issues.length===0);
  chk(d+' selection reports the runtime id, the visual id and the source id',
      r.selection.runtime_object_id===o.runtime_object_id
      &&r.selection.visual_object_id===o.visual_object_id
      &&r.selection.source_element_id===o.source_element_id);
  chk(d+' selection is marked runtime-only', r.runtime_only===true);
  chk(d+' selection reports the discipline and kind it was compiled with',
      r.selection.discipline===d&&r.selection.kind===o.kind);
});

const deco=pick(villa,o=>o.visual_only===true);
chk('a visual-only object exists in the fixture', !!deco);
if(deco){
  const st=createRuntimeState(villa,null,null,null);
  const r=selectRuntimeObject(st,villa,deco.runtime_object_id);
  chk('a visual-only object is selectable', r.valid&&!!r.selection);
  chk('a visual-only selection declares itself visual-only, never engineering',
      r.selection.visual_only===true);
  chk('an engineering object is not marked visual-only',
      selectRuntimeObject(createRuntimeState(villa,null,null,null),villa,
        byDisc(villa,'ARCHITECTURE').runtime_object_id).selection.visual_only===false);
}

console.log('\n== SELECTION BY ANY OF THE THREE IDENTITIES ==');
const anyO=byDisc(villa,'ARCHITECTURE');
[['runtime id',anyO.runtime_object_id],['visual id',anyO.visual_object_id],
 ['source element id',anyO.source_element_id]].forEach(function(p){
  if(!p[1]) { chk('the fixture object exposes a '+p[0], false); return; }
  const st=createRuntimeState(villa,null,null,null);
  const r=selectRuntimeObject(st,villa,p[1]);
  chk('an object resolves by its '+p[0],
      r.valid&&r.selection.runtime_object_id===anyO.runtime_object_id);
});

console.log('\n== SELECTION STATE LIVES IN RUNTIME STATE ALONE ==');
(function(){
  const st=createRuntimeState(villa,null,null,null);
  chk('a fresh runtime state carries no selection', st.selection===null);
  const before=JSON.stringify(villa);
  const mHash=JSON.stringify(SC.models.fls_full);
  selectRuntimeObject(st,villa,anyO.runtime_object_id);
  chk('the selection is recorded in runtime state',
      st.selection&&st.selection.runtime_object_id===anyO.runtime_object_id);
  chk('the runtime scene is byte-identical after a selection',
      JSON.stringify(villa)===before);
  chk('the source model is byte-identical after a selection',
      JSON.stringify(SC.models.fls_full)===mHash);
  chk('no runtime object carries a selected flag',
      villa.objects.every(o=>o.selected===undefined&&o.is_selected===undefined));
  const r2=selectRuntimeObject(st,villa,byDisc(villa,'MEP').runtime_object_id);
  chk('selecting a second object replaces the first — selection is single',
      st.selection.runtime_object_id===r2.selection.runtime_object_id);
  const d=deselectRuntimeObject(st);
  chk('deselection clears the selection', st.selection===null&&d.selection===null);
  chk('deselection is marked runtime-only', d.runtime_only===true);
  chk('the returned selection is a copy, not a live reference', (function(){
    const st2=createRuntimeState(villa,null,null,null);
    const rr=selectRuntimeObject(st2,villa,anyO.runtime_object_id);
    rr.selection.runtime_object_id='TAMPERED';
    return st2.selection.runtime_object_id===anyO.runtime_object_id; })());
})();

console.log('\n== INVALID SELECTION TARGETS ARE REFUSED ==');
[['an unknown identifier','no_such_object_id'],
 ['an empty string',''],
 ['a null target',null],
 ['a numeric target',12345],
 ['an object target',{id:'x'}],
 ['an array target',['a']],
 ['a boolean target',true],
 ['a room identifier used as an object',villa.rooms[0].runtime_room_id],
 ['a portal identifier used as an object',villa.walkability.portals[0].portal_id]
].forEach(function(p){
  const st=createRuntimeState(villa,null,null,null);
  const r=selectRuntimeObject(st,villa,p[1]);
  chk('selection refuses '+p[0],
      r.valid===false&&r.selection===null
      &&codes(r).indexOf('INTERACTION_TARGET_INVALID')>=0, JSON.stringify(codes(r)));
  chk('a refused selection leaves runtime state untouched ('+p[0]+')',
      st.selection===null);
});

console.log('\n== §24 — INSPECTION SHOWS SOURCE-BACKED VALUES ONLY ==');
(function(){
  const o=byDisc(villa,'ARCHITECTURE');
  const r=inspectRuntimeObject(villa,o.runtime_object_id,vsV);
  const i=r.inspection;
  chk('inspection succeeds for a source-backed object', r.valid&&!!i);
  chk('inspection is marked runtime-only', r.runtime_only===true);
  chk('inspection names the source element, not just the runtime id',
      i.source_element_id===o.source_element_id&&i.source_element_id!==RT_NOT_SPECIFIED);
  chk('inspection declares the object source-backed', i.source_backed===true);
  chk('inspected dimensions equal the compiled runtime box exactly',
      i.dimensions_m.width===_rtQ(o.obb.hx*2)
      &&i.dimensions_m.height===_rtQ(o.obb.hy*2)
      &&i.dimensions_m.depth===_rtQ(o.obb.hz*2));
  chk('inspected position equals the compiled runtime centre exactly',
      i.position[0]===o.obb.cx&&i.position[1]===o.obb.cy&&i.position[2]===o.obb.cz);
  chk('inspected orientation equals the compiled yaw exactly',
      i.orientation_rad===o.obb.yaw);
  chk('every inspected numeric value is finite',
      i.position.concat([i.orientation_rad,i.dimensions_m.width,
        i.dimensions_m.height,i.dimensions_m.depth]).every(Number.isFinite));
  chk('inspection reports the collision policy and its basis',
      !!i.collision&&typeof i.collision.blocking==='boolean'&&!!i.collision.basis);
  chk('inspection states that an absent property is NOT_SPECIFIED',
      /NOT_SPECIFIED/.test(String(i.note)));
})();

console.log('\n== ABSENT PROPERTIES ARE NOT_SPECIFIED, NEVER INVENTED ==');
(function(){
  const o=byDisc(villa,'ARCHITECTURE');
  const stripped=C(vsV);
  stripped.objects.forEach(function(v){
    delete v.material; delete v.material_provenance; delete v.asset_id;
    delete v.exposure; delete v.host_wall_id; });
  const r=inspectRuntimeObject(villa,o.runtime_object_id,stripped);
  const i=r.inspection;
  ['material','material_provenance','asset_id','exposure','host_wall_id'].forEach(function(k){
    chk('an absent '+k+' is reported NOT_SPECIFIED', i[k]===RT_NOT_SPECIFIED); });
  chk('no absent property is replaced by null, zero, an empty string or false',
      ['material','material_provenance','asset_id','exposure','host_wall_id']
        .every(k=>i[k]!==null&&i[k]!==0&&i[k]!==''&&i[k]!==false));
  const r2=inspectRuntimeObject(villa,o.runtime_object_id,null);
  chk('inspection without a visual scene still answers, reporting NOT_SPECIFIED',
      r2.valid&&r2.inspection.material===RT_NOT_SPECIFIED);
  chk('inspection without a visual scene keeps the geometry it does own',
      r2.inspection.position[0]===o.obb.cx
      &&r2.inspection.dimensions_m.width===_rtQ(o.obb.hx*2));
})();

console.log('\n== INSPECTION INVENTS NO ENGINEERING DATA ==');
(function(){
  const o=byDisc(villa,'ARCHITECTURE');
  const i=inspectRuntimeObject(villa,o.runtime_object_id,vsV).inspection;
  const NOTE_KEYS=['note','notes','detail','reason','basis','disclaimer','derivation'];
  const FORBIDDEN=new RegExp(['fire_rating','fire_resistance','u_value','r_value',
    'load_bearing','capacity_kn','\\bsbc\\b','\\bibc\\b','nfpa','\\bada\\b','\\baci\\b',
    'asce','aisc','eurocode','\\bnec\\b','\\biec\\b','ashrae','occupancy_load',
    'egress_width','compliance','code_check','approved','certified'].join('|'),'i');
  const scan=(root)=>{ const hits=[];
    const walk=(v,p)=>{ if(Array.isArray(v)) return v.forEach((x,n)=>walk(x,p+'['+n+']'));
      if(v&&typeof v==='object') return Object.keys(v).forEach(k=>{
        if(NOTE_KEYS.indexOf(k)>=0) return;
        if(FORBIDDEN.test(k)) hits.push(p+'.'+k);
        if(typeof v[k]==='string'&&FORBIDDEN.test(v[k])) hits.push(p+'.'+k+'='+v[k]);
        walk(v[k],p+'.'+k); }); };
    walk(root,''); return hits; };
  const hits=villa.objects.map(x=>scan(inspectRuntimeObject(villa,x.runtime_object_id,vsV)
      .inspection)).reduce((a,b)=>a.concat(b),[]);
  if(hits.length) console.log('     hits:',JSON.stringify(hits.slice(0,4)));
  chk('no inspection anywhere invents a rating, a load or a code value',
      hits.length===0);
  chk('the forbidden pattern is not vacuous — it catches a planted value',
      scan({fire_rating:'2HR'}).length>0&&scan({compliance:'PASS'}).length>0);
  chk('inspection denies being a compliance statement in its own words',
      /never replaced by a plausible default/.test(String(i.note)));
})();

console.log('\n== A VISUAL-ONLY OBJECT IS NEVER PRESENTED AS ENGINEERING ==');
(function(){
  if(!deco){ chk('a visual-only object exists to inspect', false); return; }
  const i=inspectRuntimeObject(villa,deco.runtime_object_id,vsV).inspection;
  chk('a visual-only inspection declares visual_only', i.visual_only===true);
  chk('a visual-only inspection is not source-backed', i.source_backed===false);
  chk('a visual-only inspection reports NOT_SPECIFIED as its engineering source',
      i.engineering_source===RT_NOT_SPECIFIED);
  chk('a visual-only inspection is flagged visual metadata only',
      i.visual_metadata_only===true);
  const e=byDisc(villa,'ARCHITECTURE');
  const ei=inspectRuntimeObject(villa,e.runtime_object_id,vsV).inspection;
  chk('an engineering object is not flagged visual metadata only',
      ei.visual_metadata_only===undefined&&ei.source_backed===true);
})();

console.log('\n== ROOMS ARE INSPECTABLE AS ROOMS ==');
(function(){
  const r0=villa.rooms[0];
  const i=inspectRuntimeObject(villa,r0.runtime_room_id,vsV).inspection;
  chk('a room inspects as kind ROOM', i.kind==='ROOM');
  chk('a room inspection names its canonical space instance',
      i.source_element_id===r0.space_instance_id&&i.space_id===r0.space_id);
  chk('room dimensions equal the canonical rectangle exactly',
      i.width_m===_rtQ(r0.rect_local[2])&&i.depth_m===_rtQ(r0.rect_local[3]));
  chk('a room inspection is source-backed and invents nothing',
      i.source_backed===true&&/nothing is invented/.test(String(i.note)));
  chk('a room with no declared area reports NOT_SPECIFIED, never zero', (function(){
    const s=C(villa);
    s.rooms[0]=Object.assign({},s.rooms[0],{area_m2:null,name:null,level_index:null});
    const j=inspectRuntimeObject(s,s.rooms[0].runtime_room_id,vsV).inspection;
    return j.area_m2===RT_NOT_SPECIFIED&&j.name===RT_NOT_SPECIFIED
        &&j.level_index===RT_NOT_SPECIFIED; })());
})();

console.log('\n== INSPECTION IS PURE ==');
(function(){
  const before=JSON.stringify(villa), mBefore=JSON.stringify(SC.models.fls_full);
  const vBefore=JSON.stringify(vsV);
  villa.objects.forEach(o=>inspectRuntimeObject(villa,o.runtime_object_id,vsV));
  villa.rooms.forEach(r=>inspectRuntimeObject(villa,r.runtime_room_id,vsV));
  chk('inspecting every object and room leaves the runtime scene unchanged',
      JSON.stringify(villa)===before);
  chk('inspecting every object and room leaves the visual scene unchanged',
      JSON.stringify(vsV)===vBefore);
  chk('inspecting every object and room leaves the source model unchanged',
      JSON.stringify(SC.models.fls_full)===mBefore);
  chk('inspection is deterministic across repeated calls', (function(){
    const a=JSON.stringify(inspectRuntimeObject(villa,anyO.runtime_object_id,vsV));
    const b=JSON.stringify(inspectRuntimeObject(villa,anyO.runtime_object_id,vsV));
    return a===b; })());
  chk('mutating a returned inspection cannot reach the runtime scene', (function(){
    const i=inspectRuntimeObject(villa,anyO.runtime_object_id,vsV).inspection;
    i.collision.blocking=!i.collision.blocking;
    i.dimensions_m.width=999999;
    const o=villa.objects.filter(x=>x.runtime_object_id===anyO.runtime_object_id)[0];
    return o.collision.blocking!==i.collision.blocking
        && _rtQ(o.obb.hx*2)!==999999; })());
})();

console.log('\n== INVALID INSPECTION TARGETS ==');
['no_such_id','',null,42,{a:1},['x'],false].forEach(function(t){
  const r=inspectRuntimeObject(villa,t,vsV);
  chk('inspection refuses target '+JSON.stringify(t),
      r.valid===false&&r.inspection===null
      &&codes(r).indexOf('INTERACTION_TARGET_INVALID')>=0, JSON.stringify(codes(r)));
});

console.log('\n== §22 — SELECT AND INSPECT ARE DECLARED ACTIONS ==');
(function(){
  ['SELECT','DESELECT','INSPECT'].forEach(function(a){
    chk('the action '+a+' is declared in the canonical specification',
        RT_ACTIONS.indexOf(a)>=0); });
  const r=validateRuntimeAction('SELECT','OBJECT','x',null);
  chk('SELECT on an OBJECT validates', r.valid&&r.action==='SELECT');
  const w=validateRuntimeAction('SELECT','OBJECT','x',{set_material:'brick'});
  chk('a selection payload carrying a write intent is refused',
      w.valid===false&&codes(w).indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0);
  const w2=validateRuntimeAction('INSPECT','OBJECT','x',{writes_to_model:true});
  chk('an inspection claiming to write to the model is refused',
      w2.valid===false&&codes(w2).indexOf('RUNTIME_MODEL_WRITE_ATTEMPT')>=0);
})();

console.log('\n── multiple models ──');
['hotel','clinic','warehouse','office','mixed_use'].forEach(function(n){
  const s=RS(n);
  const st=createRuntimeState(s,null,null,null);
  const o=s.objects[0];
  const ok=o?selectRuntimeObject(st,s,o.runtime_object_id):{valid:false};
  chk(n+': the first object selects and inspects without an issue',
      !!o&&ok.valid&&inspectRuntimeObject(s,o.runtime_object_id,VS(n)).valid);
});

console.log('\n──────────────────────────────────────────────');
console.log('SELECTION: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
