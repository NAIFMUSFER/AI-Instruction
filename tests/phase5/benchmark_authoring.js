/* ============================================================================
   المرحلة 5 — قياس أداء التأليف (جافاسكربت)
   أرقام حقيقية من هذه الآلة: التطبيع، المعاينة، التحقّق، فرق الاعتماديات،
   دلتا التنسيق، والإيداع مع بصمة المراجعة.
   لا ادّعاء إطارات في الثانية ولا أداء بطاقة رسوميات — لا شيء منه مقيس هنا.
   ========================================================================== */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const LIB=require(_np.join(HERE,'lib_authoring_fixtures.js'));
const SC=LIB.load();
const C=o=>JSON.parse(JSON.stringify(o));
const AT='2026-01-01T00:00:00Z';

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

const CASES=[['villa',C(SC.models.villa),'g.majlis','bld_0.g.majlis.door_0'],
             ['hotel',C(SC.models.hotel),'g.lobby',null],
             ['project_1000',genProject(1000),'g.sp_0',null]];

const rows=[];
CASES.forEach(function(cs){
  const name=cs[0], model=cs[1], space=cs[2], door=cs[3];
  const project=auCreateProject(C(model),'bld_0','IMPORT',null);
  const wallCmd={type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
    parameters:{delta_m:0.25,hosted_strategy:'KEEP_RELATIVE_POSITION'}};
  const doorCmd=door?{type:'MOVE_DOOR',target_id:door,parameters:{offset:3.0}}:null;
  const resizeCmd={type:'RESIZE_SPACE',target_id:space,parameters:{w:6,d:4}};
  const renameOf=i=>({type:'RENAME_SPACE',target_id:space,parameters:{name:'n'+i}});

  auNormaliseCommand(wallCmd,null,null,null);                    /* إحماء */
  auPreviewCommand(project.model,resizeCmd,null,'bld_0',null,null);

  const t=(fn,reps)=>{ const n=reps||1; const t0=Date.now();
    for(let i=0;i<n;i++) fn(i); return Date.now()-t0; };

  const normalise_ms_x100=t(()=>auNormaliseCommand(resizeCmd,null,null,null),100);
  const wall_preview_ms=t(()=>auPreviewCommand(project.model,wallCmd,null,'bld_0',null,null));
  const door_preview_ms=doorCmd
    ?t(()=>auPreviewCommand(project.model,doorCmd,null,'bld_0',null,null)):null;
  const resize_preview_ms=t(()=>auPreviewCommand(project.model,resizeCmd,null,'bld_0',
    null,null));
  const validate_ms=t(()=>auValidateModelIntegrity(project.model,'bld_0'));
  const impact_ms=t(()=>auDependencyImpact(resizeCmd,project.model,'bld_0'));

  const batch10=[]; for(let i=0;i<10;i++) batch10.push(renameOf(i));
  const batch100=[]; for(let i=0;i<100;i++) batch100.push(renameOf(i));
  const batch10_validate_ms=t(()=>auValidateTransaction(project,batch10,'bld_0'));
  const batch100_validate_ms=t(()=>auValidateTransaction(project,batch100,'bld_0'));

  const commit_ms=t(()=>auCommitTransaction(project,[renameOf(1)],{created_at:AT}));
  const committed=auCommitTransaction(project,[renameOf(1)],{created_at:AT});
  const hash_ms_x20=t(()=>auModelHash(project.model,'building','bld_0'),20);
  const diff_ms=committed.committed
    ?t(()=>auRevisionDiff(project.model,committed.project.model)):null;
  const serialise_ms=t(()=>auSerialiseProject(project,true,false));

  const rooms=(function(){ let n=0;
    Object.keys(model.floors||{}).forEach(k=>{n+=(model.floors[k].rooms||[]).length;});
    return n; })();

  rows.push({model:name,spaces:rooms,levels:(model.levels||[]).length,
    normalise_ms_per_100:normalise_ms_x100,
    wall_edit_preview_ms:wall_preview_ms,
    door_edit_preview_ms:door_preview_ms,
    space_resize_preview_ms:resize_preview_ms,
    model_integrity_validate_ms:validate_ms,
    dependency_impact_ms:impact_ms,
    batch_10_validate_ms:batch10_validate_ms,
    batch_100_validate_ms:batch100_validate_ms,
    commit_with_revision_hash_ms:commit_ms,
    model_hash_ms_per_20:hash_ms_x20,
    revision_diff_ms:diff_ms,
    serialise_ms:serialise_ms,
    committed:committed.committed===true});
});

console.log(JSON.stringify(rows,null,1));
console.log('AUTHORING BENCHMARK ROWS: '+rows.length);
console.log('measured on this machine: normalisation, preview, validation, dependency '
  +'impact, batch validation, commit and revision hashing. NOT MEASURED: frames per '
  +'second, GPU behaviour, pixel output — no such claim is made anywhere in this phase.');
const ok=rows.every(r=>r.committed===true&&r.spaces>0);
console.log('every benchmarked case actually committed a revision: '+ok);
if(!ok) process.exit(1);
