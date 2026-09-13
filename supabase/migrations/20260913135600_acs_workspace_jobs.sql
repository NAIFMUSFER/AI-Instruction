-- Durable delivery receipts. Canonical revisions/approvals remain in PlanStore.
-- A job status is never accepted as model, approval or artifact authority.
create table if not exists public.acs_workspace_jobs (
  id uuid primary key,
  project_id uuid not null references public.acs_projects(id) on delete cascade,
  created_by uuid not null default auth.uid() references auth.users(id),
  input_hash text not null check (input_hash ~ '^[a-f0-9]{64}$'),
  expected_head text,
  worker_id uuid not null,
  state text not null default 'RUNNING' check (state in ('RUNNING','SUCCEEDED','FAILED')),
  revision_id text,
  error_code text check (length(error_code) <= 80),
  created_at timestamptz not null default now(),
  finished_at timestamptz,
  foreign key (project_id, revision_id) references public.acs_plan_revisions(project_id, revision_id)
);
alter table public.acs_workspace_jobs enable row level security;
revoke all on public.acs_workspace_jobs from public, anon, authenticated;
grant select, insert on public.acs_workspace_jobs to authenticated;
grant update (state, revision_id, error_code, finished_at) on public.acs_workspace_jobs to authenticated;
create policy acs_workspace_job_read on public.acs_workspace_jobs for select to authenticated
  using (created_by = (select auth.uid()) and exists (
    select 1 from public.acs_project_members m
    where m.project_id = acs_workspace_jobs.project_id and m.user_id = (select auth.uid()) and m.role in ('owner','editor')
  ));
create policy acs_workspace_job_insert on public.acs_workspace_jobs for insert to authenticated
  with check (created_by = (select auth.uid()) and state = 'RUNNING' and revision_id is null
    and error_code is null and finished_at is null and exists (
      select 1 from public.acs_project_members m
      where m.project_id = acs_workspace_jobs.project_id and m.user_id = (select auth.uid()) and m.role in ('owner','editor')
  ));
create policy acs_workspace_job_finish on public.acs_workspace_jobs for update to authenticated
  using (created_by = (select auth.uid()) and state = 'RUNNING' and exists (
    select 1 from public.acs_project_members m
    where m.project_id = acs_workspace_jobs.project_id and m.user_id = (select auth.uid()) and m.role in ('owner','editor')
  ))
  with check (created_by = (select auth.uid()) and state in ('SUCCEEDED','FAILED') and exists (
    select 1 from public.acs_project_members m
    where m.project_id = acs_workspace_jobs.project_id and m.user_id = (select auth.uid()) and m.role in ('owner','editor')
  ));
create index if not exists acs_workspace_jobs_project_actor on public.acs_workspace_jobs(project_id, created_by, created_at desc);
create index if not exists acs_workspace_jobs_actor on public.acs_workspace_jobs(created_by);
create index if not exists acs_workspace_jobs_revision on public.acs_workspace_jobs(project_id, revision_id);
