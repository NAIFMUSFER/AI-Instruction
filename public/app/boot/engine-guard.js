/* ============================================================
   public/app/boot/engine-guard.js — production auth + ACS boot guard.
   Supabase credentials flow only through the pinned ACS backend. Local name-only
   entry is retained on localhost solely for deterministic development tests.
   ============================================================ */
(function(){
  "use strict";
  var SESSION_KEY="acs_supabase_session_v1", PROJECT_KEY="acs_project_v1";
  var memorySession=null, refreshFlight=null, sessionEpoch=0, busy=false, mode="signin";
  var onEntry=null, restoredSession=null;
  function byId(id){return document.getElementById(id);}
  function localHost(){return ["127.0.0.1","localhost","::1","[::1]"].indexOf(location.hostname)>=0;}
  function api(path){
    // Auth always uses the configured origin. A model-server override must not
    // redirect passwords or refresh credentials to a different origin.
    var a=window.ACS_API;
    return a && typeof a.configured==="string" ? a.configured.replace(/\/+$/,"")+path : "";
  }
  function error(message,code,status){var e=new Error(message);e.code=code;e.status=status||0;return e;}
  function setStatus(text,bad){var e=byId("acsAuthStatus");if(!e)return;e.textContent=text||"";e.setAttribute("role",bad?"alert":"status");e.classList.toggle("bad",!!bad);}
  function setBusy(value){
    busy=!!value;
    ["lgGo","lgSignup"].forEach(function(id){var e=byId(id);if(e)e.disabled=busy;});
    var form=byId("acsAuthForm");if(form)form.setAttribute("aria-busy",String(busy));
  }
  function setMode(next){
    mode=next;
    var local=localHost(), signup=next==="signup", project=next==="project", resume=next==="resume";
    var name=byId("acsAuthNameField"), p=byId("acsAuthProjectField"), cred=byId("acsAuthCredentials");
    if(name)name.hidden=!local&&!signup;
    if(p)p.hidden=!local&&!project;
    if(cred)cred.hidden=project||resume;
    var title=byId("acsAuthTitle");if(title)title.textContent=resume?"العودة إلى مشروعك":project?"أنشئ مشروعك الأول":signup?"حساب جديد":"تسجيل الدخول";
    var go=byId("lgGo");if(go)go.textContent=resume?"إعادة المحاولة":project?"فتح المشروع ▸":signup?"إنشاء الحساب ▸":"تسجيل الدخول ▸";
    var back=byId("lgSignup");if(back)back.textContent=project||resume?"استخدام حساب آخر":signup?"لدي حساب — تسجيل الدخول":"إنشاء حساب جديد";
    var pw=byId("lgPassword");if(pw){pw.autocomplete=signup?"new-password":"current-password";pw.placeholder=signup?"8 أحرف على الأقل":"كلمة المرور";}
  }
  async function acsFetchJSON(path,body,token){
    var url=api(path);if(!url)throw error("تعذّر الاتصال بخدمة الدخول.","AUTH_NOT_CONFIGURED",503);
    var headers={"content-type":"application/json","accept":"application/json"};
    if(token)headers.authorization="Bearer "+token;
    var controller=new AbortController(), timer=setTimeout(function(){controller.abort();},15000);
    try{
      var res=await fetch(url,{method:"POST",headers:headers,body:JSON.stringify(body||{}),cache:"no-store",credentials:"omit",redirect:"error",signal:controller.signal});
      var data;try{data=JSON.parse(await res.text());}catch(e){throw error("استجابة خدمة الدخول غير مكتملة. حاول مجددًا.","AUTH_INVALID_RESPONSE",502);}
      if(!res.ok){
        var detail=data&&data.error;
        throw error(detail&&detail.message||"تعذّر إكمال العملية. حاول مجددًا.",detail&&detail.code||"AUTH_FAILED",res.status);
      }
      if(!data||typeof data!=="object"||Array.isArray(data))throw error("استجابة خدمة الدخول غير صالحة.","AUTH_INVALID_RESPONSE",502);
      return data;
    }catch(e){
      if(e&&e.code)throw e;
      throw error("تعذّر الاتصال. تحقق من الإنترنت وحاول مجددًا؛ لم تُحذف جلستك.","AUTH_NETWORK",0);
    }finally{clearTimeout(timer);}
  }
  function loadSession(){
    if(memorySession)return memorySession;
    try{var s=JSON.parse(localStorage.getItem(SESSION_KEY)||"null");
      if(s&&typeof s.access_token==="string"&&s.access_token&&typeof s.refresh_token==="string"&&s.refresh_token&&s.user&&typeof s.user.id==="string"&&s.user.id)return s;
    }catch(e){}return null;
  }
  function saveSession(s){
    if(!s||typeof s.access_token!=="string"||!s.access_token||typeof s.refresh_token!=="string"||!s.refresh_token||!s.user||typeof s.user.id!=="string"||!s.user.id)return null;
    var old=loadSession();
    if(!old||old.user.id!==s.user.id){try{localStorage.removeItem(PROJECT_KEY);}catch(e){}}
    var expires=Number(s.expires_at||0);
    if(!expires&&Number(s.expires_in)>0)expires=Math.floor(Date.now()/1000)+Number(s.expires_in);
    var slim={access_token:s.access_token,refresh_token:s.refresh_token,expires_at:Number.isFinite(expires)?expires:0,
      user:{id:s.user.id,email:s.user.email||"",user_metadata:{name:s.user.user_metadata&&s.user.user_metadata.name||""}}};
    memorySession=slim;
    try{localStorage.setItem(SESSION_KEY,JSON.stringify(slim));}catch(e){}
    return slim;
  }
  function clearSession(){
    sessionEpoch++;memorySession=null;restoredSession=null;
    if(window.ACS){delete window.ACS.authSession;delete window.ACS.project;window.ACS.projectId=null;}
    try{localStorage.removeItem(SESSION_KEY);localStorage.removeItem(PROJECT_KEY);localStorage.removeItem("acs_user");}catch(e){}
  }
  async function freshSession(){
    var s=loadSession();if(!s)return null;
    if(Number(s.expires_at)>Math.floor(Date.now()/1000)+60)return s;
    if(refreshFlight)return refreshFlight;
    var epoch=sessionEpoch, token=s.refresh_token;
    refreshFlight=(async function(){
      try{
        var next=await acsFetchJSON("/v1/auth/refresh",{refresh_token:token});
        if(epoch!==sessionEpoch)return null;
        var current=loadSession();
        if(!current||current.refresh_token!==token)return current;
        var valid=saveSession(next);
        if(!valid)throw error("تعذّر تجديد الجلسة. حاول مجددًا.","AUTH_INVALID_RESPONSE",502);
        return valid;
      }catch(e){
        if(epoch!==sessionEpoch)return null;
        if(e.status===400||e.status===401||e.status===403){
          // Another tab may already have rotated the token. Do not erase its session.
          var current=loadSession();
          if(current&&current.refresh_token!==token)return current;
          clearSession();return null;
        }
        throw e;
      }finally{refreshFlight=null;}
    })();
    return refreshFlight;
  }
  async function bootstrapProject(session,name){
    var out=await acsFetchJSON("/v1/auth/bootstrap-project",{name:String(name||"").trim()},session.access_token);
    if(!out.project||typeof out.project.id!=="string"||!out.project.id)throw error("لم يتم فتح المشروع. حاول مجددًا.","AUTH_INVALID_RESPONSE",502);
    try{localStorage.setItem(PROJECT_KEY,JSON.stringify(out.project));}catch(e){}
    return out;
  }
  function values(){return {name:byId("lgName").value.trim(),email:byId("lgEmail").value.trim(),password:byId("lgPassword").value,project:byId("lgProject").value.trim()};}
  function clearPassword(){var pw=byId("lgPassword");if(pw){pw.value="";pw.type="password";}var t=byId("acsPasswordToggle");if(t){t.textContent="إظهار";t.setAttribute("aria-label","إظهار كلمة المرور");t.setAttribute("aria-pressed","false");}}
  async function finishSession(session,projectName,name){
    try{
      var boot=await bootstrapProject(session,projectName);
      if(!loadSession()||loadSession().user.id!==session.user.id)return;
      restoredSession=null;clearPassword();setStatus("",false);
      onEntry({mode:"supabase",name:name||session.user.user_metadata&&session.user.user_metadata.name||session.user.email||"عميل",session:session,project:boot.project,user:boot.user});
    }catch(e){
      if(e.code==="PROJECT_NAME_REQUIRED"){
        restoredSession=session;clearPassword();setMode("project");setStatus("تم تسجيل الدخول. سمّ مشروعك لتبدأ.",false);byId("lgProject").focus();return;
      }
      throw e;
    }
  }
  async function submit(){
    if(busy)return;
    if(mode==="resume"){await restore();return;}
    var v=values();
    if(localHost()&&mode!=="signup"&&!v.email&&!v.password){onEntry({mode:"local",name:v.name||"عميل",project:{name:v.project||"Local test project"}});return;}
    if(mode==="project"){
      if(!v.project){setStatus("اكتب اسم مشروعك.",true);byId("lgProject").focus();return;}
      setBusy(true);setStatus("جارٍ فتح المشروع…",false);
      try{var current=await freshSession();if(!current){setMode("signin");throw error("انتهت الجلسة. سجّل الدخول مجددًا.","AUTH_REQUIRED",401);}await finishSession(current,v.project);}
      catch(e){setStatus(e.message,true);}finally{setBusy(false);}return;
    }
    if(!v.email||!byId("lgEmail").validity.valid||!v.password){setStatus("أدخل بريدًا إلكترونيًا صحيحًا وكلمة المرور.",true);return;}
    if(mode==="signup"&&v.password.length<8){setStatus("كلمة المرور يجب أن تكون 8 أحرف على الأقل.",true);return;}
    setBusy(true);setStatus(mode==="signup"?"جارٍ إنشاء الحساب…":"جارٍ تسجيل الدخول…",false);
    var epoch=++sessionEpoch;
    try{
      var raw=await acsFetchJSON(mode==="signup"?"/v1/auth/signup":"/v1/auth/signin",{email:v.email,password:v.password,name:v.name});
      if(epoch!==sessionEpoch)return;
      var session=saveSession(raw);
      if(!session){
        if(mode!=="signup"||!raw.user)throw error("لم تُرجع خدمة الدخول جلسة صالحة.","AUTH_INVALID_RESPONSE",502);
        clearPassword();setMode("signin");setStatus("تحقق من رسالة التأكيد في بريدك، ثم ارجع لتسجيل الدخول.",false);return;
      }
      clearPassword();await finishSession(session,v.project,v.name);
    }catch(e){if(loadSession()&&(e.status===0||e.status>=500))setMode("resume");setStatus(e.message||"تعذّر تسجيل الدخول.",true);}finally{setBusy(false);}
  }
  async function restore(){
    if(!loadSession()){setMode("signin");return false;}
    setBusy(true);setStatus("جارٍ استعادة جلستك…",false);
    try{
      var session=await freshSession();
      if(!session){setMode("signin");setStatus("انتهت الجلسة. سجّل الدخول مجددًا.",false);return false;}
      await finishSession(session,"");return true;
    }catch(e){
      if(e.status===401||e.status===403){clearSession();setMode("signin");}
      else setMode("resume");
      setStatus(e.message||"تعذّر فتح المشروع. حاول مجددًا.",true);return false;
    }finally{setBusy(false);}
  }
  function addLogout(){
    if(byId("acsLogout"))return;
    var header=document.querySelector("#left header");if(!header)return;
    var b=document.createElement("button");b.id="acsLogout";b.type="button";b.className="ghost";b.textContent="خروج";
    b.addEventListener("click",async function(){
      if(b.disabled)return;b.disabled=true;
      var s=loadSession();clearSession();
      // Hide the current project immediately, even when the network is offline.
      document.body.classList.remove("acs-entered");
      byId("login").classList.remove("acs-hidden");byId("login").style.display="flex";
      setStatus("جارٍ تسجيل الخروج…",false);
      try{if(s)await acsFetchJSON("/v1/auth/signout",{},s.access_token);}catch(e){}
      location.reload();
    });header.appendChild(b);
  }
  function authInit(callback){
    onEntry=callback;setMode("signin");
    var form=byId("acsAuthForm");
    if(form)form.addEventListener("submit",function(e){e.preventDefault();submit();});
    else byId("lgGo").addEventListener("click",submit);
    byId("lgSignup").addEventListener("click",function(){if(busy)return;if(mode==="project"||mode==="resume"){clearSession();clearPassword();}setStatus("",false);setMode(mode==="signin"?"signup":"signin");});
    var toggle=byId("acsPasswordToggle");if(toggle)toggle.addEventListener("click",function(){var pw=byId("lgPassword"),show=pw.type==="password";pw.type=show?"text":"password";toggle.textContent=show?"إخفاء":"إظهار";toggle.setAttribute("aria-label",show?"إخفاء كلمة المرور":"إظهار كلمة المرور");toggle.setAttribute("aria-pressed",String(show));});
    window.addEventListener("storage",function(e){
      if(e.key!==SESSION_KEY)return;
      sessionEpoch++;memorySession=null;
      var next=loadSession(),active=window.ACS&&window.ACS.authSession;
      if(active&&(!next||next.user.id!==active.user.id))location.reload();
    });
    restore();
  }
  function storageScope(){
    if(localHost())return "acs_local_project";
    var a=window.ACS, uid=a&&a.authSession&&a.authSession.user&&a.authSession.user.id, pid=a&&a.projectId;
    return typeof uid==="string"&&uid&&typeof pid==="string"&&pid ? "acs_local_project:"+uid+":"+pid : null;
  }
  window.ACS_AUTH={contract:"acs-production-auth/1.1",init:authInit,loadSession:loadSession,freshSession:freshSession,storageScope:storageScope,
    bootstrapProject:bootstrapProject,addLogout:addLogout,clearSession:clearSession,isLocalTestHost:localHost};
})();

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
    if(identity.mode==='local'){
      if(window.ACS.ready && window.ACS.showExample) window.ACS.showExample();
      else window.ACS.pending='example';
    }
    document.dispatchEvent(new CustomEvent('acs:authenticated',{detail:{mode:identity.mode}}));
  }
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
    fallbackLocalOnly();
  }
  function init(){
    initMobileNavigation();
    loadAuth();
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
