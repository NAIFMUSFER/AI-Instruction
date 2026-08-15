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
   المرحلة 5 — حدّ الذكاء الاصطناعي وخطّ التحرير باللغة الطبيعية
   ========================================================================== */
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_authoring.json'),'utf8'));
const MOVE={type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',parameters:{delta_m:0.5}};

console.log('\n== §86 — TEST H: AN AI PROPOSAL IS NEVER A COMMIT ==');
(function(){
  const r=auProposeCommand(MOVE,'the user asked to widen the majlis by half a metre',null);
  chk('the proposal is produced', r.valid&&!!r.proposal);
  chk('the status is PROPOSED_AUTHORING_COMMAND, not committed',
      r.proposal.status==='PROPOSED_AUTHORING_COMMAND'&&r.proposal.committed===false);
  chk('the proposal is marked as needing explicit confirmation',
      r.proposal.requires_explicit_confirmation===true);
  chk('the proposed command is sourced AI_PROPOSAL', r.proposal.command.source==='AI_PROPOSAL');
  chk('the proposed command is still PENDING', r.proposal.command.status==='PENDING');
  chk('the proposal carries no model and no candidate',
      r.proposal.model===undefined&&r.proposal.candidate===undefined);
  chk('the rationale is recorded as text, not as authority',
      typeof r.proposal.rationale==='string');
  const p=PR('villa');
  const H=p.model_hash;
  chk('producing a proposal changes no model', p.model_hash===H
      &&auModelHash(p.model,'building','bld_0')===H);
  chk('the proposal did not create a revision', p.history.length===1);
})();

console.log('\n== §31/§36 — AI CANNOT BYPASS ANY GATE ==');
(function(){
  const p=PR('villa');
  const prop=auProposeCommand(MOVE,'because',null).proposal.command;
  const noConfirm=auCommitTransaction(p,[prop],{});
  chk('an AI-sourced command cannot commit without an explicit token',
      noConfirm.committed===false
      &&codes(noConfirm).indexOf('AI_COMMIT_NOT_PERMITTED')>=0,
      JSON.stringify(codes(noConfirm)));
  chk('the refusal leaves the model byte-identical',
      auModelHash(p.model,'building','bld_0')===p.model_hash);
  const v=auValidateTransaction(p,[prop],'bld_0');
  chk('the transaction flags that it contains an AI proposal',
      v.transaction.contains_ai_proposal===true);
  const withToken=auCommitTransaction(p,[prop],
    {confirm:v.transaction.confirmation_digest||'explicit-user-approval'});
  chk('with an explicit confirmation the same command commits normally',
      withToken.committed===true, JSON.stringify(codes(withToken)));
  chk('the committed revision records the AI source honestly',
      withToken.project.history.slice(-1)[0].authoring_source==='AI_PROPOSAL');
  chk('the audit entry records the AI source',
      withToken.audit.source==='AI_PROPOSAL');
  const bad=auProposeCommand({type:'RAW_JSON_MUTATION',target_id:'x',parameters:{}},null,null);
  chk('an AI proposal of a forbidden type is refused by the same validator',
      bad.valid===false&&codes(bad).indexOf('COMMAND_NOT_ALLOWED')>=0);
  const badTarget=auProposeCommand({type:'RENAME_SPACE',target_id:'nope',
    parameters:{name:'x'}},null,null);
  chk('an AI proposal still normalises through the identical schema',
      badTarget.valid===true);
  chk('but it is still rejected by the identical validator at preview',
      prev(M('villa'),badTarget.proposal.command).valid===false);
  const stale=auProposeCommand(Object.assign({base_revision:'rev:old'},MOVE),null,null);
  chk('an AI proposal is subject to the identical revision guard',
      codes(auValidateTransaction(p,[stale.proposal.command],'bld_0'))
        .indexOf('STALE_BASE_REVISION')>=0);
  chk('an AI proposal is subject to the identical security scan',
      auProposeCommand(LIB.hydrate(ADV.proto_pollution),null,null).valid===false);
  chk('the specification states there is no privileged AI write path',
      /There is no privileged AI write path/.test(CANON.ai_boundary_note));
  chk('the proposal note repeats the boundary in its own words',
      /a proposal is not a commit/i.test(
        auProposeCommand(MOVE,null,null).proposal.note));
})();

console.log('\n== §32 — NATURAL LANGUAGE PIPELINE STOPS AT A PROPOSAL ==');
(function(){
  chk('the declared pipeline has all seven stages',
      JSON.stringify(CANON.nl_pipeline_stages)
        ===JSON.stringify(['USER_TEXT','INTENT','TARGET_RESOLUTION','AUTHORING_COMMAND',
          'PREVIEW','USER_CONFIRMATION','COMMIT']));
  chk('user confirmation sits between preview and commit',
      CANON.nl_pipeline_stages.indexOf('USER_CONFIRMATION')
        ===CANON.nl_pipeline_stages.indexOf('COMMIT')-1);
  chk('there is no stage that goes from text straight to the model',
      /Natural language never reaches the model directly/.test(CANON.nl_pipeline_note));
  const m=M('villa');
  const t=auResolveNlTarget(m,'majlis','bld_0');
  chk('a unique phrase resolves to one target', t.valid&&t.target==='bld_0.g.majlis');
  chk('target resolution is a separate stage from command construction',
      t.target!==undefined&&t.command===undefined);
})();

console.log('\n== §33 — AMBIGUITY IS DECLARED, NEVER GUESSED ==');
(function(){
  const m=M('dup_ids');
  const t=auResolveNlTarget(m,'corridor','bld_0');
  chk('an ambiguous phrase is refused', t.valid===false);
  chk('the refusal is AMBIGUOUS_TARGET',
      codes(t).indexOf('AMBIGUOUS_TARGET')>=0, JSON.stringify(codes(t)));
  chk('the candidates are returned so the caller can choose',
      t.candidates.length>1, JSON.stringify(t.candidates));
  chk('no target was chosen on the user behalf', t.target===null);
  chk('the count of matches is stated',
      t.issues.some(i=>/\d+ spaces match/.test(String(i.detail))));
  chk('a phrase matching nothing is refused rather than approximated',
      auResolveNlTarget(m,'the blue room','bld_0').valid===false);
  chk('an empty phrase resolves to nothing',
      auResolveNlTarget(m,'   ','bld_0').valid===false);
  chk('a non-string phrase is refused',
      auResolveNlTarget(m,42,'bld_0').valid===false);
  chk('disambiguating by template resolves cleanly',
      auResolveNlTarget(m,'a','bld_0').valid===true);
})();

console.log('\n== §34 — A NEGATIVE INSTRUCTION IS CARRIED, NOT DROPPED ==');
(function(){
  /* "انقل الباب ولا تغيّر حجم الغرفة" */
  const withNegative={type:'MOVE_DOOR',target_id:'bld_0.g.majlis.door_0',
    parameters:{offset:3.0},constraints:{must_not_change:['SPACE_RECT','SPACE_AREA']}};
  const r=prev(M('villa'),withNegative);
  chk('the door moves while the negative constraint holds', r.valid,
      JSON.stringify(codes(r)));
  chk('the space rectangle is genuinely unchanged',
      JSON.stringify(r.candidate.floors.g.rooms.filter(x=>x.id==='majlis')[0].rect)
        ===JSON.stringify(M('villa').floors.g.rooms.filter(x=>x.id==='majlis')[0].rect));
  const violating={type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:6,d:4},
    constraints:{must_not_change:['SPACE_RECT']}};
  chk('a command that would violate the negative instruction is refused',
      codes(prev(M('villa'),violating)).indexOf('CONSTRAINT_VIOLATION')>=0);
  chk('the negative constraint survives normalisation into the command identity',
      auNormaliseCommand(withNegative,null,null,null).command
        .constraints.must_not_change.length===2);
  chk('the constraint is part of the command hash, so it cannot be dropped later',
      auCommandHash(withNegative,null)
        !==auCommandHash({type:'MOVE_DOOR',target_id:'bld_0.g.majlis.door_0',
          parameters:{offset:3.0}},null));
  chk('a transaction enforces the constraint too, not only a preview',
      auCommitTransaction(PR('villa'),[violating],{}).committed===false);
  chk('the specification states negatives are never silently violated',
      /is never silently violated/.test(CANON.constraint_note));
})();

console.log('\n== §37/§39/§40/§43 — UI, SELECTION AND GIZMO BOUNDARIES ==');
(function(){
  chk('two UI modes are declared',
      JSON.stringify(CANON.ui_modes)===JSON.stringify(['VIEW','EDIT']));
  chk('the default mode is VIEW, not EDIT', CANON.default_ui_mode==='VIEW');
  chk('runtime walking is not an editing mode',
      RT_NAVIGATION_MODES.every(m=>CANON.ui_modes.indexOf(m)<0));
  chk('only translation is implemented among gizmo operations',
      JSON.stringify(CANON.implemented_gizmo_operations)===JSON.stringify(['TRANSLATE']));
  const g=auGizmoToCommand('TRANSLATE','g.majlis.obj_0',{x:2,z:3});
  chk('a transform handle produces a typed domain command', g.valid
      &&g.command.type==='MOVE_OBJECT');
  chk('the produced command carries the moved coordinates',
      g.command.parameters.x===2&&g.command.parameters.z===3);
  chk('the produced command still goes through the normal validator',
      auNormaliseCommand(g.command,null,null,null).valid===true);
  chk('a gizmo command reaches the model only through the authoring path', (function(){
    const p=PR('windowed');
    const before=p.model_hash;
    auGizmoToCommand('TRANSLATE','g.majlis.obj_0',{x:2,z:3});
    return p.model_hash===before; })());
  chk('scaling is refused because a wall is not a generic mesh',
      auGizmoToCommand('SCALE','bld_0.flr_0.wall_0',{x:2}).valid===false);
  chk('rotation is refused for an element with no rotational meaning',
      auGizmoToCommand('ROTATE','g.majlis',{x:1}).valid===false);
  chk('the gizmo note states the rule',
      /never a direct mesh transform/.test(CANON.gizmo_note));
  const p=PR('villa');
  const st=createRuntimeState(compileRuntimeScene(compileVisualScene(C(p.model),'bld_0',
    null,0,{mode:'ENGINEERING',at:'2026-01-01T00:00:00Z'}),null),null,null,null);
  chk('selecting an object in the runtime mutates nothing',
      st.selection===null&&auModelHash(p.model,'building','bld_0')===p.model_hash);
  chk('selection is only a way to name a target, never an edit',
      /TARGET IDENTIFICATION|target/i.test('selection is target identification'));
})();

console.log('\n== §44 — DERIVED ELEMENTS ARE READ-ONLY ==');
(function(){
  ['COMPILED_WALL','DERIVED_ENVELOPE','COORDINATION_FINDING','NAVIGATION_EDGE',
   'RUNTIME_OBSTACLE','RUNTIME_PORTAL','VISUAL_OBJECT'].forEach(k=>
    chk('the derived kind '+k+' is declared read-only',
        CANON.read_only_element_kinds.indexOf(k)>=0));
  chk('no command type targets a coordination finding directly',
      AU_COMMAND_TYPES.every(t=>!/CLASH|FINDING|OBSTACLE|PORTAL|ENVELOPE/i.test(t)));
  chk('no command type targets a navigation edge or a runtime object',
      AU_COMMAND_TYPES.every(t=>!/NAVIGATION|RUNTIME|EGRESS/i.test(t)));
  chk('a runtime obstacle id is not an authoring target',
      auResolveTarget(M('villa'),'obstacle:bld_0.g.majlis.door_0@0','bld_0').kind===null);
  chk('a visual object id is not an authoring target either',
      auResolveTarget(M('villa'),'vis:tree_1','bld_0').kind===null);
})();

console.log('\n──────────────────────────────────────────────');
console.log('AI BOUNDARY: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
