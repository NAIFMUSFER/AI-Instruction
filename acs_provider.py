# -*- coding: utf-8 -*-
"""acs_provider.py — طبقة حلّ مزوّد النموذج: اسمٌ ومفتاحٌ وعنوانٌ ونموذجٌ ونقل.

لماذا طبقة مستقلّة؟ لأن `acs_understand._call_llm_impl` كان يبني العميل بنفسه:

    anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=...)

فاسم المزوّد ومفتاحه وعنوانه كانت ثلاثة قرارات مبعثرة داخل دالّة التوليد. تبديل
نقطة النهاية كان يعني تعديل مسار التوليد نفسه — وهو المسار الذي تحرسه KI-23
وKI-24 وF-50. هنا تُحلّ كلّ هذه القرارات **قبل** أي بايت شبكة، وتُسلَّم إلى مسار
التوليد ككائن واحد لا يعرف من أمره شيئاً.

عقد هذه الوحدة: دوالّ خالصة تقرأ البيئة وتعيد قيماً. لا تستورد anthropic، ولا
تفتح اتصالاً، ولا تطبع سرّاً، ولا ترمي استثناءً غير معلن.

المتغيّرات:
    ACS_LLM_PROVIDER            deepseek | anthropic          (افتراضي anthropic)
    ACS_LLM_BASE_URL            عنوان نقطة النهاية            (افتراضي حسب المزوّد)
    ACS_LLM_API_KEY             المفتاح                       (لا افتراضي)
    ACS_LLM_MODEL               معرّف النموذج                  (افتراضي حسب المزوّد)
    ACS_LLM_TRANSPORT           stream | create               (افتراضي stream)

    ACS_LLM_FALLBACK_PROVIDER   المزوّد البديل — غيابه يعني «لا بديل»
    ACS_LLM_FALLBACK_BASE_URL
    ACS_LLM_FALLBACK_API_KEY
    ACS_LLM_FALLBACK_MODEL
    ACS_LLM_FALLBACK_ON_BILLING 1 لتفعيل التحويل عند عطل الرصيد (افتراضي 0)

توافق خلفيّ صريح: إن غاب ACS_LLM_API_KEY وكان المزوّد anthropic، يُقبل
ANTHROPIC_API_KEY القديم. ولا يُقبل أبداً كمفتاح deepseek — مفتاح مزوّد يُرسل
إلى مزوّد آخر تسريبُ اعتماد، لا «تجربة».
"""

import os
import re

CONTRACT_VERSION = "acs.provider/1.0.0"

#: المزوّدون المعروفون. اسمٌ خارج هذه القائمة عطلُ ضبطٍ لا عطلُ منبع.
PROVIDERS = ("anthropic", "deepseek")

# ملاحظة مصدر — الأرقام والعناوين هنا موثّقة عند المزوّد، لا مُستنتجة:
#   deepseek base_url و«واجهة Anthropic المتوافقة»:
#       https://api-docs.deepseek.com/guides/anthropic_api
#   معرّفات نماذج deepseek وسقف المخرجات 384K:
#       https://api-docs.deepseek.com/quick_start/pricing
#   رمز 402 «Insufficient Balance»:
#       https://api-docs.deepseek.com/quick_start/error_codes
# سقف مخرجات anthropic غير موثّق في هذا المستودع، فيبقى None — ولا يُخترع رقم.
PROVIDER_SPEC = {
    "anthropic": {
        "base_url": None,                 # نقطة النهاية الافتراضية للمكتبة
        "requires_base_url": False,
        "models": ("claude-sonnet-5", "claude-haiku-4-5"),
        "documented_max_output": None,    # غير موثّق هنا: لا يُخترع
        "legacy_key_env": "ANTHROPIC_API_KEY",
        "key_prefix": "sk-ant-",
        "capabilities": {
            # النظام كلّه مُعاير على هذا المزوّد منذ نشأته: `output_tokens`
            # تقارب حجم JSON المرئي، فتُقرأ كثافةً وتُشتقّ منها أحجام الشرائح.
            # هذا هو السلوك القائم، ويبقى كما هو حرفياً.
            "output_tokens_are_content_proxy": True,
            "content_token_multiplier": 1.0,
        },
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/anthropic",
        "requires_base_url": True,        # بلا عنوان صريح لا يُنادى إطلاقاً
        "models": ("deepseek-v4-pro", "deepseek-v4-flash"),
        "documented_max_output": 384000,  # موثّق: MAXIMUM 384K
        "legacy_key_env": None,           # لا مفتاح قديم يُستعار لهذا المزوّد
        "key_prefix": None,
        "capabilities": {
            # W2-B · مُقاسٌ حيّاً على الإنتاج (SHA 681ec04)، لا مُستنتَج:
            #   stage=single  out_tokens=13945  out_chars=6917   cpt=0.496
            #   stage=single  out_tokens=31022  out_chars=20463  cpt=0.6596
            #   stage=single  out_tokens=32000  out_chars=18982  cpt=0.5932 (قُطِع)
            #   stage=plan    out_tokens=16000  out_chars=0      cpt=0.0
            #                 blocks=1 types=thinking:1 text_blocks=0
            # النداء الأخير يحسم المسألة: ميزانيةٌ كاملة استُهلكت في كتلة تفكير
            # وحدها، بصفر حرفٍ مرئيّ. فـ`output_tokens` عند هذا المزوّد ليست
            # وكيلاً عن حجم المحتوى — لا كثافةً تُقرأ ولا سعةً تُحجَز عليها.
            "output_tokens_are_content_proxy": False,
            # كم رمز مخرج **محاسَب** يستهلكه رمزُ محتوى واحد يقدّره المقدّر.
            # مشتقّ من الحالة المتوسّطة المقيسة: تقدير 15944 → استهلاك 31022،
            # أي 1.946. المعلن 2.0 بهامشٍ في اتّجاه الأمان وحده. لا يرفع سقفاً:
            # يرفع **الطلبَ المقدَّر** فيُوجَّه إلى المراحل أبكر (القاعدة 6).
            "content_token_multiplier": 2.0,
        },
    },
}

# قيم القدرة حين لا يعلنها المزوّد. الافتراض هو السلوك القائم: أي مزوّد جديد
# يُعامَل معاملة anthropic حتى يُقاس ويُعلَن خلافُ ذلك — فلا يتغيّر سلوكٌ بصمت.
CAPABILITY_DEFAULTS = {
    "output_tokens_are_content_proxy": True,
    "content_token_multiplier": 1.0,
}

#: حدود المضاعِف. أقلّ من 1.0 يعني ادّعاء أن المزوّد أوفر من المقدّر — وهو رفعٌ
#: للعتبة في اتّجاه الخطر، فيُمنع. والأعلى حارسٌ ضدّ ضبطٍ خاطئ يشلّ التوجيه.
MIN_CONTENT_TOKEN_MULTIPLIER = 1.0
MAX_CONTENT_TOKEN_MULTIPLIER = 8.0

#: تجاوزات المشغّل — لتصحيح إعلانٍ كذّبه القياس بلا تعديل شفرة ولا نشر.
_CAPABILITY_ENV = {
    "output_tokens_are_content_proxy": "ACS_LLM_OUTPUT_TOKENS_CONTENT_PROXY",
    "content_token_multiplier": "ACS_LLM_CONTENT_TOKEN_MULTIPLIER",
}

#: النقل المسموح. `stream` هو سلوك الإنتاج القائم ولا يتغيّر بلا ضبط صريح.
TRANSPORTS = ("stream", "create")

# ── حالات الحلّ ─────────────────────────────────────────────────────────────
RESOLVED = "resolved"
UNKNOWN_PROVIDER = "unknown_provider"
MISSING_KEY = "missing_key"
MISSING_BASE_URL = "missing_base_url"
NOT_CONFIGURED = "not_configured"          # لا بديل مُعلن أصلاً

_HOST_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://(?:[^/@]*@)?([^/:?#]+)", re.I)


def _env(name, default=""):
    return (os.environ.get(name, default) or "").strip()


def clean_key(raw, provider="anthropic"):
    """يزيل ما يلتصق بالمفتاح عند اللصق: فراغات وعلامات اقتباس.

    لمزوّد له بادئة معروفة يُستخرج المفتاح بالبادئة — وهو سلوك
    `acs_understand.clean_key` القائم لـanthropic، محفوظاً حرفياً. لمزوّد بلا
    بادئة معلنة يُكتفى بالتقليم: التخمين هنا قد يبتر مفتاحاً صحيحاً.
    """
    raw = (raw or "").strip().strip('"').strip("'")
    prefix = (PROVIDER_SPEC.get(provider) or {}).get("key_prefix")
    if prefix:
        m = re.search(re.escape(prefix) + r"[A-Za-z0-9_\-]+", raw)
        return m.group(0) if m else raw
    return raw


def base_host(url):
    """اسم المضيف وحده من عنوان — بلا مسار ولا استعلام ولا اعتماد مضمَّن.

    التليمتري يحتاج «إلى أين ذهب النداء»، لا العنوان الكامل: العنوان قد يحمل
    `user:pass@` وقد يحمل رمزاً في الاستعلام. المضيف يجيب على السؤال ولا يحمل
    سرّاً.
    """
    if not url:
        return None
    m = _HOST_RE.match(str(url).strip())
    return m.group(1).lower() if m else None


class ProviderConfig(object):
    """ضبطٌ محلول لمزوّد واحد. لا يحمل عميلاً ولا يفتح اتصالاً.

    `api_key` موجودة لأن مسار النداء يحتاجها، ولا تظهر في `__repr__` ولا في
    `public()` ولا في أي حقل تليمتري — والاختبار يثبت ذلك على الكائن نفسه.
    """

    __slots__ = ("role", "provider", "api_key", "base_url", "model",
                 "transport", "documented_max_output", "state", "missing")

    def __init__(self, role, provider, api_key=None, base_url=None, model=None,
                 transport="stream", documented_max_output=None,
                 state=RESOLVED, missing=None):
        self.role = role
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.transport = transport
        self.documented_max_output = documented_max_output
        self.state = state
        self.missing = tuple(missing or ())

    @property
    def ok(self):
        return self.state == RESOLVED

    @property
    def base_host(self):
        return base_host(self.base_url)

    def public(self):
        """كل ما يجوز أن يخرج إلى /health أو السجلّ. لا مفتاح ولا عنوان كامل."""
        return {"role": self.role,
                "provider": self.provider,
                "model": self.model,
                "base_host": self.base_host,
                "transport": self.transport,
                "state": self.state,
                "missing": list(self.missing)}

    def __repr__(self):                                        # pragma: no cover
        return "<ProviderConfig %s provider=%s model=%s host=%s state=%s>" % (
            self.role, self.provider, self.model, self.base_host, self.state)


def _resolve(role, prefix, legacy_key_allowed):
    """يحلّ دوراً واحداً (primary أو fallback) من متغيّراته وحدها."""
    name = _env(prefix + "PROVIDER").lower()
    if role == "primary" and not name:
        name = "anthropic"                       # التوافق الخلفي هو الافتراضي
    if not name:
        return ProviderConfig(role, None, state=NOT_CONFIGURED)
    if name not in PROVIDER_SPEC:
        return ProviderConfig(role, name, state=UNKNOWN_PROVIDER,
                              missing=(prefix + "PROVIDER",))
    spec = PROVIDER_SPEC[name]

    base_url = _env(prefix + "BASE_URL") or spec["base_url"]
    model = _env(prefix + "MODEL") or spec["models"][0]

    transport = _env("ACS_LLM_TRANSPORT").lower() or "stream"
    if transport not in TRANSPORTS:
        transport = "stream"

    key = clean_key(_env(prefix + "API_KEY"), name)
    if not key and legacy_key_allowed and spec["legacy_key_env"]:
        # التوافق الخلفي: نشرٌ قائم لا يعرف ACS_LLM_API_KEY يظلّ يعمل.
        # مقصورٌ على المزوّد صاحب المفتاح — لا يُعار مفتاح anthropic لـdeepseek.
        key = clean_key(_env(spec["legacy_key_env"]), name)

    missing = []
    if not key:
        missing.append(prefix + "API_KEY")
    if spec["requires_base_url"] and not base_url:
        missing.append(prefix + "BASE_URL")

    state = RESOLVED
    if missing:
        state = MISSING_BASE_URL if (
            spec["requires_base_url"] and not base_url) else MISSING_KEY

    return ProviderConfig(role, name, api_key=key or None, base_url=base_url,
                          model=model, transport=transport,
                          documented_max_output=spec["documented_max_output"],
                          state=state, missing=missing)


def primary():
    """المزوّد الأساسي. الافتراضي anthropic بمفتاحه القديم — نشرٌ قائم لا يتغيّر."""
    return _resolve("primary", "ACS_LLM_", legacy_key_allowed=True)


def fallback():
    """المزوّد البديل. غياب ACS_LLM_FALLBACK_PROVIDER يعني «لا بديل» صراحةً.

    المفتاح القديم مقبول هنا أيضاً حين يكون البديل anthropic: هذا هو الشكل
    الإنتاجي المقصود — deepseek أساسياً وanthropic بديلاً بمفتاحه المضبوط سلفاً.
    """
    return _resolve("fallback", "ACS_LLM_FALLBACK_", legacy_key_allowed=True)


def fallback_on_billing():
    """هل يُسمح بالتحويل عند عطل رصيد/حساب؟ افتراضياً لا.

    عطل الرصيد ليس عطلاً عابراً: التحويل التلقائي عنده ينقل الإنفاق إلى مزوّد
    آخر بلا قرار بشريّ. يبقى خلف مفتاح صريح.
    """
    return _env("ACS_LLM_FALLBACK_ON_BILLING", "0") in ("1", "true", "yes", "on")


def should_fallback(code, fb=None):
    """هل يجوز التحويل إلى البديل بسبب هذا الرمز؟ (السبب، لا الرأي).

    ثلاثة شروط مجتمعة، وغياب أيّها منعٌ:
      1) بديلٌ محلول فعلاً (مفتاح ونموذج وعنوان)،
      2) الرمز ضمن قائمة السماح المعلنة في acs_api_errors،
      3) وإن كان رمز الفوترة، فبمفتاح المشغّل الصريح وحده.

    تعيد (bool, reason) — والسبب يُسجَّل كما هو في التليمتري، فيقرأ المشغّل
    **لماذا** لم يقع التحويل، لا صمتاً يُقرأ «لا بديل مضبوط».
    """
    import acs_api_errors as E
    fb = primary_fallback_or(fb)
    if not fb.ok:
        return False, "no_fallback_configured"
    if code in E.FALLBACK_ELIGIBLE:
        return True, "provider_unavailable"
    if code in E.FALLBACK_ELIGIBLE_ON_BILLING:
        if fallback_on_billing():
            return True, "provider_billing"
        return False, "billing_fallback_disabled"
    return False, "code_not_eligible"


def primary_fallback_or(fb):
    """يقبل ضبطاً محلولاً مسبقاً أو يحلّه — حتى لا يُقرأ المحيط مرّتين."""
    return fb if isinstance(fb, ProviderConfig) else fallback()


def allowed_models(cfg=None):
    """قائمة النماذج المسموح طلبها. ACS_ALLOWED_MODELS يعلوها إن ضُبط.

    بلا هذا كان الافتراضي المدفون `claude-sonnet-5,claude-haiku-4-5` يرفض أي
    معرّف deepseek، فيقلع الخادم ويردّ /ready بـ503 بلا سبب واضح.
    """
    raw = _env("ACS_ALLOWED_MODELS")
    if raw:
        return {m.strip() for m in raw.split(",") if m.strip()}
    cfg = cfg or primary()
    spec = PROVIDER_SPEC.get(cfg.provider or "anthropic") or PROVIDER_SPEC["anthropic"]
    models = set(spec["models"])
    if cfg.model:
        models.add(cfg.model)
    return models


def documented_max_output(cfg=None):
    """سقف مخرجات النموذج **الموثّق عند المزوّد** — أو None إن لم يُوثَّق.

    F-50 أبقى ACS_LLM_MODEL_MAX_OUTPUT سقفاً واحداً معلناً للمشغّل. هذه الدالّة
    لا تنافسه: تُستشار حين يغيب وحده، فلا يُخترع رقم ولا يُرفع سقف قائم.
    """
    cfg = cfg or primary()
    return (PROVIDER_SPEC.get(cfg.provider or "") or {}).get(
        "documented_max_output")


def capabilities(cfg=None):
    """قدرات المزوّد المُعلَنة — قاموسٌ واحد، تجاوزات المشغّل تعلوه (W2-B).

    لماذا «قدرة» لا «اسم مزوّد»
    ---------------------------
    الشرط الثاني في تفويض W2: «لا تتفرّع على اسم المزوّد داخل منطق التقطيع».
    الاسم صفةُ هوية لا صفةُ سلوك: مزوّدٌ ثالث قد يشارك deepseek محاسبتَه،
    وdeepseek نفسه قد يغيّرها غداً. فما يقرؤه منطقُ التوجيه والتقطيع هو
    **ما يفعله المزوّد** كما أُعلن هنا وقِيسَ حيّاً — لا مَن هو.

    القيم مقيَّدة ومُصحَّحة: قيمة غير صالحة تسقط إلى المُعلَن، والمُعلَن يسقط
    إلى CAPABILITY_DEFAULTS. لا يرفع هذا أبداً.
    """
    cfg = cfg or primary()
    spec_caps = (PROVIDER_SPEC.get(cfg.provider or "") or {}).get("capabilities")
    out = dict(CAPABILITY_DEFAULTS)
    if isinstance(spec_caps, dict):
        out.update(spec_caps)

    raw = _env(_CAPABILITY_ENV["output_tokens_are_content_proxy"])
    if raw:
        low = raw.lower()
        if low in ("1", "true", "yes", "on"):
            out["output_tokens_are_content_proxy"] = True
        elif low in ("0", "false", "no", "off"):
            out["output_tokens_are_content_proxy"] = False

    raw = _env(_CAPABILITY_ENV["content_token_multiplier"])
    if raw:
        try:
            out["content_token_multiplier"] = float(raw)
        except (TypeError, ValueError):
            pass

    out["output_tokens_are_content_proxy"] = bool(
        out.get("output_tokens_are_content_proxy"))
    try:
        m = float(out.get("content_token_multiplier"))
    except (TypeError, ValueError):
        m = CAPABILITY_DEFAULTS["content_token_multiplier"]
    if m != m:                                          # NaN
        m = CAPABILITY_DEFAULTS["content_token_multiplier"]
    out["content_token_multiplier"] = max(
        MIN_CONTENT_TOKEN_MULTIPLIER, min(MAX_CONTENT_TOKEN_MULTIPLIER, m))
    return out


def capability(name, cfg=None):
    """قدرة واحدة بالاسم. الاسم المجهول يعيد None — لا يرفع ولا يُخمَّن."""
    return capabilities(cfg).get(name)


def health_status():
    """حالة المزوّد لـ/health — أسماء وحالات فقط. لا مفتاح ولا عنوان كامل."""
    p = primary()
    f = fallback()
    return {"contract": CONTRACT_VERSION,
            "llm_provider": p.provider,
            "llm_model": p.model,
            "llm_base_host": p.base_host,
            "llm_transport": p.transport,
            "llm_state": p.state,
            "api_key_configured": bool(p.api_key),
            "fallback_configured": bool(f.ok),
            "fallback_provider": f.provider if f.state != NOT_CONFIGURED else None,
            "fallback_model": f.model if f.ok else None,
            "fallback_base_host": f.base_host if f.ok else None,
            "fallback_state": f.state,
            "fallback_on_billing": fallback_on_billing(),
            # W2-B: القدرة المُعلَنة تظهر في /health لأن التوجيه والتقطيع
            # يقرآنها. مشغّلٌ يرى تصعيداً غير متوقّع يحتاج أن يعرف بأي محاسبة
            # يعمل النظام الآن — بلا قراءة شفرة ولا تخمين.
            "capabilities": capabilities(p)}


def spec():
    """عقد الوحدة — تقرؤه الاختبارات بدل تكرار الأرقام."""
    return {"contract": CONTRACT_VERSION,
            "providers": list(PROVIDERS),
            "transports": list(TRANSPORTS),
            "states": [RESOLVED, UNKNOWN_PROVIDER, MISSING_KEY,
                       MISSING_BASE_URL, NOT_CONFIGURED],
            "capability_keys": sorted(CAPABILITY_DEFAULTS),
            "capability_defaults": dict(CAPABILITY_DEFAULTS),
            "capability_env": dict(_CAPABILITY_ENV),
            "content_token_multiplier_bounds": [MIN_CONTENT_TOKEN_MULTIPLIER,
                                                MAX_CONTENT_TOKEN_MULTIPLIER],
            "provider_spec": {k: dict(v) for k, v in PROVIDER_SPEC.items()}}
