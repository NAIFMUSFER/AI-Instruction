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
set -e
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

step "F-01 · engineering authority: no silent engineering change"
python3 "$HERE/test_engineering_authority.py"; guard $?

step "F-05/F-19 · upload security"
python3 "$HERE/test_upload_security.py"; guard $?

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
