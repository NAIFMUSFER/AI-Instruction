/* ============================================================================
   المرحلة 6 §75 — قياس أداء مساحة العمل (جافاسكربت)
   أرقام حقيقية من هذه الآلة: تحميل المشروع، بناء الشجرة، تسطيحها، زمن التحديد،
   فتح الفاحص، مركز الملاحظات، المعاينة، والإيداع.
   لا ادّعاء إطارات في الثانية ولا أداء بطاقة رسوميات — لا شيء منه مقيس هنا.
   ========================================================================== */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const LIB=require(_np.join(HERE,'lib_workspace_fixtures.js'));
const FX=LIB.models();
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';
const SPEC=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_workspace.json'),'utf8'));
const METRICS=SPEC.performance_metrics||[];

function genProject(n){
  const cols=Math.ceil(Math.sqrt(n)), rooms=[];
  for(let i=0;i<n;i++){ const r=Math.floor(i/cols), c=i%cols;
    rooms.push({id:'sp_'+i,rect:[c*6,r*5,6,5],height:3,
      doors:[{edge:'N',offset:3,width:1,height:2.1}],
      windows:(i%3===0)?[{edge:'S',offset:3,width:1.4,height:1.4,sill:0.9}]:[]}); }
  return {meta:{type:'office',name:'synthetic_'+n},wall_h:3,wall_t:0.2,floor_height:3.2,
    site:{w:cols*6,d:Math.ceil(n/cols)*5},
    levels:[{index:0,template:'g'},{index:1,template:'g'}],
    floors:{g:{rooms:rooms}}};
}

const CASES=[['villa',C(FX.villa),'g.majlis'],
             ['hotel',C(FX.hotel),null],
             ['project_1000',genProject(1000),'g.sp_0']];

const t=(fn,reps)=>{ const n=reps||1; const t0=Date.now();
  for(let i=0;i<n;i++) fn(i); return Date.now()-t0; };

const rows=[];
CASES.forEach(function(cs){
  const name=cs[0], model=cs[1];
  const load_ms=t(()=>auCreateProject(C(model),'bld_0','IMPORT',null));
  const project=auCreateProject(C(model),'bld_0','IMPORT',null);
  const arch_ms=t(()=>compileArchitecture(C(model),'bld_0',null,0));
  const arch=compileArchitecture(C(model),'bld_0',null,0);
  let coord=null;
  const coord_ms=t(()=>{ try{ coord=compileCoordination(C(model),'bld_0',null,0); }
    catch(e){ coord=null; } });
  let runtime=null;
  try{ runtime=compileRuntimeScene(
    compileVisualScene(C(model),'bld_0',null,0,{mode:'ENGINEERING'}),null); }
  catch(e){ runtime=null; }

  wsProjectTree(project,arch,coord,'en');                        /* إحماء */
  const tree_ms=t(()=>wsProjectTree(project,arch,coord,'en'));
  const tree=wsProjectTree(project,arch,coord,'en');
  /* الشجرة تُفتح بكاملها: هذه أسوأ حالة حقيقية للتسطيح، ولا تخفي كلفة */
  const expanded=[];
  (function walk(n){ expanded.push(n.node_id);
    (n.children||[]).forEach(walk); })(tree.root);
  const flatten_ms=t(()=>wsFlattenTree(tree,expanded,null,null),10);
  const flat=wsFlattenTree(tree,expanded,null,null).rows;

  /* أوّل فراغ حقيقي في الشجرة يُستعمل هدفاً، فلا يعتمد القياس على اسم مختلَق */
  let target=cs[2];
  if(!target){ const sp=flat.filter(r=>r.kind==='SPACE')[0];
    target=sp?sp.node_id:null; }
  const inspector_ms=target
    ?t(()=>wsInspectorModel(project,target,arch,null,coord,'en'),10):null;
  const issues_ms=t(()=>wsIssueCenter(project,arch,coord,runtime,null,'bld_0'));
  const issues=wsIssueCenter(project,arch,coord,runtime,null,'bld_0');

  const resizeCmd=target
    ?{type:'RESIZE_SPACE',target_id:target,parameters:{w:6,d:4}}:null;
  const preview_ms=resizeCmd
    ?t(()=>auPreviewCommand(project.model,resizeCmd,null,'bld_0',null,null)):null;
  let commit_ms=null, committed=false;
  if(resizeCmd){
    const txn=auValidateTransaction(project,[resizeCmd],'bld_0');
    const t0=Date.now();
    const c=auCommitTransaction(project,[resizeCmd],
      {confirm:(txn.transaction||{}).confirmation_digest,
       acknowledge_warnings:true,created_at:AT});
    commit_ms=Date.now()-t0;
    committed=c.committed===true; }

  const summary_ms=t(()=>wsWorkspaceSummary(project,wsUiStateDefault(),tree,issues),10);

  rows.push({case:name,
    tree_nodes:tree.node_count,
    visible_rows:flat.length,
    issue_total:issues.total,
    project_load_ms:load_ms,
    architecture_compile_ms:arch_ms,
    coordination_compile_ms:coord_ms,
    tree_build_ms:tree_ms,
    tree_flatten_ms_per_10:flatten_ms,
    inspector_open_ms_per_10:inspector_ms,
    issue_centre_ms:issues_ms,
    edit_preview_ms:preview_ms,
    commit_ms:commit_ms,
    summary_ms_per_10:summary_ms,
    committed:committed});
});

console.log(JSON.stringify(rows,null,1));
console.log('WORKSPACE BENCHMARK ROWS: '+rows.length);
console.log('declared measurable metrics: '+JSON.stringify(METRICS));
console.log(SPEC.performance_note);
console.log('measured on this machine: project load, discipline compilation, tree build '
  +'and flatten, inspector open, issue centre, edit preview and commit. NOT MEASURED: '
  +'frames per second, GPU behaviour, pixel output, render latency — no such claim is '
  +'made anywhere in this phase.');
const ok=rows.every(r=>r.tree_nodes>3&&r.visible_rows>0&&r.committed===true);
console.log('every benchmarked case built a real tree and committed a revision: '+ok);
if(!ok) process.exit(1);
