// UI contract only. No Firebase calls, real phone numbers, or SMS charges.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const root = path.resolve(__dirname, '../../public/firebase-check');
const mock = `
export const inMemoryPersistence = {};
export function initializeAuth(app, options) {
  if (options.persistence !== inMemoryPersistence) throw Error('persistent auth');
  return {};
}
export class RecaptchaVerifier { clear() {} }
export async function signInWithPhoneNumber(auth, phone) {
  window.sent = (window.sent || 0) + 1;
  window.normalizedPhone = phone;
  return { confirm: async code => {
    if (code !== '123456') throw {code: 'auth/invalid-verification-code'};
    window.confirmed = true;
    return {user: {}};
  }};
}
export async function signOut() { window.signedOut = true; }
`;
(async () => {
  const server = http.createServer((req, res) => {
    const name = req.url === '/' ? 'index.html' : req.url.slice(1);
    if (!['index.html', 'check.js', 'style.css'].includes(name)) { res.writeHead(404).end(); return; }
    res.setHeader('Content-Type', name.endsWith('.js') ? 'application/javascript' : name.endsWith('.css') ? 'text/css' : 'text/html');
    res.end(fs.readFileSync(path.join(root, name)));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({headless: true});
    const page = await browser.newPage({viewport: {width: 390, height: 844}});
    const origin = `http://127.0.0.1:${server.address().port}`;
    await page.route('**/*', route => {
      const url = route.request().url();
      if (url.startsWith(origin)) return route.continue();
      if (url.endsWith('/firebase-app.js')) return route.fulfill({contentType: 'application/javascript', body: 'export function initializeApp(config) { return config; }'});
      if (url.endsWith('/firebase-auth.js')) return route.fulfill({contentType: 'application/javascript', body: mock});
      return route.abort();
    });
    await page.goto(origin);
    await page.waitForFunction(() => !document.getElementById('send').disabled);
    assert.equal(await page.evaluate(() => window.sent || 0), 0);
    await page.fill('#phone', '123');
    await page.click('#send');
    assert.equal(await page.evaluate(() => window.sent || 0), 0);
    await page.fill('#phone', '٠٥١٢٣٤٥٦٧٨');
    await page.click('#send');
    await page.waitForSelector('#code-form', {state: 'visible'});
    assert.equal(await page.evaluate(() => window.normalizedPhone), '+966512345678');
    assert.equal(await page.isDisabled('#send'), true);
    await page.fill('#code', '000000');
    await page.click('#confirm');
    await page.waitForFunction(() => document.getElementById('status').textContent.includes('غير صحيح'));
    assert.equal(await page.evaluate(() => !!window.confirmed), false);
    await page.fill('#code', '١٢٣٤٥٦');
    await page.click('#confirm');
    await page.waitForFunction(() => document.getElementById('status').textContent.includes('نجح التحقق'));
    assert.equal(await page.evaluate(() => window.signedOut), true);
    assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0);
    assert.equal(await page.inputValue('#code'), '');
    assert.equal(await page.inputValue('#phone'), '');
    assert.equal(await page.isDisabled('#send'), true);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    console.log('PASS: mocked phone verification UI; invalid input/code, normalization, cooldown, cleanup, mobile width. No SMS sent.');
  } finally {
    await browser?.close();
    server.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
