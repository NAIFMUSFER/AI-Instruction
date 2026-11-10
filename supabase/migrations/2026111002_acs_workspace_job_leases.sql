-- Server-signed durable paid-operation admission and fenced worker leases.
-- Depends on acs_private.acs_verified_backend_payload from the write-boundary migration.
do $$ begin
  if not exists(select 1 from acs_private.acs_backend_write_keys where name='v1') then
    raise exception 'BACKEND_WRITE_KEY_REQUIRED';
  end if;
end $$;
alter table public.acs_workspace_jobs
  add column if not exists lease_token uuid,
  add column if not exists lease_expires_at timestamptz,
  add column if not exists heartbeat_at timestamptz,
  add column if not exists resumed_by uuid;
alter table public.acs_workspace_jobs drop constraint if exists acs_workspace_jobs_state_check;
alter table public.acs_workspace_jobs add constraint acs_workspace_jobs_state_check
  check (state in ('RUNNING','SUCCEEDED','FAILED','INTERRUPTED','CANCELLED'));
-- Old in-flight work has unknown ownership, not proof of a safely retryable call.
update public.acs_workspace_jobs set state='INTERRUPTED', error_code='PROVIDER_OUTCOME_UNKNOWN', finished_at=clock_timestamp()
 where state='RUNNING' and lease_expires_at is null;
revoke insert, update, delete on public.acs_workspace_jobs from public, anon, authenticated;
-- Revoke earlier column grants too: REVOKE UPDATE(table) alone leaves them.
revoke update (state,revision_id,error_code,finished_at,phase,progress,checkpoint,provider_calls)
 on public.acs_workspace_jobs from authenticated;

create or replace function public.acs_workspace_job_mutate(p_payload text, p_signature text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  env jsonb; doc jsonb; op text; pid uuid; actor uuid; jid uuid; token uuid;
  row public.acs_workspace_jobs%rowtype; old public.acs_workspace_jobs%rowtype;
  cmd jsonb; expected text; actual text; member_role text; now_at timestamptz := clock_timestamp();
begin
  env := acs_private.acs_verified_backend_payload(p_payload,p_signature,'workspace_job');
  doc := env->'document'; op := doc->>'operation';
  pid := (env->>'project_id')::uuid; actor := auth.uid(); jid := (doc->>'job_id')::uuid;
  if jsonb_typeof(doc) is distinct from 'object' or length(doc::text) > 3000000 then
    raise exception 'INVALID_JOB_COMMAND' using errcode='22023';
  end if;
  select m.role into member_role from public.acs_project_members m where m.project_id=pid and m.user_id=actor for share;
  if member_role is null or member_role not in ('owner','editor') then
    raise exception 'PROJECT_ACCESS_DENIED' using errcode='42501';
  end if;
  if jid is null or op is null then raise exception 'INVALID_JOB_COMMAND'; end if;
  -- Serialize admissions across replicas; no local-worker heuristic is authority.
  if op='reserve' then
    perform pg_advisory_xact_lock(743106821);
  end if;
  select * into row from public.acs_workspace_jobs j where j.id=jid and j.project_id=pid and j.created_by=actor for update;
  now_at := clock_timestamp();
  if to_timestamp((env->>'expires_at')::double precision) <= now_at then raise exception 'EXPIRED_CAPABILITY'; end if;
  if op='reserve' then
    if row.id is not null then
      if row.input_hash is distinct from doc->>'input_hash' then raise exception 'STALE_REVISION'; end if;
      return jsonb_build_object('created',false,'job',to_jsonb(row));
    end if;
    cmd := doc->'command'; expected := env->>'expected_head';
    if jsonb_typeof(cmd) is distinct from 'object' or cmd->>'action' is null or cmd->>'action' not in ('generate','chat_edit') or cmd->'confirmed' is distinct from 'true'::jsonb
       or cmd->>'job_id' is distinct from jid::text or cmd->>'expected_head' is distinct from expected
       or jsonb_typeof(cmd->'max_provider_calls') is distinct from 'number'
       or (cmd->>'max_provider_calls')::numeric <> trunc((cmd->>'max_provider_calls')::numeric)
       or (cmd->>'max_provider_calls')::integer not between 1 and 12
       or doc->>'input_hash' is null or doc->>'input_hash' !~ '^[a-f0-9]{64}$' then raise exception 'INVALID_JOB_COMMAND'; end if;
    -- Canonical project head row locked before paid work; changes still undergo
    -- the normal append CAS after generation.
    select p.head_revision_id into actual from public.acs_projects p where p.id=pid for update;
    if not found then raise exception 'PROJECT_ACCESS_DENIED' using errcode='42501'; end if;
    now_at := clock_timestamp();
    if to_timestamp((env->>'expires_at')::double precision) <= now_at then raise exception 'EXPIRED_CAPABILITY'; end if;
    if actual is distinct from expected then raise exception 'STALE_REVISION'; end if;
    if (select count(*) from public.acs_workspace_jobs j where j.state='RUNNING' and j.lease_expires_at > now_at) >= 8
       or exists(select 1 from public.acs_workspace_jobs j where j.project_id=pid and j.state='RUNNING' and j.lease_expires_at > now_at) then
      raise exception 'GENERATION_BUSY';
    end if;
    -- Durable abuse/cost request quotas supplement the configured HTTP limiter.
    if (select count(*) from public.acs_workspace_jobs j where j.created_at > now_at-interval '1 day') >= 400
       or (select count(*) from public.acs_workspace_jobs j where j.created_by=actor and j.created_at > now_at-interval '1 day') >= 25
       or (select count(*) from public.acs_workspace_jobs j where j.created_by=actor and j.created_at > now_at-interval '1 hour'
           and j.resume_command->>'action'=cmd->>'action') >= (case when cmd->>'action'='chat_edit' then 30 else 8 end) then
      raise exception 'JOB_RATE_LIMITED';
    end if;
    if cmd->>'resume_job_id' is not null then
      select * into old from public.acs_workspace_jobs j where j.id=(cmd->>'resume_job_id')::uuid and j.project_id=pid and j.created_by=actor for update;
      if old.id is null or old.state <> 'FAILED' or old.resumed_by is not null
         or old.error_code is null or (old.error_code not in ('PLAN_DETAIL_INCOMPLETE','PLAN_LAYOUT_INCOMPLETE','ACS_PROVIDER_BUDGET_EXHAUSTED') and left(old.error_code,length('PLAN_GEOMETRY_')) <> 'PLAN_GEOMETRY_')
         or old.resume_command->>'action' <> 'generate'
         or (cmd->>'max_provider_calls')::int <= old.provider_calls then raise exception 'INVALID_RESUME'; end if;
      update public.acs_workspace_jobs set resumed_by=jid where id=old.id;
    end if;
    token := (doc->>'lease_token')::uuid;
    if token is null or doc->>'worker_id' is null then raise exception 'INVALID_JOB_COMMAND'; end if;
    insert into public.acs_workspace_jobs(id,project_id,created_by,input_hash,expected_head,worker_id,state,
      resume_command,phase,lease_token,lease_expires_at,heartbeat_at,checkpoint,provider_calls)
    values (jid,pid,actor,doc->>'input_hash',expected,(doc->>'worker_id')::uuid,'RUNNING',cmd,'UNDERSTANDING',
      token,least(now_at+interval '90 seconds',to_timestamp((env->>'expires_at')::double precision)),now_at,old.checkpoint,coalesce(old.provider_calls,0)) returning * into row;
    return jsonb_build_object('created',true,'job',to_jsonb(row));
  end if;
  if row.id is null then raise exception 'PROJECT_ACCESS_DENIED' using errcode='42501'; end if;
  if op='expire' then
    if row.state='RUNNING' and row.lease_expires_at <= now_at then
      update public.acs_workspace_jobs set state='INTERRUPTED',error_code='PROVIDER_OUTCOME_UNKNOWN',finished_at=now_at
        where id=jid returning * into row;
    end if;
    return jsonb_build_object('job',to_jsonb(row));
  elsif op='cancel' then
    if row.state='RUNNING' then
      update public.acs_workspace_jobs set state='CANCELLED',error_code='PROVIDER_OUTCOME_UNKNOWN',finished_at=now_at,lease_expires_at=now_at
        where id=jid returning * into row;
    end if;
    return jsonb_build_object('job',to_jsonb(row));
  end if;
  if op='finish' and row.state='SUCCEEDED' and doc->>'state'='SUCCEEDED' and row.revision_id=doc->>'revision_id' then
    return jsonb_build_object('job',to_jsonb(row));
  end if;
  token := (doc->>'lease_token')::uuid;
  if row.state <> 'RUNNING' or row.lease_token is distinct from token or row.lease_expires_at <= now_at then
    raise exception 'JOB_LEASE_LOST';
  end if;
  if op='heartbeat' then
    update public.acs_workspace_jobs set heartbeat_at=now_at,lease_expires_at=least(now_at+interval '90 seconds',to_timestamp((env->>'expires_at')::double precision))
      where id=jid returning * into row;
  elsif op='progress' then
    if doc ? 'provider_calls' and ((doc->>'provider_calls')::int < row.provider_calls or (doc->>'provider_calls')::int > (row.resume_command->>'max_provider_calls')::int) then
      raise exception 'INVALID_JOB_PROGRESS';
    end if;
    update public.acs_workspace_jobs set heartbeat_at=now_at,lease_expires_at=least(now_at+interval '90 seconds',to_timestamp((env->>'expires_at')::double precision)),
      phase=coalesce(doc->>'phase',phase),progress=coalesce(doc->'progress',progress),
      checkpoint=coalesce(doc->'checkpoint',checkpoint),provider_calls=coalesce((doc->>'provider_calls')::int,provider_calls)
      where id=jid returning * into row;
  elsif op='finish' then
    if doc->>'state' is null or doc->>'state' not in ('SUCCEEDED','FAILED') then raise exception 'INVALID_JOB_COMMAND'; end if;
    if doc->>'state'='SUCCEEDED' and not exists(select 1 from public.acs_plan_revisions r where r.project_id=pid and r.revision_id=doc->>'revision_id' and r.created_by=actor
        and right(r.revision_json->>'note',length('task:'||jid::text))='task:'||jid::text) then
      raise exception 'REVISION_NOT_FOUND';
    end if;
    update public.acs_workspace_jobs set state=doc->>'state',revision_id=doc->>'revision_id',error_code=doc->>'error_code',finished_at=now_at,lease_expires_at=now_at
      where id=jid returning * into row;
  else raise exception 'INVALID_JOB_COMMAND';
  end if;
  return jsonb_build_object('job',to_jsonb(row));
end $$;
revoke all on function public.acs_workspace_job_mutate(text,text) from public,anon,authenticated;
grant execute on function public.acs_workspace_job_mutate(text,text) to authenticated;
