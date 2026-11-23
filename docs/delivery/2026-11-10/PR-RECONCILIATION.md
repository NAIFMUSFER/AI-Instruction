# PR reconciliation — 2026-11-10

Read-only review; no PR merged, ref moved, or shared repository source changed by this specialist. Repository root `AGENTS.md` returned 404 and no tracked AGENTS.md was found. Metadata/diffs came from GitHub connector and local fetched refs. Current main tested: `c37b5250dc4ff18ba0606add993b5afe52beebaa`. All reviewed PRs still target their `adec616aa5191315991fb9439cee83efbb719b8f` base and are OPEN/unmerged.

| PR | Exact head | GitHub mergeable observation | Recommendation |
|---|---|---|---|
| 182 | 78374061fda33851cc6a7317bcd8c0053818047e | false | Retain as dated architecture reference; no production move needed. |
| 183 | 987e9a7c779af30cd64938f20ce1b0e45715f390 | true | Selectively integrate provider accounting, disjoint warehouse policy and explicit Arabic role normalization with their tests. |
| 184 | 7fd39d8721872d6589c7b9a69aaf64f26878068d | true | Selectively integrate opening validation, conservative reciprocal door pairing and honest vertical coverage with tests. |
| 185 | d95c5713cd20c09de82f14ecf9045f50c700c91a | false | Selectively port parser, labels/focus, traversal disclosure and lazy module ownership guards; preserve guest changes. |
| 186 | 418ba0c7902f56d39f728219981451bb88a8e8f1 | true | Retain as historical audit evidence; application source unchanged. |

GitHub mergeable is an observation, not release approval. Exact-head workflow API returned completed/success workflows for every PR (first-page, PR-triggered API scope only). Netlify deploy-preview status is success for all five. Dedicated audit workflow IDs: #183 `36273466352`, #184 `36274363314`, #185 `36273930873`. No production deployment inferred from previews or PR CI.

## Changes and integration boundaries

183 fixes a started stream's internal AttributeError triggering another paid create call. The new code resolves stream availability before spending, then spends exactly once immediately before the chosen transport. Repair telemetry is carried through successful and malformed repair responses. This does not centralize paid admission, enforce monetary limits, or fix worker leases. Warehouse policy forbids double-counting a whole envelope as an occupied zone and keeps operational zones open. Explicit Arabic role allowlist normalizes roles without changing names or geometry; role-only resumes retain completed details. All role/general layout logic still requires wider integration tests.

184 validates finite positive opening dimensions and valid edges, uses explicit wall/opening heights, checks single-room door/window overlap and actual aperture spans against partially adjacent rooms. Reciprocal leaf meshes merge only exact opposite-edge, distinct-room, same-floor, same-dimension/center/material/semantics matches; both source records survive in glTF extras. No rounding-based deduplication. Vertical coverage only reports declared dimensioned core objects and explicitly keeps physical traversal NOT_VERIFIED. It does not build real stairs, guarantee apertures, repair elevations/rotation/areas, or turn connected IFC into full BIM.

185 supports a narrow set of explicit Arabic bedroom number words and single-storey phrases, preserves Unicode source spans, asks about unitless dimensions, and rejects compound/conditional quantities. Adds focus transfer/return for nonmodal legacy panels and generated architectural labels. Connected/review tables distinguish core alignment from physical traversal. Preserve the source generator and generated markup together. The newly released guest workspace was absent from this PR's base; never replace entire current files with old head copies. Panel/browser tests are validated by prior exact-head GitHub CI; this specialist locally ran logic checks, not Chromium.

182 measures imports, late-bound frontend dependencies and exhaustive scoped move mapping. It explicitly recommends retaining layout. 186 consolidates dated observations including failed live generations and calculated fallbacks; these are historical, not today's live outcome. All five contain duplicate BASELINE.md and baseline harness/results; do not merge them wholesale into a new rolling status document.

## Exact changed files

182: `BASELINE.md`, `STRUCTURE-PROPOSAL.md`, `docs/audit/2026-09-26/baseline-results.json`, `docs/audit/2026-09-26/measure_structure.py`, `docs/audit/2026-09-26/run_baseline.py`.

183: `.github/workflows/acs-audit-backend.yml`, `BACKEND-AUDIT.md`, `BASELINE.md`, `Dockerfile`, `acs_residential_generation.py`, `acs_understand.py`, `acs_warehouse_generation.py`, `acs_workspace_service.py`, `docs/audit/2026-09-26/baseline-results.json`, `docs/audit/2026-09-26/run_baseline.py`, `tests/remediation/test_audit_backend_corpus.py`, `tests/remediation/test_audit_backend_provider.py`, `tests/remediation/test_audit_backend_residential_roles.py`, `tests/remediation/test_audit_backend_warehouse_policy.py`, `tests/remediation/test_workspace_recovery.py`.

184: `.github/workflows/acs-audit-engineering.yml`, `BASELINE.md`, `ENGINEERING-AUDIT.md`, `acs_compiler.py`, `acs_plan_bridge.py`, `acs_plan_review.py`, `acs_validate.py`, `docs/audit/2026-09-26/baseline-results.json`, `docs/audit/2026-09-26/run_baseline.py`, `tests/remediation/test_audit_engineering_door_meshes.py`, `tests/remediation/test_audit_engineering_openings.py`, `tests/remediation/test_audit_engineering_vertical_coverage.py`.

185: `.github/workflows/acs-audit-frontend.yml`, `BASELINE.md`, `FRONTEND-AUDIT.md`, `KNOWN-ISSUES.md`, `docs/audit/2026-09-26/baseline-results.json`, `docs/audit/2026-09-26/run_baseline.py`, `public/app/core/brief-program.mjs`, `public/app/ui/connected-workspace.mjs`, `public/app/ui/panels-entry.js`, `public/index.html`, `public/plan-review/review.mjs`, `tests/phase6/test_security.js`, `tests/phase7/test_security.js`, `tests/remediation/test_audit_frontend_brief.mjs`, `tests/remediation/test_audit_frontend_guards.js`, `tests/remediation/test_audit_frontend_panels.js`, `tests/remediation/test_audit_frontend_vertical.cjs`, `tools/build_archdetail_browser.py`.

186: `BASELINE.md`, `CUSTOMER-REVIEW.md`, `FINDINGS.md`, `docs/audit/2026-09-26/audit_guard_mutations.py`, `docs/audit/2026-09-26/baseline-results.json`, `docs/audit/2026-09-26/guard-verification.md`, `docs/audit/2026-09-26/run_baseline.py`.

## Fresh local regression evidence

Isolated git-archive copies of each exact PR head were tested. An isolated exact current-main archive received only these regression test files; its production sources remained unchanged. These tests make mocked/synthetic provider calls, not paid requests. Commands and logs are under sibling `logs/` and the two JSON command manifests.

| Suite | Current main exit | Respective PR head result |
|---|---|---|
| test_audit_backend_provider.py | 1 (6 failures / 1 error) | 10 tests pass |
| test_audit_backend_warehouse_policy.py | 1 (2 failures) | 6 tests pass |
| test_audit_backend_residential_roles.py | 1 (4 failures / 182 errors) | 14 tests pass |
| test_audit_engineering_openings.py | 1 (22 failed subcases / 4 errors) | 20 tests pass; separate mutation run kills 14 |
| test_audit_engineering_door_meshes.py | 1 (3 failures / 2 errors) | 12 tests pass; separate mutation run kills 11 |
| test_audit_engineering_vertical_coverage.py | 1 (27 errors) | 15 tests pass; separate mutation run kills 10 |
| test_audit_frontend_brief.mjs | 1 | 21 checks pass (includes 13 mutation controls) |
| test_audit_frontend_vertical.cjs | 1 | 24 checks pass (includes 12 mutation controls) |
| test_audit_frontend_guards.js | 1 | 12 checks pass |

Important: baseline errors from absent proposed helpers/coverage keys or mutation anchors are not independent product defects. The concrete behavioral failures (duplicate calls, missing policy, invalid openings, duplicate mesh, missing labels/parser behavior) are identified separately in source review. No claim of a complete test replay, live provider success, physical-device testing, or full semantic review of the audit reports.
