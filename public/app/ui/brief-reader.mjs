// Step 01 smart reading: one paid, confirmed provider read of the brief, shown in
// an editable Arabic «فهمنا» card. Nothing reaches the step-01 fields until the
// owner confirms the card. When the read fails or is unavailable, the free
// local reader («قراءة المتطلبات من الوصف») runs instead with a clear message.
// All program text is shown with textContent/value only.
import {SCHEMA,SIDE_AR,POSITION_AR,ROLE_AR,OUTDOOR_AR,STAIR_AR,OUTPUT_AR,OUTPUT_READY,programChecks,checkProgram,programFields,levelSummary,programKey,clone} from '../core/brief-reader.mjs';
import {normalizeNumberText} from '../core/brief-program.mjs';

const POLL_MS = 3000;
// Owner-facing reasons when the service answers without Arabic text.
export const READ_FAILURES = {
  BRIEF_READ_INVALID_JSON:'لم يرجع الذكاء الاصطناعي برنامجًا مقروءًا بالصيغة المطلوبة.',
  BRIEF_PROGRAM_INVALID:'رجع برنامج فيه قيم خارج الحدود المدعومة، فلم نعرضه.',
  BRIEF_PROGRAM_INCONSISTENT:'رجع برنامج بأبعاد متعارضة، فلم نعرضه. راجع أرقام وصفك.',
  ACS_PROVIDER_BUDGET_EXHAUSTED:'احتاجت القراءة أكثر من الطلب الواحد المسموح، فتوقفت دون تكلفة إضافية.',
  ACS_UPSTREAM_NOT_CONFIGURED:'خدمة الذكاء الاصطناعي غير متاحة الآن.',
  GENERATION_IN_PROGRESS:'توجد مهمة جارية لهذا المشروع؛ انتظر انتهاءها ثم أعد القراءة.',
  PROVIDER_OUTCOME_UNKNOWN:'توقف الخادم أثناء القراءة.',
};

export function createBriefReader(root, {api, confirmPaid, briefEditor, storageKey, jobKey, localDraftKeys = () => [], onError = () => {}}) {
  const $ = id => root.querySelector('#' + id);
  const el = (tag, text, parent, cls) => {const n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; if (parent) parent.append(n); return n;};
  const store = {
    get(key) {try {return JSON.parse(localStorage.getItem(key) || 'null');} catch (e) {return null;}},
    set(key, value) {try {localStorage.setItem(key, JSON.stringify(value));} catch (e) {}},
    drop(key) {try {localStorage.removeItem(key);} catch (e) {}},
  };
  const smart = el('button', 'قراءة ذكية للوصف بالذكاء الاصطناعي', null, 'cw-smart-read'); smart.type = 'button'; smart.id = 'cwSmartRead';
  const note = el('p', 'طلب واحد مدفوع، يستغرق عادةً من دقيقة إلى ثلاث دقائق. تظهر النتيجة في بطاقة تراجعها وتعدّلها، ولا تُعبّأ الحقول قبل تأكيدك.', null, 'cw-muted cw-smart-note'); note.id = 'cwSmartReadNote';
  const progress = el('p', null, null, 'cw-program-status'); progress.id = 'cwProgramStatus';
  progress.setAttribute('role', 'status'); progress.setAttribute('aria-live', 'polite'); progress.hidden = true;
  $('cwReadBrief').after(smart, note, progress);
  const card = el('section', null, null, 'cw-brief-review cw-program'); card.id = 'cwProgramCard'; card.hidden = true;
  card.setAttribute('aria-labelledby', 'cwProgramTitle');
  ($('cwBriefReview') || progress).after(card);
  // Card edits are not step-01 field edits: they stay in the card until confirmed.
  for (const kind of ['input', 'change']) card.addEventListener(kind, e => e.stopPropagation());

  let program = null, confirmed = false, confirmedKey = null, source = null, readBrief = null, jobId = null, startedAt = 0, timer = null, ticker = null;
  const value = id => $(id)?.value ?? '';
  const number = text => {const t = normalizeNumberText(text); return t === '' ? null : Number(t);};
  const save = () => {if (program) store.set(storageKey(), {program, confirmed, key:confirmedKey, source, brief:readBrief});};
  const say = (text, bad = false) => {progress.hidden = !text; progress.textContent = text || ''; progress.classList.toggle('bad', bad);};
  const sync = () => {const residential = value('cwType') === 'residential'; smart.hidden = note.hidden = !residential; card.hidden = !program || !residential;};

  // ── editable fields inside the card ──────────────────────────────────────
  function field(parent, label, current, onValue, {kind = 'decimal', id} = {}) {
    const wrap = el('label', null, parent, 'cw-program-field');
    el('span', label, wrap);
    const input = el('input', null, wrap); input.type = 'text'; input.inputMode = kind; input.autocomplete = 'off';
    if (id) input.id = id;
    input.value = current == null ? '' : String(current);
    input.addEventListener('input', () => {
      const n = number(input.value);
      onValue(input.value.trim() === '' ? null : Number.isFinite(n) ? n : NaN);
      refreshChecks();
    });
    return input;
  }
  function choice(parent, label, current, options, onValue, id) {
    const wrap = el('label', null, parent, 'cw-program-field');
    el('span', label, wrap);
    const select = el('select', null, wrap); if (id) select.id = id;
    for (const [key, text] of options) {const o = el('option', text, select); o.value = key;}
    select.value = current ?? '';
    select.addEventListener('change', () => {onValue(select.value || null); refreshChecks();});
    return select;
  }
  function tag(parent, text, cls = 'cw-badge') {return el('span', text, parent, cls);}

  function renderSite(box) {
    const site = program.site;
    const group = el('div', null, box, 'cw-program-group'); el('h4', 'الأرض والشارع', group);
    const grid = el('div', null, group, 'cw-program-grid');
    field(grid, 'عرض الأرض (م)', site.width_m, v => {site.width_m = v;}, {id:'cwProgramWidth'});
    field(grid, 'عمق الأرض (م)', site.depth_m, v => {site.depth_m = v;}, {id:'cwProgramDepth'});
    const sides = [['', 'غير محددة'], ...Object.entries(SIDE_AR).map(([k, v]) => [k, v.replace('ال', '')])];
    choice(grid, 'جهة الشارع', site.street_sides[0] || '', sides, v => {site.street_sides = [v, site.street_sides[1]].filter(Boolean);}, 'cwProgramStreet');
    choice(grid, 'شارع ثانٍ', site.street_sides[1] || '', [['', 'لا يوجد'], ...sides.slice(1)], v => {site.street_sides = [site.street_sides[0], v].filter(Boolean);});
    if (site.area_m2 != null) {
      const ok = site.width_m != null && site.depth_m != null && Math.abs(site.width_m * site.depth_m - site.area_m2) <= Math.max(0.5, site.area_m2 * 0.01);
      el('p', 'مساحة الأرض في الوصف ' + site.area_m2 + ' م²' + (ok ? ' — تطابق العرض × العمق.' : '.'), group, 'cw-muted');
    }
    el('h4', 'الارتدادات حول المبنى', group);
    const setbacks = el('div', null, group, 'cw-program-grid cw-program-setbacks');
    for (const s of ['N', 'E', 'S', 'W']) {
      const cell = el('div', null, setbacks);
      const input = field(cell, 'ارتداد ' + SIDE_AR[s] + ' (م)', site.setbacks_m[s], v => {site.setbacks_m[s] = v; mark();}, {id:'cwProgramSetback' + s});
      const badge = tag(cell, '');
      const mark = () => {const given = site.setbacks_m[s] != null; badge.textContent = given ? 'من وصفك' : 'افتراض: يحسبه ACS من الاشتراطات'; badge.dataset.assumed = String(!given);};
      mark();
    }
    el('h4', 'كتلة المبنى', group);
    const block = el('div', null, group, 'cw-program-grid');
    field(block, 'عرض المبنى (م)', site.footprint.width_m, v => {site.footprint.width_m = v;}, {id:'cwProgramBldWidth'});
    field(block, 'عمق المبنى (م)', site.footprint.depth_m, v => {site.footprint.depth_m = v;}, {id:'cwProgramBldDepth'});
    if (site.footprint.position) el('p', 'موضعه في الأرض: ' + POSITION_AR[site.footprint.position] + '. يتحدد الموضع في المخطط من الارتدادات.', group, 'cw-muted');
  }

  function renderRoom(list, unit, room, index) {
    const row = el('li', null, list, 'cw-program-room');
    const head = el('div', null, row, 'cw-program-room-head');
    const name = el('input', null, head); name.type = 'text'; name.value = room.name; name.maxLength = 40; name.setAttribute('aria-label', 'اسم الفراغ');
    name.addEventListener('input', () => {room.name = name.value; refreshChecks();});
    const role = el('select', null, head); role.setAttribute('aria-label', 'استخدام الفراغ');
    for (const [key, text] of Object.entries(ROLE_AR)) {const o = el('option', text, role); o.value = key;}
    role.value = room.role; role.addEventListener('change', () => {room.role = role.value; refreshChecks(); refreshSummaries();});
    const size = el('div', null, row, 'cw-program-room-size');
    field(size, 'العدد', room.count, v => {room.count = v; refreshSummaries();}, {kind:'numeric'});
    field(size, 'العرض (م)', room.width_m, v => {room.width_m = v;});
    field(size, 'العمق (م)', room.depth_m, v => {room.depth_m = v;});
    const remove = el('button', '✕', size); remove.type = 'button'; remove.setAttribute('aria-label', 'حذف ' + room.name); remove.title = 'حذف الفراغ';
    remove.addEventListener('click', () => {unit.rooms.splice(index, 1); render();});
    const extra = [room.approx ? 'مقاس تقريبي' : null, room.ensuite ? 'بحمام خاص' : null, room.note].filter(Boolean);
    if (extra.length) el('small', extra.join(' · '), row);
  }

  function renderLevels(box) {
    const group = el('div', null, box, 'cw-program-group'); el('h4', 'الأدوار وبرامجها', group);
    program.levels.forEach((level, i) => {
      const details = el('details', null, group, 'cw-program-level'); details.open = i === 0;
      const summary = el('summary', null, details); summary.dataset.level = String(i);
      el('strong', level.name, summary); el('span', ' · ' + levelSummary(level), summary);
      if (level.note) el('p', level.note, details, 'cw-muted');
      level.units.forEach((unit, u) => {
        if (level.units.length > 1 || unit.name) el('h5', unit.name || 'الشقة ' + (u + 1), details);
        if (unit.bedrooms != null || unit.bathrooms != null)
          el('p', 'المذكور في الوصف: ' + [unit.bedrooms != null ? unit.bedrooms + ' غرف نوم' : null, unit.bathrooms != null ? unit.bathrooms + ' حمامات' : null].filter(Boolean).join('، ') + '.', details, 'cw-muted');
        const list = el('ul', null, details, 'cw-program-rooms');
        unit.rooms.forEach((room, r) => renderRoom(list, unit, room, r));
        const add = el('button', '+ إضافة فراغ', details); add.type = 'button';
        add.addEventListener('click', () => {unit.rooms.push({role:'other', name:'فراغ جديد', count:1, width_m:null, depth_m:null, approx:false, ensuite:false, note:null}); render(); details.open = true;});
      });
      if (!level.units.length) el('p', 'لا شقق في هذا الدور.', details, 'cw-muted');
    });
  }

  function renderRest(box) {
    const core = program.core, parking = program.parking;
    const group = el('div', null, box, 'cw-program-group'); el('h4', 'الدرج والمواقف', group);
    const grid = el('div', null, group, 'cw-program-grid');
    choice(grid, 'الدرج', core.stair || '', [['', 'غير محدد'], ...Object.entries(STAIR_AR)], v => {core.stair = v;});
    for (const [key, text] of [['elevator', 'مصعد'], ['landing_entries', 'أبواب الشقق من بسطة مشتركة']]) {
      const wrap = el('label', null, grid, 'cw-check cw-program-check');
      const box = el('input', null, wrap); box.type = 'checkbox'; box.checked = core[key] === true;
      box.addEventListener('change', () => {core[key] = box.checked;}); wrap.append(' ' + text);
    }
    field(grid, 'عدد المواقف', parking.count, v => {parking.count = v;}, {kind:'numeric', id:'cwProgramParking'});
    if (parking.stall_width_m != null)
      el('p', 'مقاس الموقف في وصفك ' + parking.stall_width_m + ' × ' + parking.stall_depth_m + ' م' + (parking.note ? ' (' + parking.note + ')' : '') + '.', group, 'cw-muted');
    if (program.outdoor.length) {
      const outdoor = el('div', null, box, 'cw-program-group'); el('h4', 'الأحواش والعناصر الخارجية', outdoor);
      const list = el('ul', null, outdoor, 'cw-program-list');
      for (const item of program.outdoor) {
        const li = el('li', null, list);
        el('strong', item.name, li);
        el('span', ' · ' + [OUTDOOR_AR[item.kind], item.width_m != null ? item.width_m + ' × ' + item.depth_m + ' م' : null, item.location ? POSITION_AR[item.location] : null].filter(Boolean).join(' · '), li);
        tag(li, 'سيُرسم لاحقًا', 'cw-badge cw-later');
        if (item.note) el('small', item.note, li);
      }
    }
    if (program.facade.materials.length || program.facade.notes.length) {
      const facade = el('div', null, box, 'cw-program-group'); el('h4', 'الواجهة', facade);
      el('p', [...program.facade.materials, ...program.facade.notes].join('، ') + '.', facade);
    }
    const wanted = Object.entries(program.outputs).filter(([, on]) => on);
    if (wanted.length) {
      const outputs = el('div', null, box, 'cw-program-group'); el('h4', 'المخرجات المطلوبة', outputs);
      const list = el('ul', null, outputs, 'cw-program-list');
      for (const [key] of wanted) {const li = el('li', OUTPUT_AR[key] + ' — ', list); tag(li, OUTPUT_READY.has(key) ? 'متاح' : 'غير متاح بعد', OUTPUT_READY.has(key) ? 'cw-badge' : 'cw-badge cw-later');}
    }
  }

  let checksBox = null, summaries = [];
  function refreshChecks() {
    if (!checksBox) return;
    checksBox.replaceChildren();
    let notes;
    try {notes = programChecks(program);} catch (e) {notes = [];}
    // The server's note that it fitted odd values of the read (READ_ADJUSTED) stays until the card is confirmed.
    const adjusted = (Array.isArray(program?.checks) ? program.checks : []).find(c => c?.code === 'READ_ADJUSTED' && typeof c.message === 'string');
    if (adjusted && !confirmed) notes = [adjusted, ...notes];
    if (!notes.length) return;
    el('h4', 'تحقق من الأرقام', checksBox);
    const list = el('ul', null, checksBox); for (const n of notes) el('li', n.message, list);
  }
  function refreshSummaries() {
    for (const summary of root.querySelectorAll('#cwProgramCard summary[data-level]')) {
      const level = program.levels[Number(summary.dataset.level)];
      if (level) summary.lastChild.textContent = ' · ' + levelSummary(level);
    }
  }

  function render() {
    card.replaceChildren(); sync();
    if (!program) return;
    const head = el('div', null, card, 'cw-program-head');
    el('h3', 'فهمنا من وصفك:', head).id = 'cwProgramTitle';
    tag(head, confirmed ? (source === 'cloud' ? 'مؤكد ومحفوظ مع النسخة' : 'مؤكد وعُبّئت الحقول') : 'قراءة بالذكاء الاصطناعي — راجعها');
    el('p', confirmed ? 'هذا البرنامج المؤكد يُرسل مع التوليد. عدّله ثم أكّده من جديد إن تغيّر شيء.'
      : (source === 'device' ? 'قراءة محفوظة من جهاز آخر. ' : '') + 'راجع القيم وعدّلها. لا تتغير حقول المتطلبات قبل أن تضغط «تأكيد البرنامج وتعبئة الحقول».', card, 'cw-muted');
    if (readBrief && readBrief !== value('cwBrief').trim())
      el('p', 'تغيّر وصفك بعد هذه القراءة. أعد القراءة الذكية إن أردت أن تعكس البطاقة التعديل.', card, 'cw-program-warning');
    renderSite(card); renderLevels(card); renderRest(card);
    checksBox = el('div', null, card, 'cw-program-checks'); checksBox.id = 'cwProgramChecks'; refreshChecks();
    const later = [...(program.cannot_do || []).map(c => c.message), ...program.other_requests.map(t => 'طلب يُرسل وصفًا: ' + t)];
    if (later.length) {
      const box = el('div', null, card, 'cw-program-unsupported'); box.id = 'cwProgramUnsupported';
      el('h4', 'ما لا ينفذه ACS بعد:', box);
      const list = el('ul', null, box); for (const text of later) el('li', text, list);
    }
    const actions = el('div', null, card, 'cw-actions');
    const go = el('button', confirmed ? 'تأكيد التعديلات وتعبئة الحقول' : 'تأكيد البرنامج وتعبئة الحقول', actions, 'cw-primary'); go.type = 'button'; go.id = 'cwProgramConfirm';
    const hide = el('button', 'إلغاء البطاقة', actions); hide.type = 'button'; hide.id = 'cwProgramDismiss';
    go.addEventListener('click', confirmCard);
    hide.addEventListener('click', () => {program = null; confirmed = false; store.drop(storageKey()); render(); say('أُلغيت بطاقة البرنامج؛ لن تُرسل مع التوليد. حقولك كما هي.');});
  }

  // ── confirmation: fill the existing step-01 fields ────────────────────────
  function setField(id, next, kind = 'input') {
    const node = $(id);
    if (!node || next == null || next === '') return false;
    const text = String(next);
    if (node.value !== text) {node.value = text; node.dispatchEvent(new Event(kind, {bubbles:true}));}
    return true;
  }
  function fillFields(f, {requirements = true} = {}) {
    const filled = [];
    if (requirements) {
      for (const [id, v, label] of [['cwWidth', f.width, 'عرض الموقع'], ['cwDepth', f.depth, 'عمق الموقع'], ['cwLevels', f.levels, 'عدد الأدوار'],
        ['cwBldWidth', f.buildingWidth, 'عرض المبنى'], ['cwBldDepth', f.buildingDepth, 'عمق المبنى']]) if (setField(id, v)) filled.push(label);
    }
    if (f.units && setField('cwUnits', f.units.units)) {setField('cwUnitsScope', f.units.scope, 'change'); filled.push('عدد الشقق');}
    if (f.villa) {
      const villa = [['cwVillaBedrooms', f.villa.bedrooms, 'input'], ['cwVillaBathrooms', f.villa.bathrooms, 'input'],
        ['cwVillaMaster', f.villa.master, 'change'], ['cwVillaMaid', f.villa.maid, 'change'], ['cwVillaDriver', f.villa.driver, 'change']]
        .filter(([id, v, kind]) => setField(id, v, kind));
      if (villa.length) filled.push('برنامج الفيلا');
    }
    if (setField('cwBedrooms', f.bedrooms)) filled.push('غرف النوم');
    if (setField('cwBathrooms', f.bathrooms)) filled.push('دورات المياه');
    if (f.guests) setField('cwGuests', f.guests, 'change');
    if (setField('cwCity', f.city)) filled.push('المدينة');
    if (f.street && setField('cwStreet', f.street, 'change')) filled.push('جهة الشارع');
    if (f.street2) setField('cwPlotStreet2', f.street2, 'change');
    setField('cwPlotStreetWidth', f.streetWidth);
    const setbacks = ['N', 'E', 'S', 'W'].filter(s => setField('cwPlotSetback' + s, f.setbacks[s]));
    if (setbacks.length) filled.push('الارتدادات (' + setbacks.map(s => SIDE_AR[s]).join('، ') + ')');
    if (f.parking.placement) setField('cwPlotParking', f.parking.placement, 'change');
    if (setField('cwPlotParkingCount', f.parking.count)) filled.push('عدد المواقف');
    const landing = $('cwPlotLanding');
    if (f.landing && landing && !landing.checked) {landing.checked = true; landing.dispatchEvent(new Event('change', {bubbles:true}));}
    if (requirements && f.rows.length) {briefEditor.useValues(f.rows); filled.push('إجمالي ' + f.rows.map(r => r.role === 'bedroom' ? 'غرف النوم' : 'الحمامات').join(' و'));}
    return filled;
  }
  function confirmCard() {
    try {
      const finite = v => v == null || Number.isFinite(v);
      const bad = JSON.stringify(program, (k, v) => typeof v === 'number' && !finite(v) ? '\u0000' : v).includes('\\u0000');
      if (bad) throw new Error('في البطاقة رقم غير صالح. اكتب الأرقام بالأرقام العربية أو اللاتينية.');
      checkProgram(program);
      program.checks = programChecks(program);
      if (value('cwType') !== 'residential') setField('cwType', 'residential', 'change');
      const f = programFields(program), filled = fillFields(f);
      confirmed = true; confirmedKey = programKey(program); save(); render();
      say('عبّأنا من البرنامج المؤكد: ' + (filled.join('، ') || 'لا حقول جديدة') + '. ' + f.notes.join(' ') + ' راجع المتطلبات ثم أكّدها للمتابعة.');
    } catch (e) {say(e.message, true);}
  }

  // ── the paid read ─────────────────────────────────────────────────────────
  const elapsed = () => {const s = Math.max(0, Math.floor((Date.now() - startedAt) / 1000)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');};
  function reading(on) {
    smart.disabled = on; smart.setAttribute('aria-busy', String(on));
    clearInterval(ticker); ticker = on ? setInterval(() => {if (jobId) say('جارٍ قراءة الوصف بالذكاء الاصطناعي… ' + elapsed() + ' — يمكنك متابعة الكتابة أو مغادرة الصفحة؛ نتابع الطلب نفسه.');}, 1000) : null;
  }
  function finishJob() {clearTimeout(timer); timer = null; jobId = null; store.drop(jobKey()); reading(false);}
  function fallback(code, message) {
    finishJob();
    const reason = typeof message === 'string' && message.length <= 300 && /[؀-ۿ]/.test(message) ? message : READ_FAILURES[code] || 'تعذّرت القراءة الذكية الآن.';
    $('cwReadBrief').click();   // the free local reader
    say(reason + ' عرضنا ما قرأه القارئ المحلي المجاني من وصفك؛ راجع القيم واستخدمها، أو أعد القراءة الذكية لاحقًا.', true);
  }
  function handle(job) {
    // An answer about no job or another job: keep following this one, never resend.
    if (!job || job.id !== jobId) {if (jobId) {clearTimeout(timer); timer = setTimeout(poll, POLL_MS);} return;}
    if (job.state === 'SUCCEEDED') {
      const took = elapsed(); finishJob();
      if (!job.program || job.program.schema !== SCHEMA) return fallback('BRIEF_PROGRAM_INVALID');
      program = clone(job.program); confirmed = false; confirmedKey = null; source = 'ai'; readBrief = value('cwBrief').trim();
      save(); render();
      say('اكتملت القراءة الذكية في ' + took + '. راجع البطاقة ثم أكّدها لتعبئة الحقول.');
      card.scrollIntoView?.({block:'start'});
      return;
    }
    if (['FAILED', 'INTERRUPTED', 'CANCELLED'].includes(job.state)) return fallback(job.error_code, job.error_message);
    timer = setTimeout(poll, POLL_MS);
  }
  async function poll() {
    if (!jobId) return;
    try {handle((await api({action:'job', job_id:jobId})).job);}
    catch (e) {
      if (e?.status === 404) return fallback(e.code);
      say('انقطع الاتصال أثناء متابعة القراءة. نعيد المحاولة على الطلب نفسه…', true);
      clearTimeout(timer); timer = setTimeout(poll, POLL_MS * 3);
    }
  }
  async function start() {
    const brief = value('cwBrief').trim();
    if (jobId) return poll();
    if (value('cwType') !== 'residential') throw new Error('القراءة الذكية متاحة حاليًا للمشاريع السكنية. للمستودعات استخدم «قراءة المتطلبات من الوصف».');
    if (brief.length < 20) throw new Error('اكتب وصفًا أطول (20 حرفًا على الأقل) قبل القراءة الذكية.');
    if (!await confirmPaid('سنرسل وصفك إلى الذكاء الاصطناعي في طلب واحد ليستخرج برنامج المشروع: الأرض والارتدادات والأدوار والغرف والمواقف والعناصر الخارجية. يستغرق عادةً من دقيقة إلى ثلاث دقائق، ويستهلك طلبًا واحدًا من رصيد الذكاء الاصطناعي. لن تتغير حقولك قبل أن تراجع البطاقة وتؤكدها.',
      'ابدأ القراءة', 'قراءة الوصف بالذكاء الاصطناعي؟')) {say('لم تبدأ القراءة الذكية، ولم يُستهلك أي رصيد.'); return;}
    jobId = crypto.randomUUID(); startedAt = Date.now(); store.set(jobKey(), {jobId, startedAt});
    reading(true); say('جارٍ إرسال الوصف…');
    try {handle((await api({action:'read_brief', job_id:jobId, brief, confirmed:true, max_provider_calls:1})).job);}
    catch (e) {
      // A refusal started nothing; an unknown outcome is followed, never resent.
      if (e?.status > 0) return fallback(e.code, e.message);
      say('لم يصل تأكيد الطلب. نتابع الطلب نفسه دون إرسال طلب جديد…', true);
      timer = setTimeout(poll, POLL_MS);
    }
  }
  smart.addEventListener('click', () => {start().catch(e => {reading(false); say(e.message, true);});});
  $('cwType').addEventListener('change', sync);
  $('cwBrief').addEventListener('input', () => {if (program && !card.hidden && readBrief) {const warn = card.querySelector('.cw-program-warning'); if (!warn && readBrief !== value('cwBrief').trim()) render();}});

  // ── restore: this device, then the revision, then another device's read ──
  const hasLocal = () => localDraftKeys().some(key => {try {return localStorage.getItem(key) !== null;} catch (e) {return false;}});
  function restoreRevision(data) {
    // Older revisions carry no program: their plot inputs and flat counts still come back.
    const plot = data?.plot_input, f = {setbacks:{}, parking:{}, rows:[], notes:[]};
    if (plot) {
      [f.street, f.street2] = plot.streets || [];
      f.setbacks = plot.setbacks_m || {}; f.streetWidth = plot.street_width_m;
      f.parking = {placement:plot.parking?.placement, count:plot.parking?.count}; f.landing = plot.landing_entries === true;
    }
    const req = metric => (data?.requirements || []).find(r => r?.metric === metric && !r.role)?.expected;
    const perUnit = role => (data?.requirements || []).find(r => r?.metric === 'room_count_per_unit' && r.role === role)?.expected;
    if (req('unit_count_per_level') != null) f.units = {units:req('unit_count_per_level'), scope:'per_level'};
    else if (req('unit_count') != null) f.units = {units:req('unit_count'), scope:'total'};
    f.bedrooms = perUnit('bedroom'); f.bathrooms = perUnit('bathroom');
    const city = /\nالمدينة: ([^؛\n]{1,60})؛ جهة الشارع:/.exec(data?.brief || '')?.[1];
    if (city && city !== 'غير محددة') f.city = city;
    fillFields(f, {requirements:false});
  }
  async function latestRead() {
    let data;
    try {data = await api({action:'brief_read_latest'});} catch (e) {return;}
    const read = data?.read;
    if (!read?.program || program || jobId) return;
    const current = value('cwBrief').trim();
    if (current && current !== read.brief.trim()) return;
    if (!current) {$('cwBrief').value = read.brief; $('cwBrief').dispatchEvent(new Event('input', {bubbles:true}));}
    program = clone(read.program); confirmed = false; source = 'device'; readBrief = read.brief.trim(); save(); render();
  }

  return {
    fill(data) {
      clearTimeout(timer); reading(false); jobId = null; program = null; confirmed = false; confirmedKey = null; source = null; readBrief = null; say('');
      const local = hasLocal(), saved = store.get(storageKey());
      if (saved?.program?.schema === SCHEMA) {
        ({program, confirmed, key:confirmedKey, source, brief:readBrief} = saved); confirmed = !!confirmed;
      } else if (data?.brief_program?.schema === SCHEMA) {
        program = clone(data.brief_program); confirmed = true; confirmedKey = programKey(program); source = 'cloud'; readBrief = null;
        if (!local) fillFields(programFields(program), {requirements:false});
        save();
      } else if (data && !local && value('cwType') === 'residential') restoreRevision(data);
      render();
      const pending = store.get(jobKey());
      if (typeof pending?.jobId === 'string' && pending.jobId) {
        jobId = pending.jobId; startedAt = Number(pending.startedAt) || Date.now(); reading(true); poll();
      } else if (!program && !data?.head && !local) latestRead();
    },
    // {program} for a generation from the description; {} when no card is confirmed.
    command() {
      if (!program || !confirmed || value('cwType') !== 'residential') return {};
      const fixed = JSON.parse(confirmedKey || '[]'), now = ['cwWidth', 'cwDepth', 'cwLevels', 'cwBldWidth', 'cwBldDepth'].map(id => number(value(id)));
      if (fixed.some((v, i) => v != null && v !== now[i])) throw new Error('تغيّرت أبعاد الأرض أو المبنى أو عدد الأدوار بعد تأكيد بطاقة البرنامج. أكّد البطاقة من جديد أو ألغها قبل التوليد.');
      const {checks, cannot_do, ...sent} = program;
      return {program:sent};
    },
    current() {return program ? {program:clone(program), confirmed, source} : null;},
  };
}
