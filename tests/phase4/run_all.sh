#!/usr/bin/env sh
# ==============================================================================
# تشغيل تحقّق المرحلة 4 كاملاً من نسخة نظيفة من المستودع.
# لا يعتمد على أي ملفّ موجود مسبقاً في /tmp — كل مصدر تنفيذي داخل المستودع،
# و/tmp تُستعمل لمخرجات التشغيل المؤقّتة فقط. يعمل من أي مجلّد عمل.
#
#   sh tests/phase4/run_all.sh            # كل شيء عدا المتصفّح الحقيقي
#   sh tests/phase4/run_all.sh --browser  # مع Chromium عبر Playwright
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
import importlib
mods = ["acs_arch", "acs_struct", "acs_mep", "acs_fls", "acs_coord", "acs_visual",
        "acs_runtime", "acs_relations", "acs_distance", "acs_egress", "acs_navigation",
        "acs_occupancy", "acs_revision", "acs_rules", "acs_ingest", "acs_compiler",
        "acs_understand", "acs_project", "acs_programs", "acs_validate", "acs_layout"]
for m in mods:
    importlib.import_module(m)
print("imports: OK (%d modules)" % len(mods))
PY
guard $?

step "1 · the browser runtime layer is regenerated from the canonical source"
python3 "$ROOT/tools/build_runtime_browser.py"; guard $?

step "2 · regenerate Phase 4 fixtures from the vendored Phase 3 fixtures"
node "$ROOT/tests/phase3/gen_visual_fixtures.js"
node "$HERE/fixture_generator.js"; guard $?

step "3 · runtime scene compilation and contract"
node "$ROOT/tests/lib/run.js" "$HERE/test_runtime.js"; guard $?

step "4 · navigation modes"
node "$ROOT/tests/lib/run.js" "$HERE/test_navigation.js"; guard $?

step "5 · walkability, capsule and collision"
node "$ROOT/tests/lib/run.js" "$HERE/test_collision.js"; guard $?

step "6 · portals, connectivity and vertical connections"
node "$ROOT/tests/lib/run.js" "$HERE/test_portals.js"; guard $?

step "7 · selection and inspection"
node "$ROOT/tests/lib/run.js" "$HERE/test_selection.js"; guard $?

step "8 · visibility"
node "$ROOT/tests/lib/run.js" "$HERE/test_visibility.js"; guard $?

step "9 · measurement"
node "$ROOT/tests/lib/run.js" "$HERE/test_measurement.js"; guard $?

step "10 · immutability and model write protection"
node "$ROOT/tests/lib/run.js" "$HERE/test_immutability.js"; guard $?

step "11 · adversarial inputs"
node "$ROOT/tests/lib/run.js" "$HERE/test_adversarial.js"; guard $?

step "12 · model regression — 3D geometry and model hashes unchanged"
node "$HERE/test_model_regression.js"; guard $?

step "12b · Python <-> JavaScript parity"
node "$HERE/test_parity.js"; guard $?

step "13 · security and configuration"
python3 "$ROOT/tests/security/test_security.py"; guard $?

step "14 · Phase 1/2/3 regression (no phase may be broken by Phase 4)"
sh "$ROOT/tests/phase3/run_all.sh" "$1"; guard $?

step "15 · deterministic runtime benchmarks (no FPS, no GPU, no pixel claim)"
node "$ROOT/tests/lib/run.js" "$HERE/benchmark_runtime.js"
python3 "$HERE/benchmark_runtime.py"

if [ "$1" = "--browser" ]; then
  step "16 · real Chromium (Playwright)"
  node "$HERE/test_browser_parity.js"; guard $?
else
  printf '\n=== 16 · real Chromium ===\nSKIPPED (pass --browser to run). '
  printf 'Without it: NOT VERIFIED — CHROMIUM ENVIRONMENT UNAVAILABLE\n'
fi

printf '\n==============================================\n'
if [ "$FAIL" -eq 0 ]; then
  echo "PHASE 4 VERIFICATION: all executed suites passed"
else
  echo "PHASE 4 VERIFICATION: FAILURES PRESENT"
  exit 1
fi
