"""Connect the authenticated UI to the existing canonical revision aggregate.

Only the trusted parent admits provider geometry. Browser commands contain user
requirements or narrow element changes, never a replacement model or approval
receipt. Derived artifacts always cross the existing frozen-baseline gate.
"""
from __future__ import annotations

import base64
import json
import math
from pathlib import Path
import tempfile

from acs_plan_review import PlanError, canonical, digest, _geometry
from acs_plan_store_reload import load_workspace
from acs_plan_commands import _command, _view_result
from acs_plan_bridge import existing_geometry_verifier

SCHEMA = "acs.connected-workspace/1.0"
OPTIONS = {
    "A": "اقتراح يركز على استثمار المساحة ضمن المتطلبات المؤكدة.",
    "B": "اقتراح يركز على وضوح الحركة وقرب الأنشطة المرتبطة، بلا ادعاء قياس الإنتاجية.",
    "C": "اقتراح يركز على فصل الاستخدامات ومرونة التوسع ضمن القيود المؤكدة.",
}

# Persist only trusted validator categories, never provider text or geometry.
GEOMETRY_MESSAGES = {
    "AREA_EXCEEDS_SITE": "مجموع مساحات الفراغات التي ولّدها النظام أكبر من مساحة الموقع. لا يكفي تغيير مواقعها؛ يلزم مراجعة أحجام الفراغات والتوزيع.",
    "SITE_NOT_SPECIFIED": "أبعاد الموقع في المخطط الناتج غير محددة أو غير صالحة.",
    "DIMENSION_NOT_SPECIFIED": "بعض ارتفاعات المبنى أو سماكات الجدران في المخطط الناتج غير محددة أو غير صالحة.",
    "LEVELS_NOT_SPECIFIED": "المخطط الناتج لا يحدد الأدوار.",
    "INVALID_LEVEL": "تعريف الأدوار أو ربطها بالمخططات غير صالح.",
    "UNREFERENCED_TEMPLATE": "يوجد مخطط دور غير مرتبط بأدوار المبنى.",
    "EMPTY_TEMPLATE": "أحد مخططات الأدوار لا يحتوي فراغات.",
    "INVALID_RECT": "أبعاد أحد الفراغات في المخطط الناتج غير صالحة.",
    "OUTSIDE_SITE": "يوجد فراغ خارج حدود الأرض في المخطط الناتج.",
    "UNRESOLVED_SPACE": "لم يكتمل تخطيط بعض الفراغات؛ لم تُعتمد الأبعاد البديلة.",
    "UNSUPPORTED_NON_RECTANGULAR_SPACE": "يحتوي المخطط فراغًا غير مستطيل لا يدعمه مسار العرض الحالي.",
    "ROOM_OVERLAP": "توجد غرف أو فراغات متداخلة في المخطط الناتج.",
    "NON_FINITE_MEASUREMENT": "تعذّر حساب قياسات صالحة للمخطط الناتج.",
    "EMPTY_MODEL": "المخطط الناتج لا يحتوي مخططات أدوار.",
}


def geometry_failure_message(code):
    if code == "ACS_PROVIDER_BUDGET_EXHAUSTED":
        return "بلغ المقترح حد الاستدعاءات الذي وافقت عليه قبل اكتمال المخطط. راجع نطاق الطلب وحد الاستدعاءات قبل بدء محاولة جديدة."
    if code == "INVALID_GEOMETRY":
        return "لم يجتز المخطط فحص الهندسة. تفاصيل هذه المحاولة القديمة غير محفوظة."
    if isinstance(code, str) and code.startswith("PLAN_GEOMETRY_"):
        return GEOMETRY_MESSAGES.get(code[len("PLAN_GEOMETRY_"):])
    return None


def checked_command(command, allowed):
    _command(command)
    if set(command) - (set(allowed) | {"action"}):
        raise PlanError("INVALID_PLAN_COMMAND", "الطلب يحتوي حقولاً غير مدعومة.")
    return json.loads(canonical(command))


def workspace(store, project_id, actor_id):
    return load_workspace(store, project_id, actor_id=actor_id, verifier=existing_geometry_verifier)


def view(store, project_id, actor_id, revision_id=None):
    ws = workspace(store, project_id, actor_id)
    rid = revision_id or ws.head
    if rid is None:
        return {"schema": SCHEMA, "ok": True, "head": None, "baseline": None, "history": [], "revision_id": None}
    result = _view_result(ws, "state", rid)
    revision = ws.get(rid)
    result.update({"schema": SCHEMA, "ok": True, "brief": revision.brief,
                   "requirements": json.loads(revision.requirements_json),
                   "review_findings": [{"code": issue.get("code"),
                       "message": str(issue.get("message") or "")[:1000],
                       "requirement_id": issue.get("requirement_id")}
                       for issue in ws.review(rid).get("issues", [])[:512]]})
    return result


def generation_command(command):
    out = checked_command(command, {"job_id", "brief", "requirements", "expected_head", "option", "confirmed", "max_provider_calls", "source_id", "source_mode"})
    if "source_id" in out:
        from acs_plan_sources import identity
        identity(out["source_id"])
        if out.get("source_mode") not in {"preserve", "revise"}:
            raise PlanError("INVALID_PLAN_SOURCE", "اختر الحفاظ على توزيع المخطط أو طلب تعديله.")
    elif "source_mode" in out:
        raise PlanError("INVALID_PLAN_SOURCE", "اختر ملف مخطط محفوظًا أولًا.")
    if out.get("confirmed") is not True:
        raise PlanError("EXPLICIT_CONFIRMATION_REQUIRED", "راجع المتطلبات وأكدها قبل التوليد.")
    brief, requirements = out.get("brief"), out.get("requirements")
    if not isinstance(brief, str) or not 1 <= len(brief.strip()) <= 60000:
        raise PlanError("DESCRIPTION_REQUIRED", "اكتب وصف المشروع ضمن الحد المسموح.")
    if not isinstance(requirements, list) or not requirements or len(requirements) > 100:
        raise PlanError("INVALID_PROGRAM", "أضف متطلبات مؤكدة للمشروع.")
    if out.get("option") not in OPTIONS:
        raise PlanError("INVALID_OPTION", "اختر البديل A أو B أو C.")
    if type(out.get("max_provider_calls")) is not int or not 1 <= out["max_provider_calls"] <= 12:
        raise PlanError("INVALID_BUDGET", "اختر سقف استدعاءات من 1 إلى 12.")
    expected = out.get("expected_head")
    if expected is not None and (not isinstance(expected, str) or len(expected) > 160):
        raise PlanError("STALE_REVISION", "معرّف النسخة غير صالح.")
    from acs_plan_projection import _requirements
    from types import SimpleNamespace
    _requirements(SimpleNamespace(requirements_json=canonical(requirements), brief=brief))
    return out


def chat_command(command):
    out = checked_command(command, {"job_id", "expected_head", "notes", "confirmed", "max_provider_calls"})
    if out.get("confirmed") is not True or type(out.get("max_provider_calls")) is not int or not 1 <= out["max_provider_calls"] <= 12:
        raise PlanError("EXPLICIT_CONFIRMATION_REQUIRED", "أكد طلب التعديل وحد الاستدعاءات.")
    notes = out.get("notes")
    if not isinstance(notes, list) or not 1 <= len(notes) <= 30 or any(
        not isinstance(n, dict) or set(n) != {"text"} or not isinstance(n["text"], str)
        or not n["text"].strip() or len(n["text"]) > 6000 for n in notes
    ):
        raise PlanError("INVALID_EDIT", "اكتب طلب تعديل واضحًا ضمن الحد المسموح.")
    from acs_plan_commands import validate_plan_chat_command
    validate_plan_chat_command({"action": "chat_edit", "expected_head": out.get("expected_head"), "notes": out.get("notes")}, actor_id="preflight")
    return out


def job_command(command):
    return chat_command(command) if command.get("action") == "chat_edit" else generation_command(command)


def budgeted_chat_candidate(building, notes, max_provider_calls):
    from acs_plan_chat_job import generate_chat_candidate
    from acs_provider_budget import limited
    with limited(max_provider_calls):
        return generate_chat_candidate(building, notes)


def chat_and_save(store, project_id, actor_id, command):
    command = chat_command(command)
    from acs_plan_chat_orchestration import execute_isolated_persisted_chat_edit
    from acs_generation_job import default_runner
    runner = default_runner()

    class BudgetRunner:
        def run(self, target, kwargs, **controls):
            return runner.run("acs_workspace_service:budgeted_chat_candidate", {
                "building": kwargs["building"], "notes": kwargs["notes"],
                "max_provider_calls": command["max_provider_calls"],
            }, **controls)

    notes = json.loads(canonical(command["notes"]))
    notes[-1]["text"] += "\nمعرّف متابعة التعديل: task:" + command["job_id"]
    result = execute_isolated_persisted_chat_edit(store, project_id, {
        "action": "chat_edit", "expected_head": command["expected_head"], "notes": notes,
    }, actor_id=actor_id, verifier=existing_geometry_verifier, runner=BudgetRunner())
    return result["revision_id"]


def generate_plan_candidate(brief, requirements, option, max_provider_calls):
    """Isolated worker: has no actor, bearer, project, store or approval input."""
    from acs_plan_bridge import generate_candidate, _reject_provider_authority_changes
    from acs_provider_budget import limited
    prompt = brief + "\n\nمتطلبات أكدها المستخدم:\n" + canonical(requirements)
    prompt += "\nهدف المقترح " + option + ": " + OPTIONS[option]
    with limited(max_provider_calls) as budget:
        result = generate_candidate(prompt)
        _reject_provider_authority_changes({}, result["building"])
        from acs_plan_overlap_repair import repair_overlap
        result["building"] = repair_overlap(result["building"], prompt, budget)
    candidate = result["building"]
    _reject_provider_authority_changes({}, candidate)
    return {"building": candidate, "provider_calls": budget["used"], "stage": "PLAN_DRAFT"}


def generate_and_save(store, project_id, actor_id, command, *, runner=None):
    command = generation_command(command)
    expected = command.get("expected_head")
    before = workspace(store, project_id, actor_id)
    if before.head != expected:
        raise PlanError("STALE_REVISION", "تغيّرت النسخة. افتح آخر نسخة قبل التوليد.")
    if runner is None:
        from acs_generation_job import default_runner
        runner = default_runner()
    kwargs = {
        k: command[k] for k in ("brief", "requirements", "option", "max_provider_calls")
    }
    source_receipt = None
    target = "acs_workspace_service:generate_plan_candidate"
    if command.get("source_id"):
        from acs_plan_sources import read_source
        row, image = read_source(store, project_id, command["source_id"], "preview")
        kwargs["plan_source"] = {"image": base64.b64encode(image).decode("ascii"),
            "media_type": row["preview_media_type"], "mode": command["source_mode"]}
        source_receipt = {k: row[k] for k in ("id", "sha256", "page", "page_count", "preview_sha256")}
        source_receipt["mode"] = command["source_mode"]
        source_receipt["measurement_status"] = "needs_review"
        target = "acs_plan_sources:candidate"
    result = runner.run(target, kwargs, request_id=command["job_id"])
    if not isinstance(result, dict) or not isinstance(result.get("building"), dict):
        raise PlanError("INVALID_PLAN", "لم يعد المزود بمخطط صالح.")
    from acs_plan_bridge import _reject_provider_authority_changes
    _reject_provider_authority_changes({}, result["building"])
    if source_receipt:
        result["building"].setdefault("meta", {})["acs_plan_source"] = source_receipt
    # Re-read after provider work, then append with compare-and-swap. Existing
    # locks apply to every new option, and an approved baseline remains unchanged.
    ws = workspace(store, project_id, actor_id)
    if ws.head != expected:
        raise PlanError("STALE_REVISION", "تغيّرت النسخة أثناء التوليد؛ لم تُستبدل النسخة الأحدث.")
    revision = ws.propose(result["building"], brief=command["brief"], requirements=command["requirements"],
                          expected_head=expected, note="البديل " + command["option"] + " · task:" + command["job_id"])
    issues, _ = _geometry(revision.model)
    if issues:
        # First category in the canonical validator's deterministic order.
        # The remaining projection checks stay authoritative and unchanged.
        reason = issues[0].get("code")
        code = "PLAN_GEOMETRY_" + reason if reason in GEOMETRY_MESSAGES else "INVALID_GEOMETRY"
        raise PlanError(code, geometry_failure_message(code))
    _view_result(ws, "generate", revision.id)  # projection admission before write
    store.save_revision(project_id, actor_id=actor_id, revision=revision, expected_head=expected)
    return revision.id


def edit_geometry(store, project_id, actor_id, command):
    command = checked_command(command, {"expected_head", "room_ref", "rect"})
    ws = workspace(store, project_id, actor_id)
    expected = command.get("expected_head")
    if not expected or ws.head != expected:
        raise PlanError("STALE_REVISION", "افتح آخر نسخة قبل التعديل.")
    ref, rect = command.get("room_ref"), command.get("rect")
    if not isinstance(ref, list) or len(ref) != 2 or any(not isinstance(v, str) for v in ref):
        raise PlanError("ROOM_NOT_FOUND", "اختر فراغًا من المخطط.")
    if not isinstance(rect, list) or len(rect) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in rect) or min(rect[2:]) <= 0:
        raise PlanError("INVALID_GEOMETRY", "أدخل موضعًا وأبعادًا صالحة بالمتر.")
    before = ws.get(expected)
    candidate = before.model
    floor = candidate["floors"].get(ref[0])
    room = next((r for r in floor["rooms"] if r["id"] == ref[1]), None) if floor else None
    if room is None:
        raise PlanError("ROOM_NOT_FOUND", "الفراغ غير موجود في هذه النسخة.")
    room["rect"] = rect
    revision = ws.propose(candidate, brief=before.brief, requirements=json.loads(before.requirements_json),
                          expected_head=expected, note="تعديل أبعاد وموضع " + ref[1])
    result = _view_result(ws, "edit_geometry", revision.id, reference_revision_id=expected)
    store.save_revision(project_id, actor_id=actor_id, revision=revision, expected_head=expected)
    return result


def artifact(store, project_id, actor_id, command):
    command = checked_command(command, {"revision_id", "format", "level_index"})
    ws = workspace(store, project_id, actor_id)
    rid, fmt = command.get("revision_id"), command.get("format")
    if fmt not in {"svg", "dxf", "pdf", "ifc", "gltf", "review"}:
        raise PlanError("INVALID_FORMAT", "صيغة التصدير غير مدعومة.")
    if fmt == "review":
        from tools.acs_plan_review_packet import build_review_packet
        raw = canonical(build_review_packet(ws, rid)).encode("utf-8")
        return {"ok": True, "filename": "acs-review.json", "mime": "application/json", "data_base64": base64.b64encode(raw).decode("ascii")}
    # All other formats must first resolve the exact stored approval receipt.
    ws.handoff(rid)
    with tempfile.TemporaryDirectory(prefix="acs-approved-") as directory:
        path = Path(directory) / ("acs-approved." + fmt)
        level = command.get("level_index")
        if fmt in {"svg", "dxf"}:
            from tools.acs_plan_cad_export import export_approved_cad
            receipt = export_approved_cad(ws, rid, level, path)
        elif fmt == "pdf":
            from tools.acs_plan_pdf_export import export_approved_pdf
            receipt = export_approved_pdf(ws, rid, path)
        elif fmt == "ifc":
            from tools.acs_plan_ifc_export import export_approved_ifc
            receipt = export_approved_ifc(ws, rid, path)
        else:
            from tools.acs_plan_handoff import compile_approved_baseline
            receipt = compile_approved_baseline(ws, rid, path)
        if path.stat().st_size > 12 * 1024 * 1024:
            raise PlanError("INPUT_LIMIT", "ملف التصدير أكبر من حد التسليم المباشر.")
        raw = path.read_bytes()
    return {"ok": True, "revision_id": rid, "filename": path.name, "mime": {
        "svg": "image/svg+xml", "dxf": "application/dxf", "pdf": "application/pdf", "ifc": "application/x-step", "gltf": "model/gltf+json"
    }[fmt], "data_base64": base64.b64encode(raw).decode("ascii"), "receipt": receipt}


class _SnapshotStore:
    """Immutable server-read snapshot for the isolated artifact compiler."""
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def project_state(self, *args, **kwargs):
        raise PlanError("READ_ONLY", "Artifact workers cannot read mutable project state")

    def workspace_snapshot(self, project_id, *, actor_id):
        if project_id != self.snapshot.get("project_id"):
            raise PlanError("PROJECT_ACCESS_DENIED", "Artifact project changed")
        return self.snapshot

    def save_revision(self, *args, **kwargs):
        raise PlanError("READ_ONLY", "Artifact workers cannot write revisions")

    def save_approval(self, *args, **kwargs):
        raise PlanError("READ_ONLY", "Artifact workers cannot approve")


def artifact_from_snapshot(snapshot, command):
    """No access token, provider or database client crosses this worker boundary."""
    try:
        return artifact(_SnapshotStore(snapshot), snapshot["project_id"], "artifact-worker", command)
    except PlanError as exc:
        # Domain validation must survive process isolation. Generic worker errors
        # remain private and are handled by the runner, never copied here.
        return {"ok": False, "artifact_error": {"code": exc.code, "message": str(exc)}}


def isolated_artifact(store, project_id, actor_id, command):
    checked_command(command, {"revision_id", "format", "level_index"})
    snapshot = store.workspace_snapshot(project_id, actor_id=actor_id)
    from acs_generation_job import default_runner
    result = default_runner().run("acs_workspace_service:artifact_from_snapshot", {
        "snapshot": snapshot, "command": command,
    }, timeout_s=60)
    if isinstance(result, dict) and isinstance(result.get("artifact_error"), dict):
        error = result["artifact_error"]
        raise PlanError(error["code"], error["message"])
    return result
