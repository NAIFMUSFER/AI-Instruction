import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {understand,generate,validate,totals,assertModel,createHistory,exportEnvelope,importEnvelope,conceptEnvelopeArea,requirementStatus,clone} from '../shared/model.js';
import {planSVG} from '../shared/geometry.js';
const prompt=readFileSync(new URL('./fixtures/customer-chalet-ar.txt',import.meta.url),'utf8');
const brief=()=>understand(prompt);
test('exact 2191-character customer request: chalet not warehouse, three bedrooms retained',()=>{
 const b=brief();assert.equal(prompt.length,2191);assert.equal(b.prompt,prompt);assert.equal(b.projectType,'chalet');assert.equal(b.bedrooms,3);assert.equal(b.width,20);assert.equal(b.depth,25);assert.equal(b.parking,1);assert.equal(b.priority,'outdoor');assert.deepEqual([b.buildingArea.min,b.buildingArea.max],[120,160]);
});
test('principal intent is not overridden by an ancillary store or office',()=>{
 for(const [p,expected] of [['فيلا بها مستودع صغير ومكتب','villa'],['شاليه مع مستودع ومكتب','chalet'],['أريد مستودع بضائع ومكتب تشغيل','warehouse'],['مكاتب مع مستودع ملفات','office'],['متجر مع مخزن خلفي','retail']])assert.equal(understand(p).projectType,expected,p);
});
test('dimensions with units and Arabic digits parse without requiring a repeated short form',()=>{
 const b=understand('فيلا بنظام شاليه على أرض ٢٠ متر واجهة × ٢٥ متر عمق. ٣ غرف نوم. مساحة البناء ١٢٠–١٦٠ م²');assert.equal(b.width,20);assert.equal(b.depth,25);assert.deepEqual([b.buildingArea.min,b.buildingArea.max],[120,160]);
 assert.equal(understand('فيلا أرض 20×25 = 500 م²').buildingArea,null,'land area must never become a building cap');
});
test('customer proposal: correct programme, envelope <=160, no redundant stair, no geometry blockers',()=>{
 const b=brief(),before=JSON.stringify(b),m=assertModel(generate(b)),errors=validate(m).filter(x=>x.status==='error');
 assert.deepEqual(errors,[]);assert.equal(JSON.stringify(b),before);assert.equal(m.brief.prompt,prompt);
 const r=m.levels[0].rooms;assert.equal(r.filter(x=>x.kind==='bedroom').length,3);assert.equal(r.filter(x=>x.kind==='stairs'||x.kind==='elevator').length,0);
 for(const kind of ['majlis','living','kitchen','dining','laundry','storage'])assert.ok(r.some(x=>x.kind===kind),kind);
 for(const label of ['غرفة ملابس الرئيسية','حمام الغرفة الرئيسية','الحمام المشترك','حمام ومغاسل الضيوف','دورة مياه المسبح','بانتري'])assert.ok(r.some(x=>x.name===label),label);
 for(const kind of ['pool','parking','terrace','garden'])assert.ok(m.site.features.some(x=>x.type===kind),kind);
 const area=conceptEnvelopeArea(m);assert.ok(area>=120&&area<=160,`actual envelope ${area}`);assert.ok(totals(m).outdoorArea>340);
 const req=m.requirements.find(x=>x.type==='building-area');assert.equal(req.locked,true);assert.equal(requirementStatus(m,req).satisfied,true);
 assert.ok(validate(m).some(x=>x.status==='unchecked'&&x.id==='r-compact-review'));
 mkdirSync('test-output/customer-after',{recursive:true});writeFileSync('test-output/customer-after/model.json',JSON.stringify(m,null,2));writeFileSync('test-output/customer-after/plan.svg',planSVG(m,'l0',{interactive:false,dimensions:true,furniture:true,issues:validate(m)}));
 writeFileSync('test-output/customer-after/summary.json',JSON.stringify({promptCharacters:prompt.length,area,totals:totals(m),errors,rooms:r.map(x=>({name:x.name,x:x.x,y:x.y,w:x.w,d:x.d,kind:x.kind})),warnings:validate(m).filter(x=>['warning','unchecked'].includes(x.status))},null,2));
});
test('area constraint remains enforced after an edit, not only at initial generation',()=>{
 const m=generate(brief());m.levels[0].rooms.find(r=>r.id==='l0-bed2').w+=12;
 assert.ok(validate(m).some(i=>i.id==='r-building-area'&&i.status==='error'));
});
test('same small budget can be reviewed on each street orientation without unrotated site features',()=>{
 for(const street of ['جنوب','شمال','شرق','غرب']){const b=brief();b.street=street;if(['شرق','غرب'].includes(street)){b.width=25;b.depth=20;}
 const m=generate(b);assert.deepEqual(validate(m).filter(x=>x.status==='error'),[],street);assert.ok(conceptEnvelopeArea(m)<=160);}
});
test('infeasible budgets fail explicitly instead of expanding or silently dropping the area constraint',()=>{
 for(const config of [{buildingArea:{min:80,max:100}},{floors:2},{bedrooms:5},{parking:4}])assert.throws(()=>generate({...brief(),...config}));
});
test('JSON project export round-trip retains the original text and measurable budget',()=>{
 const history=createHistory(generate(brief())),envelope=exportEnvelope(history);const restored=importEnvelope(typeof envelope==='string'?envelope:JSON.stringify(envelope));
 assert.equal(restored.revisions[restored.cursor].model.brief.prompt,prompt);assert.equal(restored.revisions[restored.cursor].model.requirements.find(r=>r.type==='building-area').value[1],160);
});
