/** Real Blender, real HTTP queue, no customer database and no mock renderer. */
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,rm,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';import os from 'node:os';import path from 'node:path';import net from 'node:net';
import {createApp} from '../server/server.mjs';
import {generate,understand,createHistory,current,clone,pushHistory} from '../shared/model.js';
import {createRenderScene,stableJSON} from '../shared/render-scene.js';
const output=path.resolve('test-output/blender');await mkdir(output,{recursive:true});
const temporary=await mkdtemp(path.join(os.tmpdir(),'masar-real-blender-')),checks=[],password='Blender-CI-Test-Only-12345',secret='blender-ci-disposable-worker-token-123456789';
const check=(name,value)=>{assert.ok(value,name);checks.push(name);};
const probe=net.createServer();await new Promise(r=>probe.listen(0,'127.0.0.1',r));const port=probe.address().port;await new Promise(r=>probe.close(r));const base='http://127.0.0.1:'+port;
const app=await createApp({production:false,port,origin:base,dbPath:path.join(temporary,'db.sqlite'),render:{enabled:true,workerToken:secret,outputDir:path.join(temporary,'artifacts')}});
await new Promise(r=>app.server.listen(port,'127.0.0.1',r));
async function req(route,{method='GET',body,headers={}}={}) {const res=await fetch(base+route,{method,headers:{Origin:base,'Content-Type':'application/json',...headers},body:body===undefined?undefined:JSON.stringify(body)});return{status:res.status,data:await res.json(),headers:res.headers};}
try {
    const reg=await req('/api/auth/register',{method:'POST',body:{name:'Render CI',email:'blender-ci@example.test',password}});check('register isolated owner',reg.status===201);
    const owner={Cookie:reg.headers.get('set-cookie').split(';')[0],'X-CSRF-Token':reg.data.csrf};
    const h=createHistory(generate(understand('أرض 20×25 ثلاثة أدوار خمس غرف نوم'))),before=JSON.stringify(h),revision=h.revisions[0].id;
    check('save canonical project', (await req('/api/projects/'+h.projectId,{method:'PUT',headers:owner,body:{history:h,version:0}})).status===200);
    const heartbeat=await req('/api/render-worker/heartbeat',{method:'POST',headers:{Authorization:'Bearer '+secret},body:{version:'4.5.13'}});check('worker heartbeat',heartbeat.status===200);
    const created=await req('/api/renders',{method:'POST',headers:owner,body:{projectId:h.projectId,version:1,revisionId:revision,settings:{finish:'warm',quality:'preview',furniture:true}}});check('queue immutable revision',created.status===202);
    const id=created.data.job.id;
    const scene=createRenderScene(current(h),revision,{finish:'warm',quality:'preview',furniture:true});await writeFile(path.join(output,'scene.json'),stableJSON(scene));
    const child=spawn(process.execPath,['render-worker/worker.mjs',...(process.env.MASAR_RENDER_DOCKER==='true'?[]:['--native']),'--once'],{env:{...process.env,MASAR_API_URL:base,RENDER_WORKER_TOKEN:secret,RENDER_UNSANDBOXED_LOCAL:'true'},stdio:['ignore','pipe','pipe']});
    let log='';child.stdout.on('data',b=>{log+=b;});child.stderr.on('data',b=>{log+=b;});
    const timer=setTimeout(()=>child.kill('SIGKILL'),360000);
    const exit=await new Promise((r,j)=>{child.once('error',j);child.once('exit',r);});clearTimeout(timer);await writeFile(path.join(output,'worker.log'),log);if(exit!==0)console.error(log);check('real Blender worker exited successfully',exit===0);
    const {data:{job}}=await req('/api/renders/'+id,{headers:owner});check('result published only after validation',job.status==='succeeded');check('five verified artifacts',job.files.length===5);check('current revision tag',!job.stale&&job.revisionId===revision);
    check('source digest',job.snapshotHash===createHash('sha256').update(stableJSON(scene)).digest('hex'));
    for(const f of job.files){const res=await fetch(base+f.url,{headers:owner});const bytes=Buffer.from(await res.arrayBuffer());check(f.name+' private download',res.status===200);check(f.name+' sha256',createHash('sha256').update(bytes).digest('hex')===f.sha256);await writeFile(path.join(output,f.name),bytes);}
    const unauthorized=await fetch(base+job.files[0].url);check('artifact blocks anonymous access',unauthorized.status===401);
    const fetched=await req('/api/projects/'+h.projectId,{headers:owner});check('render leaves complete history untouched',JSON.stringify(fetched.data.history)===before);
    if(process.env.MASAR_RENDER_BROWSER==='true') {
        const browserTest=spawn('python',['tests/browser_render.py'],{env:process.env,stdio:['pipe','pipe','pipe']});
        let browserLog='';browserTest.stdout.on('data',b=>{browserLog+=b;});browserTest.stderr.on('data',b=>{browserLog+=b;});
        browserTest.stdin.end(JSON.stringify({base,projectId:h.projectId,email:'blender-ci@example.test',password}));
        const browserExit=await new Promise((r,j)=>{browserTest.once('error',j);browserTest.once('exit',r);});
        await writeFile(path.join(output,'browser-render.log'),browserLog);if(browserExit!==0)console.error(browserLog);check('real browser visualization and private artifacts',browserExit===0);
    }
    const next=clone(current(h));next.title='New revision after render';const newer=pushHistory(h,next,'New revision');await req('/api/projects/'+h.projectId,{method:'PUT',headers:owner,body:{history:newer,version:1}});
    check('old render is marked stale', (await req('/api/renders/'+id,{headers:owner})).data.job.stale);
    check('owner deletion succeeds',(await req('/api/auth/account',{method:'DELETE',headers:owner,body:{password}})).status===200);
    check('deleted owner cannot access files',(await fetch(base+job.files[0].url,{headers:owner})).status===401);
    check('render job FK cascades with account',app.db.prepare('SELECT COUNT(*) n FROM render_jobs').get().n===0);
    const report={status:'PASS',passed:checks.length,failed:0,checks,snapshotHash:job.snapshotHash,sourceRevision:revision,scope:'Real HTTP API + actual Blender worker; not a paid/cloud worker deployment',workerMode:process.env.MASAR_RENDER_DOCKER==='true'?'isolated-docker':'trusted-native'};
    await writeFile(path.join(output,'e2e-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
} finally {await new Promise(r=>app.server.close(r));await rm(temporary,{recursive:true,force:true});}
