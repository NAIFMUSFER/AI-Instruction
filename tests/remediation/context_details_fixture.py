"""Explicit synthetic context fixture, no provider output or structural claim."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from acs_context_details import with_context_details

def context_fixture():
    model={'site':{'w':26,'d':6},'wall_t':.2,'wall_h':3,'floor_height':3.2,
           'levels':[{'index':0,'template':'g','elevation':0}],
           'floors':{'g':{'rooms':[
               {'id':'porch','name':'رواق تجريبي','role':'porch','covered':True,'rect':[0,0,6,5],'walls':['S']},
               {'id':'balcony','name':'شرفة تجريبية','role':'balcony','rect':[10,0,5,4],'walls':['S','E','W']},
               {'id':'court','name':'فناء تجريبي','role':'courtyard','outdoor':True,'rect':[20,0,6,6],'walls':'none'}]}}}
    for room in model['floors']['g']['rooms']:
        room['doors']=[{'id':'entry_'+room['id'],'edge':'S','offset':room['rect'][2]/2,'width':1,'height':2.1,'material':'wood'}]
        room['points']=[{'id':'light_'+room['id'],'type':'light','x':room['rect'][2]/2,'z':room['rect'][3]/2}]
        room['windows']=[]
    out,report,reason=with_context_details(model)
    assert reason is None and len(report['added'])==5,(report,reason)
    return out

def approved_context_fixture(output):
    from acs_plan_lock_binding import PlanLockWorkspace
    from acs_plan_bridge import existing_geometry_verifier
    from tools.acs_plan_handoff import compile_approved_baseline,verify_compiled_artifact
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    model=context_fixture();workspace=PlanLockWorkspace(existing_geometry_verifier)
    revision=workspace.propose(model,brief='Synthetic context fixture total room area 86 m2.',requirements=[{'id':'area','metric':'building_target_area_m2','expected':86,'source':'requested','evidence':'86'}],expected_head=None,note='Synthetic context QA; no provider call')
    review=workspace.review(revision.id);assert review['can_approve'],review
    workspace.approve(revision.id,expected_head=revision.id,actor_label='synthetic-context-test',confirmed=True,acknowledge_concept_only=True)
    path=output/'context.gltf';receipt=compile_approved_baseline(workspace,revision.id,path)
    assert verify_compiled_artifact(path)['ok']
    (output/'context.canonical.json').write_text(json.dumps(model,ensure_ascii=False,indent=2))
    record={'kind':'context','revision':revision.id,'model_hash':revision.model_hash,'gltf':path.name,'receipt':receipt,'scope':'Synthetic conceptual porch columns, open-edge balcony railing and potted courtyard plants; no structural, safety or regulatory claim'}
    (output/'context-fixture.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
    return record

if __name__=='__main__':print(json.dumps(approved_context_fixture(sys.argv[1]),ensure_ascii=False))
