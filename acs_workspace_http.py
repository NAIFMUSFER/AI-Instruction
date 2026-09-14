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
import acs_plan_sources as SOURCES
from acs_logging import LOG
from acs_workspace_progress import PHASES
from acs_plan_review import PlanError, digest

ROUTE = re.compile(r"^/v1/projects/([0-9a-f-]+)/workspace(?P<source>/plan-source)?$")
WORKER_ID = str(uuid.uuid4())
ACTIVE_JOBS = set()


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
    if state == "RUNNING" and (row.get("worker_id") != WORKER_ID or row.get("id") not in ACTIVE_JOBS):
        state = "INTERRUPTED"
    return {"ok": True, "job": {"id": row["id"], "state": state,
        "revision_id": row.get("revision_id"), "reference_revision_id": row.get("expected_head"),
        "error_code": row.get("error_code"),
        "error_message": SERVICE.geometry_failure_message(row.get("error_code")) if state == "FAILED" else None,
        "phase": row.get("phase"), "progress": row.get("progress"),
        "provider_calls": row.get("provider_calls", 0),
        "can_resume": bool(row.get("checkpoint")) and state in {"FAILED", "INTERRUPTED"},
        "storage": "supabase", "automatic_resubmission": False}}


class WorkspaceMiddleware:
    def __init__(self, app):
        self.app = app
        self.tasks = set()

    async def _finish(self, store, project_id, actor_id, command):
        payload = {"state": "FAILED", "error_code": "GENERATION_FAILED"}
        try:
            execute = SERVICE.chat_and_save if command["action"] == "chat_edit" else SERVICE.generate_and_save
            def progress(event):
                if not isinstance(event, dict) or event.get("phase") not in PHASES:
                    return
                update = {"phase":event["phase"], "progress":{k:v for k,v in event.items()
                          if k in {"completed", "total"} and type(v) is int and v >= 0}}
                if type(event.get("provider_calls")) is int:
                    update["provider_calls"] = event["provider_calls"]
                if isinstance(event.get("checkpoint"), dict):
                    update["checkpoint"] = event["checkpoint"]
                store._request("PATCH", _job_query(project_id, command["job_id"]), update)
            controls = {"on_progress":progress} if command["action"] == "generate" else {}
            rid = await asyncio.to_thread(execute, store, project_id, actor_id, command, **controls)
            payload = {"state": "SUCCEEDED", "revision_id": rid, "error_code": None}
        except TimeoutError:
            payload["error_code"] = E.ACS_TIMEOUT
        except (PlanError, E.AcsApiError) as exc:
            payload["error_code"] = str(exc.code)[:80]
        except Exception as exc:
            from acs_generation_job import JobRejected, JobError
            payload["error_code"] = "GENERATION_BUSY" if isinstance(exc, JobRejected) else "GENERATION_WORKER_FAILED" if isinstance(exc, JobError) else "GENERATION_FAILED"
            LOG.error("workspace_worker_failed", request_id=command["job_id"], error_class=type(exc).__name__, error_code=payload["error_code"])
        LOG.info("workspace_job_finished", request_id=command["job_id"], state=payload["state"], error_code=payload.get("error_code"))
        payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        try:
            await asyncio.to_thread(store._request, "PATCH", _job_query(project_id, command["job_id"]), payload)
        except Exception:
            # The revision append is durable even if this delivery receipt fails.
            # A later job read recovers by its immutable revision task marker.
            pass

    async def _start(self, scope, store, project_id, actor_id, command):
        command = SERVICE.job_command(command)
        job_id = _id(command.get("job_id"))
        fingerprint = digest(command)
        prior = await asyncio.to_thread(_read_job, store, project_id, job_id)
        if prior:
            if prior.get("input_hash") != fingerprint:
                raise PlanError("STALE_REVISION", "معرّف المهمة مستخدم لطلب مختلف؛ لم يبدأ توليد آخر.")
            return _job_view(prior)
        before = await asyncio.to_thread(SERVICE.workspace, store, project_id, actor_id)
        if before.head != command.get("expected_head"):
            raise PlanError("STALE_REVISION", "افتح آخر نسخة قبل التوليد.")
        if command.get("source_id"):
            await asyncio.to_thread(SOURCES.source, store, project_id, command["source_id"])
        if len(self.tasks) >= 8:
            raise PlanError("STORE_UNAVAILABLE", "التوليد مشغول حاليًا. حاول لاحقًا.")
        # Reuse the deployment's shared admission limiter. Job reattachment above
        # consumes no generation quota and never creates another provider request.
        headers = {k.decode("latin1"): v.decode("latin1") for k, v in scope.get("headers", [])}
        peer = (scope.get("client") or ("unknown", 0))[0]
        decision = RL.default_limiter().check(RL.client_identity(headers, peer), "edit" if command["action"] == "chat_edit" else "gen")
        if not decision.get("allowed"):
            raise E.AcsApiError(E.ACS_RATE_LIMITED, "تجاوزت حد التوليد. حاول لاحقًا.", retryable=True, retry_after=decision.get("retry_after", 60))
        row = {"id": job_id, "project_id": project_id, "created_by": actor_id,
               "input_hash": fingerprint, "expected_head": command.get("expected_head"),
               "worker_id": WORKER_ID, "state": "RUNNING",
               "resume_command": command, "phase":"UNDERSTANDING"}
        if command.get("resume_job_id"):
            source = await asyncio.to_thread(_read_job, store, project_id, _id(command["resume_job_id"]))
            if not source or not source.get("checkpoint") or _job_view(source)["job"]["state"] not in {"FAILED", "INTERRUPTED"}:
                raise PlanError("INVALID_RESUME", "لا توجد مرحلة محفوظة قابلة للاستئناف.")
            row.update(checkpoint=source["checkpoint"], provider_calls=source.get("provider_calls",0), phase=source.get("phase"))
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
        task.add_done_callback(self.tasks.discard)
        task.add_done_callback(lambda _: ACTIVE_JOBS.discard(job_id))
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
                else:
                    raise PlanError("PLAN_COMMAND_NOT_SUPPORTED", "الأمر غير مدعوم لملفات المخطط.")
            elif action in {"generate", "chat_edit"}:
                result = await self._start(scope, store, project_id, actor_id, command)
            elif action == "resume":
                SERVICE.checked_command(command, {"job_id", "resume_job_id", "max_provider_calls"})
                old = await asyncio.to_thread(_read_job, store, project_id, _id(command.get("resume_job_id")))
                if not old or not isinstance(old.get("resume_command"), dict) or old["resume_command"].get("action") != "generate":
                    raise PlanError("INVALID_RESUME", "هذه المهمة القديمة لا تحتوي بيانات استئناف. ابدأ طلبًا جديدًا من وصفك المحفوظ.")
                resumed = dict(old["resume_command"], job_id=_id(command.get("job_id")), resume_job_id=old["id"], max_provider_calls=command.get("max_provider_calls"))
                result = await self._start(scope, store, project_id, actor_id, resumed)
            elif action == "state":
                SERVICE.checked_command(command, {"revision_id"})
                result = await asyncio.to_thread(SERVICE.view, store, project_id, actor_id, command.get("revision_id"))
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
                if row["state"] == "RUNNING":
                    ws = await asyncio.to_thread(SERVICE.workspace, store, project_id, actor_id)
                    for revision in ws.history():
                        if (revision.get("note") or "").endswith("task:" + row["id"]):
                            row = dict(row, state="SUCCEEDED", revision_id=revision["revision_id"])
                            break
                result = _job_view(row)
            elif action == "edit_geometry":
                result = await asyncio.to_thread(SERVICE.edit_geometry, store, project_id, actor_id, command)
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
        return await HTTP._send_json(scope, send, 202 if action in {"generate", "chat_edit", "resume"} else 200, result)
