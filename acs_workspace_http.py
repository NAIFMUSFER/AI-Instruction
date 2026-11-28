"""Authenticated project workspace, with durable generation delivery receipts."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import re
import uuid

import acs_api_errors as E
import acs_auth as AUTH
import acs_plan_http as HTTP
import acs_plan_session as SESSION
import acs_rate_limit as RL
import acs_workspace_service as SERVICE
import acs_brief_reader as BRIEF
import acs_plan_sources as SOURCES
import acs_designer_workspace as DESIGNER
from acs_logging import LOG
from acs_workspace_progress import PHASES
from acs_plan_review import PlanError, digest

ROUTE = re.compile(r"^/v1/projects/([0-9a-f-]+)/workspace(?P<source>/plan-source)?$")
WORKER_ID = str(uuid.uuid4())
ACTIVE_JOBS = set()
ACTIVE_PROJECTS = {}  # project_id -> the one job_id admitted or running for it
PAID_TASKS = set()
RESUMABLE_ERRORS = frozenset({"PLAN_DETAIL_INCOMPLETE", "PLAN_LAYOUT_INCOMPLETE",
                              "ACS_PROVIDER_BUDGET_EXHAUSTED"})


# A reply cut at the output cap, or a job stopped at the worker deadline, after
# a saved stage: resuming re-runs only the unfinished stages from the checkpoint.
# Without a checkpoint it is not offered, because a restart would pay for every
# stage again and meet the same cap or deadline.
# A reply that spent the whole cap thinking (no visible text) is the same case:
# the stage met its output cap, and the low-effort rung can answer it now.
RESUMABLE_WITH_CHECKPOINT = frozenset({"ACS_UPSTREAM_TRUNCATED", "ACS_TIMEOUT",
                                       "ACS_UPSTREAM_NO_VISIBLE_OUTPUT"})


def _resumable_failure(code, checkpoint=None):
    if isinstance(code, str) and code in RESUMABLE_WITH_CHECKPOINT:
        return bool(checkpoint)
    return isinstance(code, str) and (code in RESUMABLE_ERRORS or code.startswith("PLAN_GEOMETRY_"))


# A RUNNING receipt is only true while some process can still finish it. The
# worker deadline terminates the child and its parent then writes a receipt, so
# beyond deadline + grace nobody can: the owning process died (deploy, OOM,
# crash) or its terminal receipt write was lost. Report INTERRUPTED with an
# uncertain provider outcome instead of RUNNING forever. Read-only: nothing is
# resubmitted and the stored receipt is not rewritten.
ORPHAN_GRACE_S = 300
OWN_ORPHAN_AFTER_S = 60


def _started_at(row):
    value = row.get("created_at")
    if not isinstance(value, str):
        return None
    try:
        started = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return started if started.tzinfo else started.replace(tzinfo=timezone.utc)


def _orphaned(row, now=None):
    if row.get("state") != "RUNNING" or row.get("id") in ACTIVE_JOBS:
        return False
    if DESIGNER.is_designer(row):
        return False   # the run lives in its Managed Agents session; polls advance it
    started = _started_at(row)
    if started is None:
        return False
    from acs_generation_job import DEFAULT_TIMEOUT_S, WORKSPACE_JOB_TIMEOUT_S
    own = row.get("worker_id") == WORKER_ID
    limit = OWN_ORPHAN_AFTER_S if own else max(DEFAULT_TIMEOUT_S, WORKSPACE_JOB_TIMEOUT_S) + ORPHAN_GRACE_S
    return ((now or datetime.now(timezone.utc)) - started).total_seconds() > limit



def _failure_fields(exc):
    """What failed and where, without user text or secrets.

    A JobError only wraps the worker's own exception, so log that exception's
    class and position (file:line), its message only when it is fixed ASCII
    wording, and the exit code of a worker that died. Other failures happened
    in this process: their class is already logged, their position is added.
    """
    from acs_generation_job import JobError, _origin
    if isinstance(exc, JobError):
        return {"worker_error_class": str(exc.error_class)[:80], "worker_error_at": exc.error_at,
                "worker_error_message": exc.safe_message, "worker_exit_code": exc.exit_code}
    return {"error_at": _origin(exc)}


def _id(value):
    try:
        if not isinstance(value, str) or str(uuid.UUID(value)) != value:
            raise ValueError()
    except ValueError:
        raise PlanError("INVALID_IDENTITY", "معرّف الطلب غير صالح.") from None
    return value


def _job_query(project_id, job_id):
    return "/rest/v1/acs_workspace_jobs?project_id=eq." + project_id + "&id=eq." + job_id


def _read_job(store, project_id, job_id):
    rows = store._request("GET", _job_query(project_id, job_id))
    if not isinstance(rows, list) or len(rows) > 1:
        raise PlanError("STORE_UNAVAILABLE", "تعذّر قراءة حالة المهمة.")
    return rows[0] if rows else None


def _job_view(row):
    state = row.get("state")
    original = row.get("resume_command") or {}
    can_restart = isinstance(original,dict) and original.get('action') == 'generate' and not original.get('source_id')
    reading = isinstance(original, dict) and original.get("action") == "read_brief"
    failed = state in {"FAILED", "INTERRUPTED", "CANCELLED"}
    view = {"ok": True, "job": {"id": row["id"], "state": state,
        "revision_id": row.get("revision_id"), "reference_revision_id": row.get("expected_head"),
        "error_code": row.get("error_code"),
        "error_message": ((BRIEF.failure_message(row.get("error_code")) if reading else None)
                          or DESIGNER.message(row.get("error_code"))
                          or SERVICE.geometry_failure_message(row.get("error_code"))) if failed else None,
        "phase": row.get("phase"), "progress": row.get("progress"),
        "provider_calls": row.get("provider_calls", 0),
        "can_resume": not reading and bool(row.get("checkpoint") or can_restart) and state == "FAILED" and _resumable_failure(row.get("error_code"), row.get("checkpoint")) and not row.get("resumed_by"),
        "choice": None if reading else _choice(row),
        "storage": "supabase", "automatic_resubmission": False}}
    if reading:
        # A brief read saves no revision: its receipt carries the validated program.
        view["job"]["kind"] = "read_brief"
        checkpoint = row.get("checkpoint") if isinstance(row.get("checkpoint"), dict) else {}
        if state == "SUCCEEDED" and checkpoint.get("kind") == "brief_program":
            view["job"]["program"] = BRIEF.usable(checkpoint.get("program"))
    if DESIGNER.is_designer(row):
        view["job"]["kind"] = "design"
        view["job"]["can_resume"] = False
    if view["job"]["choice"] and view["job"]["choice"]["adopted_revision_id"]:
        view["job"]["error_message"] = "اعتُمدت النسخة المولّدة كنسخة جديدة. تعديلك السابق محفوظ في سجل النسخ ويمكن استعادته."
    return view


def _choice(row):
    """Explicit owner choice for a generated version kept after a newer revision."""
    kept = SERVICE.generated_version(row)
    if kept is None:
        return None
    building = kept["building"]
    floors = building.get("floors") if isinstance(building.get("floors"), dict) else {}
    return {"kind": "generated_version", "options": ["keep_edit", "use_generated"],
            "current_head": kept.get("current_head"), "adopted_revision_id": row.get("adopted_revision_id"),
            "generated_summary": {"levels": len(building.get("levels") or []),
                                  "rooms": sum(len(f.get("rooms") or []) for f in floors.values() if isinstance(f, dict))}}


def _adoption(ws, job_id):
    marker = SERVICE.adoption_marker(job_id)
    for revision in ws.history():
        if (revision.get("note") or "").endswith(marker):
            return revision["revision_id"]
    return None


def _read_brief(store, project_id, actor_id, command, *, on_progress=None):
    """One validated brief read: (program, provider_calls). Writes no revision."""
    return BRIEF.read_and_check(command, on_progress=on_progress)


class WorkspaceMiddleware:
    def __init__(self, app):
        self.app = app
        self.tasks = PAID_TASKS

    async def _finish(self, store, project_id, actor_id, command):
        payload = {"state": "FAILED", "error_code": "GENERATION_FAILED"}
        spent, kept = {}, None
        try:
            execute = {"chat_edit": SERVICE.chat_and_save, "read_brief": _read_brief}.get(command["action"], SERVICE.generate_and_save)
            def progress(event):
                if not isinstance(event, dict) or event.get("phase") not in PHASES:
                    return
                update = {"phase":event["phase"], "progress":{k:v for k,v in event.items()
                          if k in {"completed", "total"} and type(v) is int and v >= 0}}
                if type(event.get("provider_calls")) is int:
                    update["provider_calls"] = spent["provider_calls"] = event["provider_calls"]
                if isinstance(event.get("checkpoint"), dict):
                    update["checkpoint"] = event["checkpoint"]
                try:
                    store._request("PATCH", _job_query(project_id, command["job_id"]), update)
                except PlanError as exc:
                    # Progress is advisory and cumulative: the next event rewrites
                    # counts and the latest checkpoint. A transient store failure
                    # must not kill a worker that may already have paid provider
                    # requests. Authorization failures still stop the job.
                    if exc.code != "STORE_UNAVAILABLE":
                        raise
                    LOG.warn("workspace_progress_write_failed", request_id=command["job_id"], error_code=exc.code)
            # Chat edits spend provider requests too; their counts must reach the receipt.
            rid = await asyncio.to_thread(execute, store, project_id, actor_id, command, on_progress=progress)
            payload = {"state": "SUCCEEDED", "revision_id": rid, "error_code": None}
            if command["action"] == "read_brief":
                # The validated program is the receipt's result; no revision is written.
                payload.update(revision_id=None, checkpoint={"kind": "brief_program", "program": rid[0]},
                               provider_calls=rid[1])
                spent.pop("provider_calls", None)
        except TimeoutError:
            payload["error_code"] = E.ACS_TIMEOUT
        except (PlanError, E.AcsApiError) as exc:
            payload["error_code"] = str(exc.code)[:80]
            if isinstance(exc, SERVICE.GeneratedVersionConflict):
                kept = exc.checkpoint()
        except Exception as exc:
            from acs_generation_job import JobRejected, JobError
            payload["error_code"] = "GENERATION_BUSY" if isinstance(exc, JobRejected) else "GENERATION_WORKER_FAILED" if isinstance(exc, JobError) else "GENERATION_FAILED"
            LOG.error("workspace_worker_failed", request_id=command["job_id"], error_class=type(exc).__name__,
                      error_code=payload["error_code"], **_failure_fields(exc))
        LOG.info("workspace_job_finished", request_id=command["job_id"], state=payload["state"], error_code=payload.get("error_code"))
        payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        payload.update(spent)  # the terminal receipt carries the last known provider count
        if kept is not None:
            # Keep the paid version before the terminal receipt: never discarded,
            # never saved over the newer revision; the owner chooses later. Written
            # like a progress checkpoint so it maps onto lease-fenced job writes.
            try:
                await asyncio.to_thread(store._request, "PATCH", _job_query(project_id, command["job_id"]), {"checkpoint": kept})
            except Exception:
                payload["error_code"] = "STALE_REVISION"   # not kept: never offer a choice we cannot honour
        try:
            await asyncio.to_thread(store._request, "PATCH", _job_query(project_id, command["job_id"]), payload)
        except Exception:
            # The revision append is durable even if this delivery receipt fails.
            # A later job read recovers by its immutable revision task marker.
            pass

    async def _start(self, scope, store, project_id, actor_id, command):
        reading = command.get("action") == "read_brief"
        command = BRIEF.read_command(command) if reading else SERVICE.job_command(command)
        job_id = _id(command.get("job_id"))
        fingerprint = digest(command)
        prior = await asyncio.to_thread(_read_job, store, project_id, job_id)
        if prior:
            if prior.get("input_hash") != fingerprint:
                raise PlanError("STALE_REVISION", "معرّف المهمة مستخدم لطلب مختلف؛ لم يبدأ توليد آخر.")
            return _job_view(prior)
        # Membership is proven by this read, before any reservation below.
        before = await asyncio.to_thread(SERVICE.workspace, store, project_id, actor_id)
        if not reading and before.head != command.get("expected_head"):
            raise PlanError("STALE_REVISION", "افتح آخر نسخة قبل التوليد.")
        # One paid job per project at a time. Every job is checked against the
        # same head and saved by compare-and-swap, so a second concurrent job
        # (another tab, a second resume of the same failed job) can never be
        # saved: its provider spend would always be wasted. Check and reserve
        # happen with no await in between, so concurrent requests cannot both
        # pass. Process-local: valid under the declared single-instance invariant.
        if ACTIVE_PROJECTS.setdefault(project_id, job_id) != job_id:
            raise PlanError("GENERATION_IN_PROGRESS", "توجد مهمة توليد أو تعديل جارية لهذا المشروع. تابعها حتى تنتهي ثم افتح آخر نسخة؛ لم يُرسل أي طلب إلى مزود النموذج.")
        try:
            return await self._admit(store, project_id, actor_id, command, job_id, fingerprint)
        finally:
            if job_id not in ACTIVE_JOBS and ACTIVE_PROJECTS.get(project_id) == job_id:
                ACTIVE_PROJECTS.pop(project_id, None)

    async def _start_design(self, store, project_id, actor_id, command):
        """Open an ACS Designer run for this project (beta accounts only).

        The job row is written first, then the session is opened and recorded in
        the row's checkpoint; polls of the job advance it (acs_designer_workspace)."""
        if not DESIGNER.enabled(actor_id):
            raise PlanError("DESIGNER_NOT_ENABLED", DESIGNER.message("DESIGNER_NOT_ENABLED"))
        command = DESIGNER.design_command(command)
        job_id = _id(command.get("job_id"))
        fingerprint = digest(dict(command, action="design"))
        prior = await asyncio.to_thread(_read_job, store, project_id, job_id)
        if prior:
            if prior.get("input_hash") != fingerprint:
                raise PlanError("STALE_REVISION", "معرّف المهمة مستخدم لطلب مختلف؛ لم يبدأ تصميم آخر.")
            return _job_view(prior)
        before = await asyncio.to_thread(SERVICE.workspace, store, project_id, actor_id)
        if before.head != command.get("expected_head"):
            raise PlanError("STALE_REVISION", "افتح آخر نسخة قبل التصميم.")
        if ACTIVE_PROJECTS.setdefault(project_id, job_id) != job_id:
            raise PlanError("GENERATION_IN_PROGRESS", "توجد مهمة جارية لهذا المشروع. تابعها حتى تنتهي.")
        try:
            running = await asyncio.to_thread(store._request, "GET",
                "/rest/v1/acs_workspace_jobs?project_id=eq." + project_id
                + "&state=eq.RUNNING&checkpoint->>kind=eq." + DESIGNER.KIND + "&select=id&limit=1")
            if not isinstance(running, list):
                raise PlanError("STORE_UNAVAILABLE", "تعذّر التحقق من المهام الجارية.")
            if running:
                raise PlanError("DESIGNER_IN_PROGRESS", DESIGNER.message("DESIGNER_IN_PROGRESS"))
            decision = await asyncio.to_thread(RL.default_limiter().check, "actor:" + actor_id, "gen")
            if decision.get("degraded"):
                raise PlanError("STORE_UNAVAILABLE", "تعذّر التحقق من حصة التوليد. حاول لاحقًا.")
            if not decision.get("allowed"):
                raise E.AcsApiError(E.ACS_RATE_LIMITED, "تجاوزت حد التوليد. حاول لاحقًا.", retryable=True,
                                    retry_after=decision.get("retry_after", 60))
            row = {"id": job_id, "project_id": project_id, "created_by": actor_id, "input_hash": fingerprint,
                   "expected_head": command.get("expected_head"), "worker_id": WORKER_ID, "state": "RUNNING",
                   "resume_command": dict(command, action="design"), "phase": "UNDERSTANDING",
                   "checkpoint": {"kind": DESIGNER.KIND, "session_id": None}, "provider_calls": 0}
            inserted = await asyncio.to_thread(store._request, "POST", "/rest/v1/acs_workspace_jobs?on_conflict=id", row,
                                               prefer="resolution=ignore-duplicates,return=representation")
            if not isinstance(inserted, list) or not inserted:
                raise PlanError("STORE_UNAVAILABLE", "لم يصل تأكيد حفظ المهمة.")
            try:
                checkpoint = await asyncio.to_thread(DESIGNER.begin, project_id, job_id, command["brief"])
            except PlanError as exc:
                failed = {"state": "FAILED", "error_code": str(exc.code)[:80],
                          "finished_at": datetime.now(timezone.utc).isoformat()}
                await asyncio.to_thread(store._request, "PATCH", _job_query(project_id, job_id), failed)
                raise
            await asyncio.to_thread(store._request, "PATCH", _job_query(project_id, job_id), {"checkpoint": checkpoint})
            LOG.info("designer_job_started", request_id=job_id)
            return _job_view(dict(row, checkpoint=checkpoint))
        finally:
            if ACTIVE_PROJECTS.get(project_id) == job_id:
                ACTIVE_PROJECTS.pop(project_id, None)

    async def _admit(self, store, project_id, actor_id, command, job_id, fingerprint):
        if command.get("source_id"):
            for floor in SOURCES.read_options(command)["floors"]:
                await asyncio.to_thread(SOURCES.source, store, project_id, floor["source_id"])
        if len(self.tasks) >= 8:
            raise PlanError("STORE_UNAVAILABLE", "التوليد مشغول حاليًا. حاول لاحقًا.")
        # Reuse the deployment's shared admission limiter. Job reattachment above
        # consumes no generation quota and never creates another provider request.
        decision = await asyncio.to_thread(RL.default_limiter().check, "actor:" + actor_id,
                                           "edit" if command["action"] in {"chat_edit", "read_brief"} else "gen")
        if decision.get("degraded"):
            raise PlanError("STORE_UNAVAILABLE", "تعذّر التحقق من حصة التوليد. حاول لاحقًا.")
        if not decision.get("allowed"):
            raise E.AcsApiError(E.ACS_RATE_LIMITED, "تجاوزت حد التوليد. حاول لاحقًا.", retryable=True, retry_after=decision.get("retry_after", 60))
        row = {"id": job_id, "project_id": project_id, "created_by": actor_id,
               "input_hash": fingerprint, "expected_head": command.get("expected_head"),
               "worker_id": WORKER_ID, "state": "RUNNING",
               "resume_command": command, "phase":"UNDERSTANDING"}
        if command.get("resume_job_id"):
            source = await asyncio.to_thread(_read_job, store, project_id, _id(command["resume_job_id"]))
            if not source or not _job_view(source)["job"]["can_resume"]:
                raise PlanError("INVALID_RESUME", "لا توجد مرحلة محفوظة قابلة للاستئناف.")
            row.update(checkpoint=source.get("checkpoint") or {"kind":"start"}, provider_calls=source.get("provider_calls",0), phase=source.get("phase"))
        inserted = await asyncio.to_thread(store._request, "POST", "/rest/v1/acs_workspace_jobs?on_conflict=id", row,
                                           prefer="resolution=ignore-duplicates,return=representation")
        if not isinstance(inserted, list):
            raise PlanError("STORE_UNAVAILABLE", "لم يصل تأكيد حفظ المهمة.")
        if not inserted:
            prior = await asyncio.to_thread(_read_job, store, project_id, job_id)
            if not prior or prior.get("input_hash") != fingerprint:
                raise PlanError("PROJECT_ACCESS_DENIED", "المهمة غير متاحة لهذا المشروع.")
            return _job_view(prior)
        task = asyncio.create_task(self._finish(store, project_id, actor_id, command))
        self.tasks.add(task)
        ACTIVE_JOBS.add(job_id)
        ACTIVE_PROJECTS.setdefault(project_id, job_id)
        task.add_done_callback(self.tasks.discard)
        task.add_done_callback(lambda _: ACTIVE_JOBS.discard(job_id))
        task.add_done_callback(lambda _: ACTIVE_PROJECTS.pop(project_id, None)
                               if ACTIVE_PROJECTS.get(project_id) == job_id else None)
        return _job_view(row)

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        matched = ROUTE.fullmatch(path)
        if not matched:
            return await self.app(scope, receive, send)
        if scope.get("method") != "POST":
            return await HTTP._send_json(scope, send, 405, {"ok": False, "error": {"code": "METHOD_NOT_ALLOWED", "message": "POST فقط."}})
        if not await AUTH.authorize_asgi(scope, send):
            return None
        try:
            project_id = _id(matched.group(1))
            actor_id = (scope.get("state") or {}).get("authenticated_user_id")
            store = SESSION.authenticated_supabase_plan_store(scope)
            source_route = bool(matched.group("source"))
            if source_route:
                # Membership is checked before reading a potentially large file.
                await asyncio.to_thread(SERVICE.workspace, store, project_id, actor_id)
            command = await HTTP._read_json(receive, max_body_bytes=SOURCES.MAX_BODY if source_route else HTTP.MAX_BODY_BYTES,
                                            file_fields=("data_base64", "preview_base64") if source_route else ())
            action = command.get("action")
            if source_route:
                if action == "upload":
                    import acs_cpu_pool as CPU
                    checked = await CPU.run("validate_plan_source", args=(command,))
                    result = {"ok": True, "source": await asyncio.to_thread(SOURCES.save_source, store, project_id, actor_id, checked)}
                elif action == "list":
                    SERVICE.checked_command(command, set())
                    result = {"ok": True, "sources": await asyncio.to_thread(SOURCES.list_sources, store, project_id)}
                elif action == "download":
                    import base64
                    SERVICE.checked_command(command, {"source_id"})
                    row, raw = await asyncio.to_thread(SOURCES.read_source, store, project_id, command.get("source_id"))
                    result = {"ok": True, "name": row["name"], "media_type": row["media_type"], "data_base64": base64.b64encode(raw).decode("ascii")}
                elif action == "preview":
                    SERVICE.checked_command(command, {"source_id"})
                    result = dict(await asyncio.to_thread(SOURCES.preview_of, store, project_id,
                                                          command.get("source_id")), ok=True)
                elif action == "delete":
                    SERVICE.checked_command(command, {"source_id"})
                    result = dict(await asyncio.to_thread(SOURCES.delete_source, store, project_id, actor_id,
                                                          command.get("source_id")), ok=True)
                else:
                    raise PlanError("PLAN_COMMAND_NOT_SUPPORTED", "الأمر غير مدعوم لملفات المخطط.")
            elif action in {"generate", "chat_edit", "read_brief"}:
                result = await self._start(scope, store, project_id, actor_id, command)
            elif action == "design":
                result = await self._start_design(store, project_id, actor_id, command)
            elif action in {"designer_files", "designer_file"}:
                SERVICE.checked_command(command, {"job_id", "file_id"} if action == "designer_file" else {"job_id"})
                await asyncio.to_thread(SERVICE.workspace, store, project_id, actor_id)
                row = await asyncio.to_thread(_read_job, store, project_id, _id(command.get("job_id")))
                if not row:
                    raise PlanError("REVISION_NOT_FOUND", "المهمة غير متاحة لهذا الحساب والمشروع.")
                if action == "designer_files":
                    result = {"ok": True, "files": await asyncio.to_thread(DESIGNER.files, project_id, row)}
                else:
                    import base64
                    name, data = await asyncio.to_thread(DESIGNER.file, project_id, row, command.get("file_id"))
                    result = {"ok": True, "name": name, "data_base64": base64.b64encode(data).decode("ascii")}
            elif action == "brief_read_latest":
                # The newest validated read of this project by this account, for
                # another device before any revision exists. No provider request.
                SERVICE.checked_command(command, set())
                await asyncio.to_thread(SERVICE.workspace, store, project_id, actor_id)
                rows = await asyncio.to_thread(store._request, "GET",
                    "/rest/v1/acs_workspace_jobs?project_id=eq." + project_id + "&created_by=eq." + actor_id
                    + "&state=eq.SUCCEEDED&checkpoint->>kind=eq.brief_program"
                    + "&select=id,checkpoint,created_at,resume_command&order=created_at.desc&limit=1")
                if not isinstance(rows, list):
                    raise PlanError("STORE_UNAVAILABLE", "تعذّر قراءة البرنامج المقروء المحفوظ.")
                found = next((r for r in rows if isinstance(r, dict) and isinstance(r.get("checkpoint"), dict)
                              and r["checkpoint"].get("kind") == "brief_program"), None)
                program = BRIEF.usable(found["checkpoint"].get("program")) if found else None
                original = found.get("resume_command") if found and isinstance(found.get("resume_command"), dict) else {}
                brief = original.get("brief") if isinstance(original.get("brief"), str) and len(original["brief"]) <= 20000 else None
                result = {"ok": True, "read": {"job_id": found.get("id"), "created_at": found.get("created_at"),
                                               "brief": brief, "program": program} if program and brief else None}
            elif action == "resume":
                SERVICE.checked_command(command, {"job_id", "resume_job_id", "max_provider_calls", "confirmed"})
                if command.get("confirmed") is not True:
                    raise PlanError("EXPLICIT_CONFIRMATION_REQUIRED", "أكد الاستئناف وحد الاستدعاءات قبل المتابعة.")
                old = await asyncio.to_thread(_read_job, store, project_id, _id(command.get("resume_job_id")))
                if not old or not isinstance(old.get("resume_command"), dict) or old["resume_command"].get("action") != "generate":
                    raise PlanError("INVALID_RESUME", "هذه المهمة القديمة لا تحتوي بيانات استئناف. ابدأ طلبًا جديدًا من وصفك المحفوظ.")
                resumed = dict(old["resume_command"], job_id=_id(command.get("job_id")), resume_job_id=old["id"], max_provider_calls=command.get("max_provider_calls"))
                result = await self._start(scope, store, project_id, actor_id, resumed)
            elif action == "state":
                SERVICE.checked_command(command, {"revision_id"})
                result = await asyncio.to_thread(SERVICE.view, store, project_id, actor_id, command.get("revision_id"))
                result["designer_enabled"] = DESIGNER.enabled(actor_id)
            elif action == "research":
                SERVICE.checked_command(command, {"city", "building_type"})
                await asyncio.to_thread(SERVICE.workspace, store, project_id, actor_id)
                from acs_design_research import research
                result = await asyncio.to_thread(research, command.get("city", ""), command.get("building_type", "residential"))
            elif action == "job":
                SERVICE.checked_command(command, {"job_id"})
                row = await asyncio.to_thread(_read_job, store, project_id, _id(command.get("job_id")))
                if not row:
                    raise PlanError("REVISION_NOT_FOUND", "المهمة غير متاحة لهذا الحساب والمشروع.")
                if row["state"] == "RUNNING" and DESIGNER.is_designer(row) and row["checkpoint"].get("session_id"):
                    row = await asyncio.to_thread(DESIGNER.advance, store, project_id, actor_id, row)
                if row["state"] == "RUNNING":
                    ws = await asyncio.to_thread(SERVICE.workspace, store, project_id, actor_id)
                    for revision in ws.history():
                        if (revision.get("note") or "").endswith("task:" + row["id"]):
                            row = dict(row, state="SUCCEEDED", revision_id=revision["revision_id"])
                            break
                if _orphaned(row):
                    row = dict(row, state="INTERRUPTED", error_code="PROVIDER_OUTCOME_UNKNOWN")
                if SERVICE.generated_version(row) is not None:
                    ws = await asyncio.to_thread(SERVICE.workspace, store, project_id, actor_id)
                    row = dict(row, adopted_revision_id=_adoption(ws, row["id"]))
                result = _job_view(row)
            elif action == "adopt_generated":
                # Owner's explicit choice. No quota and no provider request: the
                # version was already paid for by its job.
                SERVICE.checked_command(command, {"job_id", "expected_head", "confirmed"})
                if command.get("confirmed") is not True:
                    raise PlanError("EXPLICIT_CONFIRMATION_REQUIRED", "أكد اختيار النسخة المولّدة أولًا.")
                row = await asyncio.to_thread(_read_job, store, project_id, _id(command.get("job_id")))
                if not row:
                    raise PlanError("REVISION_NOT_FOUND", "المهمة غير متاحة لهذا الحساب والمشروع.")
                rid = await asyncio.to_thread(SERVICE.adopt_generated_version, store, project_id, actor_id,
                                              row, command.get("expected_head"))
                result = await asyncio.to_thread(SERVICE.view, store, project_id, actor_id, rid)
                result["job"] = _job_view(dict(row, adopted_revision_id=rid))["job"]
            elif action == "generated_versions":
                SERVICE.checked_command(command, set())
                rows = await asyncio.to_thread(store._request, "GET",
                    "/rest/v1/acs_workspace_jobs?project_id=eq." + project_id + "&error_code=eq." + SERVICE.CONFLICT_CODE
                    + "&state=eq.FAILED&select=id,created_at,expected_head&order=created_at.desc&limit=5")
                if not isinstance(rows, list):
                    raise PlanError("STORE_UNAVAILABLE", "تعذّر قراءة النسخ المولّدة المحفوظة.")
                ws = await asyncio.to_thread(SERVICE.workspace, store, project_id, actor_id)
                result = {"ok": True, "versions": [{"job_id": r.get("id"), "created_at": r.get("created_at"),
                                                    "adopted_revision_id": _adoption(ws, r.get("id") or "")}
                                                   for r in rows[:5] if isinstance(r, dict) and isinstance(r.get("id"), str)]}
            elif action == "edit_geometry":
                result = await asyncio.to_thread(SERVICE.edit_geometry, store, project_id, actor_id, command)
            elif action == "set_roof":
                result = await asyncio.to_thread(SERVICE.set_roof, store, project_id, actor_id, command)
            elif action == "artifact":
                result = await asyncio.to_thread(SERVICE.isolated_artifact, store, project_id, actor_id, command)
            else:
                raise PlanError("PLAN_COMMAND_NOT_SUPPORTED", "الأمر غير مدعوم في مساحة المشروع.")
        except PlanError as exc:
            return await HTTP._send_plan_error(scope, send, exc)
        except E.AcsApiError as exc:
            return await HTTP._send_json(scope, send, exc.status, exc.envelope(HTTP._request_id(scope)))
        except Exception:
            return await HTTP._send_json(scope, send, 503, {"ok": False, "error": {"code": "WORKSPACE_UNAVAILABLE", "message": "تعذّر فتح مساحة المشروع. حاول مجددًا؛ نسخك المحفوظة لم تُحذف."}})
        return await HTTP._send_json(scope, send, 202 if action in {"generate", "chat_edit", "resume", "read_brief", "design"} else 200, result)
