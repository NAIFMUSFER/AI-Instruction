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
  acsErrorPanel: undefined,
  acsFetchJSON: undefined,
});
