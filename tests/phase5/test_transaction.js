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
   المرحلة 5 — المعاملة: المعاينة، التحقّق، الإيداع، الذرّية، حرس المراجعة
   ========================================================================== */
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_authoring.json'),'utf8'));
const RENAME={type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'Grand Majlis'}};

console.log('\n== §6 — TRANSACTION LIFECYCLE ==');
(function(){
  const p=PR('villa');
  chk('a fresh project is IDLE', p.authoring.transaction_status==='IDLE');
  const b=auBeginEdit(p);
  chk('beginning an edit enters DRAFT', b.state==='DRAFT'
      &&p.authoring.transaction_status==='DRAFT');
  chk('the draft pins the base revision', b.base_revision===p.current_revision);
  const pv=prev(p.model,RENAME);
  chk('a valid preview reaches PREVIEWED', pv.state==='PREVIEWED');
  const v=auValidateTransaction(p,[RENAME],'bld_0');
  chk('a valid transaction reaches VALIDATED', v.state==='VALIDATED');
  chk('the model is still untouched at VALIDATED',
      auModelHash(p.model,'building','bld_0')===p.model_hash);
  const c=auCommitTransaction(p,[RENAME],{});
  chk('an explicit commit reaches COMMITTED', c.state==='COMMITTED'&&c.committed===true);
  chk('the returned project is a new object, not the old one', c.project!==p);
  chk('the old project object still holds the old revision',
      p.current_revision!==c.revision);
  const bad=auValidateTransaction(p,[{type:'RENAME_SPACE',target_id:'nope',
    parameters:{name:'x'}}],'bld_0');
  chk('an invalid target reaches REJECTED', bad.state==='REJECTED');
  const stale=auValidateTransaction(p,[Object.assign({base_revision:'rev:old'},RENAME)],'bld_0');
  chk('a stale base revision reaches STALE_BASE_REVISION',
      stale.state==='STALE_BASE_REVISION');
  const conf=auValidateTransaction(p,[{type:'DELETE_WALL',
    target_id:'bld_0.flr_0.wall_0',parameters:{}}],'bld_0');
  chk('a dependency conflict reaches CONFLICT', conf.state==='CONFLICT');
  const inv=auValidateTransaction(p,[{type:'NOT_A_COMMAND',parameters:{}}],'bld_0');
  chk('an unknown command reaches INVALID_COMMAND', inv.state==='INVALID_COMMAND');
})();

console.log('\n== §79 — TEST A: PREVIEW MOVE WALL, THEN CANCEL ==');
(function(){
  const p=PR('villa');
  const H1=p.model_hash;
  const r=prev(p.model,{type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
    parameters:{delta_m:0.5}});
  chk('the preview succeeds', r.valid, JSON.stringify(codes(r)));
  chk('the base model hash is still H1', r.preview.base_model_hash===H1);
  chk('the candidate is a different hash H2', r.preview.candidate_model_hash!==H1);
  chk('the preview declares itself a preview and not committed',
      r.preview.preview===true&&r.preview.committed===false);
  chk('the canonical model object is untouched after the preview',
      auModelHash(p.model,'building','bld_0')===H1&&p.model_hash===H1);
  chk('the project revision did not move', p.current_revision
      ===PR('villa').current_revision);
  const vs=compileVisualScene(C(r.candidate),'bld_0',null,0,
    {mode:'ENGINEERING',at:'2026-01-01T00:00:00Z'});
  const vsBase=compileVisualScene(C(p.model),'bld_0',null,0,
    {mode:'ENGINEERING',at:'2026-01-01T00:00:00Z'});
  chk('a visual preview built from the candidate differs from the base scene',
      JSON.stringify(vs.objects)!==JSON.stringify(vsBase.objects));
  chk('the preview visual scene compiles from the candidate, never from the canonical model',
      vs.model_hash!==vsBase.model_hash);
  const cancel=auCancelPreview(p);
  chk('cancelling returns to IDLE', cancel.state==='IDLE');
  chk('after cancelling, the current model hash is still H1',
      p.model_hash===H1&&auModelHash(p.model,'building','bld_0')===H1);
  chk('cancelling leaves no pending command and no preview',
      p.authoring.pending_commands.length===0&&p.authoring.preview===null);
  chk('cancelling created no revision', p.history.length===1);
})();

console.log('\n== §80 — TEST B: COMMIT MOVE WALL ==');
(function(){
  const p=PR('villa');
  const R1=p.current_revision, H1=p.model_hash;
  const cmd={type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',parameters:{delta_m:0.5}};
  const c=auCommitTransaction(p,[cmd],{created_at:'2026-01-01T00:00:00Z'});
  chk('the commit succeeds', c.committed===true, JSON.stringify(codes(c)));
  const p2=c.project;
  chk('R1 advanced to a new revision R2', p2.current_revision!==R1);
  chk('the new revision id follows the declared pattern',
      /^rev:[0-9a-f]{16}$/.test(p2.current_revision));
  chk('the model hash changed', p2.model_hash!==H1);
  chk('a revision history entry was appended', p2.history.length===p.history.length+1);
  const rec=p2.history[p2.history.length-1];
  ['revision_id','parent_revision_id','model_hash','command_id','authoring_source',
   'created_at','summary','changed_paths'].forEach(k=>
    chk('the revision record carries '+k, k in rec));
  chk('the record names its parent revision', rec.parent_revision_id===R1);
  chk('the record names the command that produced it',
      rec.command_hash===auCommandHash(cmd,null));
  chk('the record lists the changed paths', rec.changed_paths.length>0);
  chk('the commit reports which derived artifacts went stale',
      c.stale_artifacts.length>0
      &&c.stale_artifacts.every(a=>AU_DEPENDENCY_ARTIFACTS.indexOf(a)>=0));
  chk('coordination, visual and runtime are all marked stale',
      ['COORDINATION','VISUAL','RUNTIME'].every(a=>c.stale_artifacts.indexOf(a)>=0));
  chk('structure, MEP and FLS are not marked stale by an architectural edit',
      ['STRUCTURE','MEP','FLS'].every(a=>c.stale_artifacts.indexOf(a)<0));
  chk('the downstream layers rebuild from the new revision', (function(){
    const vs=compileVisualScene(C(p2.model),'bld_0',null,0,
      {mode:'ENGINEERING',at:'2026-01-01T00:00:00Z'});
    const rs=compileRuntimeScene(vs,null);
    return rs.objects.length>0&&rs.source_scene===vs.scene_id; })());
  chk('the previous model object was not mutated by the commit',
      auModelHash(p.model,'building','bld_0')===H1);
  chk('the previous revision stays addressable by its own hash',
      p2.revision_models[R1]!==undefined
      &&auModelHash(p2.revision_models[R1],'building','bld_0')===H1);
})();

console.log('\n== §67 — AUDIT LOG ==');
(function(){
  const p=PR('villa');
  const c=auCommitTransaction(p,[RENAME],{source:'USER',actor_id:null,
    created_at:'2026-01-01T00:00:00Z'});
  const a=c.audit;
  ['transaction_id','command_ids','command_hashes','source','actor_id','base_revision',
   'new_revision','model_hash_before','model_hash_after','changed_paths',
   'validation_summary','created_at'].forEach(k=>
    chk('the audit entry records '+k, k in a));
  chk('the audit entry is appended to the project log',
      c.project.audit_log.length===p.audit_log.length+1);
  chk('the audit records the before and after model hashes distinctly',
      a.model_hash_before!==a.model_hash_after);
  chk('the audit records zero errors for a successful commit',
      a.validation_summary.errors===0);
  chk('the audit carries no secret, token or reasoning trace',
      !/secret|token|api[_-]?key|chain.of.thought|reasoning/i
        .test(JSON.stringify(a).replace(/confirmation token/gi,'')
          .replace(/no secret, token or AI reasoning trace is recorded here/gi,'')));
  chk('the audit note states the exclusion explicitly',
      /no secret, token or AI reasoning trace is recorded here/.test(a.note));
  chk('the transaction id follows the declared pattern',
      /^txn:[0-9a-f]{16}$/.test(a.transaction_id));
})();

console.log('\n== §81 — TEST C: STALE BASE REVISION ==');
(function(){
  const p=PR('villa');
  const R1=p.current_revision;
  const old={type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'From R1'},
    base_revision:R1};
  const c1=auCommitTransaction(p,[{type:'RENAME_SPACE',target_id:'g.living',
    parameters:{name:'Advanced'}}],{});
  const p2=c1.project;
  chk('the project advanced to R2', p2.current_revision!==R1);
  const H2=p2.model_hash;
  const c2=auCommitTransaction(p2,[old],{});
  chk('the stale command is refused', c2.committed===false);
  chk('the refusal is STALE_BASE_REVISION',
      codes(c2).indexOf('STALE_BASE_REVISION')>=0, JSON.stringify(codes(c2)));
  chk('the refusal names both revisions',
      c2.issues.some(i=>/authored against revision .* but the current revision is/
        .test(String(i.detail))));
  chk('zero mutation followed the refusal',
      p2.model_hash===H2&&auModelHash(p2.model,'building','bld_0')===H2);
  chk('no revision was appended by the refusal', p2.history.length===2);
  chk('the same command against the current revision is accepted', (function(){
    const fresh=Object.assign({},old,{base_revision:p2.current_revision});
    return auCommitTransaction(p2,[fresh],{}).committed===true; })());
  chk('a command with no base revision is not treated as stale',
      auCommitTransaction(p2,[{type:'RENAME_SPACE',target_id:'g.majlis',
        parameters:{name:'No base'}}],{}).committed===true);
})();

console.log('\n== §82 — TEST D: DOOR HOST RANGE ==');
(function(){
  const p=PR('villa');
  const H=p.model_hash;
  const far=auCommitTransaction(p,[{type:'MOVE_DOOR',
    target_id:'bld_0.g.majlis.door_0',parameters:{offset:99}}],{});
  chk('a door moved beyond its host is rejected', far.committed===false);
  chk('the rejection is an out-of-range opening',
      codes(far).indexOf('OPENING_OUT_OF_RANGE')>=0);
  chk('the model is untouched after the rejection', p.model_hash===H);
  const ok=prev(p.model,{type:'MOVE_DOOR',target_id:'bld_0.g.majlis.door_0',
    parameters:{offset:3.0}});
  chk('a door moved inside its host range previews valid', ok.valid);
  chk('the valid preview leaves no opening without a host',
      auValidateModelIntegrity(ok.candidate,'bld_0').issues
        .filter(i=>i.code==='HOST_INVALID').length===0);
})();

console.log('\n== §83 — TEST E: DELETE WITH DEPENDENCIES ==');
(function(){
  const p=PR('villa');
  const H=p.model_hash;
  const del={type:'DELETE_SPACE',target_id:'g.majlis',parameters:{}};
  const v=auValidateTransaction(p,[del],'bld_0');
  chk('deleting a space that hosts openings requires confirmation',
      v.transaction.requires_confirmation===true);
  chk('the dependency list is not empty and names exact ids',
      v.transaction.dependencies.length>0);
  const noConfirm=auCommitTransaction(p,[del],{});
  chk('the commit without a confirmation token is refused',
      noConfirm.committed===false
      &&codes(noConfirm).indexOf('CONFIRMATION_REQUIRED')>=0);
  const wrong=auCommitTransaction(p,[del],{confirm:'not-the-right-token'});
  chk('a wrong confirmation token is refused',
      wrong.committed===false&&codes(wrong).indexOf('CONFIRMATION_REQUIRED')>=0);
  const right=auCommitTransaction(p,[del],
    {confirm:v.transaction.confirmation_digest,acknowledge_warnings:true});
  chk('the commit with the exact confirmation token succeeds',
      right.committed===true, JSON.stringify(codes(right)));
  chk('no orphan opening survives the deletion',
      auValidateModelIntegrity(right.project.model,'bld_0').valid===true);
  chk('the model was untouched by both refusals', p.model_hash===H);
  const wall={type:'DELETE_WALL',target_id:'bld_0.flr_0.wall_0',parameters:{}};
  const wv=auCommitTransaction(p,[wall],{confirm:'anything'});
  chk('deleting a wall that generates a space edge is refused outright',
      wv.committed===false&&codes(wv).indexOf('DEPENDENCY_CONFLICT')>=0);
  chk('a harmless preview needs no confirmation',
      auValidateTransaction(p,[RENAME],'bld_0').transaction
        .requires_confirmation===false);
})();

console.log('\n== §84/§85 — TEST F: BATCH ATOMICITY ==');
(function(){
  const p=PR('villa');
  const H=p.model_hash, R=p.current_revision;
  const batch=[
    {type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'A'}},
    {type:'RENAME_SPACE',target_id:'g.living',parameters:{name:'B'}},
    {type:'RENAME_SPACE',target_id:'g.kitchen',parameters:{name:'C'}},
    {type:'MOVE_DOOR',target_id:'bld_0.g.majlis.door_0',parameters:{offset:999}},
    {type:'RENAME_SPACE',target_id:'g.guest',parameters:{name:'E'}}];
  const v=auValidateTransaction(p,batch,'bld_0');
  chk('the batch is rejected as a whole', v.valid===false);
  chk('each command reports its own result',
      v.transaction.command_results.length===5);
  chk('four commands are accepted individually',
      v.transaction.command_results.filter(r=>r.accepted).length===4);
  chk('exactly one command is refused',
      v.transaction.command_results.filter(r=>!r.accepted).length===1);
  chk('the refused command is the fourth',
      v.transaction.command_results.filter(r=>!r.accepted)[0].index===3);
  const c=auCommitTransaction(p,batch,{confirm:'x',acknowledge_warnings:true});
  chk('the commit changes nothing at all', c.committed===false
      &&p.model_hash===H&&auModelHash(p.model,'building','bld_0')===H);
  chk('no revision was created', p.current_revision===R&&p.history.length===1);
  chk('the transaction declares itself atomic', v.transaction.atomic===true);
  const good=batch.slice(0,3).concat([batch[4]]);
  const c2=auCommitTransaction(p,good,{acknowledge_warnings:true});
  chk('the same batch without the failing command commits as one revision',
      c2.committed===true&&c2.project.history.length===2);
  chk('all four edits landed in that single revision', (function(){
    const rooms=c2.project.model.floors.g.rooms;
    const by={}; rooms.forEach(r=>{by[r.id]=r.name;});
    return by.majlis==='A'&&by.living==='B'&&by.kitchen==='C'&&by.guest==='E'; })());
  chk('a batch beyond the declared cap is refused', (function(){
    const big=[];
    for(let i=0;i<Number(AU_LIMITS.max_commands_per_transaction)+1;i++)
      big.push({type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'n'+i}});
    const r=auValidateTransaction(p,big,'bld_0');
    return codes(r).indexOf('BATCH_TOO_LARGE')>=0; })());
  chk('an empty transaction is refused',
      codes(auValidateTransaction(p,[],'bld_0')).indexOf('INVALID_COMMAND')>=0);
  chk('a non-list transaction is refused',
      codes(auValidateTransaction(p,'RENAME','bld_0')).indexOf('INVALID_COMMAND')>=0);
})();

console.log('\n== §54 — COMMIT POLICY IS DECLARED, NOT HIDDEN ==');
(function(){
  chk('the policy blocks on ERROR', AU_COMMIT_POLICY.block_on.indexOf('ERROR')>=0);
  chk('the warning policy is declared explicitly',
      AU_COMMIT_POLICY.warning_policy_options.indexOf(AU_COMMIT_POLICY.warning_policy)>=0);
  chk('the default warning policy requires explicit acknowledgement',
      AU_COMMIT_POLICY.warning_policy==='ALLOW_WITH_EXPLICIT_ACKNOWLEDGEMENT');
  chk('a silent-allow policy exists only as a deliberate opt-in',
      AU_COMMIT_POLICY.warning_policy_options.indexOf('ALLOW_SILENTLY')>=0
      &&AU_COMMIT_POLICY.warning_policy!=='ALLOW_SILENTLY');
  const p=PR('villa');
  const err=auCommitTransaction(p,[{type:'RESIZE_SPACE',target_id:'g.majlis',
    parameters:{w:0.001,d:5}}],{confirm:'x',acknowledge_warnings:true});
  chk('a model-integrity error always rejects the commit', err.committed===false);
  chk('the policy is stated in the specification rather than only in code',
      /A model-integrity ERROR always rejects the commit/.test(CANON.commit_policy_note));
})();

console.log('\n== §10 — COMMIT SEMANTICS ==');
(function(){
  const p=PR('villa');
  const before=JSON.stringify(p.model);
  const c=auCommitTransaction(p,[RENAME],{});
  chk('1 the base revision was verified as current',
      c.transaction.base_revision===p.current_revision);
  chk('2 the candidate was validated before commit', c.transaction.candidate_model_hash
      ===c.model_hash);
  chk('3 a new canonical model was generated', c.project.model!==p.model);
  chk('4 a new model hash was generated', c.model_hash!==p.model_hash);
  chk('5 a revision record was created',
      c.project.history.slice(-1)[0].revision_id===c.revision);
  chk('6 the parent revision is preserved',
      c.project.history.slice(-1)[0].parent_revision_id===p.current_revision);
  chk('7 stale derived snapshots are named', c.stale_artifacts.length>0);
  chk('8 no in-place mutation happened', JSON.stringify(p.model)===before);
  chk('committing twice from the same base yields the same deterministic revision',
      auCommitTransaction(PR('villa'),[RENAME],{}).revision===c.revision);
})();

console.log('\n== §49 — TRANSACTION SIZE AND PAYLOAD LIMITS ==');
(function(){
  chk('a command cap is declared', Number(AU_LIMITS.max_commands_per_transaction)>0);
  chk('a payload byte cap is declared', Number(AU_LIMITS.max_payload_bytes)>0);
  chk('a nesting cap is declared', Number(AU_LIMITS.max_nesting_depth)>0);
  const p=PR('villa');
  const huge={type:'RENAME_SPACE',target_id:'g.majlis',
    parameters:{name:new Array(900).join('y')}};
  chk('an over-long string is refused before it reaches the model',
      auCommitTransaction(p,[huge],{}).committed===false);
  chk('a memory-exhausting batch is refused rather than attempted', (function(){
    const big=[];
    for(let i=0;i<5000;i++) big.push(RENAME);
    const r=auValidateTransaction(p,big,'bld_0');
    return codes(r).indexOf('BATCH_TOO_LARGE')>=0; })());
})();

console.log('\n──────────────────────────────────────────────');
console.log('TRANSACTIONS: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
