/* ============================================================
   public/app/late-bindings.js
   سجلّ الربط المتأخّر. ترتيب تقييم وحدات ES يتبع رسم الاستيراد، فحافةٌ
   إلى وحدة لاحقة تقلب الترتيب وتفتح دورة. الأسماء هنا يقرؤها مقطع أسبق
   من مالكها، وكلّها تُقرأ داخل دوالّ لا وقت التقييم (مُقاس بالمحلّل
   النحويّ). المرور بهذا السجلّ يبقي الرسم لا دورياً وترتيب التقييم
   مطابقاً لترتيب الصفحة قبل التفكيك.
   ============================================================ */
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
  lastBuilding: undefined,
  mepRenderItems: undefined,
  model: undefined,
  orbit: undefined,
  pqPlateRect: undefined,
  pqRackBlock: undefined,
  setSun: undefined,
  spaceCategories: undefined,
  structRenderItems: undefined,
});
