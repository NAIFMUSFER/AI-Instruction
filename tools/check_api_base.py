# -*- coding: utf-8 -*-
"""حارس عنوان الخادم — عنوان واحد في الصفحة، ومطابق لسياسة CSP.

الحادثة التي يمنعها: عنوان الخادم كان مكتوباً في أعلى الصفحة، ثم مُستهلَكاً في
أربعة مواضع نداء، ثم مكرّراً مرّة خامسة داخل `connect-src` في netlify.toml. نقل
الخدمة إلى مضيف آخر كان يتطلّب تعديل خمسة مواضع؛ نسيان واحدٍ منها يعطي
`Failed to fetch` بلا سبب ظاهر — أو نجاحاً في التطوير وفشلاً في الإنتاج وحده.

يفحص:
  1. `CONFIGURED_BASE` معرّف مرّة واحدة بالضبط في public/index.html.
  2. لا يظهر مضيف الـAPI في الصفحة إلا في سطر الإعداد وسطر المثال في التعليق.
  3. كل مسار `/v1/...` يُنادى عبر acsFetchJSON، ولا يبقى `fetch(` خام على الخادم.
  4. `connect-src` في netlify.toml يسمح بأصل الإعداد نفسه — وإلا حجبه المتصفّح.
  5. جسور التشخيص وتصنيفات الفشل موجودة في الصفحة المشحونة.

    python3 tools/check_api_base.py [<root>]
"""
import io
import os
import re
import sys

PAGE = os.path.join("public", "index.html")
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
    page = io.open(page_path, encoding="utf-8").read()

    # 1) إعداد واحد فقط
    bases = re.findall(r'CONFIGURED_BASE\s*=\s*"([^"]*)"', page)
    if len(bases) != 1:
        fails.append("public/index.html must define CONFIGURED_BASE exactly once "
                     "(found %d)" % len(bases))
        return fails, {}
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

    # 3) لا نداء خام لمسارات الخادم
    raw = re.findall(r"fetch\(\s*(?:llm|u|srv|base)\s*\+\s*['\"]/v1", page)
    if raw:
        fails.append("%d raw fetch(base + '/v1/...') call site(s) remain — "
                     "they bypass classification and the single base" % len(raw))
    for path in sorted(set(re.findall(r"['\"](/v1/[a-z/]+)['\"]", page))):
        callers = re.findall(r"(\w+)\(\s*['\"]" + re.escape(path) + r"['\"]", page)
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

    # 5) رموز العقد موجودة
    for sym in REQUIRED_SYMBOLS:
        if sym not in page:
            fails.append("shipped page is missing required API-contract symbol %r" % sym)
    for cls in REQUIRED_CLASSES:
        if ("'%s'" % cls) not in page:
            fails.append("shipped page is missing failure class %r" % cls)

    return fails, {"base": base, "host": host, "csp_ok": bool(csp_origin)}


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    fails, info = check(root)
    if fails:
        print("API BASE GATE FAILED")
        for f in fails:
            print("  ✗ %s" % f)
        sys.exit(1)
    print("✓ API base: one authoritative origin %s · every /v1 call classified · "
          "CSP connect-src allows it" % info.get("base"))


if __name__ == "__main__":
    main()
