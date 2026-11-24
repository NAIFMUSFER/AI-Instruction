/* Public, local-only workspace. No auth identity, provider call or cloud upload. */
import { openGuestFloorPlan } from './guest-floor-plan.mjs';

const A = window.ACS;
const $ = id => document.getElementById(id);

async function openGuestWorkspace() {
  if (!A?.guest || $('acsGuestBanner')) return;
  A.finishGuestBoot?.();
  document.body.classList.add('acs-guest');
  const banner = document.createElement('aside');
  banner.id = 'acsGuestBanner';
  banner.setAttribute('aria-label', 'أدوات المشروع المحلي');
  banner.innerHTML = `
    <div class="guest-identity">
      <strong id="acsGuestStatus" role="status">مشروع تجريبي</strong>
      <span id="guestSaveStatus" role="status">غير محفوظ على هذا الجهاز</span>
    </div>
    <div class="guest-controls">
      <button id="guestCreate" type="button">صف مبناك</button>
      <button id="guestRevise" type="button" aria-haspopup="dialog" hidden>تعديل التصميم</button>
      <button id="guestPlan" type="button" aria-haspopup="dialog">المخطط</button>
      <button id="guestViewToggle" type="button">كشف الدور</button>
      <details id="guestOptions">
        <summary id="guestTools" aria-label="خيارات المشروع المحلي"><span aria-hidden="true">•••</span></summary>
        <div class="guest-menu">
          <p id="guestFacts" hidden></p>
          <p id="guestStorageNote" hidden>تُحفظ تغييرات هذا المثال في مسودة مستقلة على جهازك.</p>
          <a id="guestNew" href="/?guest=1&amp;new=1" target="_blank" rel="noopener">مشروع جديد في علامة تبويب أخرى</a>
          <button id="guestReviseExisting" type="button" aria-haspopup="dialog" hidden>تعديل التصميم الحالي</button>
          <div class="guest-menu-grid" role="group" aria-label="اختيار نموذج تجريبي">
            <button id="guestExample" type="button">عمارة تجريبية</button>
            <button id="guestWarehouse" type="button">مستودع تجريبي</button>
          </div>
          <div class="guest-menu-grid" role="group" aria-label="مشاهد المبنى">
            <button id="guestInterior" type="button">من الداخل</button>
            <button id="guestDetail" type="button">تفاصيل المدخل</button>
          </div>
          <button id="guestFloors" type="button">اختيار الطوابق والطبقات</button>
          <button id="guestExport" type="button">تنزيل النموذج بصيغة JSON</button>
          <a id="guestSignin" href="/?signin=1">تسجيل الدخول للحفظ السحابي</a>
        </div>
      </details>
    </div>
    <div class="guest-warning" id="guestWarning" hidden>
      <span id="guestFeedback" role="status"></span>
    </div>
    <button id="guestDownload" type="button" hidden>تنزيل JSON</button>
    <dialog id="guestRevisionDialog" dir="rtl" aria-labelledby="guestRevisionTitle">
      <form id="guestRevisionForm">
        <h2 id="guestRevisionTitle">تعديل التصميم</h2>
        <p id="guestRevisionFacts"></p>
        <label for="guestRevisionText">وش تبي تغيّر في العمارة؟</label>
        <textarea id="guestRevisionText" rows="3" required placeholder="مثلاً: خلّ المدخل من الجنوب"></textarea>
        <p id="guestRevisionError" role="alert" hidden></p>
        <div><button id="guestApplyRevision" type="submit">تطبيق التعديل</button>
        <button id="guestCancelRevision" type="button">الاحتفاظ بالتصميم الحالي</button></div>
      </form>
    </dialog>`;
  document.body.append(banner);
  A.guestRecoveryPending = true;
  A.guestAutosaveReady = false;
  A.guestRecoveryReadable = false;
  let interactionEpoch = 0;
  let changedModel = false;
  let restoring = false;
  const namedDraft = Boolean(window.ACS_AUTH.guestProjectId);
  const saveStatus = $('guestSaveStatus');
  const download = $('guestDownload');
  const options = $('guestOptions');
  const tools = $('guestTools');
  const viewToggle = $('guestViewToggle');
  const warning = $('guestWarning');
  const feedback = $('guestFeedback');
  const feedbackMessage = text => {
    feedback.textContent = text;
    warning.hidden = !text;
  };
  const closeOptions = (returnFocus = false) => {
    options.open = false;
    if (returnFocus) tools.focus();
  };
  const openPanel = tab => {
    closeOptions();
    A.setProjectPanelOpen?.(true);
    $(tab).click();
  };
  function syncViewButton(state = A.guestViewState?.()) {
    viewToggle.hidden = typeof A.guestView !== 'function' || !A.exportModel?.();
    const returnToExterior = ['cutaway','interior','detail'].includes(state?.mode);
    viewToggle.textContent = returnToExterior ? 'الواجهة' : 'كشف الدور';
  }
  viewToggle.addEventListener('click', () => {
    const mode = A.guestViewState?.()?.mode;
    chooseView(['cutaway','interior','detail'].includes(mode) ? 'exterior' : 'cutaway');
  });
  function chooseView(mode) {
    if (A.guestView?.(mode) === false) {
      feedbackMessage('لا يحتوي هذا النموذج على عناصر كافية لهذا المنظر. يمكنك فتح مخطط الدور.');
    } else if (A.guestRecoveryReadable) {
      feedbackMessage('');
    }
    syncViewButton();
  }
  for (const [id, mode] of [['guestInterior','interior'], ['guestDetail','detail']]) {
    $(id).addEventListener('click', () => { closeOptions(true); chooseView(mode); });
  }
  syncViewButton();
  window.addEventListener('acs:guest-view', event => syncViewButton(event.detail));
  function facts() {
    const model = A.exportModel?.();
    const apartment = model?.meta?.acs_apartment;
    const region = $('guestFacts');
    region.hidden = !apartment;
    region.textContent = apartment
      ? `المبنى ${apartment.width_m} × ${apartment.depth_m} م · ${apartment.occupied_levels} أدوار · ${apartment.units_total} شقق`
      : '';
    $('guestCreate').hidden = namedDraft && Boolean(apartment);
    $('guestRevise').hidden = !namedDraft || !apartment;
    $('guestReviseExisting').hidden = namedDraft || !apartment;
    for (const id of ['guestPlan','guestExport','guestInterior','guestDetail','guestFloors']) $(id).hidden = !model;
  }
  const exampleDraft = A_AUTH_SCOPE() === 'acs_guest_apartment_20x25_v1';
  $('guestStorageNote').hidden = !exampleDraft;
  if (exampleDraft) $('guestSignin').href = '/?signin=1&example=apartment-20x25';
  document.addEventListener('click', event => {
    if (options.open && !options.contains(event.target)) closeOptions();
  });
  options.addEventListener('keydown', event => {
    if (event.key === 'Escape' && options.open) {
      event.preventDefault(); event.stopPropagation(); closeOptions(true);
    }
  });
  options.addEventListener('toggle', () => { if (options.open) facts(); });
  $('guestFloors').addEventListener('click', () => {
    openPanel('acsTabModel');
    $('floors').querySelector('button')?.focus();
  });
  $('guestPlan').addEventListener('click', () => {
    closeOptions();
    try {
      const floorKey = A.guestViewState?.()?.floorKey;
      const selected = /^F(-?\d+)$/.exec(floorKey || '');
      openGuestFloorPlan(A, selected ? Number(selected[1]) : 0);
    } catch {
      feedbackMessage('تعذّر فتح المخطط. يمكنك اختيار الطابق من خيارات المشروع.');
    }
  });
  $('guestExport').addEventListener('click', () => {
    $('bJson').click();
    closeOptions(true);
  });
  download.addEventListener('click', () => $('bJson').click());
  const markUnsaved = () => { saveStatus.textContent = 'غير محفوظ على هذا الجهاز'; };
  function modelChanged() {
    // Recovery can replace the temporary sample while its floor sheet is open.
    const plan = $('guestPlanDialog');
    if (plan?.open) plan.close();
    facts();
    if (restoring) return;
    interactionEpoch++;
    changedModel = true;
    notice('مسودة محلية');
    if (A.guestRecoveryReadable) {
      feedbackMessage('');
      A.guestAutosaveReady = true;
      markUnsaved();
    }
  }
  function failedRecovery() {
    A.guestRecoveryReadable = false;
    A.guestAutosaveReady = false;
    if (!changedModel) notice(namedDraft ? 'مشروع محلي' : 'عمارة تجريبية');
    saveStatus.textContent = 'غير محفوظ · تعذّرت قراءة التخزين المحلي';
    download.hidden = !A.exportModel?.();
    feedbackMessage(download.hidden ? 'تعذّرت قراءة التخزين. يمكنك التصميم وتنزيل النتيجة.' : 'تعذّرت استعادة المسودة. نزّل النموذج للاحتفاظ به.');
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
    button.title = 'تتوفر خدمة الذكاء في مساحة الحساب.';
  }
  $('genLLM').hidden = true;
  $('descText').placeholder = 'عمارة سكنية بعرض ٢٠ م وعمق ٢٥ م، أرضي وأول وثانٍ. شقتان في كل دور، وفي كل شقة ثلاث غرف نوم وصالة ومطبخ وحمام عائلي وحمام خاص ودورة مياه للضيوف.';
  const widthLabel = document.querySelector('label[for="siteW"]');
  const depthLabel = document.querySelector('label[for="siteD"]');
  if (widthLabel) widthLabel.textContent = 'عرض المبنى (م)';
  if (depthLabel) depthLabel.textContent = 'عمق المبنى (م)';
  function suggestFormDimensions(model) {
    const values = {
      siteW: model?.site?.w,
      siteD: model?.site?.d,
      nFloors: model?.levels?.filter(level => level.kind !== 'roof').length,
    };
    for (const [id, value] of Object.entries(values)) {
      const input = $(id);
      if (Number.isFinite(value) && value > 0 && input.value === input.defaultValue) {
        input.defaultValue = String(value);
        input.value = String(value);
      }
    }
  }
  const local = $('genText');
  local.textContent = 'إنشاء التصميم على جهازي';
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
  if (sub) sub.textContent = 'وصف المبنى وملفات المشروع على جهازك';
  const firstNote = document.querySelector('#acsPanelMake > .note');
  if (firstNote) firstNote.textContent = 'يحوّل المصمم المحلي الأبعاد والفراغات المدعومة إلى مخطط أولي. يبقى الوصف وملفات JSON وDXF على جهازك.';

  function sample(kind, initial = false) {
    if (!initial) modelChanged();
    if (kind === 'warehouse') $('loadWarehouse').click();
    else A.showExample();
    if (A.setProjectPanelOpen && innerWidth <= 820) A.setProjectPanelOpen(false);
    const text = kind === 'warehouse' ? 'مستودع تجريبي' : 'عمارة تجريبية';
    notice(text); facts(); syncViewButton();
    $('status').textContent = text;
    if (A.residentialQuality) A.residentialQuality.apply(A.exportModel()).catch(() => {});
  }
  for (const [id, kind] of [['guestExample','residential'],['guestWarehouse','warehouse']]) {
    $(id).addEventListener('click', () => {
      closeOptions(true);
      sample(kind);
    });
  }
  $('guestCreate').addEventListener('click', () => {
    openPanel('acsTabMake');
    $('descText').focus();
  });
  const revisionDialog = $('guestRevisionDialog');
  const revisionText = $('guestRevisionText');
  const revisionError = $('guestRevisionError');
  for (const id of ['guestRevise','guestReviseExisting']) $(id).addEventListener('click', () => {
    closeOptions();
    facts();
    $('guestRevisionFacts').textContent = $('guestFacts').textContent;
    revisionText.value = '';
    revisionError.hidden = true;
    revisionDialog.showModal();
    revisionText.focus();
  });
  $('guestCancelRevision').addEventListener('click', () => revisionDialog.close());
  $('guestRevisionForm').addEventListener('submit', event => {
    event.preventDefault();
    if (!revisionText.value.trim()) { revisionText.focus(); return; }
    const result = A.reviseGuestApartment(revisionText.value.trim());
    if (result.ok) revisionDialog.close();
    else {
      revisionError.textContent = result.message;
      revisionError.hidden = false;
      revisionText.focus();
    }
  });
  for (const [id, label] of [['loadExample','عمارة تجريبية'],['loadWarehouse','مستودع تجريبي']]) {
    $(id).addEventListener('click', () => { notice(label); $('status').textContent = label; facts(); });
  }
  window.addEventListener('acs:local-generation', event => {
    const result = event.detail;
    if (!result?.ok) {
      feedbackMessage(result?.message || 'تعذّر إنشاء التصميم. راجع وصف المبنى.');
      return;
    }
    if (A.guestRecoveryReadable) feedbackMessage('');
    notice('تصميم محلي أولي');
    facts(); syncViewButton();
    if (innerWidth <= 820) {
      A.setProjectPanelOpen?.(false);
      $('guestPlan').focus();
    }
  });
  A.guestWorkspace = { contract: 'acs-local-guest/1', localOnly: true, storageScope: A_AUTH_SCOPE(), sample, modelChanged };
  // Named drafts start empty. Legacy and example links keep their preview.
  let timer;
  try {
    const recovery = A.persistence.recover();
    if (namedDraft) {
      notice('مشروع محلي');
      facts();
      openPanel('acsTabMake');
    } else {
      restoring = true;
      try { sample('residential', true); } finally { restoring = false; }
    }
    suggestFormDimensions(A.exportModel?.());
    saveStatus.textContent = 'جارٍ استعادة المسودة…';
    timer=setTimeout(()=>{
      banner.dataset.recoveryStatus='slow';
      if(interactionEpoch===0)saveStatus.textContent='استعادة المسودة مستمرة…';
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
      suggestFormDimensions(recoveredModel);
      saveStatus.textContent = 'استُعيد من هذا الجهاز';
      notice('استُعيد المشروع المحلي'); facts(); syncViewButton();
      if (A.setProjectPanelOpen && innerWidth <= 820) A.setProjectPanelOpen(false);
    } else {
      markUnsaved();
      notice(namedDraft ? 'مشروع جديد' : 'عمارة تجريبية');
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
