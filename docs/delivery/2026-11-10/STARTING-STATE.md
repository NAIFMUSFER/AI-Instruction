# Delivery starting state — 10 November 2026

Repository: NAIFMUSFER/AI-Instruction. Integration owner: Codex, for Naif.

Fresh checkout: `c37b5250dc4ff18ba0606add993b5afe52beebaa`, default branch `main`, initially clean working tree, 893 tracked files. No tracked AGENTS.md was found, and the root GitHub contents query returned 404. The user-supplied task instructions apply. The unrelated MASAR branches were not selected or overwritten.

Netlify site `74951b97-7411-476c-9261-0cb243afe45c`, production deploy `6af21a9487b8d19c260b9896`, state ready, reports the same full commit. Backend `/version` independently returned the same full commit with verified build provenance. PR187 is merged; its guest work and dependency fixes are part of this starting tree. The supplied audit bundle's delivery-status file was read, not assumed.

PR182–186 remain open at discovery. See PR-RECONCILIATION.md for actual heads, changed files, red/green regression evidence and selected integration boundaries. No bulk merge is authorized by this record.

GitHub's main branch metadata reported `protected: false` and no required checks. Recommended policy: require the aggregate `CI required` and delivery critical-boundary check, require branch up-to-date and resolution of review discussions, disallow force-push/deletion. This is a proposal, not an applied repository administration policy; available GitHub connector write operations do not expose branch-protection administration.

## Observed limits and blockers

The current Supabase connection lists five projects. Metadata-only checks found no public ACS tables in any of them; no project data or user records were read. The actual production ACS database identity and migration state are therefore **NOT VERIFIED**, not inferred from source migrations. No production migration has been applied.

The production Google-start gateway returned HTTP503 with `AUTH_UPSTREAM_UNAVAILABLE`. No account was created and no real-user credential was used. Root cause is not established from this response.

The cloud browser opened the public guest URL without registration and verified interactive selection in the explicitly labeled 2D fallback. This browser did not support the application's WebGL path. A separate local Chromium launch was attempted and failed at process singleton socket creation (`Operation not permitted`); this is an executor limitation, not a website pass or failure. Real browser evidence must come from the CI environment. No physical iPhone, Safari, Revit or live paid-generation claim is made.

## Runtime journey and authority map

| Stage | Actual executing modules | Authority and boundary |
|---|---|---|
| Public entry | index shell, auth-session/guest-workspace, boot entry | Explicit guest storage namespace; no account/provider request |
| Brief or local source | brief-program, brief-review, plan-upload; workspace HTTP/service | Unconfirmed or inferred input remains identified |
| Requirements and generation | workspace HTTP, workspace service, provider budget, understand/provider, residential/warehouse policies | Verified actor, expected head, confirmation, bounded operation |
| Canonical revision | plan review, store, lock binding, persisted commands | Immutable canonical model and requirement/provenance receipts |
| Review/edit/locks | connected workspace, plan review packet, semantic locks/diff | Stale-head rejection; derived preview never becomes authoring state |
| Conceptual approval | plan review + lock binding + store approval | Approval binds selected revision/hashes; no engineering certification |
| Derived outputs | plan handoff, compiler, CAD/PDF/IFC exporters, approved viewer | Exact approved source identity; honest output capability limits |
| Save and reopen | authenticated Supabase adapter + reload; guest persistence separately | Role-bound cloud history; local guest snapshot remains local |

The legacy guest compiler/viewer and the connected approved-artifact viewer are distinct entry paths. Enhancing only the former does not prove improvement in the latter. Dependency ownership and generated outputs are recorded per path in file-coverage.csv.
