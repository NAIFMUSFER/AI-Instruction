#!/usr/bin/env sh
# ==============================================================================
# tests/remediation/run_all.sh — مجموعة تصحيح ثقة الإنتاج.
#
#   sh tests/remediation/run_all.sh            # كل ما يعمل بلا متصفّح
#   sh tests/remediation/run_all.sh --browser  # مع Chromium عبر Playwright
#
# الخروج غير الصفري يعني فشلاً حقيقياً. ما يحتاج بيئة خارجية يخرج بالرمز 2
# ويُعلَن NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED، ولا يُحسَب نجاحاً.
# ==============================================================================
# W0: كان هنا `set -e`. مع `cmd; guard $?` يموت السكربت عند أوّل فشل قبل أن
# يُنفَّذ `guard` إطلاقاً، فكان المُجمِّع `FAIL` وفرعُ «FAILURES PRESENT» شفرةً
# ميتةً لا تُبلَغ أبداً — أي أن السكربت كان يتوقّف بصمت بدل أن يُكمل ويُبلِّغ.
# أُعيد إنتاجه: `set -e; false; guard $?` يخرج بـ1 بلا طباعة شيء.
# الآن تُجمَع كل الأعطال وتُطبَع مرّةً واحدة، والخروج غير الصفريّ في النهاية.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
cd "$ROOT"
FAIL=0
step() { printf '\n=== %s ===\n' "$1"; }
guard() { if [ "$1" -ne 0 ]; then FAIL=1; fi }
soft() {
  rc=$1; label=$2
  if [ "$rc" -eq 2 ]; then
    echo "$label: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED (exit 2, not a failure)"
  else
    guard "$rc"
  fi
}

# W0: بوّابات التحقّق نفسها — دلالة خروج CI، ووصول المتحقّق الحيّ.
step "W0 · CI cannot false-green and the live verifier reaches the backend"
python3 "$HERE/test_ci_gate.py"; guard $?

# W1: أعطال P0 — قنبلة الانضغاط، تطبيعات السلطة، مقعد المجمّع، اسم المزوّد،
# وسقف الملاحظات. لكلٍّ شاهدٌ سالب يُعيد إدخال العطل الأصلي.
step "W1 · P0 security and correctness"
python3 "$HERE/test_p0_hardening.py"; guard $?

# W2-A/W2-D: محاسبة كتل الرد، وإسقاط المحاولة المطابقة بايتاً. القياس أوّلاً:
# تصميم W2-C ينتظر ما يقوله السجلّ الحيّ عن أنواع الكتل.
step "W2-A/W2-D · provider response accounting and the identical-retry skip"
python3 "$HERE/test_provider_accounting.py"; guard $?

# W2-B/W2-C/W2-E: القدرة المُعلَنة تحلّ محلّ اسم المزوّد، والتوجيه والتقطيع
# يُقاسان بالمحتوى المرئي المكتمل، ودلالة الرد أربع حالات لا اثنتان.
# شواهده السالبة تُعيد إنتاج الانهيار المقيس 60→35→20→11→6→4.
step "W2-B/W2-C/W2-E · provider capability, routing and response semantics"
python3 "$HERE/test_provider_capability.py"; guard $?

step "F-01 · engineering authority: no silent engineering change"
python3 "$HERE/test_engineering_authority.py"; guard $?

step "F-05/F-19 · upload security"
python3 "$HERE/test_upload_security.py"; guard $?
python3 "$HERE/test_request_body_limits.py"; guard $?
python3 "$HERE/test_image_dimensions.py"; guard $?
python3 "$HERE/test_validator_response.py"; guard $?
python3 "$HERE/test_validator_openings.py"; guard $?
python3 "$HERE/test_validator_geometry.py"; guard $?
python3 "$HERE/test_core_alignment.py"; guard $?
python3 "$HERE/test_repair_proposal.py"; guard $?
node "$ROOT/tests/lib/run.js" "$HERE/test_repair_report.js"; guard $?
python3 "$HERE/test_level_elevation.py"; guard $?
python3 "$HERE/test_compiler_arch_failure.py"; guard $?
node "$ROOT/tests/lib/run.js" "$HERE/test_level_elevation.js"; guard $?

step "F-04 · distributed rate limiting"
python3 "$HERE/test_rate_limit.py"; guard $?

step "F-06 · generation job cancellation"
python3 "$HERE/test_generation_cancel.py"; guard $?

step "F-18/F-13 · structured logging and llm telemetry"
python3 "$HERE/test_logging.py"; guard $?

step "F-12 · regulatory claim boundary and privacy"
python3 "$HERE/test_privacy_boundary.py"; guard $?

step "provenance · build metadata"
python3 "$HERE/test_build_metadata.py"; guard $?

step "F-10 · reproducible dependencies"
python3 "$HERE/test_dependency_lock.py"; guard $?

step "F-07 · floor plate extent"
python3 "$HERE/test_plate_extent.py"; guard $?

step "F-09 · shipped bundle measurement (measurement only — F-09 NOT IMPLEMENTED)"
python3 "$HERE/test_bundle_report.py"; guard $?

step "F-09 · module evaluation order (acyclic graph, backward edges, __ACS_LATE)"
node "$HERE/test_module_graph.js"; guard $?

step "F-11 · content security policy"
node "$ROOT/tests/lib/run.js" "$HERE/test_csp.js"; guard $?
# القياس الحيّ للسياسة في Chromium حقيقي (يكتب tests/remediation/outputs/csp_probe.json)
# يُشغَّل مع --browser فقط، ويُسجّل ضعف 'unsafe-inline'/'unsafe-eval' سطرَ
# KNOWN-WEAKNESS بدل أن يمرّره صامتاً.

step "F-08 · webgl runtime diagnostics (node scope)"
node "$ROOT/tests/lib/run.js" "$HERE/test_webgl_diagnostics.js"; guard $?

step "concurrency and production error ui (node scope)"
node "$ROOT/tests/lib/run.js" "$HERE/test_concurrency.js"; guard $?
node "$ROOT/tests/lib/run.js" "$HERE/test_production_error_ui.js"; guard $?

step "F-15 · local persistence safety (node scope)"
node "$ROOT/tests/lib/run.js" "$HERE/test_persistence.js"; guard $?

# F-31…F-34: مسار نداء المزوّد — بديل SDK بتوقيع v0.40.0 الحقيقي، فيكشف عدم
# تطابق التوقيع الذي لا يمكن لبديلٍ يقبل **kwargs أن يكشفه.
step "F-31…F-34 · provider integration (local TypeError is never an upstream fault)"
python3 "$HERE/test_provider_integration.py"; guard $?

# KI-24/F-35…F-40: المزوّد المزيّف هنا **يفرض سقف الرموز** ويقصّ ما تجاوزه،
# فيكشف عطل الميزانية الذي لا يكشفه بديلٌ يعيد رداً صالحاً دائماً.
step "KI-24 · F-35…F-40 · bounded plan chunking (no stage reaches its ceiling)"
python3 "$HERE/test_plan_chunking.py"; guard $?

# KI-25/F-41…F-45: يُشغَّل compile() المشحون على بديل هندسة معلَن، فيُقاس ما
# يُبنى فعلاً لا ما يُدَّعى. البكسلات لها الملفّ التالي تحت --browser.
step "KI-25 · F-41…F-45 · post-200 model apply (a 200 that does not display is a failure)"
node "$ROOT/tests/lib/run.js" "$HERE/test_model_apply.js"; guard $?

# KI-14/F-46/F-47: حلقة asyncio حقيقيّة + مدقّقات مشحونة + redis-server حقيقيّ.
step "KI-14 · F-46/F-47 · event-loop isolation and the rate-limit decision"
python3 "$HERE/test_event_loop.py"; guard $?

# هندسة المشهد المحدودة (KI-25 pass): سقوف معلنة وحلقات مقيّدة وأخطاء مرئية.
step "scene complexity · declared limits, bounded loops, visible compiler failures"
node "$ROOT/tests/lib/run.js" "$HERE/test_scene_limits.js"; guard $?

# F-50: رفض المزوّد 400 لا يُشخَّص من `upstream_class=BadRequestError` وحدها.
step "F-50 · provider 400 diagnostics and the single model-output ceiling"
python3 "$HERE/test_provider_reject.py"; guard $?

# هجرة المزوّد: البديل هنا يسجّل **إلى أين** كان النداء ذاهباً — وهو الفحص
# الذي يمنع وصول مفتاح deepseek إلى api.anthropic.com، ولا يكشفه بديلٌ لا
# يحفظ ما بُني به العميل.
step "multi-provider · deepseek primary, one bounded anthropic fallback, billing"
python3 "$HERE/test_multi_provider.py"; guard $?

step "api wiring · every job target and keyword binds to its real signature"
python3 "$HERE/test_api_wiring.py"; guard $?

if [ "$1" = "--browser" ]; then
  step "F-11 · content security policy measured in real Chromium"
  node "$HERE/csp_browser_probe.js"; soft $? "csp browser probe"
  step "accessibility · WCAG 2.1 AA baseline in real Chromium"
  node "$HERE/test_accessibility.js"; soft $? "accessibility"
  step "F-14 · WebGL performance in real Chromium"
  node "$HERE/test_performance.js"; soft $? "performance"
  # F-27: لا يحتاج three مُعبَّأً — يخدم كعباً أدنى ويعلن ذلك في مخرجه.
  step "F-27 · panel entry points reachable from the shipped UI (real Chromium)"
  node "$HERE/test_panel_entry.js"; guard $?
  # KI-13/F-30: يقيس السياسة الإنتاجية نفسها من netlify.toml كرأس استجابة حقيقيّ.
  step "KI-13 · F-30 · CSP style architecture (real Chromium, production policy)"
  node "$HERE/test_csp_style_architecture.js"; guard $?
  # KI-25: WebGL2 حقيقيّ وreadPixels حقيقيّ على هندسة compile() المشحونة.
  # three.js نفسه غير مُعبَّأ هنا، والملفّ يعلن ذلك بنفسه في مخرجه.
  step "KI-25 · F-41…F-45 · the applied model is actually drawn (real Chromium, real WebGL2)"
  node "$HERE/test_apply_render_browser.js"; guard $?
  # ميزانيات الأداء المعلنة على سطح المكتب والجوال واللوحي.
  step "performance budgets · SMALL…ADVERSARIAL on desktop, mobile and tablet"
  node "$HERE/test_scene_benchmark.js"; guard $?
else
  printf '\n=== accessibility and performance ===\nSKIPPED (pass --browser). '
  printf 'Without it: NOT VERIFIED — CHROMIUM ENVIRONMENT UNAVAILABLE\n'
fi

printf '\n==============================================\n'
if [ "$FAIL" -eq 0 ]; then
  echo "REMEDIATION VERIFICATION: all executed suites passed"
else
  echo "REMEDIATION VERIFICATION: FAILURES PRESENT"
  exit 1
fi
