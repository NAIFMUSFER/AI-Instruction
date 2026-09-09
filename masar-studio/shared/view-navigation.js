/**
 * Presentation-only camera math and visibility. Coordinates here are Three.js:
 * X east, Y up, Z south. No project/history or floor-to-floor coordinates change.
 */
export const VIEW_DIRECTIONS = Object.freeze({
    iso: Object.freeze([.6,.52,.7]), top: Object.freeze([0,1,.0001]),
    south: Object.freeze([0,.12,1]), north: Object.freeze([0,.12,-1]),
    east: Object.freeze([1,.12,0]), west: Object.freeze([-1,.12,0])
});
export function visualLevelIds(spec) {
    const map = new Map();
    for (const room of spec?.proofs?.rooms || []) {
        if (typeof room.levelId === 'string' && Number.isFinite(room.elevation)) {
            if (map.has(room.levelId) && Math.abs(map.get(room.levelId)-room.elevation)>1e-5)
                throw Error('ارتفاع الدور غير متسق في مشهد العرض.');
            map.set(room.levelId,room.elevation);
        }
    }
    return [...map].sort((a,b)=>a[1]-b[1]).map(([id])=>id);
}
export function visibleInView(data,{levelId=null,cutaway=false}={}) {
    if (levelId!==null && data.levelId!==levelId) return false;
    return !(cutaway && ['roof','ceiling'].includes(data.category));
}
/** Three.js raycasting can hit invisible meshes; check all ancestors explicitly. */
export function visibleForPicking(object) {
    for(let node=object;node;node=node.parent) if(node.visible===false) return false;
    return true;
}
const dot=(a,b)=>a.reduce((sum,n,i)=>sum+n*b[i],0);
const norm=a=>{const n=Math.hypot(...a);if(n<1e-10)throw Error('اتجاه الكاميرا غير صالح.');return a.map(x=>x/n);};
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
/** Fit all eight actual bounding corners to vertical AND horizontal perspective FOV. */
export function fitPerspectiveBounds(bounds,preset='iso',aspect=1,fov=45) {
    const {min,max}=bounds||{};
    if(!Array.isArray(min)||!Array.isArray(max)||min.length!==3||max.length!==3||
       ![...min,...max,aspect,fov].every(Number.isFinite) || aspect<=0 || fov<=1 || fov>=170 ||
       max.some((n,i)=>n<min[i]) || !Object.hasOwn(VIEW_DIRECTIONS,preset))
        throw Error('حدود أو زاوية معاينة غير صالحة.');
    const center=min.map((n,i)=>(n+max[i])/2),back=norm(VIEW_DIRECTIONS[preset]);
    const right=norm(cross([0,1,0],back)),up=cross(back,right);
    const tanY=Math.tan(fov*Math.PI/360),tanX=tanY*aspect;
    let distance=.5;
    for(let bits=0;bits<8;bits++) {
        const v=min.map((n,i)=>((bits>>i)&1?max[i]:n)-center[i]);
        distance=Math.max(distance,dot(v,back)+Math.max(Math.abs(dot(v,right))/tanX,Math.abs(dot(v,up))/tanY)*1.12+.1);
    }
    const diagonal=Math.hypot(...min.map((n,i)=>max[i]-n));
    return {target:center,position:center.map((n,i)=>n+back[i]*distance),distance,
        near:.01,far:Math.max(50,distance+diagonal*4),back,right,up};
}
