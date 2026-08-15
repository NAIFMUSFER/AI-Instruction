/* ============================================================
   public/app/shared-state.js
   ارتباط الاستيراد في ES للقراءة فقط. الأسماء القليلة التي تُكتَب من
   وحدة غير مالكها تعيش هنا على كائن واحد، فيبقى معناها في النطاق
   الواحد الأصلي محفوظاً بلا إعادة كتابة للمنطق.
   ============================================================ */
export const __ACS_SHARED = Object.seal({
  ACS_EXTRA_RULESETS: undefined,
  ACS_INGEST_STORE: undefined,
  ACS_OCCUPANCY_STORE: undefined,
  DETAIL: undefined,
  LAST_REQUEST_TEXT: undefined,
  USE_TEX: undefined,
  /* KI-25/F-44 — لوحة عطل ما بعد 200، منفصلة عمداً عن acsErrorPanel:
     الخادم نجح وأجاب، والعطل في تحميل النموذج عندنا. الخلط بينهما يجعل
     المستخدم يتّهم الشبكة ويعيد المحاولة بلا نهاية. */
  acsApplyErrorPanel: undefined,
  acsErrorPanel: undefined,
  acsFetchJSON: undefined,
});
