import {verifyRenderGLB} from '../shared/render-glb.js';
/** Optional render queue. Owner-authenticated snapshots, worker leases, private artifacts.
 * Not enabled on the free public preview. No executable or arbitrary file/URL inputs.
 */
import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import { mkdir, readFile, writeFile, rename, rm, readdir, lstat } from 'node:fs/promises';
import path from 'node:path';
import { current, assertHistory } from '../shared/model.js';
import { createRenderScene, stableJSON, RENDER_PIPELINE } from '../shared/render-scene.js';
const digest = x => createHash('sha256').update(x).digest('hex');
const ID = /^[a-f0-9]{32}$/;
const NAMES = ['model.blend','model.glb','exterior.png','interior.png','manifest.json'];
const MIME = { 'model.blend':'application/octet-stream','model.glb':'model/gltf-binary','exterior.png':'image/png','interior.png':'image/png','manifest.json':'application/json' };
const reject = (status,message) => { const e=Error(message); e.status=status; throw e; };
const equal = (a,b) => typeof a==='string' && typeof b==='string' && Buffer.byteLength(a)===Buffer.byteLength(b) && timingSafeEqual(Buffer.from(a),Buffer.from(b));
export async function renderService({db,root,auth,body,json,config={}}) {
    const enabled=config.enabled ?? process.env.BLENDER_RENDER_ENABLED==='true';
    const secret=config.workerToken ?? process.env.RENDER_WORKER_TOKEN ?? '';
    if(enabled && (secret.length<32 || secret.length>256)) throw Error('RENDER_WORKER_TOKEN must contain 32–256 characters before rendering can be enabled.');
    const output=path.resolve(config.outputDir ?? process.env.RENDER_OUTPUT_DIR ?? path.join(root,'data','renders'));
    const now=config.now || Date.now, leaseMs=120000, ttlMs=7*86400000;
    db.exec(`CREATE TABLE IF NOT EXISTS render_jobs (
        id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        project_id TEXT NOT NULL, revision_id TEXT NOT NULL, project_version INTEGER NOT NULL,
        snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed','cancelled')),
        created INTEGER NOT NULL, updated INTEGER NOT NULL, attempt INTEGER NOT NULL DEFAULT 1,
        lease_hash TEXT, lease_expires INTEGER, error_code TEXT,
        FOREIGN KEY(project_id,user_id) REFERENCES projects(id,user_id) ON DELETE CASCADE);
        CREATE INDEX IF NOT EXISTS render_jobs_owner ON render_jobs(user_id,project_id,created);
        CREATE TABLE IF NOT EXISTS render_artifacts(job_id TEXT NOT NULL REFERENCES render_jobs(id) ON DELETE CASCADE,name TEXT NOT NULL,bytes INTEGER NOT NULL,sha256 TEXT NOT NULL,PRIMARY KEY(job_id,name));
        CREATE TABLE IF NOT EXISTS render_worker_state(id INTEGER PRIMARY KEY CHECK(id=1),seen INTEGER NOT NULL,version TEXT NOT NULL);`);
    if(enabled) await mkdir(output,{recursive:true,mode:0o700});
    function worker(req) {
        if(!enabled) reject(503,'خدمة Blender غير مفعلة.');
        const token=String(req.headers.authorization||'').replace(/^Bearer /,'');
        if(!equal(token,secret)) reject(401,'عامل إخراج غير مصرح.');
    }
    function online() { return enabled && (db.prepare('SELECT seen FROM render_worker_state WHERE id=1').get()?.seen ?? 0)>now()-30000; }
    function record(id) { if(!ID.test(id)) reject(404,'مهمة الإخراج غير موجودة.'); return db.prepare('SELECT * FROM render_jobs WHERE id=?').get(id); }
    function owned(id,userId) { const row=record(id); if(!row || row.user_id!==userId) reject(404,'مهمة الإخراج غير موجودة.'); return row; }
    function leased(req,id) {
        worker(req);const row=record(id);
        if(!row || row.status!=='running' || row.lease_expires<now() || !equal(digest(String(req.headers['x-render-lease']||'')),row.lease_hash)) reject(409,'انتهى تفويض هذه المهمة أو أُلغيت.');
        return row;
    }
    function summary(row) {
        const project=db.prepare('SELECT version,document FROM projects WHERE id=? AND user_id=?').get(row.project_id,row.user_id);
        let stale=true; if(project) {const h=JSON.parse(project.document);try {stale=h.revisions[h.cursor].id!==row.revision_id || digest(stableJSON(createRenderScene(current(h),row.revision_id,JSON.parse(row.snapshot).settings)))!==row.snapshot_hash;} catch {stale=true;}}
        return {id:row.id,projectId:row.project_id,revisionId:row.revision_id,projectVersion:row.project_version,snapshotHash:row.snapshot_hash,status:row.status,created:row.created,updated:row.updated,attempt:row.attempt,errorCode:row.error_code,stale,settings:JSON.parse(row.snapshot).settings,
            files:row.status==='succeeded'?db.prepare('SELECT name,bytes,sha256 FROM render_artifacts WHERE job_id=? ORDER BY name').all(row.id).map(f=>({...f,url:`/api/renders/${row.id}/files/${f.name}`})):[]};
    }
    function sweep() {
        db.prepare("UPDATE render_jobs SET status='failed',error_code='WORKER_LOST',lease_hash=NULL,lease_expires=NULL,updated=? WHERE status='running' AND lease_expires<?").run(now(),now());
        db.prepare('DELETE FROM render_jobs WHERE created<?').run(now()-ttlMs);
    }
    async function prune() {
        if(!enabled) return;
        sweep();
        for(const entry of await readdir(output,{withFileTypes:true})) if(ID.test(entry.name)) {
            const row=record(entry.name);
            if(!row || ['failed','cancelled'].includes(row.status)) await rm(path.join(output,entry.name),{recursive:true,force:true});
        }
    }
    await prune();
    async function artifactBytes(jobId,name) {
        if(!ID.test(jobId) || !NAMES.includes(name)) reject(404,'ملف غير موجود.');
        const file=path.join(output,jobId,name);const st=await lstat(file);
        if(!st.isFile() || st.isSymbolicLink() || st.size>24_000_000) reject(422,'ملف إخراج غير صالح.');
        return readFile(file);
    }
    function validateArtifact(name,data,scene) {
        if(name.endsWith('.png')) {
            if(data.length<33 || !data.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])) || data.toString('ascii',12,16)!=='IHDR' || data.readUInt32BE(16)!==scene.resolution.width || data.readUInt32BE(20)!==scene.resolution.height) reject(422,'أبعاد أو صيغة الصورة غير صالحة.');
        } else if(name==='model.blend') {
            if(data.toString('ascii',0,7)!=='BLENDER') reject(422,'ملف Blender غير صالح.');
        } else if(name==='model.glb') {
            if(data.length<24 || data.toString('ascii',0,4)!=='glTF' || data.readUInt32LE(4)!==2 || data.readUInt32LE(8)!==data.length || data.readUInt32LE(16)!==0x4e4f534a) reject(422,'ملف GLB غير صالح.');
            let g;try {g=JSON.parse(data.toString('utf8',20,20+data.readUInt32LE(12)));}catch{reject(422,'GLB JSON غير صالح.');}
            if((g.buffers||[]).some(b=>b.uri) || (g.images||[]).some(i=>i.uri) || g.extensionsRequired?.length) reject(422,'المجسم يجب أن يكون ذاتي المحتوى بلا روابط أو امتدادات إضافية.');
            try{verifyRenderGLB(data,scene);}catch(e){reject(422,e.message);}
            const meshNodes=(g.nodes||[]).filter(n=>n.mesh!==undefined), ids=meshNodes.map(n=>n.extras?.objectId);
            if(ids.length!==scene.objects.length || new Set(ids).size!==ids.length || scene.objects.some(o=>!ids.includes(o.id))) reject(422,'فقد المجسم معرّفات عناصر مسار.');
        } else if(name==='manifest.json') {
            let m;try {m=JSON.parse(data);}catch{reject(422,'تقرير الإخراج غير صالح.');}
            if(m.schema!=='masar-render-result-1' || m.pipeline!==RENDER_PIPELINE || stableJSON(m.source)!==stableJSON(scene.source)) reject(422,'التقرير لا يطابق مصدر التصميم.');
        }
    }
    async function handle(req,res,p,method) {
        if(!p.startsWith('/api/renders') && !p.startsWith('/api/render-worker/')) return false;
        sweep();
        if(p==='/api/renders/capabilities' && method==='GET') {
            json(res,200,{enabled,workerOnline:online(),pipeline:RENDER_PIPELINE,formats:NAMES,retentionDays:7,storage:config.storageClass||process.env.PERSISTENCE_CLASS||'operator-managed',maxAttempts:2});return true;
        }
        if(p==='/api/render-worker/heartbeat' && method==='POST') {
            worker(req);const b=await body(req);
            if(typeof b.version!=='string'||!/^4\.5\.\d+$/.test(b.version)) reject(400,'إصدار Blender غير مدعوم.');
            db.prepare('INSERT INTO render_worker_state VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET seen=excluded.seen,version=excluded.version').run(now(),b.version);
            await prune();json(res,200,{ok:true});return true;
        }
        if(p==='/api/render-worker/claim' && method==='POST') {
            worker(req);await body(req);
            // Synchronous claim is atomic in this single API process. Multi-node API needs Postgres.
            if(db.prepare("SELECT COUNT(*) n FROM render_jobs WHERE status='running'").get().n>=1) {json(res,200,{job:null});return true;}
            const row=db.prepare("SELECT * FROM render_jobs WHERE status='queued' ORDER BY created,id LIMIT 1").get();
            if(!row){json(res,200,{job:null});return true;}
            const lease=randomBytes(32).toString('hex');
            db.prepare("UPDATE render_jobs SET status='running',lease_hash=?,lease_expires=?,updated=? WHERE id=? AND status='queued'").run(digest(lease),now()+leaseMs,now(),row.id);
            json(res,200,{job:{id:row.id,snapshot:JSON.parse(row.snapshot),snapshotHash:row.snapshot_hash,lease,leaseMs}});return true;
        }
        const wr=p.match(/^\/api\/render-worker\/jobs\/([a-f0-9]{32})\/(heartbeat|complete|fail|files\/([a-z.]+))$/);
        if(wr) {
            let row=leased(req,wr[1]);const action=wr[2],name=wr[3];
            if(action==='heartbeat' && method==='POST') {await body(req);leased(req,row.id);db.prepare('UPDATE render_jobs SET lease_expires=? WHERE id=?').run(now()+leaseMs,row.id);json(res,200,{ok:true});return true;}
            if(name && method==='PUT') {
                if(!NAMES.includes(name)) reject(404,'اسم ملف غير مدعوم.');
                let size=0;const chunks=[];for await(const chunk of req){size+=chunk.length;if(size>24_000_000)reject(413,'الملف يتجاوز 24 ميجابايت.');chunks.push(chunk);}
                const data=Buffer.concat(chunks),scene=JSON.parse(row.snapshot);validateArtifact(name,data,scene);row=leased(req,row.id);
                const dir=path.join(output,row.id);await mkdir(dir,{recursive:true,mode:0o700});
                const tmp=path.join(dir,name+'.'+randomBytes(8).toString('hex')+'.part');
                try {await writeFile(tmp,data,{mode:0o600,flag:'wx'});leased(req,row.id);await rename(tmp,path.join(dir,name));leased(req,row.id);db.prepare('INSERT INTO render_artifacts VALUES(?,?,?,?) ON CONFLICT(job_id,name) DO UPDATE SET bytes=excluded.bytes,sha256=excluded.sha256').run(row.id,name,data.length,digest(data));}
                finally{await rm(tmp,{force:true});}
                json(res,200,{stored:true,sha256:digest(data)});return true;
            }
            if(action==='complete' && method==='POST') {
                await body(req);const manifest=JSON.parse(await artifactBytes(row.id,'manifest.json')),scene=JSON.parse(row.snapshot);
                if(manifest.snapshotHash!==row.snapshot_hash || !Array.isArray(manifest.geometry) || manifest.geometry.length!==scene.objects.length) reject(422,'التقرير لا يطابق النسخة.');
                const map=new Map(manifest.geometry.map(g=>[g.objectId,g]));
                if(map.size!==scene.objects.length) reject(422,'معرّفات مكررة في التقرير.');
                for(const o of scene.objects) {
                    const g=map.get(o.id),expected=[...o.min,...o.min.map((v,i)=>v+o.size[i])];
                    const actual=[...(g?.min||[]),...(g?.max||[])];
                    if(g?.elementId!==o.elementId || actual.length!==6 || actual.some((n,i)=>!Number.isFinite(n)||Math.abs(n-expected[i])>.00005)) reject(422,'فشل تطابق أبعاد المجسم مع التصميم.');
                }
                for(const name of NAMES.filter(n=>n!=='manifest.json')) {
                    const bytes=await artifactBytes(row.id,name);const expected=manifest.files?.[name];
                    if(!expected || expected.bytes!==bytes.length || expected.sha256!==digest(bytes)) reject(422,'فشل تحقق بصمة ملف الإخراج.');
                }
                leased(req,row.id);db.prepare("UPDATE render_jobs SET status='succeeded',updated=?,lease_hash=NULL,lease_expires=NULL WHERE id=?").run(now(),row.id);
                json(res,200,{job:summary(record(row.id))});return true;
            }
            if(action==='fail' && method==='POST') {
                const b=await body(req);leased(req,row.id);const code=['BLENDER_FAILED','TIMEOUT','ARTIFACT_INVALID'].includes(b.code)?b.code:'BLENDER_FAILED';
                db.prepare("UPDATE render_jobs SET status='failed',error_code=?,updated=?,lease_hash=NULL,lease_expires=NULL WHERE id=?").run(code,now(),row.id);
                await prune();json(res,200,{ok:true});return true;
            }
            reject(405,'الطريقة غير مدعومة.');
        }
        if(p.startsWith('/api/render-worker/')) {worker(req);reject(404,'المسار غير موجود.');}
        const user=auth(req,method!=='GET'),b=(method==='POST')?await body(req):{};
        if(p==='/api/renders' && method==='GET') {
            json(res,200,{jobs:db.prepare('SELECT * FROM render_jobs WHERE user_id=? ORDER BY created DESC LIMIT 30').all(user.user_id).map(summary)});return true;
        }
        if(p==='/api/renders' && method==='POST') {
            if(!enabled||!online())reject(503,'عامل Blender غير متصل؛ تستطيع تنزيل مشهد الإخراج وتشغيله محليًا.');
            if(Object.keys(b).some(k=>!['projectId','version','revisionId','settings'].includes(k)))reject(400,'حقول طلب غير مدعومة.');
            const project=db.prepare('SELECT * FROM projects WHERE id=? AND user_id=?').get(String(b.projectId),user.user_id);
            if(!project)reject(404,'احفظ المشروع في حسابك أولًا.');
            const h=assertHistory(JSON.parse(project.document)),revision=h.revisions[h.cursor];
            if(project.version!==b.version || revision.id!==b.revisionId)reject(409,'نسخة الحساب مختلفة. احفظ آخر نسخة ثم أعد الطلب.');
            let scene;try {scene=createRenderScene(current(h),revision.id,b.settings);}catch(e){reject(422,e.message);}
            const snapshot=stableJSON(scene),hash=digest(snapshot);
            const previous=db.prepare("SELECT * FROM render_jobs WHERE user_id=? AND snapshot_hash=? AND status IN ('queued','running','succeeded') ORDER BY created DESC LIMIT 1").get(user.user_id,hash);
            if(previous){json(res,200,{job:summary(previous),reused:true});return true;}
            const daily=db.prepare('SELECT COUNT(*) n FROM render_jobs WHERE user_id=? AND created>?').get(user.user_id,now()-86400000).n;
            const pending=db.prepare("SELECT COUNT(*) n FROM render_jobs WHERE user_id=? AND status IN ('queued','running')").get(user.user_id).n;
            const total=db.prepare('SELECT COUNT(*) n FROM render_jobs').get().n;
            if(daily>=4||pending>=2||total>=100)reject(429,'بلغت حدود طابور الإخراج. حاول لاحقًا.');
            const id=randomBytes(16).toString('hex');
            db.prepare("INSERT INTO render_jobs(id,user_id,project_id,revision_id,project_version,snapshot,snapshot_hash,status,created,updated) VALUES(?,?,?,?,?,?,?,'queued',?,?)").run(id,user.user_id,b.projectId,revision.id,b.version,snapshot,hash,now(),now());
            json(res,202,{job:summary(record(id))});return true;
        }
        const match=p.match(/^\/api\/renders\/([a-f0-9]{32})(?:\/(cancel|retry|files\/([a-z.]+)))?$/);
        if(!match)reject(404,'المهمة غير موجودة.');
        const row=owned(match[1],user.user_id),action=match[2],name=match[3];
        if(!action && method==='GET'){json(res,200,{job:summary(row)});return true;}
        if(action==='cancel' && method==='POST') {
            if(!['queued','running','cancelled'].includes(row.status))reject(409,'المهمة انتهت بالفعل.');
            db.prepare("UPDATE render_jobs SET status='cancelled',lease_hash=NULL,lease_expires=NULL,updated=? WHERE id=?").run(now(),row.id);await prune();json(res,200,{job:summary(record(row.id))});return true;
        }
        if(action==='retry' && method==='POST') {
            if(!online())reject(503,'عامل Blender غير متصل.');
            if(row.status!=='failed'||row.attempt>=2)reject(409,'تتوفر إعادة محاولة واحدة للمهمة الفاشلة.');
            const active=db.prepare("SELECT COUNT(*) n FROM render_jobs WHERE user_id=? AND status IN ('queued','running')").get(user.user_id).n;
            if(active>=2)reject(429,'طابور حسابك ممتلئ.');
            await rm(path.join(output,row.id),{recursive:true,force:true});
            db.prepare('DELETE FROM render_artifacts WHERE job_id=?').run(row.id);
            const retried=db.prepare("UPDATE render_jobs SET status='queued',attempt=attempt+1,error_code=NULL,updated=? WHERE id=? AND status='failed' AND attempt<2").run(now(),row.id);
            if(retried.changes!==1)reject(409,'تغيرت حالة المهمة؛ لم تُعد المحاولة مرتين.');
            json(res,202,{job:summary(record(row.id))});return true;
        }
        if(name && method==='GET') {
            if(row.status!=='succeeded'||!NAMES.includes(name))reject(404,'ملف الإخراج غير متاح.');
            const buffer=await artifactBytes(row.id,name);
            res.writeHead(200,{'Content-Type':MIME[name],'Cache-Control':'no-store','Content-Disposition':`${name.endsWith('.png')?'inline':'attachment'}; filename="${name}"`,'X-Masar-Revision':encodeURIComponent(row.revision_id),'X-Masar-Snapshot':row.snapshot_hash});res.end(buffer);return true;
        }
        reject(405,'الطريقة غير مدعومة.');
    }
    return {handle,prune};
}
