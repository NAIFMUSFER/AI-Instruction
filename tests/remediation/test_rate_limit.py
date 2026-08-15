# -*- coding: utf-8 -*-
"""انحدار حدّ المعدّل — «الحدّ موجود، والحصّة مضاعفة، والذاكرة تنمو».

هذا الملف يعيد إنتاج أربعة أعطال في acs_understand_api.py بالحساب الصريح،
ثمّ يُثبت أن acs_rate_limit.py يُزيلها. الأعطال بالكامل:

  1. `_hits = defaultdict(deque)` محليّ داخل العملية. نسختان من الواجهة
     ⇒ حِصّتان مستقلّتان ⇒ الحدّ 8/ساعة صار 16/ساعة فعلياً؛ وإعادة التشغيل
     تمسح كل شيء. يُعاد إنتاجه صراحةً في القسم A.
  2. تنظيف `len(_hits) > 4000` لا يحذف إلا الطوابير الفارغة، فتدوير هويّات
     مزوّرة يُنمّي الذاكرة بلا حدّ طول النافذة كاملةً. القسم I.
  3. `x-real-ip` تُقرأ بلا أي حساب للقفزات الموثوقة ⇒ تجاوز كامل للحدّ
     بترويسة يكتبها العميل نفسه في كل طلب. القسم H.
  4. `int(os.environ.get("ACS_TRUSTED_PROXIES", "1"))` يرمي ValueError على
     السلسلة الفارغة التي يشحنها .env.example:17 ⇒ الخادم لا يُقلع. القسم H.

كل شيء هنا بساعة محقونة (Clock): لا نوم، لا شبكة، لا Redis حقيقي.
FakeRedis يُنفّذ نفس سطح الأوامر الذي يستعمله RedisBackend بنفس دلالات
الانتهاء، وتحت قفل واحد لكل EVAL — أي أنه يُحاكي ذرّية السكربت، ولا يُفسّر
لغة Lua. تكامل Redis حقيقي غير مُتحقَّق منه هنا (لا شبكة في هذه البيئة).
"""
import json
import os
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_rate_limit as RL                                       # noqa: E402

# ---------------------------------------------------------------- preflight --
_REQUIRED = ('RateLimitBackend', 'MemoryBackend', 'RedisBackend',
             'RateLimiter', 'make_backend', 'client_identity',
             'health_status', 'RateLimitBackendUnavailable', 'LUA_HIT',
             'SCOPE_GLOBAL_DAY', 'SCOPE_GEN_HOUR', 'SCOPE_GEN_DAY',
             'SCOPE_EDIT_HOUR', 'SCOPE_BACKEND', 'SCOPE_EVICTED',
             'trusted_hops', 'normalise_ip', 'limits_from_env',
             'fail_policy_from_env', 'DEFAULT_LIMITS', 'UNKNOWN_IDENTITY')
_missing = [s for s in _REQUIRED if not hasattr(RL, s)]
if _missing:
    print('RATE LIMIT REGRESSION: CANNOT RUN — PARTIALLY MERGED TREE')
    print('  acs_rate_limit.py is missing: %s' % ', '.join(_missing))
    print('  this test and acs_rate_limit.py come from different deliveries.')
    sys.exit(1)

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s %s' % (name, detail))


def raises(fn, exc_type):
    try:
        fn()
    except exc_type:
        return True
    except Exception:
        return False
    return False


# ---------------------------------------------------------------------------
# ساعة محقونة — كل قرار حتميّ، ولا ثانية نوم واحدة في هذا الملف.
# ---------------------------------------------------------------------------
class Clock(object):
    def __init__(self, t=1700000000.0):
        self._t = float(t)
        self._lock = threading.Lock()

    def now(self):
        with self._lock:
            return self._t

    def advance(self, seconds):
        with self._lock:
            self._t += float(seconds)


# ---------------------------------------------------------------------------
# FakeRedis — بديل داخل العملية لنفس سطح الأوامر الذي يستعمله RedisBackend:
#   GET / INCR / PEXPIRE / PTTL / PING / SCRIPT LOAD / EVAL / EVALSHA
# دلالات الانتهاء مقودة بالساعة المحقونة، لا بساعة النظام.
# eval/evalsha تُنفّذان نفس تسلسل LUA_HIT تحت قفل واحد: محاكاة ذرّية السكربت
# (وهي ما يهمّ الاختبار)، لا تفسيرٌ للغة Lua.
# GET تُعيد bytes كما يفعل عميل redis الحقيقي، كي يُختبر تحويل الأنواع فعلاً.
# ---------------------------------------------------------------------------
class FakeRedis(object):

    def __init__(self, clock):
        self.clock = clock
        self._lock = threading.RLock()
        self._data = {}          # key -> [int value, expires_at_s or None]
        self._scripts = {}       # sha -> script text
        self.calls = {'get': 0, 'incr': 0, 'pexpire': 0, 'pttl': 0,
                      'eval': 0, 'evalsha': 0, 'script_load': 0}

    def _reap(self, key):
        """يُنادى والقفل مأخوذ."""
        rec = self._data.get(key)
        if rec is not None and rec[1] is not None \
                and rec[1] <= self.clock.now():
            del self._data[key]

    # -- سطح الأوامر --------------------------------------------------------
    def get(self, key):
        with self._lock:
            self.calls['get'] += 1
            self._reap(key)
            rec = self._data.get(key)
            return None if rec is None else str(rec[0]).encode('ascii')

    def incr(self, key):
        with self._lock:
            self.calls['incr'] += 1
            self._reap(key)
            rec = self._data.get(key)
            if rec is None:
                rec = [0, None]
                self._data[key] = rec
            rec[0] += 1
            return rec[0]

    def pexpire(self, key, ms):
        with self._lock:
            self.calls['pexpire'] += 1
            self._reap(key)
            rec = self._data.get(key)
            if rec is None:
                return 0
            rec[1] = self.clock.now() + (float(ms) / 1000.0)
            return 1

    def pttl(self, key):
        with self._lock:
            self.calls['pttl'] += 1
            self._reap(key)
            rec = self._data.get(key)
            if rec is None:
                return -2                     # لا مفتاح
            if rec[1] is None:
                return -1                     # مفتاح بلا انتهاء صلاحية
            return int(round((rec[1] - self.clock.now()) * 1000.0))

    def ping(self):
        return True

    def script_load(self, script):
        import hashlib
        with self._lock:
            self.calls['script_load'] += 1
            sha = hashlib.sha1(script.encode('utf-8')).hexdigest()
            self._scripts[sha] = script
            return sha

    def evalsha(self, sha, numkeys, *args):
        with self._lock:
            self.calls['evalsha'] += 1
            script = self._scripts.get(sha)
            if script is None:
                raise RuntimeError('NOSCRIPT No matching script.')
            return self._exec(script, numkeys, args)

    def eval(self, script, numkeys, *args):
        with self._lock:
            self.calls['eval'] += 1
            return self._exec(script, numkeys, args)

    # -- تنفيذ LUA_HIT بنفس ترتيبه، ذرّياً تحت قفل واحد ----------------------
    def _exec(self, script, numkeys, args):
        if script.strip() != RL.LUA_HIT.strip():
            raise RuntimeError('FakeRedis implements LUA_HIT only; the module '
                               'changed its script without updating the test')
        key = list(args[:numkeys])[0]
        argv = list(args[numkeys:])
        limit, window_ms, consume = int(argv[0]), int(argv[1]), int(argv[2])
        self._reap(key)
        rec = self._data.get(key)
        count = 0 if rec is None else rec[0]
        if count >= limit:
            pttl = self.pttl(key)
            return [0, window_ms if pttl < 0 else pttl, count]
        if consume == 1:
            count = self.incr(key)
            if count == 1:
                self.pexpire(key, window_ms)
        pttl = self.pttl(key)
        return [1, window_ms if pttl < 0 else pttl, count]

    # -- تشخيص للاختبار -----------------------------------------------------
    def live_keys(self):
        with self._lock:
            for k in list(self._data):
                self._reap(k)
            return sorted(self._data)

    def keys_without_expiry(self):
        with self._lock:
            return [k for k, v in self._data.items() if v[1] is None]


class ClientView(object):
    """يكشف مجموعةً محدّدة من أوامر FakeRedis فقط.

    يُحاكي عميلاً أو خادماً مُداراً يمنع السكربتات: الغياب هنا غيابٌ حقيقي
    (hasattr يُرجع False)، لا سمة قيمتها None.
    """

    def __init__(self, inner, allow):
        self.inner = inner
        for name in allow:
            setattr(self, name, getattr(inner, name))


class RaisingBackend(RL.RateLimitBackend):
    """واجهة خلفية تسقط في كل طلب — لاختبار سياسة الفشل."""
    name = 'redis'
    distributed = True

    def __init__(self):
        self.hits = 0

    def hit(self, key, limit, window_s, now, consume=True):
        self.hits += 1
        raise RL.BackendOperationError(
            'Error 111 connecting to cache.internal:6380. Connection refused.')

    def healthy(self):
        return False


class RaisingClient(object):
    """عميل Redis يرمي — لاختبار أن RedisBackend يُترجم العطل ولا يُسرّبه."""

    def eval(self, *a, **k):
        raise RuntimeError('Error 111 connecting to cache.internal:6380')

    def evalsha(self, *a, **k):
        raise RuntimeError('Error 111 connecting to cache.internal:6380')

    def script_load(self, *a, **k):
        raise RuntimeError('Error 111 connecting to cache.internal:6380')

    def ping(self):
        raise RuntimeError('Error 111 connecting to cache.internal:6380')


class ShapeShifter(object):
    """عميل يُعيد شكلاً غير متوقَّع — يجب أن يُترجم إلى قرار لا إلى 500."""

    def eval(self, *a, **k):
        return 'not a list at all'

    def ping(self):
        return True


BIG = {'gen_hour': 10 ** 6, 'gen_day': 10 ** 6, 'edit_hour': 10 ** 6,
       'global_day': 10 ** 6}


def limits(**over):
    out = dict(BIG)
    out.update(over)
    return out


def redis_limiter(client, **over):
    return RL.RateLimiter(backend=RL.RedisBackend(client),
                          limits=limits(**over),
                          fail_policy=RL.FAIL_CLOSED)


def memory_limiter(max_keys=20000, **over):
    return RL.RateLimiter(backend=RL.MemoryBackend(max_keys=max_keys),
                          limits=limits(**over), fail_policy=RL.FAIL_CLOSED)


# ===========================================================================
print('\n== A · THE DEFECT REPRODUCED: A PROCESS-LOCAL QUOTA IS DOUBLED ==')
c = Clock()
a_mem = RL.RateLimiter(backend=RL.MemoryBackend(), limits=limits(gen_hour=8))
b_mem = RL.RateLimiter(backend=RL.MemoryBackend(), limits=limits(gen_hour=8))
allowed_local = 0
for i in range(16):
    inst = a_mem if i % 2 == 0 else b_mem
    if inst.check('1.2.3.4', 'gen', now=c.now())['allowed']:
        allowed_local += 1
chk('two PROCESS-LOCAL limiters let 16 requests through a limit of 8 — this '
    'is exactly the production defect', allowed_local == 16,
    'allowed=%d' % allowed_local)

fake = FakeRedis(c)
a_red = redis_limiter(fake, gen_hour=8)
b_red = redis_limiter(fake, gen_hour=8)
chk('the two limiters are genuinely independent objects over one store',
    a_red is not b_red and a_red.backend is not b_red.backend)
allowed_shared = 0
for i in range(16):
    inst = a_red if i % 2 == 0 else b_red
    if inst.check('1.2.3.4', 'gen', now=c.now())['allowed']:
        allowed_shared += 1
chk('(a) two API instances over ONE shared store enforce ONE quota of 8',
    allowed_shared == 8, 'allowed=%d' % allowed_shared)
d = b_red.check('1.2.3.4', 'gen', now=c.now())
chk('the refusal carries the 429 code, the scope and a Retry-After',
    d['allowed'] is False and d['code'] == RL.ACS_RATE_LIMITED
    and d['scope'] == RL.SCOPE_GEN_HOUR and d['retry_after'] > 0, str(d))
chk('the refusal message is Arabic and user-facing',
    isinstance(d['message'], str) and 'توليد' in d['message'])
chk('the decision carries the effective limits for the caller to echo',
    d['limits']['gen_hour'] == 8)
chk('every counter Redis holds carries an expiry — no immortal keys',
    fake.live_keys() and not fake.keys_without_expiry(),
    str(fake.keys_without_expiry()))

# ===========================================================================
print('\n== B · RESTART RETENTION: A NEW PROCESS DOES NOT REFUND THE QUOTA ==')
c = Clock()
fake = FakeRedis(c)
lim_a = redis_limiter(fake, gen_hour=3)
spent = sum(1 for _ in range(3)
            if lim_a.check('9.9.9.9', 'gen', now=c.now())['allowed'])
chk('limiter A spends the whole quota of 3', spent == 3, 'spent=%d' % spent)
del lim_a                                     # «إعادة تشغيل العملية»
lim_b = redis_limiter(fake, gen_hour=3)       # نسخة جديدة تماماً، نفس المخزن
d = lim_b.check('9.9.9.9', 'gen', now=c.now())
chk('(b) a brand-new RateLimiter over the same store still refuses — the '
    'quota survived the restart',
    d['allowed'] is False and d['scope'] == RL.SCOPE_GEN_HOUR, str(d))
chk('the surviving Retry-After is still bounded by the hour window',
    0 < d['retry_after'] <= RL.WINDOW_HOUR, str(d['retry_after']))
chk('by contrast a restarted MEMORY limiter refunds the quota in full — '
    'why a restart used to reset every visitor',
    RL.RateLimiter(backend=RL.MemoryBackend(),
                   limits=limits(gen_hour=3)).check(
        '9.9.9.9', 'gen', now=c.now())['allowed'] is True)

# ===========================================================================
print('\n== C · IDENTITIES ARE ISOLATED ==')
for label in ('memory', 'redis'):
    c = Clock()
    lim = memory_limiter(gen_hour=2) if label == 'memory' \
        else redis_limiter(FakeRedis(c), gen_hour=2)
    res = {}
    for who in ('10.0.0.1', '10.0.0.2', '2001:db8::1'):
        res[who] = [lim.check(who, 'gen', now=c.now())['allowed']
                    for _ in range(3)]
    chk('(c) %s: each identity gets its own 2, and only its own 3rd is '
        'refused' % label,
        all(v == [True, True, False] for v in res.values()), str(res))
    chk('%s: exhausting one identity does not touch another' % label,
        lim.check('10.0.0.9', 'gen', now=c.now())['allowed'] is True)
    chk('%s: the gen and edit ledgers are separate scopes' % label,
        lim.check('10.0.0.1', 'edit', now=c.now())['allowed'] is True)

# ===========================================================================
print('\n== D · THE GLOBAL DAILY CAP, CONSUMED LAST ==')
c = Clock()
lim = memory_limiter(global_day=3)
seq = [lim.check('7.7.7.%d' % i, 'gen', now=c.now()) for i in range(4)]
chk('(d) the global daily cap refuses the 4th request server-wide',
    [s['allowed'] for s in seq] == [True, True, True, False],
    str([s['allowed'] for s in seq]))
chk('the global refusal names the global scope and the Arabic message',
    seq[3]['scope'] == RL.SCOPE_GLOBAL_DAY
    and 'سقفه اليومي' in seq[3]['message'], str(seq[3]))
chk('the global Retry-After is bounded by the day window',
    0 < seq[3]['retry_after'] <= RL.WINDOW_DAY, str(seq[3]['retry_after']))

c = Clock()
lim = memory_limiter(gen_hour=1, global_day=50)
lim.check('5.5.5.5', 'gen', now=c.now())
chk('one accepted request consumed exactly one unit of the global cap',
    lim.peek(RL.SCOPE_GLOBAL_DAY, now=c.now()) == 1,
    'global=%d' % lim.peek(RL.SCOPE_GLOBAL_DAY, now=c.now()))
refused = lim.check('5.5.5.5', 'gen', now=c.now())
chk('(d) a per-identity refusal does NOT consume the global cap — one '
    'abusive visitor cannot switch the service off for everyone',
    refused['allowed'] is False
    and lim.peek(RL.SCOPE_GLOBAL_DAY, now=c.now()) == 1,
    'global=%d' % lim.peek(RL.SCOPE_GLOBAL_DAY, now=c.now()))
for _ in range(20):
    lim.check('5.5.5.5', 'gen', now=c.now())
chk('twenty further refusals still leave the global cap at 1',
    lim.peek(RL.SCOPE_GLOBAL_DAY, now=c.now()) == 1,
    'global=%d' % lim.peek(RL.SCOPE_GLOBAL_DAY, now=c.now()))
lim.check('6.6.6.6', 'gen', now=c.now())
chk('another visitor passing its own checks does consume the global cap',
    lim.peek(RL.SCOPE_GLOBAL_DAY, now=c.now()) == 2,
    'global=%d' % lim.peek(RL.SCOPE_GLOBAL_DAY, now=c.now()))

# ===========================================================================
print('\n== E · CONCURRENCY: N THREADS AT A LIMIT OF M ALLOW EXACTLY M ==')
N_THREADS = 48
M_LIMIT = 7


def hammer(limiter, clock, ident='8.8.8.8', n=N_THREADS, distinct=False):
    barrier = threading.Barrier(n)
    out = []
    out_lock = threading.Lock()

    def worker(i):
        who = ('11.0.0.%d' % i) if distinct else ident
        barrier.wait()
        d = limiter.check(who, 'gen', now=clock.now())
        with out_lock:
            out.append(bool(d['allowed']))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return out


c = Clock()
res = hammer(memory_limiter(gen_hour=M_LIMIT), c)
chk('(e) memory backend: %d threads, limit %d ⇒ exactly %d allowed, no '
    'overshoot' % (N_THREADS, M_LIMIT, M_LIMIT),
    len(res) == N_THREADS and sum(res) == M_LIMIT,
    'allowed=%d of %d' % (sum(res), len(res)))

c = Clock()
fake = FakeRedis(c)
res = hammer(redis_limiter(fake, gen_hour=M_LIMIT), c)
chk('(e) FakeRedis backend: %d threads, limit %d ⇒ exactly %d allowed'
    % (N_THREADS, M_LIMIT, M_LIMIT),
    len(res) == N_THREADS and sum(res) == M_LIMIT,
    'allowed=%d of %d' % (sum(res), len(res)))
chk('the atomic primitive never let the counter pass the limit',
    RL._as_int(fake.get('acs:rl:v1:gen_hour:8.8.8.8')) == M_LIMIT,
    str(fake.get('acs:rl:v1:gen_hour:8.8.8.8')))
chk('the decision really went through the single-round-trip EVALSHA path',
    fake.calls['evalsha'] > 0 and fake.calls['eval'] == 0, str(fake.calls))

c = Clock()
fake = FakeRedis(c)
res = hammer(redis_limiter(fake, global_day=M_LIMIT), c, distinct=True)
chk('(e) the global cap also holds exactly under %d concurrent DISTINCT '
    'identities' % N_THREADS, sum(res) == M_LIMIT, 'allowed=%d' % sum(res))

# ===========================================================================
print('\n== F · RETRY-AFTER IS TRUE, BOUNDED, AND SHRINKS ==')
for label in ('memory', 'redis'):
    c = Clock()
    lim = memory_limiter(gen_hour=1) if label == 'memory' \
        else redis_limiter(FakeRedis(c), gen_hour=1)
    lim.check('4.4.4.4', 'gen', now=c.now())
    first = lim.check('4.4.4.4', 'gen', now=c.now())
    chk('(f) %s: after refusal Retry-After is > 0 and ≤ the window' % label,
        first['allowed'] is False
        and 0 < first['retry_after'] <= RL.WINDOW_HOUR,
        str(first['retry_after']))
    seen = [first['retry_after']]
    for _ in range(5):
        c.advance(600)
        seen.append(lim.check('4.4.4.4', 'gen', now=c.now())['retry_after'])
    chk('(f) %s: it shrinks monotonically as the clock advances' % label,
        all(seen[i] > seen[i + 1] for i in range(len(seen) - 1)), str(seen))
    chk('%s: it never advertises a wait longer than the window' % label,
        max(seen) <= RL.WINDOW_HOUR, str(max(seen)))
    chk('%s: a flood of refusals does not extend the wait (no rolling ban)'
        % label,
        lim.check('4.4.4.4', 'gen', now=c.now())['retry_after'] <= seen[-1])

# ===========================================================================
print('\n== G · COUNTERS EXPIRE — THE QUOTA COMES BACK ==')
for label in ('memory', 'redis'):
    c = Clock()
    store = None
    if label == 'memory':
        lim = memory_limiter(gen_hour=2)
    else:
        store = FakeRedis(c)
        lim = redis_limiter(store, gen_hour=2)
    got = [lim.check('3.3.3.3', 'gen', now=c.now())['allowed']
           for _ in range(3)]
    chk('(g) %s: the window is spent after 2' % label,
        got == [True, True, False], str(got))
    c.advance(RL.WINDOW_HOUR - 10)
    chk('%s: still refused 10 s before the window ends' % label,
        lim.check('3.3.3.3', 'gen', now=c.now())['allowed'] is False)
    c.advance(20)
    if store is not None:
        chk('%s: the counter key genuinely EXPIRED out of the store, it was '
            'not merely reset' % label,
            'acs:rl:v1:gen_hour:3.3.3.3' not in store.live_keys(),
            str(store.live_keys()))
    after = [lim.check('3.3.3.3', 'gen', now=c.now())['allowed']
             for _ in range(3)]
    chk('(g) %s: once the window elapses the FULL quota is available again'
        % label, after == [True, True, False], str(after))

c = Clock()
lim = memory_limiter(gen_hour=2, gen_day=3)
for _ in range(2):
    lim.check('3.3.3.4', 'gen', now=c.now())
c.advance(RL.WINDOW_HOUR + 5)
decs = [lim.check('3.3.3.4', 'gen', now=c.now()) for _ in range(2)]
chk('the hour window resetting does NOT reset the day window',
    [d['allowed'] for d in decs] == [True, False]
    and decs[1]['scope'] == RL.SCOPE_GEN_DAY, str(decs[1]))

# ===========================================================================
print('\n== H · MALFORMED PROXY HEADERS CANNOT MINT A FRESH BUCKET ==')
PEER = '203.0.113.9'
DEFAULT_ENV = {}          # لا متغيّرات مضبوطة: ACS_TRUSTED_PROXIES = 1 ضمناً


def ident(headers, peer=PEER, env=None):
    return RL.client_identity(headers, peer,
                              env=DEFAULT_ENV if env is None else env)


chk('the trusted hop is read RIGHT-to-left, not left-to-right',
    ident({'X-Forwarded-For': '1.2.3.4, %s' % PEER}) == PEER)
cases = {
    'spoofed leading XFF (client writes 1.2.3.4, the proxy appends the peer)':
        {'X-Forwarded-For': '1.2.3.4, %s' % PEER},
    'a whole spoofed chain with the real hop last':
        {'X-Forwarded-For': '9.9.9.9, 8.8.8.8, 7.7.7.7, %s' % PEER},
    'X-Real-IP alone — ignored by default':
        {'X-Real-IP': '66.66.66.66'},
    'X-Real-IP alongside a valid XFF — still ignored':
        {'X-Forwarded-For': '1.2.3.4, %s' % PEER,
         'X-Real-IP': '66.66.66.66'},
    'a 10 KB header value':
        {'X-Forwarded-For': ', '.join(['1.2.3.4'] * 1250)},
    'a 10 KB single token':
        {'X-Forwarded-For': '1' * 10240},
    'a 10 KB X-Real-IP':
        {'X-Real-IP': '1' * 10240},
    'embedded CRLF (header injection attempt)':
        {'X-Forwarded-For': '1.2.3.4\r\nX-Real-IP: 66.66.66.66'},
    'embedded bare newline':
        {'X-Forwarded-For': 'evil\n1.2.3.4'},
    'a NUL byte':
        {'X-Forwarded-For': '1.2.3.4\x00'},
    'a tab':
        {'X-Forwarded-For': '1.2.3.4\t, 5.6.7.8'},
    'a non-IP token':
        {'X-Forwarded-For': 'not-an-ip-at-all'},
    'a hostname':
        {'X-Forwarded-For': 'attacker.example.com'},
    'an empty XFF':
        {'X-Forwarded-For': '   '},
    'commas only':
        {'X-Forwarded-For': ',,,,'},
    'hop-count stuffing (40 short hops)':
        {'X-Forwarded-For': ', '.join(['1.2.3.4'] * 40)},
    'an out-of-range octet':
        {'X-Forwarded-For': '999.999.999.999'},
    'no headers at all': {},
}
bad = [k for k, h in cases.items() if ident(h) != PEER]
chk('(h) all %d malformed / spoofed header shapes resolve to the PEER '
    'address' % len(cases), not bad, '; '.join(bad[:3]))

# ملاحظة على نموذج التهديد: ACS_TRUSTED_PROXIES=1 يعني إقراراً بأن وكيلاً
# موثوقاً واحداً يقف أمام الخادم ويُلحق عنوان نظيره بـ XFF دائماً. فالعنصر
# الأخير هو ما كتبه الوكيل، وكلّ ما قبله يكتبه العميل. الشكل الذي يصل فعلاً
# إلى نشرٍ صحيح هو «<مزوَّر>, <النظير>» — وهذا ما نُدوّره هنا.
rotated = {ident({'X-Forwarded-For': '198.51.100.%d, %s' % (i % 250, PEER)})
           for i in range(500)}
chk('(h) 500 rotating spoofed XFF prefixes collapse to ONE identity, not '
    '500 buckets', rotated == {PEER}, str(sorted(rotated)[:4]))
rotated = {ident({'X-Real-IP': '198.51.100.%d' % (i % 250)})
           for i in range(500)}
chk('(h) 500 rotating spoofed X-Real-IP values collapse to ONE identity',
    rotated == {PEER}, str(sorted(rotated)[:4]))
rotated = {RL.client_identity({'X-Forwarded-For': '198.51.100.%d' % (i % 250),
                               'X-Real-IP': '192.0.2.%d' % (i % 250)}, PEER,
                              env={'ACS_TRUSTED_PROXIES': '0'})
           for i in range(500)}
chk('(h) with NO trusted proxy declared, 500 rotating XFF/X-Real-IP values '
    'collapse to ONE identity as well', rotated == {PEER},
    str(sorted(rotated)[:4]))

c = Clock()
lim = memory_limiter(gen_hour=4)
allowed = 0
for i in range(500):
    who = ident({'X-Forwarded-For': '198.51.100.%d, %s' % (i % 250, PEER),
                 'X-Real-IP': '192.0.2.%d' % (i % 250)})
    if lim.check(who, 'gen', now=c.now())['allowed']:
        allowed += 1
chk('(h) end to end: 500 header-spoofed requests get exactly 4 through a '
    'limit of 4 — the old x-real-ip path would have granted all 500',
    allowed == 4, 'allowed=%d' % allowed)

chk('ACS_TRUSTED_PROXIES=2 reads the second hop from the right',
    RL.client_identity({'X-Forwarded-For': '1.2.3.4, 5.6.7.8, %s' % PEER},
                       PEER, env={'ACS_TRUSTED_PROXIES': '2'}) == '5.6.7.8')
chk('hops=0 means no proxy is trusted: XFF is ignored entirely',
    RL.client_identity({'X-Forwarded-For': '1.2.3.4, 5.6.7.8'}, PEER,
                       env={'ACS_TRUSTED_PROXIES': '0'}) == PEER)
chk('more hops declared than present clamps to the leftmost, never past the '
    'end of the list',
    RL.client_identity({'X-Forwarded-For': '1.2.3.4, %s' % PEER}, PEER,
                       env={'ACS_TRUSTED_PROXIES': '9'}) == '1.2.3.4')
chk('X-Real-IP is honoured ONLY behind the explicit opt-in flag',
    RL.client_identity({'X-Real-IP': '66.66.66.66'}, PEER,
                       env={'ACS_TRUST_X_REAL_IP': '1',
                            'ACS_TRUSTED_PROXIES': '0'}) == '66.66.66.66'
    and RL.client_identity({'X-Real-IP': '66.66.66.66'}, PEER,
                           env={'ACS_TRUSTED_PROXIES': '0'}) == PEER)
chk('even opted in, a malformed X-Real-IP falls back to the peer',
    RL.client_identity({'X-Real-IP': 'not-an-ip'}, PEER,
                       env={'ACS_TRUST_X_REAL_IP': '1',
                            'ACS_TRUSTED_PROXIES': '0'}) == PEER)

try:
    int(os.environ.get('X_UNSET_ON_PURPOSE', ''), 10)
    empty_raises = False
except ValueError:
    empty_raises = True
chk('bare int("") really does raise — this IS the .env.example:17 boot crash',
    empty_raises)
ok = True
for bad_val in ('', '   ', 'abc', 'NaN', '1.5', '-4', None):
    env = {} if bad_val is None else {'ACS_TRUSTED_PROXIES': bad_val}
    try:
        got = RL.trusted_hops(env)
        if not isinstance(got, int) or got < 0:
            ok = False
    except Exception:
        ok = False
chk('(h) trusted_hops() tolerates "", whitespace, garbage, negatives and '
    'absence — no ValueError at import, the server boots', ok)
chk('and the empty string specifically yields the documented default of 1',
    RL.trusted_hops({'ACS_TRUSTED_PROXIES': ''}) == 1
    and RL.trusted_hops({}) == 1)
chk('every env int reader is equally tolerant',
    RL.env_int('X', 5, {'X': ''}) == 5 and RL.env_int('X', 5, {'X': 'zz'}) == 5
    and RL.env_int('X', 5, {}) == 5 and RL.env_int('X', 5, {'X': '9'}) == 9)
chk('limits_from_env survives an entirely empty .env',
    RL.limits_from_env({'ACS_RL_GEN_HOUR': '', 'ACS_RL_GEN_DAY': '',
                        'ACS_RL_EDIT_HOUR': '', 'ACS_RL_GLOBAL_DAY': ''})
    == RL.DEFAULT_LIMITS, str(RL.limits_from_env({})))
chk('the shipped defaults still are 8 / 25 / 30 / 400 — no limit was '
    'weakened by this remediation',
    RL.DEFAULT_LIMITS == {'gen_hour': 8, 'gen_day': 25, 'edit_hour': 30,
                          'global_day': 400})
chk('IPv6 and bracketed / ported forms normalise to ONE canonical identity',
    RL.normalise_ip('[2001:db8::1]:443') == '2001:db8::1'
    and RL.normalise_ip('2001:0db8:0000::0001') == '2001:db8::1'
    and RL.normalise_ip('192.0.2.7:5555') == '192.0.2.7')
chk('a missing or garbage peer never crashes and never mints a bucket per '
    'request',
    ident({}, peer=None) == RL.UNKNOWN_IDENTITY
    and ident({}, peer='garbage') == RL.UNKNOWN_IDENTITY)
chk('header names are matched case-insensitively',
    ident({'x-forwarded-for': '1.2.3.4, %s' % PEER}) == PEER
    and ident({'X-FORWARDED-FOR': '1.2.3.4, 5.6.7.8'}) == '5.6.7.8')
chk('bytes headers do not crash the pure function',
    ident({b'X-Forwarded-For': b'1.2.3.4, ' + PEER.encode()}) == PEER)
chk('client_identity imports no web framework — it is a pure function',
    'fastapi' not in sys.modules and 'starlette' not in sys.modules)

# ===========================================================================
print('\n== I · MEMORY KEY CARDINALITY IS BOUNDED, EVICTION FAILS CLOSED ==')
CAP = 64
c = Clock()
mb = RL.MemoryBackend(max_keys=CAP)
for i in range(5000):
    mb.hit('spoof:%d' % i, 3, RL.WINDOW_HOUR, c.now(), consume=True)
st = mb.stats()
chk('(i) 5000 rotating identities leave the live store at or under the cap '
    'of %d' % CAP, mb.key_count() <= CAP, 'keys=%d' % mb.key_count())
chk('(i) the tombstone table is bounded by the same cap',
    mb.tombstone_count() <= CAP, 'tombstones=%d' % mb.tombstone_count())
chk('(i) the whole structure is bounded by 2 × ACS_RL_MAX_KEYS, as '
    'documented',
    mb.key_count() + mb.tombstone_count() <= st['bound_total'],
    '%d > %d' % (mb.key_count() + mb.tombstone_count(), st['bound_total']))
chk('live keys really were evicted — the attack was felt, not absorbed',
    st['evicted_live'] > 0, str(st))
chk('the documented (and bounded) cost is stated honestly: beyond '
    '2 × MAX_KEYS rotations the OLDEST tombstones are dropped',
    st['tombstones_dropped'] > 0, str(st))
chk('the old rule by contrast only ever freed EMPTY deques — a live key '
    'was never reclaimed, which is why memory grew for a whole window',
    st['evicted_live'] + st['evicted_expired'] > 4000, str(st))

# السياسة الموثّقة: المفتاح الحيّ المُخلى يُرفض، ولا يُمنح حصّة جديدة.
c = Clock()
mb = RL.MemoryBackend(max_keys=CAP)
for i in range(CAP + 8):                    # ضغط طفيف: الشواهد كلّها تنجو
    mb.hit('spoof:%d' % i, 3, RL.WINDOW_HOUR, c.now(), consume=True)
victim = 'spoof:0'
chk('the oldest-touched identity is tombstoned, not forgotten',
    mb.evicted_at(victim, c.now()) is True,
    'tombstones=%d dropped=%d' % (mb.tombstone_count(),
                                  mb.stats()['tombstones_dropped']))
allowed, wait, _ = mb.hit(victim, 3, RL.WINDOW_HOUR, c.now(), consume=True)
chk('(i) an EVICTED live key FAILS CLOSED on its next request — it is '
    'refused, NOT handed a fresh quota', allowed is False,
    'allowed=%s' % allowed)
chk('and its Retry-After is the remainder of its ORIGINAL window',
    0 < wait <= RL.WINDOW_HOUR, str(wait))
before = mb.stats()['refused_evicted']
for _ in range(10):
    mb.hit(victim, 3, RL.WINDOW_HOUR, c.now(), consume=True)
chk('repeating the request does not wear the tombstone down',
    mb.hit(victim, 3, RL.WINDOW_HOUR, c.now(), consume=True)[0] is False
    and mb.stats()['refused_evicted'] >= before + 10,
    str(mb.stats()['refused_evicted']))
c.advance(RL.WINDOW_HOUR + 1)
chk('(i) once its ORIGINAL window truly elapses the identity is served '
    'again — this is fail-closed, not a permanent ban',
    mb.hit(victim, 3, RL.WINDOW_HOUR, c.now(), consume=True)[0] is True)

c = Clock()
mb = RL.MemoryBackend(max_keys=CAP)
resident = 'resident'
for _ in range(3):
    mb.hit(resident, 3, RL.WINDOW_HOUR, c.now(), consume=True)
for i in range(CAP * 3):
    mb.hit('noise:%d' % i, 3, RL.WINDOW_HOUR, c.now(), consume=True)
    mb.hit(resident, 3, RL.WINDOW_HOUR, c.now(), consume=False)   # يُبقيه MRU
chk('a resident key stays enforced while the store churns around it — '
    'rotation cannot wash a real visitor out of its own limit',
    mb.hit(resident, 3, RL.WINDOW_HOUR, c.now(), consume=True)[0] is False)

c = Clock()
lim = memory_limiter(max_keys=CAP, gen_hour=4)
for i in range(40):
    lim.check('172.16.0.%d' % i, 'gen', now=c.now())
d = lim.check('172.16.0.0', 'gen', now=c.now())
chk('(i) the policy layer names an eviction refusal SCOPE_EVICTED so a '
    'production log does not read it as an over-quota visitor',
    d['allowed'] is False and d['scope'] == RL.SCOPE_EVICTED, str(d))
chk('its Arabic message blames server pressure, not the visitor',
    isinstance(d['message'], str) and 'الخادم' in d['message'])
chk('ACS_RL_MAX_KEYS defaults to 20000 and tolerates an empty value',
    RL.MemoryBackend(env={}).max_keys == 20000
    and RL.MemoryBackend(env={'ACS_RL_MAX_KEYS': ''}).max_keys == 20000
    and RL.MemoryBackend(env={'ACS_RL_MAX_KEYS': '99'}).max_keys == 99)
chk('a consume=False probe never creates a key — a health probe cannot '
    'inflate the cardinality it is measuring',
    RL.MemoryBackend(max_keys=8).hit('probe', 5, 60, 0.0,
                                     consume=False) == (True, 0, 0))

# ===========================================================================
print('\n== J · FAIL POLICY IS EXPLICIT AND WORKS BOTH WAYS ==')
c = Clock()
closed = RL.RateLimiter(backend=RaisingBackend(), limits=limits(),
                        fail_policy=RL.FAIL_CLOSED)
d = closed.check('1.1.1.1', 'gen', now=c.now())
chk('(j) fail_policy=closed REFUSES when the backend raises',
    d['allowed'] is False and d['code'] == RL.ACS_RATE_LIMITED
    and d['scope'] == RL.SCOPE_BACKEND and d['retry_after'] > 0, str(d))
chk('the refusal is marked degraded and speaks Arabic to the visitor',
    d.get('degraded') is True and 'أعِد المحاولة' in d['message'], str(d))

opened = RL.RateLimiter(backend=RaisingBackend(), limits=limits(),
                        fail_policy=RL.FAIL_OPEN)
d2 = opened.check('1.1.1.1', 'gen', now=c.now())
chk('(j) fail_policy=open ALLOWS when the backend raises',
    d2['allowed'] is True and d2.get('degraded') is True, str(d2))

h_closed = RL.health_status(limiter=closed, env={})
h_open = RL.health_status(limiter=opened, env={})
chk('(j) health_status()["healthy"] is False under BOTH policies once the '
    'backend has failed',
    h_closed['healthy'] is False and h_open['healthy'] is False,
    '%s %s' % (h_closed['healthy'], h_open['healthy']))
chk('health_status reports the policy actually in force',
    h_closed['fail_policy'] == 'closed' and h_open['fail_policy'] == 'open')
chk('health_status raises the BACKEND_UNHEALTHY flag and counts the errors',
    'BACKEND_UNHEALTHY' in h_closed['warnings']
    and h_closed['backend_errors'] > 0, str(h_closed['warnings']))
chk('the default policy is closed — the credit is protected unless someone '
    'opts out deliberately',
    RL.fail_policy_from_env({}) == RL.FAIL_CLOSED
    and RL.fail_policy_from_env({'ACS_RL_FAIL_POLICY': ''}) == RL.FAIL_CLOSED
    and RL.fail_policy_from_env({'ACS_RL_FAIL_POLICY': 'nonsense'})
    == RL.FAIL_CLOSED
    and RL.fail_policy_from_env({'ACS_RL_FAIL_POLICY': 'open'})
    == RL.FAIL_OPEN)
chk('a healthy limiter reports healthy=True — the flag is not stuck low',
    RL.health_status(limiter=memory_limiter(), env={})['healthy'] is True)

# ===========================================================================
print('\n== K · THE FACTORY NEVER FALLS BACK TO MEMORY SILENTLY ==')


def factory_raises(env, client=None):
    try:
        b = RL.make_backend(env=env, client=client)
    except RL.RateLimitBackendUnavailable as exc:
        return True, str(exc)
    return False, 'returned %s' % type(b).__name__


ok1, why1 = factory_raises({'ACS_RATE_LIMIT_BACKEND': 'redis'})
chk('(k) ACS_RATE_LIMIT_BACKEND=redis with no URL and no client RAISES',
    ok1, why1)
ok2, why2 = factory_raises({'ACS_RATE_LIMIT_BACKEND': 'redis',
                            'ACS_REDIS_URL': 'redis://h:6379/0'})
chk('(k) redis requested but the library absent RAISES rather than '
    'degrading to a process-local limiter', ok2, why2)
chk('the error names the cause and forbids the silent fallback explicitly',
    'redis' in why2.lower() and 'fall back' in why2.lower(), why2)
chk('ACS_ENV=production does not turn the hard rule into a soft one',
    factory_raises({'ACS_RATE_LIMIT_BACKEND': 'redis',
                    'ACS_ENV': 'production'})[0])
chk('an explicitly injected client IS accepted, with no redis import',
    isinstance(RL.make_backend(env={'ACS_RATE_LIMIT_BACKEND': 'redis'},
                               client=FakeRedis(Clock())), RL.RedisBackend))
chk('acs_rate_limit does not import redis at module import time',
    'redis' not in sys.modules)
chk('the default (unset) backend is memory',
    isinstance(RL.make_backend(env={}), RL.MemoryBackend)
    and isinstance(RL.make_backend(env={'ACS_RATE_LIMIT_BACKEND': 'memory'}),
                   RL.MemoryBackend))
chk('an unrecognised value is treated as unset, not as redis',
    isinstance(RL.make_backend(env={'ACS_RATE_LIMIT_BACKEND': 'memcached'}),
               RL.MemoryBackend))

prod = RL.health_status(limiter=memory_limiter(),
                        env={'ACS_ENV': 'production'})
chk('(k) an unset backend in production is flagged: distributed=false plus '
    'an explicit warning',
    prod['distributed'] is False
    and 'PRODUCTION_WITHOUT_DISTRIBUTED_BACKEND' in prod['warnings']
    and 'PROCESS_LOCAL_RATE_LIMIT' in prod['warnings'], str(prod['warnings']))
chk('the same deployment in development is NOT flagged for production',
    'PRODUCTION_WITHOUT_DISTRIBUTED_BACKEND' not in RL.health_status(
        limiter=memory_limiter(), env={})['warnings'])
red_health = RL.health_status(
    limiter=redis_limiter(FakeRedis(Clock())),
    env={'ACS_RATE_LIMIT_BACKEND': 'redis',
         'ACS_REDIS_URL': 'rediss://default:hunter2@cache.internal:6380/0'})
chk('a redis-backed limiter reports distributed=true and healthy=true',
    red_health['distributed'] is True and red_health['healthy'] is True
    and red_health['backend'] == 'redis'
    and 'PROCESS_LOCAL_RATE_LIMIT' not in red_health['warnings'],
    str(red_health))

# ===========================================================================
print('\n== L · HEALTH OUTPUT LEAKS NO CREDENTIAL ==')
SECRET_URL = 'rediss://default:hunter2@cache.internal:6380/0'
h = RL.health_status(
    limiter=redis_limiter(FakeRedis(Clock())),
    env={'ACS_RATE_LIMIT_BACKEND': 'redis', 'ACS_REDIS_URL': SECRET_URL})
blob = json.dumps(h, ensure_ascii=False)
leaks = [s for s in ('hunter2', SECRET_URL, 'cache.internal', '6380',
                     'default:hunter2') if s in blob]
chk('(l) the health payload contains no password, host, port or full URL',
    not leaks, 'leaked: %s' % leaks)
chk('(l) it surfaces only the scheme and a boolean about the password',
    h['redis_scheme'] == 'rediss'
    and h['redis_password_configured'] is True, str(h))
chk('a URL without a password reports the boolean as False',
    RL.health_status(limiter=redis_limiter(FakeRedis(Clock())),
                     env={'ACS_RATE_LIMIT_BACKEND': 'redis',
                          'ACS_REDIS_URL': 'redis://cache:6379/0'}
                     )['redis_password_configured'] is False)
chk('the memory backend surfaces no redis fields at all',
    'redis_scheme' not in RL.health_status(limiter=memory_limiter(),
                                           env={'ACS_REDIS_URL': SECRET_URL}))
chk('the payload carries every key the contract promises',
    all(k in h for k in ('backend', 'distributed', 'fail_policy', 'limits',
                         'healthy')), str(sorted(h)))
chk('(l) a backend error is surfaced as a CLASS NAME, never as its text — '
    'redis-py error strings carry the host and port verbatim',
    'cache.internal' not in json.dumps(RL.health_status(limiter=closed,
                                                        env={}),
                                       ensure_ascii=False)
    and RL.health_status(limiter=closed,
                         env={})['last_error_kind']
    == 'BackendOperationError',
    str(RL.health_status(limiter=closed, env={}).get('last_error_kind')))
chk('the payload is JSON-serialisable as-is (it goes straight into /health)',
    isinstance(blob, str) and json.loads(blob)['backend'] == 'redis')

# ===========================================================================
print('\n== M · THE REDIS ADAPTER IS NOT HAND-WAVED ==')
chk('the Lua script decides, increments and expires in ONE round trip',
    all(cmd in RL.LUA_HIT for cmd in ('GET', 'INCR', 'PEXPIRE', 'PTTL')))
chk('PEXPIRE is armed only on the FIRST increment, so a flood cannot extend '
    'the window', 'count == 1' in RL.LUA_HIT)
chk('the non-scripting fallback sequence is declared, not hand-waved',
    RL.REDIS_FALLBACK_SEQUENCE
    and any('PEXPIRE' in s for s in RL.REDIS_FALLBACK_SEQUENCE))

c = Clock()
inner = FakeRedis(c)
eval_only = ClientView(inner, ['eval', 'get', 'incr', 'pexpire', 'pttl',
                               'ping'])
lim = redis_limiter(eval_only, gen_hour=2)
got = [lim.check('2.2.2.2', 'gen', now=c.now())['allowed'] for _ in range(3)]
chk('a client exposing only EVAL (no SCRIPT LOAD) still enforces the limit',
    got == [True, True, False] and inner.calls['eval'] > 0
    and inner.calls['evalsha'] == 0, str(got))

c = Clock()
inner = FakeRedis(c)
plain = ClientView(inner, ['get', 'incr', 'pexpire', 'pttl', 'ping'])
lim = redis_limiter(plain, gen_hour=2)
got = [lim.check('2.2.2.2', 'gen', now=c.now())['allowed'] for _ in range(3)]
chk('the documented GET/INCR/PEXPIRE/PTTL fallback enforces the limit too',
    got == [True, True, False] and inner.calls['incr'] > 0
    and inner.calls['pexpire'] > 0 and inner.calls['eval'] == 0, str(got))
chk('the fallback still leaves no key without an expiry',
    not inner.keys_without_expiry(), str(inner.keys_without_expiry()))
c.advance(RL.WINDOW_HOUR + 1)
chk('the fallback expires its keys too',
    lim.check('2.2.2.2', 'gen', now=c.now())['allowed'] is True)

d = RL.RateLimiter(backend=RL.RedisBackend(RaisingClient()), limits=limits(),
                   fail_policy=RL.FAIL_CLOSED).check('1.1.1.1', 'gen', now=0.0)
chk('a client that raises becomes a policy decision, never a 500',
    d['allowed'] is False and d['scope'] == RL.SCOPE_BACKEND, str(d))
chk('and the raw client error text never reaches the visitor message',
    'cache.internal' not in (d['message'] or ''), str(d['message']))
chk('RedisBackend refuses to be built without a client',
    raises(lambda: RL.RedisBackend(None), RL.RateLimitBackendUnavailable))
chk('a client returning a nonsense shape is a policy decision too, not a '
    'crash',
    RL.RateLimiter(backend=RL.RedisBackend(ShapeShifter()), limits=limits(),
                   fail_policy=RL.FAIL_CLOSED).check(
        '1.1.1.1', 'gen', now=0.0)['allowed'] is False)

print('\n──────────────────────────────────────────────')
print('TEST SUMMARY')
print('  passed: %d' % p[0])
print('  failed: %d' % f[0])
print('  total:  %d' % (p[0] + f[0]))
print('RATE LIMIT REGRESSION: %d passed, %d failed' % (p[0], f[0]))
print('NOT VERIFIED HERE: integration against a REAL Redis server — there is '
      'no network in this environment.')
if f[0]:
    sys.exit(1)
