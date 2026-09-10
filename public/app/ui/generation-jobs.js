/* Short-request generation delivery. No provider key, input text, image or model
   is saved by this module. sessionStorage holds only this tab's job capability.
   Recovery is GET-only: a lost receipt NEVER submits another paid generation. */
import { __ACS_SHARED } from '../shared-state.js';
import { statusEl } from '../render/scene.js';
import { acsApplyTicket, acsApplyBuilding, acsApplyFirstFrame, showReport, srvURL } from './workspace-ui-wiring.js';

const ACS_ASYNC_PATHS = {
  '/v1/understand': '/v1/jobs/understand',
  '/v1/understand/image': '/v1/jobs/understand/image',
  '/v1/understand/pdf': '/v1/jobs/understand/pdf',
  '/v1/edit': '/v1/jobs/edit',
};
const ACS_ASYNC_STORAGE = 'acs.pending-generation.v1';
const ACS_ASYNC_BASE_FETCH = __ACS_SHARED.acsFetchJSON;
let ACS_ASYNC_ACTIVE = null;
let ACS_ASYNC_MEMORY = null;

function acsJobBase() {
  return String(srvURL() || '').replace(/\/$/, '');
}
function acsJobRead() {
  let row = ACS_ASYNC_MEMORY;
  try { row = JSON.parse(window.sessionStorage.getItem(ACS_ASYNC_STORAGE)) || row; }
  catch (e) { /* storage unavailable: same-page recovery still works */ }
  if (!row || !/^job_[a-f0-9]{32}$/.test(row.id)
      || !/^[a-f0-9]{64}$/.test(row.token) || !ACS_ASYNC_PATHS[row.path]
      || typeof row.base !== 'string' || !Number.isFinite(row.created)) return null;
  return row;
}
function acsJobSave(row) {
  ACS_ASYNC_MEMORY = row;
  try { window.sessionStorage.setItem(ACS_ASYNC_STORAGE, JSON.stringify(row)); }
  catch (e) { /* No input is persisted; never fail generation on storage quota. */ }
}
function acsJobClear() {
  ACS_ASYNC_MEMORY = null;
  try { window.sessionStorage.removeItem(ACS_ASYNC_STORAGE); } catch (e) { /* optional storage */ }
  const box = document.getElementById('acsJobRecovery');
  if (box) box.remove();
}
function acsJobRandom(bytes) {
  if (!window.crypto || typeof window.crypto.getRandomValues !== 'function')
    throw new Error('Secure random generation is unavailable');
  const data = new Uint8Array(bytes);
  window.crypto.getRandomValues(data);
  return Array.from(data, b => b.toString(16).padStart(2, '0')).join('');
}
function acsJobFailure(message, http = 0, code = 'ACS_NOT_FOUND') {
  return {status: 'VALID_API_ERROR', http, code, message,
    retryable: false, request_id: '', body: null};
}
function acsJobTransient(res) {
  return ['NETWORK_ERROR', 'NETWORK_OFFLINE', 'NETWORK_DNS', 'TIMEOUT', 'HTTP_5XX', 'HTTP_429'].includes(res.status)
    || (res.status === 'VALID_API_ERROR' && res.retryable && res.http >= 500);
}
function acsJobSleep(ms) {
  return new Promise(resolve => {
    let timer;
    const finish = () => {
      clearTimeout(timer);
      window.removeEventListener('online', finish);
      document.removeEventListener('visibilitychange', visible);
      resolve();
    };
    const visible = () => { if (document.visibilityState !== 'hidden') finish(); };
    timer = setTimeout(finish, ms);
    window.addEventListener('online', finish, {once: true});
    document.addEventListener('visibilitychange', visible);
  });
}
function acsJobProgress(message) {
  if (statusEl) statusEl.textContent = message;
  const pill = document.getElementById('srvPill');
  if (pill) { pill.className = 'srv'; pill.textContent = message; }
  const live = document.getElementById('acsLiveRegion');
  if (live && live.textContent !== message) live.textContent = message;
}
async function acsJobWait(row, signal) {
  const headers = {'X-ACS-Job-Token': row.token};
  const path = '/v1/jobs/' + row.id;
  let absent = 0;
  for (;;) {
    if (acsJobBase() !== row.base)
      return acsJobFailure('تغيّر عنوان الخادم؛ لم تُرسل بيانات الاستعادة إلى خادم آخر.');
    if (signal && signal.aborted)
      return acsJobFailure('توقفت المتابعة فقط؛ المهمة قد تكون مستمرة. استخدم استعادة النتيجة.');
    const res = await ACS_ASYNC_BASE_FETCH(path, {method: 'GET', headers, cache: 'no-store'}, 15000);
    if (res.status === 'SUCCESS' && res.body && res.body.contract === 'acs.async-generation/1.0'
        && res.body.job && res.body.job.id === row.id) {
      const job = res.body.job;
      row.state = job.state;
      if (Number.isFinite(job.expires_at)) row.expires = job.expires_at * 1000;
      acsJobSave(row);
      if (job.state === 'SUCCEEDED' || job.state === 'FAILED') {
        const result = await ACS_ASYNC_BASE_FETCH(path + '/result',
          {method: 'GET', headers, cache: 'no-store'}, 20000);
        // A stored error is a terminal result, even when the original error is
        // retryable. Only a failed delivery may be polled again, never the job.
        if (result.status === 'SUCCESS' || (result.status === 'VALID_API_ERROR'
            && result.body && result.body.error)) {
          row.delivered = true;
          acsJobSave(row);
          return result;
        }
        if (!acsJobTransient(result)) return result;
        acsJobProgress('⏳ النتيجة جاهزة؛ تعذّر تنزيلها مؤقتاً. تُستعاد نفس النتيجة بلا توليد جديد.');
      } else if (job.state === 'QUEUED' || job.state === 'RUNNING') {
        acsJobProgress(job.state === 'QUEUED'
          ? '⏳ تم استلام المهمة؛ تنتظر التنفيذ. يمكنك العودة إلى هذه الصفحة لمتابعتها.'
          : '🤖 التوليد مستمر على الخادم — المتابعة بطلبات قصيرة، دون إعادة التوليد.');
      } else {
        return acsJobFailure('حالة المهمة غير قابلة للاستعادة؛ لم يُعَد التوليد تلقائياً.');
      }
    } else if (res.http === 404 && !row.acknowledged && absent++ < 4) {
      acsJobProgress('⏳ جارٍ التحقق من وصول الطلب السابق — لن نرسل طلب توليد آخر.');
    } else if (!acsJobTransient(res)) {
      return res;
    } else {
      acsJobProgress('⏳ انقطع الاتصال مؤقتاً؛ ستُستأنف متابعة نفس المهمة عند عودته.');
    }
    if (Date.now() > (row.expires || row.created + 1800000))
      return acsJobFailure('انتهت مهلة متابعة النتيجة؛ لم يُعَد تشغيل التوليد تلقائياً.', 410);
    await acsJobSleep(document.visibilityState === 'hidden' ? 10000 : 2000);
  }
}
async function acsJobSubmit(path, opts) {
  const previous = acsJobRead();
  if (previous && !previous.delivered) {
    acsJobRecoveryBanner();
    return acsJobFailure('يوجد طلب سابق لم تُستلم نتيجته. تابع المهمة السابقة أولاً.', 409, 'ACS_BAD_REQUEST');
  }
  const row = {id: 'job_' + acsJobRandom(16), token: acsJobRandom(32), path,
    base: acsJobBase(), created: Date.now(), state: 'SUBMITTING', delivered: false};
  acsJobSave(row); // Before POST: even loss of the receipt can be recovered by GET.
  const headers = Object.assign({}, opts.headers || {},
    {'X-ACS-Job-ID': row.id, 'X-ACS-Job-Token': row.token});
  const receipt = await ACS_ASYNC_BASE_FETCH(ACS_ASYNC_PATHS[path],
    Object.assign({}, opts, {headers}), 20000);
  if (receipt.status === 'SUCCESS' && receipt.body && receipt.body.contract === 'acs.async-generation/1.0'
      && receipt.body.job && receipt.body.job.id === row.id) {
    row.acknowledged = true;
    acsJobSave(row);
  } else if (!acsJobTransient(receipt)) {
    // A definite rejection at the new endpoint, not an ambiguous network error.
    // An old backend returns 404 here without calling a generation handler.
    if ([400, 404, 405, 413, 422, 429].includes(receipt.http)) acsJobClear();
    return receipt;
  }
  const result = await acsJobWait(row, opts.signal);
  if (!row.delivered) acsJobRecoveryBanner();
  return result;
}
__ACS_SHARED.acsFetchJSON = function acsJobTransport(path, opts, timeoutMs) {
  if (!ACS_ASYNC_PATHS[path] || !opts || String(opts.method || '').toUpperCase() !== 'POST')
    return ACS_ASYNC_BASE_FETCH(path, opts, timeoutMs);
  if (ACS_ASYNC_ACTIVE)
    return Promise.resolve(acsJobFailure('هناك مهمة قيد المتابعة؛ لم يُرسل طلب مكرر.', 409, 'ACS_BAD_REQUEST'));
  ACS_ASYNC_ACTIVE = acsJobSubmit(path, opts).catch(() => {
    acsJobRecoveryBanner();
    return acsJobFailure('تعذّرت متابعة المهمة محلياً؛ استخدم استعادة النتيجة قبل بدء توليد آخر.');
  }).finally(() => { ACS_ASYNC_ACTIVE = null; });
  return ACS_ASYNC_ACTIVE;
};

async function acsJobRecover() {
  const row = acsJobRead();
  if (!row || ACS_ASYNC_ACTIVE) return;
  const seq = acsApplyTicket();
  const before = window.ACS.exportModel && window.ACS.exportModel();
  ACS_ASYNC_ACTIVE = acsJobWait(row);
  let result;
  try { result = await ACS_ASYNC_ACTIVE; }
  finally { ACS_ASYNC_ACTIVE = null; }
  if (!result || result.status !== 'SUCCESS' || !(result.body && result.body.building)) {
    acsJobProgress((result && result.message) || 'تعذّرت استعادة المهمة؛ لم يبدأ توليد آخر.');
    return;
  }
  const data = result.body;
  if (row.path === '/v1/edit') {
    // Recovery cannot bypass the existing engineering replacement approval.
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = 'acs-edit-proposal.json';
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 30000);
    acsJobProgress('✓ استُعيد اقتراح التعديل للتنزيل والمراجعة؛ لم يُستبدل النموذج تلقائياً.');
    return;
  }
  const current = window.ACS.exportModel && window.ACS.exportModel();
  if (current !== before) {
    acsJobProgress('النتيجة جاهزة، لكن النموذج تغيّر أثناء الانتظار. اضغط الاستعادة مجدداً لمراجعتها.');
    return;
  }
  if (current && !window.confirm('استبدال النموذج المعروض بنتيجة المهمة السابقة؟ لن يُعاد التوليد.')) return;
  const ap = acsApplyBuilding(data.building, {seq});
  if (ap.stale) return;
  if (!ap.ok) {
    __ACS_SHARED.acsApplyErrorPanel(ap, result, acsJobRecover, null);
    return;
  }
  // The original description isn't reconstructed or guessed after a reload.
  __ACS_SHARED.LAST_REQUEST_TEXT = '';
  showReport(data.report, '');
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const frame = acsApplyFirstFrame(ap);
    if (!frame.ok || frame.degraded) {
      __ACS_SHARED.acsApplyErrorPanel(frame, result, acsJobRecover, null);
      return;
    }
    acsJobProgress('✓ استُعيدت نتيجة التوليد السابقة — '
      + window.ACS.trust.modelReviewSummary(data, document.documentElement.lang));
    if (window.ACS.residentialQuality) window.ACS.residentialQuality.apply(data.building);
  }));
}
function acsJobRecoveryBanner() {
  if (typeof document === 'undefined') return;
  const row = acsJobRead(), anchor = document.getElementById('genLLM');
  if (!row || !anchor || document.getElementById('acsJobRecovery')) return;
  const box = document.createElement('div'); box.id = 'acsJobRecovery'; box.className = 'srv';
  const text = document.createElement('p');
  text.textContent = 'لديك مهمة سابقة. استعد نتيجتها دون توليد جديد. تُحفظ النتيجة مؤقتاً لمدة 30 دقيقة على الخادم؛ إعادة تشغيل الخادم قد تفقدها.';
  const resume = document.createElement('button'); resume.type = 'button';
  resume.textContent = row.path === '/v1/edit' ? 'استعادة اقتراح التعديل' : 'متابعة / استعادة النتيجة';
  resume.onclick = async () => { resume.disabled = true; try { await acsJobRecover(); } finally { resume.disabled = false; } };
  const forget = document.createElement('button'); forget.type = 'button'; forget.textContent = 'إغلاق متابعة المهمة';
  forget.onclick = () => {
    if (ACS_ASYNC_ACTIVE) return;
    if (window.confirm('هذا لا يلغي التوليد على الخادم. بدء توليد جديد قد يستهلك حصة وتكلفة إضافية. إغلاق المتابعة؟')) acsJobClear();
  };
  box.append(text, resume, forget); anchor.insertAdjacentElement('afterend', box);
}
if (typeof window !== 'undefined') {
  window.ACS = window.ACS || {};
  window.ACS.asyncGeneration = {
    recover: acsJobRecover,
    state: () => { const row = acsJobRead(); return row ? {id: row.id, state: row.state,
      delivered: !!row.delivered, path: row.path} : null; }, // Never expose capability.
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', acsJobRecoveryBanner);
  else acsJobRecoveryBanner();
}
