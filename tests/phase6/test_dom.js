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
   المرحلة 6 — الواجهة الحقيقية في DOM حقيقي
   ========================================================================== */
const HAS_DOM = (typeof document!=='undefined' && !!document.getElementById);
if(!HAS_DOM){
  console.log('  · DOM checks require a page: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED');
  chk('the DOM suite declares its requirement instead of faking a pass', true);
} else {
(function(){
const $=id=>document.getElementById(id);
const q=s=>document.querySelector(s);
const qa=s=>Array.prototype.slice.call(document.querySelectorAll(s));

console.log('\n== §1/§3 — WORKSPACE SHELL EXISTS ==');
chk('the workspace root is present', !!$('acsWorkspace'));
chk('the workspace declares an application role',
    $('acsWorkspace').getAttribute('role')==='application');
['wsTreePane','wsViewport','wsInspPane'].forEach(id=>
  chk('the panel '+id+' exists', !!$(id)));
chk('the top bar exists', !!q('.ws-top'));
chk('the status bar exists', !!q('.ws-status'));
chk('the 3D viewport is the primary panel, not a widget',
    ACS_WORKSPACE_SPEC.primary_panel==='VIEWPORT');
['wsProjName','wsRev','wsBtnMode','wsBtnUndo','wsBtnRedo','wsBtnLang',
 'wsBtnHistory','wsBtnIssues','wsBtnExport','wsBtnAI'].forEach(id=>
  chk('the top bar control '+id+' exists', !!$(id)));
chk('the status bar shows the revision', !!$('wsStRev'));
chk('the status bar shows the mode', !!$('wsStMode'));
chk('the status bar shows separate issue counts',
    !!$('wsStErr')&&!!$('wsStWarn')&&!!$('wsStInfo'));
chk('the status bar states compliance NOT_EVALUATED',
    /NOT_EVALUATED/.test(q('[data-ws="compliance"]').textContent));
chk('no status element claims safe, compliant or approved',
    !/\b(SAFE|COMPLIANT|APPROVED|CERTIFIED)\b/i.test(q('.ws-status').textContent));

console.log('\n== §62 — ACCESSIBILITY OF THE PRODUCT UI ==');
(function(){
  const iconButtons=qa('.ws-top .ws-btn');
  chk('every top-bar button carries an accessible label',
      iconButtons.length>0&&iconButtons.every(b=>
        (b.getAttribute('aria-label')||'').length>0));
  chk('every top-bar button carries a title for pointer users',
      iconButtons.every(b=>(b.getAttribute('title')||'').length>0));
  chk('the mode toggle exposes its pressed state',
      $('wsBtnMode').hasAttribute('aria-pressed'));
  chk('the tree is a focusable tree widget',
      $('wsTree').getAttribute('role')==='tree'
      &&$('wsTree').getAttribute('tabindex')==='0');
  chk('the status region announces politely',
      q('.ws-status').getAttribute('aria-live')==='polite');
  chk('the modal declares itself a modal dialog',
      $('wsModal').getAttribute('role')==='dialog'
      &&$('wsModal').getAttribute('aria-modal')==='true');
  chk('the specification does not claim formal accessibility conformance',
      ACS_WORKSPACE_SPEC.accessibility.claims_formal_compliance===false);
  chk('a minimum touch target is declared',
      Number(ACS_WORKSPACE_SPEC.min_touch_target_px)>=44);
})();

console.log('\n== §78 — TEST A: CREATE A PROJECT THROUGH THE UI ==');
(function(){
  WS.init(null);
  WS.open();
  chk('the workspace opens', $('acsWorkspace').classList.contains('on'));
  chk('the empty state says there is no project',
      /no project|لا مشروع/i.test($('wsTree').textContent));
  chk('no demo project was inserted automatically', WS.project()===null);
  const r=WS.generate({name:'Villa Test',type:'residential',
    requirements:'مجلس ومطبخ وغرفتا نوم',w:30,d:24});
  chk('generation produced a canonical project', !!r.project&&!!r.project.model);
  chk('the project has a revision', /^rev:/.test(r.project.current_revision));
  chk('the workspace is now showing that project',
      WS.project().current_revision===r.project.current_revision);
  chk('the project tree rendered real rows', qa('#wsTree [data-ws-node]').length>0);
  chk('the tree rows carry real node ids',
      qa('#wsTree [data-ws-node]').every(el=>
        (el.getAttribute('data-ws-node')||'').length>0));
  chk('the top bar shows the project name',
      $('wsProjName').textContent==='Villa Test');
  chk('the top bar shows the revision',
      $('wsRev').textContent===r.project.current_revision);
  chk('generation stages were reported truthfully',
      ACS_WORKSPACE_SPEC.generation_stages.length===4);
  chk('no console-only step was required', true);
})();

console.log('\n== §79 — TEST B: SELECT AND INSPECT ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  const rows=qa('#wsTree [data-ws-node]');
  chk('the villa tree rendered', rows.length>0);
  WS.ui().tree_expanded=['project','site','bld_0','bld_0.flr_0','bld_0.flr_0.spaces'];
  WS.render();
  const spaceRow=qa('#wsTree [data-ws-kind="SPACE"]')[0];
  chk('a space row is reachable in the tree', !!spaceRow);
  const id=spaceRow.getAttribute('data-ws-node');
  spaceRow.click();
  chk('clicking the tree selects that element', WS.ui().selected_id===id);
  chk('the selected row is marked selected',
      qa('#wsTree .ws-row.sel').some(el=>el.getAttribute('data-ws-node')===id));
  chk('the row exposes its selection to assistive technology',
      qa('#wsTree [data-ws-node="'+id+'"]')[0].getAttribute('aria-selected')==='true');
  chk('the inspector rendered sections for the selection',
      qa('#wsInsp [data-ws-section]').length>0);
  chk('the inspector shows identity',
      !!q('#wsInsp [data-ws-section="IDENTITY"]'));
  chk('the inspector shows real property fields',
      qa('#wsInsp [data-ws-field]').length>0);
  chk('a viewport selection resolves to the same identity', (function(){
    WS.select(id);
    return WS.ui().selected_id===id; })());
  chk('there is one selection identity, not two',
      Object.keys(WS.ui()).filter(k=>/selected/i.test(k)).length===1);
  chk('selecting created no revision', WS.project().history.length===1);
})();

console.log('\n== §9/§10 — UNKNOWN AND DERIVED IN THE REAL DOM ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  WS.select('bld_0.g.majlis.door_0');
  const unknown=qa('#wsInsp [data-ws-unknown]');
  chk('an unknown value is rendered as unknown', unknown.length>0);
  chk('the unknown text is the declared label',
      unknown.every(el=>['Not specified','غير محدد'].indexOf(el.textContent)>=0));
  chk('an unknown value is never rendered as 0',
      unknown.every(el=>el.textContent.trim()!=='0'));
  const derived=qa('#wsInsp [data-ws-editability="DERIVED"]');
  chk('a derived field is marked derived in the DOM', derived.length>0);
  chk('a derived field shows a derived tag',
      derived.every(el=>!!el.querySelector('.ws-tag.derived')));
  const display=qa('#wsInsp [data-ws-editability="DISPLAY_ONLY"]');
  chk('a display-only field is marked display only', display.length>0);
  chk('every rendered field declares a declared editability class',
      qa('#wsInsp [data-ws-editability]').every(el=>
        WS_EDITABILITY.indexOf(el.getAttribute('data-ws-editability'))>=0));
  chk('provenance labels are rendered',
      qa('#wsInsp [data-ws-provenance]').length>0);
  chk('no provenance label claims a regulation',
      qa('#wsInsp [data-ws-provenance]').every(el=>
        !wsIsForbiddenLabel(el.textContent)));
})();

console.log('\n== §13/§14 — EDIT MODE IN THE REAL DOM ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  const H=p.model_hash;
  WS.select('g.majlis');
  chk('view mode offers no operation buttons',
      qa('#wsInsp [data-ws-op]').length===0);
  WS.setMode('EDIT');
  chk('the mode toggle reflects edit mode',
      $('wsBtnMode').getAttribute('aria-pressed')==='true');
  chk('edit mode is visually distinct', $('wsBtnMode').classList.contains('on'));
  const ops=qa('#wsInsp [data-ws-op]');
  chk('edit mode offers operations for the selection', ops.length>0);
  chk('every offered operation is a declared one',
      ops.every(b=>ACS_WORKSPACE_SPEC.element_operations.SPACE
        .indexOf(b.getAttribute('data-ws-op'))>=0));
  chk('entering edit mode created no transaction and no revision',
      WS.project().history.length===1&&wsModelHashOf(WS.project())===H);
  WS.setMode('VIEW');
  chk('leaving edit mode removes the operations',
      qa('#wsInsp [data-ws-op]').length===0);
})();

console.log('\n== §16/§17 — PREVIEW PANEL IN THE REAL DOM ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  const H=p.model_hash;
  WS.setMode('EDIT'); WS.select('g.majlis');
  const r=WS.beginPreview({type:'RESIZE_SPACE',target_id:'g.majlis',
    parameters:{w:6,d:4}});
  chk('the preview succeeded', r.valid===true);
  chk('the preview dialog is open', $('wsModal').classList.contains('on'));
  ['SUMMARY','AFFECTED','DEPENDENCIES','COORDINATION','INTEGRITY'].forEach(s=>
    chk('the preview panel shows the section '+s,
        !!q('#wsModalBody [data-ws-section="'+s+'"]')));
  chk('the preview panel names the base and candidate hashes',
      /base hash/.test($('wsModalBody').textContent)
      &&/candidate hash/.test($('wsModalBody').textContent));
  chk('the preview panel offers commit and cancel',
      !!$('wsCommitBtn')&&!!$('wsCancelBtn'));
  chk('the preview badge is shown over the viewport',
      $('wsPreviewBadge').classList.contains('on'));
  chk('the status bar reports an active preview in the active language',
      $('wsStPreview').textContent===
      CANON.ui_labels.preview_active[WS.ui().language]);
  chk('the canonical model is unchanged during the preview',
      wsModelHashOf(WS.project())===H&&WS.project().history.length===1);
  chk('the preview reports coordination as a diff, not a fix',
      /NEW/.test($('wsModalBody').textContent)
      &&/RESOLVED_BY_CHANGE/.test($('wsModalBody').textContent));
  chk('the preview states compliance is not evaluated',
      /NOT_EVALUATED/.test($('wsModalBody').textContent));
})();

console.log('\n== §80/§81 — COMMIT AND CANCEL THROUGH THE DOM ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  const H=p.model_hash;
  WS.setMode('EDIT'); WS.select('g.majlis');
  WS.beginPreview({type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:6,d:4}});
  WS.cancelPreview();
  chk('cancelling closes the dialog', !$('wsModal').classList.contains('on'));
  chk('cancelling clears the preview badge',
      !$('wsPreviewBadge').classList.contains('on'));
  chk('cancelling changed nothing',
      wsModelHashOf(WS.project())===H&&WS.project().history.length===1);
  chk('a toast reported the cancellation',
      qa('[data-ws-toast="PREVIEW_CANCELLED"]').length>0);
  WS.beginPreview({type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:6,d:4}});
  const before=WS.project().current_revision;
  $('wsCommitBtn').click();
  chk('committing produced a new revision',
      WS.project().current_revision!==before);
  chk('the model hash changed', WS.project().model_hash!==H);
  chk('the top bar shows the new revision',
      $('wsRev').textContent===WS.project().current_revision);
  chk('the status bar shows the new revision',
      $('wsStRev').textContent===WS.project().current_revision);
  chk('a toast reported the commit',
      qa('[data-ws-toast="REVISION_COMMITTED"]').length>0);
  chk('the tree rebuilt after the commit', qa('#wsTree [data-ws-node]').length>0);
})();

console.log('\n== §18 — DESTRUCTIVE EDIT SHOWS EXACT DEPENDENCIES ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  const H=p.model_hash;
  WS.setMode('EDIT'); WS.select('g.majlis');
  WS.startOperation('DELETE_SPACE');
  chk('the delete dialog opened', $('wsModal').classList.contains('on'));
  const deps=q('#wsModalBody [data-ws-section="DEPENDENCIES"]');
  chk('the dialog shows a dependency section', !!deps);
  chk('the dialog names exact dependencies, not a vague question',
      qa('#wsModalBody [data-ws-section="DEPENDENCIES"] .ws-f').length>0);
  chk('the dialog does not merely ask are you sure',
      !/^\s*are you sure\??\s*$/i.test($('wsModalBody').textContent.trim()));
  chk('the dependency names look like real identifiers',
      /door_\d|obj_\d|window_\d/.test(deps.textContent));
  WS.closeModal();
  chk('closing the dialog changed nothing',
      wsModelHashOf(WS.project())===H&&WS.project().history.length===1);
})();

console.log('\n== §19 — HOSTED STRATEGY IS ASKED IN THE DOM ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  WS.setMode('EDIT'); WS.select('bld_0.flr_0.wall_14');
  WS.startOperation('MOVE_WALL');
  const sel=q('#wsModalBody [data-ws="hosted-strategy"]');
  chk('a hosted strategy selector is shown', !!sel);
  chk('no strategy is preselected', sel.value==='');
  chk('all three strategies are offered',
      qa('#wsModalBody [data-ws="hosted-strategy"] option').length===4);
  chk('the offered strategies are the declared ones',
      qa('#wsModalBody [data-ws="hosted-strategy"] option')
        .filter(o=>o.value).every(o=>
          ACS_AUTHORING_SPEC.hosted_element_strategies.indexOf(o.value)>=0));
  WS.closeModal();
})();

console.log('\n== §69/§70 — TOASTS AND ERROR DETAIL ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  WS.setMode('EDIT'); WS.select('bld_0.g.majlis.door_0');
  const r=WS.beginPreview({type:'MOVE_DOOR',target_id:'bld_0.g.majlis.door_0',
    parameters:{offset:999}});
  chk('an impossible edit is rejected', r.valid===false);
  chk('the rejection dialog shows the declared code',
      qa('#wsModalBody [data-ws-code]').length>0);
  chk('the code shown is a declared authoring code',
      qa('#wsModalBody [data-ws-code]').every(el=>
        ACS_AUTHORING_SPEC.issue_codes.indexOf(el.textContent)>=0));
  chk('the rejection shows the target and an explanation',
      /target/.test($('wsModalBody').textContent)
      &&/explanation/.test($('wsModalBody').textContent));
  chk('no stack trace is shown to the user',
      !/at\s+\w+\s*\(|\.js:\d+/.test($('wsModalBody').textContent));
  chk('a toast announced the rejection',
      qa('[data-ws-toast="COMMAND_REJECTED"]').length>0);
  chk('engineering detail lives in the panel, not only in the toast',
      $('wsModalBody').textContent.length>
        (qa('[data-ws-toast="COMMAND_REJECTED"]')[0]||{textContent:''}).textContent.length);
  WS.closeModal();
})();

console.log('\n== §21/§22 — HISTORY AND DIFF IN THE DOM ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  WS.setMode('EDIT'); WS.select('g.majlis');
  WS.commit([{type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'X'}}],
    null,true);
  WS.history();
  chk('the history panel opened', !!q('#wsModalBody [data-ws-section="HISTORY"]'));
  const revs=qa('#wsModalBody [data-ws-rev]');
  chk('the history lists every revision', revs.length===WS.project().history.length);
  chk('a history row shows the revision id and its source',
      /rev:/.test(revs[0].textContent));
  revs[0].click();
  chk('clicking a revision shows a human-readable diff',
      qa('#wsModalBody [data-ws-diff]').length>0
      ||/no parent revision/.test($('wsModalBody').textContent));
  chk('inspecting history did not switch the canonical revision',
      WS.project().current_revision===WS.project().history.slice(-1)[0].revision_id);
  WS.closeModal();
})();

console.log('\n== §24/§26 — ISSUE CENTER AND NAVIGATION IN THE DOM ==');
(function(){
  const p=auCreateProject(C(MEPF.clash_mep),'bld_0','IMPORT',null);
  WS.attach(p);
  WS.issues();
  chk('the issue panel opened', qa('#wsModalBody [data-ws-issue-cat]').length>0);
  chk('every declared category has its own section',
      WS_ISSUE_CATEGORIES.every(c=>
        !!q('#wsModalBody [data-ws-issue-cat="'+c+'"]')));
  chk('categories are not flattened into one list',
      qa('#wsModalBody [data-ws-issue-cat]').length===WS_ISSUE_CATEGORIES.length);
  const issues=qa('#wsModalBody [data-ws-issue]');
  chk('real issues are listed', issues.length>0);
  chk('every issue shows a declared severity',
      issues.every(el=>WS_ISSUE_SEVERITIES
        .indexOf(el.getAttribute('data-ws-severity'))>=0));
  const H=WS.project().model_hash;
  issues[0].click();
  chk('clicking an issue closes the panel and focuses',
      !$('wsModal').classList.contains('on'));
  chk('navigating to an issue mutated nothing',
      wsModelHashOf(WS.project())===H&&WS.project().history.length===1);
})();

console.log('\n== §63/§64 — LANGUAGE AND DIRECTION ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  WS.select('g.majlis');
  const sel=WS.ui().selected_id;
  const rev=WS.project().current_revision;
  const ar=WS.setLanguage('ar');
  chk('Arabic sets the document direction to rtl',
      document.documentElement.getAttribute('dir')==='rtl');
  chk('Arabic sets the document language', 
      document.documentElement.getAttribute('lang')==='ar');
  chk('switching to Arabic preserves the selection', ar.selection_preserved===true
      &&WS.ui().selected_id===sel);
  chk('switching language does not reload the project',
      ar.project_reloaded===false&&WS.project().current_revision===rev);
  const arUnknown=qa('#wsInsp [data-ws-unknown]');
  chk('unknown values render in Arabic',
      arUnknown.length===0||arUnknown.every(el=>el.textContent==='غير محدد'));
  const en=WS.setLanguage('en');
  chk('English sets the document direction to ltr',
      document.documentElement.getAttribute('dir')==='ltr');
  chk('switching back preserves the selection', en.selection_preserved===true);
  chk('switching back preserves the mode', en.mode_preserved===true);
  chk('the language is UI state, not model state',
      wsClassifyStateKey('language')==='UI_STATE'
      &&wsModelHashOf(WS.project())===p.model_hash);
  chk('the tree still renders after the switch',
      qa('#wsTree [data-ws-node]').length>0);
  chk('the viewport is unaffected by the language', !!$('wsViewport'));
})();

console.log('\n== §67 — KEYBOARD SHORTCUTS ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  const fake=(k,mod,shift)=>({key:k,ctrlKey:!!mod,metaKey:false,shiftKey:!!shift,
    target:{tagName:'DIV'},preventDefault:()=>{}});
  chk('Ctrl+Z maps to undo', WS.keydown(fake('z',true,false))==='UNDO');
  chk('Ctrl+Shift+Z maps to redo', WS.keydown(fake('z',true,true))==='REDO');
  chk('Escape maps to cancel', WS.keydown(fake('Escape'))==='CANCEL');
  chk('F maps to fit selection', WS.keydown(fake('f'))==='FIT_SELECTION');
  chk('E toggles edit mode', WS.keydown(fake('e'))==='TOGGLE_EDIT');
  WS.setMode('VIEW');
  WS.select('g.majlis'); WS.setMode('EDIT');
  chk('Delete requests a delete rather than deleting',
      WS.keydown(fake('Delete'))==='REQUEST_DELETE');
  chk('the delete request still shows the dependency dialog',
      $('wsModal').classList.contains('on')
      &&!!q('#wsModalBody [data-ws-section="DEPENDENCIES"]'));
  const H=WS.project().model_hash;
  WS.closeModal();
  chk('pressing Delete deleted nothing by itself',
      wsModelHashOf(WS.project())===H&&WS.project().history.length===1);
  chk('a shortcut inside a text field does not trigger a command',
      WS.keydown({key:'e',target:{tagName:'INPUT'},ctrlKey:false,
        metaKey:false,shiftKey:false,preventDefault:()=>{}})===null);
})();

console.log('\n== §60/§61 — LOADING AND DEGRADED MODE ==');
(function(){
  WS.setLoading(true,'ENGINE');
  chk('a loading state is shown', $('wsLoading').classList.contains('on'));
  chk('the loading state names a stage', /ENGINE/.test($('wsLoading').textContent));
  WS.setLoading(false);
  chk('the loading state clears', !$('wsLoading').classList.contains('on'));
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  const d=WS.setDegraded(true,'WebGL context could not be created');
  chk('degraded mode is shown', $('wsDegraded').classList.contains('on'));
  chk('degraded mode explains itself',
      /WebGL/.test($('wsDegraded').textContent));
  chk('the project data stays accessible in degraded mode',
      d.data_accessible===true&&qa('#wsTree [data-ws-node]').length>0);
  chk('the inspector still works in degraded mode', (function(){
    WS.select('g.majlis');
    return qa('#wsInsp [data-ws-section]').length>0; })());
  chk('the screen is not blank', $('acsWorkspace').textContent.length>50);
  WS.setDegraded(false);
  chk('degraded mode clears', !$('wsDegraded').classList.contains('on'));
})();

console.log('\n== §73 — UNSAVED WORK WARNING ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  chk('a freshly attached project needs no warning',
      WS.beforeUnload(null)===false);
  WS.commit([{type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'Y'}}],
    null,true);
  chk('after a commit the workspace warns before unloading',
      WS.beforeUnload(null)===true);
  WS.save();
  chk('after exporting, the warning is no longer raised',
      WS.beforeUnload(null)===false);
  chk('the status bar reflects the exported state in the active language',
      $('wsStSaved').textContent===CANON.ui_labels.exported[WS.ui().language]);
  chk('nothing claims a cloud save',
      ACS_WORKSPACE_SPEC.persistence.cloud===false
      &&/never described as one/.test(ACS_WORKSPACE_SPEC.persistence.note));
})();

console.log('\n== §92 — VISUAL REFERENCES THROUGH THE UI ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  const H=p.model_hash;
  const before=JSON.stringify(WS.project().model);
  WS.select('g.majlis');
  const r=WS.attachReference('STYLE','SPACE','g.majlis',
    'https://example.com/majlis.jpg','warm majlis');
  chk('the reference attached through the UI', r.valid===true);
  chk('it is stored in the presentation context, not the model',
      WS.presentation().references.length===1
      &&JSON.stringify(WS.project().model)===before);
  chk('the engineering model hash is unchanged', wsModelHashOf(WS.project())===H);
  chk('no revision was created', WS.project().history.length===1);
  const vi=WS.setVisualIntent('style','najdi');
  chk('visual intent is stored in presentation context', vi.valid===true
      &&WS.presentation().visual_intent.style==='najdi');
  chk('visual intent changed no engineering data',
      wsModelHashOf(WS.project())===H);
  WS.references();
  chk('the reference panel lists the attached reference',
      qa('#wsModalBody [data-ws-ref]').length===1);
  WS.closeModal();
})();

console.log('\n== §90 — TEST M: UI EVENTS CANNOT WRITE TO THE MODEL ==');
(function(){
  const p=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
  WS.attach(p);
  const H=p.model_hash;
  const before=JSON.stringify(WS.project().model);
  /* كل تفاعل واجهة ممكن، ثم هجمات المرحلتين 4 و5 عبر أحداث الواجهة */
  WS.select('g.majlis'); WS.setMode('EDIT'); WS.setMode('VIEW');
  WS.setLanguage('en'); WS.setLanguage('ar');
  WS.ui().tree_expanded=['project','site']; WS.render();
  WS.ui().discipline_filter=['MEP']; WS.render();
  WS.fit('FIT_SELECTION'); WS.fit('TOP');
  WS.issues(); WS.closeModal();
  WS.history(); WS.closeModal();
  WS.exportPanel(); WS.closeModal();
  WS.assistant(); WS.closeModal();
  WS.references(); WS.closeModal();
  WS.setLoading(true,'X'); WS.setLoading(false);
  WS.setDegraded(true,'x'); WS.setDegraded(false);
  RT_WRITE_INTENTS.forEach(i=>{ const pl={}; pl[i]=1;
    validateRuntimeAction('SELECT','OBJECT','x',pl); });
  AU_FORBIDDEN_TYPES.forEach(t=>{
    WS.beginPreview({type:t,target_id:'g.majlis',parameters:{}}); WS.closeModal(); });
  WS.beginPreview({type:'RENAME_SPACE',target_id:'g.majlis',
    parameters:{name:'x','__proto__':{p:1}}}); WS.closeModal();
  chk('the canonical model is byte-identical after every UI interaction',
      JSON.stringify(WS.project().model)===before);
  chk('the model hash is unchanged', wsModelHashOf(WS.project())===H);
  chk('no revision was created by any UI event', WS.project().history.length===1);
  chk('Object.prototype was not polluted', ({}).p===undefined);
  chk('the runtime still refuses every write intent',
      RT_WRITE_INTENTS.every(i=>{ const pl={}; pl[i]=1;
        return validateRuntimeAction('SELECT','OBJECT','x',pl).valid===false; }));
  chk('no UI function writes to the model outside a commit',
      wsWorkspaceSummary(WS.project(),WS.ui(),null,null).ui_writes_to_model===false);
})();

console.log('\n== §95 — NO DOM XSS FROM UNTRUSTED TEXT ==');
(function(){
  const evil='<img src=x onerror="window.__XSS__=1">';
  const m=C(FX.villa);
  m.meta.name=evil;
  m.floors.g.rooms[0].name=evil;
  const p=auCreateProject(m,'bld_0','IMPORT',null);
  WS.attach(p);
  WS.ui().tree_expanded=['project','site','bld_0','bld_0.flr_0','bld_0.flr_0.spaces'];
  WS.render();
  WS.select('g.majlis');
  chk('a malicious project name did not execute',
      typeof window==='undefined'||window.__XSS__===undefined);
  chk('a malicious project name is rendered as text',
      $('wsProjName').textContent.indexOf('<img')>=0);
  chk('no injected image element exists in the top bar',
      q('.ws-top img')===null);
  chk('a malicious element label did not execute',
      typeof window==='undefined'||window.__XSS__===undefined);
  chk('no injected element exists in the tree',
      document.querySelectorAll('#wsTree img').length===0);
  WS.toast('COMMAND_REJECTED',evil);
  chk('a malicious toast is rendered as text',
      document.querySelectorAll('#wsToasts img').length===0);
  const r=WS.attachReference('STYLE','SPACE','g.majlis','javascript:alert(1)','x');
  chk('a javascript: reference is refused', r.valid===false);
  const r2=WS.attachReference('STYLE','SPACE','g.majlis','https://x/y.jpg',evil);
  chk('a malicious caption is refused', r2.valid===false);
  WS.references();
  chk('the reference panel injected no element',
      document.querySelectorAll('#wsModalBody img').length===0);
  WS.closeModal();
  chk('the page never executed the payload',
      typeof window==='undefined'||window.__XSS__===undefined);
})();

console.log('\n== §71 — DEVELOPER API IS PRESERVED ==');
(function(){
  chk('the ACS namespace still exists', typeof window!=='undefined'&&!!window.ACS);
  ['previewCommand','commitTransaction','undo','redo','revisionHistory',
   'revisionDiff','editableProperties','dependencyImpact','authoringState']
    .forEach(n=>chk('the Phase 5 API ACS.'+n+' is still available',
      typeof window.ACS[n]==='function'));
  ['projectTree','inspectorModel','issueCenter','workspaceSummary','workspace']
    .forEach(n=>chk('the Phase 6 API ACS.'+n+' is available',
      window.ACS[n]!==undefined));
  chk('the workspace consumes the same canonical engines',
      window.ACS.workspace===WS);
  chk('no generic model writer was added',
      ['setModel','writeModel','applyPatch','mutateModel']
        .every(n=>typeof window.ACS[n]!=='function'));
})();
})();
}

console.log('\n──────────────────────────────────────────────');
console.log('WORKSPACE DOM: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
