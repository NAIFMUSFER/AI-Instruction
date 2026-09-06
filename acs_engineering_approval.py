# -*- coding: utf-8 -*-
# =============================================================================
# acs_engineering_approval.py — اعتماد الاقتراح الهندسي أو رفضه.
#
# مفصول عن acs_engineering_authority عمداً: الاعتماد يستورد طبقة التأليف، وهي
# مرآة متصفّح لا تُشحَن في صورة الخادم. طبقة التخطيط تبقى نظيفة الإغلاق، وطبقة
# الاعتماد تعيش حيث يعيش المشروع والمراجعات.
#
# لا مسار كتابة ثانٍ: كل اقتراح معتمد يُترجَم إلى أمر تأليف قانوني ويمرّ بـ
# acs_authoring.commit_transaction — تطبيع، معاينة، تحقّق، تأكيد صريح، مراجعة.
# =============================================================================
from acs_engineering_authority import (  # noqa: F401
    PROPOSAL, SAFE, SCHEMA, VERSION, UNSOURCED_RULE_CHANGES, classify, model_hash, _copy)

_POINT_DEFAULT_HEIGHT = {"smoke": 2.9, "sprinkler": 2.9, "camera": 2.7,
                         "exit": 2.2, "assembly": 0.0, "extinguisher": 1.1,
                         "light": None, "outlet": 0.40, "switch": 1.20}


def _commands_for(prop, model):
    """يترجم اقتراحاً معتمداً إلى أوامر تأليف قانونية.

    لا يوجد مسار كتابة ثانٍ: كل ما يخرج من هنا يدخل commit_transaction."""
    ctype = prop.get("authoring_command")
    if not ctype:
        return []
    targets = prop.get("target_ids") or []
    after = prop.get("after") or {}
    detail = prop.get("detail") or {}
    out = []

    if ctype == "CHANGE_SITE_DIMENSIONS":
        out.append({"type": ctype, "target_id": "site", "source": "SYSTEM_TOOL",
                    "parameters": {"w": after.get("w"), "d": after.get("d")}})
        return out

    if ctype == "RESIZE_SPACE":
        for t in targets:
            params = {}
            rect = after.get("rect")
            if isinstance(rect, list) and len(rect) == 4:
                params = {"x": rect[0], "z": rect[1], "w": rect[2], "d": rect[3]}
            elif "width_m" in after:                       # توسيع ممرّ
                before_rect = (prop.get("before") or {}).get("rect")
                if not (isinstance(before_rect, list) and len(before_rect) == 4):
                    continue
                x, z, w, d = [float(v) for v in before_rect]
                if detail.get("axis") == "w":
                    w = float(after["width_m"])
                else:
                    d = float(after["width_m"])
                params = {"x": x, "z": z, "w": w, "d": d}
            if params:
                out.append({"type": ctype, "target_id": t, "source": "SYSTEM_TOOL",
                            "parameters": params})
        return out

    if ctype == "ADD_POINT":
        ptype = detail.get("point_type")
        missing = int(detail.get("missing") or 1)
        if ptype:                                          # نقص مُعلَن بالعدد
            for t in targets:
                room = _room_of(model, t)
                w = float((room.get("rect") or [0, 0, 4, 4])[2]) if room else 4.0
                d = float((room.get("rect") or [0, 0, 4, 4])[3]) if room else 4.0
                for i in range(missing):
                    p = {"point_type": ptype,
                         "x": round(w * (i + 1) / (missing + 1), 2),
                         "z": round(d / 2.0, 2)}
                    h = _POINT_DEFAULT_HEIGHT.get(ptype)
                    if h is not None:
                        p["height"] = h
                    out.append({"type": ctype, "target_id": t, "source": "SYSTEM_TOOL",
                                "parameters": p})
            return out
        for t in targets:                                  # نقطة بعينها من autofix
            pts = after.get("points") or []
            for p in pts:
                params = {"point_type": p.get("type"), "x": p.get("x"), "z": p.get("z")}
                if p.get("height") is not None:
                    params["height"] = p["height"]
                out.append({"type": ctype, "target_id": t, "source": "SYSTEM_TOOL",
                            "parameters": params})
        return out

    if ctype in ("MOVE_POINT", "CHANGE_POINT_PROPERTIES"):
        for t in targets:
            params = {k: v for k, v in (after or {}).items()
                      if k in ("x", "z", "height") and v is not None}
            if params:
                out.append({"type": ctype, "target_id": t, "source": "SYSTEM_TOOL",
                            "parameters": params})
        return out

    if ctype == "ADD_DOOR":
        for t in targets:
            for dr in (after.get("doors") or []):
                out.append({"type": ctype, "target_id": t, "source": "SYSTEM_TOOL",
                            "parameters": {"edge": dr.get("edge"),
                                           "offset": dr.get("offset"),
                                           "width": dr.get("width"),
                                           "height": dr.get("height", 2.1)}})
        return out

    if ctype in ("CHANGE_DOOR_PROPERTIES", "MOVE_DOOR", "MOVE_OBJECT"):
        for t in targets:
            params = {k: v for k, v in (after or {}).items()
                      if k in ("width", "height", "offset", "edge", "x", "z")
                      and v is not None}
            if params:
                out.append({"type": ctype, "target_id": t, "source": "SYSTEM_TOOL",
                            "parameters": params})
        return out
    return out


def _room_of(model, target):
    parts = str(target).split(".")
    if len(parts) < 2:
        return None
    tmpl, rid = parts[0], ".".join(parts[1:])
    for r in ((model.get("floors") or {}).get(tmpl, {}).get("rooms") or []):
        if str(r.get("id")) == rid:
            return r
    return None


def reject(project, proposals, proposal_ids):
    """الرفض لا يمسّ شيئاً — يعيد المشروع نفسه والاقتراحات موسومة مرفوضة."""
    ids = set(proposal_ids or [])
    out = []
    for p in proposals:
        q = _copy(p)
        if q["proposal_id"] in ids:
            q["rejected"] = True
        q["committed"] = False
        out.append(q)
    return {"project": project, "proposals": out, "committed": False,
            "model_hash": model_hash(project.get("model") or {},
                                     project.get("building_id", "bld_0"))}


def approve(project, proposals, proposal_ids, actor_id="user",
            created_at=None, building_id=None):
    """يعتمد اقتراحات محدّدة عبر مسار التأليف الواحد.

    ينتج مراجعة واحدة طبيعية (لا مسار موازٍ، ولا إيداع تلقائي). الاستدعاء بلا
    proposal_ids لا يودع شيئاً — لا يوجد "اعتماد الكل" ضمنيّ."""
    import acs_authoring as A
    bid = building_id or project.get("building_id") or "bld_0"
    ids = [str(i) for i in (proposal_ids or [])]
    if not ids:
        return {"committed": False, "project": project,
                "issues": [{"code": "NO_PROPOSAL_SELECTED", "severity": "ERROR",
                            "subject": None,
                            "detail": "approval requires an explicit proposal id; "
                                      "there is no implicit approve-all"}]}
    chosen = [p for p in proposals if p["proposal_id"] in ids]
    missing = [i for i in ids if not any(p["proposal_id"] == i for p in chosen)]
    if missing:
        return {"committed": False, "project": project,
                "issues": [{"code": "UNKNOWN_PROPOSAL", "severity": "ERROR",
                            "subject": missing[0],
                            "detail": "the proposal id does not belong to this plan"}]}

    base = project.get("current_revision")
    for p in chosen:
        if p.get("type") in UNSOURCED_RULE_CHANGES:
            return {"committed": False, "project": project,
                    "issues": [{"code": "RULE_SOURCE_REQUIRED", "severity": "ERROR",
                                "subject": p["proposal_id"],
                                "detail": "A confirmation does not establish an "
                                          "authoritative rule or validate its threshold."}]}
        if p.get("base_revision") is not None and p["base_revision"] != base:
            return {"committed": False, "project": project,
                    "issues": [{"code": "STALE_BASE_REVISION", "severity": "ERROR",
                                "subject": p["proposal_id"],
                                "detail": "the proposal was computed against another "
                                          "revision; recompute the plan"}]}

    commands = []
    for p in chosen:
        cmds = _commands_for(p, project.get("model") or {})
        if not cmds:
            return {"committed": False, "project": project,
                    "issues": [{"code": "PROPOSAL_NOT_AUTHORABLE", "severity": "ERROR",
                                "subject": p["proposal_id"],
                                "detail": "this proposal has no authoring command; it is "
                                          "reported for human action and cannot be "
                                          "committed by the system"}]}
        commands.extend(cmds)

    txn = A.validate_transaction(project, commands, bid)
    digest = (txn.get("transaction") or {}).get("confirmation_digest")
    res = A.commit_transaction(project, commands, confirm=digest,
                               acknowledge_warnings=True, actor_id=actor_id,
                               building_id=bid, created_at=created_at)
    if res.get("committed"):
        approved = []
        for p in proposals:
            q = _copy(p)
            if q["proposal_id"] in ids:
                q["committed"] = True
                q["committed_revision"] = res["project"]["current_revision"]
            approved.append(q)
        res["proposals"] = approved
    return res

