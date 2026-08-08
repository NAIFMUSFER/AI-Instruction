// =============================================================================
// verify-offline.mjs — يثبت أن محرّك 3D يُحمّل بلا أي CDN خارجي (بعد vendor.sh).
// يشغّل خادماً ثابتاً على public/، يحجب نطاقات الـCDN الثلاثة، يفتح الصفحة،
// ثم يتحقّق أن window.ACS.ready === true (لا يصير true إلا بعد نجاح استيراد
// three وكل الإضافات الستّ) وأن لافتة الفشل مخفيّة وبلا أخطاء صفحة.
//
// المتطلّبات على جهازك (مرّة واحدة):
//   npm i -D playwright && npx playwright install chromium
// التشغيل من جذر المستودع:
//   node tools/verify-offline.mjs
// الخروج 0 = PASS ، الخروج 1 = FAIL.
// =============================================================================
import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { chromium } from 'playwright';

const ROOT = new URL('../public/', import.meta.url).pathname;
const CDN_HOSTS = ['unpkg.com', 'cdn.jsdelivr.net', 'cdnjs.cloudflare.com'];
const MIME = { '.html':'text/html', '.js':'text/javascript', '.mjs':'text/javascript',
  '.css':'text/css', '.json':'application/json', '.svg':'image/svg+xml',
  '.png':'image/png', '.jpg':'image/jpeg', '.webp':'image/webp', '.gltf':'model/gltf+json',
  '.glb':'model/gltf-binary', '.wasm':'application/wasm' };

const server = http.createServer(async (req, res) => {
  try {
    let p = decodeURIComponent(req.url.split('?')[0]);
    if (p === '/') p = '/index.html';
    const file = normalize(join(ROOT, p));
    if (!file.startsWith(ROOT)) { res.writeHead(403); return res.end('forbidden'); }
    const buf = await readFile(file);
    res.writeHead(200, { 'Content-Type': MIME[extname(file)] || 'application/octet-stream' });
    res.end(buf);
  } catch { res.writeHead(404); res.end('not found'); }
});

const PORT = 8791;
await new Promise(r => server.listen(PORT, r));

const browser = await chromium.launch({ args: ['--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });

const blocked = [], pageErrors = [];
await page.route('**/*', route => {
  const host = new URL(route.request().url()).hostname;
  if (CDN_HOSTS.some(h => host === h || host.endsWith('.' + h))) { blocked.push(host); return route.abort(); }
  return route.continue();
});
page.on('pageerror', e => pageErrors.push(String(e)));

await page.goto(`http://localhost:${PORT}/index.html`, { waitUntil: 'load' });
await page.fill('#lgName', 'verify').catch(() => {});
await page.click('#lgGo').catch(() => {});
// انتظر تهيئة المحرّك (window.ACS.ready) حتى 20 ثانية
let ready = false;
for (let i = 0; i < 40; i++) {
  ready = await page.evaluate(() => !!(window.ACS && window.ACS.ready === true)).catch(() => false);
  if (ready) break;
  await page.waitForTimeout(500);
}
const warnVisible = await page.isVisible('#engineWarn').catch(() => false);

await browser.close();
await new Promise(r => server.close(r));

const cdnBlockedCount = new Set(blocked).size;
const PASS = ready === true && warnVisible === false && pageErrors.length === 0;

console.log('── verify-offline ──');
console.log('  CDN hosts blocked at network layer:', [...new Set(blocked)].join(', ') || '(none seen)');
console.log('  window.ACS.ready:', ready);
console.log('  engineWarn visible:', warnVisible);
console.log('  page errors:', pageErrors.length, pageErrors.slice(0, 3));
console.log('\nRESULT:', PASS ? 'PASS ✅  three.js + all addons loaded with CDN blocked'
                              : 'FAIL ❌  see above (likely a missing vendored addon path)');
process.exit(PASS ? 0 : 1);
