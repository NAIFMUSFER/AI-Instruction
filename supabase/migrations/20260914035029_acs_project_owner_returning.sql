-- INSERT ... RETURNING checks SELECT visibility before the AFTER INSERT
-- owner-membership trigger runs. Owner access must not depend on that row yet.
-- Keep membership-based access for collaborators and existing INSERT ownership checks.
alter policy acs_projects_select_member on public.acs_projects
  using (owner_id = (select auth.uid())
    or acs_private.acs_has_project_role(id, array['owner','editor','viewer']));
