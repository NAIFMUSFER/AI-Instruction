# Model review remediation — 2026-09-06

## Executive summary

The captured warehouse response reported `issues: 0` while the architecture
compiler found seven invalid walls. The API now recomputes semantic and
architecture diagnostics for the model it actually returns. Missing or failed
validation has an unknown count and cannot pass the paid live verifier.

Uncited exit, extinguisher, assembly, camera, aisle, detector, sprinkler and
electrical-height proposals are blocked. The planner exposes six unresolved
review tasks with unknown required values. Confirmation does not establish the
validity of a regulatory threshold; previously saved proposals are blocked too.

This is an incremental diagnostic and authority-boundary fix. **It does not
repair the captured model's unknown thickness, opening IDs or field provenance.**
No new paid generation, production merge or deployment was performed.

## Architectural changes and files

| Files | Change |
| --- | --- |
| `acs_engineering_authority.py` | Recompute model diagnostics inside the existing bounded CPU worker; disclose unresolved requirements; stop generating unsupported numeric proposals |
| `acs_engineering_changes.json` | Version 1.1.0; explicitly mark eight legacy changes as requiring authoritative rule sources |
| `acs_engineering_approval.py` | Reject stored unsupported proposals with `RULE_SOURCE_REQUIRED` before authoring |
| `acs_validate.py` | Remove uncited regulatory/security thresholds from automatic repair instructions; preserve geometry checks |
| `acs_understand_api.py` | Return `model_validation`, nullable `issues`, partial findings and `review_requirements` |
| `public/app/trust/core.js` | Pure Arabic/English review summary with validated counts and explicit non-evaluation |
| `public/app/ui/workspace-ui-wiring.js` | Show review state for generated models and drawing interpretation; do not label coverage-report entries as independently implemented requirements |
| `tests/deploy/verify_backend_live.py` | Require completed diagnostic scopes and zero findings for paid generation acceptance |
| `tests/remediation/test_live_generation_verdict.py` | Six additional offline failure cases, for 16 tests total |
| `tests/remediation/test_model_diagnostics.py` | Captured geometry, deterministic diagnostics, partial failures, real CPU worker and ASGI response coverage |
| `tests/remediation/test_rule_source_boundary.py` | Unknown thresholds, observed template counts and rejection of legacy/fabricated rule claims |
| `tests/remediation/test_model_review_ui.js` | Shipped Arabic/English summary behavior, invalid counters and inert provider text |
| `tests/remediation/test_engineering_authority.py` | Preserve all eight historical cases with corrected review/approval expectations; no test case disabled |
| `tests/remediation/test_event_loop.py` | Measure the actual `ea_plan_model` target including diagnostics on 4,000 rooms |
| `tests/remediation/test_privacy_boundary.py` | Inspect this function's returned compliance blocks in every branch, excluding local diagnostics and nested helpers; add nine positive/negative controls |
| `.github/workflows/ci.yml` | Add the new tests to existing required jobs |
| `README.md`, this audit | Document the API contract, gates, compatibility and remaining work |

`model_validation` uses `acs.model-diagnostics/1.0.0` and identifies the exact
returned model hash. Each validator retains its own findings; counts are findings
per validator, not necessarily unique defects. If either validator fails,
`issue_count` and API `issues` are `null`, `status` is `NOT_EVALUATED`, and
`known_issue_count` retains results from the completed scope. This is geometry
diagnostics, not proof of complete input extraction or engineering verification.

`review_requirements` contains six topics: fire exits, fire equipment, assembly,
security, circulation and electrical heights. Required values remain
`null` / `UNKNOWN`; rule sources remain empty. Observations count point records
in floor templates, not physical quantities or adequacy. The existing direct
user authoring commands remain available; these restrictions apply to the
unsupported system proposal types.

## Captured-response replay

No provider was contacted. The unchanged response from request
`req_acs_acceptance_20260906_warehouse_01` was passed through the new planner.

- Model hash before and after:
  `b245082ab521a9d1a367687d223c242aec755fca86ae85b147911d1268491ee2`.
- Semantic findings: 0; architecture findings: 7 `WALL_NEGATIVE_THICKNESS`.
- Six unresolved review tasks; one architectural proposal remains:
  `LAYOUT_SITE_EXPANSION`, unapplied. Its planning allowance is a heuristic, not
  a regulatory requirement or permission to change the user's site.
- Local replay elapsed: 2.180 ms; this is one small-model measurement, not a
  production latency guarantee.

The historical live acceptance result remains **34 passing / 6 failing**. It
has not been overwritten with a synthetic production pass. Local replay shows
the issue-reporting and deterministic recommendation boundaries are fixed;
deployment verification is still required.

## Tests executed

Python commands used the existing interpreter
`/workspace/scratch/5b03d54e3a82/acs-build-metadata-venv/bin/python` (Python 3.11).
Node was 24.19.0 locally; CI declares Node 22. The module graph check reused the
existing Playwright 1.62.1 installation after verifying identical lockfiles.
No browser executable path was hard-coded.

| Command (Python prefix as above) | Passed | Failed |
| --- | ---: | ---: |
| `python tests/remediation/test_live_generation_verdict.py` | 16 tests | 0 |
| `python tests/remediation/test_model_diagnostics.py` | 11 tests | 0 |
| `python tests/remediation/test_rule_source_boundary.py` | 9 tests | 0 |
| `python tests/remediation/test_engineering_authority.py` | 115 assertions | 0 |
| `python tests/remediation/test_api_wiring.py` | 73 assertions | 0 |
| `python tests/remediation/test_p0_hardening.py` | 57 assertions | 0 |
| `python tests/remediation/test_ci_gate.py` | 78 assertions | 0 |
| `python tests/phase9_2/test_generation_budget.py` | 74 assertions | 0 |
| `python tests/remediation/test_event_loop.py` | 63 assertions | 0 |
| `python tests/remediation/test_privacy_boundary.py` | 72 assertions | 0 |
| `node tests/lib/run.js tests/remediation/test_model_review_ui.js` | 11 assertions | 0 |
| `node tests/lib/run.js tests/remediation/test_production_error_ui.js` | 262 assertions | 0 |
| `node tests/lib/run.js tests/remediation/test_module_graph.js` | 36 assertions | 0 |
| `node tests/lib/run.js tests/remediation/test_csp.js` | 142 assertions | 0 |
| `sh tests/deploy/verify_deploy.sh` | 602 assertions; 5 injectors | 0 |
| `python3 tools/dependency_audit.py` | 109 offline checks | 0 |
| `git diff --check` | exit 0 | — |

Full Python contract run used `bash tools/ci_run.sh --runner` with the interpreter
above and these targets, in order:

```text
tests/phase8/test_bim.py                 526 passed, 0 failed
tests/phase9/test_docs.py                421 passed, 0 failed
tests/phase9_1/test_pbr.py                156 passed, 0 failed
tests/phase9_2/test_alignment.py           92 passed, 0 failed
tests/phase9_2/test_archdetail.py         168 passed, 0 failed
tests/phase9_2/test_backend_contract.py   122 passed, 0 failed
tests/phase9_2/test_black_viewport.py      87 passed, 0 failed
tests/phase9_2/test_generation_budget.py   74 passed, 0 failed
tests/phase9_2/test_live_render.py         77 passed, 0 failed
```

Aggregate: **9 suites, 1,723 assertions passed, 0 failed**. The eight parity
suites ran through `bash tools/ci_run.sh --runner node` against
`tests/phase{4,5,6,7,8,9,9_1,9_2}/test_parity.js`:
17, 35, 47, 49, 54, 72, 7 and 7 assertions respectively; **288 passed, 0 failed**.
These compare actual Python and shipped JS implementations in Node, not WebGL.

Failures encountered and fixed before publication: the first local module-graph
attempt lacked installed dependencies; after using the matching installation,
the graph check found two assertions failing due to a forward import. The fix
uses the established deferred `window.ACS.trust` interface and preserves module
evaluation order. The new UI test also initially failed through the CI bundle
runner because of a relative `require`; using `path.join(__dirname, ...)` fixed
both normal execution and the shared runner without platform-specific paths.

## Browser, CI and security evidence

CI #39, run `34014606341`, passed **11/11 jobs** for verifier-only commit
`0d45479e9e2faaf4620802eae6519988903e0ceb`, including real Chromium. That tree
matches local verifier commit `4e865f6`; it does not verify these later changes.
Remote CI for this implementation is **PENDING at document creation**.

CI #40, run `34015628216`, subsequently failed the privacy contract at published
commit `de94b567589299bfb1575886aca0d4f05ab0ec53`: **29 remediation targets passed,
1 failed**. The CVE step was skipped as a consequence and is not a pass. The
failure was reproduced locally: **60 assertions passed, 3 failed**. The AST
checker iterated over every dictionary in `_understand_payload`; a local
diagnostics dictionary overwrote the actual response's compliance block during
traversal. The real ASGI response still reported `NOT_EVALUATED`.

The checker now inspects only returned dictionaries in the function's own
scope, covers every return branch, and rejects missing, dynamic or ambiguous
compliance declarations. Nine controls cover internal dictionaries, nested
helpers, missing/changed response status, duplicate keys, unpacking, an earlier
invalid return, no response and a missing note. No application code, scanner
allowlist, workflow gate or security policy was changed to fix this failure.

Regression command after the checker correction:

```sh
bash tools/ci_run.sh \
  --log ../evidence/model-review-20260906/privacy-fix-regression.log \
  --label 'privacy return contract regression' \
  --runner /workspace/scratch/5b03d54e3a82/acs-build-metadata-venv/bin/python \
  tests/remediation/test_privacy_boundary.py \
  tests/remediation/test_model_diagnostics.py \
  tests/remediation/test_live_generation_verdict.py \
  tests/remediation/test_ci_gate.py
```

Result: **4 targets passed, 0 failed**; respectively **72 assertions, 11 tests,
16 tests and 78 assertions**, all passing. The new published commit still needs
its own required CI result; earlier green runs are not substituted for it.

**BROWSER NOT VERIFIED locally for this implementation.** The connected cloud
browser has WebGL disabled. The local `test_csp.js` suite includes checks against
a stored browser witness; its printed Chromium version is historical, not a
browser launched during this phase. Fresh Chromium/CSP evidence must come from
the required CI run. Local deployment closure did not materialize vendor assets.

No authentication, CSP, CORS, secrets, provider configuration or billing settings
were changed. The API does not return compiler exception text; invalid UI counts
and provider labels cannot become HTML. CPU diagnostics retain the existing
queue/time limits. The event-loop probe does not test FastAPI routing; Redis
distributed enforcement was **NOT VERIFIED locally** because redis-server is not
installed. CVE/secret scanning for the new commit is a required remote CI gate;
the local dependency audit establishes lock consistency only.

On the 4,000-room probe the synchronous planner plus diagnostics took 2,312 ms.
The measured event-loop stall was 2,235.6 ms synchronously and 37.4 ms through
the worker; the longest lightweight request was 44.4 ms through the worker.
The existing limits (250 ms stall / 500 ms lightweight request) were unchanged.

## Known issues and unverified items

- Unknown wall thickness remains zero in the captured response. Missing global
  dimensions can still be filled by legacy defaults; a compatible migration
  across generation, authoring, compilers, drawings and exports is still needed.
- Raw opening IDs and inferred offsets still need persistent IDs and field-level
  provenance. No inference has been relabeled as a confirmed engineering fact.
- The legacy generation prompt and local layout heuristics are not an
  authoritative regulatory subsystem. No jurisdiction/rule applicability or
  regulatory compliance has been established.
- The actual generated model has not been verified in a real 3D browser, nor
  through UI editing, undo/redo, export or browser reload persistence.
- Server-side authenticated project persistence and provider invoice totals
  remain unverified. The prior P0 suite still reports a pre-parser multipart
  body-size limitation; this phase does not close it.

## Deployment status, next actions and definition of done

Production remains the previously deployed `ca2f98a` release. Publication is to
draft PR #6 only. **PRODUCTION VERIFICATION PENDING**. Merge/deploy approval is
required after reviewing the final commit and its required CI results.

Next: verify the published tree and CI, then implement a compatible uncertainty
and stable-identity contract using the captured fixture. Do not spend another
paid generation without separate authorization. This phase is ready for review
when the implementation and regressions above pass, required CI passes for the
published tree, and the remaining product limitations stay explicit. Production
completion additionally requires verifying the approved deployed commit.
