/* ============================================================================
   المرحلة 6 — تكافؤ بايثون وجافاسكربت في نماذج عرض مساحة العمل
   الفشل هنا يعني أن الواجهة تعرض للمستعمل شيئاً غير ما يقوله المحرّك في اللغة
   الأخرى من التطبيق — وهو ما يمنعه العقد صراحةً.
   ========================================================================== */
const fs=require('fs'), os=require('os'), path=require('path');
const {execFileSync}=require('child_process');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const RUN=path.join(ROOT,'tests','lib','run.js');
const JS=path.join(os.tmpdir(),'acs_parity_workspace_js.json');
const PY=path.join(os.tmpdir(),'acs_parity_workspace_py.json');
const env=Object.assign({},process.env,
  {ACS_PARITY_WORKSPACE_JS:JS,ACS_PARITY_WORKSPACE_PY:PY});

let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};

/* أي نتيجة قديمة في /tmp تُمسح أوّلاً كي لا يُقارَن تشغيل سابق */
[JS,PY].forEach(f=>{ try{ fs.unlinkSync(f); }catch(e){} });

console.log('\n== BOTH IMPLEMENTATIONS ARE ACTUALLY EXECUTED ==');
try{
  const o=execFileSync(process.execPath,[RUN,path.join(HERE,'parity','js_workspace_body.js')],
    {env:env,encoding:'utf8',maxBuffer:1<<28});
  chk('the browser implementation ran and wrote its result', /parity written/.test(o));
}catch(e){ chk('the browser implementation ran and wrote its result',false,
  String(e.stdout||'')+String(e.stderr||'')); }
try{
  const o=execFileSync('python3',[path.join(HERE,'parity','py_workspace.py')],
    {env:env,encoding:'utf8',maxBuffer:1<<28});
  chk('the python implementation ran and wrote its result', /parity written/.test(o));
}catch(e){ chk('the python implementation ran and wrote its result',false,
  String(e.stdout||'')+String(e.stderr||'')); }

console.log('\n== THE TWO RESULTS AGREE ==');
let cmp='', ok=false;
try{ cmp=execFileSync(process.execPath,[path.join(HERE,'parity','compare.js')],
  {env:env,encoding:'utf8',maxBuffer:1<<28}); ok=true; }
catch(e){ cmp=String(e.stdout||'')+String(e.stderr||''); ok=false; }
cmp.split('\n').filter(l=>/^✗/.test(l)).slice(0,8).forEach(l=>console.log('   ',l));
chk('the canonical comparison reports no mismatch', ok, cmp.split('\n').pop());
const grab=(re,label)=>{ const m=re.exec(cmp);
  chk('a real comparison was performed for '+label, !!m&&Number(m[2])>0, m?m[0]:cmp.slice(-200));
  chk('every '+label+' agrees between the two implementations',
      !!m&&m[1]===m[2], m?m[0]:''); };
grab(/WORKSPACE PARITY: (\d+)\/(\d+) byte-identical/,'top-level key');
grab(/trees: (\d+)\/(\d+)/,'project tree');
grab(/inspectors: (\d+)\/(\d+)/,'inspector view model');
grab(/issue counts: (\d+)\/(\d+)/,'issue-centre count');
grab(/export descriptors: (\d+)\/(\d+)/,'export descriptor');
grab(/model hashes: (\d+)\/(\d+)/,'model hash');
grab(/labels: (\d+)\/(\d+)/,'provenance label');
grab(/ui labels: (\d+)\/(\d+)/,'interface label');
grab(/display values: (\d+)\/(\d+)/,'displayed value');
grab(/references: (\d+)\/(\d+)/,'visual-reference verdict');
grab(/operations: (\d+)\/(\d+)/,'available-operation set');

console.log('\n== THE COMPARISON IS NOT VACUOUS ==');
(function(){
  const J=JSON.parse(fs.readFileSync(JS,'utf8'));
  const P=JSON.parse(fs.readFileSync(PY,'utf8'));
  const CANON=JSON.parse(fs.readFileSync(path.join(ROOT,'acs_workspace.json'),'utf8'));
  chk('both files carry the same keys',
      JSON.stringify(Object.keys(J).sort())===JSON.stringify(Object.keys(P).sort()));
  const scen=Object.keys(J).filter(k=>k.indexOf('__')!==0);
  chk('the comparison covers every shipped fixture model',
      scen.length>=8, String(scen.length));
  chk('every model produced a tree with real nodes',
      scen.every(k=>J[k].tree_en.node_count>3&&P[k].tree_en.node_count>3));
  chk('every model produced a populated inspector for a real space',
      scen.some(k=>J[k].insp_en['g.majlis']&&J[k].insp_en['g.majlis'].valid===true));
  chk('an unresolvable identifier is refused identically in both',
      scen.every(k=>J[k].insp_en['nope'].valid===false
                 &&P[k].insp_en['nope'].valid===false));
  chk('the Arabic tree really differs from the English one',
      scen.every(k=>JSON.stringify(J[k].tree_ar)!==JSON.stringify(J[k].tree_en)));
  chk('the Arabic and English trees carry identical node identifiers',
      scen.every(k=>{
        const ids=t=>{const o=[];(function w(n){o.push(n.node_id);
          (n.children||[]).forEach(w);})(t.root); return o.join('|');};
        return ids(J[k].tree_ar)===ids(J[k].tree_en); }));
  chk('no view model claims it writes to the engineering model',
      scen.every(k=>J[k].insp_en['g.majlis'].writes_to_model!==true
                 ||J[k].insp_en['g.majlis'].valid===false));
  chk('every interface label is covered in both languages',
      Object.keys(CANON.ui_labels).every(k=>
        J.__ui_labels__['en|'+k]===CANON.ui_labels[k].en
        &&J.__ui_labels__['ar|'+k]===CANON.ui_labels[k].ar));
  chk('an unrecognised provenance key falls back to unknown, never to a claim',
      J.__labels__['en|not_a_label_key']===CANON.provenance_labels.unknown.en
      &&P.__labels__['ar|not_a_label_key']===CANON.provenance_labels.unknown.ar);
  chk('no provenance label is one of the forbidden compliance words',
      Object.keys(J.__labels__).every(k=>
        CANON.forbidden_provenance_labels.every(f=>
          String(J.__labels__[k]).trim().toLowerCase()!==String(f).trim().toLowerCase())));
  chk('an unknown value reads as unknown in both languages and both implementations',
      J.__display__['en|UNKNOWN|0'].known===false
      &&P.__display__['ar|UNKNOWN|0'].known===false
      &&J.__display__['ar|UNKNOWN|0'].text===CANON.unknown_label.ar);
  chk('a very large number is formatted identically, not in exponent form',
      /^[0-9]+$/.test(J.__display__['en|EDITABLE|5'].text)
      &&J.__display__['en|EDITABLE|5'].text===P.__display__['en|EDITABLE|5'].text,
      J.__display__['en|EDITABLE|5'].text+' vs '+P.__display__['en|EDITABLE|5'].text);
  chk('a unit conversion never claims to write to the model',
      Object.keys(J.__convert__).every(k=>J.__convert__[k].writes_to_model===false));
  chk('a malicious visual reference is refused by both implementations',
      ['script_uri','markup_caption','data_html','svg_caption'].every(k=>
        J.__references__[k].valid===false&&P.__references__[k].valid===false
        &&J.__references__[k].count===0));
  chk('a legitimate visual reference is accepted by both implementations',
      J.__references__.ok.valid===true&&P.__references__.ok.valid===true);
  chk('the assistant never reports a commit',
      J.__assistant__.propose.committed===false
      &&P.__assistant__.propose.committed===false);
  chk('the assistant refuses to guess an unresolved target',
      J.__assistant__.propose_unknown.valid===false
      &&P.__assistant__.propose_unknown.valid===false);
  chk('interface state is proven to sit outside the engineering model',
      J.__ui_boundary__.clean===true&&P.__ui_boundary__.clean===true
      &&J.__ui_boundary__.leaked_keys.length===0
      &&J.__ui_boundary__.model_hash_before===J.__ui_boundary__.model_hash_after);
  chk('requirement coverage never claims full coverage',
      ['en|real','ar|real','en|empty','en|null'].every(k=>
        J.__coverage__[k].claims_full_coverage===false
        &&P.__coverage__[k].claims_full_coverage===false));
  chk('unresolved requirements are counted, not hidden',
      J.__coverage__['en|real'].unresolved>0
      &&J.__coverage__['en|real'].unresolved===P.__coverage__['en|real'].unresolved);
  chk('a planted difference would be detected', (function(){
    const canon=v=>{ if(Array.isArray(v)) return v.map(canon);
      if(v&&typeof v==='object'){ const o={};
        Object.keys(v).sort().forEach(k=>{o[k]=canon(v[k]);}); return o; }
      return v; };
    const t=JSON.parse(JSON.stringify(P[scen[0]]));
    t.model_hash_of='tampered';
    return JSON.stringify(canon(J[scen[0]]))!==JSON.stringify(canon(t)); })());
})();

console.log('\n──────────────────────────────────────────────');
console.log('WORKSPACE PARITY: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
