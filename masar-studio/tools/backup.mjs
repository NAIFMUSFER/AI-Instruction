/** Operator-only consistent SQLite snapshots. Never serve this module over HTTP.
 * Backup files contain private account/project data; store them outside the web root.
 */
import { DatabaseSync, backup } from 'node:sqlite';
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { mkdir, mkdtemp, rm, lstat, link, readFile, writeFile, chmod, open } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

async function sha256(file) {
  const hash=createHash('sha256');
  for await(const part of createReadStream(file))hash.update(part);
  return hash.digest('hex');
}
async function absent(file) {
  try { await lstat(file); } catch(e) { if(e.code==='ENOENT')return; throw e; }
  throw Error('Refusing to overwrite an existing file: '+file);
}
async function syncFile(file) { const fd=await open(file,'r');try{await fd.sync();}finally{await fd.close();} }
function inspect(db) {
  const integrity=db.prepare('PRAGMA integrity_check').all();
  if(integrity.length!==1||Object.values(integrity[0])[0]!=='ok')throw Error('SQLite integrity verification failed.');
  const foreignKeys=db.prepare('PRAGMA foreign_key_check').all();if(foreignKeys.length)throw Error('SQLite foreign-key verification failed.');
  const tables=new Set(db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map(r=>r.name));
  for(const name of ['users','sessions','projects','shares','share_comments','usage'])if(!tables.has(name))throw Error('Not a supported MASAR database: missing '+name);
  const version=db.prepare('PRAGMA user_version').get().user_version;
  if(![0,1].includes(version))throw Error('Unsupported MASAR database schema.');
  return { schemaVersion:version, counts:Object.fromEntries(['users','projects','shares','share_comments'].map(name=>[name,db.prepare('SELECT count(*) AS n FROM '+name).get().n])) };
}
export async function createBackup(source,target) {
  source=path.resolve(source);target=path.resolve(target);const manifest=target+'.json';
  if(source===target)throw Error('Source and target must differ.');
  const st=await lstat(source);if(!st.isFile())throw Error('The source must be an existing database file.');
  await mkdir(path.dirname(target),{recursive:true,mode:0o700});await absent(target);await absent(manifest);
  const tmp=await mkdtemp(path.join(path.dirname(target),'.masar-backup-')),snapshot=path.join(tmp,'snapshot.sqlite');
  let src,check,published=false,publishedManifest=false;
  try {
    src=new DatabaseSync(source,{readOnly:true});src.exec('PRAGMA busy_timeout=5000;');inspect(src);
    await backup(src,snapshot);src.close();src=null;await chmod(snapshot,0o600);
    check=new DatabaseSync(snapshot,{readOnly:true});const info=inspect(check);check.close();check=null;
    const data={format:'masar-sqlite-backup',version:1,product:'4.1.0',createdAt:new Date().toISOString(),sha256:await sha256(snapshot),bytes:(await lstat(snapshot)).size,...info,confidential:true,integrity:'sha256+sqlite-integrity+foreign-keys',authentication:'manifest is not a cryptographic signature'};
    await writeFile(path.join(tmp,'manifest.json'),JSON.stringify(data,null,2)+'\n',{mode:0o600,flag:'wx'});
    await syncFile(snapshot);await syncFile(path.join(tmp,'manifest.json'));
    // Hard links are atomic, same-filesystem and fail if another process created the destination.
    await link(snapshot,target);published=true;await link(path.join(tmp,'manifest.json'),manifest);publishedManifest=true;
    return {snapshot:target,manifest,...data};
  } catch(e) {
    if(published&&!publishedManifest)await rm(target,{force:true});throw e;
  } finally { if(src)src.close();if(check)check.close();await rm(tmp,{recursive:true,force:true}); }
}
export async function restoreBackup(snapshot,target) {
  snapshot=path.resolve(snapshot);target=path.resolve(target);
  if(snapshot===target)throw Error('Source and target must differ.');
  const m=JSON.parse(await readFile(snapshot+'.json','utf8'));
  if(m.format!=='masar-sqlite-backup'||m.version!==1||!/^[a-f0-9]{64}$/.test(m.sha256)||m.sha256!==await sha256(snapshot)||(await lstat(snapshot)).size!==m.bytes)throw Error('Snapshot hash/size/manifest verification failed.');
  await mkdir(path.dirname(target),{recursive:true,mode:0o700});await absent(target);await absent(target+'-wal');await absent(target+'-shm');
  const tmp=await mkdtemp(path.join(path.dirname(target),'.masar-restore-')),restored=path.join(tmp,'restored.sqlite');let src,dest;
  try {
    src=new DatabaseSync(snapshot,{readOnly:true});inspect(src);await backup(src,restored);src.close();src=null;
    dest=new DatabaseSync(restored);dest.exec('PRAGMA journal_mode=DELETE;PRAGMA foreign_keys=ON;DELETE FROM sessions;');const result=inspect(dest);dest.close();dest=null;
    await chmod(restored,0o600);await syncFile(restored);await link(restored,target);
    return {restored:target,...result,sessionsInvalidated:true,sourceSha256:m.sha256,sha256:await sha256(target)};
  } finally {if(src)src.close();if(dest)dest.close();await rm(tmp,{recursive:true,force:true});}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const [operation,source,target]=process.argv.slice(2);
  if(!['create','restore'].includes(operation)||!source||!target||process.argv.length!==5){console.error('Usage: node tools/backup.mjs create|restore SOURCE.sqlite NEW_TARGET.sqlite');process.exitCode=2;}
  else try {console.log(JSON.stringify(await (operation==='create'?createBackup(source,target):restoreBackup(source,target)),null,2));}
  catch(e){console.error(e.message);process.exitCode=1;}
}
