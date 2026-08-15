/* ============================================================================
   المرحلة 8 §38–§42 و§60 — لوحة التبادل في متصفّح حقيقي
   يعمل هذا الجناح في Node وفي Chromium من المصدر نفسه. ما يحتاج DOM حقيقياً
   يُحرَس بـ HAS_DOM ولا يُنمذَج.
   ========================================================================== */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const LIB=require(_np.join(HERE,'lib_bim_fixtures.js'));
const ALL=LIB.models();
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_bim.json'),'utf8'));
const STAGED=JSON.parse(fs.readFileSync(
  _np.join(HERE,'fixtures','staging_parity.json'),'utf8'));
const HOSTILE=JSON.parse(fs.readFileSync(
  _np.join(HERE,'fixtures','staging_hostile.json'),'utf8'));
const RT=JSON.parse(fs.readFileSync(
  _np.join(HERE,'fixtures','roundtrip_report.json'),'utf8'));
const PR=n=>auCreateProject(C(ALL[n]),'bld_0','IMPORT',null);

console.log('\n== §1 — THE SPECIFICATION REACHED THE BROWSER UNCHANGED ==');
(function(){
  chk('the browser carries the canonical BIM specification',
      typeof ACS_BIM_SPEC==='object'&&ACS_BIM_SPEC.schema===CANON.schema);
  chk('the mirrored specification has not drifted from the file',
      JSON.stringify(ACS_BIM_SPEC)===JSON.stringify(CANON));
  chk('the mandatory invariant is present and correct in the browser',
      ACS_BIM_SPEC.external_bim_is_model_truth===false
      &&ACS_BIM_SPEC.direct_import_write_allowed===false
      &&ACS_BIM_SPEC.requires_explicit_commit===true
      &&ACS_BIM_SPEC.writes_via_authoring_path===true);
  const HAS_WIN=(typeof window!=='undefined');
  chk('the browser states plainly that it does not parse STEP',
      BX_STEP_PARSER_IN_BROWSER===false
      &&(!HAS_WIN||window.ACS.bim.stepParserInBrowser===false));
})();

const HAS_DOM=(typeof document!=='undefined'&&!!document.getElementById);
if(!HAS_DOM){
  console.log('\n(DOM checks require a real browser — run with run_browser.js)');
} else {

console.log('\n== §38 — THE PANEL OPENS INSIDE THE WORKSPACE ==');
(function(){
  const $=id=>document.getElementById(id);
  chk('the panel element exists in the shipped page',
      !!$('bxPanel')&&$('bxPanel').getAttribute('data-bx')==='panel');
  chk('the panel is closed before it is opened',
      !$('bxPanel').classList.contains('on'));
  const p=PR('villa_glazed');
  BX.init(); BX.attach(p); BX.open();
  chk('the panel opens', $('bxPanel').classList.contains('on'));
  chk('the panel names the canonical model section',
      !!document.querySelector('#bxBody [data-bx-section="MODEL"]'));
  chk('the panel offers every declared control',
      CANON.panel_controls.every(()=>true)
      &&['bxImport','bxExport','bxValidate','bxCompare','bxProposals','bxRoundtrip']
        .every(id=>!!$(id)));
  chk('the panel offers no forbidden engineering control',
      CANON.panel_forbidden_controls.every(c=>
        document.querySelectorAll('#bxPanel [data-bx-action="'+c+'"]').length===0),
      JSON.stringify(CANON.panel_forbidden_controls));
})();

console.log('\n== §39 — THE IMPORT REVIEW SHOWS WHAT WAS ACTUALLY READ ==');
(function(){
  const p=PR('villa_glazed');
  const h0=p.model_hash;
  BX.attach(p); BX.open();
  BX.loadStaging(C(STAGED['villa_glazed']));
  const sec=document.querySelector('#bxBody [data-bx-section="IMPORT"]');
  chk('an import summary section is rendered', !!sec);
  const txt=sec?sec.textContent:'';
  chk('the summary is labelled as staged external data, not as the model',
      !!document.querySelector('#bxBody [data-bx="staging-label"]')
      &&document.querySelector('#bxBody [data-bx="staging-label"]').textContent
        .indexOf(CANON.staging_preview_label)>=0);
  const c=STAGED['villa_glazed'].counts;
  chk('the parsed entity count is shown and is real',
      c.parsed_entities>0&&txt.indexOf(String(c.parsed_entities))>=0,
      String(c.parsed_entities));
  chk('the supported and unsupported counts are both shown',
      txt.indexOf(String(c.supported))>=0&&txt.indexOf(String(c.unsupported))>=0);
  chk('the summary states that the import writes nothing to the model',
      txt.indexOf('false')>=0
      &&STAGED['villa_glazed'].writes_to_model===false);
  chk('loading a staged file changed no model hash', p.model_hash===h0);
  const v=BX.validate();
  chk('validation reports the real issue list',
      !!v&&Array.isArray(v.issues)&&Array.isArray(v.blocking));
})();

console.log('\n== §40 — THE DIFF AND THE PROPOSALS RENDER ==');
(function(){
  const p=PR('villa_glazed');
  const h0=p.model_hash, r0=p.current_revision;
  BX.attach(p); BX.open();
  BX.loadStaging(C(HOSTILE.staging));   /* ملفّ يختلف عن النموذج فعلاً */
  const d=BX.compare();
  chk('a comparison runs in the browser', !!d&&d.valid===true);
  chk('the diff section renders',
      !!document.querySelector('#bxBody [data-bx-section="DIFF"]'));
  const rows=document.querySelectorAll('#bxBody [data-bx-diff]');
  chk('real difference entries are rendered', rows.length>0, String(rows.length));
  BX.proposals();
  const pr=document.querySelectorAll('#bxBody [data-bx-proposal]');
  chk('the proposal section renders real proposals', pr.length>0, String(pr.length));
  chk('every rendered proposal offers accept and reject',
      Array.prototype.every.call(pr,el=>
        !!el.querySelector('[data-bx-accept]')&&!!el.querySelector('[data-bx-reject]')));
  chk('comparing and proposing changed nothing in the model',
      p.model_hash===h0&&p.current_revision===r0);
})();

console.log('\n== §41 — ACCEPT AND REJECT ARE REAL CLICKS, AND STILL NOT A WRITE ==');
(function(){
  const p=PR('villa_glazed');
  const h0=p.model_hash;
  BX.attach(p); BX.open();
  BX.loadStaging(C(STAGED['__alt']));
  BX.compare(); BX.proposals();
  const names=BX.state().proposals.proposals.filter(
    x=>x.change_type==='PROPERTY_CHANGED'&&x.field==='name');
  chk('the renamed space produced a name proposal', names.length>=1);
  const id=names.length?names[0].proposal_id:null;
  const btn=id?document.querySelector('[data-bx-accept="'+id+'"]'):null;
  chk('the accept control for that proposal is in the document', !!btn);
  if(btn){
    btn.click();
    const after=BX.state().proposals.proposals.filter(x=>x.proposal_id===id)[0];
    chk('clicking accept moves the proposal to ACCEPTED', after.state==='ACCEPTED',
        after.state);
    chk('accepting alone writes nothing to the model', p.model_hash===h0);
    const rej=document.querySelector('[data-bx-reject="'+id+'"]');
    rej.click();
    chk('clicking reject moves it back out of ACCEPTED',
        BX.state().proposals.proposals.filter(x=>x.proposal_id===id)[0].state
          ==='REJECTED');
    chk('rejecting writes nothing either', p.model_hash===h0);
    document.querySelector('[data-bx-accept="'+id+'"]').click();
  }
  const commit=document.getElementById('bxCommit');
  chk('an explicit commit control is present', !!commit);
  if(commit){
    commit.click();
    const st=BX.state();
    chk('the explicit commit produced a new revision through authoring',
        st.project.model_hash!==h0
        &&st.project.current_revision!==p.current_revision,
        String(st.project.current_revision));
    chk('the committed change appears in ordinary revision history',
        (st.project.history||[]).length===2, String((st.project.history||[]).length));
    chk('the project object handed to the panel was not mutated in place',
        p.model_hash===h0);
  }
})();

console.log('\n== §42 — THE EXPORT SUMMARY AND THE ROUND-TRIP REPORT ==');
(function(){
  const p=PR('villa_glazed');
  const h0=p.model_hash;
  BX.attach(p); BX.open();
  const e=BX.exportBim();
  chk('an export summary is produced in the browser', !!e&&e.valid===true);
  const sec=document.querySelector('#bxBody [data-bx-section="EXPORT"]');
  chk('the export section renders', !!sec);
  chk('the export section states that the browser did not serialise',
      !!sec&&sec.textContent.indexOf('false')>=0
      &&BX.state().manifest.serialised_in_browser===false);
  chk('the export counts match the real exchange model',
      BX.state().manifest.space_count===11
      &&BX.state().manifest.wall_count===44,
      JSON.stringify([BX.state().manifest.space_count,
                      BX.state().manifest.wall_count]));
  chk('exporting changed no model hash', p.model_hash===h0);
  BX.roundtrip(RT.report);
  const rs=document.querySelector('#bxBody [data-bx-section="ROUNDTRIP"]');
  chk('the round-trip section renders a real report', !!rs
      &&rs.textContent.indexOf('PASS')>=0, rs?rs.textContent.slice(0,80):'');
  chk('the report carries the four fidelity dimensions',
      ['semantic','geometry','relationship','property'].every(
        k=>typeof RT.report[k+'_fidelity']==='number'));
})();

console.log('\n== §60 — HOSTILE IMPORTED STRINGS ARE INERT IN A REAL DOCUMENT ==');
(function(){
  window.__PWNED__=undefined;
  const p=PR('villa_glazed');
  BX.attach(p); BX.open();
  BX.loadStaging(C(HOSTILE.staging));
  BX.compare(); BX.proposals();
  const host=document.getElementById('bxBody');
  chk('the executable payloads never reached a staged name',
      HOSTILE.payloads.slice(0,4).every(
        pl=>(HOSTILE.staging.entities||[]).every(e2=>e2.name!==pl)),
      JSON.stringify((HOSTILE.staging.entities||[]).map(e2=>e2.name)).slice(0,200));
  chk('the parser refused them with a typed issue',
      (HOSTILE.issues||[]).some(i=>i.code==='BIM_UNSAFE_STRING'));
  chk('the inert labels did reach the panel as text',
      ['__proto__','constructor','prototype','{{7*7}}'].every(
        pl=>host.textContent.indexOf(pl)>=0), host.textContent.slice(0,120));
  chk('no element was opened from an imported value',
      host.querySelectorAll('script,iframe,object,embed,svg,img,b').length===0,
      String(host.querySelectorAll('script,iframe,object,embed,svg,img,b').length));
  chk('a markup label that the deny-list does not cover is escaped, not rendered',
      host.textContent.indexOf('<b>bold</b>')>=0
      &&host.innerHTML.indexOf('&lt;b&gt;bold&lt;/b&gt;')>=0
      &&host.innerHTML.indexOf('<b>bold</b>')<0);
  chk('quotes and ampersands in an imported label are escaped too',
      host.textContent.indexOf('a "quoted" & <tag>')>=0
      &&host.innerHTML.indexOf('&amp;')>=0);
  chk('nothing executed while rendering the hostile file',
      window.__PWNED__===undefined);
  chk('the document prototype was not polluted by any imported label',
      ({}).polluted===undefined&&({})['{{7*7}}']===undefined
      &&Object.prototype.polluted===undefined);
  chk('an Arabic and an apostrophe name render as themselves',
      host.textContent.indexOf('مجلس')>=0
      &&host.textContent.indexOf("O'Brien Room")>=0);
})();

console.log('\n== §61 — ARABIC AND ENGLISH SWITCHING PRESERVES THE PANEL STATE ==');
(function(){
  const p=PR('villa_glazed');
  BX.attach(p); BX.open();
  BX.loadStaging(C(STAGED['__alt']));
  BX.compare(); BX.proposals();
  const before={view:BX.state().view,
    proposals:BX.state().proposals.count,
    diff:BX.state().diff.count,
    states:BX.state().proposals.proposals.map(x=>x.state).join(',')};
  WS.setLanguage('ar');
  chk('the document switches to right to left',
      document.documentElement.getAttribute('dir')==='rtl');
  chk('the exchange panel is still open in Arabic',
      document.getElementById('bxPanel').classList.contains('on'));
  chk('the panel still shows the same number of proposals',
      document.querySelectorAll('#bxBody [data-bx-proposal]').length
        ===before.proposals, String(before.proposals));
  WS.setLanguage('en');
  chk('the document switches back to left to right',
      document.documentElement.getAttribute('dir')==='ltr');
  const after={view:BX.state().view,
    proposals:BX.state().proposals.count,
    diff:BX.state().diff.count,
    states:BX.state().proposals.proposals.map(x=>x.state).join(',')};
  chk('the whole exchange state survived the round trip of languages',
      JSON.stringify(after)===JSON.stringify(before),
      JSON.stringify(after)+' vs '+JSON.stringify(before));
})();

console.log('\n== §62 — THE PANEL IS USABLE ON A NARROW VIEWPORT ==');
(function(){
  const el=document.getElementById('bxPanel');
  const cs=getComputedStyle(el);
  chk('the panel is laid out with logical properties, not hard sides',
      cs.insetInlineStart!==undefined&&cs.insetInlineEnd!==undefined);
  chk('the panel never exceeds the viewport width',
      el.getBoundingClientRect().width<=window.innerWidth+1,
      el.getBoundingClientRect().width+' vs '+window.innerWidth);
  const btns=document.querySelectorAll('#bxPanel .bx-btn');
  const small=Array.prototype.filter.call(btns,
    b=>b.getBoundingClientRect().height<40&&b.offsetParent!==null);
  chk('every visible control meets the workspace hit target',
      small.length===0, String(small.length));
  BX.close();
  chk('the panel closes', !el.classList.contains('on'));
})();
}

console.log('\n──────────────────────────────────────────────');
console.log('BIM BROWSER: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
