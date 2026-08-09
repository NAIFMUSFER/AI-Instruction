/* يقارن نماذج عرض مساحة العمل في بايثون وجافاسكربت مقارنة قانونية دقيقة.
   أي اختلاف في شجرة، أو فاحص، أو ملاحظة، أو تغطية، أو واصف تصدير، أو حكم على
   مرجع بصري يُعدّ فشلاً — لا يُسمح بـ Python PASS / JS FAIL ولا بالعكس. */
const fs = require('fs');
const os = require('os');
const path = require('path');

const JS = process.env.ACS_PARITY_WORKSPACE_JS
  || path.join(os.tmpdir(), 'acs_parity_workspace_js.json');
const PY = process.env.ACS_PARITY_WORKSPACE_PY
  || path.join(os.tmpdir(), 'acs_parity_workspace_py.json');

const canon = v => {
  if (Array.isArray(v)) return v.map(canon);
  if (v && typeof v === 'object') {
    const o = {};
    Object.keys(v).sort().forEach(k => { o[k] = canon(v[k]); });
    return o;
  }
  return v;
};

const J = JSON.parse(fs.readFileSync(JS, 'utf8'));
const P = JSON.parse(fs.readFileSync(PY, 'utf8'));
const keys = Array.from(new Set(Object.keys(J).concat(Object.keys(P)))).sort();
let bad = 0;
keys.forEach(k => {
  const a = JSON.stringify(canon(J[k]));
  const b = JSON.stringify(canon(P[k]));
  if (a !== b) {
    bad++;
    console.log('✗ MISMATCH', k);
    for (let i = 0; i < Math.max(a.length, b.length); i++) {
      if (a[i] !== b[i]) {
        console.log('   js:', a.slice(Math.max(0, i - 160), i + 160));
        console.log('   py:', b.slice(Math.max(0, i - 160), i + 160));
        break;
      }
    }
  } else console.log('✓ identical', k);
});

/* فحوص صريحة على ما تطلبه المرحلة 6 نصّاً */
const scen = keys.filter(k => k.indexOf('__') !== 0);
let treeBad = 0, inspBad = 0, issueBad = 0, expBad = 0, hashBad = 0;
scen.forEach(k => {
  const j = J[k] || {}, p = P[k] || {};
  ['en', 'ar'].forEach(lang => {
    if (JSON.stringify(canon(j['tree_' + lang])) !==
        JSON.stringify(canon(p['tree_' + lang]))) {
      treeBad++; console.log('✗ TREE DISAGREEMENT', k, lang);
    }
    if (JSON.stringify(canon(j['insp_' + lang])) !==
        JSON.stringify(canon(p['insp_' + lang]))) {
      inspBad++; console.log('✗ INSPECTOR DISAGREEMENT', k, lang);
    }
  });
  const ji = JSON.stringify(canon((j.issues || {}).counts));
  const pi = JSON.stringify(canon((p.issues || {}).counts));
  if (ji !== pi) { issueBad++; console.log('✗ ISSUE COUNT DISAGREEMENT', k, ji, pi); }
  if (JSON.stringify(canon(j.exports)) !== JSON.stringify(canon(p.exports))) {
    expBad++; console.log('✗ EXPORT DESCRIPTOR DISAGREEMENT', k);
  }
  if (j.model_hash_of !== p.model_hash_of) {
    hashBad++; console.log('✗ MODEL HASH DISAGREEMENT', k, j.model_hash_of, p.model_hash_of);
  }
});
const langScen = scen.length * 2;

const sub = (name, key) => {
  const a = JSON.stringify(canon(J[key])), b = JSON.stringify(canon(P[key]));
  const n = Object.keys(J[key] || {}).length;
  if (a !== b) { console.log('✗ ' + name.toUpperCase() + ' DISAGREEMENT'); return [0, n]; }
  return [n, n];
};
const labels = sub('labels', '__labels__');
const display = sub('display', '__display__');
const refs = sub('references', '__references__');
const opsC = sub('operations', '__operations__');
const uiL = sub('ui labels', '__ui_labels__');

console.log('\nWORKSPACE PARITY: ' + (keys.length - bad) + '/' + keys.length +
            ' byte-identical   trees: ' + (langScen - treeBad) + '/' + langScen +
            '   inspectors: ' + (langScen - inspBad) + '/' + langScen +
            '   issue counts: ' + (scen.length - issueBad) + '/' + scen.length +
            '   export descriptors: ' + (scen.length - expBad) + '/' + scen.length +
            '   model hashes: ' + (scen.length - hashBad) + '/' + scen.length +
            '   labels: ' + labels[0] + '/' + labels[1] +
            '   display values: ' + display[0] + '/' + display[1] +
            '   references: ' + refs[0] + '/' + refs[1] +
            '   operations: ' + opsC[0] + '/' + opsC[1] +
            '   ui labels: ' + uiL[0] + '/' + uiL[1]);
process.exit(bad || treeBad || inspBad || issueBad || expBad || hashBad
             || labels[0] !== labels[1] || display[0] !== display[1]
             || refs[0] !== refs[1] || opsC[0] !== opsC[1]
             || uiL[0] !== uiL[1] ? 1 : 0);
