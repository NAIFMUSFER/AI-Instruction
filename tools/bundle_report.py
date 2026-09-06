# -*- coding: utf-8 -*-
"""F-09 — قياس الواجهة المشحونة فعلاً بعد التفكيك. قياس فقط، بلا إعادة هيكلة.

    python3 tools/bundle_report.py            # يكتب tests/performance/bundle_report.json
    python3 tools/bundle_report.py --stdout   # يطبع ولا يكتب

لماذا هذا الملفّ موجود: الادّعاء بأن F-09 نُفّذ أسهل من تنفيذه. فوُضع أوّلاً رقمٌ
لا يقبل الادّعاء — حجم الصفحة الحقيقي موزّعاً على كل كتلة فيها، مقارَناً بميزانية
معلنة — وكان يقول حينها `F-09 NOT IMPLEMENTED`. الآن جرى التفكيك فعلاً، فتغيّر ما
يُقاس: لم تعد الصفحة هي الحزمة، بل صارت قشرةً تشير إلى ملفّات تحت public/app/.

والسؤال لم يعد «هل جرى تفكيك؟» بل «أهو تفكيك حقيقي أم إعادة تسمية؟». تقسيمٌ يضع
٩٥٪ من الشيفرة في ملفّ واحد ويشتّت الباقي على ثمانية عشر ملفّاً يبدو مفكَّكاً في
عدّ الملفّات ولا يفكّك شيئاً. لذلك يُقاس هنا لكل وحدة حجمها ونسبتها من مجموع شيفرة
الطرف الأوّل، ويُفحَص في tests/remediation/test_bundle_report.py أن أكبر وحدة تبقى
دون عتبة معلنة من ذلك المجموع. هذا هو الرقم المضادّ للتلاعب.

ما لا يُقاس لا يُقدَّر:
  • brotli يُبلَّغ عنه فقط إذا كانت الوحدة مستوردة، وإلّا null مع سبب.
  • public/vendor فارغ في هذا الصندوق، فأحجام المكتبات null مع سبب.
  • «الشيفرة المؤجَّلة» صفرٌ اليوم — يُقال صفراً صراحةً مع تعداد نداءات import()
    الديناميكية التي وُجدت فعلاً وسببِ عدم احتسابها.

الحتمية شرط: لا طابع زمني ولا مسار مطلق في المخرَج، وgzip يُضغط بـmtime=0.
تشغيلان متتاليان يعطيان بايتاً ببايت المخرَج نفسه.
"""
import gzip
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import app_source as A                                            # noqa: E402

PAGE_REL = "public/index.html"
CSS_REL = "public/app/styles/app.css"
OUT_REL = "tests/performance/bundle_report.json"

# ── الميزانية المعلَنة ──────────────────────────────────────────────────────
# سقف القشرة: 200 KB. هو نفسه MAX_BYTES في tools/check_index_guard.py — رقم
# واحد لمعنى واحد. القشرة تحمل العلامة وكتل DOM المولَّدة ووسوم التحميل فقط.
SHELL_BUDGET_BYTES = 200 * 1024              # 204800
# والمفضَّل أشدّ من السقف: 150 KB. السقف يمنع الارتداد، والمفضَّل هو الهدف.
SHELL_PREFERRED_BYTES = 150 * 1024           # 153600
# أكبر ملفّ JS واحد: تقسيمٌ لا ينتج عنه قطعة أصغر من ذلك ليس تقسيماً.
MAX_SINGLE_MODULE_BYTES = 300 * 1024         # 307200


def read(rel):
    with io.open(os.path.join(ROOT, rel), "r", encoding="utf-8") as fh:
        return fh.read()


def b(s):
    return len(s.encode("utf-8"))


def gzip_bytes(text):
    """gzip حتمي: mtime=0 وإلّا اختلف المخرَج بين تشغيلين."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as g:
        g.write(text.encode("utf-8"))
    return len(buf.getvalue())


def brotli_bytes(text):
    try:
        import brotli                                            # noqa: F401
    except Exception:                                            # noqa: BLE001
        return None, ("brotli is not importable in this environment "
                      "(no `brotli` / `brotlicffi` module, and the standard "
                      "library ships no brotli compressor); reported as null "
                      "rather than estimated")
    try:
        return len(brotli.compress(text.encode("utf-8"), quality=11)), None
    except Exception as exc:                                     # noqa: BLE001
        return None, "brotli import succeeded but compression failed: %r" % (exc,)


# ─────────────────────────────────────────────── عناصر القشرة (مسح تسلسلي) ──
def script_and_style_elements(page):
    """مسح تسلسلي — لا regex عام. يقفز من نهاية كل عنصر فلا يرى ما بداخله."""
    scripts, styles = [], []
    i = 0
    while True:
        a = page.find("<script", i)
        if a < 0:
            break
        ge = page.find(">", a)
        e = page.find("</script>", ge)
        if e < 0:
            break
        attrs = page[a + 7:ge].strip()
        body = page[ge + 1:e]
        kind = "module" if 'type="module"' in attrs else (
            "importmap" if 'type="importmap"' in attrs else "classic")
        src = re.search(r'\bsrc\s*=\s*"([^"]+)"', attrs)
        scripts.append({
            "index": len(scripts) + 1,
            "line": page.count("\n", 0, a) + 1,
            "kind": kind,
            "external": bool(src),
            "src": src.group(1) if src else None,
            "inline_body_bytes": b(body),
        })
        i = e + 9
    i = 0
    while True:
        a = page.find("<style", i)
        if a < 0:
            break
        ge = page.find(">", a)
        e = page.find("</style>", ge)
        if e < 0:
            break
        styles.append({"index": len(styles) + 1,
                       "line": page.count("\n", 0, a) + 1,
                       "body_bytes": b(page[ge + 1:e])})
        i = e + 8
    return scripts, styles


# ───────────────────────────────────────────── رسم بيان الاستيراد الساكن ───
STATIC_IMPORT = re.compile(
    r"""^import\s+(?:[^;'"]*?from\s*)?['"]([^'"]+)['"];""", re.M)
DYNAMIC_IMPORT = re.compile(r"""\bimport\(\s*['"]([^'"]+)['"]""")

# علامات الكتل المولَّدة — نفس الشكل الذي يكتبه المولِّدون بالضبط، بعلامة النهاية
# ` ===== */` أو ` ===== -->`. بدونها يلتقط النمط أي تعليق يبدأ بـ`ACS` فيُبالغ العدّ.
JS_BEGIN = re.compile(r"/\* ===== ACS (?!END)[A-Z0-9][A-Z0-9 .]*?"
                      r"(?: \([^)]*\))? ===== \*/")
DOM_BEGIN = re.compile(r"<!-- ===== ACS (?!END)[A-Z0-9][A-Z0-9 .]*?"
                       r"(?: \([^)]*\))? ===== -->")


def eager_closure(modules, entry="main.js"):
    """كل وحدة يصل إليها main.js باستيراد ساكن — أي كل ما يُقيَّم عند الإقلاع."""
    seen, stack = set(), [entry]
    while stack:
        cur = stack.pop()
        if cur in seen or cur not in modules:
            continue
        seen.add(cur)
        for spec in STATIC_IMPORT.findall(modules[cur]):
            if spec.startswith("."):
                tgt = os.path.normpath(os.path.join(
                    os.path.dirname(cur), spec)).replace(os.sep, "/")
                stack.append(tgt)
    return seen


def dynamic_specifiers(modules):
    """كل نداء import() ديناميكي، مصنَّفاً: طرفٌ أوّل أم مكتبة موردة."""
    out = []
    for name in sorted(modules):
        for spec in DYNAMIC_IMPORT.findall(modules[name]):
            out.append({"in_module": "public/app/" + name,
                        "specifier": spec,
                        "first_party": spec.startswith(".")
                        or spec.startswith("/app/")})
    return out


def vendor_report():
    vdir = os.path.join(ROOT, "public", "vendor")
    if not os.path.isdir(vdir):
        return {"present": False, "total_bytes": None, "files": None,
                "reason": "public/vendor does not exist in this checkout; "
                          "Netlify populates it at build time via "
                          "tools/netlify-build.sh. NOT MEASURED — no estimate "
                          "is substituted. (es-module-shims is no longer "
                          "vendored at all: F-11 removed it from the page and "
                          "from tools/netlify-build.sh.)"}
    files = []
    for base, _dirs, names in os.walk(vdir):
        for n in sorted(names):
            p = os.path.join(base, n)
            files.append({"path": os.path.relpath(p, ROOT).replace(os.sep, "/"),
                          "bytes": os.path.getsize(p)})
    files.sort(key=lambda f: f["path"])
    if not files:
        return {"present": True, "empty": True, "total_bytes": None,
                "files": None,
                "reason": "public/vendor exists but is EMPTY in this sandbox "
                          "(no network, tools/vendor.sh has never run). The 17 "
                          "vendored runtime assets — the three@0.160.0 build "
                          "plus 14 addons, and the pdfjs@4.10.38 module and "
                          "worker — are NOT MEASURED here. (es-module-shims is "
                          "no longer vendored at all: F-11 removed it from the "
                          "page and from tools/netlify-build.sh.) NOT VERIFIED "
                          "— EXTERNAL ENVIRONMENT REQUIRED."}
    return {"present": True, "empty": False,
            "total_bytes": sum(f["bytes"] for f in files),
            "file_count": len(files), "files": files, "reason": None}


# ───────────────────────────────────────────────────────────────── البناء ──
def build():
    page = read(PAGE_REL)
    raw = page.encode("utf-8")
    scripts, styles = script_and_style_elements(page)

    modules = A.modules()
    sizes = {k: b(v) for k, v in modules.items()}
    boot = sorted(k for k in modules if k.startswith("boot/"))
    first_party_total = sum(sizes.values())

    eager = eager_closure(modules)
    core_bytes = sum(sizes[k] for k in eager)
    boot_bytes = sum(sizes[k] for k in boot)
    # المؤجَّل: وحدة طرفٍ أوّل لا يبلغها الاستيراد الساكن من main.js وليست سكربت
    # إقلاع. اليوم لا توجد واحدة — يُقال صفراً، ولا يُتظاهَر بتقسيم كسول.
    lazy = sorted(k for k in modules
                  if k not in eager and not k.startswith("boot/"))
    dyn = dynamic_specifiers(modules)
    dyn_first_party = [d for d in dyn if d["first_party"]]

    css = A.css_text()
    br, br_reason = brotli_bytes(page)

    per_module = sorted(
        ({"path": "public/app/" + k,
          "bytes": sizes[k],
          "gzip_bytes": gzip_bytes(modules[k]),
          "group": (k.split("/")[0] if "/" in k else "(root)"),
          "loaded": ("boot-classic" if k.startswith("boot/")
                     else "eager" if k in eager else "unreferenced"),
          "pct_of_first_party_js": round(
              100.0 * sizes[k] / first_party_total, 2)}
         for k in modules),
        key=lambda m: (-m["bytes"], m["path"]))
    largest = per_module[0]

    warnings = [{"path": m["path"], "bytes": m["bytes"],
                 "over_by_bytes": m["bytes"] - MAX_SINGLE_MODULE_BYTES}
                for m in per_module if m["bytes"] > MAX_SINGLE_MODULE_BYTES]

    shell_bytes = len(raw)
    inline_exec = [s for s in scripts
                   if not s["external"] and s["kind"] != "importmap"]
    app_text = A.app_text()

    report = {
        "report": "acs.bundle/2",
        "status": (
            "F-09 IMPLEMENTED — MEASUREMENT ONLY. public/index.html is a %d "
            "byte shell and every byte of application JavaScript (%d bytes) "
            "lives in %d files under public/app/. This file records where the "
            "bytes are; it does NOT prove the application still runs. Runtime "
            "behaviour is the browser tests' job, not this tool's."
            % (shell_bytes, first_party_total, len(modules))),
        "what_this_is": (
            "A measurement of the frontend that is actually shipped today: the "
            "index shell, every first-party module under public/app/, the "
            "stylesheet and the boot scripts. It does NOT modify anything and "
            "must not be read as evidence that the application works — only "
            "that the bytes are where this report says they are. Its second "
            "job is anti-gaming: each module's share of total first-party "
            "JavaScript is reported, so a 'split' that leaves one file holding "
            "most of the code cannot hide behind a file count."),
        "deterministic": True,
        "determinism_note": (
            "No timestamp and no absolute path is written. gzip uses mtime=0. "
            "Two consecutive runs produce byte-identical output; "
            "tests/remediation/test_bundle_report.py asserts exactly that."),

        "shell": {
            "path": PAGE_REL,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "raw_bytes": shell_bytes,
            "gzip_bytes": gzip_bytes(page),
            "gzip_level": 9,
            "brotli_bytes": br,
            "brotli_reason": br_reason,
            "characters": len(page),
            "lines": page.count("\n") + 1,
            "script_element_count": len(scripts),
            "external_script_count": len([s for s in scripts if s["external"]]),
            "inline_executable_script_count": len(inline_exec),
            "inline_importmap_bytes": sum(s["inline_body_bytes"] for s in scripts
                                          if s["kind"] == "importmap"),
            "style_element_count": len(styles),
            "inline_style_attribute_count": len(
                re.findall(r'\sstyle\s*=\s*"', page)),
            "scripts": scripts,
            "note": ("inline_executable_script_count, style_element_count and "
                     "inline_style_attribute_count are all 0 by design after "
                     "F-11 — that is exactly what lets the CSP drop "
                     "'unsafe-inline' from script-src and style-src. The one "
                     "remaining inline element is the import map, allowed by "
                     "the sha256 pinned in netlify.toml."),
        },

        "javascript": {
            "first_party_total_bytes": first_party_total,
            "first_party_module_count": len(modules),
            "core_initial_bytes": core_bytes,
            "core_initial_module_count": len(eager),
            "core_initial_note": (
                "core = public/app/main.js plus everything it reaches through "
                "static imports; all of it is parsed and evaluated on first "
                "load. The five boot scripts are loaded on first paint too, "
                "but they are classic <script src> elements outside the module "
                "graph, so they are counted separately."),
            "boot_bytes": boot_bytes,
            "boot_script_count": len(boot),
            "boot_scripts": [{"path": "public/app/" + k, "bytes": sizes[k]}
                             for k in boot],
            "initial_javascript_bytes": core_bytes + boot_bytes,
            "lazy_bytes": sum(sizes[k] for k in lazy),
            "lazy_module_count": len(lazy),
            "lazy_modules": ["public/app/" + k for k in lazy],
            "lazy_note": (
                "ZERO first-party JavaScript is code-split behind a dynamic "
                "import today, and that is reported as 0 rather than dressed "
                "up. %d dynamic import() call(s) do exist in the modules, but "
                "every one targets a vendored library specifier "
                "(three/addons/*, /vendor/pdfjs@*) — %d of them are "
                "first-party — so none defers first-party bytes. Route-level "
                "or panel-level lazy loading of first-party code is NOT "
                "IMPLEMENTED." % (len(dyn), len(dyn_first_party))),
            "dynamic_imports": dyn,
            "dynamic_import_count": len(dyn),
            "first_party_dynamic_import_count": len(dyn_first_party),
            "modules": per_module,
            "largest_module": largest,
            "largest_module_pct_of_first_party_js":
                largest["pct_of_first_party_js"],
        },

        "css": {
            "path": CSS_REL,
            "raw_bytes": b(css),
            "gzip_bytes": gzip_bytes(css),
            "note": ("this file is the former inline <style> block plus the "
                     "generated .acs-u-NN utility classes that replaced every "
                     "style=\"…\" attribute in the markup."),
        },

        "generated_blocks": {
            "js_pairs_in_modules": len(JS_BEGIN.findall(app_text)),
            "css_pairs_in_stylesheet": len(JS_BEGIN.findall(css)),
            "dom_pairs_in_shell": len(DOM_BEGIN.findall(page)),
            "expected": {"js_pairs_in_modules": 10,
                         "css_pairs_in_stylesheet": 6,
                         "dom_pairs_in_shell": 6},
            "note": ("the generated markers survived the split intact: the JS "
                     "pairs moved into public/app/generated/*.js, the CSS "
                     "pairs into public/app/styles/app.css, and the DOM pairs "
                     "stayed in the shell, where markup belongs."),
        },

        "vendor": vendor_report(),

        "budget": {
            "target": (
                "The deployed index.html is an index SHELL — markup, "
                "<link rel=stylesheet>, five classic boot scripts and "
                "<script type=module src=/app/main.js> — and every line of "
                "application logic lives in cacheable files under public/app/."),
            "index_shell_budget_bytes": SHELL_BUDGET_BYTES,
            "index_shell_preferred_bytes": SHELL_PREFERRED_BYTES,
            "max_single_module_budget_bytes": MAX_SINGLE_MODULE_BYTES,
            "current_index_bytes": shell_bytes,
            "headroom_bytes": SHELL_BUDGET_BYTES - shell_bytes,
            "preferred_headroom_bytes": SHELL_PREFERRED_BYTES - shell_bytes,
            "ratio_of_budget_used": round(
                float(shell_bytes) / SHELL_BUDGET_BYTES, 4),
            "budget_met": shell_bytes <= SHELL_BUDGET_BYTES,
            "preferred_met": shell_bytes <= SHELL_PREFERRED_BYTES,
            "largest_module_bytes": largest["bytes"],
            "largest_module_headroom_bytes":
                MAX_SINGLE_MODULE_BYTES - largest["bytes"],
            "budget_note": (
                "index_shell_budget_bytes is the same constant as MAX_BYTES in "
                "tools/check_index_guard.py, which fails the build above it. "
                "budget_met and preferred_met are COMPUTED from the measured "
                "size here, never asserted."),
        },

        "module_size_warnings": warnings,
        "module_size_warning_threshold_bytes": MAX_SINGLE_MODULE_BYTES,
        "module_size_warning_note": (
            "any first-party module above the threshold is listed here AND "
            "fails tools/check_index_guard.py unless it is written into that "
            "tool's OVERSIZE_ALLOWLIST with a stated reason. The list is empty "
            "today."),

        "not_measured_here": [
            "whether the split application still boots and renders — that "
            "needs a browser with public/vendor populated: NOT VERIFIED — "
            "EXTERNAL ENVIRONMENT REQUIRED",
            "the HTTP/2 request overhead of serving many files instead of one, "
            "and the cache-hit benefit of doing so: NOT VERIFIED — EXTERNAL "
            "ENVIRONMENT REQUIRED",
            "production transfer size over brotli — no brotli module here",
            "vendored library sizes — public/vendor is empty in this sandbox",
        ],
    }
    return report


def main():
    rep = build()
    text = json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if "--stdout" in sys.argv:
        sys.stdout.write(text)
        return 0
    out = os.path.join(ROOT, OUT_REL)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    s, j, bg = rep["shell"], rep["javascript"], rep["budget"]
    print("wrote %s" % OUT_REL)
    print("  index shell         : %d B raw, %d B gzip (brotli %s)"
          % (s["raw_bytes"], s["gzip_bytes"], s["brotli_bytes"]))
    print("                        %d inline executable script(s), %d <style> "
          "block(s), %d style= attribute(s)"
          % (s["inline_executable_script_count"], s["style_element_count"],
             s["inline_style_attribute_count"]))
    print("  first-party JS      : %d B in %d modules"
          % (j["first_party_total_bytes"], j["first_party_module_count"]))
    print("  core initial JS     : %d B in %d modules  (+ %d B in %d boot "
          "scripts = %d B on first load)"
          % (j["core_initial_bytes"], j["core_initial_module_count"],
             j["boot_bytes"], j["boot_script_count"],
             j["initial_javascript_bytes"]))
    print("  lazy first-party JS : %d B in %d modules — honestly zero"
          % (j["lazy_bytes"], j["lazy_module_count"]))
    print("  css                 : %d B raw, %d B gzip"
          % (rep["css"]["raw_bytes"], rep["css"]["gzip_bytes"]))
    print("  largest module      : %s — %d B (%.2f%% of first-party JS)"
          % (j["largest_module"]["path"], j["largest_module"]["bytes"],
             j["largest_module_pct_of_first_party_js"]))
    print("  module warnings     : %d over %d B"
          % (len(rep["module_size_warnings"]),
             rep["module_size_warning_threshold_bytes"]))
    print("  budget              : shell %d B of %d B (%.1f%% used, preferred "
          "%d B) · budget_met=%s preferred_met=%s"
          % (bg["current_index_bytes"], bg["index_shell_budget_bytes"],
             100.0 * bg["ratio_of_budget_used"],
             bg["index_shell_preferred_bytes"], bg["budget_met"],
             bg["preferred_met"]))
    print("  STATUS              : %s"
          % rep["status"].split(".")[0].strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
