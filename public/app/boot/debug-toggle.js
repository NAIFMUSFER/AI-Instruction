/* ============================================================
   public/app/boot/debug-toggle.js — مفتاح عرض عدّاد التشخيص
   مُستخرَج من public/index.html بـ tools/frontend_shell.js (F-09/F-11).
   كلاسيكي عمداً: يعمل قبل الوحدات ولا يعتمد على تحميلها.
   ============================================================ */
/* F-28: كان `e.style.display=''` — ومسحُ نمطٍ سطريّ لا يهزم قاعدة صنف.
   بعد هجرة F-09 صار الإخفاء من `.acs-u-13{display:none}` في app.css لا من
   `style="display:none"`، فبقي ?debug=1 بلا أي أثر: العدّاد يُحدَّث في
   ui/workspace-ui-wiring.js ولا يظهر أبداً. نزع الصنف هو ما يعمل فعلاً —
   وهو نفس ما فعله boot/engine-guard.js بشكل صحيح. */
(function(){try{var dbg=/[?&]debug=1/.test(location.search)||localStorage.getItem('acs_debug')==='1';
        if(dbg){var e=document.getElementById('statCount');
          if(e) e.classList.add('acs-debug-on');}}catch(e){}})();
