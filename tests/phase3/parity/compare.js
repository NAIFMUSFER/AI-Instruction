/* يقارن مخرجات مصرّف المشهد في بايثون وجافاسكربت مقارنة قانونية دقيقة.
   أي اختلاف في القبول أو رمز التحقّق أو هوية الجسم أو بصمة النموذج أو المشهد
   يُعدّ فشلاً — لا يُسمح بـ Python PASS / JS FAIL ولا بالعكس. */
const fs = require('fs');
const os = require('os');
const path = require('path');

const JS = process.env.ACS_PARITY_JS || path.join(os.tmpdir(), 'acs_parity_js.json');
const PY = process.env.ACS_PARITY_PY || path.join(os.tmpdir(), 'acs_parity_py.json');

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

/* عدم الخواء: مقارنة بلا مشاهد ليست نجاحاً بل غياب فحص. الحدّان أدناه هما ما
   يُنتَج فعلاً اليوم؛ نقصان أيّهما يعني أن جانباً توقّف عن الكتابة أو أن ملفّاً
   قديماً في /tmp قُرئ — وكلاهما فشل يُعلَن، لا مرور صامت. */
const MIN_KEYS = 116, MIN_ADV = 16;
if (keys.length === 0) {
  console.log('✗ THE COMPARISON SET IS EMPTY — nothing was compared');
  process.exit(2);
}
if (Object.keys(J).length === 0 || Object.keys(P).length === 0) {
  console.log('✗ ONE SIDE WROTE NOTHING — js:' + Object.keys(J).length
              + ' py:' + Object.keys(P).length);
  process.exit(2);
}
if (keys.length < MIN_KEYS) {
  console.log('✗ THE COMPARISON IS VACUOUS: ' + keys.length
              + ' groups, minimum ' + MIN_KEYS);
  process.exit(2);
}
if (Object.keys(J.__adversarial__ || {}).length < MIN_ADV) {
  console.log('✗ THE ADVERSARIAL BLOCK IS VACUOUS: '
              + Object.keys(J.__adversarial__ || {}).length
              + ', minimum ' + MIN_ADV);
  process.exit(2);
}
console.log('not vacuous: ' + keys.length + ' groups (minimum ' + MIN_KEYS
            + ') and ' + Object.keys(J.__adversarial__ || {}).length
            + ' adversarial cases (minimum ' + MIN_ADV + ')');

let bad = 0;
keys.forEach(k => {
  const a = JSON.stringify(canon(J[k]));
  const b = JSON.stringify(canon(P[k]));
  if (a !== b) {
    bad++;
    console.log('✗ MISMATCH', k);
    for (let i = 0; i < Math.max(a.length, b.length); i++) {
      if (a[i] !== b[i]) {
        console.log('   js:', a.slice(Math.max(0, i - 110), i + 110));
        console.log('   py:', b.slice(Math.max(0, i - 110), i + 110));
        break;
      }
    }
  } else console.log('✓ identical', k);
});

/* فحص صريح إضافي: اتّفاق القبول/الرفض ورموز التحقّق في الحالات الخصومية */
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

console.log('\nVISUAL PARITY: ' + (keys.length - bad) + '/' + keys.length +
            ' byte-identical   adversarial agreement: ' +
            (Object.keys(advJ).length - advBad) + '/' + Object.keys(advJ).length);
process.exit(bad || advBad ? 1 : 0);
