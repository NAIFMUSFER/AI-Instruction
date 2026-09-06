# File inventory

All files present at scan time, including untracked files. Git internals are scanned separately.
mtime is the local filesystem time, not an author timestamp. No importer does not prove a file is dead; CLI, tests and generated artifacts have separate entry points.

| File | Tracked | Bytes | Last Git change / local mtime | Importers / literal references |
|---|---|---:|---|---|
| .dockerignore | False | 173 | 2026-09-06T11:25:55.130877+00:00 | None found statically |
| .env.example | True | 5149 | 2026-08-15T09:00:09Z | None found statically |
| .gitattributes | True | 1861 | 2026-08-15T09:00:09Z | None found statically |
| .github/workflows/ci.yml | True | 22377 | 2026-08-16T16:23:15+03:00 | None found statically |
| .github/workflows/production-verify.yml | True | 5395 | 2026-08-15T08:59:34Z | None found statically |
| .gitignore | True | 4140 | 2026-08-15T08:59:34Z | None found statically |
| ARCHITECTURE-AUDIT.md | True | 10710 | 2026-08-15T08:59:34Z | None found statically |
| AUDIT-REPORT-AR.md | True | 21400 | 2026-08-15T09:05:18Z | None found statically |
| CLEANUP-MANIFEST.md | True | 2020 | 2026-08-15T08:59:34Z | None found statically |
| CSP-HARDENING.md | True | 19506 | 2026-08-15T08:59:34Z | None found statically |
| DEPENDENCY-POLICY.md | True | 11048 | 2026-08-15T08:59:34Z | None found statically |
| DEPLOYMENT-MANIFEST.md | True | 7707 | 2026-08-15T08:59:34Z | None found statically |
| Dockerfile | True | 4127 | 2026-08-15T21:54:32+03:00 | None found statically |
| KNOWN-ISSUES.md | True | 95534 | 2026-08-15T21:54:32+03:00 | None found statically |
| PHASE1-FREEZE.md | True | 11969 | 2026-08-15T08:59:34Z | None found statically |
| PHASE2-FOUNDATION.md | True | 157483 | 2026-08-15T08:59:34Z | None found statically |
| PHASE4-FOUNDATION.md | True | 15008 | 2026-08-15T08:59:34Z | None found statically |
| PHASE5-AUTHORING.md | True | 17526 | 2026-08-15T08:59:34Z | None found statically |
| PHASE6-FINAL-REPORT.md | True | 19213 | 2026-08-15T08:59:34Z | None found statically |
| PHASE6-WORKSPACE.md | True | 8485 | 2026-08-15T08:59:34Z | None found statically |
| PHASE7-FINAL-REPORT.md | True | 18817 | 2026-08-15T08:59:34Z | None found statically |
| PHASE7-PHOTOREALISTIC.md | True | 13108 | 2026-08-15T08:59:34Z | None found statically |
| PHASE8-BIM-INTEROPERABILITY.md | True | 15394 | 2026-08-15T08:59:34Z | None found statically |
| PHASE8-FINAL-REPORT.md | True | 25783 | 2026-08-15T08:59:34Z | None found statically |
| PHASE9-DEPLOYMENT-MANIFEST.md | True | 7724 | 2026-08-15T08:59:34Z | None found statically |
| PHASE9-DOCUMENTATION.md | True | 15593 | 2026-08-15T08:59:34Z | None found statically |
| PHASE9-FINAL-REPORT.md | True | 18623 | 2026-08-15T08:59:34Z | None found statically |
| PHASE9-PRODUCTION-VERIFICATION.md | True | 10559 | 2026-08-15T08:59:34Z | None found statically |
| PHASE9.1-DEPLOYMENT-MANIFEST.md | True | 3547 | 2026-08-15T08:59:34Z | None found statically |
| PHASE9.1-FINAL-REPORT.md | True | 7062 | 2026-08-15T08:59:34Z | None found statically |
| PHASE9.1-PRODUCTION-VERIFICATION.md | True | 3532 | 2026-08-15T08:59:34Z | None found statically |
| PHASE9.1-VISUAL-QUALITY.md | True | 7291 | 2026-08-15T08:59:34Z | None found statically |
| PHASE9.2-ARCHITECTURAL-FIDELITY.md | True | 10489 | 2026-08-15T08:59:34Z | None found statically |
| PHASE9.2-DEPLOYMENT-MANIFEST.md | True | 2499 | 2026-08-15T08:59:34Z | None found statically |
| PHASE9.2-FINAL-REPORT.md | True | 8765 | 2026-08-15T08:59:34Z | None found statically |
| PHASE9.2-PRODUCTION-VERIFICATION.md | True | 3430 | 2026-08-15T08:59:34Z | None found statically |
| PRODUCTION-TRUST-REMEDIATION-FINAL.md | True | 44428 | 2026-08-15T08:59:34Z | None found statically |
| PRODUCTION-VERIFICATION-LATEST.md | True | 27110 | 2026-08-15T08:59:34Z | None found statically |
| README.md | True | 57646 | 2026-08-15T11:44:54Z | None found statically |
| REVIEW-BOARD.md | True | 9145 | 2026-08-15T08:59:34Z | None found statically |
| VERIFICATION-RUNBOOK.md | True | 47622 | 2026-08-15T08:59:34Z | None found statically |
| acs_api_errors.py | True | 32813 | 2026-08-16T16:23:15+03:00 | acs_provider.py:278 (python_import); acs_logging.py:23 (python_import); acs_understand_api.py:32 (python_import); acs_understand.py:24 (python_import); acs_generation_job.py:474 (python_import); acs_generation_job.py:92 (python_import); acs_generation_job.py:129 (python_import); tests/deploy/verify_deploy.py:1167 (python_import); tests/phase9_2/test_backend_contract.py:29 (python_import); tests/phase9_2/test_generation_budget.py:36 (python_import); tests/remediation/test_p0_hardening.py:39 (python_import); tests/remediation/lib_job_faults.py:17 (python_import); tests/remediation/test_plan_chunking.py:36 (python_import); tests/remediation/test_provider_accounting.py:41 (python_import); tests/remediation/test_provider_capability.py:51 (python_import); tests/remediation/test_logging.py:33 (python_import); tests/remediation/test_job_boundary.py:39 (python_import); tests/remediation/test_provider_integration.py:59 (python_import); tests/remediation/test_multi_provider.py:40 (python_import); tests/remediation/test_provider_reject.py:44 (python_import) |
| acs_arch.json | True | 3327 | 2026-08-15T08:59:34Z | acs_arch.py:23 (literal_reference); tests/security/test_security.py:216 (literal_reference); tests/security/test_security.py:217 (literal_reference); tests/phase2/test_arch.js:26 (literal_reference) |
| acs_arch.py | True | 34124 | 2026-08-15T08:59:34Z | acs_fls.py:24 (python_import); acs_docs.py:272 (python_import); acs_compiler.py:914 (python_import); acs_coord.py:23 (python_import); acs_struct.py:23 (python_import); acs_distance.py:54 (python_import); acs_distance.py:77 (python_import); acs_visual.py:23 (python_import); acs_mep.py:23 (python_import); acs_authoring.py:365 (python_import); acs_relations.py:117 (python_import); tests/phase9/test_docs.py:16 (python_import); tests/phase3/perf_visual.py:6 (python_import); tests/phase6/benchmark_workspace.py:21 (python_import); tests/remediation/test_model_diagnostics.py:18 (python_import); tests/remediation/test_plate_extent.py:39 (python_import); tests/remediation/test_opening_identity.py:14 (python_import); tests/phase7/parity/py_render.py:21 (python_import); tests/phase2/parity/py_arch.py:14 (python_import); tests/phase3/parity/py_visual.py:8 (python_import); tests/phase6/parity/py_workspace.py:22 (python_import) |
| acs_archdetail.json | True | 39092 | 2026-08-15T08:59:34Z | acs_archdetail.py:23 (literal_reference); tools/build_archdetail_browser.py:28 (literal_reference); tests/deploy/verify_deploy.py:208 (literal_reference); tests/deploy/verify_deploy.py:338 (literal_reference); tests/deploy/verify_deploy.py:938 (literal_reference); tests/phase9_2/test_archdetail_browser.js:11 (literal_reference); tests/phase9_2/test_archdetail.py:36 (literal_reference); tests/phase9_2/capture_reference_92.js:18 (literal_reference); tests/security/test_security.py:870 (literal_reference) |
| acs_archdetail.py | True | 37943 | 2026-08-15T08:59:34Z | tests/phase9_2/test_black_viewport.py:33 (python_import); tests/phase9_2/test_archdetail.py:16 (python_import); tests/security/test_security.py:868 (python_import); tests/phase9_2/parity/py_ad.py:12 (python_import) |
| acs_authoring.json | True | 24576 | 2026-08-15T08:59:34Z | acs_authoring.py:26 (literal_reference); tools/build_authoring_browser.py:22 (literal_reference); tests/deploy/verify_deploy.py:202 (literal_reference); tests/deploy/verify_deploy.py:332 (literal_reference); tests/security/test_security.py:420 (literal_reference); tests/security/test_security.py:620 (literal_reference); tests/phase5/test_transaction.js:22 (literal_reference); tests/phase5/test_authoring.js:22 (literal_reference); tests/phase5/test_adversarial.js:23 (literal_reference); tests/phase5/test_immutability.js:22 (literal_reference); tests/phase5/test_integration.js:23 (literal_reference); tests/phase5/test_ai_boundary.js:22 (literal_reference); tests/phase8/test_bim.py:492 (literal_reference); tests/remediation/test_privacy_boundary.py:212 (literal_reference); tests/remediation/test_accessibility.js:753 (literal_reference) |
| acs_authoring.py | True | 113822 | 2026-08-15T08:59:34Z | acs_engineering_approval.py:149 (python_import); acs_workspace.py:19 (python_import); tests/phase9/test_docs.py:15 (python_import); tests/phase9/benchmark_docs.py:16 (python_import); tests/phase9/make_outputs.py:16 (python_import); tests/phase9_1/test_pbr.py:16 (python_import); tests/phase9_1/benchmark_pbr.py:22 (python_import); tests/phase9_2/test_alignment.py:29 (python_import); tests/phase9_2/test_black_viewport.py:58 (python_import); tests/phase9_2/test_archdetail.py:19 (python_import); tests/security/test_security.py:744 (python_import); tests/phase5/benchmark_authoring.py:18 (python_import); tests/phase8/make_outputs.py:18 (python_import); tests/phase8/test_bim.py:15 (python_import); tests/phase8/benchmark_bim.py:20 (python_import); tests/phase8/fixture_generator.py:19 (python_import); tests/phase6/benchmark_workspace.py:19 (python_import); tests/remediation/test_rule_source_boundary.py:12 (python_import); tests/remediation/test_generation_cancel.py:48 (python_import); tests/remediation/test_engineering_authority.py:29 (python_import); tests/remediation/test_opening_identity.py:13 (python_import); tests/phase7/parity/py_render.py:22 (python_import); tests/phase9/parity/py_docs.py:20 (python_import); tests/phase5/parity/py_authoring.py:19 (python_import); tests/phase8/parity/py_bim.py:24 (python_import); tests/phase6/parity/py_workspace.py:20 (python_import) |
| acs_bim.json | True | 20893 | 2026-08-15T08:59:34Z | acs_bim.py:24 (literal_reference); tools/build_bim_browser.py:21 (literal_reference); tests/deploy/verify_deploy.py:205 (literal_reference); tests/deploy/verify_deploy.py:335 (literal_reference); tests/security/test_security.py:563 (literal_reference); tests/security/test_security.py:588 (literal_reference); tests/phase8/test_bim_browser.js:14 (literal_reference) |
| acs_bim.py | True | 106161 | 2026-08-15T08:59:34Z | tests/security/test_security.py:561 (python_import); tests/phase8/make_outputs.py:17 (python_import); tests/phase8/test_bim.py:14 (python_import); tests/phase8/benchmark_bim.py:19 (python_import); tests/phase8/fixture_generator.py:18 (python_import); tests/remediation/test_opening_identity.py:15 (python_import); tests/phase8/parity/py_bim.py:23 (python_import) |
| acs_build_info.py | True | 3630 | 2026-08-15T08:59:34Z | acs_understand_api.py:34 (python_import); tools/stamp_build_tokens.py:28 (python_import); tools/write_build_info.py:88 (python_import); tests/remediation/test_build_metadata.py:31 (python_import) |
| acs_compiler.py | True | 49971 | 2026-08-15T08:59:34Z | tests/remediation/test_plate_extent.py:40 (python_import) |
| acs_coord.json | True | 9393 | 2026-08-15T08:59:34Z | acs_coord.py:30 (literal_reference); tests/security/test_security.py:332 (literal_reference); tests/security/test_security.py:335 (literal_reference); tests/phase2/test_coord.js:37 (literal_reference) |
| acs_coord.py | True | 50605 | 2026-08-15T08:59:34Z | acs_visual.py:27 (python_import); tests/phase6/benchmark_workspace.py:22 (python_import); tests/phase2/parity/py_coord.py:8 (python_import); tests/phase6/parity/py_workspace.py:23 (python_import) |
| acs_cpu_pool.py | True | 19951 | 2026-08-16T04:41:41+03:00 | acs_understand_api.py:38 (python_import); tests/remediation/test_p0_hardening.py:40 (python_import); tests/remediation/test_api_wiring.py:143 (python_import); tests/remediation/test_event_loop.py:51 (python_import); tests/remediation/test_event_loop.py:344 (python_import) |
| acs_distance.py | True | 23323 | 2026-08-15T08:59:34Z | acs_egress.py:15 (python_import); tests/remediation/test_opening_identity.py:18 (python_import); tests/phase2/parity/py_rules.py:11 (python_import); tests/phase2/parity/py_ing.py:11 (python_import); tests/phase2/parity/py_dist.py:11 (python_import); tests/phase2/parity/py_occ.py:11 (python_import) |
| acs_docs.json | True | 24610 | 2026-08-15T08:59:34Z | acs_docs.py:18 (literal_reference); tools/build_docs_browser.py:22 (literal_reference); tests/deploy/verify_deploy.py:206 (literal_reference); tests/deploy/verify_deploy.py:336 (literal_reference); tests/phase9/test_docs.py:34 (literal_reference); tests/phase9/test_docs.py:1097 (literal_reference); tests/phase9/test_docs_browser.js:13 (literal_reference); tests/security/test_security.py:674 (literal_reference); tests/security/test_security.py:694 (literal_reference) |
| acs_docs.py | True | 106105 | 2026-08-15T08:59:34Z | tests/phase9/test_docs.py:14 (python_import); tests/phase9/benchmark_docs.py:15 (python_import); tests/phase9/make_outputs.py:15 (python_import); tests/phase9_1/test_pbr.py:15 (python_import); tests/phase9_1/benchmark_pbr.py:21 (python_import); tests/phase9_2/test_alignment.py:28 (python_import); tests/phase9_2/test_black_viewport.py:57 (python_import); tests/phase9_2/test_archdetail.py:18 (python_import); tests/security/test_security.py:672 (python_import); tests/phase9/parity/py_docs.py:19 (python_import) |
| acs_egress.py | True | 17391 | 2026-08-15T08:59:34Z | acs_fls.py:27 (python_import); tests/phase2/parity/py_rules.py:11 (python_import); tests/phase2/parity/py_ing.py:11 (python_import); tests/phase2/parity/py_dist.py:11 (python_import); tests/phase2/parity/py_occ.py:11 (python_import) |
| acs_engineering_approval.py | True | 9775 | 2026-08-15T08:59:34Z | tests/remediation/test_rule_source_boundary.py:11 (python_import); tests/remediation/test_engineering_authority.py:30 (python_import) |
| acs_engineering_authority.py | True | 23174 | 2026-08-16T04:41:41+03:00 | acs_engineering_approval.py:12 (python_import); acs_understand_api.py:37 (python_import); acs_layout.py:405 (python_import); tests/remediation/test_rule_source_boundary.py:10 (python_import); tests/remediation/test_p0_hardening.py:41 (python_import); tests/remediation/test_model_diagnostics.py:19 (python_import); tests/remediation/test_engineering_authority.py:31 (python_import); tests/remediation/test_event_loop.py:290 (python_import) |
| acs_engineering_changes.json | True | 18270 | 2026-08-15T08:59:34Z | acs_engineering_authority.py:24 (literal_reference); tests/remediation/test_engineering_authority.py:355 (literal_reference) |
| acs_fls.json | True | 12959 | 2026-08-15T08:59:34Z | acs_fls.py:30 (literal_reference); tests/security/test_security.py:300 (literal_reference); tests/security/test_security.py:304 (literal_reference); tests/phase2/test_fls.js:55 (literal_reference) |
| acs_fls.py | True | 58592 | 2026-08-15T08:59:34Z | acs_docs.py:293 (python_import); acs_coord.py:26 (python_import); acs_visual.py:26 (python_import); tests/phase2/parity/py_fls.py:8 (python_import) |
| acs_generation.py | True | 30515 | 2026-08-16T16:23:15+03:00 | acs_plan_chunks.py:56 (python_import); acs_understand.py:25 (python_import); tests/deploy/verify_deploy.py:1168 (python_import); tests/phase9_2/test_live_render.py:40 (python_import); tests/phase9_2/test_generation_budget.py:37 (python_import); tests/remediation/test_plan_chunking.py:37 (python_import); tests/remediation/test_provider_accounting.py:42 (python_import); tests/remediation/test_provider_capability.py:52 (python_import); tests/remediation/test_provider_integration.py:439 (python_import); tests/remediation/test_multi_provider.py:570 (python_import); tests/remediation/test_provider_reject.py:45 (python_import) |
| acs_generation_job.py | True | 20347 | 2026-08-15T10:49:48Z | acs_understand_api.py:39 (python_import); tests/remediation/test_generation_cancel.py:49 (python_import); tests/remediation/test_job_boundary.py:40 (python_import); tests/remediation/test_provider_integration.py:60 (python_import) |
| acs_ingest.json | True | 24311 | 2026-08-15T08:59:34Z | acs_ingest.py:26 (literal_reference); tests/security/test_security.py:154 (literal_reference); tests/security/test_security.py:156 (literal_reference); tests/phase2/test_ingest.js:48 (literal_reference) |
| acs_ingest.py | True | 39570 | 2026-08-15T08:59:34Z | acs_pbr.py:16 (python_import); acs_docs.py:15 (python_import); acs_occupancy.py:21 (python_import); acs_bim.py:21 (python_import); acs_render.py:23 (python_import); acs_runtime.py:24 (python_import); acs_archdetail.py:20 (python_import); acs_revision.py:21 (python_import); acs_authoring.py:23 (python_import); acs_engineering_authority.py:21 (python_import); tests/remediation/test_plate_extent.py:41 (python_import); tests/phase2/parity/py_rev.py:11 (python_import); tests/phase2/parity/py_ing.py:12 (python_import) |
| acs_layout.py | True | 21216 | 2026-08-15T08:59:34Z | acs_engineering_authority.py:273 (python_import); acs_engineering_authority.py:322 (python_import); tests/remediation/test_engineering_authority.py:32 (python_import) |
| acs_logging.py | True | 10927 | 2026-08-16T16:23:15+03:00 | acs_understand_api.py:33 (python_import); acs_understand.py:27 (python_import); tests/remediation/test_privacy_boundary.py:31 (python_import); tests/remediation/test_plan_chunking.py:504 (python_import); tests/remediation/test_provider_accounting.py:43 (python_import); tests/remediation/test_provider_capability.py:53 (python_import); tests/remediation/test_logging.py:34 (python_import); tests/remediation/test_provider_integration.py:480 (python_import); tests/remediation/test_multi_provider.py:42 (python_import); tests/remediation/test_provider_reject.py:46 (python_import) |
| acs_mep.json | True | 11608 | 2026-08-15T08:59:34Z | acs_mep.py:27 (literal_reference); tests/security/test_security.py:264 (literal_reference); tests/security/test_security.py:265 (literal_reference); tests/phase2/test_mep.js:29 (literal_reference) |
| acs_mep.py | True | 63314 | 2026-08-15T08:59:34Z | acs_fls.py:25 (python_import); acs_docs.py:286 (python_import); acs_coord.py:25 (python_import); acs_visual.py:25 (python_import); tests/phase2/parity/py_mep.py:8 (python_import) |
| acs_navigation.py | True | 14639 | 2026-08-15T08:59:34Z | acs_egress.py:14 (python_import); tests/phase2/parity/py_rules.py:11 (python_import); tests/phase2/parity/py_ing.py:11 (python_import); tests/phase2/parity/py_dist.py:11 (python_import); tests/phase2/parity/py_occ.py:11 (python_import) |
| acs_occupancy.json | True | 7154 | 2026-08-15T08:59:34Z | acs_occupancy.py:24 (literal_reference); tests/security/test_security.py:184 (literal_reference); tests/security/test_security.py:185 (literal_reference); tests/phase2/test_occ.js:53 (literal_reference) |
| acs_occupancy.py | True | 26015 | 2026-08-15T08:59:34Z | tests/phase2/parity/py_occ.py:12 (python_import) |
| acs_opening_identity.py | False | 4269 | 2026-09-06T11:25:55.135981+00:00 | tests/remediation/test_opening_identity.py:20 (python_import) |
| acs_pbr.json | True | 32416 | 2026-08-15T08:59:34Z | acs_pbr.py:19 (literal_reference); tools/check_integration.py:97 (literal_reference); tools/build_pbr_browser.py:25 (literal_reference); tests/deploy/verify_page_boot.js:167 (literal_reference); tests/deploy/verify_deploy.py:207 (literal_reference); tests/deploy/verify_deploy.py:337 (literal_reference); tests/deploy/verify_deploy.py:915 (literal_reference); tests/deploy/verify_deploy.py:982 (literal_reference); tests/deploy/verify_deploy.py:1006 (literal_reference); tests/deploy/verify_deploy.py:1028 (literal_reference); tests/deploy/verify_deploy.py:1084 (literal_reference); tests/deploy/verify_deploy.py:1090 (literal_reference); tests/deploy/verify_deploy.py:1247 (literal_reference); tests/deploy/verify_deploy.py:1264 (literal_reference); tests/phase9_1/test_pbr.py:33 (literal_reference); tests/phase9_1/capture_reference.js:18 (literal_reference); tests/phase9_1/test_pbr_browser.js:10 (literal_reference); tests/phase9_2/test_black_viewport.py:283 (literal_reference); tests/phase9_2/capture_reference_92.js:19 (literal_reference); tests/security/test_security.py:803 (literal_reference) |
| acs_pbr.py | True | 54664 | 2026-08-15T08:59:34Z | acs_compiler.py:24 (python_import); acs_archdetail.py:19 (python_import); tools/check_integration.py:230 (python_import); tools/build_pbr_browser.py:1158 (python_import); tests/deploy/verify_deploy.py:963 (python_import); tests/phase9_1/test_pbr.py:14 (python_import); tests/phase9_1/benchmark_pbr.py:20 (python_import); tests/phase9_2/test_live_render.py:39 (python_import); tests/phase9_2/test_alignment.py:27 (python_import); tests/phase9_2/test_black_viewport.py:32 (python_import); tests/phase9_2/test_archdetail.py:17 (python_import); tests/security/test_security.py:801 (python_import); tests/remediation/test_plate_extent.py:42 (python_import); tests/phase9_1/parity/py_pbr.py:12 (python_import); tests/phase9_2/parity/py_ad.py:147 (python_import) |
| acs_plan_chunks.py | True | 43895 | 2026-08-16T16:23:15+03:00 | acs_understand.py:26 (python_import); tests/remediation/test_plan_chunking.py:38 (python_import); tests/remediation/test_provider_accounting.py:44 (python_import); tests/remediation/test_provider_capability.py:54 (python_import); tests/remediation/test_multi_provider.py:596 (python_import); tests/remediation/test_provider_reject.py:235 (python_import); tests/remediation/test_provider_reject.py:248 (python_import); tests/remediation/test_provider_reject.py:262 (python_import); tests/remediation/test_provider_reject.py:273 (python_import); tests/remediation/test_provider_reject.py:286 (python_import) |
| acs_programs.json | True | 8602 | 2026-08-15T08:59:34Z | acs_programs.py:16 (literal_reference); tests/security/test_security.py:127 (literal_reference); tests/security/test_security.py:211 (literal_reference); tests/phase1/test_phase2.js:8 (literal_reference) |
| acs_programs.py | True | 5015 | 2026-08-15T08:59:34Z | acs_understand.py:38 (python_import) |
| acs_project.py | True | 7523 | 2026-08-15T08:59:34Z | acs_revision.py:22 (python_import); tests/remediation/test_engineering_authority.py:381 (python_import) |
| acs_provider.py | True | 20816 | 2026-08-16T16:23:15+03:00 | acs_plan_chunks.py:209 (python_import); acs_understand_api.py:40 (python_import); acs_generation.py:94 (python_import); acs_generation.py:296 (python_import); acs_understand.py:28 (python_import); tests/remediation/test_provider_accounting.py:45 (python_import); tests/remediation/test_provider_capability.py:55 (python_import); tests/remediation/test_multi_provider.py:41 (python_import) |
| acs_rate_limit.py | True | 51789 | 2026-08-15T16:43:12Z | acs_understand_api.py:35 (python_import); tests/remediation/test_rate_limit.py:31 (python_import); tests/remediation/test_container_topology.py:40 (python_import); tests/remediation/test_event_loop.py:52 (python_import) |
| acs_relations.py | True | 15620 | 2026-08-15T08:59:34Z | acs_fls.py:26 (python_import); tests/remediation/test_opening_identity.py:19 (python_import); tests/phase2/parity/py_rules.py:11 (python_import); tests/phase2/parity/py_ing.py:11 (python_import); tests/phase2/parity/py_dist.py:11 (python_import); tests/phase2/parity/py_occ.py:11 (python_import) |
| acs_render.json | True | 30961 | 2026-08-15T08:59:34Z | acs_render.py:27 (literal_reference); tools/build_render_browser.py:21 (literal_reference); tests/phase7/benchmark_render.js:9 (literal_reference); tests/phase7/test_parity.js:60 (literal_reference); tests/phase7/test_targets.js:9 (literal_reference); tests/phase7/test_render.js:9 (literal_reference); tests/phase7/test_security.js:9 (literal_reference); tests/deploy/verify_deploy.py:204 (literal_reference); tests/deploy/verify_deploy.py:334 (literal_reference); tests/security/test_security.py:484 (literal_reference) |
| acs_render.py | True | 80522 | 2026-08-15T08:59:34Z | tests/phase7/parity/py_render.py:19 (python_import) |
| acs_revision.json | True | 4668 | 2026-08-15T08:59:34Z | acs_revision.py:26 (literal_reference); tests/security/test_security.py:198 (literal_reference); tests/security/test_security.py:199 (literal_reference); tests/security/test_security.py:261 (literal_reference); tests/phase2/test_rev.js:42 (literal_reference) |
| acs_revision.py | True | 19337 | 2026-08-15T08:59:34Z | acs_coord.py:27 (python_import); acs_visual.py:28 (python_import); tests/phase2/parity/py_rev.py:11 (python_import) |
| acs_rules.json | True | 37338 | 2026-08-15T08:59:34Z | acs_rules.py:20 (literal_reference); tests/security/test_security.py:128 (literal_reference); tests/security/test_security.py:130 (literal_reference); tests/phase2/test_rules.js:42 (literal_reference) |
| acs_rules.py | True | 40981 | 2026-08-15T08:59:34Z | acs_ingest.py:23 (python_import); acs_revision.py:23 (python_import); tests/phase2/parity/py_rules.py:11 (python_import); tests/phase2/parity/py_ing.py:12 (python_import); tests/phase2/parity/py_occ.py:12 (python_import) |
| acs_runtime.json | True | 18047 | 2026-08-15T08:59:34Z | acs_runtime.py:27 (literal_reference); tools/build_runtime_browser.py:22 (literal_reference); tests/deploy/verify_deploy.py:201 (literal_reference); tests/deploy/verify_deploy.py:331 (literal_reference); tests/phase4/test_runtime.js:15 (literal_reference); tests/phase4/test_visibility.js:35 (literal_reference); tests/phase4/test_measurement.js:33 (literal_reference); tests/phase4/test_adversarial.js:19 (literal_reference) |
| acs_runtime.py | True | 67741 | 2026-08-15T08:59:34Z | tests/phase4/benchmark_runtime.py:21 (python_import); tests/phase6/benchmark_workspace.py:24 (python_import); tests/phase4/parity/py_runtime.py:21 (python_import); tests/phase6/parity/py_workspace.py:25 (python_import) |
| acs_sources.json | True | 27894 | 2026-08-15T08:59:34Z | acs_ingest.py:169 (literal_reference); tests/security/test_security.py:173 (literal_reference); tests/security/test_security.py:174 (literal_reference); tests/phase2/test_ingest.js:437 (literal_reference) |
| acs_struct.json | True | 7058 | 2026-08-15T08:59:34Z | acs_struct.py:26 (literal_reference); tests/security/test_security.py:236 (literal_reference); tests/security/test_security.py:237 (literal_reference); tests/phase2/test_struct.js:27 (literal_reference) |
| acs_struct.py | True | 61946 | 2026-08-15T08:59:34Z | acs_docs.py:279 (python_import); acs_coord.py:24 (python_import); acs_visual.py:24 (python_import); acs_mep.py:24 (python_import); tests/phase2/parity/py_struct.py:8 (python_import) |
| acs_understand.py | True | 128209 | 2026-08-16T16:23:15+03:00 | acs_understand_api.py:31 (python_import); tests/phase9_2/test_backend_contract.py:30 (python_import); tests/phase9_2/test_generation_budget.py:38 (python_import); tests/remediation/test_privacy_boundary.py:32 (python_import); tests/remediation/test_plan_chunking.py:239 (python_import); tests/remediation/test_engineering_authority.py:374 (python_import); tests/remediation/test_provider_accounting.py:167 (python_import); tests/remediation/test_provider_capability.py:186 (python_import); tests/remediation/test_logging.py:529 (python_import); tests/remediation/test_provider_integration.py:193 (python_import); tests/remediation/test_opening_identity.py:17 (python_import); tests/remediation/test_multi_provider.py:168 (python_import) |
| acs_understand_api.py | True | 53072 | 2026-08-16T04:41:41+03:00 | tests/phase9_2/test_backend_contract.py:361 (python_import); tests/remediation/test_model_diagnostics.py:20 (python_import) |
| acs_upload_security.py | True | 52991 | 2026-08-16T04:41:41+03:00 | acs_understand_api.py:36 (python_import); acs_cpu_pool.py:266 (python_import); tests/remediation/test_upload_security.py:40 (python_import); tests/remediation/test_p0_hardening.py:42 (python_import); tests/remediation/test_privacy_boundary.py:33 (python_import); tests/remediation/test_event_loop.py:50 (python_import) |
| acs_validate.py | True | 12715 | 2026-08-15T08:59:34Z | acs_understand.py:380 (python_import); acs_understand.py:1308 (python_import); acs_understand.py:1326 (python_import); acs_understand.py:1720 (python_import); acs_understand.py:1897 (python_import); acs_layout.py:230 (python_import); acs_layout.py:327 (python_import); acs_engineering_authority.py:192 (python_import); acs_engineering_authority.py:281 (python_import); tests/remediation/test_rule_source_boundary.py:13 (python_import); tests/remediation/test_model_diagnostics.py:21 (python_import) |
| acs_visual.json | True | 24242 | 2026-08-15T08:59:34Z | acs_visual.py:31 (literal_reference); tests/deploy/verify_deploy.py:200 (literal_reference); tests/deploy/verify_deploy.py:330 (literal_reference); tests/security/test_security.py:367 (literal_reference); tests/security/test_security.py:370 (literal_reference); tests/phase3/test_visual.js:43 (literal_reference) |
| acs_visual.py | True | 87670 | 2026-08-15T08:59:34Z | acs_render.py:24 (python_import); tests/phase4/benchmark_runtime.py:20 (python_import); tests/phase3/perf_visual.py:6 (python_import); tests/phase6/benchmark_workspace.py:23 (python_import); tests/phase7/parity/py_render.py:20 (python_import); tests/phase4/parity/py_runtime.py:20 (python_import); tests/phase3/parity/py_visual.py:7 (python_import); tests/phase6/parity/py_workspace.py:24 (python_import) |
| acs_workspace.json | True | 27271 | 2026-08-15T08:59:34Z | acs_workspace.py:22 (literal_reference); tools/build_workspace_ui.py:22 (literal_reference); tests/deploy/verify_deploy.py:203 (literal_reference); tests/deploy/verify_deploy.py:333 (literal_reference); tests/security/test_security.py:443 (literal_reference); tests/phase6/test_responsive.js:155 (literal_reference); tests/phase6/test_responsive.js:172 (literal_reference); tests/phase6/test_responsive.js:283 (literal_reference); tests/phase6/benchmark_workspace.js:13 (literal_reference); tests/phase6/test_parity.js:62 (literal_reference); tests/phase6/test_workspace.js:12 (literal_reference); tests/phase6/test_security.js:8 (literal_reference); tests/phase6/test_workflow.js:12 (literal_reference); tests/phase6/test_dom.js:12 (literal_reference) |
| acs_workspace.py | True | 40165 | 2026-08-15T08:59:34Z | tests/phase6/benchmark_workspace.py:20 (python_import); tests/remediation/test_opening_identity.py:16 (python_import); tests/phase6/parity/py_workspace.py:21 (python_import) |
| docs/audits/2026-09-05-ci-33989619297.md | False | 10289 | 2026-09-06T11:25:55.145799+00:00 | None found statically |
| docs/audits/2026-09-05-ci-33991306859.md | False | 10839 | 2026-09-06T11:25:55.145882+00:00 | None found statically |
| docs/audits/2026-09-05-production-trust.md | False | 16483 | 2026-09-06T11:25:55.145882+00:00 | None found statically |
| docs/audits/2026-09-06-ci-33993089732.md | False | 9478 | 2026-09-06T11:25:55.145882+00:00 | None found statically |
| docs/audits/2026-09-06-image-build-provenance.md | False | 10170 | 2026-09-06T11:25:55.145882+00:00 | None found statically |
| docs/audits/2026-09-06-live-generation-acceptance.md | False | 7294 | 2026-09-06T11:25:55.145882+00:00 | None found statically |
| docs/audits/2026-09-06-model-review-remediation.md | False | 13483 | 2026-09-06T11:25:55.145882+00:00 | None found statically |
| docs/audits/2026-09-06-network-diagnostics.md | False | 7128 | 2026-09-06T11:25:55.145882+00:00 | None found statically |
| docs/audits/2026-09-06-opening-identity.md | False | 9773 | 2026-09-06T11:25:55.145882+00:00 | None found statically |
| netlify.toml | True | 6583 | 2026-08-15T08:59:34Z | None found statically |
| package-lock.json | True | 1985 | 2026-08-15T08:59:34Z | tools/dependency_audit.py:184 (literal_reference); tools/dependency_audit.py:271 (literal_reference); tests/remediation/test_dependency_lock.py:251 (literal_reference); tests/remediation/test_dependency_lock.py:253 (literal_reference); tests/remediation/test_dependency_lock.py:434 (literal_reference) |
| package.json | True | 107 | 2026-08-15T08:59:34Z | tools/dependency_audit.py:184 (literal_reference); tools/dependency_audit.py:272 (literal_reference); tests/remediation/test_dependency_lock.py:252 (literal_reference); tests/remediation/test_dependency_lock.py:254 (literal_reference) |
| public/app/boot/a11y-baseline.js | True | 5037 | 2026-08-15T08:59:34Z | public/index.html:660 (literal_reference) |
| public/app/boot/api-base.js | True | 1955 | 2026-08-15T08:59:34Z | public/index.html:17 (literal_reference) |
| public/app/boot/build-info.js | True | 5429 | 2026-08-15T08:59:34Z | public/index.html:26 (literal_reference); tools/stamp_build_tokens.py:32 (literal_reference); tests/production/verify_live.py:740 (literal_reference) |
| public/app/boot/debug-toggle.js | True | 1118 | 2026-08-15T09:00:09Z | public/index.html:204 (literal_reference) |
| public/app/boot/engine-guard.js | True | 2650 | 2026-08-15T08:59:34Z | public/index.html:481 (literal_reference) |
| public/app/boot/style-bridge.js | True | 9360 | 2026-08-15T09:55:47Z | public/index.html:24 (literal_reference) |
| public/app/core/disciplines.js | True | 205018 | 2026-08-15T08:59:34Z | tests/remediation/test_scene_benchmark.js:129 (literal_reference); public/app/main.js:10 (js_import); public/app/main.js:10 (literal_reference); public/app/generated/authoring.js:7 (js_import); public/app/generated/authoring.js:7 (literal_reference); public/app/generated/workspace-ui.js:8 (js_import); public/app/generated/workspace-ui.js:8 (literal_reference); public/app/generated/runtime.js:7 (js_import); public/app/generated/runtime.js:7 (literal_reference); public/app/generated/docs.js:7 (js_import); public/app/generated/docs.js:7 (literal_reference); public/app/ui/workspace-ui-wiring.js:8 (js_import); public/app/ui/workspace-ui-wiring.js:8 (literal_reference); public/app/render/scene.js:7 (js_import); public/app/render/scene.js:7 (literal_reference) |
| public/app/core/standards.js | True | 228695 | 2026-08-15T08:59:34Z | tests/remediation/test_scene_benchmark.js:128 (literal_reference); public/app/main.js:9 (js_import); public/app/main.js:9 (literal_reference); public/app/generated/authoring.js:8 (js_import); public/app/generated/authoring.js:8 (literal_reference); public/app/generated/bim.js:7 (js_import); public/app/generated/bim.js:7 (literal_reference); public/app/generated/pbr-bridge.js:8 (js_import); public/app/generated/pbr-bridge.js:8 (literal_reference); public/app/generated/workspace-ui.js:9 (js_import); public/app/generated/workspace-ui.js:9 (literal_reference); public/app/generated/runtime.js:8 (js_import); public/app/generated/runtime.js:8 (literal_reference); public/app/generated/pbr.js:8 (js_import); public/app/generated/pbr.js:8 (literal_reference); public/app/generated/render-engine.js:7 (js_import); public/app/generated/render-engine.js:7 (literal_reference); public/app/generated/docs.js:8 (js_import); public/app/generated/docs.js:8 (literal_reference); public/app/generated/arch-detail.js:7 (js_import); public/app/generated/arch-detail.js:7 (literal_reference); public/app/ui/workspace-ui-wiring.js:9 (js_import); public/app/ui/workspace-ui-wiring.js:9 (literal_reference); public/app/core/disciplines.js:7 (js_import); public/app/core/disciplines.js:7 (literal_reference); public/app/render/scene.js:8 (js_import); public/app/render/scene.js:8 (literal_reference) |
| public/app/core/viewer.js | True | 197799 | 2026-08-15T16:43:12Z | tests/remediation/test_apply_render_browser.js:77 (literal_reference); tests/remediation/test_scene_benchmark.js:130 (literal_reference); public/app/main.js:8 (js_import); public/app/main.js:8 (literal_reference); public/app/generated/authoring.js:9 (js_import); public/app/generated/authoring.js:9 (literal_reference); public/app/generated/bim.js:8 (js_import); public/app/generated/bim.js:8 (literal_reference); public/app/generated/pbr-bridge.js:9 (js_import); public/app/generated/pbr-bridge.js:9 (literal_reference); public/app/generated/workspace-ui.js:10 (js_import); public/app/generated/workspace-ui.js:10 (literal_reference); public/app/generated/runtime.js:9 (js_import); public/app/generated/runtime.js:9 (literal_reference); public/app/generated/pbr.js:9 (js_import); public/app/generated/pbr.js:9 (literal_reference); public/app/generated/render-engine.js:8 (js_import); public/app/generated/render-engine.js:8 (literal_reference); public/app/generated/arch-detail-bridge.js:7 (js_import); public/app/generated/arch-detail-bridge.js:7 (literal_reference); public/app/generated/docs.js:9 (js_import); public/app/generated/docs.js:9 (literal_reference); public/app/ui/workspace-ui-wiring.js:10 (js_import); public/app/ui/workspace-ui-wiring.js:10 (literal_reference); public/app/core/standards.js:8 (js_import); public/app/core/standards.js:8 (literal_reference); public/app/core/disciplines.js:8 (js_import); public/app/core/disciplines.js:8 (literal_reference); public/app/render/scene.js:9 (js_import); public/app/render/scene.js:9 (literal_reference) |
| public/app/generated/arch-detail-bridge.js | True | 18198 | 2026-08-15T08:59:34Z | public/app/main.js:21 (js_import); public/app/main.js:21 (literal_reference) |
| public/app/generated/arch-detail.js | True | 70950 | 2026-08-15T08:59:34Z | tests/remediation/test_csp_style_architecture.js:130 (literal_reference); public/app/main.js:18 (js_import); public/app/main.js:18 (literal_reference); public/app/generated/arch-detail-bridge.js:8 (js_import); public/app/generated/arch-detail-bridge.js:8 (literal_reference) |
| public/app/generated/authoring.js | True | 116758 | 2026-08-15T08:59:34Z | tests/remediation/test_csp_style_architecture.js:132 (literal_reference); public/app/main.js:12 (js_import); public/app/main.js:12 (literal_reference); public/app/generated/bim.js:9 (js_import); public/app/generated/bim.js:9 (literal_reference); public/app/generated/workspace-ui.js:11 (js_import); public/app/generated/workspace-ui.js:11 (literal_reference); public/app/trust/wiring.js:8 (js_import); public/app/trust/wiring.js:8 (literal_reference) |
| public/app/generated/bim.js | True | 56339 | 2026-08-15T08:59:34Z | tests/remediation/test_csp_style_architecture.js:128 (literal_reference); public/app/main.js:15 (js_import); public/app/main.js:15 (literal_reference) |
| public/app/generated/docs.js | True | 115993 | 2026-08-15T09:55:47Z | tests/remediation/test_csp_style_architecture.js:127 (literal_reference); public/app/main.js:16 (js_import); public/app/main.js:16 (literal_reference) |
| public/app/generated/pbr-bridge.js | True | 45991 | 2026-08-15T08:59:34Z | tests/remediation/test_alignment_diagnostics.js:16 (literal_reference); public/app/main.js:20 (js_import); public/app/main.js:20 (literal_reference); public/app/generated/arch-detail-bridge.js:9 (js_import); public/app/generated/arch-detail-bridge.js:9 (literal_reference); public/app/ui/workspace-ui-wiring.js:11 (js_import); public/app/ui/workspace-ui-wiring.js:11 (literal_reference) |
| public/app/generated/pbr.js | True | 74050 | 2026-08-15T08:59:34Z | tests/remediation/test_apply_render_browser.js:78 (literal_reference); tests/remediation/test_csp_style_architecture.js:129 (literal_reference); tests/remediation/test_scene_benchmark.js:131 (literal_reference); public/app/main.js:17 (js_import); public/app/main.js:17 (literal_reference); public/app/generated/pbr-bridge.js:10 (js_import); public/app/generated/pbr-bridge.js:10 (literal_reference); public/app/generated/arch-detail-bridge.js:10 (js_import); public/app/generated/arch-detail-bridge.js:10 (literal_reference); public/app/generated/arch-detail.js:8 (js_import); public/app/generated/arch-detail.js:8 (literal_reference) |
| public/app/generated/render-engine.js | True | 99740 | 2026-08-15T09:55:47Z | tests/remediation/test_csp_style_architecture.js:126 (literal_reference); public/app/main.js:14 (js_import); public/app/main.js:14 (literal_reference) |
| public/app/generated/runtime.js | True | 75987 | 2026-08-15T08:59:34Z | tests/remediation/test_csp_style_architecture.js:131 (literal_reference); public/app/main.js:11 (js_import); public/app/main.js:11 (literal_reference); public/app/generated/workspace-ui.js:12 (js_import); public/app/generated/workspace-ui.js:12 (literal_reference) |
| public/app/generated/workspace-ui.js | True | 103991 | 2026-08-15T09:55:47Z | tests/remediation/test_csp_style_architecture.js:125 (literal_reference); public/app/main.js:13 (js_import); public/app/main.js:13 (literal_reference) |
| public/app/importmap.sha256 | True | 52 | 2026-08-15T08:59:34Z | None found statically |
| public/app/late-bindings.js | True | 1341 | 2026-08-15T08:59:34Z | public/app/main.js:7 (js_import); public/app/main.js:7 (literal_reference); public/app/generated/pbr-bridge.js:7 (js_import); public/app/generated/pbr-bridge.js:7 (literal_reference); public/app/generated/workspace-ui.js:7 (js_import); public/app/generated/workspace-ui.js:7 (literal_reference); public/app/generated/pbr.js:7 (js_import); public/app/generated/pbr.js:7 (literal_reference); public/app/ui/workspace-ui-wiring.js:7 (js_import); public/app/ui/workspace-ui-wiring.js:7 (literal_reference); public/app/core/standards.js:7 (js_import); public/app/core/standards.js:7 (literal_reference); public/app/core/viewer.js:7 (js_import); public/app/core/viewer.js:7 (literal_reference); public/app/core/disciplines.js:6 (js_import); public/app/core/disciplines.js:6 (literal_reference); public/app/render/scene.js:6 (js_import); public/app/render/scene.js:6 (literal_reference) |
| public/app/main.js | True | 1372 | 2026-08-15T09:00:09Z | public/index.html:483 (literal_reference); tools/frontend_shell.js:178 (literal_reference); tools/check_index_guard.py:166 (literal_reference); tests/deploy/verify_page_boot.js:207 (literal_reference); tests/deploy/verify_deploy.py:165 (literal_reference); tests/deploy/verify_deploy.py:166 (literal_reference); tests/deploy/verify_deploy.py:724 (literal_reference); tests/production/verify_live.py:315 (literal_reference); tests/production/verify_live.py:572 (literal_reference); tests/production/verify_live.py:589 (literal_reference); tests/production/verify_live.py:715 (literal_reference); tests/production/verify_live_browser.js:384 (literal_reference); tests/remediation/test_panel_entry.js:264 (literal_reference); tests/remediation/test_privacy_boundary.py:109 (literal_reference); tests/remediation/test_webgl_diagnostics.js:471 (literal_reference); tests/remediation/test_accessibility.js:436 (literal_reference) |
| public/app/render/scene.js | True | 165257 | 2026-08-15T08:59:34Z | public/app/main.js:19 (js_import); public/app/main.js:19 (literal_reference); public/app/generated/pbr-bridge.js:11 (js_import); public/app/generated/pbr-bridge.js:11 (literal_reference); public/app/generated/arch-detail-bridge.js:11 (js_import); public/app/generated/arch-detail-bridge.js:11 (literal_reference); public/app/ui/workspace-ui-wiring.js:12 (js_import); public/app/ui/workspace-ui-wiring.js:12 (literal_reference); public/app/trust/wiring.js:9 (js_import); public/app/trust/wiring.js:9 (literal_reference) |
| public/app/shared-state.js | True | 1116 | 2026-08-15T14:58:14Z | tests/remediation/test_apply_render_browser.js:79 (literal_reference); public/app/main.js:6 (js_import); public/app/main.js:6 (literal_reference); public/app/ui/workspace-ui-wiring.js:6 (js_import); public/app/ui/workspace-ui-wiring.js:6 (literal_reference); public/app/core/standards.js:6 (js_import); public/app/core/standards.js:6 (literal_reference); public/app/core/viewer.js:6 (js_import); public/app/core/viewer.js:6 (literal_reference); public/app/trust/wiring.js:7 (js_import); public/app/trust/wiring.js:7 (literal_reference) |
| public/app/styles/app.css | True | 53599 | 2026-08-15T09:55:47Z | public/index.html:28 (literal_reference); tools/bundle_report.py:43 (literal_reference); tools/frontend_shell.js:180 (literal_reference); tools/check_index_guard.py:197 (literal_reference); tests/deploy/verify_deploy.py:591 (literal_reference); tests/deploy/verify_deploy.py:592 (literal_reference); tests/production/verify_live.py:318 (literal_reference); tests/remediation/test_dependency_lock.py:384 (literal_reference); tests/remediation/test_privacy_boundary.py:111 (literal_reference); tests/remediation/test_privacy_boundary.py:192 (literal_reference); tests/phase3/lib/build_browser_page.js:496 (literal_reference) |
| public/app/trust/core.js | True | 50069 | 2026-08-16T16:23:15+03:00 | tests/deploy/verify_deploy.py:1216 (literal_reference); tests/remediation/test_privacy_boundary.py:110 (literal_reference); tests/remediation/test_accessibility.js:422 (literal_reference); public/app/main.js:23 (js_import); public/app/main.js:23 (literal_reference); public/app/trust/wiring.js:10 (js_import); public/app/trust/wiring.js:10 (literal_reference) |
| public/app/trust/wiring.js | True | 36038 | 2026-08-15T08:59:34Z | public/app/main.js:24 (js_import); public/app/main.js:24 (literal_reference) |
| public/app/ui/panels-entry.js | True | 9204 | 2026-08-15T09:55:47Z | public/app/main.js:29 (js_import); public/app/main.js:29 (literal_reference) |
| public/app/ui/workspace-ui-wiring.js | True | 200958 | 2026-08-15T16:43:12Z | tests/remediation/test_panel_entry.js:258 (literal_reference); tests/remediation/_transport_source.js:6 (literal_reference); public/app/main.js:22 (js_import); public/app/main.js:22 (literal_reference); public/app/trust/wiring.js:11 (js_import); public/app/trust/wiring.js:11 (literal_reference) |
| public/assets/env/README.txt | True | 426 | 2026-08-15T08:59:34Z | None found statically |
| public/assets/materials/README.txt | True | 423 | 2026-08-15T08:59:34Z | None found statically |
| public/index.html | True | 47424 | 2026-08-15T09:55:47Z | None found statically |
| public/privacy.html | True | 13113 | 2026-08-15T08:59:34Z | None found statically |
| public/robots.txt | True | 1547 | 2026-08-15T08:59:34Z | None found statically |
| public/sitemap.xml | True | 900 | 2026-08-15T08:59:34Z | None found statically |
| render.yaml | True | 5909 | 2026-08-15T21:54:32+03:00 | None found statically |
| requirements-dev.in | False | 93 | 2026-09-06T11:25:55.153901+00:00 | None found statically |
| requirements-dev.txt | False | 8195 | 2026-09-06T11:25:55.153901+00:00 | None found statically |
| requirements.in | True | 3048 | 2026-08-15T08:59:34Z | None found statically |
| requirements.lock | True | 6488 | 2026-08-15T08:59:34Z | None found statically |
| requirements.txt | True | 1812 | 2026-08-15T08:59:34Z | None found statically |
| tests/deploy/lib_alignment_expectations.js | False | 1265 | 2026-09-06T11:25:55.155010+00:00 | tests/remediation/test_alignment_diagnostics.js:6 (literal_reference) |
| tests/deploy/lib_viewport_pixels.js | True | 5979 | 2026-08-15T08:59:34Z | tests/deploy/verify_page_boot.js:25 (literal_reference); tests/deploy/test_viewport_pixels.js:17 (literal_reference); tests/deploy/verify_deploy.py:991 (literal_reference); tests/deploy/verify_deploy.py:1003 (literal_reference) |
| tests/deploy/test_viewport_pixels.js | True | 13691 | 2026-08-15T08:59:34Z | tests/deploy/verify_deploy.py:992 (literal_reference); tests/deploy/verify_deploy.py:1025 (literal_reference) |
| tests/deploy/verify_backend_live.py | True | 20890 | 2026-08-16T04:41:41+03:00 | None found statically |
| tests/deploy/verify_deploy.py | True | 71408 | 2026-08-16T16:23:15+03:00 | None found statically |
| tests/deploy/verify_deploy.sh | True | 2427 | 2026-08-15T08:59:34Z | None found statically |
| tests/deploy/verify_page_boot.js | True | 31821 | 2026-08-15T08:59:34Z | tools/dependency_audit.py:138 (literal_reference); tools/dependency_audit.py:140 (literal_reference); tests/deploy/verify_deploy.py:979 (literal_reference); tests/deploy/verify_deploy.py:994 (literal_reference); tests/deploy/verify_deploy.py:995 (literal_reference); tests/deploy/verify_deploy.py:997 (literal_reference); tests/deploy/verify_deploy.py:998 (literal_reference); tests/deploy/verify_deploy.py:1000 (literal_reference); tests/deploy/verify_deploy.py:1001 (literal_reference); tests/deploy/verify_deploy.py:1115 (literal_reference); tests/deploy/verify_deploy.py:1276 (literal_reference); tests/remediation/test_dependency_lock.py:338 (literal_reference); tests/remediation/test_dependency_lock.py:338 (literal_reference); tests/remediation/test_webgl_diagnostics.js:673 (literal_reference) |
| tests/lib/app_source.js | True | 6499 | 2026-08-15T08:59:34Z | tests/remediation/test_bundle_extractor.js:52 (literal_reference) |
| tests/lib/js_segment.js | False | 11142 | 2026-09-06T11:25:55.155848+00:00 | tests/remediation/test_bundle_extractor.js:51 (literal_reference) |
| tests/lib/run.js | True | 1593 | 2026-08-15T08:59:34Z | tests/remediation/test_opening_identity_parity.js:7 (literal_reference); tests/remediation/test_bundle_extractor.js:53 (literal_reference) |
| tests/performance/budgets.json | True | 13226 | 2026-08-15T08:59:34Z | tests/performance/run_perf.js:49 (literal_reference); tests/performance/run_perf.js:770 (literal_reference); tests/performance/run_perf.js:864 (literal_reference); tests/remediation/test_performance.js:341 (literal_reference) |
| tests/performance/bundle_report.json | True | 15341 | 2026-08-16T16:23:15+03:00 | tools/bundle_report.py:44 (literal_reference) |
| tests/performance/frontend_analysis.json | True | 55134 | 2026-08-15T08:59:34Z | None found statically |
| tests/performance/outputs/perf.json | True | 8842 | 2026-08-16T04:41:41+03:00 | None found statically |
| tests/performance/quality_governor.json | True | 11779 | 2026-08-15T08:59:34Z | tests/performance/run_perf.js:51 (literal_reference); tests/performance/run_perf.js:772 (literal_reference); tests/performance/run_perf.js:865 (literal_reference) |
| tests/performance/run_perf.js | True | 41114 | 2026-08-15T08:59:34Z | None found statically |
| tests/performance/vacuity_page.html | True | 5205 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase1/test_gate.js | True | 3620 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase1/test_p0.js | True | 3446 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase1/test_phase2.js | True | 8557 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase1/test_prov.js | True | 8964 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase1/test_types.js | True | 4763 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase1/test_xss.js | True | 1168 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/arch_scen.json | True | 8437 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/coord_scen.json | True | 19386 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/dist_scen.json | True | 26632 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/eg_queries.json | True | 317 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/fixtures.json | True | 4574 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/fls_scen.json | True | 35671 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/ing_scen.json | True | 2844 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/mep_scen.json | True | 32173 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/nav_queries.json | True | 423 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/occ_scen.json | True | 1777 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/rev_scen.json | True | 17511 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/rule_scen.json | True | 21698 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/sha_cases.json | True | 1318 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/struct_scen.json | True | 45912 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/fixtures/type_cases.json | True | 898 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/compare.js | True | 2138 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/js_arch_body.js | True | 1567 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/js_coord_body.js | True | 2813 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/js_dist_body.js | True | 1194 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/js_fls_body.js | True | 1183 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/js_ing_body.js | True | 5330 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/js_mep_body.js | True | 1199 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/js_occ_body.js | True | 5898 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/js_rev_body.js | True | 1597 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/js_rules_body.js | True | 1321 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/js_struct_body.js | True | 1629 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/py_arch.py | True | 1938 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/py_coord.py | True | 3513 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/py_dist.py | True | 1659 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/py_fls.py | True | 1743 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/py_ing.py | True | 6126 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/py_mep.py | True | 1721 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/py_occ.py | True | 6519 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/py_rev.py | True | 1930 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/py_rules.py | True | 1757 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/parity/py_struct.py | True | 2082 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_arch.js | True | 24801 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_coord.js | True | 27684 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_dist.js | True | 19001 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_eg.js | True | 10301 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_fls.js | True | 33643 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_ingest.js | True | 37613 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_mep.js | True | 34622 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_nav.js | True | 7118 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_occ.js | True | 20176 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_rel.js | True | 8698 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_render.js | True | 15212 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_rev.js | True | 22716 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_rules.js | True | 24150 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase2/test_struct.js | True | 32112 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/fixtures/base_fixtures.json | True | 9030 | 2026-08-15T08:59:34Z | tests/security/test_security.py:746 (literal_reference); tests/performance/run_perf.js:370 (literal_reference); tests/remediation/test_performance.js:298 (literal_reference) |
| tests/phase3/fixtures/fls_fixtures.json | True | 9415 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/fixtures/mep_fixtures.json | True | 35393 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/fixtures/mesh_baseline.json | True | 72387 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/fixtures/visual_scenarios.json | True | 51236 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/gen_visual_fixtures.js | True | 6444 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/lib/build_browser_page.js | True | 10918 | 2026-08-15T08:59:34Z | tests/phase3/lib/run_browser.js:10 (literal_reference) |
| tests/phase3/lib/extract_browser_bundle.js | True | 13687 | 2026-08-15T14:58:14Z | tests/remediation/test_bundle_extractor.js:54 (literal_reference); tests/phase3/lib/build_browser_page.js:129 (literal_reference); tests/phase3/lib/run.js:16 (literal_reference) |
| tests/phase3/lib/run.js | True | 1711 | 2026-08-15T08:59:34Z | tests/remediation/test_bundle_extractor.js:55 (literal_reference) |
| tests/phase3/lib/run_browser.js | True | 4108 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/lib_app_files.js | True | 3399 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/mesh_invariance_dump.js | True | 3153 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/parity/compare.js | True | 3937 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/parity/js_visual_body.js | True | 8487 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/parity/py_visual.py | True | 11334 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/perf_visual.js | True | 3272 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/perf_visual.py | True | 2754 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/run_all.sh | True | 2864 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/test_dev_api.js | True | 6927 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/test_visual.js | True | 44868 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase3/test_visual_adversarial.js | True | 21323 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase4/benchmark_runtime.js | True | 4777 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase4/benchmark_runtime.py | True | 5265 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase4/fixture_generator.js | True | 4609 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase4/fixtures/runtime_scenarios.json | True | 31444 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase4/lib_runtime_fixtures.js | True | 805 | 2026-08-15T08:59:34Z | tests/phase4/test_runtime.js:5 (literal_reference); tests/phase4/test_visibility.js:5 (literal_reference); tests/phase4/test_collision.js:5 (literal_reference); tests/phase4/test_selection.js:5 (literal_reference); tests/phase4/test_measurement.js:5 (literal_reference); tests/phase4/test_navigation.js:5 (literal_reference); tests/phase4/benchmark_runtime.js:10 (literal_reference); tests/phase4/test_portals.js:5 (literal_reference); tests/phase4/test_adversarial.js:5 (literal_reference); tests/phase4/test_immutability.js:5 (literal_reference) |
| tests/phase4/lib_runtime_fixtures.py | True | 749 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase4/parity/compare.js | True | 3755 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase4/parity/js_runtime_body.js | True | 8192 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase4/parity/py_runtime.py | True | 9623 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase4/run_all.sh | True | 3824 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase4/test_adversarial.js | True | 15283 | 2026-08-15T08:59:34Z | tests/phase4/test_browser_parity.js:27 (literal_reference) |
| tests/phase4/test_browser_parity.js | True | 6387 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase4/test_collision.js | True | 14322 | 2026-08-15T08:59:34Z | tests/phase4/test_browser_parity.js:25 (literal_reference) |
| tests/phase4/test_immutability.js | True | 14726 | 2026-08-15T08:59:34Z | tests/phase4/test_browser_parity.js:27 (literal_reference) |
| tests/phase4/test_measurement.js | True | 21307 | 2026-08-15T08:59:34Z | tests/phase4/test_browser_parity.js:26 (literal_reference) |
| tests/phase4/test_model_regression.js | True | 6383 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase4/test_navigation.js | True | 4961 | 2026-08-15T08:59:34Z | tests/phase4/test_browser_parity.js:25 (literal_reference) |
| tests/phase4/test_parity.js | True | 5265 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase4/test_portals.js | True | 12113 | 2026-08-15T08:59:34Z | tests/phase4/test_browser_parity.js:26 (literal_reference) |
| tests/phase4/test_runtime.js | True | 10400 | 2026-08-15T08:59:34Z | tests/phase4/test_browser_parity.js:25 (literal_reference) |
| tests/phase4/test_selection.js | True | 15941 | 2026-08-15T08:59:34Z | tests/phase4/test_browser_parity.js:26 (literal_reference) |
| tests/phase4/test_visibility.js | True | 19188 | 2026-08-15T08:59:34Z | tests/phase4/test_browser_parity.js:26 (literal_reference) |
| tests/phase5/benchmark_authoring.js | True | 4982 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase5/benchmark_authoring.py | True | 5475 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase5/fixture_generator.js | True | 14768 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase5/fixtures/authoring_scenarios.json | True | 35185 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase5/lib_authoring_fixtures.js | True | 1154 | 2026-08-15T08:59:34Z | tests/phase5/test_transaction.js:5 (literal_reference); tests/phase5/test_authoring.js:5 (literal_reference); tests/phase5/benchmark_authoring.js:9 (literal_reference); tests/phase5/test_adversarial.js:5 (literal_reference); tests/phase5/test_revision.js:5 (literal_reference); tests/phase5/test_immutability.js:5 (literal_reference); tests/phase5/test_integration.js:5 (literal_reference); tests/phase5/test_ai_boundary.js:5 (literal_reference); tests/phase5/test_browser.js:5 (literal_reference); tests/phase5/test_commands.js:5 (literal_reference) |
| tests/phase5/lib_authoring_fixtures.py | True | 767 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase5/parity/compare.js | True | 4124 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase5/parity/js_authoring_body.js | True | 6019 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase5/parity/py_authoring.py | True | 6594 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase5/run_all.sh | True | 4024 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase5/test_adversarial.js | True | 12581 | 2026-08-15T08:59:34Z | tests/phase5/test_immutability.js:263 (literal_reference); tests/phase5/test_browser_parity.js:30 (literal_reference) |
| tests/phase5/test_ai_boundary.js | True | 12111 | 2026-08-15T08:59:34Z | tests/phase5/test_browser_parity.js:29 (literal_reference) |
| tests/phase5/test_authoring.js | True | 18093 | 2026-08-15T08:59:34Z | tests/phase5/test_browser_parity.js:28 (literal_reference) |
| tests/phase5/test_browser.js | True | 9621 | 2026-08-15T08:59:34Z | tests/phase5/test_browser_parity.js:30 (literal_reference) |
| tests/phase5/test_browser_parity.js | True | 6866 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase5/test_commands.js | True | 24400 | 2026-08-15T08:59:34Z | tests/phase5/test_browser_parity.js:28 (literal_reference) |
| tests/phase5/test_immutability.js | True | 16316 | 2026-08-15T08:59:34Z | tests/phase5/test_browser_parity.js:30 (literal_reference); tests/phase5/test_browser_parity.js:44 (literal_reference) |
| tests/phase5/test_integration.js | True | 14686 | 2026-08-15T08:59:34Z | tests/phase5/test_browser_parity.js:29 (literal_reference) |
| tests/phase5/test_parity.js | True | 6632 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase5/test_revision.js | True | 15435 | 2026-08-15T08:59:34Z | tests/phase5/test_browser_parity.js:29 (literal_reference) |
| tests/phase5/test_transaction.js | True | 18524 | 2026-08-15T08:59:34Z | tests/phase5/test_browser_parity.js:28 (literal_reference) |
| tests/phase6/benchmark_workspace.js | True | 5404 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/benchmark_workspace.py | True | 6713 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/lib_workspace_fixtures.js | True | 482 | 2026-08-15T08:59:34Z | tests/phase6/benchmark_workspace.js:9 (literal_reference); tests/phase6/test_workspace.js:5 (literal_reference); tests/phase6/test_security.js:5 (literal_reference); tests/phase6/test_workflow.js:5 (literal_reference); tests/phase6/test_dom.js:5 (literal_reference) |
| tests/phase6/lib_workspace_fixtures.py | True | 598 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/parity/compare.js | True | 4296 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/parity/js_workspace_body.js | True | 8644 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/parity/py_workspace.py | True | 9809 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/run_all.sh | True | 5329 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/screenshots/EDIT_PREVIEW.png | True | 137963 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/screenshots/EMPTY.png | True | 35986 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/screenshots/ISSUE_SELECTED.png | True | 93103 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/screenshots/MOBILE.png | True | 12616 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/screenshots/PROJECT_GENERATED.png | True | 59752 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/screenshots/ROOM_SELECTED.png | True | 112626 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/screenshots/RTL.png | True | 28974 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/test_dom.js | True | 28093 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/test_parity.js | True | 8504 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/test_responsive.js | True | 16643 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/test_security.js | True | 13674 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/test_workflow.js | True | 23930 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/test_workspace.js | True | 18282 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/walkthrough.js | True | 20518 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase6/walkthrough_result.json | True | 2907 | 2026-08-15T08:59:34Z | tests/phase6/walkthrough.js:493 (literal_reference) |
| tests/phase7/benchmark_render.js | True | 3556 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/fixture_generator.js | True | 2466 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/fixtures/render_fixtures.json | True | 18758 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/lib_render_fixtures.js | True | 609 | 2026-08-15T08:59:34Z | tests/phase7/make_outputs.js:6 (literal_reference); tests/phase7/benchmark_render.js:6 (literal_reference); tests/phase7/test_targets.js:5 (literal_reference); tests/phase7/test_render.js:5 (literal_reference); tests/phase7/test_security.js:5 (literal_reference) |
| tests/phase7/lib_render_fixtures.py | True | 648 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/make_outputs.js | True | 3816 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/MANIFEST.json | True | 16299 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/clinic_buffer_depth.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/clinic_buffer_edge.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/clinic_buffer_object_id.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/clinic_buffer_semantic_mask.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/clinic_elevation_east.svg | True | 5731 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/clinic_elevation_north.svg | True | 5708 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/clinic_elevation_south.svg | True | 5708 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/clinic_elevation_west.svg | True | 5731 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/clinic_plan_level0.svg | True | 5826 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/clinic_section_x.svg | True | 5151 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/clinic_section_z.svg | True | 5074 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/hotel_buffer_depth.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/hotel_buffer_edge.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/hotel_buffer_object_id.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/hotel_buffer_semantic_mask.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/hotel_elevation_east.svg | True | 11212 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/hotel_elevation_north.svg | True | 11080 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/hotel_elevation_south.svg | True | 11080 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/hotel_elevation_west.svg | True | 11212 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/hotel_plan_level0.svg | True | 2859 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/hotel_plan_level1.svg | True | 4621 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/hotel_plan_level2.svg | True | 4621 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/hotel_section_x.svg | True | 10225 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/hotel_section_z.svg | True | 9975 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/villa_buffer_depth.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/villa_buffer_edge.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/villa_buffer_object_id.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/villa_buffer_semantic_mask.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/villa_elevation_east.svg | True | 13588 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/villa_elevation_north.svg | True | 13543 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/villa_elevation_south.svg | True | 13543 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/villa_elevation_west.svg | True | 13588 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/villa_plan_level0.svg | True | 7661 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/villa_plan_level1.svg | True | 6486 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/villa_section_x.svg | True | 12318 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/villa_section_z.svg | True | 12181 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/warehouse_buffer_depth.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/warehouse_buffer_edge.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/warehouse_buffer_object_id.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/warehouse_buffer_semantic_mask.png | True | 64268 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/warehouse_elevation_east.svg | True | 4442 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/warehouse_elevation_north.svg | True | 4457 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/warehouse_elevation_south.svg | True | 4457 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/warehouse_elevation_west.svg | True | 4442 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/warehouse_plan_level0.svg | True | 4565 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/warehouse_section_x.svg | True | 4008 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/outputs/warehouse_section_z.svg | True | 4010 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/parity/compare.js | True | 3743 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/parity/js_render_body.js | True | 9001 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/parity/py_render.py | True | 11664 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/run_all.sh | True | 4860 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/test_parity.js | True | 7372 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/test_render.js | True | 39201 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/test_security.js | True | 22054 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase7/test_targets.js | True | 24782 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/benchmark_bim.py | True | 5981 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/fixture_generator.py | True | 4087 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/fixtures/roundtrip_report.json | True | 1776 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/fixtures/staging_hostile.json | True | 16988 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/fixtures/staging_parity.json | True | 882018 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/lib_bim_fixtures.js | True | 1056 | 2026-08-15T08:59:34Z | tests/phase8/test_bim_browser.js:10 (literal_reference) |
| tests/phase8/lib_bim_fixtures.py | True | 2474 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/lib_large_fixture.py | True | 2144 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/make_outputs.py | True | 4920 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/benchmark_bim.json | True | 7257 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/clinic.ifc | True | 17281 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/clinic.manifest.json | True | 1247 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/clinic.roundtrip.json | True | 2153 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/clinic_glazed.ifc | True | 23690 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/clinic_glazed.manifest.json | True | 1247 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/clinic_glazed.roundtrip.json | True | 2155 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/hotel.ifc | True | 32785 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/hotel.manifest.json | True | 2060 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/hotel.roundtrip.json | True | 2748 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/hotel_glazed.ifc | True | 39434 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/hotel_glazed.manifest.json | True | 2061 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/hotel_glazed.roundtrip.json | True | 2753 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/index.json | True | 8099 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/office.ifc | True | 21472 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/office.manifest.json | True | 1737 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/office.roundtrip.json | True | 2542 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/synthetic_grid.ifc | True | 2246817 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/synthetic_grid.manifest.json | True | 2338 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/synthetic_grid.roundtrip.json | True | 2340 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/synthetic_grid_large.ifc | True | 5276347 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/synthetic_grid_large.manifest.json | True | 2961 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/synthetic_grid_large.roundtrip.json | True | 2441 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/villa.ifc | True | 36856 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/villa.manifest.json | True | 1403 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/villa.roundtrip.json | True | 2182 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/villa_glazed.ifc | True | 51153 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/villa_glazed.manifest.json | True | 1404 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/villa_glazed.roundtrip.json | True | 2185 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/villa_glazed_edited.ifc | True | 51161 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/villa_glazed_edited.manifest.json | True | 1404 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/villa_glazed_import_report.json | True | 16109 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/villa_single_level.ifc | True | 30275 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/villa_single_level.manifest.json | True | 1248 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/villa_single_level.roundtrip.json | True | 2158 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/warehouse.ifc | True | 13949 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/warehouse.manifest.json | True | 1247 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/warehouse.roundtrip.json | True | 2153 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/warehouse_glazed.ifc | True | 16739 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/warehouse_glazed.manifest.json | True | 1247 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/outputs/warehouse_glazed.roundtrip.json | True | 2153 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/parity/compare.js | True | 3936 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/parity/js_bim_body.js | True | 5861 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/parity/py_bim.py | True | 7616 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/run_all.sh | True | 4758 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/test_bim.py | True | 43937 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/test_bim_browser.js | True | 13534 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase8/test_parity.js | True | 9033 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/benchmark_docs.py | True | 6189 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/lib_docs_fixtures.js | True | 1854 | 2026-08-15T08:59:34Z | tests/phase9/test_docs_browser.js:10 (literal_reference) |
| tests/phase9/lib_docs_fixtures.py | True | 3890 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/make_outputs.py | True | 10121 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/ARTIFACT-MANIFEST.json | True | 22744 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/benchmark_docs.json | True | 6444 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_beam_schedule.json | True | 4630 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_column_schedule.json | True | 6514 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_coordination_plan_flr_0_coordination.svg | True | 5821 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_coordination_plan_flr_1_coordination.svg | True | 5558 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_documentation.json | True | 18288 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_floor_plan_flr_0.svg | True | 6153 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_foundation_schedule.json | True | 5789 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_mep_equipment_schedule.json | True | 1188 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_mep_plan_flr_0_mechanical.svg | True | 4959 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_mep_plan_flr_1_mechanical.svg | True | 3954 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_quantities.json | True | 7944 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_sheets.pdf | True | 13742 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_structural_plan_flr_0_structure.svg | True | 7041 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clash_mep_structural_plan_flr_1_structure.svg | True | 7403 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clinic_documentation.json | True | 9504 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clinic_door_schedule.json | True | 6108 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clinic_floor_plan_flr_0.svg | True | 4563 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clinic_quantities.json | True | 5893 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clinic_room_schedule.json | True | 4561 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/clinic_sheets.pdf | True | 2208 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/hotel_documentation.json | True | 12295 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/hotel_door_schedule.json | True | 11540 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/hotel_elevation_north.svg | True | 2116 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/hotel_floor_plan_flr_0.svg | True | 2860 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/hotel_quantities.json | True | 6914 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/hotel_room_schedule.json | True | 8552 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/hotel_section_x6p0.svg | True | 6446 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/hotel_sheets.pdf | True | 4382 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_fls_documentation.json | True | 12978 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_fls_floor_plan_flr_0.svg | True | 6153 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_fls_fls_device_schedule.json | True | 2373 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_fls_fls_plan_flr_0_fire_protection.svg | True | 6367 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_fls_fls_plan_flr_1_fire_protection.svg | True | 4695 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_fls_fls_sign_schedule.json | True | 1146 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_fls_quantities.json | True | 7473 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_fls_sheets.pdf | True | 6319 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_documentation.json | True | 18014 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_door_schedule.json | True | 15624 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_elevation_east.svg | True | 3016 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_elevation_north.svg | True | 2916 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_elevation_south.svg | True | 2919 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_elevation_west.svg | True | 3029 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_floor_plan_flr_0.svg | True | 8753 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_floor_plan_flr_1.svg | True | 7437 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_quantities.json | True | 7740 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_room_schedule.json | True | 9339 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_section_x3p0.svg | True | 9427 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_section_z2p0.svg | True | 9600 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_sheets.pdf | True | 14613 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/villa_glazed_window_schedule.json | True | 20237 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/warehouse_documentation.json | True | 8811 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/warehouse_floor_plan_flr_0.svg | True | 3950 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/warehouse_quantities.json | True | 5788 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/warehouse_room_schedule.json | True | 3777 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/outputs/warehouse_sheets.pdf | True | 2141 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/parity/compare.js | True | 4105 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/parity/js_docs_body.js | True | 7374 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/parity/py_docs.py | True | 9627 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/run_all.sh | True | 4809 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/test_docs.py | True | 61688 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/test_docs_browser.js | True | 19073 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9/test_parity.js | True | 7682 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_1/benchmark_pbr.py | True | 6038 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_1/capture_reference.js | True | 8455 | 2026-08-15T08:59:34Z | tools/dependency_audit.py:141 (literal_reference); tools/dependency_audit.py:143 (literal_reference); tests/remediation/test_dependency_lock.py:340 (literal_reference); tests/remediation/test_dependency_lock.py:341 (literal_reference) |
| tests/phase9_1/outputs/benchmark_pbr.json | True | 4792 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_1/parity/compare.js | True | 2676 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_1/parity/js_pbr_body.js | True | 9067 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_1/parity/py_pbr.py | True | 11490 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_1/run_all.sh | True | 5170 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_1/test_parity.js | True | 2687 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_1/test_pbr.py | True | 16470 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_1/test_pbr_browser.js | True | 10032 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_2/capture_reference_92.js | True | 7937 | 2026-08-15T08:59:34Z | tools/dependency_audit.py:144 (literal_reference); tools/dependency_audit.py:146 (literal_reference); tests/remediation/test_dependency_lock.py:342 (literal_reference); tests/remediation/test_dependency_lock.py:343 (literal_reference) |
| tests/phase9_2/fixtures/alignment_expectations.json | False | 1331 | 2026-09-06T11:25:55.191367+00:00 | tests/deploy/lib_alignment_expectations.js:5 (js_import); tests/deploy/lib_alignment_expectations.js:5 (literal_reference) |
| tests/phase9_2/fixtures/live_large_generated.json | True | 147200 | 2026-08-15T08:59:34Z | tests/deploy/verify_deploy.py:1269 (literal_reference); tests/deploy/verify_deploy.py:1272 (literal_reference); tests/deploy/verify_deploy.py:1274 (literal_reference) |
| tests/phase9_2/fixtures/live_large_generated_outlier.json | True | 147407 | 2026-08-15T08:59:34Z | tests/deploy/verify_deploy.py:1270 (literal_reference) |
| tests/phase9_2/lib_ad_fixtures.py | True | 5303 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_2/parity/compare.js | True | 2543 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_2/parity/js_ad_body.js | True | 6811 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_2/parity/py_ad.py | True | 8284 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_2/run_all.sh | True | 6850 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_2/test_alignment.py | True | 21256 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_2/test_archdetail.py | True | 29057 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_2/test_archdetail_browser.js | True | 9944 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_2/test_backend_contract.py | True | 28534 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_2/test_black_viewport.py | True | 15206 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_2/test_generation_budget.py | True | 26970 | 2026-08-15T11:44:54Z | None found statically |
| tests/phase9_2/test_live_render.py | True | 23717 | 2026-08-15T08:59:34Z | None found statically |
| tests/phase9_2/test_parity.js | True | 2697 | 2026-08-15T08:59:34Z | None found statically |
| tests/production/outputs/summary.json | True | 761 | 2026-08-15T08:59:34Z | None found statically |
| tests/production/outputs/verify_live.json | True | 10902 | 2026-08-15T08:59:34Z | None found statically |
| tests/production/outputs/verify_live_browser.json | True | 10665 | 2026-08-15T08:59:34Z | None found statically |
| tests/production/run_all.sh | True | 7107 | 2026-08-15T08:59:34Z | None found statically |
| tests/production/verify_live.py | True | 52244 | 2026-08-15T08:59:34Z | None found statically |
| tests/production/verify_live_browser.js | True | 46692 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/_transport_source.js | False | 570 | 2026-09-06T11:25:55.192789+00:00 | tests/remediation/test_transport_browser.js:6 (js_import); tests/remediation/test_transport_browser.js:6 (literal_reference); tests/remediation/test_transport_errors.js:3 (js_import); tests/remediation/test_transport_errors.js:3 (literal_reference) |
| tests/remediation/_trust_core.js | True | 3282 | 2026-08-15T08:59:34Z | tests/remediation/test_model_review_ui.js:5 (literal_reference); tests/remediation/test_production_error_ui.js:8 (literal_reference); tests/remediation/test_transport_errors.js:4 (js_import); tests/remediation/test_transport_errors.js:4 (literal_reference); tests/remediation/test_persistence.js:10 (literal_reference); tests/remediation/test_concurrency.js:8 (literal_reference); tests/remediation/test_accessibility.js:28 (literal_reference); tests/remediation/test_accessibility.js:459 (literal_reference) |
| tests/remediation/csp_browser_probe.js | True | 37949 | 2026-08-15T08:59:34Z | tests/remediation/test_ci_gate.py:162 (literal_reference); tests/remediation/test_inline_style_sources.py:199 (literal_reference); tests/remediation/test_browser_acquisition.py:164 (literal_reference) |
| tests/remediation/fixtures/plate/footprint_equals_site.json | True | 1004 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/fixtures/plate/irregular_multi_room.json | True | 2220 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/fixtures/plate/l_shaped_footprint.json | True | 1495 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/fixtures/plate/mesh_baseline_phase1_site_wide.json | True | 72804 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/fixtures/plate/stacked_setback_floors.json | True | 1790 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/fixtures/plate/stair_void_footprint.json | True | 1849 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/fixtures/plate/villa_small_on_large_plot.json | True | 1923 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/lib_csp_harness.js | True | 20440 | 2026-08-15T09:55:47Z | tests/remediation/test_apply_render_browser.js:37 (literal_reference); tests/remediation/test_csp_style_architecture.js:45 (literal_reference); tests/remediation/test_scene_benchmark.js:34 (literal_reference) |
| tests/remediation/lib_gl_three.js | True | 19397 | 2026-08-15T14:58:14Z | tests/remediation/test_apply_render_browser.js:52 (literal_reference); tests/remediation/test_scene_benchmark.js:205 (literal_reference) |
| tests/remediation/lib_job_faults.py | False | 3416 | 2026-09-06T11:25:55.193606+00:00 | None found statically |
| tests/remediation/lib_loop_probe.py | True | 11850 | 2026-08-15T16:43:12Z | None found statically |
| tests/remediation/lib_resp_client.py | True | 4704 | 2026-08-15T16:43:12Z | None found statically |
| tests/remediation/outputs/csp_probe.json | True | 10476 | 2026-08-16T04:41:41+03:00 | None found statically |
| tests/remediation/outputs/scene_benchmark.json | True | 17348 | 2026-08-16T04:41:41+03:00 | None found statically |
| tests/remediation/run_all.sh | True | 9321 | 2026-08-16T16:23:15+03:00 | None found statically |
| tests/remediation/test_accessibility.js | True | 52777 | 2026-08-15T08:59:34Z | tests/remediation/test_ci_gate.py:161 (literal_reference); tests/remediation/test_browser_acquisition.py:165 (literal_reference) |
| tests/remediation/test_alignment_diagnostics.js | False | 6315 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_api_wiring.py | True | 9551 | 2026-08-16T04:41:41+03:00 | None found statically |
| tests/remediation/test_apply_render_browser.js | True | 21229 | 2026-08-15T14:58:14Z | tests/remediation/test_browser_acquisition.py:166 (literal_reference) |
| tests/remediation/test_asgi_client_contract.py | False | 14526 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_browser_acquisition.py | False | 24215 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_build_metadata.py | True | 23209 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/test_bundle_extractor.js | False | 10711 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_bundle_report.py | True | 28615 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/test_ci_dependencies.py | False | 13442 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_ci_gate.py | True | 14171 | 2026-08-16T04:41:41+03:00 | None found statically |
| tests/remediation/test_concurrency.js | True | 15559 | 2026-08-15T08:59:34Z | tests/remediation/test_ci_gate.py:160 (literal_reference) |
| tests/remediation/test_container_topology.py | False | 10098 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_csp.js | True | 39917 | 2026-08-15T08:59:34Z | tests/remediation/test_ci_gate.py:159 (literal_reference) |
| tests/remediation/test_csp_style_architecture.js | True | 32829 | 2026-08-15T09:55:47Z | tests/remediation/test_browser_acquisition.py:167 (literal_reference) |
| tests/remediation/test_dependency_lock.py | True | 22865 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/test_engineering_authority.py | True | 19381 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/test_event_loop.py | True | 27859 | 2026-08-16T04:41:41+03:00 | None found statically |
| tests/remediation/test_generation_cancel.py | True | 27137 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/test_gl_probe_contract.mjs | False | 3147 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_image_build_metadata.py | False | 6695 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_inline_style_sources.py | False | 13596 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_job_boundary.py | False | 13489 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_live_generation_verdict.py | False | 8205 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_logging.py | True | 29800 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/test_model_apply.js | True | 28473 | 2026-08-15T14:58:14Z | None found statically |
| tests/remediation/test_model_diagnostics.py | False | 6176 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_model_review_ui.js | False | 1868 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_module_graph.js | True | 17907 | 2026-08-15T08:59:34Z | tests/remediation/test_bundle_extractor.js:72 (literal_reference) |
| tests/remediation/test_multi_provider.py | True | 31993 | 2026-08-15T21:54:32+03:00 | None found statically |
| tests/remediation/test_opening_identity.js | False | 5985 | 2026-09-06T11:25:55.194362+00:00 | tests/remediation/test_opening_identity_parity.js:8 (literal_reference) |
| tests/remediation/test_opening_identity.py | False | 10415 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_opening_identity_parity.js | False | 969 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_p0_hardening.py | True | 21570 | 2026-08-16T04:41:41+03:00 | None found statically |
| tests/remediation/test_panel_entry.js | True | 24229 | 2026-08-15T09:00:09Z | tests/remediation/test_browser_acquisition.py:168 (literal_reference) |
| tests/remediation/test_pdf_runtime.mjs | False | 2339 | 2026-09-06T11:25:55.194362+00:00 | None found statically |
| tests/remediation/test_performance.js | True | 27689 | 2026-08-15T08:59:34Z | tests/remediation/test_ci_gate.py:168 (literal_reference) |
| tests/remediation/test_persistence.js | True | 20511 | 2026-08-15T08:59:34Z | tests/remediation/test_ci_gate.py:161 (literal_reference) |
| tests/remediation/test_plan_chunking.py | True | 36386 | 2026-08-15T14:58:14Z | None found statically |
| tests/remediation/test_plate_extent.py | True | 20247 | 2026-08-15T16:43:12Z | None found statically |
| tests/remediation/test_privacy_boundary.py | True | 25680 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/test_production_error_ui.js | True | 12202 | 2026-08-16T16:23:15+03:00 | tests/remediation/test_ci_gate.py:159 (literal_reference) |
| tests/remediation/test_provider_accounting.py | True | 20185 | 2026-08-16T05:22:59+03:00 | None found statically |
| tests/remediation/test_provider_capability.py | True | 37799 | 2026-08-16T16:23:15+03:00 | None found statically |
| tests/remediation/test_provider_integration.py | True | 27028 | 2026-08-15T10:49:48Z | None found statically |
| tests/remediation/test_provider_reject.py | True | 17828 | 2026-08-16T05:22:59+03:00 | None found statically |
| tests/remediation/test_rate_limit.py | True | 44101 | 2026-08-15T08:59:34Z | None found statically |
| tests/remediation/test_rule_source_boundary.py | False | 4736 | 2026-09-06T11:25:55.195982+00:00 | None found statically |
| tests/remediation/test_scene_benchmark.js | True | 16589 | 2026-08-15T16:43:12Z | tests/remediation/test_browser_acquisition.py:169 (literal_reference) |
| tests/remediation/test_scene_limits.js | True | 46712 | 2026-08-15T16:43:12Z | None found statically |
| tests/remediation/test_transport_browser.js | False | 4454 | 2026-09-06T11:25:55.195982+00:00 | None found statically |
| tests/remediation/test_transport_errors.js | False | 4526 | 2026-09-06T11:25:55.195982+00:00 | None found statically |
| tests/remediation/test_upload_security.py | True | 46341 | 2026-08-16T04:41:41+03:00 | None found statically |
| tests/remediation/test_webgl_diagnostics.js | True | 47487 | 2026-08-15T08:59:34Z | tests/remediation/test_ci_gate.py:160 (literal_reference); tests/remediation/test_browser_acquisition.py:170 (literal_reference) |
| tests/remediation_baseline/environment.txt | True | 296 | 2026-08-15T08:59:34Z | None found statically |
| tests/security/test_security.py | True | 64626 | 2026-08-15T08:59:34Z | None found statically |
| tools/_archdetail_bridge_block.js | True | 17118 | 2026-08-15T08:59:34Z | tools/build_archdetail_browser.py:884 (literal_reference) |
| tools/_pbr_bridge_block.js | True | 43496 | 2026-08-15T08:59:34Z | tools/check_integration.py:102 (literal_reference); tools/build_pbr_browser.py:1174 (literal_reference) |
| tools/_visual_api_block.js | True | 6103 | 2026-08-15T08:59:34Z | tools/build_visual_browser.py:29 (literal_reference) |
| tools/_visual_renderer_block.js | True | 5106 | 2026-08-15T08:59:34Z | tools/build_visual_browser.py:31 (literal_reference) |
| tools/app_source.py | True | 3067 | 2026-08-15T08:59:34Z | None found statically |
| tools/build_archdetail_browser.py | True | 41502 | 2026-08-15T08:59:34Z | None found statically |
| tools/build_authoring_browser.py | True | 94803 | 2026-08-15T08:59:34Z | None found statically |
| tools/build_bim_browser.py | True | 45779 | 2026-08-15T08:59:34Z | None found statically |
| tools/build_docs_browser.py | True | 102398 | 2026-08-15T09:55:47Z | None found statically |
| tools/build_pbr_browser.py | True | 56770 | 2026-08-15T08:59:34Z | None found statically |
| tools/build_render_browser.py | True | 82178 | 2026-08-15T09:55:47Z | None found statically |
| tools/build_runtime_browser.py | True | 58826 | 2026-08-15T08:59:34Z | None found statically |
| tools/build_visual_browser.py | True | 5136 | 2026-08-15T08:59:34Z | None found statically |
| tools/build_workspace_ui.py | True | 99141 | 2026-08-15T09:55:47Z | None found statically |
| tools/bundle_report.py | True | 22978 | 2026-08-15T08:59:34Z | None found statically |
| tools/check_api_base.py | True | 8817 | 2026-08-15T08:59:34Z | None found statically |
| tools/check_csp_hash.py | True | 7189 | 2026-08-15T08:59:34Z | None found statically |
| tools/check_harness_encapsulation.py | True | 4374 | 2026-08-15T08:59:34Z | None found statically |
| tools/check_index_guard.py | True | 18731 | 2026-08-15T08:59:34Z | None found statically |
| tools/check_integration.py | True | 14562 | 2026-08-15T08:59:34Z | None found statically |
| tools/ci_run.sh | True | 3477 | 2026-08-16T04:41:41+03:00 | None found statically |
| tools/csp_static_server.py | True | 15395 | 2026-08-15T08:59:34Z | None found statically |
| tools/dependency_audit.py | True | 16618 | 2026-08-15T08:59:34Z | None found statically |
| tools/frontend_analyze.js | True | 8072 | 2026-08-15T08:59:34Z | tools/frontend_split.js:31 (literal_reference); tests/remediation/test_bundle_extractor.js:75 (literal_reference) |
| tools/frontend_globals.txt | True | 2261 | 2026-08-15T08:59:34Z | None found statically |
| tools/frontend_shell.js | True | 11541 | 2026-08-15T08:59:34Z | None found statically |
| tools/frontend_split.js | True | 20100 | 2026-08-15T08:59:34Z | tests/remediation/test_bundle_extractor.js:74 (literal_reference) |
| tools/netlify-build.sh | True | 7563 | 2026-08-15T08:59:34Z | None found statically |
| tools/package_release.sh | True | 3507 | 2026-08-15T08:59:34Z | None found statically |
| tools/pw_chromium.js | True | 3028 | 2026-08-15T08:59:34Z | tests/remediation/test_browser_acquisition.py:154 (literal_reference) |
| tools/stamp_build_tokens.py | True | 5521 | 2026-08-15T08:59:34Z | None found statically |
| tools/vendor.sh | True | 5533 | 2026-08-15T09:00:09Z | None found statically |
| tools/verify-offline.mjs | True | 3820 | 2026-08-15T08:59:34Z | None found statically |
| tools/verify-provenance-browser.js | True | 7864 | 2026-08-15T08:59:34Z | None found statically |
| tools/write_build_info.py | True | 5052 | 2026-08-15T08:59:34Z | None found statically |
