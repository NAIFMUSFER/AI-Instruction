#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# tests/production/verify_live.py — التحقّق الإنتاجي الحيّ (HTTP + الأصول).
#
# ثلاث نتائج لا رابع لها، ولا تُخلط أبداً:
#   PASS         — رُصد السلوك الصحيح فعلاً على النشر.
#   FAIL         — رُصد سلوك خاطئ فعلاً.
#   NOT VERIFIED — تعذّر الرصد أصلاً (شبكة/بيئة). فحصٌ لم يُنفَّذ لا يُحوَّل إلى نجاح.
#
# الفحص الساكن (قراءة ملفّات المستودع) لا يُترجَم أبداً إلى PASS زمن تشغيل:
# يُستعمل لاشتقاق العقود المتوقَّعة فقط (قائمة الأصول، شكل مغلّف الخطأ، الأصل
# المسموح)، ثمّ يُقاس السلوك عبر HTTP حقيقي أو لا يُدَّعى شيء.
#
# مجموعات الفحص هنا:
#   A — HTTP: جذر الواجهة، و/ و/health و/ready و/version للخادم، ومغلّف الخطأ
#       على مسار غير موجود، وCORS preflight من الأصل المسموح ومن أصل غريب.
#   B — أصول الواجهة: كل وحدة JS حرِجة 200، وThree.js REVISION=160، ولا مرجع
#       CDN زمن التشغيل، ولا انتهاك CSP، ولا 404 غير متوقّع، ولا استيراد معطوب.
#   G — أصل النشر (provenance): SHA الخادم من /version، وSHA الواجهة من
#       window.ACS_BUILD_INFO كما تُقدّمه الصفحة، والطابع الزمني، ومقارنته
#       بمراجعة متوقّعة عند تمريرها عبر --expect-sha.
#
# المجموعات C و D و E و F (المتصفّح الحقيقي) في tests/production/verify_live_browser.js.
#
#   python3 tests/production/verify_live.py
#   python3 tests/production/verify_live.py --frontend https://... --backend https://...
#   python3 tests/production/verify_live.py --expect-sha 6bc8a88b1871334c1d371d4e5e5da9ad540109ac
#   ACS_VERIFY_BACKEND=http://127.0.0.1:8000 python3 tests/production/verify_live.py
#
# رموز الخروج:
#   0  لا فشل، ورُصد شيء واحد على الأقل
#   1  فشل واحد على الأقل (FAIL مرصود)
#   2  لم يُرصد شيء إطلاقاً — كل شيء NOT VERIFIED
# =============================================================================
from __future__ import print_function

import argparse
import io
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUTDIR = os.path.join(HERE, "outputs")

# ── الأهداف الافتراضية ──────────────────────────────────────────────────────
# مصدرها المُعلن في المستودع، لا رقم مكتوب هنا من الذاكرة:
#   netlify.toml                     → publish=public ، CSP connect-src للخادم
#   render.yaml                      → ACS_ALLOWED_ORIGINS = نطاق Netlify
#   acs_understand_api._DEFAULT_ORIGIN → نفس نطاق Netlify
#   public/index.html CONFIGURED_BASE → نطاق Render
DEFAULT_FRONTEND = "https://sprightly-selkie-d906c3.netlify.app"
DEFAULT_BACKEND = "https://acs-engine.onrender.com"

PASS = "PASS"
FAIL = "FAIL"
NV = "NOT VERIFIED"
NV_SUFFIX = "NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED"

ERROR_CONTRACT = "acs-error-envelope/1.0.0"
ENVELOPE_ERROR_FIELDS = {"code", "message", "request_id", "retryable", "upstream"}
THREE_REVISION = "160"

# مضيفو CDN الشائعون — وجود أيّ منهم في أصل يُخدَم زمن التشغيل يعني اعتماداً
# خارجياً لم يُعبَّأ محلياً، وهو بالضبط ما تمنعه tools/netlify-build.sh والـCSP.
CDN_HOSTS = (
    "unpkg.com", "cdn.jsdelivr.net", "jsdelivr.net", "cdnjs.cloudflare.com",
    "skypack.dev", "esm.sh", "esm.run", "ajax.googleapis.com",
    "fonts.googleapis.com", "fonts.gstatic.com", "code.jquery.com",
    "threejs.org", "cdn.skypack.dev", "jspm.dev", "ga.jspm.io",
)

_LOOPBACK = ("127.0.0.1", "localhost", "::1", "0.0.0.0")


# ══════════════════════════════════════════════════════════════════════════
# سجلّ النتائج
# ══════════════════════════════════════════════════════════════════════════
class Results(object):
    def __init__(self):
        self.rows = []

    def add(self, group, cid, name, status, detail="", reason=""):
        row = {"group": group, "id": cid, "name": name, "status": status,
               "detail": str(detail)[:600], "reason": str(reason)[:400]}
        self.rows.append(row)
        mark = {PASS: "✓", FAIL: "✗", NV: "―"}[status]
        line = "  %s %-6s %s" % (mark, cid, name)
        if status == NV:
            line += "\n      %s" % NV_SUFFIX
            if reason:
                line += "\n      reason: %s" % str(reason)[:300]
        elif detail:
            line += "\n      %s" % str(detail)[:300]
        print(line)
        return row

    def ok(self, group, cid, name, cond, detail="", nv_reason=None):
        """PASS/FAIL مرصودان. nv_reason غير الفارغ يعني: لم نستطع الرصد."""
        if nv_reason:
            return self.add(group, cid, name, NV, "", nv_reason)
        return self.add(group, cid, name, PASS if cond else FAIL, detail)

    def not_verified(self, group, cid, name, reason):
        return self.add(group, cid, name, NV, "", reason)

    def count(self, status):
        return sum(1 for r in self.rows if r["status"] == status)


# ══════════════════════════════════════════════════════════════════════════
# طبقة HTTP — لا ترفع استثناءً، وتفصل خطأ النقل عن حالة HTTP
# ══════════════════════════════════════════════════════════════════════════
class Resp(object):
    """status=0 ⇒ لم يصل شيء: transport_error يحمل السبب (وكيل/DNS/TLS/رفض)."""

    def __init__(self, status=0, headers=None, text="", raw=b"",
                 transport_error="", elapsed=0.0, url=""):
        self.status = status
        self.headers = headers or {}
        self.text = text
        self.raw = raw
        self.transport_error = transport_error
        self.elapsed = elapsed
        self.url = url

    @property
    def reached(self):
        return self.status != 0

    def header(self, name):
        low = name.lower()
        for k, v in self.headers.items():
            if str(k).lower() == low:
                return v
        return ""

    def json(self):
        try:
            return json.loads(self.text), True
        except Exception:
            return None, False


def _is_loopback(url):
    try:
        host = urllib.parse.urlsplit(url).hostname or ""
    except Exception:
        return False
    return host in _LOOPBACK


def _opener_for(url):
    """المضيف المحلّي لا يمرّ عبر أي وكيل — وإلّا تعذّر إثبات مسار FAIL محلياً."""
    if _is_loopback(url):
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener()


def http(url, method="GET", headers=None, body=None, timeout=45,
         max_bytes=4 * 1024 * 1024):
    started = time.time()
    data = None
    hdrs = {"User-Agent": "acs-production-verifier/1.0 (+tests/production)"}
    hdrs.update(headers or {})
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    opener = _opener_for(url)
    try:
        with opener.open(req, timeout=timeout) as r:
            raw = r.read(max_bytes)
            return Resp(r.getcode(), dict(r.headers), raw.decode("utf-8", "replace"),
                        raw, "", time.time() - started, url)
    except urllib.error.HTTPError as e:
        # وصلنا فعلاً — حالة HTTP خطأ ليست عطل نقل.
        try:
            raw = e.read(max_bytes)
        except Exception:
            raw = b""
        return Resp(e.code, dict(e.headers or {}), raw.decode("utf-8", "replace"),
                    raw, "", time.time() - started, url)
    except Exception as e:  # noqa: BLE001 — كل ما تبقّى عطل نقل
        return Resp(0, {}, "", b"", "%s: %s" % (type(e).__name__, str(e)[:220]),
                    time.time() - started, url)


def classify_transport(err):
    """يترجم عطل النقل إلى سبب NOT VERIFIED مفهوم — لا إلى فشل منطقي."""
    low = (err or "").lower()
    if "tunnel connection failed" in low or "403 forbidden" in low and "tunnel" in low:
        return ("egress proxy refused the CONNECT tunnel (HTTP 403) — this "
                "sandbox cannot reach arbitrary external hosts: %s" % err)
    if "certificate" in low or "ssl" in low:
        return "TLS could not be established: %s" % err
    if "name or service not known" in low or "nodename nor servname" in low \
            or "getaddrinfo" in low or "-2]" in low or "-3]" in low:
        return "DNS did not resolve the host: %s" % err
    if "refused" in low:
        return "the connection was refused: %s" % err
    if "timed out" in low or "timeout" in low:
        return "the connection timed out: %s" % err
    return "the target could not be reached: %s" % err


# ══════════════════════════════════════════════════════════════════════════
# اشتقاق العقود من المستودع (ساكن — لا يُنتج PASS بذاته)
# ══════════════════════════════════════════════════════════════════════════
def read_repo(rel):
    try:
        with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return ""


def declared_targets():
    """ما يعلنه المستودع فعلاً — يُطبع كاستشهاد، ولا يُقاس عليه نجاح."""
    out = {}
    render = read_repo("render.yaml")
    m = re.search(r"ACS_ALLOWED_ORIGINS[\s\S]{0,120}?value:\s*\"([^\"]+)\"", render)
    out["render_allowed_origins"] = m.group(1) if m else ""
    api = read_repo("acs_understand_api.py")
    m = re.search(r"_DEFAULT_ORIGIN\s*=\s*\"([^\"]+)\"", api)
    out["api_default_origin"] = m.group(1) if m else ""
    page = read_repo("public/index.html")
    m = re.search(r"CONFIGURED_BASE\s*=\s*\"([^\"]*)\"", page)
    out["page_configured_base"] = (m.group(1) if m else "").rstrip("/")
    toml = read_repo("netlify.toml")
    m = re.search(r"publish\s*=\s*\"([^\"]+)\"", toml)
    out["netlify_publish"] = m.group(1) if m else ""
    m = re.search(r"Content-Security-Policy\s*=\s*\"([^\"]+)\"", toml)
    out["netlify_csp"] = m.group(1) if m else ""
    m = re.search(r"connect-src([^;\"]*)", out["netlify_csp"] or "")
    out["netlify_connect_src"] = (m.group(1).strip() if m else "")
    return out


def frontend_auth_config():
    """هل هناك حماية بكلمة مرور مقصودة للواجهة؟ نبحث حيث تُضبط فعلاً.

    Netlify يضبطها في netlify.toml أو public/_headers أو لوحة الموقع
    (Site settings ▸ Access control ▸ Visitor access) — وهذه الأخيرة لا أثر
    لها في المستودع. نُعيد ما وجدناه حرفياً، ولا نخمّن."""
    found = []
    toml = read_repo("netlify.toml")
    for key in ("basic_auth", "Basic-Auth", "[[edge_functions]]", "password"):
        if key in toml:
            found.append("netlify.toml contains %r" % key)
    if os.path.exists(os.path.join(ROOT, "public", "_headers")):
        found.append("public/_headers exists")
    if os.path.exists(os.path.join(ROOT, "public", "_redirects")):
        found.append("public/_redirects exists")
    return found


def critical_assets():
    """قائمة الأصول الحرِجة مشتقّة من مصدرين اثنين لا من ذاكرة الكاتب:

      1) tools/netlify-build.sh  — مصفوفة `must=( … )` التي يتحقّق منها البناء.
      2) public/index.html       — خريطة الاستيراد وكل مسار /vendor/ في الصفحة.

    تُعاد مساراً URL مطلقاً على أصل الواجهة."""
    sh = read_repo("tools/netlify-build.sh")
    variables = {}
    for name in ("THREE", "SHIMS", "PDFJS", "VEN"):
        m = re.search(r"^%s=(\S+)" % name, sh, re.M)
        if m:
            variables[name] = m.group(1).strip().strip('"')
    variables.setdefault("VEN", "public/vendor")

    def expand(raw):
        s = raw.strip().strip('"').strip("'")
        for k, v in variables.items():
            s = s.replace("$%s" % k, v).replace("${%s}" % k, v)
        return s

    assets = []
    block = re.search(r"^must=\(\s*$(.*?)^\)\s*$", sh, re.M | re.S)
    if block:
        for line in block.group(1).splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            path = expand(line)
            if path.startswith("public/"):
                assets.append("/" + path[len("public/"):])
    declared_by_build = list(assets)

    page = read_repo("public/index.html")
    # خريطة الاستيراد: تحوّل "three" و"three/addons/" إلى مسارات /vendor
    imap = {}
    m = re.search(r'<script type="importmap">(.*?)</script>', page, re.S)
    if m:
        try:
            imap = (json.loads(m.group(1)) or {}).get("imports") or {}
        except Exception:
            imap = {}
    for spec in sorted(set(re.findall(r"three/addons/[A-Za-z0-9/_.\-]+\.js", page))):
        prefix = imap.get("three/addons/")
        if prefix:
            assets.append(prefix + spec[len("three/addons/"):])
    if imap.get("three"):
        assets.append(imap["three"])
    for ref in sorted(set(re.findall(r"/vendor/[A-Za-z0-9@./_\-]+\.(?:js|mjs)", page))):
        assets.append(ref)

    seen, ordered = set(), []
    for a in assets:
        if a not in seen:
            seen.add(a)
            ordered.append(a)
    return ordered, declared_by_build, imap


# ══════════════════════════════════════════════════════════════════════════
# المجموعة A — HTTP
# ══════════════════════════════════════════════════════════════════════════
def group_a(R, frontend, backend, timeout, state):
    print("\n── A · HTTP: الواجهة والخادم وعقد الأخطاء وCORS ──")

    # A1 — جذر الواجهة
    r = http(frontend, timeout=timeout)
    state["frontend_root"] = r
    if not r.reached:
        why = classify_transport(r.transport_error)
        state["frontend_reachable"] = False
        R.not_verified("A", "A1", "frontend root answers 200", why)
    else:
        state["frontend_reachable"] = True
        if r.status in (401, 403):
            cfg = frontend_auth_config()
            detail = ("FRONTEND_ACCESS_RESTRICTED — HTTP %d from %s. "
                      "Authentication configuration found in the repository: %s. "
                      "The site is NOT publicly verified."
                      % (r.status, frontend,
                         "; ".join(cfg) if cfg else
                         "NONE — no basic_auth / _headers / edge function in the "
                         "repo, so any password is set in the Netlify site "
                         "dashboard (Site settings ▸ Access control), outside "
                         "this tree"))
            R.add("A", "A1", "frontend root answers 200", FAIL, detail)
        else:
            R.ok("A", "A1", "frontend root answers 200 (not 401/403)",
                 r.status == 200, "HTTP %d in %.2fs" % (r.status, r.elapsed))
        ctype = r.header("content-type")
        R.ok("A", "A1b", "frontend root is served as HTML",
             "text/html" in ctype.lower(), "content-type=%r" % ctype)

    # ── الخادم ──
    br = http(backend + "/", timeout=timeout)
    state["backend_root"] = br
    if not br.reached:
        why = classify_transport(br.transport_error)
        state["backend_reachable"] = False
        for cid, name in (
                ("A2", "GET / answers 200 with the service JSON"),
                ("A3", "GET /health answers 200 and declares configuration"),
                ("A4", "GET /ready is a real verdict (200 ready or 503 envelope)"),
                ("A5", "GET /version matches the acs_build_info contract"),
                ("A6", "an invalid route returns the declared error envelope"),
                ("A7", "a CORS preflight from the allowed origin is accepted"),
                ("A8", "a CORS preflight from an unrelated origin is refused")):
            R.not_verified("A", cid, name, why)
        return
    state["backend_reachable"] = True

    j, ok = br.json()
    R.ok("A", "A2", "GET / answers 200 with the service JSON",
         br.status == 200 and ok and isinstance(j, dict)
         and j.get("ok") is True and bool(j.get("service"))
         and j.get("error_contract") == ERROR_CONTRACT,
         "HTTP %d body=%s" % (br.status, br.text[:160]))

    hr = http(backend + "/health", timeout=timeout)
    hj, ok = hr.json()
    R.ok("A", "A3", "GET /health answers 200 and declares configuration",
         hr.status == 200 and ok and isinstance(hj, dict)
         and hj.get("ok") is True and bool(hj.get("service"))
         and bool(hj.get("version"))
         and hj.get("error_contract") == ERROR_CONTRACT
         and "model_configured" in hj
         and isinstance(hj.get("api_key_configured"), bool),
         "HTTP %d body=%s" % (hr.status, hr.text[:200]))
    # فحص التسرّب لا معنى له على صفحة خطأ: لو لم يردّ /health بجسد JSON فعليّ
    # فلا شيء يُفحَص، والادّعاء بالنجاح هنا فراغ.
    if hr.status == 200 and ok:
        R.ok("A", "A3b", "/health leaks no credential material",
             "sk-ant" not in hr.text and "Bearer " not in hr.text,
             "%d bytes of the real health body scanned" % len(hr.text))
    else:
        R.not_verified("A", "A3b", "/health leaks no credential material",
                       "/health did not answer 200 with a JSON body (HTTP %d), "
                       "so there was no health payload to scan" % hr.status)
    state["health"] = hj if ok else None

    rr = http(backend + "/ready", timeout=timeout)
    rj, ok = rr.json()
    ready_ok = ok and (
        (rr.status == 200 and rj.get("ready") is True)
        or (rr.status == 503 and rj.get("ok") is False
            and (rj.get("error") or {}).get("code") == "ACS_NOT_CONFIGURED"))
    R.ok("A", "A4", "GET /ready is a real verdict (200 ready or 503 "
                    "ACS_NOT_CONFIGURED envelope)",
         ready_ok, "HTTP %d body=%s" % (rr.status, rr.text[:200]))

    # A5 — /version: العقد مأخوذ من acs_build_info.build_info() حرفياً
    vr = http(backend + "/version", timeout=timeout)
    vj, ok = vr.json()
    state["version"] = vj if ok else None
    required = ("service", "version", "git_sha", "git_sha_short", "git_branch",
                "built_at", "provenance_verified", "schema_versions")
    problems = []
    if vr.status != 200:
        problems.append("HTTP %d" % vr.status)
    if not ok or not isinstance(vj, dict):
        problems.append("body is not a JSON object: %s" % vr.text[:120])
    else:
        for k in required:
            if k not in vj:
                problems.append("missing key %r" % k)
        sha = vj.get("git_sha")
        short = vj.get("git_sha_short")
        if isinstance(sha, str) and isinstance(short, str):
            expect_short = "unknown" if sha == "unknown" else sha[:12]
            if short != expect_short:
                problems.append("git_sha_short=%r does not derive from git_sha=%r"
                                % (short, sha))
        if not isinstance(vj.get("provenance_verified"), bool):
            problems.append("provenance_verified is not a boolean")
        elif vj.get("provenance_verified") != (sha != "unknown"
                                               and vj.get("built_at") != "unknown"):
            problems.append("provenance_verified contradicts git_sha/built_at")
        sv = vj.get("schema_versions")
        if not isinstance(sv, dict):
            problems.append("schema_versions is not an object")
        else:
            if sv.get("error_contract") != ERROR_CONTRACT:
                problems.append("schema_versions.error_contract=%r"
                                % sv.get("error_contract"))
            for k in ("engineering_changes", "api_base"):
                if k not in sv:
                    problems.append("schema_versions missing %r" % k)
        if "sk-ant" in vr.text or "/" in str(vj.get("built_at", "")):
            problems.append("/version exposed a secret or a filesystem path")
    R.ok("A", "A5", "GET /version matches the acs_build_info contract "
                    "(service/version/git_sha/git_sha_short/git_branch/built_at/"
                    "provenance_verified/schema_versions)",
         not problems, "; ".join(problems) if problems else vr.text[:220])

    # A6 — مسار غير موجود: مغلّف الخطأ المُعلن، لا صفحة HTML
    nr = http(backend + "/acs-production-verifier-no-such-route", timeout=timeout)
    nj, ok = nr.json()
    problems = []
    if nr.status != 404:
        problems.append("HTTP %d (expected 404)" % nr.status)
    if "<html" in nr.text.lower() or "<!doctype" in nr.text.lower():
        problems.append("an HTML page was returned instead of the envelope")
    if "Traceback" in nr.text:
        problems.append("a traceback was returned")
    if not ok or not isinstance(nj, dict):
        problems.append("body is not one valid JSON object: %s" % nr.text[:120])
    else:
        if nj.get("contract") != ERROR_CONTRACT:
            problems.append("contract=%r (expected %r)"
                            % (nj.get("contract"), ERROR_CONTRACT))
        if nj.get("ok") is not False:
            problems.append("ok=%r (expected false)" % nj.get("ok"))
        err = nj.get("error")
        if not isinstance(err, dict):
            problems.append("error is not an object")
        else:
            if set(err) != ENVELOPE_ERROR_FIELDS:
                problems.append("error fields=%s (expected %s)"
                                % (sorted(err), sorted(ENVELOPE_ERROR_FIELDS)))
            if err.get("code") != "ACS_NOT_FOUND":
                problems.append("error.code=%r" % err.get("code"))
            if not str(err.get("request_id") or "").strip():
                problems.append("error.request_id is empty")
    if not nr.header("x-request-id"):
        problems.append("no X-Request-ID response header")
    R.ok("A", "A6", "an invalid route returns the %s envelope "
                    "(ok:false, error.code, error.request_id) and NOT an HTML page"
         % ERROR_CONTRACT,
         not problems, "; ".join(problems) if problems else nr.text[:220])

    # A7/A8 — CORS
    allowed_origin = state["allowed_origin"]
    pr = http(backend + "/v1/understand", method="OPTIONS", timeout=timeout,
              headers={"Origin": allowed_origin,
                       "Access-Control-Request-Method": "POST",
                       "Access-Control-Request-Headers": "content-type"})
    allow = pr.header("access-control-allow-origin")
    R.ok("A", "A7", "a CORS preflight from the allowed origin (%s) is accepted"
         % allowed_origin,
         pr.reached and pr.status < 400 and allow == allowed_origin,
         "HTTP %d allow-origin=%r allow-methods=%r"
         % (pr.status, allow, pr.header("access-control-allow-methods")))

    ev = "https://acs-verifier-unrelated-origin.example"
    er = http(backend + "/v1/understand", method="OPTIONS", timeout=timeout,
              headers={"Origin": ev, "Access-Control-Request-Method": "POST",
                       "Access-Control-Request-Headers": "content-type"})
    bad = er.header("access-control-allow-origin")
    R.ok("A", "A8", "a CORS preflight from an unrelated origin is refused",
         er.reached and bad not in (ev, "*"),
         "allow-origin=%r (HTTP %d)" % (bad, er.status))


# ══════════════════════════════════════════════════════════════════════════
# المجموعة B — أصول الواجهة
# ══════════════════════════════════════════════════════════════════════════
def group_b(R, frontend, backend, timeout, state):
    print("\n── B · أصول الواجهة: الوحدات الحرِجة، Three.js 160، لا CDN، لا CSP violation ──")
    assets, declared, imap = critical_assets()
    state["assets"] = assets
    print("  derived asset list: %d file(s) — %d declared by tools/netlify-build.sh "
          "must=(), the rest from the import map in public/index.html"
          % (len(assets), len(declared)))

    root = state.get("frontend_root")
    if not root or not root.reached:
        why = classify_transport((root.transport_error if root else "")
                                 or "the frontend root was never reached")
        for cid, name in (
                ("B1", "every critical JS module returns 200 (%d file(s))" % len(assets)),
                ("B2", "the served Three.js declares REVISION 160"),
                ("B3", "no runtime CDN reference is served"),
                ("B4", "the CSP header is present and forbids external script origins"),
                ("B5", "no unexpected 404 among the critical assets"),
                ("B6", "every import specifier in the page resolves to a served module")):
            R.not_verified("B", cid, name, why)
        return

    if root.status != 200:
        why = ("the frontend root answered HTTP %d, so no asset could be measured "
               "against a healthy deploy" % root.status)
        for cid, name in (
                ("B1", "every critical JS module returns 200"),
                ("B2", "the served Three.js declares REVISION 160"),
                ("B3", "no runtime CDN reference is served"),
                ("B5", "no unexpected 404 among the critical assets"),
                ("B6", "every import specifier in the page resolves to a served module")):
            R.not_verified("B", cid, name, why)
        # الـCSP ما زال قابلاً للقياس من الترويسة نفسها
        csp = root.header("content-security-policy")
        R.ok("B", "B4", "the CSP header is present and forbids external script origins",
             bool(csp) and "script-src" in csp
             and not any(h in csp for h in CDN_HOSTS),
             "CSP=%s" % (csp[:240] or "<absent>"))
        return

    bad_status, empty, cdn_hits = [], [], []
    three_rev = None
    fetched = 0
    for path in assets:
        url = urllib.parse.urljoin(frontend + "/", path.lstrip("/"))
        ar = http(url, timeout=timeout)
        if not ar.reached:
            R.not_verified("B", "B1", "every critical JS module returns 200",
                           classify_transport(ar.transport_error))
            return
        fetched += 1
        if ar.status != 200:
            bad_status.append("%s → HTTP %d" % (path, ar.status))
            continue
        if len(ar.raw) < 64:
            empty.append("%s → %d bytes" % (path, len(ar.raw)))
        for host in CDN_HOSTS:
            if host in ar.text:
                cdn_hits.append("%s references %s" % (path, host))
        if path.endswith("three.module.js"):
            m = re.search(r"REVISION\s*=\s*['\"]([^'\"]+)['\"]", ar.text)
            three_rev = m.group(1) if m else None

    R.ok("B", "B1", "every critical JS module returns 200 (%d file(s) fetched)"
         % fetched,
         not bad_status and not empty,
         "; ".join(bad_status + empty) if (bad_status or empty)
         else "all %d assets 200 and non-empty" % fetched)

    R.ok("B", "B2", "the served Three.js declares REVISION %s" % THREE_REVISION,
         three_rev == THREE_REVISION,
         "REVISION=%r" % three_rev)

    page_cdn = [h for h in CDN_HOSTS if h in root.text]
    R.ok("B", "B3", "no runtime CDN reference is served (page or vendored modules)",
         not page_cdn and not cdn_hits,
         "; ".join(["index.html references " + h for h in page_cdn] + cdn_hits)
         or "no CDN host found in the page or in %d vendored module(s)" % fetched)

    csp = root.header("content-security-policy")
    csp_problems = []
    if not csp:
        csp_problems.append("no Content-Security-Policy response header")
    else:
        if "script-src" not in csp:
            csp_problems.append("no script-src directive")
        for h in CDN_HOSTS:
            if h in csp:
                csp_problems.append("CSP allows the CDN host %s" % h)
        m = re.search(r"connect-src([^;]*)", csp)
        connect = (m.group(1) if m else "")
        if backend.rstrip("/") not in connect:
            csp_problems.append("connect-src %r does not allow the backend %s"
                                % (connect.strip(), backend))
    R.ok("B", "B4", "the CSP header is present, forbids external script origins "
                    "and allows exactly the backend in connect-src",
         not csp_problems, "; ".join(csp_problems) if csp_problems else csp[:240])

    R.ok("B", "B5", "no unexpected 404 among the critical assets",
         not bad_status, "; ".join(bad_status) or "0 of %d assets 404ed" % fetched)

    # B6 يُقاس على الصفحة المخدومة نفسها لا على نسخة المستودع. صفحة بلا خريطة
    # استيراد وبلا أي specifier ليست «نجاحاً» — هي صفحة أخرى. لذلك يُشترط وجود
    # الاثنين فعلاً قبل أي حكم، وإلّا فهو FAIL مرصود لا PASS فارغ.
    served_specs = sorted(set(
        re.findall(r"three/addons/[A-Za-z0-9/_.\-]+\.js", root.text)))
    served_map = re.search(r'<script type="importmap">', root.text) is not None
    unresolved = []
    if not served_map:
        unresolved.append("the served page declares no <script type=\"importmap\">")
    if not served_specs:
        unresolved.append("the served page imports no three/addons module — this "
                          "is not the ACS studio page")
    for spec in served_specs:
        prefix = imap.get("three/addons/")
        if not prefix:
            unresolved.append("%s (no import-map prefix)" % spec)
            continue
        target = prefix + spec[len("three/addons/"):]
        if target not in assets:
            unresolved.append("%s → %s (never fetched)" % (spec, target))
        elif ("%s → HTTP" % target) in " ".join(bad_status):
            unresolved.append("%s → %s (did not return 200)" % (spec, target))
    R.ok("B", "B6", "the served page declares an import map and every "
                    "three/addons specifier in it resolves to a module that was "
                    "fetched 200 (%d specifier(s))" % len(served_specs),
         not unresolved, "; ".join(unresolved) or
         "%d import specifiers resolved through the import map and served"
         % len(served_specs))


# ══════════════════════════════════════════════════════════════════════════
# المجموعة G — أصل النشر (الجزء المقيس عبر HTTP)
# ══════════════════════════════════════════════════════════════════════════
def group_g(R, frontend, backend, expect_sha, state):
    print("\n── G · أصل النشر: SHA الخادم من /version وSHA الواجهة من ACS_BUILD_INFO ──")

    vj = state.get("version")
    if not state.get("backend_reachable"):
        R.not_verified("G", "G1", "the backend build SHA and timestamp are captured "
                                  "from GET /version",
                       classify_transport(
                           (state.get("backend_root").transport_error
                            if state.get("backend_root") else "")
                           or "the backend was never reached"))
    elif not isinstance(vj, dict):
        R.add("G", "G1", "the backend build SHA and timestamp are captured from "
                         "GET /version", FAIL,
              "/version did not return a JSON object")
    else:
        sha = str(vj.get("git_sha") or "")
        built = str(vj.get("built_at") or "")
        state["backend_sha"] = sha
        R.ok("G", "G1", "the backend build SHA and timestamp are captured from "
                        "GET /version",
             bool(sha) and sha != "unknown" and bool(built) and built != "unknown",
             "git_sha=%s git_branch=%s built_at=%s provenance_verified=%s"
             % (sha, vj.get("git_branch"), built, vj.get("provenance_verified")))

    root = state.get("frontend_root")
    if not root or not root.reached:
        R.not_verified("G", "G2", "the frontend page declares window.ACS_BUILD_INFO "
                                  "with a build SHA",
                       classify_transport((root.transport_error if root else "")
                                          or "the frontend was never reached"))
    else:
        # الصفحة قد تُسند كائناً حرفياً أو متغيّراً يُبنى من رموز نائبة يستبدلها
        # البناء (__ACS_GIT_SHA__). الحالتان تُميَّزان: إسناد موجود برمز نائب لم
        # يُستبدَل ليس provenance — هو بناء بلا هويّة، وهذا FAIL مرصود لا PASS.
        state["frontend_sha"] = ""
        assigned = re.search(r"window\.ACS_BUILD_INFO\s*=", root.text) is not None
        literal = re.search(r"window\.ACS_BUILD_INFO\s*=\s*(\{.*?\})\s*;",
                            root.text, re.S)
        placeholder = False
        if literal:
            try:
                info = json.loads(literal.group(1))
                if isinstance(info, dict) and info.get("git_sha"):
                    state["frontend_sha"] = str(info["git_sha"])
            except Exception:
                pass
        if not state["frontend_sha"]:
            m = re.search(r"git_sha\s*:\s*\"([^\"]*)\"", root.text)
            raw = m.group(1) if m else ""
            if re.match(r"^__[A-Z0-9_]+__$", raw or ""):
                placeholder = True
            elif re.match(r"^[0-9a-f]{7,40}$", raw or ""):
                state["frontend_sha"] = raw
        if not assigned:
            detail = ("the served page contains no window.ACS_BUILD_INFO "
                      "assignment; the frontend ships no build provenance, so a "
                      "deployed page cannot be tied to a revision")
        elif placeholder:
            detail = ("window.ACS_BUILD_INFO is assigned, but the build identity "
                      "token is still the literal placeholder — no build step "
                      "substituted it, so the deployed page is UNPROVENANCED and "
                      "cannot be tied to a revision")
        elif not state["frontend_sha"]:
            detail = ("window.ACS_BUILD_INFO is assigned but no build SHA could be "
                      "read out of the served bytes")
        else:
            detail = "frontend git_sha=%s" % state["frontend_sha"]
        R.ok("G", "G2", "the frontend page declares window.ACS_BUILD_INFO with a "
                        "substituted build SHA",
             bool(state["frontend_sha"]), detail)

    fsha, bsha = state.get("frontend_sha"), state.get("backend_sha")
    if not fsha or not bsha:
        R.not_verified("G", "G3", "the frontend and the backend report the same "
                                  "build SHA",
                       "one of the two SHAs was never observed "
                       "(frontend=%r backend=%r)" % (fsha or None, bsha or None))
    else:
        R.ok("G", "G3", "the frontend and the backend report the same build SHA",
             fsha == bsha, "frontend=%s backend=%s" % (fsha, bsha))

    if not expect_sha:
        R.not_verified("G", "G4", "the deployed revision matches the expected one",
                       "no expected revision was supplied; pass --expect-sha "
                       "<sha> to turn this into a measured check")
    else:
        observed = [s for s in (bsha, fsha) if s]
        if not observed:
            R.not_verified("G", "G4", "the deployed revision matches the expected one",
                           "no build SHA could be observed on either target")
        else:
            match = all(s.startswith(expect_sha) or expect_sha.startswith(s)
                        for s in observed)
            R.ok("G", "G4", "the deployed revision matches --expect-sha",
                 match, "expected=%s observed=%s" % (expect_sha, observed))


# ══════════════════════════════════════════════════════════════════════════
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="ACS live production verification (HTTP + frontend assets). "
                    "PASS / FAIL / NOT VERIFIED are never conflated.")
    ap.add_argument("--frontend", default=os.environ.get(
        "ACS_VERIFY_FRONTEND", DEFAULT_FRONTEND))
    ap.add_argument("--backend", default=os.environ.get(
        "ACS_VERIFY_BACKEND", DEFAULT_BACKEND))
    ap.add_argument("--expect-sha", default=os.environ.get("ACS_VERIFY_EXPECT_SHA", ""),
                    help="expected git SHA of the deployed revision")
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--json", default=os.path.join(OUTDIR, "verify_live.json"),
                    help="machine-readable summary path")
    args = ap.parse_args(argv)

    frontend = args.frontend.rstrip("/")
    backend = args.backend.rstrip("/")

    declared = declared_targets()
    print("ACS PRODUCTION VERIFICATION — live HTTP layer")
    print("  frontend : %s" % frontend)
    print("  backend  : %s" % backend)
    print("  started  : %s" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    print("\n── deployment targets as the repository declares them (static, "
          "cited only — never a runtime PASS) ──")
    print("  netlify.toml            publish=%r  connect-src=%r"
          % (declared["netlify_publish"], declared["netlify_connect_src"]))
    print("  render.yaml             ACS_ALLOWED_ORIGINS=%r"
          % declared["render_allowed_origins"])
    print("  acs_understand_api.py   _DEFAULT_ORIGIN=%r"
          % declared["api_default_origin"])
    print("  public/index.html       CONFIGURED_BASE=%r"
          % declared["page_configured_base"])

    R = Results()
    state = {"allowed_origin": declared["api_default_origin"] or frontend}

    group_a(R, frontend, backend, args.timeout, state)
    group_b(R, frontend, backend, args.timeout, state)
    group_g(R, frontend, backend, args.expect_sha.strip(), state)

    npass, nfail, nnv = R.count(PASS), R.count(FAIL), R.count(NV)
    if nfail:
        code = 1
    elif npass == 0:
        code = 2
    else:
        code = 0

    summary = {
        "schema": "acs-production-verification/1.0.0",
        "tool": "tests/production/verify_live.py",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "frontend": frontend,
        "backend": backend,
        "expect_sha": args.expect_sha.strip() or None,
        "declared_targets": declared,
        "groups": ["A", "B", "G"],
        "browser_groups_elsewhere": ["C", "D", "E", "F", "G(frontend runtime)"],
        "counts": {"pass": npass, "fail": nfail, "not_verified": nnv,
                   "total": len(R.rows)},
        "exit_code": code,
        "verdict": ("FAIL" if nfail else
                    ("NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED" if npass == 0
                     else "PASS")),
        "observed": {"frontend_reachable": bool(state.get("frontend_reachable")),
                     "backend_reachable": bool(state.get("backend_reachable")),
                     "frontend_sha": state.get("frontend_sha") or None,
                     "backend_sha": state.get("backend_sha") or None},
        "critical_assets": state.get("assets") or [],
        "checks": R.rows,
    }
    try:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with io.open(args.json, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        wrote = args.json
    except Exception as e:  # noqa: BLE001
        wrote = "<not written: %s>" % e

    print("\n" + "─" * 70)
    print("HTTP LAYER: %d PASS · %d FAIL · %d NOT VERIFIED (of %d checks)"
          % (npass, nfail, nnv, len(R.rows)))
    print("summary: %s" % wrote)
    if code == 2:
        print("VERDICT: %s — nothing was observed; no check is claimed as passing."
              % NV_SUFFIX)
    elif code == 1:
        print("VERDICT: FAIL — at least one check observed wrong behaviour.")
    else:
        print("VERDICT: PASS — no observed failure.")
    return code


if __name__ == "__main__":
    sys.exit(main())
