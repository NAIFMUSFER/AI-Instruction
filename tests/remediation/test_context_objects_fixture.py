"""Preflight the exact browser fixture through real persisted command boundaries."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from context_objects_browser_server import seeded_application, PROJECT, ACTOR
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from acs_plan_persisted_commands import execute_persisted_plan_command
from acs_plan_review import PlanError
import acs_workspace_service as S


class ContextBrowserFixture(unittest.TestCase):
    def test_actual_seed_remove_reopen_approve_and_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'plans.sqlite3';seeded_application(path)
            def store():return SQLitePlanStoreAdapter(SQLitePlanStore(path))
            def view():return S.view(store(),PROJECT,ACTOR)
            def command(body):return execute_persisted_plan_command(store(),PROJECT,body,actor_id=ACTOR,verifier=S.existing_geometry_verifier)
            first=view();r1=first['head']
            column=next(row for row in first['object_actions']['items'] if row['kind']=='column' and row['supported'])
            remove=lambda row,head:{'action':'remove_object','expected_head':head,'room_ref':[row['template'],row['room_id']], 'object_id':row['object_id'],'confirm_new_draft':True}
            removed=command(remove(column,r1));r2=removed['head'];self.assertNotEqual(r1,r2)
            self.assertNotIn('revision_comparison',removed);self.assertIn('semantic_diff',removed)
            self.assertEqual(removed['revision_comparison_unavailable']['reason'],'OPTION_TYPOLOGY_UNKNOWN')
            self.assertNotIn('type',S.workspace(store(),PROJECT,ACTOR).get(r2).model['meta'],'unknown typology must not be invented to make comparison work')
            self.assertEqual(next(row['state'] for row in removed['history'] if row['revision_id']==r1),'APPROVED')
            self.assertEqual(next(row['state'] for row in removed['history'] if row['revision_id']==r2),'DRAFT')
            self.assertEqual(view()['object_actions'],removed['object_actions'])
            self.assertFalse(any(row['object_id']==column['object_id'] for row in view()['object_actions']['items']))
            approve=lambda head:{'action':'approve','expected_head':head,'confirmed':True,'acknowledge_concept_only':True}
            command(approve(r2))
            remaining=next(row for row in view()['object_actions']['items'] if row['kind']=='column' and row['supported'])
            locked=command({'action':'set_room_lock','expected_head':r2,'room_ref':[remaining['template'],remaining['room_id']],'locked':True})
            command(approve(locked['head']));before=view()
            with self.assertRaises(PlanError) as error:command(remove(remaining,locked['head']))
            self.assertEqual(error.exception.code,'LOCK_VIOLATION');self.assertEqual(view(),before)


if __name__=='__main__':unittest.main()
