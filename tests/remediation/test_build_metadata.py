# -*- coding: utf-8 -*-
"""provenance — أصل البناء: أي نسخة يقيسها التحقّق الإنتاجي؟

يُثبت أن `acs_build_info` يجيب عن سؤال واحد بلا اختراع:

  أ) الشكل: `build_info()` يعيد الحقول الثمانية المعلنة كاملة.
  ب) ترتيب المصادر: البيئة ثمّ الملفّ ثمّ مستودع git المحلّي ثمّ "unknown" —
     كل درجة تُختبَر تشغيلاً لا نصّاً، ولا تُخترَع قيمة عند غياب الجميع.
  ج) لا تسرّب: لا قيمة بشكل مفتاح API، ولا مسار ملفّ مطلق في الردّ.
  د) السلسلة الفارغة لا تُسقِط الإقلاع — هذه الوحدة محصَّنة ضدّ صنف العطل
     `int("")` الذي كان يمنع بدء الخادم.
  هـ) التوصيل الساكن (ast) في acs_understand_api.py: مسار /version موجود،
     و/health يحمل مفتاح build، ولا يذكر أيّهما ANTHROPIC_API_KEY ولا
     ACS_REDIS_URL.
  و) `build_identifier()` سطر قصير للعرض البشري.

ليس pytest — سكربت عادي: python3 tests/remediation/test_build_metadata.py
"""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_build_info as B                                        # noqa: E402

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s%s' % (name, ('  — %s' % detail) if detail else ''))


def rd(rel):
    with open(os.path.join(ROOT, rel), 'r', encoding='utf-8') as fh:
        return fh.read()


# كل أسماء البيئة التي تقرأها الوحدة فعلاً — تُؤخذ من الوحدة نفسها لا تُنسَخ
ENV_NAMES = tuple(B._ENV_SHA) + tuple(B._ENV_BUILT) + tuple(B._ENV_BRANCH) + \
    ("ACS_VERSION", "ACS_BUILD_INFO_FILE", "ACS_BUILD_INFO_SOURCE")


class Env(object):
    """يضبط البيئة ضبطاً كاملاً ثمّ يعيدها كما كانت — لا تسرّب بين الحالات."""

    def __init__(self, **overrides):
        self.overrides = overrides
        self.saved = {}

    def __enter__(self):
        for n in ENV_NAMES:
            self.saved[n] = os.environ.get(n)
            os.environ.pop(n, None)
        for n, v in self.overrides.items():
            if n not in self.saved:
                self.saved[n] = os.environ.get(n)
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
        return self

    def __exit__(self, *a):
        for n, v in self.saved.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
        return False


NOWHERE = os.path.join(tempfile.gettempdir(),
                       "acs_build_info_absent_%d.json" % os.getpid())
if os.path.exists(NOWHERE):                                       # pragma: no cover
    os.remove(NOWHERE)

REQUIRED_KEYS = ("service", "version", "git_sha", "git_sha_short",
                 "git_branch", "built_at", "schema_versions",
                 "provenance_verified")

# ═══════════════════════════════════════════════════ أ) شكل الردّ ═══════════
print('\n── أ · شكل أصل البناء ──')

with Env(ACS_BUILD_INFO_FILE=NOWHERE):
    INFO = B.build_info()

chk('build_info returns a dict', isinstance(INFO, dict), type(INFO).__name__)
for k in REQUIRED_KEYS:
    chk('build_info declares %s' % k, k in INFO,
        str(sorted(INFO.keys())) if isinstance(INFO, dict) else '')
chk('build_info returns nothing beyond the declared fields',
    isinstance(INFO, dict) and set(INFO.keys()) == set(REQUIRED_KEYS),
    str(sorted(set(INFO.keys()) - set(REQUIRED_KEYS))))
chk('service is the declared service name',
    INFO.get("service") == B.SERVICE_NAME, repr(INFO.get("service")))
chk('schema_versions is a non-empty mapping of strings',
    isinstance(INFO.get("schema_versions"), dict)
    and len(INFO["schema_versions"]) > 0
    and all(isinstance(k, str) and isinstance(v, str)
            for k, v in INFO["schema_versions"].items()))
chk('schema_versions is a copy, so a caller cannot mutate the module constant',
    INFO["schema_versions"] is not B.SCHEMA_VERSIONS)
chk('provenance_verified is a boolean, never a string',
    isinstance(INFO.get("provenance_verified"), bool),
    repr(INFO.get("provenance_verified")))
chk('build_info is serialisable as JSON exactly as returned',
    isinstance(json.loads(json.dumps(INFO, ensure_ascii=False)), dict))

# ═════════════════════════════════════════════ ب) ترتيب المصادر ════════════
print('\n── ب · ترتيب المصادر: البيئة ← الملفّ ← git ← unknown ──')

ENV_SHA = "a" * 40
ENV_BUILT = "2026-02-03T04:05:06Z"

with Env(ACS_GIT_SHA=ENV_SHA, ACS_BUILT_AT=ENV_BUILT,
         ACS_BUILD_INFO_FILE=NOWHERE):
    env_info = B.build_info()
chk('environment · ACS_GIT_SHA wins',
    env_info["git_sha"] == ENV_SHA, repr(env_info["git_sha"]))
chk('environment · ACS_BUILT_AT wins',
    env_info["built_at"] == ENV_BUILT, repr(env_info["built_at"]))
chk('environment · the short sha is derived from the winning sha, not invented',
    env_info["git_sha_short"] == ENV_SHA[:12], repr(env_info["git_sha_short"]))
chk('environment · both sources present means provenance is verified',
    env_info["provenance_verified"] is True)

# البيئة تسبق الملفّ حتى حين يوجد الملفّ
_fd, FILE_PATH = tempfile.mkstemp(prefix="acs_build_info_", suffix=".json")
os.close(_fd)
FILE_SHA = "b" * 40
FILE_BUILT = "2025-12-31T23:59:59Z"
FILE_BRANCH = "file-branch"
FILE_VERSION = "9.9-from-file"
with open(FILE_PATH, "w", encoding="utf-8") as fh:
    json.dump({"git_sha": FILE_SHA, "built_at": FILE_BUILT,
               "git_branch": FILE_BRANCH, "version": FILE_VERSION}, fh)

with Env(ACS_GIT_SHA=ENV_SHA, ACS_BUILT_AT=ENV_BUILT,
         ACS_BUILD_INFO_FILE=FILE_PATH):
    both_info = B.build_info()
chk('precedence · the environment beats the build_info.json file',
    both_info["git_sha"] == ENV_SHA and both_info["built_at"] == ENV_BUILT,
    repr((both_info["git_sha"], both_info["built_at"])))

with Env(ACS_GIT_SHA=ENV_SHA, ACS_BUILD_INFO_FILE=FILE_PATH):
    mixed_info = B.build_info()
chk('a deployment SHA cannot borrow the timestamp of a different commit',
    mixed_info['built_at'] == B.UNKNOWN, repr(mixed_info))
chk('mixed-commit metadata is never reported as verified',
    mixed_info['provenance_verified'] is False)
chk('a deployment SHA cannot borrow a different commit branch or version',
    mixed_info['git_branch'] == B.UNKNOWN
    and mixed_info['version'] == B.SERVICE_VERSION)
with Env(ACS_GIT_SHA=FILE_SHA, ACS_BUILD_INFO_FILE=FILE_PATH):
    matching_info = B.build_info()
chk('matching-commit file metadata remains usable',
    matching_info['built_at'] == FILE_BUILT
    and matching_info['provenance_verified'] is True)
with Env(ACS_GIT_SHA='not-a-commit', ACS_BUILT_AT=ENV_BUILT,
         ACS_BUILD_INFO_FILE=NOWHERE):
    invalid_sha = B.build_info()
chk('a nonempty but invalid commit is not verified provenance',
    invalid_sha['provenance_verified'] is False)
with Env(ACS_GIT_SHA=ENV_SHA, ACS_BUILT_AT='not-a-timestamp',
         ACS_BUILD_INFO_FILE=NOWHERE):
    invalid_time = B.build_info()
chk('a nonempty but invalid build timestamp is not verified provenance',
    invalid_time['provenance_verified'] is False)

with Env(ACS_BUILD_INFO_FILE=FILE_PATH):
    file_info = B.build_info()
chk('file · with the environment unset the file is used for the sha',
    file_info["git_sha"] == FILE_SHA, repr(file_info["git_sha"]))
chk('file · the timestamp comes from the file too',
    file_info["built_at"] == FILE_BUILT, repr(file_info["built_at"]))
chk('file · the branch comes from the file',
    file_info["git_branch"] == FILE_BRANCH, repr(file_info["git_branch"]))
chk('file · the version comes from the file',
    file_info["version"] == FILE_VERSION, repr(file_info["version"]))
chk('file · a file-sourced build is reported as verified',
    file_info["provenance_verified"] is True)

# هذا المستودع نسخة git فعلاً — يُتحقَّق مستقلاً قبل الاعتماد عليه
try:
    GIT_HEAD = subprocess.check_output(
        ["git", "-C", ROOT, "rev-parse", "HEAD"],
        stderr=subprocess.DEVNULL, timeout=10).decode("ascii").strip()
except Exception:                                                 # pragma: no cover
    GIT_HEAD = ""
chk('git · this checkout really is a git repository (verified independently)',
    bool(re.fullmatch(r"[0-9a-f]{40}", GIT_HEAD or "")), repr(GIT_HEAD))

if GIT_HEAD:
    with Env(ACS_BUILD_INFO_FILE=NOWHERE):
        git_info = B.build_info()
    chk('git · with no environment and no file the local checkout sha is used',
        git_info["git_sha"] == GIT_HEAD,
        '%r != %r' % (git_info["git_sha"], GIT_HEAD))
    chk('git · the short sha is the first twelve characters of that sha',
        git_info["git_sha_short"] == GIT_HEAD[:12])
    chk('git · a sha with no timestamp is NOT reported as verified provenance',
        git_info["provenance_verified"] is False
        or git_info["built_at"] != B.UNKNOWN,
        repr((git_info["built_at"], git_info["provenance_verified"])))

# لا مصدر إطلاقاً — تُحاكى بتعطيل قراءة git وحدها، والباقي مضبوط فعلاً
_real_from_git = B._from_git
try:
    B._from_git = lambda: None
    with Env(ACS_BUILD_INFO_FILE=NOWHERE):
        none_info = B.build_info()
finally:
    B._from_git = _real_from_git

chk('none · the sha is the literal "unknown"',
    none_info["git_sha"] == "unknown", repr(none_info["git_sha"]))
chk('none · the short sha is the literal "unknown" too, not a slice of it',
    none_info["git_sha_short"] == "unknown", repr(none_info["git_sha_short"]))
chk('none · the timestamp is the literal "unknown"',
    none_info["built_at"] == "unknown", repr(none_info["built_at"]))
chk('none · the branch is the literal "unknown"',
    none_info["git_branch"] == "unknown", repr(none_info["git_branch"]))
chk('none · provenance_verified is False and nothing is invented',
    none_info["provenance_verified"] is False)
chk('none · the version still falls back to the declared service version',
    none_info["version"] == B.SERVICE_VERSION, repr(none_info["version"]))
chk('none · no field was filled with a fabricated placeholder',
    all(none_info[k] == "unknown"
        for k in ("git_sha", "git_sha_short", "git_branch", "built_at")))

# كل اسم بيئة معلن للـSHA يُقرأ فعلاً (لا اسم ميّت في القائمة)
for name in B._ENV_SHA:
    with Env(**{name: "c" * 40, "ACS_BUILD_INFO_FILE": NOWHERE}):
        chk('environment · %s is actually read' % name,
            B.build_info()["git_sha"] == "c" * 40)
for name in B._ENV_BUILT:
    with Env(**{name: "2026-01-01T00:00:00Z",
                "ACS_BUILD_INFO_FILE": NOWHERE}):
        chk('environment · %s is actually read' % name,
            B.build_info()["built_at"] == "2026-01-01T00:00:00Z")
for name in B._ENV_BRANCH:
    with Env(**{name: "some-branch", "ACS_BUILD_INFO_FILE": NOWHERE}):
        chk('environment · %s is actually read' % name,
            B.build_info()["git_branch"] == "some-branch")

# ملفّ تالف لا يُسقِط الخدمة ولا يُخترَع منه شيء
_fd, BAD_FILE = tempfile.mkstemp(prefix="acs_build_info_bad_", suffix=".json")
os.close(_fd)
with open(BAD_FILE, "w", encoding="utf-8") as fh:
    fh.write("{ this is not json")
try:
    with Env(ACS_BUILD_INFO_FILE=BAD_FILE):
        bad_info = B.build_info()
    chk('file · a corrupt build_info.json degrades instead of raising',
        isinstance(bad_info, dict) and set(bad_info) == set(REQUIRED_KEYS))
except Exception as exc:                                          # pragma: no cover
    chk('file · a corrupt build_info.json degrades instead of raising',
        False, repr(exc))

with open(BAD_FILE, "w", encoding="utf-8") as fh:
    fh.write('["a list, not an object"]')
try:
    with Env(ACS_BUILD_INFO_FILE=BAD_FILE):
        list_info = B.build_info()
    chk('file · a JSON file that is not an object is ignored, not trusted',
        isinstance(list_info, dict) and set(list_info) == set(REQUIRED_KEYS))
except Exception as exc:                                          # pragma: no cover
    chk('file · a JSON file that is not an object is ignored, not trusted',
        False, repr(exc))

# ═══════════════════════════════════════════════ ج) لا تسرّب سرّ ═══════════
print('\n── ج · لا سرّ ولا مسار ملفّ في الردّ ──')

# أشكال مفاتيح شائعة: sk-... / sk-ant-... / رمز طويل عشوائي متّصل
KEY_SHAPES = (
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"sk-ant-", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\b\s*[:=]"),
)
WIN_PATH = re.compile(r"[A-Za-z]:[\\/]")


def flat_strings(obj, prefix=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append(("%s.key" % prefix, str(k)))
            out.extend(flat_strings(v, "%s.%s" % (prefix, k)))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out.extend(flat_strings(v, "%s[%d]" % (prefix, i)))
    elif isinstance(obj, str):
        out.append((prefix, obj))
    return out


def leak_report(info):
    bad = []
    for where, s in flat_strings(info, "build_info"):
        for pat in KEY_SHAPES:
            if pat.search(s):
                bad.append(("api-key shape", where, s[:40]))
        if s.startswith("/") or s.startswith("\\\\") or WIN_PATH.match(s):
            bad.append(("absolute path", where, s[:80]))
        if ROOT in s or tempfile.gettempdir() in s:
            bad.append(("filesystem path", where, s[:80]))
    return bad


# يُفحَص كل شكل من أشكال الردّ، بما فيها الشكل المقروء من ملفّ في /tmp
SAMPLES = [("environment", env_info), ("file", file_info),
           ("none", none_info), ("default", INFO)]
if GIT_HEAD:
    SAMPLES.append(("git", git_info))
for label, sample in SAMPLES:
    rep = leak_report(sample)
    chk('no_secret_leak · the %s response contains no key-shaped value and no '
        'absolute path' % label, not rep, str(rep[:3]))

chk('no_secret_leak · the response never names ANTHROPIC_API_KEY',
    all("ANTHROPIC_API_KEY" not in s
        for _, s in flat_strings(INFO, "build_info")))
chk('no_secret_leak · the response never names ACS_REDIS_URL',
    all("ACS_REDIS_URL" not in s for _, s in flat_strings(INFO, "build_info")))

# حتى لو حُقن سرّ في البيئة التي تقرأها الوحدة، لا يخرج إلا ما طُلب
with Env(ACS_BUILD_INFO_FILE=NOWHERE):
    os.environ["ANTHROPIC_API_KEY"] = "sk-" + "ant-" + "test-not-a-real-key-000000000000"
    try:
        poisoned = B.build_info()
    finally:
        os.environ.pop("ANTHROPIC_API_KEY", None)
chk('no_secret_leak · a secret present in the environment never reaches the '
    'response', not leak_report(poisoned), str(leak_report(poisoned)[:3]))

# مسار الملفّ المستعمل فعلاً لا يُعاد للعميل
with Env(ACS_BUILD_INFO_FILE=FILE_PATH):
    pathy = B.build_info()
chk('no_secret_leak · the build_info.json path used is never echoed back',
    FILE_PATH not in json.dumps(pathy, ensure_ascii=False))

# ═════════════════════════════ د) السلسلة الفارغة لا تُسقِط الإقلاع ════════
print('\n── د · السلسلة الفارغة لا تُسقِط الوحدة (صنف عطل int("")) ──')

empty = {n: "" for n in ENV_NAMES}
try:
    with Env(**empty):
        empty_info = B.build_info()
        empty_id = B.build_identifier()
    ok_empty = isinstance(empty_info, dict)
except Exception as exc:                                          # pragma: no cover
    empty_info, empty_id, ok_empty = None, None, False
    print('     raised: %r' % (exc,))
chk('empty_env · build_info still returns with every read variable set to ""',
    ok_empty)
if ok_empty:
    chk('empty_env · the full declared shape survives',
        set(empty_info.keys()) == set(REQUIRED_KEYS))
    chk('empty_env · an empty ACS_VERSION falls back to the declared version',
        empty_info["version"] == B.SERVICE_VERSION,
        repr(empty_info["version"]))
    chk('empty_env · an empty ACS_GIT_SHA does not become the empty string',
        empty_info["git_sha"] != "")
    chk('empty_env · build_identifier still returns a string',
        isinstance(empty_id, str) and empty_id != "")

# قيمة غير رقمية / بيضاء لا تُسقِط شيئاً أيضاً
spacey = {n: "   " for n in ENV_NAMES}
try:
    with Env(**spacey):
        spacey_info = B.build_info()
    chk('empty_env · whitespace-only values are treated as absent, not as data',
        isinstance(spacey_info, dict)
        and spacey_info["version"] == B.SERVICE_VERSION
        and spacey_info["git_sha"].strip() == spacey_info["git_sha"])
except Exception as exc:                                          # pragma: no cover
    chk('empty_env · whitespace-only values are treated as absent, not as data',
        False, repr(exc))

# لا قراءة int في هذه الوحدة أصلاً — يُثبَت ساكناً لا بالثقة
BI_SRC = rd('acs_build_info.py')
_bi_tree = ast.parse(BI_SRC)
_int_on_env = []
for node in ast.walk(_bi_tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in ("int", "float") and node.args:
        _int_on_env.append(ast.dump(node.args[0])[:60])
chk('empty_env · the module performs no int()/float() coercion at all',
    not _int_on_env, str(_int_on_env))

# ═══════════════════════════════ هـ) التوصيل الساكن في الواجهة ═════════════
print('\n── هـ · التوصيل الساكن: /version و/health في acs_understand_api.py ──')

API_SRC = rd('acs_understand_api.py')
API_TREE = ast.parse(API_SRC)


def route_of(fn):
    """('get', '/version') لكل زخرفة @app.<method>("<path>") على الدالّة."""
    out = []
    for d in fn.decorator_list:
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) \
                and isinstance(d.func.value, ast.Name) \
                and d.func.value.id == "app" and d.args \
                and isinstance(d.args[0], ast.Constant):
            out.append((d.func.attr, d.args[0].value))
    return out


FUNCS = [n for n in ast.walk(API_TREE)
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
BY_NAME = {n.name: n for n in FUNCS}

version_fn = BY_NAME.get("version")
chk('a route function named version exists', version_fn is not None)
chk('the version function is decorated with @app.get("/version")',
    version_fn is not None and ("get", "/version") in route_of(version_fn),
    str(route_of(version_fn)) if version_fn else 'no function named version')

health_fn = BY_NAME.get("health")
chk('a route function named health exists', health_fn is not None)
chk('the health function is decorated with @app.get("/health")',
    health_fn is not None and ("get", "/health") in route_of(health_fn),
    str(route_of(health_fn)) if health_fn else 'no function named health')


def dict_keys_in(fn):
    keys = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Dict):
            for k in node.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.add(k.value)
        if isinstance(node, ast.keyword) and node.arg:
            keys.add(node.arg)
    return keys


chk('the health response includes a build key',
    health_fn is not None and "build" in dict_keys_in(health_fn),
    str(sorted(dict_keys_in(health_fn))) if health_fn else '')
chk('the health build block is produced by acs_build_info, not hand-written',
    health_fn is not None
    and "BUILD.build_info()" in (ast.get_source_segment(API_SRC, health_fn) or ''))

VERSION_KEYS = dict_keys_in(version_fn) if version_fn else set()
for k in ("git_sha", "git_sha_short", "built_at", "provenance_verified",
          "schema_versions"):
    chk('the version response exposes %s' % k, k in VERSION_KEYS,
        str(sorted(VERSION_KEYS)))


def constants_in(fn):
    return {n.value for n in ast.walk(fn)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}


for fname, fn in (("version", version_fn), ("health", health_fn)):
    if fn is None:
        continue
    seg = ast.get_source_segment(API_SRC, fn) or ''
    for secret in ("ANTHROPIC_API_KEY", "ACS_REDIS_URL"):
        chk('the %s response never mentions %s' % (fname, secret),
            secret not in constants_in(fn) and secret not in seg,
            secret)
    chk('the %s response contains no os.environ read of a secret' % fname,
        "ANTHROPIC_API_KEY" not in seg and "ACS_REDIS_URL" not in seg)

# مسار /version لا يُعلن مرّتين ولا يتعارض مع مسار آخر
_route_pairs = [r for fn in FUNCS for r in route_of(fn)]
chk('/version is declared exactly once',
    _route_pairs.count(("get", "/version")) == 1, str(_route_pairs))
chk('/health is declared exactly once',
    _route_pairs.count(("get", "/health")) == 1, str(_route_pairs))
chk('acs_build_info is imported by the API module',
    "import acs_build_info" in API_SRC)

# الوحدة منسوخة إلى صورة النشر — وإلّا لن يوجد /version في الإنتاج
DOCKER_SRC = rd('Dockerfile')
chk('the Dockerfile copies acs_build_info.py into the deployed image',
    "acs_build_info.py" in DOCKER_SRC)

# ═══════════════════════════════════ و) معرّف البناء المعروض ═══════════════
print('\n── و · معرّف قصير للعرض البشري ──')

with Env(ACS_GIT_SHA=ENV_SHA, ACS_BUILT_AT=ENV_BUILT,
         ACS_BUILD_INFO_FILE=NOWHERE):
    ident = B.build_identifier()
    ident_info = B.build_info()

chk('build_identifier returns a string', isinstance(ident, str), repr(ident))
chk('build_identifier is short enough to render in a UI chip',
    isinstance(ident, str) and 0 < len(ident) <= 64, repr(ident))
chk('build_identifier is a single line',
    isinstance(ident, str) and "\n" not in ident and "\r" not in ident)
chk('build_identifier joins version and short sha with a middle dot',
    ident == "%s · %s" % (ident_info["version"], ident_info["git_sha_short"]),
    repr(ident))
chk('build_identifier shows the short sha, never the full forty characters',
    ENV_SHA not in ident and ident_info["git_sha_short"] in ident)
chk('build_identifier leaks nothing',
    not any(pat.search(ident) for pat in KEY_SHAPES)
    and not ident.startswith("/") and ROOT not in ident)

with Env(ACS_BUILD_INFO_FILE=NOWHERE):
    _real = B._from_git
    try:
        B._from_git = lambda: None
        unknown_ident = B.build_identifier()
    finally:
        B._from_git = _real
chk('build_identifier says unknown rather than inventing an identifier',
    unknown_ident == "%s · unknown" % B.SERVICE_VERSION, repr(unknown_ident))

for path in (FILE_PATH, BAD_FILE):
    try:
        os.remove(path)
    except OSError:                                               # pragma: no cover
        pass

print('\n' + '─' * 62)
print('BUILD METADATA: %d passed, %d failed' % (p[0], f[0]))
sys.exit(1 if f[0] else 0)
