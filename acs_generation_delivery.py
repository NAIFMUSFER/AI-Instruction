# -*- coding: utf-8 -*-
"""Bounded, capability-protected delivery receipts; no extra model calls.

A receipt survives an HTTP disconnect, not a server restart. This is explicitly
single-process and opt-in. Descriptions/results are never logged or written to
files; terminal results are deleted after TTL, including while the API is idle.
"""
import asyncio
import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass, field

import acs_api_errors as E

CONTRACT = "acs.generation-delivery/1"
ID_HEADER = "X-ACS-Operation-ID"
TOKEN_HEADER = "X-ACS-Operation-Token"
_ID = re.compile(r"^[a-f0-9]{32}$")
_TOKEN = re.compile(r"^[a-f0-9]{64}$")


@dataclass(repr=False)
class Receipt:
    operation_id: str
    token_hash: bytes = field(repr=False)
    fingerprint: bytes = field(repr=False)
    request_id: str
    status: int = 202
    body: bytes | None = field(default=None, repr=False)
    expires_at: float | None = None
    task: asyncio.Task | None = field(default=None, repr=False)
    expiry: asyncio.TimerHandle | None = field(default=None, repr=False)


class DeliveryStore:
    """Event-loop confined; admission contains no await and is therefore atomic.

    The admission callback is evaluated ONCE, before retaining a request or
    starting work. Duplicate receipts do not reconsume the generation quota.
    """
    def __init__(self, capacity=16, active_limit=8, ttl=900, max_result_bytes=4*1024*1024):
        self.capacity = capacity
        self.active_limit = active_limit
        self.ttl = ttl
        self.max_result_bytes = max_result_bytes
        self._items = {}
        self._loop = None

    @staticmethod
    def validate(operation_id, token):
        if not _ID.fullmatch(operation_id or "") or not _TOKEN.fullmatch(token or ""):
            raise E.AcsApiError(E.ACS_BAD_REQUEST, "بيانات متابعة الطلب غير صالحة.")
        return hashlib.sha256(token.encode("ascii")).digest()

    def _bind(self):
        loop = asyncio.get_running_loop()
        if self._loop is not None and self._loop is not loop:
            raise E.AcsApiError(E.ACS_NOT_CONFIGURED,
                               "متابعة الطلبات تتطلب عملية خادم واحدة.")
        self._loop = loop
        return loop

    def _remove(self, operation_id, receipt):
        if self._items.get(operation_id) is receipt:
            self._items.pop(operation_id, None)
            receipt.body = None
            if receipt.expiry:
                receipt.expiry.cancel()

    def _prune(self):
        now = time.monotonic()
        for key, rec in list(self._items.items()):
            if rec.expires_at is not None and rec.expires_at <= now:
                self._remove(key, rec)

    def _existing(self, operation_id, token_hash):
        self._prune()
        rec = self._items.get(operation_id)
        if rec is not None and not hmac.compare_digest(rec.token_hash, token_hash):
            # Wrong token and missing receipt have the same public result.
            raise E.AcsApiError(E.ACS_NOT_FOUND, "الطلب غير متاح أو انتهت مدة الاحتفاظ به.")
        return rec

    def submit(self, operation_id, token, fingerprint, request_id, admit, run):
        loop = self._bind()
        digest = self.validate(operation_id, token)
        rec = self._existing(operation_id, digest)
        if rec:
            if not hmac.compare_digest(rec.fingerprint, fingerprint):
                raise E.AcsApiError(E.ACS_BAD_REQUEST,
                                   "رقم المتابعة مستخدم لطلب مختلف.", status=409)
            return rec
        if len(self._items) >= self.capacity or sum(
                r.body is None for r in self._items.values()) >= self.active_limit:
            raise E.AcsApiError(E.ACS_RATE_LIMITED,
                               "متابعة التوليد مشغولة الآن. أعد المحاولة لاحقاً.",
                               retry_after=30)
        admit()
        rec = Receipt(operation_id, digest, fingerprint, request_id)
        self._items[operation_id] = rec
        rec.task = loop.create_task(self._execute(rec, run))
        return rec

    async def _execute(self, rec, run):
        try:
            payload = await run()
            status = 200
        except E.AcsApiError as exc:
            payload, status = exc.envelope(rec.request_id), exc.status
        except asyncio.CancelledError:
            payload = E.AcsApiError(E.ACS_TIMEOUT,
                "توقفت متابعة الطلب على الخادم؛ لا تعد التوليد تلقائياً.").envelope(rec.request_id)
            status = 504
        except Exception:
            # No exception repr, raw response, prompt, or token in logs/results.
            payload, status = E.AcsApiError(E.ACS_INTERNAL).envelope(rec.request_id), 500
        try:
            raw = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
            if len(raw) > self.max_result_bytes:
                raise ValueError("result exceeds the retained-result byte budget")
        except Exception:
            raw = json.dumps(E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE,
                "تعذر الاحتفاظ بنتيجة الطلب ضمن حد الحجم؛ لم تُعد عملية التوليد.")
                .envelope(rec.request_id), ensure_ascii=False).encode("utf-8")
            status = 413
        rec.body, rec.status = raw, status
        rec.task = None
        rec.expires_at = time.monotonic() + self.ttl
        rec.expiry = self._loop.call_later(self.ttl, self._remove, rec.operation_id, rec)

    def get(self, operation_id, token):
        self._bind()
        digest = self.validate(operation_id, token)
        rec = self._existing(operation_id, digest)
        if rec is None:
            raise E.AcsApiError(E.ACS_NOT_FOUND, "الطلب غير متاح أو انتهت مدة الاحتفاظ به.")
        return rec

    async def close(self):
        tasks = [r.task for r in self._items.values() if r.task is not None]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for key, rec in list(self._items.items()):
            self._remove(key, rec)
        self._loop = None
