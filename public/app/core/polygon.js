/* Building polygon contract: site-local X/Z metres. Mirror of acs_polygon.py;
   parity is tested alongside the actual exported/rendered triangle geometry. */
const ACS_POLYGON = (()=>{
  const EPS=1e-7;
  const edges=r=>r.map((p,i)=>[p,r[(i+1)%r.length]]);
  const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
  const distance=(a,b)=>Math.hypot(b[0]-a[0],b[1]-a[1]);
  const signed_area=r=>edges(r).reduce((s,[a,b])=>s+a[0]*b[1]-b[0]*a[1],0)/2;
  const on_segment=(p,a,b)=>Math.abs(cross(a,b,p))<=EPS*Math.max(distance(a,b),EPS)
    &&p[0]>=Math.min(a[0],b[0])-EPS&&p[0]<=Math.max(a[0],b[0])+EPS
    &&p[1]>=Math.min(a[1],b[1])-EPS&&p[1]<=Math.max(a[1],b[1])+EPS;
  function intersection(a,b,c,d){
    const dx=b[0]-a[0],dz=b[1]-a[1],ex=d[0]-c[0],ez=d[1]-c[1],det=dx*ez-dz*ex;
    if(Math.abs(det)<=EPS*Math.max(Math.hypot(dx,dz),Math.hypot(ex,ez),EPS))return null;
    const t=((c[0]-a[0])*ez-(c[1]-a[1])*ex)/det,u=((c[0]-a[0])*dz-(c[1]-a[1])*dx)/det;
    return t>=-EPS&&t<=1+EPS&&u>=-EPS&&u<=1+EPS?[a[0]+t*dx,a[1]+t*dz]:null;
  }
  function ring_validated(raw){
    if(!Array.isArray(raw)||raw.length<3)throw Error('POLYGON_INVALID: at least three X/Z vertices are required');
    const ring=raw.map(p=>{
      if(!Array.isArray(p)||p.length!==2||!p.every(v=>typeof v==='number'&&Number.isFinite(v)))
        throw Error('POLYGON_INVALID: vertices must be finite numeric X/Z pairs');
      return p.slice();
    });
    if(ring[0][0]===ring[ring.length-1][0]&&ring[0][1]===ring[ring.length-1][1])ring.pop();
    if(ring.length<3)throw Error('POLYGON_INVALID: fewer than three distinct vertices');
    const segments=edges(ring);
    segments.forEach(([a,b],i)=>{
      if(distance(a,b)<=EPS)throw Error('POLYGON_INVALID: zero-length edge');
      const prev=ring[(i+ring.length-1)%ring.length];
      if(on_segment(b,prev,a)||on_segment(prev,a,b))throw Error('POLYGON_INVALID: adjacent edges overlap');
      for(let j=i+1;j<segments.length;j++){
        if(j===i+1||(i===0&&j===segments.length-1))continue;
        const[c,d]=segments[j];
        if(intersection(a,b,c,d)!==null||on_segment(a,c,d)||on_segment(b,c,d)||on_segment(c,a,b)||on_segment(d,a,b))
          throw Error('POLYGON_INVALID: boundary intersects itself');
      }
    });
    if(Math.abs(signed_area(ring))<=EPS*EPS)throw Error('POLYGON_INVALID: boundary has no area');
    return ring;
  }
  const rect_ring=([x,z,w,d])=>[[x,z],[x+w,z],[x+w,z+d],[x,z+d]];
  function room_ring(room){
    if(!Object.hasOwn(room,'polygon'))return rect_ring(room.rect);
    const ring=ring_validated(room.polygon),xs=ring.map(p=>p[0]),zs=ring.map(p=>p[1]);
    const bbox=[Math.min(...xs),Math.min(...zs),Math.max(...xs)-Math.min(...xs),Math.max(...zs)-Math.min(...zs)],rc=room.rect;
    if(!Array.isArray(rc)||rc.length!==4||!rc.every(v=>typeof v==='number'&&Number.isFinite(v))
       ||rc.some((v,i)=>Math.abs(v-bbox[i])>EPS))
      throw Error('POLYGON_RECT_MISMATCH: rect must equal the polygon bounding box');
    return ring;
  }
  function contains_point(ring,p){
    let inside=false;
    for(const[a,b]of edges(ring)){
      if(on_segment(p,a,b))return true;
      if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<a[0]+(p[1]-a[1])*(b[0]-a[0])/(b[1]-a[1]))inside=!inside;
    }return inside;
  }
  function edge_index(room,opening){
    const ring=room_ring(room),i=opening.edge_index;
    if(!Number.isInteger(i)||i<0||i>=ring.length)
      throw Error('POLYGON_OPENING_EDGE_INVALID: edge_index must identify a boundary edge');
    return i;
  }
  function segment_frame(a,b){
    const dx=b[0]-a[0],dz=b[1]-a[1],length=Math.hypot(dx,dz);
    if(length<=EPS)throw Error('POLYGON_INVALID: zero-length edge');
    let tx=dx/length,tz=dz/length,axis,nx,nz;
    if(tx < -EPS||(Math.abs(tx)<=EPS&&tz<0)){tx=-tx;tz=-tz;}
    if(Math.abs(tz)<=EPS){axis='x';tx=1;tz=0;nx=0;nz=1;}
    else if(Math.abs(tx)<=EPS){axis='z';tx=0;tz=1;nx=1;nz=0;}
    else{axis='oblique';nx=-tz;nz=tx;}
    const au=a[0]*tx+a[1]*tz,bu=b[0]*tx+b[1]*tz;
    return {axis,direction:[tx,tz],normal:[nx,nz],fixed:a[0]*nx+a[1]*nz,
      u0:Math.min(au,bu),u1:Math.max(au,bu),first_u:au,sense:bu>au?1:-1};
  }
  const frame_point=(f,u)=>[0,1].map(i=>u*f.direction[i]+f.fixed*f.normal[i]);
  const zAt=([a,b],x)=>a[1]+(x-a[0])*(b[1]-a[1])/(b[0]-a[0]);
  function intervals(rings,x){
    const spans=[];
    for(const ring of rings){
      const hits=edges(ring).filter(([a,b])=>Math.min(a[0],b[0])<x&&x<Math.max(a[0],b[0])).sort((a,b)=>zAt(a,x)-zAt(b,x));
      for(let i=0;i+1<hits.length;i+=2)spans.push([hits[i],hits[i+1]]);
    }
    spans.sort((a,b)=>zAt(a[0],x)-zAt(b[0],x));
    const merged=[];
    for(const[lo,hi]of spans){
      if(merged.length&&zAt(lo,x)<=zAt(merged[merged.length-1][1],x)+EPS){
        if(zAt(hi,x)>zAt(merged[merged.length-1][1],x))merged[merged.length-1][1]=hi;
      }else merged.push([lo,hi]);
    }return merged;
  }
  function cells(rings,holes=[]){
    const all=rings.concat(holes),segments=all.flatMap(edges),cuts=all.flatMap(r=>r.map(p=>p[0]));
    segments.forEach(([a,b],i)=>{
      for(let j=i+1;j<segments.length;j++){
        const hit=intersection(a,b,...segments[j]);if(hit!==null)cuts.push(hit[0]);
      }
    });
    const xs=[];
    cuts.sort((a,b)=>a-b).forEach(x=>{if(!xs.length||x-xs[xs.length-1]>EPS)xs.push(x);});
    const out=[];
    for(let i=0;i+1<xs.length;i++){
      const left=xs[i],right=xs[i+1],mid=(left+right)/2;
      let spans=intervals(rings,mid);
      for(const[hlo,hhi]of intervals(holes,mid)){
        const remaining=[];
        for(const[lo,hi]of spans){
          if(zAt(hhi,mid)<=zAt(lo,mid)+EPS||zAt(hlo,mid)>=zAt(hi,mid)-EPS){remaining.push([lo,hi]);continue;}
          if(zAt(hlo,mid)>zAt(lo,mid)+EPS)remaining.push([lo,hlo]);
          if(zAt(hhi,mid)<zAt(hi,mid)-EPS)remaining.push([hhi,hi]);
        }spans=remaining;
      }
      for(const[lo,hi]of spans){
        const pts=[[left,zAt(lo,left)],[right,zAt(lo,right)],[right,zAt(hi,right)],[left,zAt(hi,left)]],clean=[];
        pts.forEach(p=>{if(!clean.length||distance(p,clean[clean.length-1])>EPS)clean.push(p);});
        if(clean.length>1&&distance(clean[0],clean[clean.length-1])<=EPS)clean.pop();
        if(clean.length>=3&&signed_area(clean)>EPS*EPS)out.push(clean);
      }
    }return out;
  }
  return {EPS,edges,cross,signed_area,on_segment,intersection,ring_validated,rect_ring,room_ring,contains_point,edge_index,segment_frame,frame_point,cells};
})();
export { ACS_POLYGON };
