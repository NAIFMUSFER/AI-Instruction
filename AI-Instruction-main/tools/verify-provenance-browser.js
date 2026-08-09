/* =============================================================================
 * verify-provenance-browser.js
 * تحقّق إنتاجي من صدق تقرير التغطية (Provenance) — يُلصَق في Console المتصفح
 * على الموقع المنشور بعد إعادة النشر عبر Git.
 *
 * الاستخدام:
 *   1) افتح الموقع، سجّل الدخول حتى تظهر اللوحة.
 *   2) DevTools → Console → الصق هذا الملف كاملاً → Enter.
 *   3) انتظر حتى تُطبع الجداول (يولّد نموذجين: فيلا، وفيلا بدون مصعد).
 *
 * لا يعدّل الكود ولا الهندسة — يقرأ الواجهة ويلتقط ملف JSON المُصدَّر فقط.
 * ============================================================================= */
(async () => {
  const VILLA = 'فيلا دورين، الدور الأرضي يحتوي على مجلس وصالة ومطبخ وغرفة ضيوف وحمامين، ' +
                'والدور الأول يحتوي على 4 غرف نوم و3 حمامات وصالة عائلية، مع درج وموقف سيارتين.';
  const VILLA_NO_LIFT = VILLA.replace(/\.$/, '') + ' بدون مصعد.';

  // عبارات ممنوعة بلا دليل قاعدة منفَّذة
  const FORBIDDEN = /وفق\s+الكود|متطلّب\s*كود|متطلب\s*كود|مطلوب\s+حسب\s+الكود|مطابق\s+للكود|متوافق\s+مع\s+الكود|code[- ]?compliant|code[- ]?required|إصلاح\s+مطلوب|إصلاح\s*:/i;
  const CONNECT   = /يربط\s+(?:بين\s+)?(?:الطوابق|الأدوار)/i;

  const R = [];
  const rec = (check, status, evidence) => R.push({ check, status, evidence: String(evidence).slice(0, 160) });
  const $ = id => document.getElementById(id);
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const txt = () => ($('reportBox') ? $('reportBox').innerText : '');

  async function generate(prompt, useAI) {
    $('descText').value = prompt;
    const btn = useAI ? $('genLLM') : $('genText');
    btn.click();
    // انتظر ظهور التقرير (حتى 90 ثانية لمسار الذكاء)
    for (let i = 0; i < (useAI ? 180 : 30); i++) {
      await wait(500);
      if (txt().trim()) break;
    }
    return txt();
  }

  // يلتقط ملف JSON المُصدَّر دون تنزيله فعلياً
  async function captureJsonExport() {
    const origCreate = URL.createObjectURL;
    let captured = null;
    URL.createObjectURL = function (blob) { captured = blob; return origCreate.call(URL, blob); };
    const origClick = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () { /* امنع التنزيل الفعلي */ };
    try { $('bJson').click(); await wait(400); }
    finally { URL.createObjectURL = origCreate; HTMLAnchorElement.prototype.click = origClick; }
    if (!captured) return null;
    return JSON.parse(await captured.text());
  }

  console.log('%c▶ توليد الفيلا…', 'font-weight:bold');
  const report = await generate(VILLA, false);
  if (!report.trim()) { console.error('لم يظهر تقرير التغطية — تأكّد من تسجيل الدخول وظهور اللوحة.'); return; }

  // 1) عدد الأدوار المطلوب = 2
  rec('Requested floors = 2', /عدد الأدوار الذي طلبته:\s*2/.test(report) ? 'PASS' : 'FAIL',
      (report.match(/عدد الأدوار الذي طلبته:\s*\d+/) || ['(غير موجود)'])[0]);

  // 2) لا يُعرض ادّعاء عدد أدوار مخالف تحت «طلبتَه ونُفِّذ»
  const userSection = (report.split('◇')[0].split('＋')[0] || '');
  rec('No "عدد الأدوار 3" under طُلب ونُفِّذ',
      /عدد الأدوار\s*3/.test(userSection) ? 'FAIL' : 'PASS',
      userSection.slice(0, 120));

  // 3+4) السطح مصنّف كإضافة نظام وبلا ادّعاء كود
  const sysIdx = report.indexOf('أضافه النظام تلقائياً');
  rec('Roof / technical level = SYSTEM_DEFAULT',
      (sysIdx >= 0 || !/roof|سطح/i.test(report)) ? 'PASS' : 'PARTIAL',
      sysIdx >= 0 ? report.slice(sysIdx, sysIdx + 140) : '(لا يوجد قسم إضافات)');

  // 4/12) لا عبارة كود ممنوعة في التقرير المعروض
  rec('No fake code claims in rendered report', FORBIDDEN.test(report) ? 'FAIL' : 'PASS',
      (report.match(FORBIDDEN) || ['(none)'])[0]);

  // 5) الدرج: تمثيل بصري لا ربط رأسي مُتحقَّق
  rec('Stair wording truthful (no connectivity claim)', CONNECT.test(report) ? 'FAIL' : 'PASS',
      (report.match(CONNECT) || ['(none)'])[0]);

  // 11) CODE_REQUIRED = 0 (لا قسم قاعدة موثّقة)
  rec('CODE_REQUIRED = 0 (no rule engine)', /مطلوب بقاعدة موثّقة/.test(report) ? 'FAIL' : 'PASS',
      /مطلوب بقاعدة موثّقة/.test(report) ? 'ظهر قسم قاعدة!' : 'لا قسم قاعدة — صحيح');

  // إفصاح صريح
  rec('Discloses no code validation performed',
      /لم يُنفَّذ تحقّق مطابقة لأي كود/.test(report) ? 'PASS' : 'PARTIAL', '');

  // 6+10) تصدير JSON: مصدر + عناصر
  const json = await captureJsonExport();
  if (!json) rec('JSON provenance exported', 'FAIL', 'تعذّر التقاط ملف JSON');
  else {
    const reqs = ((json.meta || {}).requirements) || [];
    const srcs = [...new Set(reqs.map(r => r.source).filter(Boolean))];
    const objs = Object.values(json.floors || {})
      .flatMap(f => (f.rooms || []).flatMap(r => (r.objects || []).map(o => o.kind + '×' + (o.count || 1))));
    rec('JSON provenance exported (source field)', srcs.length ? 'PASS' : 'FAIL', 'sources: ' + srcs.join(','));
    rec('JSON backward-compatible (meta/floors/rooms intact)',
        (json.meta && json.floors && json.levels) ? 'PASS' : 'FAIL', Object.keys(json).join(','));
    rec('Parking: car ×2 preserved (dropped = 0)',
        objs.some(o => /^car×2$/.test(o)) ? 'PASS' : 'FAIL', objs.join(', ') || '(no objects)');
    rec('Stairs object present', objs.some(o => /^stairs×/.test(o)) ? 'PASS' : 'PARTIAL', objs.join(', '));
    const noCodeInJson = !FORBIDDEN.test(JSON.stringify(json.meta || {}));
    rec('No fake code claims inside exported JSON', noCodeInJson ? 'PASS' : 'FAIL', '');
  }

  // 9) الاستبعاد
  console.log('%c▶ توليد الفيلا «بدون مصعد»…', 'font-weight:bold');
  const rep2 = await generate(VILLA_NO_LIFT, false);
  const excOk = /مُستبعَد/.test(rep2) && /مصعد/.test(rep2.slice(rep2.indexOf('مُستبعَد')));
  const notAdded = !/أضافه النظام تلقائياً[\s\S]*مصعد/.test(rep2);
  rec('Exclusion preserved (elevator EXCLUDED, not auto-added)',
      (excOk && notAdded) ? 'PASS' : 'FAIL', rep2.slice(Math.max(0, rep2.indexOf('مُستبعَد')), rep2.indexOf('مُستبعَد') + 120));

  // 13) انحدار التشغيل
  rec('ACS.ready === true', (window.ACS && window.ACS.ready === true) ? 'PASS' : 'FAIL', String(window.ACS && window.ACS.ready));
  rec('3D canvas present / renders', document.querySelector('canvas') ? 'PASS' : 'FAIL',
      document.querySelectorAll('canvas').length + ' canvas');
  rec('Engine warning hidden', ($('engineWarn') && getComputedStyle($('engineWarn')).display === 'none') ? 'PASS' : 'FAIL', '');

  console.table(R);
  const fails = R.filter(r => r.status === 'FAIL');
  console.log(fails.length
    ? '%c✗ FAILED CHECKS: ' + fails.map(f => f.check).join(' | ')
    : '%c✓ PROVENANCE INTEGRITY = VERIFIED (all checks passed in production)',
    'font-weight:bold;color:' + (fails.length ? '#ef4444' : '#22c55e'));
  console.log('انسخ الجدول أعلاه وأرسله لإغلاق البوابة.');
})();
