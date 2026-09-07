"""Independent IFC4 EXPRESS, geometry and hosted void verification.
Requires ifcopenshell==0.8.5 and pytest==8.4.2. Not a code-compliance certificate.
"""
import json, math, sys, traceback
from pathlib import Path
import ifcopenshell, ifcopenshell.validate, ifcopenshell.geom, ifcopenshell.util.shape
root=Path(sys.argv[1] if len(sys.argv)>1 else 'test-output/ifc')
results=[]
def union_area(rects):
    xs=sorted({v for x1,y1,x2,y2 in rects for v in (x1,x2)})
    area=0.
    for left,right in zip(xs,xs[1:]):
        mid=(left+right)/2
        spans=sorted((r[1],r[3]) for r in rects if r[0]<mid<r[2])
        total=0.;end=-math.inf
        for low,high in spans:
            total+=max(0.,high-max(low,end));end=max(end,high)
        area+=(right-left)*total
    return area
for name in json.loads((root/'fixtures.json').read_text()):
    result={'fixture':name,'status':'PASS','errors':[],'representedProducts':0,'checkedWallVolumes':0,'checkedSpaceVolumes':0}
    try:
        expected=json.loads((root/(name+'.json')).read_text());model=ifcopenshell.open(str(root/(name+'.ifc')))
        logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(model,logger,express_rules=True)
        if logger.statements:raise AssertionError(json.dumps(logger.statements,default=str,ensure_ascii=False))
        assert model.schema=='IFC4';assert model.by_type('IfcProject')[0].Name==expected['title']
        roots=model.by_type('IfcRoot');assert len({r.GlobalId for r in roots})==len(roots)
        counts=expected['counts'];assert len(model.by_type('IfcSpace'))==counts['spaces'];assert len(model.by_type('IfcWall'))==counts['walls'];assert len(model.by_type('IfcDoor'))==counts['doors'];assert len(model.by_type('IfcWindow'))==counts['windows']
        assert len(model.by_type('IfcRelVoidsElement'))==counts['openings'];assert len(model.by_type('IfcRelFillsElement'))==counts['openings']
        settings=ifcopenshell.geom.settings();settings.set('use-world-coords',True)
        geometries={}
        for obj in model.by_type('IfcProduct'):
            if not obj.Representation:continue
            shape=ifcopenshell.geom.create_shape(settings,obj)
            assert len(shape.geometry.verts)>0 and all(math.isfinite(v) for v in shape.geometry.verts)
            geometries[obj.GlobalId]=shape;result['representedProducts']+=1
        for space in expected['spaces']:
            obj=model.by_guid(space['guid']);assert obj.Name==space['name']
            geometry=geometries[space['guid']].geometry;volume=ifcopenshell.util.shape.get_volume(geometry)
            assert math.isclose(volume,space['volume'],rel_tol=.0002,abs_tol=.005),(name,obj.Name,volume,space['volume'])
            zs=geometry.verts[2::3];assert abs(min(zs)-space['z'])<.002;assert abs(max(zs)-(space['z']+space['height']))<.002
            assert len(obj.Decomposes)==1 and obj.Decomposes[0].RelatingObject.is_a('IfcBuildingStorey')
            result['checkedSpaceVolumes']+=1
        for wall in expected['walls']:
            cuts=[]
            for op in wall['openings']:
                x=op['y'] if wall['axis']=='v' else op['x'];z=op.get('sill',0) if op['type']=='window' else 0
                cuts.append((x-op['width']/2,z,x+op['width']/2,z+op['height']))
            wanted=(wall['length']*wall['height']-union_area(cuts))*wall['thickness']
            actual=ifcopenshell.util.shape.get_volume(geometries[wall['guid']].geometry)
            assert math.isclose(actual,wanted,rel_tol=.002,abs_tol=.008),(name,wall['id'],actual,wanted)
            result['checkedWallVolumes']+=1
    except Exception as exc:
        result['status']='FAIL';result['errors'].append(traceback.format_exc())
    results.append(result)
    print(json.dumps(result,ensure_ascii=False),flush=True)
report={'validator':'IfcOpenShell '+ifcopenshell.version,'scope':'IFC4 EXPRESS + tessellation + world-space volumes + hosted void subtraction. Not regulatory/engineering approval or Revit certification.','fixtures':results,'passed':sum(x['status']=='PASS' for x in results),'failed':sum(x['status']!='PASS' for x in results)}
(root/'independent-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(1 if report['failed'] else 0)
