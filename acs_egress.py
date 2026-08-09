# -*- coding: utf-8 -*-
# =============================================================================
# acs_egress.py — أساس المخارج والإخلاء (طوبولوجيا فقط).
#
# يجيب فقط عن:
#   ما المخارج المُمثَّلة في النموذج؟ وأي الفراغات تصل إليها عبر رسم الاتصال؟
# ولا يجيب إطلاقاً عن: هل المسار آمن/مطابق/نظامي؟ هل عدد المخارج كافٍ؟ هل
# المسافة ضمن الحد؟ هل الدرج محمي؟ هل يجوز استعمال المصعد؟ — كل ذلك يحتاج
# محرّك قواعد حقيقياً غير موجود في هذه المرحلة.  compliance = NOT_EVALUATED دائماً.
#
# يعيد استخدام رسم التنقّل كما هو (لا تكرار للمحرّك). العلاقات هي مصدر الحقيقة،
# والمخارج تُستخرج من بيانات النموذج الفعلية (نقاط type=exit وأبواب الحدّ الخارجي).
# =============================================================================
import acs_navigation as NAV
import acs_distance as DIST

DESTINATIONS = ("exterior", "site", "protected_area", "unknown")
SOURCES = ("user", "ai_inference", "system_generated", "geometry_inference", "rule")
STATUSES = ("confirmed", "inferred", "unresolved")
USABLE = ("confirmed", "inferred")          # unresolved لا يكون مقصداً أساسياً
_PEOPLE = ("person", "worker", "visitor", "engineer", "child")
PROBE = 0.15
MARGIN = 0.05


def _rect(r):
    rc = r.get("rect")
    if not rc or len(rc) < 4:
        return None
    return [float(v) for v in rc[:4]]


def _space_id(bid, tmpl, room, i):
    return room.get("space_id") or "%s.%s.%s" % (bid, tmpl, room.get("id") or ("sp_%d" % i))


def _footprint(rooms):
    """صندوق إحاطة لمسطح الدور — دليل هندسي حقيقي لتحديد "الخارج"."""
    xs, zs, xe, ze = [], [], [], []
    for r in rooms:
        rc = _rect(r)
        if rc:
            xs.append(rc[0]); zs.append(rc[1]); xe.append(rc[0] + rc[2]); ze.append(rc[1] + rc[3])
    if not xs:
        return None
    return (min(xs), min(zs), max(xe), max(ze))


def _probe(rc, edge, off):
    x, z, w, d = rc
    e = str(edge or "N").upper()[:1]
    if e == "N":
        return x + off, z - PROBE
    if e == "S":
        return x + off, z + d + PROBE
    if e == "W":
        return x - PROBE, z + off
    return x + w + PROBE, z + off


def extract_exits(building, relationships, building_id="bld_0"):
    """يستخرج المخارج من بيانات النموذج الفعلية — لا يخترع مخرجاً غير ممثَّل.

    ثلاثة مصادر (بترتيب القوة):
      1) باب معلَّم صراحةً exit=true            → confirmed
      2) باب غير محلول يخرج خارج مسطح الدور     → inferred, destination=exterior
      3) نقطة type=exit بلا باب خارجي مُثبَت    → unresolved, destination=unknown
    """
    exits, seq = [], [0]
    resolved_via = {r.get("via") for r in (relationships or [])
                    if r.get("type") == "DOOR_CONNECTS" and r.get("to")}

    def add(level, space, via, dest, source, status, meta=None):
        seq[0] += 1
        e = {"id": "%s.exit_%d" % (building_id, seq[0]), "type": "exit",
             "building_id": building_id,
             "level_id": "%s.flr_%d" % (building_id, level) if level is not None else None,
             "level": level, "space_id": space, "via": via, "destination": dest,
             "source": source, "status": status}
        if meta:
            e["meta"] = meta
        exits.append(e)

    for tmpl, fdef in (building.get("floors") or {}).items():
        rooms = (fdef or {}).get("rooms") or []
        fp = _footprint(rooms)
        levels = sorted(int(l.get("index", 0)) for l in (building.get("levels") or [])
                        if l.get("template") == tmpl)
        for i, room in enumerate(rooms):
            rc = _rect(room)
            if not rc:
                continue
            sid = _space_id(building_id, tmpl, room, i)
            space_has_exterior = False
            for di, dr in enumerate(room.get("doors") or []):
                via = "%s.door_%d" % (sid, di)
                if dr.get("exit") is True or dr.get("destination"):
                    dest = dr.get("destination") or "exterior"
                    for lv in levels:
                        add(lv, sid, via, dest if dest in DESTINATIONS else "unknown",
                            dr.get("source") or "user", "confirmed", {"basis": "explicit_door_flag"})
                    space_has_exterior = True
                    continue
                if via in resolved_via or not fp:
                    continue                       # باب داخلي مُثبت الطرف الآخر
                px, pz = _probe(rc, dr.get("edge"), float(dr.get("offset") or 0))
                outside = (px < fp[0] - MARGIN or px > fp[2] + MARGIN or
                           pz < fp[1] - MARGIN or pz > fp[3] + MARGIN)
                if outside:
                    for lv in levels:
                        add(lv, sid, via, "exterior", "geometry_inference", "inferred",
                            {"basis": "door_probe_outside_level_footprint"})
                    space_has_exterior = True
                # داخل المسطح ولم يُعرف الطرف الآخر ⇒ ليس دليل خروج، لا نسجّله مخرجاً
            if not space_has_exterior:
                for pi, p in enumerate(room.get("points") or []):
                    if str(p.get("type")) != "exit":
                        continue
                    src = "system_generated" if p.get("auto") else "user"
                    for lv in levels:
                        add(lv, sid, "%s.exitpoint_%d" % (sid, pi), "unknown", src, "unresolved",
                            {"basis": "exit_marker_without_proven_exterior_door"})
    return exits


def usable_exits(exits):
    return [e for e in exits if e.get("status") in USABLE]


def _people_in(building, space_id, building_id="bld_0"):
    for tmpl, fdef in (building.get("floors") or {}).items():
        for i, r in enumerate(((fdef or {}).get("rooms") or [])):
            if _space_id(building_id, tmpl, r, i) != space_id:
                continue
            return sum(max(1, int(o.get("count") or 1)) for o in (r.get("objects") or [])
                       if str(o.get("kind") or "").lower() in _PEOPLE)
    return 0


def _characteristics(route):
    tr = route.get("transitions") or []
    verts = [t for t in tr if t.get("type") == "vertical"]
    lv = set()
    for t in verts:
        lv.add(t.get("from_level")); lv.add(t.get("to_level"))
    return {"door_count": sum(1 for t in tr if t.get("type") == "door"),
            "vertical_transition_count": len(verts),
            "uses_stairs": any(t.get("kind") == "stairs" for t in verts),
            "uses_elevator": any(t.get("kind") == "elevator" for t in verts),
            "levels_crossed": max(0, len(lv) - 1) if lv else 0,
            "contains_inferred_edges": route.get("resolution") == "contains_inferred_edges",
            "contains_unresolved_edges": False}


def find_egress(building, relationships, origin, building_id="bld_0"):
    """مسارات مرشّحة إلى المخارج المُمثَّلة. طوبولوجيا فقط — لا تقييم مطابقة."""
    out = {"status": None, "origin": origin, "exit": None, "route": None,
           "alternative_exits": [], "unreachable_exits": [], "resolution": None,
           "distance": None, "distance_status": "NOT_MEASURED",
           "compliance": "NOT_EVALUATED", "selection_basis": "minimum_hops",
           "selection_basis_reason": None, "distance_measurement": None,
           "characteristics": None, "represented_people_count": 0, "reason": None}

    if origin and building_id and not str(origin).startswith(building_id + "."):
        out.update(status="NOT_SUPPORTED_INTER_BUILDING",
                   reason="egress is evaluated within one building only")
        return out

    exits = extract_exits(building, relationships, building_id)
    if not exits:
        out.update(status="NO_EXIT_DEFINED",
                   reason="no exit is represented in the model (none was invented)")
        return out
    ok = usable_exits(exits)
    if not ok:
        out.update(status="UNRESOLVED_EXIT",
                   reason="exit markers exist but their destination is not proven")
        out["unreachable_exits"] = [e["id"] for e in exits]
        return out

    probe = NAV.find_path(building, relationships, origin, origin, building_id)
    if probe["status"] in ("INVALID_SOURCE", "INVALID_TARGET"):
        st = "AMBIGUOUS_ORIGIN" if "ambiguous_level" in str(probe.get("reason")) else "INVALID_ORIGIN"
        out.update(status=st, reason=probe.get("reason"))
        return out

    cands, unreachable = [], []
    for e in ok:
        target = NAV.node_id(e["space_id"], e["level"]) if e.get("level") is not None else e["space_id"]
        r = NAV.find_path(building, relationships, origin, target, building_id)
        if r["status"] == "FOUND":
            cands.append({"exit": e, "route": r, "hops": r["hops"]})
        else:
            unreachable.append({"exit_id": e["id"], "status": r["status"], "reason": r.get("reason")})

    out["unreachable_exits"] = unreachable
    if not cands:
        out.update(status="NO_PATH", reason="NO_PATH_TO_REPRESENTED_EXIT")
        return out

    # --- قياس هندسي إضافي (لا يُنشئ اتصالاً ولا يغيّر الطوبولوجيا) ---
    # نقطة الوجهة هي مرساة باب المخرج نفسه من هندسة النموذج، لا مركز الفراغ.
    rooms_idx = DIST._rooms_index(building, building_id)
    arch = DIST.architecture_of(building, building_id)      # مرّة واحدة لكل المرشّحين
    for c in cands:
        sp, di = DIST._via_door(c["exit"].get("via"))
        dest_pt = DIST.door_anchor(rooms_idx.get(sp), di, arch, sp) if sp in rooms_idx else None
        c["measurement"] = DIST.measure_path(building, c["route"], building_id,
                                             destination_point=dest_pt, arch=arch)

    all_complete = all(c["measurement"]["distance_status"] == "COMPLETE" for c in cands)
    if all_complete:
        # مسموح فقط لأن كل المرشّحين مقيسون بالكامل من هندسة النموذج
        cands.sort(key=lambda c: (c["measurement"]["walking_distance_m"], c["exit"]["id"]))
        selection_basis = "minimum_measured_walking_distance"
        selection_reason = "all candidate routes measured COMPLETE from model geometry"
    else:
        cands.sort(key=lambda c: (c["hops"], c["exit"]["id"]))   # اختيار طوبولوجي مُوثَّق فقط
        selection_basis = "minimum_hops"
        by = {}
        for c in cands:
            st = c["measurement"]["distance_status"]
            if st != "COMPLETE":
                by[st] = by.get(st, 0) + 1
        selection_reason = ("geometric shortest route not claimed: " +
                            ", ".join("%d %s" % (by[k], k) for k in sorted(by)))

    best = cands[0]
    m = best["measurement"]
    out.update(status="FOUND", exit=best["exit"], route=best["route"],
               resolution=best["route"]["resolution"],
               distance=m.get("walking_distance_m"),
               distance_status=m["distance_status"],
               distance_measurement=m,
               selection_basis=selection_basis, selection_basis_reason=selection_reason,
               characteristics=_characteristics(best["route"]),
               represented_people_count=_people_in(building, str(origin).split("@")[0], building_id))
    out["metrics"] = best["route"].get("metrics")
    out["alternative_exits"] = [{"exit_id": c["exit"]["id"], "hops": c["hops"],
                                 "characteristics": _characteristics(c["route"]),
                                 "distance_status": c["measurement"]["distance_status"],
                                 "walking_distance_m": c["measurement"].get("walking_distance_m")}
                                for c in cands[1:]]
    return out


def audit_egress(building, relationships, building_id="bld_0"):
    """جرد اتصال على مستوى المبنى — معلومات طوبولوجية لا نتيجة مطابقة."""
    exits = extract_exits(building, relationships, building_id)
    ok = usable_exits(exits)
    nav = NAV.build_nav_graph(building, relationships, building_id, False)
    starts = [NAV.node_id(e["space_id"], e["level"]) for e in ok
              if NAV.node_id(e["space_id"], e["level"]) in nav["nodes"]]
    seen = set(starts)
    q = list(starts)
    while q:                                    # BFS متعدّد المصادر من المخارج (تمريرة واحدة)
        cur = q.pop(0)
        for nb in nav["adj"].get(cur, []):
            if nb["to"] not in seen:
                seen.add(nb["to"]); q.append(nb["to"])
    total_spaces = len(NAV.known_spaces(building, building_id))
    nodes = list(nav["nodes"].keys())
    reachable = [n for n in nodes if n in seen]
    return {"spaces": total_spaces, "nav_nodes": len(nodes),
            "exits_total": len(exits),
            "confirmed_exits": sum(1 for e in exits if e["status"] == "confirmed"),
            "inferred_exits": sum(1 for e in exits if e["status"] == "inferred"),
            "unresolved_exits": sum(1 for e in exits if e["status"] == "unresolved"),
            "nodes_with_reachable_exit": len(reachable),
            "nodes_without_reachable_exit": len(nodes) - len(reachable),
            "spaces_without_nav_edges": max(0, total_spaces - len({nav["nodes"][n]["space"] for n in nodes})),
            "compliance": "NOT_EVALUATED"}


def validate_exits(building, exits, building_id="bld_0"):
    """فحوص بنيوية فقط — لا فحص مطابقة هندسية."""
    issues, ids = [], set()
    spaces = NAV.known_spaces(building, building_id)
    levels = {int(l.get("index", 0)) for l in (building.get("levels") or [])}
    seen = set()
    for e in exits or []:
        if e["id"] in ids:
            issues.append("duplicate exit id: %s" % e["id"])
        ids.add(e["id"])
        if e.get("source") not in SOURCES:
            issues.append("[%s] invalid source: %s" % (e["id"], e.get("source")))
        if e.get("source") == "rule":
            issues.append("[%s] source=rule requires real rule evidence (none in this phase)" % e["id"])
        if e.get("status") not in STATUSES:
            issues.append("[%s] invalid status: %s" % (e["id"], e.get("status")))
        if e.get("destination") not in DESTINATIONS:
            issues.append("[%s] invalid destination: %s" % (e["id"], e.get("destination")))
        if e.get("space_id") not in spaces:
            issues.append("[%s] dangling space: %s" % (e["id"], e.get("space_id")))
        if e.get("level") is not None and e["level"] not in levels:
            issues.append("[%s] invalid level: %s" % (e["id"], e.get("level")))
        if not e.get("via"):
            issues.append("[%s] exit without via element" % e["id"])
        if e.get("building_id") != building_id or not str(e.get("space_id")).startswith(building_id + "."):
            issues.append("[%s] exit points to another building" % e["id"])
        key = (e.get("space_id"), e.get("via"), e.get("level"))
        if key in seen:
            issues.append("[%s] duplicate exit definition %s" % (e["id"], str(key)))
        seen.add(key)
    return issues


def egress_summary(result):
    """صياغة واقعية — ممنوع أي وصف سلامة/مطابقة."""
    s = result.get("status")
    if s == "FOUND":
        c = result.get("characteristics") or {}
        head = ("مسار مرشّح إلى مخرج ممثّل في النموذج (%d انتقال، أبواب %d، انتقالات رأسية %d%s) — " % (
                (result.get("route") or {}).get("hops") or 0, c.get("door_count", 0),
                c.get("vertical_transition_count", 0),
                "، يستخدم درجاً" if c.get("uses_stairs") else
                ("، يستخدم مصعداً" if c.get("uses_elevator") else "")))
        if result.get("distance_status") == "COMPLETE" and result.get("distance") is not None:
            return head + ("المسافة الهندسية المقاسة %.2f م من هندسة النموذج، ولم تُقيَّم أي مطابقة."
                           % result["distance"])
        return head + "المسافة الفعلية للمشي لم تُحسب، ولم تُقيَّم أي مطابقة."
    if s == "NO_EXIT_DEFINED":
        return "لا يوجد مخرج ممثّل في النموذج (لم يُختلق أي مخرج)."
    if s == "NO_PATH":
        return "لا يوجد مسار اتصال معروف إلى أي مخرج ممثّل."
    if s == "UNRESOLVED_EXIT":
        return "توجد علامات مخارج لكن وجهتها غير مُثبتة — لا تُعتمد مقصداً."
    return "تعذّر التقييم الطوبولوجي: %s (%s)" % (s, result.get("reason") or "")
