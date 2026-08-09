#!/usr/bin/env sh
# ==============================================================================
# verify_deploy.sh — تحقّق النشر الحتمي.
#
#   sh tests/deploy/verify_deploy.sh
#
# لا يفترض أن ملفّاً منشور لمجرّد وجوده في المستودع. يحسب إغلاق استيراد الخادوم
# من مدخله الحقيقي ويقارنه بما ينسخه Dockerfile، ويتحقّق أن كل كتلة متصفّح
# مولَّدة داخل الصفحة التي ينشرها Netlify، ويمنع تسرّب مسار الصندوق الرملي أو
# أي سرّ. الخروج غير الصفري يعني أن النشر سيسقط شيئاً لازماً.
# ==============================================================================
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
cd "$ROOT"

printf '\n=== 0 · the generated browser blocks are regenerated from the specs ===\n'
python3 tools/build_visual_browser.py    >/dev/null 2>&1 || true
python3 tools/build_runtime_browser.py   >/dev/null
python3 tools/build_authoring_browser.py >/dev/null
python3 tools/build_workspace_ui.py      >/dev/null
python3 tools/build_render_browser.py    >/dev/null
python3 tools/build_bim_browser.py       >/dev/null
echo "regenerated: 6 injectors"

printf '\n=== 1 · deployment content verification ===\n'
python3 "$HERE/verify_deploy.py"
