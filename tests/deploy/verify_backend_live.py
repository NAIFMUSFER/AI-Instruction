# -*- coding: utf-8 -*-
"""تحقّق حيّ من الخادم المنشور — DNS، TLS، الحياة، الجاهزية، CORS، عقد JSON.

يعمل بمكتبة بايثون القياسية وحدها: لا يحتاج تثبيت شيء على الجهاز الذي يشغّله.

    python3 tests/deploy/verify_backend_live.py
    python3 tests/deploy/verify_backend_live.py https://acs-engine.onrender.com
    python3 tests/deploy/verify_backend_live.py --generation      # توليد حقيقي

بلا `--generation` لا يُنادى النموذج اللغوي إطلاقاً، فلا يُستهلك رصيد ولا حدّ
معدّل: الفحوص الروتينية يجب أن تكون مجّانية وإلا امتنع الناس عن تشغيلها.

رموز الخروج:
    0  اجتازت كل الفحوص المنفَّذة
    1  فشل فحص واحد على الأقل
    2  تعذّر الوصول أصلاً (DNS/TLS/شبكة) — NOT VERIFIED لا فشل منطقي
"""
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# W0 · العنوان يُقرأ من مصدره القانوني الواحد. كان يُقرأ من public/index.html
# وحده، وF-09 نقل CONFIGURED_BASE منها إلى public/app/boot/api-base.js — فصار
# هذا الملفّ يخرج بالرمز 2 «لا عنوان» **قبل فتح أي مقبس**، على كل جهاز، كل يوم،
# وهو السكربت الحيّ الوحيد في production-verify.yml. البوّابة الحيّة لم تكن
# تتحقّق من شيء. تُمسَح القشرة وكل سكربتات الإقلاع معاً، فلا يوجد عنوان ثانٍ
# يُكتب في أي مكان: هذا قارئٌ للمصدر القائم، لا مصدرٌ جديد.
PAGE = os.path.join(ROOT, "public", "index.html")
BOOT_DIR = os.path.join(ROOT, "public", "app", "boot")
GEN_PROMPT = "مستودع بسيط 20×15م، دور واحد، منطقة تخزين ومنطقة استقبال."

p = [0]
f = [0]
skipped = []


def chk(name, cond, detail=""):
    if cond:
        p[0] += 1
        print("  ✓ %s" % name)
    else:
        f[0] += 1
        print("  ✗ %s%s" % (name, ("  — %s" % detail) if detail else ""))
    return bool(cond)


def note(name, why):
    skipped.append(name)
    print("  ― %s: NOT VERIFIED — %s" % (name, why))


def _shipped_sources():
    """نصّ القشرة + كل سكربت إقلاع كلاسيكيّ، بالترتيب. لا شيء خارج المشحون."""
    texts = []
    for path in [PAGE] + sorted(
            os.path.join(BOOT_DIR, n) for n in (os.listdir(BOOT_DIR)
                                                if os.path.isdir(BOOT_DIR) else [])
            if n.endswith(".js")):
        try:
            with open(path, encoding="utf-8") as fh:
                texts.append(fh.read())
        except Exception:                                         # noqa: BLE001
            continue
    return "\n".join(texts)


def configured_base():
    """العنوان يُقرأ من المصدر المشحون — القشرة أو سكربتات الإقلاع.

    F-09 نقل الثابت من الصفحة إلى public/app/boot/api-base.js. البحث في
    الاثنين معاً يعني أن نقلة أخرى مستقبلاً لن تُعطِّل هذه البوّابة صامتةً،
    وأن العنوان يبقى مكتوباً مرّة واحدة في المستودع كلّه.
    """
    m = re.search(r'CONFIGURED_BASE\s*=\s*"([^"]*)"', _shipped_sources())
    return m.group(1).rstrip("/") if m else ""


def request(base, path, method="GET", body=None, headers=None, timeout=60):
    """يعيد (status, headers, text, error). لا يرفع استثناءً أبداً."""
    url = base + path
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), dict(r.headers), r.read().decode("utf-8", "replace"), None
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read().decode("utf-8", "replace"), None
    except Exception as e:                                        # noqa: BLE001
        return 0, {}, "", "%s: %s" % (type(e).__name__, str(e)[:200])


def _hget(headers, name):
    """رؤوس HTTP غير حسّاسة لحالة الأحرف؛ قاموس urllib ليس كذلك دائماً."""
    low = name.lower()
    for k, v in (headers or {}).items():
        if str(k).lower() == low:
            return v
    return ""


def as_json(text):
    try:
        return json.loads(text), True
    except Exception:                                             # noqa: BLE001
        return None, False


def main():
    args = [a for a in sys.argv[1:]]
    do_gen = "--generation" in args
    args = [a for a in args if not a.startswith("--")]
    base = (args[0] if args else configured_base()).rstrip("/")
    if not base:
        print("BACKEND LIVE: no base URL — CONFIGURED_BASE was not found in "
              "public/index.html nor in public/app/boot/*.js. Pass one "
              "explicitly, or restore the constant in its canonical source.")
        return 2
    host = re.sub(r"^https?://", "", base).split("/")[0]
    print("BACKEND LIVE VERIFICATION — %s" % base)
    print("generation call: %s" % ("ENABLED (--generation)" if do_gen
                                   else "SKIPPED (pass --generation to run it)"))

    # ── DNS ─────────────────────────────────────────────────────────────────
    print("\n── DNS ──")
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        addrs = sorted({i[4][0] for i in infos})
        chk("%s resolves (%d address(es))" % (host, len(addrs)), bool(addrs))
    except Exception as e:                                        # noqa: BLE001
        chk("%s resolves" % host, False, "%s: %s" % (type(e).__name__, e))
        print("\nDNS: FAIL — nothing downstream can be tested. "
              "This is the ERR_NAME_NOT_RESOLVED condition.")
        return 2

    # ── TLS ─────────────────────────────────────────────────────────────────
    print("\n── TLS ──")
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=20) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls:
                cert = tls.getpeercert()
                chk("TLS handshake succeeds and the certificate matches %s" % host,
                    bool(cert))
                chk("the negotiated protocol is TLS 1.2 or newer",
                    (tls.version() or "").replace("TLSv", "") >= "1.2", tls.version())
    except Exception as e:                                        # noqa: BLE001
        chk("TLS handshake to %s" % host, False, "%s: %s" % (type(e).__name__, e))
        return 2

    # ── الحياة والجاهزية ────────────────────────────────────────────────────
    print("\n── process, health and readiness ──")
    st, hd, tx, err = request(base, "/")
    if err:
        chk("the root endpoint answers", False, err)
        return 2
    rootj, ok = as_json(tx)
    chk("GET / answers 200 with valid JSON", st == 200 and ok, "HTTP %s" % st)
    chk("GET / identifies the service", bool(ok and rootj.get("service")))

    st, hd, tx, err = request(base, "/health")
    hj, ok = as_json(tx)
    chk("GET /health answers 200 with valid JSON", st == 200 and ok, "HTTP %s" % st)
    if ok:
        chk("/health declares ok/service/version",
            hj.get("ok") is True and hj.get("service") and hj.get("version"),
            json.dumps(hj, ensure_ascii=False)[:160])
        chk("/health declares model_configured and api_key_configured",
            "model_configured" in hj and isinstance(hj.get("api_key_configured"), bool))
        chk("/health never returns any credential material",
            "sk-ant" not in tx and "Bearer " not in tx)
        # W0 · كان هذا يثبّت claude-sonnet-5 حرفياً، فيصير أحمرَ على نشرٍ
        # deepseek صحيح تماماً. المُثبَّت الآن هو ما يجب أن يصحّ لأي مزوّد:
        # أن المعرّف المُعلَن غير فارغ وأنه **يطابق** ما حلّته طبقة المزوّد.
        llm = hj.get("llm") if isinstance(hj.get("llm"), dict) else {}
        chk("the deployed model identifier is declared and non-empty",
            bool(str(hj.get("model_configured") or "").strip()),
            str(hj.get("model_configured")))
        chk("/health exposes the resolved provider block",
            bool(llm.get("llm_provider")) and "llm_state" in llm,
            json.dumps(llm, ensure_ascii=False)[:160])
        chk("the provider resolved cleanly (no missing key or endpoint)",
            llm.get("llm_state") == "resolved", str(llm.get("llm_state")))
        chk("model_configured agrees with the resolved provider model",
            llm.get("llm_model") == hj.get("model_configured"),
            "%s vs %s" % (llm.get("llm_model"), hj.get("model_configured")))
        chk("the provider host is declared, and it is a host not a URL",
            llm.get("llm_base_host") is None
            or ("://" not in str(llm.get("llm_base_host"))
                and "/" not in str(llm.get("llm_base_host"))),
            str(llm.get("llm_base_host")))
        chk("/health leaks no credential through the provider block",
            "api_key" not in json.dumps(llm) or llm.get("api_key_configured") in (True, False))
        chk("the deployment has an API key configured",
            hj.get("api_key_configured") is True)

    st, hd, tx, err = request(base, "/ready")
    rj, ok = as_json(tx)
    chk("GET /ready answers valid JSON", ok, tx[:120])
    if ok:
        chk("/ready is a real verdict (200 ready, or 503 ACS_NOT_CONFIGURED)",
            (st == 200 and rj.get("ready") is True)
            or (st == 503 and rj.get("ok") is False
                and rj.get("error", {}).get("code") == "ACS_NOT_CONFIGURED"),
            "HTTP %s %s" % (st, tx[:120]))

    # ── عقد الأخطاء ─────────────────────────────────────────────────────────
    print("\n── error contract: every response is one valid JSON object ──")
    probes = [
        ("GET", "/definitely-not-a-route", None, 404, "ACS_NOT_FOUND"),
        ("POST", "/health", {}, 405, "ACS_METHOD_NOT_ALLOWED"),
        ("POST", "/v1/understand", {}, 422, "ACS_VALIDATION_FAILED"),
        ("POST", "/v1/understand", {"text": "   "}, 400, "ACS_BAD_REQUEST"),
    ]
    for method, path, body, want_status, want_code in probes:
        st, hd, tx, err = request(base, path, method=method, body=body)
        if err:
            chk("%s %s answers" % (method, path), False, err)
            continue
        j, ok = as_json(tx)
        chk("json.loads(response.text) succeeds for %s %s (HTTP %s)"
            % (method, path, st), ok, tx[:120])
        chk("%s %s -> HTTP %d %s" % (method, path, want_status, want_code),
            ok and st == want_status
            and j.get("ok") is False
            and j.get("error", {}).get("code") == want_code,
            "HTTP %s %s" % (st, (j or {}).get("error", {}).get("code")))
        if ok and isinstance(j, dict) and j.get("ok") is False:
            chk("  the envelope carries all five fields",
                set(j["error"]) == {"code", "message", "request_id",
                                    "retryable", "upstream"})
            chk("  the response carries an X-Request-ID header",
                bool(hd.get("X-Request-ID") or hd.get("x-request-id")))
        chk("  no HTML and no traceback is returned for %s %s" % (method, path),
            "<html" not in tx.lower() and "Traceback" not in tx)

    st, hd, tx, err = request(base, "/health",
                              headers={"X-Request-ID": "req_live_probe_1"})
    chk("a caller-supplied X-Request-ID is echoed back for correlation",
        (hd.get("X-Request-ID") or hd.get("x-request-id")) == "req_live_probe_1",
        str(hd.get("X-Request-ID")))

    # ── CORS ────────────────────────────────────────────────────────────────
    print("\n── CORS for the deployed frontend ──")
    origin = os.environ.get("ACS_FRONTEND_ORIGIN",
                            "https://sprightly-selkie-d906c3.netlify.app")
    st, hd, tx, err = request(base, "/v1/understand", method="OPTIONS", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    allow = hd.get("access-control-allow-origin") or hd.get("Access-Control-Allow-Origin")
    chk("the preflight for %s is granted" % origin, allow == origin,
        "allow-origin=%r (HTTP %s)" % (allow, st))
    # ملاحظة تشخيصية مهمّة: `Access-Control-Expose-Headers` **لا يظهر أبداً** في
    # رد الـpreflight. المواصفة تجعل الـpreflight يحمل allow-origin/methods/headers
    # وmax-age فقط، وexpose-headers يخصّ الرد الفعلي. فحصه على OPTIONS يعطي فشلاً
    # كاذباً دائماً — وهو سبب تقرير «X-Request-ID is not exposed» رغم صحّة الضبط.
    st2, hd2, tx2, err2 = request(base, "/health", headers={"Origin": origin})
    expose = _hget(hd2, "access-control-expose-headers")
    chk("the ACTUAL response (not the preflight) grants the page the origin",
        _hget(hd2, "access-control-allow-origin") == origin,
        str(_hget(hd2, "access-control-allow-origin")))
    chk("X-Request-ID is exposed on the actual response so the page can read it",
        "x-request-id" in expose.lower(), expose or "<none>")
    chk("Retry-After is exposed on the actual response so the page can honour it",
        "retry-after" in expose.lower(), expose or "<none>")
    chk("the preflight itself does not carry expose-headers "
        "(per the CORS spec — checking it there is a verifier bug)",
        not (hd.get("access-control-expose-headers")
             or hd.get("Access-Control-Expose-Headers")))
    st, hd, tx, err = request(base, "/v1/understand", method="OPTIONS", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    bad = hd.get("access-control-allow-origin") or hd.get("Access-Control-Allow-Origin")
    chk("an unlisted origin is not granted CORS", bad != "https://evil.example",
        str(bad))

    # ── توليد حقيقي (اختياري) ───────────────────────────────────────────────
    print("\n── real generation ──")
    if not do_gen:
        note("end-to-end generation", "not requested; pass --generation to spend "
                                      "one real model call")
    else:
        print("  prompt: %s" % GEN_PROMPT)
        t0 = time.time()
        st, hd, tx, err = request(base, "/v1/understand", method="POST",
                                  body={"text": GEN_PROMPT, "btype": "warehouse",
                                        "site_w": 20, "site_d": 15, "floors": 1},
                                  timeout=900)
        dt = time.time() - t0
        if err:
            chk("the generation request completed", False, err)
        else:
            j, ok = as_json(tx)
            chk("json.loads(response.text) succeeds for the generation response "
                "(HTTP %s, %.1fs)" % (st, dt), ok, tx[:160])
            if ok and st == 200:
                b = j.get("building") or {}
                chk("HTTP 200 carries a building object", bool(b))
                chk("the building declares a site", isinstance(b.get("site"), dict))
                chk("the building declares levels and floors",
                    bool(b.get("levels")) and bool(b.get("floors")))
                rooms = sum(len(fl.get("rooms", []))
                            for fl in (b.get("floors") or {}).values())
                chk("levels >= 1", len(b.get("levels") or []) >= 1,
                    str(len(b.get("levels") or [])))
                chk("rooms >= 2 (%d)" % rooms, rooms >= 2)
                chk("every room carries a well-formed rect — nothing truncated "
                    "mid-object reached the compiler",
                    all(isinstance(r.get("rect"), list) and len(r["rect"]) == 4
                        for fl in (b.get("floors") or {}).values()
                        for r in fl.get("rooms", [])))
                chk("one level was produced as requested",
                    len(b.get("levels") or []) == 1,
                    str(len(b.get("levels") or [])))
                gen = j.get("generation") or {}
                chk("the response declares which generation strategy ran",
                    bool(gen.get("strategy")), str(gen))
                chk("no stage stopped at max_tokens",
                    "max_tokens" not in (gen.get("stop_reasons") or []),
                    str(gen.get("stop_reasons")))
                # §2 — الالتقاط المطلوب حرفياً، بأرقام حقيقية من هذا النداء
                print("\n  ── §2 capture ──")
                print("  model            : %s" % (hj.get("model_configured")
                                                   if isinstance(hj, dict) else "?"))
                print("  strategy         : %s (%s)" % (gen.get("strategy"),
                                                        gen.get("size_class")))
                print("  single/multi     : %s" % ("multi-stage"
                      if gen.get("strategy") == "staged" else "single-stage"))
                print("  deep mode used   : %s" % (j.get("mode") == "deep"))
                print("  stages           : %s (escalations=%s)"
                      % (gen.get("stages"), gen.get("escalations")))
                print("  max out tokens   : %s" % gen.get("max_output_tokens"))
                print("  output tokens    : %s" % gen.get("output_tokens_total"))
                print("  input tokens     : %s" % gen.get("input_tokens_total"))
                print("  stop reasons     : %s" % (gen.get("stop_reasons") or []))
                print("  completion       : %d chars of building JSON"
                      % len(json.dumps(b, ensure_ascii=False)))
                print("  parse status     : json.loads(response.text) OK")
                for sd in (gen.get("stage_detail") or []):
                    print("    stage=%-7s depth=%s stop=%-10s out=%-6s max=%-6s "
                          "parsed=%s err=%s"
                          % (sd.get("stage"), sd.get("depth"), sd.get("stop_reason"),
                             sd.get("output_tokens"), sd.get("max_output_tokens"),
                             sd.get("parsed"), sd.get("error")))
                chk("the response reports coverage of the request",
                    isinstance(j.get("report"), dict))
                print("  levels=%s rooms=%s mode=%s issues=%s"
                      % (j.get("levels"), j.get("rooms"), j.get("mode"), j.get("issues")))
            elif ok:
                code = j.get("error", {}).get("code")
                chk("a failed generation is still a classified envelope",
                    j.get("ok") is False and bool(code), tx[:160])
                print("  generation did not succeed: HTTP %s %s — %s"
                      % (st, code, j.get("error", {}).get("message", "")[:140]))
                print("  request_id=%s" % j.get("error", {}).get("request_id"))

    print("\n" + "─" * 46)
    print("BACKEND LIVE: %d passed, %d failed%s"
          % (p[0], f[0], (", %d not verified" % len(skipped)) if skipped else ""))
    return 1 if f[0] else 0


if __name__ == "__main__":
    sys.exit(main())
