// The guest can inspect the same architectural meshes when a GPU context is unavailable.
// Three supplies CPU-side geometry and camera matrices. Canvas receives a depth-tested image.
import * as THREE from 'three';
import {compile} from '../core/viewer.js';
import '../core/disciplines.js';
import '../generated/pbr.js';
import {__ACS_SHARED} from '../shared-state.js';
import {apartmentJoinery,disposeGuestJoinery,fitGuestCamera,guestFocus,visibleInGuestCut} from './guest-presentation.mjs';

const cache=new WeakMap();
const corners=[
  [-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],
  [-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]
];
const faces=[[0,3,2,1],[4,5,6,7],[0,4,7,3],[1,2,6,5],[3,7,6,2],[0,1,5,4]];
const sun=new THREE.Vector3(-.44,.86,-.48).normalize();
const metalLight=new THREE.Color('#b5a58e');
const metalDark=new THREE.Color('#64584f');

function makeSolid(mesh,matrix,level,layer,name){
  const size=mesh.geometry.parameters;
  if(!size||mesh.geometry.type!=='BoxGeometry')throw new Error('SOFTWARE_VIEW_UNKNOWN_GEOMETRY');
  const vertices=corners.map(([x,y,z])=>new THREE.Vector3(x*size.width/2,y*size.height/2,z*size.depth/2).applyMatrix4(matrix));
  const material=mesh.material;
  const color=material.color.clone();
  if(layer==='WINDOW'||material.userData.matName==='door_glass')color.set('#74999b');
  if(layer==='FLOOR'&&!material.userData.tint)color.set('#b9b3a7');
  const faceColors=faces.map(([a,b,c])=>{
    const n=vertices[b].clone().sub(vertices[a]).cross(vertices[c].clone().sub(vertices[a])).normalize();
    const light=.53+.44*Math.max(0,n.dot(sun))+.09*Math.max(0,n.y);
    const shade=color.clone().multiplyScalar(light);
    if(material.metalness>.2)shade.lerp(n.y>.2?metalLight:metalDark,.12);
    return shade.getHex();
  });
  return {level,layer,name,vertices,faceColors};
}

function sceneFor(building){
  const saved=cache.get(building);
  if(saved)return saved;
  const useTextures=__ACS_SHARED.USE_TEX;
  let model;
  try{
    __ACS_SHARED.USE_TEX=false;
    model=compile(structuredClone(building));
  }finally{__ACS_SHARED.USE_TEX=useTextures;}
  model.updateMatrixWorld(true);
  const bounds=new THREE.Box3(),solids=[];
  for(const mesh of model.children){
    if(!mesh.visible||!mesh.isMesh)continue;
    const [layer,floor]=mesh.name.split('|');
    const solid=makeSolid(mesh,mesh.matrixWorld,Number(floor.slice(1)),layer,mesh.name);
    solids.push(solid);
    for(const vertex of solid.vertices)bounds.expandByPoint(vertex);
  }
  // The same facade frames and cornices displayed by the primary viewer.
  const joinery=apartmentJoinery(model,building),frame=new THREE.Matrix4();
  for(const batch of joinery.children)for(let i=0;i<batch.count;i++){
    batch.getMatrixAt(i,frame);
    solids.push(makeSolid(batch,frame,Number(batch.userData.floor.slice(1)),'TRIM',batch.name));
  }
  disposeGuestJoinery(joinery);
  const focus={
    interior:guestFocus(model,building,'interior',false),
    detail:guestFocus(model,building,'detail',false)
  };
  for(const mesh of model.children)mesh.geometry.dispose();
  const result={solids,bounds,focus};
  cache.set(building,result);
  return result;
}

function triangle(a,b,c,color,frame){
  const edge=(p,q,x,y)=>(q.x-p.x)*(y-p.y)-(q.y-p.y)*(x-p.x);
  const area=edge(a,b,c.x,c.y);
  // Outward winding becomes clockwise on screen because pixel Y increases down.
  if(area>=-1e-7)return;
  const {width,height,pixels,depth}=frame;
  const left=Math.max(0,Math.ceil(Math.min(a.x,b.x,c.x)-.5));
  const right=Math.min(width-1,Math.floor(Math.max(a.x,b.x,c.x)-.5));
  const top=Math.max(0,Math.ceil(Math.min(a.y,b.y,c.y)-.5));
  const bottom=Math.min(height-1,Math.floor(Math.max(a.y,b.y,c.y)-.5));
  const red=color>>16,green=color>>8&255,blue=color&255;
  for(let y=top;y<=bottom;y++){
    let wa=edge(b,c,left+.5,y+.5)/area,wb=edge(c,a,left+.5,y+.5)/area;
    for(let x=left;x<=right;x++,wa+=(b.y-c.y)/area,wb+=(c.y-a.y)/area){
      const wc=1-wa-wb;
      if(wa<0||wb<0||wc<0)continue;
      const z=wa*a.z+wb*b.z+wc*c.z,index=y*width+x;
      if(z>=depth[index])continue;
      depth[index]=z;
      if(pixels){
        const offset=index*4;
        pixels[offset]=red; pixels[offset+1]=green; pixels[offset+2]=blue;
      }
    }
  }
}

// Clip against the camera's near plane before division. This also supports an eye inside a room.
function clipNear(vertices){
  const result=[];
  let prev=vertices.at(-1),p=prev.z+prev.w;
  for(const next of vertices){
    const q=next.z+next.w;
    if((p<0)!==(q<0))result.push(prev.clone().lerp(next,p/(p-q)));
    if(q>=0)result.push(next);
    prev=next;p=q;
  }
  return result;
}

// The shadow pass uses the same surfaces as the camera, including the opening through
// the entire roof. Reconstruct each visible point from its stored depth for soft shadows.
function drawSolids(solids,vp,frame,ground){
  const {width,height}=frame;
  const project=p=>new THREE.Vector4(p.x,p.y,p.z,1).applyMatrix4(vp);
  const pixel=p=>({x:(p.x/p.w+1)*width/2,y:(1-p.y/p.w)*height/2,z:p.z/p.w});
  function polygon(verts,color){
    const clipped=clipNear(verts).map(pixel);
    for(let i=1;i+1<clipped.length;i++)triangle(clipped[0],clipped[i],clipped[i+1],color,frame);
  }
  if(ground){
    const {w,d}=ground,p=(x,z)=>project({x,y:-.1,z});
    polygon([p(-1.6,-1.6),p(-1.6,d+1.6),p(w+1.6,d+1.6),p(w+1.6,-1.6)],0xc5bba7);
  }
  for(const solid of solids){
    const projected=solid.vertices.map(project);
    for(let i=0;i<faces.length;i++)polygon(faces[i].map(k=>projected[k]),solid.faceColors[i]);
  }
}

function shadowMap(solids,box){
  const {center,radius}=box.getBoundingSphere(new THREE.Sphere());
  const light=new THREE.OrthographicCamera(-radius,radius,radius,-radius,.05,4*radius);
  light.position.copy(center).addScaledVector(sun,2*radius);light.lookAt(center);light.updateMatrixWorld();
  const vp=light.projectionMatrix.clone().multiply(light.matrixWorldInverse);
  const size=512,depth=new Float32Array(size*size).fill(Infinity);
  drawSolids(solids.filter(s=>s.layer!=='WINDOW'),vp,{depth,width:size,height:size});
  return {size,depth,vp};
}

function applyShadows(frame,cameraVP,map){
  const {width,height,depth,pixels}=frame;
  const m=map.vp.clone().multiply(cameraVP.clone().invert()).elements;
  for(let y=0;y<height;y++){
    const ny=1-2*(y+.5)/height;
    for(let x=0;x<width;x++){
      const idx=y*width+x,nz=depth[idx];
      if(!Number.isFinite(nz))continue;
      const nx=2*(x+.5)/width-1;
      const invW=1/(m[3]*nx+m[7]*ny+m[11]*nz+m[15]);
      const u=((m[0]*nx+m[4]*ny+m[8]*nz+m[12])*invW+1)*map.size/2;
      const v=(1-(m[1]*nx+m[5]*ny+m[9]*nz+m[13])*invW)*map.size/2;
      const z=(m[2]*nx+m[6]*ny+m[10]*nz+m[14])*invW-.0026;
      if(u<1||v<1||u>=map.size-1||v>=map.size-1)continue;
      const j=Math.floor(v-.5)*map.size+Math.floor(u-.5);
      const shade=1-.058*([j,j+1,j+map.size,j+map.size+1].reduce((n,k)=>n+Number(map.depth[k]<z),0));
      if(shade<1){
        pixels[4*idx]*=shade;pixels[4*idx+1]*=shade;pixels[4*idx+2]*=shade+.015;
      }
    }
  }
}

export function drawGuestSoftwareView(canvas,building,{view='exterior',levelIndex=0}={}){
  const context=canvas.getContext('2d');
  if(!context)throw new Error('CANVAS_2D_UNAVAILABLE');
  const {solids,bounds,focus}=sceneFor(building);
  const width=Math.max(1,Math.min(1400,Math.round((canvas.clientWidth||640)*Math.min(globalThis.devicePixelRatio||1,1.5))));
  const height=Math.max(1,Math.round(width*(canvas.clientHeight||480)/(canvas.clientWidth||640)));
  if(canvas.width!==width)canvas.width=width;
  if(canvas.height!==height)canvas.height=height;
  const frame={width,height,depth:new Float32Array(width*height).fill(Infinity)};
  const image=context.createImageData(width,height);
  frame.pixels=image.data;
  for(let y=0;y<height;y++){
    const t=y/height;
    const r=226+Math.round(13*t),g=234+Math.round(4*t),b=232-Math.round(5*t);
    for(let i=y*width*4,end=i+width*4;i<end;i+=4){
      image.data[i]=r;image.data[i+1]=g;image.data[i+2]=b;image.data[i+3]=255;
    }
  }
  const cut=view==='cutaway';
  const visible=solids.filter(s=>!cut||(s.level===levelIndex&&visibleInGuestCut(s.name,false)));
  if(!visible.length)throw new Error('SOFTWARE_VIEW_EMPTY');
  const box=bounds.clone();
  if(cut){
    box.makeEmpty();
    for(const s of visible)for(const p of s.vertices)box.expandByPoint(p);
  }
  const camera=new THREE.PerspectiveCamera(41,width/height,.03,1000);
  const orbit={target:new THREE.Vector3(),update(){camera.lookAt(this.target);camera.updateMatrixWorld();}};
  const anchor=focus[view];
  fitGuestCamera(anchor?.box||box,view,camera,orbit,{width,height,right:0,top:0,bottom:0},-.1,building.meta?.acs_apartment?.street_edge);
  if(anchor?.position){
    camera.position.copy(anchor.position);orbit.target.copy(anchor.target);orbit.update();
  }
  const vp=new THREE.Matrix4().multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse);
  drawSolids(visible,vp,frame,cut?null:building.site);
  applyShadows(frame,vp,shadowMap(visible,box));
  context.putImageData(image,0,0);
  return {meshCount:visible.length,levelIndex:cut?levelIndex:null,view};
}
