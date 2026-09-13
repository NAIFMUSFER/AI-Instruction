-- Harden ACS SECURITY DEFINER helpers by moving them out of the exposed public schema.
-- Policies/triggers keep their dependencies on the same function OIDs after ALTER FUNCTION SET SCHEMA.

create schema if not exists acs_private;
revoke all on schema acs_private from public, anon;
grant usage on schema acs_private to authenticated;

alter function public.acs_has_project_role(uuid,text[]) set schema acs_private;
alter function public.acs_is_project_owner(uuid,uuid) set schema acs_private;
alter function public.acs_seed_owner_membership() set schema acs_private;
alter function public.acs_guard_membership_mutation() set schema acs_private;

revoke all on function acs_private.acs_has_project_role(uuid,text[]) from public, anon;
revoke all on function acs_private.acs_is_project_owner(uuid,uuid) from public, anon;
revoke all on function acs_private.acs_seed_owner_membership() from public, anon, authenticated;
revoke all on function acs_private.acs_guard_membership_mutation() from public, anon, authenticated;

grant execute on function acs_private.acs_has_project_role(uuid,text[]) to authenticated;
grant execute on function acs_private.acs_is_project_owner(uuid,uuid) to authenticated;
