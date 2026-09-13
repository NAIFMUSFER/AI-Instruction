/* ============================================================
   ACS production authentication client.
   Browser talks only to ACS backend; backend proxies bounded Supabase Auth.
   Localhost keeps the historical name-only entry solely for automated/dev use.
   ============================================================ */
(function(){
  "use strict";

  var SESSION_KEY = "acs_supabase_session_v1";
  var PROJECT_KEY = "acs_project_v1";

  function byId(id){ return document.getElementById(id); }
  function localHost(){
    return location.hostname === "127.0.0.1" || location.hostname === "localhost" || location.hostname === "::1";
  }
  function api(path){
    return window.ACS_API && typeof window.ACS_API.url === "function" ? window.ACS_API.url(path) : "";
  }
  function statusEl(){ return byId("acsAuthStatus"); }
  function setStatus(text, bad){
    var el = statusEl();
    if(!el) return;
    el.textContent = text || "";
    el.setAttribute("role", bad ? "alert" : "status");
    el.classList.toggle("bad", !!bad);
  }
  function setBusy(on){
    ["lgGo","lgSignup"].forEach(function(id){ var b=byId(id); if(b) b.disabled=!!on; });
  }
  function safeJson(text){ try{return JSON.parse(text);}catch(e){return null;} }
  async function request(path, body, token){
    var url = api(path);
    if(!url) throw new Error("الخادم غير مضبوط.");
    var headers = {"content-type":"application/json","accept":"application/json"};
    if(token) headers.authorization = "Bearer " + token;
    var res = await fetch(url, {
      method:"POST",
      headers:headers,
      body:JSON.stringify(body||{}),
      cache:"no-store",
      credentials:"omit"
    });
    var text = await res.text();
    var data = safeJson(text) || {};
    if(!res.ok){
      var msg = data && data.error && data.error.message;
      if(!msg && data && data.msg) msg=data.msg;
      throw new Error(msg || "تعذّر إكمال العملية.");
    }
    return data;
  }
  function saveSession(s){
    if(!s || !s.access_token || !s.refresh_token) return null;
    var expiresAt = Number(s.expires_at || 0);
    if(!expiresAt && s.expires_in) expiresAt = Math.floor(Date.now()/1000)+Number(s.expires_in);
    var slim = {
      access_token:String(s.access_token),
      refresh_token:String(s.refresh_token),
      expires_at:expiresAt || 0,
      user:s.user && typeof s.user === "object" ? {id:s.user.id||"",email:s.user.email||"",user_metadata:s.user.user_metadata||{}} : null
    };
    try{ localStorage.setItem(SESSION_KEY, JSON.stringify(slim)); }catch(e){}
    return slim;
  }
  function loadSession(){
    try{
      var raw=localStorage.getItem(SESSION_KEY); if(!raw) return null;
      var s=JSON.parse(raw);
      return s && s.access_token && s.refresh_token ? s : null;
    }catch(e){ return null; }
  }
  function clearSession(){
    try{ localStorage.removeItem(SESSION_KEY); localStorage.removeItem(PROJECT_KEY); }catch(e){}
  }
  async function freshSession(){
    var s=loadSession(); if(!s) return null;
    var now=Math.floor(Date.now()/1000);
    if(Number(s.expires_at||0) > now+60) return s;
    try{
      var next=await request("/v1/auth/refresh", {refresh_token:s.refresh_token});
      return saveSession(next);
    }catch(e){ clearSession(); return null; }
  }
  async function bootstrapProject(session, projectName){
    var out=await request("/v1/auth/bootstrap-project", {name:String(projectName||"").trim()}, session.access_token);
    if(out && out.project){
      try{ localStorage.setItem(PROJECT_KEY, JSON.stringify(out.project)); }catch(e){}
    }
    return out;
  }
  function injectUI(){
    var email=byId("lgEmail");
    var go=byId("lgGo");
    if(!email || !go || byId("lgPassword")) return;

    var label=document.createElement("label");
    label.setAttribute("for","lgPassword");
    label.textContent="كلمة المرور · Password";
    var input=document.createElement("input");
    input.id="lgPassword";
    input.type="password";
    input.autocomplete="current-password";
    input.placeholder="8 أحرف على الأقل";
    email.insertAdjacentElement("afterend", label);
    label.insertAdjacentElement("afterend", input);

    go.textContent="تسجيل الدخول ▸";
    var signup=document.createElement("button");
    signup.id="lgSignup";
    signup.type="button";
    signup.className="ghost";
    signup.textContent="إنشاء حساب جديد";
    go.insertAdjacentElement("afterend", signup);

    var hint=go.parentElement && go.parentElement.querySelector(".hint");
    if(hint) hint.textContent="تسجيل دخول حقيقي عبر Supabase Auth — لا تُحفظ كلمة المرور في ACS.";
    var st=document.createElement("div");
    st.id="acsAuthStatus";
    st.className="hint";
    st.setAttribute("aria-live","polite");
    signup.insertAdjacentElement("afterend", st);
  }

  function values(){
    return {
      name:String((byId("lgName")&&byId("lgName").value)||"").trim(),
      email:String((byId("lgEmail")&&byId("lgEmail").value)||"").trim(),
      password:String((byId("lgPassword")&&byId("lgPassword").value)||""),
      project:String((byId("lgProject")&&byId("lgProject").value)||"").trim()
    };
  }

  async function signIn(onAuthenticated){
    var v=values();
    if(localHost() && !v.email && !v.password){
      onAuthenticated({mode:"local",name:v.name||"عميل",project:{name:v.project||"Local test project"}});
      return;
    }
    if(!v.email || !v.password){ setStatus("أدخل البريد وكلمة المرور.",true); return; }
    setBusy(true); setStatus("جاري تسجيل الدخول…",false);
    try{
      var raw=await request("/v1/auth/signin", {email:v.email,password:v.password});
      var session=saveSession(raw);
      if(!session) throw new Error("لم تُرجع خدمة الدخول جلسة صالحة.");
      var boot=await bootstrapProject(session,v.project);
      setStatus("تم تسجيل الدخول.",false);
      onAuthenticated({mode:"supabase",name:v.name || (session.user&&session.user.email) || "عميل",session:session,project:boot.project,user:boot.user});
    }catch(e){ setStatus(e && e.message ? e.message : "تعذّر تسجيل الدخول.",true); }
    finally{ setBusy(false); }
  }

  async function signUp(onAuthenticated){
    var v=values();
    if(!v.email || !v.password){ setStatus("أدخل البريد وكلمة مرور من 8 أحرف على الأقل.",true); return; }
    if(v.password.length<8){ setStatus("كلمة المرور يجب أن تكون 8 أحرف على الأقل.",true); return; }
    setBusy(true); setStatus("جاري إنشاء الحساب…",false);
    try{
      var raw=await request("/v1/auth/signup", {name:v.name,email:v.email,password:v.password});
      var session=saveSession(raw);
      if(!session){
        setStatus("تم إنشاء الحساب. افتح رسالة التأكيد في بريدك، ثم ارجع واضغط تسجيل الدخول.",false);
        return;
      }
      var boot=await bootstrapProject(session,v.project);
      setStatus("تم إنشاء الحساب وتسجيل الدخول.",false);
      onAuthenticated({mode:"supabase",name:v.name || (session.user&&session.user.email) || "عميل",session:session,project:boot.project,user:boot.user});
    }catch(e){ setStatus(e && e.message ? e.message : "تعذّر إنشاء الحساب.",true); }
    finally{ setBusy(false); }
  }

  async function restore(onAuthenticated){
    var session=await freshSession();
    if(!session) return false;
    try{
      var boot=await bootstrapProject(session,"");
      onAuthenticated({mode:"supabase",name:(session.user&&session.user.email)||"عميل",session:session,project:boot.project,user:boot.user});
      return true;
    }catch(e){
      // A legitimate account with no project must remain at login so the user can
      // name the first project instead of creating hidden synthetic data.
      setStatus("الحساب مسجّل. اكتب اسم المشروع الأول ثم اضغط تسجيل الدخول.",false);
      return false;
    }
  }

  function addLogout(){
    if(byId("acsLogout")) return;
    var header=document.querySelector("#left header");
    if(!header) return;
    var b=document.createElement("button");
    b.id="acsLogout"; b.type="button"; b.className="ghost"; b.textContent="خروج";
    b.addEventListener("click",async function(){
      var s=loadSession();
      try{ if(s) await request("/v1/auth/signout",{},s.access_token); }catch(e){}
      clearSession(); location.reload();
    });
    header.appendChild(b);
  }

  function init(onAuthenticated){
    injectUI();
    var go=byId("lgGo"), signup=byId("lgSignup"), pw=byId("lgPassword");
    if(go) go.addEventListener("click",function(){signIn(onAuthenticated);});
    if(signup) signup.addEventListener("click",function(){signUp(onAuthenticated);});
    [byId("lgName"),byId("lgEmail"),byId("lgProject"),pw].forEach(function(el){
      if(el) el.addEventListener("keydown",function(e){ if(e.key==="Enter") signIn(onAuthenticated); });
    });
    restore(onAuthenticated);
  }

  window.ACS_AUTH={
    contract:"acs-production-auth/1.0",
    init:init,
    loadSession:loadSession,
    freshSession:freshSession,
    bootstrapProject:bootstrapProject,
    addLogout:addLogout,
    clearSession:clearSession,
    isLocalTestHost:localHost
  };
})();
