"""Independent serialized GLB vertex and PNG verification. No bpy/Blender exporter code."""
import json, struct, math
from pathlib import Path
from PIL import Image, ImageStat
root=Path('test-output/blender')
spec=json.loads((root/'scene.json').read_text());raw=(root/'model.glb').read_bytes()
assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,4)[0]==2
size=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+size]);binary=raw[28+size:]
assert not any(b.get('uri') for b in gltf.get('buffers',[]))
identity=[[1 if i==j else 0 for j in range(4)] for i in range(4)]
def multiply(a,b): return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def matrix(node):
    if 'matrix' in node:return [[node['matrix'][j*4+i] for j in range(4)] for i in range(4)]
    x,y,z,w=node.get('rotation',[0,0,0,1]);s=node.get('scale',[1,1,1]);t=node.get('translation',[0,0,0])
    rotation=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    return [[rotation[i][j]*s[j] for j in range(3)]+[t[i]] for i in range(3)]+[[0,0,0,1]]
found={}
def visit(index,parent):
    node=gltf['nodes'][index];world=multiply(parent,matrix(node))
    if 'mesh' in node:
        oid=node.get('extras',{}).get('objectId');assert oid and oid not in found
        vertices=[]
        for p in gltf['meshes'][node['mesh']]['primitives']:
            acc=gltf['accessors'][p['attributes']['POSITION']];assert acc['componentType']==5126 and acc['type']=='VEC3'
            view=gltf['bufferViews'][acc['bufferView']];start=view.get('byteOffset',0)+acc.get('byteOffset',0);stride=view.get('byteStride',12)
            for i in range(acc['count']):
                v=(*struct.unpack_from('<fff',binary,start+i*stride),1)
                vertices.append([sum(world[j][k]*v[k] for k in range(4)) for j in range(3)])
        found[oid]={'min':[min(v[k] for v in vertices) for k in range(3)],'max':[max(v[k] for v in vertices) for k in range(3)],'elementId':node['extras'].get('elementId')}
    for child in node.get('children',[]):visit(child,world)
for node in gltf['scenes'][gltf.get('scene',0)]['nodes']:visit(node,identity)
assert len(found)==len(spec['objects'])
errors=[]
for obj in spec['objects']:
    actual=found[obj['id']];x,y,z=obj['min'];w,d,h=obj['size'];expected=[x,z,-y-d,x+w,z+h,-y]
    error=max(abs(a-b) for a,b in zip(actual['min']+actual['max'],expected));assert error<.00005,(obj['id'],error,actual,expected)
    assert actual['elementId']==obj['elementId'];errors.append(error)
images=[]
for name in ['exterior.png','interior.png']:
    im=Image.open(root/name);assert im.size==(spec['resolution']['width'],spec['resolution']['height']);im.load()
    deviations=ImageStat.Stat(im.convert('RGB')).stddev;assert max(deviations)>5,(name,deviations)
    images.append({'file':name,'size':im.size,'stddev':deviations})
report={'status':'PASS','glbObjectsVerified':len(found),'maximumVertexBoundsErrorM':max(errors),'images':images,'scope':'Independent glTF 2.0 vertex decoding and raster image checks; not architectural approval'}
(root/'independent-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
