"""The ACS Designer in the signed-in workspace (beta).

A project owner starts a design from a brief; the run lives in a Claude
Managed Agents session (acs_agent_designer), not in this process. The job row
(acs_workspace_jobs) records the session in its checkpoint, and every poll of
that job, made with the owner's own fresh session, advances it:

  running  -> the job stays RUNNING with a progress phase;
  finished -> building.json is read from the session, normalised for the
              review's explicit forms, admitted on the head the owner started
              from and saved as a normal revision (note "... task:<job_id>"),
              so the existing 2D review, approval and 3D viewer serve it; the
              agent's PDF, DXF, model, renders and report stay downloadable;
  failed   -> the job fails with a fixed code.

Nothing runs between polls, so a deploy or a restart loses nothing and no
long-lived worker holds the owner's token. Access is limited to the accounts
in ACS_DESIGNER_USER_IDS until billing is connected, and all workspace
sessions together may commit at most ACS_DESIGNER_DAILY_CAP_CENTS in 24 hours.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import acs_agent_designer as D
from acs_plan_review import PlanError

KIND = "designer"
NOTE = "تصميم ACS Designer · "
DAILY_CAP_CENTS = 4000            # USD 40 per rolling 24 hours, all workspace sessions together
SESSION_BUDGET_CENTS = 1000       # USD 10: the most one project may spend
BUILDING_MAX_BYTES = 900_000      # the review's canonical model limit
FILE_MAX_BYTES = 12 * 1024 * 1024
POLL_EVERY_S = 15.0

_ERRORS = {
    "DESIGNER_NOT_ENABLED": "التصميم الكامل بالذكاء متاح حاليًا لحسابات التجربة فقط.",
    "DESIGNER_DAILY_CAP_REACHED": "بلغ التصميم الكامل سقف اليوم. حاول بعد ساعات.",
    "DESIGNER_IN_PROGRESS": "يوجد تصميم جارٍ لهذا المشروع. تابعه حتى ينتهي.",
    "DESIGNER_FAILED": "لم يكتمل التصميم. لم تُحفظ نسخة جديدة؛ يمكنك المحاولة مرة أخرى.",
    "DESIGNER_OUTPUT_MISSING": "انتهى التصميم دون ملف المبنى. لم تُحفظ نسخة.",
    "DESIGNER_OUTPUT_INVALID": "ملف المبنى الناتج غير صالح. لم تُحفظ نسخة.",
    "DESIGNER_NOT_CONFIGURED": "التصميم الكامل غير مهيأ على الخادم.",
}


def message(code):
    return _ERRORS.get(code)


def enabled(actor_id):
    allowed = {v.strip() for v in os.environ.get("ACS_DESIGNER_USER_IDS", "").split(",") if v.strip()}
    return isinstance(actor_id, str) and actor_id in allowed


def daily_cap_cents():
    try:
        return max(0, int(os.environ.get("ACS_DESIGNER_DAILY_CAP_CENTS", DAILY_CAP_CENTS)))
    except ValueError:
        return DAILY_CAP_CENTS


def _refuse(code, status_hint=None):
    return PlanError(code, _ERRORS.get(code, "تعذّر التصميم."))


def design_command(command):
    from acs_workspace_service import checked_command
    out = checked_command(command, {"job_id", "brief", "expected_head", "confirmed"})
    if out.get("confirmed") is not True:
        raise PlanError("EXPLICIT_CONFIRMATION_REQUIRED", "أكد بدء التصميم الكامل أولًا.")
    brief = out.get("brief")
    if not isinstance(brief, str) or not 1 <= len(brief.strip()) <= D.BRIEF_MAX_CHARS:
        raise PlanError("DESCRIPTION_REQUIRED", "اكتب وصف المشروع ضمن الحد المسموح.")
    expected = out.get("expected_head")
    if expected is not None and (not isinstance(expected, str) or len(expected) > 160):
        raise PlanError("STALE_REVISION", "معرّف النسخة غير صالح.")
    return out


def is_designer(row):
    checkpoint = row.get("checkpoint") if isinstance(row, dict) else None
    return isinstance(checkpoint, dict) and checkpoint.get("kind") == KIND


def begin(project_id, job_id, brief, client=None):
    """Open the session for one design; returns the job checkpoint."""
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        out = D.start(brief, "ACS " + project_id[:8], SESSION_BUDGET_CENTS, client,
                      tag=D.PRODUCT_TAG, metadata={"project": project_id, "job": job_id},
                      cap_cents=daily_cap_cents(), since=since)
    except D.DesignerError as exc:
        raise _refuse(exc.code if exc.code in _ERRORS else "DESIGNER_FAILED") from None
    return {"kind": KIND, "session_id": out["session_id"]}


# ── polling ──────────────────────────────────────────────────────────────────
_LOCKS: dict = {}
_LAST: dict = {}
_GUARD = threading.Lock()


def _lock(job_id):
    with _GUARD:
        return _LOCKS.setdefault(job_id, threading.Lock())


def _finished(status):
    """('import' | 'fail' | None) for a session status."""
    if status.get("status") == "terminated":
        return "fail"
    if status.get("status") != "idle":
        return None
    results = [o.get("result") for o in status.get("outcomes") or []]
    last = results[-1] if results else None
    return "import" if last in ("satisfied", "max_iterations_reached") else "fail"


def _patch(store, project_id, job_id, payload):
    from acs_workspace_http import _job_query
    store._request("PATCH", _job_query(project_id, job_id), payload)


def _building(session_id, project_id, client):
    files = D.outputs(session_id, client, tag=D.PRODUCT_TAG, project_id=project_id)
    found = [f for f in files if f.get("filename") == "building.json"]
    if not found:
        raise _refuse("DESIGNER_OUTPUT_MISSING")
    _, raw = D.download(session_id, found[-1]["file_id"], client, tag=D.PRODUCT_TAG, project_id=project_id)
    if len(raw) > BUILDING_MAX_BYTES:
        raise _refuse("DESIGNER_OUTPUT_INVALID")
    try:
        building = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise _refuse("DESIGNER_OUTPUT_INVALID") from None
    if not isinstance(building, dict) or not isinstance(building.get("floors"), dict):
        raise _refuse("DESIGNER_OUTPUT_INVALID")
    return D.normalise_building(building)


def admit(store, project_id, actor_id, row, building):
    """Save the design as a revision on the head the owner started from."""
    import acs_workspace_service as SERVICE
    command = row.get("resume_command") or {}
    ws = SERVICE.workspace(store, project_id, actor_id)
    if ws.head != row.get("expected_head"):
        marker = SERVICE.adoption_marker(row["id"])
        for revision in ws.history():
            if (revision.get("note") or "").endswith(marker):
                return revision["revision_id"]       # saved by an earlier poll that could not mark the job
        raise PlanError("STALE_REVISION", "تغيّرت النسخة الحالية أثناء التصميم؛ لم تُحفظ نسخة فوقها.")
    admitted = {"brief": command.get("brief") or "", "requirements": D.requirements_for(building),
                "expected_head": row.get("expected_head")}
    return SERVICE._admit_generated(store, project_id, actor_id, admitted, building, ws, source_receipt=None,
                                    on_progress=None, note=NOTE + SERVICE.adoption_marker(row["id"]),
                                    fresh_defaults=False)


def advance(store, project_id, actor_id, row, client=None, now=None):
    """Bring a RUNNING designer job up to date; returns the row to report."""
    if row.get("state") != "RUNNING" or not is_designer(row):
        return row
    job_id = row["id"]
    lock = _lock(job_id)
    if not lock.acquire(blocking=False):
        return row                                   # another poll is advancing it
    try:
        moment = time.monotonic() if now is None else now
        if moment - _LAST.get(job_id, -1e9) < POLL_EVERY_S:
            return row
        _LAST[job_id] = moment
        session_id = row["checkpoint"]["session_id"]
        try:
            status = D.status(session_id, client, tag=D.PRODUCT_TAG, project_id=project_id)
        except D.DesignerError as exc:
            if exc.status == 404:
                return _fail(store, project_id, row, "DESIGNER_FAILED")
            return row                               # transient: the next poll asks again
        verdict = _finished(status)
        if verdict is None:
            phase = "REVIEW" if status.get("outcomes") else "LAYOUT"
            minutes = int((status.get("active_seconds") or 0) // 60)
            update = {"phase": phase, "progress": {"completed": minutes, "total": 30}}
            _patch(store, project_id, job_id, update)
            return dict(row, **update)
        if verdict == "fail":
            return _fail(store, project_id, row, "DESIGNER_FAILED")
        try:
            building = _building(session_id, project_id, client)
            revision_id = admit(store, project_id, actor_id, row, building)
        except PlanError as exc:
            return _fail(store, project_id, row, str(exc.code)[:80])
        done = {"state": "SUCCEEDED", "revision_id": revision_id, "error_code": None, "phase": "SAVING",
                "finished_at": datetime.now(timezone.utc).isoformat()}
        _patch(store, project_id, job_id, done)
        return dict(row, **done)
    finally:
        lock.release()


def _fail(store, project_id, row, code):
    failed = {"state": "FAILED", "error_code": code, "finished_at": datetime.now(timezone.utc).isoformat()}
    _patch(store, project_id, row["id"], failed)
    return dict(row, **failed)


# ── files ────────────────────────────────────────────────────────────────────
def files(project_id, row, client=None):
    if not is_designer(row):
        raise PlanError("REVISION_NOT_FOUND", "لا توجد ملفات تصميم لهذه المهمة.")
    try:
        return D.outputs(row["checkpoint"]["session_id"], client, tag=D.PRODUCT_TAG, project_id=project_id,
                         deliverables=True)
    except D.DesignerError:
        raise PlanError("STORE_UNAVAILABLE", "تعذّر قراءة ملفات التصميم. حاول لاحقًا.") from None


def file(project_id, row, file_id, client=None):
    if not is_designer(row):
        raise PlanError("REVISION_NOT_FOUND", "لا توجد ملفات تصميم لهذه المهمة.")
    allowed = {f["file_id"] for f in files(project_id, row, client)}
    if file_id not in allowed:
        raise PlanError("REVISION_NOT_FOUND", "الملف غير متاح لهذا التصميم.")
    try:
        name, data = D.download(row["checkpoint"]["session_id"], file_id, client, tag=D.PRODUCT_TAG,
                                project_id=project_id)
    except D.DesignerError:
        raise PlanError("STORE_UNAVAILABLE", "تعذّر تنزيل الملف. حاول لاحقًا.") from None
    if len(data) > FILE_MAX_BYTES:
        raise PlanError("ARTIFACT_TOO_LARGE", "الملف أكبر من الحد المسموح للتنزيل.")
    return name, data
