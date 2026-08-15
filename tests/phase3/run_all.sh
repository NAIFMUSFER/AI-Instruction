#!/usr/bin/env sh
# ==============================================================================
# تشغيل تحقّق المرحلة 3 كاملاً من نسخة نظيفة من المستودع.
# لا يعتمد على أي ملفّ موجود مسبقاً في /tmp — كل مصدر تنفيذي داخل المستودع،
# و/tmp تُستعمل لمخرجات التشغيل المؤقّتة فقط.
#
#   sh tests/phase3/run_all.sh            # كل شيء عدا المتصفّح الحقيقي
#   sh tests/phase3/run_all.sh --browser  # مع Chromium عبر Playwright
# ==============================================================================
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
cd "$ROOT"
FAIL=0
step() { printf '\n=== %s ===\n' "$1"; }
guard() { if [ "$1" -ne 0 ]; then FAIL=1; fi }

step "0 · Python syntax and imports"
python3 -m py_compile acs_*.py && echo "py_compile: OK"
python3 - <<'PY'
import importlib, sys
mods = ["acs_arch","acs_struct","acs_mep","acs_fls","acs_coord","acs_visual",
        "acs_relations","acs_distance","acs_egress","acs_navigation","acs_occupancy",
        "acs_revision","acs_rules","acs_ingest","acs_compiler","acs_understand",
        "acs_project","acs_programs","acs_validate","acs_layout"]
for m in mods:
    importlib.import_module(m)
print("imports: OK (%d modules)" % len(mods))
PY
guard $?

step "1 · regenerate Phase 3 fixtures from the vendored base fixtures"
node "$HERE/gen_visual_fixtures.js"; guard $?

step "2 · Phase 3 visual suite (Node)"
node "$HERE/lib/run.js" test_visual.js; guard $?

step "3 · Phase 3 adversarial suite (Node)"
node "$HERE/lib/run.js" test_visual_adversarial.js; guard $?

step "4 · Phase 3 developer API (Node, runs the block injected into index.html)"
node "$HERE/lib/run.js" test_dev_api.js; guard $?

step "5 · Python <-> JavaScript parity"
python3 "$HERE/parity/py_visual.py"
node "$HERE/lib/run.js" parity/js_visual_body.js
node "$HERE/parity/compare.js"; guard $?

step "6 · security and configuration"
python3 "$ROOT/tests/security/test_security.py"; guard $?

step "7 · deterministic scene-build benchmarks"
node "$HERE/lib/run.js" perf_visual.js
python3 "$HERE/perf_visual.py"

if [ "$1" = "--browser" ]; then
  step "8 · real Chromium (Playwright)"
  node "$HERE/lib/run_browser.js" test_visual.js; guard $?
  node "$HERE/lib/run_browser.js" test_visual_adversarial.js; guard $?
  node "$HERE/lib/run_browser.js" test_dev_api.js; guard $?
else
  printf '\n=== 8 · real Chromium ===\nSKIPPED (pass --browser to run). '
  printf 'Without it: NOT VERIFIED — CHROMIUM ENVIRONMENT UNAVAILABLE\n'
fi

printf '\n==============================================\n'
if [ "$FAIL" -eq 0 ]; then
  echo "PHASE 3 VERIFICATION: all executed suites passed"
else
  echo "PHASE 3 VERIFICATION: FAILURES PRESENT"
  exit 1
fi
