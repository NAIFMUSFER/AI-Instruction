// C09b: actual shipped compiler and Three meshes. No WebGL/pixel claim.
if (require.main === module) {
  require('../lib/run.js').run(__filename);
} else {
  const a = require('assert/strict'), path = require('path');
  globalThis.THREE = require(path.resolve(__dirname,'../../node_modules/three/build/three.cjs'));
  getMat = () => new THREE.MeshStandardMaterial();
  scaleBoxUV = () => {};
  const L = [[0,0],[6,0],[6,2],[2,2],[2,6],[0,6]];
  const make = (ring=L,extra={}) => {
    const xs=ring.map(p=>p[0]),zs=ring.map(p=>p[1]);
    return {site:{w:20,d:25},wall_h:3,wall_t:.15,floor_height:3.2,
      levels:[{index:0,template:'plan',elevation:7}],floors:{plan:{rooms:[{
        id:'polygon',rect:[Math.min(...xs),Math.min(...zs),Math.max(...xs)-Math.min(...xs),Math.max(...zs)-Math.min(...zs)],
        polygon:ring.map(p=>p.slice()),walls:'full',...extra}]}}};
  };
  const triangles = (group,token,y) => {
    group.updateMatrixWorld(true);
    const out=[];
    group.traverse(o=>{
      if(!o.isMesh||!o.name.includes(token))return;
      const pos=o.geometry.getAttribute('position'),idx=o.geometry.getIndex();
      for(let i=0;i<(idx?idx.count:pos.count);i+=3){
        const tri=[0,1,2].map(j=>new THREE.Vector3().fromBufferAttribute(pos,idx?idx.getX(i+j):i+j).applyMatrix4(o.matrixWorld).toArray());
        if(y==null||tri.every(p=>Math.abs(p[1]-y)<1e-5))out.push(tri);
      }
    });return out;
  };
  const area=ts=>ts.reduce((s,[p,q,r])=>s+Math.abs((q[0]-p[0])*(r[2]-p[2])-(q[2]-p[2])*(r[0]-p[0]))/2,0);
  const covers=(tri,x,z)=>{const cr=tri.map((p,i)=>{const q=tri[(i+1)%3];return(q[0]-p[0])*(z-p[2])-(q[2]-p[2])*(x-p[0]);});
    return cr.every(v=>v>=-1e-6)||cr.every(v=>v<=1e-6);};
  let passed=0,failed=0;
  const check=(name,fn)=>{try{fn();passed++;console.log('PASS '+name);}catch(e){failed++;console.error('FAIL '+name+'\n'+e.stack);}};
  check('concave L area and notch',()=>{
    const t=triangles(compile(make()),'|slab|',7);
    a.ok(Math.abs(area(t)-20)<1e-5,'area='+area(t));
    a.equal(t.some(p=>covers(p,4,4)),false);a.ok(t.some(p=>covers(p,1,5)));
  });
  check('sloping door and immutable Building',()=>{
    const b=make([[3,4],[9,4],[3,10]],{doors:[{edge_index:1,offset:Math.sqrt(18),width:1,height:2.1}]});
    const before=JSON.stringify(b),g=compile(b),points=triangles(g,'DOOR|').flat();
    a.ok(points.length);a.equal(JSON.stringify(b),before);
    const bounds=axis=>[Math.min(...points.map(p=>p[axis])),Math.max(...points.map(p=>p[axis]))];
    a.ok(Math.abs(bounds(0).reduce((s,x)=>s+x,0)/2-6)<1e-5);
    a.ok(Math.abs(bounds(2).reduce((s,x)=>s+x,0)/2-7)<1e-5);
    const along=points.map(p=>(-p[0]+p[2])/Math.sqrt(2));
    a.ok(Math.abs(Math.max(...along)-Math.min(...along)-1)<1e-5);
  });
  check('core void and coloured finishes',()=>{
    const b=make(L,{floor_color:'#ff0000',ceiling_color:'#00ff00',objects:[{kind:'stairs',core_id:'A',x:1,z:3,w:1,d:1,h:3}]});
    b.levels.push({index:1,template:'plan',elevation:10.2});const g=compile(b);
    const slab=triangles(g,'|slab|',10.2);a.ok(Math.abs(area(slab)-19)<1e-5,'area='+area(slab));
    for(const [token,y] of [['|slab|',10.2],['|plate',10.224],['|ceil',13.195]]){
      const ts=triangles(g,token,y);a.ok(ts.length,token);
      a.equal(ts.some(t=>covers(t,4,4)),false);a.equal(ts.some(t=>covers(t,1,3)),false);
    }
  });
  check('invalid polygon is not silently rendered',()=>{
    a.throws(()=>compile(make([[0,0],[6,6],[0,6],[6,0]])),/POLYGON/);
  });
  check('clockwise outline and open-zone label',()=>{
    const g=compile(make(L.slice().reverse(),{walls:'none'}));
    a.ok(Math.abs(area(triangles(g,'|slab|',7))-20)<1e-5);
    const label=triangles(g,'|label',7.017);a.ok(label.length);a.equal(label.some(t=>covers(t,4,4)),false);
  });
  check('explicit negative origin is preserved',()=>{
    const ts=triangles(compile(make(L.map(([x,z])=>[x-100,z+230]))),'|slab|',7);
    a.ok(Math.abs(area(ts)-20)<1e-5);a.ok(ts.some(t=>covers(t,-99,235)));
    a.equal(ts.some(t=>covers(t,-96,234)),false);
  });
  check('Python and shipped JavaScript polygon parity',()=>{
    const cases=[{rings:[L],holes:[]},{rings:[L.slice().reverse()],holes:[[[.5,2.5],[1.5,2.5],[1.5,3.5],[.5,3.5]]]},
      {rings:[[[0,0],[6,0],[0,6]],[[0,2],[6,2],[6,8]]],holes:[]},
      {rings:[L.map(([x,z])=>[x-100,z+230])],holes:[]}];
    const py=require('child_process').execFileSync('python3',['-c',
      'import json,sys,acs_polygon as P; print(json.dumps([P.cells(c["rings"],c["holes"]) for c in json.load(sys.stdin)]))'],
      {cwd:path.resolve(__dirname,'../..'),input:JSON.stringify(cases),encoding:'utf8'});
    const round=v=>Array.isArray(v)?v.map(round):Math.round(v*1e8)/1e8;
    a.deepEqual(round(cases.map(c=>ACS_POLYGON.cells(c.rings,c.holes))),round(JSON.parse(py)));
  });
  check('polygon and box meshes share the same scene budget',()=>{
    const state=acsBuildDefectsReset(),g=new THREE.Group();state.accepted_box=SCENE_LIMITS.max_total_meshes-1;
    addPolygonPrism(g,[[0,0],[2,0],[0,2]],0,.15,'floor','polygon');
    addBox(g,0,0,0,1,1,1,'wall','box');
    addPolygonPrism(g,[[0,0],[2,0],[0,2]],0,.15,'floor','suppressed-polygon');
    a.equal(g.children.length,1);a.equal(state.accepted_box,SCENE_LIMITS.max_total_meshes);
    a.equal(state.suppressed_box,2);a.ok(state.degradation_reasons.includes('SCENE_COMPLEXITY_LIMIT'));
  });
  console.log(`POLYGON MESHES: ${passed} passed, ${failed} failed (actual meshes; no pixels)`);
  if(failed)process.exitCode=1;
}
