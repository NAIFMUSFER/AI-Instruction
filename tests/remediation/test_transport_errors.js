'use strict';
const assert = require('assert/strict'), vm = require('vm');
const {source} = require('./_transport_source.js');
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
  console.log(`TRANSPORT UNIT: ${passed} passed, 0 failed (Node, no browser or paid calls)`);
}
main().catch(e=>{console.error(e);console.error(`TRANSPORT UNIT: ${passed} passed, 1 failed`);process.exitCode=1;});
