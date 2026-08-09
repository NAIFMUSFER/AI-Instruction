/* ============================================================================
   المرحلة 9 — تكافؤ بايثون وجافاسكربت في طبقة التوثيق
   الفشل هنا يعني أن اللوحة التي يراها المستعمل تحمل هندسة أو جدولاً أو كمّية
   غير التي يحسبها الخادوم — وهو ما يمنعه العقد صراحةً.
   ========================================================================== */
const fs=require('fs'), os=require('os'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const RUN=path.join(ROOT,'tests','lib','run.js');
const JS=path.join(os.tmpdir(),'acs_parity_docs_js.json');
const PY=path.join(os.tmpdir(),'acs_parity_docs_py.json');
const env=Object.assign({},process.env,
  {ACS_PARITY_DOCS_JS:JS,ACS_PARITY_DOCS_PY:PY});
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
[JS,PY].forEach(f=>{ try{ fs.unlinkSync(f); }catch(e){} });

console.log('\n== BOTH IMPLEMENTATIONS ARE ACTUALLY EXECUTED ==');
try{
  const o=execFileSync('python3',[path.join(HERE,'parity','py_docs.py')],
    {env:env,encoding:'utf8',maxBuffer:1<<28});
  chk('the python implementation ran and wrote its result',/parity written/.test(o),
    o.slice(-200));
}catch(e){ chk('the python implementation ran and wrote its result',false,
  (String(e.stdout||'')+String(e.stderr||'')).slice(-900)); }
try{
  const o=execFileSync(process.execPath,[RUN,path.join(HERE,'parity','js_docs_body.js')],
    {env:env,encoding:'utf8',maxBuffer:1<<28});
  chk('the browser implementation ran and wrote its result',/parity written/.test(o),
    o.slice(-400));
}catch(e){ chk('the browser implementation ran and wrote its result',false,
  (String(e.stdout||'')+String(e.stderr||'')).slice(-900)); }

console.log('\n== THE TWO RESULTS AGREE ==');
let cmp='', ok=false;
try{ cmp=execFileSync(process.execPath,[path.join(HERE,'parity','compare.js')],
  {env:env,encoding:'utf8',maxBuffer:1<<28}); ok=true; }
catch(e){ cmp=String(e.stdout||'')+String(e.stderr||''); ok=false; }
cmp.split('\n').filter(l=>/^✗/.test(l)).slice(0,10).forEach(l=>console.log('   ',l));
chk('the comparator proves it is not blind to a prototype key',
  /does not silently drop a prototype key/.test(cmp));
chk('the canonical comparison reports no mismatch',ok,
  cmp.split('\n').filter(Boolean).pop());
const grab=(re,label)=>{ const m=re.exec(cmp);
  chk('a real comparison was performed for '+label,!!m&&Number(m[2])>0,
    m?m[0]:cmp.slice(-200));
  chk('every '+label+' agrees between the two implementations',!!m&&m[1]===m[2],
    m?m[0]:''); };
grab(/DOCS PARITY: (\d+)\/(\d+) byte-identical/,'top-level key');
grab(/view definitions: (\d+)\/(\d+)/,'view definition set');
grab(/view validity: (\d+)\/(\d+)/,'view validity verdict');
grab(/projected geometry: (\d+)\/(\d+)/,'plan geometry');
grab(/elevation geometry: (\d+)\/(\d+)/,'elevation geometry');
grab(/section geometry: (\d+)\/(\d+)/,'section geometry');
grab(/dimensions: (\d+)\/(\d+)/,'dimension set');
grab(/annotations: (\d+)\/(\d+)/,'annotation set');
grab(/draw operations: (\d+)\/(\d+)/,'draw operation set');
grab(/svg output: (\d+)\/(\d+)/,'vector output');
grab(/svg hashes: (\d+)\/(\d+)/,'vector output hash');
grab(/schedule rows: (\d+)\/(\d+)/,'schedule');
grab(/quantities: (\d+)\/(\d+)/,'quantity report');
grab(/sheet descriptors: (\d+)\/(\d+)/,'sheet descriptor');
grab(/title block refusals: (\d+)\/(\d+)/,'title block refusal');
grab(/document descriptors: (\d+)\/(\d+)/,'document descriptor');
grab(/pdf content streams: (\d+)\/(\d+)/,'PDF content stream');
grab(/export manifests: (\d+)\/(\d+)/,'export manifest');
grab(/export sets: (\d+)\/(\d+)/,'export set');
grab(/staleness verdicts: (\d+)\/(\d+)/,'staleness verdict');
grab(/model hashes: (\d+)\/(\d+)/,'model hash');
grab(/model immutability: (\d+)\/(\d+)/,'model immutability verdict');
grab(/specification view: (\d+)\/(\d+)/,'specification view');
grab(/safety verdicts: (\d+)\/(\d+)/,'safety verdict set');
grab(/stated value readings: (\d+)\/(\d+)/,'stated value reading');

console.log('\n== THE COMPARISON IS NOT VACUOUS ==');
(function(){
  const J=JSON.parse(fs.readFileSync(JS,'utf8'));
  const P=JSON.parse(fs.readFileSync(PY,'utf8'));
  const scen=Object.keys(J).filter(k=>k.indexOf('__')!==0);
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
  chk('the comparison covers every shipped fixture model',scen.length>=12,
    String(scen.length));
  chk('every model produced a real floor plan',
    scen.every(k=>J[k].v00.valid===true
      &&J[k].v00.geometry.elements.length>0));
  chk('every model produced a real elevation and section',
    scen.every(k=>J[k].v01.valid===true&&J[k].v03.valid===true));
  chk('a section really classifies cut geometry somewhere',
    scen.some(k=>J[k].v03.geometry.cut_count>0));
  chk('real SVG bytes were compared, not empty strings',
    scen.every(k=>typeof J[k].v00.svg==='string'&&J[k].v00.svg.length>2000));
  chk('real PDF content streams were compared',
    scen.every(k=>J[k].pdf&&J[k].pdf.content_streams.length===1
      &&J[k].pdf.content_streams[0].length>200));
  chk('real schedules with rows were compared',
    scen.some(k=>J[k].schedules.ROOM_SCHEDULE.schedule.row_count>0));
  chk('real quantities were compared',
    scen.every(k=>J[k].quantities.count>0));
  chk('both implementations agree the model is untouched',
    scen.every(k=>J[k].model_untouched===true&&P[k].model_untouched===true));
  chk('the unsupported view is refused identically on both sides',
    scen.every(k=>J[k].v10.valid===false&&P[k].v10.valid===false
      &&J[k].v11.valid===false&&P[k].v11.valid===false));
  chk('a traversing filename is refused on both sides',
    verdict(J,'safe_filename','../escape.svg')===null
    &&verdict(P,'safe_filename','../escape.svg')===null);
  chk('a plain filename is accepted on both sides',
    verdict(J,'safe_filename','A-001_plan.svg')==='A-001_plan.svg'
    &&verdict(P,'safe_filename','A-001_plan.svg')==='A-001_plan.svg');
  chk('a hostile string is unsafe on both sides',
    verdict(J,'unsafe','javascript:window.__PWNED__=1')===true
    &&verdict(P,'unsafe','javascript:window.__PWNED__=1')===true);
  chk('an inert label is not refused on either side',
    verdict(J,'unsafe','__proto__')===false
    &&verdict(P,'unsafe','__proto__')===false);
  chk('but a prototype key is refused as a key on both sides',
    verdict(J,'safe_key','__proto__')===false
    &&verdict(P,'safe_key','__proto__')===false);
  chk('the render fallback is never read as a value on either side',
    S(J.__stated)===S(P.__stated)
    &&J.__stated[0][1].status==='UNKNOWN'&&J.__stated[0][1].value===null);
  chk('a restricted drawing status is refused on both sides',
    scen.every(k=>J[k].title_block_restricted.status===null
      &&P[k].title_block_restricted.status===null));
  chk('the safety tables are pairs, never object keys',
    Array.isArray(J.__safety.unsafe)&&Array.isArray(P.__safety.safe_filename));
})();

console.log('\nDOCS PARITY SUITE: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
