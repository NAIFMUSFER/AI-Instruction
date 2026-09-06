# -*- coding: utf-8 -*-
# =============================================================================
# tests/remediation/lib_job_faults.py — أعطالٌ تقع **داخل العامل**.
#
# العامل يعمل في عملية أخرى، ويستورد وحدة الهدف باسمها:
#     mod = importlib.import_module(mod_name); fn = getattr(mod, fn_name)
# فترقيعُ دالّةٍ في عملية الاختبار لا يبلغه إطلاقاً. لذلك تُعلَن الأعطال هنا
# كدوالّ حقيقية على مستوى الوحدة، ويُوجَّه الهدف إليها، فيقع العطل حيث يقع في
# الإنتاج: في العامل، وعبر حدّ العملية نفسه، بلا محاكاةٍ للحدّ.
#
# التواقيع تقبل **كل** وسائط acs_understand.understand بأسمائها ثم تتجاهلها:
# ما يُختبَر هو انتقال الخطأ لا حساب النموذج. و`**_` يجعلها محصّنة من إضافة
# وسيطٍ جديد إلى العقد لاحقاً.
# =============================================================================
import time

import acs_api_errors as E


def upstream_auth(**_):
    """فشل استيثاق من المزوّد — مصنّف في العامل كما يُصنَّف في الإنتاج."""
    raise E.classify_upstream(_FakeUpstream("AuthenticationError", 401))


def upstream_trailing_json(**_):
    """العطل الإنتاجيّ الأصلي: ردٌّ بكائنين. يُرفَع مصنّفاً لا نصّاً خاماً."""
    raise E.AcsApiError(E.ACS_UPSTREAM_TRAILING_JSON,
                        "المزوّد أعاد أكثر من كائن JSON واحد.")


def stall(seconds=30.0, **_):
    """توقّفٌ حقيقيّ في العامل — يُختبَر به مهلة الخادم لا مهلةٌ مُحاكاة."""
    time.sleep(float(seconds))
    return {}


def unknown_failure(**_):
    """عطلٌ لم يصنّفه أحد. يجب أن يبقى ACS_UPSTREAM_UNKNOWN، لا أن يُرقّى."""
    raise RuntimeError("nobody classified this")


def leaky_failure(**_):
    """عطلٌ نصُّه يحمل ما لا يجوز أن يصل العميل: مفتاح وأثر استدعاء."""
    raise RuntimeError(
        "boom sk-ant-api03-LEAKED_SECRET_VALUE\n"
        '  File "/srv/acs/acs_understand.py", line 42, in understand\n'
        "    raise RuntimeError(...)")


def die_without_sending(**_):
    """تموت الابنة بلا إرسال — الحالة التي أنتجت EOFError في CI.

    `os._exit` يتخطّى كل معالج ومنقٍّ، فلا يُرسَل شيء عبر الأنبوب. هكذا يبدو
    عند الأب موتُ عاملٍ لأي سببٍ بيئيّ: إعادةُ تنفيذ ملفّ نقطة الدخول في
    spawn، أو قتلٌ بإشارة، أو خروجٌ مبكّر. الرمز 7 اعتباطيّ ومقصود: يُقرأ في
    رسالة JobError فيثبت أن الرقم يُنقَل لا يُخمَّن.
    """
    import os
    os._exit(7)


class _FakeUpstream(Exception):
    """شكلُ استثناءِ مزوّدٍ كما يراه المصنِّف: اسم صنف ورمز حالة."""

    def __init__(self, name, status):
        Exception.__init__(self, name)
        self.__class__ = type(name, (_FakeUpstream,), {})
        self.status_code = status
