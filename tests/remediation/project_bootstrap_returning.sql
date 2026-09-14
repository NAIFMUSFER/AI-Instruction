-- Run through an administrative SQL connection against the migrated ACS schema.
-- Synthetic identities and project writes are rolled back; no real user is impersonated.
begin;
create temporary table acs_bootstrap_probe_result(result jsonb);
grant insert,select on acs_bootstrap_probe_result to authenticated;
insert into auth.users(id,aud,role) values ('e38e55f8-8efe-4c94-8f40-4d1e0c90c755','authenticated','authenticated');
select set_config('request.jwt.claim.sub','e38e55f8-8efe-4c94-8f40-4d1e0c90c755',true);
set local role authenticated;
do $$ declare p uuid; begin
  insert into public.acs_projects(owner_id,name)
  values (auth.uid(),'ACS rollback-only bootstrap verification') returning id into p;
  if not exists(select 1 from public.acs_project_members where project_id=p and user_id=auth.uid() and role='owner') then
    raise exception 'owner membership missing';
  end if;
  if not exists(select 1 from public.acs_projects where id=p) then
    raise exception 'owner cannot reload project';
  end if;
  perform set_config('request.jwt.claim.sub','79c7d37a-6b81-4015-a2af-654f551ca2de',true);
  if exists(select 1 from public.acs_projects where id=p) then
    raise exception 'unrelated principal can read project';
  end if;
  insert into acs_bootstrap_probe_result values(jsonb_build_object('created',true,'owner_membership',true,'reload',true,'unrelated_read_denied',true));
end $$;
reset role;
select result from acs_bootstrap_probe_result;
rollback;
