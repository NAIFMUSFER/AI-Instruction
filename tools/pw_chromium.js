/* ============================================================================
   محدِّد ثنائيّة Chromium لـPlaywright — بلا شبكة، وبلا نجاح مزيَّف.

   السبب: نسخة Playwright المثبّتة تطلب بناءً محدّداً من Chromium (مثلاً 1234)،
   بينما الصندوق قد يحمل بناءً آخر (1194) أو رابطاً رمزياً /opt/pw-browsers/chromium.
   بلا شبكة لا يمكن تنزيل البناء المطلوب، فإمّا أن نستعمل الموجود صراحةً وإمّا
   أن نُعلن أن القياس متعذّر. لا نتظاهر بالنجاح.

     const PW = require('tools/pw_chromium.js');
     const exe = PW.executable();          // مسار موجود، أو null
     const browser = await PW.launch();    // يرمي إن لم يوجد متصفّح
   ========================================================================== */
const fs = require('fs'), path = require('path');

const CANDIDATE_ENV = ['ACS_CHROMIUM', 'CHROMIUM_PATH', 'PLAYWRIGHT_CHROMIUM_EXECUTABLE'];

function fromPlaywright() {
  try {
    const { chromium } = require('playwright');
    const p = chromium.executablePath();
    if (p && fs.existsSync(p)) return p;
  } catch (e) { /* يُبلَّغ عنه في المستدعي */ }
  return null;
}

function scanBrowsersRoot() {
  const roots = [process.env.PLAYWRIGHT_BROWSERS_PATH, '/opt/pw-browsers',
    path.join(process.env.HOME || '/root', '.cache', 'ms-playwright')]
    .filter(Boolean);
  const found = [];
  for (const root of roots) {
    if (!fs.existsSync(root)) continue;
    /* الرابط الرمزي المباشر أوّلاً — أوضح نيّة من مسح الأرقام */
    for (const direct of ['chromium', 'chrome']) {
      const d = path.join(root, direct);
      try { if (fs.existsSync(d) && fs.statSync(d).isFile()) found.push(d); }
      catch (e) { /* تجاهل */ }
    }
    let entries = [];
    try { entries = fs.readdirSync(root); } catch (e) { entries = []; }
    for (const e of entries) {
      for (const rel of [
        path.join(e, 'chrome-linux', 'chrome'),
        path.join(e, 'chrome-linux64', 'chrome'),
        path.join(e, 'chrome-headless-shell-linux64', 'chrome-headless-shell')]) {
        const p = path.join(root, rel);
        if (fs.existsSync(p)) found.push(p);
      }
    }
  }
  return found;
}

function executable() {
  for (const k of CANDIDATE_ENV) {
    if (process.env[k] && fs.existsSync(process.env[k])) return process.env[k];
  }
  const pw = fromPlaywright();
  if (pw) return pw;
  const scanned = scanBrowsersRoot();
  return scanned.length ? scanned[0] : null;
}

async function launch(opts) {
  const { chromium } = require('playwright');
  const exe = executable();
  if (!exe) throw new Error('no Chromium binary is available in this sandbox');
  return chromium.launch(Object.assign({ executablePath: exe }, opts || {}));
}

module.exports = { executable, launch, scanBrowsersRoot };
