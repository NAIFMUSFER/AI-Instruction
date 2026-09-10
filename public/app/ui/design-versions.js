/* ============================================================================
   ACS Design Versions
   -------------------
   Engineer-facing local version snapshots. A generated design can be saved,
   restored, renamed, deleted or marked as the approved local version without
   replacing earlier snapshots. This is intentionally local-only for now;
   cloud persistence is a separate authenticated backend phase.
   ========================================================================= */

const ACS_VERSIONS_DB = 'acs_design_versions';
const ACS_VERSIONS_DB_VERSION = 1;
const ACS_VERSIONS_STORE = 'versions';
const ACS_VERSIONS_MAX = 20;

function acsVersionsClone(v) {
  return v == null ? v : JSON.parse(JSON.stringify(v));
}

function acsVersionsHash(text) {
  let h = 2166136261;
  const s = String(text || '');
  for (let i = 0; i < s.length; i += 1) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0).toString(16).padStart(8, '0');
}

function acsVersionsOpen() {
  return new Promise((resolve, reject) => {
    const rq = indexedDB.open(ACS_VERSIONS_DB, ACS_VERSIONS_DB_VERSION);
    rq.onupgradeneeded = () => {
      const db = rq.result;
      if (!db.objectStoreNames.contains(ACS_VERSIONS_STORE)) {
        const store = db.createObjectStore(ACS_VERSIONS_STORE, { keyPath: 'id' });
        store.createIndex('saved_at_ms', 'saved_at_ms');
        store.createIndex('approved', 'approved');
      }
    };
    rq.onsuccess = () => resolve(rq.result);
    rq.onerror = () => reject(rq.error || new Error('versions database unavailable'));
  });
}

function acsVersionsTx(mode, work) {
  return acsVersionsOpen().then((db) => new Promise((resolve, reject) => {
    const tx = db.transaction([ACS_VERSIONS_STORE], mode);
    const store = tx.objectStore(ACS_VERSIONS_STORE);
    let out;
    tx.oncomplete = () => { db.close(); resolve(out); };
    tx.onerror = () => { const e = tx.error; db.close(); reject(e); };
    tx.onabort = () => { const e = tx.error; db.close(); reject(e); };
    try { out = work(store, tx); } catch (err) { try { tx.abort(); } catch (_e) {} reject(err); }
  }));
}

function acsVersionsAll() {
  return new Promise((resolve, reject) => {
    acsVersionsOpen().then((db) => {
      const tx = db.transaction([ACS_VERSIONS_STORE], 'readonly');
      const rq = tx.objectStore(ACS_VERSIONS_STORE).getAll();
      rq.onsuccess = () => {
        const rows = (rq.result || []).sort((a, b) => b.saved_at_ms - a.saved_at_ms);
        db.close(); resolve(rows);
      };
      rq.onerror = () => { const e = rq.error; db.close(); reject(e); };
    }, reject);
  });
}

function acsVersionsConfig() {
  const get = (id) => (document.getElementById(id) || {}).value;
  return {
    description: String(get('descText') || '').trim(),
    site_w: Number(get('siteW')) || null,
    site_d: Number(get('siteD')) || null,
    floors: Number(get('nFloors')) || null,
    building_type: String(get('bType') || 'auto'),
  };
}

async function acsVersionsPrune() {
  const rows = await acsVersionsAll();
  if (rows.length <= ACS_VERSIONS_MAX) return 0;
  const removable = rows.filter((r) => !r.approved).slice(ACS_VERSIONS_MAX);
  if (!removable.length) return 0;
  await acsVersionsTx('readwrite', (store) => {
    removable.forEach((r) => store.delete(r.id));
  });
  return removable.length;
}

async function acsVersionsSave(label) {
  const A = window.ACS || {};
  const model = A.exportModel && A.exportModel();
  if (!model) throw new Error('لا يوجد تصميم حالي لحفظه.');
  const rows = await acsVersionsAll();
  const now = Date.now();
  const config = acsVersionsConfig();
  let audit = null;
  try {
    if (A.residentialQuality && typeof A.residentialQuality.audit === 'function') {
      audit = A.residentialQuality.audit(model);
    }
  } catch (_e) { audit = null; }
  const payload = JSON.stringify(model);
  const item = {
    id: 'ver_' + now + '_' + acsVersionsHash(payload).slice(0, 6),
    label: String(label || ('نسخة ' + (rows.length + 1))).trim().slice(0, 80),
    saved_at_ms: now,
    approved: false,
    model_hash: acsVersionsHash(payload),
    request: config,
    audit,
    model: acsVersionsClone(model),
    storage: 'INDEXEDDB_LOCAL_TO_THIS_DEVICE',
  };
  await acsVersionsTx('readwrite', (store) => { store.put(item); });
  await acsVersionsPrune();
  await acsVersionsRefresh();
  return acsVersionsClone(item);
}

async function acsVersionsRestore(id) {
  const rows = await acsVersionsAll();
  const item = rows.find((r) => r.id === id);
  if (!item) throw new Error('النسخة المطلوبة غير موجودة.');
  const A = window.ACS || {};
  if (!A.setModel) throw new Error('عارض النموذج غير جاهز.');
  A.setModel(acsVersionsClone(item.model));
  const cfg = item.request || {};
  const set = (id2, value) => {
    const el = document.getElementById(id2);
    if (el && value !== undefined && value !== null) el.value = value;
  };
  set('descText', cfg.description); set('siteW', cfg.site_w); set('siteD', cfg.site_d);
  set('nFloors', cfg.floors); set('bType', cfg.building_type);
  return acsVersionsClone(item);
}

async function acsVersionsRename(id, label) {
  const rows = await acsVersionsAll();
  const item = rows.find((r) => r.id === id);
  if (!item) return false;
  item.label = String(label || '').trim().slice(0, 80) || item.label;
  await acsVersionsTx('readwrite', (store) => { store.put(item); });
  await acsVersionsRefresh();
  return true;
}

async function acsVersionsDelete(id) {
  await acsVersionsTx('readwrite', (store) => { store.delete(id); });
  await acsVersionsRefresh();
  return true;
}

async function acsVersionsApprove(id) {
  const rows = await acsVersionsAll();
  const target = rows.find((r) => r.id === id);
  if (!target) return { ok: false, reason: 'NOT_FOUND' };
  const audit = target.audit || {};
  if (audit.block_approval) return { ok: false, reason: 'QUALITY_GATE', audit };
  rows.forEach((r) => { r.approved = r.id === id; });
  await acsVersionsTx('readwrite', (store) => { rows.forEach((r) => store.put(r)); });
  await acsVersionsRefresh();
  return { ok: true, version: acsVersionsClone(target) };
}

function acsVersionsLoadCss() {
  if (document.querySelector('link[data-acs-design-versions]')) return;
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = new URL('./design-versions.css', import.meta.url).href;
  link.dataset.acsDesignVersions = '1';
  document.head.appendChild(link);
}

function acsVersionsEl(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text != null) el.textContent = text;
  return el;
}

let ACS_VERSIONS_MODAL = null;
let ACS_VERSIONS_COUNT = null;

async function acsVersionsRefresh() {
  const rows = await acsVersionsAll();
  if (ACS_VERSIONS_COUNT) ACS_VERSIONS_COUNT.textContent = String(rows.length);
  if (!ACS_VERSIONS_MODAL) return rows;
  const list = ACS_VERSIONS_MODAL.querySelector('[data-acs-versions-list]');
  if (!list) return rows;
  list.textContent = '';
  if (!rows.length) {
    list.appendChild(acsVersionsEl('p', 'acs-ver-empty', 'لا توجد نسخ محفوظة بعد. احفظ التصميم الذي يعجبك ثم جرّب توليدًا جديدًا.'));
    return rows;
  }
  rows.forEach((item) => {
    const card = acsVersionsEl('article', 'acs-ver-card');
    if (item.approved) card.classList.add('approved');
    const head = acsVersionsEl('div', 'acs-ver-card-head');
    head.appendChild(acsVersionsEl('strong', '', (item.approved ? '⭐ ' : '') + item.label));
    const when = new Date(item.saved_at_ms).toLocaleString('ar-SA');
    head.appendChild(acsVersionsEl('span', 'acs-ver-date', when));
    card.appendChild(head);
    const cfg = item.request || {};
    const meta = acsVersionsEl('div', 'acs-ver-meta');
    meta.textContent = [cfg.building_type, cfg.site_w && cfg.site_d ? (cfg.site_w + '×' + cfg.site_d + 'م') : '', cfg.floors ? (cfg.floors + ' أدوار') : '', 'hash ' + String(item.model_hash || '').slice(0, 8)].filter(Boolean).join(' · ');
    card.appendChild(meta);
    if (item.audit) {
      const q = acsVersionsEl('div', 'acs-ver-quality');
      q.textContent = 'جودة سكنية: ' + item.audit.score + '/100' + (item.audit.block_approval ? ' · يحتاج مراجعة قبل الاعتماد' : ' · صالح للاعتماد المحلي');
      card.appendChild(q);
    }
    const actions = acsVersionsEl('div', 'acs-ver-card-actions');
    const restore = acsVersionsEl('button', 'ghost', 'فتح');
    restore.type = 'button'; restore.onclick = async () => { await acsVersionsRestore(item.id); acsVersionsClose(); };
    const approve = acsVersionsEl('button', 'ghost', item.approved ? 'معتمد ✓' : 'اعتماد ⭐');
    approve.type = 'button'; approve.disabled = !!item.approved;
    approve.onclick = async () => {
      const r = await acsVersionsApprove(item.id);
      if (!r.ok && r.reason === 'QUALITY_GATE') window.alert('لا يمكن اعتماد هذه النسخة بعد: فحص الجودة السكنية رصد مشاكل حرجة. يمكن حفظها ومراجعتها، لكن الاعتماد محجوب.');
    };
    const rename = acsVersionsEl('button', 'ghost', 'إعادة تسمية');
    rename.type = 'button'; rename.onclick = async () => { const v = window.prompt('اسم النسخة', item.label); if (v) await acsVersionsRename(item.id, v); };
    const del = acsVersionsEl('button', 'ghost danger', 'حذف');
    del.type = 'button'; del.onclick = async () => { if (window.confirm('حذف هذه النسخة المحفوظة من هذا الجهاز؟')) await acsVersionsDelete(item.id); };
    actions.append(restore, approve, rename, del); card.appendChild(actions); list.appendChild(card);
  });
  return rows;
}

function acsVersionsClose() {
  if (ACS_VERSIONS_MODAL) ACS_VERSIONS_MODAL.classList.remove('on');
}

async function acsVersionsOpenModal() {
  if (ACS_VERSIONS_MODAL) {
    ACS_VERSIONS_MODAL.classList.add('on');
    await acsVersionsRefresh();
  }
}

function acsVersionsInstallUi() {
  acsVersionsLoadCss();
  const gen = document.getElementById('genLLM');
  if (!gen || document.querySelector('[data-acs-version-actions]')) return false;
  const row = acsVersionsEl('div', 'acs-ver-actions');
  row.dataset.acsVersionActions = '1';
  const save = acsVersionsEl('button', 'acs-ver-save', '💾 حفظ التصميم');
  save.type = 'button';
  save.onclick = async () => {
    try {
      const item = await acsVersionsSave();
      const status = document.getElementById('srvPill');
      if (status) status.textContent = '✓ حُفظت ' + item.label + ' على هذا الجهاز — يمكنك الآن توليد نسخة جديدة بدون فقدها.';
    } catch (err) { window.alert(String(err && err.message || err)); }
  };
  const browse = acsVersionsEl('button', 'ghost acs-ver-browse', 'الإصدارات ');
  browse.type = 'button';
  ACS_VERSIONS_COUNT = acsVersionsEl('span', 'acs-ver-count', '0');
  browse.appendChild(ACS_VERSIONS_COUNT); browse.onclick = acsVersionsOpenModal;
  row.append(save, browse); gen.insertAdjacentElement('afterend', row);

  const modal = acsVersionsEl('section', 'acs-ver-modal');
  modal.setAttribute('role', 'dialog'); modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-label', 'إصدارات التصميم المحفوظة');
  const sheet = acsVersionsEl('div', 'acs-ver-sheet');
  const top = acsVersionsEl('div', 'acs-ver-top');
  top.appendChild(acsVersionsEl('h2', '', 'إصدارات التصميم'));
  const close = acsVersionsEl('button', 'ghost', 'إغلاق ✕'); close.type = 'button'; close.onclick = acsVersionsClose;
  top.appendChild(close); sheet.appendChild(top);
  sheet.appendChild(acsVersionsEl('p', 'acs-ver-note', 'كل حفظ ينشئ نسخة مستقلة على هذا الجهاز. التوليد الجديد لا يستبدل النسخ المحفوظة. النسخة المعتمدة لا تُستبدل تلقائيًا.'));
  const list = acsVersionsEl('div', 'acs-ver-list'); list.dataset.acsVersionsList = '1'; sheet.appendChild(list);
  modal.appendChild(sheet); document.body.appendChild(modal); ACS_VERSIONS_MODAL = modal;
  modal.addEventListener('click', (ev) => { if (ev.target === modal) acsVersionsClose(); });
  acsVersionsRefresh().catch(() => {});
  return true;
}

function acsVersionsWireGenerationHint() {
  const gen = document.getElementById('genLLM');
  if (!gen || typeof gen.onclick !== 'function' || gen.__acsVersionHint) return;
  const original = gen.onclick;
  gen.onclick = function versionAwareGeneration(ev) {
    const result = original.call(this, ev);
    Promise.resolve(result).then(() => {
      const A = window.ACS || {};
      if (A.exportModel && A.exportModel()) {
        const save = document.querySelector('.acs-ver-save');
        if (save) save.classList.add('ready');
      }
    }, () => {});
    return result;
  };
  gen.__acsVersionHint = true;
}

function acsVersionsInit() {
  if (typeof window === 'undefined' || typeof document === 'undefined' || !('indexedDB' in window)) return false;
  window.ACS = window.ACS || {};
  window.ACS.versions = {
    save: acsVersionsSave,
    list: acsVersionsAll,
    restore: acsVersionsRestore,
    rename: acsVersionsRename,
    remove: acsVersionsDelete,
    approve: acsVersionsApprove,
    open: acsVersionsOpenModal,
    storage_kind: 'INDEXEDDB_LOCAL_TO_THIS_DEVICE',
    is_cloud: false,
    max_versions: ACS_VERSIONS_MAX,
  };
  acsVersionsInstallUi();
  acsVersionsWireGenerationHint();
  return true;
}

acsVersionsInit();
