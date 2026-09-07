/** Isolated Docker image + durable-volume lifecycle/restore smoke. Never uses an existing volume. */
import { execFileSync } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { writeFile,mkdir } from 'node:fs/promises';
import assert from 'node:assert/strict';
import { generate,understand,createHistory } from '../shared/model.js';
const suffix=Date.now().toString(36),image='masar-ci:'+suffix,container='masar-ci-'+suffix,volume='masar-ci-data-'+suffix,origin='https://masar.example.test';
const history=createHistory(generate(understand('أرض 20×25 ثلاثة أدوار خمس غرف نوم'))),results=[];
const docker=(...args)=>execFileSync('docker',args,{encoding:'utf8',timeout:180000,stdio:['ignore','pipe','pipe']}).trim();
let base;
async function start(dbPath='/app/data/masar.sqlite'){
 docker('run','-d','--name',container,'--read-only','--cap-drop=ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,size=32m','-p','127.0.0.1::3000','-e','PUBLIC_ORIGIN='+origin,'-e','ALLOW_REGISTRATION=true','-e','PERSISTENCE_CLASS=persistent','-e','DB_PATH='+dbPath,'-v',volume+':/app/data',image);
 const port=docker('port',container,'3000/tcp').split(':').at(-1);base='http://127.0.0.1:'+port;
 for(let i=0;i<120;i++){try{const r=await fetch(base+'/api/ready');if(r.ok)return;}catch{}await sleep(250);}throw Error('Container readiness deadline');
}
async function req(url,{method='GET',body,cookie,csrf}={}){const res=await fetch(base+url,{method,headers:{...(method!=='GET'?{Origin:origin,'Content-Type':'application/json'}:{}),...(cookie?{Cookie:cookie}:{}),...(csrf?{'X-CSRF-Token':csrf}:{})},body:body===undefined?undefined:JSON.stringify(body)});const raw=await res.text();let data;try{data=JSON.parse(raw);}catch{data=raw;}return {status:res.status,data,headers:res.headers};}
try{
 docker('build','-t',image,'.');results.push('Image build on pinned Node release');docker('volume','create',volume);await start();
 const health=await req('/api/health');assert.equal(health.data.persistenceClass,'persistent');assert.equal(health.data.version,'4.1.0');assert.equal((await req('/')).status,200);results.push('Non-root read-only container serves full UI and DB readiness');
 const credentials={name:'Docker fixture',email:'docker@example.test',password:'Disposable-test-password-2026!'};
 const registered=await req('/api/auth/register',{method:'POST',body:credentials});assert.equal(registered.status,201);assert.match(registered.headers.get('set-cookie'),/Secure/);
 let auth={cookie:registered.headers.get('set-cookie').split(';')[0],csrf:registered.data.csrf};
 assert.equal((await req('/api/projects/'+history.projectId,{method:'PUT',body:{history,version:0},...auth})).status,200);results.push('Production-origin authentication, Secure cookie and versioned save');
 assert.equal((await req('/server/server.mjs')).status,404);assert.equal((await req('/tools/backup.mjs')).status,404);results.push('Server/operator sources are not publicly served');
 docker('stop',container);docker('rm',container);await start();assert.deepEqual((await req('/api/projects/'+history.projectId,auth)).data.history,history);results.push('Entire container replacement retains exact history on dedicated volume');
 docker('exec',container,'node','tools/backup.mjs','create','/app/data/masar.sqlite','/app/data/snapshot.sqlite');
 docker('exec',container,'node','tools/backup.mjs','restore','/app/data/snapshot.sqlite','/app/data/restored.sqlite');
 docker('stop',container);docker('rm',container);await start('/app/data/restored.sqlite');
 assert.equal((await req('/api/projects',auth)).status,401);const login=await req('/api/auth/login',{method:'POST',body:credentials});assert.equal(login.status,200);
 auth={cookie:login.headers.get('set-cookie').split(';')[0],csrf:login.data.csrf};assert.deepEqual((await req('/api/projects/'+history.projectId,auth)).data.history,history);results.push('Consistent backup restoration retains data and invalidates old sessions');
 await mkdir('test-output',{recursive:true});await writeFile('test-output/docker-report.json',JSON.stringify({status:'PASS',checks:results.length,results,scope:'Disposable local Docker containers and one dedicated volume; not proof of cloud disk provisioning'},null,2));console.log(JSON.stringify({status:'PASS',checks:results.length,results}));
}finally{try{docker('rm','-f',container);}catch{}try{docker('volume','rm',volume);}catch{}try{docker('image','rm',image);}catch{}}
