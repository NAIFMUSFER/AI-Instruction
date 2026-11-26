-- ACS 2026-11-25 (2): the private plan RPC bodies fail closed on a NULL role.
--
-- 20261125000000 closed the four PostgREST-exposed public wrappers. The
-- SECURITY DEFINER bodies behind them, acs_private.acs_plan_project_state,
-- acs_plan_workspace_snapshot, acs_save_plan_revision and acs_save_plan_approval,
-- still test `if role_name not in (...)`: with no membership row the test is
-- NULL, the IF does not raise, and a direct call by `authenticated` (which has
-- USAGE on acs_private and EXECUTE on these functions) is admitted. Default
-- PostgREST does not expose acs_private, but the bodies must not rely on that.
--
-- Composition with PR #197 (2026111001 rewrites these four bodies fail closed):
-- this migration does not carry copies of the bodies. It rewrites only the
-- fail-open test, `if role_name not in (` -> `if role_name is null or role_name
-- not in (`, inside whatever definition is installed, re-creating it with
-- CREATE OR REPLACE, which keeps owner, ACL, SECURITY DEFINER and search_path.
--   * #197 applied first (fresh database, filename order): its bodies already
--     use `role_name is null or ...`; nothing matches and nothing is
--     re-created, so #197's revocations and checks stay exactly as installed.
--   * This migration first, #197 later (a live database): the original bodies
--     are patched now; #197's CREATE OR REPLACE later installs its own
--     fail-closed bodies over them.
-- Either way the postcondition below must hold, or the migration aborts.

do $$
declare
  f record;
  definition text;
  patched text;
  changed integer := 0;
begin
  for f in
    select p.oid
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'acs_private'
      and p.proname in ('acs_plan_project_state', 'acs_plan_workspace_snapshot',
                        'acs_save_plan_revision', 'acs_save_plan_approval')
  loop
    definition := pg_get_functiondef(f.oid);
    patched := regexp_replace(definition, '\mif\s+role_name\s+not\s+in\s*\(',
                              'if role_name is null or role_name not in (', 'gi');
    if patched <> definition then
      execute patched;
      changed := changed + 1;
    end if;
  end loop;
  if exists (
    select 1 from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'acs_private'
      and p.prosrc ~* '\mif\s+role_name\s+not\s+in\s*\('
  ) then
    raise exception 'ACS_FAIL_OPEN_ROLE_CHECK_REMAINS';
  end if;
  raise notice 'ACS private plan RPC role checks fail closed (% re-created)', changed;
end $$;
