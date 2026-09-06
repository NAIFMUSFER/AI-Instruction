// C13: test the shipped documentation mirror, not a copied placement formula.
if(require.main===module){require('../lib/run.js').run(__filename);}else{
  const assert=require('assert/strict');let passed=0,failed=0;
  const test=(name,fn)=>{try{fn();passed++;console.log('PASS '+name);}catch(e){failed++;console.error('FAIL '+name+'\n'+e.stack);}};
  for(const[edge,expected]of [['N',[13,5]],['S',[13,11]],['E',[16,8]],['W',[10,8]]]){
    test('opening centre '+edge,()=>{
      const b={wall_h:3,wall_t:.15,levels:[{index:0,template:'g'}],floors:{g:{rooms:[{id:'r',rect:[10,5,6,6],doors:[{edge,offset:3,width:1,height:2.1}]}]}}};
      const before=JSON.stringify(b),arch=compileArchitecture(b),g=_dcOpeningPlan(arch.openings[0],arch);
      assert.deepEqual(g.start.map((v,i)=>(v+g.end[i])/2),expected);assert.equal(JSON.stringify(b),before);
    });
  }
  test('oblique shared wall',()=>{
    const b={wall_h:3,wall_t:.15,levels:[{index:0,template:'g'}],floors:{g:{rooms:[{id:'a',rect:[0,0,6,6],polygon:[[0,0],[6,0],[0,6]],doors:[{edge_index:1,offset:Math.sqrt(18),width:1,height:2.1}]},{id:'b',rect:[0,0,6,6],polygon:[[6,0],[6,6],[0,6]]}]}}};
    const arch=compileArchitecture(b),g=_dcOpeningPlan(arch.openings[0],arch);
    g.start.forEach((v,i)=>assert.ok(Math.abs((v+g.end[i])/2-3)<1e-5));
  });
  console.log(`SVG OPENING ORIGIN: ${passed} passed, ${failed} failed`);if(failed)process.exitCode=1;
}
