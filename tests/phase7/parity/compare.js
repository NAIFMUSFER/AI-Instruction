/* يقارن مخرجات العرض في بايثون وجافاسكربت مقارنة قانونية دقيقة.
   أي اختلاف في كاميرا، أو مادّة، أو رسم، أو مخزن تحكّم، أو سمة هندسية، أو حكم
   انحراف يُعدّ فشلاً — لا يُسمح بـ Python PASS / JS FAIL ولا بالعكس. */
const fs=require('fs'), os=require('os'), path=require('path');
const JS=process.env.ACS_PARITY_RENDER_JS
  ||path.join(os.tmpdir(),'acs_parity_render_js.json');
const PY=process.env.ACS_PARITY_RENDER_PY
  ||path.join(os.tmpdir(),'acs_parity_render_py.json');
const canon=v=>{ if(Array.isArray(v)) return v.map(canon);
  if(v&&typeof v==='object'){ const o={};
    Object.keys(v).sort().forEach(k=>{o[k]=canon(v[k]);}); return o; }
  return v; };
const S=v=>JSON.stringify(canon(v));
const J=JSON.parse(fs.readFileSync(JS,'utf8'));
const P=JSON.parse(fs.readFileSync(PY,'utf8'));
const keys=Array.from(new Set(Object.keys(J).concat(Object.keys(P)))).sort();
let bad=0;
keys.forEach(k=>{
  const a=S(J[k]), b=S(P[k]);
  if(a!==b){ bad++; console.log('✗ MISMATCH',k);
    for(let i=0;i<Math.max(a.length,b.length);i++)
      if(a[i]!==b[i]){
        console.log('   js:',a.slice(Math.max(0,i-160),i+160));
        console.log('   py:',b.slice(Math.max(0,i-160),i+160));
        break; }
  } else console.log('✓ identical',k); });

const scen=keys.filter(k=>k.indexOf('__')!==0);
let camBad=0,matBad=0,drwBad=0,bufBad=0,featBad=0,svgBad=0,pngBad=0,hashBad=0;
scen.forEach(k=>{
  const j=J[k]||{}, p=P[k]||{};
  if(S(j.cameras)!==S(p.cameras)){ camBad++; console.log('✗ CAMERA DISAGREEMENT',k); }
  if(S(j.materials)!==S(p.materials)){ matBad++; console.log('✗ MATERIAL DISAGREEMENT',k); }
  if(S(j.plans)!==S(p.plans)||S(j.elevations)!==S(p.elevations)
     ||S(j.sections)!==S(p.sections)){ drwBad++;
    console.log('✗ DRAWING DISAGREEMENT',k); }
  if(S(j.buffers)!==S(p.buffers)){ bufBad++; console.log('✗ BUFFER DISAGREEMENT',k); }
  if(S(j.features)!==S(p.features)){ featBad++; console.log('✗ FEATURE DISAGREEMENT',k); }
  if(j.plan_svg!==p.plan_svg||j.elevation_svg!==p.elevation_svg
     ||j.section_svg!==p.section_svg){ svgBad++;
    console.log('✗ SVG DISAGREEMENT',k); }
  if(S(j.png_sha)!==S(p.png_sha)){ pngBad++; console.log('✗ PNG DISAGREEMENT',k); }
  if(j.model_hash!==p.model_hash){ hashBad++;
    console.log('✗ MODEL HASH DISAGREEMENT',k,j.model_hash,p.model_hash); } });

const sub=(name,key)=>{
  const n=Object.keys(J[key]||{}).length;
  if(S(J[key])!==S(P[key])){ console.log('✗ '+name.toUpperCase()+' DISAGREEMENT');
    return [0,n]; }
  return [n,n]; };
const drift=sub('drift','__drift__');
const ai=sub('ai','__ai__');
const mats=sub('materials','__materials__');
const interior=sub('interior','__interior__');

console.log('\nRENDER PARITY: '+(keys.length-bad)+'/'+keys.length+
  ' byte-identical   cameras: '+(scen.length-camBad)+'/'+scen.length+
  '   materials: '+(scen.length-matBad)+'/'+scen.length+
  '   drawings: '+(scen.length-drwBad)+'/'+scen.length+
  '   control buffers: '+(scen.length-bufBad)+'/'+scen.length+
  '   geometry features: '+(scen.length-featBad)+'/'+scen.length+
  '   svg output: '+(scen.length-svgBad)+'/'+scen.length+
  '   png bytes: '+(scen.length-pngBad)+'/'+scen.length+
  '   model hashes: '+(scen.length-hashBad)+'/'+scen.length+
  '   drift cases: '+drift[0]+'/'+drift[1]+
  '   ai boundary: '+ai[0]+'/'+ai[1]+
  '   material ops: '+mats[0]+'/'+mats[1]+
  '   interior cameras: '+interior[0]+'/'+interior[1]);
process.exit(bad||camBad||matBad||drwBad||bufBad||featBad||svgBad||pngBad||hashBad
  ||drift[0]!==drift[1]||ai[0]!==ai[1]||mats[0]!==mats[1]
  ||interior[0]!==interior[1] ? 1 : 0);
