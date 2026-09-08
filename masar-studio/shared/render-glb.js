/** Independent glTF 2.0 vertex readback. Validates real exported geometry, not
 * the worker's self-reported manifest. Deliberately accepts only our box subset. */
export function verifyRenderGLB(raw, scene) {
    const bytes=raw instanceof Uint8Array?raw:new Uint8Array(raw),v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
    const fail=message=>{throw Error('GLB verification: '+message);};
    if(bytes.length<28||bytes.length>24000000||v.getUint32(0,true)!==0x46546c67||v.getUint32(4,true)!==2||v.getUint32(8,true)!==bytes.length)fail('invalid header');
    const length=v.getUint32(12,true);if(length%4||length>bytes.length-28||v.getUint32(16,true)!==0x4e4f534a)fail('invalid JSON chunk');
    const doc=JSON.parse(new TextDecoder().decode(bytes.subarray(20,20+length))),binStart=28+length,binLength=v.getUint32(20+length,true);
    if(v.getUint32(24+length,true)!==0x004e4942||binStart+binLength!==bytes.length||doc.asset?.version!=='2.0')fail('invalid binary chunk');
    if(doc.buffers?.length!==1||doc.buffers[0].uri||doc.buffers[0].byteLength>binLength||(doc.images||[]).some(x=>x.uri)||doc.extensionsRequired?.length||doc.animations?.length||doc.skins?.length)fail('only embedded static meshes are accepted');
    if(!Array.isArray(doc.nodes)||doc.nodes.length>32000||!Array.isArray(doc.meshes)||doc.meshes.length>16000)fail('scene limit');
    const identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
    const matrix=(node)=>{
        let m;if(node.matrix)m=node.matrix;else{
            const [x,y,z,w]=node.rotation||[0,0,0,1],s=node.scale||[1,1,1],t=node.translation||[0,0,0];
            if(Math.abs(x*x+y*y+z*z+w*w-1)>.00001)fail('invalid rotation');
            m=[(1-2*(y*y+z*z))*s[0],2*(x*y+z*w)*s[0],2*(x*z-y*w)*s[0],0,2*(x*y-z*w)*s[1],(1-2*(x*x+z*z))*s[1],2*(y*z+x*w)*s[1],0,2*(x*z+y*w)*s[2],2*(y*z-x*w)*s[2],(1-2*(x*x+y*y))*s[2],0,...t,1];
        }
        if(m.length!==16||!m.every(Number.isFinite)||m[3]!==0||m[7]!==0||m[11]!==0||m[15]!==1)fail('non-affine transform');return m;
    };
    const mul=(a,b)=>Array.from({length:16},(_,i)=>{const r=i%4,c=Math.floor(i/4);return a[r]*b[c*4]+a[r+4]*b[c*4+1]+a[r+8]*b[c*4+2]+a[r+12]*b[c*4+3];});
    const expected=new Map(scene.objects.map(o=>[o.id,o])),found=new Set(),visited=new Set();let count=0,maxError=0;
    const roots=doc.scenes?.[doc.scene||0]?.nodes;if(!Array.isArray(roots))fail('missing default scene');
    const stack=roots.map(index=>({index,parent:identity}));
    while(stack.length){const {index,parent}=stack.pop();if(!Number.isInteger(index)||visited.has(index)||!doc.nodes[index])fail('invalid/cyclic hierarchy');visited.add(index);const node=doc.nodes[index],world=mul(parent,matrix(node));
        if(node.mesh!==undefined){const oid=node.extras?.objectId,o=expected.get(oid);if(!o||found.has(oid)||node.extras.elementId!==o.elementId)fail('element identifiers differ');found.add(oid);
            const mesh=doc.meshes[node.mesh];if(!mesh||mesh.weights||node.weights||node.skin!==undefined||!mesh.primitives?.length)fail('unsupported mesh');
            const [x,y,z]=o.min,[w,d,h]=o.size,min=[x,z,-y-d],max=[x+w,z+h,-y],boundsMin=[Infinity,Infinity,Infinity],boundsMax=[-Infinity,-Infinity,-Infinity];let corners=0;
            for(const primitive of mesh.primitives){if(primitive.targets||primitive.extensions||(primitive.mode??4)!==4)fail('unsupported primitive');const a=doc.accessors?.[primitive.attributes?.POSITION],b=doc.bufferViews?.[a?.bufferView];
                if(!a||!b||b.buffer!==0||a.componentType!==5126||a.type!=='VEC3'||a.sparse||a.normalized||!Number.isInteger(a.count)||a.count<8)fail('unsupported vertex accessor');
                const stride=b.byteStride||12,offset=(b.byteOffset||0)+(a.byteOffset||0);count+=a.count;
                if(count>2000000||!Number.isInteger(stride)||stride<12||stride>252||stride%4||offset<0||offset%4||offset+(a.count-1)*stride+12>binLength||offset+(a.count-1)*stride+12>(b.byteOffset||0)+b.byteLength)fail('invalid vertex range');
                for(let i=0;i<a.count;i++){const at=binStart+offset+i*stride,p=[v.getFloat32(at,true),v.getFloat32(at+4,true),v.getFloat32(at+8,true)],q=[0,1,2].map(k=>world[k]*p[0]+world[k+4]*p[1]+world[k+8]*p[2]+world[k+12]);let corner=0;
                    for(let k=0;k<3;k++){if(!Number.isFinite(q[k]))fail('non-finite vertex');boundsMin[k]=Math.min(boundsMin[k],q[k]);boundsMax[k]=Math.max(boundsMax[k],q[k]);const low=Math.abs(q[k]-min[k]),high=Math.abs(q[k]-max[k]);if(Math.min(low,high)>.00005)fail('vertex is not a canonical box corner');if(high<low)corner|=1<<k;}
                    corners|=1<<corner;
                }
            }
            if(corners!==255)fail('missing canonical corners');for(let k=0;k<3;k++)maxError=Math.max(maxError,Math.abs(boundsMin[k]-min[k]),Math.abs(boundsMax[k]-max[k]));
        }
        for(const child of node.children||[])stack.push({index:child,parent:world});
    }
    if(found.size!==expected.size||maxError>.00005)fail('missing elements or mismatched bounds');
    return {objects:found.size,vertices:count,maximumErrorM:maxError};
}
