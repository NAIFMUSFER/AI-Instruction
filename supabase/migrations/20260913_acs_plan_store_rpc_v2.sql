-- ACS Design Pipeline v2 — authenticated Supabase persistence RPC boundary.
--
-- The Canonical ACS Model remains authoritative. These columns/RPCs persist
-- immutable revision + approval receipts and project pointers only; CAD/BIM/3D
-- are never accepted as alternate authoring authority.

alter table public.acs_projects
  add column if not exists head_revision_id text,
  add column if not exists baseline_revision_id text,
  add column if not exists updated_at timestamptz not null default now();

alter table public.acs_plan_revisions
  add column if not exists created_by uuid references auth.users(id);

-- This migration is introduced before the application write path is enabled.
-- Refuse to invent authors for pre-existing rows: production rollout must stop
-- instead of backfilling identity if an unexpected row already exists.
do $$
begin
  if exists (select 1 from public.acs_plan_revisions where created_by is null) then
    raise exception 'ACS_CREATED_BY_BACKFILL_REQUIRED';
  end if;
end $$;

alter table public.acs_plan_revisions alter column created_by set not null;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'acs_projects_head_revision_fk') then
    alter table public.acs_projects
      add constraint acs_projects_head_revision_fk
      foreign key (id, head_revision_id)
      references public.acs_plan_revisions(project_id, revision_id)
      on delete restrict;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'acs_projects_baseline_revision_fk') then
    alter table public.acs_projects
      add constraint acs_projects_baseline_revision_fk
      foreign key (id, baseline_revision_id)
      references public.acs_plan_approvals(project_id, revision_id)
      on delete restrict;
  end if;
end $$;

-- Keep direct client table privileges narrow: authenticated clients still cannot
-- mutate project authority pointers directly. Only private, checked helpers do so.
revoke update (head_revision_id, baseline_revision_id, updated_at)
  on table public.acs_projects from authenticated;

create schema if not exists acs_private;
revoke all on schema acs_private from public, anon;
grant usage on schema acs_private to authenticated;

create or replace function acs_private.acs_plan_project_state(p_project uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, acs_private, pg_temp
as $$
declare
  uid uuid := auth.uid();
  p public.acs_projects%rowtype;
  role_name text;
  revisions jsonb;
begin
  if uid is null then
    raise exception using errcode = 'P0001', message = 'ACS_PROJECT_ACCESS_DENIED';
  end if;
  select * into p from public.acs_projects where id = p_project;
  if not found then
    raise exception using errcode = 'P0001', message = 'ACS_PROJECT_NOT_FOUND';
  end if;
  select m.role into role_name
  from public.acs_project_members m
  where m.project_id = p_project and m.user_id = uid;
  if role_name not in ('owner','editor','viewer') then
    raise exception using errcode = 'P0001', message = 'ACS_PROJECT_ACCESS_DENIED';
  end if;
  select coalesce(jsonb_agg(jsonb_build_object(
      'revision_id', r.revision_id,
      'number', r.revision_number,
      'parent_id', r.parent_revision_id,
      'created_by', r.created_by,
      'created_at', r.created_at
    ) order by r.revision_number), '[]'::jsonb)
    into revisions
  from public.acs_plan_revisions r where r.project_id = p_project;
  return jsonb_build_object(
    'schema','acs.plan-store/1.0',
    'project_id',p.id,
    'role',role_name,
    'head_revision_id',p.head_revision_id,
    'baseline_revision_id',p.baseline_revision_id,
    'revisions',revisions
  );
end;
$$;

create or replace function acs_private.acs_plan_workspace_snapshot(p_project uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = public, acs_private, pg_temp
as $$
declare
  uid uuid := auth.uid();
  p public.acs_projects%rowtype;
  role_name text;
  revisions jsonb;
  approvals jsonb;
begin
  if uid is null then
    raise exception using errcode = 'P0001', message = 'ACS_PROJECT_ACCESS_DENIED';
  end if;
  select * into p from public.acs_projects where id = p_project;
  if not found then
    raise exception using errcode = 'P0001', message = 'ACS_PROJECT_NOT_FOUND';
  end if;
  select m.role into role_name
  from public.acs_project_members m
  where m.project_id = p_project and m.user_id = uid;
  if role_name not in ('owner','editor') then
    raise exception using errcode = 'P0001', message = 'ACS_PROJECT_ACCESS_DENIED';
  end if;
  select coalesce(jsonb_agg(r.revision_json order by r.revision_number), '[]'::jsonb)
    into revisions from public.acs_plan_revisions r where r.project_id = p_project;
  select coalesce(jsonb_agg(a.approval_json order by a.approved_at, a.revision_id), '[]'::jsonb)
    into approvals from public.acs_plan_approvals a where a.project_id = p_project;
  return jsonb_build_object(
    'schema','acs.plan-store-workspace-snapshot/1.0',
    'project_id',p.id,
    'head_revision_id',p.head_revision_id,
    'baseline_revision_id',p.baseline_revision_id,
    'revisions',revisions,
    'approvals',approvals
  );
end;
$$;

create or replace function acs_private.acs_save_plan_revision(
  p_project uuid,
  p_expected_head text,
  p_revision jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, acs_private, pg_temp
as $$
declare
  uid uuid := auth.uid();
  current_head text;
  role_name text;
  rid text := p_revision->>'revision_id';
  parent_id text := nullif(p_revision->>'parent_id','');
  rev_number integer;
  previous_number integer := 0;
begin
  if uid is null then
    raise exception using errcode='P0001', message='ACS_PROJECT_ACCESS_DENIED';
  end if;
  select p.head_revision_id into current_head
    from public.acs_projects p where p.id=p_project for update;
  if not found then
    raise exception using errcode='P0001', message='ACS_PROJECT_NOT_FOUND';
  end if;
  select m.role into role_name from public.acs_project_members m
    where m.project_id=p_project and m.user_id=uid;
  if role_name not in ('owner','editor') then
    raise exception using errcode='P0001', message='ACS_PROJECT_ACCESS_DENIED';
  end if;
  if current_head is distinct from p_expected_head then
    raise exception using errcode='P0001', message='ACS_STALE_REVISION';
  end if;
  if parent_id is distinct from p_expected_head then
    raise exception using errcode='P0001', message='ACS_INVALID_REVISION_CHAIN';
  end if;
  begin
    rev_number := (p_revision->>'number')::integer;
  exception when others then
    raise exception using errcode='P0001', message='ACS_INVALID_REVISION_CHAIN';
  end;
  if p_expected_head is not null then
    select r.revision_number into previous_number
      from public.acs_plan_revisions r
      where r.project_id=p_project and r.revision_id=p_expected_head;
    if not found then
      raise exception using errcode='P0001', message='ACS_INVALID_REVISION_CHAIN';
    end if;
  end if;
  if rev_number <> previous_number + 1 then
    raise exception using errcode='P0001', message='ACS_INVALID_REVISION_CHAIN';
  end if;
  begin
    insert into public.acs_plan_revisions(
      project_id,revision_id,revision_number,parent_revision_id,revision_json,
      model_hash,content_hash,bound_content_hash,semantic_lock_manifest_hash,
      created_by,created_at
    ) values (
      p_project,rid,rev_number,parent_id,p_revision,
      p_revision->>'model_hash',p_revision->>'content_hash',p_revision->>'bound_content_hash',
      nullif(p_revision->>'semantic_lock_manifest_hash',''),uid,
      (p_revision->>'created_at')::timestamptz
    );
  exception when unique_violation then
    raise exception using errcode='P0001', message='ACS_REVISION_EXISTS';
  when foreign_key_violation then
    raise exception using errcode='P0001', message='ACS_INVALID_REVISION_CHAIN';
  end;
  update public.acs_projects
    set head_revision_id=rid, updated_at=now()
    where id=p_project;
  return p_revision;
end;
$$;

create or replace function acs_private.acs_save_plan_approval(
  p_project uuid,
  p_expected_head text,
  p_approval jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, acs_private, pg_temp
as $$
declare
  uid uuid := auth.uid();
  current_head text;
  role_name text;
  rid text := p_approval->>'revision_id';
  rev public.acs_plan_revisions%rowtype;
begin
  if uid is null then
    raise exception using errcode='P0001', message='ACS_PROJECT_ACCESS_DENIED';
  end if;
  select p.head_revision_id into current_head
    from public.acs_projects p where p.id=p_project for update;
  if not found then
    raise exception using errcode='P0001', message='ACS_PROJECT_NOT_FOUND';
  end if;
  select m.role into role_name from public.acs_project_members m
    where m.project_id=p_project and m.user_id=uid;
  if role_name not in ('owner','editor') then
    raise exception using errcode='P0001', message='ACS_PROJECT_ACCESS_DENIED';
  end if;
  if current_head is distinct from p_expected_head or rid is distinct from p_expected_head then
    raise exception using errcode='P0001', message='ACS_STALE_REVISION';
  end if;
  select * into rev from public.acs_plan_revisions
    where project_id=p_project and revision_id=rid;
  if not found then
    raise exception using errcode='P0001', message='ACS_REVISION_NOT_FOUND';
  end if;
  if (p_approval->>'revision_content_hash') is distinct from rev.content_hash
     or (p_approval->>'bound_content_hash') is distinct from rev.bound_content_hash
     or (p_approval->>'model_hash') is distinct from rev.model_hash
     or nullif(p_approval->>'semantic_lock_manifest_hash','') is distinct from rev.semantic_lock_manifest_hash then
    raise exception using errcode='P0001', message='ACS_APPROVAL_RECEIPT_CHANGED';
  end if;
  begin
    insert into public.acs_plan_approvals(
      project_id,revision_id,approval_json,revision_content_hash,bound_content_hash,
      model_hash,approved_by,approved_at
    ) values (
      p_project,rid,p_approval,p_approval->>'revision_content_hash',
      p_approval->>'bound_content_hash',p_approval->>'model_hash',uid,
      (p_approval->>'approved_at')::timestamptz
    );
  exception when unique_violation then
    raise exception using errcode='P0001', message='ACS_APPROVAL_EXISTS';
  end;
  update public.acs_projects
    set baseline_revision_id=rid, updated_at=now()
    where id=p_project;
  return p_approval;
end;
$$;

-- Private SECURITY DEFINER helpers are not in the exposed API schema.
revoke all on function acs_private.acs_plan_project_state(uuid) from public, anon;
revoke all on function acs_private.acs_plan_workspace_snapshot(uuid) from public, anon;
revoke all on function acs_private.acs_save_plan_revision(uuid,text,jsonb) from public, anon;
revoke all on function acs_private.acs_save_plan_approval(uuid,text,jsonb) from public, anon;
grant execute on function acs_private.acs_plan_project_state(uuid) to authenticated;
grant execute on function acs_private.acs_plan_workspace_snapshot(uuid) to authenticated;
grant execute on function acs_private.acs_save_plan_revision(uuid,text,jsonb) to authenticated;
grant execute on function acs_private.acs_save_plan_approval(uuid,text,jsonb) to authenticated;

-- Public API wrappers remain SECURITY INVOKER and contain no privileged logic.
create or replace function public.acs_plan_project_state(p_project uuid)
returns jsonb language sql stable security invoker set search_path=public,acs_private,pg_temp
as $$ select acs_private.acs_plan_project_state(p_project); $$;
create or replace function public.acs_plan_workspace_snapshot(p_project uuid)
returns jsonb language sql stable security invoker set search_path=public,acs_private,pg_temp
as $$ select acs_private.acs_plan_workspace_snapshot(p_project); $$;
create or replace function public.acs_save_plan_revision(p_project uuid,p_expected_head text,p_revision jsonb)
returns jsonb language sql security invoker set search_path=public,acs_private,pg_temp
as $$ select acs_private.acs_save_plan_revision(p_project,p_expected_head,p_revision); $$;
create or replace function public.acs_save_plan_approval(p_project uuid,p_expected_head text,p_approval jsonb)
returns jsonb language sql security invoker set search_path=public,acs_private,pg_temp
as $$ select acs_private.acs_save_plan_approval(p_project,p_expected_head,p_approval); $$;

revoke all on function public.acs_plan_project_state(uuid) from public, anon;
revoke all on function public.acs_plan_workspace_snapshot(uuid) from public, anon;
revoke all on function public.acs_save_plan_revision(uuid,text,jsonb) from public, anon;
revoke all on function public.acs_save_plan_approval(uuid,text,jsonb) from public, anon;
grant execute on function public.acs_plan_project_state(uuid) to authenticated;
grant execute on function public.acs_plan_workspace_snapshot(uuid) to authenticated;
grant execute on function public.acs_save_plan_revision(uuid,text,jsonb) to authenticated;
grant execute on function public.acs_save_plan_approval(uuid,text,jsonb) to authenticated;
