# نتائج الاختبارات قبل الإصلاح

المصدر: `remediation/production-trust@962f8daec2f194957d1a4322ce1ed22fd39086ea`.
هذه أعداد **ملفات الاختبار**، وليست مجموع assertions فريداً: 109 محاولات، 93 PASS، 8 FAIL، 8 NOT_VERIFIED. بعض الملفات تجمع فحوص Node ناجحة مع فحوص DOM غير منفذة. كل المخرجات الأصلية محفوظة حرفياً في الروابط أدناه.

| الملف | النتيجة الخام | الخروج | الزمن بالثواني | الملخص الأصلي الأخير | السجل الكامل |
|---|---|---:|---:|---|---|
| tests/deploy/test_viewport_pixels.js | FAIL | 1 | 0.316 | VIEWPORT PIXEL TEST: 8 passed, 1 failed | [log](all-tests/tests__deploy__test_viewport_pixels.js.log) |
| tests/phase1/test_gate.js | FAIL | 1 | 0.317 | توقّف/لا ملخص | [log](all-tests/tests__phase1__test_gate.js.log) |
| tests/phase1/test_p0.js | PASS | 0 | 0.315 | RESULT: 17 passed, 0 failed | [log](all-tests/tests__phase1__test_p0.js.log) |
| tests/phase1/test_phase2.js | PASS | 0 | 0.265 | PHASE2: 47 passed, 0 failed | [log](all-tests/tests__phase1__test_phase2.js.log) |
| tests/phase1/test_prov.js | FAIL | 1 | 0.315 | توقّف/لا ملخص | [log](all-tests/tests__phase1__test_prov.js.log) |
| tests/phase1/test_types.js | PASS | 0 | 0.315 | TYPES RESULT: 33 passed, 0 failed | [log](all-tests/tests__phase1__test_types.js.log) |
| tests/phase1/test_xss.js | PASS | 0 | 0.368 | XSS: 6 passed, 0 failed | [log](all-tests/tests__phase1__test_xss.js.log) |
| tests/phase2/test_arch.js | PASS | 0 | 0.366 | ARCHITECTURE: 147 passed, 0 failed | [log](all-tests/tests__phase2__test_arch.js.log) |
| tests/phase2/test_coord.js | PASS | 0 | 0.417 | COORDINATION FOUNDATION: 131 passed, 0 failed | [log](all-tests/tests__phase2__test_coord.js.log) |
| tests/phase2/test_dist.js | PASS | 0 | 0.318 | DISTANCE: 80 passed, 0 failed | [log](all-tests/tests__phase2__test_dist.js.log) |
| tests/phase2/test_eg.js | PASS | 0 | 0.265 | EGRESS: 55 passed, 0 failed | [log](all-tests/tests__phase2__test_eg.js.log) |
| tests/phase2/test_fls.js | PASS | 0 | 0.416 | FLS: 169 passed, 0 failed | [log](all-tests/tests__phase2__test_fls.js.log) |
| tests/phase2/test_ingest.js | PASS | 0 | 0.315 | INGEST: 188 passed, 0 failed | [log](all-tests/tests__phase2__test_ingest.js.log) |
| tests/phase2/test_mep.js | PASS | 0 | 0.368 | MEP: 183 passed, 0 failed | [log](all-tests/tests__phase2__test_mep.js.log) |
| tests/phase2/test_nav.js | PASS | 0 | 0.269 | NAVIGATION: 43 passed, 0 failed | [log](all-tests/tests__phase2__test_nav.js.log) |
| tests/phase2/test_occ.js | PASS | 0 | 0.316 | OCCUPANCY: 98 passed, 0 failed | [log](all-tests/tests__phase2__test_occ.js.log) |
| tests/phase2/test_rel.js | PASS | 0 | 0.269 | RELATIONSHIPS: 48 passed, 0 failed | [log](all-tests/tests__phase2__test_rel.js.log) |
| tests/phase2/test_render.js | PASS | 0 | 0.317 | RENDER: 53 passed, 0 failed | [log](all-tests/tests__phase2__test_render.js.log) |
| tests/phase2/test_rev.js | PASS | 0 | 0.316 | REVISION: 99 passed, 0 failed | [log](all-tests/tests__phase2__test_rev.js.log) |
| tests/phase2/test_rules.js | PASS | 0 | 0.315 | RULES: 129 passed, 0 failed | [log](all-tests/tests__phase2__test_rules.js.log) |
| tests/phase2/test_struct.js | PASS | 0 | 0.365 | STRUCTURE: 177 passed, 0 failed | [log](all-tests/tests__phase2__test_struct.js.log) |
| tests/phase3/test_dev_api.js | PASS | 0 | 0.365 | VISUAL DEV API: 33 passed, 0 failed | [log](all-tests/tests__phase3__test_dev_api.js.log) |
| tests/phase3/test_visual.js | PASS | 0 | 0.868 | VISUAL FOUNDATION: 211 passed, 0 failed | [log](all-tests/tests__phase3__test_visual.js.log) |
| tests/phase3/test_visual_adversarial.js | PASS | 0 | 0.676 | VISUAL ADVERSARIAL: 115 passed, 0 failed | [log](all-tests/tests__phase3__test_visual_adversarial.js.log) |
| tests/phase4/test_adversarial.js | PASS | 0 | 0.316 | ADVERSARIAL: 457 passed, 0 failed | [log](all-tests/tests__phase4__test_adversarial.js.log) |
| tests/phase4/test_browser_parity.js | NOT_VERIFIED | 1 | 0.315 | توقّف/لا ملخص | [log](all-tests/tests__phase4__test_browser_parity.js.log) |
| tests/phase4/test_collision.js | PASS | 0 | 0.317 | COLLISION: 73 passed, 0 failed | [log](all-tests/tests__phase4__test_collision.js.log) |
| tests/phase4/test_immutability.js | PASS | 0 | 0.566 | IMMUTABILITY: 135 passed, 0 failed | [log](all-tests/tests__phase4__test_immutability.js.log) |
| tests/phase4/test_measurement.js | PASS | 0 | 0.365 | MEASUREMENT: 131 passed, 0 failed | [log](all-tests/tests__phase4__test_measurement.js.log) |
| tests/phase4/test_model_regression.js | PASS | 0 | 0.919 | MODEL REGRESSION: 23 passed, 0 failed | [log](all-tests/tests__phase4__test_model_regression.js.log) |
| tests/phase4/test_navigation.js | PASS | 0 | 0.265 |   ✓ unknown mode 42 fails deterministically<br>NAVIGATION: 39 passed, 0 failed | [log](all-tests/tests__phase4__test_navigation.js.log) |
| tests/phase4/test_parity.js | PASS | 0 | 0.916 | PARITY: 17 passed, 0 failed | [log](all-tests/tests__phase4__test_parity.js.log) |
| tests/phase4/test_portals.js | PASS | 0 | 0.315 | PORTALS: 45 passed, 0 failed | [log](all-tests/tests__phase4__test_portals.js.log) |
| tests/phase4/test_runtime.js | PASS | 0 | 0.466 | RUNTIME SCENE: 49 passed, 0 failed | [log](all-tests/tests__phase4__test_runtime.js.log) |
| tests/phase4/test_selection.js | PASS | 0 | 0.315 | SELECTION: 113 passed, 0 failed | [log](all-tests/tests__phase4__test_selection.js.log) |
| tests/phase4/test_visibility.js | PASS | 0 | 0.369 | VISIBILITY: 145 passed, 0 failed | [log](all-tests/tests__phase4__test_visibility.js.log) |
| tests/phase5/test_adversarial.js | PASS | 0 | 0.366 | AUTHORING ADVERSARIAL: 519 passed, 0 failed | [log](all-tests/tests__phase5__test_adversarial.js.log) |
| tests/phase5/test_ai_boundary.js | PASS | 0 | 0.315 | AI BOUNDARY: 67 passed, 0 failed | [log](all-tests/tests__phase5__test_ai_boundary.js.log) |
| tests/phase5/test_authoring.js | PASS | 0 | 0.315 | AUTHORING CONTRACT: 127 passed, 0 failed | [log](all-tests/tests__phase5__test_authoring.js.log) |
| tests/phase5/test_browser.js | PASS | 0 | 0.315 | AUTHORING BROWSER: 55 passed, 0 failed | [log](all-tests/tests__phase5__test_browser.js.log) |
| tests/phase5/test_browser_parity.js | NOT_VERIFIED | 1 | 0.315 | توقّف/لا ملخص | [log](all-tests/tests__phase5__test_browser_parity.js.log) |
| tests/phase5/test_commands.js | PASS | 0 | 0.367 | COMMANDS: 188 passed, 0 failed | [log](all-tests/tests__phase5__test_commands.js.log) |
| tests/phase5/test_immutability.js | PASS | 0 | 1.424 | IMMUTABILITY: 107 passed, 0 failed | [log](all-tests/tests__phase5__test_immutability.js.log) |
| tests/phase5/test_integration.js | PASS | 0 | 0.418 | INTEGRATION: 70 passed, 0 failed | [log](all-tests/tests__phase5__test_integration.js.log) |
| tests/phase5/test_parity.js | PASS | 0 | 0.967 | AUTHORING PARITY: 35 passed, 0 failed | [log](all-tests/tests__phase5__test_parity.js.log) |
| tests/phase5/test_revision.js | PASS | 0 | 0.365 | REVISIONS: 89 passed, 0 failed | [log](all-tests/tests__phase5__test_revision.js.log) |
| tests/phase5/test_transaction.js | PASS | 0 | 0.369 | TRANSACTIONS: 120 passed, 0 failed | [log](all-tests/tests__phase5__test_transaction.js.log) |
| tests/phase6/test_dom.js | PASS | 0 | 0.265 | WORKSPACE DOM: 1 passed, 0 failed | [log](all-tests/tests__phase6__test_dom.js.log) |
| tests/phase6/test_parity.js | PASS | 0 | 0.716 | WORKSPACE PARITY: 47 passed, 0 failed | [log](all-tests/tests__phase6__test_parity.js.log) |
| tests/phase6/test_responsive.js | NOT_VERIFIED | 1 | 0.766 | توقّف/لا ملخص | [log](all-tests/tests__phase6__test_responsive.js.log) |
| tests/phase6/test_security.js | PASS | 0 | 0.315 | WORKSPACE SECURITY: 168 passed, 0 failed | [log](all-tests/tests__phase6__test_security.js.log) |
| tests/phase6/test_workflow.js | PASS | 0 | 0.317 | WORKFLOW: 153 passed, 0 failed | [log](all-tests/tests__phase6__test_workflow.js.log) |
| tests/phase6/test_workspace.js | PASS | 0 | 0.365 | WORKSPACE CONTRACT: 113 passed, 0 failed | [log](all-tests/tests__phase6__test_workspace.js.log) |
| tests/phase7/test_parity.js | PASS | 0 | 1.774 | RENDER PARITY: 49 passed, 0 failed | [log](all-tests/tests__phase7__test_parity.js.log) |
| tests/phase7/test_render.js | PASS | 0 | 0.516 | RENDER CONTRACT: 272 passed, 0 failed | [log](all-tests/tests__phase7__test_render.js.log) |
| tests/phase7/test_security.js | PASS | 0 | 0.367 | RENDER SECURITY: 164 passed, 0 failed | [log](all-tests/tests__phase7__test_security.js.log) |
| tests/phase7/test_targets.js | PASS | 0 | 0.522 | RENDER TARGETS: 93 passed, 0 failed | [log](all-tests/tests__phase7__test_targets.js.log) |
| tests/phase8/test_bim.py | PASS | 0 | 2.722 | BIM EXCHANGE: 526 passed, 0 failed | [log](all-tests/tests__phase8__test_bim.py.log) |
| tests/phase8/test_bim_browser.js | PASS | 0 | 0.369 | BIM BROWSER: 4 passed, 0 failed | [log](all-tests/tests__phase8__test_bim_browser.js.log) |
| tests/phase8/test_parity.js | PASS | 0 | 0.671 | BIM PARITY SUITE: 54 passed, 0 failed | [log](all-tests/tests__phase8__test_parity.js.log) |
| tests/phase9/test_docs.py | PASS | 0 | 0.215 | DOCUMENTATION: 421 passed, 0 failed | [log](all-tests/tests__phase9__test_docs.py.log) |
| tests/phase9/test_docs_browser.js | PASS | 0 | 0.316 | DOCS BROWSER: 4 passed, 0 failed | [log](all-tests/tests__phase9__test_docs_browser.js.log) |
| tests/phase9/test_parity.js | PASS | 0 | 1.433 | DOCS PARITY SUITE: 72 passed, 0 failed | [log](all-tests/tests__phase9__test_parity.js.log) |
| tests/phase9_1/test_parity.js | PASS | 0 | 0.519 | PBR PARITY SUITE: 7 passed, 0 failed | [log](all-tests/tests__phase9_1__test_parity.js.log) |
| tests/phase9_1/test_pbr.py | PASS | 0 | 0.065 | PBR QUALITY: 156 passed, 0 failed | [log](all-tests/tests__phase9_1__test_pbr.py.log) |
| tests/phase9_1/test_pbr_browser.js | PASS | 0 | 0.318 | PBR BROWSER: 14 passed, 0 failed | [log](all-tests/tests__phase9_1__test_pbr_browser.js.log) |
| tests/phase9_2/test_alignment.py | PASS | 0 | 0.065 | ALIGNMENT REGRESSION: 92 passed, 0 failed | [log](all-tests/tests__phase9_2__test_alignment.py.log) |
| tests/phase9_2/test_archdetail.py | PASS | 0 | 0.115 | ARCH DETAIL: 168 passed, 0 failed | [log](all-tests/tests__phase9_2__test_archdetail.py.log) |
| tests/phase9_2/test_archdetail_browser.js | PASS | 0 | 0.365 | ARCH DETAIL BROWSER: 15 passed, 0 failed | [log](all-tests/tests__phase9_2__test_archdetail_browser.js.log) |
| tests/phase9_2/test_backend_contract.py | FAIL | 1 | 0.366 | توقّف/لا ملخص | [log](all-tests/tests__phase9_2__test_backend_contract.py.log) |
| tests/phase9_2/test_black_viewport.py | PASS | 0 | 0.115 | BLACK VIEWPORT REGRESSION: 87 passed, 0 failed | [log](all-tests/tests__phase9_2__test_black_viewport.py.log) |
| tests/phase9_2/test_generation_budget.py | PASS | 0 | 0.115 | GENERATION BUDGET: 74 passed, 0 failed | [log](all-tests/tests__phase9_2__test_generation_budget.py.log) |
| tests/phase9_2/test_live_render.py | PASS | 0 | 0.165 | LIVE RENDER RECOVERY: 75 passed, 0 failed | [log](all-tests/tests__phase9_2__test_live_render.py.log) |
| tests/phase9_2/test_parity.js | PASS | 0 | 0.469 | AD PARITY SUITE: 7 passed, 0 failed | [log](all-tests/tests__phase9_2__test_parity.js.log) |
| tests/remediation/test_accessibility.js | NOT_VERIFIED | 2 | 0.315 | توقّف/لا ملخص | [log](all-tests/tests__remediation__test_accessibility.js.log) |
| tests/remediation/test_api_wiring.py | PASS | 0 | 0.165 | API WIRING: 62 passed, 0 failed | [log](all-tests/tests__remediation__test_api_wiring.py.log) |
| tests/remediation/test_apply_render_browser.js | NOT_VERIFIED | 1 | 0.315 | توقّف/لا ملخص | [log](all-tests/tests__remediation__test_apply_render_browser.js.log) |
| tests/remediation/test_build_metadata.py | PASS | 0 | 0.115 | BUILD METADATA: 93 passed, 0 failed | [log](all-tests/tests__remediation__test_build_metadata.py.log) |
| tests/remediation/test_bundle_report.py | FAIL | 1 | 0.566 | توقّف/لا ملخص | [log](all-tests/tests__remediation__test_bundle_report.py.log) |
| tests/remediation/test_ci_gate.py | PASS | 0 | 0.315 | CI GATE: 52 passed, 0 failed | [log](all-tests/tests__remediation__test_ci_gate.py.log) |
| tests/remediation/test_concurrency.js | PASS | 0 | 0.315 | CONCURRENCY AND DOUBLE-ACTION SAFETY: 61 passed, 0 failed | [log](all-tests/tests__remediation__test_concurrency.js.log) |
| tests/remediation/test_csp.js | PASS | 0 | 0.317 | CSP: 125 passed, 0 failed | [log](all-tests/tests__remediation__test_csp.js.log) |
| tests/remediation/test_csp_style_architecture.js | NOT_VERIFIED | 1 | 0.617 | CSP STYLE ARCHITECTURE: 20 passed, 0 failed  (الطبقة الحيّة: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED) | [log](all-tests/tests__remediation__test_csp_style_architecture.js.log) |
| tests/remediation/test_dependency_lock.py | PASS | 0 | 0.115 | DEPENDENCY LOCK CONTRACT: 108 passed, 0 failed | [log](all-tests/tests__remediation__test_dependency_lock.py.log) |
| tests/remediation/test_engineering_authority.py | PASS | 0 | 0.115 | ENGINEERING AUTHORITY: 135 passed, 0 failed | [log](all-tests/tests__remediation__test_engineering_authority.py.log) |
| tests/remediation/test_event_loop.py | PASS | 0 | 17.172 | EVENT LOOP AND RATE-LIMIT DECISION: 57 passed, 0 failed | [log](all-tests/tests__remediation__test_event_loop.py.log) |
| tests/remediation/test_generation_cancel.py | FAIL | 1 | 1.779 | توقّف/لا ملخص | [log](all-tests/tests__remediation__test_generation_cancel.py.log) |
| tests/remediation/test_logging.py | PASS | 0 | 0.166 | LOGGING: 82 passed, 0 failed | [log](all-tests/tests__remediation__test_logging.py.log) |
| tests/remediation/test_model_apply.js | PASS | 0 | 0.516 | MODEL APPLY: 85 passed, 0 failed | [log](all-tests/tests__remediation__test_model_apply.js.log) |
| tests/remediation/test_module_graph.js | PASS | 0 | 1.469 | F-09 MODULE GRAPH: 32 passed, 0 failed | [log](all-tests/tests__remediation__test_module_graph.js.log) |
| tests/remediation/test_multi_provider.py | PASS | 0 | 0.065 | MULTI-PROVIDER: 111 passed, 0 failed | [log](all-tests/tests__remediation__test_multi_provider.py.log) |
| tests/remediation/test_p0_hardening.py | PASS | 0 | 0.716 | P0 HARDENING: 57 passed, 0 failed | [log](all-tests/tests__remediation__test_p0_hardening.py.log) |
| tests/remediation/test_panel_entry.js | NOT_VERIFIED | 0 | 0.315 | PANEL ENTRY: 13 passed, 0 failed  (الطبقة الحيّة: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED) | [log](all-tests/tests__remediation__test_panel_entry.js.log) |
| tests/remediation/test_performance.js | FAIL | 1 | 0.368 | PERFORMANCE CONTRACT: 121 passed, 2 failed | [log](all-tests/tests__remediation__test_performance.js.log) |
| tests/remediation/test_persistence.js | PASS | 0 | 0.315 | F-15 LOCAL PERSISTENCE: 105 passed, 0 failed | [log](all-tests/tests__remediation__test_persistence.js.log) |
| tests/remediation/test_plan_chunking.py | PASS | 0 | 0.168 | PLAN CHUNKING: 72 passed, 0 failed | [log](all-tests/tests__remediation__test_plan_chunking.py.log) |
| tests/remediation/test_plate_extent.py | PASS | 0 | 0.167 | PLATE EXTENT: 159 passed, 0 failed | [log](all-tests/tests__remediation__test_plate_extent.py.log) |
| tests/remediation/test_privacy_boundary.py | PASS | 0 | 0.215 | PRIVACY BOUNDARY: 63 passed, 0 failed | [log](all-tests/tests__remediation__test_privacy_boundary.py.log) |
| tests/remediation/test_production_error_ui.js | PASS | 0 | 0.315 | PRODUCTION ERROR UI: 262 passed, 0 failed | [log](all-tests/tests__remediation__test_production_error_ui.js.log) |
| tests/remediation/test_provider_accounting.py | PASS | 0 | 0.065 | PROVIDER ACCOUNTING: 51 passed, 0 failed | [log](all-tests/tests__remediation__test_provider_accounting.py.log) |
| tests/remediation/test_provider_capability.py | PASS | 0 | 0.115 | PROVIDER CAPABILITY / ROUTING / RESPONSE SEMANTICS: 92 passed, 0 failed | [log](all-tests/tests__remediation__test_provider_capability.py.log) |
| tests/remediation/test_provider_integration.py | PASS | 0 | 0.215 | PROVIDER INTEGRATION: 56 passed, 0 failed | [log](all-tests/tests__remediation__test_provider_integration.py.log) |
| tests/remediation/test_provider_reject.py | PASS | 0 | 0.065 | PROVIDER REJECTION DIAGNOSTICS: 57 passed, 0 failed | [log](all-tests/tests__remediation__test_provider_reject.py.log) |
| tests/remediation/test_rate_limit.py | PASS | 0 | 0.215 | RATE LIMIT REGRESSION: 120 passed, 0 failed | [log](all-tests/tests__remediation__test_rate_limit.py.log) |
| tests/remediation/test_scene_benchmark.js | NOT_VERIFIED | 1 | 0.315 | توقّف/لا ملخص | [log](all-tests/tests__remediation__test_scene_benchmark.js.log) |
| tests/remediation/test_scene_limits.js | PASS | 0 | 6.735 | SCENE LIMITS: 171 passed, 0 failed | [log](all-tests/tests__remediation__test_scene_limits.js.log) |
| tests/remediation/test_upload_security.py | PASS | 0 | 4.437 | TEST SUMMARY: 200 passed, 0 failed | [log](all-tests/tests__remediation__test_upload_security.py.log) |
| tests/remediation/test_webgl_diagnostics.js | FAIL | 1 | 120.527 | WEBGL DIAGNOSTICS: 123 passed, 5 failed | [log](all-tests/tests__remediation__test_webgl_diagnostics.js.log) |
| tests/security/test_security.py | PASS | 0 | 0.617 | BACKEND/CONFIG SECURITY: 377 passed, 0 failed | [log](all-tests/tests__security__test_security.py.log) |

## مراجعة أسباب الفشل — لا تغيّر السجلات الأصلية

| المحاولة | التشخيص | دليل المتابعة |
|---|---|---|
| viewport_pixels | Chromium غير موجود، وليست نتيجة بكسلات للمنتج | سجل الملف |
| phase1/gate وprov | اختارا مشغّل Node بينما يحتاجان `document` و`__box` من صفحة المتصفح؛ فشل المشغّل لا يثبت خللاً في المنتج | `tests/phase3/lib/build_browser_page.js:339` |
| backend_contract | Starlette 0.36.3 يمرر app إلى httpx 0.28.1؛ تجربة httpx 0.27.2 كشفت بعدها اعتماد الاختبار على API._hits المحذوف | [التجربة](test-backend-httpx027-experiment.log) |
| bundle_report | يقطع V.reason عند كونها None بعد وجود vendor | السجل الكامل |
| generation_cancel | psutil.NoSuchProcess عند فحص PID؛ صلاحية رؤية العملية عبر البيئة غير متحققة | السجل الكامل |
| performance | يتوقع وصفاً بيئياً محدداً (vendor فارغ/لا شبكة) وvacuity proof؛ لا يثبت بطء التوليد | السجل الكامل |
| webgl_diagnostics | البناء استبدل tokens التي يفحصها الاختبار؛ بعد إعادة ملف build-info إلى نص HEAD ومشغّل الاختبار الصحيح: 128 passed, 0 failed؛ فحص Chromium ما زال NOT VERIFIED | [الإعادة الصحيحة](test-webgl-clean-source-correct-harness.log) |

شغّلنا أيضاً مشغّل المرحلة 9.2 الرسمي وremediation مع `--browser`. الأول توقف عند عدم توافق TestClient؛ الثاني أخفق. تشغيل سلسلة 9.1 الإضافية توقف عند بوابة أمن/بيئة؛ لا يُعد ما بعدها منفذاً. لا يُستنتج مرور السلسلة من مرور ملفاتها الفردية.

الاختبارات الجديدة غير المتتبعة الموجودة في checkout لم تُخلط باختبارات SHA المطلوب؛ جُردت منفصلة. وليست النتائج أعلاه وصفاً لاختبارات main الأحدث.

الفحوص الفارغة المثبتة: `tests/phase1/test_gate.js:27` شرط ينتهي دائماً بـ true، و`:29` true صريح؛ `tests/phase2/test_nav.js:60` true صريح. بعض checks(true) الأخرى داخل try أو شرط تعذّر هي فحوص عدم رمي/إعلان تعذّر وليست كلها فارغة.
