# -*- coding: utf-8 -*-
"""W1 — أعطال P0 أمنية وصحّية، كلٌّ منها مُعاد إنتاجه قبل إصلاحه.

    python3 tests/remediation/test_p0_hardening.py

خمسة أعطال، لا يمسّ أيٌّ منها استراتيجية الرموز ولا التقطيع (تلك الموجة W2):

  W1-A  حارس قنبلة الانضغاط كان يقيس **طبقة Flate واحدة** لكل مجرى، ويتخطّى
        صامتاً كل ما تعجز zlib عنه. مقيس: ملفّ ٧١٣ بايتاً يعلن
        `/Filter [/FlateDecode /FlateDecode]` يُقاس ٦١ ١٦٢ بايتاً ويمرّ،
        بينما pypdf — الذي يحترم السلسلة — يبني منه ٦٠ م.ب.

  W1-B  `EA.plan` يطبّق SAFE_NORMALIZATION على الكائن الممرَّر، لكنه يعمل في
        عاملٍ منفصل على نسخةٍ مُسلسَلة. فكان الردّ يقول «طُبِّقت أربع تطبيعات»
        ويُرجع نموذجاً لا يحوي واحدة منها، و`model_hash_*` يصف كائن العامل.

  W1-C  `acs_cpu_pool.run` كان يُطلق المقعد في أربع حالات، وأيُّ استثناءٍ خامس
        يهرب بلا إطلاق. عشرةُ تسريبات تُقفل التدقيق كلّه حتى إعادة التشغيل.

  W1-D  أربعةُ مواضع في طبقة الواجهة تنادي `classify_upstream` بلا `provider=`،
        فتُنسَب أعطالُنا نحن — بما فيها موت عمليتنا — إلى anthropic على نشرٍ
        deepseek.

  W1-E  `MAX_NOTES` يعدّ أربعة مفاتيح مسموحة وحدها. `{"kind": "A"×10⁷}` يمرّ.

كل شاهد سالب هنا يُعيد إدخال العطل الأصلي حرفياً ويثبت أنه يُكتشَف.
"""
import io
import os
import pickle
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_api_errors as E                                       # noqa: E402
import acs_cpu_pool as CPU                                       # noqa: E402
import acs_engineering_authority as EA                           # noqa: E402
import acs_upload_security as UP                                 # noqa: E402

p = [0]
f = [0]


def chk(name, cond, detail=""):
    if cond:
        p[0] += 1
        print("  ✓ %s" % name)
    else:
        f[0] += 1
        print("  ✗ %s  %s" % (name, detail))


def rd(path):
    return io.open(os.path.join(ROOT, path), encoding="utf-8").read()


# ─────────────────────────── W1-A · مولّد PDF عدائي ──────────────────────────
def pdf_with(stream_bytes, filt):
    """PDF صالح بصفحة واحدة، ومجرى محتوى يعلن `filt` حرفياً."""
    objs = [b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            b"/Contents 4 0 R /Resources << >> >>\nendobj\n",
            b"4 0 obj\n<< /Length " + str(len(stream_bytes)).encode()
            + b" /Filter " + filt + b" >>\nstream\n" + stream_bytes
            + b"\nendstream\nendobj\n"]
    out = b"%PDF-1.4\n"
    offs = []
    for o in objs:
        offs.append(len(out))
        out += o
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offs:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, x))
    return out


def legacy_flate_expansion(data, budget):
    """الحارس **قبل** W1-A، منسوخاً حرفياً — الشاهد السالب."""
    budget = int(budget)
    total = 0
    position = 0
    while position < len(data):
        start = data.find(b"stream", position)
        if start < 0:
            break
        cursor = start + 6
        if data[cursor:cursor + 2] == b"\r\n":
            cursor += 2
        elif data[cursor:cursor + 1] in (b"\n", b"\r"):
            cursor += 1
        end = data.find(b"endstream", cursor)
        if end < 0:
            break
        position = end + 9
        blob = data[cursor:end]
        if not blob:
            continue
        try:
            eng = zlib.decompressobj()
            room = budget - total + 1
            produced = len(eng.decompress(blob, room))
            while eng.unconsumed_tail and produced < room:
                produced += len(eng.decompress(eng.unconsumed_tail,
                                               room - produced))
        except zlib.error:
            continue
        total += produced
        if total > budget:
            return total, True
    return total, False


def model():
    return {"levels": [{"index": 0, "name": "F0", "template": "ground"}],
            "floors": {"ground": {"rooms": [
                {"id": "r1", "name": "store", "rect": [0, 0, 10.004, 8.0079]}]}},
            "meta": {"type": "warehouse"}}


def main():
    B = int(UP.ACS_UPLOAD_MAX_PDF_DECOMPRESSED_BYTES)
    PAY = b"A" * (60 * 1024 * 1024)
    s1 = zlib.compress(PAY, 9)
    s2 = zlib.compress(s1, 9)
    s3 = zlib.compress(s2, 9)
    rle = bytes([129, 0x41]) * 200000            # كل بايتين ⇒ ١٢٨ بايتاً

    # ═══ W1-A ═══════════════════════════════════════════════════════════════
    print("\n== W1-A · حارس قنبلة الانضغاط يتبع سلسلة المُرشِّحات كاملةً ==")
    BOMBS = (
        ("single /FlateDecode", s1, b"/FlateDecode"),
        ("nested [/FlateDecode /FlateDecode]", s2,
         b"[/FlateDecode /FlateDecode]"),
        ("triple [/Fl /Fl /Fl]", s3,
         b"[/FlateDecode /FlateDecode /FlateDecode]"),
        ("/RunLengthDecode", rle, b"/RunLengthDecode"),
        ("[/FlateDecode /RunLengthDecode]", zlib.compress(rle, 9),
         b"[/FlateDecode /RunLengthDecode]"),
    )
    for label, blob, filt in BOMBS:
        doc = pdf_with(blob, filt)
        t0 = time.perf_counter()
        _, over = UP._flate_expansion(doc, B)
        ms = (time.perf_counter() - t0) * 1000.0
        chk("%s is rejected" % label, over is True, "not flagged")
        chk("  …and measuring it costs under 2 s (the guard is not a bomb)",
            ms < 2000.0, "%.0f ms" % ms)

    # الشاهد السالب: الحارس القديم على نفس الحمولات.
    caught_old = sum(1 for _, blob, filt in BOMBS
                     if legacy_flate_expansion(pdf_with(blob, filt), B)[1])
    chk("NEGATIVE CONTROL — the pre-W1-A guard catches only 1 of the 5 "
        "(that is the defect, reproduced)", caught_old == 1, caught_old)
    nested_old = legacy_flate_expansion(
        pdf_with(s2, b"[/FlateDecode /FlateDecode]"), B)
    chk("  …and it measured the 713-byte nested bomb at only %d bytes"
        % nested_old[0], nested_old[1] is False and nested_old[0] < B)

    # لا رفض زائف: الملفّات البريئة تبقى مقبولة.
    for label, blob, filt in (
            ("a small legitimate /FlateDecode stream",
             zlib.compress(b"BT (hello) Tj ET", 9), b"/FlateDecode"),
            ("a JPEG image stream (/DCTDecode)",
             b"\xff\xd8\xff\xe0" + b"\x00" * 5000, b"/DCTDecode"),
            ("an uncompressed content stream", b"BT (hi) Tj ET", b"/ASCIIHexDecode")):
        _, over = UP._flate_expansion(pdf_with(blob, filt), B)
        chk("no false positive: %s" % label, over is False)

    up_src = rd("acs_upload_security.py")
    # المقيس هو أن السلسلة تُقرأ من البايتات، لا أن كلمة pypdf غائبة من تعليق
    # يشرح أننا لا نستعملها. فحصُ الاستدعاءات لا فحصُ النصّ.
    import ast as _a
    _ut = _a.parse(up_src)
    _chain = [n for n in _a.walk(_ut)
              if isinstance(n, _a.FunctionDef)
              and n.name in ("_declared_filters", "_decode_stage",
                             "_lzw_decode_len", "_rle_decode_len",
                             "_flate_expansion")]
    _uses_pypdf = [fn.name for fn in _chain for n in _a.walk(fn)
                   if isinstance(n, _a.Attribute) and isinstance(n.value, _a.Name)
                   and n.value.id == "pypdf"]
    chk("the filter chain is read from the stream dictionary, and the guard "
        "calls into pypdf nowhere — it must not depend on what it guards",
        "_FILTER_RE.search" in up_src and _uses_pypdf == [], _uses_pypdf)
    chk("image codecs terminate the chain instead of being measured",
        "_IMAGE_FILTERS" in rd("acs_upload_security.py"))
    chk("the LZW and RLE decoders return a LENGTH, not the bytes",
        "_lzw_decode_len" in rd("acs_upload_security.py")
        and "_rle_decode_len" in rd("acs_upload_security.py"))
    chk("the module still imports nothing dangerous",
        all(bad not in rd("acs_upload_security.py")
            for bad in ("import subprocess", "import tempfile", "import pickle")))

    # ═══ W1-B ═══════════════════════════════════════════════════════════════
    print("\n== W1-B · التطبيعات المُعلَنة موجودة في النموذج المُعاد ==")
    worker_copy = pickle.loads(pickle.dumps(model()))    # ما يستلمه العامل
    out = pickle.loads(pickle.dumps(EA.plan_with_model(worker_copy)))
    plan, returned = out["plan"], out["building"]
    chk("the planner still reports its safe normalisations",
        len(plan["safe_changes"]) >= 4, len(plan["safe_changes"]))
    chk("and the RETURNED model carries every one of them",
        returned.get("floor_height") == 3.2
        and returned.get("wall_h") == 3.0
        and returned.get("wall_t") == 0.15
        and returned["floors"]["ground"]["rooms"][0]["rect"]
        == [0.0, 0.0, 10.0, 8.01],
        returned.get("floor_height"))
    chk("the hashes describe the object that comes back",
        plan["model_hash_before"] == EA.model_hash(returned, "bld_0"))

    # الشاهد السالب: الهدف القديم — التطبيعات تبقى في العامل.
    legacy_worker = pickle.loads(pickle.dumps(model()))
    legacy_plan = pickle.loads(pickle.dumps(EA.plan(legacy_worker)))
    parent = model()
    chk("NEGATIVE CONTROL — with the old `ea_plan` target the parent's model "
        "gets none of them, while the response still declares them",
        len(legacy_plan["safe_changes"]) >= 4
        and parent.get("floor_height") is None
        and parent["floors"]["ground"]["rooms"][0]["rect"] == [0, 0, 10.004, 8.0079])
    chk("  …and its hash describes a different object than the one returned",
        legacy_plan["model_hash_before"] != EA.model_hash(parent, "bld_0"))

    chk("the authority model is unchanged: proposals are still not applied",
        plan["proposals"] == [] or all(
            pr.get("class") != "SAFE_NORMALIZATION" for pr in plan["proposals"]))
    api = rd("acs_understand_api.py")
    chk("the handler uses the target that returns the model",
        'await _validate("ea_plan_model"' in api)
    chk("and it normalises BEFORE counting rooms and levels",
        api.index("authority, normalised = await _engineering_authority")
        < api.index('nr = sum(len(f.get("rooms", []))'))
    chk("the new target is declared in the pool allow-list",
        CPU.TARGETS.get("ea_plan_model")
        == ("acs_engineering_authority", "plan_with_model"))
    chk("the old target stays declared too — nothing was removed",
        CPU.TARGETS.get("ea_plan") == ("acs_engineering_authority", "plan"))

    # ═══ W1-C ═══════════════════════════════════════════════════════════════
    print("\n== W1-C · كل مقعد مأخوذ يعود، مهما كان مسار الخروج ==")
    src = rd("acs_cpu_pool.py")
    run_src = src[src.index("async def run("):]
    # يُعدّ الاستدعاء الفعليّ وحده — لا ذكرُ الاسم في تعليق أو سلسلة توثيق.
    import ast as _ast
    _tree = _ast.parse(rd("acs_cpu_pool.py"))
    _run = [n for n in _ast.walk(_tree)
            if isinstance(n, _ast.AsyncFunctionDef) and n.name == "run"][0]
    _calls = [n for n in _ast.walk(_run)
              if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Name)
              and n.func.id == "release"]
    _finally = [n for n in _ast.walk(_run)
                if isinstance(n, _ast.Try) and n.finalbody]
    _in_finally = [c for c in _calls
                   if any(c in list(_ast.walk(st))
                          for t in _finally for st in t.finalbody)]
    chk("run() calls release() exactly once, and from a `finally`",
        len(_calls) == 1 and len(_in_finally) == 1,
        "%d call(s), %d in finally" % (len(_calls), len(_in_finally)))
    chk("release() is idempotent, so a `finally` cannot double-release",
        'released["v"]' in src)

    import asyncio

    class _Boom(Exception):
        pass

    class _FakePool(object):
        """مجمّع صغير حقيقي السيمافور، يحقن الاستثناء المطلوب عند الحلّ."""

        def __init__(self, exc):
            self.timeout_s = 5.0
            self.capacity = 3
            self._exc = exc
            self._sem = __import__("threading").BoundedSemaphore(3)
            self.taken = 0

        def submit(self, target, args, kwargs, timeout_s):
            self._sem.acquire()
            self.taken += 1
            done = {"v": False}

            def release():
                if done["v"]:
                    return
                done["v"] = True
                self.taken -= 1
                self._sem.release()

            fut = concurrent_future(self._exc)
            return fut, release

        def note_timeout(self):
            pass

        def note_crash(self):
            pass

        def note_wait(self, ms):
            pass

        def shutdown(self, wait=False):
            pass

        def unwrap(self, env):
            return env

    def concurrent_future(exc):
        import concurrent.futures as cf
        fut = cf.Future()
        if exc is None:
            fut.set_result({"ok": True, "value": 1})
        else:
            fut.set_exception(exc)
        return fut

    async def drive(exc, times):
        pool = _FakePool(exc)
        for _ in range(times):
            try:
                await CPU.run("validate_pdf", (b"",), pool=pool)
            except Exception:                                 # noqa: BLE001
                pass
        return pool

    for label, exc in (("an unexpected executor exception", _Boom("boom")),
                       ("a pickling failure", pickle.PicklingError("nope")),
                       ("a MemoryError from the worker", MemoryError())):
        pool = asyncio.get_event_loop().run_until_complete(drive(exc, 10)) \
            if False else asyncio.run(drive(exc, 10))
        chk("10 x %s leaves capacity intact" % label, pool.taken == 0,
            "%d seats still held" % pool.taken)
    ok_pool = asyncio.run(drive(None, 10))
    chk("10 successful runs leave capacity intact too", ok_pool.taken == 0)

    # ═══ W1-D ═══════════════════════════════════════════════════════════════
    print("\n== W1-D · عطلٌ محلّي لا يُنسَب إلى مزوّدٍ لا شأن له ==")
    # لا مطابقة نصّية: `classify_upstream(e)` سلسلةٌ جزئية من الصيغة الصحيحة.
    _api_tree = __import__("ast").parse(api)
    _ast2 = __import__("ast")
    _cu = [n for n in _ast2.walk(_api_tree)
           if isinstance(n, _ast2.Call) and isinstance(n.func, _ast2.Attribute)
           and n.func.attr == "classify_upstream"]
    _bare = [n for n in _cu
             if not any(k.arg == "provider" for k in n.keywords)]
    chk("no API-layer call site omits provider= any more",
        _cu and _bare == [], "%d of %d bare" % (len(_bare), len(_cu)))
    chk("every call site passes the RESOLVED provider, not a literal",
        api.count("classify_upstream(e, provider=_resolved_provider())")
        + api.count("classify_upstream(exc, provider=_resolved_provider())") >= 5,
        api.count("_resolved_provider()"))
    chk("the helper derives the name from the provider layer",
        "PROV.primary().provider" in api)
    saved = os.environ.get("ACS_LLM_PROVIDER")
    try:
        os.environ["ACS_LLM_PROVIDER"] = "deepseek"
        os.environ["ACS_LLM_API_KEY"] = "sk-" + "d" * 32
        err = E.classify_upstream(RuntimeError("worker died"),
                                  provider="deepseek")
        chk("a local worker death on a DeepSeek deployment is labelled deepseek",
            (err.upstream or {}).get("provider") == "deepseek",
            (err.upstream or {}).get("provider"))
        legacy = E.classify_upstream(RuntimeError("worker died"))
        chk("NEGATIVE CONTROL — omitting provider= still defaults to anthropic, "
            "which is exactly why the call sites had to be fixed",
            (legacy.upstream or {}).get("provider") == "anthropic")
    finally:
        os.environ.pop("ACS_LLM_API_KEY", None)
        if saved is None:
            os.environ.pop("ACS_LLM_PROVIDER", None)
        else:
            os.environ["ACS_LLM_PROVIDER"] = saved
    chk("genuine upstream classification is untouched",
        E.classify_upstream(TimeoutError("timed out")).code
        in (E.ACS_UPSTREAM_TIMEOUT, E.ACS_UPSTREAM_UNKNOWN))

    # ═══ W1-E ═══════════════════════════════════════════════════════════════
    print("\n== W1-E · سقف الملاحظات يقيس ما يصل التوجيه فعلاً ==")
    ns = {"E": E, "MAX_NOTES": 20000}
    block = api[api.index("#: سقوف مسح الوزن"):api.index("async def _read_capped")]
    exec(compile(block, "cap", "exec"), ns)
    cap = ns["_cap_notes"]

    def rejected(notes):
        try:
            cap(notes)
            return False
        except E.AcsApiError as err:
            return err.code == E.ACS_PAYLOAD_TOO_LARGE

    chk("the originally guarded key is still capped",
        rejected([{"text": "A" * 30000}]))
    for key in ("kind", "note", "label", "detail", "anything_at_all"):
        chk("an oversized `%s` key is now capped too" % key,
            rejected([{key: "A" * 10_000_000}]))
    chk("a nested oversized value is capped",
        rejected([{"payload": {"deep": {"deeper": "A" * 10_000_000}}}]))
    chk("40 notes x 5 000 000 chars (200 MB) is capped",
        rejected([{"kind": "A" * 5_000_000} for _ in range(40)]))
    chk("a normal note is still accepted",
        not rejected([{"text": "أضف باباً في الغرفة r1", "layer": "L1"}]))
    chk("four notes of 4 000 chars are still accepted",
        not rejected([{"text": "A" * 4000} for _ in range(4)]))

    deep = {"a": "x"}
    for _ in range(60):
        deep = {"n": deep}
    t0 = time.perf_counter()
    r_deep = rejected([deep])
    ms_deep = (time.perf_counter() - t0) * 1000.0
    chk("a 60-deep structure is refused rather than walked", r_deep)
    chk("  …and refusing it costs under 50 ms", ms_deep < 50.0, "%.1f ms" % ms_deep)
    wide = {str(i): "y" * 10 for i in range(50000)}
    t0 = time.perf_counter()
    r_wide = rejected([wide])
    ms_wide = (time.perf_counter() - t0) * 1000.0
    chk("a 50 000-key structure is refused rather than walked", r_wide)
    chk("  …and refusing it costs under 200 ms", ms_wide < 200.0,
        "%.1f ms" % ms_wide)

    # الشاهد السالب: العدّ القديم بأربعة مفاتيح.
    def legacy_cap(notes):
        total = 0
        for n in notes:
            for key in ("text", "layer", "floor", "room"):
                v = n.get(key) if isinstance(n, dict) else None
                if isinstance(v, str):
                    total += len(v)
        return total > 20000
    chk("NEGATIVE CONTROL — the four-key count accepts 10 000 000 chars in "
        "`kind` (the defect, reproduced)",
        legacy_cap([{"kind": "A" * 10_000_000}]) is False)
    chk("the scan bounds are declared, not buried",
        "_WEIGH_MAX_NODES" in api and "_WEIGH_MAX_DEPTH" in api)

    print("\n" + "=" * 62)
    print("P0 HARDENING: %d passed, %d failed" % (p[0], f[0]))
    print("PRE-PARSE BODY LIMIT: NOT IMPLEMENTED — the framework buffers and "
          "spools the whole multipart body before any handler runs, so no "
          "application-level check can bound bytes already accepted. This is "
          "a residual limitation, recorded not papered over; closing it needs "
          "a server/middleware layer and is deferred to W3.")
    return 1 if f[0] else 0


if __name__ == "__main__":
    sys.exit(main())
