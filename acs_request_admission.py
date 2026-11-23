"""Cheap bounded admission before external identity/auth work.

This is a process safety bound, not the paid-operation quota. It never keys on
bearer tokens or untrusted forwarded IP headers. Production's single-instance
invariant or distributed paid limiter remains required independently.
"""
from __future__ import annotations
import asyncio
from collections import OrderedDict
import threading
import time


class AdmissionRejected(Exception):
    def __init__(self, status):
        self.status = status
        self.code = 'ACS_RATE_LIMITED' if status == 429 else 'ACS_AUTH_UNAVAILABLE'


class AdmissionGate:
    def __init__(self, *, concurrency=16, per_minute=120, global_per_minute=1200,
                 max_peers=4096, clock=time.monotonic):
        self.concurrency, self.per_minute = concurrency, per_minute
        self.global_per_minute, self.max_peers = global_per_minute, max_peers
        self.clock, self.lock = clock, threading.Lock()
        self.peers, self.active = OrderedDict(), 0
        self.global_window, self.global_count = clock(), 0

    def acquire(self, scope):
        # socket peer only. Reverse proxies require an explicit trusted-proxy
        # configuration before forwarded headers may become identity inputs.
        peer = str((scope.get('client') or ('unknown',))[0])[:256]
        with self.lock:
            now = self.clock()
            if now-self.global_window >= 60:
                self.global_window, self.global_count = now, 0
            while self.peers and next(iter(self.peers.values()))[0] <= now-60:
                self.peers.popitem(last=False)
            prior = self.peers.get(peer)
            count = prior[1] if prior and now-prior[0] < 60 else 0
            if count >= self.per_minute or self.global_count >= self.global_per_minute:
                raise AdmissionRejected(429)
            if prior is None and len(self.peers) >= self.max_peers:
                # No eviction of live quota windows: new identities fail closed.
                raise AdmissionRejected(429)
            self.peers[peer] = (prior[0] if count else now, count+1)
            if not count:
                self.peers.move_to_end(peer)
            self.global_count += 1
            if self.active >= self.concurrency:
                raise AdmissionRejected(503)
            self.active += 1
        return self.release

    def release(self):
        with self.lock:
            self.active -= 1


GATE = AdmissionGate()


async def run(scope, function, *args, **kwargs):
    """A cancelled HTTP task cannot release a still-running outbound slot."""
    release = GATE.acquire(scope)
    def worker():
        try:
            return function(*args, **kwargs)
        finally:
            release()
    # Shield preserves the thread-owned permit until actual completion. The
    # configured urllib timeout bounds that work independently of the client.
    task = asyncio.create_task(asyncio.to_thread(worker))
    def observe(done):
        if not done.cancelled():
            done.exception()  # consume an error when the HTTP caller disconnected
    task.add_done_callback(observe)
    return await asyncio.shield(task)
