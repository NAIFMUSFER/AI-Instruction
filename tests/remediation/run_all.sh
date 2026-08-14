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

step "F-11 · content security policy"
node "$ROOT/tests/lib/run.js" "$HERE/test_csp.js"; guard $?

step "F-08 · webgl runtime diagnostics (node scope)"
node "$ROOT/tests/lib/run.js" "$HERE/test_webgl_diagnostics.js"; guard $?

step "concurrency and production error ui (node scope)"
node "$ROOT/tests/lib/run.js" "$HERE/test_concurrency.js"; guard $?
node "$ROOT/tests/lib/run.js" "$HERE/test_production_error_ui.js"; guard $?

if [ "$1" = "--browser" ]; then
  step "accessibility · WCAG 2.1 AA baseline in real Chromium"
  node "$HERE/test_accessibility.js"; soft $? "accessibility"
  step "F-14 · WebGL performance in real Chromium"
  node "$HERE/test_performance.js"; soft $? "performance"
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
