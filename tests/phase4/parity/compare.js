/* يقارن مخرجات زمن التشغيل في بايثون وجافاسكربت مقارنة قانونية دقيقة.
   أي اختلاف في القبول أو رمز التحقّق أو هوية جسم أو مسافة أو بصمة مشهد
   يُعدّ فشلاً — لا يُسمح بـ Python PASS / JS FAIL ولا بالعكس. */
const fs = require('fs');
const os = require('os');
const path = require('path');

const JS = process.env.ACS_PARITY_RUNTIME_JS
  || path.join(os.tmpdir(), 'acs_parity_runtime_js.json');
const PY = process.env.ACS_PARITY_RUNTIME_PY
  || path.join(os.tmpdir(), 'acs_parity_runtime_py.json');

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
        console.log('   js:', a.slice(Math.max(0, i - 130), i + 130));
        console.log('   py:', b.slice(Math.max(0, i - 130), i + 130));
        break;
      }
    }
  } else console.log('✓ identical', k);
});

/* فحص صريح إضافي: اتّفاق القبول وتسلسل رموز التحقّق في الحالات الخصومية */
const advJ = (J.__adversarial__ || {}), advP = (P.__adversarial__ || {});
let advBad = 0;
Object.keys(advJ).sort().forEach(k => {
  const j = advJ[k], p = advP[k] || {};
  const sameAccept = j.accepted === p.accepted;
  const sameCodes = JSON.stringify((j.issues || []).map(i => i.code)) ===
                    JSON.stringify((p.issues || []).map(i => i.code));
  if (!sameAccept || !sameCodes) {
    advBad++;
    console.log('✗ ADVERSARIAL DISAGREEMENT', k,
                'js.accepted=' + j.accepted, 'py.accepted=' + p.accepted,
                JSON.stringify((j.issues || []).map(i => i.code)),
                JSON.stringify((p.issues || []).map(i => i.code)));
  }
});

/* فحص صريح إضافي: تسلسل رموز التحقّق في كل عملية زمن تشغيل لكل استعلام */
const OPS = ['validate', 'nav_bad', 'capsule_bad', 'spawn_default', 'spawn_far',
             'move_short', 'move_long', 'move_bad', 'select', 'select_bad',
             'select_null', 'inspect_bad', 'visibility_bad_mode',
             'visibility_bad_target', 'measure_bad_type', 'measure_bad_vector',
             'measure_bad_target', 'portal_bad_state', 'portal_bad_id',
             'time_ok', 'time_bad'];
let opBad = 0, opTotal = 0;
keys.filter(k => k.indexOf('__') !== 0).forEach(k => {
  OPS.forEach(op => {
    const j = (J[k] || {})[op] || {}, p = (P[k] || {})[op] || {};
    opTotal++;
    const jc = JSON.stringify((j.issues || []).map(i => i.code));
    const pc = JSON.stringify((p.issues || []).map(i => i.code));
    if (jc !== pc || j.valid !== p.valid) {
      opBad++;
      console.log('✗ OPERATION DISAGREEMENT', k + '.' + op,
                  'js.valid=' + j.valid, 'py.valid=' + p.valid, jc, pc);
    }
  });
});

console.log('\nRUNTIME PARITY: ' + (keys.length - bad) + '/' + keys.length +
            ' byte-identical   adversarial agreement: ' +
            (Object.keys(advJ).length - advBad) + '/' + Object.keys(advJ).length +
            '   operation agreement: ' + (opTotal - opBad) + '/' + opTotal);
process.exit(bad || advBad || opBad ? 1 : 0);
