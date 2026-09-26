'use strict';
// Execute the shipped review renderers with a minimal DOM. This measures table
// content and replacement behavior, not browser layout, WebGL, or API validation.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ROOT=path.resolve(__dirname,'../..');
const alignment='محاذاة النوى بين الأدوار';
const traversal='المشي/الانتقال الفعلي بين الأدوار';
class Element {
  constructor(){this.children=[];this.value='';this.dataset={};this.hidden=false;this._text='';this.classList={contains:()=>false,toggle(){},add(){}};}
  set textContent(value){this._text=String(value);this.children=[];}
  get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
  append(...items){this.children.push(...items);}
  replaceChildren(...items){this._text='';this.children=items;}
  setAttribute(){}
  addEventListener(){}
  querySelectorAll(){return [];}
}
const surfaces=[
  {name:'connected workspace',file:'public/app/ui/connected-workspace.mjs',pass:'اجتاز ضمن نطاق الفحص',root:'cwChecks',suffix:`
    draw=()=>{};
    globalThis.renderReview=async review=>{
      const packet={revision:{version:1},projections:[],scorecard:{metrics:{}},review,locks:{rooms:[],semantic:[]},requirements:[]};
      await renderState({review_packet:packet,revision_id:'r1',head:'r1',history:[{revision_id:'r1',version:1,state:'DRAFT',note:'fixture'}]},{keepStep:true});
    };`},
  {name:'standalone review',file:'public/plan-review/review.mjs',pass:'اجتاز وفق الملف',root:'scopes',suffix:`
    draw=()=>{};
    globalThis.renderReview=review=>{
      versions=[{revision:{},projections:[],scorecard:{metrics:{}},review,locks:{rooms:[],semantic:[]},requirements:[]}];
      $('revision').value='0';showVersion();
    };`},
];
function renderer(surface,source=fs.readFileSync(path.join(ROOT,surface.file),'utf8')){
  const elements=new Map();
  const document={body:new Element(),getElementById:id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement:()=>new Element(),addEventListener(){},querySelectorAll:()=>[]};
  const context={document,window:{},console,parseReviewFile:async raw=>JSON.parse(raw)};
  vm.createContext(context);
  vm.runInContext(source.replace(/^import .*;\s*$/gm,'').replace(/^export /gm,'')+'\n'+surface.suffix,context,{filename:surface.file});
  return async review=>{
    const snapshot=JSON.stringify(review);
    await context.renderReview(review);
    assert.equal(JSON.stringify(review),snapshot,'presentation must not mutate the review');
    const children=document.getElementById(surface.root).children;
    if(surface.root==='cwChecks')return children.map(row=>row.children.map(cell=>cell.textContent));
    const rows=[];for(let i=0;i<children.length;i+=2)rows.push([children[i].textContent,children[i+1].textContent]);return rows;
  };
}
const review=(coverage,status='PASS')=>({scopes:{vertical_circulation:status,regulatory_compliance:'NOT_VERIFIED',structural_safety:'NOT_VERIFIED'},issues:[],...(coverage===undefined?{}:{coverage:{vertical_circulation:coverage}})});
function physical(rows){
  const row=rows.filter(r=>r[0]===traversal);assert.equal(row.length,1,'physical traversal needs its own row');
  assert.match(row[0][1],/^غير متحقق(?:$| — )/);assert.doesNotMatch(row[0][1],/اجتاز/);return row[0][1];
}
const cases=[];
for(const surface of surfaces){
  cases.push([surface.name+': legacy PASS describes only alignment',async()=>{
    const rows=await renderer(surface)(review());assert.deepEqual(rows.find(r=>r[0]===alignment),[alignment,surface.pass]);
    assert.equal(rows.some(r=>['الحركة بين الأدوار','الحركة الرأسية'].includes(r[0])),false);physical(rows);
  }]);
  cases.push([surface.name+': missing geometry is explicitly disclosed',async()=>{
    const rows=await renderer(surface)(review({core_alignment:'PASS',physical_traversal:'NOT_VERIFIED',geometry:'MISSING',missing_geometry:[{level_index:0,room_id:'stairs',core_id:'stairs-core',kind:'stairs'}]}));
    assert.match(physical(rows),/هندسة الدرج أو المصعد.*غير مكتملة/);
  }]);
  cases.push([surface.name+': represented elements never prove traversal',async()=>{
    const rows=await renderer(surface)(review({core_alignment:'PASS',physical_traversal:'NOT_VERIFIED',geometry:'PRESENT',missing_geometry:[]}));
    assert.doesNotMatch(physical(rows),/غير مكتملة/);assert.equal(rows.find(r=>r[0]===alignment)?.[1],surface.pass);
  }]);
  cases.push([surface.name+': single-storey and failed alignment keep their existing statuses',async()=>{
    for(const [status,text] of [['PASS',surface.pass],['FAIL','يحتاج معالجة'],['NOT_VERIFIED','غير متحقق'],['NOT_APPLICABLE',surface.root==='cwChecks'?'لا ينطبق على هذا المشروع':'غير منطبق على هذه النسخة']]){
      const rows=await renderer(surface)(review({core_alignment:status,physical_traversal:'NOT_VERIFIED',geometry:'NOT_APPLICABLE',missing_geometry:[]},status));
      assert.equal(rows.find(r=>r[0]===alignment)?.[1],text);assert.doesNotMatch(physical(rows),/غير مكتملة/,'single-storey coverage must not imply missing stairs');
    }
  }]);
  cases.push([surface.name+': unknown or malformed coverage cannot manufacture a pass',async()=>{
    for(const data of [null,[],{},'PASS',{core_alignment:'PASS',physical_traversal:'PASS',geometry:'PRESENT'},{geometry:'<img src=x onerror=alert(1)>'}]){
      const rows=await renderer(surface)(review(data));assert.doesNotMatch(physical(rows),/<img|onerror/);
    }
  }]);
  cases.push([surface.name+': revision changes remove stale missing-geometry evidence',async()=>{
    const render=renderer(surface);physical(await render(review({geometry:'MISSING'})));
    const rows=await render(review({geometry:'PRESENT'}));assert.doesNotMatch(physical(rows),/غير مكتملة/);
    assert.equal(rows.find(r=>r[0]==='الامتثال التنظيمي')?.[1],'غير متحقق');
    assert.equal(rows.find(r=>r[0]==='السلامة الإنشائية')?.[1],'غير متحقق');
  }]);
  const source=fs.readFileSync(path.join(ROOT,surface.file),'utf8');
  const row=source.split('\n').find(line=>line.includes(traversal)&&(line.includes('checks.push(')||line.includes("pair($('scopes')")));
  const geometry=(surface.root==='cwChecks'?'packet':'active')+".review.coverage?.vertical_circulation?.geometry==='MISSING'";
  const mutations=[
    ['broad alignment label',"vertical_circulation:'"+alignment+"'","vertical_circulation:'الحركة بين الأدوار'",review(),rows=>assert.equal(rows.find(r=>r[0]===alignment)?.[1],surface.pass)],
    ['missing physical row',row,'',review(),physical],
    ['false physical pass',"const traversal='غير متحقق — '","const traversal='اجتاز — '",review({geometry:'PRESENT',physical_traversal:'NOT_VERIFIED'}),physical],
    ['missing geometry suppression',geometry,'false',review({geometry:'MISSING'}),rows=>assert.match(physical(rows),/غير مكتملة/)],
    ['false missing geometry',geometry,'true',review({geometry:'PRESENT'}),rows=>assert.doesNotMatch(physical(rows),/غير مكتملة/)],
    ['legacy fallback suppression',row,'if('+(surface.root==='cwChecks'?'packet':'active')+'.review.coverage?.vertical_circulation) '+row,review(),physical],
  ];
  for(const [name,from,to,input,guard] of mutations)cases.push([surface.name+': reject mutation '+name,async()=>{
    guard(await renderer(surface)(input));
    assert.equal(typeof from,'string','the mutation needs its real rendering statement');
    assert.equal(source.split(from).length-1,1,'mutation anchor must occur once');
    const mutant=renderer(surface,source.replace(from,to));
    await assert.rejects(async()=>guard(await mutant(input)),assert.AssertionError,'mutation survived');
  }]);
}
// Optional handshake with an engineering review of an actually captured model.
// Keep captured customer data out of the repository and ordinary CI fixtures.
const reviewArg=process.argv.indexOf('--review');
if(reviewArg!==-1){
  assert.ok(process.argv[reviewArg+1],'--review requires a local JSON path');
  const captured=JSON.parse(fs.readFileSync(process.argv[reviewArg+1],'utf8'));
  for(const surface of surfaces)cases.push([surface.name+': captured multilevel review handshake',async()=>{
    assert.equal(captured.scopes.vertical_circulation,'PASS');
    assert.equal(captured.coverage.vertical_circulation.geometry,'MISSING');
    assert.equal(captured.coverage.vertical_circulation.physical_traversal,'NOT_VERIFIED');
    assert.equal(captured.can_approve,true,'conceptual approval is separate from traversal proof');
    const rows=await renderer(surface)(captured);
    assert.equal(rows.find(r=>r[0]===alignment)?.[1],surface.pass);
    assert.match(physical(rows),/هندسة الدرج أو المصعد.*غير مكتملة/);
  }]);
}
(async()=>{
  let failed=0;
  for(const [name,test] of cases){try{await test();console.log('PASS '+name);}catch(e){failed++;console.error('FAIL '+name+'\n'+e.stack);}}
  console.log('AUDIT VERTICAL DISCLOSURES: '+(cases.length-failed)+' passed, '+failed+' failed');
  if(failed)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
