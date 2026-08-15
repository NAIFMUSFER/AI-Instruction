/* جانب جافاسكربت من تكافؤ المرحلة 6 — يعمل داخل شيفرة المتصفّح المستخرَجة من
   وحدات public/app/ (لا من الصفحة: بعد F-09 صارت قشرة)، ويكرّر ما يفعله py_workspace.py حرفاً بحرف. */
const fs=require('fs'), path=require('path');
const HERE=__dirname, PHASE=path.resolve(HERE,'..'), ROOT=path.resolve(PHASE,'..','..');
const _tmp=(function(){ try{ return require('os').tmpdir(); }catch(e){ return '/tmp'; } })();
const OUT=(process.env&&process.env.ACS_PARITY_WORKSPACE_JS)
  ||path.join(_tmp,'acs_parity_workspace_js.json');
const LIB=require(path.join(PHASE,'lib_workspace_fixtures.js'));
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';

const FX=LIB.models(), MEPF=LIB.mep();
const ALL={};
Object.keys(FX).forEach(k=>{ ALL[k]=FX[k]; });
Object.keys(MEPF).forEach(k=>{ ALL['mep_'+k]=MEPF[k]; });
const MODEL_KEYS=Object.keys(ALL).sort();
const LANGS=['en','ar'];
const TARGETS=['g.majlis','bld_0.g.majlis.door_0','g.corridor.obj_0','site',
  'building','g','bld_0.flr_0.wall_0','nope','','runtime:obj:x','obstacle:x'];

function compiled(model,bid){
  let arch=null,coord=null,vis=null,rt=null;
  try{ arch=compileArchitecture(C(model),bid,null,0); }catch(e){ arch=null; }
  try{ coord=compileCoordination(C(model),bid,null,0); }catch(e){ coord=null; }
  try{ vis=compileVisualScene(C(model),bid,null,0,{mode:'ENGINEERING'});
       rt=compileRuntimeScene(vis,null); }catch(e){ vis=null; rt=null; }
  return {arch:arch,coord:coord,vis:vis,rt:rt}; }

const out={};
MODEL_KEYS.forEach(function(key){
  const model=C(ALL[key]);
  const before=JSON.stringify(model);
  const project=auCreateProject(C(model),'bld_0','IMPORT',null);
  const cp=compiled(model,'bld_0');
  const entry={model_hash_of:wsModelHashOf(project)};
  LANGS.forEach(function(lang){
    const tree=wsProjectTree(project,cp.arch,cp.coord,lang);
    entry['tree_'+lang]=tree;
    entry['flat_'+lang]=wsFlattenTree(tree,
      [tree.root.node_id,'site','bld_0','bld_0.flr_0','bld_0.flr_0.spaces'],null,null);
    const insp={};
    TARGETS.forEach(t=>{ insp[t]=wsInspectorModel(project,t,cp.arch,cp.vis,cp.coord,lang); });
    entry['insp_'+lang]=insp; });
  entry.issues=wsIssueCenter(project,cp.arch,cp.coord,cp.rt,null,'bld_0');
  const it=[];
  Object.keys(entry.issues.categories).sort().forEach(cat=>{
    entry.issues.categories[cat].forEach(i=>{ it.push(wsIssueTargets(i)); }); });
  entry.issue_targets=it;
  entry.summary=wsWorkspaceSummary(project,wsUiStateDefault(),entry.tree_en,entry.issues);
  const ex={};
  ACS_WORKSPACE_SPEC.export_kinds.forEach(k=>{
    ex[k]=wsExportDescriptor(project,k,'COMMITTED',null,AT); });
  entry.exports=ex;
  if(JSON.stringify(model)!==before)
    throw new Error('a workspace view model mutated the engineering model: '+key);
  if(wsModelHashOf(project)!==entry.model_hash_of)
    throw new Error('the project hash changed while building views: '+key);
  out[key]=entry; });

/* ---- العمليات المتاحة لكل نوع عقدة، مقفولاً وغير مقفول */
const ops={};
ACS_WORKSPACE_SPEC.tree_node_kinds.forEach(kind=>{
  [false,true].forEach(locked=>{
    ops[kind+(locked?'|locked':'|open')]=wsAvailableOperations(kind,locked); }); });
out.__operations__=ops;

/* ---- عرض القيم المجهولة والمشتقّة والتحويلات
   ترقيم القيم بدل تمثيلها النصّي: repr في بايثون يميّز 0 عن 0.0 بينما
   جافاسكربت لا تفعل، وهو فرق في صياغة مفتاح الاختبار لا في السلوك المقارَن */
const VALUES=[null,0,1,2.5,-3.25,1e21,'text','',true,false];
const CONVERT_VALUES=[0,1,2.5,-3.25,1234.5678,null];
const disp={};
LANGS.forEach(lang=>{
  ACS_WORKSPACE_SPEC.editability_classes.forEach(ed=>{
    VALUES.forEach((v,i)=>{
      disp[lang+'|'+ed+'|'+i]=wsDisplayValue(v,ed,lang); }); }); });
out.__display__=disp;
const conv={};
ACS_WORKSPACE_SPEC.display_units.forEach(u=>{
  CONVERT_VALUES.forEach((v,i)=>{ conv[u+'|'+i]=wsConvertDisplay(v,u); }); });
out.__convert__=conv;
/* wsLabel نطاقها تسميات المصدر لا نصوص الواجهة؛ تُفحَص على نطاقها الحقيقي */
const labels={};
LANGS.forEach(lang=>{
  Object.keys(ACS_WORKSPACE_SPEC.provenance_labels).sort()
    .concat(['not_a_label_key','']).sort().forEach(k=>{
      labels[lang+'|'+k]=wsLabel(k,lang); }); });
out.__labels__=labels;
/* نصوص الواجهة تُقرأ من المواصفة في التطبيقين — لا جدول خاصّ في أيّهما.
   T داخل وحدة التحكّم تُبنى من نفس الخريطة، فأي جدول موازٍ يظهر هنا فوراً. */
const uiLabels={};
LANGS.forEach(lang=>{ Object.keys(ACS_WORKSPACE_SPEC.ui_labels).sort().forEach(k=>{
  uiLabels[lang+'|'+k]=ACS_WORKSPACE_SPEC.ui_labels[k][lang]; }); });
out.__ui_labels__=uiLabels;
const prov={};
LANGS.forEach(lang=>{
  Object.keys(ACS_WORKSPACE_SPEC.provenance_labels).sort()
    .concat(['NOT_A_REAL_SOURCE','','CODE_COMPLIANT']).forEach(src=>{
      prov[lang+'|'+src]=wsResolveProvenanceLabel(src,lang); }); });
out.__provenance__=prov;

/* ---- تغطية المتطلّبات */
const cov={};
LANGS.forEach(lang=>{
  cov[lang+'|null']=wsRequirementCoverage(null,lang);
  cov[lang+'|empty']=wsRequirementCoverage({},lang);
  cov[lang+'|real']=wsRequirementCoverage({requirements:[
    {id:'r1',text:'ثلاث غرف نوم',klass:'SPATIAL'},
    {id:'r2',text:'مصعد',klass:'UNSUPPORTED'},
    {id:'r3',text:'مطبخ 12 متر',klass:'DIMENSIONAL',satisfied_by:['g.kitchen']}]},lang); });
out.__coverage__=cov;

/* ---- حدود الحالة */
const cls={};
Object.keys(ACS_WORKSPACE_SPEC.state_ownership)
  .concat(['not_a_key','','model','ui_mode']).sort().forEach(k=>{
    cls[k]=wsClassifyStateKey(k); });
out.__state__={classify:cls,ui_default:wsUiStateDefault()};

/* ---- المراجع البصرية والنيّة، بما فيها المدخلات الخبيثة */
const ctx=wsPresentationContext(null);
const CASES=[
  ['ok','STYLE','PROJECT',null,'https://example.invalid/a.png','مرجع'],
  ['ok_space','MATERIAL','SPACE','g.majlis','https://example.invalid/b.png','رخام'],
  ['script_uri','STYLE','PROJECT',null,'javascript:alert(1)','x'],
  ['markup_caption','STYLE','PROJECT',null,'https://example.invalid/a.png',
   '<img src=x onerror=alert(1)>'],
  ['data_html','STYLE','PROJECT',null,'data:text/html,<script>x</script>','x'],
  ['svg_caption','LIGHTING','PROJECT',null,'https://example.invalid/a.png',
   '<svg onload=alert(1)>'],
  ['bad_kind','NOT_A_KIND','PROJECT',null,'https://example.invalid/a.png','x'],
  ['bad_scope','STYLE','NOT_A_SCOPE',null,'https://example.invalid/a.png','x'],
  ['empty_uri','STYLE','PROJECT',null,'','x'],
  ['none_uri','STYLE','PROJECT',null,null,'x']];
const refs={};
CASES.forEach(c=>{
  const r=wsAttachReference(ctx,c[1],c[2],c[3],c[4],'user',c[5]);
  refs[c[0]]={valid:r.valid,issues:(r.issues===undefined)?null:r.issues,
    count:((r.context||ctx).references||[]).length}; });
out.__references__=refs;
const INTENT_VALUES=['warm','','<script>x</script>'];
const intent={};
ACS_WORKSPACE_SPEC.visual_intent_fields.concat(['not_a_field']).forEach(f=>{
  INTENT_VALUES.forEach((v,i)=>{
    const r=wsSetVisualIntent(wsPresentationContext(null),f,v);
    intent[f+'|'+i]={valid:r.valid,
      issues:(r.issues===undefined)?null:r.issues}; }); });
out.__intent__=intent;

/* ---- المساعد: ادّعاءات ومقترحات، بلا إيداع تلقائي */
const claims={};
ACS_WORKSPACE_SPEC.assistant_claim_classes.concat(['NOT_A_CLASS']).forEach(k=>{
  ['this is compliant with code','the room is 5 m wide',''].forEach(t=>{
    claims[k+'|'+t.slice(0,12)]=wsAssistantClaim(k,t,null); }); });
const proj=auCreateProject(C(FX.villa),'bld_0','IMPORT',null);
out.__assistant__={claims:claims,
  propose:wsAssistantProposeEdit(proj,'اجعل المجلس أوسع',
    {type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:6,d:4}},
    'because the user asked'),
  propose_unknown:wsAssistantProposeEdit(proj,'nothing matches this',null,null)};

/* ---- عزل حالة الواجهة عن النموذج */
const ui=wsUiStateDefault();
ui.selected_id='g.majlis';
ui.ui_mode='EDIT';
out.__ui_boundary__=wsAssertUiStateExcluded(proj,ui);

out.__spec__={schema:WS_SCHEMA,version:ACS_WORKSPACE_SPEC.version};

fs.writeFileSync(OUT,JSON.stringify(out),'utf8');
console.log('javascript workspace parity written: '+OUT+' ('+Object.keys(out).length+' keys)');
