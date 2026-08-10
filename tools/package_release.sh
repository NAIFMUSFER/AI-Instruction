#!/usr/bin/env sh
# ==============================================================================
# تغليف إصدار كامل مع بوّابة سلامة إلزامية — علاج المرحلة 9.2 الإنتاجي.
#
#   sh tools/package_release.sh <اسم-الأرشيف.zip> [--browser]
#
# الخطوات، وكل واحدة تُفشل التغليف عند أول عطل:
#   1) حارس الصفحة البنيوي على شجرة المصدر
#   2) إنشاء الأرشيف + بصمة SHA-256 جانبية
#   3) فكّ الأرشيف في مجلد نظيف
#   4) تأكيد أن public/index.html المفكوك غير فارغ وبنفس بصمة المصدر بايت-ببايت
#   5) الحارس البنيوي على النسخة المفكوكة
#   6) تحقّق النشر كاملاً من داخل النسخة المفكوكة
#   7) (--browser) فحص لوحة المتصفح الحقيقي من داخل النسخة المفكوكة
# لا أرشيف بلا بوّابة — التغليف اليدوي بلا هذا السكربت هو الثغرة التي عولجت.
# ==============================================================================
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
cd "$ROOT"

OUTZIP="${1:?usage: sh tools/package_release.sh <archive.zip> [--browser]}"
case "$OUTZIP" in
  /*) : ;;
  *) OUTZIP="$ROOT/../$OUTZIP" ;;
esac

echo "▶ 1/7 structural guard on the source tree"
python3 tools/check_index_guard.py public/index.html

echo "▶ 2/7 creating archive"
rm -f "$OUTZIP" "$OUTZIP.sha256"
zip -qr "$OUTZIP" . -x "*/__pycache__/*" -x "__pycache__/*" -x "*.pyc" \
  -x "node_modules/*" -x "*/node_modules/*"
( cd "$(dirname "$OUTZIP")" && sha256sum "$(basename "$OUTZIP")" \
    > "$(basename "$OUTZIP").sha256" )
cat "$OUTZIP.sha256"

EXTRACT=$(mktemp -d)
trap 'rm -rf "$EXTRACT"' EXIT
echo "▶ 3/7 extracting to a fresh directory: $EXTRACT"
unzip -q "$OUTZIP" -d "$EXTRACT"

echo "▶ 4/7 extracted page is non-empty and byte-identical to the source"
[ -s "$EXTRACT/public/index.html" ] || {
  echo "✗ extracted public/index.html is MISSING or EMPTY"; exit 1; }
SRC_SHA=$(sha256sum public/index.html | cut -d' ' -f1)
EXT_SHA=$(sha256sum "$EXTRACT/public/index.html" | cut -d' ' -f1)
[ "$SRC_SHA" = "$EXT_SHA" ] || {
  echo "✗ SHA-256 mismatch: source=$SRC_SHA extracted=$EXT_SHA"; exit 1; }
echo "✓ index.html sha256 $SRC_SHA ($(wc -c < public/index.html) bytes)"

echo "▶ 5/7 structural guard on the extracted copy"
( cd "$EXTRACT" && python3 tools/check_index_guard.py public/index.html )

echo "▶ 6/7 full deploy verification from the extracted copy"
( cd "$EXTRACT" && sh tests/deploy/verify_deploy.sh )

if [ "$2" = "--browser" ]; then
  echo "▶ 7/7 real-Chromium panel suite from the extracted copy"
  ( cd "$EXTRACT" && node tests/phase3/lib/run_browser.js \
      "$EXTRACT/tests/phase9_2/test_archdetail_browser.js" )
else
  echo "▶ 7/7 browser suite SKIPPED (pass --browser to include it)"
fi

echo ""
echo "✓ PACKAGE INTEGRITY GATE PASSED"
echo "  archive : $OUTZIP"
echo "  files   : $(unzip -l "$OUTZIP" | tail -1 | awk '{print $2}')"
echo "  bytes   : $(wc -c < "$OUTZIP")"
echo "  sha256  : $(cut -d' ' -f1 "$OUTZIP.sha256")"
