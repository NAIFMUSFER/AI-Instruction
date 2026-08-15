# -*- coding: utf-8 -*-
"""بيئة قياس واحدة لاستجابة حلقة الأحداث تحت أثقل حمل مقبول (KI-14).

لماذا خادم asyncio حقيقيّ لا محاكاة
------------------------------------
السؤال «هل يحجب هذا النداء حلقة الأحداث؟» سؤالٌ عن asyncio لا عن FastAPI:
تعليمةٌ متزامنة داخل `async def` تحجب الحلقة أيّاً كان الإطار فوقها. ولذلك
يُبنى هنا خادم HTTP حقيقيّ بـ`asyncio.start_server`، تُخدَم منه المسارات
الخفيفة من كوروتينات، ويُستدعى فيه **مدقّق الرفع المشحون نفسه**
(`acs_upload_security`) بالطريقتين: كما يستدعيه الخادم اليوم (متزامناً داخل
الكوروتين)، وكما سيستدعيه بعد الإصلاح (عبر منفّذ محدود).

FastAPI و uvicorn غير مثبَّتين في هذا الصندوق (PyPI يردّ 403)، فلا يُدّعى هنا
قياسٌ لتوجيه FastAPI. المقيس: الحلقة نفسها، والمدقّق نفسه، وزمن الاستجابة
الفعليّ لطلبات خفيفة متزامنة — وهي كل ما يحتاجه سؤال KI-14.

المقاييس المُخرَجة لكل تشغيل:
    p50 · p95 · p99 · max لزمن الطلب الخفيف
    أطول توقّف لحلقة الأحداث (يقيسه راصدٌ ينام 10ms ويقيس الانحراف)
    زمن العملية الثقيلة نفسها
"""
import asyncio
import json
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

FIXTURES = os.environ.get("ACS_LOOP_FIXTURES", "/tmp/ai3/fx")

# عتبات القبول — معلنة هنا، لا تُخفَّض في مكان آخر بصمت.
MAX_STALL_MS = float(os.environ.get("ACS_ACCEPT_MAX_STALL_MS", "250"))
MAX_P95_MS = float(os.environ.get("ACS_ACCEPT_MAX_P95_MS", "500"))

_MON_TICK = 0.01          # الراصد ينام ١٠ms؛ ما زاد عن ذلك توقّفٌ للحلقة


class LoopMonitor(object):
    """يقيس أطول توقّف للحلقة. لا يقيس عمل نفسه: النوم ثم الانحراف عنه."""

    def __init__(self):
        self.max_stall_ms = 0.0
        self.samples = []
        self._run = False
        self._task = None

    async def _loop(self):
        prev = time.perf_counter()
        while self._run:
            await asyncio.sleep(_MON_TICK)
            now = time.perf_counter()
            drift = (now - prev - _MON_TICK) * 1000.0
            prev = now
            if drift > 0:
                self.samples.append(drift)
                if drift > self.max_stall_ms:
                    self.max_stall_ms = drift

    def start(self):
        self._run = True
        self._task = asyncio.ensure_future(self._loop())

    async def stop(self):
        self._run = False
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=1.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass


def pct(values, q):
    if not values:
        return None
    s = sorted(values)
    k = min(len(s) - 1, int(round((q / 100.0) * (len(s) - 1))))
    return s[k]


# ---------------------------------------------------------------------------
# خادم HTTP أدنى — حقيقيّ، على حلقة أحداث حقيقيّة.
# ---------------------------------------------------------------------------
class Probe(object):

    def __init__(self, heavy):
        """heavy(kind) -> coroutine تنفّذ العملية الثقيلة بالطريقة المطلوبة."""
        self.heavy = heavy
        self.server = None
        self.port = None
        self.health_hits = 0

    async def _handle(self, reader, writer):
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=30)
            if not line:
                writer.close()
                return
            parts = line.decode("latin-1").split()
            path = parts[1] if len(parts) > 1 else "/"
            # ترويسات ثم جسد إن وُجد
            length = 0
            while True:
                h = await asyncio.wait_for(reader.readline(), timeout=30)
                if h in (b"\r\n", b"\n", b""):
                    break
                if h.lower().startswith(b"content-length:"):
                    length = int(h.split(b":")[1].strip())
            body = await reader.readexactly(length) if length else b""

            if path in ("/health", "/ready", "/ping"):
                self.health_hits += 1
                payload = {"ok": True, "path": path}
            else:
                kind = path.strip("/").split("/")[-1]
                t0 = time.perf_counter()
                try:
                    out = await self.heavy(kind, body)
                    payload = {"ok": True, "kind": kind, "out": out,
                               "ms": round((time.perf_counter() - t0) * 1000, 1)}
                except Exception as exc:                        # noqa: BLE001
                    payload = {"ok": False, "kind": kind,
                               "error": type(exc).__name__,
                               "code": getattr(exc, "code", None),
                               "ms": round((time.perf_counter() - t0) * 1000, 1)}
            raw = json.dumps(payload).encode()
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                         b"Content-Length: " + str(len(raw)).encode()
                         + b"\r\nConnection: close\r\n\r\n" + raw)
            await writer.drain()
        except Exception:                                       # noqa: BLE001
            pass
        finally:
            try:
                writer.close()
            except Exception:                                   # noqa: BLE001
                pass

    async def start(self):
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def stop(self):
        if self.server:
            self.server.close()
            try:
                await self.server.wait_closed()
            except Exception:                                   # noqa: BLE001
                pass


async def _request(port, path, body=b"", timeout=60.0):
    t0 = time.perf_counter()
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    head = ("%s %s HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: %d\r\n"
            "Connection: close\r\n\r\n"
            % ("POST" if body else "GET", path, len(body))).encode()
    writer.write(head + body)
    await writer.drain()
    data = await asyncio.wait_for(reader.read(), timeout=timeout)
    writer.close()
    ms = (time.perf_counter() - t0) * 1000.0
    body_txt = data.split(b"\r\n\r\n", 1)[-1]
    try:
        parsed = json.loads(body_txt.decode())
    except Exception:                                           # noqa: BLE001
        parsed = None
    return ms, parsed


def _poll_thread(port, paths, interval, stop, out):
    """العميل الخفيف يعيش على **خيط آخر بحلقته الخاصّة**.

    لماذا هذا ضروريّ: أوّل نسخة من هذا القياس كانت تقصف من الحلقة نفسها،
    فأعطت p95 = 1.5 ms أثناء توقّف 461 ms — لأن الطلب المحجوب لا يستطيع أن
    **يبدأ** أصلاً، فلا يُحتسَب زمنه. العميل الحقيقي لا يشارك الخادم حلقته:
    طلبه يصل أثناء التوقّف وينتظر فيه. فالقياس الصادق يحتاج خيطاً منفصلاً.
    """
    import socket

    def one(path):
        t0 = time.perf_counter()
        s = socket.create_connection(("127.0.0.1", port), timeout=60)
        try:
            s.sendall(("GET %s HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                       "Connection: close\r\n\r\n" % path).encode())
            buf = b""
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
        finally:
            s.close()
        return (time.perf_counter() - t0) * 1000.0

    i = 0
    while not stop["v"]:
        path = paths[i % len(paths)]
        i += 1
        try:
            out.append(one(path))
        except Exception:                                       # noqa: BLE001
            out.append(float("inf"))
        time.sleep(interval)


async def measure(heavy, kind, payload, poll_paths=("/health", "/ready", "/ping"),
                  poll_interval=0.005, settle=0.25):
    """يشغّل العملية الثقيلة مرّة، ويقصف المسارات الخفيفة طوالها من خيط آخر.

    يعيد قاموس القياس. لا يطبع شيئاً: الطباعة عمل المستدعي.
    """
    import threading

    probe = Probe(heavy)
    await probe.start()
    mon = LoopMonitor()
    mon.start()
    await asyncio.sleep(settle)

    latencies = []
    stop = {"v": False}
    th = threading.Thread(target=_poll_thread,
                          args=(probe.port, list(poll_paths), poll_interval,
                                stop, latencies),
                          daemon=True)
    th.start()
    await asyncio.sleep(settle)
    base_max = mon.max_stall_ms
    mon.max_stall_ms = 0.0
    mon.samples = []
    latencies.clear()

    t0 = time.perf_counter()
    heavy_ms, heavy_out = await _request(probe.port, "/heavy/" + kind, payload,
                                         timeout=180.0)
    total_ms = (time.perf_counter() - t0) * 1000.0

    await asyncio.sleep(settle)
    stop["v"] = True
    # الراصد يتوقّف **قبل** الانضمام: `th.join` نداءٌ حاجب، ولو بقي الراصد
    # حيّاً لسجّل انتظارَ الانضمام نفسه توقّفاً للحلقة — وهو خطأ قياس لا عطل
    # في المقيس. (وقع فعلاً في أوّل تشغيل: ٥٠٠٠ms على حملٍ مدّته ١٣ms.)
    await mon.stop()
    await probe.stop()
    th.join(timeout=5.0)

    finite = [v for v in latencies if v != float("inf")]
    return {"kind": kind,
            "heavy_ms": round(heavy_ms, 1),
            "total_ms": round(total_ms, 1),
            "heavy_result": heavy_out,
            "light_requests": len(latencies),
            "light_failed": len(latencies) - len(finite),
            "p50": round(pct(finite, 50) or 0, 1),
            "p95": round(pct(finite, 95) or 0, 1),
            "p99": round(pct(finite, 99) or 0, 1),
            "max": round(max(finite) if finite else 0, 1),
            "mean": round(statistics.mean(finite), 1) if finite else 0,
            "stall_ms": round(mon.max_stall_ms, 1),
            "baseline_stall_ms": round(base_max, 1)}


def load_fixtures():
    """أثقل مدخلٍ **مقبول** لكل نوع. غير الموجود يُعلَن ولا يُختلَق."""
    out = {}
    for key, name, mode in (("image", "worst.png", "rb"),
                            ("pdf", "worst.pdf", "rb"),
                            ("json", "worst.json", "rb"),
                            ("dxf", "worst.dxf", "rb")):
        p = os.path.join(FIXTURES, name)
        out[key] = open(p, mode).read() if os.path.exists(p) else None
    return out


def row(title, m):
    return ("  %-26s heavy=%8.1f  p50=%6.1f  p95=%6.1f  p99=%7.1f  "
            "max=%8.1f  stall=%8.1f  n=%d"
            % (title, m["heavy_ms"], m["p50"], m["p95"], m["p99"],
               m["max"], m["stall_ms"], m["light_requests"]))
