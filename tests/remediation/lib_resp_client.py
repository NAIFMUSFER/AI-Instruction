# -*- coding: utf-8 -*-
"""عميل Redis أدنى ببروتوكول RESP على مقبس — بلا أي اعتماد خارجيّ.

لماذا لا `redis-py`: PyPI يردّ 403 في هذا الصندوق، بينما `redis-server` نفسه
مثبَّت. و`acs_rate_limit.RedisBackend` **لا يستورد redis إطلاقاً** — يقبل أي
كائن يكشف `eval`/`evalsha`/`script_load` (أو get/incr/pexpire/pttl). فهذا
الملفّ يملأ ذلك العقد بمقبس TCP حقيقيّ إلى خادم Redis حقيقيّ.

هذا ليس بديلاً ولا كعباً: الأوامر تُرسَل فعلاً، والنصّ يُنفَّذ في Redis فعلاً،
والذرّية التي تُقاس هي ذرّية Redis نفسها. ما لا يقدّمه: تجميع الاتصالات
وإعادة المحاولة والعنقود — وهي خصائص المكتبة لا خصائص العقد المقيس هنا.
"""
import socket
import threading


class RespError(Exception):
    pass


class RespClient(object):
    """اتصال واحد، محميّ بقفل — يكفي عاملاً واحداً."""

    def __init__(self, host="127.0.0.1", port=6379, timeout=5.0):
        self.host, self.port, self.timeout = host, int(port), float(timeout)
        self._lock = threading.RLock()
        self._sock = None
        self._buf = b""

    # ------------------------------------------------------------ اتصال ---
    def _connect(self):
        if self._sock is None:
            self._sock = socket.create_connection((self.host, self.port),
                                                  timeout=self.timeout)
            self._buf = b""
        return self._sock

    def close(self):
        with self._lock:
            if self._sock is not None:
                try:
                    self._sock.close()
                except Exception:                               # noqa: BLE001
                    pass
                self._sock = None

    # ------------------------------------------------------------ قراءة ---
    def _readline(self):
        while b"\r\n" not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise RespError("connection closed by redis")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\r\n", 1)
        return line

    def _readexact(self, n):
        while len(self._buf) < n + 2:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise RespError("connection closed by redis")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n + 2:]
        return out

    def _read(self):
        line = self._readline()
        tag, rest = line[:1], line[1:]
        if tag == b"+":
            return rest.decode()
        if tag == b"-":
            raise RespError(rest.decode())
        if tag == b":":
            return int(rest)
        if tag == b"$":
            n = int(rest)
            return None if n < 0 else self._readexact(n)
        if tag == b"*":
            n = int(rest)
            return None if n < 0 else [self._read() for _ in range(n)]
        raise RespError("unknown RESP tag %r" % tag)

    # ------------------------------------------------------------ أوامر ---
    def command(self, *parts):
        with self._lock:
            self._connect()
            out = [b"*%d\r\n" % len(parts)]
            for p in parts:
                if isinstance(p, str):
                    p = p.encode("utf-8")
                elif not isinstance(p, (bytes, bytearray)):
                    p = str(p).encode("ascii")
                out.append(b"$%d\r\n" % len(p))
                out.append(bytes(p))
                out.append(b"\r\n")
            self._sock.sendall(b"".join(out))
            return self._read()

    # -- العقد الذي يطلبه acs_rate_limit.RedisBackend -----------------------
    def ping(self):
        return self.command("PING")

    def script_load(self, script):
        v = self.command("SCRIPT", "LOAD", script)
        return v.decode() if isinstance(v, bytes) else v

    def evalsha(self, sha, numkeys, *args):
        return self.command("EVALSHA", sha, numkeys, *args)

    def eval(self, script, numkeys, *args):
        return self.command("EVAL", script, numkeys, *args)

    def get(self, key):
        return self.command("GET", key)

    def incr(self, key):
        return self.command("INCR", key)

    def pexpire(self, key, ms):
        return self.command("PEXPIRE", key, ms)

    def pttl(self, key):
        return self.command("PTTL", key)

    def flushdb(self):
        return self.command("FLUSHDB")
