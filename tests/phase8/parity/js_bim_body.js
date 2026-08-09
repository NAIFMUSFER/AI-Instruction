/* جانب جافاسكربت من تكافؤ المرحلة 8 — يعمل داخل شيفرة المتصفّح المستخرَجة من
   public/index.html ويكرّر ما يفعله py_bim.py حرفاً بحرف على الطبقة المشتركة.
   تحليل STEP وتسلسله ليسا هنا (BX_STEP_PARSER_IN_BROWSER = false)، فالتمثيل
   المرحلي يُقرأ من الملفّ الذي كتبه جانب بايثون. الحدّ معلَن ولا يُموّه. */
const fs=require('fs'), path=require('path');
const HERE=__dirname, PHASE=path.resolve(HERE,'..'), ROOT=path.resolve(PHASE,'..','..');
const _tmp=(function(){ try{ return require('os').tmpdir(); }catch(e){ return '/tmp'; } })();
const OUT=(process.env&&process.env.ACS_PARITY_BIM_JS)
  ||path.join(_tmp,'acs_parity_bim_js.json');
const LIB=require(path.join(PHASE,'lib_bim_fixtures.js'));
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';

const ALL=LIB.models();
const SHARED=LIB.staging();
const MODEL_KEYS=Object.keys(ALL).sort();

const out={};
MODEL_KEYS.forEach(function(key){
  const model=C(ALL[key]);
  const before=JSON.stringify(model);
  const project=auCreateProject(C(model),'bld_0','IMPORT',null);
  const h0=project.model_hash;

  const entry={model_hash:h0};
  const built=bxBuildExchange(project,{});
  entry.exchange_valid=built.valid;
  entry.exchange=built.valid?built.exchange:null;
  entry.exchange_issues=built.issues.map(i=>i.code);
  if(!built.valid){ out[key]=entry; return; }
  const ex=built.exchange;
  entry.validation=bxValidateExchange(ex);

  /* المتصفّح لا يسلسل، فيبني الوصف نفسه بلا بصمة ملفّ */
  const desc=bxExportDescriptor(project,ex,null,null);
  const shared={};
  Object.keys(desc).sort(_scmp).forEach(k=>{
    if(k==='file_hash'||k==='body_hash'||k==='entity_count') return;
    if(k==='export_id'||k==='serialised_in_browser'||k==='note') { shared[k]=desc[k]; return; }
    shared[k]=desc[k]; });
  delete shared.serialised_in_browser; delete shared.note;
  entry.manifest_shared=shared;
  entry.export_valid=true;

  const st=SHARED[key]||null;
  entry.staging_valid=!!st;
  entry.staging_counts=st?st.counts:null;
  if(!st){ out[key]=entry; return; }

  const d=bxImportDiff(project,st,{});
  entry.diff=d.diff;
  entry.conflicts=bxConflicts(project,st,ex);
  const ps=bxImportProposals(d.diff,st);
  entry.proposals=ps;
  entry.staleness_current=bxImportStaleness(ps,project);
  const moved=C(project); moved.model_hash='moved'; moved.current_revision='rev:moved';
  entry.staleness_moved=bxImportStaleness(ps,moved);
  entry.export_staleness_current=bxExportStaleness(desc,project);
  entry.export_staleness_moved=bxExportStaleness(desc,moved);
  entry.commands=ps.proposals.map(p=>bxCommandFor(p));
  const nothing=bxCommitImport(project,ps,AT);
  const nk={}; ['valid','committed','state','note'].forEach(k=>{
    if(nothing[k]!==undefined) nk[k]=nothing[k]; });
  entry.commit_nothing_accepted=nk;
  const g={};
  ['space:'+key,'wall:'+key,'door:'+key,'level:'+key,'مجلس',"O'Brien"]
    .forEach(s=>{ g[s]=bxIfcGuid(s); });
  entry.guids=g;
  entry.model_untouched=(project.model_hash===h0&&JSON.stringify(model)===before);
  out[key]=entry; });

/* حالة الإيداع الحقيقية على التمثيل المرحلي نفسه الذي استعمله بايثون */
const base=auCreateProject(C(ALL['villa_glazed']),'bld_0','IMPORT',null);
const sta=SHARED['__alt'];
const d2=bxImportDiff(base,sta,{});
const ps2=bxImportProposals(d2.diff,sta);
const nameProps=ps2.proposals.filter(
  p=>p.change_type==='PROPERTY_CHANGED'&&p.field==='name');
const acc=nameProps.length?bxSetProposalState(ps2,nameProps[0].proposal_id,'ACCEPTED'):null;
const com=acc?bxCommitImport(base,acc.proposals,AT):null;
const comOut={};
if(com) ['valid','committed','state','via','previous_model_hash','new_model_hash',
  'previous_revision','new_revision','changed_objects','commands']
  .forEach(k=>{ comOut[k]=com[k]; });
out.__commit={diff:d2.diff,proposals:ps2,name_proposal_count:nameProps.length,
  accepted:acc,command:nameProps.length?bxCommandFor(nameProps[0]):null,
  commit:com?comOut:null,
  base_untouched:base.model_hash===out['villa_glazed'].model_hash};

out.__spec={schema:ACS_BIM_SPEC.schema,version:ACS_BIM_SPEC.version,
  invariant:{external_bim_is_model_truth:ACS_BIM_SPEC.external_bim_is_model_truth,
    direct_import_write_allowed:ACS_BIM_SPEC.direct_import_write_allowed,
    requires_explicit_commit:ACS_BIM_SPEC.requires_explicit_commit,
    writes_via_authoring_path:ACS_BIM_SPEC.writes_via_authoring_path},
  command_source:BX_COMMAND_SOURCE,command_map:BX_COMMAND_MAP,
  limits:ACS_BIM_SPEC.limits,tolerances:ACS_BIM_SPEC.tolerances};

/* أزواج لا كائنات: الإسناد o['__proto__']=x لا ينشئ خاصّية أصلاً، فلو بنينا
   كائناً هنا لاختفى المفتاح بصمت وبدا التكافؤ ناجحاً وهو أعمى */
out.__safety={
  unsafe:['<script>x</script>','javascript:a','JavaScript:A','../x',
    'data:text/html,x','<!ENTITY e>','file:///etc/passwd','vbscript:x',
    'plain name','مجلس',"O'Brien Room",'__proto__','constructor','{{7*7}}']
    .map(p=>[p,bxIsUnsafe(p)]),
  safe_key:['LoadBearing','IsExternal','__proto__','constructor','prototype',
    '__defineGetter__','a b','',new Array(301).join('x')]
    .map(k=>[k,bxSafeKey(k)]),
  safe_id:['bld_0.flr_0.g.r1','a-b_c:d@e$f','has space','مجلس','']
    .map(k=>[k,bxIsSafeId(k)])};

const un={};
Object.keys(ACS_BIM_SPEC.length_units).sort(_scmp)
  .forEach(u=>{ un[u]=ACS_BIM_SPEC.length_units[u]; });
out.__units=un;

fs.writeFileSync(OUT,JSON.stringify(out),'utf8');
console.log('parity written: '+MODEL_KEYS.length+' models');
