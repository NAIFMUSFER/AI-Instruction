/* ============================================================
   public/app/boot/engine-guard.js — تهيئة window.ACS وحارس تعذّر تحميل المحرّك
   مُستخرَج من public/index.html بـ tools/frontend_shell.js (F-09/F-11).
   كلاسيكي عمداً: يعمل قبل الوحدات ولا يعتمد على تحميلها.
   ============================================================ */
  window.ACS = { ready:false, pending:null };
  (function(){
    function byId(i){return document.getElementById(i);}
    function enter(){
      var nm = (byId('lgName').value||'عميل').trim();
      try{ localStorage.setItem('acs_user', nm); }catch(e){}
      byId('login').style.display='none';
      byId('left').style.display='flex';
      byId('who').textContent=nm;
      if(window.ACS.ready && window.ACS.showExample) window.ACS.showExample();
      else window.ACS.pending='example';
    }
    function init(){
      var b=byId('lgGo'); if(!b) return;
      b.addEventListener('click', enter);
      b.addEventListener('touchend', function(e){ e.preventDefault(); enter(); });
      ['lgName','lgEmail','lgProject'].forEach(function(id){
        var el=byId(id); if(el) el.addEventListener('keydown',function(e){ if(e.key==='Enter') enter(); });
      });
      try{ var u=localStorage.getItem('acs_user'); if(u) byId('lgName').value=u; }catch(e){}
      // تحذير إن لم يُحمَّل محرّك العرض خلال 12 ثانية
      setTimeout(function(){
        if(!window.ACS.ready){
          var w=byId('engineWarn'); if(w) w.style.display='block';
        }
      }, 12000);
    }
    if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', init);
    else init();
  })();

