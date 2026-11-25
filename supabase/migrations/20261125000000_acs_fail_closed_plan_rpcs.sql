-- ACS 2026-11-25: membership checks on the exposed plan RPCs fail closed.
--
-- The acs_private RPC bodies test `role_name not in (...)`. For a caller with
-- no membership row role_name is NULL, the test is NULL, and the IF does not
-- raise. Any authenticated account that knew a project UUID could therefore
-- read full revision documents, append revisions and set the approved baseline
-- of a project it does not belong to.
--
-- Historical migrations stay unchanged. The public (PostgREST-exposed) wrappers
-- now check membership through acs_private.acs_has_project_role, which returns
-- false (never NULL) for a non-member, before delegating. They stay SECURITY
-- INVOKER; CREATE OR REPLACE keeps their existing grants and revocations.
-- Missing and inaccessible projects get the same denial.

create or replace function public.acs_plan_project_state(p_project uuid)
returns jsonb language plpgsql stable security invoker
set search_path = pg_catalog, public, acs_private, pg_temp
as $$
begin
  if auth.uid() is null
     or not acs_private.acs_has_project_role(p_project, array['owner','editor','viewer']) then
    raise exception using errcode = 'P0001', message = 'ACS_PROJECT_ACCESS_DENIED';
  end if;
  return acs_private.acs_plan_project_state(p_project);
end $$;

create or replace function public.acs_plan_workspace_snapshot(p_project uuid)
returns jsonb language plpgsql stable security invoker
set search_path = pg_catalog, public, acs_private, pg_temp
as $$
begin
  if auth.uid() is null
     or not acs_private.acs_has_project_role(p_project, array['owner','editor']) then
    raise exception using errcode = 'P0001', message = 'ACS_PROJECT_ACCESS_DENIED';
  end if;
  return acs_private.acs_plan_workspace_snapshot(p_project);
end $$;

create or replace function public.acs_save_plan_revision(p_project uuid, p_expected_head text, p_revision jsonb)
returns jsonb language plpgsql security invoker
set search_path = pg_catalog, public, acs_private, pg_temp
as $$
begin
  if auth.uid() is null
     or not acs_private.acs_has_project_role(p_project, array['owner','editor']) then
    raise exception using errcode = 'P0001', message = 'ACS_PROJECT_ACCESS_DENIED';
  end if;
  return acs_private.acs_save_plan_revision(p_project, p_expected_head, p_revision);
end $$;

create or replace function public.acs_save_plan_approval(p_project uuid, p_expected_head text, p_approval jsonb)
returns jsonb language plpgsql security invoker
set search_path = pg_catalog, public, acs_private, pg_temp
as $$
begin
  if auth.uid() is null
     or not acs_private.acs_has_project_role(p_project, array['owner','editor']) then
    raise exception using errcode = 'P0001', message = 'ACS_PROJECT_ACCESS_DENIED';
  end if;
  return acs_private.acs_save_plan_approval(p_project, p_expected_head, p_approval);
end $$;
