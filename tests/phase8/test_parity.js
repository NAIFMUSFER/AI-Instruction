/* ============================================================================
   المرحلة 8 — تكافؤ بايثون وجافاسكربت في طبقة التبادل المشتركة
   حدّ معلَن: تحليل STEP وتسلسله يعملان في بايثون وحدها، والمتصفّح يبني ويتحقّق
   ويفرّق ويقترح ويودع على النموذج المرحلي نفسه. الفشل هنا يعني أن الواجهة
   تُظهر للمستعمل فرقاً أو تضارباً غير الذي يحسبه الخادوم.
   ========================================================================== */
const fs=require('fs'), os=require('os'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const RUN=path.join(ROOT,'tests','lib','run.js');
const JS=path.join(os.tmpdir(),'acs_parity_bim_js.json');
const PY=path.join(os.tmpdir(),'acs_parity_bim_py.json');
const STG=path.join(os.tmpdir(),'acs_parity_bim_staging.json');
const env=Object.assign({},process.env,
  {ACS_PARITY_BIM_JS:JS,ACS_PARITY_BIM_PY:PY,ACS_PARITY_BIM_STAGING:STG});
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
[JS,PY,STG].forEach(f=>{ try{ fs.unlinkSync(f); }catch(e){} });

console.log('\n== BOTH IMPLEMENTATIONS ARE ACTUALLY EXECUTED ==');
try{
  const o=execFileSync('python3',[path.join(HERE,'parity','py_bim.py')],
    {env:env,encoding:'utf8',maxBuffer:1<<28});
  chk('the python implementation ran and wrote its result', /parity written/.test(o), o.slice(-200));
}catch(e){ chk('the python implementation ran and wrote its result',false,
  String(e.stdout||'')+String(e.stderr||'')); }
chk('the shared staging representation was produced by the parser side',
  fs.existsSync(STG));
try{
  const o=execFileSync(process.execPath,[RUN,path.join(HERE,'parity','js_bim_body.js')],
    {env:env,encoding:'utf8',maxBuffer:1<<28});
  chk('the browser implementation ran and wrote its result', /parity written/.test(o), o.slice(-400));
}catch(e){ chk('the browser implementation ran and wrote its result',false,
  (String(e.stdout||'')+String(e.stderr||'')).slice(-900)); }

console.log('\n== THE TWO RESULTS AGREE ==');
let cmp='', ok=false;
try{ cmp=execFileSync(process.execPath,[path.join(HERE,'parity','compare.js')],
  {env:env,encoding:'utf8',maxBuffer:1<<28}); ok=true; }
catch(e){ cmp=String(e.stdout||'')+String(e.stderr||''); ok=false; }
cmp.split('\n').filter(l=>/^✗/.test(l)).slice(0,10).forEach(l=>console.log('   ',l));
chk('the canonical comparison reports no mismatch', ok, cmp.split('\n').filter(Boolean).pop());
const grab=(re,label)=>{ const m=re.exec(cmp);
  chk('a real comparison was performed for '+label, !!m&&Number(m[2])>0, m?m[0]:cmp.slice(-200));
  chk('every '+label+' agrees between the two implementations', !!m&&m[1]===m[2], m?m[0]:''); };
grab(/BIM PARITY: (\d+)\/(\d+) byte-identical/,'top-level key');
grab(/exchange models: (\d+)\/(\d+)/,'exchange model');
grab(/exchange validations: (\d+)\/(\d+)/,'exchange validation');
grab(/export manifests: (\d+)\/(\d+)/,'export manifest');
grab(/import diffs: (\d+)\/(\d+)/,'import diff');
grab(/conflict sets: (\d+)\/(\d+)/,'conflict set');
grab(/proposal sets: (\d+)\/(\d+)/,'proposal set');
grab(/generated commands: (\d+)\/(\d+)/,'generated command');
grab(/staleness verdicts: (\d+)\/(\d+)/,'staleness verdict');
grab(/empty commits: (\d+)\/(\d+)/,'empty commit');
grab(/deterministic guids: (\d+)\/(\d+)/,'deterministic identifier set');
grab(/model hashes: (\d+)\/(\d+)/,'model hash');
grab(/commit case: (\d+)\/(\d+)/,'commit case');
grab(/specification view: (\d+)\/(\d+)/,'specification view');
grab(/safety verdicts: (\d+)\/(\d+)/,'safety verdict set');
grab(/unit factors: (\d+)\/(\d+)/,'unit factor table');

console.log('\n== THE COMPARISON IS NOT VACUOUS ==');
(function(){
  const J=JSON.parse(fs.readFileSync(JS,'utf8'));
  const P=JSON.parse(fs.readFileSync(PY,'utf8'));
  const put=(o,k,v)=>Object.defineProperty(o,k,
    {value:v,enumerable:true,writable:true,configurable:true});
  const canon=v=>{ if(Array.isArray(v)) return v.map(canon);
    if(v&&typeof v==='object'){ const o={};
      Object.keys(v).sort().forEach(k=>{ put(o,k,canon(v[k])); }); return o; }
    return v; };
  const S=v=>JSON.stringify(canon(v));
  const verdict=(side,group,key)=>{
    const row=(side.__safety[group]||[]).filter(r=>r[0]===key)[0];
    return row?row[1]:undefined; };
  const scen=Object.keys(J).filter(k=>k.indexOf('__')!==0);
  chk('the comparison covers every shipped fixture model', scen.length>=9, String(scen.length));
  chk('every model produced a real exchange model',
      scen.every(k=>J[k].exchange_valid===true&&J[k].exchange
        &&J[k].exchange.walls.length>0&&J[k].exchange.spaces.length>0));
  chk('every model produced a real staged comparison',
      scen.every(k=>J[k].staging_valid===true&&J[k].diff&&J[k].diff.by_type));
  chk('at least one model carries doors and windows in the exchange',
      scen.some(k=>J[k].exchange.doors.length>0&&J[k].exchange.windows.length>0));
  chk('the commit case really committed through the authoring path',
      J.__commit.commit&&J.__commit.commit.committed===true
      &&J.__commit.commit.via==='AUTHORING_PATH',
      JSON.stringify((J.__commit.commit||{}).state));
  chk('the same command was generated on both sides',
      S(J.__commit.command)===S(P.__commit.command),
      S(J.__commit.command)+' vs '+S(P.__commit.command));
  chk('the command uses only the phase 5 vocabulary',
      J.__commit.command.source===P.__spec.command_source
      &&Object.keys(J.__commit.command).sort().join(',')
        ==='parameters,source,target_id,type');
  chk('both implementations agree the model is untouched by exchange work',
      scen.every(k=>J[k].model_untouched===true&&P[k].model_untouched===true));
  chk('the mandatory invariant is identical on both sides',
      S(J.__spec.invariant)===S(P.__spec.invariant)
      &&J.__spec.invariant.external_bim_is_model_truth===false
      &&J.__spec.invariant.direct_import_write_allowed===false
      &&J.__spec.invariant.requires_explicit_commit===true
      &&J.__spec.invariant.writes_via_authoring_path===true);
  chk('a hostile string is judged unsafe by both implementations',
      verdict(J,'unsafe','<script>x</script>')===true
      &&verdict(P,'unsafe','<script>x</script>')===true
      &&verdict(J,'unsafe','JavaScript:A')===true
      &&verdict(P,'unsafe','JavaScript:A')===true);
  chk('a legitimate Arabic name is judged safe by both implementations',
      verdict(J,'unsafe','مجلس')===false&&verdict(P,'unsafe','مجلس')===false);
  chk('an inert label is not refused by either implementation',
      verdict(J,'unsafe','__proto__')===false
      &&verdict(P,'unsafe','__proto__')===false
      &&verdict(J,'unsafe','{{7*7}}')===false
      &&verdict(P,'unsafe','{{7*7}}')===false);
  chk('but a prototype key is refused as a key by both implementations',
      verdict(J,'safe_key','__proto__')===false
      &&verdict(P,'safe_key','__proto__')===false
      &&verdict(J,'safe_key','LoadBearing')===true
      &&verdict(P,'safe_key','LoadBearing')===true);
  chk('the safety verdict tables are carried as pairs, never as object keys',
      Array.isArray(J.__safety.unsafe)&&Array.isArray(P.__safety.safe_key)
      &&J.__safety.unsafe.length===P.__safety.unsafe.length
      &&J.__safety.unsafe.length>=14);
})();

console.log('\n== THE DECLARED BOUNDARY IS STATED, NOT DISGUISED ==');
(function(){
  const src=fs.readFileSync(path.join(ROOT,'public','index.html'),'utf8');
  chk('the browser declares that it does not parse STEP',
      /BX_STEP_PARSER_IN_BROWSER\s*=\s*false/.test(src));
  chk('the browser export descriptor says serialisation is not done here',
      /serialised_in_browser:false/.test(src));
  const P=JSON.parse(fs.readFileSync(PY,'utf8'));
  chk('the serialisation-only fields exist on the python side and are excluded openly',
      !!P['villa'].manifest_serialised_only
      &&typeof P['villa'].manifest_serialised_only.file_hash==='string'
      &&P['villa'].manifest_serialised_only.entity_count>0);
})();

console.log('\nBIM PARITY SUITE: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
