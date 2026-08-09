const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const LIB=require(_np.join(HERE,'lib_workspace_fixtures.js'));
const FX=LIB.models(), MEPF=LIB.mep();
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const PR=n=>auCreateProject(C(FX[n]||MEPF[n]),'bld_0','IMPORT',null);
const ARCH=p=>compileArchitecture(C(p.model),'bld_0',null,0);
const codes=r=>r.issues.map(i=>i.code);
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_workspace.json'),'utf8'));

/* ============================================================================
   المرحلة 6 — سير العمل الحقيقي: إنشاء · تحديد · تحرير · معاينة · إيداع
   ========================================================================== */
const WSAPI = (typeof WS!=='undefined')?WS:null;

console.log('\n== §13/§14 — VIEW AND EDIT MODES ==');
(function(){
  chk('two modes are declared and VIEW is the default',
      JSON.stringify(ACS_WORKSPACE_SPEC.ui_modes)===JSON.stringify(['VIEW','EDIT'])
      &&ACS_WORKSPACE_SPEC.default_ui_mode==='VIEW');
  const p=PR('villa');
  const H=p.model_hash;
  const ui=wsUiStateDefault();
  chk('a fresh workspace starts in VIEW', ui.ui_mode==='VIEW');
  ui.ui_mode='EDIT';
  chk('entering EDIT mode creates no transaction and no revision',
      p.history.length===1&&wsModelHashOf(p)===H);
  chk('the mode is UI state, not model state',
      wsClassifyStateKey('ui_mode')==='UI_STATE');
  chk('every declared view capability is a read-only capability',
      ACS_WORKSPACE_SPEC.view_mode_capabilities.every(c=>
        ['ORBIT','PAN','ZOOM','WALK','FLY','SELECT','INSPECT','MEASURE'].indexOf(c)>=0));
  chk('the specification states that entering edit mode creates nothing',
      /Entering EDIT mode creates nothing/.test(ACS_WORKSPACE_SPEC.edit_mode_note));
})();

console.log('\n== §14 — ONLY POSSIBLE OPERATIONS ARE OFFERED ==');
(function(){
  const sp=wsAvailableOperations('SPACE',false);
  chk('a space offers resize, rename and delete',
      ['RESIZE_SPACE','RENAME_SPACE','DELETE_SPACE'].every(o=>
        sp.some(x=>x.operation===o&&x.enabled)));
  const dr=wsAvailableOperations('DOOR',false);
  chk('a door offers move, properties and delete',
      ['MOVE_DOOR','CHANGE_DOOR_PROPERTIES','DELETE_DOOR'].every(o=>
        dr.some(x=>x.operation===o&&x.enabled)));
  chk('a door is not offered a space resize',
      !dr.some(x=>x.operation==='RESIZE_SPACE'));
  const wl=wsAvailableOperations('WALL',false);
  chk('a derived wall offers only the source-boundary move',
      wl.filter(x=>x.operation!=='INSPECT').every(x=>x.operation==='MOVE_WALL'));
  chk('a coordination finding offers inspection only',
      wsAvailableOperations('COORDINATION_FINDING',false)
        .every(x=>x.operation==='INSPECT'));
  chk('a runtime obstacle offers inspection only',
      wsAvailableOperations('RUNTIME_OBSTACLE',false)
        .every(x=>x.operation==='INSPECT'));
  const locked=wsAvailableOperations('SPACE',true);
  chk('a locked element offers nothing that would mutate it',
      locked.filter(x=>x.operation!=='INSPECT').every(x=>x.enabled===false
        &&x.reason==='TARGET_LOCKED'));
  chk('every offered operation maps to a real command type',
      sp.filter(x=>x.command_type).every(x=>AU_COMMAND_TYPES.indexOf(x.command_type)>=0));
  chk('an unimplemented command is offered as disabled with its reason',
      wsAvailableOperations('SPACE',false).every(x=>x.enabled
        ||['TARGET_LOCKED','COMMAND_NOT_IMPLEMENTED'].indexOf(x.reason)>=0));
})();

console.log('\n== §80 — TEST C: EDIT THROUGH THE AUTHORING PATH ==');
(function(){
  const p=PR('villa');
  const H1=p.model_hash, R1=p.current_revision;
  const cmd={type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:6,d:4}};
  const pv=auPreviewCommand(p.model,cmd,null,'bld_0',null,null);
  chk('the UI edit produces a preview through the authoring engine', pv.valid===true);
  chk('the preview declares itself a preview and not committed',
      pv.preview.preview===true&&pv.preview.committed===false);
  chk('the canonical hash is unchanged after the preview',
      wsModelHashOf(p)===H1&&p.model_hash===H1);
  chk('no revision was created by the preview', p.history.length===1);
  const c=auCommitTransaction(p,[cmd],{acknowledge_warnings:true,created_at:AT});
  chk('the explicit commit succeeds', c.committed===true, JSON.stringify(codes(c)));
  chk('a new revision was created', c.project.current_revision!==R1);
  chk('the committed hash equals the previewed candidate hash',
      c.model_hash===pv.preview.candidate_model_hash);
  chk('the previous project object is still at the old hash', p.model_hash===H1);
  const t2=wsProjectTree(c.project,ARCH(c.project),null,'en');
  chk('the tree rebuilds from the new revision',
      t2.root.meta.revision===c.project.current_revision);
  const insp=wsInspectorModel(c.project,'g.majlis',ARCH(c.project),null,null,'en');
  const rect=(insp.sections.GEOMETRY||[]).filter(f=>f.field==='space.rect')[0];
  chk('the inspector shows the edited geometry',
      JSON.stringify(rect.display.raw)===JSON.stringify([0,0,6,4]));
})();

console.log('\n== §81 — TEST D: CANCEL LEAVES EVERYTHING UNCHANGED ==');
(function(){
  const p=PR('villa');
  const H=p.model_hash, R=p.current_revision;
  const cmd={type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',parameters:{delta_m:0.5}};
  const pv=auPreviewCommand(p.model,cmd,null,'bld_0',null,null);
  chk('the wall move previews', pv.valid===true);
  const cancel=auCancelPreview(p);
  chk('cancelling returns the transaction to IDLE', cancel.state==='IDLE');
  chk('the canonical model hash is unchanged', wsModelHashOf(p)===H&&p.model_hash===H);
  chk('the revision pointer is unchanged', p.current_revision===R);
  chk('no revision was appended', p.history.length===1);
  chk('the tree still reflects the original model',
      wsProjectTree(p,ARCH(p),null,'en').root.meta.model_hash===String(H).slice(0,24));
})();

console.log('\n== §82 — TEST E: DELETE SHOWS EXACT DEPENDENCIES ==');
(function(){
  const p=PR('villa');
  const H=p.model_hash;
  const cmd={type:'DELETE_SPACE',target_id:'g.majlis',parameters:{}};
  const v=auValidateTransaction(p,[cmd],'bld_0');
  const txn=v.transaction;
  chk('the delete is dependency-breaking', txn.dependency_breaking.length>0);
  chk('every broken dependency is a named identifier, not a vague count',
      txn.dependency_breaking.every(d=>typeof d==='string'&&d.length>2));
  chk('the dialog can state exactly what is affected',
      txn.dependency_breaking.some(d=>/door_\d+$/.test(d)));
  chk('the delete requires an explicit confirmation',
      txn.requires_confirmation===true);
  const refused=auCommitTransaction(p,[cmd],{});
  chk('cancelling by not confirming changes nothing',
      refused.committed===false&&wsModelHashOf(p)===H&&p.history.length===1);
  chk('the refusal names the confirmation requirement',
      codes(refused).indexOf('CONFIRMATION_REQUIRED')>=0);
  const done=auCommitTransaction(p,[cmd],
    {confirm:txn.confirmation_digest,acknowledge_warnings:true});
  chk('confirming explicitly performs the delete', done.committed===true);
  chk('no orphan survives the delete',
      auValidateModelIntegrity(done.project.model,'bld_0').valid===true);
})();

console.log('\n== §19 — HOSTED ELEMENT STRATEGY IS ASKED, NEVER ASSUMED ==');
(function(){
  const p=PR('villa');
  const noStrategy=auPreviewCommand(p.model,
    {type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_14',parameters:{delta_m:0.5}},
    null,'bld_0',null,null);
  chk('moving a hosting wall without a strategy is refused',
      codes(noStrategy).indexOf('HOSTED_STRATEGY_REQUIRED')>=0);
  chk('the specification declares no default strategy',
      ACS_AUTHORING_SPEC.default_hosted_element_strategy===null);
  ['KEEP_RELATIVE_POSITION','KEEP_WORLD_POSITION','CANCEL_IF_HOSTED'].forEach(s=>{
    const r=auPreviewCommand(p.model,{type:'MOVE_WALL',
      target_id:'bld_0.flr_0.wall_14',parameters:{delta_m:0.5,hosted_strategy:s}},
      null,'bld_0',null,null);
    chk('the strategy '+s+' is offered and judged', typeof r.valid==='boolean'); });
  chk('all three strategies are presented to the user',
      ACS_AUTHORING_SPEC.hosted_element_strategies.length===3);
})();

console.log('\n== §83 — TEST F: UNDO AND REDO THROUGH PHASE 5 ==');
(function(){
  let p=PR('villa');
  const H1=p.model_hash;
  const c1=auCommitTransaction(p,[{type:'RENAME_SPACE',target_id:'g.majlis',
    parameters:{name:'A'}}],{created_at:AT});
  const c2=auCommitTransaction(c1.project,[{type:'RENAME_SPACE',target_id:'g.living',
    parameters:{name:'B'}}],{created_at:AT});
  chk('two edits committed', c1.committed&&c2.committed
      &&c2.project.history.length===3);
  const u=auUndo(c2.project,undefined,AT,'bld_0');
  chk('undo produces a new forward revision',
      u.valid&&u.project.history.length===4);
  chk('undo restores the previous hash', u.model_hash===c1.model_hash);
  const r=auRedo(u.project,undefined,AT,'bld_0');
  chk('redo produces another new forward revision',
      r.valid&&r.project.history.length===5);
  chk('redo restores the later hash', r.model_hash===c2.model_hash);
  chk('no history entry was ever removed',
      c2.project.history.every(x=>r.project.history.some(y=>
        y.revision_id===x.revision_id)));
  chk('the UI has no independent undo stack that could disagree',
      Object.keys(wsUiStateDefault()).every(k=>!/undo|redo|history/i.test(k)));
})();

console.log('\n== §21/§22 — REVISION HISTORY AND DIFF ==');
(function(){
  const p=PR('villa');
  const c=auCommitTransaction(p,[{type:'RESIZE_SPACE',target_id:'g.majlis',
    parameters:{w:6,d:4}}],{acknowledge_warnings:true,created_at:AT});
  const h=c.project.history;
  chk('every revision record carries the fields the panel shows',
      h.every(r=>'revision_id' in r&&'created_at' in r&&'summary' in r
        &&'authoring_source' in r&&'changed_paths' in r));
  chk('the history panel data is append-only', h.length===2);
  const snaps=c.project.revision_models;
  const d=auRevisionDiff(snaps[p.current_revision],snaps[c.revision]);
  chk('a human-readable diff is available', d.property_changes.length>0);
  chk('each change names a path with a before and an after',
      d.property_changes.every(x=>x.path&&'before' in x&&'after' in x));
  chk('the diff names the changed element', d.changed_elements.indexOf('g.majlis')>=0);
  chk('inspecting a revision does not switch the canonical revision',
      c.project.current_revision===c.revision);
  chk('the diff writes nothing', (function(){
    const H=c.project.model_hash;
    auRevisionDiff(snaps[p.current_revision],snaps[c.revision]);
    return c.project.model_hash===H; })());
})();

console.log('\n== §89 — TEST L: SAVE AND LOAD ==');
(function(){
  let p=PR('villa');
  ['A','B','C'].forEach(n=>{
    p=auCommitTransaction(p,[{type:'RENAME_SPACE',target_id:'g.majlis',
      parameters:{name:n}}],{created_at:AT}).project; });
  const H=p.model_hash, R=p.current_revision;
  const blob=auSerialiseProject(p,true,true);
  const text=JSON.stringify(blob);
  chk('the export carries no runtime state',
      text.indexOf('"camera"')<0&&text.indexOf('"portal_states"')<0
      &&text.indexOf('"measurements"')<0);
  chk('the export carries no UI state',
      text.indexOf('"selected_id"')<0&&text.indexOf('"tree_expanded"')<0
      &&text.indexOf('"active_panel"')<0&&text.indexOf('"theme"')<0);
  const l=auLoadProject(JSON.parse(text),'bld_0');
  chk('the project reloads', l.valid===true);
  chk('the canonical hash is identical after reload', l.project.model_hash===H);
  chk('the current revision is identical after reload',
      l.project.current_revision===R);
  chk('runtime state starts fresh', l.runtime_state_restored===false);
  chk('the reloaded tree rebuilds identically',
      JSON.stringify(wsProjectTree(l.project,null,null,'en'))
        ===JSON.stringify(wsProjectTree(p,null,null,'en')));
  const bad=JSON.parse(text); bad.model_hash='0'.repeat(64);
  chk('a corrupted payload is reported explicitly',
      auLoadProject(bad,'bld_0').issues.some(i=>
        i.code==='MODEL_INTEGRITY_FAILURE'));
  chk('an incompatible payload is refused',
      auLoadProject({not:'a project'},'bld_0').valid===false);
})();

console.log('\n== §48/§49/§50 — EXPORT CENTER ==');
(function(){
  const p=PR('villa');
  WS_EXPORT_KINDS.forEach(k=>{
    const d=wsExportDescriptor(p,k,'COMMITTED',null,AT);
    chk('the export kind '+k+' produces a descriptor', d.valid===true);
    chk(k+' is taken from the committed revision by default',
        d.descriptor.source==='COMMITTED'&&d.descriptor.is_preview===false);
    chk(k+' embeds the revision and model hash',
        d.descriptor.metadata.revision_id===p.current_revision
        &&d.descriptor.metadata.model_hash===p.model_hash);
    chk(k+' certifies nothing', d.descriptor.certifies_nothing===true); });
  const pv=wsExportDescriptor(p,'GLB','PREVIEW',null,AT);
  chk('a preview export is labelled PREVIEW in the filename',
      pv.descriptor.filename.indexOf('PREVIEW_')===0);
  chk('a preview export is labelled PREVIEW in the metadata',
      pv.descriptor.metadata.source==='PREVIEW'&&pv.descriptor.is_preview===true);
  chk('an unknown export kind is refused',
      wsExportDescriptor(p,'DWG','COMMITTED',null,null).valid===false);
  chk('an unknown export source is refused',
      wsExportDescriptor(p,'GLB','DRAFT',null,null).valid===false);
  chk('the snapshot metadata carries every declared field',
      ACS_WORKSPACE_SPEC.snapshot_metadata_fields.every(f=>
        f in wsExportDescriptor(p,'SNAPSHOT_PNG','COMMITTED','TOP',AT)
          .descriptor.metadata));
  chk('no export implies certification',
      /implies no certification/.test(
        wsExportDescriptor(p,'GLB','COMMITTED',null,null).descriptor.note));
})();

console.log('\n== §85 — TEST H: AI PROPOSES, NEVER COMMITS ==');
(function(){
  const p=PR('villa');
  const H=p.model_hash;
  const cmd={type:'MOVE_DOOR',target_id:'bld_0.g.majlis.door_0',
    parameters:{offset:3.0},source:'AI_PROPOSAL'};
  const r=wsAssistantProposeEdit(p,null,cmd,'the user asked to move the door');
  chk('the assistant produces a proposal', r.valid===true&&!!r.proposal);
  chk('the proposal is explicitly not committed', r.committed===false
      &&r.proposal.committed===false);
  chk('the proposal is marked PROPOSED_AUTHORING_COMMAND',
      r.proposal.status==='PROPOSED_AUTHORING_COMMAND');
  chk('the proposal requires explicit confirmation',
      r.requires_explicit_confirmation===true);
  chk('producing the proposal changed no model',
      wsModelHashOf(p)===H&&p.history.length===1);
  const noToken=auCommitTransaction(p,[r.proposal.command],{});
  chk('applying without an explicit token is refused',
      noToken.committed===false
      &&codes(noToken).indexOf('AI_COMMIT_NOT_PERMITTED')>=0);
  chk('the refusal changed nothing', wsModelHashOf(p)===H);
  const withToken=auCommitTransaction(p,[r.proposal.command],
    {confirm:'explicit-user-approval'});
  chk('applying with an explicit user action goes through the full validation',
      withToken.committed===true, JSON.stringify(codes(withToken)));
  chk('the committed revision records the AI source honestly',
      withToken.project.history.slice(-1)[0].authoring_source==='AI_PROPOSAL');
  chk('the assistant has no capability that writes',
      WS_ASSISTANT_CAPS.every(c=>!/COMMIT|WRITE|APPLY|SAVE/i.test(c)));
})();

console.log('\n== §53/§54 — AI AMBIGUITY AND CLAIM CLASSES ==');
(function(){
  const dup={meta:{type:'office',name:'dup'},wall_h:3,wall_t:0.2,floor_height:3.2,
    site:{w:20,d:20},levels:[{index:0,template:'g'},{index:1,template:'f'}],
    floors:{g:{rooms:[{id:'corridor',rect:[0,0,6,5]}]},
            f:{rooms:[{id:'corridor',rect:[0,0,6,5]}]}}};
  const p=auCreateProject(dup,'bld_0','IMPORT',null);
  const r=wsAssistantProposeEdit(p,'corridor',
    {type:'RENAME_SPACE',target_id:'x',parameters:{name:'y'}},null);
  chk('an ambiguous phrase is refused', r.valid===false);
  chk('the candidates are returned for the user to choose',
      r.candidates.length>1, JSON.stringify(r.candidates));
  chk('nothing is guessed and nothing is committed',
      r.proposal===null&&r.committed===false);
  chk('the refusal names AMBIGUOUS_TARGET',
      r.issues.some(i=>i.code==='AMBIGUOUS_TARGET'));
  WS_CLAIM_CLASSES.forEach(c=>{
    const claim=wsAssistantClaim(c,'text',null);
    chk('the claim class '+c+' is preserved', claim.claim_class===c); });
  chk('an unknown claim class falls back to UNKNOWN, never to MODEL_FACT',
      wsAssistantClaim('CERTAIN_TRUTH','x',null).claim_class==='UNKNOWN');
  chk('no claim carries engineering authority',
      WS_CLAIM_CLASSES.every(c=>
        wsAssistantClaim(c,'x',null).is_engineering_authority===false));
})();

console.log('\n== §92 — TEST O: VISUAL REFERENCES DO NOT TOUCH GEOMETRY ==');
(function(){
  const p=PR('villa');
  const H=p.model_hash;
  const before=JSON.stringify(p.model);
  let ctx=wsPresentationContext(p);
  chk('the presentation context is separate from the model',
      ctx.is_engineering_data===false&&ctx.writes_to_model===false);
  const r=wsAttachReference(ctx,'STYLE','SPACE','g.majlis',
    'https://example.com/ref.jpg','user','warm majlis');
  chk('a reference attaches', r.valid===true&&!!r.reference);
  ctx=r.context;
  chk('the reference records its kind, scope and target',
      r.reference.kind==='STYLE'&&r.reference.scope==='SPACE'
      &&r.reference.scope_id==='g.majlis');
  chk('the reference declares it is not engineering data',
      r.reference.is_engineering_data===false&&r.reference.affects_geometry===false);
  chk('the engineering model is byte-identical after attaching',
      JSON.stringify(p.model)===before&&wsModelHashOf(p)===H);
  chk('no revision was created', p.history.length===1);
  chk('the model carries no reference field',
      JSON.stringify(p.model).indexOf('reference')<0);
  chk('an unknown reference kind is refused',
      wsAttachReference(ctx,'SMELL','SPACE','g.majlis','u',null,null).valid===false);
  chk('an unknown reference scope is refused',
      wsAttachReference(ctx,'STYLE','GALAXY','g.majlis','u',null,null).valid===false);
  chk('a script payload in a reference is refused',
      wsAttachReference(ctx,'STYLE','SPACE','g.majlis',
        'javascript:alert(1)',null,null).valid===false);
  chk('a script payload in a caption is refused',
      wsAttachReference(ctx,'STYLE','SPACE','g.majlis','https://x/y.jpg',null,
        '<script>alert(1)</script>').valid===false);
  const vi=wsSetVisualIntent(ctx,'style','warm najdi');
  chk('visual intent is accepted as presentation context',
      vi.valid===true&&vi.is_engineering_data===false);
  chk('setting visual intent changes no model', wsModelHashOf(p)===H);
  chk('an unknown intent field is refused',
      wsSetVisualIntent(ctx,'structural_capacity','high').valid===false);
  chk('every declared intent field is accepted',
      WS_VISUAL_INTENT_FIELDS.every(f=>wsSetVisualIntent(ctx,f,'x').valid===true));
  chk('no dimension is inferred from an image',
      /no dimension is inferred/.test(r.reference.note));
  chk('the exported project carries no visual reference as engineering data',
      JSON.stringify(auSerialiseProject(p,true,false)).indexOf('reference_id')<0);
})();

console.log('\n== §59 — THE PHOTOREALISTIC PATH IS DECLARED, NOT BUILT ==');
(function(){
  chk('the pipeline is declared in order',
      JSON.stringify(ACS_WORKSPACE_SPEC.photorealistic_pipeline)===JSON.stringify(
        ['ENGINEERING_MODEL','VISUAL_SCENE','CAMERA','CONTROL_BUFFERS',
         'VISUAL_ENHANCEMENT','PHOTOREALISTIC_IMAGE']));
  chk('it is explicitly not implemented in this phase',
      ACS_WORKSPACE_SPEC.photorealistic_implemented===false);
  chk('the boundary states an image may never alter geometry',
      /no image-generation result may alter engineering geometry/
        .test(ACS_WORKSPACE_SPEC.photorealistic_note));
  chk('no renderer or image generator was added to the workspace layer',
      !/diffusion|stable_diffusion|img2img|controlnet|txt2img/i.test(
        JSON.stringify(ACS_WORKSPACE_SPEC)));
  chk('the pipeline starts at the engineering model and ends at an image',
      ACS_WORKSPACE_SPEC.photorealistic_pipeline[0]==='ENGINEERING_MODEL'
      &&ACS_WORKSPACE_SPEC.photorealistic_pipeline.slice(-1)[0]==='PHOTOREALISTIC_IMAGE');
})();

console.log('\n== §40/§41 — REQUIREMENTS AND COVERAGE ==');
(function(){
  const rep={items:[
    {text:'مجلس 6×5',status:'USER_REQUESTED'},
    {text:'مطبخ',status:'USER_REQUESTED'},
    {text:'ارتفاع الدور 3.2',status:'SYSTEM_DEFAULT'},
    {text:'مصعد',status:'EXCLUDED'},
    {text:'موقف سيارات',status:'UNRESOLVED'},
    {text:'إضاءة',status:'REPRESENTED_ALTERNATIVELY'},
    {text:'حديقة',status:'SOMETHING_ELSE'}]};
  const c=wsRequirementCoverage(rep,'en');
  chk('every declared class is present', WS_REQUIREMENT_CLASSES.every(k=>
    Array.isArray(c.classes[k])));
  chk('user requests are counted separately', c.counts.USER_REQUESTED===2);
  chk('excluded items are counted separately', c.counts.EXCLUDED===1);
  chk('an unknown status becomes UNRESOLVED, never USER_REQUESTED',
      c.counts.UNRESOLVED===2);
  chk('unresolved and excluded are reported together as outstanding',
      c.unresolved===3);
  chk('the report never claims full coverage', c.claims_full_coverage===false);
  chk('no wording implies everything requested was implemented', (function(){
    const s=JSON.stringify(c).toLowerCase();
    return !ACS_WORKSPACE_SPEC.forbidden_coverage_words.some(w=>
      s.indexOf(String(w).toLowerCase())>=0); })());
  chk('the coverage probe is not vacuous',
      ACS_WORKSPACE_SPEC.forbidden_coverage_words.indexOf('complete coverage')>=0);
  chk('reading coverage writes nothing', c.writes_to_model===false);
})();

console.log('\n== §33/§34 — MEASUREMENT HONESTY ==');
(function(){
  chk('the three measurement kinds are distinguished',
      JSON.stringify(WS_MEASUREMENT_KINDS)===JSON.stringify(
        ['VIEWPORT_MEASUREMENT','CANONICAL_GEOMETRY_MEASUREMENT','WALKING_DISTANCE']));
  chk('a viewport measurement is labelled as such in both languages',
      ACS_WORKSPACE_SPEC.measurement_labels.VIEWPORT_MEASUREMENT.en
        ==='Viewport measurement'
      &&ACS_WORKSPACE_SPEC.measurement_labels.VIEWPORT_MEASUREMENT.ar==='قياس في العرض');
  chk('a viewport measurement is never presented as a walking distance',
      /never presented as a verified walking distance/
        .test(ACS_WORKSPACE_SPEC.measurement_note));
  chk('a partial distance is never shown as complete',
      /PARTIAL distance result is never shown as a complete one/
        .test(ACS_WORKSPACE_SPEC.measurement_note));
  chk('a path overlay is never called safe or approved',
      /never labelled a safe, approved or code-compliant route/
        .test(ACS_WORKSPACE_SPEC.path_overlay_note));
  const p=PR('villa');
  const vs=compileVisualScene(C(p.model),'bld_0',null,0,{mode:'ENGINEERING',at:AT});
  const rs=compileRuntimeScene(vs,null);
  const m=createRuntimeMeasurement(rs,'POINT_TO_POINT',{start:[0,0,0],end:[3,4,0]});
  chk('a canonical geometry measurement comes from the runtime engine',
      m.valid&&m.measurement.distance_m===5);
  chk('that measurement declares it is not a code check',
      /never a code check/.test(m.measurement.note));
})();

console.log('\n──────────────────────────────────────────────');
console.log('WORKFLOW: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
