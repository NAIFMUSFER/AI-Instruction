const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const LIB=require(_np.join(HERE,'lib_authoring_fixtures.js'));
const SC=LIB.load();
const C=o=>JSON.parse(JSON.stringify(o));
const M=n=>C(SC.models[n]);
const PR=n=>auCreateProject(M(n),'bld_0','IMPORT',null);
const codes=r=>r.issues.map(i=>i.code);
const SCEN={}; SC.scenarios.forEach(s=>{ SCEN[s[0]]=s; });
const ADV={}; SC.adversarial.forEach(a=>{ ADV[a[0]]=a[1]; });
const prev=(model,cmd,rev,bid,snap,grid)=>auPreviewCommand(model,LIB.hydrate(cmd),
  rev===undefined?null:rev,bid||'bld_0',snap===undefined?null:snap,
  grid===undefined?null:grid);
const scen=name=>{ const s=SCEN[name]; return {model:M(s[1]),cmd:LIB.hydrate(s[2]),
  project:auCreateProject(M(s[1]),'bld_0','IMPORT',null)}; };

/* ============================================================================
   المرحلة 5 — عقد التأليف: المواصفة، مخطّط الأمر، التطبيع، الحتمية
   ========================================================================== */
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_authoring.json'),'utf8'));

console.log('\n== §1 — SPEC INTEGRITY AND NO DRIFT ==');
chk('the browser spec is byte-identical to acs_authoring.json',
    JSON.stringify(CANON)===JSON.stringify(ACS_AUTHORING_SPEC));
chk('schema and engine version are pinned',
    AU_SCHEMA==='acs.authoring/1'&&/^acs-authoring-engine\//.test(AU_ENGINE_VERSION));
chk('the transaction states are the six declared states',
    JSON.stringify(AU_TRANSACTION_STATES)
      ===JSON.stringify(['IDLE','DRAFT','PREVIEWED','VALIDATED','READY_TO_COMMIT','COMMITTED']));
chk('the four declared failure states exist',
    JSON.stringify(AU_FAILURE_STATES)
      ===JSON.stringify(['REJECTED','CONFLICT','STALE_BASE_REVISION','INVALID_COMMAND']));
chk('DRAFT can never transition straight to COMMITTED',
    CANON.transaction_transitions.DRAFT.indexOf('COMMITTED')<0);
chk('no state transitions directly into a mutated model without COMMITTED', (function(){
  const t=CANON.transaction_transitions;
  return Object.keys(t).every(k=>k==='READY_TO_COMMIT'||t[k].indexOf('COMMITTED')<0); })());
chk('every declared issue code carries a declared severity',
    AU_ISSUE_CODES.every(c=>AU_SEVERITIES.indexOf(AU_ISSUE_SEVERITY[c])>=0));
chk('every command type declares its owning discipline',
    AU_COMMAND_TYPES.every(t=>AU_DISCIPLINES.indexOf(AU_COMMAND_DISCIPLINE[t])>=0));
chk('every implemented command type is part of the declared vocabulary',
    AU_IMPLEMENTED.every(t=>AU_COMMAND_TYPES.indexOf(t)>=0));
chk('the declared-but-unimplemented set is disjoint from the implemented set',
    AU_NOT_IMPLEMENTED.every(t=>AU_IMPLEMENTED.indexOf(t)<0));
chk('every command type is either implemented or explicitly declared unimplemented',
    AU_COMMAND_TYPES.every(t=>AU_IMPLEMENTED.indexOf(t)>=0
      ||AU_NOT_IMPLEMENTED.indexOf(t)>=0));
chk('every implemented command type appears in the dependency graph',
    AU_IMPLEMENTED.every(t=>Array.isArray(AU_DEPENDENCY_GRAPH[t])));
chk('the whole Part 3 vocabulary is present', (function(){
  const REQUIRED=['MOVE_WALL','ADD_WALL','DELETE_WALL','MOVE_DOOR','ADD_DOOR','DELETE_DOOR',
    'CHANGE_DOOR_PROPERTIES','MOVE_WINDOW','ADD_WINDOW','DELETE_WINDOW',
    'CHANGE_WINDOW_PROPERTIES','RESIZE_SPACE','RENAME_SPACE','ADD_SPACE','DELETE_SPACE',
    'MOVE_OBJECT','ADD_OBJECT','DELETE_OBJECT','CHANGE_LEVEL_HEIGHT','ADD_LEVEL',
    'DELETE_LEVEL','MOVE_STAIR','ADD_STAIR','DELETE_STAIR','CHANGE_SITE_DIMENSIONS',
    'CHANGE_BUILDING_POSITION','CHANGE_BUILDING_ROTATION'];
  return REQUIRED.every(t=>AU_COMMAND_TYPES.indexOf(t)>=0); })());
chk('no arbitrary path-based write type is offered',
    ['SET_ANY_FIELD','PATCH_OBJECT','RAW_JSON_MUTATION']
      .every(t=>AU_FORBIDDEN_TYPES.indexOf(t)>=0&&AU_IMPLEMENTED.indexOf(t)<0));

console.log('\n== §9 — VALIDATION IS NOT CODE COMPLIANCE ==');
chk('the specification states plainly that validity is not compliance',
    /does NOT mean code compliant/.test(CANON.validation_note));
chk('no issue code is named as a code violation',
    AU_ISSUE_CODES.every(c=>!/VIOLATION_OF_CODE|NON_COMPLIAN|CODE_VIOLATION/i.test(c)));
chk('the specification declares compliance NOT_EVALUATED',
    CANON.compliance_status==='NOT_EVALUATED');
chk('the specification carries no building-code vocabulary anywhere', (function(){
  const RE=new RegExp(['\\bsbc\\b','\\bibc\\b','nfpa','\\bada\\b','\\baci\\b','asce','aisc',
    'eurocode','\\bnec\\b','\\biec\\b','ashrae'].join('|'),'i');
  return !RE.test(JSON.stringify(CANON)); })());
chk('the code vocabulary probe is not vacuous', /\bibc\b/i.test('see IBC 1004'));

console.log('\n== §2 — COMMAND SCHEMA AND NORMALISATION ==');
(function(){
  const c={type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'X'}};
  const r=auNormaliseCommand(c,null,null,null);
  chk('a well-formed command normalises', r.valid&&!!r.command);
  const n=r.command;
  ['command_id','command_hash','type','discipline','target_id','parameters','constraints',
   'source','actor_id','base_revision','created_at','status','writes_to_model']
    .forEach(k=>chk('the normalised command carries '+k, k in n));
  chk('the command id follows the declared pattern', /^cmd:[0-9a-f]{16}$/.test(n.command_id));
  chk('the command declares that it writes nothing by itself', n.writes_to_model===false);
  chk('the default source is USER', n.source==='USER');
  chk('an unauthenticated actor is null, never invented', n.actor_id===null);
  chk('the discipline is taken from the specification, not guessed',
      n.discipline===AU_COMMAND_DISCIPLINE.RENAME_SPACE);
})();

console.log('\n== §45/§46 — DETERMINISTIC COMMAND IDENTITY ==');
(function(){
  const a={type:'MOVE_WALL',target_id:'w1',parameters:{delta_m:0.5}};
  const b={parameters:{delta_m:0.5},target_id:'w1',type:'MOVE_WALL'};
  chk('key order does not change the command hash',
      auCommandHash(a,null)===auCommandHash(b,null));
  chk('the same semantic edit hashes the same across repeated calls',
      auCommandHash(a,null)===auCommandHash(a,null));
  chk('a timestamp does not affect the semantic command hash',
      auCommandHash(Object.assign({created_at:'2020-01-01T00:00:00Z'},a),null)
        ===auCommandHash(a,null));
  chk('an actor does not affect the semantic command hash',
      auCommandHash(Object.assign({actor_id:'someone'},a),null)===auCommandHash(a,null));
  chk('the source does not affect the semantic command hash',
      auCommandHash(Object.assign({source:'AI_PROPOSAL'},a),null)===auCommandHash(a,null));
  chk('a different parameter changes the hash',
      auCommandHash({type:'MOVE_WALL',target_id:'w1',parameters:{delta_m:0.6}},null)
        !==auCommandHash(a,null));
  chk('a different target changes the hash',
      auCommandHash({type:'MOVE_WALL',target_id:'w2',parameters:{delta_m:0.5}},null)
        !==auCommandHash(a,null));
  chk('a different base revision changes the hash',
      auCommandHash(a,'rev:aaaa')!==auCommandHash(a,'rev:bbbb'));
  chk('a constraint changes the hash',
      auCommandHash(Object.assign({constraints:{must_not_change:['SITE']}},a),null)
        !==auCommandHash(a,null));
  chk('constraint order does not change the hash',
      auCommandHash(Object.assign({constraints:{must_not_change:['SITE','SPACE_RECT']}},a),null)
        ===auCommandHash(Object.assign({constraints:{must_not_change:['SPACE_RECT','SITE']}},a),null));
  chk('the hash carries no timestamp or random component', (function(){
    const h=[]; for(let i=0;i<20;i++) h.push(auCommandHash(a,null));
    return new Set(h).size===1; })());
})();

console.log('\n== §41/§47 — UNTRUSTED INPUT IS REFUSED ==');
[['a null command','null_command'],['a string command','string_command'],
 ['an array command','array_command'],['a numeric command','number_command'],
 ['an empty object','empty_object'],['an unknown type','unknown_type'],
 ['an array used as a type','array_as_type'],['a numeric type','numeric_type']
].forEach(function(p){
  const r=auNormaliseCommand(LIB.hydrate(ADV[p[1]]),null,null,null);
  chk('normalisation refuses '+p[0], r.valid===false&&r.command===null,
      JSON.stringify(codes(r)));
  chk('the refusal of '+p[0]+' uses a declared code',
      codes(r).every(c=>AU_ISSUE_CODES.indexOf(c)>=0), JSON.stringify(codes(r)));
});
['forbidden_set_field','forbidden_patch'].forEach(function(k){
  const r=auNormaliseCommand(LIB.hydrate(ADV[k]),null,null,null);
  chk('a path-based write type ('+k+') is refused as not allowed',
      codes(r).indexOf('COMMAND_NOT_ALLOWED')>=0, JSON.stringify(codes(r)));
});
['proto_pollution','constructor_key'].forEach(function(k){
  const r=auNormaliseCommand(LIB.hydrate(ADV[k]),null,null,null);
  chk('a prototype-pollution key ('+k+') is refused before processing',
      codes(r).indexOf('PAYLOAD_REJECTED')>=0, JSON.stringify(codes(r)));
});
chk('a prototype-pollution attempt does not pollute Object.prototype', (function(){
  auNormaliseCommand(LIB.hydrate(ADV.proto_pollution),null,null,null);
  return ({}).polluted===undefined; })());
['script_value','javascript_url','eval_value'].forEach(function(k){
  const r=auNormaliseCommand(LIB.hydrate(ADV[k]),null,null,null);
  chk('an executable payload ('+k+') is refused',
      codes(r).indexOf('PAYLOAD_REJECTED')>=0, JSON.stringify(codes(r)));
});
['nan_delta','inf_delta','bool_delta'].forEach(function(k){
  const r=auNormaliseCommand(LIB.hydrate(ADV[k]),null,null,null);
  chk('a non-numeric delta ('+k+') is judged without throwing',
      typeof r.valid==='boolean');
  chk('a non-numeric delta ('+k+') never reaches a model as a number', (function(){
    const p=prev(M('villa'),ADV[k]);
    return p.valid===false; })(), JSON.stringify(codes(prev(M('villa'),ADV[k]))));
});
chk('deep nesting is refused',
    codes(auNormaliseCommand(LIB.hydrate(ADV.deep_nesting),null,null,null))
      .indexOf('PAYLOAD_REJECTED')>=0);
chk('an over-long string is refused',
    codes(auNormaliseCommand(LIB.hydrate(ADV.long_string),null,null,null))
      .indexOf('PAYLOAD_REJECTED')>=0);
chk('the authoring engine uses no eval, no exec and no Function constructor', (function(){
  const src=fs.readFileSync(_np.join(ROOT,'acs_authoring.py'),'utf8');
  return !/\beval\s*\(|\bexec\s*\(|compile\s*\(/.test(src); })());

console.log('\n== §41 — DECLARED SNAPPING ONLY ==');
(function(){
  const r=auNormaliseCommand(LIB.hydrate(ADV.unknown_snap),null,null,null);
  chk('an unknown snap type is refused and falls back to NONE',
      codes(r).indexOf('INVALID_PARAMETER')>=0&&r.command.snap==='NONE');
  const r2=auNormaliseCommand(LIB.hydrate(ADV.declared_unimplemented_snap),null,null,null);
  chk('a declared but unimplemented snap type says so rather than pretending',
      codes(r2).indexOf('INVALID_PARAMETER')>=0&&r2.command.snap==='NONE');
  const s=SCEN.snap_grid;
  const r3=auNormaliseCommand(LIB.hydrate(s[2]),null,null,null);
  chk('grid snap rounds the parameter to the declared grid',
      r3.command.parameters.delta_m===0.5, String(r3.command.parameters.delta_m));
  chk('snapping happens before hashing, so a snapped edit is one normal form',
      auCommandHash({type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
        parameters:{delta_m:0.5321},snap:'GRID',grid_m:0.25},null)
      ===auCommandHash({type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
        parameters:{delta_m:0.5111},snap:'GRID',grid_m:0.25},null));
  chk('the edit grid is documented as not a structural grid',
      /NOT a structural grid/.test(CANON.snap_note));
})();

console.log('\n== §38 — EDITABILITY CONTRACT ==');
(function(){
  const m=M('villa');
  const r=auEditableProperties(m,'g.majlis','bld_0');
  chk('a space exposes an editable property model', r.valid&&!!r.properties);
  const f=r.properties.fields;
  const by={}; f.forEach(x=>{by[x.field]=x;});
  chk('wall geometry is editable through the space rectangle',
      by['space.rect'].editability==='EDITABLE');
  chk('a computed area is DERIVED, not editable', by['space.area_m2'].editability==='DERIVED');
  chk('the model hash is DERIVED', by['model_hash'].editability==='DERIVED');
  chk('a render material is DISPLAY_ONLY', by['visual.material'].editability==='DISPLAY_ONLY');
  chk('the source id is READ_ONLY', by['space.id'].editability==='READ_ONLY');
  chk('every field carries one of the five declared classes',
      f.every(x=>AU_EDITABILITY_CLASSES.indexOf(x.editability)>=0));
  chk('not every displayed property is editable',
      r.properties.editable_count<f.length&&r.properties.editable_count>0);
  chk('an editable field publishes its validation constraints',
      Object.keys(by['space.rect'].constraints).length>0);
  const d=auEditableProperties(m,'bld_0.g.majlis.door_0','bld_0').properties;
  const dby={}; d.fields.forEach(x=>{dby[x.field]=x;});
  chk('an opening width is editable', dby['opening.width_m'].editability==='EDITABLE');
  chk('a derived host wall reference is DERIVED',
      dby['opening.host_wall_id'].editability==='DERIVED');
  chk('an unstated clear width is UNKNOWN, never invented',
      dby['opening.clear_width_m'].editability==='UNKNOWN'
      &&dby['opening.clear_width_m'].value===AU_NOT_SPECIFIED);
  const w=auEditableProperties(m,'bld_0.flr_0.wall_0','bld_0').properties;
  chk('a compiled wall exposes no editable geometry of its own',
      w.fields.filter(x=>x.field.indexOf('wall.')===0
        &&x.editability==='EDITABLE').length===0);
  chk('a derived element is documented as edited through its source',
      /edited by editing the semantic source/.test(CANON.read_only_element_note));
})();

console.log('\n== §16/§17 — DEPENDENCY GRAPH IS SELECTIVE, NOT BLIND ==');
(function(){
  const m=M('villa');
  const r=auDependencyImpact({type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
    parameters:{delta_m:0.5}},m,'bld_0');
  chk('a wall move reports its dependency impact', r.valid&&!!r.impact);
  const inv=r.impact.invalidates;
  ['ARCHITECTURE','RELATIONSHIPS','COORDINATION','VISUAL','RUNTIME'].forEach(a=>
    chk('a wall move invalidates '+a, inv.indexOf(a)>=0));
  chk('a wall move does not invalidate the structural discipline',
      inv.indexOf('STRUCTURE')<0);
  chk('a wall move does not invalidate MEP', inv.indexOf('MEP')<0);
  chk('a wall move does not invalidate fire and life safety', inv.indexOf('FLS')<0);
  chk('the report states no structural, MEP or FLS element was mutated',
      r.impact.structure_mutated===false&&r.impact.mep_mutated===false
      &&r.impact.fls_mutated===false);
  const w=auDependencyImpact({type:'MOVE_WINDOW',target_id:'x',parameters:{}},m,'bld_0');
  chk('a window move does not invalidate navigation blindly',
      AU_DEPENDENCY_GRAPH.MOVE_WINDOW.indexOf('NAVIGATION')<0);
  chk('a rename does not invalidate the whole world',
      AU_DEPENDENCY_GRAPH.RENAME_SPACE.length<AU_DEPENDENCY_ARTIFACTS.length/2);
  chk('a lock invalidates nothing at all',
      AU_DEPENDENCY_GRAPH.LOCK_ELEMENT.length===0);
  chk('deleting a door reports fire and life safety as possibly affected',
      AU_DEPENDENCY_GRAPH.DELETE_DOOR.indexOf('FLS')>=0);
  chk('the dependency note explains why STRUCTURE is absent architecturally',
      /never rebuilds or moves a structural/.test(CANON.dependency_graph_note));
  chk('the impact report is factual and disclaims recommendation',
      /Nothing here is an engineering recommendation/.test(r.impact.note));
})();

console.log('\n== §18 — CASCADE PREVIEW NAMES EXACT IDS ==');
(function(){
  const m=M('villa');
  const r=auDependencyImpact({type:'DELETE_SPACE',target_id:'g.majlis',parameters:{}},
    m,'bld_0');
  chk('a destructive impact names exact element ids, never "some dependencies"',
      r.impact.affected_element_ids.length>0
      &&r.impact.affected_element_ids.every(x=>typeof x==='string'&&x.length>0));
  chk('the affected count matches the named ids',
      r.impact.affected_count===r.impact.affected_element_ids.length);
  chk('the named ids resolve in the model',
      r.impact.affected_element_ids.every(id=>
        auResolveTarget(m,'bld_0.'+id,'bld_0').kind!==null
        ||auResolveTarget(m,id,'bld_0').kind!==null
        ||/space_boundary_changed|vertical_connectivity/.test(id)));
})();

console.log('\n== §95 — NO USER OR ROLE IS FABRICATED ==');
(function(){
  chk('the declared sources are exactly the four allowed',
      JSON.stringify(AU_SOURCES)===JSON.stringify(['USER','AI_PROPOSAL','IMPORT','SYSTEM_TOOL']));
  const p=PR('villa');
  const c=auCommitTransaction(p,[{type:'RENAME_SPACE',target_id:'g.majlis',
    parameters:{name:'X'}}],{});
  chk('a commit without an identity records a null actor',
      c.audit.actor_id===null);
  chk('no user, role or permission is fabricated — the absence is stated, not implied',
      /there are no users and no roles in this phase/.test(CANON.lock_note)
      &&/actor_id is null unless an authenticated identity is supplied/.test(CANON.actor_note));
  chk('no permission or role field exists anywhere in the command schema',
      !/"(role|permission|privilege|is_admin)"/i.test(JSON.stringify(CANON)));
  chk('an unknown source is refused rather than accepted as a new identity',
      codes(auNormaliseCommand(LIB.hydrate(ADV.bad_source),null,null,null))
        .indexOf('INVALID_COMMAND')>=0);
})();

console.log('\n== §96 — NO COLLABORATION IS IMPLEMENTED ==');
chk('no multiplayer, websocket or CRDT vocabulary exists in the specification',
    !/multiplayer|websocket|crdt|realtime|real-time co/i.test(JSON.stringify(CANON)));
chk('the revision guard exists as the concurrency foundation instead',
    AU_ISSUE_CODES.indexOf('STALE_BASE_REVISION')>=0);

console.log('\n──────────────────────────────────────────────');
console.log('AUTHORING CONTRACT: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
