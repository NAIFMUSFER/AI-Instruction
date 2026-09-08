"""Run with Blender on its own GENERATED file, never untrusted customer .blend."""
import bpy,json,sys
from pathlib import Path
root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
spec=json.loads((root/'scene.json').read_text());found={o.get('objectId'):o for o in bpy.context.scene.objects if o.type=='MESH'}
assert len(found)==len(spec['objects'])
errors=[]
for expected in spec['objects']:
    obj=found[expected['id']];verts=[obj.matrix_world@v.co for v in obj.data.vertices]
    actual=[min(v[k] for v in verts) for k in range(3)]+[max(v[k] for v in verts) for k in range(3)]
    target=expected['min']+[v+expected['size'][k] for k,v in enumerate(expected['min'])]
    error=max(abs(a-b) for a,b in zip(actual,target));assert error<.00005;errors.append(error)
    assert obj['elementId']==expected['elementId']
report={'status':'PASS','blendReopened':True,'objectsVerified':len(found),'maxErrorM':max(errors),'blenderVersion':bpy.app.version_string}
(root/'blend-reopen-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
