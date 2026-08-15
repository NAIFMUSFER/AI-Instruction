/* ============================================================================
   public/app/ui/panels-entry.js — نقطة الدخول إلى لوحات المراحل ٦…٩٫٢.

   العطل الذي يغلقه هذا الملفّ (F-27)
   ---------------------------------
   لوحات مساحة العمل والعرض وتبادل BIM والتوثيق وجودة العرض والتفصيل المعماري
   مشحونة كاملةً: العلامات في public/index.html (‏#acsWorkspace و#rvPanel
   و#bxPanel و#dcPanel و#pqPanel و#adPanel)، والمنطق في وحدات
   public/app/generated/‎. لكنّ لا سطر واحد في الشيفرة المشحونة كان يستدعي
   ‎WS.init()‎ ولا ‎bind()‎ ولا ‎open()‎ لأيٍّ منها — الاستدعاء الوحيد في
   المستودع كلّه كان داخل tests/‎. النتيجة المقيسة:

     • ‎#acsWorkspace‎ محكوم بـ‎display:none‎ حتى يضاف الصنف ‎.on‎، ولا أحد يضيفه،
       فالشجرة والمفتّش ومركز المسائل وسجلّ المراجعات والتراجع/الإعادة وتبديل
       اللغة غير قابلة للوصول من الواجهة إطلاقاً.
     • ‎bind()‎ هي التي تركّب اختصارات لوحة المفاتيح (B/E/I/F و Ctrl+Z) وحارس
       ‎beforeunload‎ للعمل غير المحفوظ — فلم يكن أيٌّ منها مركّباً، والمستخدم
       يفقد تعديلاته بإغلاق التبويب بلا أي تنبيه.
     • أزرار شريط ‎.ws-top‎ الإحدى عشرة موجودة في العلامات وبلا أي معالِج.

   لماذا لم يظهر هذا في الاختبارات: الملفّ الوحيد الذي كان سيكشفه هو
   tests/production/verify_live_browser.js — وهو يبحث عن ‎#wsBtnTree‎ وإخوته في
   الصفحة الحيّة، ولم يُشغَّل قطّ (‎NOT VERIFIED — EXTERNAL ENVIRONMENT
   REQUIRED‎). كل الاختبارات الأخرى تستدعي ‎init()‎ بنفسها، فتُثبت أن اللوحة
   تعمل **إن استُدعيت**، لا أن أحداً يستدعيها.

   قواعد هذا الملفّ
   ---------------
   • لا سلوك جديد: كل ما هنا استدعاءٌ لدوالّ موجودة سلفاً بعقودها المختبَرة.
   • لا معالِج داخل العلامات ولا نمط سطريّ: سياسة CSP المنشورة
     (‎script-src 'self'‎ و‎style-src 'self'‎) تمنع الاثنين، والتوصيل هنا
     بـaddEventListener وبأصناف معرّفة في app/styles/app.css وحدها.
   • فشل لوحة واحدة لا يُسقط البقيّة ولا حلقة العرض: كل استدعاء داخل try.
   ========================================================================= */

const $ = (id) => (typeof document === 'undefined'
  ? null : document.getElementById(id));

/* اللوحات الخمس المولَّدة: كلٌّ منها يكشف كائن panel فيه init/open/close. */
const GENERATED_PANELS = [
  { button: 'acsOpenRender', ns: 'render', label: 'لوحة العرض' },
  { button: 'acsOpenBim', ns: 'bim', label: 'تبادل BIM' },
  { button: 'acsOpenDocs', ns: 'docs', label: 'التوثيق' },
  { button: 'acsOpenPbr', ns: 'pbr', label: 'جودة العرض' },
  { button: 'acsOpenDetail', ns: 'archdetail', label: 'التفصيل المعماري' },
];

function panelOf(ns) {
  const api = (typeof window !== 'undefined' && window.ACS) ? window.ACS[ns] : null;
  return (api && api.panel) ? api.panel : null;
}

/* المشروع الذي تعمل عليه اللوحات. المبنى المعروض حالياً هو المصدر: لا نموذج
   ثانٍ ولا نسخة موازية — auCreateProject هي الطريق الوحيد المعلن لبناء مشروع. */
function currentProject() {
  const ACS = (typeof window !== 'undefined') ? window.ACS : null;
  if (!ACS) return null;
  try {
    const building = ACS.exportModel ? ACS.exportModel() : null;
    if (!building) return null;
    if (building.buildings || building.revisions) return building;   // مشروع سلفاً
    return ACS.createProject ? ACS.createProject(building) : null;
  } catch (e) {
    return null;
  }
}

/* لا مشروع = لا لوحة فارغة بلا تفسير: الرسالة تقول ما ينقص وماذا يفعل. */
function requireProject(labelAr) {
  const project = currentProject();
  if (project) return project;
  const status = $('acsPanelsState');
  if (status) {
    status.textContent = 'لا يوجد نموذج بعد — ولّد مبنى أوّلاً ثم افتح '
      + labelAr + '.';
  }
  return null;
}

function announce(text) {
  const status = $('acsPanelsState');
  if (status) status.textContent = text;
}

/* ------------------------------------------------------- مساحة العمل - */
let workspaceReady = false;

function openWorkspace() {
  const ACS = (typeof window !== 'undefined') ? window.ACS : null;
  const WS = ACS ? ACS.workspace : null;
  if (!WS) { announce('طبقة مساحة العمل غير محمّلة.'); return false; }
  const project = requireProject('مساحة العمل');
  if (!project) return false;
  try {
    if (!workspaceReady) {
      // init يركّب أزرار الشريط واختصارات المفاتيح وحارس beforeUnload مرّة واحدة.
      WS.init(project);
      workspaceReady = true;
    } else if (WS.attach) {
      WS.attach(project);
    }
    WS.open();
    announce('فُتحت مساحة العمل.');
    return true;
  } catch (e) {
    announce('تعذّر فتح مساحة العمل: ' + String((e && e.message) || e).slice(0, 80));
    return false;
  }
}

/* ------------------------------------------------------ اللوحات الخمس - */
const inited = Object.create(null);

function openGenerated(entry) {
  const panel = panelOf(entry.ns);
  if (!panel) { announce('طبقة «' + entry.label + '» غير محمّلة.'); return false; }
  const project = requireProject(entry.label);
  if (!project) return false;
  try {
    if (!inited[entry.ns]) {
      if (panel.init) panel.init();
      inited[entry.ns] = true;
    }
    // لوحة العرض وحدها تحتاج المشهد الحيّ إضافةً إلى المشروع.
    if (entry.ns === 'render' && panel.attach) {
      panel.attach(project, (window.ACS && window.ACS.scene) || null, null);
    } else if (panel.attach) {
      panel.attach(project);
    }
    panel.open();
    announce('فُتحت «' + entry.label + '».');
    return true;
  } catch (e) {
    announce('تعذّر فتح «' + entry.label + '»: '
      + String((e && e.message) || e).slice(0, 80));
    return false;
  }
}

/* ------------------------------------------------------------- التوصيل - */
function wire() {
  if (typeof document === 'undefined') return false;
  const ws = $('acsOpenWorkspace');
  if (ws) ws.addEventListener('click', openWorkspace);
  for (const entry of GENERATED_PANELS) {
    const btn = $(entry.button);
    if (btn) btn.addEventListener('click', () => openGenerated(entry));
  }
  // Escape يغلق أي لوحة مفتوحة — سلوك الحوار المتوقّع، وكل لوحة تملك close().
  window.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Escape') return;
    for (const entry of GENERATED_PANELS) {
      const panel = panelOf(entry.ns);
      try { if (panel && panel.close) panel.close(); } catch (e) { /* لا تُسقط البقيّة */ }
    }
  });
  return true;
}

try {
  wire();
} catch (e) {
  /* لا شيء هنا يبرّر إسقاط بقيّة التطبيق. */
}

/* واجهة مطوّر صريحة — نفس المسارات التي تسلكها الأزرار، بلا طريق ثانٍ. */
if (typeof window !== 'undefined') {
  window.ACS = window.ACS || {};
  window.ACS.openWorkspace = openWorkspace;
  window.ACS.openPanel = (ns) => {
    const entry = GENERATED_PANELS.filter((p) => p.ns === ns)[0];
    return entry ? openGenerated(entry) : false;
  };
  window.ACS.panelEntryPoints = () => ({
    workspace: 'acsOpenWorkspace',
    panels: GENERATED_PANELS.map((p) => ({ ns: p.ns, button: p.button })),
  });
}

export { openWorkspace, openGenerated, currentProject, GENERATED_PANELS, wire };
