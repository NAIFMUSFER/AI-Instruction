"""Export recorded real models with the audited compiler; never simulates an LLM.
The DXF is an audit-only room-outline projection (the app has no DXF exporter).
"""
import copy, hashlib, json, sys, time
from pathlib import Path
root=Path(sys.argv[1]).resolve(); inputs=Path(sys.argv[2]).resolve(); out=Path(sys.argv[3]).resolve()
sys.path.insert(0,str(root))
import acs_compiler as C
import acs_authoring as A
import acs_docs as D
import acs_arch as AR
import acs_validate as V
out.mkdir(parents=True,exist_ok=True)
manifest=[]
for name in ('warehouse','chalet'):
    local='--local' in sys.argv
    p=inputs/((name if local else 'live-'+name)+'.json')
    if not p.exists(): continue
    response=json.loads(p.read_text())
    if not local and (response.get('status')!=200 or 'building' not in response.get('body',{})): continue
    case=out/name;case.mkdir(exist_ok=True)
    b=response if local else response['body']['building']
    if local:
        evidence=json.loads((inputs/'local-generation-evidence.json').read_text())
        generation_s=next(x['understanding_ms']/1000 for x in evidence if x['name']==name)
    else: generation_s=response['seconds']
    (case/'building.json').write_text(json.dumps(b,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    t=time.perf_counter(); issue,stats=V.validate_building(copy.deepcopy(b));vt=time.perf_counter()-t
    t=time.perf_counter(); ar=AR.compile_architecture(copy.deepcopy(b));at=time.perf_counter()-t
    t=time.perf_counter(); n,size=C.compile_building(copy.deepcopy(b),str(case/'building.gltf'));ct=time.perf_counter()-t
    t=time.perf_counter();project=A.create_project(copy.deepcopy(b),'bld_0','IMPORT',None)
    src=D.sources(project); svgrows=[]
    for level in src['arch']['levels']:
        r=D.build_view(project,{'view_type':'FLOOR_PLAN','level_id':level['id'],
          'discipline':'ARCHITECTURE','scale':'1:100','dimension_policy':'FULL_CHAIN','annotation_policy':'TAGS_ONLY'},src)
        if r['valid']:
            svg=D.view_svg(r['view'],r['geometry'],r['dimensions'],r['annotations'],{'paper_size':'A3','mode':'MONOCHROME'})
            fn='floor-'+str(level['index'])+'.svg';(case/fn).write_text(svg['svg']);svgrows.append(fn)
    st=time.perf_counter()-t
    dxf=['0','SECTION','2','HEADER','9','$INSUNITS','70','6','0','ENDSEC','0','SECTION','2','ENTITIES']
    for level in b['levels']:
        for room in b['floors'][level['template']].get('rooms',[]):
            x,z,w,d=room['rect']; dxf+=['0','LWPOLYLINE','8','F'+str(level['index']),'90','4','70','1']
            for a,c in ((x,z),(x+w,z),(x+w,z+d),(x,z+d)):dxf+=['10',str(a),'20',str(c)]
    dxf+=['0','ENDSEC','0','EOF'];(case/'audit-room-outlines.dxf').write_text('\n'.join(dxf)+'\n')
    (case/'validation.json').write_text(json.dumps({'legacy_issues':issue,'stats':stats,'architecture_issues':ar['issues']},ensure_ascii=False,indent=2)+'\n')
    manifest.append({'case':name,'source':('shipped local generator; DOM controls stubbed; no provider call, no pixel verification' if local else 'recorded actual production HTTP response; compiled using audited branch'),
      'generation_s':generation_s,'language_understanding_and_engineering_generation':('combined local parser/buildLocal execution' if local else 'combined single/staged provider pipeline; separate timing not exposed'),
      'validation_s':vt,'architecture_compilation_s':at,'gltf_export_s':ct,'svg_export_s':st,
      'measured_total_s':generation_s+vt+at+ct+st,'gltf_nodes':n,'gltf_buffer_bytes':size,
      'native_dxf_export':'NOT_IMPLEMENTED; audit-room-outlines.dxf is an audit-only room-outline projection',
      'files':[{'path':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(case.iterdir()) if p.is_file()]})
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps([{k:v for k,v in r.items() if k!='files'} for r in manifest],ensure_ascii=False,indent=2))
