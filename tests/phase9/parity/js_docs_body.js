/* جانب جافاسكربت من تكافؤ المرحلة 9 — يعمل داخل شيفرة المتصفّح المستخرَجة من
   وحدات public/app/ (لا من الصفحة: بعد F-09 صارت قشرة) ويكرّر ما يفعله py_docs.py حرفاً بحرف. */
const fs=require('fs'), path=require('path');
const HERE=__dirname, PHASE=path.resolve(HERE,'..'), ROOT=path.resolve(PHASE,'..','..');
const _tmp=(function(){ try{ return require('os').tmpdir(); }catch(e){ return '/tmp'; } })();
const OUT=(process.env&&process.env.ACS_PARITY_DOCS_JS)
  ||path.join(_tmp,'acs_parity_docs_js.json');
const LIB=require(path.join(PHASE,'lib_docs_fixtures.js'));
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';

const ALL=LIB.all();
const KEYS=Object.keys(ALL).sort();
const SPECS=[
  {view_type:'FLOOR_PLAN',discipline:'ARCHITECTURE',scale:'1:100',
   dimension_policy:'FULL_CHAIN',annotation_policy:'TAGS_AND_NOTES'},
  {view_type:'ELEVATION',orientation:'NORTH',scale:'1:100'},
  {view_type:'ELEVATION',orientation:'EAST',scale:'1:200'},
  {view_type:'SECTION',cut_plane:{axis:'x',at:3.0},view_depth:6.0,scale:'1:100'},
  {view_type:'SECTION',cut_plane:{axis:'z',at:2.0},view_depth:4.0,
   dimension_policy:'OVERALL_AND_SPACES'},
  {view_type:'STRUCTURAL_PLAN',discipline:'STRUCTURE',scale:'1:100'},
  {view_type:'MEP_PLAN',discipline:'MECHANICAL',scale:'1:100'},
  {view_type:'FLS_PLAN',discipline:'FIRE_PROTECTION',scale:'1:100'},
  {view_type:'COORDINATION_PLAN',discipline:'COORDINATION'},
  {view_type:'SITE_PLAN',discipline:'ARCHITECTURE'},
  {view_type:'THREE_D_REFERENCE'},
  {view_type:'NOT_A_VIEW'}];
const NOTES=[{text:'a user note'},{text:'__proto__'},{text:'مجلس'}];
const PLAN_TYPES=['FLOOR_PLAN','STRUCTURAL_PLAN','MEP_PLAN','FLS_PLAN',
  'COORDINATION_PLAN','SITE_PLAN'];

const out={};
KEYS.forEach(function(key){
  const model=C(ALL[key]);
  const before=ingestCanonicalJson(model);
  const project=auCreateProject(C(model),'bld_0','IMPORT',null);
  const src=dcSources(project);
  const lv=src.arch.levels.length?src.arch.levels[0].id:null;
  const entry={model_hash:project.model_hash,level_id:lv};
  const views=[], drawings={};
  SPECS.forEach(function(sp,i){
    const s=C(sp);
    if(s.level_id===undefined&&PLAN_TYPES.indexOf(s.view_type)>=0) s.level_id=lv;
    const r=dcBuildView(project,s,src,NOTES);
    const rec={valid:r.valid,issues:r.issues.map(x=>x.code).sort(_scmp)};
    if(r.valid){
      rec.view=r.view; rec.geometry=r.geometry; rec.dimensions=r.dimensions;
      rec.annotations=r.annotations;
      const svg=dcViewSvg(r.view,r.geometry,r.dimensions,r.annotations,
        {paper_size:'A3'});
      rec.svg=svg.svg; rec.svg_hash=svg.file_hash; rec.svg_bytes=svg.byte_length;
      rec.ops=dcDrawOps(r.view,r.geometry,r.dimensions,r.annotations,
        420.0,297.0,12.0,'MONOCHROME');
      drawings[r.view.view_id]=rec.ops;
      views.push(r.view); }
    entry['v'+(i<10?'0':'')+i]=rec; });
  entry.schedules={};
  ACS_DOCS_SPEC.schedule_types.forEach(stype=>{
    const sr=dcSchedule(project,stype,{},src);
    entry.schedules[stype]={valid:sr.valid,schedule:sr.schedule,
      issues:sr.issues.map(x=>x.code).sort(_scmp)}; });
  entry.quantities=dcQuantities(project,{},src).report;
  const byid={}; views.forEach(v=>{ byid[v.view_id]=v; });
  const sheets=[];
  if(views.length){
    const vps=[{view_id:views[0].view_id,x:10,y:10,width:180,height:120}];
    if(views.length>1) vps.push({view_id:views[1].view_id,x:200,y:10,
      width:190,height:120});
    const sh=dcComposeSheet(project,{paper_size:'A3',orientation:'LANDSCAPE',
      sheet_number:'A-001',sheet_name:'Plan',
      title_block:{project:key,status:'DRAFT'},
      notes:[{text:'sheet note'}],viewports:vps},byid);
    entry.sheet={valid:sh.valid,sheet:sh.sheet,
      issues:sh.issues.map(x=>x.code).sort(_scmp)};
    if(sh.sheet) sheets.push(sh.sheet);
    const collide=dcComposeSheet(project,{paper_size:'A3',sheet_number:'A-002',
      viewports:[{view_id:views[0].view_id,x:10,y:10,width:180,height:120},
        {view_id:views[0].view_id,x:100,y:50,width:180,height:120}]},byid);
    entry.sheet_collision=collide.issues.map(x=>x.code).sort(_scmp); }
  entry.title_block_restricted=dcTitleBlock(project,
    {status:'APPROVED_FOR_CONSTRUCTION'}).title_block;
  const schedList=Object.keys(entry.schedules).sort(_scmp)
    .filter(s=>entry.schedules[s].schedule)
    .map(s=>entry.schedules[s].schedule);
  const doc=dcDocumentationProject(project,views,sheets,schedList,
    entry.quantities,[],'A',null,[]);
  entry.document={documentation_id:doc.documentation_id,
    documentation_revision:doc.documentation_revision,
    model_hash:doc.model_hash,source_revision:doc.source_revision,
    drawing_index:doc.drawing_index,legends:doc.legends,metadata:doc.metadata};
  if(sheets.length){
    const pdf=dcSheetPdfStreams(sheets,drawings);
    entry.pdf={page_count:pdf.page_count,media_boxes:pdf.media_boxes,
      content_streams:pdf.content_streams,sheet_ids:pdf.sheet_ids,
      semantic_hash:pdf.semantic_hash,
      cad_interoperability_claimed:pdf.cad_interoperability_claimed}; }
  else entry.pdf=null;
  const files=[{file_name:'plan.svg',format:'SVG',
      artifact_id:views.length?views[0].view_id:null,byte_length:10,
      file_hash:'abc',generation_mode:'DETERMINISTIC_VECTOR'},
    {file_name:'../escape.svg',format:'SVG',byte_length:1,file_hash:'x'},
    {file_name:'doc.json',format:'JSON',byte_length:2,file_hash:'y',
      generation_mode:'DETERMINISTIC_PACKAGE'}];
  const ex=dcExportPackage(doc,files,AT);
  entry.export={valid:ex.valid,package:ex.package,manifest:ex.manifest,
    package_hash:ex.package_hash,issues:ex.issues.map(x=>x.code).sort(_scmp)};
  entry.export_set=dcExportSet('Permit Review','review',
    sheets.map(s=>s.sheet_id),['SVG','PDF','DXF'],AT).export_set;
  const moved=C(project); moved.model_hash='moved'; moved.current_revision='rev:moved';
  entry.staleness={current:views.length?dcStaleness(views[0],project):null,
    moved:views.length?dcStaleness(views[0],moved):null};
  entry.regenerate=dcRegenerate(doc,project,AT);
  entry.impact=dcImpact(doc,project,moved);
  entry.model_untouched=(ingestCanonicalJson(project.model)===before
    &&project.model_hash===entry.model_hash);
  out[key]=entry; });

out.__spec={schema:ACS_DOCS_SPEC.schema,version:ACS_DOCS_SPEC.version,
  read_only:ACS_DOCS_SPEC.documentation_is_read_only,
  writes_to_model:ACS_DOCS_SPEC.writes_to_model,limits:ACS_DOCS_SPEC.limits,
  line_weights:ACS_DOCS_SPEC.line_weights,paper_sizes:ACS_DOCS_SPEC.paper_sizes,
  scales:ACS_DOCS_SPEC.scales};
out.__safety={
  unsafe:LIB.HOSTILE_TEXT.concat(LIB.INERT_TEXT).map(t=>[t,dcIsUnsafe(t)]),
  safe_key:['LoadBearing','__proto__','constructor','prototype',
    '__defineGetter__','a b',''].map(k=>[k,dcSafeKey(k)]),
  safe_filename:LIB.HOSTILE_FILENAMES.concat(['A-001_plan.svg','a.pdf'])
    .map(n=>[n,dcSafeFilename(n)]),
  tags:['bld_0.g.majlis.door_0@0','x','مجلس'].map(i=>[i,dcTagFor(i,'DOOR')])};
out.__stated=[
  {value:null,source:'unknown',render_fallback:0.15},
  {value:3.0,source:'imported',render_fallback:3.0},
  {value:null,source:null},null,2.5,{value:'x',source:'y'}]
  .map((t,i)=>['case_'+i,dcStated(t)]);

fs.writeFileSync(OUT,JSON.stringify(out),'utf8');
console.log('parity written: '+KEYS.length+' models');
