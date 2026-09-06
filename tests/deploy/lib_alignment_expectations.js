/* Explicit negative fixtures: a renderer must report their conflicts without
   altering input geometry. All other fixtures retain the zero-outside gate. */
'use strict';
const crypto=require('node:crypto');
const expected=require('../phase9_2/fixtures/alignment_expectations.json');
function evaluate(name,input,diagnostics){
  const e=expected[name];
  if(!e)return {ok:diagnostics.outside_host_objects===0,kind:'NO_OUTSIDE_OBJECTS'};
  const digest=crypto.createHash('sha256').update(JSON.stringify(input)).digest('hex');
  const fields=['INSIDE','INTERSECTING_BOUNDARY','OUTSIDE','UNRESOLVED'];
  const ok=digest===e.model_sha256 &&
    diagnostics.objects_checked===e.objects_checked &&
    diagnostics.outside_host_objects===e.containment.OUTSIDE &&
    fields.every(k=>diagnostics.containment?.[k]===e.containment[k]) &&
    ['x','y','z'].every(k=>diagnostics.outside_axes?.[k]===e.outside_axes[k]) &&
    diagnostics.review_status==='REVIEW_REQUIRED' &&
    diagnostics.writes_to_model===false && diagnostics.objects_moved_to_fit===0;
  return {ok,kind:'EXPECTED_CONFLICTS_REQUIRE_REVIEW',
    expected_outside:e.containment.OUTSIDE,actual_outside:diagnostics.outside_host_objects,
    source_matches:digest===e.model_sha256};
}
module.exports={evaluate};
