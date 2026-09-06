"""Audit-only independent IFC tessellation, using IfcOpenShell 0.8.5."""
import json
from pathlib import Path
import sys
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.shape

root,out=map(lambda p:Path(p).resolve(),sys.argv[1:3])
sys.path[:0]=[str(root),str(root/'tests/remediation')]
import acs_bim as B
import acs_authoring as A
from test_polygon_gltf import model,L
from test_polygon_architecture import adjacent_triangles

core=model(objects=[{'kind':'stairs','core_id':'A','x':1,'z':3,'w':1,'d':1}])
core['levels'].append({'index':1,'template':'plan','elevation':10.2})
cases=[('polygon-l',model(),[60],[4]),('polygon-core',core,[60,60],[4,3.8]),
       ('polygon-triangles',adjacent_triangles(),[54,54],[7.2]),
       ('polygon-origin',model([[x-100,z+230] for x,z in L]),[60],[4])]
settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
out.mkdir(parents=True,exist_ok=True);rows=[]
for name,building,spaces,slabs in cases:
    (out/(name+'.json')).write_text(json.dumps(building,indent=2)+'\n')
    result=B.export_ifc(A.create_project(building),generated_at='2026-09-06T00:00:00Z')
    assert result['valid'],result['issues']
    (out/(name+'.ifc')).write_text(result['file'])
    doc=ifcopenshell.file.from_string(result['file'])
    row={'case':name,'checker':ifcopenshell.version,'geometry':{}}
    for kind,expected in [('IfcSpace',spaces),('IfcSlab',slabs)]:
        measured=[]
        for entity in doc.by_type(kind):
            shape=ifcopenshell.geom.create_shape(settings,entity)
            vertices=list(zip(*[iter(shape.geometry.verts)]*3))
            volume=ifcopenshell.util.shape.get_volume(shape.geometry)
            measured.append(volume)
            row['geometry'].setdefault(kind,[]).append({'global_id':entity.GlobalId,
                 'volume_m3':volume,'vertices':len(vertices),
                 'bounds':[[min(p[i] for p in vertices),max(p[i] for p in vertices)] for i in range(3)]})
        assert len(measured)==len(expected),(name,kind,len(measured),len(expected))
        assert all(abs(a-b)<1e-5 for a,b in zip(sorted(measured),sorted(expected))), (name,kind,measured,expected)
    if name=='polygon-origin':
        assert row['geometry']['IfcSpace'][0]['bounds']==[[-100.,-94.],[230.,236.],[7.,10.]]
    row['expected_volumes_m3']={'IfcSpace':spaces,'IfcSlab':slabs}
    row['passed']=True;rows.append(row)
    (out/'geometry-results.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
