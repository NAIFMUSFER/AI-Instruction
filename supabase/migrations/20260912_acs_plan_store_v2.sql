-- ACS Design Pipeline v2 durable plan-store schema.
-- Canonical ACS Model receipts remain the source of truth; this database stores
-- immutable revision/approval/handoff receipts and never treats CAD/BIM/3D as authority.

create table if not exists public.acs_projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 200),
  created_at timestamptz not null default now()
);

create table if not exists public.acs_project_members (
  project_id uuid not null references public.acs_projects(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('owner','editor','viewer')),
  created_at timestamptz not null default now(),
  primary key (project_id, user_id)
);

create table if not exists public.acs_plan_revisions (
  project_id uuid not null references public.acs_projects(id) on delete cascade,
  revision_id text not null check (char_length(revision_id) between 1 and 160),
  revision_number integer not null check (revision_number > 0),
  parent_revision_id text,
  revision_json jsonb not null,
  model_hash text not null check (char_length(model_hash) = 64),
  content_hash text not null check (char_length(content_hash) = 64),
  bound_content_hash text not null check (char_length(bound_content_hash) = 64),
  semantic_lock_manifest_hash text,
  created_at timestamptz not null default now(),
  primary key (project_id, revision_id),
  unique (project_id, revision_number),
  check (semantic_lock_manifest_hash is null or char_length(semantic_lock_manifest_hash) = 64)
);

create table if not exists public.acs_plan_approvals (
  project_id uuid not null references public.acs_projects(id) on delete cascade,
  revision_id text not null,
  approval_json jsonb not null,
  revision_content_hash text not null check (char_length(revision_content_hash) = 64),
  bound_content_hash text not null check (char_length(bound_content_hash) = 64),
  model_hash text not null check (char_length(model_hash) = 64),
  approved_by uuid not null references auth.users(id),
  approved_at timestamptz not null default now(),
  primary key (project_id, revision_id),
  foreign key (project_id, revision_id)
    references public.acs_plan_revisions(project_id, revision_id) on delete restrict
);

create table if not exists public.acs_plan_handoffs (
  project_id uuid not null references public.acs_projects(id) on delete cascade,
  revision_id text not null,
  artifact_kind text not null check (artifact_kind in ('bim','3d','dxf','ifc','svg','pdf')),
  handoff_json jsonb not null,
  provenance_hash text not null check (char_length(provenance_hash) = 64),
  created_at timestamptz not null default now(),
  primary key (project_id, revision_id, artifact_kind),
  foreign key (project_id, revision_id)
    references public.acs_plan_revisions(project_id, revision_id) on delete restrict
);

create index if not exists acs_project_members_user_idx on public.acs_project_members(user_id, project_id);
create index if not exists acs_plan_revisions_project_number_idx on public.acs_plan_revisions(project_id, revision_number desc);

alter table public.acs_projects enable row level security;
alter table public.acs_project_members enable row level security;
alter table public.acs_plan_revisions enable row level security;
alter table public.acs_plan_approvals enable row level security;
alter table public.acs_plan_handoffs enable row level security;

-- Membership predicate is SECURITY DEFINER only to avoid recursive RLS on the
-- membership table. It exposes only a boolean and pins search_path.
create or replace function public.acs_has_project_role(p_project uuid, allowed_roles text[])
returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select exists (
    select 1 from public.acs_project_members m
    where m.project_id = p_project
      and m.user_id = auth.uid()
      and m.role = any(allowed_roles)
  );
$$;
revoke all on function public.acs_has_project_role(uuid,text[]) from public;
grant execute on function public.acs_has_project_role(uuid,text[]) to authenticated;

create policy acs_projects_select_member on public.acs_projects
for select to authenticated using (public.acs_has_project_role(id, array['owner','editor','viewer']));
create policy acs_projects_insert_owner on public.acs_projects
for insert to authenticated with check (owner_id = auth.uid());
create policy acs_projects_update_owner on public.acs_projects
for update to authenticated using (owner_id = auth.uid()) with check (owner_id = auth.uid());

create policy acs_members_select_member on public.acs_project_members
for select to authenticated using (public.acs_has_project_role(project_id, array['owner','editor','viewer']));
create policy acs_members_insert_owner on public.acs_project_members
for insert to authenticated with check (
  user_id = auth.uid() and role = 'owner' and
  exists (select 1 from public.acs_projects p where p.id = project_id and p.owner_id = auth.uid())
  or public.acs_has_project_role(project_id, array['owner'])
);
create policy acs_members_update_owner on public.acs_project_members
for update to authenticated using (public.acs_has_project_role(project_id, array['owner']))
with check (public.acs_has_project_role(project_id, array['owner']));
create policy acs_members_delete_owner on public.acs_project_members
for delete to authenticated using (public.acs_has_project_role(project_id, array['owner']) and role <> 'owner');

create policy acs_revisions_select_member on public.acs_plan_revisions
for select to authenticated using (public.acs_has_project_role(project_id, array['owner','editor','viewer']));
create policy acs_revisions_insert_editor on public.acs_plan_revisions
for insert to authenticated with check (public.acs_has_project_role(project_id, array['owner','editor']));
-- Revisions are immutable: intentionally no UPDATE or DELETE policy.

create policy acs_approvals_select_member on public.acs_plan_approvals
for select to authenticated using (public.acs_has_project_role(project_id, array['owner','editor','viewer']));
create policy acs_approvals_insert_editor on public.acs_plan_approvals
for insert to authenticated with check (
  approved_by = auth.uid() and public.acs_has_project_role(project_id, array['owner','editor'])
);
-- Approval receipts are immutable.

create policy acs_handoffs_select_member on public.acs_plan_handoffs
for select to authenticated using (public.acs_has_project_role(project_id, array['owner','editor','viewer']));
create policy acs_handoffs_insert_editor on public.acs_plan_handoffs
for insert to authenticated with check (public.acs_has_project_role(project_id, array['owner','editor']));
-- Derived artifact receipts are immutable and remain downstream of approved revisions.
