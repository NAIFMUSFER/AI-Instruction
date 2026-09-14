-- Checkpoints remain unapproved proposal data; canonical revision gates apply.
alter table public.acs_workspace_jobs
  add column if not exists phase text,
  add column if not exists progress jsonb,
  add column if not exists checkpoint jsonb,
  add column if not exists resume_command jsonb,
  add column if not exists provider_calls integer not null default 0 check (provider_calls between 0 and 12);
grant update (phase, progress, checkpoint, provider_calls) on public.acs_workspace_jobs to authenticated;
drop policy if exists acs_workspace_job_finish on public.acs_workspace_jobs;
create policy acs_workspace_job_finish on public.acs_workspace_jobs for update to authenticated
using (created_by = (select auth.uid()) and state = 'RUNNING' and exists (
  select 1 from public.acs_project_members m where m.project_id = acs_workspace_jobs.project_id
  and m.user_id = (select auth.uid()) and m.role in ('owner','editor')))
with check (created_by = (select auth.uid()) and state in ('RUNNING','SUCCEEDED','FAILED') and exists (
  select 1 from public.acs_project_members m where m.project_id = acs_workspace_jobs.project_id
  and m.user_id = (select auth.uid()) and m.role in ('owner','editor')));
