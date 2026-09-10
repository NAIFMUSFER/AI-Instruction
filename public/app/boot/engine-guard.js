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
      /* الإخفاء الابتدائي صار صنفاً (style-src 'self' يمنع سمة style):
         الإظهار يزيل الصنف، ولا يكفي إسناد style.display لأن قاعدة المعرّف
         #left{display:flex} أقوى من صنف الإخفاء. */
      byId('login').classList.add('acs-hidden');
      byId('login').style.display='none';
      byId('left').classList.remove('acs-hidden');
      byId('left').style.display='flex';
      byId('who').textContent=nm;
      document.body.classList.add('acs-entered');
      if(window.innerWidth<=820 && window.ACS.setProjectPanelOpen)
        window.ACS.setProjectPanelOpen(true);
      if(window.ACS.ready && window.ACS.showExample) window.ACS.showExample();
      else window.ACS.pending='example';
    }
    // Navigation works even while the 3D engine is still loading.
    function initMobileNavigation(){
      var panel=byId('left'), toggle=byId('panelToggle');
      var tools=byId('camBar'), more=byId('mobileToolsToggle'), close=byId('projectPanelClose');
      if(!panel || !toggle || !tools || !more || !close) return;
      function mobile(){return window.innerWidth<=820;}
      function projectOpen(open){
        if(open) toolsOpen(false);
        panel.classList.toggle('open',!!open);
        toggle.setAttribute('aria-expanded',String(!!open));
        panel.inert=mobile() && !open;
      }
      function toolsOpen(open){
        if(open) projectOpen(false);
        tools.classList.toggle('mobile-open',!!open);
        more.setAttribute('aria-expanded',String(!!open));
        tools.inert=mobile() && !open;
      }
      window.ACS.setProjectPanelOpen=projectOpen;
      toggle.addEventListener('click',function(){projectOpen(!panel.classList.contains('open'));});
      close.addEventListener('click',function(){projectOpen(false);toggle.focus();});
      more.addEventListener('click',function(){
        var open=!tools.classList.contains('mobile-open');
        toolsOpen(open);
        if(open){var first=tools.querySelector('button');if(first) first.focus();}
      });
      tools.addEventListener('click',function(e){
        var button=e.target.closest('button');
        if(!mobile() || !button) return;
        toolsOpen(false);
        if(button.id==='cbClip') projectOpen(true);
        else more.focus();
      });
      document.addEventListener('keydown',function(e){
        if(e.key!=='Escape' || !mobile()) return;
        if(tools.classList.contains('mobile-open')){
          toolsOpen(false);more.focus();
        }else if(panel.classList.contains('open')){
          projectOpen(false);toggle.focus();
        }
      });
      var wasMobile=mobile();
      window.addEventListener('resize',function(){
        if(mobile()===wasMobile) return;
        wasMobile=mobile();
        toolsOpen(false);
        projectOpen(panel.classList.contains('open'));
      });
      toolsOpen(false);projectOpen(false);
    }
    function init(){
      var b=byId('lgGo'); if(!b) return;
      initMobileNavigation();
      b.addEventListener('click', enter);
      b.addEventListener('touchend', function(e){ e.preventDefault(); enter(); });
      ['lgName','lgEmail','lgProject'].forEach(function(id){
        var el=byId(id); if(el) el.addEventListener('keydown',function(e){ if(e.key==='Enter') enter(); });
      });
      try{ var u=localStorage.getItem('acs_user'); if(u) byId('lgName').value=u; }catch(e){}
      /* زرّ إعادة التحميل في تحذير المحرّك: كان onclick="location.reload()"
         في العلامة، وهو ميّت تحت script-src بلا 'unsafe-inline' — أي أن المخرج
         الوحيد المعروض للمستخدم حين يتعذّر المحرّك كان لا يعمل. */
      var rl=byId('engineWarnReload');
      if(rl) rl.addEventListener('click', function(){ location.reload(); });
      // تحذير إن لم يُحمَّل محرّك العرض خلال 12 ثانية
      setTimeout(function(){
        if(!window.ACS.ready){
          var w=byId('engineWarn');
          if(w){ w.classList.remove('acs-hidden'); w.style.display='block'; }
        }
      }, 12000);
    }
    if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', init);
    else init();
  })();
