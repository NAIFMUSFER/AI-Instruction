/* ============================================================
   public/app/boot/build-info.js — أصل البناء + مسار التنزيل الاحتياطي
   مُستخرَج من public/index.html بـ tools/frontend_shell.js (F-09/F-11).
   كلاسيكي عمداً: يعمل قبل الوحدات ولا يعتمد على تحميلها.
   ============================================================ */
/* ===========================================================================
   F-08 — هوية البناء المشحون. القيم أدناه رموز نائبة يستبدلها مسار البناء
   (tools/netlify-build.sh عبر tools/write_build_info.py). الرمز الذي لم
   يُستبدَل يُبلَّغ null لا قيمة مختلَقة: بناء بلا إسناد يجب أن يُرى بلا إسناد،
   لا أن يبدو موثَّقاً كذباً. لا شبكة، لا تخزين، لا أثر جانبي هنا.
   =========================================================================== */
(function(){
  "use strict";
  var RAW = {
    git_sha:          "__ACS_GIT_SHA__",
    built_at:         "__ACS_BUILT_AT__",
    frontend_version: "__ACS_FRONTEND_VERSION__"
  };
  /* الرمز النائب يُبنى تركيباً حتى لا يطابق نفسه نصّاً في هذا الملفّ */
  function unsubstituted(v, name){
    var token = "__" + "ACS_" + name + "__";
    return (typeof v !== "string") || v === "" || v === token;
  }
  var INFO = {
    contract: "acs-build-info/1.0.0",
    git_sha:          unsubstituted(RAW.git_sha, "GIT_SHA") ? null : RAW.git_sha,
    built_at:         unsubstituted(RAW.built_at, "BUILT_AT") ? null : RAW.built_at,
    frontend_version: unsubstituted(RAW.frontend_version, "FRONTEND_VERSION")
                        ? null : RAW.frontend_version,
    fabricated: false
  };
  INFO.substituted = !(INFO.git_sha === null && INFO.built_at === null
                       && INFO.frontend_version === null);
  INFO.provenance = INFO.substituted ? "BUILD_SUBSTITUTED" : "UNPROVENANCED";
  INFO.short = INFO.git_sha ? String(INFO.git_sha).slice(0, 12) : null;
  INFO.label = INFO.substituted
    ? ((INFO.frontend_version || "?") + " · " + (INFO.short || "?")
       + " · " + (INFO.built_at || "?"))
    : "UNPROVENANCED BUILD — no build step substituted the identity tokens";
  window.ACS_BUILD_INFO = INFO;

  /* أخطاء الإقلاع تُسجَّل من أوّل لحظة: إن مات سكربت الوحدة (Three.js غائب
     مثلاً) فهذه هي الحالة التي يحتاج فيها المستخدم التشخيص أكثر ما يحتاجه. */
  var BOOT_ERRORS = [];
  window.ACS_BOOT_ERRORS = BOOT_ERRORS;
  window.addEventListener("error", function(e){
    if(BOOT_ERRORS.length < 20)
      BOOT_ERRORS.push({ message: String((e && e.message) || e).slice(0,200),
        source: String((e && e.filename) || "").slice(0,200),
        line: (e && e.lineno) || null });
  }, true);

  function paintBuildId(){
    try{
      var el = document.getElementById("acsBuildId");
      if(!el) return;
      el.textContent = INFO.label;
      if(!INFO.substituted) el.setAttribute("data-unprovenanced","1");
    }catch(e){}
  }
  /* احتياطي التشخيص: إن لم يُقلع سكربت الوحدة فلا وجود لـ
     window.ACS.captureRenderFailure، ويبقى الزرّ ميّتاً في اللحظة التي يهمّ
     فيها أكثر من غيرها. هذا المعالِج الكلاسيكي ينزّل ما هو معروف يقيناً —
     هويّة البناء وأخطاء الإقلاع — ولا يخمّن رقماً ولا يرسل شيئاً إلى أي جهة.
     يستبدله معالِج الوحدة الكامل حالما يُقلع. */
  function fallbackDiagnostics(){
    var payload = {
      contract: "acs-render-failure/1.0.0",
      capture_source: "CLASSIC_FALLBACK_MODULE_NOT_EXECUTED",
      uploaded: false, upload_target: null, transmits_anything: false,
      build_info: INFO,
      application_module_executed: !!(window.ACS && window.ACS.ready),
      boot_errors: BOOT_ERRORS,
      user_agent: (typeof navigator !== "undefined")
        ? navigator.userAgent : null,
      note: "the application module did not execute, so no renderer, scene or "
          + "pixel measurement exists. Nothing here is guessed."
    };
    var text = JSON.stringify(payload, null, 2);
    try{
      var url = URL.createObjectURL(new Blob([text],
        { type: "application/json" }));
      var a = document.createElement("a");
      a.href = url; a.download = "acs-render-diagnostics-boot-failure.json";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function(){ try{ URL.revokeObjectURL(url); }catch(e){} },
        30000);
    }catch(e){}
    var st = document.getElementById("acsDiagState");
    if(st) st.textContent = "لم يُقلع سكربت التطبيق — نُزِّل تشخيص الإقلاع "
      + "المتاح فقط. لم يُرسَل إلى أي جهة.";
    return payload;
  }
  function wireFallback(){
    paintBuildId();
    var btn = document.getElementById("acsDiagBtn");
    if(btn && !btn.onclick) btn.onclick = fallbackDiagnostics;
  }
  if(document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", wireFallback);
  else wireFallback();
})();

