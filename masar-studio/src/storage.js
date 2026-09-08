import { assertHistory, current } from '../shared/model.js';
let dbPromise;
function database() { if (!('indexedDB' in globalThis))
    return Promise.reject(Error('الحفظ المحلي غير متاح في هذا المتصفح. نزّل ملف المشروع لحفظه.')); if (!dbPromise)
    dbPromise = new Promise((resolve, reject) => { let req; try {
        req = indexedDB.open('masar-studio', 1);
    }
    catch {
        reject(Error('الحفظ المحلي غير متاح في وضع المعاينة الحالي. نزّل JSON للاحتفاظ بمشروعك.'));
        return;
    } req.onupgradeneeded = () => req.result.createObjectStore('projects', { keyPath: 'id' }); req.onsuccess = () => resolve(req.result); req.onerror = () => reject(Error('تعذّر فتح مخزن المشاريع المحلي.')); }); return dbPromise; }
export async function saveLocal(history, cloudVersions = {}) { assertHistory(history); const db = await database(); const row = { id: history.projectId, title: current(history).title, updated: new Date().toISOString(), history, cloudVersions }; return new Promise((resolve, reject) => { const tx = db.transaction('projects', 'readwrite'); tx.objectStore('projects').put(row); tx.oncomplete = () => resolve(row); tx.onerror = () => reject(Error('تعذّر الحفظ المحلي. قد تكون مساحة الجهاز ممتلئة؛ نزّل ملف المشروع.')); tx.onabort = () => reject(Error('لم يكتمل الحفظ المحلي. نزّل ملف المشروع.')); }); }
export async function listLocal() { const db = await database(); return new Promise((resolve, reject) => { const req = db.transaction('projects').objectStore('projects').getAll(); req.onsuccess = () => resolve(req.result.sort((a, b) => b.updated.localeCompare(a.updated))); req.onerror = () => reject(Error('تعذّر قراءة المشاريع.')); }); }
export async function loadLocal(id) { const db = await database(); return new Promise((resolve, reject) => { const req = db.transaction('projects').objectStore('projects').get(id); req.onsuccess = () => { try {
    if (!req.result)
        throw Error('المشروع غير موجود.');
    resolve(assertHistory(req.result.history));
}
catch (e) {
    reject(e);
} }; req.onerror = () => reject(Error('تعذّر استعادة المشروع.')); }); }
export async function loadLocalVersions(id) {
 const db=await database();return new Promise((resolve,reject)=>{
  const req=db.transaction('projects').objectStore('projects').get(id);
  req.onsuccess=()=>resolve(Object.fromEntries(Object.entries(req.result?.cloudVersions||{}).filter(([key,v])=>key.endsWith(':'+id)&&Number.isSafeInteger(v)&&v>=0)));
  req.onerror=()=>reject(Error('تعذرت قراءة بيانات مزامنة المشروع المحلي.'));
 });
}
export async function deleteLocal(id) { const db = await database(); return new Promise((resolve, reject) => { const tx = db.transaction('projects', 'readwrite'); tx.objectStore('projects').delete(id); tx.oncomplete = () => resolve(); tx.onerror = () => reject(Error('تعذّر حذف المشروع.')); }); }
export class Api {
    constructor() { this.csrf = null; this.user = null; this.available = false; this.aiConfigured = false; this.registration = false; this.persistenceClass='unavailable'; }
    async request(url, { method = 'GET', body, timeout = 35000 } = {}) { if (location.protocol === 'file:')
        throw Error('هذه نسخة محلية مستقلة؛ الحسابات والمشاركة تحتاج تشغيل الخادم.'); const res = await fetch(url, { method, credentials: 'same-origin', headers: { ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}), ...(this.csrf ? { 'X-CSRF-Token': this.csrf } : {}) }, body: body !== undefined ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(timeout) }); let data; try {
        data = await res.json();
    }
    catch {
        throw Error('الخادم لم يرجع ردًا صالحًا.');
    } if (!res.ok) {
        const error = Error(data.error || 'تعذّرت العملية.');
        error.status = res.status;
        throw error;
    } return data; }
    async init() { if (location.protocol === 'file:' || globalThis.MASAR_STANDALONE)
        return; try {
        // Startup must never make the local-first studio wait on a long network timeout.
        // Cloud/account calls retain their normal 35 s budget; only the boot probe is bounded.
        const health = await this.request('/api/health', { timeout: 5000 });
        this.available = health.ok;
        this.aiConfigured = health.aiConfigured;
        this.registration = health.registration;
        this.persistenceClass = health.persistenceClass || 'operator-managed';
        const me = await this.request('/api/auth/me', { timeout: 5000 });
        this.user = me.user;
        this.csrf = me.csrf;
    }
    catch {
        this.available = false;
    } }
    async authenticate(type, body) { const result = await this.request('/api/auth/' + type, { method: 'POST', body }); this.user = result.user; this.csrf = result.csrf; return result; }
    async logout() { await this.request('/api/auth/logout', { method: 'POST', body: {} }); this.user = null; this.csrf = null; }
}