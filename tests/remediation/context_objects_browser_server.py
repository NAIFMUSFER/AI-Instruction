"""Loopback-only object editing fixture; real approval/store/commands, no provider."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from connected_workspace_browser_server import application, PROJECT, ACTOR
from context_details_fixture import context_fixture
from acs_context_details import list_context_details
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_bridge import existing_geometry_verifier
from acs_plan_persisted_commands import execute_persisted_plan_command
import uvicorn


def seeded_application(database):
    app = application(database)
    store = SQLitePlanStoreAdapter(SQLitePlanStore(database))
    building = context_fixture()
    assert any(row['kind'] == 'column' for row in list_context_details(building))
    ws = PlanLockWorkspace(existing_geometry_verifier)
    revision = ws.propose(building, brief='Synthetic object removal fixture, site width 26 metres; zero provider calls.',
        requirements=[{'id': 'width', 'metric': 'site_width_m', 'expected': 26,
                       'source': 'requested', 'evidence': '26'}],
        expected_head=None, note='Synthetic canonical context objects')
    assert ws.review(revision.id)['can_approve'], ws.review(revision.id)
    store.save_revision(PROJECT, actor_id=ACTOR, revision=revision, expected_head=None)
    execute_persisted_plan_command(store, PROJECT,
        {'action': 'approve', 'expected_head': revision.id, 'confirmed': True,
         'acknowledge_concept_only': True}, actor_id=ACTOR, verifier=existing_geometry_verifier)
    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--database', required=True)
    args = parser.parse_args()
    uvicorn.run(seeded_application(args.database), host='127.0.0.1', port=args.port, log_level='warning')
