#!/usr/bin/env bash
# =============================================================================
# tools/ci_run.sh — مُشغِّل مجموعات الاختبار في CI، بحالة خروج **يُعتمد عليها**.
#
#     bash tools/ci_run.sh --log logs/x.log --runner "python3" a.py b.py
#     bash tools/ci_run.sh --log logs/x.log --runner "node tests/lib/run.js" a.js
#
# لماذا يوجد هذا الملفّ
# ---------------------
# كان CI يشغّل المجموعات هكذا:
#
#     set -o pipefail
#     for t in a b c ; do
#       node "$t" 2>&1 | tee -a logs/x.log
#     done
#
# وحالة خروج حلقة `for` في الصَّدَفة هي حالة **آخر تكرار وحده**. فإن فشل `a`
# ونجح `c`، خرجت الحلقة بصفر ومرّت الوظيفة خضراء. أُعيد إنتاج ذلك حرفياً:
#
#     for t in a b c; do if [ "$t" = a ]; then false; else true; fi; done
#     echo $?            →  0
#
# أي أن كل اختبار في الحلقة ما عدا الأخير كان بلا بوّابة. `set -o pipefail`
# لا يعالج هذا: هو يصحّح حالة **الأنبوب** داخل التكرار الواحد، لا حالة الحلقة.
# و`set -e` وحده لا يكفي أيضاً حين يكون الأمر داخل أنبوب `| tee`.
#
# العقد هنا صريح: **تفشل هذه الأداة إن فشل أيّ عنصر، لا آخر عنصر.**
# ويُطبع في النهاية جردٌ بما نجح وما فشل، فلا يُقرأ السجلّ بحثاً عن ✗ ضائعة.
# =============================================================================
set -u

LOG=""
RUNNER=""
LABEL="suite"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --log)    LOG="$2";    shift 2 ;;
    --runner) RUNNER="$2"; shift 2 ;;
    --label)  LABEL="$2";  shift 2 ;;
    --)       shift; break ;;
    *)        break ;;
  esac
done

if [ -z "$RUNNER" ]; then
  echo "ci_run: --runner is required" >&2
  exit 64
fi
if [ "$#" -eq 0 ]; then
  echo "ci_run: no targets given — refusing to report success on an empty run" >&2
  exit 64
fi

if [ -n "$LOG" ]; then
  mkdir -p "$(dirname "$LOG")"
  : >> "$LOG"
fi

emit() {
  if [ -n "$LOG" ]; then printf '%s\n' "$1" | tee -a "$LOG"; else printf '%s\n' "$1"; fi
}

failed_list=""
passed=0
failed=0

for target in "$@"; do
  emit "=== $target ==="
  # الحالة تُلتقط من الأمر نفسه لا من الأنبوب: PIPESTATUS[0] هو الاختبار،
  # و[1] هو tee. الاعتماد على $? هنا كان سيقيس نجاح tee لا نجاح الاختبار.
  if [ -n "$LOG" ]; then
    # shellcheck disable=SC2086
    $RUNNER "$target" 2>&1 | tee -a "$LOG"
    rc=${PIPESTATUS[0]}
  else
    # shellcheck disable=SC2086
    $RUNNER "$target" 2>&1
    rc=$?
  fi
  if [ "$rc" -eq 0 ]; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
    failed_list="$failed_list$target (exit $rc)
"
  fi
done

emit "──────────────────────────────────────────────────────────────"
emit "ci_run · $LABEL: $passed passed, $failed failed, $(($passed + $failed)) total"
if [ "$failed" -ne 0 ]; then
  emit "FAILED TARGETS:"
  emit "$failed_list"
  emit "::error::$failed target(s) in '$LABEL' failed — this job cannot pass"
  exit 1
fi
emit "ci_run · $LABEL: every target passed"
exit 0
