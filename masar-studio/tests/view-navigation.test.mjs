import test from 'node:test';
import assert from 'node:assert/strict';
import {VIEW_DIRECTIONS,fitPerspectiveBounds,visualLevelIds,visibleInView,visibleForPicking} from '../shared/view-navigation.js';
const dot=(a,b)=>a.reduce((s,n,i)=>s+n*b[i],0);
test('perspective fitting keeps all real corners inside landscape and portrait frusta for every labelled direction',()=>{
    // Independent projection, not a stored expected distance.
    for(const aspect of [.2,.5,1,1.5,3,5]) for(const preset of Object.keys(VIEW_DIRECTIONS)) {
        for(const b of [{min:[0,-.3,-25],max:[20,3.5,0]},{min:[1,30,-20],max:[8,34,-4]},{min:[-200,-5,90],max:[10,50,170]}]){
            const f=fitPerspectiveBounds(b,preset,aspect,45),tanY=Math.tan(Math.PI/8);
            for(let bits=0;bits<8;bits++){
                const point=b.min.map((n,i)=>(bits>>i)&1?b.max[i]:n),delta=point.map((n,i)=>n-f.position[i]),depth=-dot(delta,f.back);
                assert.ok(depth>f.near&&depth<f.far);
                assert.ok(Math.abs(dot(delta,f.right)/(depth*tanY*aspect))<.9,preset+' horizontal');
                assert.ok(Math.abs(dot(delta,f.up)/(depth*tanY))<.9,preset+' vertical');
            }
        }
    }
});
test('north south east and west presets use model axes, never infer a street direction',()=>{
    const b={min:[0,0,-25],max:[20,3,0]};
    const n=fitPerspectiveBounds(b,'north'),s=fitPerspectiveBounds(b,'south'),e=fitPerspectiveBounds(b,'east'),w=fitPerspectiveBounds(b,'west');
    assert.ok(n.position[2]<n.target[2]&&s.position[2]>s.target[2]);
    assert.ok(e.position[0]>e.target[0]&&w.position[0]<w.target[0]);
    const top=fitPerspectiveBounds(b,'top');assert.ok(top.back[1]>.999&&top.up[2]<-.999);
});
test('camera helper refuses malformed bounds and unsafe projection parameters without mutating inputs',()=>{
    const b={min:[0,0,0],max:[20,3,25]},old=structuredClone(b);
    for(const args of [[b,'missing',1,45],[b,'top',0,45],[b,'iso',1,180],[{min:[0,0],max:[1,1,1]}],[{min:[2,0,0],max:[1,1,1]}],[{min:[NaN,0,0],max:[1,1,1]}]])assert.throws(()=>fitPerspectiveBounds(...args));
    fitPerspectiveBounds(b);assert.deepEqual(b,old);
});
test('level choices are distinct and ordered by canonical elevation, not by label or object order',()=>{
    const spec={proofs:{rooms:[{levelId:'upper',elevation:3.4},{levelId:'ground',elevation:0},{levelId:'upper',elevation:3.4}]}};
    const before=structuredClone(spec);assert.deepEqual(visualLevelIds(spec),['ground','upper']);assert.deepEqual(spec,before);
    assert.deepEqual(visualLevelIds(null),[]);
    assert.throws(()=>visualLevelIds({proofs:{rooms:[{levelId:'x',elevation:0},{levelId:'x',elevation:2}]}}));
});
test('floor isolation hides unrelated levels and site without ever moving or deleting objects',()=>{
    const objects=[{id:'g',levelId:'G',category:'wall'},{id:'u',levelId:'U',category:'wall'},{id:'r',levelId:'U',category:'roof'},{id:'s',category:'site'}],before=structuredClone(objects);
    assert.deepEqual(objects.filter(o=>visibleInView(o,{levelId:'G'})).map(o=>o.id),['g']);
    assert.deepEqual(objects.filter(o=>visibleInView(o,{levelId:'U',cutaway:true})).map(o=>o.id),['u']);
    assert.deepEqual(objects.filter(o=>visibleInView(o,{cutaway:true})).map(o=>o.id),['g','u','s']);
    assert.deepEqual(objects.filter(o=>visibleInView(o)).map(o=>o.id),['g','u','r','s']);
    assert.deepEqual(objects,before);
});
test('ray hit rejection includes invisible ancestors, not just the leaf mesh',()=>{
    assert.equal(visibleForPicking({visible:false}),false);
    assert.equal(visibleForPicking({visible:true,parent:{visible:false}}),false);
    assert.equal(visibleForPicking({visible:true,parent:{visible:true}}),true);
});
