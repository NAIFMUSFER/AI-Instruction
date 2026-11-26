'use strict';
// Owner decisions on the guest brief, checked in the real guest workspace at
// phone (393x852) and desktop (1440x900) widths, right-to-left:
//  1. a missing building size or floor count is asked, never prefilled;
//  2. «فهمنا: …» is shown before anything is drawn, assumptions are marked, and
//     one tap on «ارسم» draws exactly that summary while «عدّل» draws nothing;
//  3. the building size has its own fields, separate from the land;
//  4. a request the local generator cannot honour is listed before drawing;
//  5. a description and a field that disagree are offered as a choice.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const PW = require('../../tools/pw_chromium.js');
const { serve, origin, sourceSHA } = require('./test_public_apartment_journey.cjs');

const out = path.resolve(process.env.ACS_APARTMENT_EVIDENCE || 'logs/public-apartment', 'confirm-card-' + sourceSHA.slice(0, 12));
const fieldIds = ['bldW', 'bldD', 'siteW', 'siteD', 'nFloors'];

async function open(page) {
  await page.goto(origin + '/?guest=1&new=1');
  await page.locator('#acsGuestBanner[data-recovery="complete"]').waitFor();
  assert.equal(await page.evaluate(() => window.ACS.exportModel()), null, 'a new guest project starts empty');
}
async function generate(page, text, fields = {}) {
  for (const id of fieldIds) await page.locator('#' + id).fill(String(fields[id] ?? ''));
  await page.locator('#descText').fill(text);
  await page.locator('#genText').click();
}
async function card(page, mode) {
  await page.locator('#guestConfirm[data-mode="' + mode + '"]').waitFor({ state: 'visible', timeout: 10000 });
  return page.locator('#guestConfirm').evaluate(el => ({
    title: el.querySelector('h3').textContent,
    question: el.querySelector('#guestConfirmQuestion').hidden ? null : el.querySelector('#guestConfirmQuestion').textContent,
    rows: Object.fromEntries([...el.querySelectorAll('#guestConfirmRows li')].map(li => [li.dataset.key, { text: li.textContent, assumed: li.dataset.assumed === 'true' }])),
    direction: getComputedStyle(el).direction,
    draw: !el.querySelector('#guestConfirmDraw').hidden,
    unsupported: el.querySelector('#guestConfirmUnsupported').hidden ? [] : [...el.querySelectorAll('#guestConfirmUnsupported li')].map(li => li.textContent),
    choices: el.querySelector('#guestConfirmChoices').hidden ? [] : [...el.querySelectorAll('#guestConfirmChoices button')].map(b => b.dataset.choice + ':' + b.textContent),
  }));
}
async function onScreen(page, selector, viewport) {
  const box = await page.locator(selector).boundingBox();
  assert.ok(box && box.x >= -1 && box.y >= -1 && box.x + box.width <= viewport.width + 1 && box.y + box.height <= viewport.height + 1,
    selector + ' must be visible without scrolling: ' + JSON.stringify(box));
  return box;
}
const occupied = model => model.levels.filter(level => level.kind !== 'roof').length;

async function run(browser, width) {
  const viewport = { width, height: width === 393 ? 852 : 900 };
  const phone = width === 393;
  const ctx = await browser.newContext({ viewport, hasTouch: phone, isMobile: phone, deviceScaleFactor: 1, serviceWorkers: 'block' });
  ctx.setDefaultTimeout(45000);
  const denied = [], errors = [], report = { sourceSHA, viewport, checks: [] };
  await serve(ctx, denied);
  const page = await ctx.newPage();
  page.on('pageerror', error => errors.push(error.name + ': ' + error.message));
  try {
    await open(page);
    // 3. Separate building and land fields; 1. nothing prefilled.
    assert.equal(await page.locator('label[for="bldW"]').textContent(), 'عرض المبنى (م)');
    assert.equal(await page.locator('label[for="bldD"]').textContent(), 'عمق المبنى (م)');
    assert.equal(await page.locator('label[for="siteW"]').textContent(), 'عرض الأرض (م)');
    assert.equal(await page.locator('label[for="siteD"]').textContent(), 'عمق الأرض (م)');
    for (const id of fieldIds) assert.equal(await page.locator('#' + id).inputValue(), '', id + ' is not prefilled');

    // 1. Missing building size: a short Arabic question, nothing drawn.
    await generate(page, 'أبغى عمارة سكنية ٣ أدوار، شقتين بكل دور');
    const asked = await card(page, 'question');
    assert.match(asked.question, /كم عرض المبنى وعمقه بالمتر؟/);
    assert.equal(asked.draw, false, 'a question offers no «ارسم»');
    assert.equal(await page.evaluate(() => window.ACS.exportModel()), null, 'no 20 x 25 x 3 default was drawn');
    await page.locator('#guestConfirmEdit').click();
    assert.equal(await page.evaluate(() => document.activeElement?.id), 'bldW', '«عدّل» goes to the missing building width');
    report.checks.push({ question: asked.question });

    // 2. «فهمنا: …» before drawing, with the ground-floor rule and marked assumptions.
    const brief = 'عمارة سكنية ٢٤×٢٨ م، ثلاثة أدوار غير الأرضي، شقتين في كل دور';
    await generate(page, brief);
    let summary = await card(page, 'confirm');
    assert.equal(summary.title, 'فهمنا:');
    assert.equal(summary.direction, 'rtl');
    assert.match(summary.rows.levels.text, /4 أدوار: الأرضي و3 أدوار فوقه/);
    assert.match(summary.rows.levels.text, /أضفنا الأرضي/);
    assert.match(summary.rows.building.text, /عرض 24 م × عمق 28 م/);
    assert.equal(summary.rows.plot, undefined, 'no land row when the land was not given');
    assert.match(summary.rows.units.text, /شقتان في كل دور، 8 شقق/);
    assert.equal(summary.rows.entrance.assumed, true);
    assert.match(summary.rows.entrance.text, /افتراض/);
    assert.match(summary.rows.courtyard.text, /لا يوجد/);
    assert.equal(await page.evaluate(() => window.ACS.exportModel()), null, 'nothing is drawn before «ارسم»');
    const draw = await onScreen(page, '#guestConfirmDraw', viewport);
    assert.ok(draw.height >= 44 && draw.width >= 44, '«ارسم» is a 44px touch target');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal overflow');
    await page.screenshot({ path: path.join(out, width + '-confirm.png') });
    await page.locator('#guestConfirmEdit').click();
    assert.equal(await page.locator('#guestConfirm').isVisible(), false);
    assert.equal(await page.evaluate(() => window.ACS.exportModel()), null, '«عدّل» draws nothing');
    assert.equal(await page.evaluate(() => document.activeElement?.id), 'descText');
    await page.locator('#genText').click();
    await card(page, 'confirm');
    await page.locator('#guestConfirmDraw').click();
    await page.waitForFunction(() => window.ACS.exportModel()?.meta?.acs_apartment?.source === 'local_brief');
    let model = await page.evaluate(() => window.ACS.exportModel());
    assert.deepEqual(model.site, { w: 24, d: 28 });
    assert.equal(occupied(model), 4, '«ثلاثة أدوار غير الأرضي» draws four floors');
    assert.equal(await page.locator('#guestConfirm').isVisible(), false);
    report.checks.push({ drawn: model.site, floors: occupied(model) });

    // 3. Land 25 x 30 with building 20 x 25 in the fields draws 20 x 25.
    await open(page);
    await generate(page, 'أبغى عمارة سكنية على أرض، شقتين في كل دور', { bldW: 20, bldD: 25, siteW: 25, siteD: 30, nFloors: 3 });
    summary = await card(page, 'confirm');
    assert.match(summary.rows.plot.text, /25 × 30 م/);
    assert.match(summary.rows.building.text, /عرض 20 م × عمق 25 م/);
    assert.match(summary.rows.building.text, /من الحقول/);
    assert.match(summary.rows.levels.text, /3 أدوار: الأرضي ودوران فوقه/);
    await onScreen(page, '#guestConfirmDraw', viewport);
    await page.screenshot({ path: path.join(out, width + '-land-and-building.png') });
    await page.locator('#guestConfirmDraw').click();
    await page.waitForFunction(() => window.ACS.exportModel()?.meta?.acs_apartment?.source === 'local_brief');
    model = await page.evaluate(() => window.ACS.exportModel());
    assert.deepEqual(model.site, { w: 20, d: 25 }, 'the building, not the land, is drawn');
    assert.deepEqual(model.meta.acs_apartment.understanding.plot, { w: 25, d: 30, source: 'form' });

    // 4. Unsupported requests are listed in «فهمنا» before drawing, never dropped.
    await open(page);
    await generate(page, 'عمارة سكنية ٢٤×٢٨، ٣ أدوار، شقتين في كل دور، كل شقة فيها أربع غرف نوم ومجلس حريم، مع منور');
    summary = await card(page, 'confirm');
    assert.equal(summary.unsupported.length, 3, JSON.stringify(summary.unsupported));
    assert.match(summary.unsupported.join(' '), /طلبت 4، ويرسم المخطط المحلي 3/);
    assert.match(summary.unsupported.join(' '), /مجلس حريم/);
    assert.match(summary.unsupported.join(' '), /منور/);
    assert.match(await page.locator('#guestConfirmUnsupported p').textContent(), /غير مدعوم في المولّد المحلي بعد/);
    await onScreen(page, '#guestConfirmDraw', viewport);
    await page.screenshot({ path: path.join(out, width + '-unsupported.png') });
    await page.locator('#guestConfirmDraw').click();
    await page.waitForFunction(() => window.ACS.exportModel()?.meta?.acs_apartment?.source === 'local_brief');
    model = await page.evaluate(() => window.ACS.exportModel());
    assert.equal(model.meta.acs_apartment.understanding.not_drawn.length, 3, 'the model records what was not drawn');

    // Round 3: elevator, usable roof, separate entrances and unmapped words are listed; «مع الأرضي» is stated.
    await open(page);
    await generate(page, 'عمارة سكنية ٢٤×٢٨، ثلاث أدوار مع الأرضي، شقتين في كل دور، بدون مصعد، سطح مستخدم ومدخل منفصل لكل شقة، ومواقف أمامية');
    summary = await card(page, 'confirm');
    assert.equal(summary.unsupported.length, 4, JSON.stringify(summary.unsupported));
    for (const pattern of [/بدون مصعد/, /سطح مستخدم/, /مدخل منفصل لكل شقة/, /لم يُطبَّق: مواقف السيارات/])
      assert.match(summary.unsupported.join(' | '), pattern);
    assert.match(summary.rows.levels.text, /شاملة الأرضي كما ذكرت/);
    assert.equal(summary.rows.levels.assumed, false, 'the ground floor was stated, not assumed');
    await onScreen(page, '#guestConfirmDraw', viewport);
    await page.screenshot({ path: path.join(out, width + '-round3.png') });

    // Round 4 (Buraidah): roof rooms and structures are listed; a land size written in the text is shown.
    await open(page);
    await generate(page, 'عمارة سكنية في بريدة، عرض الأرض ٢٥ م وعمق الأرض ٣٠ م، والمبنى ٢٠×٢٥، ثلاث أدوار مع الأرضي، شقتين في كل دور، وغرفة غسيل على السطح وخزان علوي ومظلة');
    summary = await card(page, 'confirm');
    assert.match(summary.rows.plot.text, /25 × 30 م/);
    assert.match(summary.rows.plot.text, /من وصفك/);
    assert.match(summary.unsupported.join(' | '), /على السطح: غرفة غسيل، خزان علوي، مظلة/);
    await onScreen(page, '#guestConfirmDraw', viewport);
    await page.screenshot({ path: path.join(out, width + '-round4.png') });

    // 5. Text says 3 floors, the field says 4: the visitor picks; neither is preferred silently.
    await open(page);
    await generate(page, 'عمارة سكنية ٢٤×٢٨ م، ٣ أدوار، شقتين في كل دور', { nFloors: 4 });
    const conflict = await card(page, 'conflict');
    assert.deepEqual(conflict.choices, ['text:3 من الوصف', 'form:4 من الحقل']);
    assert.equal(conflict.draw, false, 'nothing can be drawn until a value is picked');
    assert.equal(await page.evaluate(() => window.ACS.exportModel()), null);
    await page.screenshot({ path: path.join(out, width + '-conflict.png') });
    await page.locator('#guestConfirmChoices button[data-choice="form"]').click();
    summary = await card(page, 'confirm');
    assert.match(summary.rows.levels.text, /4 أدوار: الأرضي و3 أدوار فوقه/);
    assert.match(summary.rows.levels.text, /اخترتَه حين اختلف الوصف عن الحقل/);
    await page.locator('#guestConfirmDraw').click();
    await page.waitForFunction(() => window.ACS.exportModel()?.meta?.acs_apartment?.source === 'local_brief');
    assert.equal(occupied(await page.evaluate(() => window.ACS.exportModel())), 4, 'the picked field value is drawn');
    await open(page);
    await generate(page, 'عمارة سكنية ٢٤×٢٨ م، ٣ أدوار، شقتين في كل دور', { nFloors: 4 });
    assert.equal((await card(page, 'conflict')).choices.length, 2, 'a new project asks again instead of reusing an old pick');
    await page.locator('#guestConfirmChoices button[data-choice="text"]').click();
    await card(page, 'confirm');
    await page.locator('#guestConfirmDraw').click();
    await page.waitForFunction(() => window.ACS.exportModel()?.meta?.acs_apartment?.source === 'local_brief');
    assert.equal(occupied(await page.evaluate(() => window.ACS.exportModel())), 3, 'the picked description value is drawn');

    // Land only: ask for the building size after setbacks.
    await open(page);
    await generate(page, 'عمارة سكنية على قطعة ٢٠×٣٠، ثلاث أدوار، شقتين في كل دور');
    const land = await card(page, 'question');
    assert.match(land.question, /ذكرت الأرض فقط/);
    assert.match(land.question, /بعد الارتدادات/);
    assert.equal(await page.evaluate(() => window.ACS.exportModel()), null);
    assert.deepEqual(errors, []);
    report.result = 'PASS';
  } catch (error) {
    report.result = 'FAIL';
    report.error = String(error.stack || error).slice(0, 2000);
    if (page) await page.screenshot({ path: path.join(out, width + '-failure.png') }).catch(() => {});
    throw error;
  } finally {
    report.denied = denied;
    report.errors = errors;
    fs.writeFileSync(path.join(out, width + '-report.json'), JSON.stringify(report, null, 2));
    await ctx.close();
  }
}

(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await PW.launch();
  try {
    for (const width of [393, 1440]) await run(browser, width);
  } finally {
    await browser.close();
  }
  console.log('PASS guest confirm card: asks for missing size, «فهمنا» before drawing, one-tap «ارسم», land separate from building (393 and 1440, RTL)');
})().catch(error => {
  console.error(error);
  process.exit(1);
});
