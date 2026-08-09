/* ============================================================================
   المرحلة 4 — انحدار النموذج (§38)
   المرحلة 4 طبقة مشتقّة فوق كل ما سبقها. الشرط: لا بصمة نموذج تتغيّر، ولا جسم
   ثلاثي الأبعاد يتحرّك أو يتغيّر مقاسه أو دورانه، ولا مشهد بصري يختلف.

   المرجع محفوظ داخل المستودع (tests/phase3/fixtures/mesh_baseline.json)،
   لا في /tmp — التحقّق يعمل من نسخة نظيفة.

   هذا يتحقّق من الهندسة المبنيّة لا من البكسل: عرض WebGL الحقيقي غير مُتحقَّق
   منه هنا — NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.
   ========================================================================== */
const fs=require('fs'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const RUN=path.join(ROOT,'tests','lib','run.js');
const DUMP=path.join(ROOT,'tests','phase3','mesh_invariance_dump.js');
const BASE=path.join(ROOT,'tests','phase3','fixtures','mesh_baseline.json');

let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};

console.log('\n== THE 3D SCENE THE APPLICATION BUILDS IS UNCHANGED ==');
const GEOM=path.join(require('os').tmpdir(),'acs_geometry_regression.json');
execFileSync(process.execPath,[RUN,DUMP],{encoding:'utf8',maxBuffer:1<<28,
  env:Object.assign({},process.env,{ACS_GEOM_OUT:GEOM})});
chk('the geometry dump produced a result', fs.existsSync(GEOM));
const now=JSON.parse(fs.readFileSync(GEOM,'utf8'));
const base=JSON.parse(fs.readFileSync(BASE,'utf8'));

/* النيّة: المرجع ملفّ من المستودع لا ملفّ خردة في مجلّد النظام المؤقّت. الفحص
   على شجرة المستودع وعلى مجلّد النظام المؤقّت نفسه، لا على مطابقة نصّية لـ
   '/tmp' — وإلّا انكسر الفحص لمجرّد أن المستودع فُكّ تحت مسار مؤقّت، وهو ما
   يحدث فعلاً عند التحقّق من أرشيف النشر. */
const REL=path.relative(ROOT,path.resolve(BASE));
chk('the vendored baseline lives in the repository, not in a temporary directory',
    fs.existsSync(BASE)
    &&fs.statSync(BASE).isFile()&&fs.statSync(BASE).size>0
    &&REL.indexOf('..')!==0&&!path.isAbsolute(REL)     /* داخل شجرة المستودع */
    &&REL.split(path.sep)[0]==='tests'                 /* في مجلّد التجهيزات */
    &&path.dirname(path.resolve(BASE))                 /* وليس حيث تُكتب الخردة */
       !==path.dirname(path.resolve(GEOM)),
    REL);
chk('the baseline is not empty and covers several models',
    base.length>=8, String(base.length));
chk('the baseline carries real geometry, so the comparison is not vacuous',
    base.reduce((s,r)=>s+r.meshes,0)>700,
    String(base.reduce((s,r)=>s+r.meshes,0)));
chk('the same models are built now as when the baseline was taken',
    JSON.stringify(now.map(r=>r.model))===JSON.stringify(base.map(r=>r.model)),
    JSON.stringify(now.map(r=>r.model)));
chk('the mesh count of every model is unchanged',
    JSON.stringify(now.map(r=>r.model+'='+r.meshes))
      ===JSON.stringify(base.map(r=>r.model+'='+r.meshes)),
    JSON.stringify(now.map(r=>r.model+'='+r.meshes)));

/* المقارنة الآن على الشجرة الأصلية كاملة: الاسم والظهور والموضع والمقاس والدوران */
const proj=r=>r.tree;
base.forEach(function(b,i){
  const n=now[i];
  chk(b.model+': every mesh keeps its name, visibility, position, size and rotation exactly',
      JSON.stringify(proj(n))===JSON.stringify(b.tree), (function(){
        const a=JSON.stringify(b.tree), c=JSON.stringify(proj(n));
        for(let k=0;k<Math.max(a.length,c.length);k++) if(a[k]!==c[k])
          return 'baseline='+a.slice(Math.max(0,k-70),k+70)
               +' now='+c.slice(Math.max(0,k-70),k+70);
        return ''; })());
});
chk('every model in the baseline was actually compared',
    now.length===base.length&&now.length>0);
chk('no mesh acquired a non-finite coordinate',
    now.every(r=>r.tree.every(t=>t[2].every(Number.isFinite)
      &&(t[3]||[]).every(Number.isFinite)&&Number.isFinite(t[4]))));
chk('the dump script refuses to overwrite a JavaScript source file', (function(){
  try{ execFileSync(process.execPath,[RUN,DUMP],{encoding:'utf8',stdio:'pipe',
        env:Object.assign({},process.env,{ACS_GEOM_OUT:''})});
       return false; }
  catch(e){ return /refusing to write the geometry dump over a JavaScript source file/
    .test(String(e.stdout||'')+String(e.stderr||'')+String(e.message||'')); } })());

console.log('\n== THE ENGINEERING MODEL HASHES ARE UNCHANGED ==');
(function(){
  const probe=path.join(require('os').tmpdir(),'acs_p4_hash_probe.js');
  fs.writeFileSync(probe,
    "const fs=require('fs'), p=require('path');\n"+
    "const FX=JSON.parse(fs.readFileSync("+JSON.stringify(
      path.join(ROOT,'tests','phase3','fixtures','base_fixtures.json'))+",'utf8'));\n"+
    "const out={};\n"+
    "['clinic','hotel','office','villa','warehouse'].forEach(function(n){\n"+
    "  out[n]=modelHash(JSON.parse(JSON.stringify(FX[n])),'building','bld_0').slice(0,24); });\n"+
    "console.log('HASHES '+JSON.stringify(out));\n",'utf8');
  const o=execFileSync(process.execPath,[RUN,probe],{encoding:'utf8'});
  const m=/HASHES (\{.*\})/.exec(o);
  chk('the model hashes were actually computed', !!m, o.slice(0,200));
  const h=JSON.parse(m[1]);
  const EXPECT={clinic:'9d53da26e80c9da134047e9c',hotel:'7e6459352f65da0d692a6d34',
    office:'e2d7e76e963de85394aa2716',villa:'de6d2d3568bce08e5bf72882',
    warehouse:'44f38c43a92e731fbe0057c7'};
  Object.keys(EXPECT).sort().forEach(function(k){
    chk(k+': the engineering model hash equals the Phase 4 pre-implementation baseline',
        h[k]===EXPECT[k], h[k]+' expected '+EXPECT[k]); });
})();

console.log('\n──────────────────────────────────────────────');
console.log('MODEL REGRESSION: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
