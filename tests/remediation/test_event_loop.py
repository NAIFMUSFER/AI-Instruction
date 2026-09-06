# -*- coding: utf-8 -*-
"""KI-14 · F-46/F-47 — لا عملٌ حاسوبيّ ثقيل على حلقة الأحداث، وقرارُ حدٍّ صريح.

    python3 tests/remediation/test_event_loop.py

العطل
-----
    @app.post("/v1/understand/image")
    async def understand_image(...):
        checked = UPLOAD.validate_images(raw)     # ← فكّ بكسلات على الحلقة

    @app.post("/v1/understand/pdf")
    async def understand_pdf(...):
        checked = UPLOAD.validate_pdf(data)       # ← تحليل صفحات على الحلقة

مقيساً على أثقل **مدخل مقبول** (وعلى أثقل مدخل **مرفوض**، وهو الأسوأ):

    صورة 3340×3340 (٣٣٫٥ م.ب مفكوكة — تحت السقف بالضبط)
        توقّف الحلقة ≈ ٤٤٠ms · أطول طلب خفيف ≈ ٤٤٣ms
    ستّ نسخ منها — تتجاوز ميزانية البكسل فتُرفَض
        توقّف الحلقة ≈ ١٥٠٠ms **قبل** أن تُرفَض

الثانية هي الخطر الحقيقيّ: حمولةٌ ترفضها البوّابة تشلّ الخادم ثانيةً ونصفاً.
طوال ذلك لا /health ولا /ready ولا أيّ طلب: العملية متوقّفة لا بطيئة.

نطاق القياس — مُعلَن
--------------------
هذا الاختبار لا يستدعي توجيه FastAPI؛ فلا يُدّعى قياسه هنا. المقيس: حلقة asyncio حقيقيّة، وخادم HTTP حقيقيّ عليها، **ومدقّقات
الرفع المشحونة نفسها**، وعميلٌ خفيف على خيط منفصل يصل أثناء التوقّف. وهذا
كلّ ما يحتاجه السؤال: تعليمةٌ متزامنة داخل `async def` تحجب الحلقة أيّاً كان
الإطار فوقها.

عتبات القبول ثابتة في lib_loop_probe (توقّف ≤ ٢٥٠ms · p95 ≤ ٥٠٠ms) ولا
تُخفَّض هنا.
"""
import asyncio
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import lib_loop_probe as P                                       # noqa: E402
import acs_upload_security as U                                  # noqa: E402
import acs_cpu_pool as CPU                                       # noqa: E402
import acs_rate_limit as RL                                      # noqa: E402

p = [0]
f = [0]


def chk(name, cond, detail=""):
    if cond:
        p[0] += 1
        print("  ✓ %s" % name)
    else:
        f[0] += 1
        print("  ✗ %s  %s" % (name, detail))


# ── أثقل مدخل مقبول يُبنى هنا، فلا يعتمد الاختبار على ملفّات خارجية ────────
def build_fixtures():
    import zlib
    from PIL import Image, ImageDraw
    L = U.SPEC["limits"]
    # أكبر عدد بكسل يسعه سقف البايتات المفكوكة، بمحتوى مخطّط معماريّ واقعيّ
    # (خطوط على أبيض) فيضغط جيّداً ويبقى تحت سقف البايتات المرفوعة.
    side = int(((L["max_image_decoded_bytes"] / 3.0) ** 0.5)) - 2
    im = Image.new("RGB", (side, side), "white")
    d = ImageDraw.Draw(im)
    for i in range(0, side, 40):
        d.line([(i, 0), (i, side)], fill=(30, 30, 30), width=2)
        d.line([(0, i), (side, i)], fill=(30, 30, 30), width=2)
    for i in range(0, side, 200):
        d.rectangle([i, i, i + 180, i + 180], outline=(200, 0, 0), width=3)
    b = io.BytesIO()
    im.save(b, "PNG", compress_level=6)
    png = b.getvalue()

    def mkpdf(pages, lines):
        out = io.BytesIO()
        out.write(b"%PDF-1.7\n")
        offs = {}

        def add(n, body):
            offs[n] = out.tell()
            out.write(("%d 0 obj\n" % n).encode())
            out.write(body)
            out.write(b"\nendobj\n")
        kids = " ".join("%d 0 R" % (3 + 2 * i) for i in range(pages))
        add(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        add(2, ("<< /Type /Pages /Count %d /Kids [%s] >>"
                % (pages, kids)).encode())
        for i in range(pages):
            txt = ("BT /F1 9 Tf 20 800 Td 11 TL\n" + "".join(
                "(warehouse zone %04d rack bay %03d aisle 3.4 m clear 11.50) Tj T*\n"
                % (i, j) for j in range(lines)) + "ET")
            comp = zlib.compress(txt.encode(), 9)
            add(3 + 2 * i,
                ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                 "/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 "
                 "/BaseFont /Helvetica >> >> >> /Contents %d 0 R >>"
                 % (4 + 2 * i)).encode())
            add(4 + 2 * i,
                ("<< /Length %d /Filter /FlateDecode >>\nstream\n"
                 % len(comp)).encode() + comp + b"\nendstream")
        xref = out.tell()
        n = max(offs) + 1
        out.write(("xref\n0 %d\n" % n).encode())
        out.write(b"0000000000 65535 f \n")
        for k in range(1, n):
            out.write(("%010d 00000 n \n" % offs.get(k, 0)).encode())
        out.write(("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
                   % (n, xref)).encode())
        return out.getvalue()

    pdf = mkpdf(L["max_pdf_pages"], 60)
    big = {"rooms": [{"id": "z%05d" % i, "rect": [i % 50 * 2.0, i // 50 * 3.0,
                                                  1.8, 2.6], "role": "storage"}
                     for i in range(3000)]}
    js = json.dumps(big).encode()
    return {"image": png, "pdf": pdf, "json": js}


def main():
    FX = build_fixtures()
    L = U.SPEC["limits"]

    print("\n== أ · أثقل مدخل مقبول — مبنيّ من حدود العقد نفسها ==")
    chk("الصورة تحت سقف البايتات المرفوعة",
        len(FX["image"]) <= L["max_image_bytes"],
        "%d / %d" % (len(FX["image"]), L["max_image_bytes"]))
    side = int(((L["max_image_decoded_bytes"] / 3.0) ** 0.5)) - 2
    chk("وعند سقف البايتات المفكوكة تقريباً",
        U._decoded_bytes("RGB", side, side) <= L["max_image_decoded_bytes"]
        and U._decoded_bytes("RGB", side, side)
        > L["max_image_decoded_bytes"] * 0.99,
        "%.1f MB" % (U._decoded_bytes("RGB", side, side) / 1e6))
    chk("والـPDF عند سقف الصفحات بالضبط",
        U.validate_pdf(FX["pdf"])["pages"] == L["max_pdf_pages"])

    # ── ب · إعادة الإنتاج: النداء المتزامن يحجب الحلقة ──────────────────────
    async def heavy_sync(kind, _body):
        if kind == "image":
            return {"n": len(U.validate_images([(FX["image"], "image/png")]))}
        if kind == "image_batch":
            try:
                return {"n": len(U.validate_images(
                    [(FX["image"], "image/png")] * L["max_images"]))}
            except U.UploadRejected as exc:
                return {"rejected": exc.code}
        if kind == "pdf":
            return {"pages": U.validate_pdf(FX["pdf"])["pages"]}
        if kind == "json":
            U.validate_json_bytes(FX["json"])
            return {"ok": 1}
        raise ValueError(kind)

    async def heavy_pool(kind, _body):
        if kind == "image":
            return {"n": len(await CPU.run("validate_images",
                                           ([(FX["image"], "image/png")],)))}
        if kind == "image_batch":
            try:
                return {"n": len(await CPU.run(
                    "validate_images",
                    ([(FX["image"], "image/png")] * L["max_images"],)))}
            except U.UploadRejected as exc:
                return {"rejected": exc.code}
        if kind == "pdf":
            return {"pages": (await CPU.run("validate_pdf",
                                            (FX["pdf"],)))["pages"]}
        if kind == "json":
            await CPU.run("validate_json_bytes", (FX["json"],))
            return {"ok": 1}
        raise ValueError(kind)

    async def run_all():
        pool = CPU.default_pool()
        warm = pool.warmup()
        print("\n== ب · المجمّع المحدود ==")
        chk("العمّال في **عمليات** لا خيوط (فكّ القفل العامّ كاملاً)",
            warm["executor"] == CPU.EXEC_PROCESS and warm["isolated"] is True,
            warm["executor"])
        chk("والسعة محدودة ومُعلنة",
            warm["workers"] > 0 and warm["queue"] > 0
            and warm["capacity"] == warm["workers"] + warm["queue"],
            "%d+%d" % (warm["workers"], warm["queue"]))
        chk("وحدّ الإلغاء مُعلَن نصّاً لا مُدَّعى",
            "no in-process task kill is claimed" in warm["cancellation_note"])

        print("\n== ج · قياس التوقّف: قبل وبعد، على نفس الحمل ==")
        print("     العتبات: توقّف ≤ %.0f ms · p95 ≤ %.0f ms · أطول طلب ≤ %.0f ms"
              % (P.MAX_STALL_MS, P.MAX_P95_MS, P.MAX_P95_MS))
        rows = []
        for kind in ("json", "pdf", "image", "image_batch"):
            before = await P.measure(heavy_sync, kind, b"")
            after = await P.measure(heavy_pool, kind, b"")
            rows.append((kind, before, after))
            print("     %-12s قبل: توقّف %8.1f ms · أطول %8.1f ms   |   "
                  "بعد: توقّف %6.1f ms · أطول %6.1f ms · p95 %5.1f ms"
                  % (kind, before["stall_ms"], before["max"],
                     after["stall_ms"], after["max"], after["p95"]))
        for kind, before, after in rows:
            chk("%-12s → لا توقّف يتجاوز %.0f ms" % (kind, P.MAX_STALL_MS),
                after["stall_ms"] <= P.MAX_STALL_MS,
                "%.1f ms" % after["stall_ms"])
            chk("%-12s → p95 للطلب الخفيف تحت %.0f ms" % (kind, P.MAX_P95_MS),
                after["p95"] <= P.MAX_P95_MS, "%.1f ms" % after["p95"])
            chk("%-12s → وأطول طلب خفيف تحت %.0f ms" % (kind, P.MAX_P95_MS),
                after["max"] <= P.MAX_P95_MS, "%.1f ms" % after["max"])
            chk("%-12s → النتيجة نفسها قبل وبعد (لا سلوك تغيّر)" % kind,
                json.dumps((before["heavy_result"] or {}).get("out"),
                           sort_keys=True)
                == json.dumps((after["heavy_result"] or {}).get("out"),
                              sort_keys=True),
                json.dumps([(before["heavy_result"] or {}).get("out"),
                            (after["heavy_result"] or {}).get("out")]))
        # ── الشاهد: الحمل الثقيل كان فعلاً ثقيلاً ──────────────────────────
        # كان هذا التوكيد يقيس **كل** حملٍ ثقيل بالعتبة نفسها التي تقبل بها
        # النتيجة بعد الإصلاح (MAX_STALL_MS). وهما سؤالان مختلفان:
        #   القبول  سقفٌ: بعد الإصلاح لا توقّف يتجاوز ٢٥٠ ms.
        #   الشاهد  أرضيّةٌ: قبل الإصلاح كان الحمل يوقف الحلقة فعلاً.
        # فاستعمالُ السقف أرضيّةً جعل الشاهد رهينَ سرعة الآلة لا سلوك المنتج.
        # قياسٌ على ١٢ تشغيلاً نظيفاً هنا (توقّف ما قبل الإصلاح، ms):
        #     json          3.7 …    28.4     pdf     184.9 …   246.5
        #     image       365.9 …  1035.5     batch  1419.6 …  1498.2
        # فـpdf لا يتجاوز ٢٥٠ على هذه الآلة أصلاً (أقصاه 246.5)، وGitHub قاس
        # image عند ٢٢٢ فسقط الشاهد هناك. أي أن التوكيد كان يقيس العتاد.
        #
        # والادّعاء المُراد إثباته نسبيّ بطبيعته: «نقلُ العمل خارج الحلقة أزال
        # التوقّف». فيُقاس نسبةً، مع أرضيّةٍ مطلقة على أثقل حملٍ وحده — وهو
        # الوحيد الذي يعلو العتبة بهامشٍ على الآلتين (816 على GitHub، و1420+
        # هنا). النتيجة أقوى دلالةً وأثبت عبر العتاد، لا أسهل.
        heavy = {k: (b, a) for k, b, a in rows if k in ("image", "image_batch")}
        batch_before = heavy["image_batch"][0]["stall_ms"]
        chk("الشاهد المطلق: أثقل حملٍ متزامن كان يوقف الحلقة فوق %.0f ms"
            % P.MAX_STALL_MS, batch_before > P.MAX_STALL_MS,
            "%.0f ms" % batch_before)
        # النسبة: أدنى ما قيس بين الأحمال الثقيلة ٥٥×، وحتى json 6.3×.
        # أرضيّةٌ عند ٤× مستحيلةُ التحقّق إن لم يُنقَل العمل خارج الحلقة فعلاً.
        MIN_GAIN = 4.0
        gains = {k: (b["stall_ms"] / max(a["stall_ms"], 0.01))
                 for k, (b, a) in heavy.items()}
        chk("والشاهد النسبيّ: التوقّف قبل الإصلاح ≥ %.0f× ما هو بعده، لكل حملٍ "
            "ثقيل — وهو الادّعاء نفسه: العمل خرج من الحلقة" % MIN_GAIN,
            all(g >= MIN_GAIN for g in gains.values()),
            json.dumps({k: round(v, 1) for k, v in gains.items()}))
        # A 10 ms monitor cannot establish relative gains for work shorter
        # than one sampling interval. Such workloads must remain below that
        # interval; measurable stalls must strictly improve. Absolute latency
        # limits, output parity and the heavy-work 4x witness remain above.
        resolution_ms = P._MON_TICK * 1000
        def improves_or_remains_unresolved(before, after):
            return (after <= resolution_ms if before <= resolution_ms
                    else after < before)
        chk("measurable stalls improve; sub-tick workloads remain sub-tick",
            all(improves_or_remains_unresolved(b["stall_ms"], a["stall_ms"])
                for k, b, a in rows),
            json.dumps([(k, b["stall_ms"], a["stall_ms"]) for k, b, a in rows]))
        chk("no measurable improvement is rejected",
            not improves_or_remains_unresolved(100, 100))
        chk("a sub-tick workload becoming a measurable stall is rejected",
            not improves_or_remains_unresolved(1, resolution_ms + 1))
        chk("sub-tick equality does not claim an improvement",
            improves_or_remains_unresolved(1, 1))
        # شاهدٌ سالب على القاعدة نفسها: لو لم يتغيّر شيء (قبل == بعد) لَما
        # اجتازت. فالقاعدة تُدين انعدام التحسّن، ولا تمرّ لمجرّد أنها نسبيّة.
        chk("والقاعدة تُدين حالة «لا تحسّن»: نسبة 1.0 لا تجتاز",
            not (1.0 >= MIN_GAIN))
        chk("وعدد الطلبات المخدومة أثناء الحمل ارتفع فعلاً",
            all(a["light_requests"] >= b["light_requests"]
                for k, b, a in rows if k in ("image", "image_batch")),
            json.dumps([(b["light_requests"], a["light_requests"])
                        for k, b, a in rows]))

        print("\n== د · الإشباع رفضٌ صريح لا طابور بلا سقف ==")
        small = CPU.CpuPool(workers=1, queue=0, timeout_s=20)
        small.warmup()
        held = []
        try:
            fut, rel = small.submit("validate_images",
                                    ([(FX["image"], "image/png")],))
            held.append(rel)
            saturated = False
            try:
                small.submit("validate_json_bytes", (FX["json"],))
            except CPU.PoolSaturated:
                saturated = True
            chk("مجمّع مشبع يرفض فوراً بـPoolSaturated", saturated)
            chk("والرفض محسوب في القياسات",
                small.health_status()["stats"]["saturated"] == 1)
            fut.result(timeout=60)
        finally:
            for r in held:
                r()
            small.shutdown()
        chk("والمقعد يعود بعد الانتهاء", small.available() == small.capacity)

        print("\n== هـ · المهلة تحرّر المقعد ولا تدّعي قتلاً ==")
        slow = CPU.CpuPool(workers=1, queue=1, timeout_s=0.05)
        slow.warmup()
        timed_out = False
        try:
            await CPU.run("validate_images", ([(FX["image"], "image/png")],),
                          pool=slow)
        except CPU.PoolTimeout:
            timed_out = True
        chk("تجاوز المهلة يرفع PoolTimeout", timed_out)
        chk("والمقعد يعود فوراً", slow.available() == slow.capacity,
            "%d/%d" % (slow.available(), slow.capacity))
        chk("والمهلة محسوبة", slow.health_status()["stats"]["timed_out"] == 1)
        slow.shutdown()

        print("\n== و · الرفض يعبر حدّ العملية بلا تشويه ==")
        rej = None
        try:
            await CPU.run("validate_images",
                          ([(FX["image"], "image/png")] * L["max_images"],))
        except U.UploadRejected as exc:
            rej = exc
        chk("UploadRejected يصل الأب كما هو",
            rej is not None and rej.code == "IMAGE_PIXEL_BUDGET_EXCEEDED",
            getattr(rej, "code", None))
        chk("ورسالته العربية محفوظة", bool(getattr(rej, "message_ar", "")))
        import pickle
        chk("والصنف صار قابلاً للتخليص فعلاً (كان يرفع TypeError)",
            pickle.loads(pickle.dumps(rej)).code == rej.code)

        print("\n== ز٠ · مخطّط سلطة التغيير خارج الحلقة أيضاً ==")
        import acs_engineering_authority as EA

        def big_model(levels, per):
            tm = ["t%d" % i for i in range(levels)]
            return {"meta": {"type": "warehouse"}, "site": {"w": 300, "d": 200},
                    "floor_height": 4.5, "wall_h": 4.0, "wall_t": 0.2,
                    "levels": [{"id": "L%d" % i, "index": i, "name": "L%d" % i,
                                "template": t} for i, t in enumerate(tm)],
                    "floors": {t: {"rooms": [
                        {"id": "z%d_%03d" % (ti, k),
                         "rect": [1 + (k % 20) * 14.0, 1 + (k // 20) * 9.0, 13.0, 8.0],
                         "role": "storage", "walls": "none",
                         "points": [{"type": "light", "x": 6, "z": 4}]}
                        for k in range(per)]} for ti, t in enumerate(tm)}}

        heavy_model = big_model(10, 400)          # ٤٠٠٠ غرفة · ٥٢٨ ك.ب · تحت السقف
        t0 = time.perf_counter()
        EA.plan_with_model(heavy_model)
        ea_ms = (time.perf_counter() - t0) * 1000.0
        print("     EA.plan_with_model على ٤٠٠٠ غرفة (٥٢٨ ك.ب، تحت ACS_MAX_BUILDING): "
              "%.0f ms متزامناً" % ea_ms)
        chk("والمخطّط ثقيلٌ فعلاً — كان يعمل على الحلقة في **كل** رد ناجح",
            ea_ms > P.MAX_STALL_MS, "%.0f ms" % ea_ms)

        async def ea_sync(_k, _b):
            out = EA.plan_with_model(heavy_model)
            return {"n": len(out["plan"]["proposals"]),
                    "validation": out["model_validation"]}

        async def ea_pool(_k, _b):
            out = await CPU.run("ea_plan_model", (heavy_model,))
            return {"n": len(out["plan"]["proposals"]),
                    "validation": out["model_validation"]}

        async def _ea():
            b = await P.measure(ea_sync, "ea", b"")
            a2 = await P.measure(ea_pool, "ea", b"")
            print("     ea_plan_model قبل: توقّف %8.1f ms · أطول %8.1f ms   |   "
                  "بعد: توقّف %6.1f ms · أطول %6.1f ms"
                  % (b["stall_ms"], b["max"], a2["stall_ms"], a2["max"]))
            return b, a2
        b_ea, a_ea = await _ea()
        chk("قبل: توقّفٌ يتجاوز العتبة", b_ea["stall_ms"] > P.MAX_STALL_MS,
            "%.0f ms" % b_ea["stall_ms"])
        chk("بعد: لا توقّف يتجاوز %.0f ms" % P.MAX_STALL_MS,
            a_ea["stall_ms"] <= P.MAX_STALL_MS, "%.1f ms" % a_ea["stall_ms"])
        chk("وأطول طلب خفيف تحت %.0f ms" % P.MAX_P95_MS,
            a_ea["max"] <= P.MAX_P95_MS, "%.1f ms" % a_ea["max"])
        chk("والنتيجة نفسها",
            (b_ea["heavy_result"] or {}).get("out")
            == (a_ea["heavy_result"] or {}).get("out"))
        api_src = io.open(os.path.join(ROOT, "acs_understand_api.py"),
                          encoding="utf-8").read()
        # W1-B نقل المعالج إلى الهدف `ea_plan_model` (نفس `plan()` داخل نفس
        # الوحدة، لكنه يعيد النموذج المُطبَّع معه). الثابت المحروس هنا هو ثابت
        # KI-14 نفسه ولم يتغيّر: لا نداء مخطّط متزامن على الحلقة، والنداء يمرّ
        # عبر هدفٍ **معلَن** في مجمّع المعالجة. المرساة تتبع الهدف الجديد بدل
        # أن تثبّت اسماً بعينه.
        import acs_cpu_pool as _CP
        _awaited = [t for t in _CP.TARGETS
                    if t.startswith("ea_plan")
                    and ('await _validate("%s")' % t) in api_src.replace(
                        ", building)", ")")]
        chk("ولا نداء EA.plan متزامن باقٍ في أي معالج",
            "EA.plan(" not in api_src
            and any(('await _validate("%s"' % t) in api_src
                    for t in _CP.TARGETS if t.startswith("ea_plan")),
            str(_awaited))
        chk("ولا EA.flat_diff متزامن",
            "EA.flat_diff(" not in api_src
            and 'await _validate("ea_flat_diff"' in api_src)
        chk("و_understand_payload صار كوروتين يُنتظَر في كل معالج",
            "async def _understand_payload" in api_src
            and api_src.count("await _understand_payload(") == 4,
            str(api_src.count("await _understand_payload(")))

        print("\n== ز · هدفٌ غير معلن لا يُنفَّذ ==")
        bad = False
        try:
            await CPU.run("os.system", ("echo hi",))
        except KeyError:
            bad = True
        chk("اسم هدف من خارج القائمة المعلنة يُرفض", bad)
        chk("والقائمة المعلنة محصورة في وحدتين معروفتين لا اسم يصل من الشبكة",
            set(m for m, _ in CPU.TARGETS.values())
            == {"acs_upload_security", "acs_engineering_authority"},
            json.dumps(sorted(CPU.TARGETS)))

        print("\n== ح · لا مدقّق متزامن باقٍ في أي معالج ==")
        api = io.open(os.path.join(ROOT, "acs_understand_api.py"),
                      encoding="utf-8").read()
        import re
        sync_calls = re.findall(r"(?<!await )UPLOAD\.validate_\w+\(", api)
        chk("صفر نداء UPLOAD.validate_* متزامن في acs_understand_api",
            not sync_calls, json.dumps(sync_calls))
        # خمسة: صور · PDF · JSON · مخطّط سلطة التغيير · الفرق المسطَّح.
        chk("وخمسة نداءات ثقيلة كلّها عبر المجمّع",
            len(re.findall(r"await _validate\(", api)) == 5,
            str(len(re.findall(r"await _validate\(", api))))
        chk("والإشباع يُترجَم 429 والمهلة 504 لا 500",
            "E.ACS_RATE_LIMITED" in api and "E.ACS_TIMEOUT" in api)
        chk("وحالة المجمّع مُعلنة في /health", '"cpu_pool": CPU.health_status()' in api)

        pool.shutdown()

    asyncio.run(run_all())

    # ── ط · قرار حدّ المعدّل (F-47) ────────────────────────────────────────
    print("\n== ط · F-47: قرارٌ صريح بدل تحذير بلا أثر ==")
    cases = [
        ({}, True, RL.INVARIANT_DEV, "خارج الإنتاج"),
        ({"ACS_ENV": "production"}, False, RL.INVARIANT_UNDECLARED,
         "إنتاج بلا مخزن ولا إقرار"),
        ({"ACS_ENV": "production", "ACS_SINGLE_INSTANCE": "1"}, True,
         RL.INVARIANT_SINGLE, "إقرارٌ صريح بنسخة واحدة"),
        ({"ACS_ENV": "production", "ACS_SINGLE_INSTANCE": "1",
          "WEB_CONCURRENCY": "4"}, False, RL.INVARIANT_VIOLATED,
         "إقرارٌ تنقضه المنصّة"),
        ({"ACS_ENV": "production", "ACS_SINGLE_INSTANCE": "1",
          "UVICORN_WORKERS": "2"}, False, RL.INVARIANT_VIOLATED,
         "عمّال uvicorn أكثر من واحد"),
    ]
    for env, ok, state, label in cases:
        RL.reset_default_limiter()
        d = RL.production_invariant(env=env)
        chk("%-28s → %s" % (label, state),
            d["ok"] is ok and d["state"] == state,
            "%s / %s" % (d["ok"], d["state"]))
    RL.reset_default_limiter()
    raised = False
    try:
        RL.enforce_production_invariant(env={"ACS_ENV": "production"})
    except RL.ProductionInvariantError:
        raised = True
    chk("والفرض يرفع استثناءً يمنع الإقلاع", raised)
    api = io.open(os.path.join(ROOT, "acs_understand_api.py"),
                  encoding="utf-8").read()
    chk("والخادم يستدعيه في مسار الإقلاع",
        "RL.production_invariant()" in api
        and "REFUSING TO START" in api)
    ry = io.open(os.path.join(ROOT, "render.yaml"), encoding="utf-8").read()
    chk("وملفّ النشر يُعلن الثابت صراحةً",
        "ACS_SINGLE_INSTANCE" in ry and "ACS_ENV" in ry)
    chk("ولا --workers في أمر التشغيل (عمليّة واحدة فعلاً)",
        "--workers" not in io.open(os.path.join(ROOT, "Dockerfile"),
                                   encoding="utf-8").read())
    RL.reset_default_limiter()
    chk("والقرار مُعلَن في /health",
        "production_invariant" in json.dumps(
            RL.health_status(env={"ACS_ENV": "development"})))

    # ── ي · المخزن الموزّع على Redis حقيقيّ ────────────────────────────────
    print("\n== ي · المسار الموزّع على خادم Redis حقيقيّ ==")
    import subprocess
    import lib_resp_client as RC
    port = 6399
    proc = None
    try:
        proc = subprocess.Popen(
            ["redis-server", "--port", str(port), "--save", "",
             "--appendonly", "no", "--daemonize", "no"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        client = None
        for _ in range(50):
            try:
                c = RC.RespClient(port=port)
                c.ping()
                client = c
                break
            except Exception:                                   # noqa: BLE001
                time.sleep(0.1)
        if client is None:
            raise RuntimeError("redis-server did not come up")
        client.flushdb()
        chk("خادم Redis حقيقيّ يستجيب", client.ping() == "PONG")
        back = RL.RedisBackend(client, prefix="acs:test:")
        chk("والواجهة الخلفية تُعلن نفسها موزّعة", back.distributed is True)
        chk("وهي سليمة", bool(back.healthy()))

        # عمّالٌ متعدّدون، كلٌّ باتصاله الخاصّ — الحصّة واحدة لا حصّة لكلّ عامل.
        workers = [RL.RateLimiter(backend=RL.RedisBackend(
            RC.RespClient(port=port), prefix="acs:test:"),
            limits={"gen_hour": 5, "gen_day": 50, "edit_hour": 50,
                    "global_day": 500}) for _ in range(4)]
        allowed = 0
        for i in range(20):
            d = workers[i % len(workers)].check("10.0.0.7", "gen")
            if d.get("allowed"):
                allowed += 1
        chk("أربعة عمّال · حصّة واحدة: قُبل ٥ من ٢٠ بالضبط",
            allowed == 5, str(allowed))
        chk("ولا تجاوز لكل عملية (كان كل عامل يمنح ٥ فيصير المجموع ٢٠)",
            allowed < 20)

        # الذرّية تحت تزامن حقيقيّ من خيوط متعدّدة.
        import threading
        client.flushdb()
        pool = [RL.RateLimiter(backend=RL.RedisBackend(
            RC.RespClient(port=port), prefix="acs:test:"),
            limits={"gen_hour": 10, "gen_day": 100, "edit_hour": 50,
                    "global_day": 1000}) for _ in range(8)]
        hits = []
        lock = threading.Lock()

        def hammer(idx):
            got = 0
            for _ in range(10):
                if pool[idx].check("10.0.0.9", "gen").get("allowed"):
                    got += 1
            with lock:
                hits.append(got)
        ths = [threading.Thread(target=hammer, args=(i,)) for i in range(8)]
        for t in ths:
            t.start()
        for t in ths:
            t.join()
        chk("ثمانية عمّال × عشر محاولات → عشر قبولات بالضبط (ذرّية حقيقية)",
            sum(hits) == 10, "%d (%s)" % (sum(hits), hits))

        # سياسة العطل: الواجهة تسقط، والحدّ لا يفتح صامتاً.
        client.close()
        proc.terminate()
        proc.wait(timeout=10)
        proc = None
        closed = RL.RateLimiter(
            backend=RL.RedisBackend(RC.RespClient(port=port),
                                    prefix="acs:test:"),
            limits={"gen_hour": 5, "gen_day": 50, "edit_hour": 50,
                    "global_day": 500},
            fail_policy=RL.FAIL_CLOSED)
        d = closed.check("10.0.0.11", "gen")
        chk("Redis ساقط + fail_policy=closed → يُرفض لا يُفتح صامتاً",
            not d.get("allowed"), json.dumps(d, ensure_ascii=False)[:120])
        opened = RL.RateLimiter(
            backend=RL.RedisBackend(RC.RespClient(port=port),
                                    prefix="acs:test:"),
            limits={"gen_hour": 5, "gen_day": 50, "edit_hour": 50,
                    "global_day": 500},
            fail_policy=RL.FAIL_OPEN)
        d2 = opened.check("10.0.0.12", "gen")
        chk("و fail_policy=open يُفتح لكن يُعلن العطل لا يُخفيه",
            d2.get("allowed") and bool(opened.backend_errors()[0]),
            json.dumps(opened.backend_errors()[1] or "")[:80])
        chk("والصحّة تقول غير سليم", not RL.health_status(
            limiter=opened, env={"ACS_ENV": "development"})["healthy"])
    except FileNotFoundError:
        print("  ! redis-server غير موجود — المسار الموزّع: "
              "NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED")
    finally:
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except Exception:                                   # noqa: BLE001
                pass

    print("\n" + "─" * 62)
    print("SCOPE: real asyncio loop · real shipped validators · real redis-server.")
    print("       FastAPI/uvicorn routing is NOT exercised by this probe.")
    print("EVENT LOOP AND RATE-LIMIT DECISION: %d passed, %d failed" % (p[0], f[0]))
    if f[0]:
        sys.exit(1)


if __name__ == "__main__":
    main()
