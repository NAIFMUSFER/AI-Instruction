const fs=require('fs'), _np=require('path'), _os=require('os');
const HERE=__dirname, FIXD=_np.resolve(HERE,'..','fixtures');
const OUT=process.env.ACS_PARITY_JS||_np.join(_os.tmpdir(),'acs_parity_js_rev.json');
const S=JSON.parse(fs.readFileSync(_np.join(FIXD,'rev_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const out={};
S.queries.forEach(q=>{
  const m=C(S.models[q.m]);
  out[q.n]={hash:modelHash(m,q.scope),
            canonical:ingestCanonicalJson(q.scope==='project'?canonicalProject(m):canonicalBuilding(m,'bld_0')),
            revision:modelRevision(m,q.scope,'bld_0','T0')};
});
out['__ctx__']={hash:codeContextHash({jurisdiction:{country:'TESTLAND',region:null,authority:null},
  code_context:{standard:'S',edition:'1',
    rulepacks:[{rulepack_id:'B',version:'2',enabled:true},{rulepack_id:'A',version:'1',enabled:true}],
    classification_packs:[{pack_id:'P',version:'1',enabled:true}]}})};
const occ={classifications:[
  {subject_id:'BUILDING:bld_0',subject_type:'BUILDING',status:'VERIFIED',group:'TEST_OCC_A',
   subgroup:null,standard:'TEST_STANDARD',edition:'0',classification_system:'TEST_OCC',
   pack_id:'P',pack_version:'1',jurisdiction:{country:'TESTLAND',region:null,authority:null}},
  {subject_id:'SPACE:x',subject_type:'SPACE',status:'CANDIDATE',group:'TEST_OCC_B'}],packs:[]};
out['__occ__']={hash:occupancyHash(occ),canonical:ingestCanonicalJson(canonicalOccupancy(occ))};
out['__diff__']=revisionDiff(C(S.models.villa),C(S.models.moved));
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('js revision steps:', Object.keys(out).length);
