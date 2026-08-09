const fs=require('fs'), _np=require('path'), _os=require('os');
const HERE=__dirname, FIXD=_np.resolve(HERE,'..','fixtures');
const OUT=process.env.ACS_PARITY_JS||_np.join(_os.tmpdir(),'acs_parity_js_dist.json');
const S=JSON.parse(fs.readFileSync(_np.join(FIXD,'dist_scen.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));
const out={};
S.queries.forEach(q=>{
  const b=C(S.models[q.m]), rels=buildRelationships(b,'bld_0');
  if(q.kind==='path'){
    const p=findPath(b,rels,q.from,q.to,'bld_0');
    const m=measurePath(b,p,'bld_0',q.origin,q.dest);
    out[q.n]={m:m, issues:validateMeasurement(m), summary:distanceSummary(m)};
  } else {
    const r=findEgress(b,rels,q.from,'bld_0');
    out[q.n]={status:r.status, distance:r.distance, distance_status:r.distance_status,
      selection_basis:r.selection_basis, selection_basis_reason:r.selection_basis_reason,
      alternative_exits:r.alternative_exits, measurement:r.distance_measurement||null,
      issues:r.distance_measurement?validateMeasurement(r.distance_measurement):[],
      summary:egressSummary(r)};
  }
});
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('js scenarios computed:', Object.keys(out).length);
