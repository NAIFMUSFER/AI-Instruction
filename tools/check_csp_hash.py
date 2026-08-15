# -*- coding: utf-8 -*-
"""حارس بصمة خريطة الاستيراد (F-11) — ثلاثة مواضع، قيمة واحدة.

بعد F-09/F-11 لم يبقَ في public/index.html عنصر داخليّ قابل للتنفيذ إلا
`<script type="importmap">` وحده: خريطة الاستيراد لا يمكن أن تكون ملفّاً خارجياً
(لا متصفّح يدعم `src` عليها دعماً كافياً)، فهي العنصر الوحيد الذي يحتاج إذناً
صريحاً في `script-src`. الإذن ليس `'unsafe-inline'` بل بصمة sha256 لمحتواها
حرفاً بحرف.

وهذا بالضبط موضع العطل الصامت: بصمة محتوى تُبطلها فاصلة واحدة. من يعدّل مسار
`three` في الخريطة — أو يضيف مسافة — يحصل على صفحة تعمل محلّياً بلا CSP، وتُرفض
في الإنتاج بـ`Refused to execute inline script`، فلا يُحمَّل المحرّك أصلاً
والنافذة سوداء بلا رسالة خطأ مفهومة.

القيمة الواحدة مكتوبة في ثلاثة مواضع، ويجب أن تتطابق الثلاثة:

  1. المحسوبة الآن من نصّ الخريطة داخل public/index.html  (الحقيقة)
  2. public/app/importmap.sha256   (ما كتبه tools/frontend_shell.js)
  3. `script-src` في netlify.toml  (ما سيطبّقه المتصفّح فعلاً)

أي اختلاف = خروج غير صفري، مع طباعة القيم الثلاث وسطر إصلاح واحد.

    python3 tools/check_csp_hash.py [<root>]
"""
import base64
import hashlib
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(HERE)

PAGE_REL = os.path.join("public", "index.html")
SIDECAR_REL = os.path.join("public", "app", "importmap.sha256")
TOML_REL = "netlify.toml"

# الشكل الوحيد المقبول للبصمة في CSP — 'sha256-<base64>' بين علامتَي اقتباس
CSP_HASH_RX = re.compile(r"'(sha256-[A-Za-z0-9+/=]+)'")


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def importmap_body(page):
    """جسم خريطة الاستيراد كما يراه المتصفّح: بين `>` و`</script>` حرفياً.

    لا تجريد ولا تطبيع ولا إزالة مسافات: البصمة تُحسَب على البايتات نفسها التي
    يحسبها المتصفّح، وإلّا صار الحارس يوافق على شيء ويرفض المتصفّح شيئاً آخر.
    """
    m = re.search(r'<script type="importmap">(.*?)</script>', page, re.S)
    return m.group(1) if m else None


def sha256_csp(text):
    return "sha256-" + base64.b64encode(
        hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")


def check(root):
    """يعيد (الأعطال، الوقائع). قائمة فارغة = المواضع الثلاثة متّفقة."""
    fails = []
    facts = {"computed": None, "sidecar": None, "toml": None}

    page_path = os.path.join(root, PAGE_REL)
    if not os.path.isfile(page_path):
        return ["%s is missing" % PAGE_REL], facts
    page = _read(page_path)

    body = importmap_body(page)
    if body is None:
        return ['public/index.html has no <script type="importmap"> element — '
                "the page cannot resolve the bare 'three' specifier"], facts
    facts["computed"] = sha256_csp(body)
    facts["importmap_bytes"] = len(body.encode("utf-8"))

    # 2) الملفّ المرافق الذي يكتبه tools/frontend_shell.js
    side_path = os.path.join(root, SIDECAR_REL)
    if not os.path.isfile(side_path):
        fails.append("%s is missing — re-run `node tools/frontend_shell.js`"
                     % SIDECAR_REL.replace(os.sep, "/"))
    else:
        facts["sidecar"] = _read(side_path).strip()
        if facts["sidecar"] != facts["computed"]:
            fails.append("public/app/importmap.sha256 does not match the import "
                         "map that is actually in the page")

    # 3) البصمة داخل script-src في netlify.toml
    toml_path = os.path.join(root, TOML_REL)
    if not os.path.isfile(toml_path):
        fails.append("netlify.toml is missing — the deployed CSP cannot be "
                     "verified")
    else:
        toml = _read(toml_path)
        mm = re.search(r'Content-Security-Policy\s*=\s*"([^"]*)"', toml)
        if not mm:
            fails.append("netlify.toml has no Content-Security-Policy header")
        else:
            csp = mm.group(1)
            sm = re.search(r"script-src([^;\"]*)", csp)
            if not sm:
                fails.append("the CSP has no script-src directive")
            else:
                directive = sm.group(1)
                hashes = CSP_HASH_RX.findall(directive)
                facts["toml"] = hashes[0] if hashes else None
                facts["script_src"] = directive.strip()
                if not hashes:
                    fails.append("script-src carries no 'sha256-…' hash — the "
                                 "inline import map would be refused by the "
                                 "browser (script-src: %s)" % directive.strip())
                elif len(hashes) > 1:
                    fails.append("script-src carries %d sha256 hashes; exactly "
                                 "one inline element (the import map) is "
                                 "allowed: %s" % (len(hashes), ", ".join(hashes)))
                elif hashes[0] != facts["computed"]:
                    fails.append("the netlify.toml script-src hash does not "
                                 "match the import map in the page")
                # الإذن بالبصمة لا يجوز أن يتعايش مع إذن مفتوح يُبطل معناه
                for weak in ("'unsafe-inline'", "'unsafe-eval'", "blob:"):
                    if weak in directive:
                        fails.append("script-src still contains %s — the import "
                                     "map hash is pointless next to it" % weak)
    return fails, facts


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT
    fails, facts = check(root)
    if fails:
        print("CSP IMPORTMAP HASH GATE FAILED — the three copies disagree.")
        for x in fails:
            print("  ✗ %s" % x)
        print("")
        print("  computed from public/index.html : %s" % facts.get("computed"))
        print("  public/app/importmap.sha256     : %s" % facts.get("sidecar"))
        print("  netlify.toml script-src         : %s" % facts.get("toml"))
        print("")
        print("FIX: run `node tools/frontend_shell.js` to rewrite "
              "public/app/importmap.sha256, then paste the computed value into "
              "the script-src directive in netlify.toml.")
        sys.exit(1)
    print("✓ CSP importmap hash: %s · identical in the page (%d B), "
          "public/app/importmap.sha256 and netlify.toml script-src"
          % (facts["computed"], facts["importmap_bytes"]))


if __name__ == "__main__":
    main()
