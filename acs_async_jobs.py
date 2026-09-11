"""Short-request delivery for the existing generation routes.

The original handlers still own validation, quotas, process isolation, timeouts,
and engineering review. This ASGI adapter only detaches delivery from the HTTP
connection. Anonymous jobs use a client-generated 256-bit capability, never a
job id or an IP address as authorization. Neither capability nor input is logged.

Storage is BOUNDED PROCESS MEMORY, not a durable queue. Results expire after
30 minutes; idempotency tombstones live for 24 hours. A server restart loses
these records. A missing job must never be automatically submitted again.
"""
import asyncio
import hashlib
import hmac
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field

import acs_api_errors as E
import acs_rate_limit as RL

CONTRACT = 'acs.async-generation/1.0'
SUBMIT_PATHS = {
    '/v1/jobs/understand': '/v1/understand',
    '/v1/jobs/understand/image': '/v1/understand/image',
    '/v1/jobs/understand/pdf': '/v1/understand/pdf',
    '/v1/jobs/edit': '/v1/edit',
}
JOB_PATH = re.compile(r'^/v1/jobs/(job_[a-f0-9]{32})(/result)?$')
ID_RE = re.compile(r'^job_[a-f0-9]{32}$')
TOKEN_RE = re.compile(r'^[a-f0-9]{64}$')
ACTIVE = frozenset(('QUEUED', 'RUNNING'))
_OWNER_SALT = os.urandom(32)


def _positive(name, default):
    try:
        return max(1, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


@dataclass
class Record:
    id: str
    token_hash: bytes = field(repr=False)
    fingerprint: bytes = field(repr=False)
    request_id: str
    created: float
    expires: float
    forget: float
    state: str = 'QUEUED'
    http: int = 202
    body: bytes = field(default=b'', repr=False)
    retry_after: str = ''
    owner: bytes = field(default=b'', repr=False)


class JobStore:
    def __init__(self, *, ttl=1800, tombstone_ttl=86400, capacity=8,
                 max_records=1024, max_body=8*1024*1024,
                 max_bytes=128*1024*1024, clock=time.time):
        self.ttl = ttl
        self.tombstone_ttl = max(tombstone_ttl, ttl)
        self.capacity = capacity
        self.max_records = max_records
        self.max_body = max_body
        self.max_bytes = max_bytes
        self.clock = clock
        self.records = {}
        self.lock = threading.RLock()

    def prune(self):
        with self.lock:
            now = self.clock()
            for key, row in list(self.records.items()):
                if row.state in ACTIVE:
                    continue  # Never silently evict running work.
                if now >= row.forget:
                    del self.records[key]
                elif now >= row.expires:
                    row.state, row.body = 'EXPIRED', b''

    def _authorized(self, job_id, token):
        row = self.records.get(job_id)
        digest = hashlib.sha256(token.encode('ascii')).digest()
        if row is None or not hmac.compare_digest(row.token_hash, digest):
            raise E.AcsApiError(E.ACS_NOT_FOUND, 'المهمة غير متاحة أو بيانات استعادتها غير صحيحة.')
        return row

    def get(self, job_id, token):
        with self.lock:
            self.prune()
            return self._authorized(job_id, token)

    def reserve(self, job_id, token, fingerprint, owner=b''):
        with self.lock:
            self.prune()
            if job_id in self.records:
                row = self._authorized(job_id, token)
                if not hmac.compare_digest(row.fingerprint, fingerprint):
                    raise E.AcsApiError(E.ACS_BAD_REQUEST,
                        'معرّف المهمة مستخدم لطلب مختلف؛ لم يبدأ توليد آخر.', status=409)
                return row, False
            # Admission identity limits retained records, not authorization.
            # Capability holders can still resume after a mobile IP change.
            owned = sum(r.owner == owner and r.state != 'EXPIRED'
                        for r in self.records.values())
            if owned >= 64:
                raise E.AcsApiError(E.ACS_RATE_LIMITED,
                    'تجاوزت عدد المهام المحفوظة مؤقتاً؛ لم يبدأ طلب آخر.',
                    retryable=True, retry_after=60)
            active = sum(r.state in ACTIVE for r in self.records.values())
            reserved = sum(self.max_body if r.state in ACTIVE else len(r.body)
                           for r in self.records.values())
            if (active >= self.capacity or len(self.records) >= self.max_records
                    or reserved + self.max_body > self.max_bytes):
                raise E.AcsApiError(E.ACS_RATE_LIMITED,
                    'مساحة متابعة التوليد مشغولة؛ لم يبدأ الطلب. حاول لاحقاً.',
                    retryable=True, retry_after=30)
            now = self.clock()
            row = Record(job_id, hashlib.sha256(token.encode('ascii')).digest(),
                         fingerprint, E.new_request_id(), now, now+self.ttl,
                         now+self.tombstone_ttl)
            row.owner = owner
            self.records[job_id] = row
            return row, True

    def finish(self, row, http, body, retry_after=''):
        with self.lock:
            row.http, row.body, row.retry_after = http, body, retry_after
            row.state = 'SUCCEEDED' if 200 <= http < 300 else 'FAILED'
            row.expires = self.clock() + self.ttl
            # Local admission/validation rejection has no paid result to retain.
            if http in (400, 413, 422, 429):
                row.expires = self.clock() + min(self.ttl, 60)
            row.forget = max(row.forget, row.expires)

    def status(self, row):
        return {'ok': True, 'contract': CONTRACT,
                'job': {'id': row.id, 'state': row.state,
                        'request_id': row.request_id,
                        'poll_after_ms': 2000,
                        'result_available': row.state in ('SUCCEEDED', 'FAILED'),
                        'expires_at': row.expires,
                        'retention_seconds': self.ttl,
                        'storage': 'process_memory'}}

    def health(self):
        with self.lock:
            return {'contract': CONTRACT, 'enabled': True,
                    'storage': 'process_memory', 'survives_server_restart': False,
                    'result_retention_seconds': self.ttl,
                    'idempotency_retention_seconds': self.tombstone_ttl,
                    'capacity': self.capacity, 'max_records': self.max_records,
                    'max_result_bytes': self.max_body,
                    'max_retained_bytes': self.max_bytes,
                    'in_flight': sum(r.state in ACTIVE for r in self.records.values())}


STORE = JobStore(capacity=min(8, _positive('ACS_ASYNC_JOB_CAPACITY', 8)))


def health_status():
    return STORE.health()


class AsyncGenerationMiddleware:
    """Install INSIDE CORS and OUTSIDE the original request handlers."""
    def __init__(self, app, store=None, max_input=None, execution_timeout=None):
        self.app = app
        self.store = STORE if store is None else store
        # Includes a small multipart framing allowance; the existing handlers
        # independently enforce the exact upload, field and text limits.
        self.max_input = max_input or (_positive('ACS_MAX_UPLOAD_MB', 12)*1024*1024+65536)
        self.execution_timeout = execution_timeout or (_positive('ACS_REQUEST_TIMEOUT_S', 840)+120)
        self.tasks = set()
        self.janitor = None

    async def _send(self, send, http, body, rid='', retry_after=''):
        headers = [(b'content-type', b'application/json; charset=utf-8'),
                   (b'cache-control', b'no-store, private'),
                   (b'x-content-type-options', b'nosniff')]
        if rid:
            headers.append((b'x-request-id', rid.encode('ascii')))
        if retry_after:
            headers.append((b'retry-after', str(retry_after).encode('ascii')))
        await send({'type': 'http.response.start', 'status': http, 'headers': headers})
        await send({'type': 'http.response.body', 'body': body, 'more_body': False})

    async def _error(self, send, exc, rid=None):
        rid = rid or E.new_request_id()
        await self._send(send, exc.status, _json(exc.envelope(rid)), rid,
                         str(exc.retry_after or ''))

    def _credentials(self, headers, job_id=None):
        job_id = job_id or headers.get(b'x-acs-job-id', b'').decode('ascii', 'ignore')
        token = headers.get(b'x-acs-job-token', b'').decode('ascii', 'ignore')
        if not ID_RE.fullmatch(job_id) or not TOKEN_RE.fullmatch(token):
            raise E.AcsApiError(E.ACS_BAD_REQUEST, 'بيانات متابعة المهمة ناقصة أو غير صالحة.')
        return job_id, token

    async def _maintain(self):
        try:
            while self.store.records:
                await asyncio.sleep(30)
                self.store.prune()
        except asyncio.CancelledError:
            pass

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            async def shutdown_receive():
                message = await receive()
                if message['type'] == 'lifespan.shutdown':
                    if self.janitor:
                        self.janitor.cancel()
                    for task in list(self.tasks):
                        task.cancel()
                    if self.tasks:
                        await asyncio.gather(*list(self.tasks), return_exceptions=True)
                return message
            return await self.app(scope, shutdown_receive, send)
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        path, method = scope['path'], scope['method']
        match = JOB_PATH.fullmatch(path)
        if path not in SUBMIT_PATHS and match is None:
            return await self.app(scope, receive, send)
        try:
            headers = dict(scope.get('headers', []))
            if match:
                if method != 'GET':
                    raise E.AcsApiError(E.ACS_METHOD_NOT_ALLOWED)
                job_id, token = self._credentials(headers, match[1])
                row = self.store.get(job_id, token)
                if row.state == 'EXPIRED':
                    raise E.AcsApiError(E.ACS_NOT_FOUND,
                        'انتهت مدة حفظ النتيجة. لم يُعَد تشغيل التوليد.', status=410)
                if match[2] and row.state not in ACTIVE:
                    return await self._send(send, row.http, row.body,
                                            row.request_id, row.retry_after)
                return await self._send(send, 202 if row.state in ACTIVE else 200,
                                        _json(self.store.status(row)), row.request_id)
            if method != 'POST':
                raise E.AcsApiError(E.ACS_METHOD_NOT_ALLOWED)
            job_id, token = self._credentials(headers)
            body = bytearray()
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return  # No complete input: no job and no provider call.
                body.extend(message.get('body', b''))
                if len(body) > self.max_input:
                    raise E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE)
                if not message.get('more_body', False):
                    break
            body = bytes(body)
            # Bind endpoint, content type and EXACT body. Replays with a changed
            # request fail closed, including mismatched multipart boundaries.
            fingerprint = hashlib.sha256(SUBMIT_PATHS[path].encode('ascii')+b'\0'
                +headers.get(b'content-type', b'')+b'\0'+body).digest()
            peer = (scope.get('client') or (None,))[0]
            identity = RL.client_identity({k.decode('latin-1'): v.decode('latin-1')
                for k, v in headers.items()}, peer)
            owner = hashlib.sha256(_OWNER_SALT + str(identity).encode('utf-8')).digest()
            row, fresh = self.store.reserve(job_id, token, fingerprint, owner)
            if fresh:
                inner = dict(scope)
                inner['path'] = SUBMIT_PATHS[path]
                inner['raw_path'] = inner['path'].encode('ascii')
                inner['query_string'] = b''
                inner['state'] = {'request_id': row.request_id}
                inner['headers'] = [(k, v) for k, v in scope.get('headers', [])
                    if k not in (b'x-acs-job-token', b'x-acs-job-id', b'x-request-id')]
                inner['headers'].append((b'x-request-id', row.request_id.encode('ascii')))
                # Strong reference, separate task: response delivery/cancellation
                # cannot cancel computation or consume its result.
                task = asyncio.create_task(self._execute(inner, body, row))
                self.tasks.add(task)
                task.add_done_callback(self.tasks.discard)
                if self.janitor is None or self.janitor.done():
                    self.janitor = asyncio.create_task(self._maintain())
            await self._send(send, 202, _json(self.store.status(row)), row.request_id)
        except E.AcsApiError as exc:
            await self._error(send, exc)

    async def _execute(self, scope, body, row):
        row.state = 'RUNNING'
        sent_input, http, retry_after = False, 500, ''
        chunks = bytearray()
        never_disconnect = asyncio.Event()

        async def receive_input():
            nonlocal sent_input
            if not sent_input:
                sent_input = True
                return {'type': 'http.request', 'body': body, 'more_body': False}
            await never_disconnect.wait()
            return {'type': 'http.disconnect'}

        async def collect(message):
            nonlocal http, retry_after
            if message['type'] == 'http.response.start':
                http = message['status']
                retry_after = dict(message.get('headers', [])).get(b'retry-after', b'').decode('ascii', 'ignore')
            elif message['type'] == 'http.response.body':
                chunks.extend(message.get('body', b''))
                if len(chunks) > self.store.max_body:
                    raise E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE,
                        'النتيجة تتجاوز مساحة الحفظ المؤقت؛ لم تُعرض نتيجة مبتورة.')
        try:
            await asyncio.wait_for(self.app(scope, receive_input, collect), self.execution_timeout)
            payload = json.loads(chunks)
            if not isinstance(payload, dict) or (http < 300 and not isinstance(payload.get('building'), dict)):
                raise E.AcsApiError(E.ACS_INTERNAL, 'لم يعد الخادم نتيجة مكتملة قابلة للاستعادة.')
            self.store.finish(row, http, bytes(chunks), retry_after)
        except BaseException as exc:
            if isinstance(exc, asyncio.CancelledError):
                error = E.AcsApiError(E.ACS_TIMEOUT, 'انقطع تشغيل الخادم قبل حفظ النتيجة. لم يُعَد التوليد تلقائياً.')
            elif isinstance(exc, TimeoutError):
                error = E.AcsApiError(E.ACS_TIMEOUT)
            elif isinstance(exc, E.AcsApiError):
                error = exc
            else:
                error = E.AcsApiError(E.ACS_INTERNAL)
            self.store.finish(row, error.status, _json(error.envelope(row.request_id)),
                              str(error.retry_after or ''))
