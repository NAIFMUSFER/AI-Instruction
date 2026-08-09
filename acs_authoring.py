# -*- coding: utf-8 -*-
# =============================================================================
# acs_authoring.py — أساس التأليف والتحرير المضبوط: تعديل مضبوط للنموذج فقط.
#
# كل تعديل هندسي أمرٌ مُصنَّف (AuthoringCommand) يمرّ بمسار واحد لا ثاني له:
#   أمر → تطبيع → معاينة على نسخة مرشّحة → تحقّق → جاهز → إيداع صريح → مراجعة جديدة
#
# مبادئ صارمة:
#   • زمن التشغيل يبقى زائلاً، والنموذج الهندسي لا يُعدَّل في مكانه أبداً.
#   • لا setModel ولا writeModel ولا كتابة بمسار حرّ. لا مخرج هروب.
#   • كل إيداع ينتج مراجعة جديدة وسجلّ تدقيق. لا حفظ صامت.
#   • لا إصلاح تلقائي: لا تعارضات تُحلّ، ولا مسارات ميكانيكية تُعاد، ولا إنشاء
#     يُعاد تصميمه، ولا عنصر يُضاف لأجل نظام بناء.
#   • التحقّق يعني تماسك بنية البيانات — لا مطابقة أنظمة ولا سلامة ولا كفاية.
#   • كل معرّف حتميّ: لا وقت ولا عشوائية ولا UUID في أي بصمة.
# =============================================================================
import hashlib
import json
import math
import os

# مصدر واحد للترميز الرقمي القانوني — نفس الرمز الذي تنتجه شيفرة المتصفّح.
import acs_ingest as _ing

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "acs_authoring.json"), "r", encoding="utf-8") as _f:
    SPEC = json.load(_f)

SCHEMA = SPEC["schema"]
VERSION = SPEC["version"]
ENGINE_VERSION = SPEC["compiler_version"]
TRANSACTION_STATES = tuple(SPEC["transaction_states"])
FAILURE_STATES = tuple(SPEC["transaction_failure_states"])
COMMAND_TYPES = tuple(SPEC["command_types"])
IMPLEMENTED = tuple(SPEC["implemented_command_types"])
NOT_IMPLEMENTED = tuple(SPEC["declared_not_implemented"])
FORBIDDEN_TYPES = tuple(SPEC["forbidden_command_types"])
COMMAND_DISCIPLINE = SPEC["command_discipline"]
DISCIPLINES = tuple(SPEC["disciplines"])
SOURCES = tuple(SPEC["command_sources"])
DEFAULT_SOURCE = SPEC["default_command_source"]
CONSTRAINT_KEYS = tuple(SPEC["constraint_keys"])
MUST_NOT_CHANGE = tuple(SPEC["must_not_change_subjects"])
MUST_PRESERVE = tuple(SPEC["must_preserve_subjects"])
HOSTED_STRATEGIES = tuple(SPEC["hosted_element_strategies"])
EDITABILITY = SPEC["field_editability"]
EDITABILITY_CLASSES = tuple(SPEC["editability_classes"])
READ_ONLY_KINDS = tuple(SPEC["read_only_element_kinds"])
ISSUE_CODES = tuple(SPEC["issue_codes"])
ISSUE_SEVERITY = SPEC["issue_severity"]
SEVERITIES = tuple(SPEC["severities"])
COMMIT_POLICY = SPEC["commit_policy"]
DESTRUCTIVE = tuple(SPEC["destructive_command_types"])
LIMITS = SPEC["limits"]
FORBIDDEN_KEYS = tuple(SPEC["forbidden_payload_keys"])
FORBIDDEN_VALUES = tuple(SPEC["forbidden_value_patterns"])
DEPENDENCY_GRAPH = SPEC["dependency_graph"]
DEPENDENCY_ARTIFACTS = tuple(SPEC["dependency_artifacts"])
SNAP_TYPES = tuple(SPEC["snap_types"])
IMPLEMENTED_SNAPS = tuple(SPEC["implemented_snap_types"])
DEFAULT_GRID = float(SPEC["default_grid_m"])
LOCK_REASONS = tuple(SPEC["lock_reasons"])
DERIVED_NS = tuple(SPEC["derived_id_namespaces"])
MAX_COORD = float(LIMITS["max_abs_coordinate_m"])
MIN_DIM = float(LIMITS["min_dimension_m"])
MAX_DIM = float(LIMITS["max_dimension_m"])

NOT_SPECIFIED = "NOT_SPECIFIED"


# ------------------------------------------------------------- أدوات ------
EDGES = ("N", "S", "E", "W")
EDGE_WORDS = {"N": "N", "S": "S", "E": "E", "W": "W",
              "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W"}


def _edge(v):
    """حافّة معلنة فقط. لا يُقتطَع أوّل حرف من نصّ عشوائي: NORTHWEST ليست N."""
    e = _enum(v)
    return EDGE_WORDS.get(e) if e is not None else None


def _enum(v):
    """قيمة تعداد صالحة: نصّ فقط. القوائم والأرقام لا تُكرَه على نصّ."""
    return v.upper() if isinstance(v, str) else None


def _num(v):
    """رقم حقيقي منتهٍ أو None. NaN و ±inf ليست أرقاماً ولا تُمرَّر بصمت."""
    if v is None or isinstance(v, bool):
        return None
    if not isinstance(v, (int, float, str)):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def _q(v):
    return round(float(v), 6) + 0.0


def _canon(o):
    return _ing.canonical_json(o)


def _sha16(o):
    return hashlib.sha256(_canon(o).encode("utf-8")).hexdigest()[:16]


def _copy(v):
    """نسخة عميقة: التأليف لا يشارك أي مرجع مع النموذج القانوني."""
    return json.loads(json.dumps(v)) if isinstance(v, (dict, list)) else v


def severity_of(code):
    return ISSUE_SEVERITY.get(code, "ERROR")


def _issue(code, subject=None, detail=None):
    return {"code": code, "severity": severity_of(code),
            "subject": None if subject is None else str(subject),
            "detail": None if detail is None else str(detail)}


def _sorted_issues(issues):
    rank = {s: i for i, s in enumerate(SEVERITIES)}
    return sorted(issues, key=lambda i: (-rank.get(i["severity"], 0), i["code"],
                                         str(i["subject"]), str(i["detail"])))


def _has_error(issues):
    return any(i["severity"] == "ERROR" for i in issues)


def _result(issues, **extra):
    out = {"valid": not _has_error(issues), "issues": _sorted_issues(list(issues))}
    out.update(extra)
    return out


# ------------------------------------------------------ بصمة النموذج -----
def model_hash(model, scope="building", building_id="bld_0"):
    """بصمة النموذج القانوني — نفس الترميز الرقمي في اللغتين."""
    return hashlib.sha256(_canon({"scope": scope, "building_id": building_id,
                                  "model": model}).encode("utf-8")).hexdigest()


def _short(h):
    return str(h)[:24]


# ------------------------------------------------------------ الأمن ------
def _scan_payload(value, depth=0, path="payload"):
    """مدخل التأليف غير موثوق: مفاتيح تلويث النموذج الأولي، الحمولات النصّية
    التنفيذية، الأعداد غير المنتهية والتداخل المفرط تُرفض قبل أي معالجة."""
    issues = []
    if depth > int(LIMITS["max_nesting_depth"]):
        issues.append(_issue("PAYLOAD_REJECTED", path, "nesting is too deep"))
        return issues
    if isinstance(value, dict):
        if len(value) > int(LIMITS["max_parameter_keys"]):
            issues.append(_issue("PAYLOAD_REJECTED", path, "too many keys"))
        for k in value:
            ks = str(k)
            if ks in FORBIDDEN_KEYS:
                issues.append(_issue("PAYLOAD_REJECTED", ks,
                                     "forbidden key rejected before any processing"))
                continue
            if len(ks) > int(LIMITS["max_string_length"]):
                issues.append(_issue("PAYLOAD_REJECTED", path, "key is too long"))
                continue
            issues.extend(_scan_payload(value[k], depth + 1, path + "." + ks))
    elif isinstance(value, list):
        if len(value) > int(LIMITS["max_parameter_keys"]) * 8:
            issues.append(_issue("PAYLOAD_REJECTED", path, "array is too large"))
        for i, x in enumerate(value):
            issues.extend(_scan_payload(x, depth + 1, "%s[%d]" % (path, i)))
    elif isinstance(value, str):
        if len(value) > int(LIMITS["max_string_length"]):
            issues.append(_issue("PAYLOAD_REJECTED", path, "string is too long"))
        low = value.lower()
        for bad in FORBIDDEN_VALUES:
            if bad.lower() in low:
                issues.append(_issue("PAYLOAD_REJECTED", path,
                                     "value carries an executable or unsafe pattern"))
                break
    elif isinstance(value, bool) or value is None:
        pass
    elif isinstance(value, (int, float)):
        if _num(value) is None:
            issues.append(_issue("INVALID_PARAMETER", path,
                                 "a non-finite number is not a coordinate"))
    else:
        issues.append(_issue("PAYLOAD_REJECTED", path, "unsupported value type"))
    return issues


def _coord_ok(v):
    n = _num(v)
    return n is not None and abs(n) <= MAX_COORD


# ------------------------------------------------- تحديد موضع النموذج ----
def _templates(model):
    return (model.get("floors") or {})


def _rooms_of(model, template):
    fl = _templates(model).get(template) or {}
    return fl.get("rooms") or []


def _level_templates(model):
    out = []
    for lv in (model.get("levels") or []):
        t = lv.get("template")
        if t is not None and t not in out:
            out.append(t)
    return out


def _find_room(model, template, room_id):
    for r in _rooms_of(model, template):
        if str(r.get("id")) == str(room_id):
            return r
    return None


def _all_rooms(model):
    """كل الغرف مع قالبها — مصدر الحقيقة المعماري، لا الجدران المشتقّة."""
    out = []
    for t in sorted(_templates(model).keys()):
        for r in _rooms_of(model, t):
            out.append((t, r))
    return out


def _space_key(building_id, template, room_id):
    return "%s.%s.%s" % (building_id, template, room_id)


def resolve_target(model, target_id, building_id="bld_0"):
    """يحلّ معرّفاً — قانونياً كان أم مشتقّاً — إلى موضعه في النموذج القانوني.

    الجدران والفتحات والبلاطات مشتقّة من مستطيلات الغرف، فالتحرير يقع على
    المصدر لا على المشتقّ. الغموض يُعلَن AMBIGUOUS_TARGET ولا يُخمَّن."""
    tid = target_id if isinstance(target_id, str) and target_id else None
    if tid is None:
        return {"kind": None, "issues": [_issue("INVALID_TARGET", target_id,
                                                "target must be a non-empty string")]}
    for ns in DERIVED_NS:
        if tid.startswith(ns):
            return {"kind": None, "issues": [_issue(
                "INVALID_TARGET", tid,
                "this identifier names a derived projection (%s), not a semantic source; "
                "edit the element it was derived from instead" % ns)]}
    # فتحة مشتقّة: bld_0.<template>.<room>.door_<n>[@level]
    body = tid.split("@")[0]
    parts = body.split(".")
    if len(parts) >= 4 and (parts[-1].startswith("door_") or parts[-1].startswith("window_")):
        kind = "DOOR" if parts[-1].startswith("door_") else "WINDOW"
        idx = parts[-1].split("_")[-1]
        template, room_id = parts[1], ".".join(parts[2:-1])
        room = _find_room(model, template, room_id)
        if room is None:
            return {"kind": None, "issues": [_issue("INVALID_TARGET", tid,
                                                    "the space behind this opening does not exist")]}
        try:
            i = int(idx)
        except ValueError:
            return {"kind": None, "issues": [_issue("INVALID_TARGET", tid,
                                                    "opening index is not a number")]}
        key = "doors" if kind == "DOOR" else "windows"
        lst = room.get(key) or []
        if i < 0 or i >= len(lst):
            return {"kind": None, "issues": [_issue("INVALID_TARGET", tid,
                                                    "opening index is out of range")]}
        return {"kind": kind, "template": template, "room_id": room_id,
                "opening_index": i, "opening_key": key, "issues": []}
    # جدار مشتقّ: bld_0.flr_<i>.wall_<n>
    if len(parts) >= 3 and parts[-1].startswith("wall_"):
        return {"kind": "WALL", "wall_id": tid, "issues": []}
    # فضاء: bld_0.<template>.<room>  أو  <template>.<room>  أو  <room>
    if len(parts) >= 3:
        template, room_id = parts[1], ".".join(parts[2:])
        if _find_room(model, template, room_id) is not None:
            return {"kind": "SPACE", "template": template, "room_id": room_id, "issues": []}
    if len(parts) == 2:
        template, room_id = parts[0], parts[1]
        if _find_room(model, template, room_id) is not None:
            return {"kind": "SPACE", "template": template, "room_id": room_id, "issues": []}
    hits = [(t, r) for t, r in _all_rooms(model) if str(r.get("id")) == tid]
    if len(hits) == 1:
        return {"kind": "SPACE", "template": hits[0][0], "room_id": tid, "issues": []}
    if len(hits) > 1:
        return {"kind": None, "candidates": [_space_key(building_id, t, tid) for t, _ in hits],
                "issues": [_issue("AMBIGUOUS_TARGET", tid,
                                  "the same space id exists on more than one level template")]}
    # مستوى
    for lv in (model.get("levels") or []):
        if tid in (str(lv.get("template")), str(lv.get("name")),
                   "%s.flr_%s" % (building_id, lv.get("index"))):
            return {"kind": "LEVEL", "level_index": lv.get("index"),
                    "template": lv.get("template"), "issues": []}
    if tid in ("site", "SITE"):
        return {"kind": "SITE", "issues": []}
    if tid in ("building", "BUILDING", building_id):
        return {"kind": "BUILDING", "issues": []}
    # جسم دلالي داخل غرفة: <template>.<room>.obj_<n>
    if len(parts) >= 3 and parts[-1].startswith("obj_"):
        # يُقبَل الشكلان: <template>.<room>.obj_<n> و <bid>.<template>.<room>.obj_<n>
        if len(parts) >= 4:
            template, room_id = parts[1], ".".join(parts[2:-1])
        else:
            template, room_id = parts[0], parts[1]
        room = _find_room(model, template, room_id)
        if room is None and len(parts) >= 4:
            template, room_id = parts[0], ".".join(parts[1:-1])
            room = _find_room(model, template, room_id)
        if room is not None:
            try:
                i = int(parts[-1].split("_")[-1])
            except ValueError:
                i = -1
            objs = room.get("objects") or []
            if 0 <= i < len(objs):
                return {"kind": "OBJECT", "template": template, "room_id": room_id,
                        "object_index": i, "issues": []}
        return {"kind": None, "issues": [_issue("INVALID_TARGET", tid,
                                                "the object behind this id does not exist")]}
    return {"kind": None, "issues": [_issue("INVALID_TARGET", tid,
                                            "target does not resolve in the canonical model")]}


# ------------------------------------------------- الجدران المشتقّة ------
def _derived_walls(model, building_id="bld_0"):
    """يبني الجدران المشتقّة عبر مصرّف العمارة نفسه — لا نسخة ثانية من المنطق."""
    try:
        import acs_arch
    except ImportError:                                        # pragma: no cover
        return None
    try:
        return acs_arch.compile_architecture(_copy(model), building_id, None, 0)
    except Exception:                                          # pragma: no cover
        return None


def _wall_source_edges(model, arch, wall_id):
    """يعيد حواف الغرف التي وُلِّد منها هذا الجدار: (template, room_id, edge)."""
    if arch is None:
        return []
    wall = None
    for w in (arch.get("walls") or []):
        if str(w.get("id")) == str(wall_id):
            wall = w
            break
    if wall is None:
        return []
    axis, fixed = wall.get("axis"), _num(wall.get("fixed"))
    u0, u1 = _num(wall.get("u0")), _num(wall.get("u1"))
    lvl = wall.get("level_index")
    if axis is None or fixed is None or u0 is None or u1 is None:
        return []
    templates = {}
    for lv in (model.get("levels") or []):
        templates[lv.get("index")] = lv.get("template")
    template = templates.get(lvl)
    if template is None:
        return []
    out = []
    for r in _rooms_of(model, template):
        rect = r.get("rect")
        if not isinstance(rect, list) or len(rect) != 4:
            continue
        x, z, w, d = [_num(v) for v in rect]
        if None in (x, z, w, d):
            continue
        if axis == "x":                       # جدار ممتدّ على x عند z ثابت
            lo, hi = min(x, x + w), max(x, x + w)
            if abs(z - fixed) < 1e-9 and lo - 1e-9 <= u0 and u1 <= hi + 1e-9:
                out.append((template, str(r.get("id")), "N"))
            if abs((z + d) - fixed) < 1e-9 and lo - 1e-9 <= u0 and u1 <= hi + 1e-9:
                out.append((template, str(r.get("id")), "S"))
        else:                                  # جدار ممتدّ على z عند x ثابت
            lo, hi = min(z, z + d), max(z, z + d)
            if abs(x - fixed) < 1e-9 and lo - 1e-9 <= u0 and u1 <= hi + 1e-9:
                out.append((template, str(r.get("id")), "W"))
            if abs((x + w) - fixed) < 1e-9 and lo - 1e-9 <= u0 and u1 <= hi + 1e-9:
                out.append((template, str(r.get("id")), "E"))
    return out


# ------------------------------------------------------------ الأمر ------
def normalise_command(command, base_revision=None, snap=None, grid_m=None):
    """يطبّع الأمر إلى صورة قانونية واحدة: نفس التعديل الدلالي ينتج نفس البصمة.
    الوقت لا يدخل الهوية إطلاقاً."""
    issues = []
    if not isinstance(command, dict):
        return _result([_issue("INVALID_COMMAND", "command", "command must be an object")],
                       command=None)
    raw = json.dumps(command, ensure_ascii=False, default=str)
    if len(raw.encode("utf-8")) > int(LIMITS["max_payload_bytes"]):
        return _result([_issue("PAYLOAD_REJECTED", "command", "payload is too large")],
                       command=None)
    issues.extend(_scan_payload(command))
    if _has_error(issues):
        return _result(issues, command=None)

    ctype = _enum(command.get("type"))
    if ctype in FORBIDDEN_TYPES:
        return _result([_issue("COMMAND_NOT_ALLOWED", ctype,
                               "there is no arbitrary or path-based write path")],
                       command=None)
    if ctype not in COMMAND_TYPES:
        return _result([_issue("INVALID_COMMAND", command.get("type"),
                               "unknown authoring command type")], command=None)
    if ctype in NOT_IMPLEMENTED:
        return _result([_issue("COMMAND_NOT_IMPLEMENTED", ctype,
                               "declared in the vocabulary but not authored in this phase")],
                       command=None)

    source = _enum(command.get("source")) or DEFAULT_SOURCE
    if source not in SOURCES:
        issues.append(_issue("INVALID_COMMAND", command.get("source"), "unknown command source"))
        source = DEFAULT_SOURCE

    target = command.get("target_id")
    if target is not None and not isinstance(target, str):
        issues.append(_issue("INVALID_TARGET", None, "target must be a string when supplied"))
        target = None

    params = command.get("parameters")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        issues.append(_issue("INVALID_PARAMETER", "parameters", "parameters must be an object"))
        params = {}

    snap_mode = _enum(snap if snap is not None else command.get("snap")) or "NONE"
    if snap_mode not in SNAP_TYPES:
        issues.append(_issue("INVALID_PARAMETER", snap, "unknown snap type"))
        snap_mode = "NONE"
    elif snap_mode not in IMPLEMENTED_SNAPS:
        issues.append(_issue("INVALID_PARAMETER", snap_mode,
                             "this snap type is declared but not implemented in this phase"))
        snap_mode = "NONE"
    grid = _num(grid_m if grid_m is not None else command.get("grid_m"))
    if grid is None or grid <= 0:
        grid = DEFAULT_GRID

    norm = {}
    for k in sorted(params.keys()):
        v = params[k]
        n = _num(v)
        if n is not None and not isinstance(v, bool):
            if snap_mode == "GRID" and k in ("dx", "dz", "dy", "delta_m", "x", "z",
                                             "offset", "w", "d", "width", "height"):
                n = round(n / grid) * grid
            norm[k] = _q(n)
        elif isinstance(v, str):
            norm[k] = v
        else:
            norm[k] = _copy(v)

    cons = command.get("constraints")
    ncons = {}
    if cons is not None:
        if not isinstance(cons, dict):
            issues.append(_issue("INVALID_PARAMETER", "constraints",
                                 "constraints must be an object"))
        else:
            for k in sorted(cons.keys()):
                if k not in CONSTRAINT_KEYS:
                    issues.append(_issue("INVALID_PARAMETER", k, "unknown constraint key"))
                    continue
                v = cons[k]
                if k in ("must_preserve", "must_not_change", "allowed_scope"):
                    if not isinstance(v, list):
                        issues.append(_issue("INVALID_PARAMETER", k,
                                             "constraint must be a list"))
                        continue
                    if len(v) > int(LIMITS["max_constraint_entries"]):
                        issues.append(_issue("INVALID_PARAMETER", k, "too many entries"))
                        continue
                    vals = []
                    for x in v:
                        e = _enum(x)
                        if e is None:
                            issues.append(_issue("INVALID_PARAMETER", k,
                                                 "constraint entries must be strings"))
                            continue
                        if k == "must_not_change" and e not in MUST_NOT_CHANGE:
                            issues.append(_issue("INVALID_PARAMETER", e,
                                                 "unknown must_not_change subject"))
                            continue
                        if k == "must_preserve" and e not in MUST_PRESERVE:
                            issues.append(_issue("INVALID_PARAMETER", e,
                                                 "unknown must_preserve subject"))
                            continue
                        if k == "allowed_scope" and e not in DISCIPLINES:
                            issues.append(_issue("INVALID_PARAMETER", e,
                                                 "unknown scope"))
                            continue
                        vals.append(e)
                    ncons[k] = sorted(set(vals))
                else:
                    n = _num(v)
                    if n is None or n < 0:
                        issues.append(_issue("INVALID_PARAMETER", k,
                                             "max_delta_m must be a finite non-negative number"))
                        continue
                    ncons[k] = _q(n)

    identity = {"type": ctype, "target_id": target, "parameters": norm,
                "constraints": ncons, "base_revision": base_revision
                if base_revision is not None else command.get("base_revision")}
    chash = _sha16(identity)
    out = {"command_id": "cmd:" + chash, "command_hash": chash,
           "type": ctype, "discipline": COMMAND_DISCIPLINE.get(ctype),
           "target_id": target, "parameters": norm, "constraints": ncons,
           "source": source, "actor_id": command.get("actor_id")
           if isinstance(command.get("actor_id"), str) else None,
           "base_revision": identity["base_revision"],
           "created_at": command.get("created_at")
           if isinstance(command.get("created_at"), str) else None,
           "status": "NORMALISED", "snap": snap_mode, "grid_m": _q(grid),
           "writes_to_model": False,
           "note": "a normalised authoring command; identity excludes created_at, "
                   "actor and source so the same semantic edit always hashes the same"}
    return _result(issues, command=out)


def command_hash(command, base_revision=None):
    r = normalise_command(command, base_revision)
    return r["command"]["command_hash"] if r["command"] else None


# ------------------------------------------------------ تطبيق الأوامر ----
def _apply(model, cmd, building_id="bld_0"):
    """ينتج نموذجاً مرشّحاً جديداً. لا يلمس المُدخَل إطلاقاً."""
    issues = []
    candidate = _copy(model)
    changed = []
    dep = []          # متأثّر: تقرير واقعي لا يوجب تأكيداً
    brk = []          # كاسر: عنصر يُحذَف أو يُنقَل تبعاً — يوجب تأكيداً صريحاً
    ctype = cmd["type"]
    params = cmd["parameters"]
    target = cmd["target_id"]

    def bad(code, subj, detail):
        issues.append(_issue(code, subj, detail))
        return _result(issues, candidate=None, changed_paths=[], dependencies=[],
                       dependency_breaking=[])

    def need_num(key, minimum=None, maximum=None):
        v = _num(params.get(key))
        if v is None:
            issues.append(_issue("INVALID_PARAMETER", key,
                                 "a finite number is required"))
            return None
        if abs(v) > MAX_COORD:
            issues.append(_issue("COORDINATE_OUT_OF_BOUNDS", key,
                                 "value is outside the declared safe coordinate bound"))
            return None
        if minimum is not None and v < minimum:
            issues.append(_issue("INVALID_PARAMETER", key, "value is below the declared minimum"))
            return None
        if maximum is not None and v > maximum:
            issues.append(_issue("INVALID_PARAMETER", key, "value is above the declared maximum"))
            return None
        return v

    # ------------------------------------------------------------ أقفال --
    locks = (candidate.get("_authoring_locks") or {})
    if ctype not in ("LOCK_ELEMENT", "UNLOCK_ELEMENT") and target and target in locks:
        return bad("TARGET_LOCKED", target,
                   "the element is locked (%s)" % locks[target].get("reason"))

    # ------------------------------------------------------- مستوى/موقع --
    if ctype == "CHANGE_SITE_DIMENSIONS":
        w = need_num("w", MIN_DIM, MAX_DIM)
        d = need_num("d", MIN_DIM, MAX_DIM)
        if w is None or d is None:
            return _result(issues, candidate=None, changed_paths=[], dependencies=[],
                           dependency_breaking=[])
        candidate.setdefault("site", {})
        candidate["site"]["w"] = _q(w)
        candidate["site"]["d"] = _q(d)
        changed = ["site.w", "site.d"]

    elif ctype == "CHANGE_BUILDING_POSITION":
        x = need_num("x")
        z = need_num("z")
        if x is None or z is None:
            return _result(issues, candidate=None, changed_paths=[], dependencies=[],
                           dependency_breaking=[])
        candidate.setdefault("placement", {})
        candidate["placement"]["position"] = {"x": _q(x), "z": _q(z)}
        changed = ["placement.position"]

    elif ctype == "CHANGE_BUILDING_ROTATION":
        r = need_num("rotation_deg")
        if r is None:
            return _result(issues, candidate=None, changed_paths=[], dependencies=[],
                           dependency_breaking=[])
        candidate.setdefault("placement", {})
        candidate["placement"]["rotation_deg"] = _q(((r % 360.0) + 360.0) % 360.0)
        changed = ["placement.rotation_deg"]

    elif ctype == "CHANGE_LEVEL_HEIGHT":
        h = need_num("height_m", float(LIMITS["min_level_height_m"]),
                     float(LIMITS["max_level_height_m"]))
        if h is None:
            return _result(issues, candidate=None, changed_paths=[], dependencies=[],
                           dependency_breaking=[])
        candidate["floor_height"] = _q(h)
        changed = ["floor_height"]

    elif ctype == "ADD_LEVEL":
        levels = candidate.get("levels") or []
        if len(levels) >= int(LIMITS["max_level_count"]):
            return bad("INVALID_PARAMETER", "levels", "the declared level cap is reached")
        template = params.get("template")
        if not isinstance(template, str) or not template:
            return bad("INVALID_PARAMETER", "template", "a template name is required")
        if template not in _templates(candidate):
            return bad("INVALID_TARGET", template,
                       "no floor plate exists for this template; add its spaces first")
        idx = max([int(l.get("index") or 0) for l in levels] or [-1]) + 1
        name = params.get("name") if isinstance(params.get("name"), str) else "level_%d" % idx
        if any(int(l.get("index") or 0) == idx for l in levels):
            return bad("ID_COLLISION", str(idx), "a level with this index already exists")
        candidate["levels"] = levels + [{"index": idx, "name": name, "template": template}]
        changed = ["levels[%d]" % idx]

    elif ctype == "DELETE_LEVEL":
        res = resolve_target(candidate, target, building_id)
        if res["kind"] != "LEVEL":
            issues.extend(res["issues"] or [_issue("INVALID_TARGET", target, "not a level")])
            return _result(issues, candidate=None, changed_paths=[], dependencies=[],
                           dependency_breaking=[])
        levels = candidate.get("levels") or []
        if len(levels) <= 1:
            return bad("DEPENDENCY_CONFLICT", target,
                       "the last remaining level cannot be deleted")
        tmpl = res["template"]
        rooms = _rooms_of(candidate, tmpl)
        others = [l for l in levels if l.get("template") == tmpl
                  and l.get("index") != res["level_index"]]
        if rooms and not others:
            dep = ["%s.%s" % (tmpl, r.get("id")) for r in rooms]
            return bad("LEVEL_NOT_EMPTY", target,
                       "the level still carries %d spaces; delete or move them first"
                       % len(rooms))
        candidate["levels"] = [l for l in levels if l.get("index") != res["level_index"]]
        brk = ["%s.flr_%s" % (building_id, res["level_index"])]
        changed = ["levels"]

    # ------------------------------------------------------------ فضاء ---
    elif ctype in ("RESIZE_SPACE", "RENAME_SPACE", "DELETE_SPACE"):
        res = resolve_target(candidate, target, building_id)
        if res["kind"] != "SPACE":
            issues.extend(res["issues"] or [_issue("INVALID_TARGET", target, "not a space")])
            return _result(issues, candidate=None, changed_paths=[],
                           dependencies=res.get("candidates") or [],
                           dependency_breaking=[])
        t, rid = res["template"], res["room_id"]
        room = _find_room(candidate, t, rid)
        if ctype == "RENAME_SPACE":
            new = params.get("name")
            if not isinstance(new, str) or not new:
                return bad("INVALID_PARAMETER", "name", "a non-empty name is required")
            room["name"] = new
            changed = ["floors.%s.rooms.%s.name" % (t, rid)]
        elif ctype == "RESIZE_SPACE":
            rect = room.get("rect")
            if not isinstance(rect, list) or len(rect) != 4:
                return bad("MODEL_INTEGRITY_FAILURE", target,
                           "the space carries no rectangle to resize")
            x, z, w, d = [_num(v) for v in rect]
            nw = _num(params.get("w"))
            nd = _num(params.get("d"))
            nx = _num(params.get("x"))
            nz = _num(params.get("z"))
            nw = w if nw is None else nw
            nd = d if nd is None else nd
            nx = x if nx is None else nx
            nz = z if nz is None else nz
            for nm, v in (("w", nw), ("d", nd)):
                if v is None or v < MIN_DIM or v > MAX_DIM:
                    return bad("INVALID_PARAMETER", nm,
                               "a space side must be a finite value within the declared bounds")
            for nm, v in (("x", nx), ("z", nz)):
                if not _coord_ok(v):
                    return bad("COORDINATE_OUT_OF_BOUNDS", nm,
                               "value is outside the declared safe coordinate bound")
            old_w, old_d = w, d
            room["rect"] = [_q(nx), _q(nz), _q(nw), _q(nd)]
            changed = ["floors.%s.rooms.%s.rect" % (t, rid)]
            # الفتحات مُعرَّفة بإزاحة على الحافّة: تقلّص الحافّة قد يُخرجها
            for key in ("doors", "windows"):
                for i, op in enumerate(room.get(key) or []):
                    edge = str(op.get("edge") or "N").upper()[:1]
                    span = nw if edge in ("N", "S") else nd
                    off = _num(op.get("offset"))
                    wid = _num(op.get("width")) or 0.0
                    if off is not None and (off - wid / 2.0 < -1e-9
                                            or off + wid / 2.0 > span + 1e-9):
                        issues.append(_issue("OPENING_OUT_OF_RANGE",
                                             "%s.%s.%s_%d" % (t, rid, key[:-1], i),
                                             "the opening no longer fits the resized edge"))
            dep = ["%s.%s" % (t, rid)]
            if old_w != nw or old_d != nd:
                dep.append("space_boundary_changed")
        else:                                                     # DELETE_SPACE
            rooms = _rooms_of(candidate, t)
            deps = []
            for key in ("doors", "windows"):
                for i, _op in enumerate(room.get(key) or []):
                    deps.append("%s.%s.%s_%d" % (t, rid, key[:-1], i))
            for i, o in enumerate(room.get("objects") or []):
                deps.append("%s.%s.obj_%d" % (t, rid, i))
            dep = deps
            brk = list(deps) + ["%s.%s" % (t, rid)]
            candidate["floors"][t]["rooms"] = [r for r in rooms if str(r.get("id")) != rid]
            changed = ["floors.%s.rooms" % t]

    elif ctype == "ADD_SPACE":
        t = params.get("template")
        if not isinstance(t, str) or t not in _templates(candidate):
            return bad("INVALID_TARGET", t, "unknown floor template")
        rect = params.get("rect")
        if not isinstance(rect, list) or len(rect) != 4:
            return bad("INVALID_PARAMETER", "rect",
                       "a rectangle of four finite numbers is required")
        vals = [_num(v) for v in rect]
        if any(v is None for v in vals):
            return bad("INVALID_PARAMETER", "rect", "a rectangle carries a non-finite value")
        if any(abs(v) > MAX_COORD for v in vals):
            return bad("COORDINATE_OUT_OF_BOUNDS", "rect",
                       "value is outside the declared safe coordinate bound")
        if vals[2] < MIN_DIM or vals[3] < MIN_DIM or vals[2] > MAX_DIM or vals[3] > MAX_DIM:
            return bad("INVALID_PARAMETER", "rect", "space sides are outside the declared bounds")
        rooms = _rooms_of(candidate, t)
        if len(rooms) >= int(LIMITS["max_spaces_per_level"]):
            return bad("INVALID_PARAMETER", "rooms", "the declared space cap is reached")
        rid = params.get("id")
        if not isinstance(rid, str) or not rid:
            rid = _new_id("space", t, cmd["command_hash"],
                          [str(r.get("id")) for r in rooms])
        if any(str(r.get("id")) == rid for r in rooms):
            return bad("ID_COLLISION", rid, "a space with this id already exists on this template")
        new_room = {"id": rid, "rect": [_q(v) for v in vals]}
        if isinstance(params.get("name"), str):
            new_room["name"] = params["name"]
        candidate["floors"][t]["rooms"] = rooms + [new_room]
        changed = ["floors.%s.rooms.%s" % (t, rid)]

    # ---------------------------------------------------------- فتحات ----
    elif ctype in ("MOVE_DOOR", "MOVE_WINDOW", "DELETE_DOOR", "DELETE_WINDOW",
                   "CHANGE_DOOR_PROPERTIES", "CHANGE_WINDOW_PROPERTIES"):
        want = "DOOR" if "DOOR" in ctype else "WINDOW"
        res = resolve_target(candidate, target, building_id)
        if res["kind"] != want:
            issues.extend(res["issues"] or [_issue("INVALID_TARGET", target,
                                                   "target is not a %s" % want.lower())])
            return _result(issues, candidate=None, changed_paths=[], dependencies=[],
                           dependency_breaking=[])
        t, rid, i, key = res["template"], res["room_id"], res["opening_index"], res["opening_key"]
        room = _find_room(candidate, t, rid)
        op = room[key][i]
        rect = [_num(v) for v in (room.get("rect") or [0, 0, 0, 0])]
        if ctype.startswith("DELETE"):
            dep = ["%s.%s.%s_%d" % (t, rid, key[:-1], i)]
            brk = list(dep)
            room[key] = [o for j, o in enumerate(room[key]) if j != i]
            changed = ["floors.%s.rooms.%s.%s" % (t, rid, key)]
        elif ctype.startswith("MOVE"):
            edge = _edge(params.get("edge")) if params.get("edge") is not None \
                else _edge(op.get("edge") or "N")
            if edge is None:
                return bad("INVALID_PARAMETER", params.get("edge"),
                           "edge must be exactly one of N, S, E or W")
            off = _num(params.get("offset"))
            if off is None:
                return bad("INVALID_PARAMETER", "offset", "a finite offset is required")
            if not _coord_ok(off):
                return bad("COORDINATE_OUT_OF_BOUNDS", "offset",
                           "value is outside the declared safe coordinate bound")
            span = rect[2] if edge in ("N", "S") else rect[3]
            wid = _num(op.get("width")) or 0.0
            if off - wid / 2.0 < -1e-9 or off + wid / 2.0 > span + 1e-9:
                return bad("OPENING_OUT_OF_RANGE", target,
                           "the opening would extend past its host edge "
                           "(edge span %.3f m, requested centre %.3f m, width %.3f m)"
                           % (span, off, wid))
            op["edge"] = edge
            op["offset"] = _q(off)
            changed = ["floors.%s.rooms.%s.%s[%d]" % (t, rid, key, i)]
        else:                                              # CHANGE_*_PROPERTIES
            allowed = ("width", "height", "sill") if want == "WINDOW" else ("width", "height")
            touched = False
            for k in allowed:
                if k in params:
                    v = _num(params.get(k))
                    if v is None or v < MIN_DIM or v > MAX_DIM:
                        return bad("INVALID_PARAMETER", k,
                                   "a finite dimension within the declared bounds is required")
                    if k == "width":
                        edge = str(op.get("edge") or "N").upper()[:1]
                        span = rect[2] if edge in ("N", "S") else rect[3]
                        off = _num(op.get("offset")) or 0.0
                        if off - v / 2.0 < -1e-9 or off + v / 2.0 > span + 1e-9:
                            return bad("OPENING_OUT_OF_RANGE", target,
                                       "the widened opening would extend past its host edge")
                    op[k] = _q(v)
                    touched = True
            if not touched:
                return bad("INVALID_PARAMETER", "parameters",
                           "no editable opening property was supplied")
            changed = ["floors.%s.rooms.%s.%s[%d]" % (t, rid, key, i)]

    elif ctype in ("ADD_DOOR", "ADD_WINDOW"):
        key = "doors" if ctype == "ADD_DOOR" else "windows"
        res = resolve_target(candidate, target, building_id)
        if res["kind"] != "SPACE":
            issues.extend(res["issues"] or [_issue("HOST_INVALID", target,
                                                   "an opening must be added to a space")])
            return _result(issues, candidate=None, changed_paths=[],
                           dependencies=res.get("candidates") or [],
                           dependency_breaking=[])
        t, rid = res["template"], res["room_id"]
        room = _find_room(candidate, t, rid)
        rect = [_num(v) for v in (room.get("rect") or [0, 0, 0, 0])]
        edge = _edge(params.get("edge"))
        if edge is None:
            return bad("INVALID_PARAMETER", params.get("edge"),
                       "edge must be exactly one of N, S, E or W")
        off = _num(params.get("offset"))
        wid = _num(params.get("width"))
        if off is None or wid is None:
            return bad("INVALID_PARAMETER", "offset/width",
                       "a finite offset and width are required")
        if wid < MIN_DIM or wid > MAX_DIM:
            return bad("INVALID_PARAMETER", "width", "width is outside the declared bounds")
        span = rect[2] if edge in ("N", "S") else rect[3]
        if off - wid / 2.0 < -1e-9 or off + wid / 2.0 > span + 1e-9:
            return bad("OPENING_OUT_OF_RANGE", target,
                       "the opening would extend past its host edge")
        new = {"edge": edge, "offset": _q(off), "width": _q(wid)}
        for k in ("height", "sill"):
            v = _num(params.get(k))
            if v is not None:
                new[k] = _q(v)
        room.setdefault(key, [])
        room[key] = list(room[key]) + [new]
        changed = ["floors.%s.rooms.%s.%s[%d]" % (t, rid, key, len(room[key]) - 1)]

    # ---------------------------------------------------------- جدران ----
    elif ctype == "MOVE_WALL":
        arch = _derived_walls(candidate, building_id)
        edges = _wall_source_edges(candidate, arch, target)
        if not edges:
            return bad("INVALID_TARGET", target,
                       "the wall does not resolve to any space edge in the canonical model")
        delta = _num(params.get("delta_m"))
        if delta is None:
            return bad("INVALID_PARAMETER", "delta_m", "a finite delta is required")
        if not _coord_ok(delta):
            return bad("COORDINATE_OUT_OF_BOUNDS", "delta_m",
                       "value is outside the declared safe coordinate bound")
        strategy = _enum(params.get("hosted_strategy"))
        hosted = []
        for (t, rid, edge) in edges:
            room = _find_room(candidate, t, rid)
            for key in ("doors", "windows"):
                for i, op in enumerate(room.get(key) or []):
                    if str(op.get("edge") or "N").upper()[:1] == edge:
                        hosted.append((t, rid, key, i, edge))
        if hosted:
            if strategy is None:
                return bad("HOSTED_STRATEGY_REQUIRED", target,
                           "%d hosted openings ride this wall; state a hosted strategy "
                           "instead of letting the engine choose" % len(hosted))
            if strategy not in HOSTED_STRATEGIES:
                return bad("INVALID_PARAMETER", strategy, "unknown hosted element strategy")
            if strategy == "CANCEL_IF_HOSTED":
                dep = ["%s.%s.%s_%d" % (t, rid, key[:-1], i)
                       for (t, rid, key, i, _e) in hosted]
                return bad("DEPENDENCY_CONFLICT", target,
                           "the wall carries %d hosted openings and the chosen strategy "
                           "is to cancel rather than move them" % len(hosted))
        for (t, rid, edge) in edges:
            room = _find_room(candidate, t, rid)
            rect = [_num(v) for v in (room.get("rect") or [0, 0, 0, 0])]
            x, z, w, d = rect
            if edge == "N":
                z, d = z + delta, d - delta
            elif edge == "S":
                d = d + delta
            elif edge == "W":
                x, w = x + delta, w - delta
            else:                                                  # E
                w = w + delta
            if w < MIN_DIM or d < MIN_DIM:
                return bad("INVALID_PARAMETER", "delta_m",
                           "the move would collapse space %s below the minimum dimension" % rid)
            if not (_coord_ok(x) and _coord_ok(z)):
                return bad("COORDINATE_OUT_OF_BOUNDS", "delta_m",
                           "the move would place a space outside the declared bound")
            room["rect"] = [_q(x), _q(z), _q(w), _q(d)]
            changed.append("floors.%s.rooms.%s.rect" % (t, rid))
        if hosted and strategy == "KEEP_WORLD_POSITION":
            for (t, rid, key, i, edge) in hosted:
                room = _find_room(candidate, t, rid)
                op = room[key][i]
                off = _num(op.get("offset"))
                if off is None:
                    continue
                # الحافّة تحرّكت على محورها الطولي فقط عند N/W؛ الإزاحة تُصحَّح
                shift = delta if edge in ("N", "W") else 0.0
                new_off = off - shift
                span = _num(room["rect"][2]) if edge in ("N", "S") else _num(room["rect"][3])
                wid = _num(op.get("width")) or 0.0
                if new_off - wid / 2.0 < -1e-9 or new_off + wid / 2.0 > span + 1e-9:
                    return bad("OPENING_OUT_OF_RANGE",
                               "%s.%s.%s_%d" % (t, rid, key[:-1], i),
                               "keeping the world position would push the opening past "
                               "its host edge; choose another strategy or a smaller move")
                op["offset"] = _q(new_off)
                changed.append("floors.%s.rooms.%s.%s[%d]" % (t, rid, key, i))
        dep = ["%s.%s.%s_%d" % (t, rid, key[:-1], i) for (t, rid, key, i, _e) in hosted]
        brk = list(dep)

    elif ctype == "ADD_WALL":
        # الجدران مشتقّة من حواف الفضاءات، فإضافة جدار حرّ تعني إضافة فضاء
        return bad("COMMAND_NOT_ALLOWED", "ADD_WALL",
                   "walls are derived from space rectangles in this model; add or resize a "
                   "space instead of authoring a free-standing wall, so the derived geometry "
                   "and the semantic source cannot disagree")

    elif ctype == "DELETE_WALL":
        arch = _derived_walls(candidate, building_id)
        edges = _wall_source_edges(candidate, arch, target)
        if not edges:
            return bad("INVALID_TARGET", target,
                       "the wall does not resolve to any space edge in the canonical model")
        deps = []
        for (t, rid, edge) in edges:
            room = _find_room(candidate, t, rid)
            for key in ("doors", "windows"):
                for i, op in enumerate(room.get(key) or []):
                    if str(op.get("edge") or "N").upper()[:1] == edge:
                        deps.append("%s.%s.%s_%d" % (t, rid, key[:-1], i))
            deps.append("%s.%s" % (t, rid))
        return bad("DEPENDENCY_CONFLICT", target,
                   "this wall is generated by %d space edge(s) and cannot be deleted on its "
                   "own without orphaning them; delete or resize the space instead"
                   % len(edges))

    # ----------------------------------------------------------- أجسام ---
    elif ctype in ("MOVE_OBJECT", "DELETE_OBJECT", "MOVE_STAIR", "DELETE_STAIR"):
        res = resolve_target(candidate, target, building_id)
        if res["kind"] != "OBJECT":
            issues.extend(res["issues"] or [_issue("INVALID_TARGET", target, "not an object")])
            return _result(issues, candidate=None, changed_paths=[], dependencies=[],
                           dependency_breaking=[])
        t, rid, i = res["template"], res["room_id"], res["object_index"]
        room = _find_room(candidate, t, rid)
        obj = (room.get("objects") or [])[i]
        is_stair = str(obj.get("kind") or "").lower() in ("stairs", "stair")
        if ctype.endswith("STAIR") and not is_stair:
            return bad("INVALID_TARGET", target, "the target object is not a stair")
        if ctype.endswith("OBJECT") and is_stair:
            return bad("AUTHORING_SCOPE_VIOLATION", target,
                       "a stair carries vertical connectivity; use the stair commands so the "
                       "downstream effect is reported rather than hidden inside a generic move")
        if ctype.startswith("DELETE"):
            dep = ["%s.%s.obj_%d" % (t, rid, i)] + (["vertical_connectivity"] if is_stair else [])
            brk = ["%s.%s.obj_%d" % (t, rid, i)]
            room["objects"] = [o for j, o in enumerate(room["objects"]) if j != i]
            changed = ["floors.%s.rooms.%s.objects" % (t, rid)]
        else:
            x = need_num("x")
            z = need_num("z")
            if x is None or z is None:
                return _result(issues, candidate=None, changed_paths=[], dependencies=[],
                           dependency_breaking=[])
            obj["x"] = _q(x)
            obj["z"] = _q(z)
            changed = ["floors.%s.rooms.%s.objects[%d]" % (t, rid, i)]
            dep = ["vertical_connectivity"] if is_stair else []

    elif ctype in ("ADD_OBJECT", "ADD_STAIR"):
        res = resolve_target(candidate, target, building_id)
        if res["kind"] != "SPACE":
            issues.extend(res["issues"] or [_issue("INVALID_TARGET", target,
                                                   "an object must be added to a space")])
            return _result(issues, candidate=None, changed_paths=[],
                           dependencies=res.get("candidates") or [],
                           dependency_breaking=[])
        t, rid = res["template"], res["room_id"]
        room = _find_room(candidate, t, rid)
        kind = params.get("kind") if isinstance(params.get("kind"), str) else None
        if ctype == "ADD_STAIR":
            kind = "stairs"
        if not kind:
            return bad("INVALID_PARAMETER", "kind", "a semantic object kind is required")
        x = need_num("x")
        z = need_num("z")
        if x is None or z is None:
            return _result(issues, candidate=None, changed_paths=[], dependencies=[],
                           dependency_breaking=[])
        count = _num(params.get("count"))
        new = {"kind": kind, "x": _q(x), "z": _q(z),
               "count": int(count) if count is not None and count >= 1 else 1}
        room.setdefault("objects", [])
        room["objects"] = list(room["objects"]) + [new]
        changed = ["floors.%s.rooms.%s.objects[%d]" % (t, rid, len(room["objects"]) - 1)]
        dep = ["vertical_connectivity"] if ctype == "ADD_STAIR" else []

    elif ctype == "PROMOTE_VISUAL_OBJECT":
        res = resolve_target(candidate, params.get("space_id") or "", building_id)
        if res["kind"] != "SPACE":
            return bad("INVALID_TARGET", params.get("space_id"),
                       "promotion needs the space that will own the new semantic object")
        kind = params.get("semantic_kind")
        prov = params.get("provenance")
        if not isinstance(kind, str) or not kind:
            return bad("INVALID_PARAMETER", "semantic_kind",
                       "a target semantic kind is required; promotion is never implicit")
        if not isinstance(prov, str) or not prov:
            return bad("INVALID_PARAMETER", "provenance",
                       "promotion must record where the object came from")
        x = need_num("x")
        z = need_num("z")
        if x is None or z is None:
            return _result(issues, candidate=None, changed_paths=[], dependencies=[],
                           dependency_breaking=[])
        t, rid = res["template"], res["room_id"]
        room = _find_room(candidate, t, rid)
        room.setdefault("objects", [])
        room["objects"] = list(room["objects"]) + [
            {"kind": kind, "x": _q(x), "z": _q(z), "count": 1,
             "promoted_from_visual": True, "provenance": prov,
             "source_visual_object_id": target}]
        changed = ["floors.%s.rooms.%s.objects[%d]" % (t, rid, len(room["objects"]) - 1)]

    elif ctype in ("LOCK_ELEMENT", "UNLOCK_ELEMENT"):
        if not isinstance(target, str) or not target:
            return bad("INVALID_TARGET", target, "a target is required")
        lk = dict(candidate.get("_authoring_locks") or {})
        if ctype == "LOCK_ELEMENT":
            if params.get("reason") is None:
                reason = "USER_LOCKED"
            else:
                reason = _enum(params.get("reason"))
                if reason is None:
                    return bad("INVALID_PARAMETER", "reason",
                               "a lock reason must be a string")
            if reason not in LOCK_REASONS:
                return bad("INVALID_PARAMETER", reason, "unknown lock reason")
            lk[target] = {"locked": True, "reason": reason}
        else:
            if target not in lk:
                return bad("INVALID_TARGET", target, "the element is not locked")
            lk.pop(target)
        candidate["_authoring_locks"] = lk
        changed = ["_authoring_locks.%s" % target]

    else:                                                        # pragma: no cover
        return bad("COMMAND_NOT_IMPLEMENTED", ctype, "no applier for this command type")

    return _result(issues, candidate=candidate, changed_paths=sorted(set(changed)),
                   dependencies=sorted(set(dep)), dependency_breaking=sorted(set(brk)))


def _new_id(kind, parent, chash, existing):
    """معرّف جديد حتميّ: من الأب والنوع وبصمة الأمر المطبَّع وتسلسل محسوم.
    لا وقت ولا عشوائية ولا UUID."""
    base = "%s_%s" % (kind, _sha16({"kind": kind, "parent": parent, "cmd": chash})[:8])
    if base not in existing:
        return base
    n = 2
    while "%s_%d" % (base, n) in existing:
        n += 1
    return "%s_%d" % (base, n)


# ---------------------------------------------------------- القيود -------
def _enforce_constraints(cmd, before, after, building_id="bld_0"):
    """القيود جزء من عقد الأمر: التعليمات السالبة لا تُخرَق بصمت."""
    issues = []
    cons = cmd.get("constraints") or {}

    def spaces(m):
        return {"%s.%s" % (t, r.get("id")): _copy(r) for t, r in _all_rooms(m)}

    sb, sa = spaces(before), spaces(after)
    for subject in cons.get("must_not_change") or []:
        if subject == "SPACE_RECT":
            for k in sorted(set(list(sb.keys()) + list(sa.keys()))):
                if json.dumps((sb.get(k) or {}).get("rect")) != \
                   json.dumps((sa.get(k) or {}).get("rect")):
                    issues.append(_issue("CONSTRAINT_VIOLATION", k,
                                         "must_not_change SPACE_RECT was violated"))
        elif subject == "SPACE_AREA":
            for k in sorted(set(list(sb.keys()) + list(sa.keys()))):
                rb = (sb.get(k) or {}).get("rect") or [0, 0, 0, 0]
                ra = (sa.get(k) or {}).get("rect") or [0, 0, 0, 0]
                ab = (_num(rb[2]) or 0) * (_num(rb[3]) or 0)
                aa = (_num(ra[2]) or 0) * (_num(ra[3]) or 0)
                if abs(ab - aa) > 1e-9:
                    issues.append(_issue("CONSTRAINT_VIOLATION", k,
                                         "must_not_change SPACE_AREA was violated"))
        elif subject == "SPACE_NAME":
            for k in sorted(set(list(sb.keys()) + list(sa.keys()))):
                if (sb.get(k) or {}).get("name") != (sa.get(k) or {}).get("name"):
                    issues.append(_issue("CONSTRAINT_VIOLATION", k,
                                         "must_not_change SPACE_NAME was violated"))
        elif subject == "LEVEL_HEIGHT":
            if before.get("floor_height") != after.get("floor_height"):
                issues.append(_issue("CONSTRAINT_VIOLATION", "floor_height",
                                     "must_not_change LEVEL_HEIGHT was violated"))
        elif subject == "SITE":
            if json.dumps(before.get("site"), sort_keys=True) != \
               json.dumps(after.get("site"), sort_keys=True):
                issues.append(_issue("CONSTRAINT_VIOLATION", "site",
                                     "must_not_change SITE was violated"))
        elif subject == "BUILDING_TRANSFORM":
            if json.dumps(before.get("placement"), sort_keys=True) != \
               json.dumps(after.get("placement"), sort_keys=True):
                issues.append(_issue("CONSTRAINT_VIOLATION", "placement",
                                     "must_not_change BUILDING_TRANSFORM was violated"))
        elif subject in ("DOOR_COUNT", "WINDOW_COUNT", "OBJECT_COUNT"):
            key = {"DOOR_COUNT": "doors", "WINDOW_COUNT": "windows",
                   "OBJECT_COUNT": "objects"}[subject]
            cb = sum(len(r.get(key) or []) for _t, r in _all_rooms(before))
            ca = sum(len(r.get(key) or []) for _t, r in _all_rooms(after))
            if cb != ca:
                issues.append(_issue("CONSTRAINT_VIOLATION", key,
                                     "must_not_change %s was violated (%d -> %d)"
                                     % (subject, cb, ca)))
        elif subject == "LEVEL_COUNT":
            if len(before.get("levels") or []) != len(after.get("levels") or []):
                issues.append(_issue("CONSTRAINT_VIOLATION", "levels",
                                     "must_not_change LEVEL_COUNT was violated"))
        elif subject == "SPACE_COUNT":
            if len(sb) != len(sa):
                issues.append(_issue("CONSTRAINT_VIOLATION", "spaces",
                                     "must_not_change SPACE_COUNT was violated"))

    for subject in cons.get("must_preserve") or []:
        if subject == "HOSTED_OPENINGS":
            for k in sorted(sb.keys()):
                for key in ("doors", "windows"):
                    if len((sb[k].get(key) or [])) != len(((sa.get(k) or {}).get(key) or [])):
                        issues.append(_issue("CONSTRAINT_VIOLATION", k,
                                             "must_preserve HOSTED_OPENINGS was violated"))
        elif subject == "SPACE_IDS":
            if sorted(sb.keys()) != sorted(sa.keys()):
                issues.append(_issue("CONSTRAINT_VIOLATION", "space_ids",
                                     "must_preserve SPACE_IDS was violated"))
        elif subject == "STAIR_COUNT":
            def stairs(m):
                return sum(1 for _t, r in _all_rooms(m)
                           for o in (r.get("objects") or [])
                           if str(o.get("kind") or "").lower() in ("stairs", "stair"))
            if stairs(before) != stairs(after):
                issues.append(_issue("CONSTRAINT_VIOLATION", "stairs",
                                     "must_preserve STAIR_COUNT was violated"))
        elif subject == "OBJECT_IDS":
            def objs(m):
                return sorted("%s.%s.obj_%d" % (t, r.get("id"), i)
                              for t, r in _all_rooms(m)
                              for i, _o in enumerate(r.get("objects") or []))
            if objs(before) != objs(after):
                issues.append(_issue("CONSTRAINT_VIOLATION", "objects",
                                     "must_preserve OBJECT_IDS was violated"))
        elif subject == "SPACE_ADJACENCY":
            def adj(m):
                out = []
                for t, r in _all_rooms(m):
                    rect = [_num(v) for v in (r.get("rect") or [0, 0, 0, 0])]
                    out.append("%s.%s:%s" % (t, r.get("id"), json.dumps(rect)))
                return sorted(out)
            if adj(before) != adj(after):
                issues.append(_issue("CONSTRAINT_VIOLATION", "adjacency",
                                     "must_preserve SPACE_ADJACENCY was violated"))

    md = cons.get("max_delta_m")
    if md is not None:
        worst = 0.0
        for k in sorted(set(list(sb.keys()) + list(sa.keys()))):
            rb = (sb.get(k) or {}).get("rect") or [0, 0, 0, 0]
            ra = (sa.get(k) or {}).get("rect") or [0, 0, 0, 0]
            for i in range(4):
                worst = max(worst, abs((_num(ra[i]) or 0) - (_num(rb[i]) or 0)))
        if worst > md + 1e-9:
            issues.append(_issue("CONSTRAINT_VIOLATION", "max_delta_m",
                                 "the edit moved geometry by %.3f m, beyond the stated "
                                 "maximum of %.3f m" % (worst, md)))

    scope = cons.get("allowed_scope")
    if scope and cmd.get("discipline") not in scope:
        issues.append(_issue("AUTHORING_SCOPE_VIOLATION", cmd.get("discipline"),
                             "the command discipline is outside the allowed scope"))
    return issues


# ------------------------------------------------ تماسك النموذج ---------
def validate_model_integrity(model, building_id="bld_0"):
    """تماسك بنيوي فقط — ليس مطابقة أنظمة ولا سلامة ولا كفاية."""
    issues = []
    if not isinstance(model, dict):
        return _result([_issue("MODEL_INTEGRITY_FAILURE", "model", "model must be an object")])
    levels = model.get("levels")
    if not isinstance(levels, list) or not levels:
        issues.append(_issue("MODEL_INTEGRITY_FAILURE", "levels",
                             "a model must carry at least one level"))
        levels = []
    seen_idx = set()
    for lv in levels:
        if not isinstance(lv, dict):
            issues.append(_issue("MODEL_INTEGRITY_FAILURE", "levels", "a level must be an object"))
            continue
        i = lv.get("index")
        if i in seen_idx:
            issues.append(_issue("ID_COLLISION", str(i), "duplicate level index"))
        seen_idx.add(i)
        if lv.get("template") not in _templates(model):
            issues.append(_issue("MODEL_INTEGRITY_FAILURE", str(lv.get("template")),
                                 "a level references a floor template that does not exist"))
    per_template = {}
    for t, r in _all_rooms(model):
        rid = str(r.get("id") or "")
        if not rid:
            issues.append(_issue("MODEL_INTEGRITY_FAILURE", t, "a space carries no id"))
            continue
        key = "%s.%s" % (t, rid)
        if key in per_template:
            issues.append(_issue("ID_COLLISION", key, "duplicate space id on one template"))
        rect = r.get("rect")
        if not isinstance(rect, list) or len(rect) != 4:
            issues.append(_issue("MODEL_INTEGRITY_FAILURE", key,
                                 "a space carries no valid rectangle"))
            per_template[key] = None
            continue
        vals = [_num(v) for v in rect]
        if any(v is None for v in vals):
            issues.append(_issue("MODEL_INTEGRITY_FAILURE", key,
                                 "a space rectangle carries a non-finite value"))
            per_template[key] = None
            continue
        if vals[2] <= 0 or vals[3] <= 0:
            issues.append(_issue("MODEL_INTEGRITY_FAILURE", key,
                                 "a space side is zero or negative"))
        if any(abs(v) > MAX_COORD for v in vals):
            issues.append(_issue("COORDINATE_OUT_OF_BOUNDS", key,
                                 "a space rectangle is outside the declared safe bound"))
        per_template[key] = (t, vals)
        for k in ("doors", "windows"):
            for i, op in enumerate(r.get(k) or []):
                if not isinstance(op, dict):
                    issues.append(_issue("MODEL_INTEGRITY_FAILURE", key,
                                         "an opening record is not an object"))
                    continue
                edge = str(op.get("edge") or "N").upper()[:1]
                if edge not in ("N", "S", "E", "W"):
                    issues.append(_issue("HOST_INVALID", "%s.%s_%d" % (key, k[:-1], i),
                                         "the opening names no valid host edge"))
                    continue
                span = vals[2] if edge in ("N", "S") else vals[3]
                off = _num(op.get("offset"))
                wid = _num(op.get("width")) or 0.0
                if off is None:
                    issues.append(_issue("HOST_INVALID", "%s.%s_%d" % (key, k[:-1], i),
                                         "the opening carries no finite offset"))
                    continue
                if off - wid / 2.0 < -1e-9 or off + wid / 2.0 > span + 1e-9:
                    issues.append(_issue("OPENING_OUT_OF_RANGE",
                                         "%s.%s_%d" % (key, k[:-1], i),
                                         "the opening does not fit its host edge"))
        for i, o in enumerate(r.get("objects") or []):
            if not isinstance(o, dict) or not o.get("kind"):
                issues.append(_issue("MODEL_INTEGRITY_FAILURE", "%s.obj_%d" % (key, i),
                                     "a semantic object carries no kind"))
    # تداخل الفضاءات على نفس القالب — تماسك بنيوي، لا حكم تصميمي
    by_t = {}
    for key, v in per_template.items():
        if not v:
            continue
        by_t.setdefault(v[0], []).append((key, v[1]))
    for t in sorted(by_t.keys()):
        items = sorted(by_t[t])
        for a in range(len(items)):
            for b in range(a + 1, len(items)):
                (ka, ra), (kb, rb) = items[a], items[b]
                if (ra[0] < rb[0] + rb[2] - 1e-9 and rb[0] < ra[0] + ra[2] - 1e-9 and
                        ra[1] < rb[1] + rb[3] - 1e-9 and rb[1] < ra[1] + ra[3] - 1e-9):
                    issues.append(_issue("SPACE_OVERLAP", "%s | %s" % (ka, kb),
                                         "two spaces on the same template overlap"))
    site = model.get("site")
    if site is not None:
        for k in ("w", "d"):
            v = _num((site or {}).get(k))
            if v is None or v <= 0:
                issues.append(_issue("MODEL_INTEGRITY_FAILURE", "site.%s" % k,
                                     "the site dimension is missing or not positive"))
    return _result(issues, checked="structural coherence only; this is not a code, safety, "
                                   "structural, MEP or fire compliance statement",
                   compliance="NOT_EVALUATED")


# -------------------------------------------------------- الاعتماديات ----
def dependency_impact(command, model, building_id="bld_0"):
    """تقرير اعتماديات واقعي: ماذا قد يتأثّر. لا توصية هندسية ولا حكم."""
    n = normalise_command(command)
    if not n["valid"] or n["command"] is None:
        return _result(n["issues"], impact=None)
    cmd = n["command"]
    arts = DEPENDENCY_GRAPH.get(cmd["type"], [])
    a = _apply(model, cmd, building_id)
    affected = a.get("dependencies") or []
    detail = []
    res = resolve_target(model, cmd["target_id"], building_id) if cmd["target_id"] else {"kind": None}
    if res.get("kind") == "SPACE":
        room = _find_room(model, res["template"], res["room_id"])
        for key in ("doors", "windows"):
            for i, _op in enumerate((room or {}).get(key) or []):
                detail.append("%s.%s.%s_%d" % (res["template"], res["room_id"], key[:-1], i))
        for i, _o in enumerate((room or {}).get("objects") or []):
            detail.append("%s.%s.obj_%d" % (res["template"], res["room_id"], i))
    return _result([], impact={
        "command_type": cmd["type"],
        "discipline": cmd["discipline"],
        "invalidates": list(arts),
        "not_invalidated": [x for x in DEPENDENCY_ARTIFACTS if x not in arts],
        "affected_element_ids": sorted(set(affected + detail)),
        "affected_count": len(sorted(set(affected + detail))),
        "structure_mutated": False, "mep_mutated": False, "fls_mutated": False,
        "note": "a factual dependency report. Nothing here is an engineering recommendation, "
                "and no structural, MEP or fire/life-safety element is moved, rerouted or "
                "redesigned by an architectural edit."})


# ------------------------------------------------------------ المعاينة ---
def preview_command(model, command, base_revision=None, building_id="bld_0",
                    snap=None, grid_m=None):
    """معاينة على نسخة مرشّحة. النموذج القانوني يبقى كما هو حرفاً بحرف."""
    before_hash = model_hash(model, "building", building_id)
    n = normalise_command(command, base_revision, snap, grid_m)
    if not n["valid"] or n["command"] is None:
        return _result(n["issues"], preview=None, candidate=None,
                       base_model_hash=before_hash, state="INVALID_COMMAND")
    cmd = n["command"]
    if cmd["base_revision"] is not None and base_revision is not None \
       and cmd["base_revision"] != base_revision:
        return _result([_issue("STALE_BASE_REVISION", cmd["base_revision"],
                               "the command was authored against a different revision")],
                       preview=None, candidate=None, base_model_hash=before_hash,
                       state="STALE_BASE_REVISION")
    a = _apply(model, cmd, building_id)
    issues = list(n["issues"]) + list(a["issues"])
    if a.get("candidate") is None:
        return _result(issues, preview=None, candidate=None,
                       base_model_hash=before_hash,
                       dependencies=a.get("dependencies") or [],
                       state="REJECTED")
    candidate = a["candidate"]
    issues.extend(_enforce_constraints(cmd, model, candidate, building_id))
    integ = validate_model_integrity(candidate, building_id)
    issues.extend(integ["issues"])
    after_hash = model_hash(candidate, "building", building_id)
    assert model_hash(model, "building", building_id) == before_hash
    preview = {
        "command_id": cmd["command_id"], "command_hash": cmd["command_hash"],
        "base_model_hash": before_hash, "candidate_model_hash": after_hash,
        "changed_paths": a.get("changed_paths") or [],
        "dependencies": a.get("dependencies") or [],
        "dependency_breaking": a.get("dependency_breaking") or [],
        "requires_confirmation": bool(a.get("dependency_breaking"))
        or cmd["type"] in DESTRUCTIVE,
        "model_changed": after_hash != before_hash,
        "preview": True, "committed": False,
        "compliance": "NOT_EVALUATED",
        "note": "a candidate model built from a copy. The canonical engineering model is "
                "unchanged and stays unchanged unless a commit is performed explicitly."}
    state = "PREVIEWED" if not _has_error(issues) else "REJECTED"
    return _result(issues, preview=preview, candidate=candidate,
                   base_model_hash=before_hash, candidate_model_hash=after_hash,
                   state=state)


def cancel_preview(project):
    """إلغاء المعاينة: صفر تغيير هندسي."""
    p = project
    p["authoring"]["pending_commands"] = []
    p["authoring"]["preview"] = None
    p["authoring"]["validation"] = []
    p["authoring"]["transaction_status"] = "IDLE"
    return _result([], state="IDLE", model_hash=p["model_hash"],
                   note="preview cancelled; zero engineering change")


# --------------------------------------------------------- المشروع ------
def create_project(model, building_id="bld_0", source="IMPORT", actor_id=None):
    """يبني مشروعاً: نموذج قانوني + مؤشّر مراجعة + تاريخ ملحق فقط."""
    m = _copy(model)
    h = model_hash(m, "building", building_id)
    rev = "rev:" + _sha16({"parent": None, "model_hash": h, "command": None})
    record = {"revision_id": rev, "parent_revision_id": None, "model_hash": h,
              "command_id": None, "command_hash": None,
              "authoring_source": _enum(source) if _enum(source) in SOURCES else "IMPORT",
              "actor_id": actor_id if isinstance(actor_id, str) else None,
              "created_at": None, "summary": "initial revision",
              "changed_paths": [], "reverts_revision_id": None}
    return {"schema": SCHEMA, "version": VERSION, "engine_version": ENGINE_VERSION,
            "building_id": building_id, "model": m, "model_hash": h,
            "current_revision": rev, "history": [record], "audit_log": [],
            "revision_models": {rev: _copy(m)},
            "authoring": {"base_revision": rev, "working_revision": None,
                          "pending_commands": [], "preview": None, "validation": [],
                          "transaction_status": "IDLE", "history": []},
            "note": "the canonical engineering model and its revision pointer. Transient "
                    "authoring state lives beside the model, never inside it."}


def _project_model(project):
    return project["model"]


def begin_edit(project):
    a = project["authoring"]
    a["transaction_status"] = "DRAFT"
    a["base_revision"] = project["current_revision"]
    a["pending_commands"] = []
    a["preview"] = None
    a["validation"] = []
    return _result([], state="DRAFT", base_revision=a["base_revision"])


def authoring_state(project):
    a = project["authoring"]
    return {"base_revision": a["base_revision"], "working_revision": a["working_revision"],
            "pending_commands": _copy(a["pending_commands"]),
            "preview": _copy(a["preview"]), "validation": _copy(a["validation"]),
            "transaction_status": a["transaction_status"],
            "history": _copy(a["history"]),
            "current_revision": project["current_revision"],
            "model_hash": project["model_hash"],
            "runtime_state_present": False,
            "note": "transient authoring state; it is never serialised into the canonical model"}


# ------------------------------------------------------------ المعاملة ---
def _confirmation_digest(commands, base_revision):
    return _sha16({"commands": [c["command_hash"] for c in commands],
                   "base_revision": base_revision})


def validate_transaction(project, commands, building_id=None):
    """يتحقّق من دفعة كاملة معاً. النتيجة ذرّية: الكلّ أو لا شيء."""
    bid = building_id or project.get("building_id") or "bld_0"
    issues = []
    if not isinstance(commands, list):
        return _result([_issue("INVALID_COMMAND", "commands", "a list of commands is required")],
                       transaction=None, state="INVALID_COMMAND")
    if not commands:
        return _result([_issue("INVALID_COMMAND", "commands", "a transaction needs a command")],
                       transaction=None, state="INVALID_COMMAND")
    if len(commands) > int(LIMITS["max_commands_per_transaction"]):
        return _result([_issue("BATCH_TOO_LARGE", str(len(commands)),
                               "the transaction exceeds the declared command cap of %d"
                               % int(LIMITS["max_commands_per_transaction"]))],
                       transaction=None, state="REJECTED")
    base = project["current_revision"]
    working = _copy(project["model"])
    base_hash = project["model_hash"]
    norm, results, changed, deps, breaks = [], [], [], [], []
    for i, raw in enumerate(commands):
        n = normalise_command(raw, (raw or {}).get("base_revision")
                              if isinstance(raw, dict) else None)
        if not n["valid"] or n["command"] is None:
            results.append({"index": i, "command_id": None, "accepted": False,
                            "issues": n["issues"]})
            issues.extend(n["issues"])
            continue
        cmd = n["command"]
        if cmd["base_revision"] is not None and cmd["base_revision"] != base:
            iss = [_issue("STALE_BASE_REVISION", cmd["base_revision"],
                          "the command was authored against revision %s but the current "
                          "revision is %s" % (cmd["base_revision"], base))]
            results.append({"index": i, "command_id": cmd["command_id"],
                            "accepted": False, "issues": iss})
            issues.extend(iss)
            continue
        a = _apply(working, cmd, bid)
        if a.get("candidate") is None:
            results.append({"index": i, "command_id": cmd["command_id"],
                            "accepted": False, "issues": a["issues"]})
            issues.extend(a["issues"])
            continue
        cons = _enforce_constraints(cmd, working, a["candidate"], bid)
        if cons:
            results.append({"index": i, "command_id": cmd["command_id"],
                            "accepted": False, "issues": _sorted_issues(cons)})
            issues.extend(cons)
            continue
        working = a["candidate"]
        norm.append(cmd)
        changed.extend(a.get("changed_paths") or [])
        deps.extend(a.get("dependencies") or [])
        breaks.extend(a.get("dependency_breaking") or [])
        results.append({"index": i, "command_id": cmd["command_id"], "accepted": True,
                        "issues": a["issues"], "changed_paths": a.get("changed_paths") or []})
        issues.extend(a["issues"])

    integ = validate_model_integrity(working, bid) if norm else {"issues": []}
    issues.extend(integ["issues"])
    cand_hash = model_hash(working, "building", bid) if norm else base_hash
    needs_confirm = any(c["type"] in DESTRUCTIVE for c in norm) or bool(breaks)
    ai = [c for c in norm if c["source"] == "AI_PROPOSAL"]
    txn = {"transaction_id": "txn:" + _sha16({"commands": [c["command_hash"] for c in norm],
                                              "base": base}),
           "base_revision": base, "base_model_hash": base_hash,
           "candidate_model_hash": cand_hash,
           "commands": norm, "command_results": results,
           "changed_paths": sorted(set(changed)),
           "dependencies": sorted(set(deps)),
           "dependency_breaking": sorted(set(breaks)),
           "requires_confirmation": needs_confirm,
           "confirmation_digest": _confirmation_digest(norm, base) if norm else None,
           "contains_ai_proposal": bool(ai),
           "atomic": True,
           "compliance": "NOT_EVALUATED",
           "note": "commit is all-or-nothing. A single failing command leaves the canonical "
                   "model byte-identical."}
    state = "VALIDATED" if (not _has_error(issues) and norm) else "REJECTED"
    if any(i["code"] == "STALE_BASE_REVISION" for i in issues):
        state = "STALE_BASE_REVISION"
    if any(i["code"] == "DEPENDENCY_CONFLICT" for i in issues):
        state = "CONFLICT"
    if any(i["code"] in ("INVALID_COMMAND", "COMMAND_NOT_ALLOWED",
                         "COMMAND_NOT_IMPLEMENTED") for i in issues):
        state = "INVALID_COMMAND"
    return _result(issues, transaction=txn, candidate=working if norm else None,
                   state=state)


def commit_transaction(project, commands, confirm=None, acknowledge_warnings=False,
                       source=None, actor_id=None, created_at=None, building_id=None):
    """الإيداع الصريح الوحيد. يتحقّق من المراجعة، ثمّ من التماسك، ثمّ ينتج
    نموذجاً جديداً ومراجعة جديدة. لا تعديل في المكان إطلاقاً."""
    bid = building_id or project.get("building_id") or "bld_0"
    before_hash = project["model_hash"]
    before_model = _canon(project["model"])
    v = validate_transaction(project, commands, bid)
    issues = list(v["issues"])
    txn = v.get("transaction")
    if not v["valid"] or txn is None or v.get("candidate") is None:
        return _result(issues, committed=False, state=v.get("state") or "REJECTED",
                       revision=project["current_revision"], model_hash=before_hash,
                       transaction=txn,
                       note="rejected; the canonical model is byte-identical")
    if txn["contains_ai_proposal"] and not (isinstance(confirm, str) and confirm):
        issues.append(_issue("AI_COMMIT_NOT_PERMITTED", "AI_PROPOSAL",
                             "an AI-proposed command may never commit automatically; an "
                             "explicit confirmation token is required"))
    if txn["requires_confirmation"]:
        if not (isinstance(confirm, str) and confirm):
            issues.append(_issue("CONFIRMATION_REQUIRED", txn["transaction_id"],
                                 "this transaction is destructive or dependency-breaking "
                                 "and needs an explicit confirmation token"))
        elif confirm != txn["confirmation_digest"]:
            issues.append(_issue("CONFIRMATION_REQUIRED", txn["transaction_id"],
                                 "the confirmation token does not match this transaction"))
    warnings = [i for i in issues if i["severity"] == "WARNING"]
    policy = COMMIT_POLICY.get("warning_policy")
    if warnings and policy == "ALLOW_WITH_EXPLICIT_ACKNOWLEDGEMENT" \
       and not acknowledge_warnings:
        issues.append(_issue("CONFIRMATION_REQUIRED", "warnings",
                             "the declared policy requires warnings to be acknowledged "
                             "explicitly before commit"))
    elif warnings and policy == "BLOCK":
        issues.append(_issue("MODEL_INTEGRITY_FAILURE", "warnings",
                             "the declared policy blocks a commit carrying warnings"))
    if _has_error(issues):
        assert _canon(project["model"]) == before_model
        return _result(issues, committed=False, state="REJECTED",
                       revision=project["current_revision"], model_hash=before_hash,
                       transaction=txn,
                       note="rejected; the canonical model is byte-identical")

    candidate = v["candidate"]
    new_hash = model_hash(candidate, "building", bid)
    parent = project["current_revision"]
    rev = "rev:" + _sha16({"parent": parent, "model_hash": new_hash,
                           "commands": [c["command_hash"] for c in txn["commands"]]})
    if any(r["revision_id"] == rev for r in project["history"]):
        return _result([_issue("ID_COLLISION", rev,
                               "a revision with this deterministic id already exists")],
                       committed=False, state="REJECTED",
                       revision=parent, model_hash=before_hash, transaction=txn)
    record = {"revision_id": rev, "parent_revision_id": parent, "model_hash": new_hash,
              "command_id": txn["commands"][0]["command_id"] if txn["commands"] else None,
              "command_hash": txn["commands"][0]["command_hash"] if txn["commands"] else None,
              "command_ids": [c["command_id"] for c in txn["commands"]],
              "authoring_source": _enum(source) if _enum(source) in SOURCES
              else (txn["commands"][0]["source"] if txn["commands"] else "USER"),
              "actor_id": actor_id if isinstance(actor_id, str) else None,
              "created_at": created_at if isinstance(created_at, str) else None,
              "summary": ", ".join(c["type"] for c in txn["commands"]),
              "changed_paths": txn["changed_paths"], "reverts_revision_id": None}
    # النموذج القديم لا يُعدَّل: تُبنى نسخة جديدة ويُستبدَل المؤشّر
    new_project = dict(project)
    new_project["model"] = candidate
    new_project["model_hash"] = new_hash
    new_project["current_revision"] = rev
    new_project["history"] = list(project["history"]) + [record]
    audit = {"transaction_id": txn["transaction_id"],
             "command_ids": [c["command_id"] for c in txn["commands"]],
             "command_hashes": [c["command_hash"] for c in txn["commands"]],
             "source": record["authoring_source"], "actor_id": record["actor_id"],
             "base_revision": parent, "new_revision": rev,
             "model_hash_before": before_hash, "model_hash_after": new_hash,
             "changed_paths": txn["changed_paths"],
             "validation_summary": {"errors": 0,
                                    "warnings": len(warnings),
                                    "infos": len([i for i in issues
                                                  if i["severity"] == "INFO"])},
             "created_at": created_at if isinstance(created_at, str) else None,
             "confirmation_provided": bool(confirm),
             "warning_acknowledged": bool(acknowledge_warnings),
             "note": "no secret, token or AI reasoning trace is recorded here"}
    new_project["audit_log"] = list(project["audit_log"]) + [audit]
    # لقطة المراجعة: النموذج القديم يبقى قابلاً للعنونة بمراجعته إلى الأبد
    snaps = dict(project.get("revision_models") or {})
    snaps[rev] = _copy(candidate)
    new_project["revision_models"] = snaps
    stale = sorted(set(sum((DEPENDENCY_GRAPH.get(c["type"], []) for c in txn["commands"]), [])))
    new_project["authoring"] = {"base_revision": rev, "working_revision": None,
                                "pending_commands": [], "preview": None,
                                "validation": [], "transaction_status": "IDLE",
                                "history": list(project["authoring"]["history"])
                                + [txn["transaction_id"]]}
    # المشروع الأصل يبقى قابلاً للعنونة تاريخياً كما هو
    assert _canon(project["model"]) == before_model
    return _result(issues, committed=True, state="COMMITTED", project=new_project,
                   revision=rev, parent_revision=parent, model_hash=new_hash,
                   previous_model_hash=before_hash, transaction=txn,
                   stale_artifacts=stale, audit=audit,
                   note="a new revision. The previous model object was not mutated and stays "
                        "addressable through its own hash.")


# --------------------------------------------------- التراجع والإعادة ----
def _invert(project, revision_id, building_id="bld_0"):
    """التراجع مراجعة جديدة تعكس الدلالة، لا حذفاً للتاريخ."""
    hist = project["history"]
    idx = next((i for i, r in enumerate(hist) if r["revision_id"] == revision_id), None)
    if idx is None or idx == 0:
        return None, [_issue("UNDO_TARGET_INVALID", revision_id,
                             "no such revision, or it is the initial revision")]
    return hist[idx - 1]["model_hash"], []


def undo(project, revision_id=None, created_at=None, building_id=None):
    """يعيد النموذج إلى حالة سابقة عبر مراجعة جديدة تُلحَق بالتاريخ."""
    bid = building_id or project.get("building_id") or "bld_0"
    hist = project["history"]
    target = revision_id or project["current_revision"]
    idx = next((i for i, r in enumerate(hist) if r["revision_id"] == target), None)
    if idx is None or idx == 0:
        return _result([_issue("UNDO_TARGET_INVALID", target,
                               "no such revision, or it is the initial revision")],
                       project=None, state="REJECTED",
                       model_hash=project["model_hash"])
    parent_id = hist[idx - 1]["revision_id"]
    restored = _revision_model(project, parent_id, bid)
    if restored is None:
        return _result([_issue("UNDO_TARGET_INVALID", parent_id,
                               "the parent revision model could not be reconstructed")],
                       project=None, state="REJECTED", model_hash=project["model_hash"])
    new_hash = model_hash(restored, "building", bid)
    parent = project["current_revision"]
    rev = "rev:" + _sha16({"parent": parent, "model_hash": new_hash,
                           "reverts": target})
    record = {"revision_id": rev, "parent_revision_id": parent, "model_hash": new_hash,
              "command_id": None, "command_hash": None, "command_ids": [],
              "authoring_source": "SYSTEM_TOOL", "actor_id": None,
              "created_at": created_at if isinstance(created_at, str) else None,
              "summary": "undo of %s" % target,
              "changed_paths": list(hist[idx].get("changed_paths") or []),
              "reverts_revision_id": target}
    np_ = dict(project)
    np_["model"] = restored
    np_["model_hash"] = new_hash
    np_["current_revision"] = rev
    np_["history"] = list(hist) + [record]
    _s = dict(project.get("revision_models") or {}); _s[rev] = _copy(restored)
    np_["revision_models"] = _s
    np_["audit_log"] = list(project["audit_log"]) + [
        {"transaction_id": "txn:undo:" + _sha16({"reverts": target, "parent": parent}),
         "command_ids": [], "command_hashes": [], "source": "SYSTEM_TOOL",
         "actor_id": None, "base_revision": parent, "new_revision": rev,
         "model_hash_before": project["model_hash"], "model_hash_after": new_hash,
         "changed_paths": record["changed_paths"],
         "validation_summary": {"errors": 0, "warnings": 0, "infos": 0},
         "created_at": record["created_at"], "confirmation_provided": True,
         "warning_acknowledged": True,
         "note": "undo is a new forward revision; no history entry was removed"}]
    np_["authoring"] = dict(project["authoring"])
    np_["authoring"]["base_revision"] = rev
    return _result([], project=np_, state="COMMITTED", revision=rev,
                   reverts=target, model_hash=new_hash,
                   history_length=len(np_["history"]),
                   note="undo appended a new revision; nothing was deleted from history")


def redo(project, revision_id=None, created_at=None, building_id=None):
    """الإعادة أيضاً مراجعة جديدة: لا مؤشّر يعود للخلف ولا تاريخ يختفي."""
    bid = building_id or project.get("building_id") or "bld_0"
    hist = project["history"]
    cur = next((r for r in hist if r["revision_id"] == project["current_revision"]), None)
    target = revision_id
    if target is None:
        if cur is None or not cur.get("reverts_revision_id"):
            return _result([_issue("UNDO_TARGET_INVALID", project["current_revision"],
                                   "there is nothing to redo: the current revision is not "
                                   "an undo")], project=None, state="REJECTED",
                           model_hash=project["model_hash"])
        target = cur["reverts_revision_id"]
    restored = _revision_model(project, target, bid)
    if restored is None:
        return _result([_issue("UNDO_TARGET_INVALID", target,
                               "the revision model could not be reconstructed")],
                       project=None, state="REJECTED", model_hash=project["model_hash"])
    new_hash = model_hash(restored, "building", bid)
    parent = project["current_revision"]
    rev = "rev:" + _sha16({"parent": parent, "model_hash": new_hash, "redoes": target})
    record = {"revision_id": rev, "parent_revision_id": parent, "model_hash": new_hash,
              "command_id": None, "command_hash": None, "command_ids": [],
              "authoring_source": "SYSTEM_TOOL", "actor_id": None,
              "created_at": created_at if isinstance(created_at, str) else None,
              "summary": "redo of %s" % target, "changed_paths": [],
              "reverts_revision_id": None, "redoes_revision_id": target}
    np_ = dict(project)
    np_["model"] = restored
    np_["model_hash"] = new_hash
    np_["current_revision"] = rev
    np_["history"] = list(hist) + [record]
    _s = dict(project.get("revision_models") or {}); _s[rev] = _copy(restored)
    np_["revision_models"] = _s
    np_["audit_log"] = list(project["audit_log"])
    np_["authoring"] = dict(project["authoring"])
    np_["authoring"]["base_revision"] = rev
    return _result([], project=np_, state="COMMITTED", revision=rev, redoes=target,
                   model_hash=new_hash, history_length=len(np_["history"]),
                   note="redo appended a new revision; the mutable pointer never moved back")


def _revision_model(project, revision_id, building_id="bld_0"):
    """يعيد بناء نموذج مراجعة من اللقطات المحفوظة."""
    snaps = project.get("revision_models") or {}
    if revision_id in snaps:
        return _copy(snaps[revision_id])
    return None


# ------------------------------------------------------------ الفروق -----
def _flatten(model, prefix=""):
    out = {}

    def walk(v, p):
        if isinstance(v, dict):
            for k in sorted(v.keys()):
                walk(v[k], "%s.%s" % (p, k) if p else str(k))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, "%s[%d]" % (p, i))
        else:
            out[p] = v
    walk(model, prefix)
    return out


def revision_diff(before_model, after_model):
    """فرق مراجعتين: ما أُضيف وما حُذف وما تغيّرت خواصّه."""
    a, b = _flatten(before_model), _flatten(after_model)
    added = sorted(k for k in b if k not in a)
    removed = sorted(k for k in a if k not in b)
    # المقارنة بالترميز الرقمي القانوني نفسه: 0 و 0.0 ليستا تغييراً، وإلا لاختلفت
    # بايثون عن جافاسكربت في قائمة المسارات المتغيّرة دون أي تغيّر حقيقي.
    changed = sorted(k for k in a if k in b and _canon(a[k]) != _canon(b[k]))

    def elements(m):
        return {"%s.%s" % (t, r.get("id")): r for t, r in _all_rooms(m)}
    ea, eb = elements(before_model), elements(after_model)
    return {"added_paths": added, "removed_paths": removed, "changed_paths": changed,
            "added_elements": sorted(k for k in eb if k not in ea),
            "removed_elements": sorted(k for k in ea if k not in eb),
            "changed_elements": sorted(k for k in ea if k in eb
                                       and _canon(ea[k]) != _canon(eb[k])),
            "property_changes": [{"path": k, "before": a[k], "after": b[k]}
                                 for k in changed],
            "counts": {"added": len(added), "removed": len(removed), "changed": len(changed)}}


# ------------------------------------------------ الخواصّ القابلة للتحرير -
def editable_properties(model, target_id, building_id="bld_0"):
    """نموذج خواصّ قابل للتحرير: ليست كل خاصّية معروضة قابلة للتعديل."""
    res = resolve_target(model, target_id, building_id)
    if res.get("kind") is None:
        return _result(res["issues"], properties=None)
    kind = res["kind"]
    fields = []

    def add(name, value, cls, source="model"):
        fields.append({"field": name, "value": value if value is not None else NOT_SPECIFIED,
                       "editability": cls, "source": source,
                       "constraints": _field_constraints(name)})
    if kind == "SPACE":
        room = _find_room(model, res["template"], res["room_id"])
        rect = room.get("rect") or []
        add("space.id", room.get("id"), EDITABILITY["space.id"], "model")
        add("space.name", room.get("name"), EDITABILITY["space.name"], "model")
        add("space.rect", rect, EDITABILITY["space.rect"], "model")
        area = None
        if len(rect) == 4 and _num(rect[2]) is not None and _num(rect[3]) is not None:
            area = _q(_num(rect[2]) * _num(rect[3]))
        add("space.area_m2", area, EDITABILITY["space.area_m2"], "derived")
        add("space.boundary_basis", "rectangle_edges",
            EDITABILITY["space.boundary_basis"], "derived")
        add("space.wall_height_m", room.get("height"),
            EDITABILITY["space.wall_height_m"], "model")
    elif kind in ("DOOR", "WINDOW"):
        room = _find_room(model, res["template"], res["room_id"])
        op = room[res["opening_key"]][res["opening_index"]]
        add("opening.id", target_id, EDITABILITY["opening.id"], "derived")
        add("opening.edge", op.get("edge"), EDITABILITY["opening.edge"], "model")
        add("opening.offset", op.get("offset"), EDITABILITY["opening.offset"], "model")
        add("opening.width_m", op.get("width"), EDITABILITY["opening.width_m"], "model")
        add("opening.height_m", op.get("height"), EDITABILITY["opening.height_m"], "model")
        if kind == "WINDOW":
            add("opening.sill_m", op.get("sill"), EDITABILITY["opening.sill_m"], "model")
        add("opening.host_wall_id", None, EDITABILITY["opening.host_wall_id"], "derived")
        add("opening.clear_width_m", None, EDITABILITY["opening.clear_width_m"], "unknown")
        add("opening.swing_direction", None, EDITABILITY["opening.swing_direction"], "unknown")
    elif kind == "OBJECT":
        room = _find_room(model, res["template"], res["room_id"])
        o = room["objects"][res["object_index"]]
        add("object.kind", o.get("kind"), EDITABILITY["object.kind"], "model")
        add("object.x", o.get("x"), EDITABILITY["object.x"], "model")
        add("object.z", o.get("z"), EDITABILITY["object.z"], "model")
        add("object.count", o.get("count"), EDITABILITY["object.count"], "model")
    elif kind == "LEVEL":
        lv = next(l for l in model["levels"] if l.get("index") == res["level_index"])
        add("level.index", lv.get("index"), EDITABILITY["level.index"], "model")
        add("level.template", lv.get("template"), EDITABILITY["level.template"], "model")
        add("level.name", lv.get("name"), EDITABILITY["level.name"], "model")
        add("level.elevation_m", None, EDITABILITY["level.elevation_m"], "derived")
    elif kind == "SITE":
        site = model.get("site") or {}
        add("site.w", site.get("w"), EDITABILITY["site.w"], "model")
        add("site.d", site.get("d"), EDITABILITY["site.d"], "model")
    elif kind == "BUILDING":
        pl = model.get("placement") or {}
        add("building.position", pl.get("position"), EDITABILITY["building.position"], "model")
        add("building.rotation_deg", pl.get("rotation_deg"),
            EDITABILITY["building.rotation_deg"], "model")
    elif kind == "WALL":
        add("wall.id", target_id, EDITABILITY["wall.id"], "derived")
        add("wall.start", None, EDITABILITY["wall.start"], "derived")
        add("wall.end", None, EDITABILITY["wall.end"], "derived")
        add("wall.length_m", None, EDITABILITY["wall.length_m"], "derived")
        add("wall.axis", None, EDITABILITY["wall.axis"], "derived")
        add("wall.thickness_m", None, EDITABILITY["wall.thickness_m"], "unknown")
        add("wall.exposure", None, EDITABILITY["wall.exposure"], "derived")
    add("model_hash", _short(model_hash(model, "building", building_id)),
        EDITABILITY["model_hash"], "derived")
    add("visual.material", None, EDITABILITY["visual.material"], "presentation")
    locks = model.get("_authoring_locks") or {}
    return _result([], properties={
        "target_id": target_id, "kind": kind,
        "locked": target_id in locks,
        "lock_reason": (locks.get(target_id) or {}).get("reason") if target_id in locks else None,
        "fields": fields,
        "editable_count": len([f for f in fields if f["editability"] == "EDITABLE"]),
        "note": "a DERIVED value changes only by editing its source; a DISPLAY_ONLY value is "
                "presentation and never engineering data; an UNKNOWN value is not stated by "
                "the source and is not invented"})


def _field_constraints(name):
    if name in ("space.rect",):
        return {"min_side_m": MIN_DIM, "max_side_m": MAX_DIM, "max_abs_coordinate_m": MAX_COORD}
    if name in ("opening.width_m", "opening.height_m", "opening.sill_m"):
        return {"min_m": MIN_DIM, "max_m": MAX_DIM}
    if name in ("object.x", "object.z", "building.position"):
        return {"max_abs_coordinate_m": MAX_COORD}
    if name in ("site.w", "site.d"):
        return {"min_m": MIN_DIM, "max_m": MAX_DIM}
    if name == "building.rotation_deg":
        return {"min_deg": 0.0, "max_deg": 360.0}
    return {}


# ------------------------------------------------------- اقتراح الذكاء ---
def propose_command(command, rationale=None, base_revision=None):
    """اقتراح لا إيداع. يمرّ بنفس المخطّط ونفس المطبّع ونفس المتحقّق."""
    n = normalise_command(command, base_revision)
    if not n["valid"] or n["command"] is None:
        return _result(n["issues"], proposal=None, status="REJECTED")
    cmd = dict(n["command"])
    cmd["source"] = "AI_PROPOSAL"
    cmd["status"] = "PENDING"
    ident = {"type": cmd["type"], "target_id": cmd["target_id"],
             "parameters": cmd["parameters"], "constraints": cmd["constraints"],
             "base_revision": cmd["base_revision"]}
    cmd["command_hash"] = _sha16(ident)
    cmd["command_id"] = "cmd:" + cmd["command_hash"]
    return _result([], proposal={
        "status": "PROPOSED_AUTHORING_COMMAND", "committed": False,
        "command": cmd,
        "rationale": rationale if isinstance(rationale, str) else None,
        "requires_explicit_confirmation": True,
        "note": "a proposal is not a commit. It carries no privileged path: the same schema, "
                "normaliser, validator, revision guard and preview apply, and an explicit "
                "confirmation token is required before it may be committed."})


def resolve_nl_target(model, phrase, building_id="bld_0"):
    """حلّ هدف من نصّ طبيعي. التطابق المتعدّد غموض يُعلَن ولا يُخمَّن."""
    if not isinstance(phrase, str) or not phrase.strip():
        return _result([_issue("INVALID_TARGET", phrase, "an empty phrase resolves to nothing")],
                       target=None, candidates=[])
    needle = phrase.strip().lower()
    hits = []
    for t, r in _all_rooms(model):
        rid = str(r.get("id") or "")
        name = str(r.get("name") or "")
        if needle == rid.lower() or needle == name.lower() \
           or needle in rid.lower() or (name and needle in name.lower()):
            hits.append(_space_key(building_id, t, rid))
    hits = sorted(set(hits))
    if not hits:
        return _result([_issue("INVALID_TARGET", phrase,
                               "no space matches this phrase")], target=None, candidates=[])
    if len(hits) > 1:
        return _result([_issue("AMBIGUOUS_TARGET", phrase,
                               "%d spaces match; the caller must choose" % len(hits))],
                       target=None, candidates=hits)
    return _result([], target=hits[0], candidates=hits)


# ------------------------------------------------------ الحفظ والتحميل ---
def serialise_project(project, include_history=True, include_revision_models=False):
    """تسلسل نظيف: نموذج قانوني ومؤشّر مراجعة وبيانات تاريخ. لا حالة تشغيل،
    ولا حالة معاينة، ولا أي شيء زائل."""
    out = {"schema": SCHEMA, "version": VERSION, "engine_version": ENGINE_VERSION,
           "building_id": project.get("building_id"),
           "model": _copy(project["model"]),
           "model_hash": project["model_hash"],
           "current_revision": project["current_revision"]}
    if include_history:
        out["history"] = _copy(project["history"])
        out["audit_log"] = _copy(project["audit_log"])
    if include_revision_models and project.get("revision_models"):
        out["revision_models"] = _copy(project["revision_models"])
    out["note"] = ("the current canonical model and its revision pointer. No runtime state, "
                   "no camera, no selection, no portal state and no preview is serialised.")
    return out


def load_project(payload, building_id=None):
    """يعيد بناء مشروع من تسلسل. حالة زمن التشغيل تبدأ من الصفر دائماً."""
    issues = []
    if not isinstance(payload, dict):
        return _result([_issue("MODEL_INTEGRITY_FAILURE", "payload",
                               "a serialised project must be an object")], project=None)
    model = payload.get("model")
    if not isinstance(model, dict):
        return _result([_issue("MODEL_INTEGRITY_FAILURE", "model",
                               "the payload carries no canonical model")], project=None)
    bid = building_id or payload.get("building_id") or "bld_0"
    h = model_hash(model, "building", bid)
    if payload.get("model_hash") and payload["model_hash"] != h:
        issues.append(_issue("MODEL_INTEGRITY_FAILURE", "model_hash",
                             "the stored hash does not match the stored model"))
    proj = {"schema": SCHEMA, "version": VERSION, "engine_version": ENGINE_VERSION,
            "building_id": bid, "model": _copy(model), "model_hash": h,
            "current_revision": payload.get("current_revision"),
            "history": _copy(payload.get("history") or []),
            "audit_log": _copy(payload.get("audit_log") or []),
            "revision_models": _copy(payload.get("revision_models") or {}),
            "authoring": {"base_revision": payload.get("current_revision"),
                          "working_revision": None, "pending_commands": [],
                          "preview": None, "validation": [],
                          "transaction_status": "IDLE", "history": []},
            "note": "loaded project; runtime state starts fresh and is never restored "
                    "from a saved model"}
    return _result(issues, project=proj, runtime_state_restored=False)


def summary(project):
    m = project["model"]
    return {"schema": SCHEMA, "version": VERSION,
            "building_id": project.get("building_id"),
            "model_hash": _short(project["model_hash"]),
            "current_revision": project["current_revision"],
            "revisions": len(project["history"]),
            "audit_entries": len(project["audit_log"]),
            "levels": len(m.get("levels") or []),
            "spaces": len(_all_rooms(m)),
            "doors": sum(len(r.get("doors") or []) for _t, r in _all_rooms(m)),
            "windows": sum(len(r.get("windows") or []) for _t, r in _all_rooms(m)),
            "objects": sum(len(r.get("objects") or []) for _t, r in _all_rooms(m)),
            "locks": len(m.get("_authoring_locks") or {}),
            "transaction_status": project["authoring"]["transaction_status"],
            "writes_to_model_outside_authoring": False,
            "compliance": "NOT_EVALUATED"}
