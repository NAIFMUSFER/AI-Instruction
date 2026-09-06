"""Independent IFC4 schema and actual tessellation of the millimetre fixture."""
import json, sys
from pathlib import Path
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.shape, ifcopenshell.validate
root,out=map(lambda p:Path(p).resolve(),sys.argv[1:3])
sys.path[:0]=[str(root),str(root/'tests/remediation')]
from test_polygon_ifc_import import mm_rotated_space
import acs_bim as B
text=mm_rotated_space();(out/'millimetre-rotated.ifc').write_text(text)
doc=ifcopenshell.file.from_string(text);logger=ifcopenshell.validate.json_logger()
ifcopenshell.validate.validate(doc,logger,express_rules=True)
(out/'millimetre-schema.json').write_text(json.dumps(logger.statements,default=str,indent=2)+'\n')
staging=B.stage_import(text);(out/'millimetre-staging.json').write_text(json.dumps(staging,indent=2)+'\n')
settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
shape=ifcopenshell.geom.create_shape(settings,doc.by_type('IfcSpace')[0])
vertices=list(zip(*[iter(shape.geometry.verts)]*3))
row={'schema_errors':len(logger.statements),'checker_version':ifcopenshell.version,
     'volume_m3':ifcopenshell.util.shape.get_volume(shape.geometry),
     'bounds_m':[[min(p[i] for p in vertices),max(p[i] for p in vertices)] for i in range(3)],
     'expected_bounds_m':[[-108,-102],[231,237],[7,10]],'expected_volume_m3':60}
(out/'independent-import-check.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row))
assert row['schema_errors']==0
assert abs(row['volume_m3']-row['expected_volume_m3'])<1e-7
assert row['bounds_m']==row['expected_bounds_m']
