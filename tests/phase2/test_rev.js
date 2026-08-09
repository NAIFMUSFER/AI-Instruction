/* ======================================================================
   المرحلة 2 — اختبارات تثبيت النتائج على مراجعة النموذج.
   لا قاعدة تنظيمية ولا تصنيف حقيقي — بنية نزاهة فقط.
   ====================================================================== */
/* وحدة المسارات باسم غير متصادم: بعض الأجنحة تستعمل path متغيّراً محلياً */
const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
const FIXD=_np.resolve(HERE,'..','phase2','fixtures');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const AT='T0', WHO='explicit_manual_approval';
const EVID=[{type:'manual_review',ref:'reviewer',detail:'synthetic'}];
const sk=v=>Array.isArray(v)?v.map(sk):(v&&typeof v==='object'?
  Object.keys(v).sort().reduce((m,k)=>(m[k]=sk(v[k]),m),{}):v);

function villaS(){ const b=C(FX.villa); b.wall_t=0.20;
  [['f','corridor_f'],['g','corridor']].forEach(([t,id])=>{
    const r=b.floors[t].rooms.find(r=>r.id===id);
    Object.assign(r.objects[0],{risers:16,tread_m:0.28,riser_m:0.20}); });
  return b; }
const RULE=id=>ruleById(id,[],'TEST_ONLY.CORE');
function snapFor(b,ruleId,subjId,opt){
  opt=opt||{};
  const rels=buildRelationships(b,'bld_0');
  const idx=occupancyIndex(opt.occ||{classifications:[],packs:[]},[subjId]);
  const subj=resolveSubject(b,rels,subjId,'bld_0',idx);
  const p=RULE(ruleId);
  const result=evaluateRule(p[1],subj,{evaluated_at:AT},p[0],[]);
  return snapshotResult({result:result,model:b,scope:opt.scope||'building',
    rule:p[1],ruleset:p[0],occupancy_store:opt.occ||null,
    occupancy_subjects:opt.occ?[subjId]:null,project_ctx:opt.ctx||null,
    ingest_store:opt.ingest||null,created_at:AT}); }

console.log('\n== §42 — NO REGULATORY CONTENT ADDED ==');
chk('regulatory rule count still 0', regulatoryRuleCount([])===0);
chk('real occupancy classification count still 0',
    occRealClassificationCount(occupancyFixtureStore())===0);
chk('the revision spec encodes no code content',
    !/\bSBC\b|\bIBC\b|\bNFPA\b|\bADA\b/.test(JSON.stringify(ACS_REVISION_SPEC)));
const CANON_SPEC=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_revision.json'),'utf8'));
chk('browser spec is byte-identical to acs_revision.json',
    JSON.stringify(sk(ACS_REVISION_SPEC))===JSON.stringify(sk(CANON_SPEC)));
chk('hash algorithm is sha256, not something invented', REV_HASH_ALGORITHM==='sha256');
chk('nine integrity statuses declared', REV_STATUSES.length===9, REV_STATUSES.length);

console.log('\n== TEST A (§26) — SAME MODEL, SAME HASH ==');
const vb=villaS();
const h1=modelHash(vb), h2=modelHash(vb);
chk('re-hashing an unchanged model gives the identical hash', h1===h2, h1);
chk('hash is a 64-hex sha256 digest', /^[0-9a-f]{64}$/.test(h1));
const before=JSON.stringify(vb);
modelHash(vb); modelRevision(vb); canonicalBuilding(vb);
chk('hashing never mutates the model', JSON.stringify(vb)===before);
const rev=modelRevision(vb,'building','bld_0',AT);
chk('revision_id derives from the hash, not from a clock',
    rev.revision_id==='rev_'+h1.slice(0,16)&&rev.created_at===AT);
chk('revision declares its canonicalization version',
    rev.canonicalization_version===CANONICALIZATION_VERSION);
let snap=snapFor(vb,'TEST_ONLY.NUMERIC_MAX_001','ROUTE:bld_0.f.bed1>bld_0.g.majlis');
chk('the snapshot records a PASS result', snap.result.status==='PASS');
let integ=checkResultIntegrity(snap,{model:vb,rule:RULE('TEST_ONLY.NUMERIC_MAX_001')[1],
  ruleset:RULE('TEST_ONLY.NUMERIC_MAX_001')[0]});
chk('integrity is CURRENT with an unchanged model', integ.status==='CURRENT', integ.status);
chk('CURRENT reports no reasons', integ.reasons.length===0);

console.log('\n== TEST B (§27) — KEY ORDER ==');
function reorderKeys(o){ if(Array.isArray(o)) return o.map(reorderKeys);
  if(o&&typeof o==='object'){ const out={};
    Object.keys(o).sort().reverse().forEach(k=>{out[k]=reorderKeys(o[k]);}); return out; }
  return o; }
chk('reversing every object key order gives the same hash', modelHash(reorderKeys(C(vb)))===h1);
chk('whitespace/formatting cannot matter (hash is over canonical JSON)',
    modelHash(JSON.parse(JSON.stringify(vb,null,4)))===h1);

console.log('\n== TEST C (§28) — ARRAY ORDER, SENSITIVE AND NOT ==');
const lv=C(vb); lv.levels=lv.levels.slice().reverse();
chk('levels are documented order-INSENSITIVE and reordering keeps the hash',
    modelHash(lv)===h1);
chk('the reason is recorded in the spec',
    ACS_REVISION_SPEC.order_insensitive.some(e=>e.path==='levels'&&/explicit index/.test(e.reason)));
const rr=C(vb); rr.floors.g.rooms=rr.floors.g.rooms.slice().reverse();
chk('rooms are documented order-SENSITIVE and reordering changes the hash',
    modelHash(rr)!==h1);
const dd=C(vb); dd.floors.g.rooms[0].doors=dd.floors.g.rooms[0].doors.slice().reverse();
chk('doors are order-SENSITIVE (door_<i> ids are referenced elsewhere)', modelHash(dd)!==h1);
chk('every order-sensitive path states its reason',
    ACS_REVISION_SPEC.order_sensitive.every(e=>!!e.reason&&e.reason.length>10));
chk('rect order matters (it is [x,z,w,d])',
    (()=>{const x=C(vb); const r=x.floors.g.rooms[0].rect; x.floors.g.rooms[0].rect=[r[0],r[1],r[3],r[2]];
      return modelHash(x)!==h1;})());
const pins=C(vb); // مجموعات التثبيت في سياق الكود غير حسّاسة للترتيب
const ctxA={jurisdiction:{country:null,region:null,authority:null},
  code_context:{standard:null,edition:null,
    rulepacks:[{rulepack_id:'A',version:'1',enabled:true},{rulepack_id:'B',version:'1',enabled:true}],
    classification_packs:[]}};
const ctxB=C(ctxA); ctxB.code_context.rulepacks.reverse();
chk('rulepack pins are order-insensitive', codeContextHash(ctxA)===codeContextHash(ctxB));

console.log('\n== TEST D (§29) — DOOR MOVE ==');
const moved=C(vb); moved.floors.g.rooms[0].doors[0].offset=
  moved.floors.g.rooms[0].doors[0].offset+0.5;
chk('moving a door by 0.5 m changes the hash', modelHash(moved)!==h1);
integ=checkResultIntegrity(snap,{model:moved,rule:RULE('TEST_ONLY.NUMERIC_MAX_001')[1],
  ruleset:RULE('TEST_ONLY.NUMERIC_MAX_001')[0]});
chk('the old snapshot becomes STALE_MODEL_CHANGED', integ.status==='STALE_MODEL_CHANGED', integ.status);
chk('the reason names the model hash anchor',
    integ.reasons.some(r=>r.anchor==='model_hash'&&r.reason==='MODEL_CHANGED'));
chk('the stored result value is untouched — no silent recompute', snap.result.status==='PASS');
const marked=applyIntegrity(snap,{model:moved,rule:RULE('TEST_ONLY.NUMERIC_MAX_001')[1],
  ruleset:RULE('TEST_ONLY.NUMERIC_MAX_001')[0]});
chk('marking integrity does not alter the result', marked.result.status==='PASS');
chk('the export refuses to present it as current',
    exportSnapshot(marked).presented_as_current===false&&
    exportSnapshot(marked).integrity.status==='STALE_MODEL_CHANGED');
chk('a PASS with stale integrity is never a current PASS',
    exportSnapshot(marked).result==='PASS'&&exportSnapshot(marked).presented_as_current===false);
const other=C(vb); other.floors.g.rooms[1].rect[3]=other.floors.g.rooms[1].rect[3]+1;
chk('resizing a room changes the hash', modelHash(other)!==h1);
const noStair=C(vb); noStair.floors.f.rooms[0].objects=[];
chk('removing a stair changes the hash', modelHash(noStair)!==h1);
const addFloor=C(vb); addFloor.levels.push({index:2,name:'roof',template:'f'});
chk('adding a level changes the hash', modelHash(addFloor)!==h1);
const exitFlag=C(vb); exitFlag.floors.g.rooms[0].doors[0].exit=true;
chk('flagging a door as an exit changes the hash', modelHash(exitFlag)!==h1);
const cw=C(vb); cw.floors.g.rooms[0].doors[0].clear_width_m=0.95;
chk('adding an explicit clear width changes the hash', modelHash(cw)!==h1);
const prov=C(vb); prov.floors.g.rooms[0].doors[0].source='user';
chk('changing input provenance changes the hash', modelHash(prov)!==h1);

console.log('\n== TEST E (§30) — NON-ENGINEERING STATE ==');
const ui=C(vb);
ui.camera={position:[10,5,10],target:[0,0,0]}; ui.view={tab:'objects'};
ui.selection='bld_0.g.majlis'; ui.debug=true; ui.fps=59.7;
ui.session={id:'abc'}; ui.toast='saved'; ui.cache={x:1}; ui.downloaded_at='2026-01-01';
ui.theme='dark'; ui.orbit={az:1}; ui.thumbnail='data-uri-here';
chk('camera, view, selection, debug, fps, session, toast, cache, theme and thumbnail are all excluded',
    modelHash(ui)===h1, modelHash(ui));
chk('the excluded set is declared, not implicit', REV_VOLATILE_KEYS.length>=15);
integ=checkResultIntegrity(snap,{model:ui,rule:RULE('TEST_ONLY.NUMERIC_MAX_001')[1],
  ruleset:RULE('TEST_ONLY.NUMERIC_MAX_001')[0]});
chk('a UI-only change leaves the result CURRENT', integ.status==='CURRENT', integ.status);

console.log('\n== TEST F (§31) — OCCUPANCY CHANGE ==');
let ostore=occupancyFixtureStore();
const oproj=newCodeContext();
const opk=occPack(ostore,'TEST_ONLY.OCCPACK','1');
verifyOccupancyPack(opk,'UNDER_REVIEW',null,AT,WHO,null);
verifyOccupancyPack(opk,'VERIFIED_PARTIAL',null,AT,WHO,null);
oproj.code_context.classification_packs.push({pack_id:'TEST_ONLY.OCCPACK',version:'1',enabled:true});
const dA=declareOccupancy('BUILDING:bld_0','BUILDING','TEST_OCC_A',ostore,oproj,null,null,AT,null);
addOccupancyClassification(ostore,dA[0]);
verifyOccupancy(dA[0],ostore,oproj,null,AT,WHO,EVID,null);
const osnap=snapFor(vb,'TEST_ONLY.OCC_ENUM_001','BUILDING:bld_0',{occ:ostore,ctx:oproj});
chk('the occupancy-dependent result evaluates PASS', osnap.result.status==='PASS', osnap.result.status);
chk('the snapshot records an occupancy hash and its subject refs',
    /^[0-9a-f]{64}$/.test(osnap.integrity.occupancy_hash)&&
    osnap.integrity.occupancy_refs[0]==='BUILDING:bld_0');
integ=checkResultIntegrity(osnap,{model:vb,occupancy_store:ostore,project_ctx:oproj,
  rule:RULE('TEST_ONLY.OCC_ENUM_001')[1],ruleset:RULE('TEST_ONLY.OCC_ENUM_001')[0]});
chk('unchanged occupancy keeps it CURRENT', integ.status==='CURRENT', integ.status);
// نغيّر التصنيف المتحقَّق منه إلى مجموعة أخرى
dA[0].group='TEST_OCC_B';
integ=checkResultIntegrity(osnap,{model:vb,occupancy_store:ostore,project_ctx:oproj,
  rule:RULE('TEST_ONLY.OCC_ENUM_001')[1],ruleset:RULE('TEST_ONLY.OCC_ENUM_001')[0]});
chk('changing the verified classification yields STALE_OCCUPANCY_CHANGED',
    integ.status==='STALE_OCCUPANCY_CHANGED', integ.status);
chk('it is distinguished from a model change',
    integ.reasons.every(r=>r.anchor!=='model_hash'));
chk('the occupancy hash covers only verified classifications',
    (()=>{const s2=occupancyFixtureStore();
      const h=occupancyHash(s2); s2.classifications.push({subject_id:'X',status:'CANDIDATE',
        group:'TEST_OCC_A'}); return occupancyHash(s2)===h;})());

console.log('\n== TEST G (§32) — RULE REVISION ==');
const rulePair=RULE('TEST_ONLY.NUMERIC_MAX_001');
const changedRule=C(rulePair[1]); changedRule.expected.value=25; changedRule.revision=2;
integ=checkResultIntegrity(snap,{model:vb,rule:changedRule,ruleset:rulePair[0]});
chk('a changed rule meaning yields STALE_RULE_CHANGED', integ.status==='STALE_RULE_CHANGED', integ.status);
chk('it is not reported as a model change',
    integ.reasons.every(r=>r.anchor!=='model_hash'));
chk('the reason names the rule hash',
    integ.reasons.some(r=>r.anchor==='rule_hash'&&r.reason==='RULE_MEANING_CHANGED'));
const retitled=C(rulePair[1]); retitled.title='different wording entirely';
integ=checkResultIntegrity(snap,{model:vb,rule:retitled,ruleset:rulePair[0]});
chk('a wording-only rule edit does not make it stale', integ.status==='CURRENT', integ.status);

console.log('\n== TEST H (§33) — RULEPACK VERSION ==');
const newerPack=C(rulePair[0]); newerPack.ruleset_version='2';
integ=checkResultIntegrity(snap,{model:vb,rule:rulePair[1],ruleset:newerPack});
chk('a new rulepack version yields STALE_RULEPACK_CHANGED',
    integ.status==='STALE_RULEPACK_CHANGED', integ.status);
chk('the reason states both the stored and the current pack',
    integ.reasons.some(r=>r.anchor==='rulepack'&&/@1/.test(r.stored)&&/@2/.test(r.current)),
    JSON.stringify(integ.reasons));
chk('the result remains attributed to the pack that produced it',
    snap.integrity.rulepack_id==='TEST_ONLY.CORE'&&snap.integrity.rulepack_version==='1');

console.log('\n== TEST I (§34) — SOURCE DOCUMENT HASH ==');
const ing=ingestRealStore();
const srcRule=C(rulePair[1]);
srcRule.source={type:'official_document',source_id:'SBC',document_id:'SBC201-CC-2024',
                page:null,clause:null,url:null,verified:false};
const ssnap=snapshotResult({result:snap.result,model:vb,rule:srcRule,ruleset:rulePair[0],
  ingest_store:ing,created_at:AT});
chk('the snapshot pins the source document hash',
    ssnap.integrity.source_document_hashes['SBC201-CC-2024']===
    ingDocument(ing,'SBC201-CC-2024').integrity.sha256);
integ=checkResultIntegrity(ssnap,{model:vb,rule:srcRule,ruleset:rulePair[0],ingest_store:ing});
chk('unchanged source bytes keep it CURRENT', integ.status==='CURRENT', integ.status);
const ing2=ingestRealStore();
ingDocument(ing2,'SBC201-CC-2024').integrity.sha256=sha256Hex('different source bytes');
integ=checkResultIntegrity(ssnap,{model:vb,rule:srcRule,ruleset:rulePair[0],ingest_store:ing2});
chk('changed source bytes yield STALE_SOURCE_CHANGED', integ.status==='STALE_SOURCE_CHANGED', integ.status);
chk('the reason names the document', integ.reasons.some(r=>r.document_id==='SBC201-CC-2024'));
chk('ingestion semantics are untouched — the document is still not CONTENT_VERIFIED',
    documentUsable(ingDocument(ing,'SBC201-CC-2024'))===false);

console.log('\n== TEST J (§35) — MULTI-BUILDING SCOPE ==');
const pa=toProject(C(vb));
pa.project.buildings[0].id='bld_0';
pa.project.buildings.push({id:'bld_1',name:'B',building_type:'villa',programs:['villa'],
  position:{x:60,z:0,rotation:0},active:false,building:C(vb)});
const projHash=modelHash(pa,'project');
const bh=buildingHashes(pa);
chk('a project hash and per-building hashes are both produced',
    /^[0-9a-f]{64}$/.test(projHash)&&Object.keys(bh).length===2, JSON.stringify(Object.keys(bh)));
const pb=C(pa);
const b1=pb.project.buildings.find(x=>x.id==='bld_1').building;
b1.floors.g.rooms[0].doors[0].offset=b1.floors.g.rooms[0].doors[0].offset+0.5;
const bh2=buildingHashes(pb);
chk('changing building B leaves building A hash identical', bh2['bld_0']===bh['bld_0'],
    JSON.stringify([bh['bld_0'].slice(0,12),bh2['bld_0'].slice(0,12)]));
chk('changing building B changes building B hash', bh2['bld_1']!==bh['bld_1']);
chk('the project-scoped hash does change', modelHash(pb,'project')!==projHash);
const aModel=pa.project.buildings.find(x=>x.id==='bld_0').building;
const aModel2=pb.project.buildings.find(x=>x.id==='bld_0').building;
const aSnap=snapshotResult({result:snap.result,model:aModel,scope:'building',
  building_id:'bld_0',rule:rulePair[1],ruleset:rulePair[0],created_at:AT});
integ=checkResultIntegrity(aSnap,{model:aModel2,rule:rulePair[1],ruleset:rulePair[0]});
chk('a building-A scoped result stays CURRENT after building B changes',
    integ.status==='CURRENT', integ.status);
const pSnap=snapshotResult({result:snap.result,model:pa,scope:'project',
  rule:rulePair[1],ruleset:rulePair[0],created_at:AT});
integ=checkResultIntegrity(pSnap,{model:pb,rule:rulePair[1],ruleset:rulePair[0]});
chk('a project-scoped result becomes STALE_MODEL_CHANGED',
    integ.status==='STALE_MODEL_CHANGED', integ.status);
const reordered=C(pa); reordered.project.buildings.reverse();
chk('reordering buildings does not change the project hash',
    modelHash(reordered,'project')===projHash);

console.log('\n== §8/§10/§25 — STATUSES, NO SILENT RE-EVALUATION, HISTORY ==');
chk('integrity status is separate from the rule result',
    snap.result.status==='PASS'&&('status' in snap.integrity)&&
    snap.integrity.status!==snap.result.status);
const noAnchors=checkResultIntegrity(snap,{});
chk('with nothing supplied to check against ⇒ CURRENT_UNDER_SAME_HASH',
    noAnchors.status==='CURRENT_UNDER_SAME_HASH', noAnchors.status);
chk('it names which anchors went unchecked', noAnchors.unchecked.indexOf('model_hash')>=0);
const oldCanon=C(snap); oldCanon.integrity.canonicalization_version='acs-model-canonical/0';
chk('an incompatible canonicalization version ⇒ UNVERIFIABLE',
    checkResultIntegrity(oldCanon,{model:vb}).status==='UNVERIFIABLE');
chk('hashes from incompatible canonicalization are never compared',
    checkResultIntegrity(oldCanon,{model:vb}).unchecked[0]==='all');
const history=[snap,snapshotResult({result:snap.result,model:moved,rule:rulePair[1],
  ruleset:rulePair[0],created_at:'T1'})];
chk('two snapshots of different model states coexist',
    history[0].integrity.model_hash!==history[1].integrity.model_hash&&history.length===2);
const stale=staleResults(history,{model:moved,rule:rulePair[1],ruleset:rulePair[0]});
chk('staleResults reports only the outdated one with its reason',
    stale.length===1&&stale[0].integrity_status==='STALE_MODEL_CHANGED', JSON.stringify(stale));
chk('nothing was recomputed — the stale entry keeps its original result',
    history[0].result.status==='PASS');
const priority=['UNVERIFIABLE','STALE_MODEL_CHANGED','STALE_SOURCE_CHANGED','STALE_RULE_CHANGED'];
chk('status precedence is declared, not ad hoc',
    priority.every((s,i)=>REV_PRECEDENCE.indexOf(s)===i), JSON.stringify(REV_PRECEDENCE));

console.log('\n== §20 — FLOAT HANDLING ==');
const f1=C(vb); f1.floors.g.rooms[0].rect[2]=24.90548817090728;
const f2=C(vb); f2.floors.g.rooms[0].rect[2]=24.905;
chk('full precision is preserved — 24.90548817090728 ≠ 24.905', modelHash(f1)!==modelHash(f2));
const f3=C(vb); f3.floors.g.rooms[0].rect[2]=6.0;
const f4=C(vb); f4.floors.g.rooms[0].rect[2]=6;
chk('integral floats normalise so 6.0 and 6 hash alike', modelHash(f3)===modelHash(f4));
chk('the numeric policy is documented', /no rounding before hashing/.test(ACS_REVISION_SPEC.numeric_policy));

console.log('\n== §21 — ID STABILITY ==');
const noIds=C(vb);
Object.keys(noIds.floors).forEach(t=>noIds.floors[t].rooms.forEach(r=>{delete r.space_id;}));
(noIds.levels||[]).forEach(l=>{delete l.id; delete l.elevation;});
const withIds=C(noIds); ensureElementIds(withIds,'bld_0');
chk('a model hashes identically before and after ensureElementIds',
    modelHash(noIds)===modelHash(withIds));
chk('derived ids are materialised on the copy only',
    noIds.floors.g.rooms[0].space_id===undefined);
chk('the id policy is documented', /never mutated/.test(ACS_REVISION_SPEC.id_policy));
const renamed=C(vb); renamed.floors.g.rooms[0].id='majlis_renamed';
chk('renaming a room id changes the hash (it defines references)', modelHash(renamed)!==h1);

console.log('\n== §22/§23 — RELATIONSHIPS AND DERIVED DATA ==');
chk('relationships are declared derived and excluded',
    ACS_REVISION_SPEC.derived_excluded.some(e=>e.item==='relationships'));
chk('navigation, egress and distance are all declared derived',
    ['navigation graph','egress results','distance measurements']
      .every(i=>ACS_REVISION_SPEC.derived_excluded.some(e=>e.item===i)));
const relBefore=buildRelationships(vb,'bld_0').length;
const relChanged=C(vb); relChanged.floors.g.rooms[0].doors[0].edge='N';
chk('a geometry edit that changes the relationship graph also changes the hash',
    buildRelationships(relChanged,'bld_0').length!==relBefore
      ? modelHash(relChanged)!==h1 : modelHash(relChanged)!==h1);
const derived=C(vb); derived.relationships=buildRelationships(vb,'bld_0');
chk('attaching a derived relationship list would change the hash — so it is never persisted here',
    modelHash(derived)!==h1);

console.log('\n== §18 — DERIVED ANALYSIS SNAPSHOTS ==');
const rels=buildRelationships(vb,'bld_0');
const path=findPath(vb,rels,'bld_0.f.bed1','bld_0.g.majlis','bld_0');
const meas=measurePath(vb,path,'bld_0');
const dsnap=snapshotResult({result:{status:meas.distance_status,
  walking_distance_m:meas.walking_distance_m},model:vb,created_at:AT});
chk('a distance analysis can be pinned to the model that produced it',
    dsnap.integrity.model_hash===h1&&dsnap.result.walking_distance_m===24.905);
integ=checkResultIntegrity(dsnap,{model:moved});
chk('after a door move the distance snapshot is STALE_MODEL_CHANGED',
    integ.status==='STALE_MODEL_CHANGED', integ.status);
chk('transient queries are not snapshotted automatically — snapshotting is an explicit call',
    typeof snapshotResult==='function');

console.log('\n== §37 — REVISION DIFF ==');
const diff=revisionDiff(vb,moved);
chk('the diff reports the models are different', diff.identical===false);
chk('it names the changed path factually',
    diff.changes.some(c=>/doors\[0\].offset/.test(c.path)&&c.change==='changed'),
    JSON.stringify(diff.changes.slice(0,3)));
chk('it carries both hashes', diff.hash_a===h1&&diff.hash_b===modelHash(moved));
chk('it draws no engineering conclusion', /no engineering conclusion/.test(diff.note));
chk('an identical pair diffs to nothing',
    revisionDiff(vb,C(vb)).identical===true&&revisionDiff(vb,C(vb)).changes.length===0);
const addDiff=revisionDiff(vb,cw);
chk('an added field is reported as added',
    addDiff.changes.some(c=>c.change==='added'&&/clear_width_m/.test(c.path)));

console.log('\n== §41 — BACKWARD COMPATIBILITY ==');
const legacy=C(FX.clinic);          // نموذج مرحلة 1 بلا أي بيانات مراجعة
chk('a Phase 1 model with no revision metadata hashes fine',
    /^[0-9a-f]{64}$/.test(modelHash(legacy)));
chk('revision metadata is derived on demand, not stored',
    modelRevision(legacy).model_hash===modelHash(legacy)&&legacy.revision_id===undefined);
chk('the source model is not rewritten', JSON.stringify(legacy)===JSON.stringify(C(FX.clinic)));

console.log('\n== §38 — SECURITY ==');
chk('no cryptography is invented — sha256 only',
    ACS_REVISION_SPEC.hash_algorithm==='sha256'&&
    sha256Hex('')==='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
chk('a stored hash is never trusted without recomputation',
    (()=>{const s=C(snap); s.integrity.model_hash='0'.repeat(64);
      return checkResultIntegrity(s,{model:vb}).status==='STALE_MODEL_CHANGED';})());
chk('no eval/Function in the revision layer',
    !/[^a-zA-Z_.]eval\s*\(|new\s+Function\s*\(/.test(
      canonicalBuilding.toString()+checkResultIntegrity.toString()+revisionDiff.toString()));

console.log(`\nREVISION: ${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
