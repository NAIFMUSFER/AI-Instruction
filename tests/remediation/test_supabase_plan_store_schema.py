#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SQL = (ROOT / 'supabase/migrations/20260912_acs_plan_store_v2.sql').read_text(encoding='utf-8').lower()
HARDEN = (ROOT / 'supabase/migrations/20260912_acs_plan_store_v2_harden_functions.sql').read_text(encoding='utf-8').lower()

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

# Revision lineage must point to a real revision in the same project and cannot self-parent.
assert re.search(
    r'foreign key\s*\(project_id,\s*parent_revision_id\)\s*'
    r'references public\.acs_plan_revisions\(project_id,\s*revision_id\)', SQL
)
assert 'check (parent_revision_id is null or parent_revision_id <> revision_id)' in SQL

# Downstream BIM/3D/CAD/export receipts are durable only for an approved Frozen Baseline.
assert re.search(
    r'foreign key\s*\(project_id,\s*revision_id\)\s*'
    r'references public\.acs_plan_approvals\(project_id,\s*revision_id\)', SQL
)

# No mutation policy may make immutable canonical receipts editable/deletable.
for table in ['acs_plan_revisions','acs_plan_approvals','acs_plan_handoffs']:
    assert not re.search(r'create policy\s+\S+\s+on public\.' + table + r'\s+for (update|delete)', SQL), table
    assert f'revoke all on table public.{table} from anon, authenticated' in SQL
    assert f'grant select, insert on table public.{table} to authenticated' in SQL
    assert not re.search(r'grant\s+[^;]*(update|delete)[^;]*public\.' + table, SQL), table

# Authenticated-user RLS only; never embed a privileged server key in migrations.
assert 'service_role' not in SQL
assert 'auth.uid()' in SQL
assert 'security definer' in SQL
assert 'set search_path = public, pg_temp' in SQL
assert 'revoke all on function public.acs_has_project_role(uuid,text[]) from public' in SQL
assert 'revoke all on function public.acs_is_project_owner(uuid,uuid) from public' in SQL

# SECURITY DEFINER helpers are moved out of the exposed public API schema.
assert 'create schema if not exists acs_private' in HARDEN
for sig in [
    'acs_has_project_role(uuid,text[])',
    'acs_is_project_owner(uuid,uuid)',
    'acs_seed_owner_membership()',
    'acs_guard_membership_mutation()'
]:
    assert f'alter function public.{sig} set schema acs_private' in HARDEN, sig
assert 'revoke all on schema acs_private from public, anon' in HARDEN
assert 'grant usage on schema acs_private to authenticated' in HARDEN
assert 'revoke all on function acs_private.acs_seed_owner_membership() from public, anon, authenticated' in HARDEN
assert 'revoke all on function acs_private.acs_guard_membership_mutation() from public, anon, authenticated' in HARDEN
assert 'grant execute on function acs_private.acs_has_project_role(uuid,text[]) to authenticated' in HARDEN
assert 'grant execute on function acs_private.acs_is_project_owner(uuid,uuid) to authenticated' in HARDEN
assert 'service_role' not in HARDEN

# Project creation must atomically seed the owner membership, otherwise the owner
# would be unable to satisfy the membership-based SELECT policy for a new project.
assert 'create or replace function public.acs_seed_owner_membership()' in SQL
assert re.search(
    r'create trigger\s+acs_projects_seed_owner_membership\s*'
    r'after insert on public\.acs_projects\s*'
    r'for each row execute function public\.acs_seed_owner_membership\(\)', SQL
)
assert "values (new.id, new.owner_id, 'owner')" in SQL

# The owner role and membership identity are invariant even if a privileged path
# bypasses RLS. Manual membership management may add only editor/viewer members.
assert 'create or replace function public.acs_guard_membership_mutation()' in SQL
assert re.search(
    r'create trigger\s+acs_members_guard_mutation\s*'
    r'before update or delete on public\.acs_project_members', SQL
)
assert "new.user_id = project_owner and new.role <> 'owner'" in SQL
assert "new.user_id <> project_owner and new.role = 'owner'" in SQL
assert "role in ('editor','viewer')" in SQL
assert 'public.acs_is_project_owner(project_id, auth.uid())' in SQL

# Narrow table privileges: no anonymous access, immutable receipts have no
# UPDATE/DELETE grants, and project/member identity columns are not writable.
for table in required_tables:
    assert f'revoke all on table public.{table} from anon, authenticated' in SQL
assert 'grant update (name) on table public.acs_projects to authenticated' in SQL
assert 'grant update (role) on table public.acs_project_members to authenticated' in SQL
assert 'grant update on table public.acs_projects' not in SQL
assert 'grant update on table public.acs_project_members' not in SQL

# Derived artifact authority stays bounded to known publication types.
for kind in ["'bim'","'3d'","'dxf'","'ifc'","'svg'","'pdf'"]:
    assert kind in SQL, kind

print('ACS Supabase durable plan-store schema contract: PASS')
