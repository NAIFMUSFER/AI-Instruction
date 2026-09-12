#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SQL = (ROOT / 'supabase/migrations/20260912_acs_plan_store_v2.sql').read_text(encoding='utf-8').lower()

required_tables = [
    'acs_projects','acs_project_members','acs_plan_revisions',
    'acs_plan_approvals','acs_plan_handoffs'
]
for table in required_tables:
    assert f'create table if not exists public.{table}' in SQL, table
    assert f'alter table public.{table} enable row level security' in SQL, f'RLS:{table}'

# Canonical revision receipts and frozen downstream provenance must be persisted.
for field in ['revision_json jsonb','model_hash text','content_hash text','bound_content_hash text',
              'semantic_lock_manifest_hash text','approval_json jsonb','handoff_json jsonb',
              'provenance_hash text']:
    assert field in SQL, field

# No mutation policy may make immutable canonical receipts editable/deletable.
for table in ['acs_plan_revisions','acs_plan_approvals','acs_plan_handoffs']:
    assert not re.search(r'create policy\s+\S+\s+on public\.' + table + r'\s+for (update|delete)', SQL), table

# Authenticated-user RLS only; never embed a privileged server key in migrations.
assert 'service_role' not in SQL
assert 'auth.uid()' in SQL
assert 'security definer' in SQL
assert 'set search_path = public, pg_temp' in SQL
assert "revoke all on function public.acs_has_project_role(uuid,text[]) from public" in SQL

# Derived artifact authority stays bounded to known publication types.
for kind in ["'bim'","'3d'","'dxf'","'ifc'","'svg'","'pdf'"]:
    assert kind in SQL, kind

print('ACS Supabase durable plan-store schema contract: PASS')
