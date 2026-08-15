# -*- coding: utf-8 -*-
"""حدّ المعدّل: عقدٌ واحد لكل نسخ الخادم — لا نافذة داخل العملية وحدها.

المشكلة التي تُصلحها هذه الوحدة (كما هي في acs_understand_api.py):

  1. النافذة المنزلقة `_hits = defaultdict(deque)` محليّة داخل العملية.
     نسختان من الواجهة (أو عاملان) ⇒ حِصّتان مستقلّتان ⇒ الحدّ مضاعف فعلياً،
     ويُمحى كلّه عند إعادة التشغيل. لا يحمي هذا رصيد المفتاح إطلاقاً.
  2. تنظيف `len(_hits) > 4000` لا يحذف إلا الطوابير الفارغة. المهاجم الذي
     يُدوّر هويّات مزوّرة يُنشئ مفاتيح حيّة، فتنمو الذاكرة بلا حدّ طول النافذة.
  3. `x-real-ip` يُقرأ بلا أي حساب للقفزات الموثوقة — ترويسة يكتبها العميل
     نفسه، فيُنشئ دلواً جديداً لكل طلب ويتجاوز الحدّ كلّه.
  4. `int(os.environ.get("ACS_TRUSTED_PROXIES", "1"))` يرمي ValueError عند
     الإقلاع إذا كان المتغيّر سلسلةً فارغة — وهو ما يشحنه .env.example:17
     حرفياً. الخادم لا يُقلع أصلاً.

العقد هنا:

  * `RateLimitBackend.hit(key, limit, window_s, now, consume)` بدائيّة ذرّية
    واحدة، قابلة للتنفيذ في Redis بنصّ Lua واحد (انظر LUA_HIT أدناه).
  * `MemoryBackend` سلوك اليوم لكن بحدّ صريح لعدد المفاتيح وإخلاء LRU،
    والمفتاح الحيّ المُخلى يُرفض طلبه التالي (fail closed) ولا يُمنح حِصّة جديدة.
  * `RedisBackend` عدّادات مشتركة بين النسخ، كلّها بانتهاء صلاحية، ولا
    يُستورد redis عند استيراد هذه الوحدة إطلاقاً.
  * `client_identity` دالّة صرفة بلا FastAPI تُصلح أعطال الهويّة الأربعة.
  * `health_status()` يقول صراحةً إن كان الحدّ موزَّعاً أم محليّ العملية،
    ولا يكشف ACS_REDIS_URL ولا كلمة السرّ.

الرسائل الموجَّهة للزائر بالعربية؛ التفاصيل التقنية والرموز بالإنجليزية.
كل الدوالّ آمنة على الخيوط، وكل قرار حتميّ عبر حقن `now`.
"""
from __future__ import annotations

import ipaddress
import itertools
import logging
import math
import os
import threading
import time
from collections import OrderedDict

LOG = logging.getLogger("acs.rate_limit")

CONTRACT_VERSION = "acs-rate-limit/1.0"

# ---------------------------------------------------------------------------
# رموز الأخطاء — نفس رمز acs_api_errors.ACS_RATE_LIMITED كي تبقى الاستجابة 429
# وتُبثّ Retry-After من `retry_after` بلا تغيير في طبقة الأخطاء.
# ---------------------------------------------------------------------------
ACS_RATE_LIMITED = "ACS_RATE_LIMITED"

SCOPE_GLOBAL_DAY = "global_day"
SCOPE_GEN_HOUR = "gen_hour"
SCOPE_GEN_DAY = "gen_day"
SCOPE_EDIT_HOUR = "edit_hour"
SCOPE_BACKEND = "backend"          # الواجهة الخلفية سقطت وسياسة الفشل «مغلقة»
SCOPE_EVICTED = "evicted"          # مفتاح حيّ أُخلي من ذاكرة العملية

WINDOW_HOUR = 3600
WINDOW_DAY = 86400

#: كم ثانية يُطلب من الزائر الانتظار حين تسقط الواجهة الخلفية (fail closed).
BACKEND_DOWN_RETRY_AFTER_S = 30


class RateLimitError(Exception):
    """أصل كل أخطاء هذه الوحدة."""


class RateLimitBackendUnavailable(RateLimitError):
    """طُلبت واجهة خلفية موزَّعة ولم يمكن بناؤها — لا تراجُع صامت للذاكرة."""


class BackendOperationError(RateLimitError):
    """فشلت عمليّة وقت الطلب على الواجهة الخلفية (شبكة، مهلة، سكربت)."""


# ---------------------------------------------------------------------------
# قراءة البيئة — كل قراءة عدد تتحمّل السلسلة الفارغة والقيمة غير الرقمية.
# هذا بالضبط ما كان يمنع الإقلاع: ACS_TRUSTED_PROXIES= في .env.example.
# ---------------------------------------------------------------------------
def env_int(name, default, env=None, minimum=None, maximum=None):
    """int من البيئة لا يرمي أبداً: '' أو 'abc' أو None ⇒ القيمة الافتراضية."""
    src = os.environ if env is None else env
    raw = src.get(name)
    if raw is None:
        return default
    raw = str(raw).strip()
    if not raw:
        return default
    try:
        val = int(raw, 10)
    except (TypeError, ValueError):
        LOG.warning("%s=%r is not an integer; using default %r",
                    name, raw, default)
        return default
    if minimum is not None and val < minimum:
        return minimum
    if maximum is not None and val > maximum:
        return maximum
    return val


def env_str(name, default, env=None):
    src = os.environ if env is None else env
    raw = src.get(name)
    if raw is None:
        return default
    raw = str(raw).strip()
    return raw if raw else default


def env_flag(name, default=False, env=None):
    """علم منطقي: 1/true/yes/on ⇒ True. الفارغ ⇒ الافتراضي."""
    src = os.environ if env is None else env
    raw = src.get(name)
    if raw is None:
        return default
    raw = str(raw).strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def limits_from_env(env=None):
    """الحدود الأربعة كما في acs_understand_api.py، بلا تخفيف."""
    return {
        "gen_hour": env_int("ACS_RL_GEN_HOUR", 8, env, minimum=1),
        "gen_day": env_int("ACS_RL_GEN_DAY", 25, env, minimum=1),
        "edit_hour": env_int("ACS_RL_EDIT_HOUR", 30, env, minimum=1),
        "global_day": env_int("ACS_RL_GLOBAL_DAY", 400, env, minimum=1),
    }


DEFAULT_LIMITS = {
    "gen_hour": 8, "gen_day": 25, "edit_hour": 30, "global_day": 400,
}

FAIL_CLOSED = "closed"
FAIL_OPEN = "open"


def fail_policy_from_env(env=None):
    """ACS_RL_FAIL_POLICY ∈ {closed, open} — الافتراضي closed.

    closed: سقوط الواجهة الخلفية يعني رفض الطلب (يحمي رصيد المفتاح، ويقطع
            الخدمة عن الزوّار الشرعيين حتى تعود). هذا هو الافتراضي لأن
            الخادم مفتوح للعموم والمفتاح عليه.
    open:   سقوط الواجهة الخلفية يعني السماح (تبقى الخدمة، ويُفتح الرصيد
            للاستنزاف طول العطل). لا تُشغَّل إلا بقرار واعٍ.
    """
    val = env_str("ACS_RL_FAIL_POLICY", FAIL_CLOSED, env).lower()
    return val if val in (FAIL_CLOSED, FAIL_OPEN) else FAIL_CLOSED


# ---------------------------------------------------------------------------
# §1 — البدائيّة الذرّية
#
# الاختيار: hit(key, limit, window_s, now, consume) -> (allowed, retry_after, count)
#
# لماذا هذه وليست incr_window(key, window_s, now) -> (count, oldest_ts)؟
#
#   * `incr_window` تفرض سجلّ نافذة منزلقة (ZSET في Redis): ZREMRANGEBYSCORE
#     + ZADD + ZCARD + PEXPIRE، أي O(عدد الطلبات) ذاكرةً لكل مفتاح، ولا تُعطي
#     قرار «مسموح؟» ذرّياً — القرار يُتّخذ خارج الخادم بعد قراءة العدّاد،
#     فيبقى سباق check-then-act بين نسختي الواجهة وهو بالضبط العطل المُصلَح.
#   * `hit` تُعيد القرار نفسه ذرّياً: المقارنة بالحدّ والزيادة والانتهاء
#     تحدث كلّها داخل استدعاء واحد (EVALSHA واحد). ذاكرتها O(1) لكل مفتاح
#     (عدّاد صحيح واحد)، وكل مفتاح يحمل انتهاء صلاحية إجبارياً.
#   * `consume=False` يُبقي ترتيب «افحص العام بلا استهلاك، واستهلكه أخيراً»
#     الذي في الكود الحالي، وهو ترتيب مقصود: زائر مرفوض لا يستنزف السقف العام.
#
# الثمن المقبول: نافذة ثابتة مثبَّتة على أوّل طلب (لا منزلقة). قد تسمح بضعف
# الحدّ على حدّ نافذتين في أسوأ حالة — وهو ثمن معروف مقابل O(1) ذاكرة وذرّية
# حقيقية. Retry-After يأتي من PTTL فلا يمتدّ الحظر أبداً بطلبات جديدة.
# ---------------------------------------------------------------------------

#: نصّ Lua المُنفَّذ في Redis. يُحمّل مرّة بـ SCRIPT LOAD ثمّ يُنادى بـ EVALSHA.
#: KEYS[1] = المفتاح. ARGV = {limit, window_ms, consume(0|1)}.
#: يُعيد {allowed(0|1), pttl_ms, count}.
LUA_HIT = """
local limit    = tonumber(ARGV[1])
local window   = tonumber(ARGV[2])
local consume  = tonumber(ARGV[3])
local count    = tonumber(redis.call('GET', KEYS[1]) or '0')
if count >= limit then
  local pttl = redis.call('PTTL', KEYS[1])
  if pttl < 0 then pttl = window end
  return {0, pttl, count}
end
if consume == 1 then
  count = redis.call('INCR', KEYS[1])
  if count == 1 then
    redis.call('PEXPIRE', KEYS[1], window)
  end
end
local pttl = redis.call('PTTL', KEYS[1])
if pttl < 0 then pttl = window end
return {1, pttl, count}
"""

# تسلسل الأوامر البديل حين لا يُسمح بـ EVAL (Redis مُدار يمنع السكربتات).
# ليس ذرّياً بالكامل — GET ثمّ INCR سباق — لذا يُستعمل فقط عند غياب EVAL،
# ويُسجَّل تحذير. التسلسل حرفياً:
#
#     GET     <key>                      -> count أو nil
#     (إن count >= limit)  PTTL <key>     -> retry_after_ms   [رفض]
#     (وإلا, consume)      INCR <key>     -> count'
#                          (إن count'==1) PEXPIRE <key> <window_ms>
#                          PTTL <key>     -> retry_after_ms   [قبول]
#
# PEXPIRE يُضبط مرّة واحدة عند أوّل زيادة فقط: هكذا لا تمتدّ النافذة بطلبات
# لاحقة، ولا يوجد مفتاح بلا انتهاء صلاحية في أي مسار.
REDIS_FALLBACK_SEQUENCE = (
    "GET key", "PTTL key", "INCR key", "PEXPIRE key window_ms", "PTTL key",
)


class RateLimitBackend(object):
    """الواجهة الخلفية: بدائيّة واحدة ذرّية + فحص صحّة."""

    name = "abstract"
    distributed = False

    def hit(self, key, limit, window_s, now, consume=True):
        """(allowed: bool, retry_after_s: int, count: int).

        عقدٌ ملزم لكل تنفيذ:
          * القرار والزيادة والانتهاء ذرّية بالنسبة لكل المتنافسين.
          * لا يزيد العدّاد أبداً فوق `limit` (الرفض لا يزيد شيئاً).
          * retry_after_s > 0 و ≤ window_s عند الرفض، و 0 عند القبول.
          * كل مفتاح يحمل انتهاء صلاحية ≤ window_s.
          * consume=False يفحص بلا تسجيل ولا يُنشئ مفتاحاً.
        يرمي BackendOperationError عند عطل وقت الطلب.
        """
        raise NotImplementedError

    def healthy(self):
        """فحص رخيص: True إن كانت الواجهة تستجيب الآن."""
        raise NotImplementedError

    def stats(self):
        """أرقام تشخيصية — لا تحتوي أي سرّ."""
        return {}


# ---------------------------------------------------------------------------
# §2 — MemoryBackend: سلوك اليوم، لكن بذاكرة محدودة صراحةً.
#
# سياسة الإخلاء المختارة (مُوثّقة لأنها قرار أمني، لا تفصيلاً تنفيذياً):
#
#   * البنية OrderedDict مرتَّبة بآخر لمسة، بسقف صلب ACS_RL_MAX_KEYS (20000).
#   * عند إدخال مفتاح جديد والبنية ممتلئة: تُكنس أوّلاً المفاتيح المنتهية
#     صلاحيتها (لا تكلفة أمنية لإخلائها — حِصّتها انتهت فعلاً).
#   * إن لم يتحرّر شيء، يُخلى أقدم مفتاح لمساً وهو *حيّ*. هنا الخطر: لو
#     اكتفينا بالحذف لَمَنَحنا صاحبه حِصّة جديدة كاملة — وهذا بالضبط ما
#     يشتريه المهاجم بتدوير الهويّات المزوّرة.
#   * لذلك يُنقل المفتاح المُخلى الحيّ إلى جدول شواهد `_tombstones` يحمل
#     زمن انتهاء نافذته الأصلية. أي طلب لمفتاح له شاهد حيّ يُرفض فوراً
#     (FAIL CLOSED) برمز SCOPE_EVICTED و Retry-After = ما تبقّى من نافذته.
#   * جدول الشواهد نفسه محدود بـ ACS_RL_MAX_KEYS. حين يمتلئ يُسقَط الشاهد
#     الأقرب انتهاءً (الأقلّ قيمةً أمنياً). فالسقف الكلّي للبنية كلّها هو
#     2 × ACS_RL_MAX_KEYS مدخلاً، مهما بلغ عدد الهويّات المزوّرة.
#   * الحصيلة: لا نموّ بلا حدّ، ولا حِصّة مجّانية عند الإخلاء. ثمن المهاجم
#     لشراء دلو نظيف صار: أن يُزيح هويّته من جدولين بسعة 2×MAX_KEYS داخل
#     النافذة الواحدة — وكل ضحية إزاحة تُرفض بدل أن تُكافأ.
#
# لماذا لا نرفض *القادم الجديد* بدل إخلاء الحيّ؟ لأن ذلك يُسلّم للمهاجم
# سلاح حرمان خدمة كامل: يملأ الجدول فيُغلَق الباب أمام كل زائر جديد. إخلاء
# الأقدم لمساً + شاهد يُبقي الخدمة مفتوحة للزوّار الجدد ويُبقي التكلفة على
# المهاجم.
# ---------------------------------------------------------------------------
class MemoryBackend(RateLimitBackend):

    name = "memory"
    distributed = False

    def __init__(self, max_keys=None, env=None):
        if max_keys is None:
            max_keys = env_int("ACS_RL_MAX_KEYS", 20000, env, minimum=16)
        self.max_keys = int(max_keys)
        self._lock = threading.RLock()
        #: key -> [count, expires_at]؛ الترتيب = آخر لمسة (LRU في الأول).
        self._store = OrderedDict()
        #: key -> expires_at لمفاتيح حيّة أُخليت. الرفض يبقى حتى انتهاء نافذتها.
        self._tombstones = OrderedDict()
        self._evicted_live = 0
        self._evicted_expired = 0
        self._tombstones_dropped = 0
        self._refused_evicted = 0

    # -- أدوات داخلية (تُنادى دائماً والقفل مأخوذ) --------------------------
    def _purge_expired(self, now, budget=64):
        """كنس المنتهين من طرف LRU. محدود الميزانية كي يبقى الطلب O(1) مُطفَأة."""
        removed = 0
        for key in list(itertools.islice(self._store.keys(), budget)):
            rec = self._store.get(key)
            if rec is not None and rec[1] <= now:
                del self._store[key]
                removed += 1
                self._evicted_expired += 1
        for key in list(itertools.islice(self._tombstones.keys(), budget)):
            if self._tombstones.get(key, 0) <= now:
                del self._tombstones[key]
        return removed

    def _tombstone(self, key, expires_at):
        if expires_at <= 0:
            return
        self._tombstones[key] = expires_at
        self._tombstones.move_to_end(key)
        while len(self._tombstones) > self.max_keys:
            # أقدم شاهدٍ سُجّل هو الأقرب انتهاءً (كل الشواهد تُسجَّل بنفس
            # طول النافذة تقريباً) — وهو أقلّها قيمةً أمنياً. إسقاطه O(1).
            self._tombstones.popitem(last=False)
            self._tombstones_dropped += 1

    def _make_room(self, now):
        if len(self._store) < self.max_keys:
            return
        self._purge_expired(now, budget=self.max_keys)
        while len(self._store) >= self.max_keys:
            victim, rec = self._store.popitem(last=False)   # أقدم لمساً
            if rec[1] > now and rec[0] > 0:
                self._evicted_live += 1
                self._tombstone(victim, rec[1])
            else:
                self._evicted_expired += 1

    # -- العقد ---------------------------------------------------------------
    def hit(self, key, limit, window_s, now, consume=True):
        limit = int(limit)
        window_s = int(window_s)
        with self._lock:
            self._purge_expired(now)

            ts = self._tombstones.get(key)
            if ts is not None:
                if ts > now:
                    # مفتاح حيّ أُخلي: يُرفض ولا يُمنح حِصّة جديدة — FAIL CLOSED.
                    self._refused_evicted += 1
                    return False, _ceil_pos(ts - now, window_s), limit
                del self._tombstones[key]

            rec = self._store.get(key)
            if rec is not None and rec[1] <= now:
                del self._store[key]
                rec = None

            if rec is None:
                if not consume:
                    return True, 0, 0
                self._make_room(now)
                rec = [0, now + window_s]
                self._store[key] = rec

            self._store.move_to_end(key)
            count, expires_at = rec[0], rec[1]

            if count >= limit:
                return False, _ceil_pos(expires_at - now, window_s), count
            if consume:
                rec[0] = count + 1
                count = rec[0]
            return True, 0, count

    def healthy(self):
        return True

    def stats(self):
        with self._lock:
            return {
                "keys": len(self._store),
                "tombstones": len(self._tombstones),
                "max_keys": self.max_keys,
                "bound_total": 2 * self.max_keys,
                "evicted_live": self._evicted_live,
                "evicted_expired": self._evicted_expired,
                "tombstones_dropped": self._tombstones_dropped,
                "refused_evicted": self._refused_evicted,
            }

    def evicted(self, key):
        """True إن كان هذا المفتاح مرفوضاً الآن بسبب إخلاء LRU لا بسبب حدّه."""
        with self._lock:
            ts = self._tombstones.get(key)
            return ts is not None and ts > time.time()

    def evicted_at(self, key, now):
        with self._lock:
            ts = self._tombstones.get(key)
            return ts is not None and ts > now

    # يُستعمل في الاختبار والتشخيص فقط.
    def key_count(self):
        with self._lock:
            return len(self._store)

    def tombstone_count(self):
        with self._lock:
            return len(self._tombstones)


def _ceil_pos(seconds, window_s):
    """ثوانٍ للانتظار: دائماً ≥ 1 و ≤ النافذة."""
    if seconds != seconds or seconds in (float("inf"), float("-inf")):
        return int(window_s)
    val = int(math.ceil(seconds))
    if val < 1:
        val = 1
    if val > window_s:
        val = int(window_s)
    return val


# ---------------------------------------------------------------------------
# §3 — RedisBackend
#
# لا يُستورد redis هنا إطلاقاً. العميل يُحقن (duck typing): أي كائن يكشف
#   * eval(script, numkeys, *keys_and_args)  و/أو  evalsha/script_load، أو
#   * get / incr / pexpire / pttl  (مسار التراجُع غير الذرّي)
# مصنع الاتصال `redis_client_from_url` وحده يستورد المكتبة، ويرمي رسالة
# واضحة حين تغيب.
# ---------------------------------------------------------------------------
def _as_int(value, default=0):
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, (bytes, bytearray)):
        try:
            return int(value.decode("ascii", "ignore").strip() or default)
        except (TypeError, ValueError):
            return default
    try:
        return int(str(value).strip() or default)
    except (TypeError, ValueError):
        return default


class RedisBackend(RateLimitBackend):

    name = "redis"
    distributed = True

    def __init__(self, client, prefix="acs:rl:"):
        if client is None:
            raise RateLimitBackendUnavailable(
                "RedisBackend requires an injected client; none was given.")
        self.client = client
        self.prefix = prefix
        self._lock = threading.RLock()
        self._sha = None
        self._eval_supported = hasattr(client, "eval") or hasattr(
            client, "evalsha")
        self._warned_fallback = False

    # -- المسار الذرّي: EVALSHA/EVAL لنصّ LUA_HIT -----------------------------
    def _run_script(self, key, limit, window_ms, consume):
        client = self.client
        if hasattr(client, "evalsha") and hasattr(client, "script_load"):
            with self._lock:
                if self._sha is None:
                    self._sha = client.script_load(LUA_HIT)
            try:
                return client.evalsha(self._sha, 1, key, limit, window_ms,
                                      consume)
            except Exception as exc:                       # NOSCRIPT وغيره
                if "NOSCRIPT" not in str(exc).upper():
                    raise
                with self._lock:
                    self._sha = None
        return client.eval(LUA_HIT, 1, key, limit, window_ms, consume)

    # -- مسار التراجُع: GET/PTTL/INCR/PEXPIRE (غير ذرّي — يُحذَّر منه) ---------
    def _run_commands(self, key, limit, window_ms, consume):
        c = self.client
        if not self._warned_fallback:
            self._warned_fallback = True
            LOG.warning("rate limit: redis client exposes no EVAL; falling "
                        "back to the non-atomic GET/INCR sequence — a small "
                        "overshoot is possible under concurrency")
        count = _as_int(c.get(key), 0)
        if count >= limit:
            return [0, _as_int(c.pttl(key), -1), count]
        if consume:
            count = _as_int(c.incr(key), 1)
            if count == 1:
                c.pexpire(key, window_ms)
        return [1, _as_int(c.pttl(key), -1), count]

    def hit(self, key, limit, window_s, now, consume=True):
        limit = int(limit)
        window_s = int(window_s)
        window_ms = window_s * 1000
        full = self.prefix + key
        try:
            if self._eval_supported:
                res = self._run_script(full, limit, window_ms,
                                       1 if consume else 0)
            else:
                res = self._run_commands(full, limit, window_ms,
                                         bool(consume))
        except RateLimitError:
            raise
        except Exception as exc:
            raise BackendOperationError("redis hit failed: %s" % (exc,))

        if not isinstance(res, (list, tuple)) or len(res) < 3:
            raise BackendOperationError(
                "redis returned an unexpected shape: %r" % (res,))
        allowed = bool(_as_int(res[0], 0))
        pttl_ms = _as_int(res[1], -1)
        count = _as_int(res[2], 0)
        if allowed:
            return True, 0, count
        remaining = window_s if pttl_ms < 0 else pttl_ms / 1000.0
        return False, _ceil_pos(remaining, window_s), count

    def healthy(self):
        try:
            if hasattr(self.client, "ping"):
                self.client.ping()
            else:
                self.client.get(self.prefix + "__health__")
            return True
        except Exception as exc:
            LOG.warning("rate limit: redis health probe failed: %s", exc)
            return False

    def stats(self):
        return {"prefix": self.prefix, "atomic": bool(self._eval_supported)}


def redis_client_from_url(url):
    """يستورد redis كسولاً هنا فقط. غياب المكتبة = خطأ صريح، لا تراجُع."""
    if not url:
        raise RateLimitBackendUnavailable(
            "ACS_RATE_LIMIT_BACKEND=redis but ACS_REDIS_URL is empty.")
    try:
        import redis as _redis                       # noqa: F401  (lazy)
    except Exception as exc:
        raise RateLimitBackendUnavailable(
            "ACS_RATE_LIMIT_BACKEND=redis but the 'redis' package is not "
            "installed (%s). Install it or unset ACS_RATE_LIMIT_BACKEND — "
            "this deployment will NOT silently fall back to a process-local "
            "limiter." % (exc,))
    try:
        return _redis.Redis.from_url(url, socket_timeout=2.0,
                                     socket_connect_timeout=2.0)
    except Exception as exc:
        raise RateLimitBackendUnavailable(
            "could not build a redis client from ACS_REDIS_URL: %s" % (exc,))


# ---------------------------------------------------------------------------
# §4 — المصنع. القاعدة الصلبة: redis المطلوب صراحةً لا يتراجع للذاكرة أبداً.
# ---------------------------------------------------------------------------
def backend_choice(env=None):
    """('memory'|'redis', explicit: bool) — explicit=False يعني غير مضبوط."""
    raw = env_str("ACS_RATE_LIMIT_BACKEND", "", env).lower()
    if raw in ("redis",):
        return "redis", True
    if raw in ("memory", "local", "process"):
        return "memory", True
    if raw:
        LOG.warning("ACS_RATE_LIMIT_BACKEND=%r is not recognised; "
                    "treating it as unset (memory)", raw)
    return "memory", False


def make_backend(env=None, client=None):
    """يبني الواجهة الخلفية من البيئة.

    ACS_RATE_LIMIT_BACKEND ∈ {memory, redis}   (الافتراضي memory)
    ACS_REDIS_URL                              (مطلوب حين redis)
    ACS_ENV ∈ {development, test, production}  (الافتراضي development)

    حين ACS_RATE_LIMIT_BACKEND=redis: أي فشل يرمي RateLimitBackendUnavailable.
    لا يوجد مسار واحد يُرجع MemoryBackend في هذه الحالة — لأن التراجُع الصامت
    يعني حدّاً مضاعفاً بصمت في الإنتاج، وهو أسوأ من رفض الإقلاع.
    """
    choice, explicit = backend_choice(env)
    if choice == "redis":
        if client is None:
            client = redis_client_from_url(env_str("ACS_REDIS_URL", "", env))
        try:
            return RedisBackend(client)
        except RateLimitBackendUnavailable:
            raise
        except Exception as exc:
            raise RateLimitBackendUnavailable(
                "redis backend requested but unavailable: %s" % (exc,))
    if not explicit and env_str("ACS_ENV", "development", env).lower() \
            == "production":
        LOG.warning("ACS_ENV=production with no ACS_RATE_LIMIT_BACKEND: the "
                    "rate limiter is PROCESS-LOCAL. Two instances = two "
                    "quotas, and a restart clears them. health_status() "
                    "reports distributed=false.")
    return MemoryBackend(env=env)


# ---------------------------------------------------------------------------
# §4b — قرار الإنتاج (KI-14 pass · F-47): لا تحذير بلا قرار.
#
# كان /health يقول PROCESS_LOCAL_RATE_LIMIT و
# PRODUCTION_WITHOUT_DISTRIBUTED_BACKEND ثم يُقلع الخادم عادياً. تحذيرٌ لا
# يمنع شيئاً ولا يُلزم أحداً: نسختان من الخدمة تعنيان حصّتين، وإعادة نشرٍ
# متدرّجة تعني ثلاث حصص لحظياً، والسقف اليوميّ العامّ — وهو أهمّ صمّام أمان
# على الرصيد — يصير قابلاً للمضاعفة بعدد النسخ بلا أن يعلم أحد.
#
# فإمّا مخزنٌ موزّع، وإمّا **إقرارٌ صريح** بأن النشر عمليّة واحدة ونسخة واحدة.
# والإقرار ليس كلاماً: إن أعلنت المنصّة تزامناً أكبر من واحد نُسقط الإقلاع.
# ---------------------------------------------------------------------------

#: متغيّرات تُعلن بها المنصّات عدد العمليات أو النسخ. أيّها > 1 ينقض الإقرار.
CONCURRENCY_VARS = ("WEB_CONCURRENCY", "UVICORN_WORKERS", "GUNICORN_WORKERS",
                    "ACS_INSTANCES", "NUM_INSTANCES", "RENDER_INSTANCE_COUNT",
                    "FLY_MACHINE_COUNT")

INVARIANT_DISTRIBUTED = "distributed_backend"
INVARIANT_SINGLE = "single_instance_declared"
INVARIANT_DEV = "development"
INVARIANT_UNDECLARED = "UNDECLARED_SINGLE_INSTANCE"
INVARIANT_VIOLATED = "SINGLE_INSTANCE_INVARIANT_VIOLATED"


class ProductionInvariantError(RuntimeError):
    """ضبطٌ إنتاجيّ لا يجوز الإقلاع عليه. يُرفع عند بدء التشغيل لا عند أول طلب."""


def declared_concurrency(env=None):
    """أكبر تزامن تُعلنه المنصّة، والمتغيّر الذي أعلنه. (1, None) إن لم يُعلَن."""
    best, who = 1, None
    for name in CONCURRENCY_VARS:
        raw = env_str(name, "", env).strip()
        if not raw:
            continue
        try:
            v = int(raw)
        except ValueError:
            continue
        if v > best:
            best, who = v, name
    return best, who


def production_invariant(limiter=None, env=None):
    """القرار التشغيليّ الصريح. يعيد قاموساً؛ `ok=False` يعني: لا تُقلع.

    الحالات:
      distributed_backend         مخزن مشترك ذرّي — أي عدد نسخ مقبول.
      development                 خارج الإنتاج — الحدّ المحليّ كافٍ.
      single_instance_declared    الإنتاج، بلا مخزن موزّع، وبإقرار صريح
                                  ACS_SINGLE_INSTANCE=1، والمنصّة تعلن تزامن ١.
      UNDECLARED_SINGLE_INSTANCE  الإنتاج بلا مخزن ولا إقرار ⇒ لا إقلاع.
      SINGLE_INSTANCE_INVARIANT_VIOLATED
                                  أُقرَّ بنسخة واحدة والمنصّة تعلن أكثر ⇒ لا إقلاع.
    """
    lim = limiter if limiter is not None else default_limiter(env)
    distributed = bool(getattr(lim.backend, "distributed", False))
    is_prod = env_str("ACS_ENV", "development", env).lower() == "production"
    declared = env_flag("ACS_SINGLE_INSTANCE", False, env)
    concurrency, source = declared_concurrency(env)
    out = {"contract": CONTRACT_VERSION, "ok": True, "state": None,
           "distributed": distributed, "production": is_prod,
           "single_instance_declared": bool(declared),
           "declared_concurrency": concurrency,
           "concurrency_source": source, "detail": ""}
    if distributed:
        out["state"] = INVARIANT_DISTRIBUTED
        out["detail"] = ("rate limits are shared atomically; any instance "
                         "count is safe")
        return out
    if not is_prod:
        out["state"] = INVARIANT_DEV
        out["detail"] = "not production; a process-local limiter is acceptable"
        return out
    if not declared:
        out["ok"] = False
        out["state"] = INVARIANT_UNDECLARED
        out["detail"] = (
            "ACS_ENV=production with a process-local rate limiter and no "
            "ACS_SINGLE_INSTANCE=1 acknowledgement. Either set "
            "ACS_RATE_LIMIT_BACKEND=redis with ACS_REDIS_URL, or declare the "
            "single-instance invariant explicitly.")
        return out
    if concurrency > 1:
        out["ok"] = False
        out["state"] = INVARIANT_VIOLATED
        out["detail"] = (
            "ACS_SINGLE_INSTANCE=1 was declared but %s=%d asks for more than "
            "one process/instance. Each instance would carry its own quota, so "
            "the global daily cap would be multiplied silently."
            % (source, concurrency))
        return out
    out["state"] = INVARIANT_SINGLE
    out["detail"] = ("single process, single instance, declared and verified; "
                     "quotas are exact for this deployment")
    return out


def enforce_production_invariant(limiter=None, env=None):
    """يرفع ProductionInvariantError إن كان الضبط لا يجوز الإقلاع عليه."""
    d = production_invariant(limiter, env)
    if not d["ok"]:
        raise ProductionInvariantError("%s: %s" % (d["state"], d["detail"]))
    return d


# ---------------------------------------------------------------------------
# §5 — الهويّة. دالّة صرفة: لا FastAPI ولا Request ولا حالة.
# ---------------------------------------------------------------------------
#: أطول ترويسة يُنظر فيها. أي أطول ⇒ مشوّهة ⇒ تُهمَل كاملةً (لا تُقصّ جزئياً،
#: فالقصّ الجزئي بحدّ ذاته يُنتج دلواً جديداً لكل طلب).
MAX_HEADER_LEN = 512
#: أكثر من هذا العدد من القفزات في ترويسة واحدة = حشو مقصود ⇒ تُهمَل.
MAX_XFF_PARTS = 32
UNKNOWN_IDENTITY = "?"


def _clean_header(value):
    """None إن كانت الترويسة مشوّهة أو مفرطة الطول أو متعدّدة الأسطر."""
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("ascii", "strict")
        except Exception:
            return None
    if not isinstance(value, str):
        return None
    if len(value) > MAX_HEADER_LEN:
        return None                      # 10KB من القمامة: تُهمَل كاملةً
    # حقن الأسطر (CR/LF/NUL) أو أي حرف تحكّم ⇒ الترويسة غير موثوقة إطلاقاً.
    for ch in value:
        if ord(ch) < 0x20 or ord(ch) == 0x7F:
            return None
    value = value.strip()
    return value or None


def normalise_ip(token):
    """يُعيد الشكل القانوني للعنوان أو None إن لم يكن عنواناً أصلاً."""
    if not token:
        return None
    token = token.strip()
    if not token or len(token) > 64:
        return None
    if token.startswith("[") and "]" in token:            # [::1]:8080
        token = token[1:token.index("]")]
    else:
        # 1.2.3.4:5678 — منفذ على IPv4 فقط. IPv6 العاري مليء بالنقطتين.
        if token.count(":") == 1 and token.count(".") == 3:
            token = token.split(":", 1)[0]
    try:
        return ipaddress.ip_address(token).compressed
    except ValueError:
        return None


def trusted_hops(env=None):
    """عدد الوكلاء الموثوقين. يتحمّل ACS_TRUSTED_PROXIES= الفارغ (لا ValueError)."""
    return env_int("ACS_TRUSTED_PROXIES", 1, env, minimum=0, maximum=16)


def client_identity(headers, peer_ip, env=None):
    """هويّة الزائر لأغراض حدّ المعدّل — لا تُصدّق ما يستطيع العميل كتابته.

    القواعد:
      * X-Forwarded-For تُقرأ من اليمين لليسار: العنصر رقم `hops` من النهاية
        هو ما كتبه آخر وكيل موثوق. ما قبله يكتبه العميل ويستطيع تزويره.
      * hops = 0 (لا وكيل موثوق) ⇒ XFF كلّها مُهمَلة، والعنوان هو نظير TCP.
      * X-Real-IP مُهمَلة افتراضياً. لا تُقرأ إلا حين ACS_TRUST_X_REAL_IP=1،
        وعندها فقط إذا كان hops == 0 أو كانت XFF غائبة/غير صالحة.
        (هذا هو الثقب المُصلَح: الكود القديم يقرؤها بلا أي حساب للقفزات.)
      * أي ترويسة مشوّهة أو طويلة أو متعدّدة الأسطر أو غير شكل IP ⇒ تُهمَل
        ويُرجَع نظير TCP. لا يُنتَج أبداً دلوٌ جديد من قيمة يتحكّم بها العميل.
    """
    peer = normalise_ip(peer_ip) or UNKNOWN_IDENTITY
    lowered = {}
    if headers:
        try:
            items = headers.items()
        except AttributeError:
            items = list(headers or [])
        for k, v in items:
            if isinstance(k, (bytes, bytearray)):
                k = k.decode("ascii", "ignore")
            try:
                lowered[str(k).strip().lower()] = v
            except Exception:
                continue

    hops = trusted_hops(env)

    if hops > 0:
        fwd = _clean_header(lowered.get("x-forwarded-for"))
        if fwd:
            parts = [p.strip() for p in fwd.split(",") if p.strip()]
            if parts and len(parts) <= MAX_XFF_PARTS:
                # اليمين لليسار: parts[-hops] حين تكفي العناصر.
                token = parts[-min(hops, len(parts))]
                ip = normalise_ip(token)
                if ip:
                    return ip
            # XFF موجودة لكن غير صالحة ⇒ نظير TCP، لا X-Real-IP.
            return peer

    if env_flag("ACS_TRUST_X_REAL_IP", False, env):
        real = _clean_header(lowered.get("x-real-ip"))
        if real:
            ip = normalise_ip(real)
            if ip:
                return ip

    return peer


# ---------------------------------------------------------------------------
# §6 — السياسة. نفس ترتيب guard() الحالي حرفياً.
# ---------------------------------------------------------------------------
KIND_GEN = "gen"
KIND_EDIT = "edit"

MSG_GLOBAL = ("بلغ الخادم سقفه اليومي. حاول غداً أو شغّل نسخة خاصة بك.")
MSG_BACKEND_CLOSED = ("خدمة حدّ الطلبات غير متاحة مؤقتاً. أعِد المحاولة بعد "
                      "قليل.")
MSG_EVICTED = ("تعذّر التحقّق من حصّتك بسبب ضغط على الخادم. أعِد المحاولة "
               "لاحقاً.")


class RateLimiter(object):
    """يُركّب واجهةً خلفية مع السياسة. بلا حالة محلية — الحالة كلّها في الخلفية.

    ولذلك: نسختان من RateLimiter فوق نفس الـRedis تُطبّقان حِصّة واحدة، وإعادة
    بناء RateLimiter (إعادة تشغيل العملية) لا تُعيد أي حِصّة.
    """

    def __init__(self, backend=None, limits=None, fail_policy=None,
                 namespace="v1", env=None):
        self.backend = backend if backend is not None else make_backend(env)
        self.limits = dict(limits or limits_from_env(env))
        self.fail_policy = (fail_policy or fail_policy_from_env(env)).lower()
        if self.fail_policy not in (FAIL_CLOSED, FAIL_OPEN):
            self.fail_policy = FAIL_CLOSED
        self.namespace = namespace
        self._lock = threading.Lock()
        self._last_error = None
        self._backend_errors = 0

    # -- المفاتيح: مُعرَّفة صراحةً كي يستطيع الاختبار والتشخيص قراءتها --------
    def key(self, scope, identity=""):
        if scope == SCOPE_GLOBAL_DAY:
            return "%s:ALL:day" % self.namespace
        return "%s:%s:%s" % (self.namespace, scope, identity)

    def _hit(self, scope, identity, limit, window_s, now, consume):
        key = self.key(scope, identity)
        return self.backend.hit(key, limit, window_s, now, consume=consume)

    def _refusal(self, scope, identity, wait, message, now):
        """رفضٌ عادي — إلا إن كان سببه إخلاء LRU من ذاكرة العملية، فيُسمّى
        باسمه (SCOPE_EVICTED) كي لا يُقرأ سجلّ الإنتاج كأنه زائر متجاوز."""
        backend = self.backend
        if hasattr(backend, "evicted_at"):
            try:
                if backend.evicted_at(self.key(scope, identity), now):
                    return self._decision(False, ACS_RATE_LIMITED, wait,
                                          SCOPE_EVICTED, MSG_EVICTED)
            except Exception:
                pass
        return self._decision(False, ACS_RATE_LIMITED, wait, scope, message)

    def _decision(self, allowed, code=None, retry_after=0, scope=None,
                  message=None):
        return {
            "allowed": bool(allowed),
            "code": code,
            "retry_after": int(retry_after or 0),
            "scope": scope,
            "message": message,
            "limits": dict(self.limits),
        }

    def _backend_failure(self, exc):
        with self._lock:
            self._backend_errors += 1
            # فئة العطل فقط. نصّ الاستثناء يحمل عادةً مضيفاً أو منفذاً أو
            # اعتماداً (رسائل redis-py تفعل ذلك حرفياً) فلا يُخزَّن للعرض.
            self._last_error = type(exc).__name__
        LOG.error("rate limit backend failure (%s policy): %s",
                  self.fail_policy, exc)
        if self.fail_policy == FAIL_OPEN:
            # يبقى الباب مفتوحاً والرصيد مكشوفاً — قرار واعٍ لا افتراضي.
            d = self._decision(True, scope=SCOPE_BACKEND)
            d["degraded"] = True
            return d
        d = self._decision(False, ACS_RATE_LIMITED,
                           BACKEND_DOWN_RETRY_AFTER_S, SCOPE_BACKEND,
                           MSG_BACKEND_CLOSED)
        d["degraded"] = True
        return d

    def check(self, identity, kind=KIND_GEN, now=None):
        """القرار المُهيكل. `now` يُحقن للحتمية (اختبار بلا نوم)."""
        if now is None:
            now = time.time()
        identity = identity or UNKNOWN_IDENTITY
        gl = self.limits["global_day"]
        try:
            # 1) السقف العام يُفحص بلا استهلاك — زائرٌ مرفوض لا يُطفئ الخدمة
            #    للجميع (هذا الترتيب مقصود في الكود الحالي ومُبقًى كما هو).
            ok, wait, _ = self._hit(SCOPE_GLOBAL_DAY, "", gl, WINDOW_DAY,
                                    now, consume=False)
            if not ok:
                return self._decision(False, ACS_RATE_LIMITED, wait,
                                      SCOPE_GLOBAL_DAY, MSG_GLOBAL)

            # 2) حدود الزائر.
            if kind == KIND_GEN:
                lim = self.limits["gen_hour"]
                ok, wait, _ = self._hit(SCOPE_GEN_HOUR, identity, lim,
                                        WINDOW_HOUR, now, consume=True)
                if not ok:
                    return self._refusal(
                        SCOPE_GEN_HOUR, identity, wait,
                        "تجاوزت %d عمليات توليد في الساعة. أعِد المحاولة بعد "
                        "%d دقيقة." % (lim, max(1, wait // 60)), now)
                lim = self.limits["gen_day"]
                ok, wait, _ = self._hit(SCOPE_GEN_DAY, identity, lim,
                                        WINDOW_DAY, now, consume=True)
                if not ok:
                    return self._refusal(
                        SCOPE_GEN_DAY, identity, wait,
                        "تجاوزت %d عملية توليد اليوم. أعِد المحاولة غداً."
                        % lim, now)
            else:
                lim = self.limits["edit_hour"]
                ok, wait, _ = self._hit(SCOPE_EDIT_HOUR, identity, lim,
                                        WINDOW_HOUR, now, consume=True)
                if not ok:
                    return self._refusal(
                        SCOPE_EDIT_HOUR, identity, wait,
                        "تجاوزت حدّ التعديلات في الساعة. أعِد المحاولة بعد "
                        "%d دقيقة." % max(1, wait // 60), now)

            # 3) السقف العام يُستهلك أخيراً، بعد اجتياز كل فحوص الزائر.
            ok, wait, _ = self._hit(SCOPE_GLOBAL_DAY, "", gl, WINDOW_DAY,
                                    now, consume=True)
            if not ok:
                return self._decision(False, ACS_RATE_LIMITED, wait,
                                      SCOPE_GLOBAL_DAY, MSG_GLOBAL)
            return self._decision(True)
        except BackendOperationError as exc:
            return self._backend_failure(exc)
        except RateLimitError:
            raise
        except Exception as exc:                 # عميل مُحقن يرمي أي شيء
            return self._backend_failure(exc)

    def peek(self, scope, identity="", now=None):
        """(count) بلا استهلاك — للتشخيص والاختبار."""
        if now is None:
            now = time.time()
        limit = {
            SCOPE_GLOBAL_DAY: self.limits["global_day"],
            SCOPE_GEN_HOUR: self.limits["gen_hour"],
            SCOPE_GEN_DAY: self.limits["gen_day"],
            SCOPE_EDIT_HOUR: self.limits["edit_hour"],
        }[scope]
        window = WINDOW_HOUR if scope in (SCOPE_GEN_HOUR, SCOPE_EDIT_HOUR) \
            else WINDOW_DAY
        _, _, count = self._hit(scope, identity, limit, window, now,
                                consume=False)
        return count

    def backend_errors(self):
        with self._lock:
            return self._backend_errors, self._last_error


# ---------------------------------------------------------------------------
# §7 — الصحّة. لا سرّ يخرج من هنا: لا ACS_REDIS_URL ولا مضيف ولا كلمة سرّ.
# ---------------------------------------------------------------------------
def _redis_url_facts(env=None):
    """المخطَّط فقط + هل ضُبطت كلمة سرّ (منطقي). لا شيء آخر — أبداً."""
    url = env_str("ACS_REDIS_URL", "", env)
    if not url:
        return {"redis_scheme": None, "redis_password_configured": False}
    scheme = url.split("://", 1)[0].lower() if "://" in url else None
    if scheme not in ("redis", "rediss", "unix"):
        scheme = None                     # لا نُصدّر نصّاً غير معروف المصدر
    has_password = False
    try:
        rest = url.split("://", 1)[1] if "://" in url else ""
        authority = rest.split("/", 1)[0]
        if "@" in authority:
            userinfo = authority.rsplit("@", 1)[0]
            has_password = ":" in userinfo and \
                bool(userinfo.split(":", 1)[1])
    except Exception:
        has_password = False
    return {"redis_scheme": scheme, "redis_password_configured": has_password}


_DEFAULT_LIMITER = None
_DEFAULT_LOCK = threading.Lock()


def default_limiter(env=None):
    """محدّد وحيد للعملية، يُبنى كسولاً. الاستيراد لا يلمس البيئة ولا الشبكة."""
    global _DEFAULT_LIMITER
    with _DEFAULT_LOCK:
        if _DEFAULT_LIMITER is None:
            _DEFAULT_LIMITER = RateLimiter(env=env)
        return _DEFAULT_LIMITER


def reset_default_limiter():
    """للاختبار وإعادة التهيئة بعد تغيير البيئة."""
    global _DEFAULT_LIMITER
    with _DEFAULT_LOCK:
        _DEFAULT_LIMITER = None


def health_status(limiter=None, env=None):
    """حالة حدّ المعدّل — تُعرض في /health وتُسجَّل عند الإقلاع.

    مفاتيحها ثابتة:
      backend      "memory" | "redis"
      distributed  False يعني: هذا الحدّ محليّ العملية. نسختان = حِصّتان.
      fail_policy  "closed" | "open"
      limits       الحدود الأربعة الفعّالة
      healthy      نتيجة فحص حيّ للواجهة الخلفية
    ولا تحتوي أبداً على ACS_REDIS_URL ولا مضيف ولا كلمة سرّ.
    """
    lim = limiter if limiter is not None else default_limiter(env)
    backend = lim.backend
    try:
        healthy = bool(backend.healthy())
    except Exception as exc:
        LOG.warning("rate limit: health probe raised: %s", exc)
        healthy = False
    errors, last_error = lim.backend_errors()
    if errors:
        healthy = False

    choice, explicit = backend_choice(env)
    warnings = []
    distributed = bool(getattr(backend, "distributed", False))
    if not distributed:
        warnings.append("PROCESS_LOCAL_RATE_LIMIT")
    if not explicit and env_str("ACS_ENV", "development", env).lower() \
            == "production":
        warnings.append("PRODUCTION_WITHOUT_DISTRIBUTED_BACKEND")
    if not healthy:
        warnings.append("BACKEND_UNHEALTHY")

    out = {
        "contract": CONTRACT_VERSION,
        "backend": getattr(backend, "name", "unknown"),
        # F-47: القرار التشغيليّ نفسه، لا التحذير وحده.
        "production_invariant": production_invariant(lim, env),
        "distributed": distributed,
        "fail_policy": lim.fail_policy,
        "limits": dict(lim.limits),
        "healthy": healthy,
        "env": env_str("ACS_ENV", "development", env).lower(),
        "backend_errors": errors,
        "warnings": warnings,
        "stats": backend.stats() if hasattr(backend, "stats") else {},
    }
    if out["backend"] == "redis":
        out.update(_redis_url_facts(env))     # المخطَّط ومنطقيٌّ فقط
    if last_error:
        # اسم صنف الاستثناء فقط، لا نصّه — انظر RateLimiter._backend_failure.
        out["last_error_kind"] = str(last_error)[:60]
    return out


__all__ = [
    "CONTRACT_VERSION", "ACS_RATE_LIMITED", "LUA_HIT",
    "RateLimitError", "RateLimitBackendUnavailable", "BackendOperationError",
    "RateLimitBackend", "MemoryBackend", "RedisBackend",
    "RateLimiter", "make_backend", "backend_choice", "redis_client_from_url",
    "client_identity", "normalise_ip", "trusted_hops",
    "health_status", "default_limiter", "reset_default_limiter",
    "ProductionInvariantError", "production_invariant",
    "enforce_production_invariant", "declared_concurrency",
    "CONCURRENCY_VARS", "INVARIANT_DISTRIBUTED", "INVARIANT_SINGLE",
    "INVARIANT_DEV", "INVARIANT_UNDECLARED", "INVARIANT_VIOLATED",
    "limits_from_env", "fail_policy_from_env", "env_int", "env_str",
    "env_flag",
    "SCOPE_GLOBAL_DAY", "SCOPE_GEN_HOUR", "SCOPE_GEN_DAY", "SCOPE_EDIT_HOUR",
    "SCOPE_BACKEND", "SCOPE_EVICTED", "KIND_GEN", "KIND_EDIT",
    "FAIL_OPEN", "FAIL_CLOSED", "WINDOW_HOUR", "WINDOW_DAY",
]
