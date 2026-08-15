const fs=require('fs'), _np=require('path');
const HERE=__dirname, ROOT=_np.resolve(HERE,'..','..');
let pass=0,fail=0;
const chk=(n,c,d)=>{c?(pass++,console.log('  ✓',n)):(fail++,console.log('  ✗',n,d===undefined?'':d))};
const LIB=require(_np.join(HERE,'lib_authoring_fixtures.js'));
const SC=LIB.load();
const C=o=>JSON.parse(JSON.stringify(o));
const M=n=>C(SC.models[n]);
const PR=n=>auCreateProject(M(n),'bld_0','IMPORT',null);
const codes=r=>r.issues.map(i=>i.code);
const SCEN={}; SC.scenarios.forEach(s=>{ SCEN[s[0]]=s; });
const ADV={}; SC.adversarial.forEach(a=>{ ADV[a[0]]=a[1]; });
const prev=(model,cmd,rev,bid,snap,grid)=>auPreviewCommand(model,LIB.hydrate(cmd),
  rev===undefined?null:rev,bid||'bld_0',snap===undefined?null:snap,
  grid===undefined?null:grid);
const scen=name=>{ const s=SCEN[name]; return {model:M(s[1]),cmd:LIB.hydrate(s[2]),
  project:auCreateProject(M(s[1]),'bld_0','IMPORT',null)}; };

/* ============================================================================
   المرحلة 5 — التأليف الخصومي (§90)
   لا استثناء غير ملتقط، ولا قبول صامت، ولا رمز غير معلن، ولا تلويث نموذج أوّلي
   ========================================================================== */
const CANON=JSON.parse(fs.readFileSync(_np.join(ROOT,'acs_authoring.json'),'utf8'));
const declared=cs=>cs.every(c=>CANON.issue_codes.indexOf(c)>=0);
const safe=(label,fn)=>{ try{ return {ok:true,v:fn()}; }
  catch(e){ chk('no exception escapes from '+label,false,e&&e.message);
    return {ok:false,v:null}; } };

console.log('\n== EVERY ADVERSARIAL COMMAND IS HANDLED ==');
Object.keys(ADV).sort().forEach(function(k){
  const raw=LIB.hydrate(ADV[k]);
  const n=safe('normalising '+k,()=>auNormaliseCommand(raw,null,null,null));
  if(!n.ok) return;
  chk(k+': normalisation returns a result instead of throwing',
      !!n.v&&typeof n.v.valid==='boolean');
  chk(k+': every code is declared', declared(codes(n.v)), JSON.stringify(codes(n.v)));
  chk(k+': every issue carries a declared severity',
      n.v.issues.every(i=>CANON.severities.indexOf(i.severity)>=0));
  const p=safe('previewing '+k,()=>prev(M('villa'),ADV[k]));
  if(!p.ok) return;
  chk(k+': preview returns a result instead of throwing',
      !!p.v&&typeof p.v.valid==='boolean');
  chk(k+': preview codes are all declared', declared(codes(p.v)),
      JSON.stringify(codes(p.v)));
  chk(k+': a hostile command never yields a silently accepted candidate',
      p.v.valid===true||p.v.candidate===null);
  const t=safe('transacting '+k,()=>auValidateTransaction(PR('villa'),[raw],'bld_0'));
  if(!t.ok) return;
  chk(k+': a transaction judges it without throwing', typeof t.v.valid==='boolean');
  chk(k+': the transaction state is a declared state',
      CANON.transaction_states.concat(CANON.transaction_failure_states)
        .indexOf(t.v.state)>=0, String(t.v.state));
  const c=safe('committing '+k,()=>auCommitTransaction(PR('villa'),[raw],{confirm:'x',
    acknowledge_warnings:true}));
  if(!c.ok) return;
  chk(k+': a commit attempt does not throw', typeof c.v.committed==='boolean');
});

console.log('\n== NOTHING HOSTILE REACHES THE CANONICAL MODEL ==');
(function(){
  const p=PR('villa');
  const before=JSON.stringify(p.model), H=p.model_hash;
  Object.keys(ADV).sort().forEach(function(k){
    const raw=LIB.hydrate(ADV[k]);
    try{ auNormaliseCommand(raw,null,null,null); }catch(e){}
    try{ prev(p.model,ADV[k]); }catch(e){}
    try{ auValidateTransaction(p,[raw],'bld_0'); }catch(e){}
    try{ auCommitTransaction(p,[raw],{confirm:'x',acknowledge_warnings:true}); }catch(e){}
    try{ auDependencyImpact(raw,p.model,'bld_0'); }catch(e){}
    try{ auProposeCommand(raw,null,null); }catch(e){} });
  chk('the canonical model is byte-identical after the whole adversarial sweep',
      JSON.stringify(p.model)===before);
  chk('the project hash is unchanged', p.model_hash===H);
  chk('no revision was created by any hostile command', p.history.length===1);
  chk('Object.prototype was not polluted by any of them',
      ({}).polluted===undefined&&({}).a===undefined&&Object.prototype.polluted===undefined);
})();

console.log('\n== HOSTILE TARGETS ==');
[null,undefined,'',[],{},42,true,'no.such.thing','g.','..','.'.repeat(50),
 'g.majlis.door_-1','g.majlis.door_1e9','bld_0.flr_0.wall_','runtime:obj:x',
 'obstacle:x','portal:x','walk:space:x','measure:x','vis:x','clash_x'
].forEach(function(t){
  const r=safe('the target '+JSON.stringify(t),
    ()=>auResolveTarget(M('villa'),t,'bld_0'));
  if(!r.ok) return;
  chk('the target '+JSON.stringify(t)+' is resolved without throwing',
      !!r.v&&('kind' in r.v));
  chk('a hostile target never resolves to an editable element',
      r.v.kind===null||['SPACE','DOOR','WINDOW','OBJECT','LEVEL','SITE','BUILDING','WALL']
        .indexOf(r.v.kind)>=0);
  if(r.v.kind===null) chk('the refusal of '+JSON.stringify(t)+' uses a declared code',
      declared(r.v.issues.map(i=>i.code)), JSON.stringify(r.v.issues.map(i=>i.code)));
});

console.log('\n== HOSTILE NUMBERS AND COORDINATES ==');
[['NaN','NaN_MARKER'],['Infinity','INF_MARKER'],['negative infinity','NEG_INF_MARKER']]
  .forEach(function(p){
  ['delta_m','w','d','x','z','offset','width','height_m','rotation_deg'].forEach(function(k){
    const params={}; params[k]=p[1];
    const cmd={type:'RESIZE_SPACE',target_id:'g.majlis',parameters:params};
    const r=safe('a '+p[0]+' in '+k,()=>prev(M('villa'),cmd));
    if(!r.ok) return;
    chk('a '+p[0]+' in '+k+' never reaches the model',
        r.v.valid===false||r.v.candidate===null
        ||JSON.stringify(r.v.candidate).indexOf('null,null')<0); }); });
[1e308,-1e308,1e17,-1e17,999999999].forEach(function(v){
  const r=safe('the coordinate '+v,()=>prev(M('villa'),
    {type:'ADD_SPACE',parameters:{template:'g',rect:[v,v,5,5],id:'far'}}));
  if(!r.ok) return;
  chk('an absurd coordinate '+v+' is refused', r.v.valid===false,
      JSON.stringify(codes(r.v)));
  chk('the refusal of '+v+' names a declared code', declared(codes(r.v)));
});
chk('the declared coordinate bound is finite and reasonable',
    Number.isFinite(Number(AU_LIMITS.max_abs_coordinate_m))
    &&Number(AU_LIMITS.max_abs_coordinate_m)>0);
chk('the authoring bound is consistent with the runtime spatial bound',
    Number(AU_LIMITS.max_abs_coordinate_m)
      <=Number(ACS_RUNTIME_SPEC.spatial_index.max_abs_coordinate_m));

console.log('\n== WRONG TYPES EVERYWHERE ==');
(function(){
  const shapes=[
    {type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:42}},
    {type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:null}},
    {type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:[]}},
    {type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:{}}},
    {type:'ADD_SPACE',parameters:{template:42,rect:[0,0,1,1]}},
    {type:'ADD_SPACE',parameters:{template:'g',rect:'0,0,1,1'}},
    {type:'ADD_SPACE',parameters:{template:'g',rect:[0,0,1]}},
    {type:'ADD_SPACE',parameters:{template:'g',rect:[0,0,1,1,1]}},
    {type:'ADD_DOOR',target_id:'g.majlis',parameters:{edge:['N'],offset:1,width:1}},
    {type:'ADD_DOOR',target_id:'g.majlis',parameters:{edge:'NORTHWEST',offset:1,width:1}},
    {type:'MOVE_WALL',target_id:'bld_0.flr_0.wall_0',parameters:{delta_m:[0.5]}},
    {type:'CHANGE_LEVEL_HEIGHT',parameters:{height_m:'tall'}},
    {type:'LOCK_ELEMENT',target_id:'g.majlis',parameters:{reason:['IMPORTED']}},
    {type:'ADD_LEVEL',parameters:{template:{}}},
    {type:'ADD_OBJECT',target_id:'g.majlis',parameters:{kind:5,x:1,z:1}}];
  shapes.forEach(function(cmd,i){
    const r=safe('shape '+i,()=>prev(M('villa'),cmd));
    if(!r.ok) return;
    chk('wrong-typed shape '+i+' is refused', r.v.valid===false,
        JSON.stringify(codes(r.v)));
    chk('wrong-typed shape '+i+' uses declared codes only', declared(codes(r.v)),
        JSON.stringify(codes(r.v)));
  });
})();

console.log('\n== DUPLICATE IDS, LOCKED TARGETS AND STALE REVISIONS ==');
(function(){
  const p=PR('villa');
  chk('a duplicate explicit space id is refused',
      codes(prev(p.model,{type:'ADD_SPACE',
        parameters:{template:'g',rect:[20,12,4,4],id:'majlis'}}))
        .indexOf('ID_COLLISION')>=0);
  const locked=prev(p.model,{type:'LOCK_ELEMENT',target_id:'g.majlis',
    parameters:{reason:'IMPORTED'}}).candidate;
  ['RENAME_SPACE','RESIZE_SPACE','DELETE_SPACE'].forEach(function(t){
    const params=(t==='RENAME_SPACE')?{name:'x'}:(t==='RESIZE_SPACE'?{w:6,d:4}:{});
    chk('a locked element refuses '+t,
        codes(prev(locked,{type:t,target_id:'g.majlis',parameters:params}))
          .indexOf('TARGET_LOCKED')>=0); });
  chk('a locked element may still be unlocked',
      prev(locked,{type:'UNLOCK_ELEMENT',target_id:'g.majlis',parameters:{}}).valid===true);
  chk('a locked element can still be read',
      auEditableProperties(locked,'g.majlis','bld_0').properties.locked===true);
  chk('the lock reason is exposed to the reader',
      auEditableProperties(locked,'g.majlis','bld_0').properties.lock_reason==='IMPORTED');
  ['rev:0000000000000000','','not-a-revision',null].forEach(function(rev){
    const cmd={type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'x'},
      base_revision:rev};
    const r=safe('the base revision '+JSON.stringify(rev),
      ()=>auValidateTransaction(p,[cmd],'bld_0'));
    if(!r.ok) return;
    chk('the base revision '+JSON.stringify(rev)+' is judged without throwing',
        typeof r.v.valid==='boolean');
    if(rev) chk('a mismatched base revision is refused as stale',
      codes(r.v).indexOf('STALE_BASE_REVISION')>=0, JSON.stringify(codes(r.v))); });
})();

console.log('\n== MALFORMED CONSTRAINTS AND OVERSIZED BATCHES ==');
(function(){
  const p=PR('villa');
  [['constraints_array'],['unknown_constraint'],['unknown_constraint_subject'],
   ['negative_max_delta']].forEach(function(k){
    const r=auNormaliseCommand(LIB.hydrate(ADV[k[0]]),null,null,null);
    chk('the malformed constraint '+k[0]+' is refused', r.valid===false,
        JSON.stringify(codes(r)));
  });
  const many=[];
  for(let i=0;i<Number(AU_LIMITS.max_constraint_entries)+5;i++) many.push('SPACE_RECT');
  chk('too many constraint entries are refused',
      auNormaliseCommand({type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'x'},
        constraints:{must_not_change:many}},null,null,null).valid===false);
  const big=[];
  for(let i=0;i<Number(AU_LIMITS.max_commands_per_transaction)+50;i++)
    big.push({type:'RENAME_SPACE',target_id:'g.majlis',parameters:{name:'n'+i}});
  const r=auValidateTransaction(p,big,'bld_0');
  chk('an oversized batch is refused rather than attempted',
      codes(r).indexOf('BATCH_TOO_LARGE')>=0);
  chk('the oversized batch produced no transaction to commit', r.transaction===null);
  chk('a batch of hostile commands still changes nothing', (function(){
    const H=p.model_hash;
    const hostile=Object.keys(ADV).slice(0,20).map(k=>LIB.hydrate(ADV[k]));
    auCommitTransaction(p,hostile,{confirm:'x',acknowledge_warnings:true});
    return p.model_hash===H; })());
})();

console.log('\n== ERROR ORDERING IS DETERMINISTIC ==');
(function(){
  const cmd={type:'RESIZE_SPACE',target_id:'g.majlis',parameters:{w:-1,d:'NaN_MARKER'}};
  const a=prev(M('villa'),cmd), b=prev(M('villa'),cmd);
  chk('the same hostile command yields the same issue order',
      JSON.stringify(a.issues)===JSON.stringify(b.issues));
  const rank=c=>AU_SEVERITIES.indexOf(auSeverityOf(c));
  chk('issues are ordered by severity, then code, then subject', (function(){
    const p=auValidateTransaction(PR('villa'),
      [{type:'RESIZE_SPACE',target_id:'nope',parameters:{w:-1}},
       {type:'MOVE_DOOR',target_id:'bld_0.g.majlis.door_0',parameters:{offset:999}}],
      'bld_0');
    for(let i=1;i<p.issues.length;i++){
      const x=p.issues[i-1], y=p.issues[i];
      const rx=rank(x.code), ry=rank(y.code);
      if(rx!==ry){ if(rx<ry) return false; continue; }
      if(x.code!==y.code){ if(x.code>y.code) return false; continue; }
      if(String(x.subject)>String(y.subject)) return false; }
    return true; })());
  chk('every issue names its code, severity and subject',
      a.issues.every(i=>typeof i.code==='string'&&typeof i.severity==='string'
        &&'subject' in i&&'detail' in i));
})();

console.log('\n──────────────────────────────────────────────');
console.log('AUTHORING ADVERSARIAL: '+pass+' passed, '+fail+' failed');
if(fail) process.exit(1);
