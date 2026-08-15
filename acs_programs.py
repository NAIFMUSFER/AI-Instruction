# -*- coding: utf-8 -*-
# =============================================================================
# acs_programs.py — سجل برامج أنواع المباني (المصدر الوحيد للحقيقة).
#
# البرنامج = مفردات نوع المبنى + تصنيفات فراغاته + اقتراحات اختيارية.
# البرنامج ليس محرّكاً ولا يفرض متطلّبات ولا يدّعي مطابقة أي كود.
# النواة (الهندسة/الأدوار/الفراغات/العناصر) تبقى عامّة ومستقلّة عن البرامج.
#
# النطاق الصناعي مطابق تماماً لما كان في المرحلة 1، حتى تبقى عزلة الصناعي
# كما هي في acs_validate / acs_layout / acs_compiler بلا أي تعديل عليها.
# =============================================================================
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "acs_programs.json")

with open(_PATH, "r", encoding="utf-8") as _f:
    REGISTRY = json.load(_f)

PROGRAMS = {p["id"]: p for p in REGISTRY["programs"]}
INDUSTRIAL = set(REGISTRY["industrial_domain"])
DEFAULT_PROGRAM = REGISTRY.get("default_program", "residential")
_DET = REGISTRY.get("detection", {})
_STRONG_W = int(_DET.get("strong_weight", 3))
_WEAK_W = int(_DET.get("weak_weight", 1))
_IND_MIN = int(_DET.get("industrial_min_score", 3))


def is_industrial(building_type):
    """هل النوع ضمن النطاق الصناعي؟ (نفس مجموعة المرحلة 1 حرفياً)"""
    return str(building_type or "").lower() in INDUSTRIAL


def program(pid):
    return PROGRAMS.get(str(pid or "").lower())


def space_categories(pid):
    """تصنيفات الفراغات المقترحة للبرنامج — تصنيف فقط، بلا قواعد."""
    p = program(pid)
    if not p:
        return []
    return list(REGISTRY.get("space_categories", {}).get(p.get("categories", ""), []))


def suggested_spaces(pid):
    """اقتراحات إرشادية. أي عنصر يُؤخذ منها يُصنَّف AI_SUGGESTED/SYSTEM_DEFAULT — لا USER_REQUESTED."""
    return list(REGISTRY.get("suggested_spaces", {}).get(str(pid or "").lower(), []))


def _score(text, pid):
    """(النقاط, أوّل موضع لكلمة مفتاحية) — الموضع يفصل التعادل لصالح الاسم الوارد أولاً."""
    p = PROGRAMS[pid]
    score, first = 0, None
    for kw in p.get("strong", []):
        i = text.find(kw)
        if i >= 0:
            score += _STRONG_W
            first = i if first is None else min(first, i)
    for kw in p.get("weak", []):
        if text.find(kw) >= 0:
            score += _WEAK_W
    return score, (first if first is not None else 10 ** 6)


def detect_type(text, explicit=None):
    """يكشف برنامج المبنى من الوصف. الاختيار الصريح من الواجهة يغلب الكشف دائماً.

    منطق موحّد يستخدمه الخادم والواجهة معاً:
      • كلمة قاطعة = 3 نقاط، كلمة محتملة = 1.
      • الصناعي لا يُختار إلا بنقاط >= 3 وتفوّق واضح على المؤشّرات السكنية
        (نفس حارس المرحلة 1: "رفوف تخزين" في بيت لا تجعله مستودعاً).
      • عند التعادل يفوز البرنامج الذي ورد اسمه أولاً في النص.
      • الافتراضي سكني.
    """
    if explicit and str(explicit).lower() not in ("", "auto", "none"):
        return str(explicit).lower()
    t = (text or "").lower()

    scores = {pid: _score(t, pid) for pid in PROGRAMS}
    res_score = max(scores[p][0] for p in ("residential", "villa", "apartment"))

    ind = [(s, -pos, pid) for pid, (s, pos) in scores.items() if pid in INDUSTRIAL and s > 0]
    if ind:
        best_s, neg_pos, best_pid = max(ind)
        if best_s >= _IND_MIN and best_s > res_score:
            return best_pid

    gen = [(s, -pos, pid) for pid, (s, pos) in scores.items() if pid not in INDUSTRIAL and s > 0]
    if gen:
        best_s, neg_pos, best_pid = max(gen)
        if best_s >= _STRONG_W:            # لا نختار نوعاً إلا بدليل قاطع
            return best_pid
    return DEFAULT_PROGRAM


def program_context(pid):
    """سياق نصّي مختصر يمكن تمريره للنموذج — إرشادي، وممنوع أن يُقدَّم كمتطلّب."""
    p = program(pid)
    if not p:
        return ""
    cats = space_categories(pid)
    if not cats:
        return ""
    return ("سياق نوع المبنى (%s): تصنيفات الفراغات الشائعة: %s. "
            "هذه إرشادية فقط — لا تُضِف فراغاً لم يطلبه العميل، وإن أضفت شيئاً "
            "فاذكره في added لا في requirements." % (p.get("name_ar", pid), " · ".join(cats)))
