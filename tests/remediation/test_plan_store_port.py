#!/usr/bin/env python3
"""Contract for a backend-neutral ACS Plan-first persistence port.

Red-first: persisted commands and workspace reload must not depend on SQLite
internals. The SQLite implementation remains supported, but cloud persistence can
only be added safely when both boundaries consume the same narrow store port.
"""
from pathlib import Path
import importlib
import inspect

ROOT = Path(__file__).resolve().parents[2]

port = importlib.import_module('acs_plan_store_port')
assert hasattr(port, 'PlanStorePort')
required = {'project_state', 'workspace_snapshot', 'save_revision', 'save_approval'}
annotations = getattr(port.PlanStorePort, '__annotations__', {})
for name in required:
    assert hasattr(port.PlanStorePort, name), name

from acs_plan_store import SQLitePlanStore
assert hasattr(SQLitePlanStore, 'workspace_snapshot')

import acs_plan_persisted_commands as persisted
import acs_plan_store_reload as reload_mod

persisted_src = inspect.getsource(persisted)
reload_src = inspect.getsource(reload_mod)

assert 'isinstance(store, SQLitePlanStore)' not in persisted_src
assert 'isinstance(store, SQLitePlanStore)' not in reload_src
assert 'store._connect()' not in reload_src
assert 'workspace_snapshot(' in reload_src
assert 'PlanStorePort' in persisted_src
assert 'PlanStorePort' in reload_src

print('ACS backend-neutral plan-store port contract: PASS')
