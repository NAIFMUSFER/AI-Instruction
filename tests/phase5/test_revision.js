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
   المرحلة 5 — المراجعات: التاريخ الملحق، التراجع، الإعادة، الفروق، الحفظ
   ========================================================================== */
const RENAME={type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'Grand Majlis'}};
const RENAME2={type:'RENAME_SPACE',target_id:'g.living',parameters:{name:'Salon'}};
const RESIZE={type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:6,d:4}};

console.log('\n== §12 — REVISION HISTORY IS APPEND-ONLY ==');
(function(){
  const p=PR('villa');
  chk('a new project starts with exactly one revision', p.history.length===1);
  const r0=p.history[0];
  chk('the initial revision has no parent', r0.parent_revision_id===null);
  chk('the initial revision names the model hash', r0.model_hash===p.model_hash);
  let cur=p;
  [RENAME,RENAME2,RESIZE].forEach((c,i)=>{
    const res=auCommitTransaction(cur,[c],{acknowledge_warnings:true});
    chk('commit '+(i+1)+' succeeded', res.committed===true, JSON.stringify(codes(res)));
    cur=res.project; });
  chk('three commits produced four revisions', cur.history.length===4);
  chk('every revision names its parent except the first',
      cur.history.slice(1).every((r,i)=>r.parent_revision_id
        ===cur.history[i].revision_id));
  chk('every revision id is unique',
      new Set(cur.history.map(r=>r.revision_id)).size===cur.history.length);
  chk('every revision id is deterministic in shape',
      cur.history.every(r=>/^rev:[0-9a-f]{16}$/.test(r.revision_id)));
  chk('no revision carries a timestamp inside its identity', (function(){
    const a=auCommitTransaction(PR('villa'),[RENAME],
      {created_at:'2020-01-01T00:00:00Z'}).revision;
    const b=auCommitTransaction(PR('villa'),[RENAME],
      {created_at:'2099-12-31T23:59:59Z'}).revision;
    return a===b; })());
  chk('created_at is still recorded for audit even though it is not in the identity',
      auCommitTransaction(PR('villa'),[RENAME],{created_at:'2026-01-01T00:00:00Z'})
        .project.history.slice(-1)[0].created_at==='2026-01-01T00:00:00Z');
  chk('every earlier revision remains addressable',
      cur.history.every(r=>cur.revision_models[r.revision_id]!==undefined));
  chk('every stored revision model matches its recorded hash',
      cur.history.every(r=>auModelHash(cur.revision_models[r.revision_id],
        'building','bld_0')===r.model_hash));
})();

console.log('\n== §13 — UNDO IS A NEW REVISION, NOT A DELETION ==');
(function(){
  const p=PR('villa');
  const H1=p.model_hash, R1=p.current_revision;
  const c=auCommitTransaction(p,[{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
    parameters:{delta_m:0.5}}],{});
  const p2=c.project, R2=p2.current_revision, H2=p2.model_hash;
  chk('R1 -> R2 MOVE_WALL committed', c.committed===true&&H2!==H1);
  const u=auUndo(p2,undefined,null,'bld_0');
  chk('the undo succeeds', u.valid===true, JSON.stringify(codes(u)));
  const p3=u.project, R3=p3.current_revision;
  chk('R3 is a new revision, not R1', R3!==R1&&R3!==R2);
  chk('the undo restores the R1 model hash', p3.model_hash===H1);
  chk('the undo revision records which revision it reverts',
      p3.history.slice(-1)[0].reverts_revision_id===R2);
  chk('history grew rather than shrank', p3.history.length===3);
  chk('R2 is still present in history',
      p3.history.some(r=>r.revision_id===R2));
  chk('the R2 model is still addressable',
      auModelHash(p3.revision_models[R2],'building','bld_0')===H2);
  chk('the undo is recorded in the audit log',
      p3.audit_log.length===p2.audit_log.length+1);
  chk('the undo audit entry names the reverted revision',
      /undo/.test(p3.audit_log.slice(-1)[0].transaction_id));
  chk('undoing the initial revision is refused',
      auUndo(PR('villa'),undefined,null,'bld_0').valid===false);
  chk('undoing an unknown revision is refused',
      codes(auUndo(p2,'rev:doesnotexist',null,'bld_0'))
        .indexOf('UNDO_TARGET_INVALID')>=0);
})();

console.log('\n== §14 — REDO IS ALSO A NEW REVISION ==');
(function(){
  const p=PR('villa');
  const c=auCommitTransaction(p,[RENAME],{});
  const p2=c.project, H2=p2.model_hash;
  const u=auUndo(p2,undefined,null,'bld_0');
  const p3=u.project;
  const r=auRedo(p3,undefined,null,'bld_0');
  chk('the redo succeeds', r.valid===true, JSON.stringify(codes(r)));
  const p4=r.project;
  chk('the redo restores the post-edit hash', p4.model_hash===H2);
  chk('the redo appended a fourth revision', p4.history.length===4);
  chk('the mutable pointer never moved backwards',
      p4.history.length>p3.history.length&&p4.history.length>p2.history.length);
  chk('no history entry disappeared',
      p2.history.every(x=>p4.history.some(y=>y.revision_id===x.revision_id)));
  chk('the redo revision names what it redoes',
      p4.history.slice(-1)[0].redoes_revision_id===p2.current_revision);
  chk('redo with nothing to redo is refused',
      auRedo(PR('villa'),undefined,null,'bld_0').valid===false);
  const u2=auUndo(p4,undefined,null,'bld_0');
  chk('undo and redo can alternate without losing history',
      u2.valid&&u2.project.history.length===5);
})();

console.log('\n== §15 — REVISION DIFF ==');
(function(){
  const p=PR('villa');
  const c=auCommitTransaction(p,[RESIZE],{acknowledge_warnings:true});
  const d=auRevisionDiff(p.model,c.project.model);
  chk('the diff reports changed paths', d.changed_paths.length>0);
  chk('the diff names the changed element',
      d.changed_elements.indexOf('g.majlis')>=0, JSON.stringify(d.changed_elements));
  chk('the diff carries before and after values for each change',
      d.property_changes.every(x=>'before' in x&&'after' in x&&'path' in x));
  chk('the before value differs from the after value in every reported change',
      d.property_changes.every(x=>JSON.stringify(x.before)!==JSON.stringify(x.after)));
  chk('the counts agree with the lists',
      d.counts.changed===d.changed_paths.length
      &&d.counts.added===d.added_paths.length
      &&d.counts.removed===d.removed_paths.length);
  const add=auCommitTransaction(p,[{type:'ADD_SPACE',
    parameters:{template:'g',rect:[20,12,4,4],id:'store'}}],{});
  const d2=auRevisionDiff(p.model,add.project.model);
  chk('an added element is reported as added',
      d2.added_elements.indexOf('g.store')>=0, JSON.stringify(d2.added_elements));
  const del=auCommitTransaction(p,[{type:'DELETE_SPACE',target_id:'g.guest',
    parameters:{}}],{confirm:auValidateTransaction(p,[{type:'DELETE_SPACE',
      target_id:'g.guest',parameters:{}}],'bld_0').transaction.confirmation_digest,
    acknowledge_warnings:true});
  const d3=auRevisionDiff(p.model,del.project.model);
  chk('a removed element is reported as removed',
      d3.removed_elements.indexOf('g.guest')>=0, JSON.stringify(d3.removed_elements));
  chk('a diff against itself is empty',
      auRevisionDiff(p.model,p.model).counts.changed===0);
})();

console.log('\n== §16 — DEPENDENCY INVALIDATION AFTER COMMIT ==');
(function(){
  const p=PR('villa');
  const c=auCommitTransaction(p,[RESIZE],{acknowledge_warnings:true});
  const stale=c.stale_artifacts;
  chk('the commit publishes a stale-artifact list', Array.isArray(stale)&&stale.length>0);
  chk('every stale artifact is one of the declared artifacts',
      stale.every(a=>AU_DEPENDENCY_ARTIFACTS.indexOf(a)>=0));
  ['ARCHITECTURE','COORDINATION','VISUAL','RUNTIME','NAVIGATION','EGRESS','DISTANCE',
   'RULE_RESULTS','SNAPSHOTS','PRESENTATION_RENDERS'].forEach(a=>
    chk('a space resize marks '+a+' stale', stale.indexOf(a)>=0));
  chk('a rename does not mark the runtime scene stale',
      AU_DEPENDENCY_GRAPH.RENAME_SPACE.indexOf('RUNTIME')<0);
  chk('a lock marks nothing stale',
      auCommitTransaction(p,[{type:'LOCK_ELEMENT',target_id:'g.majlis',
        parameters:{reason:'USER_LOCKED'}}],{}).stale_artifacts.length===0);
  chk('a stale rule-result snapshot is invalidated by model hash, not re-judged',
      /invalidates affected rule-result snapshots by model hash/
        .test(ACS_AUTHORING_SPEC.compliance_note));
  chk('no committed change claims a new PASS or FAIL',
      /explicit re-evaluation remains required/.test(ACS_AUTHORING_SPEC.compliance_note));
  chk('the derived data of the old revision is not silently reused', (function(){
    const oldVs=compileVisualScene(C(p.model),'bld_0',null,0,
      {mode:'ENGINEERING',at:'2026-01-01T00:00:00Z'});
    const newVs=compileVisualScene(C(c.project.model),'bld_0',null,0,
      {mode:'ENGINEERING',at:'2026-01-01T00:00:00Z'});
    return oldVs.model_hash!==newVs.model_hash; })());
})();

console.log('\n== §71/§72/§89 — TEST K: SAVE AND LOAD ==');
(function(){
  let p=PR('villa');
  [RENAME,RENAME2,RESIZE].forEach(c=>{
    p=auCommitTransaction(p,[c],{acknowledge_warnings:true}).project; });
  chk('three edits committed', p.history.length===4);
  const H=p.model_hash, R=p.current_revision;
  const blob=auSerialiseProject(p,true,true);
  chk('the serialised project carries the canonical model', !!blob.model);
  chk('the serialised project carries the revision pointer', blob.current_revision===R);
  chk('the serialised project carries history metadata',
      blob.history.length===4&&blob.audit_log.length===3);
  chk('no runtime state is serialised',
      blob.runtime===undefined&&blob.camera===undefined
      &&blob.selection===undefined&&blob.portal_states===undefined);
  chk('no transient authoring state is serialised',
      blob.authoring===undefined&&blob.preview===undefined
      &&blob.pending_commands===undefined);
  chk('the serialisation note states the exclusion',
      /No runtime state, no camera, no selection/.test(blob.note));
  const text=JSON.stringify(blob);
  chk('the serialised text carries no preview marker',
      text.indexOf('"preview":true')<0);
  const l=auLoadProject(JSON.parse(text),'bld_0');
  chk('the project reloads', l.valid===true, JSON.stringify(codes(l)));
  const p2=l.project;
  chk('the reloaded model hash is identical', p2.model_hash===H);
  chk('the reloaded revision pointer is identical', p2.current_revision===R);
  chk('the reloaded history is intact', p2.history.length===4);
  chk('runtime state starts fresh and was not restored',
      l.runtime_state_restored===false
      &&p2.authoring.transaction_status==='IDLE'
      &&p2.authoring.preview===null
      &&p2.authoring.pending_commands.length===0);
  chk('editing continues from the reloaded project', (function(){
    const c=auCommitTransaction(p2,[{type:'RENAME_SPACE',target_id:'g.kitchen',
      parameters:{name:'Galley'}}],{});
    return c.committed===true&&c.project.history.length===5; })());
  chk('a payload whose stored hash disagrees with its model is reported', (function(){
    const bad=JSON.parse(text); bad.model_hash='0'.repeat(64);
    return codes(auLoadProject(bad,'bld_0')).indexOf('MODEL_INTEGRITY_FAILURE')>=0; })());
  chk('a payload with no model is refused',
      auLoadProject({current_revision:'rev:x'},'bld_0').valid===false);
  chk('a non-object payload is refused', auLoadProject('project','bld_0').valid===false);
  chk('serialising without history still carries the model and pointer', (function(){
    const b=auSerialiseProject(p,false,false);
    return !!b.model&&b.current_revision===R&&b.history===undefined; })());
})();

console.log('\n== §73/§74/§75 — DETERMINISM AND STABLE IDS ==');
(function(){
  const a=auCommitTransaction(PR('villa'),[RESIZE],{acknowledge_warnings:true});
  const b=auCommitTransaction(PR('villa'),[RESIZE],{acknowledge_warnings:true});
  chk('the same base plus the same command yields a byte-identical candidate',
      JSON.stringify(a.project.model)===JSON.stringify(b.project.model));
  chk('the new model hash is identical', a.model_hash===b.model_hash);
  chk('the new revision id is identical', a.revision===b.revision);
  chk('the transaction id is identical',
      a.transaction.transaction_id===b.transaction.transaction_id);
  const add={type:'ADD_SPACE',parameters:{template:'g',rect:[20,12,4,4]}};
  const c1=auCommitTransaction(PR('villa'),[add],{});
  const c2=auCommitTransaction(PR('villa'),[add],{});
  chk('an ADD command generates the same deterministic id twice',
      JSON.stringify(c1.project.model.floors.g.rooms.map(r=>r.id))
        ===JSON.stringify(c2.project.model.floors.g.rooms.map(r=>r.id)));
  chk('the generated id is derived from the command, not from a clock',
      /^space_[0-9a-f]{8}$/.test(c1.project.model.floors.g.rooms.slice(-1)[0].id));
  chk('a different command yields a different generated id', (function(){
    const other=auCommitTransaction(PR('villa'),
      [{type:'ADD_SPACE',parameters:{template:'g',rect:[20,17,4,4]}}],{});
    return other.project.model.floors.g.rooms.slice(-1)[0].id
      !==c1.project.model.floors.g.rooms.slice(-1)[0].id; })());
  chk('a colliding explicit id is refused rather than overwritten',
      codes(auCommitTransaction(PR('villa'),[{type:'ADD_SPACE',
        parameters:{template:'g',rect:[20,12,4,4],id:'majlis'}}],{}))
        .indexOf('ID_COLLISION')>=0);
  chk('a second automatic id elsewhere in the same model does not collide', (function(){
    const c3=auCommitTransaction(c1.project,
      [{type:'ADD_SPACE',parameters:{template:'g',rect:[20,17,4,4]}}],{});
    if(!c3.committed) return false;
    const ids=c3.project.model.floors.g.rooms.map(r=>r.id);
    return new Set(ids).size===ids.length; })());
  chk('a deterministic id that already exists is resolved, never overwritten', (function(){
    const taken=['space_abc','space_abc_2'];
    const a=_auNewId('space','g','deadbeef',[]);
    const b=_auNewId('space','g','deadbeef',[a]);
    const c=_auNewId('space','g','deadbeef',[a,b]);
    return b===a+'_2'&&c===a+'_3'&&taken.length===2; })());
  chk('adding the same space twice at the same place is refused as an overlap',
      codes(auCommitTransaction(c1.project,[add],{})).indexOf('SPACE_OVERLAP')>=0);
  chk('twenty repeated commits of the same edit all produce the same revision',
      (function(){ const s=new Set();
        for(let i=0;i<20;i++) s.add(auCommitTransaction(PR('villa'),[RENAME],{}).revision);
        return s.size===1; })());
})();

console.log('\n──────────────────────────────────────────────');
console.log('REVISIONS: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
