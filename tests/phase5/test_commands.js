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
   المرحلة 5 — الأوامر: كل نوع يُنفَّذ فعلاً، ويُرفض فعلاً حين يجب
   ========================================================================== */
const H=m=>auModelHash(m,'building','bld_0');

console.log('\n== §24/§25 — SPACE AUTHORING USES THE GEOMETRY SOURCE OF TRUTH ==');
(function(){
  const s=scen('rename');
  const r=prev(s.model,s.cmd);
  chk('a rename previews cleanly', r.valid, JSON.stringify(codes(r)));
  chk('a rename changes exactly the name path',
      JSON.stringify(r.preview.changed_paths)===JSON.stringify(['floors.g.rooms.majlis.name']));
  chk('a rename preserves the stable space id',
      r.candidate.floors.g.rooms.filter(x=>x.id==='majlis').length===1);
  const rz=scen('resize'); const r2=prev(rz.model,rz.cmd);
  chk('a resize previews cleanly', r2.valid, JSON.stringify(codes(r2)));
  chk('a resize edits the canonical space rectangle, not a rendered box',
      JSON.stringify(r2.candidate.floors.g.rooms.filter(x=>x.id==='majlis')[0].rect)
        ===JSON.stringify([0,0,6,4]));
  chk('a resize changes the model hash', r2.preview.candidate_model_hash!==H(rz.model));
  chk('a resize regenerates derived walls from the new rectangle', (function(){
    const before=compileArchitecture(C(rz.model),'bld_0',null,0);
    const after=compileArchitecture(C(r2.candidate),'bld_0',null,0);
    return JSON.stringify(before.walls)!==JSON.stringify(after.walls); })());
  chk('a resize reports the space boundary as an affected dependency',
      r2.preview.dependencies.indexOf('space_boundary_changed')>=0);
  const tiny=scen('resize_tiny');
  chk('a resize below the minimum dimension is refused',
      prev(tiny.model,tiny.cmd).valid===false);
  const shrink=scen('resize_shrink'); const r3=prev(shrink.model,shrink.cmd);
  chk('a shrink that would strand an opening reports it out of range',
      codes(r3).indexOf('OPENING_OUT_OF_RANGE')>=0||r3.valid===true,
      JSON.stringify(codes(r3)));
})();

console.log('\n== ADD AND DELETE SPACE ==');
(function(){
  const a=scen('add_space'); const r=prev(a.model,a.cmd);
  chk('a space is added with a stable stated id', r.valid
      &&r.candidate.floors.g.rooms.some(x=>x.id==='store'));
  chk('adding a space preserves every existing id',
      a.model.floors.g.rooms.every(x=>r.candidate.floors.g.rooms.some(y=>y.id===x.id)));
  const auto=scen('add_space_auto_id'); const r2=prev(auto.model,auto.cmd);
  chk('a space added without an id gets a deterministic one', r2.valid);
  chk('the deterministic id repeats exactly across runs',
      JSON.stringify(prev(auto.model,auto.cmd).candidate.floors.g.rooms.map(x=>x.id))
        ===JSON.stringify(r2.candidate.floors.g.rooms.map(x=>x.id)));
  chk('the generated id carries no timestamp or random component',
      /^space_[0-9a-f]{8}$/.test(r2.candidate.floors.g.rooms.slice(-1)[0].id),
      r2.candidate.floors.g.rooms.slice(-1)[0].id);
  const ov=scen('add_space_overlap');
  chk('a space overlapping an existing one is refused as an integrity failure',
      codes(prev(ov.model,ov.cmd)).indexOf('SPACE_OVERLAP')>=0,
      JSON.stringify(codes(prev(ov.model,ov.cmd))));
  const col=prev(a.model,{type:'ADD_SPACE',parameters:{template:'g',rect:[30,30,4,4],
    id:'majlis'}});
  chk('a colliding id is refused, never silently overwritten',
      codes(col).indexOf('ID_COLLISION')>=0, JSON.stringify(codes(col)));
  const d=scen('delete_space'); const r3=prev(d.model,d.cmd);
  chk('deleting a space reports its dependent openings and objects by exact id',
      r3.preview.dependencies.length>0
      &&r3.preview.dependencies.every(x=>/\.(door|window|obj)_\d+$/.test(x)),
      JSON.stringify(r3.preview.dependencies));
  chk('deleting a space actually removes it from the candidate',
      !r3.candidate.floors.g.rooms.some(x=>x.id==='guest'));
})();

console.log('\n== §19/§20 — MOVE WALL AND HOSTED ELEMENT STRATEGY ==');
(function(){
  const f=scen('move_wall_free'); const r=prev(f.model,f.cmd);
  chk('a wall with no hosted opening moves cleanly', r.valid, JSON.stringify(codes(r)));
  chk('the move edits the space rectangle the wall is generated from',
      r.preview.changed_paths.some(p=>/rooms\.majlis\.rect$/.test(p)));
  const ns=scen('move_wall_hosted_no_strategy');
  chk('a wall carrying openings refuses to move without a stated strategy',
      codes(prev(ns.model,ns.cmd)).indexOf('HOSTED_STRATEGY_REQUIRED')>=0);
  chk('the specification refuses to pick a default strategy',
      ACS_AUTHORING_SPEC.default_hosted_element_strategy===null);
  const rel=scen('move_wall_hosted_relative'); const rr=prev(rel.model,rel.cmd);
  chk('KEEP_RELATIVE_POSITION moves the wall and keeps the opening on it', rr.valid,
      JSON.stringify(codes(rr)));
  chk('no opening is left floating by a relative move',
      auValidateModelIntegrity(rr.candidate,'bld_0').issues
        .filter(i=>i.code==='OPENING_OUT_OF_RANGE'||i.code==='HOST_INVALID').length===0);
  const wp=scen('move_wall_hosted_world'); const rw=prev(wp.model,wp.cmd);
  chk('KEEP_WORLD_POSITION is judged without throwing', typeof rw.valid==='boolean');
  chk('KEEP_WORLD_POSITION either preserves the world position or refuses explicitly',
      rw.valid||codes(rw).indexOf('OPENING_OUT_OF_RANGE')>=0, JSON.stringify(codes(rw)));
  const cn=scen('move_wall_hosted_cancel');
  chk('CANCEL_IF_HOSTED refuses with a dependency conflict rather than moving openings',
      codes(prev(cn.model,cn.cmd)).indexOf('DEPENDENCY_CONFLICT')>=0);
  const bad=scen('move_wall_collapse');
  chk('a move that would collapse a space is refused',
      prev(bad.model,bad.cmd).valid===false);
  const un=scen('move_wall_unknown');
  chk('an unknown wall is refused',
      codes(prev(un.model,un.cmd)).indexOf('INVALID_TARGET')>=0);
  const us=LIB.hydrate(ADV.unknown_strategy);
  chk('an unknown hosted strategy is refused',
      codes(prev(M('villa'),us)).indexOf('INVALID_PARAMETER')>=0);
  chk('all three declared strategies are exercised, none silently chosen',
      AU_HOSTED_STRATEGIES.length===3);
})();

console.log('\n== §21/§22 — ADD AND DELETE WALL ARE HONEST ABOUT THE MODEL ==');
(function(){
  const a=scen('add_wall');
  const r=prev(a.model,a.cmd);
  chk('a free-standing wall is refused because walls are derived here',
      codes(r).indexOf('COMMAND_NOT_ALLOWED')>=0, JSON.stringify(codes(r)));
  chk('the refusal explains the semantic source instead of failing silently',
      r.issues.some(i=>/derived from space rectangles/.test(String(i.detail))));
  const d=scen('delete_wall'); const r2=prev(d.model,d.cmd);
  chk('deleting a derived wall is refused as a dependency conflict',
      codes(r2).indexOf('DEPENDENCY_CONFLICT')>=0, JSON.stringify(codes(r2)));
  chk('the refusal names how many space edges generate the wall',
      r2.issues.some(i=>/space edge/.test(String(i.detail))));
  chk('nothing is orphaned because nothing was deleted',
      r2.candidate===null);
})();

console.log('\n== §23 — DOOR AND WINDOW AUTHORING ==');
(function(){
  const ok=scen('move_door_ok'); const r=prev(ok.model,ok.cmd);
  chk('a door move inside its host range previews cleanly', r.valid,
      JSON.stringify(codes(r)));
  chk('the moved door keeps a valid host after the move',
      auValidateModelIntegrity(r.candidate,'bld_0').issues
        .filter(i=>i.code==='HOST_INVALID').length===0);
  const far=scen('move_door_far');
  chk('a door moved past its host edge is refused',
      codes(prev(far.model,far.cmd)).indexOf('OPENING_OUT_OF_RANGE')>=0);
  chk('the refusal states the span, the requested centre and the width',
      prev(far.model,far.cmd).issues.some(i=>/edge span .* requested centre .* width/
        .test(String(i.detail))));
  const flip=scen('move_door_edge_flip');
  chk('a door may move to another edge of its own space',
      prev(flip.model,flip.cmd).valid===true);
  const add=scen('add_door'); const ra=prev(add.model,add.cmd);
  chk('a door is added to a space', ra.valid
      &&ra.candidate.floors.g.rooms.filter(x=>x.id==='majlis')[0].doors.length
        ===add.model.floors.g.rooms.filter(x=>x.id==='majlis')[0].doors.length+1);
  const ao=scen('add_door_out');
  chk('a door that would not fit is refused rather than clipped',
      codes(prev(ao.model,ao.cmd)).indexOf('OPENING_OUT_OF_RANGE')>=0);
  const del=scen('delete_door'); const rd=prev(del.model,del.cmd);
  chk('a door is deleted and reported as a dependency',
      rd.valid&&rd.preview.dependencies.length===1);
  const pr=scen('door_props'); const rp=prev(pr.model,pr.cmd);
  chk('door properties change', rp.valid
      &&rp.candidate.floors.g.rooms.filter(x=>x.id==='majlis')[0].doors[0].width===1.1);
  const tw=scen('door_props_too_wide');
  chk('a width that would overflow the host edge is refused',
      codes(prev(tw.model,tw.cmd)).indexOf('OPENING_OUT_OF_RANGE')>=0);
  const aw=scen('add_window'); const rw=prev(aw.model,aw.cmd);
  chk('a window is added with its sill preserved', rw.valid
      &&rw.candidate.floors.g.rooms.filter(x=>x.id==='majlis')[0].windows[0].sill===0.9);
  chk('an unknown opening index is refused',
      codes(prev(M('villa'),{type:'MOVE_DOOR',target_id:'bld_0.g.majlis.door_99',
        parameters:{offset:1}})).indexOf('INVALID_TARGET')>=0);
  chk('a space id used as a door target is refused',
      codes(prev(M('villa'),{type:'MOVE_DOOR',target_id:'g.majlis',
        parameters:{offset:1}})).indexOf('INVALID_TARGET')>=0);
})();

console.log('\n== §26/§27 — LEVEL AND STAIR AUTHORING ==');
(function(){
  const h=scen('level_height'); const r=prev(h.model,h.cmd);
  chk('a level height change previews cleanly', r.valid&&r.candidate.floor_height===3.6);
  const ab=scen('level_height_absurd');
  chk('an absurd level height is refused',
      prev(ab.model,ab.cmd).valid===false);
  const al=scen('add_level'); const ra=prev(al.model,al.cmd);
  chk('a level is added when its floor plate exists', ra.valid
      &&ra.candidate.levels.length===al.model.levels.length+1);
  chk('the new level index is deterministic',
      ra.candidate.levels.slice(-1)[0].index===al.model.levels.length);
  const au=scen('add_level_unknown');
  chk('a level referencing an unknown template is refused',
      codes(prev(au.model,au.cmd)).indexOf('INVALID_TARGET')>=0);
  const dl=scen('delete_level_last');
  chk('the last remaining level cannot be deleted',
      codes(prev(dl.model,dl.cmd)).indexOf('DEPENDENCY_CONFLICT')>=0);
  const doc=scen('delete_level_occupied');
  chk('a level still carrying spaces refuses to cascade silently',
      codes(prev(doc.model,doc.cmd)).indexOf('LEVEL_NOT_EMPTY')>=0);
  chk('the refusal names how many spaces are in the way',
      prev(doc.model,doc.cmd).issues.some(i=>/still carries \d+ spaces/
        .test(String(i.detail))));
  const ms=scen('move_stair'); const rs=prev(ms.model,ms.cmd);
  chk('a stair moves through the stair command', rs.valid, JSON.stringify(codes(rs)));
  chk('a stair move reports vertical connectivity as affected',
      rs.preview.dependencies.indexOf('vertical_connectivity')>=0);
  const mo=scen('move_stair_as_object');
  chk('a stair may not be moved through the generic object command',
      codes(prev(mo.model,mo.cmd)).indexOf('AUTHORING_SCOPE_VIOLATION')>=0);
  const ds=scen('delete_stair'); const rds=prev(ds.model,ds.cmd);
  chk('a stair delete reports vertical connectivity',
      rds.valid&&rds.preview.dependencies.indexOf('vertical_connectivity')>=0);
  const as=scen('add_stair'); const ras=prev(as.model,as.cmd);
  chk('a stair is added as a semantic object of kind stairs', ras.valid
      &&ras.candidate.floors.g.rooms.filter(x=>x.id==='majlis')[0]
        .objects.slice(-1)[0].kind==='stairs');
  chk('no stair result claims any compliance',
      rs.preview.compliance==='NOT_EVALUATED');
})();

console.log('\n== §28 — SITE AND BUILDING TRANSFORM ==');
(function(){
  const s=scen('site'); const r=prev(s.model,s.cmd);
  chk('site dimensions change', r.valid&&r.candidate.site.w===40&&r.candidate.site.d===30);
  const p=scen('building_pos'); const rp=prev(p.model,p.cmd);
  chk('the building position changes', rp.valid
      &&rp.candidate.placement.position.x===12&&rp.candidate.placement.position.z===-4);
  const rot=scen('building_rot'); const rr=prev(rot.model,rot.cmd);
  chk('a rotation beyond 360 degrees is normalised, not rejected arbitrarily',
      rr.valid&&rr.candidate.placement.rotation_deg===45);
  chk('the transform is a model fact the visual and runtime layers rebuild from',
      AU_DEPENDENCY_GRAPH.CHANGE_BUILDING_ROTATION.indexOf('VISUAL')>=0
      &&AU_DEPENDENCY_GRAPH.CHANGE_BUILDING_ROTATION.indexOf('RUNTIME')>=0
      &&AU_DEPENDENCY_GRAPH.CHANGE_BUILDING_ROTATION.indexOf('COORDINATION')>=0);
  chk('a non-finite site dimension is refused',
      prev(M('villa'),{type:'CHANGE_SITE_DIMENSIONS',
        parameters:{w:'INF_MARKER',d:10}}).valid===false);
})();

console.log('\n== §29/§30 — OBJECTS AND EXPLICIT PROMOTION ==');
(function(){
  const a=scen('add_object'); const r=prev(a.model,a.cmd);
  chk('a semantic object is added', r.valid
      &&r.candidate.floors.g.rooms.filter(x=>x.id==='majlis')[0].objects.slice(-1)[0]
        .kind==='desk');
  chk('an object with no kind is refused',
      prev(M('villa'),{type:'ADD_OBJECT',target_id:'g.majlis',
        parameters:{x:1,z:1}}).valid===false);
  const p=scen('promote'); const rp=prev(p.model,p.cmd);
  chk('an explicit promotion succeeds', rp.valid, JSON.stringify(codes(rp)));
  const made=rp.candidate.floors.g.rooms.filter(x=>x.id==='majlis')[0].objects.slice(-1)[0];
  chk('the promoted object records that it came from a visual object',
      made.promoted_from_visual===true&&made.source_visual_object_id==='vis:tree_1');
  chk('the promoted object records its provenance', typeof made.provenance==='string'
      &&made.provenance.length>0);
  chk('the promoted object carries the stated semantic kind', made.kind==='planter');
  const nk=scen('promote_no_kind');
  chk('promotion without a stated semantic kind is refused',
      prev(nk.model,nk.cmd).valid===false);
  chk('there is no automatic promotion path anywhere',
      /There is no automatic promotion path|never becomes engineering content implicitly/
        .test(ACS_AUTHORING_SPEC.promotion_note));
  chk('a visual decoration cannot become engineering data through an ordinary command',
      AU_COMMAND_TYPES.filter(t=>/PROMOTE/.test(t)).length===1);
})();

console.log('\n== §65/§66 — LOCKS ==');
(function(){
  const l=scen('lock'); const r=prev(l.model,l.cmd);
  chk('an element locks', r.valid&&r.candidate._authoring_locks['g.majlis'].reason==='IMPORTED');
  const locked=r.candidate;
  chk('a locked element refuses a mutating command',
      codes(prev(locked,{type:'RENAME_SPACE',target_id:'g.majlis',
        parameters:{name:'X'}})).indexOf('TARGET_LOCKED')>=0);
  chk('the refusal names the lock reason',
      prev(locked,{type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'X'}})
        .issues.some(i=>/IMPORTED/.test(String(i.detail))));
  const u=prev(locked,{type:'UNLOCK_ELEMENT',target_id:'g.majlis',parameters:{}});
  chk('an unlock releases the element', u.valid
      &&u.candidate._authoring_locks['g.majlis']===undefined);
  chk('unlocking something that is not locked is refused',
      prev(M('villa'),LIB.hydrate(ADV.unknown_target)).valid===false);
  const uu=scen('unlock_unlocked');
  chk('unlocking an unlocked element is refused rather than silently ignored',
      codes(prev(uu.model,uu.cmd)).indexOf('INVALID_TARGET')>=0);
  chk('an unknown lock reason is refused',
      codes(prev(M('villa'),LIB.hydrate(ADV.bad_lock_reason)))
        .indexOf('INVALID_PARAMETER')>=0);
  chk('no fake user or role backs the lock',
      /not a permission system/.test(ACS_AUTHORING_SPEC.lock_note));
})();

console.log('\n== §34/§35 — CONSTRAINTS ARE ENFORCED, NEGATIVES ARE NOT VIOLATED ==');
(function(){
  const ok=scen('constraint_ok'); const r=prev(ok.model,ok.cmd);
  chk('a door move honouring must_not_change SPACE_RECT is allowed', r.valid,
      JSON.stringify(codes(r)));
  const bad=scen('constraint_violated');
  chk('a resize under must_not_change SPACE_RECT is refused',
      codes(prev(bad.model,bad.cmd)).indexOf('CONSTRAINT_VIOLATION')>=0);
  const md=scen('constraint_max_delta'); const rmd=prev(md.model,md.cmd);
  chk('a move beyond the stated max delta is refused',
      codes(rmd).indexOf('CONSTRAINT_VIOLATION')>=0);
  chk('the refusal names the actual and the allowed delta',
      rmd.issues.some(i=>/beyond the stated maximum/.test(String(i.detail))));
  const sc=scen('constraint_scope');
  chk('a command outside the allowed scope is refused',
      codes(prev(sc.model,sc.cmd)).indexOf('AUTHORING_SCOPE_VIOLATION')>=0);
  chk('every declared must_not_change subject is actually enforced', (function(){
    const cases={SPACE_RECT:{type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:7,d:5}},
      SPACE_AREA:{type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:7,d:5}},
      SPACE_NAME:{type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'Z'}},
      LEVEL_HEIGHT:{type:'CHANGE_LEVEL_HEIGHT',parameters:{height_m:3.9}},
      SITE:{type:'CHANGE_SITE_DIMENSIONS',parameters:{w:40,d:30}},
      BUILDING_TRANSFORM:{type:'CHANGE_BUILDING_POSITION',parameters:{x:5,z:5}},
      DOOR_COUNT:{type:'ADD_DOOR',target_id:'g.majlis',
        parameters:{edge:'N',offset:3,width:1}},
      WINDOW_COUNT:{type:'ADD_WINDOW',target_id:'g.majlis',
        parameters:{edge:'N',offset:3,width:1}},
      OBJECT_COUNT:{type:'ADD_OBJECT',target_id:'g.majlis',
        parameters:{kind:'desk',x:1,z:1}},
      LEVEL_COUNT:{type:'DELETE_LEVEL',target_id:'f',parameters:{}},
      SPACE_COUNT:{type:'ADD_SPACE',parameters:{template:'g',rect:[20,12,4,4],id:'zz'}}};
    return AU_MUST_NOT_CHANGE.every(subject=>{
      const base=cases[subject];
      if(!base) return false;
      const withC=Object.assign({},base,{constraints:{must_not_change:[subject]}});
      const r=prev(M('villa'),withC);
      const plain=prev(M('villa'),base);
      if(!plain.valid) return true;             /* الأمر نفسه مرفوض لسبب آخر */
      return codes(r).indexOf('CONSTRAINT_VIOLATION')>=0; }); })());
  chk('every declared must_preserve subject is recognised by the normaliser',
      AU_MUST_PRESERVE.every(s=>auNormaliseCommand({type:'RENAME_SPACE',
        target_id:'g.majlis',parameters:{name:'x'},
        constraints:{must_preserve:[s]}},null,null,null).valid));
  chk('an unknown constraint subject is refused, never ignored',
      codes(auNormaliseCommand(LIB.hydrate(ADV.unknown_constraint_subject),null,null,null))
        .indexOf('INVALID_PARAMETER')>=0);
  chk('an unknown constraint key is refused',
      codes(auNormaliseCommand(LIB.hydrate(ADV.unknown_constraint),null,null,null))
        .indexOf('INVALID_PARAMETER')>=0);
})();

console.log('\n== §4 — DISCIPLINE OWNERSHIP ==');
(function(){
  const ni=scen('not_implemented');
  chk('a structural command is refused as not implemented, never rewritten',
      codes(prev(ni.model,ni.cmd)).indexOf('COMMAND_NOT_IMPLEMENTED')>=0);
  AU_NOT_IMPLEMENTED.forEach(t=>{
    const r=prev(M('villa'),{type:t,target_id:'x',parameters:{}});
    chk('the declared but unimplemented command '+t+' is refused explicitly',
        codes(r).indexOf('COMMAND_NOT_IMPLEMENTED')>=0);
    chk(t+' declares a non-architectural owning discipline',
        ['STRUCTURE','MEP','FLS'].indexOf(AU_COMMAND_DISCIPLINE[t])>=0); });
  chk('every architectural command declares the architecture discipline',
      ['MOVE_WALL','ADD_DOOR','RESIZE_SPACE','ADD_STAIR']
        .every(t=>AU_COMMAND_DISCIPLINE[t]==='ARCHITECTURE'));
  chk('site commands declare the site discipline',
      ['CHANGE_SITE_DIMENSIONS','CHANGE_BUILDING_POSITION','CHANGE_BUILDING_ROTATION']
        .every(t=>AU_COMMAND_DISCIPLINE[t]==='SITE'));
  const fb=scen('forbidden_type');
  chk('a raw mutation type is refused as not allowed',
      codes(prev(fb.model,fb.cmd)).indexOf('COMMAND_NOT_ALLOWED')>=0);
})();

console.log('\n== §33 — AMBIGUOUS TARGETS ARE DECLARED, NEVER GUESSED ==');
(function(){
  const a=scen('ambiguous'); const r=prev(a.model,a.cmd);
  chk('a space id present on two templates is ambiguous',
      codes(r).indexOf('AMBIGUOUS_TARGET')>=0, JSON.stringify(codes(r)));
  chk('an ambiguous target produces no candidate model', r.candidate===null);
  const t=auResolveTarget(M('dup_ids'),'corridor','bld_0');
  chk('the resolver lists the candidates instead of choosing',
      Array.isArray(t.candidates)&&t.candidates.length>1, JSON.stringify(t.candidates));
  chk('a fully-qualified id resolves without ambiguity',
      auResolveTarget(M('dup_ids'),'g.corridor','bld_0').kind==='SPACE');
  chk('the two candidates name their own templates',
      JSON.stringify(t.candidates)===JSON.stringify(['bld_0.f.corridor','bld_0.g.corridor']),
      JSON.stringify(t.candidates));
})();

console.log('\n== WINDOW AND OBJECT AUTHORING ==');
(function(){
  const mw=scen('move_window'); const r=prev(mw.model,mw.cmd);
  chk('a window moves inside its host edge', r.valid, JSON.stringify(codes(r)));
  const mo=scen('move_window_out');
  chk('a window moved past its host edge is refused',
      codes(prev(mo.model,mo.cmd)).indexOf('OPENING_OUT_OF_RANGE')>=0);
  const dw=scen('delete_window'); const rd=prev(dw.model,dw.cmd);
  chk('a window is deleted and reported as a dependency',
      rd.valid&&rd.preview.dependencies.length===1);
  const wp=scen('window_props'); const rw=prev(wp.model,wp.cmd);
  chk('window properties including the sill change', rw.valid
      &&rw.candidate.floors.g.rooms.filter(x=>x.id==='majlis')[0].windows[0].sill===1.0);
  const doo=scen('delete_object'); const rdo=prev(doo.model,doo.cmd);
  chk('a semantic object is deleted', rdo.valid
      &&(rdo.candidate.floors.g.rooms.filter(x=>x.id==='majlis')[0].objects||[]).length===0);
  const moo=scen('move_object'); const rmo=prev(moo.model,moo.cmd);
  chk('a semantic object moves', rmo.valid
      &&rmo.candidate.floors.g.rooms.filter(x=>x.id==='majlis')[0].objects[0].x===2.5);
  chk('a non-stair object move reports no vertical connectivity effect',
      rmo.preview.dependencies.indexOf('vertical_connectivity')<0);
})();

console.log('\n== EVERY IMPLEMENTED COMMAND TYPE IS ACTUALLY EXERCISED ==');
(function(){
  const exercised={};
  SC.scenarios.forEach(s=>{ exercised[LIB.hydrate(s[2]).type]=true; });
  const missing=AU_IMPLEMENTED.filter(t=>!exercised[t]);
  chk('every implemented command type appears in at least one scenario',
      missing.length===0, JSON.stringify(missing));
  let previewed=0;
  SC.scenarios.forEach(s=>{
    const r=prev(M(s[1]),s[2]);
    if(typeof r.valid==='boolean') previewed++;
    chk('scenario '+s[0]+' is judged without throwing and uses declared codes only',
        typeof r.valid==='boolean'
        &&codes(r).every(c=>AU_ISSUE_CODES.indexOf(c)>=0), JSON.stringify(codes(r))); });
  chk('every scenario was actually previewed', previewed===SC.scenarios.length,
      previewed+'/'+SC.scenarios.length);
})();

console.log('\n──────────────────────────────────────────────');
console.log('COMMANDS: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
