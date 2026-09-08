/** Separate pull worker. Secret is never passed into Blender, logs or result files.
 * Production default: per-job Docker sandbox with network disabled and resource limits.
 * --native is for a trusted local/CI host only, explicitly acknowledged via env.
 */
import { promisify } from 'node:util';
import { spawn, execFile } from 'node:child_process';
import { mkdtemp, writeFile, readFile, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { stableJSON } from '../shared/render-scene.js';
const ROOT=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const base=new URL(process.env.MASAR_API_URL || 'http://localhost:3000');
if(!['http:','https:'].includes(base.protocol)||base.pathname!=='/'||base.search||base.hash||base.username||base.password || (base.protocol!=='https:'&&!['localhost','127.0.0.1','[::1]'].includes(base.hostname))) throw Error('MASAR_API_URL requires an HTTPS origin, or loopback HTTP for local development.');
const token=process.env.RENDER_WORKER_TOKEN || '';
if(token.length<32) throw Error('RENDER_WORKER_TOKEN is required.');
const native=process.argv.includes('--native'),once=process.argv.includes('--once');
if(native && process.env.RENDER_UNSANDBOXED_LOCAL!=='true') throw Error('--native requires RENDER_UNSANDBOXED_LOCAL=true on a trusted local or CI host.');
const version='4.5.13',names=['model.blend','model.glb','exterior.png','interior.png','manifest.json'];
// A heartbeat is sent only after the actual processor executable/image is available.
const safeEnv=Object.fromEntries(['PATH','HOME','TMPDIR','LD_LIBRARY_PATH','SYSTEMROOT'].filter(k=>process.env[k]).map(k=>[k,process.env[k]]));
const probe=await promisify(execFile)(native?(process.env.BLENDER_BIN||'blender'):'docker',native?['--version']:['run','--rm','--network','none','--read-only','--cap-drop','ALL','masar-blender:4.5.13','--version'],{timeout:20000,maxBuffer:32768,env:safeEnv});
if(!/^Blender 4\.5\.13(?: LTS)?[\r\n]/.test(probe.stdout))throw Error('The worker requires Blender 4.5.13 LTS.');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function request(route,{json,bytes,lease,method='POST'}={}) {
    const res=await fetch(new URL(route,base),{method,redirect:'error',headers:{Origin:base.origin,Authorization:'Bearer '+token,...(lease?{'X-Render-Lease':lease}:{}),'Content-Type':bytes?'application/octet-stream':'application/json'},body:bytes||JSON.stringify(json||{}),signal:AbortSignal.timeout(25000)});
    if(!res.ok) {const e=Error('Render API returned '+res.status);e.status=res.status;throw e;}
    return res.json();
}
let stopping=false,active=null;
for(const signal of ['SIGINT','SIGTERM']) process.on(signal,()=>{stopping=true;active?.kill('SIGTERM');});
async function render(job) {
    const dir=await mkdtemp(path.join(os.tmpdir(),'masar-render-'));
    try {
        const raw=stableJSON(job.snapshot);
        if(createHash('sha256').update(raw).digest('hex')!==job.snapshotHash) throw Error('Snapshot hash mismatch');
        await writeFile(path.join(dir,'scene.json'),raw,{mode:0o600});
        let command,args;
        const flags=['--background','--factory-startup','--disable-autoexec','--offline-mode','--threads','2','--python-exit-code','1','--python'];
        if(native){command=process.env.BLENDER_BIN||'blender';args=[...flags,path.join(ROOT,'render-worker/build_scene.py'),'--','--input',path.join(dir,'scene.json'),'--output',path.join(dir,'out')];}
        else {
            command='docker';args=['run','--rm','--name',`masar-render-${job.id}`,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--memory','3g','--cpus','2','--user',`${process.getuid?.()??1000}:${process.getgid?.()??1000}`,'--tmpfs','/tmp:rw,nosuid,size=256m','-v',`${dir}:/work:rw`,'masar-blender:4.5.13',...flags,'/opt/masar/build_scene.py','--','--input','/work/scene.json','--output','/work/out'];
        }
        const env=Object.fromEntries(['PATH','HOME','TMPDIR','LD_LIBRARY_PATH','SYSTEMROOT'].filter(k=>process.env[k]).map(k=>[k,process.env[k]]));
        env.OMP_NUM_THREADS='2';env.OPENBLAS_NUM_THREADS='2';
        const child=spawn(command,args,{env,stdio:['ignore','pipe','pipe'],shell:false});active=child;
        // Bounded diagnostic tail stays local; never publish raw paths or secrets in API errors.
        let tail='',timedOut=false,cancelled=false,checking=false;
        const stopJob=()=>{
            child.kill('SIGKILL');
            if(!native) {const kill=spawn('docker',['rm','--force',`masar-render-${job.id}`],{env,stdio:'ignore',shell:false});kill.on('error',()=>{});}
        };
        const capture=buf=>{tail=(tail+buf.toString()).slice(-10000);};child.stdout.on('data',capture);child.stderr.on('data',capture);
        const timeout=setTimeout(()=>{timedOut=true;stopJob();},job.snapshot.settings.quality==='preview'?300000:600000);
        const heartbeat=setInterval(async()=>{
            if(checking)return;checking=true;
            try {await request('/api/render-worker/heartbeat',{json:{version}});await request(`/api/render-worker/jobs/${job.id}/heartbeat`,{lease:job.lease});}
            catch {cancelled=true;stopJob();}
            finally{checking=false;}
        },8000);
        let code;
        try {code=await new Promise((resolve,reject)=>{child.once('error',reject);child.once('exit',resolve);});}
        finally {clearTimeout(timeout);clearInterval(heartbeat);if(stopping)stopJob();active=null;}
        if(cancelled||stopping) return;
        if(code!==0) {
            await writeFile(path.join(dir,'failure.log'),tail,{mode:0o600});
            await request(`/api/render-worker/jobs/${job.id}/fail`,{lease:job.lease,json:{code:timedOut?'TIMEOUT':'BLENDER_FAILED'}});
            throw Error(timedOut?'Blender exceeded the job time budget':'Blender failed; no result published. '+tail.slice(-800));
        }
        await request(`/api/render-worker/jobs/${job.id}/heartbeat`,{lease:job.lease});
        for(const name of names) {
            const bytes=await readFile(path.join(dir,'out',name));
            if(bytes.length>24_000_000) throw Error('Render artifact exceeds upload budget');
            await request(`/api/render-worker/jobs/${job.id}/files/${name}`,{method:'PUT',bytes,lease:job.lease});
        }
        await request(`/api/render-worker/jobs/${job.id}/complete`,{lease:job.lease});
        console.log(JSON.stringify({jobId:job.id,status:'succeeded',snapshotHash:job.snapshotHash}));
    } catch(e) {
        if(e.status!==409) {
            try {await request(`/api/render-worker/jobs/${job.id}/fail`,{lease:job.lease,json:{code:'ARTIFACT_INVALID'}});}catch{}
            console.error(e.message);
            if(once) process.exitCode=1;
        }
    } finally {await rm(dir,{recursive:true,force:true});}
}
do {
    try {await request('/api/render-worker/heartbeat',{json:{version}});const {job}=await request('/api/render-worker/claim');if(job) await render(job);else if(!once)await sleep(4000);}
    catch(e) {console.error(e.message);if(once){process.exitCode=1;break;}await sleep(8000);}
} while(!once&&!stopping);
