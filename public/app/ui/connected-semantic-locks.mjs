import {parseReviewFile} from '../core/plan-review-packet.mjs';

const COLLECTIONS = new Set([
  'racks', 'docks', 'lanes', 'stations', 'doors', 'windows',
  'objects', 'points', 'furniture',
]);
const COLLECTION_LABELS = {
  racks: 'رف/مجموعة رفوف', docks: 'رصيف/باب تحميل', lanes: 'ممر',
  stations: 'محطة تشغيل', doors: 'باب', windows: 'نافذة',
  objects: 'عنصر/نواة', points: 'نقطة', furniture: 'عنصر أثاث',
};

function stable(value) {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= 120;
}

function normalizeSelector(raw) {
  if (!raw || typeof raw !== 'object') return null;
  if (raw.kind === 'site') return {kind: 'site'};
  if (raw.kind === 'room' && stable(raw.template) && stable(raw.room_id)) {
    return {kind: 'room', template: raw.template.trim(), room_id: raw.room_id.trim()};
  }
  if (raw.kind === 'element' && stable(raw.template) && stable(raw.room_id)
      && COLLECTIONS.has(raw.collection) && stable(raw.element_id)) {
    return {
      kind: 'element', template: raw.template.trim(), room_id: raw.room_id.trim(),
      collection: raw.collection, element_id: raw.element_id.trim(),
    };
  }
  return null;
}

export function selectorKey(raw) {
  const selector = normalizeSelector(raw);
  if (!selector) return '';
  // A JSON tuple is injective for these normalized string components. Do not use a
  // delimiter-joined key: stable canonical ids may themselves contain delimiters.
  if (selector.kind === 'site') return JSON.stringify(['site']);
  if (selector.kind === 'room') return JSON.stringify(['room', selector.template, selector.room_id]);
  return JSON.stringify([
    'element', selector.template, selector.room_id, selector.collection, selector.element_id,
  ]);
}

export function collectSemanticLockTargets(packet) {
  const found = new Map();
  const projections = Array.isArray(packet?.projections) ? packet.projections : [];
  for (const projection of projections) {
    const sourceMap = Array.isArray(projection?.source_map) ? projection.source_map : [];
    for (const row of sourceMap) {
      const source = row?.source;
      if (source?.kind !== 'element') continue;
      const selector = normalizeSelector(source);
      const key = selectorKey(selector);
      if (selector?.kind === 'element' && key) found.set(key, selector);
    }
  }
  return [...found.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([, value]) => value);
}

function normalizedSelectorSet(selectors) {
  if (!Array.isArray(selectors)) throw new TypeError('semantic selectors must be an array');
  const found = new Map();
  for (const raw of selectors) {
    const selector = normalizeSelector(raw);
    const key = selectorKey(selector);
    if (!selector || !key) throw new TypeError('semantic selector is malformed');
    found.set(key, selector);
  }
  return found;
}

export function toggleSemanticSelector(currentSelectors, target, locked) {
  const selectors = normalizedSelectorSet(currentSelectors);
  const normalizedTarget = normalizeSelector(target);
  const key = selectorKey(normalizedTarget);
  if (normalizedTarget?.kind !== 'element' || !key) throw new TypeError('target must be a stable nested canonical element');
  if (locked) selectors.set(key, normalizedTarget);
  else selectors.delete(key);
  return [...selectors.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([, value]) => value);
}

export function buildSemanticLockCommand({currentSelectors, target, locked, expectedHead}) {
  if (!stable(expectedHead)) throw new TypeError('expected head is required');
  const normalizedTarget = normalizeSelector(target);
  if (normalizedTarget?.kind !== 'element') throw new TypeError('target must be a nested canonical element');
  const selectors = toggleSemanticSelector(currentSelectors, normalizedTarget, Boolean(locked));
  const verb = locked ? 'lock' : 'unlock';
  return {
    action: 'replace_semantic_locks',
    expected_head: expectedHead.trim(),
    selectors,
    note: `${verb} ${normalizedTarget.collection}/${normalizedTarget.element_id} from connected design review`,
  };
}

let panel = null;
let select = null;
let button = null;
let message = null;
let selectedState = null;
let selectedPacket = null;
let targets = [];
let syncing = false;
let refreshRequested = false;
let observer = null;
let scheduled = null;

function projectId() {
  const value = globalThis.window?.ACS?.projectId;
  return stable(value) ? value.trim() : null;
}

async function apiState() {
  const pid = projectId();
  const auth = globalThis.window?.ACS_AUTH;
  if (!pid || !auth?.freshSession || !auth?.acsFetchJSON) return null;
  const session = await auth.freshSession();
  if (!session?.access_token) return null;
  const visibleRevision = globalThis.document?.getElementById('cwRevision')?.value || null;
  const body = {action: 'state', ...(stable(visibleRevision) ? {revision_id: visibleRevision} : {})};
  return auth.acsFetchJSON(`/v1/projects/${pid}/workspace`, body, session.access_token, 20000);
}

async function submit(command) {
  const pid = projectId();
  const auth = globalThis.window?.ACS_AUTH;
  if (!pid || !auth?.freshSession || !auth?.acsFetchJSON) throw new Error('خدمة المشروع غير متاحة.');
  const session = await auth.freshSession();
  if (!session?.access_token) throw new Error('انتهت جلسة الدخول.');
  return auth.acsFetchJSON(`/v1/projects/${pid}/plan/commands`, command, session.access_token, 20000);
}

function lockedSelectors() {
  return Array.isArray(selectedPacket?.locks?.semantic) ? selectedPacket.locks.semantic : [];
}

function targetLocked(target) {
  const key = selectorKey(target);
  return Boolean(key) && lockedSelectors().some(row => selectorKey(row) === key);
}

function nativeBusy() {
  const root = globalThis.document?.getElementById('designWorkspace');
  const recover = globalThis.document?.getElementById('cwRecoverJob');
  return root?.getAttribute('aria-busy') === 'true' || Boolean(recover && !recover.hidden);
}

function labelFor(selector) {
  const label = COLLECTION_LABELS[selector.collection] || selector.collection;
  return `${label} · ${selector.element_id} · ${selector.room_id}`;
}

function render() {
  if (!panel || !select || !button || !message) return;
  const previous = select.value;
  select.replaceChildren();
  for (const target of targets) {
    const option = document.createElement('option');
    option.value = selectorKey(target);
    option.textContent = `${targetLocked(target) ? '🔒 ' : ''}${labelFor(target)}`;
    select.append(option);
  }
  if (previous && targets.some(row => selectorKey(row) === previous)) select.value = previous;
  const head = selectedState?.head;
  const current = selectedState?.revision_id;
  const visibleRevision = document.getElementById('cwRevision')?.value;
  const onHead = stable(head) && head === current && current === visibleRevision;
  const target = targets.find(row => selectorKey(row) === select.value) || targets[0] || null;
  if (target && !select.value) select.value = selectorKey(target);
  const isLocked = target ? targetLocked(target) : false;
  button.textContent = isLocked ? 'إلغاء قفل العنصر' : 'قفل العنصر';
  button.disabled = syncing || refreshRequested || nativeBusy() || !target || !onHead;
  select.disabled = syncing || !targets.length;
  const count = lockedSelectors().length;
  if (!selectedPacket) message.textContent = 'لا توجد نسخة مخطط قابلة لقراءة الأقفال.';
  else if (!targets.length) message.textContent = 'لا توجد عناصر داخلية محددة يمكن قفلها في هذه النسخة.';
  else if (!onHead) message.textContent = `هذه نسخة تاريخية للقراءة فقط. الأقفال الدقيقة المحفوظة فيها: ${count}. استعدها كمسودة جديدة قبل التعديل.`;
  else message.textContent = `الأقفال الدقيقة المحفوظة في النسخة الحالية: ${count}. القفل يحمي العنصر وهندسته وسياق موضعه عبر الخادم.`;
}

function ensurePanel() {
  if (panel?.isConnected) return true;
  const review = globalThis.document?.getElementById('cwReviewContent');
  if (!review) return false;
  panel = document.createElement('section');
  panel.id = 'cwSemanticLocks';
  panel.className = 'cw-card';
  const title = document.createElement('h2');
  title.textContent = 'أقفال العناصر الدقيقة';
  const help = document.createElement('p');
  help.className = 'cw-muted';
  help.textContent = 'اختر رفًا أو رصيفًا أو ممرًا أو عنصرًا محفوظًا في المخطط لحمايته من التغيير في المقترحات التالية.';
  const label = document.createElement('label');
  label.htmlFor = 'cwSemanticLockTarget';
  label.textContent = 'العنصر في المخطط';
  select = document.createElement('select');
  select.id = 'cwSemanticLockTarget';
  select.setAttribute('aria-label', 'العنصر المطلوب قفله');
  button = document.createElement('button');
  button.id = 'cwSemanticLockToggle';
  button.type = 'button';
  button.textContent = 'قفل العنصر';
  message = document.createElement('p');
  message.id = 'cwSemanticLockStatus';
  message.className = 'cw-muted';
  message.setAttribute('role', 'status');
  panel.append(title, help, label, select, button, message);
  review.append(panel);
  select.addEventListener('change', render);
  button.addEventListener('click', () => { toggleSelected().catch(showError); });
  render();
  return true;
}

function showError(error) {
  if (!message) return;
  message.textContent = error?.message || 'تعذّر تحديث القفل.';
  message.setAttribute('role', 'alert');
}

async function sync() {
  if (syncing) { refreshRequested = true; return; }
  if (!ensurePanel()) return;
  if (nativeBusy()) { render(); return; }
  refreshRequested = false;
  syncing = true;
  render();
  try {
    const state = await apiState();
    selectedState = state;
    selectedPacket = state?.review_packet ? await parseReviewFile(JSON.stringify(state.review_packet)) : null;
    targets = collectSemanticLockTargets(selectedPacket);
    if (message) message.setAttribute('role', 'status');
  } catch (error) {
    selectedState = null;
    selectedPacket = null;
    targets = [];
    showError(error);
  } finally {
    syncing = false;
    render();
    if (refreshRequested) scheduleSync(0);
  }
}

function scheduleSync(delay = 0) {
  if (scheduled) clearTimeout(scheduled);
  scheduled = setTimeout(() => { scheduled = null; sync().catch(showError); }, delay);
}

async function toggleSelected() {
  if (syncing) return;
  if (nativeBusy() || refreshRequested) throw new Error('انتظر اكتمال عملية المشروع الحالية قبل تغيير القفل.');
  const target = targets.find(row => selectorKey(row) === select?.value);
  if (!target || !selectedState || selectedState.revision_id !== selectedState.head
      || selectedState.revision_id !== document.getElementById('cwRevision')?.value) {
    throw new Error('الأقفال تُعدّل على أحدث مسودة فقط.');
  }
  syncing = true;
  render();
  try {
    const locked = !targetLocked(target);
    const command = buildSemanticLockCommand({
      currentSelectors: lockedSelectors(), target, locked,
      expectedHead: selectedState.head,
    });
    await submit(command);
    message.textContent = locked ? 'تم حفظ القفل كنسخة جديدة. جارٍ تحديث المشروع…' : 'تم حفظ إلغاء القفل كنسخة جديدة. جارٍ تحديث المشروع…';
    message.setAttribute('role', 'status');
    globalThis.document?.getElementById('cwReload')?.click();
  } finally {
    syncing = false;
    scheduleSync(250);
  }
}

function install() {
  if (typeof document === 'undefined') return;
  scheduleSync(0);
  document.addEventListener('acs:authenticated', () => scheduleSync(0));
  document.addEventListener('change', event => {
    if (['cwRevision', 'cwLevel'].includes(event.target?.id)) scheduleSync(50);
  });
  document.addEventListener('click', event => {
    if (event.target?.id === 'cwReload') scheduleSync(150);
  });
  if (typeof MutationObserver !== 'undefined' && document.body) {
    // The native workspace renders new revisions without a DOM change event.
    // Ignore mutations inside this panel so rendering cannot trigger a fetch loop.
    observer = new MutationObserver(records => {
      if (!panel?.isConnected && document.getElementById('cwReviewContent')) scheduleSync(0);
      else if (semanticWorkspaceChanged(records)) {
        render();
        if (!nativeBusy()) scheduleSync(0);
      }
    });
    observer.observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['aria-busy']});
  }
}

export function semanticWorkspaceChanged(records) {
  return records.some(record => (record.type === 'childList' && record.target?.id === 'cwRevision')
    || (record.type === 'attributes' && record.attributeName === 'aria-busy' && record.target?.id === 'designWorkspace'));
}

install();
