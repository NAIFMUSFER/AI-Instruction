// C09d: evaluate the shipped mirror and compare geometry, quantities and PDF paths.
if(require.main===module){require('../lib/run.js').run(__filename);}else{
  const assert=require('assert/strict'),path=require('path'),cp=require('child_process');
  const cases=JSON.parse(cp.execFileSync('python3',['tests/remediation/test_polygon_documentation.py','--cases'],
    {cwd:path.resolve(__dirname,'../..'),encoding:'utf8'}));
  let passed=0,failed=0;
  for(let i=0;i<cases.length;i++)try{
    const p=cases[i],src=dcSources(p.project),r=dcBuildView(p.project,p.spec,src);
    const ops=dcDrawOps(r.view,r.geometry,r.dimensions,r.annotations,420,297);
    assert.deepEqual(JSON.parse(JSON.stringify(r.geometry)),p.result.geometry);
    assert.deepEqual(JSON.parse(JSON.stringify(r.annotations)),p.result.annotations);
    assert.deepEqual(JSON.parse(JSON.stringify(ops)),p.ops);
    assert.deepEqual(JSON.parse(JSON.stringify(dcQuantities(p.project,null,src))),p.quantities);
    const pdf=dcSheetPdfStreams([p.sheet],{[r.view.view_id]:ops});
    assert.deepEqual(JSON.parse(JSON.stringify(pdf.content_streams)),p.pdf_streams);
    if(i===0){
      const svg=dcViewSvg(r.view,r.geometry,r.dimensions,r.annotations).svg;
      assert.ok(svg.includes('<polygon '));
      assert.equal(r.geometry.elements.find(e=>e.category==='SPACE').shape,'polygon');
      assert.equal(p.quantities.report.quantities.find(e=>e.quantity_type==='FLOOR_AREA').quantity,20);
    }else assert.deepEqual(r.geometry.elements.filter(e=>e.category==='SLAB').map(e=>[e.u0,e.u1]),[[0,2]]);
    passed++;console.log('PASS polygon documentation '+i);
  }catch(e){failed++;console.error('FAIL polygon documentation '+i+'\n'+e.stack);}
  console.log(`POLYGON DOCUMENTATION: ${passed} passed, ${failed} failed`);
  if(failed)process.exitCode=1;
}
