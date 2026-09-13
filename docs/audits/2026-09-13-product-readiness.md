# ACS product acceptance — 13 September 2026

This review started from production `main` commit
`01cc7805be20ddf9931f31d9a7dec5c10e1698d8`, after PRs 90, 91 and 92 were merged.
Both the repository and Render `/version` identified that commit. Render `/ready`
returned 200. These observations establish service/version availability, not a
successful authenticated generation or completion of the product specification.

## Completed in this change

- Separate sign-in, sign-up and first-project onboarding. Existing accounts enter
  with email/password; a new account names its first project after authentication.
- Project onboarding reuses the authenticated session instead of resending a password.
- Password visibility control, password clearing after successful authentication,
  accessible live errors, mobile sizing and a scrollable login on short displays.
- Hide workspace controls before entry. Production no longer inserts an example
  building on successful login; examples remain explicit user actions.
- Bounded auth requests, one concurrent refresh, duplicate-submit protection,
  retry after transient outages without deleting the session, and prevention of
  a late refresh resurrecting a signed-out account. Credential requests remain
  on the configured backend even if the model-server override changes.
- A changed account or sign-out in another tab reloads the old workspace.
- Account/project-specific local model backups and recovery. Unscoped historical
  local records are preserved, but never automatically assigned to a new account.
- Pending generation recovery is scoped to the account/project that submitted it.
- Gateway errors distinguish upstream outages from rejected authentication and
  first-project requirements. Malformed project lists do not create duplicates.
- Privacy copy now describes accounts, local design versions and temporary results.
  Its stylesheet is external so it works under the existing strict production CSP.
- Regression coverage in the existing required Async delivery workflow, including
  the complete shipped page on desktop and mobile with a controlled auth service.

## Acceptance evidence and its limits

The focused auth controller, gateway, async delivery client, local persistence,
authenticated Plan HTTP and Supabase verifier tests run without production user
credentials. The shipped-page test uses real Three.js/browser rendering and a
controlled auth service; it is not evidence that a real owner signed in to Supabase.
Full CI and deployed preview must be checked on the final head before merging.

The production logs include sign-in/sign-up 503 responses at 08:20–08:34 UTC,
before a later deployment/configuration change. Current health reports Supabase
authentication configured. No production account was created or impersonated in
this change, and no paid generation was submitted.

## Product work that is still open

| Requirement | Observed implementation | Remaining acceptance |
| --- | --- | --- |
| Real account lifecycle | Gateway, refresh, verified project bootstrap, UI | Owner account sign-in, email confirmation and logout against live Supabase; password recovery is not yet implemented |
| Four-stage connected plan workspace | `/plan-review/` imports local review packets; explicitly read-only | Connect requirements, options, edit/lock/approval and saved revisions to the authenticated project service |
| Initial durable plan revision | PlanStore and authenticated command services exist | No browser-connected first-revision/generation handoff; an empty project cannot enter the review/edit lifecycle |
| Cloud model save/reopen | Durable server store exists; studio buttons save locally | Connect explicit cloud save, project selection and cross-device reopen; retain the local backup separately |
| Approved baseline to 3D/export | Audited offline baseline/export helpers and browser renderers exist | Connect exact approved baseline lookup and artifact delivery; do not bypass the existing approval boundary |
| Structured brief and A/B/C options | Typed provenance/metrics and comparison foundations exist | Complete the user-facing confirmation, option-generation budget and measured comparison flow |
| Full 2D/CAD presentation | Current review view draws space rectangles | Connect explicit walls/openings/equipment and CAD/IFC/PDF acceptance; do not describe space boundaries as full construction drawings |
| Durable generation recovery | Process-memory results, 30-minute retention | Recovery across server restart, durable job storage and tested backup/restore |
| Final product release | CI covers individual contracts and controlled UI flows | One real residential and one warehouse journey from brief through save/reopen and approved exports, including physical mobile acceptance |

The current `/plan-review/index.html` states that editing, locks, approval and 3D
are not activated in that interface. `acs_plan_http.py` exposes review, locks,
compare, restore, approve and chat-edit commands, but no initial generation,
initial-revision save or approved-artifact route. These are integration gaps,
not gates that can be closed by renaming a draft or rerunning existing tests.

Do not call this a final commercial release, close the full product issue, or
label unknown engineering/regulatory metrics as passed based on this change.
