/* ============================================================================
   F-15 — الحفظ المحلي الآمن: اختبار وحدة للدوالّ النقيّة المشحونة في الصفحة.
     node tests/lib/run.js tests/remediation/test_persistence.js
   لا IndexedDB هنا ولا متصفّح: encode/decode/validateRecord/chooseRecovery
   دوالّ نقيّة عمداً، وطبقة IndexedDB تغلّفها. سلوك IndexedDB الحقيقي (المعاملة،
   قلب المؤشّر على قرص فعلي) يُتحقَّق منه في متصفّح حقيقي — وهنا نثبت المنطق
   الذي تعتمد عليه تلك الطبقة، ونحاكي QuotaExceededError كما يرميه المتصفّح.
   ========================================================================== */
const _np=require('path');
const LOAD=require(_np.join(__dirname,'_trust_core.js'));
const {T, page}=LOAD.load();
const P=T.persistence;
let pass=0, fail=0;
const chk=(n,c,d)=>{ c?(pass++,console.log('  ✓',n))
                      :(fail++,console.log('  ✗',n,d===undefined?'':d)); };
const C=o=>JSON.parse(JSON.stringify(o));
const PROJ={project_id:'default', current_revision:'rev_0007',
  model:{site:{w:22,d:16}, levels:[{index:0,name:'الأرضي',template:'ground'}],
         floors:{ground:{rooms:[{id:'lobby',rect:[1,1,6,5]}]}}},
  request_text:'عمارة سكنية', notes:[]};

console.log('\n== §1 — encode: كل سجلّ يحمل بصمة النموذج والمراجعة والمخطّط والوقت ==');
(function(){
  const e=P.encode(PROJ,{now:1700000000000});
  chk('encode succeeds on a serialisable project', e.ok&&!!e.record, e.code);
  const r=e.record;
  chk('the record declares the persistence contract', r.contract===P.CONTRACT, r.contract);
  chk('the record carries the current schema version',
      r.schema_version===P.SCHEMA_VERSION, r.schema_version);
  chk('the record carries a model hash', /^[0-9a-f]{16}$/.test(r.model_hash), r.model_hash);
  chk('the record carries the revision id', r.revision_id==='rev_0007', r.revision_id);
  chk('the record carries a timestamp', r.saved_at_ms===1700000000000, r.saved_at_ms);
  chk('the record carries its own payload hash and byte count',
      r.payload_hash.length===16 && r.payload_bytes===r.payload.length);
  const e2=P.encode(PROJ,{now:1700000000000});
  chk('encode is deterministic for the same input and clock',
      JSON.stringify(e2.record)===JSON.stringify(r));
  const alt=C(PROJ); alt.model.site.w=23;
  chk('a different model produces a different model hash',
      P.encode(alt,{now:1700000000000}).record.model_hash!==r.model_hash);
  const cyc={}; cyc.self=cyc;
  const bad=P.encode(cyc,{now:1});
  chk('a non-serialisable project is refused, never written half-way',
      bad.ok===false && bad.code===P.CODES.NOT_SERIALISABLE, bad.code);
})();

console.log('\n== §2 — decode: الرحلة ذهاباً وإياباً بلا فقد ==');
(function(){
  const r=P.encode(PROJ,{now:5}).record;
  const d=P.decode(r);
  chk('decode returns the project unchanged',
      d.ok && JSON.stringify(d.project)===JSON.stringify(PROJ), d.code);
  chk('decode reports the revision, hash and timestamp it recovered',
      d.revision_id==='rev_0007' && d.model_hash===r.model_hash && d.saved_at_ms===5);
  chk('decode of a current-schema record reports no migration',
      d.migrated===false && d.schema_relation==='CURRENT');
})();

console.log('\n== §3 — سجلّ فاسد: JSON غير صالح ==');
(function(){
  const r=P.encode(PROJ,{now:5}).record;
  const broken=C(r);
  broken.payload='{"model":{"site":';                    /* JSON مبتور */
  broken.payload_bytes=broken.payload.length;
  broken.payload_hash=P.hash(broken.payload);            /* بصمة صحيحة لنصّ فاسد */
  const v=P.validateRecord(broken);
  chk('a record whose payload is not valid JSON is refused',
      v.usable===false && v.code===P.CODES.PAYLOAD_NOT_JSON, v.code);
  chk('decode never throws on bad JSON, it classifies',
      P.decode(broken).ok===false && P.decode(broken).project===null);
  const garbage={contract:P.CONTRACT, schema_version:P.SCHEMA_VERSION,
    record_id:'rec_x', model_hash:'0'.repeat(16), saved_at_ms:1,
    payload:'not json at all', payload_bytes:15, payload_hash:P.hash('not json at all')};
  chk('outright garbage in the payload is refused as well',
      P.validateRecord(garbage).usable===false);
  chk('a record that is not an object at all is refused',
      P.validateRecord(null).code===P.CODES.NOT_OBJECT
      && P.validateRecord('x').code===P.CODES.NOT_OBJECT
      && P.validateRecord([]).code===P.CODES.NOT_OBJECT);
  chk('a record from a foreign contract is refused',
      P.validateRecord(Object.assign(C(r),{contract:'somebody-else/1'})).code
      ===P.CODES.BAD_CONTRACT);
  chk('a record missing a required field is refused, not defaulted',
      P.validateRecord(Object.assign(C(r),{model_hash:undefined})).code
      ===P.CODES.MISSING);
})();

console.log('\n== §4 — سجلّ مبتور: عدد المحارف لا يطابق المُعلَن ==');
(function(){
  const r=P.encode(PROJ,{now:5}).record;
  const trunc=C(r);
  trunc.payload=trunc.payload.slice(0, Math.floor(trunc.payload.length/2));
  const v=P.validateRecord(trunc);
  chk('truncation is detected by the declared byte count before anything else',
      v.usable===false && v.code===P.CODES.TRUNCATED, v.code);
  chk('the refusal names the numbers it compared',
      v.reasons.join(' ').indexOf(String(r.payload_bytes))>=0, v.reasons);
})();

console.log('\n== §5 — بصمة لا تطابق ==');
(function(){
  const r=P.encode(PROJ,{now:5}).record;
  const h1=C(r); h1.payload_hash='deadbeefdeadbeef';
  chk('a payload hash mismatch is refused',
      P.validateRecord(h1).code===P.CODES.HASH_MISMATCH);
  /* حمولة مُعدَّلة مع تحديث بصمة الحمولة — لكن بصمة النموذج تفضحها */
  const h2=C(r);
  const obj=JSON.parse(h2.payload); obj.model.site.w=999;
  h2.payload=JSON.stringify(obj);
  h2.payload_bytes=h2.payload.length;
  h2.payload_hash=P.hash(h2.payload);
  const v=P.validateRecord(h2);
  chk('a tampered model with a repaired payload hash is still caught by the model hash',
      v.usable===false && v.code===P.CODES.HASH_MISMATCH, v.code);
  chk('the model-hash refusal says which hash failed',
      v.reasons.join(' ').indexOf('model hash')>=0, v.reasons);
})();

console.log('\n== §6 — مخطّط أقدم من الحالي: يُرقَّى ولا يُهمَل ==');
(function(){
  const old=P.encode(PROJ,{now:5, schema_version:P.SCHEMA_VERSION-1}).record;
  const v=P.validateRecord(old);
  chk('an older record is structurally valid and usable',
      v.valid===true && v.usable===true, v.code);
  chk('an older record is flagged for migration, not silently accepted as current',
      v.schema_relation==='OLDER' && v.migrated===true
      && v.code===P.CODES.SCHEMA_OLDER, v.code);
  const d=P.decode(old);
  chk('decoding an older record migrates it forward and says so',
      d.ok===true && d.migrated===true
      && d.project.schema_version===P.SCHEMA_VERSION
      && d.project.schema_migrated_from===P.SCHEMA_VERSION-1, d.code);
  chk('migration preserves the user work itself',
      JSON.stringify(d.project.model)===JSON.stringify(PROJ.model));
  const ancient=P.encode(PROJ,{now:5, schema_version:1}).record;
  const av=P.validateRecord(ancient);
  chk('a record older than the oldest migratable schema is preserved, not used',
      av.valid===true && av.usable===false && av.code===P.CODES.SCHEMA_TOO_OLD, av.code);
  chk('an unmigratable old record is marked for preservation, never for deletion',
      P.decode(ancient).preserve===true);
})();

console.log('\n== §7 — مخطّط أحدث من الحالي: يُصان ولا يُخمَّن ولا يُكتَب فوقه ==');
(function(){
  const fut=P.encode(PROJ,{now:5, schema_version:P.SCHEMA_VERSION+1}).record;
  const v=P.validateRecord(fut);
  chk('a newer record is recognised as structurally valid',  v.valid===true);
  chk('a newer record is NOT used — the build cannot know its format',
      v.usable===false && v.code===P.CODES.SCHEMA_NEWER, v.code);
  chk('the refusal explains itself in terms the user can act on',
      v.reasons.join(' ').toLowerCase().indexOf('newer')>=0, v.reasons);
  chk('decode marks a newer record for preservation',
      P.decode(fut).preserve===true && P.decode(fut).project===null);
})();

console.log('\n== §8 — chooseRecovery: آخر سجلّ سليم ينجو دائماً ==');
(function(){
  const good1=P.encode(PROJ,{now:1000}).record;
  const alt=C(PROJ); alt.model.site.w=30; alt.current_revision='rev_0008';
  const good2=P.encode(alt,{now:2000}).record;
  const corrupt=C(good2); corrupt.record_id='rec_corrupt';
  corrupt.payload=corrupt.payload.slice(0,20);
  const newer=P.encode(PROJ,{now:9000, schema_version:P.SCHEMA_VERSION+5,
                             record_id:'rec_future'}).record;

  const r=P.chooseRecovery([good1, corrupt, good2, newer]);
  chk('the newest usable record is chosen', r.chosen_id===good2.record_id, r.chosen_id);
  chk('the chosen record decodes back to the newest work',
      P.decode(r.chosen).project.current_revision==='rev_0008');
  chk('the corrupt record is rejected with a named code',
      r.rejected.some(x=>x.record_id==='rec_corrupt'
                       && x.code===P.CODES.TRUNCATED), r.rejected);
  chk('the corrupt record is quarantined, never chosen',
      r.quarantine.indexOf('rec_corrupt')>=0 && r.chosen_id!=='rec_corrupt');
  chk('the future-schema record is PRESERVED, not quarantined and not chosen',
      r.preserve.indexOf('rec_future')>=0
      && r.quarantine.indexOf('rec_future')<0
      && r.chosen_id!=='rec_future');
  chk('the older good record is still accepted as a fallback candidate',
      r.accepted.some(a=>a.record_id===good1.record_id));

  /* الحالة الحرجة: لا يبقى سجلّ سليم واحد */
  const only=P.chooseRecovery([corrupt]);
  chk('with no usable record, nothing is chosen',
      only.chosen===null && only.code===P.CODES.NONE_USABLE, only.code);
  chk('with no usable record, NOTHING is quarantined — we never destroy the last copy',
      only.quarantine.length===0, only.quarantine);
  chk('the empty case is a named state, not a crash',
      P.chooseRecovery([]).code===P.CODES.NO_RECORDS
      && P.chooseRecovery(null).code===P.CODES.NO_RECORDS
      && P.chooseRecovery(undefined).code===P.CODES.NO_RECORDS);
  /* الحتمية: نفس المدخلات بأي ترتيب ⇒ نفس الاختيار */
  const shuffled=P.chooseRecovery([newer, good2, corrupt, good1]);
  chk('the choice is order-independent and deterministic',
      shuffled.chosen_id===r.chosen_id);
  const tieA=P.encode(PROJ,{now:5000, record_id:'rec_aaa'}).record;
  const tieB=P.encode(PROJ,{now:5000, record_id:'rec_bbb'}).record;
  chk('an exact timestamp tie is broken deterministically, not by array order',
      P.chooseRecovery([tieA,tieB]).chosen_id
      ===P.chooseRecovery([tieB,tieA]).chosen_id);
})();

console.log('\n== §9 — الكتابة المعاملاتية: مؤشّر يُقلَب أخيراً، ولا كتابة فوق النسخة الوحيدة ==');
(function(){
  const s0={pointer:'rec_old', records:['rec_old'], last_good:'rec_old',
            last_error:null, last_saved_at_ms:900};
  const p=P.planWrite(s0, PROJ, {now:1000});
  chk('a write plan is produced', p.ok===true, p.code);
  chk('the plan writes a NEW record id, never the current pointer',
      p.plan.new_record_id!=='rec_old'
      && p.plan.overwrites_existing_record===false);
  chk('the pointer flip is the last durable step, after read-back validation',
      p.plan.steps.indexOf('PUT_NEW_RECORD')<p.plan.steps.indexOf('READ_BACK_AND_VALIDATE')
      && p.plan.steps.indexOf('READ_BACK_AND_VALIDATE')<p.plan.steps.indexOf('FLIP_POINTER')
      && p.plan.pointer_flip_is_last===true, p.plan.steps);
  chk('the previous pointer is retained until the new record is proven',
      p.plan.keep.indexOf('rec_old')>=0 && p.plan.prune.indexOf('rec_old')<0);

  const okr=P.applyWriteResult(s0, p.plan, {ok:true});
  chk('a successful write moves the pointer to the new record',
      okr.ok===true && okr.state.pointer===p.plan.new_record_id
      && okr.pointer_moved===true);
  chk('a successful write records the new last-good',
      okr.state.last_good===p.plan.new_record_id && okr.status==='SAVED');
})();

console.log('\n== §10 — QuotaExceededError: لا فقد صامت، والسجلّ السليم لم يُمَس ==');
(function(){
  const s0={pointer:'rec_good', records:['rec_good'], last_good:'rec_good',
            last_error:null, last_saved_at_ms:900};
  const p=P.planWrite(s0, PROJ, {now:1000});
  /* كما يرميه المتصفّح فعلاً */
  const quota=new Error('The quota has been exceeded.');
  quota.name='QuotaExceededError';
  chk('a QuotaExceededError is classified by name',
      P.classifyStorageError(quota)==='STORAGE_QUOTA');
  chk('the legacy numeric quota codes are classified too',
      P.classifyStorageError({name:'', code:22})==='STORAGE_QUOTA'
      && P.classifyStorageError({name:'NS_ERROR_DOM_QUOTA_REACHED'})==='STORAGE_QUOTA'
      && P.classifyStorageError({name:'', code:1014})==='STORAGE_QUOTA');
  const r=P.applyWriteResult(s0, p.plan, {ok:false, error:quota});
  chk('the failed write is reported, never swallowed',
      r.ok===false && r.code==='STORAGE_QUOTA' && r.status==='QUOTA', r.code);
  chk('THE POINTER DID NOT MOVE — the last good record still owns it',
      r.pointer_moved===false && r.state.pointer==='rec_good');
  chk('the last good record id survives the failure untouched',
      r.state.last_good==='rec_good' && r.last_good_survived===true);
  chk('the previous good record is still in the record list',
      r.state.records.indexOf('rec_good')>=0);
  chk('the failure is remembered so the UI can show it',
      r.state.last_error==='STORAGE_QUOTA');
  chk('the last successful save time is not falsified by a failure',
      r.state.last_saved_at_ms===900);
  /* وبعد الفشل: الاستعادة ما زالت تجد السجلّ السليم */
  const good=P.encode(PROJ,{now:900, record_id:'rec_good'}).record;
  chk('after a quota failure the good record is still recoverable',
      P.chooseRecovery([good]).chosen_id==='rec_good');
  ['STORAGE_UNAVAILABLE','STORAGE_ABORTED','STORAGE_VERSION','STORAGE_BLOCKED']
    .forEach((exp,i)=>{
      const nm=['InvalidStateError','AbortError','VersionError','SecurityError'][i];
      chk('a '+nm+' is classified as '+exp,
          P.classifyStorageError({name:nm})===exp); });
  chk('an unknown storage failure is still a named state, never silence',
      P.classifyStorageError({name:'WhoKnows'})==='STORAGE_UNKNOWN'
      && P.classifyStorageError(null)==='STORAGE_UNKNOWN');
})();

console.log('\n== §11 — إعادة التحميل أثناء التحرير وأثناء التوليد ==');
(function(){
  const mid=C(PROJ); mid.notes=[{kind:'لون', text:'الجدار أخضر'}];
  const r1=P.encode(mid,{now:100}).record;
  const d1=P.decode(r1);
  chk('a reload mid-edit recovers the in-progress notes as well as the model',
      d1.ok && d1.project.notes.length===1
      && d1.project.notes[0].text==='الجدار أخضر');
  const gen=C(PROJ); gen.generation_in_flight=true;
  const d2=P.decode(P.encode(gen,{now:200}).record);
  chk('a reload mid-generation recovers the fact that generation was unfinished',
      d2.ok && d2.project.generation_in_flight===true);
  chk('an unfinished generation is never recovered as a finished one',
      d2.project.generation_in_flight!==false);
})();

console.log('\n== §12 — نسخة احتياطية يدوية: ملفّ محلي، ذهاباً وإياباً ==');
(function(){
  const e=P.exportBackup(PROJ,{now:777});
  chk('a backup file is produced', e.ok===true && !!e.file, e.code);
  chk('the backup is a JSON download with a name',
      /\.json$/.test(e.file.filename) && /json/.test(e.file.mime));
  chk('the backup states it is a local file download',
      e.envelope.storage==='LOCAL_FILE_DOWNLOAD');
  const back=P.restoreBackup(e.file.text);
  chk('restoring the backup returns the identical project',
      back.ok && JSON.stringify(back.project)===JSON.stringify(PROJ), back.code);
  chk('a non-JSON file is refused with a named code, not a crash',
      P.restoreBackup('this is not json').code==='BACKUP_NOT_JSON');
  chk('a JSON file that is not an ACS backup is refused',
      P.restoreBackup('{"hello":1}').code==='BACKUP_BAD_CONTRACT');
  const tampered=JSON.parse(e.file.text);
  tampered.record.payload=tampered.record.payload.slice(0,10);
  chk('a corrupted backup is refused and restores nothing',
      P.restoreBackup(JSON.stringify(tampered)).ok===false
      && P.restoreBackup(JSON.stringify(tampered)).project===null);
})();

console.log('\n== §13 — لا يُقال «سحابة» ولا «نسخة احتياطية على خادم» أبداً ==');
(function(){
  ['IDLE','SAVING','SAVED','FAILED','RECOVERED','QUOTA'].forEach(k=>{
    const L=P.statusLabel(k);
    chk('status '+k+' has Arabic primary text', typeof L.ar==='string'&&L.ar.length>4);
    chk('status '+k+' has English secondary text', typeof L.en==='string'&&L.en.length>4);
    chk('status '+k+' claims nothing about a cloud or a server',
        P.assertNoCloudClaim(L.ar+' '+L.en).ok===true,
        P.assertNoCloudClaim(L.ar+' '+L.en).offending);
  });
  chk('SAVED says exactly "محفوظ محلياً على هذا الجهاز"',
      P.statusLabel('SAVED').ar.indexOf('محفوظ محلياً على هذا الجهاز')>=0,
      P.statusLabel('SAVED').ar);
  chk('SAVED says exactly "saved locally on this device"',
      P.statusLabel('SAVED').en.toLowerCase()
        .indexOf('saved locally on this device')>=0, P.statusLabel('SAVED').en);
  chk('saving / saved / failed are three distinguishable states',
      P.statusLabel('SAVING').tone!==P.statusLabel('SAVED').tone
      && P.statusLabel('SAVED').tone!==P.statusLabel('FAILED').tone
      && P.statusLabel('SAVING').ar!==P.statusLabel('SAVED').ar);
  chk('the cloud-claim guard actually fires on a cloud claim',
      P.assertNoCloudClaim('your project is backed up to the cloud').ok===false);
})();

console.log('\n== §14 — الصفحة المشحونة تُعلن الحفظ المحلي ولا تدّعي سحابة ==');
(function(){
  chk('the shipped page exposes window.ACS.persistence',
      page.indexOf('window.ACS.persistence={')>=0);
  chk('the shipped page uses IndexedDB, not localStorage, for the project record',
      page.indexOf("indexedDB.open(DB_NAME,DB_VER)")>=0);
  chk('the visible Arabic status string ships in the page',
      page.indexOf('محفوظ محلياً على هذا الجهاز')>=0);
  chk('the visible English status string ships in the page',
      page.indexOf('saved locally on this device')>=0);
  chk('the page declares the storage kind is local to this device',
      page.indexOf('INDEXEDDB_LOCAL_TO_THIS_DEVICE')>=0
      && page.indexOf('is_cloud_backup:false')>=0);
  const panel=page.slice(page.indexOf('id="acsLocalNote"'),
                         page.indexOf('id="acsLocalNote"')+1400);
  chk('the user-facing note explicitly denies that this is a server backup',
      panel.indexOf('ليس نسخاً احتياطياً على خادم')>=0
      && panel.toLowerCase().indexOf('not a server backup')>=0);
  chk('the page ships explicit export / restore / clear controls',
      page.indexOf('id="acsExportBackup"')>=0
      && page.indexOf('id="acsRestoreBackup"')>=0
      && page.indexOf('id="acsClearLocal"')>=0);
  chk('clearing local data asks for confirmation',
      page.indexOf('window.confirm(')>=0
      && page.indexOf('cannot be undone')>=0);
})();

console.log('\n──────────────────────────────────────────────');
console.log('F-15 LOCAL PERSISTENCE: '+pass+' passed, '+fail+' failed');
console.log('NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED: real IndexedDB durability '
  +'across a genuine browser reload (and a real device quota wall) needs a browser '
  +'with storage; this suite proves the pure logic the IndexedDB wrapper depends on.');
if(fail) process.exit(1);
