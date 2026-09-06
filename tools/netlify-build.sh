#!/usr/bin/env bash
# =============================================================================
# netlify-build.sh — يُشغَّل في بيئة بناء Netlify (المتصلة بالإنترنت).
# يجلب مكتبات التشغيل بنُسخها المثبّتة إلى public/vendor حتى يخدمها الموقع محلياً
# بلا أي اعتماد على CDN وقت التشغيل. set -e: أي فشل يُفشل البناء فيبقى آخر نشر ناجح.
#
# النُّسخ مثبّتة لتطابق ما يستورده التطبيق — لا تُحدّثها دون التحقّق من التوافق:
#   three 0.160.0  ·  pdfjs-dist 4.10.38
#
# es-module-shims: حُذف (F-11). الصفحة لم تعد تحمّله، فتنزيله هنا كان يعني شحن
# ملفّ لا يطلبه أحد — وزناً ميّتاً ومساحة هجوم بلا مقابل. وهو نفسه كان السبب
# الوحيد لـ script-src 'unsafe-eval' و blob:، وقد سقط الاثنان معه. التفصيل في
# CSP-HARDENING.md §5.
# =============================================================================
set -euo pipefail

THREE=0.160.0
PDFJS=4.10.38
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

# --- التحقّق: كل ملف حرِج موجود وغير فارغ، وثلاثي الأبعاد بالنسخة الصحيحة ---
# 17 ملفّاً: 15 من three (البناء + 14 إضافة) + ملفّا pdf.js. كانت 18 قبل حذف
# es-module-shims. العدد مكتوب صراحةً ويُفحَص أدناه حتى لا يمرّ حذفٌ صامت لسطر
# من القائمة على أنه «تحقّقٌ ناجح».
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
  echo "  update EXPECTED_VENDORED deliberately — a shrinking list is how a"
  echo "  missing runtime asset turns into a green build and a black viewport"
  exit 1; }
for f in "${must[@]}"; do
  [ -s "$f" ] || { echo "✗ MISSING/EMPTY: $f"; exit 1; }
done
# لا يُشحَن ما لا يُطلَب: أي أثر باقٍ لـes-module-shims يعني أن التنزيل عاد
[ ! -e "$VEN/es-module-shims" ] && [ -z "$(find "$VEN" -maxdepth 1 -name 'es-module-shims@*' -print -quit)" ] || {
  echo "✗ es-module-shims was vendored into $VEN but nothing loads it (F-11)"; exit 1; }
# ثابت الإصدار داخل three.module.js هو رقم المراجعة '160' (لا 0.160.0)
grep -Eq "REVISION *= *['\"]160['\"]" "$VEN/three@$THREE/build/three.module.js" \
  || { echo "✗ three REVISION mismatch (expected 160)"; exit 1; }

echo "✓ vendoring complete — production serves three/pdf.js locally (no runtime CDN)"

# --- أصل البناء: تُختَم هوية النسخة قبل أي فحص بنيوي ------------------------
# بلا هذه الخطوة تبقى window.ACS_BUILD_INFO عند الرموز النائبة وتُعلن الواجهة عن
# نفسها UNPROVENANCED. الختم يجعل تحقّق الإنتاج قادراً على قول "أيّ نسخة قِستُ".
# الهدف بعد F-09 هو public/app/boot/build-info.js لا public/index.html: هناك
# يعيش window.ACS_BUILD_INFO الآن، والأداة ترفض أي هدف لا يحوي الرموز.
echo "▶ stamping build provenance into public/app/boot/build-info.js"
python3 tools/write_build_info.py >/dev/null || true
python3 tools/stamp_build_tokens.py || {
  echo "⚠ build provenance not stamped — the frontend will declare UNPROVENANCED"; }
python3 tools/stamp_build_tokens.py --check

echo "▶ verifying layer integration (one viewport contract everywhere)"
[ -f tools/check_integration.py ] || { echo "✗ MISSING: tools/check_integration.py"; exit 1; }
python3 tools/check_integration.py || exit 1

# --- حارس واجهة التطبيق (F-09/F-11 — علاج إنتاجي دائم) ---------------------
# لا يُنشر أبداً index.html مفقود أو فارغ أو مرتدّ إلى الكتلة الواحدة أو مشيراً
# إلى وحدة غير موجودة، ولا شجرةُ /app/ فيها وحدة يتيمة أو وحدة فوق السقف.
# منطق الفحص كله في tools/check_index_guard.py (مصدر واحد يشاركه تحقّق النشر).
echo "▶ verifying the index shell and the public/app module tree"
[ -f tools/check_index_guard.py ] || { echo "✗ MISSING: tools/check_index_guard.py"; exit 1; }
python3 tools/check_index_guard.py public/index.html || exit 1

echo "▶ verifying the single API base and its CSP allowance"
[ -f tools/check_api_base.py ] || { echo "✗ MISSING: tools/check_api_base.py"; exit 1; }
python3 tools/check_api_base.py || exit 1

# --- بصمة خريطة الاستيراد (F-11) -------------------------------------------
# آخر عنصر داخليّ في الصفحة يُسمَح به ببصمة sha256 واحدة. البصمة مكتوبة في
# ثلاثة مواضع، وتعديل بايت واحد في الخريطة يُبطلها فيرفض المتصفّح تنفيذها ولا
# يُحمَّل المحرّك أصلاً. هذا الفحص هو ما يمنع ذلك من الوصول إلى الإنتاج.
echo "▶ verifying the inline import-map CSP hash (page ≡ sidecar ≡ netlify.toml)"
[ -f tools/check_csp_hash.py ] || { echo "✗ MISSING: tools/check_csp_hash.py"; exit 1; }
python3 tools/check_csp_hash.py || exit 1

echo "✓ build verification complete"
