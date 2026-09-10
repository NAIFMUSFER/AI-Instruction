/* Text-generation delivery: short requests, one paid submission, safe GET recovery.
   The old API remains available when the backend explicitly lacks this protocol.
   Tokens and request text remain in this closure; never in URLs, logs or storage.
   A refresh/server restart is NOT covered by this initial receipt implementation. */
import { __ACS_SHARED } from '../shared-state.js';

function createGenerationDelivery(acsFetchJSON, env) {
  const contract = 'acs.generation-delivery/1';
  let pending = null;
  const transient = r => ['NETWORK_ERROR', 'NETWORK_OFFLINE', 'TIMEOUT',
    'HTTP_5XX'].includes((r || {}).status);
  const failure = (receipt, status, message) => ({
    status, http: 0, request_id: receipt ? 'req_' + receipt.id : '',
    path: '/v1/understand', url: '', body: null, message,
    retryable: false, retry_after: 0, delivery_pending: !!receipt,
  });
  const randomHex = n => Array.from(env.random(n), b => b.toString(16).padStart(2, '0')).join('');
  function sleep(ms, signal) {
    return new Promise(resolve => {
      if (signal && signal.aborted) { resolve(); return; }
      let timer;
      const finish = () => {
        env.clearTimer(timer);
        if (signal) signal.removeEventListener('abort', finish);
        resolve();
      };
      timer = env.timer(finish, ms);
      if (signal) signal.addEventListener('abort', finish, { once: true });
    });
  }
  function isPending(r, receipt) {
    return r.status === 'SUCCESS' && r.http === 202
      && r.body && r.body.contract === contract && r.body.operation_id === receipt.id;
  }
  async function poll(receipt, deadline, signal) {
    while (env.now() < deadline) {
      if (signal && signal.aborted) return failure(receipt, 'NETWORK_ERROR',
        'توقفت متابعة الطلب على هذا الجهاز؛ قد يكتمل التوليد على الخادم.');
      const r = await acsFetchJSON('/v1/understand/jobs/' + receipt.id,
        { method: 'GET', headers: { 'X-ACS-Operation-Token': receipt.token },
          signal, cache: 'no-store' }, Math.min(20000, deadline - env.now()));
      if (isPending(r, receipt) || transient(r)) {
        await sleep(Math.min(2000, Math.max(0, deadline - env.now())), signal);
        continue;
      }
      if (r.status === 'SUCCESS' && r.http === 202) return failure(receipt,
        'INVALID_JSON', 'رد متابعة الطلب لا يطابق رقم العملية؛ لم يُعد التوليد.');
      if (r.http === 404) return failure(receipt, 'NETWORK_ERROR',
        'النتيجة غير متاحة أو انتهت مدة الاحتفاظ بها. لم يُرسل طلب توليد ثانٍ.');
      if (pending === receipt) pending = null;
      return r; // Only the terminal response reaches the existing apply boundary.
    }
    return failure(receipt, 'TIMEOUT',
      'انتهت مهلة متابعة النتيجة؛ لم يُعد التوليد. تابع الطلب نفسه بدلاً من تكراره.');
  }
  async function call(path, opts, timeoutMs) {
    if (path !== '/v1/understand' || (opts || {}).method !== 'POST'
        || typeof opts.body !== 'string') return acsFetchJSON(path, opts, timeoutMs);
    const deadline = env.now() + Math.max(1000, timeoutMs || 900000);
    // This capability request happens BEFORE any paid POST. A missing endpoint
    // is the only HTTP-error path that may fall back to the legacy operation.
    const caps = await acsFetchJSON('/v1/generation-delivery',
      { method: 'GET', signal: opts.signal, cache: 'no-store' }, 10000);
    const base = env.base();
    if (pending && pending.base === base && pending.body === opts.body) {
      // Even a temporary capability failure must never resubmit a known receipt.
      return poll(pending, deadline, opts.signal);
    }
    if (opts.signal && opts.signal.aborted) return failure(null,
      'NETWORK_ERROR', 'أُلغيت المتابعة قبل إرسال التوليد.');
    if (caps.http === 404 || caps.http === 405
        || (caps.status === 'SUCCESS' && (caps.body || {}).contract === contract
          && caps.body.enabled === false)) {
      return acsFetchJSON(path, opts, timeoutMs);
    }
    if (caps.status !== 'SUCCESS') return caps;
    if ((caps.body || {}).contract !== contract) return failure(null,
      'INVALID_JSON', 'عقد متابعة التوليد غير معروف؛ لم يُرسل طلب توليد.');
    let id, token;
    try { id = randomHex(16); token = randomHex(32); }
    catch (e) { return failure(null, 'NOT_CONFIGURED',
      'تعذر إنشاء رمز متابعة آمن على هذا المتصفح؛ لم يُرسل التوليد.'); }
    const receipt = { id, token, body: opts.body, base };
    pending = receipt;
    if (typeof env.notice === 'function') env.notice('جارٍ التوليد ومتابعة النتيجة. '
      + 'تُحتفظ النتيجة مؤقتاً في ذاكرة الخادم لمدة 15 دقيقة بعد اكتمالها؛ '
      + 'أبقِ هذه الصفحة مفتوحة لاستعادتها إذا انقطع الاتصال. معرّف الطلب: req_' + id);
    const r = await acsFetchJSON('/v1/understand/jobs', {
      method: 'POST', body: opts.body, signal: opts.signal,
      headers: Object.assign({}, opts.headers || {}, {
        'X-ACS-Operation-ID': id, 'X-ACS-Operation-Token': token,
        'X-Request-ID': 'req_' + id,
      }),
    }, Math.min(20000, Math.max(1000, deadline - env.now())));
    // Lost acknowledgement: recover by GET using our original receipt identity.
    // Never retry POST, fall back to legacy POST, or invoke a second provider.
    if (isPending(r, receipt) || transient(r)) return poll(receipt, deadline, opts.signal);
    if (r.status === 'SUCCESS' && r.http === 202) return failure(receipt,
      'INVALID_JSON', 'تعذر التحقق من إيصال التوليد؛ لم يُرسل طلب ثانٍ.');
    if (pending === receipt) pending = null;
    return r;
  }
  return { call, state: () => pending ? { operation_id: pending.id,
    recoverable_in_this_page: true, survives_reload: false } : null };
}

if (typeof window !== 'undefined' && typeof __ACS_SHARED.acsFetchJSON === 'function') {
  const delivery = createGenerationDelivery(__ACS_SHARED.acsFetchJSON, {
    now: () => Date.now(), timer: (fn, ms) => setTimeout(fn, ms),
    clearTimer: id => clearTimeout(id),
    base: () => (window.ACS_API ? window.ACS_API.base() : ''),
    notice: text => {
      const el = document.getElementById('status');
      if (el) el.textContent = text;
    },
    random: n => window.crypto.getRandomValues(new Uint8Array(n)),
  });
  __ACS_SHARED.acsFetchJSON = delivery.call;
  window.ACS = window.ACS || {};
  window.ACS.generationDelivery = { state: delivery.state };
}
