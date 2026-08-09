# -*- coding: utf-8 -*-
# =============================================================================
# acs_bim.py — طبقة التبادل مع نماذج البناء (BIM).
#
# تُصدِّر النموذج القانوني إلى ملفّ IFC4 حقيقي بصيغة ISO-10303-21، وتقرأ ملفّات
# STEP قراءةً فعلية (مُحلِّل نصّي كامل لا افتراض)، ثمّ تُرحّلها إلى نموذج تجهيز
# خارجي لا يمسّ النموذج الهندسي إطلاقاً.
#
# مبادئ صارمة:
#   • النموذج القانوني وحده مرجع الهندسة؛ ملفّ BIM بيانات خارجية حتى يُودَع.
#   • لا كتابة مباشرة من استيراد إلى نموذج: كل قبول يمرّ بمسار تأليف المرحلة 5.
#   • لا وحدة تُخمَّن، ولا سماكة تُخترَع، ولا كيان غير مدعوم يُنتحَل نوعاً مدعوماً.
#   • كل اجتياز يكشف الحلقات؛ كل حدّ منتهٍ ومعلَن؛ لا جلب لأي مورد بعيد.
#   • اسم مادّة خارجية ليس دليل مقاومة حريق ولا رتبة إنشائية ولا مطابقة.
# =============================================================================
import hashlib
import json
import math
import os

import acs_ingest as ING

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_bim.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
VERSION = SPEC["version"]
COMPILER = SPEC["compiler_version"]
PARSER_VERSION = "acs-bim-step/1.0.0"
MAPPER_VERSION = "acs-bim-map/1.0.0"
LIMITS = SPEC["limits"]
TOL = SPEC["tolerances"]
LENGTH_UNITS = SPEC["length_units"]
ANGLE_UNITS = SPEC["angle_units"]
ISSUE_CODES = tuple(SPEC["issue_codes"])
BLOCKING = tuple(SPEC["blocking_issue_codes"])
UNSAFE = tuple(SPEC["unsafe_patterns"])
FORBIDDEN_KEYS = tuple(SPEC["forbidden_property_keys"])
ENTITY_SUPPORT = {e["entity"]: e for e in SPEC["entity_support"]}
# مفتاح غير حسّاس لحالة الأحرف: STEP يكتب الأنواع بحروف كبيرة والمواصفة
# تكتبها بصيغة IFC المعتادة، فالبحث يجب أن يجمع الصيغتين
ENTITY_SUPPORT_UPPER = {k.upper(): v for k, v in ENTITY_SUPPORT.items()}
GUID_ALPHABET = SPEC["global_id_alphabet"]
# جسر التأليف: المصدر ونوع الأمر معلَنان في المواصفة، ولا تخترع هذه المرحلة
# مفردة واحدة خارج مفردات المرحلة الخامسة
COMMAND_SOURCE = SPEC["import_command_source"]
COMMAND_MAP = dict(SPEC["import_command_map"])


# ----------------------------------------------------------------- أدوات ----
def _q(v):
    return round(float(v), 6) + 0.0


def _num(v):
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def _canon(o):
    return ING.canonical_json(o)


def _sha16(o):
    return hashlib.sha256(_canon(o).encode("utf-8")).hexdigest()[:16]


def _sha256_text(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def issue(code, severity="ERROR", entity_id=None, message="", blocking=None):
    """كل خلل يُعاد ككائن مُصنَّف — لا نصّ استثناء بوصفه عقد واجهة."""
    if code not in ISSUE_CODES:
        code = "BIM_INVALID_FILE"
    if blocking is None:
        blocking = code in BLOCKING and severity == "ERROR"
    return {"code": code, "severity": severity, "entity_id": entity_id,
            "message": message, "blocking": bool(blocking)}


def is_unsafe(v):
    """نصّ خارجي يحمل وسماً أو مخطّطاً تنفيذياً يُرفض، لا يُنظَّف."""
    if not isinstance(v, str):
        return False
    if "\x00" in v:
        return True
    for ch in v:
        if ord(ch) < 32 and ch not in "\t":
            return True
    low = v.lower()
    for p in UNSAFE:
        if p.lower() in low:
            return True
    return False


def safe_key(k):
    """مفتاح خاصّية خارجي مقبول: لا مفتاح نموذج أوّلي ولا مسار كائن."""
    if not isinstance(k, str) or not k or len(k) > 255:
        return False
    if k in FORBIDDEN_KEYS:
        return False
    return is_safe_id(k.replace(" ", "_"))


def is_safe_id(v):
    import re as _re
    return isinstance(v, str) and _re.match(SPEC["safe_id_pattern"], v) is not None


# ------------------------------------------------- معرّفات IFC حتميّة ------
def ifc_guid(seed):
    """معرّف IFC عالمي مشتقّ حتميّاً — 22 محرفاً بترميز IFC القاعدي 64.

    نفس النموذج ونفس المعرّف القانوني ونفس المخطّط تُعطي دائماً نفس المعرّف،
    فلا عشوائية تُفسد حتمية التصدير.
    """
    h = hashlib.sha256(_canon(seed).encode("utf-8")).hexdigest()[:32]
    n = int(h, 16)
    out = []
    # أوّل محرف يمثّل بتَّين فقط، ثم عشرون مجموعة من ستّة بتّات (وفق ترميز IFC)
    digits = []
    for _ in range(21):
        digits.append(n & 0x3F)
        n >>= 6
    digits.append(n & 0x03)
    digits.reverse()
    for d in digits:
        out.append(GUID_ALPHABET[d])
    return "".join(out)


# ================================================================ التصدير ===
_STEP_ESCAPE_NOTE = ("IFC strings are ISO-10303-21 encoded: apostrophes are doubled, "
                     "backslashes are doubled, and any character outside the basic "
                     "printable set is written as an \\X2\\ UTF-16 sequence.")


def step_string(v):
    """ترميز نصّ STEP: يحمي الفاصلة العليا والشرطة المائلة ويرمّز العربية."""
    if v is None:
        return "$"
    s = str(v)
    out = []
    buf = []

    def flush():
        if buf:
            out.append("\\X2\\" + "".join(buf) + "\\X0\\")
            del buf[:]

    for ch in s:
        o = ord(ch)
        if 32 <= o <= 126:
            flush()
            if ch == "'":
                out.append("''")
            elif ch == "\\":
                out.append("\\\\")
            else:
                out.append(ch)
        else:
            # ما خرج عن المجموعة الأساسية يُرمَّز UTF-16 كبيرَ النهاية
            if o > 0xFFFF:
                o -= 0x10000
                buf.append("%04X" % (0xD800 + (o >> 10)))
                buf.append("%04X" % (0xDC00 + (o & 0x3FF)))
            else:
                buf.append("%04X" % o)
    flush()
    return "'" + "".join(out) + "'"


def step_real(v):
    """رقم STEP حقيقي: صيغة ثابتة بفاصلة عشرية دائماً، بلا أسّ ولا محلّية."""
    n = _num(v)
    if n is None:
        return "$"
    r = round(n, 6) + 0.0
    if r == 0:
        return "0."
    s = "%.6f" % r
    s = s.rstrip("0")
    if s.endswith("."):
        s += "0" if False else ""
    return s if s.endswith(".") else s


class StepFile(object):
    """كاتب ملفّ STEP: يرقّم الكيانات ويمنع تكرار البدائيات الهندسية."""

    def __init__(self):
        self.lines = []
        self.n = 0
        self._cache = {}

    def add(self, type_name, args, dedup=False):
        if dedup:
            key = type_name + "|" + args
            if key in self._cache:
                return self._cache[key]
        self.n += 1
        ref = "#%d" % self.n
        self.lines.append("%s=%s(%s);" % (ref, type_name, args))
        if dedup:
            self._cache[type_name + "|" + args] = ref
        return ref

    def point(self, x, y, z=None):
        if z is None:
            return self.add("IFCCARTESIANPOINT", "(%s,%s)"
                            % (step_real(x), step_real(y)), True)
        return self.add("IFCCARTESIANPOINT", "(%s,%s,%s)"
                        % (step_real(x), step_real(y), step_real(z)), True)

    def direction(self, x, y, z=None):
        if z is None:
            return self.add("IFCDIRECTION", "(%s,%s)"
                            % (step_real(x), step_real(y)), True)
        return self.add("IFCDIRECTION", "(%s,%s,%s)"
                        % (step_real(x), step_real(y), step_real(z)), True)

    def axis(self, x, y, z, rot_deg=0.0):
        p = self.point(x, y, z)
        zd = self.direction(0.0, 0.0, 1.0)
        a = math.radians(float(rot_deg or 0.0))
        xd = self.direction(_q(math.cos(a)), _q(math.sin(a)), 0.0)
        return self.add("IFCAXIS2PLACEMENT3D", "%s,%s,%s" % (p, zd, xd), True)

    def placement(self, parent, x, y, z, rot_deg=0.0):
        ax = self.axis(x, y, z, rot_deg)
        return self.add("IFCLOCALPLACEMENT", "%s,%s" % (parent or "$", ax))


def _rooms(model):
    out = []
    for tk in sorted((model.get("floors") or {}).keys()):
        for r in ((model["floors"][tk] or {}).get("rooms") or []):
            out.append((tk, r))
    return out


def _levels(model):
    return sorted((model.get("levels") or []),
                  key=lambda l: (l.get("index") is None, l.get("index")))


def build_exchange(project, options=None):
    """يبني نموذج التبادل الوسيط من النموذج القانوني. لا يمسّ النموذج."""
    o = options or {}
    model = project["model"]
    bid = project.get("building_id") or "bld_0"
    mh = project.get("model_hash")
    include_spaces = o.get("include_spaces", True)
    scope = str(o.get("scope") or "ALL").upper()
    if scope not in SPEC["export_scope_options"]:
        return {"valid": False, "issues": [issue("BIM_EXPORT_VALIDATION_FAILED",
                "ERROR", None, "unknown export scope: %s" % o.get("scope"))],
                "exchange": None}
    wanted_levels = o.get("levels")
    wall_h = _num(model.get("wall_h")) or 3.0
    wall_t = _num(model.get("wall_t"))
    floor_h = _num(model.get("floor_height")) or (wall_h + 0.2)

    site = (model.get("site") or {})
    levels = _levels(model)
    if wanted_levels is not None:
        levels = [l for l in levels if l.get("index") in wanted_levels]

    ex = {
        "schema_version": SPEC["writable_schemas"][0],
        "project": {"canonical_id": "project", "name": (model.get("meta") or {}).get("name")
                    or "Project"},
        "site": {"canonical_id": "site", "name": "Site",
                 "w": _num(site.get("w")), "d": _num(site.get("d"))},
        "building": {"canonical_id": bid, "name": (model.get("meta") or {}).get("name")
                     or bid},
        "levels": [], "spaces": [], "walls": [], "slabs": [], "doors": [],
        "windows": [], "stairs": [],
        "unsupported": [], "losses": [],
    }

    by_template = {}
    for tk, r in _rooms(model):
        by_template.setdefault(tk, []).append(r)

    for lv in levels:
        idx = lv.get("index")
        elev = _q((_num(lv.get("elevation")) if lv.get("elevation") is not None
                   else float(idx or 0) * floor_h))
        ex["levels"].append({"canonical_id": "%s.flr_%s" % (bid, idx),
                             "name": lv.get("name") or ("Level %s" % idx),
                             "index": idx, "elevation": elev,
                             "template": lv.get("template")})
        rooms = sorted(by_template.get(lv.get("template")) or [],
                       key=lambda r: str(r.get("id")))
        for r in rooms:
            rect = r.get("rect") or [0, 0, 0, 0]
            x, z, w, d = [_q(_num(v) or 0.0) for v in rect[:4]]
            rh = _num(r.get("height")) or wall_h
            # القالب قد يتكرّر عبر الأدوار، فمعرّف التبادل يحمل رقم الدور كي
            # يبقى فريداً؛ ومعرّف التأليف يبقى منفصلاً كما يعرفه محرّك التأليف
            sid = "%s.flr_%s.%s.%s" % (bid, idx, lv.get("template"), r.get("id"))
            aid = "%s.%s" % (lv.get("template"), r.get("id"))
            if include_spaces and scope in ("ALL", "SPACES_ONLY", "LEVELS"):
                ex["spaces"].append({
                    "canonical_id": sid, "authoring_id": aid,
                    "name": r.get("name") or str(r.get("id")),
                    "number": str(r.get("id")), "level_index": idx,
                    "elevation": elev, "height": _q(rh),
                    "footprint": [x, z, w, d],
                    "area_m2": _q(w * d)})
            if scope == "SPACES_ONLY":
                continue
            # جدران الفراغ: أربعة محاور حقيقية من مستطيله
            edges = [("N", x, z, x + w, z), ("S", x, z + d, x + w, z + d),
                     ("W", x, z, x, z + d), ("E", x + w, z, x + w, z + d)]
            for edge, x1, z1, x2, z2 in edges:
                wid = "%s.flr_%s.%s.%s.wall_%s" % (bid, idx, lv.get("template"),
                                                  r.get("id"), edge)
                ex["walls"].append({
                    "canonical_id": wid, "level_index": idx, "elevation": elev,
                    "start": [_q(x1), _q(z1)], "end": [_q(x2), _q(z2)],
                    "height": _q(rh),
                    "thickness": _q(wall_t) if wall_t is not None else None,
                    "thickness_known": wall_t is not None,
                    "space_id": sid, "edge": edge})
            for j, op in enumerate(r.get("doors") or []):
                rec = _opening_record(bid, lv, r, op, j, "door", x, z, w, d, elev, rh)
                if rec:
                    ex["doors"].append(rec)
            for j, op in enumerate(r.get("windows") or []):
                rec = _opening_record(bid, lv, r, op, j, "window", x, z, w, d, elev, rh)
                if rec:
                    ex["windows"].append(rec)
            for j, ob in enumerate(r.get("objects") or []):
                kind = str(ob.get("kind") or "")
                oid = "%s.flr_%s.%s.obj_%d" % (bid, idx, lv.get("template"), j)
                if kind.lower() in ("stairs", "stair"):
                    ex["stairs"].append({
                        "canonical_id": oid, "level_index": idx, "elevation": elev,
                        "x": _q(x + (_num(ob.get("x")) or 0.0)),
                        "z": _q(z + (_num(ob.get("z")) or 0.0)),
                        "w": _q(_num(ob.get("w")) or 1.2),
                        "d": _q(_num(ob.get("d")) or 2.4),
                        "space_id": sid})
                else:
                    ex["unsupported"].append({
                        "canonical_id": oid, "kind": kind, "space_id": sid,
                        "reason": "no declared IFC mapping for this object kind"})
        if scope not in ("SPACES_ONLY", "ENVELOPE_ONLY"):
            xs, zs = [], []
            for r in rooms:
                rect = r.get("rect") or [0, 0, 0, 0]
                xs += [_num(rect[0]) or 0.0, (_num(rect[0]) or 0.0) + (_num(rect[2]) or 0.0)]
                zs += [_num(rect[1]) or 0.0, (_num(rect[1]) or 0.0) + (_num(rect[3]) or 0.0)]
            if xs:
                ex["slabs"].append({
                    "canonical_id": "%s.flr_%s.slab" % (bid, idx),
                    "level_index": idx, "elevation": elev,
                    "outline": [_q(min(xs)), _q(min(zs)), _q(max(xs) - min(xs)),
                                _q(max(zs) - min(zs))],
                    "thickness": None, "thickness_known": False,
                    "predefined_type": "FLOOR"})

    for u in ex["unsupported"]:
        ex["losses"].append({"entity_id": u["canonical_id"],
                             "type": "UNSUPPORTED_ENTITY", "severity": "WARNING",
                             "message": u["reason"]})
    if wall_t is None and ex["walls"]:
        ex["losses"].append({"entity_id": None, "type": "PROPERTY_LOSS",
                             "severity": "WARNING",
                             "message": "wall thickness is not stated in the model and is "
                                        "not invented on export"})
    for s in ex["slabs"]:
        ex["losses"].append({"entity_id": s["canonical_id"], "type": "PROPERTY_LOSS",
                             "severity": "INFO",
                             "message": "slab thickness is not stated in the model"})
    ex["config"] = {"scope": scope, "include_spaces": bool(include_spaces),
                    "levels": sorted(wanted_levels) if wanted_levels else None,
                    "include_external_metadata":
                        bool(o.get("include_external_metadata", True)),
                    "coordinate_policy": SPEC["coordinate_policy"],
                    "schema": ex["schema_version"]}
    ex["config_hash"] = _sha16(ex["config"])
    ex["model_hash"] = mh
    ex["revision_id"] = project.get("current_revision")
    ex["building_id"] = bid
    return {"valid": True, "issues": [], "exchange": ex}


def _opening_record(bid, lv, r, op, j, kind, x, z, w, d, elev, rh):
    edge = str(op.get("edge") or "N").upper()[:1]
    offset = _num(op.get("offset"))
    width = _num(op.get("width"))
    height = _num(op.get("height"))
    if offset is None or width is None:
        return None
    if edge == "N":
        px, pz, ang = x + offset, z, 0.0
    elif edge == "S":
        px, pz, ang = x + offset, z + d, 0.0
    elif edge == "W":
        px, pz, ang = x, z + offset, 90.0
    else:
        px, pz, ang = x + w, z + offset, 90.0
    idx = lv.get("index")
    host = "%s.flr_%s.%s.%s.wall_%s" % (bid, idx, lv.get("template"), r.get("id"), edge)
    return {"canonical_id": "%s.flr_%s.%s.%s.%s_%d" % (bid, idx, lv.get("template"),
                                                       r.get("id"), kind, j),
            "level_index": lv.get("index"), "elevation": elev,
            "x": _q(px), "z": _q(pz), "rotation_deg": _q(ang),
            "width": _q(width), "height": _q(height) if height is not None else None,
            "height_known": height is not None,
            "sill": _q(_num(op.get("sill"))) if _num(op.get("sill")) is not None else None,
            "host_wall_id": host, "edge": edge, "offset": _q(offset),
            "space_id": "%s.flr_%s.%s.%s" % (bid, idx, lv.get("template"),
                                             r.get("id")),
            "authoring_space_id": "%s.%s" % (lv.get("template"), r.get("id"))}


def serialise_ifc(exchange, generated_at=None):
    """يكتب ملفّ IFC4 حقيقياً بصيغة ISO-10303-21. الجسم حتمي بالكامل."""
    f = StepFile()
    mh = exchange.get("model_hash")
    sch = exchange["schema_version"]
    guid = lambda cid: ifc_guid({"m": mh, "id": cid, "s": sch})

    person = f.add("IFCPERSON", "$,$,'acs',$,$,$,$,$")
    org = f.add("IFCORGANIZATION", "$,'AI Construction Studio',$,$,$")
    pao = f.add("IFCPERSONANDORGANIZATION", "%s,%s,$" % (person, org))
    app = f.add("IFCAPPLICATION", "%s,'%s','ACS BIM Exporter','ACS-BIM'"
                % (org, SPEC["version"]))
    # الطابع الزمني في المالك ثابت عمداً: الجسم يجب أن يبقى متطابقاً بايتاً ببايت
    owner = f.add("IFCOWNERHISTORY", "%s,%s,$,.ADDED.,$,$,$,0" % (pao, app))

    dim = f.add("IFCDIMENSIONALEXPONENTS", "0,0,0,0,0,0,0")
    u_len = f.add("IFCSIUNIT", "*,.LENGTHUNIT.,$,.METRE.")
    u_area = f.add("IFCSIUNIT", "*,.AREAUNIT.,$,.SQUARE_METRE.")
    u_vol = f.add("IFCSIUNIT", "*,.VOLUMEUNIT.,$,.CUBIC_METRE.")
    u_rad = f.add("IFCSIUNIT", "*,.PLANEANGLEUNIT.,$,.RADIAN.")
    deg_ratio = f.add("IFCMEASUREWITHUNIT", "IFCPLANEANGLEMEASURE(%s),%s"
                      % (step_real(math.pi / 180.0), u_rad))
    u_deg = f.add("IFCCONVERSIONBASEDUNIT", "%s,.PLANEANGLEUNIT.,'DEGREE',%s"
                  % (dim, deg_ratio))
    units = f.add("IFCUNITASSIGNMENT", "(%s,%s,%s,%s)"
                  % (u_len, u_area, u_vol, u_deg))

    world = f.axis(0.0, 0.0, 0.0)
    ctx = f.add("IFCGEOMETRICREPRESENTATIONCONTEXT",
                "$,'Model',3,1.E-05,%s,$" % world)

    proj = f.add("IFCPROJECT", "'%s',%s,%s,$,$,$,$,(%s),%s"
                 % (guid("project"), owner, step_string(exchange["project"]["name"]),
                    ctx, units))
    site_pl = f.placement(None, 0.0, 0.0, 0.0)
    site = f.add("IFCSITE", "'%s',%s,%s,$,$,%s,$,$,.ELEMENT.,$,$,$,$,$"
                 % (guid("site"), owner, step_string(exchange["site"]["name"]), site_pl))
    bldg_pl = f.placement(site_pl, 0.0, 0.0, 0.0)
    bldg = f.add("IFCBUILDING", "'%s',%s,%s,$,$,%s,$,$,.ELEMENT.,$,$,$"
                 % (guid(exchange["building"]["canonical_id"]), owner,
                    step_string(exchange["building"]["name"]), bldg_pl))

    f.add("IFCRELAGGREGATES", "'%s',%s,$,$,%s,(%s)"
          % (guid("agg:project"), owner, proj, site))
    f.add("IFCRELAGGREGATES", "'%s',%s,$,$,%s,(%s)"
          % (guid("agg:site"), owner, site, bldg))

    storeys, storey_pl, contained = [], {}, {}
    for lv in exchange["levels"]:
        pl = f.placement(bldg_pl, 0.0, 0.0, lv["elevation"])
        st = f.add("IFCBUILDINGSTOREY", "'%s',%s,%s,$,$,%s,$,$,.ELEMENT.,%s"
                   % (guid(lv["canonical_id"]), owner, step_string(lv["name"]), pl,
                      step_real(lv["elevation"])))
        storeys.append(st)
        storey_pl[lv["index"]] = pl
        contained[lv["index"]] = []
    if storeys:
        f.add("IFCRELAGGREGATES", "'%s',%s,$,$,%s,(%s)"
              % (guid("agg:building"), owner, bldg, ",".join(storeys)))

    def local(idx):
        return storey_pl.get(idx) or bldg_pl

    space_refs = {}
    for sp in exchange["spaces"]:
        x, z, w, d = sp["footprint"]
        pl = f.placement(local(sp["level_index"]), x, z, 0.0)
        prof = f.add("IFCRECTANGLEPROFILEDEF", ".AREA.,$,%s,%s,%s"
                     % (f.axis(_q(w / 2.0), _q(d / 2.0), 0.0), step_real(w),
                        step_real(d)))
        solid = f.add("IFCEXTRUDEDAREASOLID", "%s,%s,%s,%s"
                      % (prof, f.axis(0.0, 0.0, 0.0), f.direction(0.0, 0.0, 1.0),
                         step_real(sp["height"])))
        shp = f.add("IFCSHAPEREPRESENTATION", "%s,'Body','SweptSolid',(%s)" % (ctx, solid))
        pds = f.add("IFCPRODUCTDEFINITIONSHAPE", "$,$,(%s)" % shp)
        ref = f.add("IFCSPACE", "'%s',%s,%s,$,$,%s,%s,%s,.ELEMENT.,.INTERNAL.,%s"
                    % (guid(sp["canonical_id"]), owner, step_string(sp["name"]), pl, pds,
                       step_string(sp["number"]), step_real(sp["elevation"])))
        space_refs[sp["canonical_id"]] = ref
        contained.setdefault(sp["level_index"], []).append(ref)

    wall_refs = {}
    for wl in exchange["walls"]:
        x1, z1 = wl["start"]
        x2, z2 = wl["end"]
        length = _q(math.sqrt((x2 - x1) ** 2 + (z2 - z1) ** 2))
        ang = _q(math.degrees(math.atan2(z2 - z1, x2 - x1)))
        pl = f.placement(local(wl["level_index"]), x1, z1, 0.0, ang)
        thick = wl["thickness"] if wl["thickness_known"] else 0.2
        prof = f.add("IFCRECTANGLEPROFILEDEF", ".AREA.,$,%s,%s,%s"
                     % (f.axis(_q(length / 2.0), 0.0, 0.0), step_real(length),
                        step_real(thick)))
        solid = f.add("IFCEXTRUDEDAREASOLID", "%s,%s,%s,%s"
                      % (prof, f.axis(0.0, 0.0, 0.0), f.direction(0.0, 0.0, 1.0),
                         step_real(wl["height"])))
        ax = f.add("IFCPOLYLINE", "(%s,%s)" % (f.point(0.0, 0.0), f.point(length, 0.0)))
        axr = f.add("IFCSHAPEREPRESENTATION", "%s,'Axis','Curve2D',(%s)" % (ctx, ax))
        bod = f.add("IFCSHAPEREPRESENTATION", "%s,'Body','SweptSolid',(%s)" % (ctx, solid))
        pds = f.add("IFCPRODUCTDEFINITIONSHAPE", "$,$,(%s,%s)" % (axr, bod))
        ref = f.add("IFCWALLSTANDARDCASE", "'%s',%s,%s,$,$,%s,%s,$,.STANDARD."
                    % (guid(wl["canonical_id"]), owner,
                       step_string(wl["canonical_id"]), pl, pds))
        wall_refs[wl["canonical_id"]] = ref
        contained.setdefault(wl["level_index"], []).append(ref)

    # حيث لا يذكر النموذج سماكة، تُكتب قيمة نائبة معلَنة ومعها خاصّية تقول
    # صراحةً إنّها غير مذكورة — فالقارئ يستعيد المجهول ولا يتبنّى النائبة
    unstated = [w for w in exchange["walls"] if not w["thickness_known"]]
    if unstated:
        pv = f.add("IFCPROPERTYSINGLEVALUE",
                   "'ThicknessIsModelStated',$,IFCBOOLEAN(.F.),$")
        pset = f.add("IFCPROPERTYSET", "'%s',%s,%s,$,(%s)"
                     % (guid("pset:unstated_thickness"), owner,
                        step_string(SPEC["unstated_property_set"]), pv))
        refs = [wall_refs[w["canonical_id"]] for w in unstated
                if w["canonical_id"] in wall_refs]
        if refs:
            f.add("IFCRELDEFINESBYPROPERTIES", "'%s',%s,$,$,(%s),%s"
                  % (guid("rel:unstated_thickness"), owner, ",".join(refs), pset))

    for sl in exchange["slabs"]:
        x, z, w, d = sl["outline"]
        pl = f.placement(local(sl["level_index"]), x, z, 0.0)
        prof = f.add("IFCRECTANGLEPROFILEDEF", ".AREA.,$,%s,%s,%s"
                     % (f.axis(_q(w / 2.0), _q(d / 2.0), 0.0), step_real(w),
                        step_real(d)))
        th = sl["thickness"] if sl["thickness_known"] else 0.2
        solid = f.add("IFCEXTRUDEDAREASOLID", "%s,%s,%s,%s"
                      % (prof, f.axis(0.0, 0.0, _q(-th)), f.direction(0.0, 0.0, 1.0),
                         step_real(th)))
        shp = f.add("IFCSHAPEREPRESENTATION", "%s,'Body','SweptSolid',(%s)" % (ctx, solid))
        pds = f.add("IFCPRODUCTDEFINITIONSHAPE", "$,$,(%s)" % shp)
        ref = f.add("IFCSLAB", "'%s',%s,%s,$,$,%s,%s,$,.%s."
                    % (guid(sl["canonical_id"]), owner, step_string(sl["canonical_id"]),
                       pl, pds, sl["predefined_type"]))
        contained.setdefault(sl["level_index"], []).append(ref)

    for kind, key, ifctype in (("door", "doors", "IFCDOOR"),
                               ("window", "windows", "IFCWINDOW")):
        for op in exchange[key]:
            host = wall_refs.get(op["host_wall_id"])
            base = _q(op["sill"]) if (kind == "window" and op["sill"] is not None) else 0.0
            pl = f.placement(local(op["level_index"]), op["x"], op["z"], base,
                             op["rotation_deg"])
            oh = op["height"] if op["height_known"] else 2.1
            prof = f.add("IFCRECTANGLEPROFILEDEF", ".AREA.,$,%s,%s,%s"
                         % (f.axis(0.0, 0.0, 0.0), step_real(op["width"]),
                            step_real(0.3)))
            solid = f.add("IFCEXTRUDEDAREASOLID", "%s,%s,%s,%s"
                          % (prof, f.axis(0.0, 0.0, 0.0), f.direction(0.0, 0.0, 1.0),
                             step_real(oh)))
            shp = f.add("IFCSHAPEREPRESENTATION", "%s,'Body','SweptSolid',(%s)"
                        % (ctx, solid))
            pds = f.add("IFCPRODUCTDEFINITIONSHAPE", "$,$,(%s)" % shp)
            if host is not None:
                opl = f.placement(local(op["level_index"]), op["x"], op["z"], base,
                                  op["rotation_deg"])
                ovoid = f.add("IFCOPENINGELEMENT",
                              "'%s',%s,%s,$,$,%s,%s,$,.OPENING."
                              % (guid(op["canonical_id"] + ":void"), owner,
                                 step_string(op["canonical_id"] + ":void"), opl, pds))
                f.add("IFCRELVOIDSELEMENT", "'%s',%s,$,$,%s,%s"
                      % (guid(op["canonical_id"] + ":voids"), owner, host, ovoid))
            ref = f.add(ifctype, "'%s',%s,%s,$,$,%s,%s,$,%s,%s,$,$"
                        % (guid(op["canonical_id"]), owner,
                           step_string(op["canonical_id"]), pl, pds,
                           step_real(oh), step_real(op["width"])))
            if host is not None:
                f.add("IFCRELFILLSELEMENT", "'%s',%s,$,$,%s,%s"
                      % (guid(op["canonical_id"] + ":fills"), owner, ovoid, ref))
            contained.setdefault(op["level_index"], []).append(ref)

    for st in exchange["stairs"]:
        pl = f.placement(local(st["level_index"]), st["x"], st["z"], 0.0)
        prof = f.add("IFCRECTANGLEPROFILEDEF", ".AREA.,$,%s,%s,%s"
                     % (f.axis(0.0, 0.0, 0.0), step_real(st["w"]), step_real(st["d"])))
        solid = f.add("IFCEXTRUDEDAREASOLID", "%s,%s,%s,%s"
                      % (prof, f.axis(0.0, 0.0, 0.0), f.direction(0.0, 0.0, 1.0),
                         step_real(3.0)))
        shp = f.add("IFCSHAPEREPRESENTATION", "%s,'Body','SweptSolid',(%s)" % (ctx, solid))
        pds = f.add("IFCPRODUCTDEFINITIONSHAPE", "$,$,(%s)" % shp)
        ref = f.add("IFCSTAIR", "'%s',%s,%s,$,$,%s,%s,$,.STRAIGHT_RUN_STAIR."
                    % (guid(st["canonical_id"]), owner,
                       step_string(st["canonical_id"]), pl, pds))
        contained.setdefault(st["level_index"], []).append(ref)

    for lv in exchange["levels"]:
        items = contained.get(lv["index"]) or []
        if not items:
            continue
        f.add("IFCRELCONTAINEDINSPATIALSTRUCTURE", "'%s',%s,$,$,(%s),%s"
              % (guid("contain:%s" % lv["canonical_id"]), owner, ",".join(items),
                 storeys[exchange["levels"].index(lv)]))

    body = "\n".join(f.lines)
    stamp = generated_at or "1970-01-01T00:00:00"
    header = ("ISO-10303-21;\n"
              "HEADER;\n"
              "FILE_DESCRIPTION((%s),'2;1');\n"
              "FILE_NAME(%s,'%s',(%s),(%s),'%s','%s','');\n"
              "FILE_SCHEMA(('%s'));\n"
              "ENDSEC;\n"
              % (step_string("ViewDefinition [CoordinationView]"),
                 step_string((exchange["project"]["name"] or "project") + ".ifc"),
                 stamp, step_string("ACS"), step_string("AI Construction Studio"),
                 PARSER_VERSION, COMPILER, sch))
    text = header + "DATA;\n" + body + "\nENDSEC;\nEND-ISO-10303-21;\n"
    return {"text": text, "entity_count": f.n, "body": body,
            "body_hash": _sha256_text(body)}


def export_ifc(project, options=None, generated_at=None):
    """تصدير كامل: بناء، تحقّق، تسلسل، ثم بيان. النموذج لا يتغيّر."""
    before_hash = project.get("model_hash")
    before_rev = project.get("current_revision")
    built = build_exchange(project, options)
    if not built["valid"]:
        return {"valid": False, "issues": built["issues"], "file": None,
                "manifest": None}
    ex = built["exchange"]
    issues = validate_exchange(ex)
    if any(i["blocking"] for i in issues):
        return {"valid": False, "issues": issues, "file": None, "manifest": None}
    ser = serialise_ifc(ex, generated_at)
    manifest = {
        "export_id": "bimexp_" + _sha16({"m": ex["model_hash"], "c": ex["config_hash"],
                                         "s": ex["schema_version"]}),
        "model_hash": ex["model_hash"], "revision_id": ex["revision_id"],
        "schema": ex["schema_version"],
        "object_count": (len(ex["walls"]) + len(ex["slabs"]) + len(ex["doors"])
                         + len(ex["windows"]) + len(ex["stairs"]) + len(ex["spaces"])),
        "level_count": len(ex["levels"]), "space_count": len(ex["spaces"]),
        "wall_count": len(ex["walls"]), "door_count": len(ex["doors"]),
        "window_count": len(ex["windows"]), "slab_count": len(ex["slabs"]),
        "stair_count": len(ex["stairs"]),
        "unsupported_count": len(ex["unsupported"]),
        "losses": ex["losses"], "warnings": [i for i in issues if not i["blocking"]],
        "file_hash": _sha256_text(ser["text"]), "body_hash": ser["body_hash"],
        "generator_version": COMPILER, "config_hash": ex["config_hash"],
        "generated_at": generated_at,
        "entity_count": ser["entity_count"],
        "deterministic_fields": list(SPEC["export_deterministic_fields"]),
        "non_deterministic_fields": list(SPEC["export_non_deterministic_fields"]),
        "writes_to_model": False,
    }
    if project.get("model_hash") != before_hash \
            or project.get("current_revision") != before_rev:
        raise RuntimeError("the export path changed the project")
    return {"valid": True, "issues": issues, "file": ser["text"],
            "exchange": ex, "manifest": manifest, "state": "SERIALISED"}


def validate_exchange(ex):
    """تحقّق ما قبل التسلسل: معرّفات ومحتويات وحدود."""
    issues = []
    seen = {}
    groups = ("levels", "spaces", "walls", "slabs", "doors", "windows", "stairs")
    total = 0
    for g in groups:
        for it in ex.get(g) or []:
            total += 1
            cid = it.get("canonical_id")
            if not is_safe_id(str(cid)):
                issues.append(issue("BIM_INVALID_IDENTIFIER", "ERROR", cid,
                                    "canonical identifier is not a plausible identifier"))
            if cid in seen:
                issues.append(issue("BIM_DUPLICATE_ID", "ERROR", cid,
                                    "the same canonical identifier appears twice"))
            seen[cid] = True
            for k in ("name", "number"):
                if k in it and is_unsafe(it.get(k)):
                    issues.append(issue("BIM_UNSAFE_STRING", "ERROR", cid,
                                        "an exported name carries an unsafe value"))
    if total > int(LIMITS["max_objects"]):
        issues.append(issue("BIM_RESOURCE_LIMIT_EXCEEDED", "ERROR", None,
                            "object count exceeds the declared maximum"))
    if len(ex.get("levels") or []) > int(LIMITS["max_levels"]):
        issues.append(issue("BIM_RESOURCE_LIMIT_EXCEEDED", "ERROR", None,
                            "level count exceeds the declared maximum"))
    wall_ids = set(w["canonical_id"] for w in ex.get("walls") or [])
    for key in ("doors", "windows"):
        for op in ex.get(key) or []:
            if op.get("host_wall_id") and op["host_wall_id"] not in wall_ids:
                issues.append(issue("BIM_HOST_UNRESOLVED", "WARNING",
                                    op["canonical_id"],
                                    "the host wall is not part of this export scope"))
    for g in groups:
        for it in ex.get(g) or []:
            for k, v in sorted(it.items()):
                if isinstance(v, float) and _num(v) is None:
                    issues.append(issue("BIM_INVALID_NUMBER", "ERROR",
                                        it.get("canonical_id"),
                                        "a non-finite number reached the exporter"))
    return issues


# ================================================================ التحليل ===
class StepParseError(Exception):
    pass


def _decode_step_string(s):
    """يفكّ ترميز نصّ STEP: الفاصلة المزدوجة والشرطة والمقاطع \\X2\\ العربية."""
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "'" and i + 1 < n and s[i + 1] == "'":
            out.append("'")
            i += 2
            continue
        if c == "\\" and i + 1 < n:
            nxt = s[i + 1]
            if nxt == "\\":
                out.append("\\")
                i += 2
                continue
            if nxt in ("X", "x") and i + 2 < n and s[i + 2] == "2":
                j = s.find("\\X0\\", i)
                if j < 0:
                    j = s.find("\\x0\\", i)
                if j < 0:
                    raise StepParseError("unterminated \\X2\\ sequence")
                hexs = s[i + 4:j]
                if len(hexs) % 4 != 0:
                    raise StepParseError("malformed \\X2\\ payload")
                units = [int(hexs[k:k + 4], 16) for k in range(0, len(hexs), 4)]
                k = 0
                while k < len(units):
                    u = units[k]
                    if 0xD800 <= u <= 0xDBFF and k + 1 < len(units):
                        lo = units[k + 1]
                        out.append(chr(0x10000 + ((u - 0xD800) << 10) + (lo - 0xDC00)))
                        k += 2
                    else:
                        out.append(chr(u))
                        k += 1
                i = j + 4
                continue
            if nxt in ("S", "s") and i + 3 < n and s[i + 2] == "\\":
                out.append(chr(ord(s[i + 3]) + 128))
                i += 4
                continue
        out.append(c)
        i += 1
    return "".join(out)


class _Ref(object):
    __slots__ = ("n",)

    def __init__(self, n):
        self.n = n

    def __repr__(self):
        return "#%d" % self.n


class _Typed(object):
    __slots__ = ("name", "value")

    def __init__(self, name, value):
        self.name = name
        self.value = value


def _parse_args(src, pos, depth, issues):
    """يحلّل قائمة وسائط STEP بدءاً من قوس مفتوح. عودية محدودة العمق."""
    if depth > int(LIMITS["max_placement_depth"]) + 8:
        raise StepParseError("argument nesting exceeds the declared depth")
    out = []
    n = len(src)
    i = pos
    if src[i] != "(":
        raise StepParseError("expected (")
    i += 1
    while i < n:
        while i < n and src[i] in " \t\r\n":
            i += 1
        if i >= n:
            raise StepParseError("unterminated argument list")
        c = src[i]
        if c == ")":
            return out, i + 1
        if c == ",":
            i += 1
            continue
        if c == "(":
            sub, i = _parse_args(src, i, depth + 1, issues)
            if len(sub) > int(LIMITS["max_list_length"]):
                raise StepParseError("list length exceeds the declared maximum")
            out.append(sub)
            continue
        if c == "'":
            j = i + 1
            while j < n:
                if src[j] == "'":
                    if j + 1 < n and src[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            if j >= n:
                raise StepParseError("unterminated string")
            raw = src[i + 1:j]
            if len(raw) > int(LIMITS["max_string_length"]):
                raise StepParseError("string exceeds the declared maximum length")
            out.append(_decode_step_string(raw))
            i = j + 1
            continue
        if c == "#":
            j = i + 1
            while j < n and src[j].isdigit():
                j += 1
            if j == i + 1:
                raise StepParseError("malformed entity reference")
            out.append(_Ref(int(src[i + 1:j])))
            i = j
            continue
        if c == ".":
            j = src.find(".", i + 1)
            if j < 0:
                raise StepParseError("unterminated enumeration")
            out.append({"enum": src[i + 1:j]})
            i = j + 1
            continue
        if c == "$":
            out.append(None)
            i += 1
            continue
        if c == "*":
            out.append({"derived": True})
            i += 1
            continue
        j = i
        while j < n and (src[j].isalnum() or src[j] in "_+-."):
            j += 1
        tok = src[i:j]
        if j < n and src[j] == "(" and tok and tok[0].isalpha():
            sub, j2 = _parse_args(src, j, depth + 1, issues)
            out.append(_Typed(tok.upper(), sub[0] if len(sub) == 1 else sub))
            i = j2
            continue
        if not tok:
            raise StepParseError("unexpected character %r" % c)
        v = _num(tok)
        if v is None:
            if tok.upper() in ("T", "F", "U"):
                out.append({"enum": tok.upper()})
            else:
                raise StepParseError("invalid numeric literal %r" % tok)
        else:
            out.append(v)
        i = j
    raise StepParseError("unterminated argument list")


def parse_step(text, file_name=None):
    """يحلّل ملفّ STEP فعلياً. كل خلل يُعاد مُصنَّفاً، ولا شيء يُنفَّذ."""
    issues = []
    if not isinstance(text, str) or not text.strip():
        return {"valid": False, "issues": [issue("BIM_INVALID_FILE", "ERROR", None,
                "the file is empty")], "step": None}
    if len(text.encode("utf-8")) > int(LIMITS["max_file_bytes"]):
        return {"valid": False, "issues": [issue("BIM_RESOURCE_LIMIT_EXCEEDED", "ERROR",
                None, "the file exceeds the declared maximum size")], "step": None}
    if not text.lstrip().startswith("ISO-10303-21"):
        return {"valid": False, "issues": [issue("BIM_INVALID_FILE", "ERROR", None,
                "the file does not start with an ISO-10303-21 header")], "step": None}
    if "END-ISO-10303-21" not in text:
        return {"valid": False, "issues": [issue("BIM_INVALID_FILE", "ERROR", None,
                "the file is not terminated")], "step": None}
    if "DATA;" not in text or "HEADER;" not in text:
        return {"valid": False, "issues": [issue("BIM_INVALID_FILE", "ERROR", None,
                "the file has no HEADER or DATA section")], "step": None}

    head_src = text[text.index("HEADER;") + 7:text.index("DATA;")]
    schema = None
    try:
        k = head_src.upper().index("FILE_SCHEMA")
        args, _ = _parse_args(head_src, head_src.index("(", k), 0, issues)
        flat = args[0] if args and isinstance(args[0], list) else args
        if flat and isinstance(flat[0], str):
            schema = flat[0].strip().upper()
    except (ValueError, StepParseError, IndexError):
        schema = None
    if schema is None:
        return {"valid": False, "issues": [issue("BIM_UNKNOWN_SCHEMA", "ERROR", None,
                "the file declares no schema")], "step": None}
    schema = schema.split()[0]
    if schema not in SPEC["readable_schemas"]:
        return {"valid": False, "issues": [issue("BIM_UNKNOWN_SCHEMA", "ERROR", None,
                "unsupported schema %s; it is refused, never reinterpreted" % schema)],
                "step": None}

    body = text[text.index("DATA;") + 5:]
    end = body.find("ENDSEC;")
    if end >= 0:
        body = body[:end]
    entities = {}
    order = []
    i, n = 0, len(body)
    count = 0
    while i < n:
        while i < n and body[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        if body[i] != "#":
            j = body.find(";", i)
            if j < 0:
                break
            i = j + 1
            continue
        j = i + 1
        while j < n and body[j].isdigit():
            j += 1
        if j == i + 1:
            issues.append(issue("BIM_INVALID_FILE", "ERROR", None,
                                "malformed entity number"))
            return {"valid": False, "issues": issues, "step": None}
        eid = int(body[i + 1:j])
        while j < n and body[j] in " \t":
            j += 1
        if j >= n or body[j] != "=":
            issues.append(issue("BIM_INVALID_FILE", "ERROR", "#%d" % eid,
                                "entity is missing its assignment"))
            return {"valid": False, "issues": issues, "step": None}
        j += 1
        while j < n and body[j] in " \t\r\n":
            j += 1
        k = j
        while k < n and (body[k].isalnum() or body[k] == "_"):
            k += 1
        tname = body[j:k].upper()
        while k < n and body[k] in " \t":
            k += 1
        if k >= n or body[k] != "(":
            issues.append(issue("BIM_INVALID_FILE", "ERROR", "#%d" % eid,
                                "entity is missing its argument list"))
            return {"valid": False, "issues": issues, "step": None}
        try:
            args, k = _parse_args(body, k, 0, issues)
        except StepParseError as e:
            issues.append(issue("BIM_INVALID_FILE", "ERROR", "#%d" % eid, str(e)))
            return {"valid": False, "issues": issues, "step": None}
        while k < n and body[k] in " \t\r\n":
            k += 1
        if k < n and body[k] == ";":
            k += 1
        if eid in entities:
            issues.append(issue("BIM_DUPLICATE_ID", "ERROR", "#%d" % eid,
                                "the same entity number is assigned twice"))
            return {"valid": False, "issues": issues, "step": None}
        entities[eid] = {"id": eid, "type": tname, "args": args}
        order.append(eid)
        count += 1
        if count > int(LIMITS["max_entity_count"]):
            issues.append(issue("BIM_RESOURCE_LIMIT_EXCEEDED", "ERROR", None,
                                "entity count exceeds the declared maximum"))
            return {"valid": False, "issues": issues, "step": None}
        i = k

    if not entities:
        return {"valid": False, "issues": [issue("BIM_INVALID_FILE", "ERROR", None,
                "the DATA section holds no entity")], "step": None}

    # المراجع تُتحقَّق ولا تُصدَّق
    def walk_refs(v, acc):
        if isinstance(v, _Ref):
            acc.append(v.n)
        elif isinstance(v, list):
            for x in v:
                walk_refs(x, acc)
        elif isinstance(v, _Typed):
            walk_refs(v.value, acc)
    dangling = 0
    for eid in order:
        acc = []
        walk_refs(entities[eid]["args"], acc)
        for r in acc:
            if r not in entities:
                dangling += 1
                if dangling <= 8:
                    issues.append(issue("BIM_INVALID_REFERENCE", "ERROR",
                                        "#%d" % eid,
                                        "reference #%d does not exist" % r))
    if dangling:
        return {"valid": False, "issues": issues, "step": None}

    return {"valid": True, "issues": issues, "step": {
        "schema": schema, "entities": entities, "order": order,
        "entity_count": len(entities),
        "file_hash": _sha256_text(text),
        "file_name": file_name if (isinstance(file_name, str)
                                   and not is_unsafe(file_name)) else None,
        "parser_version": PARSER_VERSION}}


# ======================================================= نموذج التجهيز =====
def _arg(e, i):
    a = e.get("args") or []
    return a[i] if i < len(a) else None


def _enum(v):
    return v.get("enum") if isinstance(v, dict) and "enum" in v else None


def _deref(step, v):
    if isinstance(v, _Ref):
        return step["entities"].get(v.n)
    return None


def resolve_units(step):
    """يستخرج الوحدات المُعلَنة. غياب الوحدة خلل مُصنَّف لا افتراض صامت."""
    issues = []
    length = None
    angle = None
    ents = step["entities"]
    for e in ents.values():
        if e["type"] != "IFCUNITASSIGNMENT":
            continue
        lst = _arg(e, 0) or []
        for r in lst:
            u = _deref(step, r)
            if not u:
                continue
            if u["type"] == "IFCSIUNIT":
                kind = _enum(_arg(u, 1))
                prefix = _enum(_arg(u, 2))
                name = _enum(_arg(u, 3))
                if kind == "LENGTHUNIT" and name == "METRE":
                    factor = {"MILLI": 0.001, "CENTI": 0.01, "DECI": 0.1,
                              "KILO": 1000.0, None: 1.0}.get(prefix)
                    if factor is None:
                        issues.append(issue("BIM_UNIT_INVALID", "ERROR", "#%d" % u["id"],
                                            "unsupported length prefix %s" % prefix))
                    else:
                        length = ("METRE" if prefix is None
                                  else prefix + "_METRE", factor)
                elif kind == "PLANEANGLEUNIT" and name == "RADIAN":
                    angle = ("RADIAN", 1.0)
            elif u["type"] == "IFCCONVERSIONBASEDUNIT":
                kind = _enum(_arg(u, 1))
                nm = _arg(u, 2)
                mw = _deref(step, _arg(u, 3))
                factor = None
                if mw and mw["type"] == "IFCMEASUREWITHUNIT":
                    val = _arg(mw, 0)
                    if isinstance(val, _Typed):
                        factor = _num(val.value)
                    else:
                        factor = _num(val)
                nmu = str(nm).strip().upper() if isinstance(nm, str) else None
                if kind == "LENGTHUNIT":
                    if factor is None or factor <= 0:
                        issues.append(issue("BIM_UNIT_INVALID", "ERROR", "#%d" % u["id"],
                                            "a converted length unit has no valid factor"))
                    else:
                        length = (nmu or "CONVERSION", factor)
                elif kind == "PLANEANGLEUNIT":
                    if factor is None or factor <= 0:
                        issues.append(issue("BIM_UNIT_INVALID", "ERROR", "#%d" % u["id"],
                                            "a converted angle unit has no valid factor"))
                    else:
                        angle = (nmu or "CONVERSION", factor)
    if length is None:
        issues.append(issue("BIM_UNIT_UNRESOLVED", "ERROR", None,
                            "the file declares no length unit; it is never guessed"))
    if angle is None:
        issues.append(issue("BIM_UNIT_UNRESOLVED", "WARNING", None,
                            "the file declares no plane angle unit"))
    return {"length": {"name": length[0], "to_metre": _q(length[1])} if length else None,
            "angle": {"name": angle[0], "to_radian": _q(angle[1])} if angle else None,
            "canonical_length": SPEC["canonical_length_unit"],
            "issues": issues}


def _placement_local(step, pl):
    """يقرأ إزاحة ودوران موضع محلّي واحد."""
    ax = _deref(step, _arg(pl, 1))
    if not ax or ax["type"] != "IFCAXIS2PLACEMENT3D":
        return None
    p = _deref(step, _arg(ax, 0))
    if not p or p["type"] != "IFCCARTESIANPOINT":
        return None
    coords = _arg(p, 0) or []
    xyz = [_num(c) for c in coords[:3]]
    while len(xyz) < 3:
        xyz.append(0.0)
    if any(v is None for v in xyz):
        return None
    rot = 0.0
    xd = _deref(step, _arg(ax, 2))
    if xd and xd["type"] == "IFCDIRECTION":
        d = _arg(xd, 0) or []
        dx = _num(d[0]) if len(d) > 0 else None
        dy = _num(d[1]) if len(d) > 1 else None
        if dx is not None and dy is not None and (abs(dx) + abs(dy)) > 1e-12:
            rot = math.degrees(math.atan2(dy, dx))
    return {"xyz": [_q(v) for v in xyz], "rot_deg": _q(rot)}


def resolve_placements(step, length_factor):
    """يحلّ سلسلة المواضع إلى عالم مشروع واحد، ويكشف الحلقات والعمق."""
    issues = []
    ents = step["entities"]
    world = {}
    state = {}
    max_depth = int(LIMITS["max_placement_depth"])

    def resolve(eid, depth, seen):
        if eid in world:
            return world[eid]
        if eid in seen:
            issues.append(issue("BIM_PLACEMENT_CYCLE", "ERROR", "#%d" % eid,
                                "the placement chain forms a cycle"))
            world[eid] = None
            return None
        if depth > max_depth:
            issues.append(issue("BIM_RESOURCE_LIMIT_EXCEEDED", "ERROR", "#%d" % eid,
                                "the placement chain exceeds the declared depth"))
            world[eid] = None
            return None
        e = ents.get(eid)
        if not e or e["type"] != "IFCLOCALPLACEMENT":
            world[eid] = None
            return None
        loc = _placement_local(step, e)
        if loc is None:
            issues.append(issue("BIM_PLACEMENT_INVALID", "ERROR", "#%d" % eid,
                                "the placement carries no usable axis or point"))
            world[eid] = None
            return None
        parent_ref = _arg(e, 0)
        base = {"xyz": [0.0, 0.0, 0.0], "rot_deg": 0.0, "chain": 0}
        if isinstance(parent_ref, _Ref):
            seen2 = set(seen)
            seen2.add(eid)
            p = resolve(parent_ref.n, depth + 1, seen2)
            if p is None and parent_ref.n in world and world[parent_ref.n] is None:
                world[eid] = None
                return None
            if p:
                base = p
        # عمق السلسلة الحقيقي، لا عمق العودية: الحدّ المعلَن يجب أن يسري مهما
        # كان ترتيب الكيانات في الملفّ، وإلّا صار الحدّ أثراً للترتيب لا حدّاً
        chain = int(base.get("chain") or 0) + 1
        if chain > max_depth:
            issues.append(issue("BIM_RESOURCE_LIMIT_EXCEEDED", "ERROR", "#%d" % eid,
                                "the placement chain exceeds the declared depth"))
            world[eid] = None
            return None
        a = math.radians(base["rot_deg"])
        lx, ly, lz = loc["xyz"]
        wx = base["xyz"][0] + (lx * math.cos(a) - ly * math.sin(a))
        wy = base["xyz"][1] + (lx * math.sin(a) + ly * math.cos(a))
        wz = base["xyz"][2] + lz
        for v in (wx, wy, wz):
            if _num(v) is None:
                issues.append(issue("BIM_PLACEMENT_INVALID", "ERROR", "#%d" % eid,
                                    "the resolved placement is not finite"))
                world[eid] = None
                return None
        out = {"xyz": [_q(wx), _q(wy), _q(wz)],
               "rot_deg": _q((base["rot_deg"] + loc["rot_deg"]) % 360.0),
               "depth": chain, "chain": chain}
        world[eid] = out
        return out

    for eid in step["order"]:
        if ents[eid]["type"] == "IFCLOCALPLACEMENT":
            resolve(eid, 0, set())
    scaled = {}
    for k, v in world.items():
        if v is None:
            scaled[k] = None
        else:
            scaled[k] = {"xyz": [_q(c * length_factor) for c in v["xyz"]],
                         "rot_deg": v["rot_deg"], "depth": v["depth"],
                         "chain": v["chain"]}
    return {"world": scaled, "issues": issues}


def extract_relationships(step):
    """يستخرج علاقات التجميع والاحتواء والتفريغ والملء، ويكشف حلقاتها."""
    issues = []
    ents = step["entities"]
    aggregates, contains, voids, fills = {}, {}, {}, {}
    count = 0
    for eid in step["order"]:
        e = ents[eid]
        t = e["type"]
        if t == "IFCRELAGGREGATES":
            parent = _arg(e, 4)
            kids = _arg(e, 5) or []
            if isinstance(parent, _Ref):
                for k in kids:
                    if isinstance(k, _Ref):
                        aggregates.setdefault(parent.n, []).append(k.n)
                        count += 1
        elif t == "IFCRELCONTAINEDINSPATIALSTRUCTURE":
            items = _arg(e, 4) or []
            host = _arg(e, 5)
            if isinstance(host, _Ref):
                for k in items:
                    if isinstance(k, _Ref):
                        contains.setdefault(host.n, []).append(k.n)
                        count += 1
        elif t == "IFCRELVOIDSELEMENT":
            host = _arg(e, 4)
            op = _arg(e, 5)
            if isinstance(host, _Ref) and isinstance(op, _Ref):
                voids[op.n] = host.n
                count += 1
        elif t == "IFCRELFILLSELEMENT":
            op = _arg(e, 4)
            el = _arg(e, 5)
            if isinstance(op, _Ref) and isinstance(el, _Ref):
                fills[el.n] = op.n
                count += 1
        if count > int(LIMITS["max_relationship_count"]):
            issues.append(issue("BIM_RESOURCE_LIMIT_EXCEEDED", "ERROR", None,
                                "relationship count exceeds the declared maximum"))
            return {"aggregates": {}, "contains": {}, "voids": {}, "fills": {},
                    "count": count, "issues": issues}

    def find_cycle(graph, code, label):
        colour = {}

        def visit(node, depth):
            if depth > int(LIMITS["max_placement_depth"]) * 4:
                issues.append(issue("BIM_RESOURCE_LIMIT_EXCEEDED", "ERROR",
                                    "#%d" % node, "%s nesting is too deep" % label))
                return True
            c = colour.get(node)
            if c == 1:
                issues.append(issue(code, "ERROR", "#%d" % node,
                                    "the %s graph forms a cycle" % label))
                return True
            if c == 2:
                return False
            colour[node] = 1
            for k in graph.get(node, []):
                if visit(k, depth + 1):
                    colour[node] = 2
                    return True
            colour[node] = 2
            return False
        for n in sorted(graph.keys()):
            if visit(n, 0):
                return True
        return False

    find_cycle(aggregates, "BIM_CONTAINMENT_CYCLE", "aggregation")
    find_cycle(contains, "BIM_CONTAINMENT_CYCLE", "containment")
    chain = {}
    for op, host in voids.items():
        chain.setdefault(op, []).append(host)
    for el, op in fills.items():
        chain.setdefault(el, []).append(op)
    find_cycle(chain, "BIM_RELATIONSHIP_INVALID", "opening")
    return {"aggregates": aggregates, "contains": contains, "voids": voids,
            "fills": fills, "count": count, "issues": issues}


def _unstated_flags(step):
    """يقرأ إعلان النموذج بأن بُعداً ما غير مذكور، فلا تُتبنّى القيمة النائبة."""
    ents = step["entities"]
    flags = {}
    psets = {}
    refused = []
    for e in ents.values():
        if e["type"] != "IFCPROPERTYSET":
            continue
        vals = {}
        for pr in (_arg(e, 4) or []):
            pv = _deref(step, pr)
            if not pv or pv["type"] != "IFCPROPERTYSINGLEVALUE":
                continue
            nm = _arg(pv, 0)
            raw = _arg(pv, 2)
            val = raw.value if isinstance(raw, _Typed) else raw
            en = _enum(val) if isinstance(val, dict) else None
            if not isinstance(nm, str):
                continue
            # اسم خاصّية خارجي لا يصير مفتاح كائن قبل أن يجتاز قائمة السماح:
            # مفاتيح النموذج الأوّلي ومسارات الكائن تُرفض ولا تُخزَّن أصلاً
            if not safe_key(nm):
                refused.append((e["id"], nm))
                continue
            vals[nm] = (en == "T") if en in ("T", "F") else val
        psets[e["id"]] = vals
    for e in ents.values():
        if e["type"] != "IFCRELDEFINESBYPROPERTIES":
            continue
        pset = _arg(e, 5)
        objs = _arg(e, 4) or []
        vals = psets.get(pset.n) if isinstance(pset, _Ref) else None
        if not vals:
            continue
        for o in objs:
            if isinstance(o, _Ref):
                cur = flags.setdefault(o.n, {})
                cur.update(vals)
    return {"flags": flags, "refused_keys": refused}


def _profile_of(step, product):
    """أبعاد المقطع المستطيل وعمق البثق إن وُجدا — لا استنتاج من غيرهما."""
    rep = _deref(step, _arg(product, 6))
    if not rep or rep["type"] != "IFCPRODUCTDEFINITIONSHAPE":
        return None
    for r in (_arg(rep, 2) or []):
        shp = _deref(step, r)
        if not shp or shp["type"] != "IFCSHAPEREPRESENTATION":
            continue
        if _arg(shp, 1) != "Body":
            continue
        for it in (_arg(shp, 3) or []):
            solid = _deref(step, it)
            if not solid or solid["type"] != "IFCEXTRUDEDAREASOLID":
                continue
            prof = _deref(step, _arg(solid, 0))
            depth = _num(_arg(solid, 3))
            if not prof or prof["type"] != "IFCRECTANGLEPROFILEDEF":
                return {"kind": "OPAQUE_GEOMETRY", "depth": depth}
            pos = _deref(step, _arg(solid, 1))
            base_z = 0.0
            if pos and pos["type"] == "IFCAXIS2PLACEMENT3D":
                pt = _deref(step, _arg(pos, 0))
                if pt:
                    c = _arg(pt, 0) or []
                    if len(c) > 2 and _num(c[2]) is not None:
                        base_z = _num(c[2])
            return {"kind": "PARAMETRIC_MAPPED",
                    "x_dim": _num(_arg(prof, 3)), "y_dim": _num(_arg(prof, 4)),
                    "depth": depth, "base_z": base_z}
    return None


def _axis_length(step, product):
    rep = _deref(step, _arg(product, 6))
    if not rep or rep["type"] != "IFCPRODUCTDEFINITIONSHAPE":
        return None
    for r in (_arg(rep, 2) or []):
        shp = _deref(step, r)
        if not shp or shp["type"] != "IFCSHAPEREPRESENTATION":
            continue
        if _arg(shp, 1) != "Axis":
            continue
        for it in (_arg(shp, 3) or []):
            poly = _deref(step, it)
            if not poly or poly["type"] != "IFCPOLYLINE":
                continue
            pts = []
            for pr in (_arg(poly, 0) or []):
                p = _deref(step, pr)
                if p and p["type"] == "IFCCARTESIANPOINT":
                    c = [_num(v) for v in (_arg(p, 0) or [])[:2]]
                    if len(c) == 2 and None not in c:
                        pts.append(c)
            if len(pts) >= 2:
                dx = pts[-1][0] - pts[0][0]
                dy = pts[-1][1] - pts[0][1]
                return _q(math.sqrt(dx * dx + dy * dy))
    return None


def _prov(step, e, import_id, imported_at):
    gid = _arg(e, 0)
    return {"format": "IFC", "schema": step["schema"],
            "global_id": gid if isinstance(gid, str) else None,
            "entity_type": e["type"], "source_entity_id": "#%d" % e["id"],
            "source_file_hash": step["file_hash"],
            "source_file_name": step.get("file_name"),
            "import_id": import_id, "imported_at": imported_at,
            "parser_version": step["parser_version"],
            "mapper_version": MAPPER_VERSION}


def _support_of(t):
    e = ENTITY_SUPPORT_UPPER.get(str(t).upper())
    return e["support"] if e else "UNSUPPORTED"


def stage_import(text, file_name=None, options=None, import_id=None, imported_at=None):
    """يُنشئ نموذج تجهيز خارجياً. writes_to_model يبقى false دائماً."""
    o = options or {}
    parsed = parse_step(text, file_name)
    if not parsed["valid"]:
        return {"valid": False, "issues": parsed["issues"], "staging": None}
    step = parsed["step"]
    iid = import_id or ("bimimp_" + _sha16({"h": step["file_hash"],
                                            "s": step["schema"]}))
    issues = list(parsed["issues"])

    units = resolve_units(step)
    issues += units["issues"]
    lf = units["length"]["to_metre"] if units["length"] else None
    if lf is None:
        return {"valid": False, "issues": issues, "staging": {
            "import_id": iid, "status": "BLOCKED", "schema": step["schema"],
            "units": units, "entities": [], "relationships": {}, "issues": issues,
            "writes_to_model": False}}

    pl = resolve_placements(step, lf)
    issues += pl["issues"]
    rel = extract_relationships(step)
    issues += rel["issues"]
    if any(i["blocking"] for i in issues):
        return {"valid": False, "issues": issues, "staging": {
            "import_id": iid, "status": "BLOCKED", "schema": step["schema"],
            "units": units, "entities": [], "relationships": {}, "issues": issues,
            "writes_to_model": False}}

    ents = step["entities"]
    world = pl["world"]
    _uf = _unstated_flags(step)
    unstated = _uf["flags"]
    for _eid, _nm in _uf["refused_keys"]:
        issues.append(issue("BIM_PROPERTY_REFUSED", "WARNING", "#%d" % _eid,
                            "an external property name is not an accepted key and "
                            "was dropped before it could become one"))
    af = (units["angle"]["to_radian"] if units["angle"] else 1.0)
    ang_scale = 1.0 if not units["angle"] else 1.0   # الدوران يُقرأ من الاتجاه لا من قيمة

    def place(e):
        pr = _arg(e, 5)
        if isinstance(pr, _Ref):
            return world.get(pr.n)
        return None

    storey_of = {}
    for host, items in rel["contains"].items():
        for it in items:
            storey_of[it] = host
    space_of_storey = {}

    out_entities = []
    seen_gids = {}
    counts = {"SUPPORTED": 0, "PARTIALLY_SUPPORTED": 0, "PRESERVED_OPAQUE": 0,
              "UNSUPPORTED": 0, "REFUSED": 0}
    levels_by_ref = {}

    for eid in step["order"]:
        e = ents[eid]
        t = e["type"]
        if t.startswith("IFCREL") or t in (
                "IFCCARTESIANPOINT", "IFCDIRECTION", "IFCAXIS2PLACEMENT3D",
                "IFCLOCALPLACEMENT", "IFCEXTRUDEDAREASOLID", "IFCRECTANGLEPROFILEDEF",
                "IFCSHAPEREPRESENTATION", "IFCPRODUCTDEFINITIONSHAPE", "IFCPOLYLINE",
                "IFCSIUNIT", "IFCUNITASSIGNMENT", "IFCCONVERSIONBASEDUNIT",
                "IFCMEASUREWITHUNIT", "IFCDIMENSIONALEXPONENTS", "IFCPERSON",
                "IFCORGANIZATION", "IFCPERSONANDORGANIZATION", "IFCAPPLICATION",
                "IFCOWNERHISTORY", "IFCGEOMETRICREPRESENTATIONCONTEXT",
                "IFCPROPERTYSET", "IFCPROPERTYSINGLEVALUE"):
            continue
        support = _support_of(t)
        gid = _arg(e, 0)
        name = _arg(e, 2)
        if isinstance(gid, str) and gid:
            if not is_safe_id(gid):
                issues.append(issue("BIM_INVALID_IDENTIFIER", "ERROR", "#%d" % eid,
                                    "the GlobalId is not a plausible identifier"))
                counts["REFUSED"] += 1
                continue
            if gid in seen_gids:
                issues.append(issue("BIM_DUPLICATE_ID", "ERROR", "#%d" % eid,
                                    "GlobalId %s appears more than once" % gid))
                counts["REFUSED"] += 1
                continue
            seen_gids[gid] = eid
        if isinstance(name, str) and is_unsafe(name):
            issues.append(issue("BIM_UNSAFE_STRING", "ERROR", "#%d" % eid,
                                "an entity name carries an unsafe value; it is refused"))
            counts["REFUSED"] += 1
            continue

        rec = {"source_entity_id": "#%d" % eid, "entity_type": t,
               "support": support, "name": name if isinstance(name, str) else None,
               "external_global_id": gid if isinstance(gid, str) else None,
               "canonical_kind": None, "mapping_class": None,
               "mapping_basis": None, "world": place(e),
               "level_ref": storey_of.get(eid), "geometry": {}, "properties": {},
               "provenance": _prov(step, e, iid, imported_at)}

        if support in ("UNSUPPORTED", "REFUSED"):
            rec["mapping_class"] = "UNSUPPORTED_GEOMETRY"
            issues.append(issue("BIM_UNSUPPORTED_ENTITY", "WARNING", "#%d" % eid,
                                "%s has no declared canonical mapping" % t))
            counts["UNSUPPORTED"] += 1
            out_entities.append(rec)
            continue
        if support == "PRESERVED_OPAQUE":
            rec["mapping_class"] = "OPAQUE_GEOMETRY"
            issues.append(issue("BIM_UNSUPPORTED_ENTITY", "INFO", "#%d" % eid,
                                "%s is preserved as external metadata only" % t))
            counts["PRESERVED_OPAQUE"] += 1
            out_entities.append(rec)
            continue

        prof = _profile_of(step, e)
        w = rec["world"]
        if t == "IFCPROJECT":
            rec["canonical_kind"] = "project"
            rec["mapping_class"] = "PARAMETRIC_MAPPED"
        elif t == "IFCSITE":
            rec["canonical_kind"] = "site"
            rec["mapping_class"] = "PARAMETRIC_MAPPED"
        elif t == "IFCBUILDING":
            rec["canonical_kind"] = "building"
            rec["mapping_class"] = "PARAMETRIC_MAPPED"
        elif t == "IFCBUILDINGSTOREY":
            elev = _num(_arg(e, 9))
            rec["canonical_kind"] = "level"
            rec["mapping_class"] = "PARAMETRIC_MAPPED"
            rec["geometry"] = {"elevation": _q((elev or 0.0) * lf),
                               "elevation_source": "MODEL" if elev is not None
                               else "PLACEMENT"}
            if elev is None and w:
                rec["geometry"]["elevation"] = _q(w["xyz"][2])
            levels_by_ref[eid] = rec
        elif t == "IFCSPACE":
            rec["canonical_kind"] = "space"
            rec["mapping_class"] = "PARAMETRIC_MAPPED"
            long_name = _arg(e, 7)
            g = {"x": w["xyz"][0] if w else None, "z": w["xyz"][1] if w else None}
            if prof and prof.get("kind") == "PARAMETRIC_MAPPED":
                g["w"] = _q((prof["x_dim"] or 0.0) * lf)
                g["d"] = _q((prof["y_dim"] or 0.0) * lf)
                g["height"] = _q((prof["depth"] or 0.0) * lf)
            else:
                rec["mapping_class"] = "BOUNDING_GEOMETRY_ONLY"
                issues.append(issue("BIM_GEOMETRY_LOSS", "WARNING", "#%d" % eid,
                                    "space geometry is not a mappable rectangle"))
            rec["geometry"] = g
            rec["properties"]["number"] = long_name if isinstance(long_name, str) else None
        elif t in ("IFCWALL", "IFCWALLSTANDARDCASE"):
            rec["canonical_kind"] = "wall"
            length = _axis_length(step, e)
            if prof and prof.get("kind") == "PARAMETRIC_MAPPED":
                length = length if length is not None else prof["x_dim"]
                rec["geometry"] = {
                    "x": w["xyz"][0] if w else None, "z": w["xyz"][1] if w else None,
                    "rot_deg": w["rot_deg"] if w else None,
                    "length": _q((length or 0.0) * lf),
                    "thickness": _q((prof["y_dim"] or 0.0) * lf),
                    "thickness_known": prof["y_dim"] is not None,
                    "height": _q((prof["depth"] or 0.0) * lf)}
                if unstated.get(eid, {}).get("ThicknessIsModelStated") is False:
                    rec["geometry"]["thickness"] = None
                    rec["geometry"]["thickness_known"] = False
                    rec["geometry"]["thickness_placeholder_in_file"] = _q(
                        (prof["y_dim"] or 0.0) * lf)
                    rec["properties"]["ThicknessIsModelStated"] = False
                    issues.append(issue("BIM_WALL_THICKNESS_UNRESOLVED", "INFO",
                                        "#%d" % eid,
                                        "the file states the thickness is not model "
                                        "stated; the placeholder is not adopted"))
                rec["mapping_class"] = "PARAMETRIC_MAPPED"
            elif length is not None:
                rec["geometry"] = {
                    "x": w["xyz"][0] if w else None, "z": w["xyz"][1] if w else None,
                    "rot_deg": w["rot_deg"] if w else None,
                    "length": _q(length * lf), "thickness": None,
                    "thickness_known": False, "height": None}
                rec["mapping_class"] = "BOUNDING_GEOMETRY_ONLY"
                issues.append(issue("BIM_WALL_THICKNESS_UNRESOLVED", "WARNING",
                                    "#%d" % eid,
                                    "wall thickness cannot be determined and is not "
                                    "invented"))
            else:
                rec["mapping_class"] = "UNSUPPORTED_GEOMETRY"
                issues.append(issue("BIM_UNSUPPORTED_GEOMETRY", "WARNING", "#%d" % eid,
                                    "the wall carries no axis or profile to map"))
        elif t in ("IFCSLAB", "IFCROOF"):
            rec["canonical_kind"] = "slab"
            pdt = _enum(_arg(e, 8)) or "UNKNOWN"
            rec["properties"]["predefined_type"] = pdt
            if prof and prof.get("kind") == "PARAMETRIC_MAPPED":
                rec["geometry"] = {
                    "x": w["xyz"][0] if w else None, "z": w["xyz"][1] if w else None,
                    "w": _q((prof["x_dim"] or 0.0) * lf),
                    "d": _q((prof["y_dim"] or 0.0) * lf),
                    "thickness": _q((prof["depth"] or 0.0) * lf),
                    "thickness_known": prof["depth"] is not None,
                    "elevation": w["xyz"][2] if w else None}
                rec["mapping_class"] = "PARAMETRIC_MAPPED"
            else:
                rec["mapping_class"] = "BOUNDING_GEOMETRY_ONLY"
                issues.append(issue("BIM_GEOMETRY_LOSS", "WARNING", "#%d" % eid,
                                    "slab geometry is not a mappable rectangle"))
        elif t in ("IFCDOOR", "IFCWINDOW"):
            rec["canonical_kind"] = "door" if t == "IFCDOOR" else "window"
            h = _num(_arg(e, 8))
            wd = _num(_arg(e, 9))
            rec["geometry"] = {
                "x": w["xyz"][0] if w else None, "z": w["xyz"][1] if w else None,
                "y": w["xyz"][2] if w else None,
                "rot_deg": w["rot_deg"] if w else None,
                "width": _q(wd * lf) if wd is not None else None,
                "height": _q(h * lf) if h is not None else None,
                "width_known": wd is not None, "height_known": h is not None}
            rec["mapping_class"] = "PARAMETRIC_MAPPED"
            op = rel["fills"].get(eid)
            host = rel["voids"].get(op) if op is not None else None
            if host is not None:
                rec["host_source_id"] = "#%d" % host
                rec["host_basis"] = "IFC_RELATIONSHIP"
            else:
                rec["host_source_id"] = None
                rec["host_basis"] = "UNRESOLVED"
                issues.append(issue("BIM_HOST_UNRESOLVED", "WARNING", "#%d" % eid,
                                    "no void and fill relationship names a host wall; "
                                    "no host is inferred from coordinates"))
        elif t in ("IFCSTAIR", "IFCSTAIRFLIGHT"):
            rec["canonical_kind"] = "object"
            rec["properties"]["object_kind"] = "stairs"
            rec["mapping_class"] = "BOUNDING_GEOMETRY_ONLY"
            if prof and prof.get("kind") == "PARAMETRIC_MAPPED":
                rec["geometry"] = {
                    "x": w["xyz"][0] if w else None, "z": w["xyz"][1] if w else None,
                    "w": _q((prof["x_dim"] or 0.0) * lf),
                    "d": _q((prof["y_dim"] or 0.0) * lf)}
        elif t == "IFCOPENINGELEMENT":
            rec["canonical_kind"] = "opening"
            rec["mapping_class"] = "PARAMETRIC_MAPPED"
            rec["geometry"] = {"x": w["xyz"][0] if w else None,
                               "z": w["xyz"][1] if w else None}
        if rec["canonical_kind"] is None:
            rec["mapping_class"] = rec["mapping_class"] or "UNSUPPORTED_GEOMETRY"
            counts["UNSUPPORTED"] += 1
        else:
            counts[support] = counts.get(support, 0) + 1
        rec["mapping_basis"] = "SOURCE_GLOBAL_ID" if rec["external_global_id"] \
            else "SEMANTIC_AND_GEOMETRY"
        out_entities.append(rec)

    # الأدوار تُربط بالعناصر عبر الاحتواء الحقيقي لا بالقرب
    ref_to_level = {}
    for eid, lrec in levels_by_ref.items():
        ref_to_level[eid] = lrec["source_entity_id"]
    for rec in out_entities:
        lr = rec.get("level_ref")
        rec["level_source_id"] = ref_to_level.get(lr) if lr is not None else None
        rec["containment_basis"] = "IFC_RELATIONSHIP" if rec.get("level_source_id") \
            else "UNRESOLVED"
        rec.pop("level_ref", None)

    geo = _georeference(step, ents)
    staging = {
        "schema": SCHEMA, "import_id": iid, "status": "STAGED",
        "source": {"file_name": step.get("file_name"),
                   "file_hash": step["file_hash"],
                   "byte_length": len(text.encode("utf-8")),
                   "format": "IFC_SPF"},
        "bim_schema": step["schema"],
        "schema_support": "SUPPORTED" if step["schema"] in SPEC["supported_schemas"]
                          else "PARTIALLY_SUPPORTED",
        "units": units,
        "coordinate_system": {"policy": SPEC["coordinate_policy"],
                              "resolved_to": "PROJECT_WORLD",
                              "length_unit_to_metre": lf},
        "georeference": geo,
        "entities": out_entities,
        "relationships": {"aggregates": rel["aggregates"], "contains": rel["contains"],
                          "voids": rel["voids"], "fills": rel["fills"],
                          "count": rel["count"]},
        "counts": {"entities": len(out_entities), "parsed_entities": step["entity_count"],
                   "supported": counts["SUPPORTED"],
                   "partial": counts["PARTIALLY_SUPPORTED"],
                   "opaque": counts["PRESERVED_OPAQUE"],
                   "unsupported": counts["UNSUPPORTED"],
                   "refused": counts["REFUSED"],
                   "levels": len([r for r in out_entities
                                  if r["canonical_kind"] == "level"]),
                   "spaces": len([r for r in out_entities
                                  if r["canonical_kind"] == "space"])},
        "issues": issues,
        "provenance": {"parser_version": PARSER_VERSION,
                       "mapper_version": MAPPER_VERSION,
                       "imported_at": imported_at,
                       "source_file_hash": step["file_hash"]},
        "writes_to_model": False,
        "is_model_truth": False,
        "note": "an import staging model is external input. It is never the canonical "
                "engineering model and never writes to it.",
    }
    staging["staging_id"] = "bimstg_" + _sha16(
        {"i": iid, "h": step["file_hash"], "n": len(out_entities)})
    if staging["counts"]["spaces"] > int(LIMITS["max_spaces"]) \
            or staging["counts"]["levels"] > int(LIMITS["max_levels"]):
        issues.append(issue("BIM_RESOURCE_LIMIT_EXCEEDED", "ERROR", None,
                            "space or level count exceeds the declared maximum"))
    blocking = [i for i in issues if i["blocking"]]
    if blocking:
        staging["status"] = "BLOCKED"
    return {"valid": not blocking, "issues": issues, "staging": staging}


def _georeference(step, ents):
    """المرجعية الجغرافية تُحفظ منفصلة ولا تُخلط بإحداثيات النموذج المحلّية."""
    lat = lon = None
    for e in ents.values():
        if e["type"] != "IFCSITE":
            continue
        la = _arg(e, 9)
        lo = _arg(e, 10)
        if isinstance(la, list) and la:
            lat = la
        if isinstance(lo, list) and lo:
            lon = lo
    has_map = any(e["type"] in ("IFCMAPCONVERSION", "IFCPROJECTEDCRS")
                  for e in ents.values())
    if lat is None and lon is None and not has_map:
        state = "LOCAL_ONLY"
    elif has_map and lat is not None and lon is not None:
        state = "SOURCE_GEOREFERENCE_PRESENT"
    elif lat is not None or lon is not None or has_map:
        state = "GEOREFERENCE_PARTIAL"
    else:
        state = "GEOREFERENCE_UNRESOLVED"
    return {"state": state, "latitude_dms": lat, "longitude_dms": lon,
            "map_conversion_present": has_map,
            "equivalent_to_local_coordinates": False,
            "geospatial_accuracy_claimed": False}


# =========================================== المقارنة والذهاب والإياب ======
def _near(a, b, tol):
    na, nb = _num(a), _num(b)
    if na is None or nb is None:
        return na is None and nb is None
    return abs(na - nb) <= float(tol)


def _staged(staging, kind):
    return [e for e in staging["entities"] if e.get("canonical_kind") == kind]


def _wall_key(x, z, rot, length):
    return (round(float(x or 0), 3), round(float(z or 0), 3),
            round(float(rot or 0) % 180.0, 2), round(float(length or 0), 3))


def roundtrip_report(project, staging, options=None):
    """تقرير أمانة الذهاب والإياب. الفقد يُصنَّف ولا يُخفى، والحرج لا يمرّ."""
    built = build_exchange(project, options)
    if not built["valid"]:
        return {"valid": False, "issues": built["issues"], "report": None}
    ex = built["exchange"]
    tol = TOL
    losses, warnings, compared = [], [], {}

    def loss(cls, sev, eid, msg):
        losses.append({"entity_id": eid, "type": cls, "severity": sev, "message": msg})

    def cmp_count(label, a, b, critical):
        compared[label] = {"source": a, "roundtrip": b, "equal": a == b}
        if a != b:
            loss("CRITICAL_GEOMETRY_LOSS" if critical else "SEMANTIC_DEGRADATION",
                 "ERROR" if critical else "WARNING", None,
                 "%s differs: source %d, round trip %d" % (label, a, b))

    s_levels = _staged(staging, "level")
    s_spaces = _staged(staging, "space")
    s_walls = _staged(staging, "wall")
    s_doors = _staged(staging, "door")
    s_windows = _staged(staging, "window")
    s_slabs = _staged(staging, "slab")
    s_stairs = [e for e in _staged(staging, "object")
                if (e.get("properties") or {}).get("object_kind") == "stairs"]
    s_bldg = [e for e in staging["entities"] if e.get("canonical_kind") == "building"]

    cmp_count("building_count", 1, len(s_bldg), True)
    cmp_count("level_count", len(ex["levels"]), len(s_levels), True)
    cmp_count("wall_count", len(ex["walls"]), len(s_walls), True)
    cmp_count("door_count", len(ex["doors"]), len(s_doors), True)
    cmp_count("window_count", len(ex["windows"]), len(s_windows), True)
    cmp_count("slab_count", len(ex["slabs"]), len(s_slabs), True)
    cmp_count("space_count", len(ex["spaces"]), len(s_spaces), True)
    cmp_count("stair_count", len(ex["stairs"]), len(s_stairs), False)

    # مناسيب الأدوار
    src_elev = sorted(_q(l["elevation"]) for l in ex["levels"])
    rt_elev = sorted(_q(l["geometry"]["elevation"]) for l in s_levels)
    ok = len(src_elev) == len(rt_elev) and all(
        _near(a, b, tol["elevation_tolerance_m"]) for a, b in zip(src_elev, rt_elev))
    compared["level_elevations"] = {"source": src_elev, "roundtrip": rt_elev,
                                    "equal": ok}
    if not ok:
        loss("CRITICAL_GEOMETRY_LOSS", "ERROR", None,
             "level elevations differ beyond the declared tolerance")

    # الجدران: موضع وطول وسماكة وارتفاع
    src_walls = {}
    for wl in ex["walls"]:
        x1, z1 = wl["start"]
        x2, z2 = wl["end"]
        length = _q(math.sqrt((x2 - x1) ** 2 + (z2 - z1) ** 2))
        rot = _q(math.degrees(math.atan2(z2 - z1, x2 - x1)))
        src_walls[_wall_key(x1, z1, rot, length)] = wl
    matched_w, moved_w, dim_w = 0, 0, 0
    for sw in s_walls:
        g = sw.get("geometry") or {}
        k = _wall_key(g.get("x"), g.get("z"), g.get("rot_deg"), g.get("length"))
        src = src_walls.get(k)
        if src is None:
            moved_w += 1
            loss("CRITICAL_GEOMETRY_LOSS", "ERROR", sw["source_entity_id"],
                 "no source wall matches this position, orientation and length")
            continue
        matched_w += 1
        if not _near(g.get("height"), src["height"], tol["dimension_tolerance_m"]):
            dim_w += 1
            loss("GEOMETRY_APPROXIMATION", "WARNING", sw["source_entity_id"],
                 "wall height differs beyond the declared tolerance")
        if src["thickness_known"] and not _near(g.get("thickness"), src["thickness"],
                                                tol["dimension_tolerance_m"]):
            dim_w += 1
            loss("GEOMETRY_APPROXIMATION", "WARNING", sw["source_entity_id"],
                 "wall thickness differs beyond the declared tolerance")
        if not src["thickness_known"] and g.get("thickness_known"):
            warnings.append({"entity_id": sw["source_entity_id"],
                             "type": "PROPERTY_LOSS",
                             "message": "thickness was unknown in the model and the "
                                        "exchange wrote a declared default; it is "
                                        "reported, not adopted"})
    compared["wall_positions"] = {"matched": matched_w, "unmatched": moved_w,
                                  "equal": moved_w == 0}
    compared["wall_dimensions"] = {"mismatched": dim_w, "equal": dim_w == 0}

    # الفتحات: موضع وعرض
    for label, src_list, st_list in (("door", ex["doors"], s_doors),
                                     ("window", ex["windows"], s_windows)):
        src_map = {}
        for op in src_list:
            src_map[(round(op["x"], 3), round(op["z"], 3))] = op
        matched, unmatched, dim = 0, 0, 0
        for so in st_list:
            g = so.get("geometry") or {}
            k = (round(float(g.get("x") or 0), 3), round(float(g.get("z") or 0), 3))
            src = src_map.get(k)
            if src is None:
                unmatched += 1
                loss("CRITICAL_GEOMETRY_LOSS", "ERROR", so["source_entity_id"],
                     "no source %s matches this position" % label)
                continue
            matched += 1
            if not _near(g.get("width"), src["width"], tol["dimension_tolerance_m"]):
                dim += 1
                loss("GEOMETRY_APPROXIMATION", "WARNING", so["source_entity_id"],
                     "%s width differs beyond the declared tolerance" % label)
        compared[label + "_positions"] = {"matched": matched, "unmatched": unmatched,
                                          "equal": unmatched == 0}
        if dim:
            compared[label + "_dimensions"] = {"mismatched": dim, "equal": False}

    # أسماء الفراغات
    src_names = sorted(str(s["name"]) for s in ex["spaces"])
    rt_names = sorted(str(s["name"]) for s in s_spaces)
    compared["space_names"] = {"equal": src_names == rt_names,
                               "source": len(src_names), "roundtrip": len(rt_names)}
    if src_names != rt_names:
        loss("SEMANTIC_DEGRADATION", "ERROR", None,
             "space names differ after the round trip")

    # العلاقات
    contained = len([e for e in staging["entities"]
                     if e.get("containment_basis") == "IFC_RELATIONSHIP"])
    hosted = len([e for e in (s_doors + s_windows)
                  if e.get("host_basis") == "IFC_RELATIONSHIP"])
    compared["containment"] = {"resolved": contained, "equal": contained > 0}
    compared["host_relationships"] = {
        "resolved": hosted, "expected": len(ex["doors"]) + len(ex["windows"]),
        "equal": hosted == len(ex["doors"]) + len(ex["windows"])}
    if not compared["host_relationships"]["equal"]:
        loss("RELATIONSHIP_LOSS", "WARNING", None,
             "not every opening recovered a host wall relationship")

    for u in ex["unsupported"]:
        loss("UNSUPPORTED_ENTITY", "WARNING", u["canonical_id"],
             "the object kind %s has no declared IFC mapping" % u.get("kind"))

    total = len(compared)
    equal = len([k for k in compared if compared[k].get("equal")])
    geom_keys = [k for k in compared if "position" in k or "elevation" in k
                 or "dimension" in k or k.endswith("_count")]
    geom_equal = len([k for k in geom_keys if compared[k].get("equal")])
    rel_keys = ["containment", "host_relationships"]
    rel_equal = len([k for k in rel_keys if compared.get(k, {}).get("equal")])
    prop_total = len(ex["walls"]) + len(ex["slabs"])
    prop_lost = len([l for l in losses if l["type"] == "PROPERTY_LOSS"]) + \
        len([w for w in warnings if w["type"] == "PROPERTY_LOSS"])

    critical = [l for l in losses if l["type"] in SPEC["critical_loss_classes"]]
    errors = [l for l in losses if l["severity"] == "ERROR"]
    status = "FAIL" if (critical or errors) else ("WARNING" if losses else "PASS")
    report = {
        "schema": SCHEMA,
        "report_id": "bimrt_" + _sha16({"m": project.get("model_hash"),
                                        "s": staging.get("staging_id")}),
        "status": status,
        "model_hash": project.get("model_hash"),
        "revision_id": project.get("current_revision"),
        "source_file_hash": staging["source"]["file_hash"],
        "semantic_fidelity": _q(equal / float(total)) if total else 0.0,
        "geometry_fidelity": _q(geom_equal / float(len(geom_keys)))
                             if geom_keys else 0.0,
        "relationship_fidelity": _q(rel_equal / float(len(rel_keys))),
        "property_fidelity": _q(max(0.0, 1.0 - (prop_lost / float(prop_total)))
                                if prop_total else 1.0),
        "compared": compared,
        "losses": losses, "warnings": warnings,
        "critical_loss_count": len(critical),
        "tolerances": dict(tol),
        "writes_to_model": False,
        "note": "a critical geometry loss can never report PASS.",
    }
    return {"valid": True, "issues": [], "report": report}


# ================================================ الفرق والمقترحات =========
def import_diff(project, staging, options=None):
    """يقارن نموذج التجهيز بالنموذج القانوني. لا يعدّل شيئاً إطلاقاً."""
    before = project.get("model_hash")
    built = build_exchange(project, options)
    if not built["valid"]:
        return {"valid": False, "issues": built["issues"], "diff": None}
    ex = built["exchange"]
    diffs = []
    tol = TOL

    def add(kind, target, source, field=None, old=None, new=None,
            basis="UNMATCHED", severity="INFO", loss=None, authoring_id=None):
        diffs.append({"type": kind, "canonical_id": target,
                      "authoring_id": authoring_id,
                      "source_entity_id": source, "field": field,
                      "old_value": old, "proposed_value": new,
                      "mapping_basis": basis, "severity": severity,
                      "loss": loss})

    for group, kind in (("walls", "wall"), ("doors", "door"),
                        ("windows", "window"), ("spaces", "space"),
                        ("slabs", "slab")):
        src = {}
        for it in ex[group]:
            if kind == "wall":
                x1, z1 = it["start"]
                x2, z2 = it["end"]
                key = _wall_key(x1, z1, _q(math.degrees(math.atan2(z2 - z1, x2 - x1))),
                                _q(math.sqrt((x2 - x1) ** 2 + (z2 - z1) ** 2)))
            elif kind in ("door", "window"):
                key = (round(it["x"], 3), round(it["z"], 3))
            elif kind == "space":
                key = (round(it["footprint"][0], 3), round(it["footprint"][1], 3))
            else:
                key = (round(it["outline"][0], 3), round(it["outline"][1], 3))
            src[key] = it
        used = set()
        for st in _staged(staging, kind):
            g = st.get("geometry") or {}
            if kind == "wall":
                key = _wall_key(g.get("x"), g.get("z"), g.get("rot_deg"),
                                g.get("length"))
            else:
                key = (round(float(g.get("x") or 0), 3),
                       round(float(g.get("z") or 0), 3))
            match = src.get(key)
            if match is None:
                add("OBJECT_ADDED", None, st["source_entity_id"],
                    severity="WARNING", basis="UNMATCHED")
                continue
            used.add(key)
            basis = "SOURCE_GLOBAL_ID" if st.get("external_global_id") \
                else "SEMANTIC_AND_GEOMETRY"
            if kind == "wall":
                if not _near(g.get("height"), match["height"],
                             tol["dimension_tolerance_m"]):
                    add("OBJECT_RESIZED", match["canonical_id"],
                        st["source_entity_id"], "height", match["height"],
                        g.get("height"), basis, "WARNING")
            elif kind in ("door", "window"):
                if not _near(g.get("width"), match["width"],
                             tol["dimension_tolerance_m"]):
                    add("OBJECT_RESIZED", match["canonical_id"],
                        st["source_entity_id"], "width", match["width"],
                        g.get("width"), basis, "WARNING")
                sh = st.get("host_source_id")
                if sh is None:
                    add("HOST_CHANGED", match["canonical_id"],
                        st["source_entity_id"], "host_wall_id",
                        match["host_wall_id"], None, "UNMATCHED", "WARNING",
                        "RELATIONSHIP_LOSS")
            elif kind == "space":
                if str(st.get("name")) != str(match["name"]):
                    add("PROPERTY_CHANGED", match["canonical_id"],
                        st["source_entity_id"], "name", match["name"],
                        st.get("name"), basis, "INFO",
                        authoring_id=match.get("authoring_id"))
                if not _near((g.get("w") or 0) * (g.get("d") or 0), match["area_m2"],
                             tol["area_tolerance_m2"]):
                    add("OBJECT_RESIZED", match["canonical_id"],
                        st["source_entity_id"], "area_m2", match["area_m2"],
                        _q((g.get("w") or 0) * (g.get("d") or 0)), basis, "WARNING")
        for key, it in sorted(src.items(), key=lambda kv: str(kv[1]["canonical_id"])):
            if key not in used:
                add("OBJECT_REMOVED", it["canonical_id"], None,
                    severity="WARNING", basis="UNMATCHED")

    src_lv = {round(_q(l["elevation"]), 3): l for l in ex["levels"]}
    st_lv = _staged(staging, "level")
    for lv in st_lv:
        e = round(_q(lv["geometry"]["elevation"]), 3)
        if e not in src_lv:
            add("LEVEL_CHANGED", None, lv["source_entity_id"], "elevation", None, e,
                "UNMATCHED", "WARNING")
    for e in staging["entities"]:
        if e.get("support") in ("UNSUPPORTED", "PRESERVED_OPAQUE"):
            add("UNSUPPORTED_EXTERNAL_OBJECT", None, e["source_entity_id"],
                "entity_type", None, e["entity_type"], "UNMATCHED", "INFO",
                "UNSUPPORTED_ENTITY")

    conflicts = _conflicts(project, staging, ex)
    diffs.sort(key=lambda d: (str(d["type"]), str(d["canonical_id"]),
                              str(d["source_entity_id"]), str(d["field"])))
    if project.get("model_hash") != before:
        raise RuntimeError("the diff engine changed the project")
    return {"valid": True, "issues": [], "diff": {
        "schema": SCHEMA, "import_id": staging["import_id"],
        "target_model_hash": project.get("model_hash"),
        "target_revision_id": project.get("current_revision"),
        "source_file_hash": staging["source"]["file_hash"],
        "entries": diffs, "count": len(diffs),
        "by_type": {t: len([d for d in diffs if d["type"] == t])
                    for t in SPEC["diff_types"]},
        "conflicts": conflicts,
        "blocking_conflicts": [c for c in conflicts if c["blocking"]],
        "writes_to_model": False}}


def _conflicts(project, staging, ex):
    out = []

    def add(cls, subject, msg):
        out.append({"conflict": cls, "subject": subject, "message": msg,
                    "blocking": cls in SPEC["blocking_conflicts"]})
    gids = {}
    for e in staging["entities"]:
        g = e.get("external_global_id")
        if not g:
            continue
        if g in gids:
            add("DUPLICATE_EXTERNAL_ID", g, "the same GlobalId appears more than once")
        gids[g] = e["source_entity_id"]
    if staging["bim_schema"] not in SPEC["readable_schemas"]:
        add("SCHEMA_CONFLICT", staging["bim_schema"], "the schema is not readable")
    if not staging["units"].get("length"):
        add("UNIT_CONFLICT", "length", "no length unit was declared")
    for e in staging["entities"]:
        if e.get("canonical_kind") in ("door", "window") \
                and e.get("host_basis") == "UNRESOLVED":
            add("HOST_CONFLICT", e["source_entity_id"],
                "the opening has no resolvable host wall")
        if e.get("world") is None and e.get("canonical_kind") in (
                "wall", "door", "window", "space", "slab"):
            add("PLACEMENT_CONFLICT", e["source_entity_id"],
                "the placement could not be resolved to project world coordinates")
    return out


def import_proposals(diff, staging):
    """يحوّل الفروق إلى مقترحات مُصنَّفة. كل مقترح يبدأ PENDING ولا يكتب شيئاً."""
    props = []
    blocked = bool(diff.get("blocking_conflicts"))
    for d in diff["entries"]:
        if d["type"] == "UNSUPPORTED_EXTERNAL_OBJECT":
            state = "BLOCKED"
        elif blocked:
            state = "BLOCKED"
        elif d["mapping_basis"] == "UNMATCHED" and d["type"] in (
                "OBJECT_ADDED", "OBJECT_REMOVED", "LEVEL_CHANGED"):
            state = "BLOCKED"
        else:
            state = "PENDING"
        p = {"proposal_id": None, "state": state,
             "change_type": d["type"], "canonical_id": d["canonical_id"],
             "authoring_id": d.get("authoring_id"),
             "source_entity_id": d["source_entity_id"], "field": d["field"],
             "old_value": d["old_value"], "proposed_value": d["proposed_value"],
             "mapping_basis": d["mapping_basis"], "severity": d["severity"],
             "loss": d["loss"], "writes_to_model": False,
             "blocked_reason": ("an unmatched or unsupported change cannot be applied "
                                "automatically; it needs explicit reconciliation")
                               if state == "BLOCKED" else None}
        p["proposal_id"] = "bimprop_" + _sha16(
            {k: p[k] for k in ("change_type", "canonical_id", "source_entity_id",
                               "field", "proposed_value")})
        props.append(p)
    props.sort(key=lambda p: p["proposal_id"])
    return {"schema": SCHEMA, "import_id": diff["import_id"],
            "target_model_hash": diff["target_model_hash"],
            "target_revision_id": diff["target_revision_id"],
            "proposals": props, "count": len(props),
            "by_state": {s: len([p for p in props if p["state"] == s])
                         for s in SPEC["proposal_states"]},
            "writes_to_model": False,
            "note": "no pending proposal writes to the model; acceptance only prepares "
                    "an authoring command."}


def set_proposal_state(proposal_set, proposal_id, state):
    """قبول أو رفض مقترح. مقترح محجوب لا يُقبَل بالضغط عليه."""
    if state not in ("ACCEPTED", "REJECTED"):
        return {"valid": False, "issues": [issue("BIM_RELATIONSHIP_INVALID", "ERROR",
                proposal_id, "unknown proposal state")], "proposals": proposal_set}
    out = json.loads(json.dumps(proposal_set))
    found = False
    for p in out["proposals"]:
        if p["proposal_id"] != proposal_id:
            continue
        found = True
        if p["state"] == "BLOCKED":
            return {"valid": False, "issues": [issue("BIM_AMBIGUOUS_MAPPING", "ERROR",
                    proposal_id, "a blocked proposal cannot be accepted or rejected "
                                 "until it is reconciled")], "proposals": proposal_set}
        p["state"] = state
    if not found:
        return {"valid": False, "issues": [issue("BIM_INVALID_REFERENCE", "ERROR",
                proposal_id, "no such proposal")], "proposals": proposal_set}
    out["by_state"] = {s: len([p for p in out["proposals"] if p["state"] == s])
                       for s in SPEC["proposal_states"]}
    return {"valid": True, "issues": [], "proposals": out}


def import_staleness(proposal_set, project):
    """المقترح مثبَّت على مراجعة الهدف. تحرّك النموذج يجعله قديماً لا يُعاد رصفه."""
    stale = (proposal_set.get("target_model_hash") != project.get("model_hash")
             or proposal_set.get("target_revision_id")
             != project.get("current_revision"))
    return {"import_id": proposal_set.get("import_id"),
            "status": "STALE_TARGET_MODEL" if stale else "CURRENT",
            "target_model_hash": proposal_set.get("target_model_hash"),
            "current_model_hash": project.get("model_hash"),
            "auto_rebased": False, "auto_committed": False,
            "requires_rediff": bool(stale),
            "note": "a stale import is never rebased or committed automatically."}


def export_staleness(manifest, project):
    stale = (manifest.get("model_hash") != project.get("model_hash")
             or manifest.get("revision_id") != project.get("current_revision"))
    return {"export_id": manifest.get("export_id"),
            "status": "STALE_SOURCE_MODEL" if stale else "CURRENT",
            "export_revision": manifest.get("revision_id"),
            "current_revision": project.get("current_revision"),
            "auto_deleted": False, "auto_repointed": False}


def commit_import(project, proposal_set, authoring, created_at=None):
    """يودع المقبول عبر مسار التأليف وحده. لا مسار جانبي إلى النموذج."""
    st = import_staleness(proposal_set, project)
    if st["status"] == "STALE_TARGET_MODEL":
        return {"valid": False, "committed": False,
                "issues": [issue("BIM_STALE_TARGET_MODEL", "ERROR",
                                 proposal_set.get("import_id"),
                                 "the target model moved after staging; re-diff is "
                                 "required before any commit")],
                "project": project, "state": "STALE_TARGET_MODEL"}
    accepted = [p for p in proposal_set["proposals"] if p["state"] == "ACCEPTED"]
    if not accepted:
        return {"valid": True, "committed": False, "issues": [],
                "project": project, "state": "PROPOSED",
                "note": "nothing was accepted, so nothing is committed"}
    commands, unsupported = [], []
    for p in accepted:
        cmd = _command_for(p)
        if cmd is None:
            unsupported.append(p["proposal_id"])
        else:
            commands.append(cmd)
    if not commands:
        return {"valid": False, "committed": False,
                "issues": [issue("BIM_AMBIGUOUS_MAPPING", "ERROR", None,
                                 "no accepted proposal maps to an authoring command")],
                "project": project, "state": "BLOCKED",
                "unsupported_proposals": unsupported}
    before_hash = project.get("model_hash")
    before_rev = project.get("current_revision")
    txn = authoring.validate_transaction(project, [json.loads(json.dumps(c))
                                                   for c in commands],
                                         project.get("building_id") or "bld_0")
    res = authoring.commit_transaction(
        project, [json.loads(json.dumps(c)) for c in commands],
        confirm=(txn.get("transaction") or {}).get("confirmation_digest"),
        acknowledge_warnings=True, created_at=created_at)
    if not res.get("committed"):
        return {"valid": False, "committed": False,
                "issues": [issue("BIM_RELATIONSHIP_INVALID", "ERROR", None,
                                 "the authoring path refused the accepted changes")]
                          + [issue("BIM_RELATIONSHIP_INVALID", "WARNING", None,
                                   str(i.get("code"))) for i in res.get("issues") or []],
                "project": project, "state": "BLOCKED",
                "authoring_issues": res.get("issues")}
    np = res["project"]
    return {"valid": True, "committed": True, "issues": [],
            "project": np, "state": "COMMITTED",
            "import_id": proposal_set["import_id"],
            "previous_model_hash": before_hash, "previous_revision": before_rev,
            "new_model_hash": np.get("model_hash"),
            "new_revision": np.get("current_revision"),
            "changed_objects": sorted(set(c.get("target_id") for c in commands)),
            "commands": commands,
            "unsupported_proposals": unsupported,
            "via": "AUTHORING_PATH"}


def _command_for(p):
    """يحوّل مقترحاً مقبولاً إلى أمر تأليف معلَن. ما لا يقابله أمر يبقى غير مدعوم."""
    key = "%s.%s" % (p["change_type"], p["field"])
    ctype = COMMAND_MAP.get(key)
    if ctype == "RENAME_SPACE" and p.get("authoring_id"):
        v = p["proposed_value"]
        if not isinstance(v, str) or is_unsafe(v):
            return None
        return {"type": ctype, "target_id": p["authoring_id"],
                "parameters": {"name": v}, "source": COMMAND_SOURCE}
    if p["change_type"] == "OBJECT_RESIZED" and p["field"] == "area_m2":
        return None
    return None


def audit(event, payload=None):
    """سجلّ تدقيق: بصمات لا حمولات، ولا سرّ ولا نصّ خام."""
    if event not in SPEC["audit_events"]:
        return None
    safe = {}
    for k, v in sorted((payload or {}).items()):
        if not safe_key(k):
            continue
        if isinstance(v, (int, float, bool)) or v is None:
            safe[k] = v
        elif isinstance(v, str):
            safe[k] = v if (is_safe_id(v) and len(v) <= 128) else ("sha256:" +
                                                                   _sha256_text(v)[:16])
        else:
            safe[k] = "sha256:" + _sha16(v)
    return {"event": event, "fields": safe, "records_raw_payload": False,
            "records_secret": False}
