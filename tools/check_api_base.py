# -*- coding: utf-8 -*-
"""حارس عنوان الخادم — عنوان واحد في الصفحة، ومطابق لسياسة CSP.

الحادثة التي يمنعها: عنوان الخادم كان مكتوباً في أعلى الصفحة، ثم مُستهلَكاً في
أربعة مواضع نداء، ثم مكرّراً مرّة خامسة داخل `connect-src` في netlify.toml. نقل
الخدمة إلى مضيف آخر كان يتطلّب تعديل خمسة مواضع؛ نسيان واحدٍ منها يعطي
`Failed to fetch` بلا سبب ظاهر — أو نجاحاً في التطوير وفشلاً في الإنتاج وحده.

بعد F-09 لم يعد «في الصفحة» يعني ملفّاً واحداً: الإعداد الوحيد انتقل إلى
public/app/boot/api-base.js، ومواضع النداء إلى وحدات public/app/. الشرط لم
يتغيّر — عنوانٌ واحد لا خمسة — بل تغيّر النصّ الذي يُبحَث فيه: app_source.app_text()
بدل نصّ الصفحة. فحص التكرار يجري على القشرة والشيفرة معاً (page_text)، فلا يهرب
عنوانٌ ثانٍ بأن يُكتَب في العلامة.

يفحص:
  1. `CONFIGURED_BASE` معرّف مرّة واحدة بالضبط في شيفرة التطبيق كلّها.
  2. لا يظهر مضيف الـAPI في القشرة ولا في الشيفرة إلا في سطر الإعداد وسطر المثال.
  3. كل مسار `/v1/...` يُنادى عبر acsFetchJSON، ولا يبقى `fetch(` خام على الخادم.
  4. `connect-src` في netlify.toml يسمح بأصل الإعداد نفسه — وإلا حجبه المتصفّح.
  5. جسور التشخيص وتصنيفات الفشل موجودة في الوحدات المشحونة.

    python3 tools/check_api_base.py [<root>]
"""
import io
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import app_source as A                                            # noqa: E402

PAGE = os.path.join("public", "index.html")
# الموضع الوحيد المسموح به لتعريف CONFIGURED_BASE بعد F-09
API_BASE_REL = os.path.join("public", "app", "boot", "api-base.js")
TOML = "netlify.toml"

REQUIRED_SYMBOLS = (
    "window.ACS_API",
    "acsFetchJSON",
    "apiURL",
    "window.ACS.apiDiagnostics",
    "acsErrorPanel",
)
REQUIRED_CLASSES = ("NETWORK_DNS", "NETWORK_OFFLINE", "TIMEOUT", "HTTP_4XX",
                    "HTTP_429", "HTTP_5XX", "INVALID_JSON", "VALID_API_ERROR",
                    "SUCCESS")


def check(root):
    fails = []
    page_path = os.path.join(root, PAGE)
    if not os.path.isfile(page_path):
        return ["%s is missing" % PAGE], {}
    if os.path.realpath(root) != os.path.realpath(A.ROOT):
        return (["this gate reads the application modules through "
                 "tools/app_source.py, which is bound to %s; it cannot verify "
                 "the unrelated tree %s" % (A.ROOT, os.path.realpath(root))],
                {})
    base_path = os.path.join(root, API_BASE_REL)
    if not os.path.isfile(base_path):
        return ["%s is missing — the single API origin has no home"
                % API_BASE_REL.replace(os.sep, "/")], {}

    shell = A.shell()
    app = A.app_text()              # كل شيفرة التطبيق، بترتيب التحميل الحقيقي
    page = A.page_text()            # القشرة + الشيفرة — نظير `page` قبل F-09

    # 1) إعداد واحد فقط، وفي ملفّه المعلَن وحده
    bases = re.findall(r'CONFIGURED_BASE\s*=\s*"([^"]*)"', page)
    if len(bases) != 1:
        fails.append("the shipped frontend must define CONFIGURED_BASE exactly "
                     "once across public/index.html and public/app/ (found %d)"
                     % len(bases))
        return fails, {}
    if 'CONFIGURED_BASE' in shell:
        fails.append("public/index.html still mentions CONFIGURED_BASE — the "
                     "single origin lives in %s only"
                     % API_BASE_REL.replace(os.sep, "/"))
    if not re.search(r'CONFIGURED_BASE\s*=\s*"',
                     io.open(base_path, encoding="utf-8").read()):
        fails.append("%s does not define CONFIGURED_BASE — the configuration "
                     "site has drifted out of its declared file"
                     % API_BASE_REL.replace(os.sep, "/"))
    base = bases[0].rstrip("/")
    m = re.match(r"^(https?)://([^/]+)$", base)
    if not m:
        fails.append("CONFIGURED_BASE %r is not a bare scheme://host origin" % base)
        return fails, {"base": base}
    scheme, host = m.group(1), m.group(2)
    if scheme != "https":
        fails.append("CONFIGURED_BASE must be https in production (got %s)" % scheme)

    # 2) المضيف لا يتكرّر كعنوان حيّ في مواضع أخرى
    occurrences = [ln for ln in page.split("\n") if host in ln]
    live = [ln for ln in occurrences
            if "CONFIGURED_BASE" not in ln and not ln.strip().startswith(("*", "<!--", "//"))
            and "مثال" not in ln]
    if live:
        fails.append("the API host appears outside the single configuration site "
                     "(%d line(s)); route every call through ACS_API.url() instead: %s"
                     % (len(live), live[0].strip()[:100]))

    # 3) لا نداء خام لمسارات الخادم — يُمسَح في شيفرة التطبيق، فهي موضع النداء
    raw = re.findall(r"fetch\(\s*(?:llm|u|srv|base)\s*\+\s*['\"]/v1", app)
    if raw:
        fails.append("%d raw fetch(base + '/v1/...') call site(s) remain — "
                     "they bypass classification and the single base" % len(raw))
    v1_paths = sorted(set(re.findall(r"['\"](/v1/[a-z/]+)['\"]", app)))
    if not v1_paths:
        fails.append("no /v1/... endpoint is referenced anywhere in "
                     "public/app/ — either the API layer vanished or this gate "
                     "is scanning the wrong text")
    for path in v1_paths:
        callers = re.findall(r"(\w+)\(\s*['\"]" + re.escape(path) + r"['\"]", app)
        bad = [c for c in callers if c not in ("acsFetchJSON", "url", "apiURL")]
        if bad:
            fails.append("%s is called through %s — must go through acsFetchJSON"
                         % (path, ", ".join(sorted(set(bad)))))

    # 4) CSP يسمح بالأصل نفسه
    toml_path = os.path.join(root, TOML)
    csp_origin = None
    if os.path.isfile(toml_path):
        toml = io.open(toml_path, encoding="utf-8").read()
        mm = re.search(r'Content-Security-Policy\s*=\s*"([^"]*)"', toml)
        if not mm:
            fails.append("netlify.toml has no Content-Security-Policy header")
        else:
            csp = mm.group(1)
            cm = re.search(r"connect-src([^;\"]*)", csp)
            if not cm:
                fails.append("CSP has no connect-src directive")
            else:
                sources = cm.group(1).split()
                csp_origin = base in sources
                if "*" in sources or "'unsafe-inline'" in sources:
                    fails.append("connect-src must not be widened to * ")
                if not csp_origin:
                    fails.append("connect-src does not allow %s — the browser will "
                                 "block every API call from the deployed page "
                                 "(connect-src: %s)" % (base, " ".join(sources)))
    else:
        fails.append("netlify.toml is missing — CSP cannot be verified")

    # 5) رموز العقد موجودة في الشيفرة المشحونة
    for sym in REQUIRED_SYMBOLS:
        if sym not in app:
            fails.append("the shipped application modules are missing required "
                         "API-contract symbol %r" % sym)
    for cls in REQUIRED_CLASSES:
        if ("'%s'" % cls) not in app:
            fails.append("the shipped application modules are missing failure "
                         "class %r" % cls)

    return fails, {"base": base, "host": host, "csp_ok": bool(csp_origin),
                   "v1_paths": len(v1_paths)}


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    fails, info = check(root)
    if fails:
        print("API BASE GATE FAILED")
        for f in fails:
            print("  ✗ %s" % f)
        sys.exit(1)
    print("✓ API base: one authoritative origin %s declared in %s · all %d /v1 "
          "endpoint(s) routed through acsFetchJSON in public/app/ · CSP "
          "connect-src allows it"
          % (info.get("base"), API_BASE_REL.replace(os.sep, "/"),
             info.get("v1_paths")))


if __name__ == "__main__":
    main()
