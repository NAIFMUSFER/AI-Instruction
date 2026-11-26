-- Let the member who uploaded a plan source delete it. NOT APPLIED BY THIS
-- BRANCH: the general manager applies it. Until then the engine refuses a
-- delete with «تعذّر حذف الملف الآن؛ لم يُحذف شيء» and nothing is removed.
--
-- Storage layout (acs_plan_sources.py): a page preview lives at
-- <project>/<source id>/preview; an original is shared by identical uploads in
-- the project at <project>/<first 32 hex of its sha256, as a uuid>/original.
-- Sources saved before this layout keep <project>/<source id>/original.

grant delete on public.acs_plan_sources to authenticated;

-- A source row: only its uploader, and only while still an owner or editor of
-- the project. Viewers and other members cannot delete someone else's file.
create policy acs_plan_sources_delete_own on public.acs_plan_sources
for delete to authenticated
using (created_by = (select auth.uid())
  and exists (select 1 from public.acs_project_members m
    where m.project_id = acs_plan_sources.project_id and m.user_id = (select auth.uid())
    and m.role in ('owner','editor')));

-- A stored object: only once no source row of its project refers to it, by
-- source id (a preview or an older original) or by content hash (a shared
-- original). So deleting one page never removes a file other pages still use.
create policy acs_plan_source_objects_delete_unreferenced on storage.objects
for delete to authenticated
using (bucket_id = 'acs-plan-sources'
  and name ~ '^[0-9a-f-]{36}/[0-9a-f-]{36}/(original|preview)$'
  and exists (select 1 from public.acs_project_members m
    where m.project_id::text = (storage.foldername(name))[1] and m.user_id = (select auth.uid())
    and m.role in ('owner','editor'))
  -- objects.name is qualified: acs_plan_sources has its own "name" column.
  and not exists (select 1 from public.acs_plan_sources s
    where s.project_id::text = (storage.foldername(objects.name))[1]
    and ((storage.foldername(objects.name))[2] = s.id::text
      or (storage.foldername(objects.name))[2] = (substr(s.sha256, 1, 32))::uuid::text)));
