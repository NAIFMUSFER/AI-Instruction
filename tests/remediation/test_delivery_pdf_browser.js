/* Run through tests/lib/run.js: exercise the actual generated browser module. */
const assert=require('node:assert/strict');
const sheets=[{sheet_id:'synthetic',paper_mm:[210,297],viewports:[{view_id:'v',x:10,y:10,width:100,height:100}],title_block:{sheet_title:'Plan'}}];
const drawings={v:{paper_mm:[100,100],ops:[{op:'text',text:'مجلس الضيوف',x:10,y:10,size:3}]}};
const before=JSON.stringify({sheets,drawings});
assert.throws(()=>dcSheetPdfStreams(sheets,drawings),/PDF_UNICODE_REQUIRES_SERVER/);
assert.equal(JSON.stringify({sheets,drawings}),before);
drawings.v.ops[0].text='Meeting A-12';
const result=dcSheetPdfStreams(sheets,drawings);
assert.equal(result.page_count,1);
assert.ok(result.content_streams[0].includes('Meeting A-12'));
console.log('Browser PDF capability: Unicode refused explicitly; ASCII works; input unchanged.');
