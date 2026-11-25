/* Public, local-only workspace. No auth identity, provider call or cloud upload. */
import { openGuestFloorPlan } from './guest-floor-plan.mjs';
import { apartmentConfirmation } from '../core/local-apartment.mjs';

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
          <a id="guestNativeSample" class="guest-native-sample" rel="ar" href="/guest-plans/apartment-20x25.usdz" aria-label="فتح مجسّم المثال على الآيفون" hidden><img src="/guest-plans/apartment-20x25-preview.jpg" width="62" height="44" alt=""></a>
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
  // Mesh selection opens the canonical inspector on top of the guest scene.
  // Its close API preserves selection so the visitor can return to the model.
  const inspectorToolbar = document.querySelector('#acsWorkspace .ws-top');
  if (inspectorToolbar) {
    const back = document.createElement('button');
    back.id = 'guestReturnToModel';
    back.type = 'button';
    back.className = 'ws-btn';
    back.textContent = 'العودة إلى المجسّم';
    back.addEventListener('click', () => {
      A.workspace.close();
      $('guestTools').focus();
    });
    inspectorToolbar.prepend(back);
  }
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
  const nativeSample = $('guestNativeSample');
  let referenceSample = '';
  function matchesNativeSample() {
    const model = A.exportModel?.();
    return Boolean(referenceSample && model?.meta?.acs_apartment?.source === 'synthetic_sample'
      && JSON.stringify(model) === referenceSample);
  }
  nativeSample.addEventListener('click', event => {
    if (!matchesNativeSample()) {
      event.preventDefault();
      nativeSample.hidden = true;
      feedbackMessage('تخص المعاينة الأصلية العمارة التجريبية. يمكنك استكشاف هذه النسخة في الاستوديو.');
    }
  });
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
  options.addEventListener('toggle', () => {
    if (!options.open) return;
    facts();
    nativeSample.hidden = !matchesNativeSample();
  });
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
    nativeSample.hidden = true;
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
  // Building size is its own pair of fields, separate from the land (owner decision 3).
  // No field is prefilled: an empty field is a question, never a value (owner decision 1).
  const siteRow = $('siteW').closest('.fld');
  const buildingRow = document.createElement('div');
  buildingRow.className = 'fld';
  buildingRow.id = 'guestBuildingFields';
  buildingRow.innerHTML = '<div><label for="bldW">عرض المبنى (م)</label><input id="bldW" type="number" min="0" step="any" inputmode="decimal" placeholder="من الوصف"></div>'
    + '<div><label for="bldD">عمق المبنى (م)</label><input id="bldD" type="number" min="0" step="any" inputmode="decimal" placeholder="من الوصف"></div>';
  (siteRow || $('siteW')).before(buildingRow);
  for (const [id, label, placeholder] of [['siteW','عرض الأرض (م)','اختياري'],['siteD','عمق الأرض (م)','اختياري'],['nFloors','الأدوار مع الأرضي','من الوصف']]) {
    const input = $(id), caption = document.querySelector('label[for="' + id + '"]');
    if (caption) caption.textContent = label;
    input.defaultValue = '';
    input.value = '';
    input.placeholder = placeholder;
  }
  const local = $('genText');
  local.textContent = 'إنشاء التصميم على جهازي';
  local.classList.remove('acs-u-05');
  local.classList.add('btn', 'g');
  $('genLLM').before(local);
  // «فهمنا: …» before anything is drawn (owner decision 2). One tap on «ارسم» draws
  // exactly the model summarised here; «عدّل» returns to the description.
  const confirmCard = document.createElement('section');
  confirmCard.id = 'guestConfirm';
  confirmCard.className = 'guest-confirm';
  confirmCard.dir = 'rtl';
  confirmCard.hidden = true;
  confirmCard.setAttribute('role', 'region');
  confirmCard.setAttribute('aria-labelledby', 'guestConfirmTitle');
  confirmCard.setAttribute('aria-live', 'polite');
  confirmCard.innerHTML = '<h3 id="guestConfirmTitle">فهمنا:</h3><p id="guestConfirmQuestion" hidden></p><ul id="guestConfirmRows"></ul>'
    + '<ul id="guestConfirmChoices" class="guest-confirm-choices" hidden></ul>'
    + '<div id="guestConfirmUnsupported" class="guest-confirm-unsupported" hidden><p>غير مدعوم في المولّد المحلي بعد، ولن يُرسم:</p><ul></ul></div>'
    + '<div class="guest-confirm-actions"><button id="guestConfirmDraw" type="button">ارسم</button><button id="guestConfirmEdit" type="button">عدّل</button></div>';
  local.after(confirmCard);
  let pendingDraw = null, askedFields = [];
  function hideConfirm() {
    confirmCard.hidden = true;
    pendingDraw = null;
  }
  function showConfirm(summary, draw) {
    pendingDraw = draw;
    askedFields = [];
    $('guestConfirmTitle').textContent = summary.title;
    $('guestConfirmQuestion').hidden = true;
    const rows = $('guestConfirmRows');
    rows.replaceChildren(...summary.rows.map(row => {
      const item = document.createElement('li');
      item.dataset.key = row.key;
      if (row.assumed) item.dataset.assumed = 'true';
      const label = document.createElement('strong');
      label.textContent = row.label + ': ';
      const value = document.createElement('span');
      value.textContent = row.value;
      item.append(label, value);
      if (row.assumed) {
        const tag = document.createElement('em');
        tag.className = 'guest-confirm-assumed';
        tag.textContent = 'افتراض';
        item.append(' ', tag);
      }
      if (row.note) {
        const note = document.createElement('small');
        note.textContent = row.note;
        item.append(note);
      }
      return item;
    }));
    rows.hidden = false;
    $('guestConfirmChoices').replaceChildren();
    $('guestConfirmChoices').hidden = true;
    // What the visitor asked for that this generator cannot draw yet, before drawing.
    const unsupported = $('guestConfirmUnsupported');
    unsupported.querySelector('ul').replaceChildren(...(summary.notDrawn || []).map(text => {
      const item = document.createElement('li');
      item.textContent = text;
      return item;
    }));
    unsupported.hidden = !(summary.notDrawn || []).length;
    $('guestConfirmDraw').hidden = false;
    confirmCard.dataset.mode = 'confirm';
    confirmCard.hidden = false;
    $('guestConfirmDraw').scrollIntoView({ block: 'nearest' });
    $('guestConfirmDraw').focus({ preventScroll: true });
  }
  function askQuestion(message, missing = []) {
    pendingDraw = null;
    askedFields = missing;
    $('guestConfirmTitle').textContent = 'نحتاج معلومة قبل الرسم';
    const question = $('guestConfirmQuestion');
    question.textContent = message + ' اكتبها في الوصف أو في الحقول.';
    question.hidden = false;
    $('guestConfirmRows').replaceChildren();
    $('guestConfirmRows').hidden = true;
    $('guestConfirmChoices').hidden = true;
    $('guestConfirmUnsupported').hidden = true;
    $('guestConfirmDraw').hidden = true;
    confirmCard.dataset.mode = 'question';
    confirmCard.hidden = false;
    $('guestConfirmEdit').scrollIntoView({ block: 'nearest' });
    $('guestConfirmEdit').focus({ preventScroll: true });
  }
  // The description and a field disagree: the visitor picks one value for each; nothing is preferred silently.
  A.guestFieldPreference = {};
  function askConflict(conflicts) {
    pendingDraw = null;
    askedFields = [];
    $('guestConfirmTitle').textContent = 'الوصف والحقول مختلفان';
    const question = $('guestConfirmQuestion');
    question.textContent = 'اختر القيمة المقصودة لكل بند، ثم نعرض عليك ما فهمناه قبل الرسم.';
    question.hidden = false;
    $('guestConfirmRows').hidden = true;
    $('guestConfirmUnsupported').hidden = true;
    $('guestConfirmDraw').hidden = true;
    const choices = $('guestConfirmChoices');
    choices.replaceChildren(...conflicts.map(conflict => {
      const item = document.createElement('li');
      item.dataset.key = conflict.key;
      const label = document.createElement('strong');
      label.textContent = conflict.label + ': ';
      item.append(label);
      for (const [choice, value, source] of [['text', conflict.text, 'من الوصف'], ['form', conflict.form, 'من الحقل']]) {
        const button = document.createElement('button');
        button.type = 'button';
        button.dataset.choice = choice;
        button.textContent = value + (conflict.unit || '') + ' ' + source;
        button.addEventListener('click', () => {
          A.guestFieldPreference = { ...A.guestFieldPreference, [conflict.key]: choice };
          hideConfirm();
          $('genText').click();
        });
        item.append(button);
      }
      return item;
    }));
    choices.hidden = false;
    confirmCard.dataset.mode = 'conflict';
    confirmCard.hidden = false;
    choices.querySelector('button')?.scrollIntoView({ block: 'nearest' });
    choices.querySelector('button')?.focus({ preventScroll: true });
  }
  A.confirmGuestApartment = (model, draw) => showConfirm(apartmentConfirmation(model), draw);
  $('guestConfirmDraw').addEventListener('click', () => {
    const draw = pendingDraw;
    hideConfirm();
    draw?.();
  });
  $('guestConfirmEdit').addEventListener('click', () => {
    const target = askedFields.includes('width') ? 'bldW' : askedFields.includes('depth') ? 'bldD' : askedFields.includes('levels') ? 'nFloors' : 'descText';
    hideConfirm();
    $(target).focus();
  });
  // A summary of an earlier description is never drawn after the visitor changes it.
  for (const id of ['descText','bldW','bldD','siteW','siteD','nFloors','bType'])
    $(id)?.addEventListener('input', () => { A.guestFieldPreference = {}; if (!confirmCard.hidden) hideConfirm(); });
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
    hideConfirm();
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
      // A missing value is a question in the card, not an error banner.
      if (result?.conflicts?.length) { askConflict(result.conflicts); return; }
      if (result?.question) { askQuestion(result.message, result.missing); return; }
      feedbackMessage(result?.message || 'تعذّر إنشاء التصميم. راجع وصف المبنى.');
      return;
    }
    hideConfirm();
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
    const freshExample = A.exportModel?.();
    if (freshExample?.meta?.acs_apartment?.source === 'synthetic_sample') referenceSample = JSON.stringify(freshExample);
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
