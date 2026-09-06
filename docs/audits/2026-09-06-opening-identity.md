# Persistent opening identity — implementation audit, 2026-09-06

## Executive summary and current-state audit

Base: `9f574d806ba11844368e5d016c1961d2c09c978e` (`main`, PR6). A clean isolated worktree was created before editing. The baseline command suite passed 188 assertions. A separate reproduction showed that deleting door 0 made its former positional reference resolve to the next door. Existing geometry, relationships, navigation and BIM projections also reconstructed opening IDs from array position.

This phase fixes that bounded lifecycle defect. It does not establish full engineering acceptance. The prior warehouse generation still has unresolved unknown thickness and unsupported offset provenance. No paid provider call was made in this phase.

## Gap analysis, target architecture and implementation phases

1. Persist door/window source `id` values in canonical records. Compiler instance references append `@level index`; repeated templates deliberately share a source identity.
2. Preserve existing legacy projects on load. Before their first opening mutation, migrate a candidate copy, freeze positional IDs, and record the migration paths in the same authoring revision. Preview, rejection, cancellation and historical revision snapshots remain unchanged.
3. Use deterministic command/model hashes plus the persisted `_opening_identity.next` sequence for newly authored IDs. The `acs.opening-identity/1` marker prevents missing IDs from silently reverting to array positions.
4. Resolve authoring, architecture, relationships, egress/distance, inspector hosts, layout proposals and BIM exchange through source IDs. Validate identities on admission, authoring, project load and BIM exchange export.
5. Next phase: design a compatible first-class unknown/provenance contract, then migrate its consumers. Do not replace `wall_t: 0` with an invented engineering number.

## Files and architectural changes

- `acs_opening_identity.py`: independent shared identity validation/migration; no UI or AI dependency.
- `acs_authoring.json`, `acs_authoring.py`: versioned identity contract, deterministic allocation, exact resolution, locks, revision paths, integrity and load validation.
- `acs_understand.py`: admission migration and provider-edit marker/missing-ID rejection.
- `acs_arch.py`, `acs_bim.py`, `acs_distance.py`, `acs_egress.py`, `acs_relations.py`, `acs_layout.py`, `acs_workspace.py`: consume canonical source IDs, reject missing distance references, match the selected opening's host.
- `public/app/core/standards.js`, `public/app/core/viewer.js`: compiler and navigation mirrors.
- `tools/build_authoring_browser.py`, `tools/build_bim_browser.py`, `tools/build_workspace_ui.py` and their three `public/app/generated/` outputs: shipped JS parity. The BIM module imports the exported identity validator explicitly.
- `Dockerfile`: includes the independent identity module needed by model admission.
- `.github/workflows/ci.yml`: new Python, Node, parity and required real-Chromium regressions.
- Three `tests/remediation/test_opening_identity*` files, this audit and README: evidence and compatibility documentation.

Legacy BIM exchange IDs retain their old format until migration; migrated exports use `sourceID@level`. This is an intentional versioned source-identity transition, not a promise that existing IFC GlobalIds remain constant across every revision.

## Security changes and plan

Reject duplicate IDs (including implicit legacy identities), reserved aliases/projection namespaces, malformed identities and unsupported migration markers. A level-suffixed target cannot bypass its source lock. Broken migrated identity blocks project import and BIM exchange export. Missing navigation references cannot select an anonymous legacy door. No secrets, CSP exceptions, CORS changes or dependency changes were introduced.

The first deployment-closure run exposed an inappropriate import of authoring/UI configuration from backend admission (600 pass, 4 fail). Extracting the independent shared module and explicitly copying it into Docker fixed the dependency root cause; no closure check was bypassed.

## Tests executed and exact local results

Environment: Node 24.19.0; Python from `/workspace/scratch/5b03d54e3a82/acs-build-metadata-venv/bin/python`. CI independently uses Node 22 and Python 3.11. Commands below ran from the worktree. Logs are preserved separately. Assertion totals and suite-target totals are different measures and are not summed as unique test coverage.

```sh
bash tools/ci_run.sh --log ../opening-release-authoring.log --label 'opening identity authoring' --runner 'node tests/lib/run.js' tests/phase5/test_authoring.js tests/phase5/test_commands.js tests/phase5/test_transaction.js tests/phase5/test_revision.js tests/phase5/test_ai_boundary.js tests/phase5/test_integration.js tests/phase5/test_immutability.js tests/phase5/test_adversarial.js tests/phase5/test_browser.js tests/remediation/test_opening_identity.js
bash tools/ci_run.sh --log ../opening-release-parity.log --label 'opening identity parity' --runner node tests/phase4/test_parity.js tests/phase5/test_parity.js tests/phase6/test_parity.js tests/phase7/test_parity.js tests/phase8/test_parity.js tests/phase9/test_parity.js tests/phase9_1/test_parity.js tests/phase9_2/test_parity.js tests/remediation/test_opening_identity_parity.js
bash tools/ci_run.sh --log ../opening-release-python-corrected.log --label 'opening identity Python corrected targets' --runner /workspace/scratch/5b03d54e3a82/acs-build-metadata-venv/bin/python tests/remediation/test_opening_identity.py tests/remediation/test_model_diagnostics.py tests/remediation/test_plan_chunking.py tests/remediation/test_engineering_authority.py tests/remediation/test_ci_gate.py tests/security/test_security.py tests/phase8/test_bim.py tests/phase9/test_docs.py
sh tests/deploy/verify_deploy.sh
node tests/lib/run.js tests/remediation/test_module_graph.js
npx playwright install chromium
```

| Check | Exact result |
| --- | --- |
| Authoring | 10 targets pass / 0 fail; assertions per target: 127,188,120,89,67,70,107,519,55,36 |
| Cross-language parity | 9 targets pass / 0 fail; existing parity assertions 17,35,47,49,54,72,7,7; opening snapshot comparison 1/0 plus JS 36/0 |
| Python | 8 targets pass / 0 fail; identity 17 tests, diagnostics 11 tests; assertions: plan 72, authority 115, CI gate 78, security 377, BIM 526, documentation 421; all 0 fail |
| Deployment closure | 605 pass / 0 fail; 5 injectors regenerated, 0 failed |
| Module graph | 36 pass / 0 fail |
| Chromium installation | Exit 1: five download timeouts; no local browser executed |

One Python runner command incorrectly named `tests/phase9/test_documents.py`: 7 targets passed, 1 target failed to start (exit 2, missing file). The corrected command above uses the actual `test_docs.py` and passes all 8 targets. Earlier attempts referencing nonexistent `test_authoring.py` and `test_backend_config.py` also did not execute tests. An initial identity snapshot comparison exposed a test-locale mismatch (JS default Arabic versus Python English); explicit English comparison fixed that mismatch, preserving production language behavior. Partial logs without a terminal suite summary are not counted as verified runs.

## Browser verification and CI status

Local: **BROWSER NOT VERIFIED**. Chromium download timed out; Node execution of a file named `test_browser.js` is not browser evidence. The new identity test is wired into the required Playwright-managed Chromium job. Runtime CSP, responsive/accessibility and complete CI results must be read from the new commit's own run; PR6 evidence cannot validate this code. CI status at preparation: **PENDING**.

## Known issues and unverified items

- Unknown thickness and inferred placement provenance remain unresolved. No regulatory authority was added: **NOT EVALUATED**.
- AI edits reject a missing marker or missing/duplicate IDs, but do not yet prove that the provider preserved every retained object's semantic identity or obeyed every requested edit. No paid provider or live generation acceptance was rerun.
- Stable identity is scoped to doors/windows. Other canonical/derived object identity contracts need separate audits.
- Production persistence, authorization, durability and large-project performance are not established by this patch.
- Local Chromium, Windows-native execution, new image deployment and live geometry are **NOT VERIFIED** for this phase.
- `main` branch protection was reported disabled by GitHub at audit time. A required aggregate CI job exists, but platform-level merge enforcement is not configured. No repository settings were changed.

## Deployment plan, next actions and definition of done

Publish a focused draft PR and verify its exact head/tree and all required CI jobs, including actual Chromium identity execution and runtime CSP. Resolve any failure at its root. Request approval for merging this new migration only after a reviewable green result; `main` auto-deploys, so merging has production impact.

After authorized merge, verify fresh CI, deployed frontend/backend commit provenance, health/readiness, CORS, strict CSP, browser boot and geometry against that exact merge. Until then: **PRODUCTION VERIFICATION PENDING**. No current production model or service configuration was modified by this implementation.

Phase completion requires stable identity across delete/add/move/reorder/save/undo/redo, deterministic cross-language projections, preserved old snapshots, rejection of malformed/missing IDs, required CI success and an explicit live-verification record after any release. Full engineering acceptance additionally requires resolving the separately tracked unknown/provenance defects.
