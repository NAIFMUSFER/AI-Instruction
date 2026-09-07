import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

function makeDatabase(file){
  const db=new DatabaseSync(file);
  db.exec(`
    PRAGMA user_version=1;
    CREATE TABLE users(id TEXT PRIMARY KEY);
    CREATE TABLE sessions(id TEXT PRIMARY KEY);
    CREATE TABLE projects(id TEXT PRIMARY KEY);
    CREATE TABLE shares(id TEXT PRIMARY KEY);
    CREATE TABLE share_comments(id TEXT PRIMARY KEY);
    CREATE TABLE usage(id TEXT PRIMARY KEY);
    INSERT INTO users(id) VALUES ('u1');
    INSERT INTO sessions(id) VALUES ('s1');
    INSERT INTO projects(id) VALUES ('p1');
  `);
  db.close();
}

test('backup CLI accepts its documented three arguments and restore invalidates sessions', async()=>{
  const dir=await mkdtemp(path.join(tmpdir(),'masar-backup-cli-'));
  try{
    const source=path.join(dir,'source.sqlite'),snapshot=path.join(dir,'snapshot.sqlite'),restored=path.join(dir,'restored.sqlite');
    makeDatabase(source);
    const created=JSON.parse(execFileSync(process.execPath,['tools/backup.mjs','create',source,snapshot],{encoding:'utf8'}));
    assert.equal(created.product,'4.1.0');
    assert.equal(created.counts.projects,1);
    const manifest=JSON.parse(await readFile(snapshot+'.json','utf8'));
    assert.match(manifest.sha256,/^[a-f0-9]{64}$/);
    const result=JSON.parse(execFileSync(process.execPath,['tools/backup.mjs','restore',snapshot,restored],{encoding:'utf8'}));
    assert.equal(result.sessionsInvalidated,true);
    const db=new DatabaseSync(restored,{readOnly:true});
    assert.equal(db.prepare('SELECT count(*) AS n FROM projects').get().n,1);
    assert.equal(db.prepare('SELECT count(*) AS n FROM sessions').get().n,0);
    db.close();
  }finally{await rm(dir,{recursive:true,force:true});}
});

test('backup CLI rejects missing arguments with usage exit code',()=>{
  const result=spawnSync(process.execPath,['tools/backup.mjs','create'],{encoding:'utf8'});
  assert.equal(result.status,2);
  assert.match(result.stderr,/Usage: node tools\/backup\.mjs/);
});
