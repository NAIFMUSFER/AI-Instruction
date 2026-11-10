-- ACS 2026-11-10: fail-closed roles and bounded immutable-history reads.
-- Historical migrations remain unchanged. Missing and inaccessible projects have
-- the same denial; no private existence or revision metadata is returned.
create or replace function acs_private.acs_require_project_role(p_project uuid, p_roles text[])
returns text language plpgsql stable security definer
set search_path = pg_catalog, public, acs_private, pg_temp
as $$
declare role_name text;
begin
  if auth.uid() is null then
    raise exception using errcode='P0001', message='ACS_PROJECT_ACCESS_DENIED';
  end if;
  select m.role into role_name from public.acs_project_members m
    where m.project_id=p_project and m.user_id=auth.uid();
  if role_name is null or not (role_name=any(p_roles)) then
    raise exception using errcode='P0001', message='ACS_PROJECT_ACCESS_DENIED';
  end if;
  return role_name;
end $$;
revoke all on function acs_private.acs_require_project_role(uuid,text[]) from public, anon, authenticated;

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
  perform acs_private.acs_require_project_role(p_project, array['owner','editor','viewer']);
  select * into p from public.acs_projects where id = p_project;
  if not found then
    raise exception using errcode = 'P0001', message = 'ACS_PROJECT_NOT_FOUND';
  end if;
  select m.role into role_name
  from public.acs_project_members m
  where m.project_id = p_project and m.user_id = uid;
  if role_name is null or role_name not in ('owner','editor','viewer') then
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
  perform acs_private.acs_require_project_role(p_project, array['owner','editor']);
  select * into p from public.acs_projects where id = p_project;
  if not found then
    raise exception using errcode = 'P0001', message = 'ACS_PROJECT_NOT_FOUND';
  end if;
  select m.role into role_name
  from public.acs_project_members m
  where m.project_id = p_project and m.user_id = uid;
  if role_name is null or role_name not in ('owner','editor') then
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
  perform acs_private.acs_require_project_role(p_project, array['owner','editor']);
  select p.head_revision_id into current_head
    from public.acs_projects p where p.id=p_project for update;
  if not found then
    raise exception using errcode='P0001', message='ACS_PROJECT_NOT_FOUND';
  end if;
  select m.role into role_name from public.acs_project_members m
    where m.project_id=p_project and m.user_id=uid;
  if role_name is null or role_name not in ('owner','editor') then
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
  if rev_number > 100 then
    raise exception using errcode='P0001', message='ACS_HISTORY_LIMIT';
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
  perform acs_private.acs_require_project_role(p_project, array['owner','editor']);
  select p.head_revision_id into current_head
    from public.acs_projects p where p.id=p_project for update;
  if not found then
    raise exception using errcode='P0001', message='ACS_PROJECT_NOT_FOUND';
  end if;
  select m.role into role_name from public.acs_project_members m
    where m.project_id=p_project and m.user_id=uid;
  if role_name is null or role_name not in ('owner','editor') then
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


-- Bounded transport: metadata pages plus a single immutable revision per read.
-- p_head pins subsequent reads; final adapter pointer comparison catches approval
-- changes during recovery as well. Never truncate or replace immutable history.
create or replace function acs_private.acs_plan_revision_page(
  p_project uuid, p_after integer default 0, p_limit integer default 25,
  p_head text default null)
returns jsonb language plpgsql stable security definer
set search_path=pg_catalog,public,acs_private,pg_temp
as $$
declare
  role_name text;
  p public.acs_projects%rowtype;
  rows jsonb;
  next_number integer;
begin
  role_name := acs_private.acs_require_project_role(p_project,array['owner','editor','viewer']);
  if p_after is null or p_after < 0 or p_limit is null or p_limit < 1 or p_limit > 25 then
    raise exception using errcode='P0001', message='ACS_HISTORY_PAGE_INVALID';
  end if;
  select * into p from public.acs_projects where id=p_project;
  if p_after > 0 and p.head_revision_id is distinct from p_head then
    raise exception using errcode='P0001', message='ACS_STALE_REVISION';
  end if;
  select coalesce(jsonb_agg(jsonb_build_object(
      'revision_id',r.revision_id,'number',r.revision_number,
      'parent_id',r.parent_revision_id,'created_by',r.created_by,
      'created_at',r.created_at,'content_hash',r.content_hash,
      'bound_content_hash',r.bound_content_hash) order by r.revision_number),'[]'::jsonb),
      max(r.revision_number) into rows,next_number
  from (select * from public.acs_plan_revisions
        where project_id=p_project and revision_number>p_after
        order by revision_number limit p_limit) r;
  return jsonb_build_object('schema','acs.plan-revision-page/1.0','project_id',p.id,
      'role',role_name,'head_revision_id',p.head_revision_id,
      'baseline_revision_id',p.baseline_revision_id,'revisions',rows,
      'next_after',case when exists(select 1 from public.acs_plan_revisions
         where project_id=p_project and revision_number>next_number)
         then next_number else null end);
end $$;
create or replace function acs_private.acs_plan_revision_document(
  p_project uuid,p_revision text,p_head text)
returns jsonb language plpgsql stable security definer
set search_path=pg_catalog,public,acs_private,pg_temp
as $$
declare r public.acs_plan_revisions%rowtype; approval jsonb; current_head text;
begin
  perform acs_private.acs_require_project_role(p_project,array['owner','editor','viewer']);
  select head_revision_id into current_head from public.acs_projects where id=p_project;
  if current_head is distinct from p_head then
    raise exception using errcode='P0001',message='ACS_STALE_REVISION';
  end if;
  select * into r from public.acs_plan_revisions where project_id=p_project and revision_id=p_revision;
  if not found then
    raise exception using errcode='P0001',message='ACS_REVISION_NOT_FOUND';
  end if;
  select approval_json into approval from public.acs_plan_approvals
    where project_id=p_project and revision_id=p_revision;
  return jsonb_build_object('schema','acs.plan-revision-document/1.0',
    'project_id',p_project,'revision',r.revision_json,'approval',approval);
end $$;
create or replace function public.acs_plan_revision_page(
 p_project uuid,p_after integer default 0,p_limit integer default 25,p_head text default null)
returns jsonb language sql stable security invoker set search_path=pg_catalog,public,acs_private,pg_temp
as $$ select acs_private.acs_plan_revision_page(p_project,p_after,p_limit,p_head); $$;
create or replace function public.acs_plan_revision_document(p_project uuid,p_revision text,p_head text)
returns jsonb language sql stable security invoker set search_path=pg_catalog,public,acs_private,pg_temp
as $$ select acs_private.acs_plan_revision_document(p_project,p_revision,p_head); $$;
revoke all on function acs_private.acs_plan_revision_page(uuid,integer,integer,text) from public,anon;
revoke all on function acs_private.acs_plan_revision_document(uuid,text,text) from public,anon;
revoke all on function public.acs_plan_revision_page(uuid,integer,integer,text) from public,anon;
revoke all on function public.acs_plan_revision_document(uuid,text,text) from public,anon;
grant execute on function acs_private.acs_plan_revision_page(uuid,integer,integer,text) to authenticated;
grant execute on function acs_private.acs_plan_revision_document(uuid,text,text) to authenticated;
grant execute on function public.acs_plan_revision_page(uuid,integer,integer,text) to authenticated;
grant execute on function public.acs_plan_revision_document(uuid,text,text) to authenticated;

-- Dedicated backend validation key; never an auth impersonation/service-role key.
-- Provision a random 32-byte (64 hex character) value as name='v1' AND as the
-- backend-only ACS_PLAN_WRITE_SECRET before enabling writes. An empty table fails
-- closed. Do not expose it through RPCs, logs, client config or migration source.
create table if not exists acs_private.acs_backend_write_keys(
  name text primary key check(name='v1'),
  secret text not null check(secret ~ '^[0-9a-f]{64}$')
);
revoke all on table acs_private.acs_backend_write_keys from public,anon,authenticated;
alter table acs_private.acs_backend_write_keys enable row level security;

-- RFC 2104 HMAC-SHA256 using PostgreSQL's built-in SHA256, no extension required.
create or replace function acs_private.acs_hmac_sha256(p_message text,p_key text)
returns text language plpgsql immutable strict
set search_path=pg_catalog,acs_private,pg_temp
as $$
declare k bytea := convert_to(p_key,'UTF8'); i integer;
  ipad bytea := decode(repeat('00',64),'hex'); opad bytea := ipad;
begin
  if octet_length(k)>64 then k:=sha256(k); end if;
  k:=k || decode(repeat('00',64-octet_length(k)),'hex');
  for i in 0..63 loop
    ipad:=set_byte(ipad,i,get_byte(k,i) # 54);
    opad:=set_byte(opad,i,get_byte(k,i) # 92);
  end loop;
  return encode(sha256(opad || sha256(ipad || convert_to(p_message,'UTF8'))),'hex');
end $$;
revoke all on function acs_private.acs_hmac_sha256(text,text) from public,anon,authenticated;

create or replace function acs_private.acs_verified_backend_payload(
 p_payload text,p_signature text,p_kind text)
returns jsonb language plpgsql security definer
set search_path=pg_catalog,acs_private,public,pg_temp
as $$
declare key_text text; env jsonb; expires numeric; now_epoch numeric;
  expected_signature bytea; supplied_signature bytea; mismatch integer:=0; i integer;
begin
  if auth.uid() is null then
    raise exception using errcode='P0001',message='ACS_PROJECT_ACCESS_DENIED';
  end if;
  if p_payload is null or octet_length(p_payload)>2600000 or p_signature is null
      or p_signature !~ '^[0-9a-f]{64}$' then
    raise exception using errcode='P0001',message='ACS_VALIDATED_WRITE_REQUIRED';
  end if;
  select secret into key_text from acs_private.acs_backend_write_keys where name='v1';
  if key_text is null then
    raise exception using errcode='P0001',message='ACS_WRITE_BOUNDARY_UNAVAILABLE';
  end if;
  expected_signature:=decode(acs_private.acs_hmac_sha256(p_payload,key_text),'hex');
  supplied_signature:=decode(p_signature,'hex');
  for i in 0..31 loop
    mismatch:=mismatch | (get_byte(expected_signature,i) # get_byte(supplied_signature,i));
  end loop;
  if mismatch<>0 then
    raise exception using errcode='P0001',message='ACS_VALIDATED_WRITE_REQUIRED';
  end if;
  begin
    env:=p_payload::jsonb;
    expires:=(env->>'expires_at')::numeric;
  exception when others then
    raise exception using errcode='P0001',message='ACS_VALIDATED_WRITE_REQUIRED';
  end;
  now_epoch:=extract(epoch from clock_timestamp());
  if jsonb_typeof(env) is distinct from 'object'
      or env->>'schema' is distinct from 'acs.validated-write/1.0'
      or env->>'kind' is distinct from p_kind
      or env->>'actor_id' is distinct from auth.uid()::text
      or expires is null or expires<now_epoch or expires>now_epoch+120
      or jsonb_typeof(env->'document') is distinct from 'object' then
    raise exception using errcode='P0001',message='ACS_VALIDATED_WRITE_REQUIRED';
  end if;
  return env;
end $$;
revoke all on function acs_private.acs_verified_backend_payload(text,text,text) from public,anon,authenticated;

-- Predicate helper exposes only the caller's own ownership, never an arbitrary
-- user's ownership relationship when invoked directly through SQL/RPC schemas.
create or replace function acs_private.acs_is_project_owner(p_project uuid,p_user uuid)
returns boolean language sql stable security definer
set search_path=pg_catalog,public,pg_temp
as $$ select p_user=auth.uid() and exists(
  select 1 from public.acs_projects p where p.id=p_project and p.owner_id=auth.uid()
); $$;
revoke all on function acs_private.acs_is_project_owner(uuid,uuid) from public,anon;
grant execute on function acs_private.acs_is_project_owner(uuid,uuid) to authenticated;
