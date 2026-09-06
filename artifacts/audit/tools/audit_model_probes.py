"""Small counterexamples. These are NOT the missing original 22-issue fixture."""
import asyncio, copy, io, json, math, sys, tempfile, time
from contextlib import redirect_stdout
from pathlib import Path
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();sys.path.insert(0,str(root));out.mkdir(parents=True,exist_ok=True)
import acs_validate as V
import acs_understand as U
import acs_understand_api as API
import acs_compiler as C
import acs_arch as AR

def room(rid='room',rect=None):
    return {'id':rid,'rect':rect or [0,0,6,6],'walls':'full','doors':[{'edge':'N','offset':3,'width':1,'height':2.1}]}
base={'site':{'w':20,'d':25},'floor_height':3.2,'wall_h':3,'wall_t':.15,
 'levels':[{'index':0,'template':'g'}], 'floors':{'g':{'rooms':[room()]}},'meta':{'strict':True,'type':'residential'}}
cases={}
def add(name,mut,expected):
    b=copy.deepcopy(base);mut(b);cases[name]=(b,expected)
add('valid_control',lambda b:None,'No geometric issue on this simple valid control')
add('closed_room_without_access',lambda b:b['floors']['g']['rooms'][0].update(doors=[]),'Enclosed room has no door or explicit access; strict must not hide the missing connection')
add('furniture_outside_room',lambda b:b['floors']['g']['rooms'][0].update(furniture=[{'name':'desk','x':14,'z':14,'w':2,'d':1,'h':1}]),'Furniture footprint is outside its host room')
add('object_outside_room',lambda b:b['floors']['g']['rooms'][0].update(objects=[{'kind':'bed','x':14,'z':14,'w':2,'d':1}]),'Requested object is outside its host room')
add('negative_dimensions',lambda b:b['floors']['g']['rooms'][0].update(rect=[3,3,-2,-2],doors=[]),'Negative width and depth are invalid geometry even when area is positive')
add('nonfinite_position',lambda b:b['floors']['g']['rooms'][0].update(rect=[float('nan'),0,6,6]),'Nonfinite coordinates cannot be rendered')
add('invalid_opening_edge',lambda b:b['floors']['g']['rooms'][0]['doors'][0].update(edge='Q'),'Unknown wall edge must be rejected before compiler indexing')
add('door_above_wall',lambda b:b['floors']['g']['rooms'][0]['doors'][0].update(height=8),'Door head is above the represented wall')
add('window_above_wall',lambda b:b['floors']['g']['rooms'][0].update(windows=[{'edge':'S','offset':3,'width':1,'sill':2.5,'height':2}]),'Window head is above the represented wall')
add('duplicate_room_identity',lambda b:b['floors']['g']['rooms'].append(room('room',[7,0,6,6])),'Two rooms share one identity in the same template')
def core(b,kind):
    b['levels']=[{'index':i,'template':'f'+str(i)} for i in range(3)];b['floors']={}
    for i in range(3):
        r=room();r['objects']=[{'id':'core-A','kind':kind,'x':2+(1 if i==1 else 0),'z':3,'w':2,'d':2}]
        b['floors']['f'+str(i)]={'rooms':[r]}
add('stair_vertical_misalignment',lambda b:core(b,'stairs'),'Same declared core shifts by 1 metre on level 1')
add('elevator_vertical_misalignment',lambda b:core(b,'elevator'),'Same declared elevator shifts by 1 metre on level 1')
rows=[]
for name,(b,expected) in cases.items():
    t=time.perf_counter();trace=[]
    def tracer(frame,event,arg):
        if event=='line' and frame.f_code.co_filename.endswith('acs_validate.py'):trace.append(frame.f_lineno)
        return tracer
    err=None
    try:
        sys.settrace(tracer);issues,stats=V.validate_building(copy.deepcopy(b))
    except Exception as e:issues=None;stats=None;err=type(e).__name__+': '+str(e)
    finally:sys.settrace(None)
    rec={'case':name,'expected':expected,'legacy_issues':issues,'stats':stats,'exception':err,
         'executed_validator_lines':sorted(set(trace)),'seconds':time.perf_counter()-t}
    if name=='invalid_opening_edge':
        try:C.compile_building(copy.deepcopy(b),str(out/'invalid-edge.gltf'))
        except Exception as e:rec['compiler_exception']=type(e).__name__+': '+str(e)
    (out/(name+'.json')).write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n')
    rows.append(rec)

# Explicit elevation is honored by the architecture compiler and ignored by glTF.
b=copy.deepcopy(base);b['levels']=[{'index':1,'template':'g','elevation':7.5}]
ar=AR.compile_architecture(copy.deepcopy(b))
C.compile_building(copy.deepcopy(b),str(out/'explicit-elevation.gltf'))
gl=json.loads((out/'explicit-elevation.gltf').read_text())
rows.append({'case':'explicit_elevation_export_drift','declared_elevation':7.5,
 'architecture_levels':ar['levels'],'gltf_floor_nodes':[n for n in gl['nodes'] if str(n.get('name','')).startswith('FLOOR|')]})

# Exercise the real single generation route with a deterministic provider double.
# This tests control flow only; it is deliberately NOT reported as real AI output.
b=copy.deepcopy(base);b['meta']['strict']=False
fixed=copy.deepcopy(b);fixed['floors']['g']['rooms'][0]['rect']=[0,0,5,5]
fixed['floors']['g']['rooms'][0]['points']=[{'type':'light','x':2,'z':2},{'type':'smoke','x':2,'z':2}]
old_call,old_repair=U.call_llm,U.call_llm_repair
U.call_llm=lambda *a,**k:json.dumps(copy.deepcopy(b))
U.call_llm_repair=lambda *a,**k:json.dumps(copy.deepcopy(fixed))
buf=io.StringIO()
try:
    with redirect_stdout(buf):generated=U.understand('غرفة 6×6 م',deep=False,repair_rounds=1,strict=False)
finally:U.call_llm,U.call_llm_repair=old_call,old_repair
rows.append({'case':'silent_repair_replaces_requested_geometry','original_rect':[0,0,6,6],
 'returned_rect':generated['floors']['g']['rooms'][0]['rect'],'approval_required_in_path':False,
 'provider_kind':'deterministic double; control-flow test only','log':buf.getvalue()})

# Response diagnostics are copied from meta, never recomputed by the payload helper.
async def response_probe():
    bad=copy.deepcopy(base);bad['floors']['g']['rooms'][0]['rect']=[19,0,6,6];bad['meta']['acs_issues']=0
    old=API._engineering_authority
    async def passthrough(b):return {'proposals':[],'available':True},b
    API._engineering_authority=passthrough
    try:p=await API._understand_payload(bad)
    finally:API._engineering_authority=old
    return {'case':'stale_count_report','direct_validation':V.validate_building(bad)[0],
      'api_issues':p['issues'],'api_report':p['report'],'payload_keys':list(p),
      'double_scope':'proposal pool passthrough only; payload function is shipped code'}
rows.append(asyncio.run(response_probe()))
(out/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
for r in rows:print(r['case'],json.dumps({k:v for k,v in r.items() if k in ('legacy_issues','exception','compiler_exception','returned_rect','api_issues')},ensure_ascii=False))
