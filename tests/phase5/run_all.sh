#!/usr/bin/env sh
# ==============================================================================
# تشغيل تحقّق المرحلة 5 كاملاً من نسخة نظيفة من المستودع.
# لا يعتمد على أي ملفّ موجود مسبقاً في /tmp — كل مصدر تنفيذي داخل المستودع،
# و/tmp تُستعمل لمخرجات التشغيل المؤقّتة فقط. يعمل من أي مجلّد عمل.
#
#   sh tests/phase5/run_all.sh            # كل شيء عدا المتصفّح الحقيقي
#   sh tests/phase5/run_all.sh --browser  # مع Chromium عبر Playwright
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
        "acs_runtime", "acs_authoring", "acs_relations", "acs_distance", "acs_egress",
        "acs_navigation", "acs_occupancy", "acs_revision", "acs_rules", "acs_ingest",
        "acs_compiler", "acs_understand", "acs_project", "acs_programs", "acs_validate",
        "acs_layout"]
for m in mods:
    importlib.import_module(m)
print("imports: OK (%d modules)" % len(mods))
PY
guard $?

step "1 · regenerate the browser layers from the canonical specifications"
python3 "$ROOT/tools/build_runtime_browser.py"; guard $?
python3 "$ROOT/tools/build_authoring_browser.py"; guard $?

step "2 · regenerate fixtures from the vendored repository fixtures"
node "$ROOT/tests/phase3/gen_visual_fixtures.js"
node "$ROOT/tests/phase4/fixture_generator.js"
node "$HERE/fixture_generator.js"; guard $?

step "3 · authoring contract, command schema and determinism"
node "$ROOT/tests/lib/run.js" "$HERE/test_authoring.js"; guard $?

step "4 · every authoring command"
node "$ROOT/tests/lib/run.js" "$HERE/test_commands.js"; guard $?

step "5 · transaction lifecycle, preview, commit, batch atomicity"
node "$ROOT/tests/lib/run.js" "$HERE/test_transaction.js"; guard $?

step "6 · revisions, undo, redo, diff, save and load"
node "$ROOT/tests/lib/run.js" "$HERE/test_revision.js"; guard $?

step "7 · AI boundary and the natural-language pipeline"
node "$ROOT/tests/lib/run.js" "$HERE/test_ai_boundary.js"; guard $?

step "8 · coordination, navigation, egress, distance and non-mutation of other disciplines"
node "$ROOT/tests/lib/run.js" "$HERE/test_integration.js"; guard $?

step "9 · immutability and the Phase 4 hard gate"
node "$ROOT/tests/lib/run.js" "$HERE/test_immutability.js"; guard $?

step "10 · adversarial authoring input"
node "$ROOT/tests/lib/run.js" "$HERE/test_adversarial.js"; guard $?

step "11 · a full edit cycle (also runs in the browser with --browser)"
node "$ROOT/tests/lib/run.js" "$HERE/test_browser.js"; guard $?

step "12 · Python <-> JavaScript authoring parity"
node "$HERE/test_parity.js"; guard $?

step "13 · security and configuration"
python3 "$ROOT/tests/security/test_security.py"; guard $?

step "14 · Phase 4 regression (runtime immutability must not weaken)"
sh "$ROOT/tests/phase4/run_all.sh" "$1"; guard $?

step "15 · deterministic authoring benchmarks (no FPS, no GPU, no pixel claim)"
node "$ROOT/tests/lib/run.js" "$HERE/benchmark_authoring.js"
python3 "$HERE/benchmark_authoring.py"

if [ "$1" = "--browser" ]; then
  step "16 · real Chromium (Playwright)"
  node "$HERE/test_browser_parity.js"; guard $?
else
  printf '\n=== 16 · real Chromium ===\nSKIPPED (pass --browser to run). '
  printf 'Without it: NOT VERIFIED — CHROMIUM ENVIRONMENT UNAVAILABLE\n'
fi

printf '\n==============================================\n'
if [ "$FAIL" -eq 0 ]; then
  echo "PHASE 5 VERIFICATION: all executed suites passed"
else
  echo "PHASE 5 VERIFICATION: FAILURES PRESENT"
  exit 1
fi
