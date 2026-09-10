'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');
const source = fs.readFileSync(path.join(__dirname, '../../public/app/ui/generation-jobs.js'), 'utf8')
  .replace(/^import .*;\n/gm, '');
let passed = 0;
const ok = (body, http=200) => ({status:'SUCCESS', http, body, request_id:'req_test'});
const network = {status:'NETWORK_ERROR', http:0, body:null, retryable:true};
const model = {ok:true, building:{meta:{type:'villa'}, levels:[], floors:{}}};
function harness(handler, values = new Map()) {
  const calls=[];
  const events=new EventTarget();
  const document={readyState:'loading', visibilityState:'visible',
    documentElement:{lang:'ar'}, getElementById:()=>null,
    addEventListener:events.addEventListener.bind(events),
    removeEventListener:events.removeEventListener.bind(events)};
  const ctx={console, Date, Promise, JSON, Uint8Array, Array, Number, String,
    setTimeout:fn=>setTimeout(fn,0), clearTimeout,
    srvURL:()=>ctx.window.ACS_API.base(), document, statusEl:{textContent:''}, srvPill(){},
    acsApplyTicket(){return 1;}, acsApplyBuilding(){throw new Error('not a transport concern');},
    acsApplyFirstFrame(){}, showReport(){},
    window:{crypto:webcrypto, ACS:{}, ACS_API:{base:()=> 'https://acs.example'},
      sessionStorage:{getItem:k=>values.get(k)||null, setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)},
      addEventListener:events.addEventListener.bind(events),removeEventListener:events.removeEventListener.bind(events)},
    __ACS_SHARED:{acsFetchJSON:async(p,o,t)=>{calls.push({p,o,t});return handler(p,o,t);}}};
  vm.runInNewContext(source,ctx,{filename:'generation-jobs.js'});
  return {ctx, calls, values, run:ctx.__ACS_SHARED.acsFetchJSON};
}
function receipt(id,state='RUNNING') {
  return ok({contract:'acs.async-generation/1.0',job:{id,state,expires_at:Date.now()/1000+1800}},202);
}
async function test(name,fn){await fn();console.log('PASS '+name);passed++;}
(async()=>{
  await test('one POST, failed polls and failed result download never generate again',async()=>{
    let id, polls=0, downloads=0;
    const h=harness((p,o)=>{
      if(o.method==='POST'){id=o.headers['X-ACS-Job-ID'];return receipt(id,'QUEUED');}
      if(p.endsWith('/result')) return ++downloads===1?network:ok(model);
      if(++polls===1)return network;
      return receipt(id,polls===2?'RUNNING':'SUCCEEDED');
    });
    const res=await h.run('/v1/understand',{method:'POST',headers:{'Content-Type':'application/json'},body:'{"text":"villa"}'},900000);
    assert.deepEqual(res.body,model);
    assert.equal(h.calls.filter(c=>c.o.method==='POST').length,1);
    assert.equal(downloads,2);
    assert.ok(h.calls.every(c=>c.t<=20000));
    assert.ok(h.ctx.window.ACS.asyncGeneration.state().delivered);
  });
  await test('lost submission receipt recovered by known client job id, not another POST',async()=>{
    let id;
    const h=harness((p,o)=>{
      if(o.method==='POST'){id=o.headers['X-ACS-Job-ID'];return network;}
      return p.endsWith('/result')?ok(model):receipt(id,'SUCCEEDED');
    });
    assert.equal((await h.run('/v1/understand',{method:'POST',body:'{}'})).status,'SUCCESS');
    assert.equal(h.calls.filter(c=>c.o.method==='POST').length,1);
  });
  await test('refresh recovery uses only GET and retains no description or image',async()=>{
    const values=new Map();
    const first=harness(()=>{},values);
    const row={id:'job_'+'1'.repeat(32),token:'a'.repeat(64),path:'/v1/understand',
      base:'https://acs.example',created:Date.now(),delivered:false,acknowledged:true};
    first.ctx.acsJobSave(row);
    const fresh=harness(p=>p.endsWith('/result')?ok(model):receipt(row.id,'SUCCEEDED'),values);
    assert.equal((await fresh.ctx.acsJobWait(fresh.ctx.acsJobRead())).status,'SUCCESS');
    assert.ok(fresh.calls.every(c=>c.o.method==='GET'));
    assert.ok(!JSON.stringify(fresh.ctx.window.ACS.asyncGeneration.state()).includes(row.token));
    const stored=JSON.parse([...values.values()][0]);
    assert.ok(!('text' in stored)&&!('body' in stored)&&!('building' in stored));
  });
  await test('a pending prior job blocks a second paid request after refresh',async()=>{
    const h=harness(()=>{throw new Error('must not send');});
    h.ctx.acsJobSave({id:'job_'+'2'.repeat(32),token:'b'.repeat(64),path:'/v1/understand',
      base:'https://acs.example',created:Date.now(),delivered:false});
    const r=await h.run('/v1/understand',{method:'POST',body:'{}'});
    assert.equal(r.http,409);assert.equal(h.calls.length,0);
  });
  await test('capability never follows a changed backend address',async()=>{
    const h=harness(()=>{throw new Error('credentials must not be sent');});
    const r=await h.ctx.acsJobWait({id:'job_'+'2'.repeat(32),token:'b'.repeat(64),
      path:'/v1/understand',base:'https://old.example',created:Date.now()});
    assert.equal(r.status,'VALID_API_ERROR');assert.equal(h.calls.length,0);
  });
  await test('expired or restarted job is not automatically submitted again',async()=>{
    const h=harness(()=>({status:'VALID_API_ERROR',http:404,body:{ok:false,error:{code:'ACS_NOT_FOUND'}}}));
    const r=await h.ctx.acsJobWait({id:'job_'+'2'.repeat(32),token:'b'.repeat(64),
      path:'/v1/understand',base:'https://acs.example',created:Date.now(),acknowledged:true});
    assert.equal(r.http,404);assert.equal(h.calls.length,1);assert.equal(h.calls[0].o.method,'GET');
  });
  await test('backend errors retain original HTTP code for existing error and PDF handling',async()=>{
    let id;
    const failure={status:'VALID_API_ERROR',http:422,body:{ok:false,error:{code:'ACS_UNPROCESSABLE'}},code:'ACS_UNPROCESSABLE'};
    const h=harness((p,o)=>{
      if(o.method==='POST'){id=o.headers['X-ACS-Job-ID'];return receipt(id);}
      return p.endsWith('/result')?failure:receipt(id,'FAILED');
    });
    assert.equal((await h.run('/v1/understand/pdf',{method:'POST',body:'synthetic multipart'})).http,422);
    assert.equal(h.calls[0].p,'/v1/jobs/understand/pdf');
    assert.equal(h.calls[0].o.body,'synthetic multipart');
  });
  await test('health and non-generation traffic remain on the original transport',async()=>{
    const h=harness(()=>ok({ok:true}));
    await h.run('/health',{method:'GET'},12000);
    assert.equal(h.calls[0].p,'/health');assert.equal(h.calls[0].t,12000);
  });
  await test('old backend rejection at new job endpoint never falls back to a long POST',async()=>{
    const h=harness(()=>({status:'VALID_API_ERROR',http:404,body:{ok:false,error:{code:'ACS_NOT_FOUND'}}}));
    assert.equal((await h.run('/v1/understand',{method:'POST',body:'{}'})).http,404);
    assert.equal(h.calls.length,1);assert.equal(h.calls[0].p,'/v1/jobs/understand');
    assert.equal(h.ctx.window.ACS.asyncGeneration.state(),null);
  });
  console.log('GENERATION JOB CLIENT: '+passed+' passed, 0 failed');
})().catch(e=>{console.error(e);process.exitCode=1;});
