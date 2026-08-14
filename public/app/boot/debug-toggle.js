/* ============================================================
   public/app/boot/debug-toggle.js — مفتاح عرض عدّاد التشخيص
   مُستخرَج من public/index.html بـ tools/frontend_shell.js (F-09/F-11).
   كلاسيكي عمداً: يعمل قبل الوحدات ولا يعتمد على تحميلها.
   ============================================================ */
(function(){try{var dbg=/[?&]debug=1/.test(location.search)||localStorage.getItem('acs_debug')==='1';
        if(dbg){var e=document.getElementById('statCount'); if(e) e.style.display='';}}catch(e){}})();
