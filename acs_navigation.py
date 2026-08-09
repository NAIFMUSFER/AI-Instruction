# -*- coding: utf-8 -*-
# =============================================================================
# acs_navigation.py — أساس التنقّل والمسارات (Circulation / Pathfinding).
#
# يشتقّ "رسم تنقّل" من رسم العلاقات، ثم يجيب عن سؤال واحد فقط:
#   هل يوجد مسار اتصال عبر العلاقات الحالية؟
# ولا يجيب إطلاقاً عن: هل المسار مطابق لكود؟ مسار إخلاء؟ متاح لذوي الإعاقة؟
# آمن؟ ضمن مسافة نظامية؟ — تلك مراحل لاحقة بمحرّك قواعد حقيقي.
#
# قواعد صارمة:
#   • المصدر الوحيد للحواف هو رسم العلاقات — لا قرب هندسي ولا مجسّمات.
#   • SPACE_ADJACENT وحده ليس عبوراً (تجاور ≠ فتحة).
#   • unresolved لا يدخل المسار الأساسي أبداً.
#   • BUILDING_ON_SITE ليست حافة مشي.
#   • لا مسافات ملفّقة: لا طول ممر ولا طول درج ولا مسافة مصعد.
#   • لا أرقام ثقة.
#
# عقدة التنقّل = فراغ على مستوى محدّد:  "<space_id>@<level_index>"
# (القالب الواحد قد يتكرّر على عدّة مستويات، فلا بدّ من تقييد المستوى.)
# =============================================================================
from collections import deque

STATUS = ("FOUND", "NO_PATH", "UNRESOLVED", "INVALID_SOURCE", "INVALID_TARGET",
          "NOT_SUPPORTED_INTER_BUILDING")
RESOLUTION = ("confirmed", "contains_inferred_edges", "unresolved")
TRAVERSABLE_STATUS = ("confirmed", "inferred")     # unresolved مستثنى عمداً


def node_id(space_id, level):
    return "%s@%s" % (space_id, level)


def _levels_for_template(building, tmpl):
    return sorted(int(l.get("index", 0)) for l in (building.get("levels") or [])
                  if l.get("template") == tmpl)


def _level_index_of(building, level_id):
    for l in building.get("levels") or []:
        if l.get("id") == level_id:
            return int(l.get("index", 0))
    if isinstance(level_id, str) and ".flr_" in level_id:
        try:
            return int(level_id.rsplit(".flr_", 1)[1])
        except Exception:
            return None
    return None


def _centroids(building, building_id):
    """مركز كل فراغ من إحداثياته الحقيقية (لقياس تقريبي معلَن، لا مسافة مشي)."""
    out = {}
    for tmpl, fdef in (building.get("floors") or {}).items():
        for i, r in enumerate(((fdef or {}).get("rooms") or [])):
            rect = r.get("rect")
            if not rect or len(rect) < 4:
                continue
            sid = r.get("space_id") or "%s.%s.%s" % (building_id, tmpl, r.get("id") or ("sp_%d" % i))
            x, z, w, d = [float(v) for v in rect[:4]]
            out[sid] = (x + w / 2.0, z + d / 2.0)
    return out


def build_nav_graph(building, relationships, building_id="bld_0", include_unresolved=False):
    """يبني رسم التنقّل من العلاقات فقط. لا يضيف أي اتصال من عنده."""
    nodes, adj, edges = {}, {}, []
    cent = _centroids(building, building_id)

    def ensure(nid, space_id, level):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "space": space_id, "level": level,
                          "centroid": cent.get(space_id)}
            adj[nid] = []
        return nodes[nid]

    def link(a, b, edge):
        edges.append(edge)
        adj[a].append({"to": b, "edge": edge})
        adj[b].append({"to": a, "edge": edge})

    ok = set(TRAVERSABLE_STATUS) | ({"unresolved"} if include_unresolved else set())

    for rel in relationships or []:
        t, st = rel.get("type"), rel.get("status")
        meta = rel.get("meta") or {}
        if t == "DOOR_CONNECTS":
            if st not in ok or not rel.get("from") or not rel.get("to"):
                continue
            tmpl = meta.get("template")
            for lvl in (_levels_for_template(building, tmpl) or []):
                a = node_id(rel["from"], lvl)
                b = node_id(rel["to"], lvl)
                ensure(a, rel["from"], lvl)
                ensure(b, rel["to"], lvl)
                link(a, b, {"type": "door", "via": rel.get("via"), "rel_id": rel.get("id"),
                            "source": rel.get("source"), "status": st, "level": lvl})
        elif t == "VERTICAL_CONNECTS":
            if st not in ok:
                continue
            fs, ts = meta.get("from_space"), meta.get("to_space")
            fl, tl = meta.get("from_level"), meta.get("to_level")
            if fs is None or ts is None or fl is None or tl is None:
                continue
            a, b = node_id(fs, fl), node_id(ts, tl)
            ensure(a, fs, fl)
            ensure(b, ts, tl)
            link(a, b, {"type": "vertical", "kind": meta.get("kind"), "via": rel.get("via"),
                        "rel_id": rel.get("id"), "source": rel.get("source"), "status": st,
                        "from_level": fl, "to_level": tl})
        # SPACE_ADJACENT / LEVEL_CONNECTS / BUILDING_ON_SITE: ليست حواف مشي — تُتجاهل عمداً
    return {"nodes": nodes, "adj": adj, "edges": edges, "building_id": building_id}


def known_spaces(building, building_id="bld_0"):
    out = set()
    for tmpl, fdef in (building.get("floors") or {}).items():
        for i, r in enumerate(((fdef or {}).get("rooms") or [])):
            out.add(r.get("space_id") or "%s.%s.%s" % (building_id, tmpl, r.get("id") or ("sp_%d" % i)))
    return out


def _resolve(nav, ref, spaces):
    """يحوّل مرجعاً (space أو space@level) إلى عقدة.
    يعيد (node_id, reason, kind) حيث kind ∈ invalid | no_edges | ok — للتفريق بين
    "فراغ غير موجود" و"فراغ موجود لكن بلا حواف مؤهَّلة" (الأخير NO_PATH لا INVALID)."""
    if not ref:
        return None, "empty_reference", "invalid"
    ref = str(ref)
    base = ref.split("@")[0]
    if "@" in ref:
        if ref in nav["nodes"]:
            return ref, None, "ok"
        return (None, "space_has_no_eligible_edges", "no_edges") if base in spaces \
            else (None, "unknown_space", "invalid")
    cands = [n for n in nav["nodes"] if nav["nodes"][n]["space"] == ref]
    if not cands:
        return (None, "space_has_no_eligible_edges", "no_edges") if ref in spaces \
            else (None, "unknown_space", "invalid")
    if len(cands) > 1:
        return None, "ambiguous_level:specify space@level (%s)" % ",".join(sorted(cands)), "invalid"
    return cands[0], None, "ok"


def find_path(building, relationships, frm, to, building_id="bld_0", include_unresolved=False):
    """مسار اتصال بأقلّ عدد انتقالات (minimum-hop) عبر العلاقات المؤهَّلة فقط."""
    base = {"status": None, "from": frm, "to": to, "nodes": [], "edges": [],
            "transitions": [], "hops": None, "resolution": None,
            "distance": None, "distance_status": "NOT_MEASURED",
            "metrics": {}, "reason": None}

    # منع المسار بين مبنيين مختلفين (لا دوران موقع مُنفَّذ)
    def bld_of(x):
        return str(x).split(".")[0] if x else None
    if bld_of(frm) and bld_of(to) and bld_of(frm) != bld_of(to):
        base.update(status="NOT_SUPPORTED_INTER_BUILDING",
                    reason="physical inter-building circulation is not implemented")
        return base

    nav = build_nav_graph(building, relationships, building_id, include_unresolved)
    spaces = known_spaces(building, building_id)
    a, ra, ka = _resolve(nav, frm, spaces)
    if a is None:
        base.update(status="NO_PATH" if ka == "no_edges" else "INVALID_SOURCE", reason=ra)
        return base
    b, rb, kb = _resolve(nav, to, spaces)
    if b is None:
        base.update(status="NO_PATH" if kb == "no_edges" else "INVALID_TARGET", reason=rb)
        return base
    if a == b:
        base.update(status="FOUND", nodes=[a], edges=[], transitions=[], hops=0,
                    resolution="confirmed")
        base["from"], base["to"] = a, b
        base["metrics"] = {"horizontal_centroid_m": 0.0, "vertical_transitions": 0,
                           "measured_segments": "0/0"}
        return base

    prev, seen = {a: None}, {a}
    q = deque([a])
    while q:
        cur = q.popleft()
        if cur == b:
            break
        for nb in sorted(nav["adj"].get(cur, []), key=lambda e: (e["to"], str(e["edge"].get("rel_id")))):
            if nb["to"] in seen:
                continue
            seen.add(nb["to"])
            prev[nb["to"]] = (cur, nb["edge"])
            q.append(nb["to"])

    if b not in prev:
        base.update(status="NO_PATH",
                    reason="no eligible edge chain (unresolved edges are never traversed)")
        if not include_unresolved:
            alt = find_path(building, relationships, frm, to, building_id, True)
            base["unresolved_alternative_exists"] = (alt.get("status") == "FOUND")
        return base

    chain, cur = [], b
    while prev[cur] is not None:
        p, e = prev[cur]
        chain.append((p, e, cur))
        cur = p
    chain.reverse()

    nodes = [a] + [c[2] for c in chain]
    edges = [c[1] for c in chain]
    transitions, horiz, measured, verticals = [], 0.0, 0, 0
    for (p, e, c) in chain:
        if e["type"] == "door":
            transitions.append({"type": "door", "via": e.get("via"),
                                "from": nav["nodes"][p]["space"], "to": nav["nodes"][c]["space"],
                                "level": e.get("level"), "source": e.get("source"),
                                "status": e.get("status")})
            ca, cb = nav["nodes"][p].get("centroid"), nav["nodes"][c].get("centroid")
            if ca and cb:
                horiz += ((ca[0] - cb[0]) ** 2 + (ca[1] - cb[1]) ** 2) ** 0.5
                measured += 1
        else:
            verticals += 1
            # اتجاه الانتقال كما سُلك فعلاً (لا كما خُزّن في الحافة)
            transitions.append({"type": "vertical", "kind": e.get("kind"), "via": e.get("via"),
                                "from_level": nav["nodes"][p]["level"],
                                "to_level": nav["nodes"][c]["level"],
                                "from": nav["nodes"][p]["space"], "to": nav["nodes"][c]["space"],
                                "source": e.get("source"), "status": e.get("status"),
                                "distance_measurable": False})

    statuses = {e.get("status") for e in edges}
    resolution = ("unresolved" if "unresolved" in statuses
                  else ("confirmed" if statuses == {"confirmed"} else "contains_inferred_edges"))

    base.update(status="FOUND", nodes=nodes, edges=edges, transitions=transitions,
                hops=len(edges), resolution=resolution)
    base["from"], base["to"] = a, b
    base["distance"] = None                      # مسافة المشي الحقيقية غير محسوبة في هذه المرحلة
    base["distance_status"] = "PARTIAL" if measured else "NOT_MEASURED"
    base["metrics"] = {"horizontal_centroid_m": round(horiz, 2),
                       "vertical_transitions": verticals,
                       "measured_segments": "%d/%d" % (measured, len(edges)),
                       "note": "مسافة بين مراكز الفراغات — ليست مسافة مشي، والانتقال الرأسي غير مقيس"}
    return base


def validate_path(building, relationships, result, building_id="bld_0"):
    """فحص بنيوي للمسار المُعاد — لا فحص مطابقة هندسية."""
    issues = []
    if result.get("status") != "FOUND":
        return issues
    nav = build_nav_graph(building, relationships, building_id, False)
    nodes = result.get("nodes") or []
    if not nodes:
        issues.append("empty path")
        return issues
    if nodes[0] != result.get("from"):
        issues.append("first node != requested source")
    if nodes[-1] != result.get("to"):
        issues.append("last node != requested target")
    for n in nodes:
        if n not in nav["nodes"]:
            issues.append("unknown node in path: %s" % n)
    for i in range(len(nodes) - 1):
        pair = [x for x in nav["adj"].get(nodes[i], []) if x["to"] == nodes[i + 1]]
        if not pair:
            issues.append("no eligible edge between %s and %s" % (nodes[i], nodes[i + 1]))
    for e in result.get("edges") or []:
        if e.get("status") == "unresolved":
            issues.append("path traverses an unresolved edge (forbidden)")
    for t in result.get("transitions") or []:
        if t.get("type") == "vertical":
            if t.get("from_level") is None or t.get("to_level") is None:
                issues.append("vertical transition without valid levels")
    blds = {str(n).split(".")[0] for n in nodes}
    if len(blds) > 1:
        issues.append("path crosses buildings: %s" % ",".join(sorted(blds)))
    return issues


def nav_issues(building, relationships, building_id="bld_0"):
    """عقد معزولة (بلا أي حافة مؤهَّلة) — معلومة تشخيصية، ليست خطأً هندسياً."""
    nav = build_nav_graph(building, relationships, building_id, False)
    return {"isolated_nodes": sorted([n for n in nav["nodes"] if not nav["adj"].get(n)]),
            "node_count": len(nav["nodes"]), "edge_count": len(nav["edges"])}


def path_summary(result):
    """ملخّص واقعي — بلا أي وصف نظامي/سلامة/إتاحة."""
    if result.get("status") != "FOUND":
        return "لا يوجد مسار اتصال: %s (%s)" % (result.get("status"), result.get("reason") or "")
    parts = [str(result["nodes"][0]).split("@")[0]]
    for t in result.get("transitions") or []:
        if t["type"] == "door":
            parts.append("باب %s" % (t.get("via") or ""))
            parts.append(t.get("to"))
        else:
            parts.append("%s %s (مستوى %s ← %s)" % (
                "درج" if t.get("kind") == "stairs" else "مصعد",
                t.get("via") or "", t.get("from_level"), t.get("to_level")))
            parts.append(t.get("to"))
    head = "مسار تنقّل حسب العلاقات الحالية (%d انتقال، %s)" % (
        result.get("hops") or 0, result.get("resolution"))
    return head + ": " + " → ".join(str(p) for p in parts)
