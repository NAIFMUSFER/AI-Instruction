/* ============================================================
   public/app/late-bindings.js
   سجلّ الربط المتأخّر. ترتيب تقييم وحدات ES يتبع رسم الاستيراد، فحافةٌ
   إلى وحدة لاحقة تقلب الترتيب وتفتح دورة. الأسماء هنا يقرؤها مقطع أسبق
   من مالكها، وكلّها تُقرأ داخل دوالّ لا وقت التقييم (مُقاس بالمحلّل
   النحويّ). المرور بهذا السجلّ يبقي الرسم لا دورياً وترتيب التقييم
   مطابقاً لترتيب الصفحة قبل التفكيك.
   ============================================================ */
/* اسمان من هذا السجلّ **يتبدّلان بعد النشر**: `model` و`lastBuilding` يعاد
   إسنادهما في workspace-ui-wiring.js عند كل تحميل نموذج (model=_next،
   lastBuilding=data). وسطرُ النشر Object.assign ينسخ **القيمة** لحظةَ
   التقييم — وهي null — فبقيت قراءاتُهما في pbr-bridge.js وscene.js ترى null
   إلى الأبد: verifyVisibleModel يعيد model_loaded:false مع شبكاتٍ محسوبة،
   وcanonicalTransformSnapshot يعيد available:false، وalignmentDiagnostics
   يعيد كائن «لا نموذج»، وapplyVisualMode لا يفعل شيئاً. قِيس في CI ومحلياً.

   الإصلاح لا يكسر عقد السجلّ (نشرٌ واحد، بلا كتابة أخرى، مفاتيح مختصرة):
   المالك ينشر — إلى جانب اللقطة — **مرجعاً حيّاً** modelRef/lastBuildingRef
   (دالّة تعيد الربط الحاليّ)، والمفتاحان القديمان صارا واصلَين يقرآن عبر
   المرجع الحيّ إن نُشر، وإلا فاللقطة. القرّاء لم يتغيّروا حرفاً. */
let _modelSnapshot;
let _lastBuildingSnapshot;

export const __ACS_LATE = Object.seal({
  archDoorConnectsConfirmed: undefined,
  archOpeningAnchor: undefined,
  camera: undefined,
  codeRequiredAllowed: undefined,
  compileArchitecture: undefined,
  compileCoordination: undefined,
  compileFls: undefined,
  compileMep: undefined,
  compileStructure: undefined,
  compileVisualScene: undefined,
  flsRenderItems: undefined,
  get lastBuilding() {
    return typeof this.lastBuildingRef === 'function'
      ? this.lastBuildingRef() : _lastBuildingSnapshot;
  },
  set lastBuilding(v) { _lastBuildingSnapshot = v; },
  lastBuildingRef: undefined,
  mepRenderItems: undefined,
  get model() {
    return typeof this.modelRef === 'function' ? this.modelRef() : _modelSnapshot;
  },
  set model(v) { _modelSnapshot = v; },
  modelRef: undefined,
  orbit: undefined,
  pqPlateRect: undefined,
  pqRackBlock: undefined,
  setSun: undefined,
  spaceCategories: undefined,
  structRenderItems: undefined,
});
