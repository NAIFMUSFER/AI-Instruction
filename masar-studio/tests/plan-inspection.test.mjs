import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fitPlanView, navigatePlanView } from '../src/plan-inspection.js';
import { planSVG, siteFeatureLabel } from '../shared/geometry.js';
import { understand, generate } from '../shared/model.js';
const prompt=readFileSync(new URL('./fixtures/customer-chalet-ar.txt',import.meta.url),'utf8');
const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-9,`${a} != ${b}`);
test('inspection camera starts at the actual site and includes drawing margin',()=>{
    assert.deepEqual(fitPlanView(20,25),{siteWidth:20,siteDepth:25,x:-2.5,y:-2.5,w:25,d:30,zoom:1});
    for(const n of [NaN,Infinity,-1,0])assert.throws(()=>fitPlanView(n,25));
});
test('camera zoom never mutates its input or exceeds 100-600 percent',()=>{
    const v=fitPlanView(20,25),before=JSON.stringify(v);
    const z=navigatePlanView(v,{zoom:2});close(z.w,12.5);close(z.d,15);close(z.x+z.w/2,10);close(z.y+z.d/2,12.5);
    assert.equal(JSON.stringify(v),before);assert.equal(navigatePlanView(z,{zoom:100}).zoom,6);assert.deepEqual(navigatePlanView(z,{zoom:0}),v);
});
test('pinch focal point remains stationary until site boundary clamping is needed',()=>{
    const a=fitPlanView(20,25),b=navigatePlanView(a,{zoom:2,anchorX:.4,anchorY:.6});
    close(a.x+a.w*.4,b.x+b.w*.4);close(a.y+a.d*.6,b.y+b.d*.6);
});
test('pan is bounded at all site sizes and zoom steps without losing the map',()=>{
    for(const [w,d] of [[12,15],[20,25],[120,160]])for(const zoom of [1,1.4,3,6])for(const dx of [-10000,0,10000])for(const dy of [-10000,0,10000]){
        const v=navigatePlanView(fitPlanView(w,d),{zoom,dx,dy});
        assert.ok(v.x>=-2.5&&v.y>=-2.5);assert.ok(v.x+v.w<=w+2.5+1e-9&&v.y+v.d<=d+2.5+1e-9);
    }
});
test('malformed camera options cannot create nonfinite SVG attributes',()=>{
    for(const key of ['zoom','dx','dy','anchorX','anchorY'])assert.throws(()=>navigatePlanView(fitPlanView(20,25),{[key]:NaN}));
});
test('all outdoor features are labelled from canonical data in vector output',()=>{
    const m=generate(understand(prompt)),before=JSON.stringify(m),svg=planSVG(m,'l0',{interactive:false});
    for(const f of m.site.features){assert.ok(svg.includes(`data-site-feature="${f.id}"`));assert.ok(svg.includes(siteFeatureLabel(f)));}
    assert.equal((svg.match(/class="site-feature"/g)||[]).length,5);assert.equal(JSON.stringify(m),before);
    for(const label of ['مسبح','موقف','جلسة','شواء','حديقة'])assert.ok(svg.includes(label));
});
test('site labels cannot inject executable or unescaped HTML and preserve user names',()=>{
    const m=generate(understand(prompt));m.site.features[0].name='<script>alert(1)</script>';m.site.features[0].id='x" onload="alert(1)';
    const svg=planSVG(m,'l0',{interactive:false});assert.ok(!svg.includes('<script>'));assert.ok(svg.includes('&lt;script&gt;'));assert.ok(!svg.includes('" onload="'));
});
test('dimension toggle suppresses outdoor dimension text but never names or geometry',()=>{
    const m=generate(understand(prompt)),yes=planSVG(m,'l0',{dimensions:true}),no=planSVG(m,'l0',{dimensions:false});
    const group=svg=>svg.match(/<g class="site-feature"[\s\S]+?<\/g><\/g>/)[0];
    assert.equal((group(yes).match(/<text /g)||[]).length,2);assert.equal((group(no).match(/<text /g)||[]).length,1);
    assert.ok(group(no).includes('<rect '));
});
test('read-only inspection has no editing or persistence imports',()=>{
    const code=readFileSync(new URL('../src/plan-inspection.js',import.meta.url),'utf8');
    assert.ok(!/\b(pushHistory|saveLocal|commitPreview|propose|stage|persist)\s*\(/.test(code));
    assert.ok(code.includes('interactive: false'));assert.ok(code.includes("svgText,'image/svg+xml'"));
});
