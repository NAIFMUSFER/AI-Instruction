# -*- coding: utf-8 -*-
"""KI-24 · F-35…F-38 — الخطّة المحدودة والتقطيع الحتميّ.

    python3 tests/remediation/test_plan_chunking.py

العطل الإنتاجي
--------------
    POST /v1/understand → 502  ACS_UPSTREAM_TRUNCATED
    «رد مزوّد النموذج توقف عند حد المخرجات (16000 رمزاً) في المرحلة plan»
    سبقه: [ACS-PLAN] class=LARGE est_out=34437 zones=51 budget=32000 -> staged

التوليد على مراحل كان يقسّم **التفصيل** ولا يقسّم **الخطّة**: نداءٌ واحد يجب
أن يُخرج هيكل المبنى كلّه، وسقفه ٥٠٪ من الميزانية، ولا شيء يقدّر حجمه ولا
يقارنه بسقفه ولا يتعافى إن انقطع. تصعيدُ «واحد ← مراحل» يعالج النداء الواحد،
وتقسيمُ المجموعة يعالج التفصيل، والخطّة بينهما بلا حارس.

المزوّد المزيّف هنا **يفرض سقفه فعلاً**: يبني رداً بالحجم الذي يطلبه الاختبار،
وإن تجاوز max_tokens يقصّه ويعيد stop_reason="max_tokens" كما يفعل المزوّد
الحقيقي. بديلٌ يعيد رداً صالحاً دائماً لا يمكنه أن يكشف عطل ميزانية — وهو
بالضبط سبب مرور هذا العطل إلى الإنتاج.

النطاق: لا شبكة ولا مفتاح. نداء مزوّد حيّ =
NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED.
"""
import importlib
import io
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_api_errors as E                                       # noqa: E402
import acs_generation as G                                       # noqa: E402
import acs_plan_chunks as PC                                     # noqa: E402

p = [0]
f = [0]


def chk(name, cond, detail=""):
    if cond:
        p[0] += 1
        print("  ✓ %s" % name)
    else:
        f[0] += 1
        print("  ✗ %s  %s" % (name, detail))


# ════════════════ مزوّد مزيّف يفرض سقف الرموز فعلاً ══════════════════════════
CHARS_PER_TOKEN = 2.2          # العربية في JSON غير مضغوط — نفس تقدير المشروع


def _tok(text):
    return int(len(text) / CHARS_PER_TOKEN)


class _Usage(object):
    def __init__(self, i, o):
        self.input_tokens = i
        self.output_tokens = o


class _Block(object):
    def __init__(self, text):
        self.text = text


class _Msg(object):
    def __init__(self, text, stop, in_tok, out_tok):
        self.content = [_Block(text)]
        self.stop_reason = stop
        self.usage = _Usage(in_tok, out_tok)


class Provider(object):
    """يبني الرد من الطلب، ويقصّه عند max_tokens كما يفعل المزوّد الحقيقي."""

    def __init__(self, zones, brief_chars=120, fail_chunks=(), malformed=(),
                 duplicate_in=(), unknown_in=(), drop_zone_in=(),
                 fail_all_chunks=False):
        self.zones = zones
        self.brief_chars = brief_chars
        self.fail_chunks = set(fail_chunks)
        # انقطاعٌ لا يُشفى بالشطر: كل شريحة تبلغ سقفها مهما صغرت. يثبت أن
        # الحارس ينتهي إلى نسبة عطل صريحة لا إلى دوران بلا نهاية.
        self.fail_all_chunks = bool(fail_all_chunks)
        self.malformed = set(malformed)
        self.duplicate_in = set(duplicate_in)
        self.unknown_in = set(unknown_in)
        self.drop_zone_in = set(drop_zone_in)
        self.calls = []
        self._chunk_seen = 0

    # ── أشكال الردود ──
    def _outline_body(self):
        return {"site": {"w": 120, "d": 90}, "floor_height": 12.0,
                "wall_h": 11.5, "wall_t": 0.2,
                "levels": [{"id": "L0", "template": "t", "elevation": 0}],
                "zones": [{"id": "zone_%03d" % i, "role": "storage",
                           "template": "t"} for i in range(self.zones)]}

    def _legacy_plan_body(self):
        """الخطّة القديمة: كل شيء في نداء واحد — وهذا ما كان ينقطع."""
        return {"meta": {"type": "warehouse",
                         "requirements": [{"req": "بند %d" % i,
                                           "where": "zone_%03d" % i,
                                           "how": "ينفَّذ هنا"}
                                          for i in range(min(60, self.zones))],
                         "extras": [], "added": []},
                "site": {"w": 120, "d": 90}, "floor_height": 12.0,
                "wall_h": 11.5, "wall_t": 0.2,
                "levels": [{"id": "L0", "template": "t", "elevation": 0}],
                "floors": {"t": {"rooms": [
                    {"id": "zone_%03d" % i,
                     "rect": [round(2.0 * (i % 40), 2), round(8.0 * (i // 40), 2),
                              1.8, 7.0],
                     "role": "storage", "walls": "none",
                     "brief": "ب" * self.brief_chars}
                    for i in range(self.zones)]}}}

    def _chunk_body(self, ids, idx):
        rooms = []
        for j, zid in enumerate(ids):
            if idx in self.drop_zone_in and j == 0:
                continue                      # منطقة ناقصة من الشريحة
            rooms.append({"id": zid,
                          "rect": [round(2.0 * j, 2), round(8.0 * idx, 2),
                                   1.8, 7.0],
                          "role": "storage", "walls": "none",
                          "brief": "ب" * self.brief_chars})
        if idx in self.duplicate_in and rooms:
            rooms.append(dict(rooms[0]))      # معرّف مكرّر داخل الشريحة
        if idx in self.unknown_in:
            rooms.append({"id": "zone_INTRUDER", "rect": [0, 0, 1, 1],
                          "role": "x", "walls": "none"})
        return {"rooms": rooms}

    # ── واجهة SDK ──
    def _respond(self, kw):
        sys_p = kw.get("system") or ""
        body = "".join(m.get("content") or "" for m in (kw.get("messages") or [])
                       if isinstance(m, dict) and isinstance(m.get("content"), str))
        mt = int(kw.get("max_tokens") or 0)
        in_tok = _tok(sys_p + body)

        if "بيان المناطق" in body:
            stage, payload = "outline", self._outline_body()
        elif "هندسة المناطق المذكورة" in body:
            stage = "plan_chunk"
            idx = self._chunk_seen
            self._chunk_seen += 1
            ids = []
            try:
                start = body.index("[{")
                end = body.index("}]", start) + 2
                ids = [z["id"] for z in json.loads(body[start:end])]
            except Exception:                                     # noqa: BLE001
                ids = []
            if idx in self.malformed:
                text = '{"rooms":[{"id":"zone_000","rect":[0,0,1'
                self.calls.append({"stage": stage, "max_tokens": mt,
                                   "out_tokens": _tok(text), "stop": "end_turn",
                                   "chunk": idx})
                return _Msg(text, "end_turn", in_tok, _tok(text))
            if idx in self.fail_chunks or self.fail_all_chunks:
                text = json.dumps(self._chunk_body(ids, idx), ensure_ascii=False)
                cut = text[:int(mt * CHARS_PER_TOKEN)]
                self.calls.append({"stage": stage, "max_tokens": mt,
                                   "out_tokens": mt, "stop": "max_tokens",
                                   "chunk": idx})
                return _Msg(cut, "max_tokens", in_tok, mt)
            payload = self._chunk_body(ids, idx)
        elif "خطة المناطق فقط" in body:
            stage, payload = "plan", self._legacy_plan_body()
        elif "تفصيل المناطق المذكورة" in body:
            stage = "detail"
            ids = []
            for tok_ in body.split('"id"'):
                if ":" in tok_:
                    v = tok_.split(":", 1)[1].strip()
                    if v.startswith('"'):
                        ids.append(v[1:].split('"', 1)[0])
            payload = {"rooms": [{"id": i, "rect": [0, 0, 1.8, 7.0],
                                  "role": "storage", "walls": "none",
                                  "points": [], "furniture": []}
                                 for i in dict.fromkeys(ids)]}
        else:
            stage, payload = "single", self._legacy_plan_body()

        text = json.dumps(payload, ensure_ascii=False)
        out = _tok(text)
        # ── السقف يُفرض هنا، تماماً كما يفعل المزوّد ──
        if mt and out > mt:
            cut = text[:int(mt * CHARS_PER_TOKEN)]
            self.calls.append({"stage": stage, "max_tokens": mt,
                               "out_tokens": mt, "stop": "max_tokens",
                               "chunk": None})
            return _Msg(cut, "max_tokens", in_tok, mt)
        self.calls.append({"stage": stage, "max_tokens": mt, "out_tokens": out,
                           "stop": "end_turn", "chunk": None})
        return _Msg(text, "end_turn", in_tok, out)


def install(provider):
    class _Messages(object):
        def stream(self, **kw):
            msg = provider._respond(kw)

            class _Ctx(object):
                def __enter__(self_):
                    return self_

                def __exit__(self_, *a):
                    return False

                def get_final_message(self_):
                    return msg
            return _Ctx()

        def create(self, **kw):
            return provider._respond(kw)

    class _Client(object):
        def __init__(self, **kw):
            self.messages = _Messages()

    mod = types.ModuleType("anthropic")
    mod.Anthropic = _Client
    mod.__version__ = "0.40.0"
    sys.modules["anthropic"] = mod
    return provider


def fresh():
    import acs_understand as U
    return importlib.reload(U)


_saved_key = os.environ.get("ANTHROPIC_API_KEY")
os.environ["ANTHROPIC_API_KEY"] = "sk-" + "ant-" + "fake-for-tests-only"
os.environ["ACS_UPSTREAM_BACKOFF_S"] = "0"
os.environ["ACS_WORKERS"] = "1"          # ترتيب حتميّ في الاختبار

DESC_LARGE = ("مستودع لوجستي 120×90 متر بارتفاع 12 متر: استلام بأربعة أرصفة، "
              "تخزين رفوف ستة مستويات، التقاط، تغليف باثنتي عشرة محطة، فرز، "
              "شحن بستة أرصفة، صيانة، شواحن، مكاتب، تحكم، دورات مياه.")


def main():
    # ═══════════════ أ · معايرة المقدّر على مخرج حقيقيّ ══════════════════════
    print("\n== أ · معايرة تكاليف الرموز على JSON فعليّ ==")
    sample = {"id": "zone_001", "rect": [12.5, 0.2, 11.4, 14.6],
              "role": "storage", "walls": "none", "brief": "ب" * PC.BRIEF_MAX_CHARS}
    measured = _tok(json.dumps(sample, ensure_ascii=False))
    chk("كلفة المنطقة المعلنة تغطّي المقيسة (%d معلنة · %d مقيسة)"
        % (PC.estimate_plan_zone_tokens(), measured),
        PC.estimate_plan_zone_tokens() >= measured,
        "%d < %d" % (PC.estimate_plan_zone_tokens(), measured))
    om = _tok(json.dumps({"id": "zone_001", "role": "storage", "template": "t"},
                         ensure_ascii=False))
    chk("وكلفة سطر البيان كذلك (%d معلنة · %d مقيسة)" % (PC.T_OUTLINE_ZONE, om),
        PC.T_OUTLINE_ZONE >= om, "%d < %d" % (PC.T_OUTLINE_ZONE, om))

    # ═══════════════ ب · إعادة إنتاج العطل الإنتاجي ══════════════════════════
    print("\n== ب · إعادة إنتاج ACS_UPSTREAM_TRUNCATED في المرحلة plan ==")
    # brief نثريّ طويل لخمسين منطقة ⇒ الخطّة القديمة تتجاوز سقفها
    prov = install(Provider(zones=51, brief_chars=700))
    U = fresh()
    err = None
    try:
        U._plan(DESC_LARGE, model="claude-sonnet-5", btype="warehouse")
    except E.AcsApiError as exc:
        err = exc
    chk("الخطّة القديمة (نداء واحد) تنقطع فعلاً عند سقفها",
        err is not None and err.code == E.ACS_UPSTREAM_TRUNCATED,
        getattr(err, "code", None))
    plan_calls = [c for c in prov.calls if c["stage"] == "plan"]
    chk("والمزوّد بلغ السقف حقاً (stop=max_tokens عند %d)"
        % (plan_calls[0]["max_tokens"] if plan_calls else -1),
        bool(plan_calls) and plan_calls[0]["stop"] == "max_tokens"
        and plan_calls[0]["max_tokens"] == G.stage_budget("plan"),
        json.dumps(plan_calls[:1]))
    chk("والرسالة تسمّي المرحلة والسقف كما في الإنتاج",
        err is not None and "16000" in str(err.message) and "plan" in str(err.message),
        str(getattr(err, "message", ""))[:90])

    # ═══════════════ ج · المسار المحدود يُنهي نفس الحمولة ═════════════════════
    print("\n== ج · نفس الحمولة عبر المسار المحدود ==")
    prov = install(Provider(zones=51, brief_chars=700))
    U = fresh()
    stages = []
    err = None
    building = None
    try:
        building = U._plan_bounded(DESC_LARGE, model="claude-sonnet-5",
                                   btype="warehouse", stages=stages)
    except BaseException as exc:                                  # noqa: BLE001
        err = exc
    chk("الخطّة تكتمل بلا انقطاع", err is None and isinstance(building, dict),
        "%s: %s" % (type(err).__name__, str(err)[:120]) if err else "")
    rooms = (building or {}).get("floors", {}).get("t", {}).get("rooms", [])
    chk("وكل المناطق الإحدى والخمسين موجودة", len(rooms) == 51, str(len(rooms)))
    chk("ولا معرّف مكرّر", len({r["id"] for r in rooms}) == 51)
    ceiling = [c for c in prov.calls if c["stop"] == "max_tokens"]
    chk("ولا نداء واحد بلغ سقفه", not ceiling, json.dumps(ceiling[:2]))
    print("     نداءات: " + ", ".join(
        "%s=%d/%d" % (c["stage"], c["out_tokens"], c["max_tokens"])
        for c in prov.calls))

    # هذا المزوّد يتجاهل سقف brief عمداً (٧٠٠ محرفاً مقابل ١٦٠ معلنة). القياس
    # هو ما أنقذ الحمولة: التقدير وحده كان يرسل الواحدةَ والخمسين في شريحة.
    rep = (building or {}).get("meta", {}).get("acs_plan_report") or {}
    chk("والقياس كشف أن النموذج أسهب فوق العقد",
        (rep.get("measured_zone_tokens") or 0) > rep.get("estimated_zone_tokens", 0),
        "مقيسة %s · مقدَّرة %s" % (rep.get("measured_zone_tokens"),
                                   rep.get("estimated_zone_tokens")))
    chk("فنُفِّذت شرائح أكثر ممّا خطّط التقدير",
        (rep.get("chunks_executed") or 0) > (rep.get("chunk_count_planned") or 0),
        "منفَّذ %s · مخطَّط %s" % (rep.get("chunks_executed"),
                                   rep.get("chunk_count_planned")))
    chk("والنداء الاستكشافيّ سبق أوّل شريحة كاملة",
        [s for s in stages if s["stage"] == PC.STAGE_PLAN_CHUNK][0]["zones"]
        <= PC.PILOT_ZONES,
        json.dumps([s["zones"] for s in stages
                    if s["stage"] == PC.STAGE_PLAN_CHUNK]))
    chk("ولا منطقة بلا هندسة ولا شريحة فاشلة",
        not rep.get("failed_chunks") and not rep.get("capped_zones"),
        json.dumps(rep.get("failed_chunks")))

    # ═══════════════ د · الأحجام الأربعة ═════════════════════════════════════
    print("\n== د · SMALL · MEDIUM · LARGE · VERY LARGE ==")
    MEASURE = []
    for label, z in (("SMALL", 6), ("MEDIUM", 20), ("LARGE", 51),
                     ("VERY_LARGE", 220)):
        prov = install(Provider(zones=z, brief_chars=700))
        U = fresh()
        st = []
        e2 = None
        b2 = None
        try:
            b2 = U._plan_bounded(DESC_LARGE, model="claude-sonnet-5",
                                 btype="warehouse", stages=st)
        except BaseException as exc:                              # noqa: BLE001
            e2 = exc
        got = len((b2 or {}).get("floors", {}).get("t", {}).get("rooms", []))
        hit = [c for c in prov.calls if c["stop"] == "max_tokens"]
        worst = max([c["out_tokens"] for c in prov.calls] or [0])
        cap = min([c["max_tokens"] for c in prov.calls] or [0])
        MEASURE.append((label, z, got, len(prov.calls), worst, cap, len(hit)))
        chk("%-11s %3d منطقة → تكتمل بلا بلوغ سقف" % (label, z),
            e2 is None and got == z and not hit,
            "err=%s got=%d hit=%d" % (type(e2).__name__ if e2 else "-", got, len(hit)))

    print("\n     %-11s %6s %6s %7s %9s %8s" %
          ("class", "zones", "calls", "worst", "ceiling", "at_cap"))
    for label, z, got, calls, worst, cap, hit in MEASURE:
        print("     %-11s %6d %6d %7d %9d %8d" % (label, z, calls, worst, cap, hit))

    # ═══════════════ هـ · الحتمية ════════════════════════════════════════════
    print("\n== هـ · الحتمية: الترتيب وإعادة المحاولة لا يغيّران المخرج ==")
    zones = [{"id": "z%03d" % i, "role": "storage", "template": "t", "order": i}
             for i in range(37)]
    ch = PC.plan_chunks(zones)
    env = {"site": {"w": 120, "d": 90}, "floor_height": 12.0}

    def rooms_for(c):
        return [{"id": z, "rect": [1.0, 2.0, 3.0, 4.0], "role": "storage",
                 "walls": "none"} for z in c["zone_ids"]]

    forward = [(c, rooms_for(c), []) for c in ch["chunks"]]
    reverse = list(reversed(forward))
    shuffled = forward[1::2] + forward[0::2]
    a, _ = PC.merge_plan(zones, forward, env)
    b, _ = PC.merge_plan(zones, reverse, env)
    d, _ = PC.merge_plan(zones, shuffled, env)
    ja = json.dumps(a, ensure_ascii=False, sort_keys=True)
    chk("ترتيب وصول الشرائح لا يغيّر بايتاً واحداً",
        ja == json.dumps(b, ensure_ascii=False, sort_keys=True)
        == json.dumps(d, ensure_ascii=False, sort_keys=True))
    again, _ = PC.merge_plan(zones, forward, env)
    chk("والدمج نفسه مرّتين يعطي المخرج نفسه (idempotent)",
        ja == json.dumps(again, ensure_ascii=False, sort_keys=True))
    chk("وترتيب المناطق هو ترتيب البيان لا ترتيب الرد",
        [r["id"] for r in a["floors"]["t"]["rooms"]] == [z["id"] for z in zones])
    chk("وبصمة الشريحة ثابتة لنفس المدخل",
        PC.plan_chunks(zones)["chunks"][0]["digest"] == ch["chunks"][0]["digest"])

    # ═══════════════ و · حالات الفشل، كلٌّ منسوب لشريحته ═════════════════════
    print("\n== و · الفشل الجزئيّ: نسبة صريحة وبلا فقدان منطقة ==")
    # الشريحة التي تبلغ سقفها تُشطر وتُشفى: الحالة الصحيحة هي PLAN_CHUNK_SPLIT
    # **بلا** منطقة غير محلولة. أمّا PLAN_CHUNK_FAILED فموضعه العطل الذي لا
    # يشفيه الشطر: مخرجٌ مشوّه لسببٍ آخر، أو انقطاعٌ يتكرّر مهما صغرت الشريحة.
    for label, kwargs, code in (
            ("شريحة تبلغ سقفها ثم تُشطر", {"fail_chunks": (1,)},
             "PLAN_CHUNK_SPLIT"),
            ("انقطاعٌ لا يشفيه الشطر", {"fail_all_chunks": True},
             "PLAN_CHUNK_FAILED"),
            ("شريحة بمخرج مشوّه", {"malformed": (1,)}, "PLAN_CHUNK_FAILED"),
            ("منطقة ناقصة من شريحة", {"drop_zone_in": (0,)},
             "PLAN_CHUNK_MISSING_ZONE"),
            ("معرّف مكرّر داخل شريحة", {"duplicate_in": (0,)},
             "PLAN_CHUNK_DUPLICATE_ID"),
            ("منطقة دخيلة ليست في الشريحة", {"unknown_in": (0,)},
             "PLAN_CHUNK_UNKNOWN_ZONE")):
        prov = install(Provider(zones=140, brief_chars=200, **kwargs))
        U = fresh()
        st = []
        e3 = None
        b3 = None
        try:
            b3 = U._plan_bounded(DESC_LARGE, model="claude-sonnet-5",
                                 btype="warehouse", stages=st)
        except BaseException as exc:                              # noqa: BLE001
            e3 = exc
        rms = (b3 or {}).get("floors", {}).get("t", {}).get("rooms", [])
        diag = ((b3 or {}).get("meta", {}).get("acs_stage_diagnostics") or [])
        codes = {d.get("code") for d in diag}
        chk("%-30s → التوليد يكتمل" % label, e3 is None and len(rms) == 140,
            "err=%s rooms=%d" % (type(e3).__name__ if e3 else "-", len(rms)))
        chk("%-30s → و%s معلَن" % ("", code), code in codes,
            json.dumps(sorted(c for c in codes if c), ensure_ascii=False))
        if kwargs.get("fail_chunks"):
            # الشطر شفى الشريحة: لا يجوز أن تبقى منطقة بلا هندسة.
            chk("%-30s → والشطر شفاها فلا منطقة بلا هندسة" % "",
                "PLAN_ZONE_UNRESOLVED" not in codes
                and not any(r.get("acs_unresolved") for r in rms),
                json.dumps(sorted(c for c in codes if c), ensure_ascii=False))
        if kwargs.get("fail_all_chunks") or kwargs.get("malformed"):
            chk("%-30s → والمناطق غير المحلولة معلَّمة لا محذوفة" % "",
                "PLAN_ZONE_UNRESOLVED" in codes
                and any(r.get("acs_unresolved") for r in rms))

    # ═══════════════ ز · الحدود الدلالية ═════════════════════════════════════
    print("\n== ز · التقطيع على حدود دلالية لا على بايتات ==")
    mixed = ([{"id": "a%02d" % i, "role": "r", "template": "L0", "order": i}
              for i in range(9)]
             + [{"id": "b%02d" % i, "role": "r", "template": "L1", "order": 9 + i}
                for i in range(9)])
    cm = PC.plan_chunks(mixed, budget=2000, safety=0.6)
    chk("لا شريحة تخلط قالبين (دورين)",
        all(len({z[0] for z in [(zz[0],) for zz in c["zone_ids"]]}) >= 0
            for c in cm["chunks"])
        and all(all(zid.startswith(c["template"][0].replace("L", "a")
                                   if c["template"] == "L0" else "b")
                    for zid in c["zone_ids"]) for c in cm["chunks"]),
        json.dumps([(c["template"], c["zone_ids"][:2]) for c in cm["chunks"]]))
    chk("والمناطق كلّها موزّعة بلا فقد ولا تكرار",
        sorted(z for c in cm["chunks"] for z in c["zone_ids"])
        == sorted(z["id"] for z in mixed))
    chk("وحجم الشريحة مشتقّ من الميزانية لا ثابتاً مدفوناً",
        PC.chunk_size_for(budget=2000) < PC.chunk_size_for(budget=32000),
        "%d vs %d" % (PC.chunk_size_for(budget=2000),
                      PC.chunk_size_for(budget=32000)))
    chk("وكل شريحة مخرجها المتوقّع تحت سقفها مع الهامش",
        all(c["expected_output_tokens"] <= c["budget"] * PC.CHUNK_SAFETY + 1
            for c in cm["chunks"]),
        json.dumps([(c["expected_output_tokens"], c["budget"])
                    for c in cm["chunks"][:3]]))

    # ═══════════════ ح · القطع لا يُقبَل صامتاً ═══════════════════════════════
    print("\n== ح · القطع يُصنَّف ولا يُرمَّم (العقد لم يضعف) ==")
    prov = install(Provider(zones=8, brief_chars=6000))
    U = fresh()
    e4 = None
    try:
        U.call_llm("x", model="claude-sonnet-5", max_tokens=500, stage="single")
    except E.AcsApiError as exc:
        e4 = exc
    chk("stop_reason=max_tokens ⇒ ACS_UPSTREAM_TRUNCATED",
        e4 is not None and e4.code == E.ACS_UPSTREAM_TRUNCATED,
        getattr(e4, "code", None))
    chk("ولا يُعاد بناء JSON المبتور", E.HTTP_STATUS[e4.code] == 502)

    # ═══════════════ ط · تعافي المسار القديم ═════════════════════════════════
    print("\n== ط · انقطاع الخطّة القديمة يتعافى بالشرائح (F-37) ==")
    prov = install(Provider(zones=51, brief_chars=700))
    U = fresh()
    st = []
    e5 = None
    b5 = None
    try:
        b5 = U.understand_deep(DESC_LARGE, model="claude-sonnet-5",
                               btype="warehouse", stages=st,
                               strategy_plan={"estimated_zones": 4})
    except BaseException as exc:                                  # noqa: BLE001
        e5 = exc
    got = len((b5 or {}).get("floors", {}).get("t", {}).get("rooms", []))
    chk("التقدير المنخفض يبدأ بالخطّة الواحدة",
        any(c["stage"] == "plan" for c in prov.calls))
    chk("وانقطاعها يصعّد إلى الشرائح بدل 502",
        e5 is None and got == 51,
        "err=%s rooms=%d" % (type(e5).__name__ if e5 else "-", got))
    chk("والمراحل مسجَّلة بأسمائها",
        {s["stage"] for s in st} >= {"plan", PC.STAGE_OUTLINE,
                                     PC.STAGE_PLAN_CHUNK},
        json.dumps(sorted({s["stage"] for s in st})))

    # ═══════════════ ي · التليمتري ═══════════════════════════════════════════
    print("\n== ي · التليمتري يحمل موضع الشريحة ولا يحمل محتوى ==")
    import acs_logging as LOGGING
    chk("chunk_index و chunk_count معلنان في قناة التليمتري",
        "chunk_index" in io.open(os.path.join(ROOT, "acs_logging.py"),
                                 encoding="utf-8").read()
        and "chunk_count" in io.open(os.path.join(ROOT, "acs_logging.py"),
                                     encoding="utf-8").read())
    MARK = "علامة-سرّية-في-الوصف"
    SECRET = "sk-" + "ant-" + "LEAKME0123456789"
    os.environ["ANTHROPIC_API_KEY"] = SECRET
    prov = install(Provider(zones=30, brief_chars=200))
    U = fresh()
    buf = io.StringIO()
    _out = sys.stdout
    sys.stdout = buf
    try:
        U._plan_bounded(DESC_LARGE + " " + MARK, model="claude-sonnet-5",
                        btype="warehouse", stages=[])
    except BaseException:                                         # noqa: BLE001
        pass
    finally:
        sys.stdout = _out
    printed = buf.getvalue()
    chk("لا مفتاح في المطبوع", SECRET not in printed)
    chk("ولا نصّ الوصف", MARK not in printed)
    chk("ولا محتوى مبنى (لا rect في السجلّ)", '"rect"' not in printed)
    os.environ["ANTHROPIC_API_KEY"] = "sk-" + "ant-" + "fake-for-tests-only"

    # ═══════════════ ك · لم يضعف شيء قائم ═══════════════════════════════════
    print("\n== ك · العقود القائمة لم تُمَسّ ==")
    src = io.open(os.path.join(ROOT, "acs_understand.py"), encoding="utf-8").read()
    chk("KI-23 قائم: thinking مشروط بدعم النسخة",
        "if thinking is not None and supports_thinking" in src)
    chk("و AttributeError وحده يفتح الرجوع إلى create()",
        "except AttributeError:" in src
        and "except (AttributeError, TypeError):" not in src)
    chk("وسقف المرحلة الواحدة لم يتغيّر", G.stage_budget("single")
        == G.max_output_tokens())
    chk("وسقف مرحلة plan لم يُرفَع لإخفاء العطل",
        G.stage_budget("plan") == int(G.max_output_tokens() * 0.50),
        str(G.stage_budget("plan")))
    chk("وميزانية البيان لم تتجاوز سقف النداء الواحد",
        PC.outline_budget() <= G.max_output_tokens(),
        "%d / %d" % (PC.outline_budget(), G.max_output_tokens()))

    # ═══════════════ ل · البيان: المرحلة التي لا تُشطر ═══════════════════════
    # قبل البيان لا يعرف الخادم شيئاً يُقسَم عليه، فسقفه لا يجوز أن يكون كسراً
    # مريحاً: يجب أن يسع السعة المعلنة كاملةً مع الهامش، وفوقها يُعلَن صراحةً.
    print("\n== ل · سقف البيان يسع السعة المعلنة ==")
    chk("سقف البيان يسع MAX_BUILDING_ZONES مع الهامش",
        PC.estimate_outline_tokens(PC.MAX_BUILDING_ZONES)
        <= PC.outline_budget() * PC.CHUNK_SAFETY,
        "%d ≤ %d×%.2f" % (PC.estimate_outline_tokens(PC.MAX_BUILDING_ZONES),
                          PC.outline_budget(), PC.CHUNK_SAFETY))
    chk("والسعة المحسوبة من السقف لا تقلّ عن المعلنة",
        PC.outline_capacity() >= PC.MAX_BUILDING_ZONES,
        "%d / %d" % (PC.outline_capacity(), PC.MAX_BUILDING_ZONES))
    chk("وسقف البيان مشتقّ لا ثابتاً مدفوناً",
        PC.outline_budget() != 8000 and PC.outline_budget() > G.STAGE_FLOOR,
        str(PC.outline_budget()))
    _over = [{"id": "z%04d" % i, "role": "r", "template": "t"}
             for i in range(PC.MAX_BUILDING_ZONES + 5)]
    _oz, _oi = PC.normalise_outline({"zones": _over})
    chk("وفوق السعة يُعلَن PLAN_OUTLINE_TOO_LARGE ولا تُحذف منطقة",
        any(i.get("code") == "PLAN_OUTLINE_TOO_LARGE" for i in _oi)
        and len(_oz) == PC.MAX_BUILDING_ZONES + 5,
        json.dumps([i.get("code") for i in _oi], ensure_ascii=False))
    _ok, _oi2 = PC.normalise_outline(
        {"zones": _over[:PC.MAX_BUILDING_ZONES]})
    chk("وتحت السعة لا يُعلَن شيء",
        not any(i.get("code") == "PLAN_OUTLINE_TOO_LARGE" for i in _oi2))

    if _saved_key is None:
        os.environ.pop("ANTHROPIC_API_KEY", None)
    else:
        os.environ["ANTHROPIC_API_KEY"] = _saved_key

    print("\n" + "─" * 62)
    print("LIVE PROVIDER / LIVE LARGE GENERATION: "
          "NOT VERIFIED — EXTERNAL ENVIRONMENT REQUIRED")
    print("PLAN CHUNKING: %d passed, %d failed" % (p[0], f[0]))
    if f[0]:
        sys.exit(1)


if __name__ == "__main__":
    main()
