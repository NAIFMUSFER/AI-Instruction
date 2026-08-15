const fs=require('fs'), _np=require('path'), _os=require('os');
const HERE=__dirname, FIXD=_np.resolve(HERE,'..','fixtures');
const OUT=process.env.ACS_PARITY_JS||_np.join(_os.tmpdir(),'acs_parity_js_occ.json');
const S=JSON.parse(fs.readFileSync(_np.join(FIXD,'occ_scen.json'),'utf8'));
const FX=JSON.parse(fs.readFileSync(_np.join(FIXD,'fixtures.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const AT='T0', WHO='explicit_manual_approval';
const EV=[{type:'manual_review',ref:'reviewer',detail:'synthetic verification'}];
const B=()=>{const b=C(FX.hotel); b.wall_t=0.20; return b;};
const ctx=()=>newCodeContext();
function act(store,project,packId,stop){
  const p=occPack(store,packId,'1');
  if(stop!=='DRAFT'){ verifyOccupancyPack(p,'UNDER_REVIEW',null,AT,WHO,null);
                      verifyOccupancyPack(p,stop||'VERIFIED_PARTIAL',null,AT,WHO,null); }
  project.code_context.classification_packs.push({pack_id:packId,version:'1',enabled:true});
  return activeOccupancyPacks(project,store); }
function decVer(store,project,group,verify){
  const d=declareOccupancy('BUILDING:bld_0','BUILDING',group,store,project,null,null,AT,null);
  if(d[0]){ addOccupancyClassification(store,d[0]);
            if(verify) verifyOccupancy(d[0],store,project,null,AT,WHO,EV,null); }
  return d; }
function ruleRun(id,store,project,extra){
  const b=B(), rels=buildRelationships(b,'bld_0');
  const idx=occupancyIndex(store,['BUILDING:bld_0']);
  const s=resolveSubject(b,rels,'BUILDING:bld_0','bld_0',idx);
  const p=ruleById(id,[],'TEST_ONLY.CORE');
  return evaluateRule(p[1],s,Object.assign({evaluated_at:AT},extra||{}),p[0],[]); }
const out={};
S.steps.forEach(q=>{
  const store=occupancyFixtureStore(), project=ctx();
  if(q.op==='issues') out[q.n]=occupancyIssues(store,project);
  else if(q.op==='real_count') out[q.n]=occRealClassificationCount(store);
  else if(q.op==='new_ctx') out[q.n]={ctx:newCodeContext(),issues:validateCodeContext(newCodeContext())};
  else if(q.op==='activate') out[q.n]=act(store,project,q.pack,q.stop);
  else if(q.op==='suggest'){ if(q.activate) act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL');
    const made=suggestOccupancyFromProgram('BUILDING:bld_0','BUILDING',q.program,store,project,AT);
    made.forEach(c=>addOccupancyClassification(store,c));
    out[q.n]={made:made,resolved:resolveOccupancy('BUILDING:bld_0',store)}; }
  else if(q.op==='declare'){ act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL');
    const d=decVer(store,project,q.group,false);
    out[q.n]={classification:d[0],reason:d[1],resolved:resolveOccupancy('BUILDING:bld_0',store)}; }
  else if(q.op==='verify_suggested'){ act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL');
    const made=suggestOccupancyFromProgram('BUILDING:bld_0','BUILDING','hotel',store,project,AT);
    made.forEach(c=>addOccupancyClassification(store,c));
    const r=verifyOccupancy(made[0],store,project,null,AT,q.method||WHO,q.no_evidence?null:EV,null);
    out[q.n]={result:r,classification:made[0],resolved:resolveOccupancy('BUILDING:bld_0',store)}; }
  else if(q.op==='verify_declared'){ act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL');
    const d=decVer(store,project,'TEST_OCC_A',true);
    out[q.n]={classification:d[0],resolved:resolveOccupancy('BUILDING:bld_0',store)}; }
  else if(q.op==='resolve_plain') out[q.n]=resolveOccupancy('BUILDING:bld_0',store);
  else if(q.op==='conflict'){ act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL');
    ['TEST_OCC_A','TEST_OCC_B'].forEach(g=>decVer(store,project,g,true));
    out[q.n]=resolveOccupancy('BUILDING:bld_0',store); }
  else if(q.op==='mixed'||q.op==='audit_mixed'||q.op==='export_mixed'){
    act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL');
    const sp=['SPACE:bld_0.t.guest_1','SPACE:bld_0.g.lobby'], gs=['TEST_OCC_A','TEST_OCC_B'];
    sp.forEach((sid,i)=>{ const d=declareOccupancy(sid,'SPACE',gs[i],store,project,null,null,AT,null);
      addOccupancyClassification(store,d[0]);
      verifyOccupancy(d[0],store,project,null,AT,WHO,EV,null); });
    if(q.op==='mixed') out[q.n]=sp.map(sid=>resolveOccupancy(sid,store));
    else if(q.op==='audit_mixed') out[q.n]=auditOccupancy(store,sp.concat(['BUILDING:bld_0']));
    else out[q.n]=exportOccupancy(store,project); }
  else if(q.op==='rule'){
    let extra=null;
    if(q.state==='candidate'){ act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL');
      suggestOccupancyFromProgram('BUILDING:bld_0','BUILDING','hotel',store,project,AT)
        .forEach(c=>addOccupancyClassification(store,c)); }
    else if(q.state==='verified'){ act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL');
      decVer(store,project,'TEST_OCC_A',true); }
    else if(q.state==='conflict'){ act(store,project,'TEST_ONLY.OCCPACK','VERIFIED_PARTIAL');
      ['TEST_OCC_A','TEST_OCC_B'].forEach(g=>decVer(store,project,g,true)); }
    else if(q.state==='edition9'){ act(store,project,'TEST_ONLY.OCCPACK_ED9','VERIFIED_PARTIAL');
      decVer(store,project,'TEST_OCC_A',true); }
    out[q.n]=ruleRun(q.rule,store,project,extra); }
  else if(q.op==='pack_security'){
    const p=occPack(store,'TEST_ONLY.OCCPACK','1');
    const dup=C(p); dup.classifications.push(C(dup.classifications[0]));
    const bad=C(p); bad.verification.status='TOTALLY_FINE';
    const scr=C(p); scr.classifications[0].title='<script>x</script>';
    const reg=C(p); reg.regulatory=true;
    out[q.n]={duplicate:validateOccupancyPack(dup),unknown_state:validateOccupancyPack(bad),
              script:validateOccupancyPack(scr),regulatory:validateOccupancyPack(reg),
              draft_to_verified:verifyOccupancyPack(C(p),'VERIFIED_PARTIAL',null,AT,WHO,null),
              ai_verify:verifyOccupancyPack(C(p),'UNDER_REVIEW',null,AT,'ai_suggestion',null)}; }
});
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('js occupancy steps:', Object.keys(out).length);
