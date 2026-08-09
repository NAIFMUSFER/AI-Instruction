/* جانب جافاسكربت من تكافؤ المرحلة 5 — يعمل داخل شيفرة المتصفّح المستخرَجة من
   public/index.html، ويكرّر ما يفعله py_authoring.py حرفاً بحرف. */
const fs=require('fs'), path=require('path');
const HERE=__dirname, PHASE=path.resolve(HERE,'..'), ROOT=path.resolve(PHASE,'..','..');
const _tmp=(function(){ try{ return require('os').tmpdir(); }catch(e){ return '/tmp'; } })();
const OUT=(process.env&&process.env.ACS_PARITY_AUTHORING_JS)
  ||path.join(_tmp,'acs_parity_authoring_js.json');
const LIB=require(path.join(PHASE,'lib_authoring_fixtures.js'));
const SC=LIB.load();
const C=o=>JSON.parse(JSON.stringify(o));
/* نسخ عميق يحفظ NaN و Infinity ومفاتيح مثل __proto__ — دورة JSON تتلفها،
   فتضيع الحالة الخصومية قبل أن تصل إلى المحرّك. */
const D=v=>{ if(Array.isArray(v)) return v.map(D);
  if(v&&typeof v==='object'){ const o={};
    Object.keys(v).forEach(k=>{ Object.defineProperty(o,k,
      {value:D(v[k]),enumerable:true,writable:true,configurable:true}); });
    return o; }
  return v; };
const AT='2026-01-01T00:00:00Z';

const out={};
SC.scenarios.forEach(function(s){
  const name=s[0], modelKey=s[1];
  const model=C(SC.models[modelKey]);
  const before=JSON.stringify(model);
  const cmd=LIB.hydrate(s[2]);
  const project=auCreateProject(C(model),'bld_0','IMPORT',null);
  const snap=(cmd&&typeof cmd==='object')?cmd.snap:null;
  const grid=(cmd&&typeof cmd==='object')?cmd.grid_m:null;

  const norm=auNormaliseCommand(D(cmd),null,snap===undefined?null:snap,
    grid===undefined?null:grid);
  const preview=auPreviewCommand(model,D(cmd),null,'bld_0',
    snap===undefined?null:snap,grid===undefined?null:grid);
  const impact=auDependencyImpact(D(cmd),model,'bld_0');
  const txn=auValidateTransaction(project,[D(cmd)],'bld_0');
  const commit=auCommitTransaction(project,[D(cmd)],
    {confirm:(txn.transaction||{}).confirmation_digest,
     acknowledge_warnings:true,created_at:AT});
  if(JSON.stringify(model)!==before)
    throw new Error('the authoring engine mutated the model: '+name);
  if(auModelHash(project.model,'building','bld_0')!==project.model_hash)
    throw new Error('the project model changed in place: '+name);

  const entry={normalised:norm,command_hash:auCommandHash(D(cmd),null),
    preview:preview,impact:impact,transaction:txn,
    committed:(commit.valid&&commit.committed)||false,
    commit_state:commit.state,commit_issues:commit.issues,
    commit_revision:(commit.revision===undefined)?null:commit.revision,
    commit_model_hash:(commit.model_hash===undefined)?null:commit.model_hash,
    stale_artifacts:(commit.stale_artifacts===undefined)?null:commit.stale_artifacts,
    audit:(commit.audit===undefined)?null:commit.audit,
    base_model_hash:project.model_hash,base_revision:project.current_revision};
  if(commit.committed){
    const np=commit.project;
    entry.history=np.history;
    entry.summary=auSummary(np);
    entry.diff=auRevisionDiff(project.model,np.model);
    entry.serialised=auSerialiseProject(np,true,false);
    const u=auUndo(np,undefined,AT,'bld_0');
    entry.undo_state=u.state;
    entry.undo_hash=(u.model_hash===undefined)?null:u.model_hash;
    entry.undo_revision=(u.revision===undefined)?null:u.revision;
    if(u.project){
      const r=auRedo(u.project,undefined,AT,'bld_0');
      entry.redo_state=r.state;
      entry.redo_hash=(r.model_hash===undefined)?null:r.model_hash; } }
  out[name]=entry;
});

const adv={};
SC.adversarial.forEach(function(pair){
  const key=pair[0], cmd=LIB.hydrate(pair[1]);
  const model=C(SC.models.villa);
  const project=auCreateProject(C(model),'bld_0','IMPORT',null);
  const n=auNormaliseCommand(D(cmd),null,null,null);
  const p=auPreviewCommand(model,D(cmd),null,'bld_0',null,null);
  const t=auValidateTransaction(project,[D(cmd)],'bld_0');
  const c=auCommitTransaction(project,[D(cmd)],{confirm:'x',acknowledge_warnings:true});
  adv[key]={normalise_valid:n.valid,normalise_codes:n.issues.map(i=>i.code),
    preview_valid:p.valid,preview_codes:p.issues.map(i=>i.code),
    preview_state:p.state,transaction_state:t.state,
    transaction_codes:t.issues.map(i=>i.code),
    committed:(c.committed===undefined)?null:c.committed,
    commit_codes:c.issues.map(i=>i.code),
    model_unchanged:auModelHash(project.model,'building','bld_0')===project.model_hash};
});
out.__adversarial__=adv;

const targets=['g.majlis','bld_0.g.majlis.door_0','g.corridor.obj_0','site','building',
  'g','bld_0.flr_0.wall_0','nope','','runtime:obj:x','obstacle:x'];
const model=C(SC.models.villa);
const resolve={}, properties={};
targets.forEach(t=>{ resolve[t]=auResolveTarget(model,t,'bld_0');
  properties[t]=auEditableProperties(model,t,'bld_0'); });
const nl={}; ['majlis','corridor','nothing here','','kitchen'].forEach(ph=>{
  nl[ph]=auResolveNlTarget(model,ph,'bld_0'); });
const nlDup={}; ['corridor','a','b'].forEach(ph=>{
  nlDup[ph]=auResolveNlTarget(C(SC.models.dup_ids),ph,'bld_0'); });
const hashes={}; ['a','b','مجلس'].forEach(n=>{
  hashes[n]=auCommandHash({type:'RENAME_SPACE',target_id:'g.majlis',
    parameters:{name:n}},null); });
const rt=auLoadProject(auSerialiseProject(
  auCreateProject(C(model),'bld_0','IMPORT',null),true,true),'bld_0').project;
out.__ops__={spec_schema:AU_SCHEMA,command_types:AU_COMMAND_TYPES.slice(),
  issue_codes:AU_ISSUE_CODES.slice(),resolve:resolve,properties:properties,
  integrity:auValidateModelIntegrity(model,'bld_0'),nl:nl,nl_dup:nlDup,
  proposal:auProposeCommand({type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',
    parameters:{delta_m:0.5}},'because the user asked',null),
  hashes:hashes,
  load_roundtrip:{hash:rt.model_hash,revision:rt.current_revision,valid:true}};

fs.writeFileSync(OUT,JSON.stringify(out),'utf8');
console.log('javascript authoring parity written: '+OUT+' ('+Object.keys(out).length+' keys)');
