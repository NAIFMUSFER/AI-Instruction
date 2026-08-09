/* مقارنة قانونية بين مخرجات بايثون وجافاسكربت لطبقة واحدة. */
const fs=require('fs'), os=require('os'), path=require('path');
const layer=process.argv[2];
const JS=process.env.ACS_PARITY_JS||path.join(os.tmpdir(),'acs_parity_js_'+layer+'.json');
const PY=process.env.ACS_PARITY_PY||path.join(os.tmpdir(),'acs_parity_py_'+layer+'.json');
const canon=v=>{ if(Array.isArray(v)) return v.map(canon);
  if(v&&typeof v==='object'){const o={};Object.keys(v).sort().forEach(k=>{o[k]=canon(v[k]);});return o;}
  return v; };
const J=JSON.parse(fs.readFileSync(JS,'utf8')), P=JSON.parse(fs.readFileSync(PY,'utf8'));
const keys=Array.from(new Set(Object.keys(J).concat(Object.keys(P)))).sort();
let bad=0;
keys.forEach(k=>{ if(JSON.stringify(canon(J[k]))!==JSON.stringify(canon(P[k]))){bad++;
  console.log('✗ MISMATCH',k);} });
console.log(layer.toUpperCase()+' PARITY: '+(keys.length-bad)+'/'+keys.length+' byte-identical');
process.exit(bad?1:0);
