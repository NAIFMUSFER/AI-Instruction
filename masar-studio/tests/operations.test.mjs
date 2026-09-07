import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp,rm,readFile,writeFile,stat,copyFile } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { DatabaseSync } from 'node:sqlite';
import { createApp } from '../server/server.mjs';
import { createBackup,restoreBackup } from '../tools/backup.mjs';
import { createHistory,generate,understand } from '../shared/model.js';

const start=async dbPath=>{const app=await createApp({dbPath,origin:'http://masar.test',allowRegistration:true});await new Promise(r=>app.server.listen(0,'127.0.0.1',r));return {...app,close:()=>new Promise(r=>app.server.close(r))};};
test('Online WAL backup and verified restoration preserve data, revoke sessions and do not overwrite',async t=>{
 const dir=await mkdtemp(path.join(os.tmpdir(),'masar-dr-'));t.after(()=>rm(dir,{recursive:true,force:true}));
 const source=path.join(dir,'live.sqlite'),snapshot=path.join(dir,'snapshot.sqlite'),restored=path.join(dir,'restored.sqlite');
 const app=await start(source);t.after(app.close);const h=createHistory(generate(understand('أرض 20×25 ثلاثة أدوار خمس غرف نوم')));
 app.db.prepare('INSERT INTO users VALUES(?,?,?,?,?)').run('user-1','test@example.test','اختبار','test-hash','2026-01-01');
 app.db.prepare('INSERT INTO sessions VALUES(?,?,?,?)').run('test-session','user-1','test-csrf',Date.now()+60000);
 app.db.prepare('INSERT INTO projects VALUES(?,?,?,?,?,?)').run(h.projectId,'user-1','محفوظ',JSON.stringify(h),1,'2026-01-01');
 const saved=await createBackup(source,snapshot);assert.equal(saved.counts.projects,1);assert.equal(saved.schemaVersion,1);assert.match(saved.sha256,/^[0-9a-f]{64}$/);
 assert.equal((await stat(snapshot)).mode&0o777,0o600);assert.equal((await stat(snapshot+'.json')).mode&0o777,0o600);assert.equal((await stat(source)).mode&0o777,0o600);
 app.db.prepare('UPDATE projects SET title=?').run('تغيير بعد النسخة');
 const result=await restoreBackup(snapshot,restored);assert.equal(result.sessionsInvalidated,true);
 const recovered=await start(restored);t.after(recovered.close);
 assert.equal(recovered.db.prepare('SELECT count(*) n FROM sessions').get().n,0);
 assert.equal(recovered.db.prepare('SELECT title FROM projects').get().title,'محفوظ');
 assert.deepEqual(JSON.parse(recovered.db.prepare('SELECT document FROM projects').get().document),h);
 assert.equal(app.db.prepare('SELECT title FROM projects').get().title,'تغيير بعد النسخة');
 const before=await readFile(snapshot);await assert.rejects(()=>createBackup(source,snapshot),/overwrite/);assert.deepEqual(await readFile(snapshot),before);
 await assert.rejects(()=>restoreBackup(snapshot,restored),/overwrite/);
});
test('Corrupted snapshot cannot be restored and does not create a target',async t=>{
 const dir=await mkdtemp(path.join(os.tmpdir(),'masar-corrupt-'));t.after(()=>rm(dir,{recursive:true,force:true}));
 const app=await start(path.join(dir,'source.sqlite'));t.after(app.close);const snap=path.join(dir,'snap.sqlite'),target=path.join(dir,'target.sqlite');
 await createBackup(path.join(dir,'source.sqlite'),snap);const content=await readFile(snap);content[400]^=0xff;await writeFile(snap,content);
 await assert.rejects(()=>restoreBackup(snap,target),/verification failed/);await assert.rejects(()=>stat(target),{code:'ENOENT'});
});
test('Backup refuses non-MASAR source databases',async t=>{
 const dir=await mkdtemp(path.join(os.tmpdir(),'masar-other-'));t.after(()=>rm(dir,{recursive:true,force:true}));const src=path.join(dir,'source.sqlite');
 const db=new DatabaseSync(src);db.exec('CREATE TABLE unrelated(x TEXT)');db.close();
 await assert.rejects(()=>createBackup(src,path.join(dir,'output.sqlite')),/Not a supported MASAR/);
});
for(const origin of ['https://user:pass@example.test','https://example.test/path','https://example.test?key=private','https://example.test#foo','ftp://example.test'])test('Server rejects non-origin configuration '+origin.split('@').at(-1),async()=>{await assert.rejects(()=>createApp({dbPath:':memory:',origin,production:true}),/PUBLIC_ORIGIN/);});
test('Server normalizes a trailing origin slash and discloses ephemeral storage',async t=>{
 const app=await createApp({dbPath:':memory:',origin:'https://masar.test/',production:true,persistenceClass:'ephemeral'});t.after(()=>new Promise(r=>app.server.close(r)));
 assert.equal(app.origin,'https://masar.test');await new Promise(r=>app.server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+app.server.address().port;
 const res=await fetch(base+'/api/health');assert.equal((await res.json()).persistenceClass,'ephemeral');assert.match(res.headers.get('strict-transport-security'),/31536000/);
 const ready=await(await fetch(base+'/api/ready')).json();assert.equal(ready.ready,true);assert.equal(ready.persistenceClass,'ephemeral');assert.match(ready.scope,/not proof/);
 assert.equal((await fetch(base+'/tools/backup.mjs')).status,404);
 const sw=await fetch(base+'/public/sw.js');assert.equal(sw.headers.get('service-worker-allowed'),'/');
});
test('Unknown database schema cannot be silently initialized or downgraded',async t=>{
 const dir=await mkdtemp(path.join(os.tmpdir(),'masar-future-'));t.after(()=>rm(dir,{recursive:true,force:true}));const file=path.join(dir,'future.sqlite');const db=new DatabaseSync(file);db.exec('PRAGMA user_version=999;CREATE TABLE retained(value TEXT);INSERT INTO retained VALUES(\'keep\')');db.close();
 await assert.rejects(()=>createApp({dbPath:file,origin:'http://localhost:3000'}),/newer MASAR/);
 const check=new DatabaseSync(file);assert.equal(check.prepare('PRAGMA user_version').get().user_version,999);assert.equal(check.prepare('SELECT value FROM retained').get().value,'keep');check.close();
});
