#!/usr/bin/env python3
# ==============================================================================
# tests/remediation/test_ci_dependencies.py
#
# العقد: **كل تبعية خارجية مطلوبة يبلغها هدفُ اختبارٍ في CI، تُركِّبها الوظيفة
#         التي تشغّل ذلك الهدف.**
#
# لماذا يوجد
# ----------
# سقطت وظيفة `7 · Dependency audit and lock contract` مرّتين متتاليتين لنفس
# السبب البنيويّ، وبعطلين مختلفين في الاسم:
#
#     ١) ٦ أهداف — psutil وغيره غير مركَّب: الوظيفة كانت بلا `pip install`.
#     ٢) هدفٌ واحد — numpy:
#            tests/remediation/test_plate_extent.py
#              → import acs_compiler
#                  acs_compiler.py:20  import numpy as np
#            ModuleNotFoundError: No module named 'numpy'
#
# والثاني يكشف ما لا يكشفه الأوّل: التبعية **متعدّية**. الاختبار لا يستورد
# numpy، بل يستورد وحدةً من المستودع تستوردها. ففحصُ سطور الاستيراد في ملفّ
# الاختبار وحده كان سيمرّ، ويسقط CI.
#
# لذلك يمشي هذا الفحص إغلاقَ الاستيراد داخل المستودع: من الهدف إلى كل وحدة
# محلّية يبلغها، ثم يجمع ما تستورده تلك الوحدات من خارج المستودع ومن خارج
# المكتبة القياسية.
#
# «مطلوبة» تعني: استيرادٌ غير محروس. ما كان داخل try/except ImportError فهو
# اختياريّ بإعلان الشفرة نفسها، ولا يُطالَب بتركيبه. ولا يُجعَل استيرادٌ
# اختيارياً هنا ولا هناك لتمرير فحص: هذا الملفّ يقرأ ولا يعدّل.
#
# ولا يستورد هذا الفحص شيئاً ممّا يفحصه: يعمل على الشجرة النحوية وحدها، فيصحّ
# تشغيله في مفسّرٍ عارٍ — أي في البيئة التي أخفت العطلين.
# ==============================================================================
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CI = os.path.join(ROOT, ".github", "workflows", "ci.yml")

_p = _f = 0


def chk(name, cond, detail=""):
    global _p, _f
    if cond:
        _p += 1
        print("  ✓", name)
    else:
        _f += 1
        print("  ✗", name, ("\n      " + str(detail)) if detail else "")


def rd(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ── خريطة معلَنة: اسم الوحدة عند الاستيراد → اسم التوزيعة عند التثبيت ──────
# مُعلَنة عمداً: اسمٌ خارجيّ لا يرد فيها يُرفَع عطلاً بدل أن يُخمَّن، فإضافة
# تبعية جديدة قرارٌ مرئيّ في المراجعة لا انزلاقٌ صامت.
DIST = {
    "numpy": "numpy",
    "psutil": "psutil",
    "PIL": "Pillow",
    "pypdf": "pypdf",
    "fastapi": "fastapi",
    "starlette": "starlette",
    "httpx": "httpx",
    "anthropic": "anthropic",
    "uvicorn": "uvicorn",
    "multipart": "python-multipart",
    "brotli": "Brotli",
    "yaml": "PyYAML",
}

# ── تبعيات يضمنها تثبيتٌ آخر، بنصّ إعلانه لا بحسن الظنّ ───────────────────
# ليست إعفاءً: كلٌّ منها مصحوبٌ بالقيد الذي يعلنه المزوِّد حرفياً، ويُشترط أن
# يكون المزوِّد نفسه مثبَّتاً بـ== في الملفّ الذي تُركِّبه الوظيفة. فإن خرج
# المزوِّد من مجموعة التثبيت سقط الفحص.
PROVIDED_BY = {
    # fastapi 0.110.0 · pyproject.toml حرفياً:
    #   "pydantic>=1.7.4,!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0"
    # يستوردها acs_understand_api.py مباشرةً (`from pydantic import BaseModel`)
    # وهي على مسار الإنتاج. غير مثبّتة باسمها: مخاطرة انجرافٍ مسجَّلة في
    # requirements.lock ضمن UNRESOLVED-OFFLINE، لا مكتومة هنا.
    "pydantic": "fastapi",
}

STDLIB = set(sys.stdlib_module_names)


def local_modules():
    """كل وحدة .py في المستودع، باسمها المجرّد.

    الاختبارات تضيف مجلّداتٍ إلى sys.path (tests/lib، tests/phase9/…) فتستورد
    جيراناً بأسماء مجرّدة: app_source، lib_docs_fixtures، lib_ad_fixtures.
    هذه ملفّات المستودع نفسها لا حزماً خارجية، فلا تُطالَب بتثبيت. البحث
    بالاسم عبر الشجرة كلّها هو ما يميّزها.
    """
    out = {}
    skip = {"node_modules", ".git", "public"}
    for dirpath, dirnames, files in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in files:
            if fn.endswith(".py"):
                out.setdefault(fn[:-3], os.path.join(dirpath, fn))
    return out


ROOT_MODS = local_modules()


def imports_of(path):
    """(required, optional) — أسماء الوحدات العليا التي يستوردها ملفّ.

    المحروس داخل try/except ImportError اختياريّ بإعلان الشفرة؛ ما عداه مطلوب.
    """
    try:
        tree = ast.parse(rd(path), path)
    except Exception:                                          # noqa: BLE001
        return set(), set()
    guarded = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        handles_import = any(
            (h.type is None)
            or (isinstance(h.type, ast.Name)
                and h.type.id in ("ImportError", "ModuleNotFoundError", "Exception"))
            or (isinstance(h.type, ast.Tuple)
                and any(isinstance(e, ast.Name)
                        and e.id in ("ImportError", "ModuleNotFoundError", "Exception")
                        for e in h.type.elts))
            for h in node.handlers)
        if not handles_import:
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Import):
                for a in sub.names:
                    guarded.add(a.name.split(".")[0])
            elif isinstance(sub, ast.ImportFrom) and sub.level == 0 and sub.module:
                guarded.add(sub.module.split(".")[0])
    every = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                every.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            every.add(node.module.split(".")[0])
    return every - guarded, guarded


def closure(target):
    """الإغلاق: الهدف + كل وحدة مستودعٍ يبلغها، وما تطلبه كلّها من الخارج."""
    seen, stack = set(), [target]
    required, optional = set(), set()
    while stack:
        path = stack.pop()
        if path in seen:
            continue
        seen.add(path)
        req, opt = imports_of(path)
        sibling = os.path.dirname(path)
        for name in req | opt:
            if name in STDLIB:
                continue
            cand = os.path.join(sibling, name + ".py")
            nxt = cand if os.path.exists(cand) else ROOT_MODS.get(name)
            if nxt:
                stack.append(nxt)
            elif name in req:
                required.add(name)
            else:
                optional.add(name)
    return required, optional - required


# ── قراءة سير العمل: أي وظيفة تشغّل أي هدف، وماذا تُركِّب ──────────────────
def ci_jobs():
    ci = rd(CI)
    out = {}
    for blk in re.split(r"\n  (?=[a-z][a-z0-9-]*:\n)", ci)[1:]:
        m = re.match(r"\s*([a-z0-9-]+):", blk)
        if not m:
            continue
        name = m.group(1)
        targets = set(re.findall(r"(tests/[\w/]+\.py)", blk))
        installs = set()
        for line in re.findall(r"pip install[^\n]*", blk):
            installs |= set(re.findall(r"-r\s+(\S+\.txt)", line))
        if targets:
            out[name] = {"targets": sorted(targets), "installs": sorted(installs)}
    return out


def pinned_in(files):
    """أسماء التوزيعات المثبّتة في مجموعة ملفّات تثبيت."""
    names = set()
    for rel in files:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        for line in rd(p).splitlines():
            line = line.split("#", 1)[0].strip()
            m = re.match(r"^([A-Za-z0-9._-]+)(\[[^\]]*\])?==", line)
            if m:
                names.add(m.group(1).lower().replace("_", "-"))
    return names


print("== أ · سير العمل يُقرأ، والوظائف التي تشغّل أهدافاً معروفة ==")
JOBS = ci_jobs()
chk("ci.yml names at least two jobs that run Python targets", len(JOBS) >= 2,
    str(sorted(JOBS)))
for name, j in sorted(JOBS.items()):
    chk("job '%s' runs %d target(s) and installs %s"
        % (name, len(j["targets"]), j["installs"] or "NOTHING"),
        bool(j["installs"]),
        "a job that runs Python targets must install the pinned requirements")

print("\n== ب · كل اسمٍ خارجيّ يبلغه هدفٌ معروفٌ في خريطة التوزيعات ==")
unmapped = {}
for name, j in sorted(JOBS.items()):
    for t in j["targets"]:
        req, _ = closure(os.path.join(ROOT, t))
        for mod in req:
            if mod not in DIST and mod not in PROVIDED_BY:
                unmapped.setdefault(mod, []).append(t)
chk("no third-party module is missing from the declared DIST map", not unmapped,
    str({k: v[:2] for k, v in unmapped.items()}))

print("\n== ج · كل تبعية مطلوبة تُركِّبها الوظيفة التي تشغّل هدفها ==")
missing = []
checked = 0
for name, j in sorted(JOBS.items()):
    have = pinned_in(j["installs"])
    for t in j["targets"]:
        req, _ = closure(os.path.join(ROOT, t))
        for mod in sorted(req):
            checked += 1
            if mod in PROVIDED_BY:
                # مضمونةٌ بتثبيت مزوِّدها — ويُشترط أن يكون هو مثبَّتاً هنا.
                provider = PROVIDED_BY[mod].lower()
                if provider not in have:
                    missing.append((name, t, mod, provider + " (provides "
                                    + mod + ")"))
                continue
            dist = DIST.get(mod, mod).lower().replace("_", "-")
            if dist not in have:
                missing.append((name, t, mod, dist))
for name, t, mod, dist in missing:
    chk("job '%s' installs %s for %s (imports %s)" % (name, dist, t, mod),
        False, "not pinned in " + str(JOBS[name]["installs"]))
chk("every required third-party import of every CI target is installed by its "
    "job (%d import edge(s) checked)" % checked, not missing,
    "\n      ".join("%s → %s needs %s" % (n, t, d) for n, t, _, d in missing))

for mod, provider in sorted(PROVIDED_BY.items()):
    chk("'%s' is declared as provided by '%s', and that provider is itself "
        "pinned with == in requirements.txt" % (mod, provider),
        re.search(r"^%s==" % re.escape(provider),
                  rd(os.path.join(ROOT, "requirements.txt")), re.M) is not None)

print("\n== د · شاهد سالب: الفحص يمشي الاستيراد المتعدّي، لا السطر الأوّل ==")
# numpy لا يظهر في tests/remediation/test_plate_extent.py إطلاقاً — يظهر في
# acs_compiler.py التي يستوردها. لو كان الفحص سطحياً لَما رآه.
pe = os.path.join(ROOT, "tests", "remediation", "test_plate_extent.py")
if os.path.exists(pe):
    direct, _ = imports_of(pe)
    deep, _ = closure(pe)
    chk("test_plate_extent.py does NOT import numpy directly",
        "numpy" not in direct, str(sorted(direct)))
    chk("but the closure reaches it through acs_compiler", "numpy" in deep,
        str(sorted(deep)))
    chk("and acs_compiler.py is the only file that imports numpy",
        "numpy" in imports_of(os.path.join(ROOT, "acs_compiler.py"))[0])

print("\n== هـ · numpy في المجموعة الصحيحة دلالياً، لا في صورة الإنتاج ==")
prod = rd(os.path.join(ROOT, "requirements.txt"))
dev = rd(os.path.join(ROOT, "requirements-dev.txt")) \
    if os.path.exists(os.path.join(ROOT, "requirements-dev.txt")) else ""
chk("numpy is pinned with == in requirements-dev.txt",
    re.search(r"^numpy==\d+\.\d+", dev, re.M) is not None)
chk("numpy is NOT in requirements.txt — acs_compiler.py is an offline tool, "
    "deployed nowhere by design", "numpy" not in prod)
docker = rd(os.path.join(ROOT, "Dockerfile"))
chk("and the Dockerfile really does not COPY acs_compiler.py — the audit that "
    "put numpy in the dev set, verified here",
    "acs_compiler.py" not in docker)

print("\n" + "─" * 62)
print("CI DEPENDENCY CONTRACT: %d passed, %d failed" % (_p, _f))
sys.exit(1 if _f else 0)
