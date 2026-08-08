#!/usr/bin/env bash
# =============================================================================
# vendor.sh — يُنزّل مكتبات العرض إلى public/vendor لاستضافة محلية كاملة (بلا CDN).
# شغّله من جذر المستودع في بيئة لديها وصول للشبكة (جهاز المطوّر أو CI):
#     bash tools/vendor.sh
# ثم في public/index.html: عطّل خريطة الاستيراد الخارجية وفعّل الكتلة «المحلية».
#
# النُّسخ مثبّتة لتطابق ما يتوقّعه المشروع — لا تُحدّثها دون التحقّق من التوافق.
#   three            0.160.0   (three.module.js + الإضافات الستّ المستخدَمة فعلاً)
#   es-module-shims  1.8.2
#   pdf.js           4.0.379   (اختياري — لقراءة نص الـPDF محلياً)
# =============================================================================
set -euo pipefail
THREE=0.160.0
SHIMS=1.8.2
PDFJS=4.0.379
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VEN="$ROOT/public/vendor"
DST="$VEN/three@$THREE"
mkdir -p "$DST/build" "$DST/examples/jsm" "$VEN/es-module-shims@$SHIMS" "$VEN/pdfjs@$PDFJS"

base="https://unpkg.com/three@$THREE"
# النواة
curl -fsSL "$base/build/three.module.js" -o "$DST/build/three.module.js"
# الإضافات الستّ المستوردة في index.html (وتوابعها الداخلية تُحلّ عبر خريطة الاستيراد)
addons=(
  controls/OrbitControls.js
  webxr/VRButton.js
  webxr/ARButton.js
  exporters/GLTFExporter.js
  objects/Sky.js
  environments/RoomEnvironment.js
)
for a in "${addons[@]}"; do
  mkdir -p "$DST/examples/jsm/$(dirname "$a")"
  curl -fsSL "$base/examples/jsm/$a" -o "$DST/examples/jsm/$a"
done
# ملاحظة: بعض الإضافات تستورد ملفات jsm أخرى (utils, libs). إن ظهر خطأ استيراد
# في الكونسول، أضِف المسار الناقص إلى القائمة أعلاه، أو انسخ examples/jsm كاملاً:
#   npm pack three@$THREE && tar -xzf three-$THREE.tgz && \
#   cp -r package/examples/jsm/* "$DST/examples/jsm/"

# es-module-shims
curl -fsSL "https://cdn.jsdelivr.net/npm/es-module-shims@$SHIMS/dist/es-module-shims.js" \
  -o "$VEN/es-module-shims@$SHIMS/es-module-shims.js"

# pdf.js (اختياري)
curl -fsSL "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/$PDFJS/pdf.min.mjs" \
  -o "$VEN/pdfjs@$PDFJS/pdf.min.mjs" || true
curl -fsSL "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/$PDFJS/pdf.worker.min.mjs" \
  -o "$VEN/pdfjs@$PDFJS/pdf.worker.min.mjs" || true

echo "✓ تم التنزيل إلى public/vendor. فعّل الآن خريطة الاستيراد المحلية في index.html،"
echo "  ولاستضافة es-module-shims محلياً بدّل مصفوفة SHIMS في index.html إلى /vendor/..."

# --- التحقّق الذاتي: تأكّد من وجود كل ملف مطلوب ومن رقم النسخة ---------------
echo; echo "── التحقّق من الملفات ──"
fail=0
must=(
  "$DST/build/three.module.js"
  "$DST/examples/jsm/controls/OrbitControls.js"
  "$DST/examples/jsm/webxr/VRButton.js"
  "$DST/examples/jsm/webxr/ARButton.js"
  "$DST/examples/jsm/exporters/GLTFExporter.js"
  "$DST/examples/jsm/objects/Sky.js"
  "$DST/examples/jsm/environments/RoomEnvironment.js"
  "$VEN/es-module-shims@$SHIMS/es-module-shims.js"
)
for m in "${must[@]}"; do
  if [ -s "$m" ]; then echo "  ✓ $(echo "$m" | sed "s#$ROOT/##")"; else echo "  ✗ ناقص: $m"; fail=1; fi
done
# رقم نسخة three يجب أن يكون 0.160.0
if grep -q "REVISION = *'0.160.0'\|REVISION='0.160.0'\|REVISION = \"0.160.0\"" "$DST/build/three.module.js" 2>/dev/null; then
  echo "  ✓ three REVISION = 0.160.0"
else
  echo "  ⚠ لم أجد REVISION=0.160.0 صراحةً — تحقّق يدوياً: grep REVISION build/three.module.js"
fi
[ "$fail" = 0 ] && echo "── كل الملفات موجودة. التالي: فعّل الخريطة المحلية ثم شغّل tools/verify-offline.mjs ──" \
              || { echo "── نقص ملفات — راجع الأخطاء أعلاه ──"; exit 1; }
