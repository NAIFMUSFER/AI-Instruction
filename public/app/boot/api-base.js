/* ============================================================
   public/app/boot/api-base.js — أصل واجهة الخادوم الوحيد
   مُستخرَج من public/index.html بـ tools/frontend_shell.js (F-09/F-11).
   كلاسيكي عمداً: يعمل قبل الوحدات ولا يعتمد على تحميلها.
   ============================================================ */
(function(){
  "use strict";
  var CONFIGURED_BASE = "https://acs-engine.onrender.com";   // ← الإعداد الوحيد

  function norm(u){ return String(u||"").trim().replace(/\/+$/,""); }

  var ACSAPI = {
    contract: "acs-api-base/1.0.0",
    configured: norm(CONFIGURED_BASE),
    override: "",                     // من حقل الإعدادات المتقدّمة، إن مُلئ
    /* المصدر الفعّال: التجاوز اليدوي إن وُجد، وإلا الإعداد. لا قيمة ثالثة. */
    base: function(){ return norm(this.override) || this.configured; },
    source: function(){ return norm(this.override) ? "manual-override" : "configured"; },
    url: function(path){
      var b = this.base();
      if(!b) return "";
      return b + (String(path||"").charAt(0)==="/" ? path : "/"+String(path||""));
    },
    host: function(){ try{ return new URL(this.base()).host; }catch(e){ return ""; } },
    scheme: function(){ try{ return new URL(this.base()).protocol.replace(":",""); }catch(e){ return ""; } }
  };
  window.ACS_API = ACSAPI;
  /* توافق خلفي: كان اسم الإعداد القديم ACS_SERVER. يبقى قراءةً فقط ومشتقّاً
     من نفس المصدر، حتى لا يتفرّع عنوانان في الصفحة. */
  try{
    Object.defineProperty(window, "ACS_SERVER", {
      get: function(){ return ACSAPI.base(); },
      set: function(v){ ACSAPI.override = norm(v); },
      configurable: true
    });
  }catch(e){ window.ACS_SERVER = ACSAPI.base(); }
})();

