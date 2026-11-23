"""Actual checked-out main: admitted unknown type must not disable room locking."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(sys.argv[1]).resolve()
sys.path[:0]=[str(ROOT),str(ROOT/'tests/remediation')]
import acs_workspace_service as S
import acs_plan_commands as C
from acs_plan_review import PlanError
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from acs_plan_persisted_commands import execute_persisted_plan_command
from test_connected_workspace import model,command,PROJECT,ACTOR

assert Path(S.__file__).resolve().is_relative_to(ROOT)
assert Path(C.__file__).resolve().is_relative_to(ROOT)
sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert sha=='c37b5250dc4ff18ba0606add993b5afe52beebaa'
print(json.dumps({'sha':sha,'service':S.__file__,'commands':C.__file__,'scope':'Full isolated main checkout; SQLite; synthetic identity; zero provider'}))
for typed in (True,False):
 with tempfile.TemporaryDirectory() as folder,patch('acs_understand.call_llm',side_effect=AssertionError('provider forbidden')) as provider:
  db=SQLitePlanStore(Path(folder)/'plans.sqlite3');db.create_project(PROJECT,owner_id=ACTOR)
  store=SQLitePlanStoreAdapter(db);ws=S.workspace(store,PROJECT,ACTOR);building=model()
  if not typed:building['meta'].pop('type')
  first=ws.propose(building,brief=command()['brief'],requirements=command()['requirements'],expected_head=None,note='Synthetic main regression')
  store.save_revision(PROJECT,actor_id=ACTOR,revision=first,expected_head=None)
  def execute(body):return execute_persisted_plan_command(store,PROJECT,body,actor_id=ACTOR,verifier=S.existing_geometry_verifier)
  review=S.workspace(store,PROJECT,ACTOR).review(first.id);assert review['can_approve'] is True
  execute({'action':'approve','expected_head':first.id,'confirmed':True,'acknowledge_concept_only':True})
  before=S.workspace(store,PROJECT,ACTOR);before_history=before.history()
  body={'action':'set_room_lock','expected_head':first.id,'room_ref':['ground','a'],'locked':True}
  try:
   out=execute(body);after=S.workspace(store,PROJECT,ACTOR)
   result={'typed':typed,'review_can_approve':True,'lock_result':'success','revision_persisted':out['persistence']['revision_persisted'],'locked_rooms':after.get(after.head).locked_rooms}
   assert typed is True and after.get(after.head).locked_rooms==(('ground','a'),)
  except PlanError as error:
   after=S.workspace(store,PROJECT,ACTOR)
   result={'typed':typed,'review_can_approve':True,'lock_result':'rejected','code':error.code,'history_unchanged':after.history()==before_history,'head_unchanged':after.head==first.id}
   assert typed is False and error.code=='OPTION_TYPOLOGY_UNKNOWN'
   assert after.history()==before_history and after.head==first.id
  provider.assert_not_called();result['provider_calls']=0
  print(json.dumps(result))
print('BASELINE DEFECT REPRODUCED: unknown typology blocks room-lock response despite canonical admission and conceptual approval; typed control succeeds.')
