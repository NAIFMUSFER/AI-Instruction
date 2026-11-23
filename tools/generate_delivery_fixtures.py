"""Synthetic reproducible bounded corpus; never evidence of live provider quality.

Uses the production geometry verifier and conceptual approval, then actual export
adapters. Revision IDs are runtime receipts; canonical hashes are deterministic.
"""
from pathlib import Path
import sys,json,hashlib,struct,base64
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_bridge import existing_geometry_verifier
from acs_plan_review import digest
from tools.acs_plan_handoff import compile_approved_baseline
from tools.acs_plan_ifc_export import export_approved_ifc
from tools.acs_plan_cad_export import export_approved_cad
from acs_plan_projection import project

def fixtures():
    door=lambda id,edge,offset:{'id':id,'edge':edge,'offset':offset,'width':1.2,'height':2.2,'material':'wood'}
    # Explicit canonical wall top meets the next0.15m slab underside at4.05m.
    # The old3m-wall/4.2m-level model stays an unchanged adversarial fixture.
    villa={'meta':{'type':'residential','name':'Synthetic two-level villa'},'site':{'w':20,'d':20},'wall_h':4.05,'wall_t':.2,'floor_height':3.2,'levels':[{'index':0,'template':'home','elevation':0},{'index':1,'template':'home','elevation':4.2}], 'floors':{'home':{'rooms':[
       {'id':'living','name':'مجلس العائلة','role':'living','rect':[0,0,8,8],'walls':['N','S','W','E'],'doors':[door('entry','N',4),door('core_access','E',4)],'windows':[{'id':'west_window','edge':'W','offset':4,'width':2,'height':1.5,'sill':.9}],'objects':[{'id':'dining_table','kind':'table','x':4,'z':4,'y':0,'w':2,'d':1,'h':.8,'rot':45,'count':1,'pitch':1,'dir':'x'}]},
       {'id':'stairs','name':'نواة درج — المسار الرأسي غير متحقق','role':'stairs','core_id':'stair_core','rect':[8,0,4,8],'walls':['N','S','W','E'],'doors':[door('living_access','W',4)],'windows':[]} ]}}}
    warehouse={'meta':{'type':'warehouse','name':'Synthetic warehouse with open shared zone'},'site':{'w':30,'d':25},'wall_h':7.5,'wall_t':.2,'floor_height':8,'levels':[{'index':0,'template':'ground','elevation':0}],'floors':{'ground':{'rooms':[
       {'id':'storage','name':'التخزين','role':'storage','rect':[0,0,14,16],'walls':['N','S','W'],'doors':[],'windows':[],'racks':[{'id':'rack_a','kind':'pallet','x':1,'z':2,'w':10,'d':12,'dir':'z','rows':2,'depth':1.1,'bay':2.7,'aisle':3.4,'levels':3,'h':6}],'lanes':[{'id':'main_lane','kind':'forklift','x':10.5,'z':0,'w':3,'d':16,'dir':'z'}],'docks':[],'stations':[]},
       {'id':'dispatch','name':'الشحن','role':'outbound','rect':[14,0,6,16],'walls':['N','S','E'],'doors':[],'windows':[],'racks':[],'lanes':[],'docks':[{'id':'dock_e','edge':'E','offset':4,'width':3.6,'height':4.2,'count':2,'pitch':6}],'stations':[]} ]}}}
    for building in (villa,warehouse):
        for floor in building['floors'].values():
            for room in floor['rooms']:
                room['points']=[{'id':'ceiling_light','type':'light','x':room['rect'][2]/2,'z':room['rect'][3]/2}]
    return {'villa':villa,'warehouse':warehouse}

def main(out, models=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);report=[]
    for name,model in (fixtures() if models is None else models).items():
        (out/(name+'.json')).write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n')
        area=sum(r['rect'][2]*r['rect'][3] for l in model['levels'] for r in model['floors'][l['template']]['rooms'])
        brief=f'Synthetic total canonical room area {area} square metres.'
        requirements=[{'id':'area','metric':'building_target_area_m2','expected':area,'source':'requested','evidence':str(area)}]
        ws=PlanLockWorkspace(existing_geometry_verifier);rev=ws.propose(model,brief=brief,requirements=requirements,expected_head=None,note='Deterministic synthetic acceptance fixture')
        review=ws.review(rev.id)
        if not review['can_approve']:raise RuntimeError(json.dumps(review,ensure_ascii=False))
        ws.approve(rev.id,expected_head=rev.id,confirmed=True,acknowledge_concept_only=True,actor_label='synthetic-fixture-review')
        gltf=compile_approved_baseline(ws,rev.id,out/(name+'.gltf'),overwrite=True)
        ifc=export_approved_ifc(ws,rev.id,out/(name+'.ifc'),overwrite=True)
        for l in model['levels']:
            for ext in ('svg','dxf'):export_approved_cad(ws,rev.id,l['index'],out/(name+f"-F{l['index']}."+ext),overwrite=True)
        g=json.loads((out/(name+'.gltf')).read_text());triangles=sum(g['accessors'][p['indices']]['count']//3 for m in g['meshes'] for p in m['primitives'])
        row={'fixture':name,'synthetic':True,'provider_calls':0,'revision_id':rev.id,'model_hash':digest(model),'area_m2':area,'spaces':sum(len(model['floors'][l['template']]['rooms']) for l in model['levels']),'nodes':len(g['nodes']),'triangles':triangles,'gltf_bytes':(out/(name+'.gltf')).stat().st_size,'review':review,'gltf':gltf,'ifc':ifc}
        row['files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob(name+'*')) if p.is_file()}
        report.append(row)
    (out/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ['fixture','revision_id','model_hash','area_m2','spaces','nodes','triangles','gltf_bytes']} for r in report],indent=2))
if __name__=='__main__':main(sys.argv[1])
