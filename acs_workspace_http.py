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
from acs_plan_review import PlanError, digest

ROUTE = re.compile(r"^/v1/projects/([0-9a-f-]+)/workspace$")
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
        "storage": "supabase", "automatic_resubmission": False}}


class WorkspaceMiddleware:
    def __init__(self, app):
        self.app = app
        self.tasks = set()

    async def _finish(self, store, project_id, actor_id, command):
        payload = {"state": "FAILED", "error_code": "GENERATION_FAILED"}
        try:
            execute = SERVICE.chat_and_save if command["action"] == "chat_edit" else SERVICE.generate_and_save
            rid = await asyncio.to_thread(execute, store, project_id, actor_id, command)
            payload = {"state": "SUCCEEDED", "revision_id": rid, "error_code": None}
        except (PlanError, E.AcsApiError) as exc:
            payload["error_code"] = str(exc.code)[:80]
        except Exception:
            pass  # Never put provider, bearer or database exception details in jobs.
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
               "worker_id": WORKER_ID, "state": "RUNNING"}
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
            command = await HTTP._read_json(receive)
            actor_id = (scope.get("state") or {}).get("authenticated_user_id")
            store = SESSION.authenticated_supabase_plan_store(scope)
            action = command.get("action")
            if action in {"generate", "chat_edit"}:
                result = await self._start(scope, store, project_id, actor_id, command)
            elif action == "state":
                SERVICE.checked_command(command, {"revision_id"})
                result = await asyncio.to_thread(SERVICE.view, store, project_id, actor_id, command.get("revision_id"))
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
        return await HTTP._send_json(scope, send, 202 if action in {"generate", "chat_edit"} else 200, result)