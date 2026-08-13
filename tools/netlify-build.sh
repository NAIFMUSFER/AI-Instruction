#!/usr/bin/env bash
# =============================================================================
# netlify-build.sh — يُشغَّل في بيئة بناء Netlify (المتصلة بالإنترنت).
# يجلب مكتبات التشغيل بنُسخها المثبّتة إلى public/vendor حتى يخدمها الموقع محلياً
# بلا أي اعتماد على CDN وقت التشغيل. set -e: أي فشل يُفشل البناء فيبقى آخر نشر ناجح.
#
# النُّسخ مثبّتة لتطابق ما يستورده التطبيق — لا تُحدّثها دون التحقّق من التوافق:
#   three 0.160.0  ·  es-module-shims 1.8.2  ·  pdfjs-dist 4.0.379
# =============================================================================
set -euo pipefail

THREE=0.160.0
SHIMS=1.8.2
PDFJS=4.0.379
VEN="public/vendor"
mkdir -p "$VEN"

echo "▶ vendoring three@$THREE (full examples/jsm so addon internal imports resolve)"
npm pack "three@$THREE" >/dev/null
tar -xzf "three-$THREE.tgz"
mkdir -p "$VEN/three@$THREE/build" "$VEN/three@$THREE/examples"
cp package/build/three.module.js "$VEN/three@$THREE/build/three.module.js"
cp -R package/examples/jsm "$VEN/three@$THREE/examples/jsm"
rm -rf package "three-$THREE.tgz"

echo "▶ vendoring es-module-shims@$SHIMS"
npm pack "es-module-shims@$SHIMS" >/dev/null
tar -xzf "es-module-shims-$SHIMS.tgz"
mkdir -p "$VEN/es-module-shims@$SHIMS"
cp package/dist/es-module-shims.js "$VEN/es-module-shims@$SHIMS/es-module-shims.js"
rm -rf package "es-module-shims-$SHIMS.tgz"

echo "▶ vendoring pdfjs-dist@$PDFJS (module + worker)"
npm pack "pdfjs-dist@$PDFJS" >/dev/null
tar -xzf "pdfjs-dist-$PDFJS.tgz"
mkdir -p "$VEN/pdfjs@$PDFJS"
# أسماء الملفات في build/ قد تختلف قليلاً بين الإصدارات — جرّب المضغوط ثم العادي
cp package/build/pdf.min.mjs        "$VEN/pdfjs@$PDFJS/pdf.min.mjs"        2>/dev/null || cp package/build/pdf.mjs        "$VEN/pdfjs@$PDFJS/pdf.min.mjs"
cp package/build/pdf.worker.min.mjs "$VEN/pdfjs@$PDFJS/pdf.worker.min.mjs" 2>/dev/null || cp package/build/pdf.worker.mjs "$VEN/pdfjs@$PDFJS/pdf.worker.min.mjs"
rm -rf package "pdfjs-dist-$PDFJS.tgz"

# --- التحقّق: كل ملف حرِج موجود وغير فارغ، وثلاثي الأبعاد بالنسخة الصحيحة ---
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
  "$VEN/es-module-shims@$SHIMS/es-module-shims.js"
  "$VEN/pdfjs@$PDFJS/pdf.min.mjs"
  "$VEN/pdfjs@$PDFJS/pdf.worker.min.mjs"
)
for f in "${must[@]}"; do
  [ -s "$f" ] || { echo "✗ MISSING/EMPTY: $f"; exit 1; }
done
# ثابت الإصدار داخل three.module.js هو رقم المراجعة '160' (لا 0.160.0)
grep -Eq "REVISION *= *['\"]160['\"]" "$VEN/three@$THREE/build/three.module.js" \
  || { echo "✗ three REVISION mismatch (expected 160)"; exit 1; }

echo "✓ vendoring complete — production serves three/pdf.js locally (no runtime CDN)"

# --- حارس صفحة التطبيق (المرحلة 9.2 — علاج إنتاجي دائم) -------------------
# لا يُنشر أبداً index.html مفقود أو فارغ أو مبتور أو بلا كتل التطبيق المولَّدة.
# منطق الفحص كله في tools/check_index_guard.py (مصدر واحد يشاركه تحقّق النشر).
echo "▶ verifying layer integration (one viewport contract everywhere)"
[ -f tools/check_integration.py ] || { echo "✗ MISSING: tools/check_integration.py"; exit 1; }
python3 tools/check_integration.py || exit 1

echo "▶ verifying public/index.html structure"
[ -f tools/check_index_guard.py ] || { echo "✗ MISSING: tools/check_index_guard.py"; exit 1; }
python3 tools/check_index_guard.py public/index.html || exit 1

echo "▶ verifying the single API base and its CSP allowance"
[ -f tools/check_api_base.py ] || { echo "✗ MISSING: tools/check_api_base.py"; exit 1; }
python3 tools/check_api_base.py || exit 1

echo "✓ build verification complete"
