-- ACS 2026-11-28 (audit P0-3): one running job per project, for every server.
--
-- The application reserved a project for one paid job in process memory
-- (acs_workspace_http.ACTIVE_PROJECTS). Two server instances each had their
-- own map, so the same project could start two paid generations or designs at
-- once. The database now holds the reservation: at most one RUNNING row per
-- project, whichever instance writes it. A second insert fails with a unique
-- violation, which the server reports as GENERATION_IN_PROGRESS before any
-- provider request.
--
-- A RUNNING row whose worker died (deploy, crash, out of memory) would hold
-- the project forever. acs_release_stale_job marks such a row FAILED with
-- PROVIDER_OUTCOME_UNKNOWN once no worker can still finish it: 35 minutes for
-- a workspace job (the 1800 s worker deadline plus 300 s grace, as
-- acs_workspace_http._orphaned reads it) and 3 hours for an ACS Designer job,
-- whose run lives in its Managed Agents session and is capped by its budget.
-- Any owner or editor of the project may release it, also when another member
-- started the job, so it is SECURITY DEFINER and checks the role itself.

create unique index if not exists acs_workspace_jobs_one_running
  on public.acs_workspace_jobs (project_id) where state = 'RUNNING';

create or replace function public.acs_release_stale_job(p_project uuid)
returns integer language plpgsql security definer
set search_path = pg_catalog, public, acs_private, pg_temp
as $$
declare
  released integer;
begin
  if auth.uid() is null
     or not acs_private.acs_has_project_role(p_project, array['owner','editor']) then
    raise exception using errcode = 'P0001', message = 'ACS_PROJECT_ACCESS_DENIED';
  end if;
  update public.acs_workspace_jobs
     set state = 'FAILED', error_code = 'PROVIDER_OUTCOME_UNKNOWN', finished_at = now()
   where project_id = p_project
     and state = 'RUNNING'
     and created_at < now() - case when checkpoint->>'kind' = 'designer'
                                   then interval '3 hours' else interval '35 minutes' end;
  get diagnostics released = row_count;
  return released;
end $$;

revoke all on function public.acs_release_stale_job(uuid) from public, anon;
grant execute on function public.acs_release_stale_job(uuid) to authenticated;
