'use strict';
// Exercise the shipped classic auth controller with a controlled network and DOM.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {webcrypto,createHash}=require('node:crypto');
const source = fs.readFileSync('public/app/boot/engine-guard.js', 'utf8');
const KEY = 'acs_supabase_session_v1';
const PROJECT = 'acs_project_v1';
const session = (overrides = {}) => ({access_token:'access-a', refresh_token:'refresh-a',
  expires_at: Math.floor(Date.now()/1000)+3600, user:{id:'user-a',email:'a@example.test'}, ...overrides});
const response = (data, status=200) => ({ok:status<400, status, text:async()=>JSON.stringify(data)});
const problem = (code, status=503) => response({error:{code,message:'message-'+code}},status);
const settle = () => new Promise(resolve=>setImmediate(resolve));
function harness(handler, initial=null, hostname='acs.example.test', hash='', options={}) {
  const map=new Map(initial?[[KEY,JSON.stringify(initial)]]:[]), calls=[], entered=[], nodes=new Map(), listeners={};
  const tab=options.tab||new Map(), navigations=[];
  function element(id){
    if(nodes.has(id))return nodes.get(id);
    const events={}, classes=new Set();
    const e={id, value:'',type:id==='lgPassword'?'password':'',validity:{valid:true},hidden:false,
      style:{},textContent:'',attrs:{},classList:{toggle(k,v){if(v)classes.add(k);else classes.delete(k);},add:k=>classes.add(k),remove:k=>classes.delete(k)},
      setAttribute(k,v){this.attrs[k]=v;},addEventListener(k,fn){events[k]=fn;},
      focus(){},appendChild(){},emit(k){return events[k]&&events[k]({preventDefault(){}});}};
    nodes.set(id,e);return e;
  }
  const document={readyState:'loading',getElementById:element,querySelector:()=>null,
    addEventListener(){},createElement:()=>element('new'),body:{classList:{remove(){}}}};
  const location={hostname,origin:'https://'+hostname,hash,pathname:'/',search:options.search||'',reload(){h.reloads++;},assign(url){navigations.push(url);}};
  const ctx={document,location,history:{replaceState(a,b,url){const u=new URL(url,location.origin);location.hash=u.hash;location.search=u.search;}},console,setTimeout,clearTimeout,AbortController,URL,URLSearchParams,CustomEvent:class{},
    crypto:webcrypto,TextEncoder,btoa:s=>Buffer.from(s,'binary').toString('base64'),
    sessionStorage:{getItem:k=>tab.get(k)||null,setItem:(k,v)=>tab.set(k,v),removeItem:k=>tab.delete(k)},
    localStorage:{getItem:k=>map.get(k)||null,setItem:(k,v)=>map.set(k,v),removeItem:k=>map.delete(k)},
    fetch:async(url,opts)=>{calls.push({url,opts});return handler(new URL(url).pathname,opts,calls);},
    window:{ACS_API:{configured:'https://api.example.test',url:p=>'https://override.example.test'+p},
      addEventListener:(k,fn)=>{listeners[k]=fn;}}};
  const h={ctx,calls,map,tab,navigations,nodes,entered,reloads:0,el:element,listeners};
  vm.runInNewContext(source,ctx);
  h.auth=ctx.window.ACS_AUTH;
  h.init=()=>h.auth.init(identity=>{entered.push(identity);});
  return h;
}
let passed=0;
const GOOGLE='acs_google_pkce_v1', CODE='11111111-1111-4111-8111-111111111111';
const pending=(overrides={})=>new Map([[GOOGLE,JSON.stringify({verifier:'b'.repeat(64),created_at:Date.now(),
  user_id:null,redirect_to:'https://acs.example.test/',...overrides})]]);
function googleStart(opts,origin='https://acs.example.test/'){
  const challenge=JSON.parse(opts.body).code_challenge;
  return response({redirect_to:origin,url:'https://fixture.supabase.co/auth/v1/authorize?'+new URLSearchParams({
    provider:'google',redirect_to:origin,code_challenge:challenge,code_challenge_method:'s256'})});
}
async function test(name,fn){await fn();passed++;console.log('PASS '+name);}
(async()=>{
  await test('Google uses a fresh PKCE proof and recovers from browser Back',async()=>{
    const h=harness((path,opts)=>{assert.equal(path,'/v1/auth/google/start');return googleStart(opts);});h.init();
    h.el('lgPassword').value='existing-password';
    const first=h.el('acsAuthGoogle').emit('click');h.el('acsAuthGoogle').emit('click');await first;
    assert.equal(h.calls.length,1);assert.equal(h.navigations.length,1);assert.equal(h.el('lgPassword').value,'');
    const state=JSON.parse(h.tab.get(GOOGLE)),body=JSON.parse(h.calls[0].opts.body);
    assert.equal(body.code_challenge,createHash('sha256').update(state.verifier).digest('base64url'));
    assert.equal(body.code_verifier,undefined);assert.equal(h.el('acsAuthGoogle').disabled,true);
    assert.equal(h.map.has(GOOGLE),false,'proof stays in this tab, not localStorage');
    h.listeners.pageshow({persisted:true});assert.equal(h.tab.has(GOOGLE),false);assert.equal(h.el('acsAuthGoogle').disabled,false);
    await h.el('acsAuthGoogle').emit('click');assert.notEqual(JSON.parse(h.tab.get(GOOGLE)).verifier,state.verifier);
  });
  await test('unavailable Google and wrong callback origin leave email login usable',async()=>{
    for(const handler of [()=>problem('GOOGLE_NOT_CONFIGURED'),(path,opts)=>googleStart(opts,'https://other.example.test/')]){
      const h=harness(handler);h.init();await h.el('acsAuthGoogle').emit('click');
      assert.equal(h.navigations.length,0);assert.equal(h.tab.has(GOOGLE),false);
      assert.equal(h.el('lgGo').disabled,false);assert.equal(h.el('acsAuthStatus').attrs.role,'alert');
    }
  });
  await test('Google callback removes the code and reuses the existing project and Supabase user',async()=>{
    let h;h=harness((path,opts)=>{
      assert.equal(h.ctx.location.search,'?keep=value');assert.equal(h.tab.has(GOOGLE),false);
      if(path.endsWith('google/exchange')){
        assert.deepEqual(JSON.parse(opts.body),{auth_code:CODE,code_verifier:'b'.repeat(64)});
        return response(session({provider_token:'do-not-store',user:{id:'user-a',email:'a@example.test',user_metadata:{full_name:'Fixture Name'}}}));
      }
      assert.equal(path,'/v1/auth/bootstrap-project');assert.equal(opts.headers.authorization,'Bearer access-a');
      assert.equal(JSON.parse(opts.body).project_id,'existing-project');
      return response({project:{id:'existing-project',name:'Existing'},user:{id:'user-a'}});
    },session(),'acs.example.test','',{search:'?code='+CODE+'&keep=value',tab:pending({user_id:'user-a'})});
    h.map.set(PROJECT,JSON.stringify({id:'existing-project'}));h.init();await settle();
    assert.equal(h.entered.length,1);assert.equal(h.entered[0].project.id,'existing-project');
    assert.equal(h.entered[0].name,'Fixture Name');assert.ok(!h.map.get(KEY).includes('do-not-store'));
    assert.equal(h.calls.length,2);
  });
  await test('new Google user names a project without sending a password',async()=>{
    const h=harness((path,opts)=>{
      if(path.endsWith('google/exchange'))return response(session());
      assert.equal(path,'/v1/auth/bootstrap-project');
      return JSON.parse(opts.body).name?response({project:{id:'new-project'},user:{id:'user-a'}}):problem('PROJECT_NAME_REQUIRED',400);
    },null,'acs.example.test','',{search:'?code='+CODE,tab:pending()});
    h.init();await settle();assert.equal(h.el('acsAuthGoogleField').hidden,true);
    assert.equal(h.el('acsAuthProjectField').hidden,false);h.el('lgProject').value='New';
    h.el('acsAuthForm').emit('submit');await settle();assert.equal(h.entered[0].project.id,'new-project');
    assert.ok(h.calls.every(c=>!('password' in JSON.parse(c.opts.body))));
  });
  await test('missing, expired, duplicate or changed-account callbacks cannot open a project',async()=>{
    for(const opts of [{tab:new Map()},{tab:pending({created_at:Date.now()-11*60*1000})},
      {tab:pending({user_id:'different-user'})},{tab:pending(),search:'?code='+CODE+'&code='+CODE}]){
      const h=harness(()=>{throw Error('unexpected network');},null,'acs.example.test','',
        {search:'?code='+CODE,...opts});h.init();await settle();
      assert.equal(h.calls.length,0);assert.equal(h.entered.length,0);assert.equal(h.tab.has(GOOGLE),false);
      assert.equal(h.el('acsAuthStatus').attrs.role,'alert');assert.equal(h.ctx.location.search,'');
    }
  });
  await test('Google denial is sanitized and does not erase an existing account',async()=>{
    for(const fragment of [false,true]){
      const value='error=access_denied&error_description=private-detail';
      const h=harness(()=>{throw Error('no exchange after denial');},session(),'acs.example.test',fragment?'#'+value:'',
        {search:fragment?'':'?'+value,tab:pending({user_id:'user-a'})});h.init();await settle();
      assert.equal(h.calls.length,0);assert.equal(h.auth.loadSession().user.id,'user-a');
      assert.ok(!h.el('acsAuthStatus').textContent.includes('private-detail'));assert.equal(h.ctx.location.hash,'');
    }
  });
  await test('Google exchange finishing after logout cannot restore that session',async()=>{
    let resolve;const h=harness(()=>new Promise(r=>{resolve=r;}),null,'acs.example.test','',{search:'?code='+CODE,tab:pending()});
    h.init();h.auth.clearSession();resolve(response(session()));await settle();
    assert.equal(h.auth.loadSession(),null);assert.equal(h.entered.length,0);
  });
  await test('recovery sends only the selected email and never a saved password',async()=>{
    const h=harness(()=>response({ok:true,message:'Check email'}));h.init();
    h.el('lgEmail').value='a@example.test';h.el('lgPassword').value='old-fixture-password';
    h.el('acsAuthRecover').emit('click');assert.equal(h.el('lgPassword').value,'');
    assert.equal(h.el('acsAuthPasswordField').hidden,true);
    h.el('acsAuthForm').emit('submit');await settle();
    assert.equal(h.calls[0].url,'https://api.example.test/v1/auth/recover');
    assert.deepEqual(JSON.parse(h.calls[0].opts.body),{email:'a@example.test'});assert.equal(h.entered.length,0);
  });
  await test('recovery callback is verified and stripped before the password form opens',async()=>{
    let h;h=harness(path=>{assert.equal(h.ctx.location.hash,'');return path.endsWith('refresh')?response(session()):response({ok:true});},null,'acs.example.test','#type=recovery&refresh_token=fixture-link-refresh');
    assert.equal(h.ctx.location.hash,'');h.init();await settle();
    assert.equal(h.el('acsAuthTitle').textContent,'اختر كلمة مرور جديدة');assert.equal(h.entered.length,0);
    h.el('lgPassword').value='replacement-fixture';h.el('lgPasswordConfirm').value='different';
    h.el('acsAuthForm').emit('submit');await settle();assert.equal(h.calls.length,1);
    h.el('lgPasswordConfirm').value='replacement-fixture';h.el('acsAuthForm').emit('submit');await settle();
    assert.equal(h.calls[1].url,'https://api.example.test/v1/auth/update-password');assert.equal(h.calls[1].opts.headers.authorization,'Bearer access-a');
    assert.equal(h.auth.loadSession(),null);assert.equal(h.el('lgPassword').value,'');assert.equal(h.el('lgPasswordConfirm').value,'');assert.equal(h.entered.length,0);
  });
  await test('invalid email link cannot retain a previously signed-in account',async()=>{
    const h=harness(()=>{throw Error('no network');},session(),'acs.example.test','#error=access_denied&error_description=private');h.init();await settle();
    assert.equal(h.auth.loadSession(),null);assert.equal(h.entered.length,0);assert.ok(!h.el('acsAuthStatus').textContent.includes('private'));
  });
  await test('existing session stays usable without a refresh request',async()=>{
    const h=harness(()=>{throw Error('unexpected network');},session());
    assert.equal((await h.auth.freshSession()).user.id,'user-a');assert.equal(h.calls.length,0);
  });
  await test('concurrent expiration refreshes only once',async()=>{
    let resolve;const h=harness(()=>new Promise(r=>{resolve=r;}),session({expires_at:1}));
    const a=h.auth.freshSession(),b=h.auth.freshSession();
    assert.equal(h.calls.length,1);resolve(response(session({refresh_token:'rotated'})));
    assert.equal((await a).refresh_token,'rotated');assert.equal((await b).refresh_token,'rotated');
  });
  await test('temporary refresh failure retains the session and project',async()=>{
    const h=harness(()=>problem('AUTH_UPSTREAM_UNAVAILABLE'),session({expires_at:1}));
    h.map.set(PROJECT,'project-backup');
    await assert.rejects(h.auth.freshSession(),e=>e.status===503);
    assert.ok(h.map.has(KEY));assert.equal(h.map.get(PROJECT),'project-backup');
  });
  await test('revoked refresh clears stale session and project',async()=>{
    const h=harness(()=>problem('refresh_token_not_found',400),session({expires_at:1}));
    h.map.set(PROJECT,'project-backup');assert.equal(await h.auth.freshSession(),null);
    assert.equal(h.map.has(KEY),false);assert.equal(h.map.has(PROJECT),false);
  });
  await test('a refresh completing after logout cannot restore the old account',async()=>{
    let resolve;const h=harness(()=>new Promise(r=>{resolve=r;}),session({expires_at:1}));
    const pending=h.auth.freshSession();h.auth.clearSession();resolve(response(session()));
    assert.equal(await pending,null);assert.equal(h.auth.loadSession(),null);
  });
  await test('malformed refresh result preserves recovery credentials',async()=>{
    const h=harness(()=>response({access_token:'incomplete'}),session({expires_at:1}));
    await assert.rejects(h.auth.freshSession(),e=>e.code==='AUTH_INVALID_RESPONSE');
    assert.equal(h.auth.loadSession().refresh_token,'refresh-a');
  });
  await test('auth requests use pinned origin and bounded fetch',async()=>{
    const h=harness(()=>response(session()),session({expires_at:1}));await h.auth.freshSession();
    assert.equal(h.calls[0].url,'https://api.example.test/v1/auth/refresh');
    assert.equal(h.calls[0].opts.redirect,'error');assert.ok(h.calls[0].opts.signal);
  });
  await test('login opens only credentials and signup has a separate mode',async()=>{
    const h=harness(()=>{throw Error('no network on mode selection');});h.init();
    assert.equal(h.el('acsAuthNameField').hidden,true);assert.equal(h.el('acsAuthProjectField').hidden,true);
    h.el('lgSignup').emit('click');assert.equal(h.el('acsAuthNameField').hidden,false);
    assert.equal(h.el('lgPassword').autocomplete,'new-password');assert.equal(h.calls.length,0);
  });
  await test('confirmation receipt clears the password without authenticating or opening a project',async()=>{
    const h=harness(()=>response({user:{id:'pending-user',email:'a@example.test'},session:null}));h.init();
    h.el('lgSignup').emit('click');h.el('lgEmail').value='a@example.test';h.el('lgPassword').value='fixture-password';
    h.el('acsAuthForm').emit('submit');await settle();
    assert.equal(h.calls.length,1);assert.ok(h.calls[0].url.endsWith('/signup'));
    assert.equal(h.auth.loadSession(),null);assert.equal(h.map.has(KEY),false);assert.equal(h.entered.length,0);
    assert.equal(h.el('lgPassword').value,'');assert.equal(h.el('acsAuthTitle').textContent,'تسجيل الدخول');
    assert.equal(h.el('acsAuthStatus').attrs.role,'status');assert.equal(h.el('acsAuthResend').hidden,false);
    assert.match(h.el('acsAuthStatus').textContent,/إذا كان الحساب يحتاج تأكيدًا/);
  });
  await test('partial sessions and malformed users cannot become confirmation receipts',async()=>{
    for(const raw of [{user:{id:'pending-user'},access_token:'incomplete'},
      {user:{id:'pending-user'},refresh_token:'incomplete'}, {user:'unexpected',session:null},
      {user:{},session:null}, {user:{id:'pending-user'}}]){
      const h=harness(()=>response(raw));h.init();h.el('lgSignup').emit('click');
      h.el('lgEmail').value='a@example.test';h.el('lgPassword').value='fixture-password';
      h.el('acsAuthForm').emit('submit');await settle();
      assert.equal(h.el('acsAuthStatus').attrs.role,'alert');assert.equal(h.auth.loadSession(),null);
      assert.equal(h.entered.length,0);assert.equal(h.calls.length,1);
    }
  });
  await test('a user-only signin response cannot authenticate or show signup confirmation',async()=>{
    const h=harness(()=>response({user:{id:'pending-user'},session:null}));h.init();
    h.el('lgEmail').value='a@example.test';h.el('lgPassword').value='fixture-password';
    h.el('acsAuthForm').emit('submit');await settle();
    assert.equal(h.el('acsAuthStatus').attrs.role,'alert');assert.equal(h.auth.loadSession(),null);
    assert.equal(h.entered.length,0);assert.equal(h.calls.length,1);
  });
  await test('new account onboarding reuses the session without another password submission',async()=>{
    let bootstrap=0;
    const h=harness(path=>path.endsWith('signin')?response(session()):++bootstrap===1?
      problem('PROJECT_NAME_REQUIRED',400):response({project:{id:'project-a',name:'First'},user:{id:'user-a'}}));
    h.init();h.el('lgEmail').value='a@example.test';h.el('lgPassword').value='correct-password';
    h.el('acsAuthForm').emit('submit');await settle();
    assert.equal(h.el('acsAuthCredentials').hidden,true);assert.equal(h.el('acsAuthProjectField').hidden,false);
    assert.equal(h.el('lgPassword').value,'');h.el('lgProject').value='First';
    h.el('acsAuthForm').emit('submit');await settle();
    assert.equal(h.entered.length,1);assert.equal(h.entered[0].project.id,'project-a');
    assert.equal(h.calls.filter(c=>c.url.endsWith('/signin')).length,1);
  });
  await test('repeated submit while signing in sends one login request',async()=>{
    let resolve;const h=harness(path=>path.endsWith('signin')?new Promise(r=>{resolve=r;}):response({project:{id:'p'}}));
    h.init();h.el('lgEmail').value='a@example.test';h.el('lgPassword').value='correct-password';
    h.el('acsAuthForm').emit('submit');h.el('acsAuthForm').emit('submit');
    assert.equal(h.calls.length,1);resolve(response(session()));await settle();assert.equal(h.entered.length,1);
  });
  await test('restore distinguishes an upstream outage from missing first project',async()=>{
    const h=harness(()=>problem('AUTH_UPSTREAM_UNAVAILABLE'),session());h.init();await settle();
    assert.equal(h.entered.length,0);assert.equal(h.el('acsAuthProjectField').hidden,true);
    assert.equal(h.el('acsAuthStatus').textContent,'message-AUTH_UPSTREAM_UNAVAILABLE');assert.ok(h.auth.loadSession());
  });
  await test('local backup namespaces follow authenticated account and project',async()=>{
    const h=harness(()=>{});assert.equal(h.auth.storageScope(),null);
    h.ctx.window.ACS={authSession:session(),projectId:'project-a'};const first=h.auth.storageScope();
    h.ctx.window.ACS.projectId='project-b';assert.notEqual(h.auth.storageScope(),first);
    h.ctx.window.ACS.authSession=session({user:{id:'user-b'}});assert.notEqual(h.auth.storageScope(),first);
    h.auth.clearSession();assert.equal(h.auth.storageScope(),null);
  });
  await test('revocation after a temporary outage returns the retry screen to sign-in',async()=>{
    let revoked=false;
    const h=harness(()=>revoked?problem('refresh_token_not_found',400):problem('AUTH_UPSTREAM_UNAVAILABLE'),session({expires_at:1}));
    h.init();await settle();assert.equal(h.el('acsAuthCredentials').hidden,true);
    revoked=true;h.el('acsAuthForm').emit('submit');await settle();
    assert.equal(h.auth.loadSession(),null);assert.equal(h.el('acsAuthCredentials').hidden,false);
    assert.equal(h.el('acsAuthTitle').textContent,'تسجيل الدخول');assert.equal(h.el('lgGo').disabled,false);
  });
  await test('changing account in another tab closes the previous workspace',async()=>{
    const h=harness(()=>{},null);h.init();h.ctx.window.ACS.authSession=session();
    h.map.set(KEY,JSON.stringify(session({user:{id:'user-b'}})));h.listeners.storage({key:KEY});
    assert.equal(h.reloads,1);
  });
  console.log('AUTH SESSION: '+passed+' passed, 0 failed');
})().catch(e=>{console.error(e);process.exitCode=1;});
