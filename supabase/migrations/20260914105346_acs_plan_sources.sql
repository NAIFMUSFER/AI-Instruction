-- Originals and page previews are private, immutable project inputs.
insert into storage.buckets(id, name, public, file_size_limit, allowed_mime_types)
values ('acs-plan-sources', 'acs-plan-sources', false, 5242880,
        array['application/pdf','image/png','image/jpeg','image/webp'])
on conflict (id) do nothing;

create table public.acs_plan_sources (
  id uuid primary key,
  project_id uuid not null references public.acs_projects(id) on delete cascade,
  created_by uuid not null default auth.uid() references auth.users(id),
  name text not null check (length(name) between 1 and 200),
  media_type text not null check (media_type in ('application/pdf','image/png','image/jpeg','image/webp')),
  byte_size integer not null check (byte_size between 1 and 5242880),
  sha256 text not null check (sha256 ~ '^[a-f0-9]{64}$'),
  page integer not null check (page > 0),
  page_count integer not null check (page_count between 1 and 200 and page <= page_count),
  preview_sha256 text not null check (preview_sha256 ~ '^[a-f0-9]{64}$'),
  preview_media_type text not null check (preview_media_type in ('image/png','image/jpeg','image/webp')),
  created_at timestamptz not null default now()
);
alter table public.acs_plan_sources enable row level security;
revoke all on public.acs_plan_sources from public, anon, authenticated;
grant select, insert on public.acs_plan_sources to authenticated;
create index acs_plan_sources_project_created on public.acs_plan_sources(project_id,created_at desc);
create index acs_plan_sources_creator on public.acs_plan_sources(created_by);
create policy acs_plan_sources_read on public.acs_plan_sources for select to authenticated
using (exists (select 1 from public.acs_project_members m
  where m.project_id=acs_plan_sources.project_id and m.user_id=(select auth.uid())
  and m.role in ('owner','editor','viewer')));
create policy acs_plan_sources_insert on public.acs_plan_sources for insert to authenticated
with check (created_by=(select auth.uid()) and exists (select 1 from public.acs_project_members m
  where m.project_id=acs_plan_sources.project_id and m.user_id=(select auth.uid())
  and m.role in ('owner','editor')));

create policy acs_plan_source_objects_read on storage.objects for select to authenticated
using (bucket_id='acs-plan-sources' and exists (select 1 from public.acs_project_members m
  where m.project_id::text=(storage.foldername(name))[1] and m.user_id=(select auth.uid())
  and m.role in ('owner','editor','viewer')));
create policy acs_plan_source_objects_insert on storage.objects for insert to authenticated
with check (bucket_id='acs-plan-sources'
  and name ~ '^[0-9a-f-]{36}/[0-9a-f-]{36}/(original|preview)$'
  and exists (select 1 from public.acs_project_members m
    where m.project_id::text=(storage.foldername(name))[1] and m.user_id=(select auth.uid())
    and m.role in ('owner','editor')));
-- No UPDATE/DELETE policies: an imported source cannot be replaced in place.
