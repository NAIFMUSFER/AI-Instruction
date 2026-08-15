/* يقارن مخرجات التأليف في بايثون وجافاسكربت مقارنة قانونية دقيقة.
   أي اختلاف في بصمة أمر، أو نموذج مرشّح، أو رمز تحقّق، أو فرق، أو نتيجة معاملة
   يُعدّ فشلاً — لا يُسمح بـ Python PASS / JS FAIL ولا بالعكس. */
const fs = require('fs');
const os = require('os');
const path = require('path');

const JS = process.env.ACS_PARITY_AUTHORING_JS
  || path.join(os.tmpdir(), 'acs_parity_authoring_js.json');
const PY = process.env.ACS_PARITY_AUTHORING_PY
  || path.join(os.tmpdir(), 'acs_parity_authoring_py.json');

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
        console.log('   js:', a.slice(Math.max(0, i - 140), i + 140));
        console.log('   py:', b.slice(Math.max(0, i - 140), i + 140));
        break;
      }
    }
  } else console.log('✓ identical', k);
});

/* فحوص صريحة إضافية على ما تطلبه المرحلة 5 نصّاً */
const scen = keys.filter(k => k.indexOf('__') !== 0);
let hashBad = 0, candBad = 0, issueBad = 0, txnBad = 0, diffBad = 0;
scen.forEach(k => {
  const j = J[k] || {}, p = P[k] || {};
  if (j.command_hash !== p.command_hash) { hashBad++;
    console.log('✗ COMMAND HASH DISAGREEMENT', k, j.command_hash, p.command_hash); }
  const jc = (j.preview && j.preview.preview) ? j.preview.preview.candidate_model_hash : null;
  const pc = (p.preview && p.preview.preview) ? p.preview.preview.candidate_model_hash : null;
  if (jc !== pc) { candBad++;
    console.log('✗ CANDIDATE MODEL HASH DISAGREEMENT', k, jc, pc); }
  const ji = JSON.stringify(((j.preview || {}).issues || []).map(i => i.code));
  const pi = JSON.stringify(((p.preview || {}).issues || []).map(i => i.code));
  if (ji !== pi) { issueBad++;
    console.log('✗ VALIDATION ISSUE DISAGREEMENT', k, ji, pi); }
  if (j.commit_state !== p.commit_state || j.committed !== p.committed
      || j.commit_revision !== p.commit_revision) { txnBad++;
    console.log('✗ TRANSACTION RESULT DISAGREEMENT', k,
                j.commit_state, p.commit_state, j.commit_revision, p.commit_revision); }
  if (JSON.stringify(canon(j.diff || null)) !== JSON.stringify(canon(p.diff || null))) {
    diffBad++; console.log('✗ DIFF DISAGREEMENT', k); }
});

const advJ = J.__adversarial__ || {}, advP = P.__adversarial__ || {};
let advBad = 0;
Object.keys(advJ).sort().forEach(k => {
  const j = advJ[k], p = advP[k] || {};
  if (JSON.stringify(canon(j)) !== JSON.stringify(canon(p))) {
    advBad++;
    console.log('✗ ADVERSARIAL DISAGREEMENT', k,
                JSON.stringify(j.normalise_codes), JSON.stringify(p.normalise_codes),
                JSON.stringify(j.preview_codes), JSON.stringify(p.preview_codes));
  }
});

console.log('\nAUTHORING PARITY: ' + (keys.length - bad) + '/' + keys.length +
            ' byte-identical   command hashes: ' + (scen.length - hashBad) + '/' + scen.length +
            '   candidate models: ' + (scen.length - candBad) + '/' + scen.length +
            '   validation issues: ' + (scen.length - issueBad) + '/' + scen.length +
            '   transaction results: ' + (scen.length - txnBad) + '/' + scen.length +
            '   diffs: ' + (scen.length - diffBad) + '/' + scen.length +
            '   adversarial: ' + (Object.keys(advJ).length - advBad) + '/' +
            Object.keys(advJ).length);
process.exit(bad || hashBad || candBad || issueBad || txnBad || diffBad || advBad ? 1 : 0);
