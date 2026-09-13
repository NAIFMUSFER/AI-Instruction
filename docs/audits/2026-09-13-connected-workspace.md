# ACS connected project workspace

Continuation from PR94, integrated with PR93 on main
`638053271273f8c2f929e7f3f236d9e7b46d4843`.
The previous acceptance report records that earlier release, not this change.

## Delivered implementation

- Password recovery and confirmation resend use a server-pinned callback URL.
  Email callbacks are stripped from the address bar before asynchronous work,
  verified through GoTrue and, for recovery, enter a separate new-password form.
  No account is confirmed or impersonated by an administrator. A generic recovery
  receipt does not claim that an email was delivered or that an account exists.
- Four-stage Arabic responsive workspace: confirmed project brief and measured
  requirements; one explicitly requested A/B/C alternative; 2D room edits,
  persisted locks, history, comparisons and conceptual approval; exact approved
  3D and exports. Production enters an empty authenticated project without a demo.
- Projects can be created, selected and reopened. User/project-scoped local
  storage retains only the unsent brief and pending job identifier for this flow.
- Initial generation and chat edits run in the existing isolated runner.
  The canonical parent reloads the head before and after the worker. Optimistic
  writes and existing room/semantic locks prevent a stale or conflicting result
  from replacing the saved revision. Approved baselines are retained.
- A bounded provider-call context stops before exceeding the chosen ceiling
  (1–12; UI presets 3/6/12). SDK retries are disabled in this context so hidden
  transport retries cannot exceed it. No panel opening creates a paid request.
- `acs_workspace_jobs` retains an idempotent receipt for each submitted job.
  Reopening polls the same job. A server restart reports unfinished work as
  interrupted and does not automatically resubmit it. Completed canonical
  revisions remain durable even if the final job-status update fails.
- SVG/DXF/PDF describe schematic space boundaries; IFC4 describes spaces.
  glTF is compiled deterministically from the exact approved baseline with
  provenance, explicit-geometry guards and no new provider call. The browser
  displays those bytes without running the old renderer's geometry defaults.

## Verification and activation

Local validation includes the real temporary SQLite lifecycle for residential
and warehouse fixtures: generation admission, room lock, approval, all five
artifact formats, new draft and reopening the old approved baseline. Actual HTTP
routes also passed authenticated generation, job polling, review, approval and
glTF retrieval with a controlled identity/provider.

Auth gateway and browser-controller tests cover recovery, selected project
denial, account switching and password clearing. Required GitHub CI runs the
complete shipped page under the production CSP in Chromium at 393 and 1280 px,
including reload without duplicate generation, lock, approval, SVG download,
exact 3D, chat revision, comparison and logout. These fixtures are never deployed.
CI status and deployed commit identity must be recorded before release approval.

The `acs_workspace_jobs` migration was applied to the ACS Supabase project on
13 September 2026. Metadata inspection verified RLS, three policies, no anonymous
read and no client delete grant. The advisor found no new table-policy issue.
The existing Auth setting for leaked-password protection is disabled; see
[Supabase password protection](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

For email callbacks, set Supabase Auth Site URL and its redirect allowlist to
`https://sprightly-selkie-d906c3.netlify.app/`. The gateway defaults to that URL;
another canonical host requires `ACS_AUTH_SITE_URL` on Render and the same
allowlisted URL in Supabase. This release does not change SMTP or manually alter
account records. Actual confirmation/recovery email delivery and a successful
owner sign-in still require live acceptance; local tests do not prove them.

## Scope of acceptance

The connected flow is usable for schematic review; it does not establish that
every requirement in Design Pipeline v2 is finished. Full architectural wall and
opening drawings, shared-wall/CAD and native Autodesk acceptance, automatic
source-span extraction/clarification, office Design DNA, and real owner-generated
residential/warehouse output acceptance remain separate work. Regulatory and
structural results remain NOT_VERIFIED. Never label these space-boundary exports
as full construction documents or mark the complete product issue closed from
controlled fixture tests alone.
