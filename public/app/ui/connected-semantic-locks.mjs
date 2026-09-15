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
const LOCKABLE_PROPERTIES = new Set([
  'kind', 'type',
  'x', 'y', 'z', 'position', 'rect',
  'w', 'd', 'h', 'width', 'depth', 'height',
  'dir', 'edge', 'axis', 'rotation', 'angle',
  'offset', 'pitch', 'count', 'rows', 'levels',
  'radius', 'diameter',
]);
const PROPERTY_SCOPE_PRESETS = {
  racks: [
    {id: 'position', label: 'الموضع فقط (X/Z)', properties: ['x', 'z']},
    {id: 'dimensions', label: 'الأبعاد فقط (W/D)', properties: ['w', 'd']},
  ],
  docks: [{id: 'position', label: 'الموضع فقط (الحافة/الإزاحة)', properties: ['edge', 'offset']}],
  lanes: [
    {id: 'position', label: 'الموضع فقط (X/Z)', properties: ['x', 'z']},
    {id: 'dimensions', label: 'الأبعاد فقط (W/D)', properties: ['w', 'd']},
  ],
  stations: [{id: 'position', label: 'الموضع فقط (X/Z)', properties: ['x', 'z']}],
  doors: [{id: 'position', label: 'الموضع فقط (الحافة/الإزاحة)', properties: ['edge', 'offset']}],
  windows: [{id: 'position', label: 'الموضع فقط (الحافة/الإزاحة)', properties: ['edge', 'offset']}],
  objects: [{id: 'position', label: 'الموضع فقط (X/Z)', properties: ['x', 'z']}],
  points: [{id: 'position', label: 'الموضع فقط (X/Z)', properties: ['x', 'z']}],
  furniture: [{id: 'position', label: 'الموضع فقط (X/Z)', properties: ['x', 'z']}],
};

function stable(value) {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= 120;
}

function normalizeProperties(raw) {
  if (raw == null) return null;
  if (!Array.isArray(raw) || raw.length < 1 || raw.length > 24) return undefined;
  const out = [];
  for (const value of raw) {
    if (typeof value !== 'string' || !LOCKABLE_PROPERTIES.has(value)) return undefined;
    out.push(value);
  }
  if (new Set(out).size !== out.length) return undefined;
  return out.sort();
}

function normalizeSelector(raw) {
  if (!raw || typeof raw !== 'object') return null;
  if (raw.kind === 'site') {
    if (raw.properties != null) return null;
    return {kind: 'site'};
  }
  if (raw.kind === 'room' && stable(raw.template) && stable(raw.room_id)) {
    if (raw.properties != null) return null;
    return {kind: 'room', template: raw.template.trim(), room_id: raw.room_id.trim()};
  }
  if (raw.kind === 'element' && stable(raw.template) && stable(raw.room_id)
      && COLLECTIONS.has(raw.collection) && stable(raw.element_id)) {
    const properties = normalizeProperties(raw.properties);
    if (raw.properties != null && !properties) return null;
    const selector = {
      kind: 'element', template: raw.template.trim(), room_id: raw.room_id.trim(),
      collection: raw.collection, element_id: raw.element_id.trim(),
    };
    if (properties) selector.properties = properties;
    return selector;
  }
  return null;
}

function elementIdentityKey(raw) {
  const selector = normalizeSelector(raw);
  if (selector?.kind !== 'element') return '';
  return JSON.stringify([
    'element', selector.template, selector.room_id, selector.collection, selector.element_id,
  ]);
}

export function selectorKey(raw) {
  const selector = normalizeSelector(raw);
  if (!selector) return '';
  // JSON tuples remain injective even when stable canonical ids contain delimiters.
  if (selector.kind === 'site') return JSON.stringify(['site']);
  if (selector.kind === 'room') return JSON.stringify(['room', selector.template, selector.room_id]);
  return JSON.stringify([
    'element', selector.template, selector.room_id, selector.collection, selector.element_id,
    selector.properties || null,
  ]);
}

export function lockScopesForTarget(raw) {
  const target = normalizeSelector(raw);
  if (target?.kind !== 'element') return [];
  const scopes = [{id: 'whole', label: 'العنصر كاملًا', properties: null}];
  for (const preset of PROPERTY_SCOPE_PRESETS[target.collection] || []) {
    const properties = normalizeProperties(preset.properties);
    if (properties) scopes.push({id: preset.id, label: preset.label, properties});
  }
  return scopes;
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
      const key = elementIdentityKey(selector);
      if (selector?.kind === 'element' && key) {
        delete selector.properties;
        found.set(key, selector);
      }
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
  const identity = elementIdentityKey(normalizedTarget);
  if (normalizedTarget?.kind !== 'element' || !key || !identity) {
    throw new TypeError('target must be a stable nested canonical element');
  }
  if (locked) {
    // One whole-element lock subsumes every property lock. Conversely, choosing a
    // selective lock while the element is wholly locked is an explicit narrowing
    // action, so remove the whole-element selector but preserve other partial scopes.
    for (const [existingKey, selector] of [...selectors.entries()]) {
      if (selector.kind !== 'element' || elementIdentityKey(selector) !== identity) continue;
      const targetWhole = !normalizedTarget.properties;
      const existingWhole = !selector.properties;
      if (targetWhole || existingWhole) selectors.delete(existingKey);
    }
    selectors.set(key, normalizedTarget);
  } else {
    selectors.delete(key);
  }
  return [...selectors.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([, value]) => value);
}

export function buildSemanticLockCommand({currentSelectors, target, locked, expectedHead}) {
  if (!stable(expectedHead)) throw new TypeError('expected head is required');
  const normalizedTarget = normalizeSelector(target);
  if (normalizedTarget?.kind !== 'element') throw new TypeError('target must be a nested canonical element');
  const selectors = toggleSemanticSelector(currentSelectors, normalizedTarget, Boolean(locked));
  const verb = locked ? 'lock' : 'unlock';
  const scope = normalizedTarget.properties ? ` properties ${normalizedTarget.properties.join(',')}` : ' whole element';
  return {
    action: 'replace_semantic_locks',
    expected_head: expectedHead.trim(),
    selectors,
    note: `${verb}${scope} ${normalizedTarget.collection}/${normalizedTarget.element_id} from connected design review`,
  };
}

let panel = null;
let select = null;
let scopeSelect = null;
let button = null;
let message = null;
let selectedState = null;
let selectedPacket = null;
let targets = [];
let scopeChoices = [];
let scopeTargetKey = '';
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

function locksForTarget(target) {
  const identity = elementIdentityKey(target);
  if (!identity) return [];
  return lockedSelectors().map(normalizeSelector).filter(row => row?.kind === 'element' && elementIdentityKey(row) === identity);
}

function targetHasAnyLock(target) {
  return locksForTarget(target).length > 0;
}

function sameProperties(a, b) {
  return JSON.stringify(normalizeProperties(a) || null) === JSON.stringify(normalizeProperties(b) || null);
}

function scopesForTarget(target) {
  const scopes = lockScopesForTarget(target);
  for (const lock of locksForTarget(target)) {
    if (!lock.properties || scopes.some(scope => sameProperties(scope.properties, lock.properties))) continue;
    scopes.push({
      id: `saved:${JSON.stringify(lock.properties)}`,
      label: `خصائص محفوظة (${lock.properties.join('/')})`,
      properties: [...lock.properties],
    });
  }
  return scopes;
}

function scopedTarget(target, scope) {
  const normalized = normalizeSelector(target);
  if (normalized?.kind !== 'element' || !scope) return null;
  const out = {...normalized};
  delete out.properties;
  if (scope.properties) out.properties = [...scope.properties];
  return normalizeSelector(out);
}

function scopeLocked(target, scope) {
  const scoped = scopedTarget(target, scope);
  const key = selectorKey(scoped);
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
  if (!panel || !select || !scopeSelect || !button || !message) return;
  const previousTarget = select.value;
  const previousScope = scopeSelect.value;
  select.replaceChildren();
  for (const target of targets) {
    const option = document.createElement('option');
    option.value = elementIdentityKey(target);
    option.textContent = `${targetHasAnyLock(target) ? '🔒 ' : ''}${labelFor(target)}`;
    select.append(option);
  }
  if (previousTarget && targets.some(row => elementIdentityKey(row) === previousTarget)) select.value = previousTarget;
  const target = targets.find(row => elementIdentityKey(row) === select.value) || targets[0] || null;
  if (target && !select.value) select.value = elementIdentityKey(target);

  const targetKey = target ? elementIdentityKey(target) : '';
  const changedTarget = targetKey !== scopeTargetKey;
  scopeChoices = target ? scopesForTarget(target) : [];
  scopeSelect.replaceChildren();
  for (const scope of scopeChoices) {
    const option = document.createElement('option');
    option.value = scope.id;
    option.textContent = `${scopeLocked(target, scope) ? '🔒 ' : ''}${scope.label}`;
    scopeSelect.append(option);
  }
  if (!changedTarget && previousScope && scopeChoices.some(scope => scope.id === previousScope)) {
    scopeSelect.value = previousScope;
  } else {
    const lockedScope = scopeChoices.find(scope => scopeLocked(target, scope));
    scopeSelect.value = lockedScope?.id || scopeChoices[0]?.id || '';
  }
  scopeTargetKey = targetKey;

  const head = selectedState?.head;
  const current = selectedState?.revision_id;
  const visibleRevision = document.getElementById('cwRevision')?.value;
  const onHead = stable(head) && head === current && current === visibleRevision;
  const scope = scopeChoices.find(row => row.id === scopeSelect.value) || scopeChoices[0] || null;
  const isLocked = target && scope ? scopeLocked(target, scope) : false;
  const wholeLocked = target ? locksForTarget(target).some(row => !row.properties) : false;
  button.textContent = isLocked ? 'إلغاء هذا القفل' : (wholeLocked && scope?.properties ? 'استبدال القفل الكامل بهذا النطاق' : 'حفظ هذا القفل');
  button.disabled = syncing || refreshRequested || nativeBusy() || !target || !scope || !onHead;
  select.disabled = syncing || !targets.length;
  scopeSelect.disabled = syncing || !scopeChoices.length;
  const count = lockedSelectors().length;
  if (!selectedPacket) message.textContent = 'لا توجد نسخة مخطط قابلة لقراءة الأقفال.';
  else if (!targets.length) message.textContent = 'لا توجد عناصر داخلية محددة يمكن قفلها في هذه النسخة.';
  else if (!onHead) message.textContent = `هذه نسخة تاريخية للقراءة فقط. الأقفال الدقيقة المحفوظة فيها: ${count}. استعدها كمسودة جديدة قبل التعديل.`;
  else if (wholeLocked && scope?.properties && !isLocked) message.textContent = 'العنصر مقفل بالكامل. حفظ النطاق المحدد سيستبدل القفل الكامل بقفل أضيق على الخصائص المختارة.';
  else message.textContent = `الأقفال الدقيقة المحفوظة في النسخة الحالية: ${count}. اختر قفل العنصر كاملًا أو نطاقًا محددًا؛ الخادم يفرض القفل على النموذج القانوني.`;
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
  help.textContent = 'اختر عنصرًا محفوظًا في المخطط ثم حدّد ما تريد تثبيته: العنصر كاملًا، موضعه، أو أبعاده عندما يدعم نوع العنصر ذلك.';
  const label = document.createElement('label');
  label.htmlFor = 'cwSemanticLockTarget';
  label.textContent = 'العنصر في المخطط';
  select = document.createElement('select');
  select.id = 'cwSemanticLockTarget';
  select.setAttribute('aria-label', 'العنصر المطلوب قفله');
  const scopeLabel = document.createElement('label');
  scopeLabel.htmlFor = 'cwSemanticLockScope';
  scopeLabel.textContent = 'نطاق القفل';
  scopeSelect = document.createElement('select');
  scopeSelect.id = 'cwSemanticLockScope';
  scopeSelect.setAttribute('aria-label', 'نطاق القفل المطلوب');
  button = document.createElement('button');
  button.id = 'cwSemanticLockToggle';
  button.type = 'button';
  button.textContent = 'حفظ هذا القفل';
  message = document.createElement('p');
  message.id = 'cwSemanticLockStatus';
  message.className = 'cw-muted';
  message.setAttribute('role', 'status');
  panel.append(title, help, label, select, scopeLabel, scopeSelect, button, message);
  review.append(panel);
  select.addEventListener('change', render);
  scopeSelect.addEventListener('change', render);
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
  const target = targets.find(row => elementIdentityKey(row) === select?.value);
  const scope = scopeChoices.find(row => row.id === scopeSelect?.value);
  const scoped = scopedTarget(target, scope);
  if (!target || !scope || !scoped || !selectedState || selectedState.revision_id !== selectedState.head
      || selectedState.revision_id !== document.getElementById('cwRevision')?.value) {
    throw new Error('الأقفال تُعدّل على أحدث مسودة فقط.');
  }
  syncing = true;
  render();
  try {
    const locked = !scopeLocked(target, scope);
    const command = buildSemanticLockCommand({
      currentSelectors: lockedSelectors(), target: scoped, locked,
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
