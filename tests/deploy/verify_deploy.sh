#!/usr/bin/env sh
# ==============================================================================
# verify_deploy.sh — تحقّق النشر الحتمي.
#
#   sh tests/deploy/verify_deploy.sh
#
# لا يفترض أن ملفّاً منشور لمجرّد وجوده في المستودع. يحسب إغلاق استيراد الخادوم
# من مدخله الحقيقي ويقارنه بما ينسخه Dockerfile، ويتحقّق أن كل كتلة متصفّح
# مولَّدة داخل ما ينشره Netlify (القشرة + وحدات public/app/ بعد F-09)، ويمنع
# تسرّب مسار الصندوق الرملي أو أي سرّ. الخروج غير الصفري يعني أن النشر سيسقط
# شيئاً لازماً.
#
# لماذا لا `set -e` على خطوة التوليد: كانت أوّل حاقنة تسقط تُنهي السكربت كلّه،
# فتُخفي 580 توكيدة خلف عطلٍ في أداة واحدة. الآن تُسجَّل كل حاقنة على حدة،
# ويُشغَّل التحقّق دائماً، ويكون الخروج غير صفريّ إن سقط أيّ من الاثنين. لا شيء
# يُتساهَل معه — يُقاس أكثر ويُخفى أقلّ.
# ==============================================================================
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
cd "$ROOT" || exit 2

RC=0

printf '\n=== 0 · the generated browser blocks are regenerated from the specs ===\n'
# build_visual_browser.py مُعطَّل تاريخياً في هذه الشجرة ويُتجاوَز صراحةً
python3 tools/build_visual_browser.py >/dev/null 2>&1 || true
GEN_OK=0
GEN_BAD=0
for inj in build_runtime_browser build_authoring_browser build_workspace_ui \
           build_render_browser build_bim_browser; do
  if out=$(python3 "tools/$inj.py" 2>&1); then
    GEN_OK=$((GEN_OK + 1))
  else
    GEN_BAD=$((GEN_BAD + 1))
    RC=1
    printf '  ✗ tools/%s.py FAILED: %s\n' "$inj" \
      "$(printf '%s' "$out" | head -2 | tr '\n' ' ')"
  fi
done
printf 'regenerated: %d injector(s) OK, %d FAILED\n' "$GEN_OK" "$GEN_BAD"
if [ "$GEN_BAD" -ne 0 ]; then
  printf 'a generated browser block can no longer be regenerated from its spec: '
  printf 'the shipped block and its generator have drifted apart.\n'
fi

printf '\n=== 1 · deployment content verification ===\n'
python3 "$HERE/verify_deploy.py" || RC=1

exit "$RC"
