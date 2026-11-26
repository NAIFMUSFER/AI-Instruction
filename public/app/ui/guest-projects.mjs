/* «مشاريعي على هذا الجهاز»: every local guest project in this browser, with a
   link back to it, and the only way to move one to another device (download
   the JSON, then import it there). Read-only: databases are opened without a
   version, so listing never creates, upgrades or writes a project. */
const SCOPE = /^acs_guest_(project_v1|apartment_20x25_v1|draft_([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}))$/;
const when = new Intl.DateTimeFormat('ar-SA-u-nu-latn-ca-gregory', {dateStyle: 'medium', timeStyle: 'short'});

export function guestProjectHref(scope) {
  const m = SCOPE.exec(scope);
  if (!m) return null;
  if (m[1] === 'project_v1') return '/?guest=1';
  if (m[1] === 'apartment_20x25_v1') return '/?guest=1&example=apartment-20x25';
  return '/?guest=1&project=' + m[2];
}
function request(operation) {
  return new Promise((resolve, reject) => {
    operation.onsuccess = () => resolve(operation.result);
    operation.onerror = () => reject(operation.error);
  });
}
function describe(model) {
  const sample = model?.meta?.acs_apartment?.source === 'synthetic_sample';
  return {sample, name: sample ? 'العمارة التجريبية' : String(model?.meta?.name || 'مشروع محلي'), facts: facts(model)};
}
function facts(model) {
  const a = model?.meta?.acs_apartment;
  if (a) return `${a.width_m} × ${a.depth_m} م · ${a.occupied_levels} أدوار · ${a.units_total} شقق`;
  const levels = (model?.levels || []).filter(level => level.kind !== 'roof').length;
  const w = model?.site?.w, d = model?.site?.d;
  return [Number.isFinite(w) && Number.isFinite(d) ? `${w} × ${d} م` : null, levels ? `${levels} أدوار` : null].filter(Boolean).join(' · ');
}
async function readProject(scope, persistence) {
  let db;
  try {
    db = await request(indexedDB.open(scope));
    if (!db.objectStoreNames.contains('records')) return {scope, empty: true};
    const records = await request(db.transaction('records').objectStore('records').getAll());
    const pick = persistence.chooseRecovery(records);
    if (!pick.chosen) return {scope, empty: pick.code === 'NO_RECORDS', unreadable: pick.code !== 'NO_RECORDS'};
    const decoded = persistence.decode(pick.chosen);
    const model = decoded?.ok ? decoded.project?.model : null;
    if (!model) return {scope, unreadable: true};
    return {scope, savedAt: pick.chosen.saved_at_ms, ...describe(model)};
  } catch { return {scope, unreadable: true}; }
  finally { try { db?.close(); } catch {} }
}

export async function listGuestProjects(A, currentScope) {
  let names = null;
  try { names = typeof indexedDB.databases === 'function' ? (await indexedDB.databases()).map(row => row.name) : null; } catch {}
  const scopes = new Set((names || []).filter(name => SCOPE.test(name || '')));
  if (SCOPE.test(currentScope || '')) scopes.add(currentScope);
  const rows = await Promise.all([...scopes].map(scope => readProject(scope, A.persistence)));
  for (const row of rows) {
    row.current = row.scope === currentScope; row.href = guestProjectHref(row.scope);
    // The open project may not be saved yet: describe what is on screen, honestly marked.
    const live = row.current && !row.savedAt && !row.unreadable ? A.exportModel?.() : null;
    if (live) Object.assign(row, describe(live), {empty: false, unsaved: true});
  }
  rows.sort((a, b) => Number(b.current) - Number(a.current) || (b.savedAt || 0) - (a.savedAt || 0));
  return {complete: names !== null, rows};
}

export async function openGuestProjectsDialog(A, currentScope) {
  document.getElementById('guestProjectsDialog')?.remove();
  const previous = document.activeElement;
  const dialog = document.createElement('dialog');
  dialog.id = 'guestProjectsDialog'; dialog.dir = 'rtl';
  dialog.setAttribute('aria-labelledby', 'guestProjectsTitle');
  dialog.innerHTML = `
    <h2 id="guestProjectsTitle">مشاريعي على هذا الجهاز</h2>
    <p>هذه المشاريع محفوظة في هذا المتصفح على هذا الجهاز فقط، ولا تظهر وحدها على جهاز آخر.</p>
    <ul id="guestProjectsList" aria-busy="true"><li>جارٍ قراءة المشاريع…</li></ul>
    <section aria-labelledby="guestMoveTitle">
      <h3 id="guestMoveTitle">نقل مشروع إلى جهاز آخر</h3>
      <ol>
        <li>افتح المشروع هنا، ثم اضغط «تنزيل هذا المشروع». يُحفظ ملف JSON على جهازك.</li>
        <li>أرسل الملف لنفسك، بالبريد أو واتساب مثلًا.</li>
        <li>على الجهاز الآخر افتح الموقع، ثم «•••» ← «مشاريعي على هذا الجهاز» ← «استيراد مشروع من ملف» واختر الملف.</li>
      </ol>
      <div class="guest-projects-actions">
        <button id="guestProjectsDownload" type="button">تنزيل هذا المشروع (JSON)</button>
        <button id="guestProjectsImport" type="button">استيراد مشروع من ملف</button>
      </div>
      <p id="guestProjectsImportNote">الاستيراد يستبدل المشروع المفتوح الآن؛ نزّله أولًا إن أردت الاحتفاظ به.</p>
    </section>
    <button id="guestProjectsClose" type="button">إغلاق</button>`;
  document.body.append(dialog);
  const $ = id => dialog.querySelector('#' + id);
  $('guestProjectsClose').addEventListener('click', () => dialog.close());
  $('guestProjectsDownload').addEventListener('click', () => document.getElementById('bJson')?.click());
  $('guestProjectsImport').addEventListener('click', () => { dialog.close(); document.getElementById('impFile')?.click(); });
  dialog.addEventListener('close', () => { dialog.remove(); if (previous?.isConnected) previous.focus(); }, {once: true});
  dialog.showModal();
  $('guestProjectsClose').focus();
  const {complete, rows} = await listGuestProjects(A, currentScope);
  if (!dialog.isConnected) return dialog;
  const list = $('guestProjectsList');
  list.replaceChildren(...rows.map(row => {
    const item = document.createElement('li');
    const title = document.createElement('strong');
    title.textContent = row.unreadable ? 'مشروع تعذّرت قراءته' : row.empty ? 'مسودة فارغة' : row.name;
    item.append(title);
    const detail = document.createElement('span');
    detail.textContent = [row.facts, row.savedAt ? 'آخر حفظ: ' + when.format(row.savedAt) : row.unsaved ? 'لم يُحفظ بعد' : null].filter(Boolean).join(' · ');
    if (detail.textContent) item.append(detail);
    if (row.current) {
      const mark = document.createElement('em'); mark.textContent = 'المشروع المفتوح الآن'; item.append(mark);
      item.setAttribute('aria-current', 'true');
    } else if (row.href) {
      const link = document.createElement('a'); link.href = row.href; link.textContent = 'فتح';
      link.setAttribute('aria-label', 'فتح ' + title.textContent);
      item.append(link);
    }
    return item;
  }));
  if (!complete) {
    const note = document.createElement('li');
    note.textContent = 'هذا المتصفح لا يسمح بعرض كل المشاريع؛ يظهر المشروع المفتوح فقط.';
    list.append(note);
  }
  list.setAttribute('aria-busy', 'false');
  return dialog;
}
