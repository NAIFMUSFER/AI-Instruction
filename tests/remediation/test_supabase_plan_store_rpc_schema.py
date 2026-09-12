#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SQL = (ROOT / "supabase/migrations/20260913_acs_plan_store_rpc_v2.sql").read_text(encoding="utf-8").lower()

# Durable project pointers are relational receipts, not client-controlled fields.
for column in ["head_revision_id text", "baseline_revision_id text", "updated_at timestamptz"]:
    assert column in SQL, column
assert "created_by uuid references auth.users(id)" in SQL
assert "acs_projects_head_revision_fk" in SQL
assert "acs_projects_baseline_revision_fk" in SQL
assert "revoke update (head_revision_id, baseline_revision_id, updated_at)" in SQL

# No identity invention/backfill is permitted if unexpected production rows exist.
assert "acs_created_by_backfill_required" in SQL
assert "alter column created_by set not null" in SQL

# Once the atomic RPC write boundary exists, authenticated clients must not be
# able to bypass it with legacy direct INSERT privileges from the base schema.
# Otherwise an editor could create orphan/malformed revision or approval rows
# that never passed the canonical receipt validators or project-head lock.
assert "revoke insert on table public.acs_plan_revisions from authenticated" in SQL
assert "revoke insert on table public.acs_plan_approvals from authenticated" in SQL

# Privileged mutation logic stays outside the exposed public schema; public RPCs
# are invoker wrappers only, callable with authenticated user JWTs.
private_functions = [
    "acs_plan_project_state", "acs_plan_workspace_snapshot",
    "acs_save_plan_revision", "acs_save_plan_approval",
]
for fn in private_functions:
    assert f"function acs_private.{fn}" in SQL, fn
    assert f"function public.{fn}" in SQL, fn
assert SQL.count("security definer") >= 4
assert SQL.count("security invoker") >= 4
assert "grant execute on function public.acs_save_plan_revision" in SQL
assert "grant execute on function public.acs_save_plan_approval" in SQL
assert "from public, anon" in SQL
assert "service_role" not in SQL

# Atomic write helpers lock the project head and enforce the same optimistic,
# monotonic revision / approval binding contract as the audited SQLite store.
assert SQL.count("for update") >= 2
for marker in [
    "acs_stale_revision", "acs_invalid_revision_chain", "acs_revision_exists",
    "acs_revision_not_found", "acs_approval_receipt_changed", "acs_approval_exists",
]:
    assert marker in SQL, marker
assert re.search(r"rev_number\s*<>\s*previous_number\s*\+\s*1", SQL)
assert "baseline_revision_id=rid" in SQL
assert "head_revision_id=rid" in SQL

print("ACS Supabase atomic plan-store RPC schema contract: PASS")
