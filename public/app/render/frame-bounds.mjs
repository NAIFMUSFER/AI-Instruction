import * as THREE from 'three';

export function frameBounds(box,direction,fov,aspect,margin=1.12,target=null){
  const center=target?target.clone():box.getCenter(new THREE.Vector3()),forward=direction.clone().normalize();
  const right=new THREE.Vector3(0,1,0).cross(forward).normalize(),up=forward.clone().cross(right).normalize();
  const tanV=Math.tan(THREE.MathUtils.degToRad(fov/2)),tanH=tanV*Math.max(aspect,.1);
  let distance=.1;
  for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z]){
    const point=new THREE.Vector3(x,y,z).sub(center),depth=point.dot(forward);
    distance=Math.max(distance,Math.abs(point.dot(right))*margin/tanH+depth,Math.abs(point.dot(up))*margin/tanV+depth);
  }
  return {position:center.clone().addScaledVector(forward,distance),target:center};
}
