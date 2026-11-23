// Shipped panel functions with a minimal output sink, not a real-browser claim.
const assert=require('assert');
const host={innerHTML:'',querySelectorAll(){return [];}};
global.document={getElementById(id){return id==='bxBody'?host:null;}};
function fixture(form){
  const obj={id:'stair',kind:'stairs',x:2,z:2,w:1,d:2,h:3};
  if(form!==undefined)obj.form=form;
  return {building_id:'b',model_hash:form?'bad':'good',current_revision:form?'r2':'r1',
    model:{meta:{type:'residential'},site:{w:8,d:8},wall_h:3,wall_t:.2,floor_height:3.2,
      levels:[{index:0,template:'f',elevation:0}],floors:{f:{rooms:[
        {id:'core',rect:[0,0,8,8],walls:'none',objects:[obj]}]}}}};
}
BX.attach(fixture());
assert.equal(BX.exportBim().valid,true);
const previous=BX.state().manifest.export_id;
assert(host.innerHTML.includes(previous));
const invalid=fixture('u_return');
invalid.model.floors.f.rooms[0].objects[0].id='<img src=x onerror=alert(1)>';
BX.attach(invalid);
const failure=BX.exportBim();
assert.equal(failure.valid,false);
assert.equal(BX.state().manifest,null,'previous valid export must not survive a blocked stair export');
assert.equal(failure.manifest,null);
assert.equal(BX.state().exportIssues[0].code,'BIM_EXPORT_VALIDATION_FAILED');
assert(host.innerHTML.includes('data-bx-section="EXPORT_ERRORS"'));
assert(host.innerHTML.includes('تعذّر تصدير IFC'));
assert(host.innerHTML.includes('حدود الفراغات'));
assert(host.innerHTML.includes('&lt;img src=x onerror=alert(1)&gt;'));
assert(!host.innerHTML.includes('<img'));
assert(!host.innerHTML.includes(previous));
assert(!host.innerHTML.includes('data-bx-section="EXPORT"'));
BX.attach(fixture());
assert.equal(BX.exportBim().valid,true);
assert.equal(BX.state().exportIssues.filter(i=>i.blocking).length,0);
assert(!host.innerHTML.includes('EXPORT_ERRORS'));
const invalidIdentifier=fixture();
invalidIdentifier.building_id='bad identifier';
BX.attach(invalidIdentifier);
assert.equal(BX.exportBim().valid,false);
assert.equal(BX.state().manifest,null,'validation failure must not create a success descriptor');
assert(BX.state().exportIssues.some(i=>i.blocking));
const malformed=fixture();
malformed.model.floors.f.rooms[0].walls=['UNKNOWN'];
BX.attach(malformed);
assert.equal(BX.exportBim().valid,false,'unexpected model validation exception must become visible failure');
assert.equal(BX.state().manifest,null);
assert(host.innerHTML.includes('EXPORT_ERRORS'));
BX.attach(null);
assert.equal(BX.exportBim(),null);
assert(!host.innerHTML.includes('data-bx-section="EXPORT"'));
delete global.document;
console.log('Stair IFC panel refusal, escaped issues and stale-manifest regression passed');
