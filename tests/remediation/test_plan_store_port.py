#!/usr/bin/env python3
"""Contract for a backend-neutral ACS Plan-first persistence port.

The initial red run proved persisted commands/reload were directly coupled to
SQLite.  This regression requires the generic boundaries to consume one narrow
port while preserving existing SQLite callers through an isolated compatibility
adapter.  A future Supabase adapter can implement the port directly.
"""
from pathlib import Path
import importlib
import inspect
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

port = importlib.import_module('acs_plan_store_port')
assert hasattr(port, 'PlanStorePort')
assert hasattr(port, 'SQLitePlanStoreAdapter')
assert hasattr(port, 'as_plan_store_port')

required = {'project_state', 'workspace_snapshot', 'save_revision', 'save_approval'}
for name in required:
    assert hasattr(port.PlanStorePort, name), name
    assert hasattr(port.SQLitePlanStoreAdapter, name), name

from acs_plan_store import SQLitePlanStore
with tempfile.TemporaryDirectory() as tmp:
    sqlite = SQLitePlanStore(Path(tmp) / 'acs.db')
    adapted = port.as_plan_store_port(sqlite)
    assert isinstance(adapted, port.PlanStorePort)
    assert isinstance(adapted, port.SQLitePlanStoreAdapter)

import acs_plan_persisted_commands as persisted
import acs_plan_store_reload as reload_mod

persisted_src = inspect.getsource(persisted)
reload_src = inspect.getsource(reload_mod)

# Concrete SQLite knowledge is isolated in acs_plan_store_port, not duplicated
# through command/reload business logic.
assert 'SQLitePlanStore' not in persisted_src
assert 'SQLitePlanStore' not in reload_src
assert '._connect()' not in reload_src
assert 'workspace_snapshot(' in reload_src
assert 'PlanStorePort' in persisted_src
assert 'PlanStorePort' in reload_src
assert 'as_plan_store_port' in persisted_src
assert 'as_plan_store_port' in reload_src

# Snapshot contracts remain fail-closed and explicitly identify their schema.
port_src = inspect.getsource(port)
assert 'SNAPSHOT_SCHEMA' in port_src
assert '_revision_from_row' in port_src
assert '_approval_from_row' in port_src
assert 'WRITABLE_ROLES' in port_src

print('ACS backend-neutral plan-store port contract: PASS')
