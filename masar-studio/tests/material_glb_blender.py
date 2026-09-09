"""Run inside Blender against real browser downloads; never imports user Python or .blend files."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
out=Path(sys.argv[sys.argv.index('--')+1]).resolve()
reports=[]
for prefix in ['warm','slate']:
    spec=json.loads((out/(prefix+'-scene.json')).read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result=bpy.ops.import_scene.gltf(filepath=str(out/(prefix+'-model.glb')))
    assert 'FINISHED' in result
    expected={o['id']:o for o in spec['objects']}
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    assert len(meshes)==len(expected),(len(meshes),len(expected))
    seen=set();max_error=0
    for obj in meshes:
        key=obj.get('objectId');assert key in expected and key not in seen,(obj.name,key);seen.add(key)
        source=expected[key];points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
        lower=[min(v[i] for v in points) for i in range(3)];upper=[max(v[i] for v in points) for i in range(3)]
        error=max(abs(lower[i]-source['min'][i]) for i in range(3))
        error=max(error,max(abs(upper[i]-source['min'][i]-source['size'][i]) for i in range(3)))
        max_error=max(max_error,error);assert error<.001,(key,lower,upper,source,error)
        assert len(obj.data.polygons)>0 and len(obj.data.materials)>0
    assert seen==set(expected)
    roots=[o for o in bpy.context.scene.objects if o.get('schema')=='masar-browser-visual-1'];assert len(roots)==1
    assert roots[0]['modelId']==spec['source']['modelId'] and roots[0]['revisionId']==spec['source']['revisionId']
    roofs=[o for o in meshes if o.get('category')=='roof'];assert roofs
    if prefix=='slate':assert not any(o.get('category')=='furniture' for o in meshes)
    reports.append({'case':prefix,'blender':bpy.app.version_string,'meshes':len(meshes),'roofs':len(roofs),'maxBoundsErrorM':max_error,'sourceModel':roots[0]['modelId'],'sourceRevision':roots[0]['revisionId'],'status':'pass'})
(out/'blender-import-report.json').write_text(json.dumps({'results':reports,'scope':'Independent glTF import and object geometry/metadata; not architectural/BIM round-trip or rendered-image quality approval'},indent=2))
print('BLENDER_IMPORT_REPORT '+json.dumps(reports),flush=True)
