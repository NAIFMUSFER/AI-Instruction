// Loaded only after the full guest renderer fails to initialize.
import { apartmentFromBrief, apartmentFromRevision } from '../core/local-apartment.mjs';
import { carryAutoRoof, roofRemovedByUser, withDefaultRoof } from '../core/roof.mjs';
import { withContextDetails } from '../core/context-details.mjs';
import { openGuestDraft } from '../trust/guest-draft-store.mjs';
import { openGuestFloorPlan } from './guest-floor-plan.mjs';
import { compileArchitecture, projectArchitecturalLevel } from '../core/disciplines.js';
import { drawGuestSoftwareView } from '../render/guest-software-view.mjs';

const $ = id => document.getElementById(id);
const scope = () => window.ACS_AUTH.storageScope();

function openGuestModelPlan(model,initialLevel=0) {
  const architecture=compileArchitecture(model);
  return openGuestFloorPlan({
    exportModel:()=>model,
    floorPlan2D:index=>projectArchitecturalLevel(architecture,index)
  },initialLevel);
}

function generated(raw, previous) {
  if (!raw) throw new Error('يدعم العرض المبسّط حالياً العمائر السكنية ذات الشقتين في كل دور. حدّد أبعاد المبنى وعدد الأدوار والشقق.');
  let model;
  if(previous && (previous.meta?.acs_roof || roofRemovedByUser(previous))) model=carryAutoRoof(previous,raw);
  else {
    const [result,,error]=withDefaultRoof(raw);
    if(error) throw new Error(error);
    model=result;
  }
  if(model.meta?.acs_roof?.omitted) throw new Error(model.meta.acs_roof.omitted);
  if(!previous){
    const [result,,error]=withContextDetails(model);
    if(error && error!=='CONTEXT_DETAILS_INPUT_UNSUPPORTED') throw new Error(error);
    model=result;
  }
  return model;
}

export async function openGuestSoftwareStudio() {
  if ($('guestSoftwareStudio') || !window.ACS_AUTH.guestProjectId) return;
  const css = document.createElement('link');
  css.rel='stylesheet'; css.href='/app/styles/guest-software-studio.css';
  document.head.append(css);
  // Load the reusable plan dialog before the first user opens it. The full
  // renderer may have stopped before any guest presentation styles loaded.
  if (!$('guestPlanStyle')) {
    const planCss=document.createElement('link');planCss.id='guestPlanStyle';
    planCss.rel='stylesheet';planCss.href=new URL('../styles/guest-floor-plan.css',import.meta.url).href;
    document.head.append(planCss);
  }
  const studio=document.createElement('main');
  studio.id='guestSoftwareStudio';studio.dir='rtl';studio.lang='ar';
  studio.innerHTML=`
    <header><div><b>AI Construction Studio</b><span>عرض مبسّط</span></div><a href="/?guest=1&amp;new=1" target="_blank" rel="noopener">مشروع جديد ↗</a></header>
    <section id="guestSoftwarePrompt"><h1>صف مبناك</h1><form id="guestSoftwareForm">
      <label for="descText">وصف العمارة السكنية</label><div id="guestSoftwareInput"></div>
      <p id="guestSoftwareError" role="alert" hidden></p>
      <button id="guestSoftwareSubmit" type="submit" disabled>إنشاء التصميم</button>
    </form></section>
    <section id="guestSoftwareResult" hidden>
      <div class="gs-heading"><div><h1>العمارة السكنية</h1><p id="guestSoftwareFacts"></p></div><button id="guestRevise" type="button">تعديل التصميم</button></div>
      <div id="guestSoftwareViewport"><canvas id="guestSoftwareCanvas" role="img" aria-label="مجسّم العمارة بحسب وصف المشروع"></canvas></div>
      <div class="gs-tools">
        <label>المشهد <select id="guestSoftwareView"><option value="exterior">الواجهة</option><option value="top">من أعلى</option><option value="cutaway">كشف الدور</option><option value="interior">من الداخل</option><option value="detail">تفاصيل المدخل</option></select></label>
        <label>الدور <select id="guestSoftwareLevel"></select></label>
        <button type="button" id="guestPlan">فتح المخطط</button>
        <button type="button" id="guestExport">تنزيل النموذج</button>
      </div></section>
    <p id="guestSaveStatus" role="status">جارٍ فتح المسودة…</p>
    <dialog id="guestRevisionDialog" aria-labelledby="guestRevisionTitle">
      <form id="guestRevisionForm"><h2 id="guestRevisionTitle">تعديل التصميم</h2><label for="guestRevisionText">وش تبي تغيّر في العمارة؟</label>
      <textarea id="guestRevisionText" required rows="3" placeholder="مثلاً: خلّ المدخل من الجنوب"></textarea>
      <p id="guestRevisionError" role="alert" hidden></p>
      <div><button id="guestApplyRevision" type="submit">تطبيق التعديل</button> <button id="guestCancelRevision" type="button">الاحتفاظ بالتصميم الحالي</button></div></form>
    </dialog>`;
  // Reuse the actual description field, without leaving duplicate ids in the document.
  const description = $('descText');
  description.disabled=false;
  description.required=true;
  description.rows=4;
  description.placeholder='أبغى عمارة سكنية، عرض المبنى ٢٠ متر وعمقه ٢٥ متر، ثلاثة أدوار شاملة الأرضي، وفي كل دور شقتين';
  studio.querySelector('#guestSoftwareInput').append(description);
  document.body.append(studio);
  $('acsGuestFallback')?.remove();
  document.body.classList.remove('acs-guest-fallback-active');
  document.body.classList.add('acs-guest-software');
  // Avoid re-showing the classic boot fallback after software recovery.
  window.ACS.guestWorkspaceReady=true;
  window.ACS.guestBootFailure=()=>{};
  let model=null, storage, saveQueue=Promise.resolve();
  const canvas=$('guestSoftwareCanvas'), view=$('guestSoftwareView'), level=$('guestSoftwareLevel');
  const saveStatus=$('guestSaveStatus'), revision=$('guestRevisionDialog');
  function redraw(){
    if(!model || $('guestSoftwareResult').hidden) return;
    try{drawGuestSoftwareView(canvas,model,{view:view.value,levelIndex:Number(level.value)});}
    catch{canvas.setAttribute('aria-label','تعذّر رسم المجسم. يمكن فتح مخطط الأدوار.');saveStatus.textContent='تعذّر رسم المجسّم. يمكنك فتح المخطط وتنزيل النموذج.';}
  }
  function present(next){
    model=next;
    const meta=model.meta?.acs_apartment;
    $('guestSoftwareFacts').textContent=meta ? `${meta.width_m} × ${meta.depth_m} م · ${meta.occupied_levels} أدوار · ${meta.units_total} شقق` : 'مشروع محلي محفوظ';
    $('guestRevise').hidden=!meta;
    $('guestSoftwarePrompt').hidden=true;
    $('guestSoftwareResult').hidden=false;
    level.replaceChildren(...model.levels.filter(row=>row.kind!=='roof').map(row=>{
      const option=document.createElement('option');option.value=String(row.index);option.textContent=row.name;return option;
    }));
    view.value='exterior';
    redraw();
  }
  async function save(next){
    if(!storage){saveStatus.textContent='تعذّر الحفظ على الجهاز. نزّل النموذج للاحتفاظ به.';return;}
    saveStatus.textContent='جارٍ الحفظ على هذا الجهاز…';
    try{await storage.save(next);if(model===next)saveStatus.textContent='محفوظ على هذا الجهاز';}
    catch(error){saveStatus.textContent=error.message==='DRAFT_CHANGED'?'تغيّرت المسودة في علامة تبويب أخرى. نزّل نموذجك قبل فتح النسخة الأخرى.':'تعذّر الحفظ على الجهاز. نزّل النموذج للاحتفاظ به.';}
  }
  function submit(text, editing) {
    const field=$(editing?'guestRevisionError':'guestSoftwareError');
    let result;
    try {
      if(!text.trim()) throw new Error('اكتب الطلب أولاً.');
      if(model?._authoring_locks && Object.keys(model._authoring_locks).length) throw new Error('لا يمكن تعديل التصميم مع وجود نطاق مقفول.');
      const raw=editing?apartmentFromRevision(text,model):apartmentFromBrief(text);
      const next=generated(raw,model);
      present(next); field.hidden=true;
      if(editing) revision.close();
      saveQueue=saveQueue.then(()=>save(next));
      result={ok:true,building:next};
    } catch(error){
      field.textContent=error.message;field.hidden=false;
      result={ok:false,message:error.message};
    }
    window.dispatchEvent(new CustomEvent('acs:local-generation',{detail:result}));
  }
  $('guestSoftwareForm').onsubmit=e=>{e.preventDefault();submit(description.value,false);};
  $('guestRevise').onclick=()=>{
    $('guestRevisionError').hidden=true;$('guestRevisionText').value='';
    revision.showModal();$('guestRevisionText').focus();
  };
  $('guestRevisionForm').onsubmit=e=>{e.preventDefault();submit($('guestRevisionText').value,true);};
  $('guestCancelRevision').onclick=()=>revision.close();
  view.onchange=redraw;
  level.onchange=()=>{view.value='cutaway';redraw();};
  $('guestPlan').onclick=()=>openGuestModelPlan(model,Number(level.value));
  $('guestExport').onclick=()=>{
    const url=URL.createObjectURL(new Blob([JSON.stringify(model,null,2)],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download='acs-guest-model.json';link.click();
    setTimeout(()=>URL.revokeObjectURL(url),2000);
  };
  new ResizeObserver(redraw).observe($('guestSoftwareViewport'));
  window.ACS.exportModel=()=>model;
  try {
    storage=await openGuestDraft(scope());
    if(storage.model) present(storage.model);
    saveStatus.textContent=storage.model?'استُعيد المشروع من هذا الجهاز':'مسودة محلية جديدة';
  } catch{saveStatus.textContent='تعذّرت قراءة التخزين المحلي. يمكنك التصميم وتنزيل النتيجة.';}
  $('guestSoftwareSubmit').disabled=false;
  studio.dataset.recovery='complete';
}
