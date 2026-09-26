# ACS untouched baseline — 2026-09-26

This is an audit record, not an assertion that all tests passed. No application source was changed before these measurements.

## Source and environment

- Requested source: `9e3e472d6de893c8cad8b72eb870bf5768f20147`.
- Remediation source: `adec616aa5191315991fb9439cee83efbb719b8f`, the observed main head. `git rev-list --count 9e3e472..adec616` reports 766 commits, and `git merge-base --is-ancestor 9e3e472 adec616` exits 0. Fixes start from current main to preserve intervening work; no main write or merge is authorized.
- Python 3.12.14 in an isolated virtualenv (CI targets 3.11); Node/npm versions recorded below. Pinned `requirements.txt` and `requirements-dev.txt` installed successfully. `npm install` completed for both snapshots. No Chromium binary or public/vendor runtime was available for this baseline.
- The requested bare `ACS_ENV=test bash tools/ci_run.sh` exits 64 with `ci_run: --runner is required`; it does not run all suites. The expanded sweep below explicitly passes every discovered test script to the repository runner, using runner declarations from workflows and phase scripts.
- The initial discovery harness mistakenly ran phase1 snippets with plain Node. These six invocation failures are preserved verbatim; corrected `node tests/lib/run.js` results follow. Do not classify an invocation error as an application defect.
- Browser/vendor failures are environmental. The generation-cancel /proc check is unreliable in this namespace: namespace PIDs differ from the mounted host /proc PIDs. It is not remediated by changing product code.
- Reports use measured test output; exit 0 with an internal NOT VERIFIED disclosure is not treated as verified browser behavior. No paid provider calls were made for this baseline.

## Commands and complete results

All commands use `ACS_ENV=test`, `PYTHONPATH=<checkout>`, and the pinned virtualenv on PATH. Logs were captured before fixes. This table preserves every command exit including repeats.

| Target | Exit | Command |
|---|---:|---|
| 02-integration | 0 | `python3 tools/check_integration.py` |
| 03-index | 0 | `python3 tools/check_index_guard.py public/index.html` |
| 04-api | 0 | `python3 tools/check_api_base.py` |
| 05-csp | 0 | `python3 tools/check_csp_hash.py` |
| 06-deploy | 0 | `python3 tests/deploy/verify_deploy.py` |
| 07-ci-exact | 64 | `bash tools/ci_run.sh` |
| 08-bundle | 0 | `python3 tools/bundle_report.py` |
| tests/deploy/test_viewport_pixels.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/deploy/test_viewport_pixels.js` |
| tests/phase1/test_gate.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase1/test_gate.js` |
| tests/phase1/test_p0.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase1/test_p0.js` |
| tests/phase1/test_phase2.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase1/test_phase2.js` |
| tests/phase1/test_prov.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase1/test_prov.js` |
| tests/phase1/test_types.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase1/test_types.js` |
| tests/phase1/test_xss.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase1/test_xss.js` |
| tests/phase2/test_arch.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_arch.js` |
| tests/phase2/test_coord.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_coord.js` |
| tests/phase2/test_dist.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_dist.js` |
| tests/phase2/test_eg.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_eg.js` |
| tests/phase2/test_fls.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_fls.js` |
| tests/phase2/test_ingest.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_ingest.js` |
| tests/phase2/test_mep.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_mep.js` |
| tests/phase2/test_nav.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_nav.js` |
| tests/phase2/test_occ.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_occ.js` |
| tests/phase2/test_rel.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_rel.js` |
| tests/phase2/test_render.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_render.js` |
| tests/phase2/test_rev.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_rev.js` |
| tests/phase2/test_rules.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_rules.js` |
| tests/phase2/test_struct.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase2/test_struct.js` |
| tests/phase3/test_dev_api.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase3/test_dev_api.js` |
| tests/phase3/test_visual.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase3/test_visual.js` |
| tests/phase3/test_visual_adversarial.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase3/test_visual_adversarial.js` |
| tests/phase4/test_adversarial.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase4/test_adversarial.js` |
| tests/phase4/test_browser_parity.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase4/test_browser_parity.js` |
| tests/phase4/test_collision.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase4/test_collision.js` |
| tests/phase4/test_immutability.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase4/test_immutability.js` |
| tests/phase4/test_measurement.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase4/test_measurement.js` |
| tests/phase4/test_model_regression.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase4/test_model_regression.js` |
| tests/phase4/test_navigation.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase4/test_navigation.js` |
| tests/phase4/test_parity.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase4/test_parity.js` |
| tests/phase4/test_portals.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase4/test_portals.js` |
| tests/phase4/test_runtime.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase4/test_runtime.js` |
| tests/phase4/test_selection.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase4/test_selection.js` |
| tests/phase4/test_visibility.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase4/test_visibility.js` |
| tests/phase5/test_adversarial.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase5/test_adversarial.js` |
| tests/phase5/test_ai_boundary.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase5/test_ai_boundary.js` |
| tests/phase5/test_authoring.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase5/test_authoring.js` |
| tests/phase5/test_browser.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase5/test_browser.js` |
| tests/phase5/test_browser_parity.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase5/test_browser_parity.js` |
| tests/phase5/test_commands.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase5/test_commands.js` |
| tests/phase5/test_immutability.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase5/test_immutability.js` |
| tests/phase5/test_integration.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase5/test_integration.js` |
| tests/phase5/test_parity.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase5/test_parity.js` |
| tests/phase5/test_revision.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase5/test_revision.js` |
| tests/phase5/test_transaction.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase5/test_transaction.js` |
| tests/phase6/test_dom.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase6/test_dom.js` |
| tests/phase6/test_parity.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase6/test_parity.js` |
| tests/phase6/test_responsive.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase6/test_responsive.js` |
| tests/phase6/test_security.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase6/test_security.js` |
| tests/phase6/test_workflow.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase6/test_workflow.js` |
| tests/phase6/test_workspace.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase6/test_workspace.js` |
| tests/phase7/test_parity.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase7/test_parity.js` |
| tests/phase7/test_render.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase7/test_render.js` |
| tests/phase7/test_security.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase7/test_security.js` |
| tests/phase7/test_targets.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase7/test_targets.js` |
| tests/phase8/test_bim.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/phase8/test_bim.py` |
| tests/phase8/test_bim_browser.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase8/test_bim_browser.js` |
| tests/phase8/test_parity.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase8/test_parity.js` |
| tests/phase9/test_docs.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/phase9/test_docs.py` |
| tests/phase9/test_docs_browser.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase9/test_docs_browser.js` |
| tests/phase9/test_parity.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase9/test_parity.js` |
| tests/phase9_1/test_parity.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase9_1/test_parity.js` |
| tests/phase9_1/test_pbr.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/phase9_1/test_pbr.py` |
| tests/phase9_1/test_pbr_browser.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase9_1/test_pbr_browser.js` |
| tests/phase9_2/test_alignment.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/phase9_2/test_alignment.py` |
| tests/phase9_2/test_archdetail.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/phase9_2/test_archdetail.py` |
| tests/phase9_2/test_archdetail_browser.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase9_2/test_archdetail_browser.js` |
| tests/phase9_2/test_backend_contract.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/phase9_2/test_backend_contract.py` |
| tests/phase9_2/test_black_viewport.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/phase9_2/test_black_viewport.py` |
| tests/phase9_2/test_generation_budget.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/phase9_2/test_generation_budget.py` |
| tests/phase9_2/test_live_render.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/phase9_2/test_live_render.py` |
| tests/phase9_2/test_parity.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase9_2/test_parity.js` |
| tests/remediation/test_accessibility.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_accessibility.js` |
| tests/remediation/test_alignment_diagnostics.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/remediation/test_alignment_diagnostics.js` |
| tests/remediation/test_api_wiring.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_api_wiring.py` |
| tests/remediation/test_apply_render_browser.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_apply_render_browser.js` |
| tests/remediation/test_asgi_client_contract.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_asgi_client_contract.py` |
| tests/remediation/test_async_generation_jobs.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_async_generation_jobs.py` |
| tests/remediation/test_async_job_reference_receipt.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_async_job_reference_receipt.py` |
| tests/remediation/test_auth_gateway.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_auth_gateway.py` |
| tests/remediation/test_auth_session.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_auth_session.js` |
| tests/remediation/test_auth_shipped_page.cjs | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_auth_shipped_page.cjs` |
| tests/remediation/test_autofix_propose_boundary.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_autofix_propose_boundary.py` |
| tests/remediation/test_brief_program.mjs | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_brief_program.mjs` |
| tests/remediation/test_browser_acquisition.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_browser_acquisition.py` |
| tests/remediation/test_build_metadata.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_build_metadata.py` |
| tests/remediation/test_bundle_extractor.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_bundle_extractor.js` |
| tests/remediation/test_bundle_report.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_bundle_report.py` |
| tests/remediation/test_ci_dependencies.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_ci_dependencies.py` |
| tests/remediation/test_ci_gate.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_ci_gate.py` |
| tests/remediation/test_concurrency.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/remediation/test_concurrency.js` |
| tests/remediation/test_connected_semantic_locks.mjs | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_connected_semantic_locks.mjs` |
| tests/remediation/test_connected_typology_isolation.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_connected_typology_isolation.py` |
| tests/remediation/test_connected_workspace.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_connected_workspace.py` |
| tests/remediation/test_connected_workspace_browser.cjs | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_connected_workspace_browser.cjs` |
| tests/remediation/test_container_topology.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_container_topology.py` |
| tests/remediation/test_csp.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/remediation/test_csp.js` |
| tests/remediation/test_csp_style_architecture.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_csp_style_architecture.js` |
| tests/remediation/test_dependency_lock.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_dependency_lock.py` |
| tests/remediation/test_doc_claims.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_doc_claims.py` |
| tests/remediation/test_engineering_authority.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_engineering_authority.py` |
| tests/remediation/test_event_loop.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_event_loop.py` |
| tests/remediation/test_generation_cancel.py | 1 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_generation_cancel.py` |
| tests/remediation/test_generation_jobs.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_generation_jobs.js` |
| tests/remediation/test_generation_jobs_browser.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_generation_jobs_browser.js` |
| tests/remediation/test_generation_jobs_shipped_page.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_generation_jobs_shipped_page.js` |
| tests/remediation/test_generation_spatial_context.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_generation_spatial_context.py` |
| tests/remediation/test_gl_probe_contract.mjs | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_gl_probe_contract.mjs` |
| tests/remediation/test_image_build_metadata.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_image_build_metadata.py` |
| tests/remediation/test_inline_style_sources.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_inline_style_sources.py` |
| tests/remediation/test_job_boundary.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_job_boundary.py` |
| tests/remediation/test_live_generation_verdict.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_live_generation_verdict.py` |
| tests/remediation/test_logging.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_logging.py` |
| tests/remediation/test_mobile_project_layout.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_mobile_project_layout.js` |
| tests/remediation/test_model_apply.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/remediation/test_model_apply.js` |
| tests/remediation/test_model_diagnostics.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_model_diagnostics.py` |
| tests/remediation/test_model_review_ui.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/remediation/test_model_review_ui.js` |
| tests/remediation/test_module_graph.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_module_graph.js` |
| tests/remediation/test_multi_provider.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_multi_provider.py` |
| tests/remediation/test_opening_identity.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/remediation/test_opening_identity.js` |
| tests/remediation/test_opening_identity.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_opening_identity.py` |
| tests/remediation/test_opening_identity_parity.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_opening_identity_parity.js` |
| tests/remediation/test_p0_hardening.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_p0_hardening.py` |
| tests/remediation/test_panel_entry.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_panel_entry.js` |
| tests/remediation/test_pdf_runtime.mjs | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_pdf_runtime.mjs` |
| tests/remediation/test_performance.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_performance.js` |
| tests/remediation/test_persistence.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/remediation/test_persistence.js` |
| tests/remediation/test_plan_bridge.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_bridge.py` |
| tests/remediation/test_plan_bridge_integration.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_bridge_integration.py` |
| tests/remediation/test_plan_cad_export.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_cad_export.py` |
| tests/remediation/test_plan_chat_candidate_admission.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_chat_candidate_admission.py` |
| tests/remediation/test_plan_chat_isolated_worker.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_chat_isolated_worker.py` |
| tests/remediation/test_plan_chat_preflight_authority.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_chat_preflight_authority.py` |
| tests/remediation/test_plan_chat_stale_safe_orchestration.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_chat_stale_safe_orchestration.py` |
| tests/remediation/test_plan_chunking.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_chunking.py` |
| tests/remediation/test_plan_commands.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_commands.py` |
| tests/remediation/test_plan_element_provenance.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_element_provenance.py` |
| tests/remediation/test_plan_export_provenance_parity.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_export_provenance_parity.py` |
| tests/remediation/test_plan_handoff.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_handoff.py` |
| tests/remediation/test_plan_handoff_derived_authority.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_handoff_derived_authority.py` |
| tests/remediation/test_plan_handoff_large.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_handoff_large.py` |
| tests/remediation/test_plan_handoff_lock_binding.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_handoff_lock_binding.py` |
| tests/remediation/test_plan_handoff_nested_provenance.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_handoff_nested_provenance.py` |
| tests/remediation/test_plan_handoff_object_geometry.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_handoff_object_geometry.py` |
| tests/remediation/test_plan_handoff_room_presentation_geometry.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_handoff_room_presentation_geometry.py` |
| tests/remediation/test_plan_handoff_warehouse_dock_geometry.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_handoff_warehouse_dock_geometry.py` |
| tests/remediation/test_plan_handoff_warehouse_lane_geometry.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_handoff_warehouse_lane_geometry.py` |
| tests/remediation/test_plan_handoff_warehouse_rack_geometry.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_handoff_warehouse_rack_geometry.py` |
| tests/remediation/test_plan_handoff_warehouse_station_geometry.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_handoff_warehouse_station_geometry.py` |
| tests/remediation/test_plan_http_command_boundary.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_http_command_boundary.py` |
| tests/remediation/test_plan_ifc_derived_authority.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_ifc_derived_authority.py` |
| tests/remediation/test_plan_ifc_export.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_ifc_export.py` |
| tests/remediation/test_plan_lock_binding.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_lock_binding.py` |
| tests/remediation/test_plan_options.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_options.py` |
| tests/remediation/test_plan_pdf_export.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_pdf_export.py` |
| tests/remediation/test_plan_persisted_commands.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_persisted_commands.py` |
| tests/remediation/test_plan_projection.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_projection.py` |
| tests/remediation/test_plan_provenance_admission.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_provenance_admission.py` |
| tests/remediation/test_plan_requirement_evidence.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_requirement_evidence.py` |
| tests/remediation/test_plan_residential_revision_compare_restore.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_residential_revision_compare_restore.py` |
| tests/remediation/test_plan_residential_scorecard.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_residential_scorecard.py` |
| tests/remediation/test_plan_review.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_review.py` |
| tests/remediation/test_plan_review_packet.mjs | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_plan_review_packet.mjs` |
| tests/remediation/test_plan_review_packet.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_review_packet.py` |
| tests/remediation/test_plan_review_scorecard_disclosures.cjs | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_plan_review_scorecard_disclosures.cjs` |
| tests/remediation/test_plan_review_ui.cjs | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_plan_review_ui.cjs` |
| tests/remediation/test_plan_revision_compare_restore.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_revision_compare_restore.py` |
| tests/remediation/test_plan_role_area_constraints.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_role_area_constraints.py` |
| tests/remediation/test_plan_scorecard.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_scorecard.py` |
| tests/remediation/test_plan_selective_lock_export_parity.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_selective_lock_export_parity.py` |
| tests/remediation/test_plan_semantic_diff.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_semantic_diff.py` |
| tests/remediation/test_plan_semantic_diff_commands.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_semantic_diff_commands.py` |
| tests/remediation/test_plan_semantic_locks.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_semantic_locks.py` |
| tests/remediation/test_plan_source_span_artifacts.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_source_span_artifacts.py` |
| tests/remediation/test_plan_source_upload.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_source_upload.py` |
| tests/remediation/test_plan_store.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_store.py` |
| tests/remediation/test_plan_store_authenticated_session.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_store_authenticated_session.py` |
| tests/remediation/test_plan_store_port.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_store_port.py` |
| tests/remediation/test_plan_store_reload.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_store_reload.py` |
| tests/remediation/test_plan_store_row_binding.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_store_row_binding.py` |
| tests/remediation/test_plan_svg_export.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_svg_export.py` |
| tests/remediation/test_plan_typology_lifecycle.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_typology_lifecycle.py` |
| tests/remediation/test_plan_warehouse_column_locks.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_warehouse_column_locks.py` |
| tests/remediation/test_plan_warehouse_dock_zone_constraints.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_warehouse_dock_zone_constraints.py` |
| tests/remediation/test_plan_warehouse_docks_by_zone.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_warehouse_docks_by_zone.py` |
| tests/remediation/test_plan_warehouse_expansion_reserves.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_warehouse_expansion_reserves.py` |
| tests/remediation/test_plan_warehouse_lane_conflicts.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_warehouse_lane_conflicts.py` |
| tests/remediation/test_plan_warehouse_lane_length_constraints.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_warehouse_lane_length_constraints.py` |
| tests/remediation/test_plan_warehouse_operational_metrics.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_warehouse_operational_metrics.py` |
| tests/remediation/test_plan_warehouse_program.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_warehouse_program.py` |
| tests/remediation/test_plan_warehouse_rack_lane_conflicts.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_warehouse_rack_lane_conflicts.py` |
| tests/remediation/test_plan_warehouse_zone_allocation_constraints.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_warehouse_zone_allocation_constraints.py` |
| tests/remediation/test_plan_warehouse_zone_allocation_ratios.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plan_warehouse_zone_allocation_ratios.py` |
| tests/remediation/test_plate_extent.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_plate_extent.py` |
| tests/remediation/test_privacy_boundary.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_privacy_boundary.py` |
| tests/remediation/test_production_auth_boundary.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_production_auth_boundary.py` |
| tests/remediation/test_production_error_ui.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/remediation/test_production_error_ui.js` |
| tests/remediation/test_provider_accounting.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_provider_accounting.py` |
| tests/remediation/test_provider_capability.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_provider_capability.py` |
| tests/remediation/test_provider_integration.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_provider_integration.py` |
| tests/remediation/test_provider_reject.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_provider_reject.py` |
| tests/remediation/test_rate_limit.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_rate_limit.py` |
| tests/remediation/test_residential_layout_fallback.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_residential_layout_fallback.py` |
| tests/remediation/test_residential_presentation.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_residential_presentation.js` |
| tests/remediation/test_residential_program.mjs | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_residential_program.mjs` |
| tests/remediation/test_residential_quality.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_residential_quality.py` |
| tests/remediation/test_rule_source_boundary.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_rule_source_boundary.py` |
| tests/remediation/test_scene_benchmark.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_scene_benchmark.js` |
| tests/remediation/test_scene_limits.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/remediation/test_scene_limits.js` |
| tests/remediation/test_single_level_template_binding.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_single_level_template_binding.py` |
| tests/remediation/test_supabase_auth_deployment_readiness.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_supabase_auth_deployment_readiness.py` |
| tests/remediation/test_supabase_auth_integration.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_supabase_auth_integration.py` |
| tests/remediation/test_supabase_plan_store_adapter.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_supabase_plan_store_adapter.py` |
| tests/remediation/test_supabase_plan_store_rpc_schema.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_supabase_plan_store_rpc_schema.py` |
| tests/remediation/test_supabase_plan_store_schema.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_supabase_plan_store_schema.py` |
| tests/remediation/test_thinking_wire.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_thinking_wire.py` |
| tests/remediation/test_transport_browser.js | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_transport_browser.js` |
| tests/remediation/test_transport_errors.js | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_transport_errors.js` |
| tests/remediation/test_upload_security.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_upload_security.py` |
| tests/remediation/test_validate_against_real_models.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_validate_against_real_models.py` |
| tests/remediation/test_validate_topology.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_validate_topology.py` |
| tests/remediation/test_warehouse_building_target.mjs | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_warehouse_building_target.mjs` |
| tests/remediation/test_warehouse_program_feasibility.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_warehouse_program_feasibility.py` |
| tests/remediation/test_warehouse_render_identity.mjs | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_warehouse_render_identity.mjs` |
| tests/remediation/test_warehouse_soft_area_fit.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_warehouse_soft_area_fit.py` |
| tests/remediation/test_warehouse_vertical_stage_gate.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_warehouse_vertical_stage_gate.py` |
| tests/remediation/test_webgl_diagnostics.js | 124 | `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/remediation/test_webgl_diagnostics.js` |
| tests/remediation/test_workspace_recovery.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_workspace_recovery.py` |
| tests/remediation/test_workspace_viewport_selection.mjs | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_workspace_viewport_selection.mjs` |
| tests/remediation/test_workspace_viewport_selection_browser.cjs | 1 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_workspace_viewport_selection_browser.cjs` |
| tests/remediation/test_workspace_warehouse_exact_selection.mjs | 0 | `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_workspace_warehouse_exact_selection.mjs` |
| tests/security/test_security.py | 0 | `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/security/test_security.py` |
| 09-doc-claims | 1 | `python3 tools/check_doc_claims.py` |
| tests/phase1/test_gate.js (corrected runner) | 1 | `bash tools/ci_run.sh --label phase1-correct-runner --runner node tests/lib/run.js tests/phase1/test_gate.js` |
| tests/phase1/test_p0.js (corrected runner) | 0 | `bash tools/ci_run.sh --label phase1-correct-runner --runner node tests/lib/run.js tests/phase1/test_p0.js` |
| tests/phase1/test_phase2.js (corrected runner) | 0 | `bash tools/ci_run.sh --label phase1-correct-runner --runner node tests/lib/run.js tests/phase1/test_phase2.js` |
| tests/phase1/test_prov.js (corrected runner) | 1 | `bash tools/ci_run.sh --label phase1-correct-runner --runner node tests/lib/run.js tests/phase1/test_prov.js` |
| tests/phase1/test_types.js (corrected runner) | 0 | `bash tools/ci_run.sh --label phase1-correct-runner --runner node tests/lib/run.js tests/phase1/test_types.js` |
| tests/phase1/test_xss.js (corrected runner) | 0 | `bash tools/ci_run.sh --label phase1-correct-runner --runner node tests/lib/run.js tests/phase1/test_xss.js` |

## Verbatim failed command output

Every failing command from the complete sweep appears below, including corrected-runner failures. Missing entries in post-change results are not an excuse to skip a suite.

### 07-ci-exact

Command: `bash tools/ci_run.sh`; exit 64

```text
ci_run: --runner is required
```

### tests/deploy/test_viewport_pixels.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/deploy/test_viewport_pixels.js`; exit 1

```text
=== tests/deploy/test_viewport_pixels.js ===

== ANALYSER UNIT BEHAVIOUR ==
  ✓ a fully black frame is EFFECTIVELY_BLACK
  ✓ a uniform very dark frame (#010203) is EFFECTIVELY_BLACK
  ✓ a black frame with a single bright pixel is still EFFECTIVELY_BLACK
  ✓ a dark NIGHT scene that still has lit geometry is VISIBLE_CONTENT
  ✓ an ordinary daylight frame is VISIBLE_CONTENT
  ✓ an empty buffer is refused rather than passed
  ✓ a tiny sample is refused as insufficient evidence
  ✓ the thresholds are reported with every verdict (explainable)
  ✗ browser fixture error no Chromium binary is available in this sandbox — searched: playwright-managed: /root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome | browser roots: /root/.cache/ms-playwright, /opt/pw-brow

──────────────────────────────────────────────
VIEWPORT PIXEL TEST: 8 passed, 1 failed
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/deploy/test_viewport_pixels.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/phase1/test_gate.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase1/test_gate.js`; exit 1

```text
=== tests/phase1/test_gate.js ===

== GATE #6: object preservation — new example "اثنين AMR" ==
/workspace/scratch/cc68e7a7ea83/acs/tests/phase1/test_gate.js:4
let r=objectsFromText('مستودع 100×60 فيه ستة عمال واثنين AMR ورافعة شوكية');
      ^

ReferenceError: objectsFromText is not defined
    at Object.<anonymous> (/workspace/scratch/cc68e7a7ea83/acs/tests/phase1/test_gate.js:4:7)
    at Module._compile (node:internal/modules/cjs/loader:1872:14)
    at Object..js (node:internal/modules/cjs/loader:2003:10)
    at Module.load (node:internal/modules/cjs/loader:1594:32)
    at Module._load (node:internal/modules/cjs/loader:1396:12)
    at wrapModuleLoad (node:internal/modules/cjs/loader:255:19)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)
    at node:internal/main/run_main_module:33:47

Node.js v24.19.0
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/phase1/test_gate.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/phase1/test_p0.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase1/test_p0.js`; exit 1

```text
=== tests/phase1/test_p0.js ===

== TEST 5: object preservation (local fallback) ==
/workspace/scratch/cc68e7a7ea83/acs/tests/phase1/test_p0.js:10
let r=objectsFromText(txt);
      ^

ReferenceError: objectsFromText is not defined
    at Object.<anonymous> (/workspace/scratch/cc68e7a7ea83/acs/tests/phase1/test_p0.js:10:7)
    at Module._compile (node:internal/modules/cjs/loader:1872:14)
    at Object..js (node:internal/modules/cjs/loader:2003:10)
    at Module.load (node:internal/modules/cjs/loader:1594:32)
    at Module._load (node:internal/modules/cjs/loader:1396:12)
    at wrapModuleLoad (node:internal/modules/cjs/loader:255:19)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)
    at node:internal/main/run_main_module:33:47

Node.js v24.19.0
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/phase1/test_p0.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/phase1/test_phase2.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase1/test_phase2.js`; exit 1

```text
=== tests/phase1/test_phase2.js ===

== DRIFT — frontend registry must equal acs_programs.json (single source of truth) ==
/workspace/scratch/cc68e7a7ea83/acs/tests/phase1/test_phase2.js:9
const jsIds=ACS_PROGRAMS.map(p=>p.id), pyIds=REG.programs.map(p=>p.id);
            ^

ReferenceError: ACS_PROGRAMS is not defined
    at Object.<anonymous> (/workspace/scratch/cc68e7a7ea83/acs/tests/phase1/test_phase2.js:9:13)
    at Module._compile (node:internal/modules/cjs/loader:1872:14)
    at Object..js (node:internal/modules/cjs/loader:2003:10)
    at Module.load (node:internal/modules/cjs/loader:1594:32)
    at Module._load (node:internal/modules/cjs/loader:1396:12)
    at wrapModuleLoad (node:internal/modules/cjs/loader:255:19)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)
    at node:internal/main/run_main_module:33:47

Node.js v24.19.0
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/phase1/test_phase2.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/phase1/test_prov.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase1/test_prov.js`; exit 1

```text
=== tests/phase1/test_prov.js ===

== TEST A — VILLA FLOORS (user=2, model=3) ==
/workspace/scratch/cc68e7a7ea83/acs/tests/phase1/test_prov.js:8
chk('requestedFloorsFromText("فيلا دورين…") === 2', requestedFloorsFromText(VILLA)===2, requestedFloorsFromText(VILLA));
^

ReferenceError: requestedFloorsFromText is not defined
    at Object.<anonymous> (/workspace/scratch/cc68e7a7ea83/acs/tests/phase1/test_prov.js:8:1)
    at Module._compile (node:internal/modules/cjs/loader:1872:14)
    at Object..js (node:internal/modules/cjs/loader:2003:10)
    at Module.load (node:internal/modules/cjs/loader:1594:32)
    at Module._load (node:internal/modules/cjs/loader:1396:12)
    at wrapModuleLoad (node:internal/modules/cjs/loader:255:19)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)
    at node:internal/main/run_main_module:33:47

Node.js v24.19.0
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/phase1/test_prov.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/phase1/test_types.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase1/test_types.js`; exit 1

```text
=== tests/phase1/test_types.js ===

== AUDIT 2/3: 10 building types (local DATA pipeline) ==
/workspace/scratch/cc68e7a7ea83/acs/tests/phase1/test_types.js:3
  const t=detectTypeJS(txt); const oi=objectsFromText(txt);
          ^

ReferenceError: detectTypeJS is not defined
    at localBuild (/workspace/scratch/cc68e7a7ea83/acs/tests/phase1/test_types.js:3:11)
    at Object.<anonymous> (/workspace/scratch/cc68e7a7ea83/acs/tests/phase1/test_types.js:35:11)
    at Module._compile (node:internal/modules/cjs/loader:1872:14)
    at Object..js (node:internal/modules/cjs/loader:2003:10)
    at Module.load (node:internal/modules/cjs/loader:1594:32)
    at Module._load (node:internal/modules/cjs/loader:1396:12)
    at wrapModuleLoad (node:internal/modules/cjs/loader:255:19)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)
    at node:internal/main/run_main_module:33:47

Node.js v24.19.0
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/phase1/test_types.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/phase1/test_xss.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase1/test_xss.js`; exit 1

```text
=== tests/phase1/test_xss.js ===
/workspace/scratch/cc68e7a7ea83/acs/tests/phase1/test_xss.js:4
const notesHTML='<b>'+esc(payload)+'</b> — '+esc(payload)+' ('+esc('x')+')<br><span>'+esc(payload)+'</span>';
                ^

ReferenceError: esc is not defined
    at Object.<anonymous> (/workspace/scratch/cc68e7a7ea83/acs/tests/phase1/test_xss.js:4:17)
    at Module._compile (node:internal/modules/cjs/loader:1872:14)
    at Object..js (node:internal/modules/cjs/loader:2003:10)
    at Module.load (node:internal/modules/cjs/loader:1594:32)
    at Module._load (node:internal/modules/cjs/loader:1396:12)
    at wrapModuleLoad (node:internal/modules/cjs/loader:255:19)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)
    at node:internal/main/run_main_module:33:47

Node.js v24.19.0
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/phase1/test_xss.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/phase4/test_browser_parity.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase4/test_browser_parity.js`; exit 1

```text
=== tests/phase4/test_browser_parity.js ===
  ✗ browser parity aborted: no Chromium binary is available in this sandbox — searched: playwright-managed: /root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome | browser roots: /root/.cache/ms-playwright, /opt/pw-browsers

BROWSER PARITY: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/phase4/test_browser_parity.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/phase5/test_browser_parity.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase5/test_browser_parity.js`; exit 1

```text
=== tests/phase5/test_browser_parity.js ===
  ✗ browser parity aborted: no Chromium binary is available in this sandbox — searched: playwright-managed: /root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome | browser roots: /root/.cache/ms-playwright, /opt/pw-browsers

AUTHORING BROWSER PARITY: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/phase5/test_browser_parity.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/phase6/test_responsive.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/phase6/test_responsive.js`; exit 1

```text
=== tests/phase6/test_responsive.js ===
  ✗ responsive run aborted: Command failed: /opt/codex/runtimes/codex-primary-runtime/dependencies/node/bin/node /workspace/scratch/cc68e7a7ea83/acs/tests/phase3/lib/build_browser_page.js /tmp/acs_ws_driver.js
node:fs:484
    return binding.readFileUtf8(path, stringToFlags(options.flag));
                   ^

Error: ENOENT: no such file or directory, open '/workspace/scratch/cc68e7a7ea83/acs/public/vendor/three@0.160.0/build/three.module.js'
    at Object.readFileSync (node:fs:484:20)
    at Object.<anonymous> (/workspace/scratch/cc68e7a7ea83/acs/tests/phase3/lib/build_browser_page.js:521:23)
    at Module._compile (node:internal/modules/cjs/loader:1872:14)
    at Object..js (node:internal/modules/cjs/loader:2003:10)
    at Module.load (node:internal/modules/cjs/loader:1594:32)
    at Module._load (node:internal/modules/cjs/loader:1396:12)
    at wrapModuleLoad (node:internal/modules/cjs/loader:255:19)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)
    at node:internal/main/run_main_module:33:47 {
  errno: -2,
  code: 'ENOENT',
  syscall: 'open',
  path: '/workspace/scratch/cc68e7a7ea83/acs/public/vendor/three@0.160.0/build/three.module.js'
}

Node.js v24.19.0


RESPONSIVE: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/phase6/test_responsive.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/phase6/test_security.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase6/test_security.js`; exit 1

```text
=== tests/phase6/test_security.js ===

== §95 — THE ENGINE ITSELF NEVER EXECUTES A PAYLOAD ==
  ✓ a malicious project name #0 does not crash the authoring layer
  ✓ a malicious project name #0 is carried as text, never parsed
  ✓ the summary carries the same text without reinterpretation #0
  ✓ a malicious project name #1 does not crash the authoring layer
  ✓ a malicious project name #1 is carried as text, never parsed
  ✓ the summary carries the same text without reinterpretation #1
  ✓ a malicious project name #2 does not crash the authoring layer
  ✓ a malicious project name #2 is carried as text, never parsed
  ✓ the summary carries the same text without reinterpretation #2
  ✓ a malicious project name #3 does not crash the authoring layer
  ✓ a malicious project name #3 is carried as text, never parsed
  ✓ the summary carries the same text without reinterpretation #3
  ✓ a malicious project name #4 does not crash the authoring layer
  ✓ a malicious project name #4 is carried as text, never parsed
  ✓ the summary carries the same text without reinterpretation #4
  ✓ a malicious project name #5 does not crash the authoring layer
  ✓ a malicious project name #5 is carried as text, never parsed
  ✓ the summary carries the same text without reinterpretation #5
  ✓ a malicious project name #6 does not crash the authoring layer
  ✓ a malicious project name #6 is carried as text, never parsed
  ✓ the summary carries the same text without reinterpretation #6
  ✓ a malicious project name #7 does not crash the authoring layer
  ✓ a malicious project name #7 is carried as text, never parsed
  ✓ the summary carries the same text without reinterpretation #7
  ✓ a malicious project name #8 does not crash the authoring layer
  ✓ a malicious project name #8 is carried as text, never parsed
  ✓ the summary carries the same text without reinterpretation #8
  ✓ a malicious project name #9 does not crash the authoring layer
  ✓ a malicious project name #9 is carried as text, never parsed
  ✓ the summary carries the same text without reinterpretation #9

== §95 — A MALICIOUS EDIT IS REFUSED OR STORED AS INERT TEXT ==
  ✓ a malicious element label #0 leaves the committed model untouched
  ✓ a refused label #0 is refused with a real issue code
  ✓ a malicious element label #1 leaves the committed model untouched
  ✓ a malicious element label #2 leaves the committed model untouched
  ✓ a malicious element label #3 leaves the committed model untouched
  ✓ a refused label #3 is refused with a real issue code
  ✓ a malicious element label #4 leaves the committed model untouched
  ✓ a malicious element label #5 leaves the committed model untouched
  ✓ a refused label #5 is refused with a real issue code
  ✓ a malicious element label #6 leaves the committed model untouched
  ✓ a refused label #6 is refused with a real issue code
  ✓ a malicious element label #7 leaves the committed model untouched
  ✓ a malicious element label #8 leaves the committed model untouched
  ✓ a malicious element label #9 leaves the committed model untouched
  ✓ a refused label #9 is refused with a real issue code

== §95 — AN IMPORTED FILE CANNOT SMUGGLE STRUCTURE ==
  ✓ importing prototype pollution never throws an unhandled error
  ✓ importing prototype pollution either refuses or yields a real project
  ✓ importing prototype pollution does not pollute Object.prototype
  ✓ importing constructor key never throws an unhandled error
  ✓ importing constructor key either refuses or yields a real project
  ✓ importing constructor key does not pollute Object.prototype
  ✓ importing script in a name never throws an unhandled error
  ✓ importing script in a name either refuses or yields a real project
  ✓ importing script in a name does not pollute Object.prototype
  ✓ importing not json at all never throws an unhandled error
  ✓ importing not json at all either refuses or yields a real project
  ✓ importing not json at all does not pollute Object.prototype
  ✓ importing truncated json never throws an unhandled error
  ✓ importing truncated json either refuses or yields a real project
  ✓ importing truncated json does not pollute Object.prototype
  ✓ importing deeply nested never throws an unhandled error
  ✓ importing deeply nested either refuses or yields a real project
  ✓ importing deeply nested does not pollute Object.prototype

== §95 — IMAGE AND REFERENCE METADATA IS NEVER EXECUTABLE ==
  ✓ an executable reference source #0 is refused
  ✓ a rejected reference #0 never enters the context
  ✓ a caption carrying markup #0 cannot be attached
  ✓ an executable reference source #1 is refused
  ✓ a rejected reference #1 never enters the context
  ✓ a caption carrying markup #1 cannot be attached
  ✓ an executable reference source #2 is refused
  ✓ a rejected reference #2 never enters the context
  ✓ a caption carrying markup #2 cannot be attached
  ✓ an executable reference source #3 is refused
  ✓ a rejected reference #3 never enters the context
  ✓ a caption carrying markup #3 cannot be attached
  ✓ a rejected reference #4 never enters the context
  ✓ a caption carrying markup #4 cannot be attached
  ✓ an executable reference source #5 is refused
  ✓ a rejected reference #5 never enters the context
  ✓ a caption carrying markup #5 cannot be attached
  ✓ an executable reference source #6 is refused
  ✓ a rejected reference #6 never enters the context
  ✓ a caption carrying markup #6 cannot be attached
  ✓ a rejected reference #7 never enters the context
  ✓ a caption carrying markup #7 cannot be attached
  ✓ an executable reference source #8 is refused
  ✓ a rejected reference #8 never enters the context
  ✓ a caption carrying markup #8 cannot be attached
  ✓ an executable reference source #9 is refused
  ✓ a rejected reference #9 never enters the context
  ✓ a caption carrying markup #9 cannot be attached
  ✓ an executable reference source #10 is refused
  ✓ a rejected reference #10 never enters the context
  ✓ a caption carrying markup #10 cannot be attached
  ✓ an executable reference source #11 is refused
  ✓ a rejected reference #11 never enters the context
  ✓ a caption carrying markup #11 cannot be attached
  ✓ a rejected reference #12 never enters the context
  ✓ a caption carrying markup #12 cannot be attached
  ✓ the unsafe-pattern list is declared in the canonical spec, not inline

== §95 — THE ASSISTANT CANNOT ESCALATE THROUGH TEXT ==
  ✓ an assistant claim #0 is still classified, never trusted
  ✓ an assistant proposal #0 never reports a commit
  ✓ an assistant proposal #0 still demands explicit confirmation
  ✓ the model hash is unchanged after assistant text #0
  ✓ an assistant claim #1 is still classified, never trusted
  ✓ an assistant proposal #1 never reports a commit
  ✓ an assistant proposal #1 still demands explicit confirmation
  ✓ the model hash is unchanged after assistant text #1
  ✓ an assistant claim #2 is still classified, never trusted
  ✓ an assistant proposal #2 never reports a commit
  ✓ an assistant proposal #2 still demands explicit confirmation
  ✓ the model hash is unchanged after assistant text #2
  ✓ an assistant claim #3 is still classified, never trusted
  ✓ an assistant proposal #3 never reports a commit
  ✓ an assistant proposal #3 still demands explicit confirmation
  ✓ the model hash is unchanged after assistant text #3
  ✓ an assistant claim #4 is still classified, never trusted
  ✓ an assistant proposal #4 never reports a commit
  ✓ an assistant proposal #4 still demands explicit confirmation
  ✓ the model hash is unchanged after assistant text #4
  ✓ an assistant claim #5 is still classified, never trusted
  ✓ an assistant proposal #5 never reports a commit
  ✓ an assistant proposal #5 still demands explicit confirmation
  ✓ the model hash is unchanged after assistant text #5
  ✓ an assistant claim #6 is still classified, never trusted
  ✓ an assistant proposal #6 never reports a commit
  ✓ an assistant proposal #6 still demands explicit confirmation
  ✓ the model hash is unchanged after assistant text #6
  ✓ an assistant claim #7 is still classified, never trusted
  ✓ an assistant proposal #7 never reports a commit
  ✓ an assistant proposal #7 still demands explicit confirmation
  ✓ the model hash is unchanged after assistant text #7
  ✓ an assistant claim #8 is still classified, never trusted
  ✓ an assistant proposal #8 never reports a commit
  ✓ an assistant proposal #8 still demands explicit confirmation
  ✓ the model hash is unchanged after assistant text #8
  ✓ an assistant claim #9 is still classified, never trusted
  ✓ an assistant proposal #9 never reports a commit
  ✓ an assistant proposal #9 still demands explicit confirmation
  ✓ the model hash is unchanged after assistant text #9
  ✓ an assistant claim #10 is still classified, never trusted
  ✓ an assistant proposal #10 never reports a commit
  ✓ an assistant proposal #10 still demands explicit confirmation
  ✓ the model hash is unchanged after assistant text #10
  ✓ an assistant claim #11 is still classified, never trusted
  ✓ an assistant proposal #11 never reports a commit
  ✓ an assistant proposal #11 still demands explicit confirmation
  ✓ the model hash is unchanged after assistant text #11
  ✓ an assistant claim #12 is still classified, never trusted
  ✓ an assistant proposal #12 never reports a commit
  ✓ an assistant proposal #12 still demands explicit confirmation
  ✓ the model hash is unchanged after assistant text #12

== §95 — NO ISSUE OR STATUS TEXT CAN FAKE COMPLIANCE ==
  ✓ the issue centre produced real issue text to scan
  ✓ no issue text uses a forbidden status word
  ✓ the issue centre states that no status here means compliant
  ✓ the workspace never declares a compliance verdict

== §95 — THE GENERATED INTERFACE CARRIES NO DYNAMIC EXECUTION ==
  ✓ the generated workspace block appears exactly once in the whole application
  ✗ it lives in public/app/generated/workspace-ui.js, and public/app/main.js imports it 
  ✓ the canonical spec is injected as one data assignment, not code
  ✓ removing the spec assignment leaves the real implementation behind
  ✓ the workspace block contains no eval
  ✓ the workspace block constructs no function from a string
  ✓ the workspace block never assigns a javascript: url
  ✓ the workspace block never writes into the document stream
  ✓ the dynamic-execution scan is not vacuous
  ✓ an escaping helper is declared once in the workspace block
  ✓ the escaping helper covers every dangerous character

  · DOM escaping checks require a page: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED
  ✓ the DOM section declares its requirement instead of faking a pass

──────────────────────────────────────────────
WORKSPACE SECURITY: 167 passed, 1 failed
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/phase6/test_security.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/phase7/test_security.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/phase7/test_security.js`; exit 1

```text
=== tests/phase7/test_security.js ===

== §64 — UNTRUSTED VISUAL INPUT IS REFUSED, NEVER SANITISED AWAY ==
  ✓ the unsafe pattern list is declared in the canonical specification
  ✓ the list covers script, markup, executable schemes and entities
  ✓ an ordinary string is not falsely flagged
  ✓ markup payload #0 is recognised as unsafe
  ✓ markup payload #1 is recognised as unsafe
  ✓ markup payload #2 is recognised as unsafe
  ✓ markup payload #3 is recognised as unsafe
  ✓ markup payload #4 is recognised as unsafe
  ✓ markup payload #5 is recognised as unsafe
  ✓ markup payload #6 is recognised as unsafe
  ✓ markup payload #7 is recognised as unsafe
  ✓ an allow-list pattern for identifiers is declared
  ✓ an allow-list of reference schemes is declared
  ✓ payload #0 is not a plausible identifier
  ✓ payload #0 is not an allowed reference source
  ✓ payload #1 is not a plausible identifier
  ✓ payload #1 is not an allowed reference source
  ✓ payload #2 is not a plausible identifier
  ✓ payload #2 is not an allowed reference source
  ✓ payload #3 is not a plausible identifier
  ✓ payload #3 is not an allowed reference source
  ✓ payload #4 is not a plausible identifier
  ✓ payload #4 is not an allowed reference source
  ✓ payload #5 is not a plausible identifier
  ✓ payload #5 is not an allowed reference source
  ✓ payload #6 is not a plausible identifier
  ✓ payload #6 is not an allowed reference source
  ✓ payload #7 is not a plausible identifier
  ✓ payload #7 is not an allowed reference source
  ✓ payload #8 is not a plausible identifier
  ✓ payload #8 is not an allowed reference source
  ✓ payload #9 is not a plausible identifier
  ✓ payload #9 is not an allowed reference source
  ✓ a real identifier is accepted
  ✓ a real https source is accepted
  ✓ a base64 png data source is accepted
  ✓ an svg data source is refused even though it is a data image
  ✓ an unknown scheme is refused by default, not by pattern guessing
  ✓ an allow-list guard for visual intent is declared
  ✓ payload #0 is not a plausible style description
  ✓ payload #1 is not a plausible style description
  ✓ payload #2 is not a plausible style description
  ✓ payload #3 is not a plausible style description
  ✓ payload #4 is not a plausible style description
  ✓ payload #5 is not a plausible style description
  ✓ payload #6 is not a plausible style description
  ✓ payload #7 is not a plausible style description
  ✓ payload #8 is not a plausible style description
  ✓ payload #9 is not a plausible style description
  ✓ a real style description is accepted
  ✓ an over-long style description is refused

== §64 — A HOSTILE REFERENCE NEVER REACHES THE PROMPT ==
  ✓ a hostile reference #0 is dropped from the prompt
  ✓ a hostile visual intent #0 is dropped from the prompt
  ✓ the prompt for #0 still declares the preservation contract
  ✓ a hostile reference #1 is dropped from the prompt
  ✓ a hostile visual intent #1 is dropped from the prompt
  ✓ the prompt for #1 still declares the preservation contract
  ✓ a hostile reference #2 is dropped from the prompt
  ✓ a hostile visual intent #2 is dropped from the prompt
  ✓ the prompt for #2 still declares the preservation contract
  ✓ a hostile reference #3 is dropped from the prompt
  ✓ a hostile visual intent #3 is dropped from the prompt
  ✓ the prompt for #3 still declares the preservation contract
  ✓ a hostile reference #4 is dropped from the prompt
  ✓ a hostile visual intent #4 is dropped from the prompt
  ✓ the prompt for #4 still declares the preservation contract
  ✓ a hostile reference #5 is dropped from the prompt
  ✓ a hostile visual intent #5 is dropped from the prompt
  ✓ the prompt for #5 still declares the preservation contract
  ✓ a hostile reference #6 is dropped from the prompt
  ✓ a hostile visual intent #6 is dropped from the prompt
  ✓ the prompt for #6 still declares the preservation contract
  ✓ a hostile reference #7 is dropped from the prompt
  ✓ a hostile visual intent #7 is dropped from the prompt
  ✓ the prompt for #7 still declares the preservation contract
  ✓ a hostile reference #8 is dropped from the prompt
  ✓ a hostile visual intent #8 is dropped from the prompt
  ✓ the prompt for #8 still declares the preservation contract
  ✓ a hostile reference #9 is dropped from the prompt
  ✓ a hostile visual intent #9 is dropped from the prompt
  ✓ the prompt for #9 still declares the preservation contract
  ✓ a legitimate reference does reach the prompt

== §64 — A HOSTILE REFERENCE IDENTIFIER NEVER ENTERS A REQUEST ==
  ✓ a request carrying hostile reference id #0 is refused
  ✓ the refused request produced no request object #0
  ✓ a request carrying hostile reference id #1 is refused
  ✓ the refused request produced no request object #1
  ✓ a request carrying hostile reference id #2 is refused
  ✓ the refused request produced no request object #2
  ✓ a request carrying hostile reference id #3 is refused
  ✓ the refused request produced no request object #3
  ✓ a request carrying hostile reference id #4 is refused
  ✓ the refused request produced no request object #4
  ✓ a request carrying hostile reference id #5 is refused
  ✓ the refused request produced no request object #5
  ✓ a request carrying hostile reference id #6 is refused
  ✓ the refused request produced no request object #6
  ✓ a request carrying hostile reference id #7 is refused
  ✓ the refused request produced no request object #7
  ✓ a request carrying hostile reference id #8 is refused
  ✓ the refused request produced no request object #8
  ✓ a request carrying hostile reference id #9 is refused
  ✓ the refused request produced no request object #9

== §64 — GENERATED VECTOR OUTPUT ESCAPES EVERY UNTRUSTED VALUE ==
  ✓ a hostile space name #0 opens no element in the SVG
  ✓ a hostile value #0 arrives entity-escaped
  ✓ a hostile space name #1 opens no element in the SVG
  ✓ a hostile value #1 arrives entity-escaped
  ✓ a hostile space name #2 opens no element in the SVG
  ✓ a hostile value #2 arrives entity-escaped
  ✓ a hostile space name #3 opens no element in the SVG
  ✓ a hostile value #3 arrives entity-escaped
  ✓ a hostile space name #4 opens no element in the SVG
  ✓ a hostile value #4 carries no quote that could close an attribute
  ✓ a hostile space name #5 opens no element in the SVG
  ✓ a hostile value #5 carries no quote that could close an attribute
  ✓ a hostile space name #6 opens no element in the SVG
  ✓ a hostile value #6 carries no quote that could close an attribute
  ✓ a hostile space name #7 opens no element in the SVG
  ✓ a hostile value #7 arrives entity-escaped
  ✓ a hostile space name #8 opens no element in the SVG
  ✓ a hostile value #8 carries no quote that could close an attribute
  ✓ a hostile space name #9 opens no element in the SVG
  ✓ a hostile value #9 carries no quote that could close an attribute
  ✓ a hostile elevation face label cannot open a tag
  ✓ a hostile section axis label cannot open a tag

== §64 — SIZE AND TYPE LIMITS ARE DECLARED AND FINITE ==
  ✓ an allowed image type list is declared
  ✓ no executable or markup type is allowed
  ✓ a maximum reference size is declared and finite
  ✓ a maximum reference pixel count is declared, bounding decompression
  ✓ a maximum render pixel count is declared and finite
  ✓ a maximum control buffer size is declared and finite
  ✓ a buffer request beyond the limit is refused
  ✓ a zero-sized buffer request is refused, not silently defaulted
  ✓ a render resolution beyond the limit is refused
  ✓ a negative resolution is refused
  ✓ a non-numeric resolution is refused

== §65 — EVERY BUNDLED ASSET DECLARES SOURCE AND LICENCE ==
  ✓ every material declares a source
  ✓ every material declares a licence from the allowed set
  ✓ no material ships with an unknown licence
  ✓ every bundled material is procedural, so nothing copyrighted is shipped
  ✓ no material references a remote host
  ✓ the texture sources are all local or procedural
  ✓ the specification states no render depends on an uncontrolled host

== §89 — NO SECRET IS EVER EXPOSED ==
  ✓ the adapter states the secret lives in the server environment
  ✓ the adapter states the secret is never in the client
  ✓ the adapter states the secret is never in render metadata
  ✓ the adapter states the secret is never in a log
  ✓ no adapter field carries a secret value
  ✓ no request or descriptor contains an API key pattern
  ✓ no metadata field name suggests a credential
  ✓ a provider response leaking a key does not carry it into the output

== §64 — THE GENERATED ENGINE CARRIES NO DYNAMIC EXECUTION ==
  ✓ the generated render block appears exactly once in the whole application
  ✗ it lives in public/app/generated/render-engine.js, and public/app/main.js imports it 
  ✓ the canonical spec is injected as one data assignment, not code
  ✓ removing the spec assignment leaves the real implementation behind
  ✓ the render block contains no eval
  ✓ the render block constructs no function from a string
  ✓ the render block never assigns a javascript url
  ✓ the render block never writes into the document stream
  ✓ the render block never fetches from the network
  ✓ the dynamic-execution scan is not vacuous
  ✓ an escaping helper covers every dangerous character
  ✓ the python render layer contains no dynamic execution
  ✓ the python render layer opens no network connection

  · DOM checks require a page: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED
  ✓ the DOM section declares its requirement instead of faking a pass

──────────────────────────────────────────────
RENDER SECURITY: 163 passed, 1 failed
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/phase7/test_security.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/remediation/test_accessibility.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_accessibility.js`; exit 1

```text
=== tests/remediation/test_accessibility.js ===
HARNESS: accessibility DOM/ARIA layer, real Chromium, http:// load of public/ under the production CSP
axe-core: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED (not vendored in node_modules or public/; no network in this sandbox). A focused deterministic checker runs instead and is reported as such.

CHROMIUM UNAVAILABLE: Error: no Chromium binary is available in this sandbox — searched: playwright-managed: /root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome | browser roots: /root/.cache/ms-playwright, /opt/
ACCESSIBILITY: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/remediation/test_accessibility.js (exit 2)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/remediation/test_apply_render_browser.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_apply_render_browser.js`; exit 1

```text
=== tests/remediation/test_apply_render_browser.js ===
```

### tests/remediation/test_auth_shipped_page.cjs

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_auth_shipped_page.cjs`; exit 1

```text
=== tests/remediation/test_auth_shipped_page.cjs ===
Error: no Chromium binary is available in this sandbox — searched: playwright-managed: /root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome | browser roots: /root/.cache/ms-playwright, /opt/pw-browsers
    at Object.launch (/workspace/scratch/cc68e7a7ea83/acs/tools/pw_chromium.js:164:11)
    at /workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_auth_shipped_page.cjs:11:26
    at Object.<anonymous> (/workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_auth_shipped_page.cjs:119:3)
    at Module._compile (node:internal/modules/cjs/loader:1872:14)
    at Object..js (node:internal/modules/cjs/loader:2003:10)
    at Module.load (node:internal/modules/cjs/loader:1594:32)
    at Module._load (node:internal/modules/cjs/loader:1396:12)
    at wrapModuleLoad (node:internal/modules/cjs/loader:255:19)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)
    at node:internal/main/run_main_module:33:47
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/remediation/test_auth_shipped_page.cjs (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/remediation/test_connected_workspace_browser.cjs

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_connected_workspace_browser.cjs`; exit 1

```text
=== tests/remediation/test_connected_workspace_browser.cjs ===
Error: no Chromium binary is available in this sandbox — searched: playwright-managed: /root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome | browser roots: /root/.cache/ms-playwright, /opt/pw-browsers
    at Object.launch (/workspace/scratch/cc68e7a7ea83/acs/tools/pw_chromium.js:164:11)
    at /workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_connected_workspace_browser.cjs:28:82
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5)
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/remediation/test_connected_workspace_browser.cjs (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/remediation/test_csp_style_architecture.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_csp_style_architecture.js`; exit 1

```text
=== tests/remediation/test_csp_style_architecture.js ===

== 2 · فحص ساكن على المخرجات المشحونة (لا المصدر وحده) ==
  ✓ الشجرة المفحوصة هي public/ الفعليّة وفيها الطبقات المولَّدة
  ✓ صفر آلية تنسيق محجوبة في أي ملفّ مشحون
  ✓ الفاحص نفسه غير عبثيّ — يصطاد الآليات الثلاث في عيّنة مخالفة
  ✓ data-acs-style لا يُحسب خرقاً (وهو البديل المقصود)

== 3 · المولّدات ومخرجاتها متزامنة ==
  ✓ build_workspace_ui.py يعيد إنتاج مخرجه بايتاً ببايت (لا انحراف يدويّ)
  ✓ build_render_browser.py يعيد إنتاج مخرجه بايتاً ببايت (لا انحراف يدويّ)
  ✓ build_docs_browser.py يعيد إنتاج مخرجه بايتاً ببايت (لا انحراف يدويّ)
  ✓ build_bim_browser.py يعيد إنتاج مخرجه بايتاً ببايت (لا انحراف يدويّ)
  ✓ build_pbr_browser.py يعيد إنتاج مخرجه بايتاً ببايت (لا انحراف يدويّ)
  ✓ build_archdetail_browser.py يعيد إنتاج مخرجه بايتاً ببايت (لا انحراف يدويّ)
  ✓ build_runtime_browser.py يعيد إنتاج مخرجه بايتاً ببايت (لا انحراف يدويّ)
  ✓ build_authoring_browser.py يعيد إنتاج مخرجه بايتاً ببايت (لا انحراف يدويّ)

== 4 · هل workspace-ui-wiring.js مخرجٌ مولَّد؟ ==
  ✓ public/index.html فيها صفر سكربت مضمّن قابل للتنفيذ (مدخل المولّد استُهلك)
  ✓ frontend_analyze.segments على الصفحة الحالية لا تعيد مقاطع التطبيق
  ✓ لا أداة في tools/ تكتب ui/workspace-ui-wiring.js (ذِكرُه في تعليق ليس توليداً)

== 5 · السياسة الإنتاجية لم تُضعَّف ==
  ✓ netlify.toml ما زال يحوي style-src 'self' حرفياً
  ✓ لا 'unsafe-inline' في أي مكان من السياسة
  ✓ لا 'unsafe-eval' في أي مكان من السياسة
  ✓ لا توجيه style-src-attr ولا style-src-elem مُضاف
  ✓ لا 'unsafe-hashes' (وهو ما يعيد سمات style من الباب الخلفي)

  ! تعذّر تشغيل Chromium: no Chromium binary is available in this sandbox — searched: playwright-managed: /root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome | browser roots: /root/.cache/ms-playwright, /opt/pw-browsers

CSP STYLE ARCHITECTURE: 20 passed, 0 failed  (الطبقة الحيّة: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED)
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/remediation/test_csp_style_architecture.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/remediation/test_generation_cancel.py

Command: `bash tools/ci_run.sh --label audit-baseline --runner python3 tests/remediation/test_generation_cancel.py`; exit 1

```text
=== tests/remediation/test_generation_cancel.py ===

── أ · المسار السعيد ومسار الفشل ──
  ✓ _echo returns its value through a real child process
  ✓ the succeeded job declares state SUCCEEDED
  ✓ the succeeded job carries the request id
  ✓ stats().succeeded incremented by exactly one
  ✓ the slot is released after success
  ✓ _boom raises JobError, not a bare exception
  ✓ the JobError carries error_class == "RuntimeError"
  ✓ the child exception message survives the process boundary
  ✓ the failed job declares state FAILED
  ✓ stats().failed == 1 and succeeded unchanged
  ✓ the slot is released after failure

── ب · المزوّد المعلّق: مهلة حقيقية وعملية ابن ميّتة ──
  ✓ the hanging target raises TimeoutError
  ✓ the timeout is NOT downgraded to a JobError (OSError subclass trap)
  ✓ the timeout message names termination of the worker
  ✓ elapsed is close to the 1.5 s timeout, not the 600 s sleep
  ✓ the child recorded its own pid in the marker file
  ✓ the child pid is no longer alive after the timeout
  ✓ stats().timed_out == 1
  ✓ the timeout is not double-counted as a failure
  ✓ the job declares state TIMED_OUT
  ✓ the job records a finish time
  ✓ in_flight() == 0 after the timeout
  ✓ available() == capacity — the worker slot is recovered

── ج · لا عملية يتيمة ولا زومبي غير محصود ──
  ✓ no /proc entry survives for the abandoned job
  ✓ the child is not left as an un-reaped zombie
Traceback (most recent call last):
  File "/workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_generation_cancel.py", line 575, in <module>
    main()
  File "/workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_generation_cancel.py", line 542, in main
    section_hanging_provider(s)
  File "/workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_generation_cancel.py", line 281, in section_hanging_provider
    kids = psutil.Process().children(recursive=True)
           ^^^^^^^^^^^^^^^^
  File "/workspace/scratch/cc68e7a7ea83/acs-venv/lib/python3.12/site-packages/psutil/__init__.py", line 314, in __init__
    self._init(pid)
  File "/workspace/scratch/cc68e7a7ea83/acs-venv/lib/python3.12/site-packages/psutil/__init__.py", line 360, in _init
    raise NoSuchProcess(pid, msg=msg) from None
psutil.NoSuchProcess: process PID not found (pid=1788)
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/remediation/test_generation_cancel.py (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/remediation/test_generation_jobs_browser.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_generation_jobs_browser.js`; exit 1

```text
=== tests/remediation/test_generation_jobs_browser.js ===
browserType.launch: Executable doesn't exist at /root/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
╔════════════════════════════════════════════════════════════╗
║ Looks like Playwright was just installed or updated.       ║
║ Please run the following command to download new browsers: ║
║                                                            ║
║     npx playwright install                                 ║
║                                                            ║
║ <3 Playwright Team                                         ║
╚════════════════════════════════════════════════════════════╝
    at /workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_generation_jobs_browser.js:24:34 {
  log: [],
  name: 'Error'
}
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/remediation/test_generation_jobs_browser.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/remediation/test_generation_jobs_shipped_page.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_generation_jobs_shipped_page.js`; exit 1

```text
=== tests/remediation/test_generation_jobs_shipped_page.js ===
Error: no Chromium binary is available in this sandbox — searched: playwright-managed: /root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome | browser roots: /root/.cache/ms-playwright, /opt/pw-browsers
    at Object.launch (/workspace/scratch/cc68e7a7ea83/acs/tools/pw_chromium.js:164:11)
    at /workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_generation_jobs_shipped_page.js:55:20
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5)
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/remediation/test_generation_jobs_shipped_page.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/remediation/test_mobile_project_layout.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_mobile_project_layout.js`; exit 1

```text
=== tests/remediation/test_mobile_project_layout.js ===
Error: no Chromium binary is available in this sandbox — searched: playwright-managed: /root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome | browser roots: /root/.cache/ms-playwright, /opt/pw-browsers
    at Object.launch (/workspace/scratch/cc68e7a7ea83/acs/tools/pw_chromium.js:164:11)
    at /workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_mobile_project_layout.js:19:24
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5)
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/remediation/test_mobile_project_layout.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/remediation/test_pdf_runtime.mjs

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_pdf_runtime.mjs`; exit 1

```text
=== tests/remediation/test_pdf_runtime.mjs ===
node:internal/modules/esm/resolve:271
    throw new ERR_MODULE_NOT_FOUND(
          ^

Error [ERR_MODULE_NOT_FOUND]: Cannot find module '/workspace/scratch/cc68e7a7ea83/acs/public/vendor/pdfjs@4.10.38/pdf.min.mjs' imported from /workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_pdf_runtime.mjs
    at finalizeResolution (node:internal/modules/esm/resolve:271:11)
    at moduleResolve (node:internal/modules/esm/resolve:865:10)
    at defaultResolve (node:internal/modules/esm/resolve:992:11)
    at #cachedDefaultResolve (node:internal/modules/esm/loader:701:20)
    at #resolveAndMaybeBlockOnLoaderThread (node:internal/modules/esm/loader:721:38)
    at ModuleLoader.resolveSync (node:internal/modules/esm/loader:759:56)
    at #resolve (node:internal/modules/esm/loader:683:17)
    at ModuleLoader.getOrCreateModuleJob (node:internal/modules/esm/loader:603:35)
    at node:internal/modules/esm/loader:632:32
    at TracingChannel.tracePromise (node:diagnostics_channel:362:14) {
  code: 'ERR_MODULE_NOT_FOUND',
  url: 'file:///workspace/scratch/cc68e7a7ea83/acs/public/vendor/pdfjs@4.10.38/pdf.min.mjs'
}

Node.js v24.19.0
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/remediation/test_pdf_runtime.mjs (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/remediation/test_performance.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_performance.js`; exit 1

```text
=== tests/remediation/test_performance.js ===

== §1 — THE BUDGETS ARE DECLARED, AND DECLARED AS TARGETS ==
  ✓ tests/performance/budgets.json exists
  ✓ it parses as JSON
  ✓ it declares a schema
  ✓ its status says the budgets are TARGETS ONLY and NOT MEASURED
  ✓ measured === false at the top level
  ✓ it explains in words that a budget with no measurement is a promise, not a result
  ✓ it states NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED
  ✓ it names the real reason (empty public/vendor, no network)
  ✓ at least 12 individual budgets are declared
  ✓ every budget has an id, a metric, an operator, a numeric target and a unit
  ✓ EVERY budget is individually flagged measured:false — not one is presented as an achieved number
  ✓ every operator is a real comparison
  ✓ the required desktop budget exists: >= 45 fps on a MEDIUM fixture
  ✓ the required mid-range mobile navigation budget exists: >= 24 fps
  ✓ budget FRAME_TIME_P95_DESKTOP_MEDIUM is declared
  ✓ budget FRAME_TIME_P95_MOBILE is declared
  ✓ budget FIRST_VISIBLE_FRAME_MEDIUM is declared
  ✓ budget MODEL_BUILD_MEDIUM is declared
  ✓ budget THREE_INIT_DESKTOP is declared
  ✓ budget JS_PARSE_INIT_DESKTOP is declared
  ✓ budget FIRST_CONTENT_LOAD_DESKTOP is declared
  ✓ budget DRAW_CALLS_MEDIUM is declared
  ✓ budget TRIANGLES_MEDIUM is declared
  ✓ budget WEBGL_CONTEXT_COUNT is declared
  ✓ budget CONTEXT_LOSS_EVENTS is declared
  ✓ budget RENDER_LOOP_COUNT is declared
  ✓ budget DUPLICATE_EVENT_LISTENERS is declared
  ✓ budget GEOMETRIES_RETURN_TO_BASELINE is declared
  ✓ budget TEXTURES_RETURN_TO_BASELINE is declared
  ✓ budget HEAP_AFTER_20_PROJECT_SWITCHES is declared
  ✓ a p95 frame-time budget accompanies each fps budget, so an average cannot be reached by alternating fast and stalled frames
  ✓ context loss is budgeted at exactly zero
  ✓ the fixture classes name the required fixtures
  ✓ every budget offers a justification or is a self-evident zero

== §2 — THE QUALITY GOVERNOR CAN NEVER DROP SEMANTIC GEOMETRY ==
  ✓ tests/performance/quality_governor.json exists
  ✓ it parses as JSON
  ✓ the governor declares itself a specification, not an implementation
  ✓ it states plainly that it is not wired into public/index.html
  ✓ a MID_RANGE_MOBILE tier exists
  ✓ MID_RANGE_MOBILE declares an exact reduced shadow resolution
  ✓ MID_RANGE_MOBILE declares an exact reduced SSAO quality
  ✓ MID_RANGE_MOBILE declares an exact lower device-pixel-ratio cap
  ✓ MID_RANGE_MOBILE declares an exact reduced context LOD
  ✓ every mobile parameter delta is written down with its reasoning
  ✓ the reduced context LOD is explicitly scoped to DECORATIVE, non-canonical dressing only — never to model geometry
  ✓ the invariant is stated in words a reviewer can hold the code to
  ✓ the protected element classes cover the load-bearing and life-safety elements
  ✓ every tier declares removes_semantic_geometry:false
  ✓ every tier declares writes_to_model:false
  ✓ THE SPEC PASSES ITS OWN VALIDATION CONTRACT — no tier permits dropping semantic geometry
  ✓ even the MINIMUM_SAFE last-resort tier removes no geometry
  ✓ tier switching declares hysteresis, so the governor cannot oscillate
  ✓ the governor states that no tier was measured here

  -- the validator is not vacuous: hostile specs must fail --
  ✓ the validator rejects a tier that admits it removes semantic geometry
  ✓ the validator rejects a tier that writes to the model
  ✓ the validator rejects a parameter that culls walls
  ✓ the validator rejects a parameter that drops rooms
  ✓ the validator rejects a parameter that decimates geometry
  ✓ the validator rejects a parameter that hides MEP
  ✓ the validator rejects a parameter that skips element classes
  ✓ the validator rejects an innocuous-looking parameter outside the allowlist
  ✓ the validator rejects a weakened top-level invariant
  ✓ the validator rejects a governor that may change the model hash
  ✓ the validator rejects a tier-level removal switch

== §3 — THE HARNESS EXITS 2, NOT 0, WHEN IT CANNOT MEASURE ==
  ✓ tests/performance/run_perf.js exists
  ✓ it declares NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED in the source
  ✓ it can never exit 0 on the not-verified path (process.exit(2) is the only exit in notVerified)
  ✓ the harness implements a measurement for first content load
  ✓ the harness implements a measurement for JS parse/init
  ✓ the harness implements a measurement for Three init
  ✓ the harness implements a measurement for model build
  ✓ the harness implements a measurement for first visible frame
  ✓ the harness implements a measurement for FPS average
  ✓ the harness implements a measurement for frame-time p5
  ✓ the harness implements a measurement for frame-time p95
  ✓ the harness implements a measurement for draw calls
  ✓ the harness implements a measurement for triangles
  ✓ the harness implements a measurement for JS heap
  ✓ the harness implements a measurement for memory after repeated loads
  ✓ the harness implements a measurement for memory after dispose
  ✓ the harness implements a measurement for WebGL context count
  ✓ the harness implements a measurement for context loss events
  ✓ the harness implements a measurement for geometry disposal via renderer.info.memory
  ✓ the harness implements a measurement for texture disposal
  ✓ the harness implements a measurement for duplicate render loops
  ✓ the harness implements a measurement for duplicate event listeners
  ✓ leak scenario SWITCH_20_PROJECTS is implemented
  ✓ leak scenario PBR_ENTER_EXIT is implemented
  ✓ leak scenario CONTEXT_LANDSCAPE_TOGGLE is implemented
  ✓ leak scenario SCREENSHOT_CREATE_DISPOSE is implemented
  ✓ leak scenario VR_ENTER_EXIT is implemented
  ✓ fixture villa is present in the harness
  ✓ fixture apartment is present in the harness
  ✓ fixture hotel is present in the harness
  ✓ fixture clinic is present in the harness
  ✓ fixture warehouse is present in the harness
  ✓ fixture spaces_100 is present in the harness
  ✓ fixture spaces_500 is present in the harness
  ✓ fixture spaces_1000 is present in the harness
  ✓ fixture live_large_generated is present in the harness
  ✓ the real fixtures are read from the repository, not re-typed
  (running the harness for real — this takes ~30 s)
```

### tests/remediation/test_plan_review_ui.cjs

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_plan_review_ui.cjs`; exit 1

```text
=== tests/remediation/test_plan_review_ui.cjs ===
browserType.launch: Executable doesn't exist at /root/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
╔════════════════════════════════════════════════════════════╗
║ Looks like Playwright was just installed or updated.       ║
║ Please run the following command to download new browsers: ║
║                                                            ║
║     npx playwright install                                 ║
║                                                            ║
║ <3 Playwright Team                                         ║
╚════════════════════════════════════════════════════════════╝
    at /workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_plan_review_ui.cjs:82:34 {
  log: [],
  name: 'Error'
}
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/remediation/test_plan_review_ui.cjs (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/remediation/test_scene_benchmark.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_scene_benchmark.js`; exit 1

```text
=== tests/remediation/test_scene_benchmark.js ===
Error: no Chromium binary is available in this sandbox — searched: playwright-managed: /root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome | browser roots: /root/.cache/ms-playwright, /opt/pw-browsers
    at Object.launch (/workspace/scratch/cc68e7a7ea83/acs/tools/pw_chromium.js:164:11)
    at main (/workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_scene_benchmark.js:208:28)
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5)
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/remediation/test_scene_benchmark.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/remediation/test_transport_browser.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_transport_browser.js`; exit 1

```text
=== tests/remediation/test_transport_browser.js ===
Error: no Chromium binary is available in this sandbox — searched: playwright-managed: /root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome | browser roots: /root/.cache/ms-playwright, /opt/pw-browsers
    at Object.launch (/workspace/scratch/cc68e7a7ea83/acs/tools/pw_chromium.js:164:11)
    at main (/workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_transport_browser.js:36:20)
    at process.processTicksAndRejections (node:internal/process/task_queues:104:5)
TRANSPORT CHROMIUM: 0 passed, 1 failed
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/remediation/test_transport_browser.js (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### tests/remediation/test_webgl_diagnostics.js

Command: `bash tools/ci_run.sh --label audit-baseline --runner 'node tests/lib/run.js' tests/remediation/test_webgl_diagnostics.js`; exit 124

```text
=== tests/remediation/test_webgl_diagnostics.js ===

== §1 — THE DIAGNOSTICS CONTRACT SHIPS IN THE HAND-WRITTEN MODULE ==
  ✓ the block exists exactly once in the shipped application code
  ✓ the block carries real code, not a stub
  ✓ the block lives OUTSIDE every generated block, so a regenerate cannot overwrite it
  ✓ the block lives in exactly ONE shipped module
  ✓ that module is imported by public/app/main.js in the boot order — an orphaned file would ship but never run
  ✓ the shell carries no copy of it: the page is a shell, the code is a module

== §2 — NO NETWORK PATH IN captureRenderFailure (STATIC) ==
  ✓ the capture function was located in the shipped page
  ✓ captureRenderFailure contains no `fetch(`
  ✓ captureRenderFailure contains no `fetch (`
  ✓ captureRenderFailure contains no `XMLHttpRequest`
  ✓ captureRenderFailure contains no `sendBeacon`
  ✓ captureRenderFailure contains no `WebSocket`
  ✓ captureRenderFailure contains no `EventSource`
  ✓ captureRenderFailure contains no `navigator.connection`
  ✓ captureRenderFailure contains no `.submit(`
  ✓ captureRenderFailure contains no `form.action`
  ✓ captureRenderFailure contains no `importScripts`
  ✓ captureRenderFailure contains no `new Worker`
  ✓ captureRenderFailure contains no absolute URL of any scheme
  ✓ it produces the file the declared way: Blob + createObjectURL + a local download anchor
  ✓ it revokes the object URL instead of leaking it
  ✓ it states in its own output that nothing was transmitted
  ✓ the static scan is not vacuous: the same scan DOES find network calls elsewhere in the application code

== §3 — THE CONTRACT RETURNS EXACTLY ITS DECLARED KEYS ==
  ✓ the diagnostics block evaluates in a controlled scope
  ✓ renderDiagnostics is a function
  ✓ captureRenderFailure is a function
  ✓ every required key is present (24)
  ✓ there is NO key beyond the declared contract
  ✓ the key set is exactly the declared set

== §4 — EVERY VALUE IS MEASURED, NOT FABRICATED ==
  ✓ build_sha comes from window.ACS_BUILD_INFO
  ✓ model_hash and revision_id come from the canonical model, not invented
  ✓ canvas_size is read from the real canvas backing and CSS size
  ✓ device_pixel_ratio is the browser value, not 1
  ✓ webgl_version comes from renderer.capabilities
  ✓ renderer is the string the GL context reports
  ✓ object_count counts EVERY scene object, not only meshes
  ✓ mesh_count counts meshes only
  ✓ draw_calls comes from renderer.info.render.calls
  ✓ triangle_count comes from renderer.info.render.triangles
  ✓ scene_bounds is the real union of the walked mesh boxes
  ✓ scene_bounds records how many meshes it actually measured
  ✓ camera_position and camera_target are read from the live camera and orbit target
  ✓ near and far are the live clip planes
  ✓ frustum_intersections is counted against a real frustum test
  ✓ invalid_coordinate_count is zero for a healthy scene
  ✓ max_coordinate_abs is the true largest absolute bound
  ✓ render_mode reflects the state actually applied
  ✓ postprocessing reports the real composer state
  ✓ xr_state is read from renderer.xr
  ✓ context_lost is read from the GL context
  ✓ the scene world matrices were updated BEFORE anything was measured

== §5 — THE PIXEL PROBE READS REAL PIXELS ==
  ✓ the probe used readPixels on the framebuffer
  ✓ it sampled the real canvas area (57600)
  ✓ the non-zero pixel count matches the pattern exactly (one in four)
  ✓ the non-zero percentage is computed, not assumed
  ✓ the mean luminance matches the pattern to three decimals
  ✓ the maximum luminance is the real per-pixel maximum
  ✓ viewportBlank calls the probe a non-blank viewport at 25% coverage

== §6 — WHAT CANNOT BE MEASURED IS null, NEVER A NUMBER ==
  ✓ an absent ACS_BUILD_INFO yields build_sha null, not a placeholder
  ✓ no loaded model yields model_hash and revision_id null
  ✓ absent renderer capabilities yield webgl_version null, not 1
  ✓ absent renderer.info yields draw_calls and triangle_count null, not 0
  ✓ a failing readPixels yields null pixel numbers and a stated reason, never an invented count
  ✓ the contract key set is unchanged in the degraded case
  ✓ viewportBlank reports null — not "fine" — when it cannot see pixels
  ✓ a lost context is reported as lost, and the probe says so
  ✓ a non-finite mesh bound is COUNTED as invalid, not silently averaged in
  ✓ and it does not poison the reported bounds

== §7 — captureRenderFailure UPLOADS NOTHING (EXECUTED) ==
  ✓ the capture ran and produced a report
  ✓ not one network primitive was called during the capture
  ✓ the trap is not vacuous: calling the trapped fetch DOES register
  ✓ the report states no upload happened and names no upload target
  ✓ a Blob was created and an object URL handed to a local download anchor
  ✓ the report carries the fixed-key diagnostics
  ✓ the report carries the camera configuration and the render mode
  ✓ the report carries the current Building JSON when it is safe to attach
  ✓ the report carries the build identity
  ✓ the report says whether the viewport was blank, measured not assumed
  ✓ with no model loaded the Building JSON is omitted WITH a stated reason
  ✓ the produced JSON is valid JSON and self-describing

== §8 — THE BUILD IDENTITY IS A PLACEHOLDER, NOT A FAKE ==
  ✓ the build-identity script ships as a classic boot script file
  ✓ the exact substitution token __ACS_GIT_SHA__ ships in the build-identity boot script
  ✓ the exact substitution token __ACS_BUILT_AT__ ships in the build-identity boot script
  ✓ the exact substitution token __ACS_FRONTEND_VERSION__ ships in the build-identity boot script
  ✓ window.ACS_BUILD_INFO is defined by a classic <head> script that the shell loads BEFORE the application module
  ✓ the boot script is classic, not a module — it must run before the module graph, and a deferred module would be too late
  ✓ an unsubstituted build reports null for every field and declares itself UNPROVENANCED
  ✓ a substituted build reports the real values and declares itself provenanced

== §9 — THE VISIBLE, KEYBOARD-REACHABLE UI ACTION ==
  ✓ the download action exists in the hand-written DOM
  ✓ it is a real <button>, so it is focusable and Enter/Space activate it natively
  ✓ it is not hidden from the keyboard or the accessibility tree
  ✓ it carries both labels: تنزيل التشخيص and Download diagnostics
  ✓ it carries an aria-label
  ✓ the action lives OUTSIDE every generated DOM block
  ✓ the build identifier is rendered in a visible system-info area
  ✓ the status line is announced to assistive technology
  ✓ the page tells the user the file is not uploaded anywhere
  ✓ the download action carries NO inline event-handler attribute — the strict CSP would make one dead code

== §10 — F-07 PARITY: ONE PLATE CONTRACT IN BOTH LANGUAGES ==
  ✓ the browser policy mirror is byte-identical to the Python source
  ✓ the policy names the new convention and records the old one
  ✓ pqPlatePolicy is exposed on the browser contract surface
  ✓ plate_rect parity, case 1: same source and same rectangle
  ✓ plate_rect parity, case 2: same source and same rectangle
  ✓ plate_rect parity, case 3: same source and same rectangle
  ✓ plate_rect parity, case 4: same source and same rectangle
  ✓ slab strip parity, case 1: identical strips, same order
  ✓ slab strip parity, case 2: identical strips, same order
  ✓ slab strip parity, case 3: identical strips, same order
  ✓ slab strip parity, case 4: identical strips, same order

== §11 — THE PLATE CHANGE IS CONFINED TO SLAB MESHES ==
  ✓ the pre-change geometry baseline is archived beside the tests
  ✓ both baselines cover the same models
  ✓ the change moved real geometry (it is not a no-op)
  ✓ NOT ONE non-slab mesh changed name, visibility, position, size or rotation

== §12 — THE NINE RENDER STATES: WHAT IS AND IS NOT VERIFIED ==
  ✓ the existing browser matrix was EXTENDED with the state: BASE (no presentation layer applied)
  ✓ the existing browser matrix was EXTENDED with the state: PBR OFF / DETAIL OFF
  ✓ the existing browser matrix was EXTENDED with the state: PBR ON (HIGH, REALISTIC, SKY)
  ✓ the existing browser matrix was EXTENDED with the state: POST PROCESS (ULTRA, composer + SSAO)
  ✓ the existing browser matrix was EXTENDED with the state: ARCHDETAIL STANDARD / CONTEXT NONE
  ✓ the existing browser matrix was EXTENDED with the state: CONTEXT SITE
  ✓ the existing browser matrix was EXTENDED with the state: CONTEXT LANDSCAPE
  ✓ the existing browser matrix was EXTENDED with the state: ENGINEERING (compare mode restored)
  ✓ the existing browser matrix was EXTENDED with the state: VR-CAPABLE FALLBACK (xr enabled, not presenting)
  ✓ the extended matrix asserts non-zero visible pixels per state
  ✓ the extended matrix asserts no NaN or infinite camera per state
  ✓ the extended matrix asserts valid scene bounds per state
  ✓ the extended matrix asserts the fixed-key contract per state
  ✓ no parallel matrix was created: the states live in the existing harness
  ✓ the harness refuses to pass without a real renderer: it exits 2 rather than claiming a result
  ── vendored Three.js present: false
  NINE RENDER STATES: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED
  reason: public/vendor is empty and this sandbox has no network, so Three.js cannot load and no frame can be rendered.
  no pixel was rendered for those states here and none is claimed. Run: sh tools/vendor.sh && node tests/deploy/verify_page_boot.js

== §13 — REAL CHROMIUM: WHAT DOES NOT NEED THREE.js ==

AUDIT HARNESS: timeout after 120 seconds
```

### tests/remediation/test_workspace_viewport_selection_browser.cjs

Command: `bash tools/ci_run.sh --label audit-baseline --runner node tests/remediation/test_workspace_viewport_selection_browser.cjs`; exit 1

```text
=== tests/remediation/test_workspace_viewport_selection_browser.cjs ===
browserType.launch: Executable doesn't exist at /root/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
╔════════════════════════════════════════════════════════════╗
║ Looks like Playwright was just installed or updated.       ║
║ Please run the following command to download new browsers: ║
║                                                            ║
║     npx playwright install                                 ║
║                                                            ║
║ <3 Playwright Team                                         ║
╚════════════════════════════════════════════════════════════╝
    at /workspace/scratch/cc68e7a7ea83/acs/tests/remediation/test_workspace_viewport_selection_browser.cjs:53:34 {
  log: [],
  name: 'Error'
}
──────────────────────────────────────────────────────────────
ci_run · audit-baseline: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/remediation/test_workspace_viewport_selection_browser.cjs (exit 1)

::error::1 target(s) in 'audit-baseline' failed — this job cannot pass
```

### 09-doc-claims

Command: `python3 tools/check_doc_claims.py`; exit 1

```text
  ✓ كتلة الحالة الراهنة تطابق القياس.

فحص 10 ادّعاءً في التوثيق بتشغيل حزمها فعلاً…

  ✓  tests/remediation/test_plan_chunking.py            72
  ✓  tests/remediation/test_provider_integration.py     56
  ?  tests/remediation/test_csp_style_architecture.js   64     suite exited 1:   ! تعذّر تشغيل Chromium: no Chromium binary is available in this sandbox — searched: playwright-managed: /root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome | browser roots: /root/.cache/ms-playwright, /opt/pw-browsers |  | CSP 
  ✓  tests/remediation/test_plate_extent.py             159
  ✓  tests/remediation/test_module_graph.js             43
  ✓  tests/remediation/test_bundle_report.py            94
  ~  tests/remediation/test_panel_entry.js              37     الحزمة أعلنت قياساً جزئياً بلا طبقتها الحيّة
  ✓  tests/remediation/test_multi_provider.py           111
  ✓  tests/remediation/test_validate_against_real_models.py 8
  ✓  tests/remediation/test_validate_topology.py        28

DOC CLAIMS FAILED: 1 suite(s) could not be measured successfully.
DOC CLAIMS FAILED: 1 suite(s) require an unavailable environment.
```

### tests/phase1/test_gate.js (corrected runner)

Command: `bash tools/ci_run.sh --label phase1-correct-runner --runner node tests/lib/run.js tests/phase1/test_gate.js`; exit 1

```text
=== tests/phase1/test_gate.js ===

== GATE #6: object preservation — new example "اثنين AMR" ==
   {"forklift":1,"worker":6,"amr":2}
  ✓ worker=6
  ✓ amr=2 (not robot+amr)
  ✓ forklift=1
  ✓ dropped=0 (3 kinds)

== GATE #7: coverage categories distinct (never merged) ==
  meta.requirements: ["6 عمّال"]
  meta.excluded:     ["رافعات"]
  ✓ workers in REQUESTED
  ✓ forklift in EXCLUDED
  ✓ forklift NOT in REQUESTED (not silently added)
  ✓ REQUESTED and EXCLUDED are separate arrays

== render: EXCLUDED not shown under "represented alternatively" ==
<anonymous_script>:25517
  const box=document.getElementById('reportBox'); if(!box) return;
            ^

ReferenceError: document is not defined
    at showReport (eval at run (/workspace/scratch/cc68e7a7ea83/acs/tests/lib/run.js:19:12), <anonymous>:25517:13)
    at eval (eval at run (/workspace/scratch/cc68e7a7ea83/acs/tests/lib/run.js:19:12), <anonymous>:25757:1)
    at run (/workspace/scratch/cc68e7a7ea83/acs/tests/lib/run.js:21:3)
    at Object.<anonymous> (/workspace/scratch/cc68e7a7ea83/acs/tests/lib/run.js:26:3)
    at Module._compile (node:internal/modules/cjs/loader:1872:14)
    at Object..js (node:internal/modules/cjs/loader:2003:10)
    at Module.load (node:internal/modules/cjs/loader:1594:32)
    at Module._load (node:internal/modules/cjs/loader:1396:12)
    at wrapModuleLoad (node:internal/modules/cjs/loader:255:19)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)

Node.js v24.19.0
──────────────────────────────────────────────────────────────
ci_run · phase1-correct-runner: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/phase1/test_gate.js (exit 1)

::error::1 target(s) in 'phase1-correct-runner' failed — this job cannot pass
```

### tests/phase1/test_prov.js (corrected runner)

Command: `bash tools/ci_run.sh --label phase1-correct-runner --runner node tests/lib/run.js tests/phase1/test_prov.js`; exit 1

```text
=== tests/phase1/test_prov.js ===

== TEST A — VILLA FLOORS (user=2, model=3) ==
  ✓ requestedFloorsFromText("فيلا دورين…") === 2
  ✓ floors claim NOT under USER_REQUESTED
  ✓ floors claim reclassified to SYSTEM
  ✓ states user requested 2
  ✓ report exposes requested floors = 2
  ✓ genuine user item (مجلس) stays USER

== TEST B — ROOF (auto) ==
  ✓ roof → SYSTEM (not USER, not RULE)
  ✓ no "وفق الكود" in text
  ✓ source=system_default

== TEST C — SMOKE DETECTOR ==
  ✓ smoke → SYSTEM/AUTO_ADDED
  ✓ no "إصلاح:" framing
  ✓ CODE_REQUIRED count = 0

== TEST D — STAIR CONNECTIVITY ==
  ✓ no "يربط الطوابق" claim
  ✓ uses visual-representation wording

== TEST E — PARKING (represented alternatively) ==
  ✓ cars = 2, dropped = 0
  ✓ appears under REPRESENTED_ALTERNATIVELY
  ✓ not reported as unsupported

== TEST F — EXPLICIT EXCLUSION (بدون مصعد) ==
  ✓ elevator EXCLUDED
  ✓ elevator NOT in AUTO_ADDED/system
  ✓ elevator NOT in CODE_REQUIRED
  ✓ elevator NOT generated as object

== TEST G — AI INFERENCE (number user never stated) ==
  ✓ unproven number → AI_INFERRED not USER
  ✓ source=ai_inference

== TEST H — CODE_REQUIRED gated on real evidence ==
  ✓ no evidence ⇒ hasRuleEvidence=false
  ✓ partial evidence ⇒ false
  ✓ CODE_REQUIRED count = 0 in Phase 1
  ✓ full FIELDS but rule not loaded ⇒ rejected
  ✓ registry holds zero regulatory rules
  ✓ synthetic TEST_ONLY rule can never open the gate
  ✓ loaded + verified regulatory rule ⇒ CODE_REQUIRED accepted
  ✓ unverified source ⇒ gate closes again

== RENDER — no forbidden phrases + distinct sections ==
<anonymous_script>:25517
  const box=document.getElementById('reportBox'); if(!box) return;
            ^

ReferenceError: document is not defined
    at showReport (eval at run (/workspace/scratch/cc68e7a7ea83/acs/tests/lib/run.js:19:12), <anonymous>:25517:13)
    at eval (eval at run (/workspace/scratch/cc68e7a7ea83/acs/tests/lib/run.js:19:12), <anonymous>:25825:1)
    at run (/workspace/scratch/cc68e7a7ea83/acs/tests/lib/run.js:21:3)
    at Object.<anonymous> (/workspace/scratch/cc68e7a7ea83/acs/tests/lib/run.js:26:3)
    at Module._compile (node:internal/modules/cjs/loader:1872:14)
    at Object..js (node:internal/modules/cjs/loader:2003:10)
    at Module.load (node:internal/modules/cjs/loader:1594:32)
    at Module._load (node:internal/modules/cjs/loader:1396:12)
    at wrapModuleLoad (node:internal/modules/cjs/loader:255:19)
    at Module.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:154:5)

Node.js v24.19.0
──────────────────────────────────────────────────────────────
ci_run · phase1-correct-runner: 0 passed, 1 failed, 1 total
FAILED TARGETS:
tests/phase1/test_prov.js (exit 1)

::error::1 target(s) in 'phase1-correct-runner' failed — this job cannot pass
```

## Requested historical snapshot — exact command results

The requested original command sequence was also executed without application changes on 9e3e472. The exhaustive repair comparison uses adec616 above.

### python3 tools/check_integration.py — exit 0

```text
✓ integration gate: every layer declares viewport-safety/1.0.0 (spec, python, browser mirror, bridge, shipped app modules under public/app/, the index shell markup, boot/build-info.js tokens, tests)
```

### python3 tools/check_index_guard.py public/index.html — exit 0

```text
✓ index guard: shell 47424 bytes (max 204800) · 8 referenced assets all resolve · zero inline JS, zero inline style · 27 modules under /app/ (20 imported by main.js), largest core/standards.js at 228701 B (cap 307200, allow-list empty) · importmap valid · engine init present · all 10 generated block pairs intact across the modules
```

### python3 tools/check_api_base.py — exit 0

```text
✓ API base: one authoritative origin https://acs-engine.onrender.com declared in public/app/boot/api-base.js · all 4 /v1 endpoint(s) routed through acsFetchJSON in public/app/ · CSP connect-src allows it
```

### python3 tools/check_csp_hash.py — exit 0

```text
✓ CSP importmap hash: sha256-kmeUkbmn7TSoFc+bR+iKEW0CLiuQIqi5X7Op3y+XBkA= · identical in the page (131 B), public/app/importmap.sha256 and netlify.toml script-src
```

### python3 tests/deploy/verify_deploy.py — exit 0

```text

== 0 · THE APPLICATION PAGE GUARD (EMPTY-PAGE REMEDIATION) ==
  ✓ public/index.html passes the structural guard
  ✓ the netlify build runs the same guard before publishing
  ✓ guard self-test harness: an UNMUTATED copy of the published tree passes, so the guard really reads the tree it is pointed at
  ✓ guard self-test: an EMPTY page is refused
  ✓ guard self-test: a truncated page is refused
  ✓ guard self-test: a stub page is refused
  ✓ guard self-test: and it says WHY the stub is refused, in bytes or structure — not a bare non-zero exit
  ✓ guard self-test: a missing importmap is refused
  ✓ guard self-test: an importmap with invalid JSON is refused
  ✓ guard self-test: an importmap pointing at a CDN is refused
  ✓ guard self-test: a missing application entry (<script type=module src>) is refused
  ✓ guard self-test: a deleted application entry MODULE is refused — the page would serve a 404 to its own entry point
  ✓ guard self-test: missing THREE import is refused (declared engine needle)
  ✓ guard self-test: missing scene initialization is refused (declared engine needle)
  ✓ guard self-test: missing renderer initialization is refused (declared engine needle)
  ✓ guard self-test: missing camera initialization is refused (declared engine needle)
  ✓ guard self-test: missing render loop is refused (declared engine needle)
  ✓ guard self-test: a missing generated end-marker is refused: /* ===== END ACS RUNTIME LAYER ===== */
  ✓ guard self-test: a DUPLICATED generated end-marker is refused: /* ===== END ACS RUNTIME LAYER ===== */
  ✓ guard self-test: a missing generated end-marker is refused: /* ===== END ACS AUTHORING LAYER ===== */
  ✓ guard self-test: a DUPLICATED generated end-marker is refused: /* ===== END ACS AUTHORING LAYER ===== */
  ✓ guard self-test: a missing generated end-marker is refused: /* ===== END ACS WORKSPACE UI ===== */
  ✓ guard self-test: a DUPLICATED generated end-marker is refused: /* ===== END ACS WORKSPACE UI ===== */
  ✓ guard self-test: a missing generated end-marker is refused: /* ===== END ACS RENDER ENGINE ===== */
  ✓ guard self-test: a DUPLICATED generated end-marker is refused: /* ===== END ACS RENDER ENGINE ===== */
  ✓ guard self-test: a missing generated end-marker is refused: /* ===== END ACS BIM EXCHANGE ===== */
  ✓ guard self-test: a DUPLICATED generated end-marker is refused: /* ===== END ACS BIM EXCHANGE ===== */
  ✓ guard self-test: a missing generated end-marker is refused: /* ===== END ACS DOCUMENTATION ===== */
  ✓ guard self-test: a DUPLICATED generated end-marker is refused: /* ===== END ACS DOCUMENTATION ===== */
  ✓ guard self-test: a missing generated end-marker is refused: /* ===== END ACS PBR QUALITY ===== */
  ✓ guard self-test: a DUPLICATED generated end-marker is refused: /* ===== END ACS PBR QUALITY ===== */
  ✓ guard self-test: a missing generated end-marker is refused: /* ===== END ACS PBR BRIDGE ===== */
  ✓ guard self-test: a DUPLICATED generated end-marker is refused: /* ===== END ACS PBR BRIDGE ===== */
  ✓ guard self-test: a missing generated end-marker is refused: /* ===== END ACS ARCH DETAIL ===== */
  ✓ guard self-test: a DUPLICATED generated end-marker is refused: /* ===== END ACS ARCH DETAIL ===== */
  ✓ guard self-test: a missing generated end-marker is refused: /* ===== END ACS ARCH DETAIL BRIDGE ===== */
  ✓ guard self-test: a DUPLICATED generated end-marker is refused: /* ===== END ACS ARCH DETAIL BRIDGE ===== */
  ✓ guard self-test: a missing file path is refused
  ✓ the guard checks every phase layer structurally (10 marker pairs)
  · the guard self-tests run the guard as the build runs it (python3 tools/check_index_guard.py public/index.html) against a mutated copy of tools/ + public/, covering all 5 engine needles and all 10 marker pairs

== 1 · REQUIRED DEPLOYMENT FILES EXIST ==
  ✓ Dockerfile is present
  ✓ render.yaml is present
  ✓ netlify.toml is present
  ✓ requirements.txt is present
  ✓ public/index.html is present
  ✓ tools/netlify-build.sh is present
  ✓ tools/vendor.sh is present

== 2 · BROWSER INJECTORS AND THEIR CANONICAL SPECS ==
  ✓ tools/build_visual_browser.py is present
  ✓ acs_visual.json is present
  ✓ tools/build_runtime_browser.py is present
  ✓ acs_runtime.json is present
  ✓ tools/build_authoring_browser.py is present
  ✓ acs_authoring.json is present
  ✓ tools/build_workspace_ui.py is present
  ✓ acs_workspace.json is present
  ✓ tools/build_render_browser.py is present
  ✓ acs_render.json is present
  ✓ tools/build_bim_browser.py is present
  ✓ acs_bim.json is present
  ✓ tools/build_docs_browser.py is present
  ✓ acs_docs.json is present
  ✓ tools/build_pbr_browser.py is present
  ✓ acs_pbr.json is present
  ✓ tools/build_archdetail_browser.py is present
  ✓ acs_archdetail.json is present

== 3 · THE BACKEND IMPORT CLOSURE IS ACTUALLY COPIED BY THE DOCKERFILE ==
  · the deployed API entrypoint is acs_understand_api.py
  · its transitive closure is 20 module(s): acs_api_errors.py, acs_arch.py, acs_build_info.py, acs_cpu_pool.py, acs_engineering_authority.py, acs_generation.py, acs_generation_job.py, acs_ingest.py, acs_layout.py, acs_logging.py, acs_opening_identity.py, acs_plan_chunks.py, acs_programs.py, acs_provider.py, acs_rate_limit.py, acs_rules.py, acs_understand.py, acs_understand_api.py, acs_upload_security.py, acs_validate.py
  ✓ the Dockerfile copies acs_api_errors.py (required at runtime)
  ✓ the Dockerfile copies acs_arch.py (required at runtime)
  ✓ the Dockerfile copies acs_build_info.py (required at runtime)
  ✓ the Dockerfile copies acs_cpu_pool.py (required at runtime)
  ✓ the Dockerfile copies acs_engineering_authority.py (required at runtime)
  ✓ the Dockerfile copies acs_generation.py (required at runtime)
  ✓ the Dockerfile copies acs_generation_job.py (required at runtime)
  ✓ the Dockerfile copies acs_ingest.py (required at runtime)
  ✓ the Dockerfile copies acs_layout.py (required at runtime)
  ✓ the Dockerfile copies acs_logging.py (required at runtime)
  ✓ the Dockerfile copies acs_opening_identity.py (required at runtime)
  ✓ the Dockerfile copies acs_plan_chunks.py (required at runtime)
  ✓ the Dockerfile copies acs_programs.py (required at runtime)
  ✓ the Dockerfile copies acs_provider.py (required at runtime)
  ✓ the Dockerfile copies acs_rate_limit.py (required at runtime)
  ✓ the Dockerfile copies acs_rules.py (required at runtime)
  ✓ the Dockerfile copies acs_understand.py (required at runtime)
  ✓ the Dockerfile copies acs_understand_api.py (required at runtime)
  ✓ the Dockerfile copies acs_upload_security.py (required at runtime)
  ✓ the Dockerfile copies acs_validate.py (required at runtime)
  ✓ the Dockerfile copies acs_arch.json (required at runtime)
  ✓ the Dockerfile copies acs_engineering_changes.json (required at runtime)
  ✓ the Dockerfile copies acs_ingest.json (required at runtime)
  ✓ the Dockerfile copies acs_programs.json (required at runtime)
  ✓ the Dockerfile copies acs_rules.json (required at runtime)
  ✓ the Dockerfile copies acs_sources.json (required at runtime)
  ✓ the Dockerfile installs the declared dependencies
  ✓ the Dockerfile launches the real entrypoint
  ✓ the container port is taken from the platform, not hardcoded
  · 12 module(s) are in the image but not reachable from the API entrypoint: acs_coord, acs_distance, acs_egress, acs_fls, acs_mep, acs_navigation, acs_occupancy, acs_project, acs_relations, acs_revision, acs_struct, acs_visual
  · 10 module(s) are browser-mirrored only and intentionally absent from the image: acs_archdetail, acs_authoring, acs_bim, acs_compiler, acs_docs, acs_engineering_approval, acs_pbr, acs_render, acs_runtime, acs_workspace
  ✓ no module the API needs is missing from the image

== 4 · THE PUBLISHED FRONTEND CARRIES EVERY GENERATED BROWSER BLOCK ==
  ✓ marker definitions were found in the injectors
  ✓ the published frontend carries exactly one /* ===== ACS RUNTIME LAYER (generated by tools/build_runti…
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS RUNTIME LAYER (generated by tools/build_runti…
  ✓ the published frontend carries exactly one /* ===== END ACS RUNTIME LAYER ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS RUNTIME LAYER ===== */
  ✓ the published frontend carries exactly one /* ===== ACS AUTHORING LAYER (generated by tools/build_aut…
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS AUTHORING LAYER (generated by tools/build_aut…
  ✓ the published frontend carries exactly one /* ===== END ACS AUTHORING LAYER ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS AUTHORING LAYER ===== */
  ✓ the published frontend carries exactly one /* ===== ACS WORKSPACE UI (generated by tools/build_worksp…
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS WORKSPACE UI (generated by tools/build_worksp…
  ✓ the published frontend carries exactly one /* ===== END ACS WORKSPACE UI ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS WORKSPACE UI ===== */
  ✓ the published frontend carries exactly one /* ===== ACS WORKSPACE STYLES (generated) ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS WORKSPACE STYLES (generated) ===== */
  ✓ the published frontend carries exactly one /* ===== END ACS WORKSPACE STYLES ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS WORKSPACE STYLES ===== */
  ✓ the published frontend carries exactly one <!-- ===== ACS WORKSPACE DOM (generated) ===== -->
  ✓ and it is in a file the browser actually evaluates: <!-- ===== ACS WORKSPACE DOM (generated) ===== -->
  ✓ the published frontend carries exactly one <!-- ===== END ACS WORKSPACE DOM ===== -->
  ✓ and it is in a file the browser actually evaluates: <!-- ===== END ACS WORKSPACE DOM ===== -->
  ✓ the published frontend carries exactly one /* ===== ACS RENDER ENGINE (generated by tools/build_rende…
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS RENDER ENGINE (generated by tools/build_rende…
  ✓ the published frontend carries exactly one /* ===== END ACS RENDER ENGINE ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS RENDER ENGINE ===== */
  ✓ the published frontend carries exactly one /* ===== ACS RENDER STYLES (generated) ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS RENDER STYLES (generated) ===== */
  ✓ the published frontend carries exactly one /* ===== END ACS RENDER STYLES ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS RENDER STYLES ===== */
  ✓ the published frontend carries exactly one <!-- ===== ACS RENDER DOM (generated) ===== -->
  ✓ and it is in a file the browser actually evaluates: <!-- ===== ACS RENDER DOM (generated) ===== -->
  ✓ the published frontend carries exactly one <!-- ===== END ACS RENDER DOM ===== -->
  ✓ and it is in a file the browser actually evaluates: <!-- ===== END ACS RENDER DOM ===== -->
  ✓ the published frontend carries exactly one /* ===== ACS BIM EXCHANGE (generated by tools/build_bim_br…
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS BIM EXCHANGE (generated by tools/build_bim_br…
  ✓ the published frontend carries exactly one /* ===== END ACS BIM EXCHANGE ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS BIM EXCHANGE ===== */
  ✓ the published frontend carries exactly one /* ===== ACS BIM STYLES (generated) ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS BIM STYLES (generated) ===== */
  ✓ the published frontend carries exactly one /* ===== END ACS BIM STYLES ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS BIM STYLES ===== */
  ✓ the published frontend carries exactly one <!-- ===== ACS BIM DOM (generated) ===== -->
  ✓ and it is in a file the browser actually evaluates: <!-- ===== ACS BIM DOM (generated) ===== -->
  ✓ the published frontend carries exactly one <!-- ===== END ACS BIM DOM ===== -->
  ✓ and it is in a file the browser actually evaluates: <!-- ===== END ACS BIM DOM ===== -->
  ✓ the published frontend carries exactly one /* ===== ACS DOCUMENTATION (generated by tools/build_docs_…
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS DOCUMENTATION (generated by tools/build_docs_…
  ✓ the published frontend carries exactly one /* ===== END ACS DOCUMENTATION ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS DOCUMENTATION ===== */
  ✓ the published frontend carries exactly one /* ===== ACS DOCS STYLES (generated) ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS DOCS STYLES (generated) ===== */
  ✓ the published frontend carries exactly one /* ===== END ACS DOCS STYLES ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS DOCS STYLES ===== */
  ✓ the published frontend carries exactly one <!-- ===== ACS DOCS DOM (generated) ===== -->
  ✓ and it is in a file the browser actually evaluates: <!-- ===== ACS DOCS DOM (generated) ===== -->
  ✓ the published frontend carries exactly one <!-- ===== END ACS DOCS DOM ===== -->
  ✓ and it is in a file the browser actually evaluates: <!-- ===== END ACS DOCS DOM ===== -->
  ✓ the published frontend carries exactly one /* ===== ACS PBR QUALITY (generated by tools/build_pbr_bro…
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS PBR QUALITY (generated by tools/build_pbr_bro…
  ✓ the published frontend carries exactly one /* ===== END ACS PBR QUALITY ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS PBR QUALITY ===== */
  ✓ the published frontend carries exactly one /* ===== ACS PBR STYLES (generated) ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS PBR STYLES (generated) ===== */
  ✓ the published frontend carries exactly one /* ===== END ACS PBR STYLES ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS PBR STYLES ===== */
  ✓ the published frontend carries exactly one <!-- ===== ACS PBR DOM (generated) ===== -->
  ✓ and it is in a file the browser actually evaluates: <!-- ===== ACS PBR DOM (generated) ===== -->
  ✓ the published frontend carries exactly one <!-- ===== END ACS PBR DOM ===== -->
  ✓ and it is in a file the browser actually evaluates: <!-- ===== END ACS PBR DOM ===== -->
  ✓ the published frontend carries exactly one /* ===== ACS ARCH DETAIL (generated by tools/build_archdet…
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS ARCH DETAIL (generated by tools/build_archdet…
  ✓ the published frontend carries exactly one /* ===== END ACS ARCH DETAIL ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS ARCH DETAIL ===== */
  ✓ the published frontend carries exactly one /* ===== ACS ARCH DETAIL STYLES (generated) ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== ACS ARCH DETAIL STYLES (generated) ===== */
  ✓ the published frontend carries exactly one /* ===== END ACS ARCH DETAIL STYLES ===== */
  ✓ and it is in a file the browser actually evaluates: /* ===== END ACS ARCH DETAIL STYLES ===== */
  ✓ the published frontend carries exactly one <!-- ===== ACS ARCH DETAIL DOM (generated) ===== -->
  ✓ and it is in a file the browser actually evaluates: <!-- ===== ACS ARCH DETAIL DOM (generated) ===== -->
  ✓ the published frontend carries exactly one <!-- ===== END ACS ARCH DETAIL DOM ===== -->
  ✓ and it is in a file the browser actually evaluates: <!-- ===== END ACS ARCH DETAIL DOM ===== -->

== 5 · THE MIRRORED SPECIFICATIONS HAVE NOT DRIFTED FROM THE FILES ==
  ✓ ACS_VISUAL_SPEC in the shipped modules is byte-equal to the file on disk
  ✓ ACS_RUNTIME_SPEC in the shipped modules is byte-equal to the file on disk
  ✓ ACS_AUTHORING_SPEC in the shipped modules is byte-equal to the file on disk
  ✓ ACS_WORKSPACE_SPEC in the shipped modules is byte-equal to the file on disk
  ✓ ACS_RENDER_SPEC in the shipped modules is byte-equal to the file on disk
  ✓ ACS_BIM_SPEC in the shipped modules is byte-equal to the file on disk
  ✓ ACS_DOCS_SPEC in the shipped modules is byte-equal to the file on disk
  ✓ ACS_PBR_SPEC in the shipped modules is byte-equal to the file on disk
  ✓ ACS_ARCHDETAIL_SPEC in the shipped modules is byte-equal to the file on disk

== 6 · NETLIFY CONFIGURATION IS VALID AND MATCHES REALITY ==
  ✓ a publish directory is declared
  ✓ the declared publish directory exists
  ✓ the published directory contains the application entry
  ✓ a build command is declared
  ✓ netlify.toml parses as real TOML
  · netlify.toml declares no build base in any context; the effective base is the repository root, which is the intended contract
  ✓ no build base is declared, or every declared base is repository-relative
  ✓ no declared base escapes the repository with a parent segment
  · the effective Netlify build base is the repository root (base NOT SET)
  ✓ the effective base exists and is inside the repository
  ✓ the publish directory resolves to a real directory under the effective base
  ✓ the published directory under the effective base carries the app entry
  ✓ the build command script resolves from the effective base
  ✓ the build command references no parent directory
  ✓ no absolute build path is baked into netlify.toml
  ✓ the netlify configuration names no builder-internal path
  ✓ no second Netlify configuration file can reintroduce a base
  ✓ the base guard rejects a parent directory base
  ✓ the base guard rejects a parent with slash
  ✓ the base guard rejects a nested escape
  ✓ the base guard rejects a absolute builder path
  ✓ the base guard rejects a absolute repo path
  ✓ the base guard rejects a absolute root
  ✓ the base guard rejects a missing directory
  ✓ the base guard rejects a context escape
  ✓ the base guard rejects a context absolute
  ✓ the base guard accepts the shipped configuration
  ✓ the base guard accepts a legitimate committed subdirectory
  ✓ the build command points at a script that exists in the repository
  ✓ a Content-Security-Policy header is declared
  ✓ the CSP does not use a wildcard script source
  ✓ the CSP pins connect-src rather than allowing anything
  ✓ framing is denied

== 6b · THE CONTENT SECURITY POLICY IS STRICT, AND THE PAGE EARNS IT ==
  · the declared CSP has 15 directive(s): base-uri, connect-src, default-src, font-src, form-action, frame-ancestors, frame-src, img-src, manifest-src, media-src, object-src, script-src, style-src, upgrade-insecure-requests, worker-src
  ✓ the policy parses into named directives at all
  ✓ NO directive carries 'unsafe-inline' or 'unsafe-eval' — not one
  ✓ script-src is exactly 'self' plus one sha256 source
  ✓ script-src carries EXACTLY ONE hash source
  ✓ that hash is the sha256 of the page's own inline import map — the only inline script left in the shell
  ✓ the recorded hash file agrees with the page and the policy
  ✓ style-src is 'self' only — the stylesheet is external, so no inline style needs allowing
  ✓ default-src is 'self'
  ✓ base-uri is 'self'
  ✓ object-src is 'none'
  ✓ frame-ancestors is 'none'
  ✓ frame-src is 'none'
  ✓ form-action is 'self'
  ✓ worker-src is 'self'
  ✓ font-src is 'self'

== 7 · RENDER CONFIGURATION IS VALID AND MATCHES REALITY ==
  ✓ a web service is declared
  ✓ the runtime is docker, matching the Dockerfile in the repository
  ✓ a health check path is declared
  ✓ the health check path is served by the API
  ✓ the secret is declared without a value
  ✓ the allowed origin is pinned, not a wildcard
  ✓ the model identifier is unchanged
  ✓ rate limits are still declared

== 8 · EVERY ENV VAR THE BACKEND READS IS DECLARED OR DEFAULTED ==
  · the backend reads 26 environment variable(s)
  ✓ no environment variable is both undeclared and undefaulted

== 9 · NO SANDBOX PATH LEAKS INTO ANYTHING DEPLOYED ==
  · 28 published frontend file(s) are scanned for sandbox paths and secrets alongside the page
  ✓ Dockerfile carries no sandbox path
  ✓ acs_api_errors.py carries no sandbox path
  ✓ acs_arch.json carries no sandbox path
  ✓ acs_arch.py carries no sandbox path
  ✓ acs_archdetail.json carries no sandbox path
  ✓ acs_archdetail.py carries no sandbox path
  ✓ acs_authoring.json carries no sandbox path
  ✓ acs_authoring.py carries no sandbox path
  ✓ acs_bim.json carries no sandbox path
  ✓ acs_bim.py carries no sandbox path
  ✓ acs_build_info.py carries no sandbox path
  ✓ acs_compiler.py carries no sandbox path
  ✓ acs_coord.json carries no sandbox path
  ✓ acs_coord.py carries no sandbox path
  ✓ acs_cpu_pool.py carries no sandbox path
  ✓ acs_distance.py carries no sandbox path
  ✓ acs_docs.json carries no sandbox path
  ✓ acs_docs.py carries no sandbox path
  ✓ acs_egress.py carries no sandbox path
  ✓ acs_engineering_approval.py carries no sandbox path
  ✓ acs_engineering_authority.py carries no sandbox path
  ✓ acs_engineering_changes.json carries no sandbox path
  ✓ acs_fls.json carries no sandbox path
  ✓ acs_fls.py carries no sandbox path
  ✓ acs_generation.py carries no sandbox path
  ✓ acs_generation_job.py carries no sandbox path
  ✓ acs_ingest.json carries no sandbox path
  ✓ acs_ingest.py carries no sandbox path
  ✓ acs_layout.py carries no sandbox path
  ✓ acs_logging.py carries no sandbox path
  ✓ acs_mep.json carries no sandbox path
  ✓ acs_mep.py carries no sandbox path
  ✓ acs_navigation.py carries no sandbox path
  ✓ acs_occupancy.json carries no sandbox path
  ✓ acs_occupancy.py carries no sandbox path
  ✓ acs_opening_identity.py carries no sandbox path
  ✓ acs_pbr.json carries no sandbox path
  ✓ acs_pbr.py carries no sandbox path
  ✓ acs_plan_chunks.py carries no sandbox path
  ✓ acs_programs.json carries no sandbox path
  ✓ acs_programs.py carries no sandbox path
  ✓ acs_project.py carries no sandbox path
  ✓ acs_provider.py carries no sandbox path
  ✓ acs_rate_limit.py carries no sandbox path
  ✓ acs_relations.py carries no sandbox path
  ✓ acs_render.json carries no sandbox path
  ✓ acs_render.py carries no sandbox path
  ✓ acs_revision.json carries no sandbox path
  ✓ acs_revision.py carries no sandbox path
  ✓ acs_rules.json carries no sandbox path
  ✓ acs_rules.py carries no sandbox path
  ✓ acs_runtime.json carries no sandbox path
  ✓ acs_runtime.py carries no sandbox path
  ✓ acs_sources.json carries no sandbox path
  ✓ acs_struct.json carries no sandbox path
  ✓ acs_struct.py carries no sandbox path
  ✓ acs_understand.py carries no sandbox path
  ✓ acs_understand_api.py carries no sandbox path
  ✓ acs_upload_security.py carries no sandbox path
  ✓ acs_validate.py carries no sandbox path
  ✓ acs_visual.json carries no sandbox path
  ✓ acs_visual.py carries no sandbox path
  ✓ acs_workspace.json carries no sandbox path
  ✓ acs_workspace.py carries no sandbox path
  ✓ netlify.toml carries no sandbox path
  ✓ public/app/boot/a11y-baseline.js carries no sandbox path
  ✓ public/app/boot/api-base.js carries no sandbox path
  ✓ public/app/boot/build-info.js carries no sandbox path
  ✓ public/app/boot/debug-toggle.js carries no sandbox path
  ✓ public/app/boot/engine-guard.js carries no sandbox path
  ✓ public/app/boot/style-bridge.js carries no sandbox path
  ✓ public/app/core/disciplines.js carries no sandbox path
  ✓ public/app/core/standards.js carries no sandbox path
  ✓ public/app/core/viewer.js carries no sandbox path
  ✓ public/app/generated/arch-detail-bridge.js carries no sandbox path
  ✓ public/app/generated/arch-detail.js carries no sandbox path
  ✓ public/app/generated/authoring.js carries no sandbox path
  ✓ public/app/generated/bim.js carries no sandbox path
  ✓ public/app/generated/docs.js carries no sandbox path
  ✓ public/app/generated/pbr-bridge.js carries no sandbox path
  ✓ public/app/generated/pbr.js carries no sandbox path
  ✓ public/app/generated/render-engine.js carries no sandbox path
  ✓ public/app/generated/runtime.js carries no sandbox path
  ✓ public/app/generated/workspace-ui.js carries no sandbox path
  ✓ public/app/late-bindings.js carries no sandbox path
  ✓ public/app/main.js carries no sandbox path
  ✓ public/app/render/scene.js carries no sandbox path
  ✓ public/app/shared-state.js carries no sandbox path
  ✓ public/app/styles/app.css carries no sandbox path
  ✓ public/app/trust/core.js carries no sandbox path
  ✓ public/app/trust/wiring.js carries no sandbox path
  ✓ public/app/ui/panels-entry.js carries no sandbox path
  ✓ public/app/ui/workspace-ui-wiring.js carries no sandbox path
  ✓ public/index.html carries no sandbox path
  ✓ render.yaml carries no sandbox path
  ✓ requirements.txt carries no sandbox path
  ✓ tools/netlify-build.sh carries no sandbox path
  ✓ tools/vendor.sh carries no sandbox path

== 10 · NO SECRET IS PACKAGED ==
  ✓ Dockerfile carries no credential-shaped value
  ✓ acs_api_errors.py carries no credential-shaped value
  ✓ acs_arch.json carries no credential-shaped value
  ✓ acs_arch.py carries no credential-shaped value
  ✓ acs_archdetail.json carries no credential-shaped value
  ✓ acs_archdetail.py carries no credential-shaped value
  ✓ acs_authoring.json carries no credential-shaped value
  ✓ acs_authoring.py carries no credential-shaped value
  ✓ acs_bim.json carries no credential-shaped value
  ✓ acs_bim.py carries no credential-shaped value
  ✓ acs_build_info.py carries no credential-shaped value
  ✓ acs_compiler.py carries no credential-shaped value
  ✓ acs_coord.json carries no credential-shaped value
  ✓ acs_coord.py carries no credential-shaped value
  ✓ acs_cpu_pool.py carries no credential-shaped value
  ✓ acs_distance.py carries no credential-shaped value
  ✓ acs_docs.json carries no credential-shaped value
  ✓ acs_docs.py carries no credential-shaped value
  ✓ acs_egress.py carries no credential-shaped value
  ✓ acs_engineering_approval.py carries no credential-shaped value
  ✓ acs_engineering_authority.py carries no credential-shaped value
  ✓ acs_engineering_changes.json carries no credential-shaped value
  ✓ acs_fls.json carries no credential-shaped value
  ✓ acs_fls.py carries no credential-shaped value
  ✓ acs_generation.py carries no credential-shaped value
  ✓ acs_generation_job.py carries no credential-shaped value
  ✓ acs_ingest.json carries no credential-shaped value
  ✓ acs_ingest.py carries no credential-shaped value
  ✓ acs_layout.py carries no credential-shaped value
  ✓ acs_logging.py carries no credential-shaped value
  ✓ acs_mep.json carries no credential-shaped value
  ✓ acs_mep.py carries no credential-shaped value
  ✓ acs_navigation.py carries no credential-shaped value
  ✓ acs_occupancy.json carries no credential-shaped value
  ✓ acs_occupancy.py carries no credential-shaped value
  ✓ acs_opening_identity.py carries no credential-shaped value
  ✓ acs_pbr.json carries no credential-shaped value
  ✓ acs_pbr.py carries no credential-shaped value
  ✓ acs_plan_chunks.py carries no credential-shaped value
  ✓ acs_programs.json carries no credential-shaped value
  ✓ acs_programs.py carries no credential-shaped value
  ✓ acs_project.py carries no credential-shaped value
  ✓ acs_provider.py carries no credential-shaped value
  ✓ acs_rate_limit.py carries no credential-shaped value
  ✓ acs_relations.py carries no credential-shaped value
  ✓ acs_render.json carries no credential-shaped value
  ✓ acs_render.py carries no credential-shaped value
  ✓ acs_revision.json carries no credential-shaped value
  ✓ acs_revision.py carries no credential-shaped value
  ✓ acs_rules.json carries no credential-shaped value
  ✓ acs_rules.py carries no credential-shaped value
  ✓ acs_runtime.json carries no credential-shaped value
  ✓ acs_runtime.py carries no credential-shaped value
  ✓ acs_sources.json carries no credential-shaped value
  ✓ acs_struct.json carries no credential-shaped value
  ✓ acs_struct.py carries no credential-shaped value
  ✓ acs_understand.py carries no credential-shaped value
  ✓ acs_understand_api.py carries no credential-shaped value
  ✓ acs_upload_security.py carries no credential-shaped value
  ✓ acs_validate.py carries no credential-shaped value
  ✓ acs_visual.json carries no credential-shaped value
  ✓ acs_visual.py carries no credential-shaped value
  ✓ acs_workspace.json carries no credential-shaped value
  ✓ acs_workspace.py carries no credential-shaped value
  ✓ netlify.toml carries no credential-shaped value
  ✓ public/app/boot/a11y-baseline.js carries no credential-shaped value
  ✓ public/app/boot/api-base.js carries no credential-shaped value
  ✓ public/app/boot/build-info.js carries no credential-shaped value
  ✓ public/app/boot/debug-toggle.js carries no credential-shaped value
  ✓ public/app/boot/engine-guard.js carries no credential-shaped value
  ✓ public/app/boot/style-bridge.js carries no credential-shaped value
  ✓ public/app/core/disciplines.js carries no credential-shaped value
  ✓ public/app/core/standards.js carries no credential-shaped value
  ✓ public/app/core/viewer.js carries no credential-shaped value
  ✓ public/app/generated/arch-detail-bridge.js carries no credential-shaped value
  ✓ public/app/generated/arch-detail.js carries no credential-shaped value
  ✓ public/app/generated/authoring.js carries no credential-shaped value
  ✓ public/app/generated/bim.js carries no credential-shaped value
  ✓ public/app/generated/docs.js carries no credential-shaped value
  ✓ public/app/generated/pbr-bridge.js carries no credential-shaped value
  ✓ public/app/generated/pbr.js carries no credential-shaped value
  ✓ public/app/generated/render-engine.js carries no credential-shaped value
  ✓ public/app/generated/runtime.js carries no credential-shaped value
  ✓ public/app/generated/workspace-ui.js carries no credential-shaped value
  ✓ public/app/late-bindings.js carries no credential-shaped value
  ✓ public/app/main.js carries no credential-shaped value
  ✓ public/app/render/scene.js carries no credential-shaped value
  ✓ public/app/shared-state.js carries no credential-shaped value
  ✓ public/app/styles/app.css carries no credential-shaped value
  ✓ public/app/trust/core.js carries no credential-shaped value
  ✓ public/app/trust/wiring.js carries no credential-shaped value
  ✓ public/app/ui/panels-entry.js carries no credential-shaped value
  ✓ public/app/ui/workspace-ui-wiring.js carries no credential-shaped value
  ✓ public/index.html carries no credential-shaped value
  ✓ render.yaml carries no credential-shaped value
  ✓ requirements.txt carries no credential-shaped value
  ✓ tools/netlify-build.sh carries no credential-shaped value
  ✓ tools/vendor.sh carries no credential-shaped value
  ✓ no real .env file is present in the repository
  ✓ an .env.example with placeholders only is provided
  ✓ the .env.example contains no real value
  ✓ the .env.example names the secret without setting it
  ✓ the API reads the key name somewhere (the check is not vacuous)
  ✓ every mention of the key is existence-only — the value is never returned
  ✓ the key-presence helper returns a boolean, not the key
  ✓ no response, log line or f-string carries the key value
  ✓ the API never returns the key itself, only whether one is set

== 11 · THE PRODUCTION BUNDLE IS INTERNALLY SELF-CONSISTENT ==
  · shell=47424 B · 27 module(s)=1916083 B · css=54378 B · pre-split single page=1863894 B
  ✓ the published page is a SHELL, not the application: under 200 KB
  ✓ and dramatically smaller than the single file it replaced (under a tenth)
  ✓ the application did not shrink, it moved: shell + modules + stylesheet carry at least what the single page carried
  ✓ the application is split into separately cacheable modules
  ✓ the page contains NO executable inline script: the only inline <script> is the import map
  ✓ the page contains NO <style> block
  ✓ the page contains NO style= attribute — the .acs-u-NN utility classes replaced every one of them
  ✓ the utility classes that replaced them ship in the external stylesheet, so nothing lost its styling silently
  ✓ the page carries NO inline event-handler attribute — under this CSP one would never fire, so its presence is dead code, not style
  ✓ the page loads no remote script or stylesheet at runtime
  ✓ the shell declares at least one script and exactly one stylesheet
  ✓ EVERY <script src> and <link rel=stylesheet> in the shell resolves to a non-empty file that exists in public/
  ✓ the module entry point the shell names is public/app/main.js
  ✓ every classic boot script the shell names exists under public/app/boot/
  ✓ and every boot script that ships is actually referenced by the shell — no orphan boot file
  ✓ public/app/main.js imports EVERY shipped module except boot/, styles/, main.js and shared-state.js — no orphan file is published
  ✓ and every module main.js imports really exists — no missing import
  ✓ the import list has no duplicate: a module evaluated twice is a second copy of its state
  · main.js imports 20 module(s) in the original evaluation order; shared-state.js carries the 9 bindings written across module boundaries
  ✓ the cross-module write surface is a single sealed object, not a set of globals
  ✓ es-module-shims is referenced nowhere in the shipped frontend (shell, modules or stylesheet)
  ✓ every non-vendored local reference resolves inside public/
  · the build script declares 2 vendored version(s): PDFJS=4.10.38, THREE=0.160.0
  ✓ build declares a non-empty required asset array
  ✓ every version placeholder in the vendor list resolves to a declared variable
  · public/vendor holds 0 file(s); the build script requires 17 and 0 are present. Run tools/netlify-build.sh to materialize locked assets. Three.js-dependent 3D runtime behaviour in this checkout is NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.
  ✓ the missing runtime libraries are fetched by the declared build command, not expected in the repository
  ✓ the vendor fetch script pins exact versions
  ✓ the build script vendors NO es-module-shims: nothing in the shipped frontend loads it, so fetching it is dead payload on every deploy
  ✓ the vendored libraries are exactly the two the frontend actually resolves: three (import map) and pdfjs (dynamic import)
  ✓ every /vendor/ package the frontend references is fetched by the build script
  ✓ the vendor fetch script fails the build on a missing file
  ✓ the model identifier is unchanged in the Dockerfile

== 11b · EVERY CANONICAL SPEC IS CLASSIFIED, NONE IS ORPHANED ==
  · 19 canonical file(s) are browser-mirrored: acs_archdetail.json, acs_archdetail.py, acs_authoring.json, acs_authoring.py, acs_bim.json, acs_bim.py, acs_docs.json, acs_docs.py, acs_engineering_approval.py, acs_pbr.json, acs_pbr.py, acs_render.json, acs_render.py, acs_runtime.json, acs_runtime.py, acs_visual.json, acs_visual.py, acs_workspace.json, acs_workspace.py
  · 1 offline command-line tool(s), deployed nowhere by design: acs_compiler.py
  ✓ every canonical file is classified: image, browser mirror or offline tool
  ✓ the authoring companion acs_engineering_approval.py is genuinely unreachable from the API
  ✓ the authoring companion acs_engineering_approval.py is not shipped in the container
  ✓ the offline tool acs_compiler.py is genuinely unreachable from the API
  ✓ the offline tool acs_compiler.py is not shipped in the container
  ✓ the browser-mirrored acs_archdetail.json is covered by the drift check
  ✓ the browser-mirrored acs_authoring.json is covered by the drift check
  ✓ the browser-mirrored acs_bim.json is covered by the drift check
  ✓ the browser-mirrored acs_docs.json is covered by the drift check
  ✓ the browser-mirrored acs_pbr.json is covered by the drift check
  ✓ the browser-mirrored acs_render.json is covered by the drift check
  ✓ the browser-mirrored acs_runtime.json is covered by the drift check
  ✓ the browser-mirrored acs_visual.json is covered by the drift check
  ✓ the browser-mirrored acs_workspace.json is covered by the drift check
  ✓ a browser-only layer is not silently required by the backend

== 11c · THE VISUAL QUALITY BRIDGE AND ITS VENDORED MODULES ==
  ✓ the PBR bridge is present exactly once
  ✓ the render loop hook is present exactly once
  ✓ the original render call survives as the fallback path
  ✓ post-processing modules import from the local vendor origin only
  ✓ the vendor build verifies postprocessing/EffectComposer.js
  ✓ the vendor build verifies postprocessing/RenderPass.js
  ✓ the vendor build verifies postprocessing/ShaderPass.js
  ✓ the vendor build verifies postprocessing/OutputPass.js
  ✓ the vendor build verifies postprocessing/SSAOPass.js
  ✓ the vendor build verifies shaders/FXAAShader.js
  ✓ the vendor build verifies shaders/CopyShader.js
  ✓ the vendor build verifies shaders/SSAOShader.js
  ✓ the local texture root exists and documents the empty-set default
  ✓ no remote texture or environment host is referenced by the quality layer

== 11d · THE ARCHITECTURAL DETAIL LAYER (PHASE 9.2) ==
  ✓ the archdetail bridge is present exactly once
  ✓ the archdetail generated block is present exactly once
  ✓ the 9.1 render loop hook is still single — no second dispatcher
  ✓ the layer extends acs.pbr and never reverses
  ✓ no network scheme in the architectural layer
  ✓ no url-based gltf, remote texture or executable asset policy
  ✓ the bridge adds only AD_* presentation groups
  ✓ the archdetail layer needs no new vendored module

== 11d2 · ONE VIEWPORT CONTRACT ACROSS EVERY LAYER ==
  ✓ the integration gate passes on this tree
  ✓ the contract version is declared in the specification
  ✓ the python layer declares the same contract at runtime
  ✓ the netlify build refuses to publish a partially merged tree
  ✓ the black-viewport test refuses to run on a partial tree instead of raising AttributeError
  ✓ the boot harness announces its version so a stale copy is visible
  ✓ every contract symbol is callable in the python layer
  ✓ every contract symbol is mirrored in the shipped page

== 11e · THE VIEWPORT VISIBILITY APPARATUS (BLACK-SCREEN REMEDIATION) ==
  ✓ the decoded-pixel analyser ships
  ✓ the boot harness separates BOOT from VISUAL MODEL
  ✓ the boot harness loads real canonical fixtures, not an empty workspace
  ✓ the discredited PNG byte-size heuristic is gone for good
  ✓ the analyser decodes RGBA and reports luminance statistics
  ✓ the sky dome and ground plane are canonically excluded from bounds
  ✓ the page names the sky dome and ground plane so they can be excluded
  ✓ the camera clip contract is applied by the bridge, not just declared
  ✓ the render diagnostics bridge is present and presentation-only
  ✓ presentation material application fails open to the engineering material
  ✓ the composer is resized with the renderer
  ✓ the black-viewport regression ships and is wired into the phase gate

== 11f · THE TRANSFORM AND ALIGNMENT CONTRACT ==
  ✓ the coordinate space chain is declared end to end
  ✓ the axis convention is declared explicitly
  ✓ the elevation and host rules say EXACTLY ONCE
  ✓ the plate and rack rules are declared canonically
  ✓ the tolerance is small and carries its justification
  ✓ presentation offsets to hide misalignment are forbidden
  ✓ the shipped compiler derives its rack block from the contract
  ✓ the level plate is derived from the room footprint through the single shared extent contract, and the site-wide plate is gone from the compiler
  ✓ the plate policy change is provenanced, not silent: the new name, the previous name, what pinned it and why it changed all ship
  ✓ the Python compiler and the page agree on the plate extent contract
  ✓ alignment diagnostics ship and never move an object
  ✓ world bounds are measured only after updateMatrixWorld
  ✓ the seven ALIGN issue codes are declared and none is blocking
  ✓ the alignment regression ships and is wired into the phase gate

== 11g · THE HARNESS NEVER TOUCHES MODULE SCOPE ==
  ✓ every page.evaluate body uses public bridges only
  ✓ the scan is not vacuous — evaluate bodies were actually parsed
```

### bash tools/ci_run.sh — exit 64

```text
ci_run: --runner is required
```

### python3 tools/bundle_report.py — exit 0

```text
wrote tests/performance/bundle_report.json
  index shell         : 47424 B raw, 13243 B gzip (brotli None)
                        0 inline executable script(s), 0 <style> block(s), 0 style= attribute(s)
  first-party JS      : 1916083 B in 27 modules
  core initial JS     : 1890534 B in 21 modules  (+ 25549 B in 6 boot scripts = 1916083 B on first load)
  lazy first-party JS : 0 B in 0 modules — honestly zero
  css                 : 54378 B raw, 13087 B gzip
  largest module      : public/app/core/standards.js — 228701 B (11.94% of first-party JS)
  module warnings     : 0 over 307200 B
  budget              : shell 47424 B of 204800 B (23.2% used, preferred 153600 B) · budget_met=True preferred_met=True
  STATUS              : F-09 IMPLEMENTED — MEASUREMENT ONLY
```

## Baseline runner reproduction

The audit harness is recorded in `docs/audit/2026-09-26/run_baseline.py`; it does not modify application source. Generated test outputs and package-lock drift are excluded from commits.

## No-regression interpretation

Before each PR run the exact structural gates, the affected suites, new red/green/mutation tests, and this complete sweep under the same dependency/environment setup. Any new failure absent from this record is a regression until proved otherwise. A separately provisioned browser run supplements this baseline; it does not erase it. External device, Revit, authenticated live generation, browser 3G profiling, and Intel GPU performance remain NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.
