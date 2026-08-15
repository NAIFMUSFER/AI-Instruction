# -*- coding: utf-8 -*-
"""acs_plan_chunks — عقد الخطّة المحدود والتقطيع الحتميّ (KI-24 · F-35…F-38).

العطل الذي تغلقه هذه الوحدة
---------------------------
    POST /v1/understand → 502  ACS_UPSTREAM_TRUNCATED
    «رد مزوّد النموذج توقف عند حد المخرجات (16000 رمزاً) في المرحلة plan»
    سبقه: [ACS-PLAN] class=LARGE est_out=34437 zones=51 budget=32000 -> staged

كان التوليد على مراحل يقسّم **التفصيل** ولا يقسّم **الخطّة**. فالخطّة نداءٌ
واحد يجب أن يُخرج هيكل المبنى كلّه — كل منطقة بمعرّفها ومستطيلها ودورها
و«brief» نثريّ مفتوح الطول — وميزانيتها ٥٠٪ من الميزانية الواحدة. لا شيء في
النظام كان:

  · يقدّر حجم مخرج **الخطّة** (المقدّر يقدّر النموذج النهائي وحده)،
  · ولا يقارن ذلك التقدير بسقف المرحلة،
  · ولا يملك أي مسار تعافٍ إن انقطعت الخطّة: تصعيدُ «واحد ← مراحل» يعالج
    النداء الواحد، وتقسيمُ المجموعة يعالج التفصيل، والخطّة بينهما بلا حارس.

فكان يكفي أن يطلب العميل مبنى كبيراً حتى تنقطع الخطّة ويسقط الطلب كلّه — لا
لأن النموذج النهائي لا يسع الميزانية (لذلك وُجد التقطيع) بل لأن **وصف** ذلك
النموذج لا يسع سقف مرحلته.

المعمارية الجديدة — ثلاث مراحل محدودة بدل مرحلتين
-------------------------------------------------
    outline  →  plan_chunk[0..n]  →  detail_chunk[0..m]

  ١ · outline (F-35): نداء صغير مسقوف يُخرج **بيان المناطق** وحده: الغلاف
      (site/levels/ارتفاعات) وقائمة مسطّحة من (id, role) لا غير. لا مستطيلات
      ولا نثر. كلفة المنطقة ≈ ٢٤ رمزاً مقيسةً، فسقف هذه المرحلة يُشتقّ من
      MAX_BUILDING_ZONES — لأنها المرحلة الوحيدة التي لا تُشطر. هذا البيان هو
      **مرساة الحتمية**: بعده صار عدد المناطق وترتيبها وأسماؤها معروفةً
      للخادم، فلا يعود التقطيع رهن تخمين.

  ٢ · plan_chunk (F-36): لكل شريحة من البيان يُطلب الهيكل الهندسيّ لمناطقها
      وحدها: rect و walls و brief **محدود الطول**. حجم الشريحة يُحسَب من
      الميزانية لا يُختار اعتباطاً: chunk_size = floor(budget × margin / كلفة
      المنطقة). فلا شريحة تُطلَب وهي أكبر ممّا يسعه سقفها.

      وكلفة المنطقة نفسها تُقاس لا تُفترَض (F-40): أوّل ردٍّ مكتمل يكشف كم
      يُنفق هذا النموذج فعلاً على المنطقة، فتُشتقّ منه أحجام ما بعده. والحمل
      الذي قد يبلغ سقفه لو أسهب النموذج يسبقه نداءٌ استكشافيّ صغير يقيس قبل
      الالتزام. وإن بلغت شريحة سقفها رغم ذلك شُطرت نصفين وأُعيدت (F-39) —
      لا يُرفع سقفها ولا يُعاد النداء كما هو.

  ٣ · detail_chunk: كما كان، فوق خطّة مكتملة.

كل ما في هذه الوحدة **حتميّ ونقيّ**: لا نداء نموذج، ولا شبكة، ولا عشوائية،
ولا وقت. تُستدعى من acs_understand، وتُختبَر وحدها بلا مزوّد.
"""
import hashlib
import json
import os
import re

import acs_generation as G

CONTRACT_VERSION = "acs.plan-chunks/1.0.0"

# ── ١ · حدود العقد ──────────────────────────────────────────────────────────
# طول «brief» لكل منطقة. النثر المفتوح في الخطّة هو ما كان يجعل مخرجها غير
# محدود: العقد القديم يقول «انقل أرقامه وأسماءه كما ذكرها» بلا سقف. القيمة
# تكفي لنقل الأعداد والأسماء (١٢ محطة، ٦ مستويات رفّ) ولا تكفي لإعادة كتابة
# الطلب داخل الخطّة.
BRIEF_MAX_CHARS = _b = int(os.environ.get("ACS_PLAN_BRIEF_MAX_CHARS", "160"))

# كلفة الرموز المقيسة لكل عنصر في **مخرج الخطّة** (لا النموذج النهائي).
# مقيسة على JSON عربي غير مضغوط في tests/remediation/test_plan_chunking.py §أ.
# مقيسة على JSON عربي فعليّ: {"id":"zone_001","role":"storage","template":"t"}
# ≈ ٢٤ رمزاً. المعلن ٢٦ بهامش — التقدير يعلو ولا يقلّ، فسقف البيان لا يُخترَق.
T_OUTLINE_ZONE = 26
T_OUTLINE_ENVELOPE = 220   # site + levels + ارتفاعات + الإطار
T_PLAN_ZONE_BASE = 78      # id + rect + role + walls + الأقواس
T_PLAN_BRIEF = int(BRIEF_MAX_CHARS / 2.2) + 6      # brief عند سقفه
T_PLAN_REQUIREMENT = 45    # سطر واحد في meta.requirements

# هامش أمان: لا نملأ سقف المرحلة. التقدير تقريب، والنموذج قد يضيف مسافات
# وفواصل أكثر ممّا نحسب، وانقطاعٌ واحد يكلّف نداءً كاملاً ضائعاً.
CHUNK_SAFETY = float(os.environ.get("ACS_PLAN_CHUNK_SAFETY", "0.60"))
MIN_CHUNK_ZONES = 4        # شريحة أصغر من هذا تعني نداءات أكثر من فائدتها
# F-39: أقصى عدد مرّات تُشطر فيها شريحة انقطع مخرجها. الشطر يغيّر الطلب فعلاً
# (نصف المناطق ⇒ نصف المخرج) بخلاف إعادة النداء نفسه. محدود عدداً حتى لا
# تدور الخدمة على نفسها، ومحدود بـMIN_CHUNK_ZONES من الأسفل.
MAX_CHUNK_SPLITS = int(os.environ.get("ACS_MAX_PLAN_CHUNK_SPLITS", "3"))
MAX_CHUNK_ZONES = 60       # وأكبر من هذا تقترب من السقف مهما كان الهامش
MAX_PLAN_CHUNKS = int(os.environ.get("ACS_MAX_PLAN_CHUNKS", "24"))

# F-40 · هامش الإسهاب: كم ضعفاً يُسمح للنموذج أن يتجاوز العقد قبل بلوغ سقفه.
# التقدير أعلاه يفترض أن النموذج يحترم سقف `brief` المعلن، وهو افتراض **معقول
# لا مضمون** — والاتّكال على غير المضمون هو نفسه خطأ العطل الأصليّ. فإن كانت
# الشريحة كبيرة إلى حدّ أن إسهاباً بهذا القدر يبلغ سقفها، لا تُرسَل على عماها:
# يسبقها نداءٌ صغير (PILOT_ZONES منطقة) يقيس كلفة المنطقة **فعلاً** عند هذا
# النموذج وهذا الطلب، ثم تُشتقّ أحجام الباقي من المقيس لا من المقدَّر.
#
# لماذا هذا ليس «رفع السقف»: السقف لم يتغيّر، وحجم الطلب هو الذي نزل إليه.
# ولماذا ليس اكتفاءً بالشطر (F-39): الشطر ردّ فعل — يكلّف نداءً كاملاً ضائعاً
# عند كل حمل كبير. القياس المسبق يمنع الانقطاع أصلاً، والشطر يبقى حارساً
# أخيراً إن تغيّر إسهاب النموذج في منتصف التوليد.
VERBOSITY_TOLERANCE = float(os.environ.get("ACS_PLAN_VERBOSITY_TOLERANCE", "3.0"))
PILOT_ZONES = MIN_CHUNK_ZONES

# السعة المعلنة: أكبر عدد مناطق يخدمه المسار المحدود خدمةً كاملة. منها يُشتقّ
# سقف مرحلة البيان (وهي المرحلة الوحيدة التي لا تُشطر)، وفوقها يُعلَن
# PLAN_OUTLINE_TOO_LARGE صراحةً — لا تُحذف منطقة ولا يُقصّ بيان صامتاً.
MAX_BUILDING_ZONES = int(os.environ.get("ACS_MAX_BUILDING_ZONES", "400"))

STAGE_OUTLINE = "outline"
STAGE_PLAN_CHUNK = "plan_chunk"

ISSUE_CODES = (
    "PLAN_OUTLINE_EMPTY",
    "PLAN_OUTLINE_TOO_LARGE",
    "PLAN_CHUNK_MISSING_ZONE",
    "PLAN_CHUNK_UNKNOWN_ZONE",
    "PLAN_CHUNK_DUPLICATE_ID",
    "PLAN_CHUNK_BAD_RECT",
    "PLAN_CHUNK_BRIEF_TRUNCATED",
    "PLAN_CHUNK_FAILED",
    "PLAN_CHUNK_SPLIT",
    "PLAN_ZONE_UNRESOLVED",
    # KI-25/F-41 · عقد المستويات
    "PLAN_LEVELS_EMPTY",
    "PLAN_LEVEL_INDEX_DERIVED",
    "PLAN_LEVEL_INDEX_DUPLICATE",
    "PLAN_LEVEL_TEMPLATE_MISSING",
    "PLAN_TEMPLATE_ORPHANED",
)


# ── ٢ · ميزانية المرحلة الصغيرة ─────────────────────────────────────────────
def outline_budget():
    """سقف مرحلة البيان — مشتقّ من السعة المعلنة لا من كسرٍ اعتباطيّ.

    البيان هو المرحلة الوحيدة التي **لا يمكن شطرها**: قبلها لا يعرف الخادم
    عدد المناطق ولا أسماءها، فلا شيء يُقسَم. فسقفها لا يجوز أن يكون كسراً
    مريحاً من الميزانية (٢٥٪ كان يكفي ٢٩٩ منطقة فقط، ثم ينقطع صامتاً عند
    الأكبر) بل يُشتقّ من MAX_BUILDING_ZONES — السعة التي يعلنها النظام —
    مع هامش الأمان نفسه.

    السقف لا يُنفَق: مبنى من عشر مناطق يُخرج بيانه في مئات الرموز مهما علا
    السقف. رفعه هنا يمنع انقطاعاً، ولا يزيد كلفة نداءٍ واحد.
    """
    env = os.environ.get("ACS_MAX_TOKENS_OUTLINE", "")
    if env:
        try:
            v = int(env)
            if v > 0:
                return v
        except ValueError:
            pass
    need = int(estimate_outline_tokens(MAX_BUILDING_ZONES) / CHUNK_SAFETY) + 1
    return max(G.STAGE_FLOOR, min(int(G.max_output_tokens()), need))


def outline_capacity(budget=None):
    """كم منطقة يسع سقف البيان فعلاً — عدد لا وعد."""
    b = int(budget or outline_budget())
    return max(0, int((b * CHUNK_SAFETY - T_OUTLINE_ENVELOPE) / T_OUTLINE_ZONE))


def plan_chunk_budget():
    """سقف شريحة الخطّة الواحدة — نفس سقف مرحلة plan المعلن."""
    return G.stage_budget("plan")


def estimate_outline_tokens(zones):
    """حجم مخرج البيان المتوقّع. حتميّ."""
    return int(T_OUTLINE_ENVELOPE + max(0, int(zones)) * T_OUTLINE_ZONE)


def estimate_plan_zone_tokens():
    """كلفة المنطقة الواحدة في مخرج شريحة الخطّة."""
    return int(T_PLAN_ZONE_BASE + T_PLAN_BRIEF)


def estimate_plan_chunk_tokens(zone_count, requirements=0):
    """حجم مخرج شريحة تحوي هذا العدد من المناطق."""
    return int(60 + int(zone_count) * estimate_plan_zone_tokens()
               + int(requirements) * T_PLAN_REQUIREMENT)


def chunk_size_for(budget=None, safety=None, rate=None):
    """أكبر عدد مناطق تسعه شريحة واحدة تحت سقفها مع هامش الأمان.

    مشتقّ لا مختار: تغيير الميزانية يغيّر الحجم من تلقائه، فلا يبقى ثابتٌ
    مدفون يخالف السقف بعد أول تعديل بيئة.

    `rate` كلفة المنطقة **المقيسة** من ردٍّ سابق مكتمل (F-40). إن مُرّرت
    استُعملت بدل التقدير، فيصير الحجم مشتقّاً ممّا فعله النموذج فعلاً لا
    ممّا يفترضه العقد.
    """
    b = int(budget or plan_chunk_budget())
    s = float(safety if safety is not None else CHUNK_SAFETY)
    per = int(rate) if rate else estimate_plan_zone_tokens()
    n = int((b * s) / per) if per > 0 else MIN_CHUNK_ZONES
    return max(MIN_CHUNK_ZONES, min(MAX_CHUNK_ZONES, n))


def measured_zone_rate(out_tokens, zone_count, previous=None):
    """كلفة المنطقة كما قاسها ردٌّ فعليّ — لا كما يقدّرها العقد (F-40).

    التقدير المعلن أرضيّةٌ لا سقف: النموذج الأوجز من العقد لا يُكافأ بشرائح
    أكبر (فقد يُسهب في الشريحة التالية)، والأكثر إسهاباً يُخفّض حجم شرائحه
    فوراً. فالتكيّف أحاديّ الاتجاه — نحو الأمان — وبذلك يبقى حتميّاً: نفس
    القياسات بنفس الترتيب تعطي نفس الأحجام دائماً.
    """
    base = max(int(previous or 0), estimate_plan_zone_tokens())
    n = max(1, int(zone_count or 0))
    seen = int(int(out_tokens or 0) / n) + 1
    return max(base, seen)


def needs_pilot(zone_count, budget=None, rate=None, tolerance=None):
    """هل تُرسَل شريحة بهذا الحجم على عماها، أم يسبقها نداءٌ يقيس؟ (F-40)

    الجواب نعم للإرسال المباشر فقط إذا كان النموذج ليبلغ السقف مضطرّاً إلى
    تجاوز العقد بأكثر من VERBOSITY_TOLERANCE ضعفاً. وإلّا فالمخاطرة أعلى من
    كلفة نداءٍ صغير يقيس.
    """
    b = int(budget or plan_chunk_budget())
    per = int(rate) if rate else estimate_plan_zone_tokens()
    t = float(tolerance if tolerance is not None else VERBOSITY_TOLERANCE)
    return int(zone_count) * per * t > b


def group_by_template(zones):
    """يرتّب المناطق بحيث تتجاور مناطق القالب الواحد، بترتيب أوّل ظهور.

    الحدّ الدلاليّ الأوّل هو القالب (الدور). الترتيب داخل القالب هو ترتيب
    البيان. حتميّ: نفس البيان ⇒ نفس التسلسل.
    """
    order = []
    groups = {}
    for z in zones or []:
        t = z.get("template") or "t"
        if t not in groups:
            groups[t] = []
            order.append(t)
        groups[t].append(z)
    out = []
    for t in order:
        out.extend(groups[t])
    return out


# ── ٣ · التقطيع الحتميّ ─────────────────────────────────────────────────────
def _norm_id(raw, index):
    """معرّف آمن وثابت. لا يُخترع من عشوائية ولا من وقت."""
    s = str(raw or "").strip()
    s = re.sub(r"[^0-9A-Za-z_؀-ۿ-]+", "_", s).strip("_")
    return s[:64] if s else ("zone_%03d" % index)


def normalise_outline(outline):
    """يحوّل مخرج مرحلة البيان إلى شكل قانونيّ مرتّب، ويعيد (المناطق، المسائل).

    الترتيب هو ترتيب البيان نفسه — وهو ما يثبّت هوية الشرائح. المعرّفات
    المكرّرة تُفضّ بلاحقة حتميّة (‎__2‎، ‎__3‎) لا تُحذف: منطقة طلبها العميل
    مرّتين باسم واحد ما زالت منطقتين.
    """
    issues = []
    raw_zones = []
    if isinstance(outline, dict):
        raw_zones = outline.get("zones") or outline.get("rooms") or []
    elif isinstance(outline, list):
        raw_zones = outline
    zones = []
    seen = {}
    for i, z in enumerate(raw_zones):
        if isinstance(z, str):
            z = {"id": z, "role": ""}
        if not isinstance(z, dict):
            continue
        zid = _norm_id(z.get("id") or z.get("name"), i)
        if zid in seen:
            seen[zid] += 1
            issues.append({"code": "PLAN_CHUNK_DUPLICATE_ID", "id": zid,
                           "resolved_as": "%s__%d" % (zid, seen[zid])})
            zid = "%s__%d" % (zid, seen[zid])
        else:
            seen[zid] = 1
        zones.append({"id": zid,
                      "role": str(z.get("role") or z.get("kind") or "")[:40],
                      "template": str(z.get("template") or "t")[:40],
                      "order": len(zones)})
    if not zones:
        issues.append({"code": "PLAN_OUTLINE_EMPTY"})
    if len(zones) > MAX_BUILDING_ZONES:
        # فوق السعة المعلنة لا تُحذف منطقة: تُعلَن الزيادة، وما لا تسعه
        # الشرائح يُحَلّ حتميّاً ويُعلَن PLAN_ZONE_UNRESOLVED عند الدمج.
        issues.append({"code": "PLAN_OUTLINE_TOO_LARGE",
                       "zones": len(zones),
                       "declared_capacity": MAX_BUILDING_ZONES})
    return zones, issues


def plan_chunks(zones, budget=None, safety=None, max_chunks=None):
    """يقسّم بيان المناطق شرائح بحدود دلالية ثابتة.

    الحدّ الأوّل هو القالب (الدور): لا تخلط شريحةٌ مناطق دورين، فيبقى كل نداء
    متماسكاً دلالياً ويسهل نسب عطله. ثمّ يُقسَّم داخل القالب بحجم مشتقّ من
    الميزانية. لا تقسيم على مدى بايتات ولا على حدود JSON.

    يعيد قائمة شرائح، لكل شريحة:
        index · count · template · zone_ids · expected_output_tokens · budget
        · digest (بصمة محتوى الشريحة — تُثبت أن الترتيب لم ينزلق)
    """
    b = int(budget or plan_chunk_budget())
    size = chunk_size_for(b, safety)
    cap = int(max_chunks or MAX_PLAN_CHUNKS)

    chunks = []
    pending = group_by_template(zones)
    while pending:
        chunk, pending = next_chunk(pending, len(chunks), budget=b,
                                    safety=safety, allow_pilot=False)
        if chunk is None:
            break
        chunks.append(chunk)
    truncated_plan = False
    if len(chunks) > cap:
        # لا قصّ صامت: الشرائح الزائدة تبقى معلنة في التشخيص، والمناطق التي
        # لم تُفصَّل هندسياً تُحلّ لاحقاً بمستطيل مشتقّ حتميّاً لا تُحذف.
        truncated_plan = True
        chunks = chunks[:cap]
    return {"contract": CONTRACT_VERSION,
            "chunk_size": size,
            "chunk_count": len(chunks),
            "zone_count": sum(c["count"] for c in chunks),
            "budget": b,
            "safety": float(safety if safety is not None else CHUNK_SAFETY),
            "capped": truncated_plan,
            "chunks": chunks}


def next_chunk(pending, index, rate=None, budget=None, safety=None,
               allow_pilot=True):
    """يقتطع الشريحة التالية من المناطق المتبقّية. يعيد (الشريحة، الباقي).

    الحدّ الدلاليّ يُحترَم أوّلاً: الاقتطاع لا يتجاوز حدود القالب الواحد، فلا
    تخلط شريحةٌ دورين. ثمّ الحجم:

      · إن كانت كلفة المنطقة مقيسة من ردٍّ سابق (`rate`) اشتُقّ الحجم منها.
      · وإلّا فمن التقدير المعلن — ما لم يكن الحمل كبيراً بما يجعل إسهاباً
        محتملاً يبلغ السقف، فحينئذ تُقتطع شريحة استكشافية صغيرة تقيس أوّلاً
        (F-40).

    حتميّ تماماً: نفس (الباقي، الكلفة المقيسة) يعطي نفس الشريحة دائماً.
    """
    pending = list(pending or [])
    if not pending:
        return None, []
    b = int(budget or plan_chunk_budget())
    tmpl = pending[0].get("template") or "t"
    run = 0
    for z in pending:
        if (z.get("template") or "t") != tmpl:
            break
        run += 1

    size = chunk_size_for(b, safety, rate)
    pilot = False
    if allow_pilot and not rate and needs_pilot(min(run, size), b):
        size = min(size, PILOT_ZONES)
        pilot = True

    part = pending[:min(run, max(1, size))]
    ids = [z["id"] for z in part]
    return ({"index": int(index),
             "template": tmpl,
             "count": len(part),
             "zone_ids": ids,
             "expected_output_tokens": estimate_plan_chunk_tokens(len(part)),
             "budget": b,
             "pilot": pilot,
             "rate": int(rate) if rate else estimate_plan_zone_tokens(),
             "digest": hashlib.sha256(
                 ("|".join(ids)).encode("utf-8")).hexdigest()[:16]},
            pending[len(part):])


def split_chunk(chunk, depth=0):
    """يشطر شريحة انقطع مخرجها إلى نصفين بحدود ثابتة (F-39).

    لماذا الشطر لا رفع السقف: تقدير كلفة المنطقة يفترض أن النموذج يحترم سقف
    `brief` المعلن في التوجيه. الاعتماد على ذلك هو نفس خطأ العطل الأصلي —
    الاتّكال على مخرج غير مضمون. الشطر لا يفترض شيئاً: نصف المناطق يعني نصف
    المخرج مهما أطال النموذج نثره. والعمق محدود، وعند بلوغه تُنسَب المناطق
    الباقية إلى PLAN_ZONE_UNRESOLVED بدل الدوران.

    الهوية تبقى مشتقّة من الشريحة الأمّ: `index` نفسه و`part` يميّز النصفين،
    فلا ينزلق ترتيب ولا يتكرّر معرّف.
    """
    ids = list(chunk.get("zone_ids") or [])
    if len(ids) <= MIN_CHUNK_ZONES or depth >= MAX_CHUNK_SPLITS:
        return []
    mid = len(ids) // 2
    out = []
    for k, part in enumerate((ids[:mid], ids[mid:])):
        if not part:
            continue
        out.append({"index": chunk["index"],
                    "part": "%s%d" % (chunk.get("part", ""), k),
                    "template": chunk.get("template"),
                    "count": len(part),
                    "zone_ids": part,
                    "expected_output_tokens": estimate_plan_chunk_tokens(len(part)),
                    "budget": chunk.get("budget"),
                    "chunk_count": chunk.get("chunk_count"),
                    "depth": depth + 1,
                    "digest": hashlib.sha256(
                        ("|".join(part)).encode("utf-8")).hexdigest()[:16]})
    return out


# ── ٤ · التحقّق المستقلّ لكل شريحة ──────────────────────────────────────────
def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def validate_chunk(chunk, payload):
    """يتحقّق من مخرج شريحة واحدة **وحدها**، بلا معرفة ببقيّة الشرائح.

    يعيد (مناطق مقبولة بترتيب الشريحة، مسائل). لا يرفع: عطل شريحة لا يُسقط
    التوليد كلّه، بل يُنسَب إليها صراحةً.
    """
    issues = []
    want = list(chunk.get("zone_ids") or [])
    want_set = set(want)
    rooms = []
    if isinstance(payload, dict):
        rooms = payload.get("rooms") or payload.get("zones") or []
    elif isinstance(payload, list):
        rooms = payload
    got = {}
    for r in rooms:
        if not isinstance(r, dict):
            continue
        rid = _norm_id(r.get("id"), len(got))
        if rid not in want_set:
            issues.append({"code": "PLAN_CHUNK_UNKNOWN_ZONE",
                           "chunk": chunk.get("index"), "id": rid})
            continue
        if rid in got:
            issues.append({"code": "PLAN_CHUNK_DUPLICATE_ID",
                           "chunk": chunk.get("index"), "id": rid})
            continue
        rect = r.get("rect")
        vals = [_num(x) for x in rect] if isinstance(rect, (list, tuple)) else []
        if len(vals) != 4 or any(v is None for v in vals) or vals[2] <= 0 \
                or vals[3] <= 0:
            issues.append({"code": "PLAN_CHUNK_BAD_RECT",
                           "chunk": chunk.get("index"), "id": rid})
            continue
        brief = r.get("brief")
        if isinstance(brief, str) and len(brief) > BRIEF_MAX_CHARS:
            issues.append({"code": "PLAN_CHUNK_BRIEF_TRUNCATED",
                           "chunk": chunk.get("index"), "id": rid,
                           "chars": len(brief)})
            brief = brief[:BRIEF_MAX_CHARS]
        out = {"id": rid, "rect": [round(v, 4) for v in vals],
               "role": str(r.get("role") or "")[:40],
               "walls": r.get("walls", "none")}
        if isinstance(brief, str) and brief:
            out["brief"] = brief
        got[rid] = out
    for zid in want:
        if zid not in got:
            issues.append({"code": "PLAN_CHUNK_MISSING_ZONE",
                           "chunk": chunk.get("index"), "id": zid})
    # الترتيب مأخوذ من الشريحة لا من رد النموذج: ترتيبٌ يقرّره المزوّد ليس حتمياً.
    return [got[z] for z in want if z in got], issues


# ── ٥ · الدمج الحتميّ ───────────────────────────────────────────────────────
def fallback_rect(zone, index, site):
    """مستطيل مشتقّ حتميّاً لمنطقة لم تصلها شريحتها.

    ليس تخميناً هندسياً ولا ادّعاء تصميم: شبكة صفّية داخل حدود الأرض، معلَّمة
    في التشخيص بـPLAN_ZONE_UNRESOLVED. البديل — حذف المنطقة — يفقد بنداً طلبه
    العميل، وهو ما يمنعه عقد المشروع صراحةً.
    """
    w = _num((site or {}).get("w")) or 40.0
    d = _num((site or {}).get("d")) or 30.0
    per_row = max(1, int(w // 8) or 1)
    col = index % per_row
    row = index // per_row
    cw = max(2.0, (w - 0.4) / per_row)
    ch = 6.0
    x = round(0.2 + col * cw, 4)
    y = round(0.2 + row * ch, 4)
    if y + ch > d:                      # لا تخرج عن الأرض: تُكدَّس عند الحافة
        y = round(max(0.2, d - ch - 0.2), 4)
    return [x, y, round(max(2.0, cw - 0.2), 4), round(min(ch - 0.2, max(2.0, d - y - 0.2)), 4)]


def merge_plan(outline_zones, chunk_results, envelope):
    """يجمع الشرائح في خطّة واحدة قانونيّة. حتميّ تماماً.

    الحتمية: الترتيب النهائي هو ترتيب البيان، لا ترتيب وصول الشرائح ولا
    ترتيب مفاتيح أي قاموس. تمرير الشرائح مبعثرةً يعطي البايتات نفسها — وهو
    ما يثبّته اختبار «ترتيب الشرائح لا يغيّر المخرج».

    `chunk_results` قائمة (chunk, rooms, issues). الشريحة الغائبة أو الفاشلة
    لا تُسقط مناطقها: تُحَلّ بمستطيل مشتقّ ويُعلَن ذلك.
    """
    issues = []
    resolved = {}
    for chunk, rooms, chunk_issues in chunk_results:
        issues.extend(chunk_issues or [])
        for r in (rooms or []):
            rid = r.get("id")
            if rid in resolved:
                issues.append({"code": "PLAN_CHUNK_DUPLICATE_ID",
                               "id": rid, "chunk": chunk.get("index")})
                continue
            resolved[rid] = r

    site = (envelope or {}).get("site") or {}
    by_template = {}
    unresolved = []
    for i, z in enumerate(outline_zones):
        zid = z["id"]
        tmpl = z.get("template") or "t"
        room = resolved.get(zid)
        if room is None:
            unresolved.append(zid)
            room = {"id": zid, "rect": fallback_rect(z, i, site),
                    "role": z.get("role") or "", "walls": "none",
                    "acs_unresolved": True}
        by_template.setdefault(tmpl, []).append(room)
    if unresolved:
        issues.append({"code": "PLAN_ZONE_UNRESOLVED",
                       "count": len(unresolved), "ids": unresolved[:32]})

    building = {}
    for key in ("site", "floor_height", "wall_h", "wall_t", "levels", "meta"):
        if isinstance(envelope, dict) and key in envelope:
            building[key] = envelope[key]
    building.setdefault("site", {"w": _num(site.get("w")) or 40.0,
                                 "d": _num(site.get("d")) or 30.0})
    building.setdefault("floor_height", 3.2)
    building.setdefault("wall_h", 3.0)
    building.setdefault("wall_t", 0.2)
    # ترتيب القوالب من البيان لا من قاموس: نفس المدخل ⇒ نفس المخرج دائماً.
    tmpl_order = []
    for z in outline_zones:
        t = z.get("template") or "t"
        if t not in tmpl_order:
            tmpl_order.append(t)
    building["floors"] = {t: {"rooms": by_template.get(t, [])}
                          for t in tmpl_order}
    if not building.get("levels"):
        building["levels"] = [{"id": "L%d" % i, "template": t,
                               "elevation": round(i * float(
                                   building["floor_height"]), 3)}
                              for i, t in enumerate(tmpl_order)]
    meta = building.setdefault("meta", {})
    if issues:
        diag = meta.setdefault("acs_stage_diagnostics", [])
        diag.extend(issues)
    meta["acs_plan_contract"] = CONTRACT_VERSION
    return building, issues


def plan_report(strategy_plan, outline_zones, chunking, chunk_results,
                executed=None, measured_zone_tokens=None, capped_zones=0):
    """تقرير آمن للتليمتري — أعداد ورموز فقط، بلا محتوى مبنى ولا نصّ توجيه.

    `chunk_count` هو المخطَّط سلفاً و`chunks_executed` هو المنفَّذ فعلاً؛
    الفارق بينهما هو أثر التكيّف (F-40) والشطر (F-39) وهو ما يُقرأ في
    الإنتاج لمعرفة كم كذّب القياسُ التقديرَ.
    """
    failed = [c.get("index") for c, rooms, iss in chunk_results
              if any(i.get("code") == "PLAN_CHUNK_FAILED" for i in (iss or []))]
    codes = {}
    for _c, _r, iss in chunk_results:
        for i in (iss or []):
            codes[i.get("code")] = codes.get(i.get("code"), 0) + 1
    return {"contract": CONTRACT_VERSION,
            "strategy": (strategy_plan or {}).get("strategy"),
            "size_class": (strategy_plan or {}).get("size_class"),
            "outline_zones": len(outline_zones or []),
            "chunk_count_planned": (chunking or {}).get("chunk_count"),
            "chunks_executed": executed,
            "chunk_size": (chunking or {}).get("chunk_size"),
            "chunk_budget": (chunking or {}).get("budget"),
            "estimated_zone_tokens": estimate_plan_zone_tokens(),
            "measured_zone_tokens": (int(measured_zone_tokens)
                                     if measured_zone_tokens else None),
            "capped": bool((chunking or {}).get("capped")) or capped_zones > 0,
            "capped_zones": int(capped_zones or 0),
            "failed_chunks": failed,
            "issue_codes": codes}


# ── ٦ · عقد المستويات (KI-25 · F-41) ───────────────────────────────────────
def normalise_levels(levels, floors=None):
    """يُعيد المستويات إلى العقد القانونيّ: لكل مستوى `index` صحيح وفريد.

    لماذا هذه الدالة موجودة
    -----------------------
    العقد المُعلَن في acs_understand.py يقول:
        "levels": [ {"index": int, "name": str, "template": str} ]
    والعارض يبني عليه حرفياً: ارتفاع الدور ‎baseY = index × floor_height‎،
    ومفتاح طبقته ‎'F' + index‎. مستوىً بلا `index` يعطي ‎undefined × 4 = NaN‎
    فيُبنى المبنى كلّه عند إحداثيّة غير معرَّفة: الشبكات موجودة، وعدّادها
    صحيح، ولا يرسم منها العتاد شيئاً. لا خطأ يُرفع ولا رسالة تظهر.

    ولذلك لا يكفي أن **يُطلَب** `index` في التوجيه: طاعة النموذج ليست عقداً.
    هذه الدالة هي العقد — تمرّ بها كل خطّة من كل مسار قبل أن تغادر الخادم.

    الاشتقاق حتميّ تماماً
    ---------------------
      · `index` صحيح موجود ⇒ يُحترَم.
      · غائب أو غير صالح ⇒ يُشتقّ من ترتيب `elevation` إن صرّحت به المستويات
        كلّها بأرقام (فالأدنى هو الأرضي)، وإلّا من ترتيب المصفوفة.
      · مكرّر ⇒ الأوّل يحتفظ به والتالي ينزل إلى أوّل رقم حرّ — لا يُحذف
        مستوىً طلبه العميل ولا يُدمج دوران.

    يعيد (المستويات، المسائل). لا يرفع أبداً: مستوىً معطوب لا يُسقط توليداً.
    """
    issues = []
    raw = [l for l in (levels or []) if isinstance(l, dict)]
    if not raw:
        return [], [{"code": "PLAN_LEVELS_EMPTY"}]

    def _int(v):
        if isinstance(v, bool):
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        if f != f or f in (float("inf"), float("-inf")) or f != int(f) or f < 0:
            return None
        return int(f)

    # ترتيب الاشتقاق: الارتفاع إن صرّحت به المستويات كلّها، وإلّا ترتيب المصفوفة.
    elevs = [_num(l.get("elevation")) for l in raw]
    if all(e is not None for e in elevs) and len(set(elevs)) == len(elevs):
        order = [i for i, _e in sorted(enumerate(elevs), key=lambda p: p[1])]
    else:
        order = list(range(len(raw)))
    rank = {}
    for r, i in enumerate(order):
        rank[i] = r

    declared = {}
    for i, l in enumerate(raw):
        declared[i] = _int(l.get("index"))

    out = [None] * len(raw)
    taken = set()
    # أوّلاً من صرّح برقم صحيح — ترتيب المصفوفة يفضّ التكرار حتميّاً.
    for i, l in enumerate(raw):
        idx = declared[i]
        if idx is None or idx in taken:
            continue
        taken.add(idx)
        out[i] = idx
    for i, l in enumerate(raw):
        if out[i] is not None:
            continue
        if declared[i] is not None:
            issues.append({"code": "PLAN_LEVEL_INDEX_DUPLICATE",
                           "id": str(l.get("id") or i), "declared": declared[i]})
        else:
            issues.append({"code": "PLAN_LEVEL_INDEX_DERIVED",
                           "id": str(l.get("id") or i), "from": rank[i]})
        cand = rank[i]
        while cand in taken:
            cand += 1
        taken.add(cand)
        out[i] = cand

    tmpl_keys = set((floors or {}).keys())
    used = set()
    fixed = []
    for i, l in enumerate(raw):
        idx = out[i]
        tmpl = str(l.get("template") or "").strip()
        if not tmpl:
            tmpl = "t"
        if tmpl_keys and tmpl not in tmpl_keys:
            # لا يُصحَّح باختراع قالب: يُعلَن. الدور يظهر بلوحه فارغاً، وسبب
            # فراغه مكتوب بدل أن يبدو عطلاً في العرض.
            issues.append({"code": "PLAN_LEVEL_TEMPLATE_MISSING",
                           "id": str(l.get("id") or idx), "template": tmpl})
        used.add(tmpl)
        lv = dict(l)
        lv["index"] = idx
        lv["template"] = tmpl
        lv["id"] = str(l.get("id") or ("L%d" % idx))
        lv["name"] = str(l.get("name") or lv["id"])
        fixed.append(lv)

    for orphan in sorted(tmpl_keys - used):
        # قالب لا يشير إليه مستوى = غرفٌ بناها المولّد ولن يراها أحد. تُعلَن.
        issues.append({"code": "PLAN_TEMPLATE_ORPHANED", "template": orphan,
                       "rooms": len(((floors or {}).get(orphan) or {})
                                    .get("rooms") or [])})

    fixed.sort(key=lambda l: (l["index"], str(l["id"])))
    return fixed, issues


# ── ٧ · العقد المُعلَن ──────────────────────────────────────────────────────
def spec():
    return {"module": "acs_plan_chunks",
            "contract_version": CONTRACT_VERSION,
            "stages": [STAGE_OUTLINE, STAGE_PLAN_CHUNK, "detail"],
            "brief_max_chars": BRIEF_MAX_CHARS,
            "chunk_safety": CHUNK_SAFETY,
            "min_chunk_zones": MIN_CHUNK_ZONES,
            "max_chunk_zones": MAX_CHUNK_ZONES,
            "max_plan_chunks": MAX_PLAN_CHUNKS,
            "max_chunk_splits": MAX_CHUNK_SPLITS,
            "verbosity_tolerance": VERBOSITY_TOLERANCE,
            "pilot_zones": PILOT_ZONES,
            "outline_budget": outline_budget(),
            "plan_chunk_budget": plan_chunk_budget(),
            "plan_zone_tokens": estimate_plan_zone_tokens(),
            "chunk_size": chunk_size_for(),
            "issue_codes": list(ISSUE_CODES),
            "guarantees": [
                "no stage depends on an unbounded model response",
                "chunk size is derived from measured output cost, not from "
                "an estimate the provider is free to ignore",
                "chunk identity and order come from the outline, not from the "
                "provider response order",
                "merge output is byte-identical under any chunk arrival order",
                "a truncated chunk is split, never re-sent unchanged",
                "a failed chunk never deletes a zone the customer asked for",
                "no zone id is invented from randomness or wall-clock time",
            ]}
