// Isolated smoke test: no ACS session, project API, analytics, or persisted token.
const status = document.getElementById('status');
const send = document.getElementById('send');
const confirmButton = document.getElementById('confirm');
const codeForm = document.getElementById('code-form');
const codeInput = document.getElementById('code');
const phoneInput = document.getElementById('phone');
const digits = value => value.replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 1632))
  .replace(/[۰-۹]/g, d => String(d.charCodeAt(0) - 1776));
function saudiPhone(value) {
  let number = digits(value).replace(/[\s()-]/g, '');
  if (/^05\d{8}$/.test(number)) number = '+966' + number.slice(1);
  if (/^5\d{8}$/.test(number)) number = '+966' + number;
  return /^\+9665\d{8}$/.test(number) ? number : null;
}
function explain(error) {
  const messages = {
    'auth/unauthorized-domain': 'أضف نطاق هذه الصفحة إلى Authorized domains في Firebase.',
    'auth/operation-not-allowed': 'تحقق من تفعيل Phone وسياسة السماح بإرسال SMS للسعودية.',
    'auth/billing-not-enabled': 'يلزم تفعيل فوترة Blaze لهذا المشروع.',
    'auth/quota-exceeded': 'تم بلوغ حصة الإرسال. راجع الفوترة وحصة SMS في Firebase.',
    'auth/too-many-requests': 'محاولات كثيرة. انتظر قبل المحاولة مجددًا.',
    'auth/invalid-verification-code': 'الكود غير صحيح. راجعه وحاول مرة أخرى.',
    'auth/code-expired': 'انتهت صلاحية الكود. اطلب كودًا جديدًا.',
    'auth/captcha-check-failed': 'تعذر التحقق من reCAPTCHA. أعد المحاولة.',
    'auth/network-request-failed': 'تعذر الاتصال. تحقق من الإنترنت وحاول مجددًا.',
    'auth/invalid-app-credential': 'تعذر التحقق من إعدادات التطبيق. راجع النطاق وreCAPTCHA في Firebase.'
  };
  return messages[error?.code] || 'تعذر إكمال الاختبار. راجع إعدادات Firebase واتصال الإنترنت.';
}
async function main() {
  const [{ initializeApp }, sdk] = await Promise.all([
    import('https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js'),
    import('https://www.gstatic.com/firebasejs/12.19.0/firebase-auth.js')
  ]);
  const app = initializeApp({
    apiKey: 'AIzaSyCb91efpCcbNG3odlx3oMCWUz3Q0Bd1mw8',
    authDomain: 'naif-c8b45.firebaseapp.com',
    projectId: 'naif-c8b45',
    appId: '1:209379254883:web:919d11dc175a3d13c0ce56'
  }, 'acs-phone-check');
  const auth = sdk.initializeAuth(app, { persistence: sdk.inMemoryPersistence });
  auth.languageCode = 'ar';
  let verifier = null;
  let confirmation = null;
  let busy = false;
  let retryAt = 0;
  let completed = false;
  const update = () => { send.disabled = busy || completed || Date.now() < retryAt; };
  setInterval(update, 1000);
  const resetCaptcha = () => { verifier?.clear(); verifier = null; };
  document.getElementById('phone-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (busy || completed || Date.now() < retryAt) return;
    const phone = saudiPhone(phoneInput.value);
    if (!phone) { status.textContent = 'أدخل رقم جوال سعودي صحيحًا بصيغة 05xxxxxxxx أو +9665xxxxxxxx.'; return; }
    busy = true;
    confirmation = null;
    codeForm.hidden = true;
    codeInput.value = '';
    retryAt = Date.now() + 60000;
    update();
    status.textContent = 'أكمل التحقق البشري لإرسال الكود…';
    try {
      resetCaptcha();
      verifier = new sdk.RecaptchaVerifier(auth, 'recaptcha', { size: 'normal' });
      confirmation = await sdk.signInWithPhoneNumber(auth, phone, verifier);
      codeForm.hidden = false;
      status.textContent = 'تم طلب إرسال الكود. أدخله هنا عند وصوله. يمكنك إعادة الإرسال بعد دقيقة.';
      codeInput.focus();
    } catch (error) {
      status.textContent = explain(error);
    } finally {
      resetCaptcha();
      busy = false;
      update();
    }
  });
  codeForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (busy || !confirmation || completed) return;
    const code = digits(codeInput.value).trim();
    if (!/^\d{6}$/.test(code)) { status.textContent = 'أدخل الكود المكوّن من 6 أرقام.'; return; }
    busy = true;
    confirmButton.disabled = true;
    update();
    try {
      await confirmation.confirm(code);
      completed = true;
      confirmation = null;
      codeInput.value = '';
      phoneInput.value = '';
      codeForm.hidden = true;
      await sdk.signOut(auth);
      status.textContent = 'نجح التحقق من الكود. اكتمل اختبار Firebase؛ لم تُنشأ جلسة دخول إلى مشاريع acsAI.';
    } catch (error) {
      status.textContent = completed ? 'نجح التحقق. أغلق الصفحة لإنهاء جلسة الاختبار المؤقتة.' : explain(error);
    } finally {
      busy = false;
      confirmButton.disabled = false;
      update();
    }
  });
  status.textContent = 'جاهز للاختبار. أدخل رقمك ثم اضغط إرسال.';
  update();
}
main().catch(() => { status.textContent = 'تعذر تحميل خدمة التحقق. تحقق من اتصال الإنترنت وسياسة المحتوى، ثم أعد تحميل الصفحة.'; });
