/* Public, local-only workspace. No auth identity, provider call or cloud upload. */
const A = window.ACS;
const $ = id => document.getElementById(id);

async function openGuestWorkspace() {
  if (!A?.guest || $('acsGuestBanner')) return;
  document.body.classList.add('acs-guest');
  const banner = document.createElement('aside');
  banner.id = 'acsGuestBanner';
  banner.setAttribute('aria-label', 'تجربة الاستوديو بدون تسجيل');
  banner.innerHTML = '<div><strong>جرّب الاستوديو بدون تسجيل</strong><p id="acsGuestStatus" role="status">نماذج تجريبية وتعديلات محلية على هذا الجهاز. ليست مخططات تنفيذية.</p></div>'
    + '<div class="guest-actions"><button id="guestExample" type="button">عمارة تجريبية</button>'
    + '<button id="guestWarehouse" type="button">مستودع تجريبي</button>'
    + '<button id="guestCreate" type="button">إنشاء محلي</button>'
    + '<a href="/?signin=1" id="guestSignin">تسجيل الدخول للذكاء والحفظ السحابي</a></div>';
  document.body.append(banner);
  let interactionEpoch=0;
  const userIntent=event=>{
    if(event.target?.closest?.('#left,#acsGuestBanner'))interactionEpoch++;
  };
  for(const event of ['click','input','change'])document.addEventListener(event,userIntent,true);
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
  if (sub) sub.textContent = 'نماذج تجريبية أو توليد محلي تقريبي. محفوظة على جهازك فقط.';
  const firstNote = document.querySelector('#acsPanelMake > .note');
  if (firstNote) firstNote.textContent = 'جرّب نموذجًا جاهزًا أو اكتب وصفًا للتوليد المحلي التقريبي. استيراد JSON وDXF يبقى على جهازك.';

  function sample(kind) {
    interactionEpoch++;
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
  local.addEventListener('click', () => notice('توليد محلي تقريبي من وصفك؛ راجع الأبعاد والعناصر. لا يستخدم الذكاء ولا يُرسل بيانات.'));
  upload.addEventListener('change', () => notice('يُقرأ ملفك محليًا على هذا الجهاز فقط.'));
  A.guestWorkspace = { contract: 'acs-local-guest/1', localOnly: true, storageScope: A_AUTH_SCOPE(), sample };
  // One bounded recovery owner. A late read can never replace a subsequent
  // sample, input, import or local-generation action from this visitor.
  let timer;
  try {
    const recovered = await Promise.race([
      A.persistence.recover(),
      new Promise(resolve=>{timer=setTimeout(()=>resolve(null),1500);}),
    ]);
    if(interactionEpoch!==0)return;
    if (recovered?.ok && recovered.project?.model) {
      A.setModel(recovered.project.model);
      notice('استُعيد آخر عمل للضيف من هذا الجهاز. لم يُفتح أي مشروع حساب خاص.');
      if (A.setProjectPanelOpen && innerWidth <= 820) A.setProjectPanelOpen(false);
      return;
    }
    sample('residential');
    if(!recovered)notice('فُتح نموذج تجريبي؛ تعذّرت استعادة الحفظ المحلي في الوقت المحدد. يمكنك استعادة ملف JSON يدويًا.');
  } catch (e) {
    if(interactionEpoch===0){sample('residential');notice('التخزين المحلي غير متاح؛ يمكنك التجربة وتنزيل JSON للاحتفاظ بعملك.');}
  } finally {
    clearTimeout(timer);banner.dataset.recovery='complete';
    for(const event of ['click','input','change'])document.removeEventListener(event,userIntent,true);
  }
}
function A_AUTH_SCOPE() { return window.ACS_AUTH.storageScope(); }
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', openGuestWorkspace);
else openGuestWorkspace();
