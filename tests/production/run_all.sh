#!/usr/bin/env sh
# All required parts must complete. Exit 0=PASS, 1=FAIL, 2=INCOMPLETE.
# Capture child process exits before printing logs; tee must never hide a crash.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
cd "$ROOT"
OUT="$HERE/outputs"
mkdir -p "$OUT"
STAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
rm -f "$OUT/verify_live.json" "$OUT/verify_live_browser.json" "$OUT/summary.json"
echo "ACS PRODUCTION VERIFICATION SUITE"
echo "started: $STAMP"
set +e
python3 "$HERE/verify_live.py" "$@" > "$OUT/verify_live.log" 2>&1
RC_HTTP=$?
cat "$OUT/verify_live.log"
node "$HERE/verify_live_browser.js" "$@" > "$OUT/verify_live_browser.log" 2>&1
RC_BROWSER=$?
cat "$OUT/verify_live_browser.log"
python3 "$HERE/validate_evidence.py" "$OUT" "$STAMP" "$RC_HTTP" "$RC_BROWSER" > "$OUT/summary.log" 2>&1
RC_SUMMARY=$?
cat "$OUT/summary.log"
echo "logs: $OUT"
exit "$RC_SUMMARY"
