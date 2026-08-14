# -*- coding: utf-8 -*-
"""F-09 — قياس الصفحة المشحونة فعلاً. قياس فقط، بلا أي إعادة هيكلة.

    python3 tools/bundle_report.py            # يكتب tests/performance/bundle_report.json
    python3 tools/bundle_report.py --stdout   # يطبع ولا يكتب

لماذا هذا الملفّ موجود: F-09 (تفكيك public/index.html إلى public/app/*.js) لم
يُنفَّذ. الادّعاء بأنه نُفّذ أسهل من تنفيذه، فيُوضَع أوّلاً رقمٌ لا يقبل الادّعاء:
حجم الصفحة الحقيقي، موزّعاً على كل كتلة فيها، مقارَناً بميزانية معلنة. أي
"تحسين" لاحق يُقاس بهذا الملفّ نفسه أو لا يُقاس.

الحتمية شرط: لا طابع زمني ولا مسار مطلق في المخرَج، وgzip يُضغط بـmtime=0.
تشغيلان متتاليان يعطيان بايتاً ببايت المخرَج نفسه — وهذا ما يفحصه
tests/remediation/test_bundle_report.py.

ما لا يُقاس لا يُقدَّر: brotli يُبلَّغ عنه فقط إذا كانت الوحدة مستوردة فعلاً،
وإلّا null مع سبب. مجلّد public/vendor فارغ في هذا الصندوق، فأحجام المكتبات
المعبَّأة null مع سبب — لا تقدير، ولا رقم من الذاكرة.
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
PAGE_REL = "public/index.html"
OUT_REL = "tests/performance/bundle_report.json"

# ميزانية القشرة بعد F-09. الرقم ليس اعتباطياً: قشرة HTML لا تحمل تطبيقاً، بل
# ترويسة + عنصر canvas + وسم <link> + وسم <script type="module" src>. 150 KB
# سقف كريم لذلك حتى مع كتل DOM المولَّدة كاملةً في الصفحة.
SHELL_BUDGET_BYTES = 150 * 1024
# أكبر ملفّ JS واحد بعد التفكيك: تقسيم لا ينتج عنه قطعة أصغر من ذلك ليس تقسيماً.
MAX_SINGLE_MODULE_BYTES = 300 * 1024


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
    """brotli إن كان مستورَداً فعلاً. غير ذلك: None وسبب — لا تقدير أبداً."""
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


# ------------------------------------------------------------- العناصر ------
def script_and_style_elements(page):
    """مسح تسلسلي — لا regex عام.

    السبب: النصّ يحوي آلاف السلاسل التي تبدأ بـ`<script` داخل مواصفات JSON
    (قوائم الوسوم الممنوعة). أي regex عام يعدّها عناصر. المسح التسلسلي يقفز من
    نهاية كل عنصر إلى ما بعده، فلا يرى ما بداخله. `</script>` كاملةً لا تظهر
    داخل أي سلسلة في هذا الملفّ (السلاسل تكتب `</script` بلا `>`).
    """
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
        scripts.append({
            "index": len(scripts) + 1,
            "line": page.count("\n", 0, a) + 1,
            "kind": kind,
            "attributes": attrs,
            "body_bytes": b(body),
            "element_bytes": b(page[a:e + 9]),
            "body_start": ge + 1,
            "body_end": e,
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
        styles.append({
            "index": len(styles) + 1,
            "line": page.count("\n", 0, a) + 1,
            "body_bytes": b(page[ge + 1:e]),
            "element_bytes": b(page[a:e + 8]),
            "body_start": ge + 1,
            "body_end": e,
        })
        i = e + 8
    return scripts, styles


# ---------------------------------------------------- الكتل المولَّدة --------
JS_BEGIN = re.compile(r"/\* ===== ACS (?!END)([A-Z0-9][A-Z0-9 .]*?)"
                      r"(?: \(([^)]*)\))? ===== \*/")
DOM_BEGIN = re.compile(r"<!-- ===== ACS (?!END)([A-Z0-9][A-Z0-9 .]*?)"
                       r"(?: \(([^)]*)\))? ===== -->")


def generated_blocks(page, style_ranges):
    """كل كتلة مولَّدة بعلامتَي بداية ونهاية، مصنَّفة CSS / JS / DOM.

    التصنيف ليس بالاسم بل بالموقع: ما يقع داخل جسم <style> فهو CSS، وما كان
    تعليق HTML فهو DOM، وما بقي فهو JS. هكذا لا يخدع اسمٌ التصنيف.
    """
    out = []
    for rx, comment_kind, end_fmt in (
            (JS_BEGIN, "js", "/* ===== END ACS %s ===== */"),
            (DOM_BEGIN, "dom", "<!-- ===== END ACS %s ===== -->")):
        for m in rx.finditer(page):
            name = m.group(1).strip()
            end_marker = end_fmt % name
            e = page.find(end_marker, m.end())
            if e < 0:
                out.append({"name": name, "kind": "UNPAIRED", "error":
                            "no end marker %r" % end_marker})
                continue
            start, stop = m.start(), e + len(end_marker)
            kind = comment_kind
            if comment_kind == "js" and any(s <= start < t for s, t in style_ranges):
                kind = "css"
            out.append({
                "name": name,
                "kind": kind,
                "generator": (m.group(2) or "").replace("generated by ", "")
                             .replace("generated", "").strip() or None,
                "begin_line": page.count("\n", 0, start) + 1,
                "end_line": page.count("\n", 0, stop) + 1,
                "bytes": b(page[start:stop]),
                "start": start,
                "stop": stop,
            })
    out.sort(key=lambda x: x.get("start", 0))
    return out


def vendor_report():
    vdir = os.path.join(ROOT, "public", "vendor")
    if not os.path.isdir(vdir):
        return {"present": False, "total_bytes": None, "files": None,
                "reason": "public/vendor does not exist in this checkout; "
                          "Netlify populates it at build time via "
                          "tools/netlify-build.sh. NOT MEASURED — no estimate "
                          "is substituted."}
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
                          "(no network, tools/vendor.sh has never run). The "
                          "21 vendored runtime assets — three@0.160.0 + addons "
                          "+ es-module-shims@1.8.2 + pdfjs@4.0.379 — are NOT "
                          "MEASURED here. NOT VERIFIED — EXTERNAL ENVIRONMENT "
                          "REQUIRED."}
    return {"present": True, "empty": False,
            "total_bytes": sum(f["bytes"] for f in files),
            "file_count": len(files), "files": files, "reason": None}


def build():
    page = read(PAGE_REL)
    raw = page.encode("utf-8")
    scripts, styles = script_and_style_elements(page)
    style_ranges = [(s["body_start"], s["body_end"]) for s in styles]
    blocks = generated_blocks(page, style_ranges)

    by_kind = {"js": [], "css": [], "dom": [], "UNPAIRED": []}
    for blk in blocks:
        by_kind.setdefault(blk["kind"], []).append(blk)

    gen_total = sum(x["bytes"] for x in blocks if "bytes" in x)
    module_scripts = [s for s in scripts if s["kind"] == "module"]
    module_bytes = sum(s["body_bytes"] for s in module_scripts)
    classic_bytes = sum(s["body_bytes"] for s in scripts if s["kind"] == "classic")
    importmap_bytes = sum(s["body_bytes"] for s in scripts if s["kind"] == "importmap")
    style_bytes = sum(s["body_bytes"] for s in styles)

    # المولَّد داخل وحدة التطبيق وحدها — يفصل ما يُولَّد عمّا كُتب باليد فيها
    gen_in_module = 0
    for s in module_scripts:
        for blk in blocks:
            if "start" in blk and s["body_start"] <= blk["start"] < s["body_end"]:
                gen_in_module += blk["bytes"]

    br, br_reason = brotli_bytes(page)

    report = {
        "report": "acs.bundle/1",
        "status": "F-09 NOT IMPLEMENTED — measurement only",
        "what_this_is": (
            "A measurement of the page that is actually shipped today. It "
            "does NOT modify the page, does not split it, and must not be "
            "read as evidence that the frontend was modularised. It exists so "
            "that the claim 'F-09 is done' can never be made without a number "
            "moving in this file."),
        "deterministic": True,
        "determinism_note": (
            "No timestamp and no absolute path is written. gzip uses mtime=0. "
            "Two consecutive runs produce byte-identical output; "
            "tests/remediation/test_bundle_report.py asserts exactly that."),
        "source": {
            "path": PAGE_REL,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "characters": len(page),
            "lines": page.count("\n") + 1,
        },
        "compression": {
            "raw_bytes": len(raw),
            "gzip_bytes": gzip_bytes(page),
            "gzip_level": 9,
            "brotli_bytes": br,
            "brotli_reason": br_reason,
            "note": ("gzip is measured with the standard library. brotli is "
                     "reported only when a brotli module is importable; it is "
                     "never estimated. Netlify serves brotli in production, so "
                     "a null here means the production transfer size is "
                     "UNMEASURED in this sandbox, not that brotli is unused."),
        },
        "elements": {
            "script_element_count": len(scripts),
            "style_element_count": len(styles),
            "scripts": [{k: v for k, v in s.items()
                         if k not in ("body_start", "body_end")}
                        for s in scripts],
            "styles": [{k: v for k, v in s.items()
                        if k not in ("body_start", "body_end")}
                       for s in styles],
            "totals": {
                "classic_script_bytes": classic_bytes,
                "importmap_script_bytes": importmap_bytes,
                "module_script_bytes": module_bytes,
                "style_bytes": style_bytes,
            },
        },
        "generated_blocks": {
            "counts": {"js": len(by_kind["js"]), "css": len(by_kind["css"]),
                       "dom": len(by_kind["dom"]),
                       "unpaired": len(by_kind["UNPAIRED"])},
            "expected_counts": {"js": 10, "css": 6, "dom": 6},
            "total_bytes": gen_total,
            "bytes_by_kind": {
                k: sum(x["bytes"] for x in by_kind[k] if "bytes" in x)
                for k in ("js", "css", "dom")},
            "blocks": [{kk: vv for kk, vv in blk.items()
                        if kk not in ("start", "stop")} for blk in blocks],
        },
        "hand_written": {
            "remainder_bytes": len(raw) - gen_total,
            "remainder_pct_of_page": round(
                100.0 * (len(raw) - gen_total) / len(raw), 2),
            "hand_written_inside_application_module_bytes":
                module_bytes - gen_in_module,
            "generated_inside_application_module_bytes": gen_in_module,
            "note": ("`remainder` is everything outside every paired generated "
                     "marker: the markup, the seven inline scripts' "
                     "hand-written parts and the hand-written half of the "
                     "application module. It is the part a regenerate cannot "
                     "rewrite, and therefore the part F-09 must move by hand."),
        },
        "vendor": vendor_report(),
        "budget": {
            "target": (
                "After F-09 the deployed index.html is an index SHELL — markup "
                "plus <link rel=stylesheet> plus <script type=module "
                "src=/app/main.js> — and every line of application logic lives "
                "in cacheable files under public/app/. The shell must be "
                "dramatically smaller than the current >1 MB page."),
            "index_shell_budget_bytes": SHELL_BUDGET_BYTES,
            "max_single_module_budget_bytes": MAX_SINGLE_MODULE_BYTES,
            "current_index_bytes": len(raw),
            "current_delta_bytes": len(raw) - SHELL_BUDGET_BYTES,
            "current_ratio_over_budget": round(
                float(len(raw)) / SHELL_BUDGET_BYTES, 2),
            "largest_single_inline_script_bytes":
                max([s["body_bytes"] for s in scripts]) if scripts else 0,
            "largest_single_delta_bytes":
                (max([s["body_bytes"] for s in scripts]) if scripts else 0)
                - MAX_SINGLE_MODULE_BYTES,
            "budget_met": False,
            "budget_note": (
                "These are TARGETS declared here, not achievements. "
                "budget_met is false and will stay false until F-09 lands. No "
                "runtime performance consequence of the current size is "
                "measured by this tool — see tests/performance/run_perf.js, "
                "which cannot run in this sandbox either."),
        },
        "not_measured_here": [
            "runtime parse/execute cost of the 1.6 MB inline module — needs a "
            "browser with public/vendor populated: NOT VERIFIED — EXTERNAL "
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
    g = rep["generated_blocks"]["counts"]
    print("wrote %s" % OUT_REL)
    print("  page                : %d bytes (gzip %d, brotli %s)"
          % (rep["source"]["bytes"], rep["compression"]["gzip_bytes"],
             rep["compression"]["brotli_bytes"]))
    print("  script elements     : %d  (module %d B, classic %d B, importmap %d B)"
          % (rep["elements"]["script_element_count"],
             rep["elements"]["totals"]["module_script_bytes"],
             rep["elements"]["totals"]["classic_script_bytes"],
             rep["elements"]["totals"]["importmap_script_bytes"]))
    print("  style elements      : %d  (%d B)"
          % (rep["elements"]["style_element_count"],
             rep["elements"]["totals"]["style_bytes"]))
    print("  generated blocks    : js=%d css=%d dom=%d unpaired=%d  (%d B)"
          % (g["js"], g["css"], g["dom"], g["unpaired"],
             rep["generated_blocks"]["total_bytes"]))
    print("  hand-written remain : %d bytes (%.2f%%)"
          % (rep["hand_written"]["remainder_bytes"],
             rep["hand_written"]["remainder_pct_of_page"]))
    print("  budget              : shell %d B, current %d B, delta +%d B (%.2f×)"
          % (SHELL_BUDGET_BYTES, rep["budget"]["current_index_bytes"],
             rep["budget"]["current_delta_bytes"],
             rep["budget"]["current_ratio_over_budget"]))
    print("  STATUS              : %s" % rep["status"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
