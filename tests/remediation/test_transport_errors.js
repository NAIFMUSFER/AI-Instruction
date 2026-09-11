'use strict';
const assert = require('assert/strict'), vm = require('vm');
const fs = require('fs'), path = require('path');
const {source, ROOT} = require('./_transport_source.js');
const {T} = require('./_trust_core.js').load();
let passed = 0;
async function test(name, fn) { await fn(); passed++; console.log('PASS ' + name); }
function harness(fetcher, online = true) {
  let timer, cleared = false;
  const ctx = {Date, AbortController, navigator:{onLine:online}, __ACS_SHARED:{},
    apiURL:p=>'https://example.invalid'+p,
    window:{ACS_API:{base:()=> 'https://example.invalid', host:()=> 'example.invalid'}},
    fetch:fetcher,
    setTimeout:fn=>{timer=fn; return 1;}, clearTimeout:()=>{cleared=true;}};
  vm.runInNewContext(source(), ctx);
  return {ctx, call:ctx.__ACS_SHARED.acsFetchJSON, expire:()=>timer(), cleared:()=>cleared};
}
const reply = (body, status=200) => ({status, ok:status<400,
  headers:{get:k=>k==='X-Request-ID'?'req_test':''}, text:async()=>body});
// Exercise the shipped generation handler with deferred responses. Rendering is
// outside this test; no real request, credentials, or provider charge is used.
function generationHarness() {
  const src=fs.readFileSync(path.join(ROOT,'public/app/ui/workspace-ui-wiring.js'),'utf8');
  const start=src.indexOf('async function acsGenerateFromServer(){');
  const end=src.indexOf("\ndocument.getElementById('genLLM').onclick=",start);
  const pillStart=src.indexOf('function srvPill(');
  const pillEnd=src.indexOf('\nasync function checkServer(',pillStart);
  assert.ok(start>=0 && end>start && pillStart>=0 && pillEnd>pillStart);
  const pending=[], errors=[];
  const elements={descText:{value:'One room on one floor'},siteW:{value:20},
    siteD:{value:25},nFloors:{value:1},reportBox:{className:'report'},
    srvPill:{className:'srv bad',innerHTML:'Previous NETWORK_ERROR'}};
  const events=[];
  const ctx={console:{error(){},warn(){}},
    CustomEvent:function(type,init){this.type=type;this.detail=(init&&init.detail)||null;},
    document:{getElementById:id=>elements[id],dispatchEvent:event=>{events.push(event);return true;}},
    statusEl:{textContent:''}, SRV_OK:false, ACS_APPLY_SEQ:0,
    ACS_NET:{SUCCESS:'SUCCESS',INVALID_JSON:'INVALID_JSON'},
    ACS_FAIL:{API_HTTP_ERROR:'API_HTTP_ERROR',API_NETWORK_ERROR:'API_NETWORK_ERROR',
      MODEL_VALIDATION_ERROR:'MODEL_VALIDATION_ERROR'},
    esc:s=>String(s), acsFail(){}, showReport(){}, requestAnimationFrame(){},
    __ACS_SHARED:{acsFetchJSON:()=>new Promise(resolve=>pending.push(resolve)),
      acsErrorPanel:r=>errors.push(r),acsApplyErrorPanel:r=>errors.push(r)}};
  ctx.acsApplyTicket=()=>++ctx.ACS_APPLY_SEQ;
  ctx.acsApplyBuilding=(_building,opts)=>({ok:true,stale:opts.seq!==ctx.ACS_APPLY_SEQ});
  vm.runInNewContext(src.slice(pillStart,pillEnd)+'\n'+src.slice(start,end),ctx);
  return {ctx,pill:elements.srvPill,pending,errors,events,call:ctx.acsGenerateFromServer};
}
const networkFailure={status:'NETWORK_ERROR',message:'Unknown delivery status'};
async function main() {
  for (const message of ['Load failed','Failed to fetch','NetworkError when attempting to fetch resource.']) {
    await test(message+' is UNKNOWN network cause, never DNS', async()=>{
      const h=harness(async()=>{throw new TypeError(message);});
      assert.equal((await h.call('/test')).status,'NETWORK_ERROR');
      assert.ok(h.cleared());
    });
  }
  await test('offline before sending makes zero requests', async()=>{
    let requests=0; const h=harness(async()=>{requests++;},false);
    assert.equal((await h.call('/test')).status,'NETWORK_OFFLINE'); assert.equal(requests,0);
  });
  await test('going offline after send does not assert non-delivery', async()=>{
    const h=harness(async()=>{h.ctx.navigator.onLine=false; throw new TypeError('Load failed');});
    assert.equal((await h.call('/test')).status,'NETWORK_ERROR');
  });
  await test('body connection failure preserves HTTP and request id', async()=>{
    const r=reply(''); r.text=async()=>{throw new TypeError('terminated');};
    const h=harness(async()=>r), out=await h.call('/test');
    assert.equal(out.status,'NETWORK_ERROR'); assert.equal(out.http,200);
    assert.equal(out.request_id,'req_test'); assert.ok(h.cleared());
  });
  for (const phase of ['headers','body']) {
    await test('deadline covers '+phase+' with a caller signal', async()=>{
      const h=harness(async(url, opts)=>{
        const wait=()=>new Promise((resolve,reject)=>{
          opts.signal.addEventListener('abort',()=>reject(new TypeError('Load failed')));
          queueMicrotask(()=>h.expire());
        });
        if(phase==='headers') return wait();
        return {...reply(''), text:wait};
      });
      const out=await h.call('/test',{signal:new AbortController().signal},1000);
      assert.equal(out.status,'TIMEOUT'); assert.ok(h.cleared());
    });
  }
  await test('caller cancellation still aborts transport', async()=>{
    const caller=new AbortController();
    const h=harness(async(url,opts)=>new Promise((resolve,reject)=>{
      opts.signal.addEventListener('abort',()=>reject(new Error('cancelled')));
      caller.abort();
    }));
    const out=await h.call('/test',{signal:caller.signal});
    assert.notEqual(out.status,'SUCCESS'); assert.notEqual(out.status,'TIMEOUT'); assert.ok(h.cleared());
  });
  for (const [body, status, expected] of [
    ['{"ok":true}',200,'SUCCESS'], ['invalid',200,'INVALID_JSON'],
    ['{"detail":"rate"}',429,'HTTP_429'], ['{"detail":"bad"}',400,'HTTP_4XX'],
    ['{"detail":"error"}',503,'HTTP_5XX'],
    ['{"ok":false,"error":{"code":"ACS_INTERNAL","request_id":"req_error"}}',500,'VALID_API_ERROR']
  ]) {
    await test('preserves '+expected,async()=>{
      let reads=0; const r=reply(body,status); r.text=async()=>{reads++;return body;};
      const h=harness(async()=>r);
      assert.equal((await h.call('/test')).status,expected); assert.equal(reads,1); assert.ok(h.cleared());
    });
  }
  for (const cls of ['NETWORK_ERROR','NETWORK_DNS','TIMEOUT']) {
    await test(cls+' cannot offer a duplicate paid request based on a client key',async()=>{
      const s=T.resolveErrorState({status:cls,operation:'GENERATE',idempotency_key:'client_key'});
      assert.equal(s.class,cls); assert.equal(s.show_retry_button,false);
      assert.equal(s.retry_safe,false); assert.ok(!/never reached|did not reach/.test(s.en));
    });
  }
  await test('a new generation replaces the previous failure with pending status',async()=>{
    const h=generationHarness(), first=h.call();
    assert.equal(h.events[0].type,'acs:generation-started');
    h.pending[0](networkFailure); await first;
    assert.equal(h.pill.className,'srv bad');
    const next=h.call();
    assert.equal(h.events[1].type,'acs:generation-started');
    assert.equal(h.pill.className,'srv');
    assert.ok(!h.pill.innerHTML.includes('NETWORK_ERROR'));
    assert.equal(h.ctx.SRV_OK,false,'pending is not proof of connectivity');
    h.pending[1](networkFailure); await next;
  });
  await test('an older failure cannot replace a newer pending generation',async()=>{
    const h=generationHarness(), first=h.call(), next=h.call();
    const pendingText=h.ctx.statusEl.textContent;
    h.pending[0](networkFailure); await first;
    assert.equal(h.pill.className,'srv');
    assert.equal(h.ctx.statusEl.textContent,pendingText);
    assert.equal(h.errors.length,0);
    h.pending[1](networkFailure); await next;
    assert.equal(h.pill.className,'srv bad');
    assert.equal(h.errors.length,1,'the current failure must still be displayed');
  });
  await test('an older failure cannot overwrite a newer successful server response',async()=>{
    const h=generationHarness(), first=h.call(), next=h.call();
    h.pending[1]({status:'SUCCESS',body:{building:{},report:{}}}); await next;
    const currentText=h.ctx.statusEl.textContent;
    assert.equal(h.pill.className,'srv ok');
    h.pending[0](networkFailure); await first;
    assert.equal(h.pill.className,'srv ok');
    assert.equal(h.ctx.statusEl.textContent,currentText);
    assert.equal(h.errors.length,0);
  });
  await test('a parsed server response without a model ends the pending indicator',async()=>{
    const h=generationHarness(), request=h.call();
    h.pending[0]({status:'SUCCESS',http:200,body:{}}); await request;
    assert.equal(h.pill.className,'srv ok','the server responded, but the model is invalid');
    assert.equal(h.errors[0].status,'INVALID_JSON');
    assert.ok(h.ctx.statusEl.textContent.includes('غير مكتمل'));
  });
  console.log(`TRANSPORT UNIT: ${passed} passed, 0 failed (Node, no browser or paid calls)`);
}
main().catch(e=>{console.error(e);console.error(`TRANSPORT UNIT: ${passed} passed, 1 failed`);process.exitCode=1;});