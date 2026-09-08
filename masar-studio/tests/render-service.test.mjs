import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';
import os from 'node:os';import path from 'node:path';
import {createApp} from '../server/server.mjs';
import {generate,understand,createHistory,current,pushHistory,clone} from '../shared/model.js';
const token='test-worker-secret-that-is-not-a-real-key-123456',origin='http://render.test';
async function fixture(t,enabled=true){
 const dir=await mkdtemp(path.join(os.tmpdir(),'masar-render-api-test-'));let clock=Date.now();
 const app=await createApp({production:false,dbPath:path.join(dir,'db.sqlite'),origin,render:{enabled,workerToken:token,outputDir:path.join(dir,'artifacts'),now:()=>clock}});
 await new Promise(r=>app.server.listen(0,'127.0.0.1',r));t.after(async()=>{await new Promise(r=>app.server.close(r));await rm(dir,{recursive:true,force:true});});
 const base='http://127.0.0.1:'+app.server.address().port;
 async function req(route,{method='GET',body,headers={}}={}){const res=await fetch(base+route,{method,headers:{Origin:origin,'Content-Type':'application/json',...headers},body:body===undefined?undefined:JSON.stringify(body)});return {status:res.status,data:await res.json(),headers:res.headers};}
 const user=async email=>{const r=await req('/api/auth/register',{method:'POST',body:{name:'Tester',email,password:'Testing-password-12345'}});assert.equal(r.status,201);return{Cookie:r.headers.get('set-cookie').split(';')[0],'X-CSRF-Token':r.data.csrf};};
 const owner=await user('render-owner@example.test'),other=await user('render-other@example.test');
 const h=createHistory(generate(understand('أرض 20×25 ثلاثة أدوار خمس غرف نوم')));
 assert.equal((await req('/api/projects/'+h.projectId,{method:'PUT',headers:owner,body:{history:h,version:0}})).status,200);
 const wh={Authorization:'Bearer '+token};
 const beat=()=>req('/api/render-worker/heartbeat',{method:'POST',headers:wh,body:{version:'4.5.13'}});
 const submit=(more={},headers=owner)=>req('/api/renders',{method:'POST',headers,body:{projectId:h.projectId,version:1,revisionId:h.revisions[0].id,settings:{},...more}});
 return {app,base,req,owner,other,h,wh,beat,submit,advance:ms=>{clock+=ms;}};
}
test('render is disabled without explicit operator configuration',async t=>{const f=await fixture(t,false);assert.equal((await f.req('/api/renders/capabilities')).data.enabled,false);assert.equal((await f.submit()).status,503);assert.equal((await f.beat()).status,503);});
test('enabled queue fails closed when worker heartbeat is absent or expired',async t=>{const f=await fixture(t);assert.equal((await f.submit()).status,503);await f.beat();assert.equal((await f.submit()).status,202);f.advance(31000);assert.equal((await f.req('/api/renders/capabilities')).data.workerOnline,false);});
test('render authorization, CSRF, owner scope and stale project version are enforced',async t=>{
 const f=await fixture(t);await f.beat();assert.equal((await f.submit({},{})).status,401);assert.equal((await f.submit({}, {Cookie:f.owner.Cookie})).status,403);assert.equal((await f.submit({},f.other)).status,404);
 assert.equal((await f.submit({version:0})).status,409);assert.equal((await f.submit({revisionId:'stale'})).status,409);assert.equal((await f.submit({model:{}})).status,400);assert.equal((await f.submit({settings:{textureURL:'https://evil.test'}})).status,422);
});
test('snapshot requests are idempotent and cannot bypass claim exclusivity',async t=>{
 const f=await fixture(t);await f.beat();const a=await f.submit(),b=await f.submit();assert.equal(a.data.job.id,b.data.job.id);assert.equal(b.data.reused,true);
 const claim=await f.req('/api/render-worker/claim',{method:'POST',headers:f.wh,body:{}});assert.equal(claim.data.job.id,a.data.job.id);assert.ok(claim.data.job.lease);assert.equal(claim.data.job.snapshot.source.revisionId,f.h.revisions[0].id);
 assert.equal((await f.req('/api/render-worker/claim',{method:'POST',headers:f.wh,body:{}})).data.job,null);
 const normal=await f.req('/api/renders/'+a.data.job.id,{headers:f.owner});assert.ok(!JSON.stringify(normal.data).includes(claim.data.job.lease));assert.equal(normal.data.job.status,'running');
 assert.equal((await f.req('/api/renders/'+a.data.job.id,{headers:f.other})).status,404);
});
test('cancel revokes the worker lease and blocks publishing old results',async t=>{
 const f=await fixture(t);await f.beat();const {data:{job}}=await f.submit();const claim=await f.req('/api/render-worker/claim',{method:'POST',headers:f.wh,body:{}}),lease={'X-Render-Lease':claim.data.job.lease,...f.wh};
 assert.equal((await f.req(`/api/renders/${job.id}/cancel`,{method:'POST',headers:f.owner,body:{}})).status,200);
 assert.equal((await f.req(`/api/render-worker/jobs/${job.id}/complete`,{method:'POST',headers:lease,body:{}})).status,409);
 assert.equal((await f.req(`/api/renders/${job.id}/files/model.glb`,{headers:f.owner})).status,404);
});
test('lease expiry becomes failed, explicit retry is bounded and preserves source revision',async t=>{
 const f=await fixture(t);await f.beat();const {data:{job}}=await f.submit();await f.req('/api/render-worker/claim',{method:'POST',headers:f.wh,body:{}});f.advance(120001);
 const failed=await f.req('/api/renders/'+job.id,{headers:f.owner});assert.equal(failed.data.job.errorCode,'WORKER_LOST');await f.beat();const retry=await f.req(`/api/renders/${job.id}/retry`,{method:'POST',headers:f.owner,body:{}});assert.equal(retry.status,202);assert.equal(retry.data.job.attempt,2);assert.equal(retry.data.job.revisionId,job.revisionId);
 await f.req('/api/render-worker/claim',{method:'POST',headers:f.wh,body:{}});f.advance(120001);await f.beat();assert.equal((await f.req(`/api/renders/${job.id}/retry`,{method:'POST',headers:f.owner,body:{}})).status,409);
});
test('jobs are bound to their saved revision and expose staleness after later edits',async t=>{
 const f=await fixture(t);await f.beat();const {data:{job}}=await f.submit();const model=clone(current(f.h));model.title='Later version';const updated=pushHistory(f.h,model,'rename');
 assert.equal((await f.req('/api/projects/'+f.h.projectId,{method:'PUT',headers:f.owner,body:{history:updated,version:1}})).status,200);
 assert.equal((await f.req('/api/renders/'+job.id,{headers:f.owner})).data.job.stale,true);
});
test('wrong worker secret, absent leases and unrecognised worker paths are rejected',async t=>{
 const f=await fixture(t);await f.beat();const {data:{job}}=await f.submit();assert.equal((await f.req('/api/render-worker/claim',{method:'POST',body:{}})).status,401);
 await f.req('/api/render-worker/claim',{method:'POST',headers:f.wh,body:{}});
 assert.equal((await f.req(`/api/render-worker/jobs/${job.id}/heartbeat`,{method:'POST',headers:f.wh,body:{}})).status,409);
 assert.equal((await f.req('/api/render-worker/unknown',{headers:f.wh})).status,404);
});
test('per-user pending job cap prevents unbounded render requests',async t=>{const f=await fixture(t);await f.beat();assert.equal((await f.submit()).status,202);assert.equal((await f.submit({settings:{finish:'white'}})).status,202);assert.equal((await f.submit({settings:{finish:'slate'}})).status,429);});

// Stream a worker message slowly to reproduce cancellation during await body().
test('worker failure arriving after cancellation cannot resurrect a cancelled job',async t=>{
 const f=await fixture(t);await f.beat();const {data:{job}}=await f.submit();const {data:{job:claimed}}=await f.req('/api/render-worker/claim',{method:'POST',headers:f.wh,body:{}});
 const http=await import('node:http');let finish;
 const response=new Promise((resolve,reject)=>{const request=http.request(f.base+`/api/render-worker/jobs/${job.id}/fail`,{method:'POST',headers:{Origin:origin,'Content-Type':'application/json',...f.wh,'X-Render-Lease':claimed.lease}},res=>{res.resume();res.on('end',()=>resolve(res.statusCode));});request.on('error',reject);request.write('{');finish=()=>request.end('"code":"BLENDER_FAILED"}');});
 await new Promise(r=>setTimeout(r,25));await f.req(`/api/renders/${job.id}/cancel`,{method:'POST',headers:f.owner,body:{}});finish();
 assert.equal(await response,409);assert.equal((await f.req('/api/renders/'+job.id,{headers:f.owner})).data.job.status,'cancelled');
});
test('concurrent retries can consume only the single allowed retry',async t=>{
 const f=await fixture(t);await f.beat();const {data:{job}}=await f.submit();await f.req('/api/render-worker/claim',{method:'POST',headers:f.wh,body:{}});f.advance(120001);await f.beat();
 const results=await Promise.all([1,2].map(()=>f.req(`/api/renders/${job.id}/retry`,{method:'POST',headers:f.owner,body:{}})));
 assert.deepEqual(results.map(r=>r.status).sort(),[202,409]);assert.equal((await f.req('/api/renders/'+job.id,{headers:f.owner})).data.job.attempt,2);
});
test('rewritten geometry with a reused revision ID is still stale',async t=>{
 const f=await fixture(t);await f.beat();const {data:{job}}=await f.submit();const changed=clone(f.h);changed.revisions[0].model.levels[0].rooms.find(r=>r.kind==='bedroom'||r.kind==='majlis').height-=.1;
 assert.equal((await f.req('/api/projects/'+f.h.projectId,{method:'PUT',headers:f.owner,body:{history:changed,version:1}})).status,200);
 assert.equal((await f.req('/api/renders/'+job.id,{headers:f.owner})).data.job.stale,true);
});
