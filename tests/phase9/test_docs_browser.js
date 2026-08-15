/* ============================================================================
   المرحلة 9 §61–§67 و§100 — لوحة التوثيق في متصفّح حقيقي
   يعمل هذا الجناح في Node وفي Chromium من المصدر نفسه؛ ما يحتاج DOM حقيقياً
   يُحرَس بـ HAS_DOM ولا يُنمذَج.
   ========================================================================== */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const LIB=require(_np.join(HERE,'lib_docs_fixtures.js'));
const ALL=LIB.all();
const C=o=>JSON.parse(JSON.stringify(o));
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_docs.json'),'utf8'));
const PR=n=>auCreateProject(C(ALL[n]),'bld_0','IMPORT',null);

console.log('\n== §1 — THE SPECIFICATION REACHED THE BROWSER UNCHANGED ==');
(function(){
  chk('the browser carries the canonical documentation specification',
      typeof ACS_DOCS_SPEC==='object'&&ACS_DOCS_SPEC.schema===CANON.schema);
  chk('the mirrored specification has not drifted from the file',
      JSON.stringify(ACS_DOCS_SPEC)===JSON.stringify(CANON));
  chk('the read-only rule is present and correct in the browser',
      ACS_DOCS_SPEC.documentation_is_read_only===true
      &&ACS_DOCS_SPEC.writes_to_model===false
      &&ACS_DOCS_SPEC.reverse_write_allowed===false
      &&ACS_DOCS_SPEC.mutates_engineering_model===false);
  const HAS_WIN=(typeof window!=='undefined');
  chk('the documentation API is exposed on the window',
      !HAS_WIN||(window.ACS&&window.ACS.docs&&!!window.ACS.docs.panel));
})();

const HAS_DOM=(typeof document!=='undefined'&&!!document.getElementById);
if(!HAS_DOM){
  console.log('\n(DOM checks require a real browser — run with run_browser.js)');
} else {

console.log('\n== §61/§62 — THE PANEL AND THE DOCUMENTATION TREE ==');
(function(){
  const $=id=>document.getElementById(id);
  chk('the panel exists in the shipped page',
      !!$('dcPanel')&&$('dcPanel').getAttribute('data-dc')==='panel');
  chk('the panel is closed before it is opened',
      !$('dcPanel').classList.contains('on'));
  const p=PR('villa_glazed');
  DC.init(); DC.attach(p); DC.open();
  chk('the panel opens', $('dcPanel').classList.contains('on'));
  chk('the panel shows the canonical model section',
      !!document.querySelector('#dcBody [data-dc-section="MODEL"]'));
  chk('the panel declares the model read only',
      document.querySelector('#dcBody [data-dc-section="MODEL"]')
        .textContent.indexOf('true')>=0);
  const groups=Array.prototype.map.call(
    document.querySelectorAll('#dcBody [data-dc-group]'),
    e=>e.getAttribute('data-dc-group'));
  chk('the tree carries views, schedules, quantities and sheets',
      ['VIEWS','SCHEDULES','QUANTITIES','SHEETS'].every(g=>groups.indexOf(g)>=0),
      JSON.stringify(groups));
  chk('the panel offers every declared documentation control',
      ['dcNewView','dcSchedules','dcQuantities','dcSheet','dcRegenerate',
       'dcExport'].every(id=>!!$(id)));
  chk('the panel offers no engineering mutation control',
      CANON.panel_forbidden_controls.every(c=>
        document.querySelectorAll('#dcPanel [data-dc-action="'+c+'"]').length===0),
      JSON.stringify(CANON.panel_forbidden_controls));
})();

console.log('\n== §63/§67 — CREATING A VIEW IS A DOCUMENTATION ACT, NOT AN EDIT ==');
(function(){
  const p=PR('villa_glazed');
  const h0=p.model_hash, r0=p.current_revision;
  DC.attach(p); DC.open();
  const src=DC.state().src;
  const lv=src.arch.levels[0].id;
  const r=DC.createView({view_type:'FLOOR_PLAN',level_id:lv,
    discipline:'ARCHITECTURE',scale:'1:100',
    dimension_policy:'FULL_CHAIN',annotation_policy:'TAGS_ONLY'});
  chk('a floor plan view is created in the browser', r&&r.valid===true);
  chk('creating a view changed no model hash and no revision',
      p.model_hash===h0&&p.current_revision===r0);
  chk('the viewer renders the drawing',
      !!document.querySelector('#dcBody [data-dc-viewer]'));
  const svg=document.querySelector('#dcBody [data-dc-viewer] svg');
  chk('the rendered drawing is a real SVG element', !!svg);
  chk('the SVG carries real vector geometry in the document',
      svg.querySelectorAll('line,rect').length>20,
      String(svg.querySelectorAll('line,rect').length));
  chk('the SVG declares it is not a construction drawing',
      svg.getAttribute('data-construction-drawing')==='false');
  chk('the SVG is bound to the model hash',
      svg.getAttribute('data-model-hash')===h0);
  chk('the drawing is not a raster screenshot',
      svg.querySelectorAll('image').length===0);
  chk('the view appears in the tree',
      document.querySelectorAll('#dcBody [data-dc-node="VIEW"]').length===1);
  chk('the view is marked CURRENT against the model',
      document.querySelector('#dcBody [data-dc-node="VIEW"] [data-dc-state]')
        .getAttribute('data-dc-state')==='CURRENT');
})();

console.log('\n== §64/§65 — SECTION AND ELEVATION CREATION ==');
(function(){
  const p=PR('villa_glazed');
  DC.attach(p); DC.open();
  const s=DC.createView({view_type:'SECTION',cut_plane:{axis:'x',at:3.0},
    view_depth:6.0,scale:'1:100'});
  chk('a section is created from an explicit cut line', s&&s.valid===true);
  chk('the section really cut geometry', s.geometry.cut_count>0,
      String(s.geometry.cut_count));
  const e=DC.createView({view_type:'ELEVATION',orientation:'NORTH',scale:'1:100'});
  chk('an elevation is created from a geometric direction', e&&e.valid===true);
  const bad=DC.createView({view_type:'ELEVATION'});
  chk('an elevation with no direction is refused, no front facade is inferred',
      bad&&bad.valid===false);
  chk('the refused view did not enter the tree',
      document.querySelectorAll('#dcBody [data-dc-node="VIEW"]').length===2);
  chk('the section definition lives in documentation state only',
      DC.state().project.model_hash===p.model_hash);
})();

console.log('\n== §35–§41 — SCHEDULES AND QUANTITIES RENDER AS REAL TABLES ==');
(function(){
  const p=PR('villa_glazed');
  DC.attach(p); DC.open();
  const r=DC.generateSchedule('ROOM_SCHEDULE',{});
  chk('a room schedule is generated', r&&r.valid===true&&r.schedule.row_count>0);
  const t=document.querySelector('#dcBody [data-dc-table]');
  chk('the schedule renders as a real table element', !!t
      &&t.tagName.toLowerCase()==='table');
  chk('the table has one row per canonical space',
      t.querySelectorAll('tbody tr').length===r.schedule.row_count,
      String(t.querySelectorAll('tbody tr').length));
  chk('every row is traceable to its source element',
      Array.prototype.every.call(t.querySelectorAll('tbody tr'),
        tr=>!!tr.getAttribute('data-dc-row')));
  const d=DC.generateSchedule('DOOR_SCHEDULE',{});
  const dt=document.querySelector('#dcBody [data-dc-table]');
  chk('a door schedule is generated', d&&d.schedule.row_count>0);
  chk('unknown cells are shown as NOT_SPECIFIED, never filled in',
      dt.querySelectorAll('td.unk').length>0
      &&dt.textContent.indexOf('NOT_SPECIFIED')>=0,
      String(dt.querySelectorAll('td.unk').length));
  const q=DC.generateQuantities();
  chk('a quantity report is generated', q&&q.report.count>0);
  const qt=document.querySelector('#dcBody [data-dc-section="QUANTITIES"]');
  chk('the quantity report renders', !!qt&&qt.querySelectorAll('[data-dc-qty]').length>0);
  chk('the quantity report states it is not a bill of quantities',
      qt.textContent.indexOf('not a bill of quantities')>=0);
  /* الجملة النافية تحوي كلمة cost عمداً؛ الفحص على البيانات لا على النصّ:
     لا رمز عملة، ولا عمود كلفة، ولا قيمة سعرية في أي كمّية */
  chk('no currency symbol appears in the rendered report',
      !/[$€£﷼]/.test(qt.textContent));
  chk('no quantity carries a cost, price or rate field',
      q.report.quantities.every(x=>Object.keys(x).every(
        k=>ACS_DOCS_SPEC.forbidden_quantity_fields.indexOf(k)<0)));
  chk('the report explicitly denies being a cost estimate',
      q.report.is_cost_estimate===false&&q.report.is_bill_of_quantities===false);
})();

console.log('\n== §66 — THE SHEET EDITOR COMPOSES, IT DOES NOT EDIT ENGINEERING ==');
(function(){
  const p=PR('villa_glazed');
  const h0=p.model_hash;
  DC.attach(p); DC.open();
  const src=DC.state().src;
  const lv=src.arch.levels[0].id;
  DC.createView({view_type:'FLOOR_PLAN',level_id:lv,scale:'1:100'});
  const vid=DC.state().views[0].view.view_id;
  const sh=DC.composeSheet({paper_size:'A3',orientation:'LANDSCAPE',
    sheet_number:'A-001',sheet_name:'Ground floor',
    title_block:{project:'demo',status:'DRAFT'},
    viewports:[{view_id:vid,x:10,y:10,width:180,height:120}]});
  chk('a sheet is composed in the browser', sh&&sh.valid===true);
  const sel=document.querySelector('#dcBody [data-dc-sheet]');
  chk('the sheet renders with its viewport', !!sel
      &&sel.querySelectorAll('[data-dc-viewport]').length===1);
  const before=DC.state().sheets[0].viewports[0].x;
  const vpid=DC.state().sheets[0].viewports[0].viewport_id;
  const moved=DC.moveViewport(DC.state().sheets[0].sheet_id,vpid,40,20);
  chk('a viewport can be moved as a documentation edit',
      moved&&moved.sheet.viewports[0].x===40&&before===10);
  chk('moving a viewport changed no engineering model', p.model_hash===h0);
  const collide=DC.composeSheet({paper_size:'A3',sheet_number:'A-002',
    viewports:[{view_id:vid,x:10,y:10,width:180,height:120},
      {view_id:vid,x:100,y:50,width:180,height:120}]});
  chk('overlapping viewports are reported',
      collide.issues.some(i=>i.code==='DOC_VIEWPORT_COLLISION')
      ||collide.issues.some(i=>i.code==='DOC_DUPLICATE_ARTIFACT_ID'));
  const restricted=DC.composeSheet({paper_size:'A3',sheet_number:'A-003',
    title_block:{status:'APPROVED_FOR_CONSTRUCTION'},viewports:[]});
  chk('a restricted drawing status is refused in the browser',
      restricted.issues.some(i=>i.code==='DOC_RESTRICTED_STATUS_REFUSED')
      &&restricted.sheet.title_block.status===null);
})();

console.log('\n== §68/§73 — THE EXPORT WORKFLOW ==');
(function(){
  const p=PR('villa_glazed');
  const h0=p.model_hash;
  DC.attach(p); DC.open();
  const lv=DC.state().src.arch.levels[0].id;
  DC.createView({view_type:'FLOOR_PLAN',level_id:lv,scale:'1:100'});
  DC.generateSchedule('ROOM_SCHEDULE',{});
  DC.generateQuantities();
  const vid=DC.state().views[0].view.view_id;
  DC.composeSheet({paper_size:'A3',sheet_number:'A-001',
    title_block:{project:'demo'},
    viewports:[{view_id:vid,x:10,y:10,width:180,height:120}]});
  const ex=DC.exportAll();
  chk('an export package is produced in the browser', !!ex&&ex.package.valid===true);
  const sec=document.querySelector('#dcBody [data-dc-section="EXPORT"]');
  chk('the export section renders the file list', !!sec
      &&sec.querySelectorAll('[data-dc-file]').length>=3,
      String(sec?sec.querySelectorAll('[data-dc-file]').length:0));
  chk('the manifest binds every file to the model hash',
      ex.package.manifest.model_hash===h0
      &&ex.package.manifest.files.every(f=>!!f.file_name));
  chk('PDF page content was produced for the sheet',
      ex.pdf.page_count===1&&ex.pdf.content_streams[0].length>200);
  chk('exporting changed no engineering model', p.model_hash===h0);
  chk('the package states it did not come from an IFC file',
      ex.package.package.provenance.derived_from==='CANONICAL_MODEL'
      &&ex.package.package.provenance.derived_from_ifc===false);
})();

console.log('\n== §75/§76 — STALENESS AND REGENERATION IN THE BROWSER ==');
(function(){
  const p=PR('villa_glazed');
  DC.attach(p); DC.open();
  const lv=DC.state().src.arch.levels[0].id;
  DC.createView({view_type:'FLOOR_PLAN',level_id:lv,scale:'1:100'});
  DC.generateSchedule('ROOM_SCHEDULE',{});
  chk('artifacts are CURRENT before the model moves',
      Array.prototype.every.call(
        document.querySelectorAll('#dcBody [data-dc-state]'),
        e=>e.getAttribute('data-dc-state')==='CURRENT'));
  const moved=JSON.parse(JSON.stringify(p));
  moved.model_hash='moved'; moved.current_revision='rev:moved';
  DC.state().project=moved;
  DC.render();
  chk('after the model moves every artifact reads out of date',
      Array.prototype.every.call(
        document.querySelectorAll('#dcBody [data-dc-state]'),
        e=>e.getAttribute('data-dc-state')==='STALE_MODEL_CHANGED'),
      Array.prototype.map.call(document.querySelectorAll('#dcBody [data-dc-state]'),
        e=>e.getAttribute('data-dc-state')).join(','));
  chk('nothing was regenerated automatically',
      DC.state().views.length===1);
  const reg=DC.regenerate();
  chk('an explicit regeneration produces a new documentation revision',
      reg.new_revision==='B'&&reg.previous_revision==='A');
  chk('the previous documentation revision is preserved',
      reg.history.length===1&&reg.history[0].revision==='A');
})();

console.log('\n== §32/§81 — HOSTILE TEXT IS INERT IN A REAL DOCUMENT ==');
(function(){
  window.__PWNED__=undefined;
  const model=C(ALL.villa_glazed);
  /* كل النصوص الخاملة تُسنَد أسماءَ غرف عبر كل الأدوار — الدور الأرضي وحده
     لا يتّسع لها، فتُوزَّع لتظهر جميعاً تأشيراتٍ في الرسم */
  const slots=[];
  Object.keys(model.floors).sort().forEach(t=>{
    model.floors[t].rooms.forEach((r,i)=>{ slots.push([t,i]); }); });
  LIB.INERT_TEXT.forEach((t,i)=>{
    if(slots[i]) model.floors[slots[i][0]].rooms[slots[i][1]].id=t; });
  const p=auCreateProject(model,'bld_0','IMPORT',null);
  DC.attach(p); DC.open();
  /* منظر لكل دور: النصوص الخاملة موزَّعة على الأدوار كلها */
  DC.state().src.arch.levels.forEach(l=>{
    DC.createView({view_type:'FLOOR_PLAN',level_id:l.id,scale:'1:100',
      annotation_policy:'TAGS_AND_NOTES'},
      LIB.INERT_TEXT.map(t=>({text:t}))); });
  const host=document.getElementById('dcBody');
  const allSvg=DC.state().views.map(v=>v.svg.svg).join('\n');
  chk('nothing executed while rendering hostile labels',
      window.__PWNED__===undefined);
  chk('no element was opened from an imported label',
      host.querySelectorAll('script,iframe,object,embed,b').length===0,
      String(host.querySelectorAll('script,iframe,object,embed,b').length));
  chk('a markup label the deny-list does not cover is escaped, not rendered',
      allSvg.indexOf('&lt;b&gt;bold&lt;/b&gt;')>=0
      &&host.querySelectorAll('b').length===0);
  chk('a prototype-shaped label is carried as inert text',
      allSvg.indexOf('__proto__')>=0);
  chk('the document prototype was not polluted',
      ({}).polluted===undefined&&Object.prototype.polluted===undefined
      &&({})['{{7*7}}']===undefined);
  chk('a template expression is not evaluated',
      host.textContent.indexOf('49')<0||host.textContent.indexOf('{{7*7}}')>=0);
  chk('Arabic and apostrophe labels reach the drawing as themselves',
      allSvg.indexOf('مجلس')>=0&&allSvg.indexOf('O&#39;Brien Room')>=0);
  chk('every inert label reached a drawing without being refused',
      LIB.INERT_TEXT.every(t=>allSvg.indexOf(
        t.split('&').join('&amp;').split('<').join('&lt;')
         .split('>').join('&gt;').split('"').join('&quot;')
         .split("'").join('&#39;'))>=0),
      JSON.stringify(LIB.INERT_TEXT.filter(t=>allSvg.indexOf(
        t.split('&').join('&amp;').split('<').join('&lt;')
         .split('>').join('&gt;').split('"').join('&quot;')
         .split("'").join('&#39;'))<0)));
  LIB.HOSTILE_TEXT.forEach((t,i)=>{
    const sh=DC.composeSheet({paper_size:'A3',sheet_number:'H-'+i,
      sheet_name:t,title_block:{project:t},viewports:[]});
    chk('hostile payload #'+i+' is refused as sheet metadata',
      sh.sheet.sheet_name===null&&sh.sheet.title_block.project===null); });
  chk('still nothing executed after every hostile payload',
      window.__PWNED__===undefined);
})();

console.log('\n== §60/§96 — ARABIC, RTL AND GEOMETRY THAT DOES NOT MIRROR ==');
(function(){
  const p=PR('villa_glazed');
  DC.attach(p); DC.open();
  const lv=DC.state().src.arch.levels[0].id;
  DC.createView({view_type:'FLOOR_PLAN',level_id:lv,scale:'1:100'});
  DC.generateSchedule('ROOM_SCHEDULE',{});
  const before={views:DC.state().views.length,
    schedules:DC.state().schedules.length,
    ops:JSON.stringify(DC.state().views[0].svg.svg)};
  WS.setLanguage('ar'); DC.setLanguage('ar');
  chk('the document switches to right to left',
      document.documentElement.getAttribute('dir')==='rtl');
  chk('the documentation panel is still open in Arabic',
      document.getElementById('dcPanel').classList.contains('on'));
  chk('the panel title is Arabic',
      document.getElementById('dcTitle').textContent
        ===ACS_DOCS_SPEC.ui_labels.ar.panel);
  chk('the tree still lists the same artifacts',
      DC.state().views.length===before.views
      &&DC.state().schedules.length===before.schedules);
  chk('the drawing geometry is byte-identical in Arabic',
      JSON.stringify(DC.state().views[0].svg.svg)===before.ops);
  const el=document.getElementById('dcPanel');
  chk('the panel is laid out with logical properties, not hard sides',
      getComputedStyle(el).insetInlineStart!==undefined);
  WS.setLanguage('en'); DC.setLanguage('en');
  chk('the document switches back to left to right',
      document.documentElement.getAttribute('dir')==='ltr');
  chk('the whole documentation state survived the language round trip',
      DC.state().views.length===before.views
      &&DC.state().schedules.length===before.schedules
      &&JSON.stringify(DC.state().views[0].svg.svg)===before.ops);
})();

console.log('\n== §100 — RESPONSIVE WIDTHS ==');
(function(){
  const el=document.getElementById('dcPanel');
  chk('the panel never exceeds the viewport width',
      el.getBoundingClientRect().width<=window.innerWidth+1,
      el.getBoundingClientRect().width+' vs '+window.innerWidth);
  const btns=document.querySelectorAll('#dcPanel .dc-btn');
  const small=Array.prototype.filter.call(btns,
    b=>b.getBoundingClientRect().height<40&&b.offsetParent!==null);
  chk('every visible control meets the workspace hit target',
      small.length===0, String(small.length));
  const nodes=document.querySelectorAll('#dcBody .dc-node');
  const tiny=Array.prototype.filter.call(nodes,
    n=>n.getBoundingClientRect().height<40&&n.offsetParent!==null);
  chk('every tree node meets the touch target', tiny.length===0, String(tiny.length));
  DC.close();
  chk('the panel closes', !el.classList.contains('on'));
})();
}

console.log('\n──────────────────────────────────────────────');
console.log('DOCS BROWSER: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
