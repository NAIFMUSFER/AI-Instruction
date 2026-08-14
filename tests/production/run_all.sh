#!/usr/bin/env sh
# ==============================================================================
# tests/production/run_all.sh — تشغيل التحقّق الإنتاجي الحيّ كاملاً.
#
#   sh tests/production/run_all.sh
#   sh tests/production/run_all.sh --frontend https://… --backend https://…
#   sh tests/production/run_all.sh --expect-sha 6bc8a88b1871334c1d371d4e5e5da9ad540109ac
#   ACS_VERIFY_FRONTEND=… ACS_VERIFY_BACKEND=… sh tests/production/run_all.sh
#
# يتبع أعراف tests/phase9_2/run_all.sh حرفياً: set -e، وstep()، وguard()،
# وتسامح مع الخروج 2 بوصفه NOT VERIFIED لا فشلاً.
#
# اصطلاح الخروج المشترك بين المِرقابين:
#   0  لا فشل مرصود      1  فشل مرصود      2  لم يُرصد شيء (NOT VERIFIED)
#
# رمز خروج هذا السكربت:
#   0  لا فشل في أي مِرقاب
#   1  فشل مرصود في مِرقاب واحد على الأقل
#   2  لم يُرصد شيء في أي مِرقاب — التحقّق كلّه NOT VERIFIED
#
# كل السجلّات تحت tests/production/outputs/.
# ==============================================================================
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
cd "$ROOT"

OUT="$HERE/outputs"
mkdir -p "$OUT"

FAIL=0
OBSERVED=0
STAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

step() { printf '\n=== %s ===\n' "$1"; }
guard() { if [ "$1" -ne 0 ]; then FAIL=1; fi }

# guard_nv <rc> <label> — يقبل 2 بوصفه NOT VERIFIED لا فشلاً، ويعُدّ ما رُصد.
guard_nv() {
  rc=$1
  label=$2
  if [ "$rc" -eq 2 ]; then
    echo "$label: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED (exit 2, not a test failure)"
  elif [ "$rc" -eq 0 ]; then
    OBSERVED=1
  else
    OBSERVED=1
    guard "$rc"
  fi
}

echo "ACS PRODUCTION VERIFICATION SUITE"
echo "  repository : $ROOT"
echo "  started    : $STAMP"
echo "  outputs    : $OUT"
echo "  arguments  : $*"

step "0 · the deployment targets the repository actually declares"
python3 - "$ROOT" <<'PY' 2>&1 | tee "$OUT/targets.log"
import re, sys, os
root = sys.argv[1]
def read(rel):
    try:
        with open(os.path.join(root, rel), encoding='utf-8') as fh:
            return fh.read()
    except Exception:
        return ''
def find(pattern, text):
    m = re.search(pattern, text)
    return m.group(1) if m else '<absent>'
print('netlify.toml           publish            = %r'
      % find(r'publish\s*=\s*"([^"]+)"', read('netlify.toml')))
# connect-src يُقرأ من قيمة الترويسة نفسها لا من نصّ الملفّ كله: التعليقات
# العربية أعلاه تذكر الاسم، والمطابقة الساذجة تلتقط التعليق بدل السياسة.
_csp = find(r'Content-Security-Policy\s*=\s*"([^"]+)"', read('netlify.toml'))
import re as _re
_m = _re.search(r'connect-src([^;]*)', _csp)
print('netlify.toml           connect-src        = %r'
      % (_m.group(1).strip() if _m else '<absent>'))
print('render.yaml            ACS_ALLOWED_ORIGINS= %r'
      % find(r'ACS_ALLOWED_ORIGINS[\s\S]{0,120}?value:\s*"([^"]+)"',
             read('render.yaml')))
print('acs_understand_api.py  _DEFAULT_ORIGIN    = %r'
      % find(r'_DEFAULT_ORIGIN\s*=\s*"([^"]+)"', read('acs_understand_api.py')))
print('public/index.html      CONFIGURED_BASE    = %r'
      % find(r'CONFIGURED_BASE\s*=\s*"([^"]*)"', read('public/index.html')))
print('render.yaml            healthCheckPath    = %r'
      % find(r'healthCheckPath:\s*(\S+)', read('render.yaml')))
print('')
print('NOTE: the block above is STATIC inspection of the repository. It states '
      'which deployment this suite is aimed at. It is never a runtime PASS.')
PY
guard $?

step "1 · HTTP layer — groups A (HTTP), B (frontend assets), G (provenance)"
set +e
rm -f "$OUT/verify_live.json"
python3 "$HERE/verify_live.py" "$@" 2>&1 | tee "$OUT/verify_live.log"
# POSIX sh has no PIPESTATUS: the real exit code is read back from the JSON
# summary the verifier always writes. A missing summary means "nothing observed".
RC_HTTP=$(python3 - "$OUT/verify_live.json" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1], encoding='utf-8'))['exit_code'])
except Exception:
    print(2)
PY
)
set -e
echo "verify_live.py exit code: $RC_HTTP"
guard_nv "$RC_HTTP" "HTTP layer"

step "2 · real Chromium — groups C (boot), D (workflow), E (responsive), F (Arabic), G (build info)"
set +e
rm -f "$OUT/verify_live_browser.json"
node "$HERE/verify_live_browser.js" "$@" 2>&1 | tee "$OUT/verify_live_browser.log"
RC_BROWSER=$(python3 - "$OUT/verify_live_browser.json" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1], encoding='utf-8'))['exit_code'])
except Exception:
    print(2)
PY
)
set -e
echo "verify_live_browser.js exit code: $RC_BROWSER"
guard_nv "$RC_BROWSER" "browser layer"

step "3 · combined machine-readable summary"
python3 - "$OUT" "$STAMP" <<'PY' 2>&1 | tee "$OUT/summary.log"
import json, os, sys
out, stamp = sys.argv[1], sys.argv[2]
combined = {"schema": "acs-production-verification-suite/1.0.0",
            "started_at": stamp, "parts": {}, "counts":
            {"pass": 0, "fail": 0, "not_verified": 0, "total": 0}}
for name in ("verify_live.json", "verify_live_browser.json"):
    path = os.path.join(out, name)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        combined["parts"][name] = {"error": str(exc)}
        continue
    combined["parts"][name] = {"verdict": data.get("verdict"),
                               "exit_code": data.get("exit_code"),
                               "counts": data.get("counts")}
    for k in ("pass", "fail", "not_verified", "total"):
        combined["counts"][k] += (data.get("counts") or {}).get(k, 0)
c = combined["counts"]
combined["verdict"] = ("FAIL" if c["fail"] else
                       ("NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED"
                        if c["pass"] == 0 else "PASS"))
combined["exit_code"] = 1 if c["fail"] else (2 if c["pass"] == 0 else 0)
with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as fh:
    fh.write(json.dumps(combined, ensure_ascii=False, indent=2) + "\n")
print("TOTAL: %d PASS · %d FAIL · %d NOT VERIFIED (of %d checks)"
      % (c["pass"], c["fail"], c["not_verified"], c["total"]))
print("combined verdict: %s" % combined["verdict"])
PY
guard $?

printf '\n==============================================\n'
if [ "$FAIL" -ne 0 ]; then
  echo "PRODUCTION VERIFICATION: FAILURES PRESENT (observed wrong behaviour)"
  echo "logs: $OUT"
  exit 1
fi
if [ "$OBSERVED" -eq 0 ]; then
  echo "PRODUCTION VERIFICATION: NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED"
  echo "  nothing was observed on either target; no check is claimed as passing."
  echo "  re-run from a networked machine:"
  echo "    sh tests/production/run_all.sh --expect-sha \$(git rev-parse HEAD)"
  echo "logs: $OUT"
  exit 2
fi
echo "PRODUCTION VERIFICATION: no observed failure"
echo "logs: $OUT"
exit 0
