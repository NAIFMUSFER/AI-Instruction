/* ============================================================================
   المرحلة 4 — قياس أداء زمن التشغيل (جافاسكربت)
   أرقام حقيقية من هذه الآلة: زمن التصريف، زمن بناء الفهرس، زمن الاستعلام،
   عدد المرشّحين، وأعداد الأجسام والبوّابات والأسطح.
   لا ادّعاء إطارات في الثانية، ولا ادّعاء أداء بطاقة رسوميات، ولا ادّعاء بكسل —
   لا شيء من ذلك يمكن قياسه هنا، فلا يُذكر.
   ========================================================================== */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const LIB=require(_np.join(HERE,'lib_runtime_fixtures.js'));
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

const CASES=[
  ['small · villa',            C(SC.models.villa)],
  ['medium · hotel',           C(SC.models.hotel)],
  ['large · synthetic 400',    genProject(400)],
  ['very large · synthetic 1500', genProject(1500)]];

const rows=[];
CASES.forEach(function(cs){
  const name=cs[0], m=cs[1];
  const vs=compileVisualScene(C(m),'bld_0',null,0,{mode:'ENGINEERING',at:AT});
  compileRuntimeScene(vs,null);                       /* إحماء، لا يُقاس */

  const c0=Date.now();
  const rs=compileRuntimeScene(vs,null);
  const c1=Date.now();

  /* بناء الفهرس يُقاس وحده بإعادة بنائه من نفس المدخلات */
  const i0=Date.now();
  const idx=_rtBuildIndex(rs.walkability.obstacles,rs.walkability.surfaces,rs.transform);
  const i1=Date.now();

  const bounds=rs.walkability.obstacles.reduce(function(a,o){
    return [Math.min(a[0],o.bounds[0]),Math.min(a[1],o.bounds[2]),
            Math.max(a[2],o.bounds[3]),Math.max(a[3],o.bounds[5])]; },
    [Infinity,Infinity,-Infinity,-Infinity]);
  const cx=Number.isFinite(bounds[0])?(bounds[0]+bounds[2])/2:0;
  const cz=Number.isFinite(bounds[1])?(bounds[1]+bounds[3])/2:0;
  const box=[cx-2,-1,cz-2,cx+2,4,cz+2];

  const REPS=200;
  const q0=Date.now();
  let last=null;
  for(let k=0;k<REPS;k++) last=queryRuntimeSpatialIndex(rs,box);
  const q1=Date.now();

  const st=createRuntimeState(rs,null,null,null);
  const m0=Date.now();
  for(let k=0;k<REPS;k++) runtimeMoveQuery(rs,st,[cx,0.9,cz],[cx+3,0.9,cz+3]);
  const m1=Date.now();

  const s0=Date.now();
  const spawnPos=(rs.defaults.spawn||{}).position||[0,0,0];
  for(let k=0;k<REPS;k++) validateRuntimeSpawn(rs,spawnPos,null,null);
  const s1=Date.now();

  const v0=Date.now();
  effectiveRuntimeVisibility(st,rs);
  const v1=Date.now();

  rows.push({
    model:name,
    objects:rs.counts.objects,
    obstacles:rs.counts.obstacles,
    surfaces:rs.counts.surfaces,
    portals:rs.counts.portals,
    portals_unresolved:rs.counts.portals_unresolved,
    rooms:rs.counts.rooms,
    vertical_connections:rs.counts.vertical_connections,
    compile_ms:c1-c0,
    index_build_ms:i1-i0,
    index_cells:idx.cells,
    index_entries:idx.entries,
    index_oversized:idx.oversized,
    query_total_ms_over_200:q1-q0,
    query_candidates:last.candidate_count,
    query_scanned_cells:last.scanned_cells,
    query_full_scan:last.full_scan,
    candidate_reduction:(last.total_entries>0
      ? Number((1-(last.candidate_count/last.total_entries)).toFixed(4)) : null),
    move_total_ms_over_200:m1-m0,
    spawn_total_ms_over_200:s1-s0,
    effective_visibility_ms:v1-v0});
});

console.log(JSON.stringify(rows,null,1));
console.log('RUNTIME BENCHMARK ROWS: '+rows.length);
console.log('measured on this machine: compile time, index build time, query time, '
  +'candidate count. NOT MEASURED: frames per second, GPU behaviour, pixel output — '
  +'no such claim is made anywhere in this phase.');

/* الفائدة الحقيقية للفهرس تُبرهَن لا تُدَّعى */
const proven=rows.every(r=>r.query_full_scan===false
  &&(r.index_entries===0||r.query_candidates<=r.index_entries));
console.log('spatial candidate reduction demonstrated on every case: '+proven);
if(!proven) process.exit(1);
