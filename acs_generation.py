# -*- coding: utf-8 -*-
# =============================================================================
# acs_generation.py  --  عقد ميزانية المخرج واستراتيجية التوليد
#
# سبب وجود هذا الملف: كانت ميزانية المخرج موزّعة على خمسة ثوابت غير مترابطة
# (ACS_MAX_TOKENS في نداء الفهم، وثابت 32000 و16000 و8000 داخل سلّم المحاولات،
# وACS_MAX_TOKENS_PLAN، وACS_MAX_TOKENS_DETAIL، وACS_MAX_TOKENS_REPAIR)، ولم يكن
# أحد يقدّر حجم المخرج المتوقّع قبل النداء. فكان القرار «مرحلة واحدة أم مراحل»
# يُتّخذ بطول **المدخل** وحده (طول الوصف وعدد نقاطه)، وهو مقياس لا علاقة له بحجم
# المخرج: «مستودع 20×15م» وصفٌ من سطر واحد يستدعي مخرجاً صناعياً كاملاً.
#
# هنا مصدر واحد للحقيقة:
#   1) ميزانية مخرج واحدة معلنة: ACS_LLM_MAX_OUTPUT_TOKENS.
#   2) حصص المراحل مشتقّة منها بنِسَب، لا أرقاماً مستقلّة.
#   3) مقدّر حتمي لحجم المخرج المتوقّع (بلا نداء نموذج) يصنّف الطلب
#      SMALL / MEDIUM / LARGE / VERY_LARGE.
#   4) اختيار الاستراتيجية من التصنيف وحده.
#
# التصنيف يختار **طريقة التوليد** فقط. لا يمسّ متطلّبات العميل الهندسية ولا
# يحذف بنداً ولا يغيّر بُعداً — تلك مسألة KI-1 وهي خارج نطاق هذا الملف تماماً.
# =============================================================================

import os
import re

GENERATION_CONTRACT_VERSION = "acs-generation-budget/1.0.0"

# ── 1) الميزانية الواحدة ────────────────────────────────────────────────────
# ACS_MAX_TOKENS يبقى مقبولاً كاسم قديم حتى لا ينكسر نشر قائم، لكنه لم يعد
# مصدراً ثانياً: يُقرأ كمرادف ثمّ يُنسى.
_DEFAULT_MAX_OUTPUT = 32000


def max_output_tokens():
    for name in ("ACS_LLM_MAX_OUTPUT_TOKENS", "ACS_MAX_TOKENS"):
        raw = os.environ.get(name)
        if raw:
            try:
                v = int(raw)
                if v > 0:
                    return v
            except ValueError:
                pass
    return _DEFAULT_MAX_OUTPUT


# حصّة كل مرحلة من الميزانية الواحدة. الخطة مخرجها صغير بطبعه (هيكل بلا تفاصيل)،
# ومجموعة التفصيل أكبر، وجولة الإصلاح تعيد النموذج كاملاً فتأخذ الميزانية كلّها.
STAGE_SHARE = {
    "single": 1.00,
    "plan":   0.50,
    "detail": 0.75,
    "repair": 1.00,
}
# أسماء قديمة تُحترم إن ضُبطت صراحةً في بيئة قائمة، وإلا فالاشتقاق هو القاعدة.
_LEGACY_STAGE_ENV = {
    "plan":   "ACS_MAX_TOKENS_PLAN",
    "detail": "ACS_MAX_TOKENS_DETAIL",
    "repair": "ACS_MAX_TOKENS_REPAIR",
}
STAGE_FLOOR = 4000                 # لا مرحلة بميزانية أصغر من هذا


def stage_budget(stage):
    """ميزانية المرحلة — مشتقّة من الميزانية الواحدة، لا ثابتاً مستقلاً."""
    env = _LEGACY_STAGE_ENV.get(stage)
    if env and os.environ.get(env):
        try:
            v = int(os.environ[env])
            if v > 0:
                return v
        except ValueError:
            pass
    share = STAGE_SHARE.get(stage, 1.0)
    return max(STAGE_FLOOR, int(max_output_tokens() * share))


# ── 2) المقدّر الحتمي ───────────────────────────────────────────────────────
# التكاليف بالرموز (tokens) لكلّ عنصر، مقيسة على شكل المخرج الفعلي للمشروع:
# كائن Room كامل بمفاتيحه ومصفوفاته، بترميز JSON عربي غير مضغوط.
T_ENVELOPE      = 260      # site + levels + floor_height + wall_h + wall_t + إطار
T_ROOM_BASE     = 90       # id + rect + role + walls + الأقواس
T_DOOR          = 34
T_WINDOW        = 40
T_POINT         = 26
T_FURNITURE     = 52
T_RACK_ROW      = 60       # صفّ رفوف مضغوط (لا رفّ مفرد)
T_LANE          = 48
T_STATION_ROW   = 46
T_DOCK_ROW      = 46
T_REQUIREMENT   = 45       # سطر واحد في meta.requirements

# كثافات افتراضية لكل منطقة حين لا يحدّد العميل. مأخوذة من نصّ التعليمات نفسه
# (المثال المرجعي يعطي غرفة سكنية 13 نقطة وقطعتَي أثاث).
DENSITY = {
    "residential": {"doors": 1.2, "windows": 1.1, "points": 13, "furniture": 2.5,
                    "racks": 0, "lanes": 0, "stations": 0, "docks": 0},
    "industrial":  {"doors": 0.8, "windows": 0.3, "points": 9,  "furniture": 0.8,
                    "racks": 1.6, "lanes": 1.4, "stations": 0.8, "docks": 0.5},
}

INDUSTRIAL = ("warehouse", "industrial", "factory", "logistics")

# كلمات تدلّ على منطقة/حيّز مطلوب — تُستعمل لتقدير عدد المناطق من نصّ قصير.
_ZONE_WORDS = (
    "منطقة", "مناطق", "غرفة", "غرف", "قاعة", "صالة", "مكتب", "مكاتب", "ممر",
    "مستودع", "تخزين", "استقبال", "استلام", "شحن", "تغليف", "فرز", "التقاط",
    "صيانة", "ورشة", "رصيف", "أرصفة", "دورة مياه", "حمام", "مطبخ", "مجلس",
    "نوم", "بلكونة", "موقف", "درج", "مصعد",
    "zone", "room", "area", "hall", "office", "corridor", "storage",
    "receiving", "shipping", "packing", "sorting", "picking", "dock",
)
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

# متوسّط مساحة المنطقة الواحدة بالمتر المربّع، حين نستدلّ العدد من المسطّح.
AREA_PER_ZONE = {"residential": 35.0, "industrial": 180.0}
FLOOR_FACTOR_CAP = 3.0             # قوالب الأدوار مشتركة — لا تتضاعف بلا حدّ
MIN_ZONES = 2
MAX_ESTIMATED_ZONES = 400          # حارس ضدّ تقدير هارب من مدخل عدائي


def _is_industrial(btype):
    return str(btype or "").lower() in INDUSTRIAL


def _numbers(text):
    return [int(n) for n in re.findall(r"\d{1,4}",
                                       (text or "").translate(_ARABIC_DIGITS))]


def estimate_zones(description, btype=None, site_w=None, site_d=None, floors=None):
    """عدد المناطق المتوقّع — من ألفاظ الوصف ومن المسطّح، أيّهما أكبر.

    نأخذ الأكبر عمداً: التقليل يعني اختيار مرحلة واحدة لطلب لا يسعها، وهو العطل
    الذي نعالجه؛ والمبالغة تعني مراحل زائدة، وكلفتها زمنٌ لا فشل.
    """
    d = (description or "")
    industrial = _is_industrial(btype)
    kind = "industrial" if industrial else "residential"

    words = sum(d.count(w) for w in _ZONE_WORDS)
    # عدد صريح **ملتصق بلفظ حيّز** مثل «١٢ محطة» أو «8 أرصفة» يرفع التقدير.
    # الأرقام المجرّدة لا تُحسب: «مستودع 20×15م» أبعادُ أرض، لا عشرون منطقة —
    # وقراءتها عدداً كانت تصنّف الطلب الإنتاجي MEDIUM بدل SMALL.
    explicit = 0
    for m in re.finditer(r"(\d{1,3})\s*(?:من\s+)?([^\W\d_]+)",
                         d.translate(_ARABIC_DIGITS)):
        n, word = int(m.group(1)), m.group(2)
        # الاتّجاه واحد فقط: الكلمة تبدأ بلفظ الحيّز كاملاً («حمامات»←«حمام»،
        # «أرصفة»←«أرصفة»). العكس يجعل حرف «م» في «20×15م» يطابق «منطقة»،
        # فيُقرأ ١٥ منطقة من مقاس أرض — وهو ما رفع الطلب الإنتاجي من SMALL.
        if n <= 120 and len(word) >= 3 and any(word.startswith(w)
                                               for w in _ZONE_WORDS if len(w) >= 3):
            explicit = max(explicit, n)
    by_text = max(words, explicit)

    by_area = 0
    if site_w and site_d:
        try:
            area = float(site_w) * float(site_d)
            by_area = int(area / AREA_PER_ZONE[kind]) + 1
        except (TypeError, ValueError):
            by_area = 0

    zones = max(MIN_ZONES, by_text, by_area)
    # قوالب الأدوار مشتركة، فالأدوار لا تضاعف المناطق إلا جزئياً
    try:
        nf = int(floors or 1)
    except (TypeError, ValueError):
        nf = 1
    if nf > 1:
        zones = int(zones * min(FLOOR_FACTOR_CAP, 1.0 + 0.35 * (nf - 1)))
    return min(MAX_ESTIMATED_ZONES, zones)


def estimate_output_tokens(description, btype=None, site_w=None, site_d=None,
                           floors=None, zones=None):
    """تقدير حتمي لحجم المخرج بالرموز. لا نداء نموذج، ولا عشوائية."""
    industrial = _is_industrial(btype)
    dens = DENSITY["industrial" if industrial else "residential"]
    z = int(zones if zones is not None else
            estimate_zones(description, btype, site_w, site_d, floors))
    per_zone = (T_ROOM_BASE
                + dens["doors"] * T_DOOR
                + dens["windows"] * T_WINDOW
                + dens["points"] * T_POINT
                + dens["furniture"] * T_FURNITURE
                + dens["racks"] * T_RACK_ROW
                + dens["lanes"] * T_LANE
                + dens["stations"] * T_STATION_ROW
                + dens["docks"] * T_DOCK_ROW)
    reqs = max(3, min(60, len(_numbers(description)) + 4))
    total = T_ENVELOPE + z * per_zone + reqs * T_REQUIREMENT
    return int(total), z


# ── 3) التصنيف والاستراتيجية ───────────────────────────────────────────────
SMALL, MEDIUM, LARGE, VERY_LARGE = "SMALL", "MEDIUM", "LARGE", "VERY_LARGE"
CLASSES = (SMALL, MEDIUM, LARGE, VERY_LARGE)

# نِسَب من الميزانية الواحدة. عتبة المرحلة الواحدة هي MEDIUM: أي أن المخرج
# المقدَّر يجب أن يبقى تحت 60% من الميزانية حتى نجازف بنداء واحد — الهامش
# لتفاوت التقدير، ولأنّ الانقطاع يكلّف نداءً كاملاً ضائعاً.
CLASS_RATIO = ((SMALL, 0.25), (MEDIUM, 0.60), (LARGE, 1.50))
SINGLE_STAGE_MAX_CLASS = MEDIUM
SINGLE_STAGE_SAFETY = 0.60         # = نسبة MEDIUM؛ معلنة صراحةً للاختبارات

STRATEGY_SINGLE = "single"
STRATEGY_STAGED = "staged"


def classify(estimated_tokens, budget=None):
    b = int(budget or max_output_tokens())
    for name, ratio in CLASS_RATIO:
        if estimated_tokens <= b * ratio:
            return name
    return VERY_LARGE


def plan_strategy(description, btype=None, site_w=None, site_d=None,
                  floors=None, forced=None):
    """القرار الكامل قبل أي نداء: تقدير، تصنيف، استراتيجية، ميزانيات.

    `forced` يعكس ACS_DEEP / وسيط الطلب: True يفرض المراحل، False يفرض النداء
    الواحد، None يترك القرار للتقدير.
    """
    budget = max_output_tokens()
    est, zones = estimate_output_tokens(description, btype, site_w, site_d, floors)
    cls = classify(est, budget)
    if forced is True:
        strategy, why = STRATEGY_STAGED, "forced"
    elif forced is False:
        strategy, why = STRATEGY_SINGLE, "forced"
    elif cls in (SMALL, MEDIUM):
        strategy, why = STRATEGY_SINGLE, "estimate_fits"
    else:
        strategy, why = STRATEGY_STAGED, "estimate_exceeds_budget"
    return {"contract": GENERATION_CONTRACT_VERSION,
            "estimated_output_tokens": est,
            "estimated_zones": zones,
            "size_class": cls,
            "max_output_tokens": budget,
            "single_stage_threshold_tokens": int(budget * SINGLE_STAGE_SAFETY),
            "strategy": strategy,
            "reason": why,
            "stage_budgets": {s: stage_budget(s)
                              for s in ("single", "plan", "detail", "repair")}}


# ── 4) حدود التصعيد ────────────────────────────────────────────────────────
# الانقطاع لا يُعالَج بإعادة النداء نفسه: يُعالَج بتغيير الاستراتيجية، ثم بتقسيم
# المجموعة التي انقطعت. وكلاهما محدود عدداً حتى لا تدور الخدمة على نفسها.
MAX_STRATEGY_ESCALATIONS = int(os.environ.get("ACS_MAX_ESCALATIONS", "1"))
MAX_GROUP_SPLITS = int(os.environ.get("ACS_MAX_GROUP_SPLITS", "2"))
MIN_GROUP_SIZE = 1


def split_group(rooms):
    """يقسم مجموعة تفصيل انقطع مخرجها إلى نصفين حتميّين. لا يعيد مجموعة فارغة."""
    if len(rooms) <= MIN_GROUP_SIZE:
        return None
    mid = len(rooms) // 2
    return [rooms[:mid], rooms[mid:]]


# ── 5) تعليمة اقتصاد المخرج ────────────────────────────────────────────────
# تُلحَق بالتعليمات. تتكلّم عن **شكل** المخرج لا عن محتواه الهندسي: لا تحذف بنداً
# ولا تغيّر بُعداً ولا تمسّ قرارات المحرّك التلقائية (KI-1) — تمنع فقط تعداد آلاف
# القطع المتطابقة حين يوجد تمثيل مضغوط مكافئ في المخطّط نفسه.
COMPACT_RULE = r"""
اقتصاد المخرج (شكل الإخراج فقط — لا يغيّر أي متطلّب هندسي):
- استخدم التمثيل المضغوط المدعوم في المخطّط بدل تعداد القطع المتطابقة:
  racks (صفّ يولّد مئات الأرفف) · lanes · stations مع count/pitch/dir ·
  docks مع count/pitch. لا تكتب رفّاً أو محطة أو رصيفاً واحداً واحداً.
- لا تكرّر كائناً متطابقاً إلا إذا طلب العميل بياناتٍ مميّزة لكل نسخة صراحةً.
- في meta: اجعل كل سطر في requirements/extras/added جملة واحدة قصيرة تشير إلى
  معرّف المنطقة. لا تُعِد نصّ الطلب كاملاً، ولا تصف النموذج مرّة ثانية بالكلمات.
- لا شرح ولا تعليق خارج كائن JSON. كائن واحد في المستوى الأعلى، لا أكثر.
"""
