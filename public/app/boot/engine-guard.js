/* ============================================================
   public/app/boot/engine-guard.js — تهيئة window.ACS وحارس تعذّر تحميل المحرّك
   Production entry is authenticated by /app/boot/auth-client.js. The historic
   name-only entry survives only on localhost for deterministic browser tests.
   ============================================================ */
  window.ACS = { ready:false, pending:null };
  (function(){
    function byId(i){return document.getElementById(i);}
    function enter(identity){
      identity=identity||{};
      var nm=String(identity.name||'عميل').trim()||'عميل';
      if(identity.mode==='local'){
        try{ localStorage.setItem('acs_user', nm); }catch(e){}
      }
      if(identity.session) window.ACS.authSession=identity.session;
      if(identity.project){
        window.ACS.project=identity.project;
        window.ACS.projectId=identity.project.id||null;
      }
      byId('login').classList.add('acs-hidden');
      byId('login').style.display='none';
      byId('left').classList.remove('acs-hidden');
      byId('left').style.display='flex';
      byId('who').textContent=nm;
      document.body.classList.add('acs-entered');
      if(window.ACS_AUTH&&window.ACS_AUTH.addLogout&&identity.mode==='supabase')
        window.ACS_AUTH.addLogout();
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
    function fallbackLocalOnly(){
      var b=byId('lgGo'); if(!b) return;
      var local=location.hostname==='127.0.0.1'||location.hostname==='localhost'||location.hostname==='::1';
      if(!local){
        b.disabled=true;
        var hint=b.parentElement&&b.parentElement.querySelector('.hint');
        if(hint) hint.textContent='تعذّر تحميل خدمة تسجيل الدخول. أعد تحميل الصفحة.';
        return;
      }
      b.addEventListener('click',function(){
        enter({mode:'local',name:(byId('lgName').value||'عميل').trim()});
      });
    }
    function loadAuth(){
      if(window.ACS_AUTH&&window.ACS_AUTH.init){ window.ACS_AUTH.init(enter); return; }
      var s=document.createElement('script');
      s.src='/app/boot/auth-client.js';
      s.async=false;
      s.addEventListener('load',function(){
        if(window.ACS_AUTH&&window.ACS_AUTH.init) window.ACS_AUTH.init(enter);
        else fallbackLocalOnly();
      });
      s.addEventListener('error',fallbackLocalOnly);
      document.head.appendChild(s);
    }
    function init(){
      initMobileNavigation();
      loadAuth();
      /* زرّ إعادة التحميل في تحذير المحرّك: كان onclick="location.reload()"
         في العلامة، وهو ميّت تحت script-src بلا 'unsafe-inline'. */
      var rl=byId('engineWarnReload');
      if(rl) rl.addEventListener('click', function(){ location.reload(); });
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
