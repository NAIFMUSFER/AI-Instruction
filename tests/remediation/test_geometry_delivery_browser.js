// Run through tests/lib/run.js: exercises shipped engine functions, no WebGL claim.
const assert=require('assert');
assert.equal(acsRenderLevel({index:-1,elevation:-3.8},4).index,-1);
assert.equal(acsRenderLevel({},4).derived,true);
const plate=pqPlateRect([[0,0,4,2],[0,2,2,2]],[0,0,10,10]);
assert.equal(plate.area_m2,12);assert.equal(plate.rectangles.reduce((a,r)=>a+r[2]*r[3],0),12);
const model={meta:{type:'warehouse'},site:{w:20,d:20},wall_h:3,wall_t:.2,floor_height:3.2,levels:[{index:0,template:'f',elevation:0}],floors:{f:{rooms:[{id:'a',rect:[0,0,5,5],walls:'none',doors:[],windows:[]}]}}};
assert.equal(compileArchitecture(model).walls.length,0);
const ap={cx:0,cy:1.05,cz:0,hx:.06,hy:1.05,hz:.1,yaw:0},wall={...ap,hx:.1,hy:1.5,hz:5},cap={radius_m:.3,height_m:1.8};
assert.equal(_rtCapsuleFitsPortal([-1,0,0],[1,0,0],cap,ap,wall),false);
ap.hz=.6;assert.equal(_rtCapsuleFitsPortal([-1,0,0],[1,0,0],cap,ap,wall),true);
assert.equal(_rtCapsuleFitsPortal([-1,0,.5],[1,0,.5],cap,ap,wall),false);
assert.equal(_rtCapsuleFitsPortal([-1,0,-1],[1,0,1],cap,ap,wall),false);
console.log('Geometry delivery browser engine regressions: passed (no GPU claim)');
