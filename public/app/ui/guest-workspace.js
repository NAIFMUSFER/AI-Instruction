/* Public, local-only workspace. No auth identity, provider call or cloud upload. */
const A = window.ACS;
const $ = id => document.getElementById(id);

async function openGuestWorkspace() {
  if (!A?.guest || $('acsGuestBanner')) return;
  A.finishGuestBoot?.();
  document.body.classList.add('acs-guest');
  const banner = document.createElement('aside');
  banner.id = 'acsGuestBanner';
  banner.setAttribute('aria-label', 'تجربة الاستوديو بدون تسجيل');
  banner.innerHTML = '<div><strong>جرّب الاستوديو بدون تسجيل</strong><p id="acsGuestStatus" role="status">نماذج تجريبية وتعديلات محلية على هذا الجهاز. ليست مخططات تنفيذية.</p></div>'
    + '<div class="guest-save"><span id="guestSaveStatus" role="status">غير محفوظ على هذا الجهاز</span>'
    + '<button id="guestDownload" type="button" hidden>تنزيل JSON</button></div>'
    + '<div class="guest-actions"><button id="guestExample" type="button">عمارة تجريبية</button>'
    + '<button id="guestWarehouse" type="button">مستودع تجريبي</button>'
    + '<button id="guestCreate" type="button">إنشاء محلي</button>'
    + '<a href="/?signin=1" id="guestSignin">تسجيل الدخول للذكاء والحفظ السحابي</a></div>';
  document.body.append(banner);
  A.guestRecoveryPending = true;
  A.guestAutosaveReady = false;
  A.guestRecoveryReadable = false;
  let interactionEpoch = 0;
  let changedModel = false;
  let restoring = false;
  const saveStatus = $('guestSaveStatus');
  const download = $('guestDownload');
  download.addEventListener('click', () => $('bJson').click());
  const markUnsaved = () => { saveStatus.textContent = 'غير محفوظ على هذا الجهاز'; };
  function modelChanged() {
    if (restoring) return;
    interactionEpoch++;
    changedModel = true;
    if (A.guestRecoveryReadable) {
      A.guestAutosaveReady = true;
      markUnsaved();
    }
  }
  function failedRecovery() {
    A.guestRecoveryReadable = false;
    A.guestAutosaveReady = false;
    saveStatus.textContent = 'غير محفوظ · تعذّرت قراءة التخزين المحلي';
    download.hidden = false;
    notice('تعذّرت استعادة الحفظ المحلي. يمكنك تنزيل JSON للاحتفاظ بعملك.');
  }
  const userIntent=event=>{
    if(event.target?.closest?.('#acsPanelMake input,#acsPanelMake textarea,#acsPanelMake select'))interactionEpoch++;
  };
  for(const event of ['input','change'])document.addEventListener(event,userIntent,true);
  banner.dataset.recovery='pending';
  const notice = text => { $('acsGuestStatus').textContent = text; };
  for (const id of ['genLLM', 'bNotesApply']) {
    const button = $(id);
    if (!button) continue;
    button.disabled = true;
    button.setAttribute('aria-disabled', 'true');
    button.title = 'تسجيل الدخول مطلوب لاستخدام الذكاء. استخدم التوليد المحلي أو النماذج التجريبية.';
  }
  $('genLLM').textContent = 'الذكاء — سجّل الدخول من الشريط العلوي';
  const local = $('genText');
  local.textContent = 'توليد محلي تقريبي — بدون ذكاء';
  local.classList.remove('acs-u-05');
  local.classList.add('btn', 'g');
  $('genLLM').before(local);
  const upload = $('impFile');
  upload.accept = '.json,.dxf,application/json';
  const uploadLabel = document.querySelector('label[for="impFile"]');
  if (uploadLabel?.firstChild) uploadLabel.firstChild.textContent = '📎 استيراد محلي — JSON أو DXF ';
  const serverSettings = $('llmURL')?.closest('.fld');
  if (serverSettings) serverSettings.hidden = true;
  const sub = document.querySelector('#left header .sub');
  if (sub) sub.textContent = 'نماذج تجريبية أو توليد محلي تقريبي. تبقى ملفاتك على هذا الجهاز.';
  const firstNote = document.querySelector('#acsPanelMake > .note');
  if (firstNote) firstNote.textContent = 'جرّب نموذجًا جاهزًا أو اكتب وصفًا للتوليد المحلي التقريبي. استيراد JSON وDXF يبقى على جهازك.';

  function sample(kind, initial = false) {
    if (!initial) modelChanged();
    if (kind === 'warehouse') $('loadWarehouse').click();
    else A.showExample();
    if (A.setProjectPanelOpen && innerWidth <= 820) A.setProjectPanelOpen(false);
    const text = kind === 'warehouse' ? 'مستودع تجريبي جاهز — لم يُولّد بالذكاء.' : 'عمارة تجريبية جاهزة — لم تُولّد بالذكاء.';
    notice(text + ' يمكنك التنقّل وتغيير العرض وحفظ نسخة محلية.');
    $('status').textContent = text;
    if (A.residentialQuality) A.residentialQuality.apply(A.exportModel()).catch(() => {});
  }
  $('guestExample').addEventListener('click', () => sample('residential'));
  $('guestWarehouse').addEventListener('click', () => sample('warehouse'));
  $('guestCreate').addEventListener('click', () => {
    document.querySelector('[data-tab="make"]').click();
    A.setProjectPanelOpen?.(true);
    $('descText').focus();
    notice('اكتب وصفًا واضغط التوليد المحلي التقريبي. لن يُرسل الوصف إلى أي خادم.');
  });
  for (const [id, label] of [['loadExample','عمارة تجريبية جاهزة'],['loadWarehouse','مستودع تجريبي جاهز']]) {
    $(id).addEventListener('click', () => { notice(label + ' — لم يُولّد بالذكاء.'); $('status').textContent = label + ' — نموذج محلي.'; });
  }
  local.addEventListener('click', () => {
    notice('توليد محلي تقريبي من وصفك؛ راجع الأبعاد والعناصر. لا يستخدم الذكاء ولا يُرسل بيانات.');
  });
  upload.addEventListener('change', () => {
    notice('يُقرأ ملفك محليًا على هذا الجهاز فقط.');
  });
  A.guestWorkspace = { contract: 'acs-local-guest/1', localOnly: true, storageScope: A_AUTH_SCOPE(), sample, modelChanged };
  // Show a usable sample immediately, but never persist it while storage is
  // still being read. A slow read remains authoritative until user interaction;
  // the timer only explains the wait and never discards the saved project.
  let timer;
  try {
    const recovery = A.persistence.recover();
    restoring = true;
    try { sample('residential', true); } finally { restoring = false; }
    notice('نموذج تجريبي مؤقت؛ جارٍ البحث عن عملك المحلي. الحفظ التلقائي متوقف حتى اكتمال الاستعادة.');
    timer=setTimeout(()=>{
      banner.dataset.recoveryStatus='slow';
      if(interactionEpoch===0)notice('استعادة العمل المحلي تستغرق وقتًا أطول. يمكنك استعراض النموذج المؤقت؛ لم يُكتب فوق عملك المحفوظ.');
    },1500);
    const recovered = await recovery;
    const recoveredModel = recovered?.ok && recovered.project?.model;
    if (!recoveredModel && recovered?.code !== 'NO_RECORDS') {
      failedRecovery();
      return;
    }
    A.guestRecoveryReadable = true;
    if (interactionEpoch !== 0) {
      A.guestAutosaveReady = changedModel;
      markUnsaved();
      return;
    }
    if (recoveredModel) {
      restoring = true;
      try { A.setModel(recoveredModel); } finally { restoring = false; }
      saveStatus.textContent = 'استُعيد من هذا الجهاز';
      notice('استُعيد آخر عمل للضيف من هذا الجهاز. لم يُفتح أي مشروع حساب خاص.');
      if (A.setProjectPanelOpen && innerWidth <= 820) A.setProjectPanelOpen(false);
    } else {
      markUnsaved();
      notice('عمارة تجريبية جاهزة — لم تُولّد بالذكاء. يمكنك التنقّل وتغيير العرض وحفظ نسخة محلية.');
    }
    A.guestAutosaveReady = true;
  } catch {
    failedRecovery();
  } finally {
    clearTimeout(timer);A.guestRecoveryPending=false;banner.dataset.recovery='complete';
    for(const event of ['input','change'])document.removeEventListener(event,userIntent,true);
  }
}
function A_AUTH_SCOPE() { return window.ACS_AUTH.storageScope(); }
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', openGuestWorkspace);
else openGuestWorkspace();
