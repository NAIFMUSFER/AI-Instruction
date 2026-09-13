#!/usr/bin/env python3
# ==============================================================================
# tests/remediation/test_ci_dependencies.py
#
# Contract: every required third-party dependency reachable from a Python target
# run by CI must be installed by that CI job. Repository-local modules,
# including PEP 420 namespace packages such as ``tools.*``, are traversed as
# local source and must never be mistaken for PyPI distributions.
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


# import-name -> install-distribution
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

# Dependencies intentionally supplied by another exact-pinned distribution.
PROVIDED_BY = {
    "pydantic": "fastapi",
}

STDLIB = set(sys.stdlib_module_names)
_SKIP_DIRS = {"node_modules", ".git", "public", "__pycache__"}


def local_modules():
    """Index bare-name repository modules used by tests that edit ``sys.path``."""
    out = {}
    for dirpath, dirnames, files in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in files:
            if fn.endswith(".py"):
                out.setdefault(fn[:-3], os.path.join(dirpath, fn))
    return out


ROOT_MODS = local_modules()


def _package_init_paths(parts):
    """Return existing ``__init__.py`` files executed before a dotted module."""
    paths = []
    cur = ROOT
    for part in parts:
        cur = os.path.join(cur, part)
        init = os.path.join(cur, "__init__.py")
        if os.path.isfile(init):
            paths.append(init)
    return paths


def resolve_local(name, sibling):
    """Return ``(is_local, source_paths)`` for one absolute import name.

    The old audit reduced ``from tools.foo import x`` to the bare name
    ``tools`` and then looked only for ``tools.py``. ``tools/`` is a valid
    repository namespace package without ``__init__.py``, so that logic
    misclassified first-party code as a third-party distribution. Resolution
    here follows the repository path before falling back to the historical
    bare-module index.
    """
    if not isinstance(name, str) or not name:
        return False, []

    parts = name.split(".")
    root_name = parts[0]
    if root_name in STDLIB:
        return False, []

    # Exact dotted module/package under the repository root.
    rel = os.path.join(*parts)
    py = os.path.join(ROOT, rel + ".py")
    pkg = os.path.join(ROOT, rel)
    paths = _package_init_paths(parts[:-1])
    if os.path.isfile(py):
        return True, paths + [py]
    init = os.path.join(pkg, "__init__.py")
    if os.path.isfile(init):
        return True, paths + [init]
    if os.path.isdir(pkg):
        # PEP 420 namespace package. It is local even without __init__.py.
        return True, paths

    # Historical flat/sibling imports used by test harnesses that prepend a
    # directory to sys.path.
    if len(parts) == 1:
        cand = os.path.join(sibling, name + ".py")
        if os.path.isfile(cand):
            return True, [cand]
        nxt = ROOT_MODS.get(name)
        if nxt:
            return True, [nxt]

    return False, []


def _names_for_import_node(node, path):
    """Absolute import names represented by one AST import node.

    For ``from pkg import child`` we also traverse ``pkg.child`` when that is
    an actual repository module/package. If ``child`` is merely an attribute,
    the base module remains the only local path and no external dependency is
    fabricated.
    """
    sibling = os.path.dirname(path)
    names = set()
    if isinstance(node, ast.Import):
        names.update(a.name for a in node.names)
    elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        names.add(node.module)
        for alias in node.names:
            if alias.name == "*":
                continue
            candidate = node.module + "." + alias.name
            local, _ = resolve_local(candidate, sibling)
            if local:
                names.add(candidate)
    return names


def imports_of(path):
    """Return ``(required, optional)`` absolute module names imported by path."""
    try:
        tree = ast.parse(rd(path), path)
    except Exception:  # noqa: BLE001
        return set(), set()

    guarded = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        handles_import = any(
            (h.type is None)
            or (
                isinstance(h.type, ast.Name)
                and h.type.id in ("ImportError", "ModuleNotFoundError", "Exception")
            )
            or (
                isinstance(h.type, ast.Tuple)
                and any(
                    isinstance(e, ast.Name)
                    and e.id in ("ImportError", "ModuleNotFoundError", "Exception")
                    for e in h.type.elts
                )
            )
            for h in node.handlers
        )
        if not handles_import:
            continue
        for sub in ast.walk(node):
            if isinstance(sub, (ast.Import, ast.ImportFrom)):
                guarded |= _names_for_import_node(sub, path)

    every = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            every |= _names_for_import_node(node, path)
    return every - guarded, guarded


def closure(target):
    """Traverse repository imports and return required/optional external roots."""
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
            root_name = name.split(".", 1)[0]
            if root_name in STDLIB:
                continue
            is_local, paths = resolve_local(name, sibling)
            if is_local:
                for nxt in paths:
                    if nxt not in seen:
                        stack.append(nxt)
                continue
            if name in req:
                required.add(root_name)
            else:
                optional.add(root_name)
    return required, optional - required


def ci_jobs():
    """Read Python targets and requirement files installed by each CI job."""
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


print("== أ · CI jobs install pinned dependency sets ==")
JOBS = ci_jobs()
chk("ci.yml names at least two jobs that run Python targets", len(JOBS) >= 2,
    str(sorted(JOBS)))
for name, job in sorted(JOBS.items()):
    chk(
        "job '%s' runs %d target(s) and installs %s"
        % (name, len(job["targets"]), job["installs"] or "NOTHING"),
        bool(job["installs"]),
        "a job that runs Python targets must install pinned requirements",
    )

print("\n== ب · repository namespace packages stay first-party ==")
tools_app_source = os.path.join(ROOT, "tools", "app_source.py")
local_tools, tool_paths = resolve_local("tools.app_source", ROOT)
chk("tools/app_source.py exists as first-party evidence",
    os.path.isfile(tools_app_source), tools_app_source)
chk("dotted tools.app_source resolves locally without a PyPI mapping",
    local_tools and tools_app_source in tool_paths, str(tool_paths))
local_tools_root, _ = resolve_local("tools", ROOT)
chk("bare tools resolves as a local PEP 420 namespace package",
    local_tools_root)
fake_local, _ = resolve_local("definitely_not_an_acs_repo_module.child", ROOT)
chk("an unknown dotted name is still external", not fake_local)

for rel in (
    "tests/remediation/test_model_diagnostics.py",
    "tests/phase9_2/test_backend_contract.py",
):
    path = os.path.join(ROOT, rel)
    if os.path.exists(path):
        deep, _ = closure(path)
        chk("%s does not misclassify local tools as third-party" % rel,
            "tools" not in deep, str(sorted(deep)))

print("\n== ج · every external import is declared and installed ==")
unmapped = {}
missing = []
checked = 0
for job_name, job in sorted(JOBS.items()):
    have = pinned_in(job["installs"])
    for target in job["targets"]:
        req, _ = closure(os.path.join(ROOT, target))
        for mod in sorted(req):
            checked += 1
            if mod not in DIST and mod not in PROVIDED_BY:
                unmapped.setdefault(mod, []).append(target)
                continue
            if mod in PROVIDED_BY:
                provider = PROVIDED_BY[mod].lower().replace("_", "-")
                if provider not in have:
                    missing.append((job_name, target, mod, provider + " (provides " + mod + ")"))
                continue
            dist = DIST[mod].lower().replace("_", "-")
            if dist not in have:
                missing.append((job_name, target, mod, dist))

chk("no third-party module is missing from the declared DIST map",
    not unmapped, str({k: v[:2] for k, v in unmapped.items()}))
for job_name, target, mod, dist in missing:
    chk(
        "job '%s' installs %s for %s (imports %s)"
        % (job_name, dist, target, mod),
        False,
        "not pinned in " + str(JOBS[job_name]["installs"]),
    )
chk(
    "every required third-party import of every CI target is installed by its "
    "job (%d import edge(s) checked)" % checked,
    not missing,
    "\n      ".join(
        "%s → %s needs %s" % (name, target, dist)
        for name, target, _, dist in missing
    ),
)

for mod, provider in sorted(PROVIDED_BY.items()):
    chk(
        "'%s' is declared as provided by '%s', and that provider is exact-pinned"
        % (mod, provider),
        re.search(
            r"^%s==" % re.escape(provider),
            rd(os.path.join(ROOT, "requirements.txt")),
            re.M,
        )
        is not None,
    )

print("\n== د · negative witness: transitive imports are still traversed ==")
plate = os.path.join(ROOT, "tests", "remediation", "test_plate_extent.py")
if os.path.exists(plate):
    direct, _ = imports_of(plate)
    deep, _ = closure(plate)
    chk("test_plate_extent.py does NOT import numpy directly",
        all(name.split(".", 1)[0] != "numpy" for name in direct),
        str(sorted(direct)))
    chk("but the closure reaches numpy through acs_compiler",
        "numpy" in deep, str(sorted(deep)))
    compiler = os.path.join(ROOT, "acs_compiler.py")
    compiler_imports, _ = imports_of(compiler)
    chk("acs_compiler.py imports numpy",
        any(name.split(".", 1)[0] == "numpy" for name in compiler_imports))

print("\n== هـ · numpy remains dev-only because the compiler is offline ==")
prod = rd(os.path.join(ROOT, "requirements.txt"))
dev_path = os.path.join(ROOT, "requirements-dev.txt")
dev = rd(dev_path) if os.path.exists(dev_path) else ""
chk("numpy is exact-pinned in requirements-dev.txt",
    re.search(r"^numpy==\d+\.\d+", dev, re.M) is not None)
chk("numpy is NOT in requirements.txt",
    re.search(r"^numpy==", prod, re.M) is None)
docker = rd(os.path.join(ROOT, "Dockerfile"))
chk("Dockerfile does not COPY acs_compiler.py",
    "acs_compiler.py" not in docker)

print("\n" + "─" * 62)
print("CI DEPENDENCY CONTRACT: %d passed, %d failed" % (_p, _f))
sys.exit(1 if _f else 0)
