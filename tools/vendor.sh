#!/usr/bin/env bash
# =============================================================================
# vendor.sh — يجلب مكتبات العرض إلى public/vendor لاستضافة محلية كاملة (بلا CDN).
# شغّله من جذر المستودع على جهاز متّصل بالشبكة:
#     bash tools/vendor.sh
#
# النتيجة مطابقة لما ينتجه tools/netlify-build.sh في بيئة بناء Netlify، عمداً:
# البناء المحلّي والبناء المنشور يجب أن يشحنا الشجرة نفسها بالضبط.
#
# F-29 — ثلاثة أعطال أُغلقت هنا:
#   1. كان الملفّ ينزّل es-module-shims **ويُدرجه في قائمة اللازم**. لكنّ F-11
#      حذفه من الصفحة، و netlify-build.sh يُفشل البناء صراحةً إن وجد أي أثر له
#      في public/vendor. أي أن اتّباع التعليمات الموثّقة محلياً كان يُنتج شجرةً
#      يرفضها البناء المنشور.
#   2. كان ينزّل ستّ إضافات فقط، والتطبيق يستورد **اثنتي عشرة**: الستّ الساكنة،
#      إضافةً إلى EffectComposer و RenderPass و OutputPass و ShaderPass و
#      SSAOPass و FXAAShader في generated/pbr-bridge.js (وهي بدورها تسحب
#      CopyShader و SSAOShader). فيسقط SSAO و FXAA بصمت إلى POST_UNAVAILABLE،
#      و tools/verify-offline.mjs يطبع PASS لأنه يفحص ACS.ready وحدها.
#   3. كان يطلب «تعطيل خريطة الاستيراد الخارجية» و«تبديل مصفوفة SHIMS في
#      index.html» — وكلاهما لم يعد له وجود: الصفحة تحوي خريطة استيراد واحدة
#      محلّية أصلاً.
#
# النُّسخ مثبّتة لتطابق ما يستورده التطبيق — لا تُحدّثها دون التحقّق من التوافق:
#   three 0.160.0  ·  pdfjs-dist 4.10.38
# =============================================================================
set -euo pipefail

THREE=0.160.0
PDFJS=4.10.38
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VEN="public/vendor"
mkdir -p "$VEN"
# Remove the vulnerable generated copy left by pre-upgrade cached builds.
rm -rf "$VEN/pdfjs@4.0.379"

# Install the integrity-checked lock before copying browser runtime assets.
npm ci --ignore-scripts
node -e 'for (const [p,v] of [["three",process.argv[1]],["pdfjs-dist",process.argv[2]]]) { if(require("./node_modules/"+p+"/package.json").version!==v) throw Error(p+" version mismatch"); }' "$THREE" "$PDFJS"
mkdir -p "$VEN/three@$THREE/build" "$VEN/three@$THREE/examples" "$VEN/pdfjs@$PDFJS"
cp node_modules/three/build/three.module.js "$VEN/three@$THREE/build/three.module.js"
rm -rf "$VEN/three@$THREE/examples/jsm"
cp -R node_modules/three/examples/jsm "$VEN/three@$THREE/examples/jsm"
cp node_modules/pdfjs-dist/build/pdf.min.mjs "$VEN/pdfjs@$PDFJS/pdf.min.mjs"
cp node_modules/pdfjs-dist/build/pdf.worker.min.mjs "$VEN/pdfjs@$PDFJS/pdf.worker.min.mjs"

# --- التحقّق: نفس قائمة netlify-build.sh حرفاً بحرف (١٧ ملفّاً) --------------
echo "▶ verifying vendored files"
must=(
  "$VEN/three@$THREE/build/three.module.js"
  "$VEN/three@$THREE/examples/jsm/controls/OrbitControls.js"
  "$VEN/three@$THREE/examples/jsm/webxr/VRButton.js"
  "$VEN/three@$THREE/examples/jsm/webxr/ARButton.js"
  "$VEN/three@$THREE/examples/jsm/exporters/GLTFExporter.js"
  "$VEN/three@$THREE/examples/jsm/objects/Sky.js"
  "$VEN/three@$THREE/examples/jsm/environments/RoomEnvironment.js"
  "$VEN/three@$THREE/examples/jsm/postprocessing/EffectComposer.js"
  "$VEN/three@$THREE/examples/jsm/postprocessing/RenderPass.js"
  "$VEN/three@$THREE/examples/jsm/postprocessing/ShaderPass.js"
  "$VEN/three@$THREE/examples/jsm/postprocessing/OutputPass.js"
  "$VEN/three@$THREE/examples/jsm/postprocessing/SSAOPass.js"
  "$VEN/three@$THREE/examples/jsm/shaders/FXAAShader.js"
  "$VEN/three@$THREE/examples/jsm/shaders/CopyShader.js"
  "$VEN/three@$THREE/examples/jsm/shaders/SSAOShader.js"
  "$VEN/pdfjs@$PDFJS/pdf.min.mjs"
  "$VEN/pdfjs@$PDFJS/pdf.worker.min.mjs"
)
EXPECTED_VENDORED=17
[ "${#must[@]}" -eq "$EXPECTED_VENDORED" ] || {
  echo "✗ vendored-file list has ${#must[@]} entries, expected $EXPECTED_VENDORED"
  echo "  حدّث EXPECTED_VENDORED عمداً — القائمة المتقلّصة هي كيف يصير أصلٌ ناقصٌ"
  echo "  بناءً أخضرَ وشاشةً سوداء"
  exit 1; }
for f in "${must[@]}"; do
  [ -s "$f" ] || { echo "✗ MISSING/EMPTY: $f"; exit 1; }
done
# لا يُشحَن ما لا يُطلَب — نفس شرط netlify-build.sh حتى لا يختلف البناءان.
[ ! -e "$VEN/es-module-shims" ] && [ -z "$(find "$VEN" -maxdepth 1 -name 'es-module-shims@*' -print -quit)" ] || {
  echo "✗ es-module-shims موجود في $VEN ولا شيء يحمّله (F-11)"; exit 1; }
grep -Eq "REVISION *= *['\"]160['\"]" "$VEN/three@$THREE/build/three.module.js" \
  || { echo "✗ three REVISION mismatch (expected 160)"; exit 1; }

echo "✓ تمّ. public/vendor صار مطابقاً لما ينتجه tools/netlify-build.sh."
echo "  لا حاجة إلى تعديل شيء في public/index.html: خريطة الاستيراد فيها محلّية"
echo "  أصلاً وتشير إلى /vendor/three@$THREE/‎."
