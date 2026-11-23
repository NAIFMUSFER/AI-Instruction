-- Activate only after the backend-only validation signer is configured. Apply
-- 01, 02, 03 and key provisioning in one controlled transaction at release.
-- End-user JWT identity remains mandatory; the signature proves canonical Python
-- validation, not authority to act as another user/project or change locked scope.
do $$ begin
  if not exists(select 1 from acs_private.acs_backend_write_keys where name='v1') then
    raise exception 'ACS_VALIDATED_WRITE_KEY_NOT_PROVISIONED';
  end if;
end $$;

create or replace function public.acs_write_plan_receipt(p_payload text,p_signature text)
returns jsonb language plpgsql security definer
set search_path=pg_catalog,public,acs_private,pg_temp
as $$
declare env jsonb; p_project uuid; doc jsonb; lease_row record;
  kind text; current_head text; saved_receipt jsonb; lease_bound boolean:=false;
begin
  -- Read kind only to select the signed purpose; every accepted purpose has an
  -- exact validator below. Parsing cannot write anything or reveal project data.
  if p_payload is null or octet_length(p_payload)>2600000 then
    raise exception using errcode='P0001',message='ACS_VALIDATED_WRITE_REQUIRED';
  end if;
  begin kind:=(p_payload::jsonb)->>'kind';
  exception when others then
    raise exception using errcode='P0001',message='ACS_VALIDATED_WRITE_REQUIRED';
  end;
  if kind is null or kind not in ('revision','approval') then
    raise exception using errcode='P0001',message='ACS_VALIDATED_WRITE_REQUIRED';
  end if;
  env:=acs_private.acs_verified_backend_payload(p_payload,p_signature,kind);
  begin p_project:=(env->>'project_id')::uuid;
  exception when others then
    raise exception using errcode='P0001',message='ACS_PROJECT_ACCESS_DENIED';
  end;
  perform acs_private.acs_require_project_role(p_project,array['owner','editor']);
  -- Bind membership for this write transaction too: revocation/demotion cannot
  -- commit while an already authorized canonical write is waiting for its locks.
  perform 1 from public.acs_project_members
    where project_id=p_project and user_id=auth.uid() and role in ('owner','editor') for share;
  if not found then
    raise exception using errcode='P0001',message='ACS_PROJECT_ACCESS_DENIED';
  end if;
  doc:=env->'document';
  -- A worker is fenced by its durable lease inside the same transaction as the
  -- revision commit. Cancellation/expiry and late completion cannot both win.
  if env->'write_context' is not null and env->'write_context'<>'null'::jsonb then
    select * into lease_row from public.acs_workspace_jobs
      where id=(env->'write_context'->>'job_id')::uuid and project_id=p_project
        and created_by=auth.uid() for update;
    if not found or lease_row.state<>'RUNNING'
       or lease_row.lease_token is distinct from (env->'write_context'->>'lease_token')::uuid
       or lease_row.lease_expires_at is null or lease_row.lease_expires_at<=clock_timestamp() then
      raise exception using errcode='P0001',message='ACS_JOB_LEASE_LOST';
    end if;
    if kind<>'revision' or lease_row.expected_head is distinct from env->>'expected_head'
       or right(doc->>'note',length('task:'||lease_row.id::text)) is distinct from 'task:'||lease_row.id::text then
      raise exception using errcode='P0001',message='ACS_JOB_LEASE_LOST';
    end if;
    lease_bound:=true;
  end if;
  if kind='revision' then
    if doc->>'schema' is distinct from 'acs.plan-store-revision/1.0'
        or jsonb_typeof(doc->'model') is distinct from 'object'
        or jsonb_typeof(doc->'requirements') is distinct from 'array'
        or jsonb_typeof(doc->'locked_rooms') is distinct from 'array'
        or octet_length(doc::text)>2600000 then
      raise exception using errcode='P0001',message='ACS_INVALID_REVISION_RECEIPT';
    end if;
    saved_receipt:=acs_private.acs_save_plan_revision(p_project,env->>'expected_head',doc);
    if lease_bound then
      -- Commit the canonical revision and durable completion atomically. A lost
      -- delivery response, subsequent cancellation or lease expiry cannot turn
      -- an already persisted result into an interrupted/failed job.
      update public.acs_workspace_jobs set state='SUCCEEDED',
        revision_id=doc->>'revision_id',error_code=null,finished_at=clock_timestamp(),
        lease_expires_at=clock_timestamp(),phase='SAVING'
        where id=lease_row.id;
    end if;
    return saved_receipt;
  end if;
  if doc->>'schema' is distinct from 'acs.plan-store-approval/1.0'
      or doc->>'scope' is distinct from 'CONCEPTUAL_DESIGN_ONLY' then
    raise exception using errcode='P0001',message='ACS_INVALID_APPROVAL_RECEIPT';
  end if;
  return acs_private.acs_save_plan_approval(p_project,env->>'expected_head',doc);
end $$;
revoke all on function public.acs_write_plan_receipt(text,text) from public,anon;
grant execute on function public.acs_write_plan_receipt(text,text) to authenticated;

-- Neither legacy public wrappers nor directly invoked helpers may bypass signer.
revoke all on function public.acs_save_plan_revision(uuid,text,jsonb) from public,anon,authenticated;
revoke all on function public.acs_save_plan_approval(uuid,text,jsonb) from public,anon,authenticated;
revoke all on function acs_private.acs_save_plan_revision(uuid,text,jsonb) from public,anon,authenticated;
revoke all on function acs_private.acs_save_plan_approval(uuid,text,jsonb) from public,anon,authenticated;
revoke insert,update,delete on public.acs_plan_revisions from public,anon,authenticated;
revoke insert,update,delete on public.acs_plan_approvals from public,anon,authenticated;
-- Derived receipt provenance must not be manufactured through a direct table
-- insertion either. No current adapter writes this legacy cache table.
revoke insert,update,delete on public.acs_plan_handoffs from public,anon,authenticated;

-- Full-history legacy RPC is retired; old clients fail closed instead of issuing
-- unbounded responses. Writable workspaces are assembled from bounded reads.
revoke all on function public.acs_plan_workspace_snapshot(uuid) from authenticated;
revoke all on function acs_private.acs_plan_workspace_snapshot(uuid) from authenticated;
