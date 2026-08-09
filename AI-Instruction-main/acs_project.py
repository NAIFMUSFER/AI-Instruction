# -*- coding: utf-8 -*-
# =============================================================================
# acs_project.py — طبقة المشروع (PROJECT → SITE → BUILDINGS → FLOORS → SPACES).
#
# طبقة مُحوِّل (adapter) لا كتابة جديدة: نموذج المرحلة 1 (site/levels/floors)
# يبقى كما هو تماماً ويصبح "عقدة مبنى" داخل المشروع. لا كسر ولا فقدان بيانات.
#
# اصطلاح الإحداثيات (موثّق، غير مُغيَّر عن المرحلة 1):
#   X = العرض شرق-غرب · Z = العمق شمال-جنوب (z=0 الواجهة الشمالية) · Y = الارتفاع لأعلى
#   الوحدات: متر · الأصل (0,0,0) ركن الموقع · منسوب الدور = level.index * floor_height
#   موضع المبنى داخل الموقع: building.position {x, z, rotation°} (افتراضي 0,0,0)
# =============================================================================

SCHEMA = "acs.project/1"


def _slug(s, fallback):
    s = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in str(s or "").strip())
    return (s or fallback)[:48]


def is_project(obj):
    return isinstance(obj, dict) and isinstance(obj.get("project"), dict)


def is_building(obj):
    """نموذج المرحلة 1: يحوي floors (و levels عادةً) بلا غلاف مشروع."""
    return isinstance(obj, dict) and not is_project(obj) and isinstance(obj.get("floors"), dict)


def new_ids(building, index=0):
    meta = building.get("meta") or {}
    bid = _slug(meta.get("id") or meta.get("name") or ("bld_%d" % index), "bld_%d" % index)
    return bid


def ensure_element_ids(building, building_id):
    """يضيف معرّفات مستقرّة للأدوار والفراغات دون حذف أي حقل قائم (إضافي فقط)."""
    fh = float(building.get("floor_height") or (float(building.get("wall_h") or 3.0) + 0.2))
    for lvl in building.get("levels") or []:
        idx = int(lvl.get("index", 0))
        lvl.setdefault("id", "%s.flr_%d" % (building_id, idx))
        lvl.setdefault("elevation", round(idx * fh, 3))
    for tmpl, fdef in (building.get("floors") or {}).items():
        for i, room in enumerate((fdef or {}).get("rooms") or []):
            room.setdefault("space_id", "%s.%s.%s" % (building_id, tmpl, room.get("id") or ("sp_%d" % i)))
    return building


def to_project(data, name=None, project_id=None):
    """يلفّ نموذج مبنى (المرحلة 1) في مشروع، أو يعيد المشروع كما هو.

    الغلاف إضافي بالكامل: حقول المرحلة 1 تبقى في مكانها على المبنى النشط،
    فلا يتعطّل أي مستهلك قديم.
    """
    if is_project(data):
        return data
    if not is_building(data):
        raise ValueError("ليس نموذج مبنى ولا مشروعاً صالحاً")

    meta = data.get("meta") or {}
    btype = str(meta.get("type") or "residential").lower()
    bid = new_ids(data, 0)
    ensure_element_ids(data, bid)
    site = dict(data.get("site") or {"w": 30.0, "d": 25.0})
    site.setdefault("id", "site_0")
    site.setdefault("units", "m")
    site.setdefault("north", meta.get("north", "-Z"))
    site.setdefault("origin", {"x": 0, "y": 0, "z": 0})

    return {
        "schema": SCHEMA,
        "project": {
            "id": _slug(project_id or "prj_0", "prj_0"),
            "name": name or meta.get("name") or "مشروع",
            "site": site,
            "buildings": [{
                "id": bid,
                "name": meta.get("name") or "مبنى 1",
                "building_type": btype,
                "programs": [btype],
                "position": {"x": 0, "z": 0, "rotation": 0},
                "active": True,
                "building": data,          # عقدة المرحلة 1 كما هي — بلا نسخ ولا تعديل
            }],
            "meta": {"created_from": "phase1_building"},
        },
    }


def active_building(data):
    """يعيد عقدة المبنى بصيغة المرحلة 1 (للعارض/المترجم) من مشروع أو مبنى."""
    if is_building(data):
        return data
    if not is_project(data):
        raise ValueError("لا يوجد مبنى صالح")
    blds = (data.get("project") or {}).get("buildings") or []
    if not blds:
        raise ValueError("المشروع بلا مبانٍ")
    for b in blds:
        if b.get("active") and isinstance(b.get("building"), dict):
            return b["building"]
    return blds[0].get("building")


def buildings(data):
    """قائمة (معرّف, عقدة مبنى) لكل مباني المشروع — يدعم المجمّعات والحرم والمختلط."""
    if is_building(data):
        return [(new_ids(data, 0), data)]
    return [(b.get("id"), b.get("building")) for b in
            ((data.get("project") or {}).get("buildings") or []) if isinstance(b.get("building"), dict)]


def add_building(project, building, building_type=None, name=None, position=None, active=False):
    """يضيف مبنى إلى مشروع قائم (مجمّع/منتجع/حرم/متعدد الاستخدامات)."""
    if not is_project(project):
        project = to_project(project)
    blds = project["project"].setdefault("buildings", [])
    idx = len(blds)
    bid = _slug((building.get("meta") or {}).get("id") or name or ("bld_%d" % idx), "bld_%d" % idx)
    ensure_element_ids(building, bid)
    if active:
        for b in blds:
            b["active"] = False
    blds.append({
        "id": bid,
        "name": name or "مبنى %d" % (idx + 1),
        "building_type": str(building_type or (building.get("meta") or {}).get("type") or "residential").lower(),
        "programs": [str(building_type or (building.get("meta") or {}).get("type") or "residential").lower()],
        "position": position or {"x": 0, "z": 0, "rotation": 0},
        "active": bool(active),
        "building": building,
    })
    return project


def stats(data):
    """إحصاء عام يخدم اختبارات التوافق: عدد المباني/الأدوار/الفراغات/العناصر."""
    out = {"buildings": 0, "levels": 0, "spaces": 0, "objects": 0}
    for _bid, b in buildings(data):
        if not isinstance(b, dict):
            continue
        out["buildings"] += 1
        out["levels"] += len(b.get("levels") or [])
        for fdef in (b.get("floors") or {}).values():
            rooms = (fdef or {}).get("rooms") or []
            out["spaces"] += len(rooms)
            for r in rooms:
                for o in (r.get("objects") or []):
                    out["objects"] += max(1, int(o.get("count") or 1))
    return out
