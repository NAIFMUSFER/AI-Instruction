# -*- coding: utf-8 -*-
"""tests/remediation/test_validate_against_real_models.py — F-51.

لماذا هذه الحزمة موجودة إلى جانب test_validate_topology.py
----------------------------------------------------------
تلك الحزمة تفحص المنطق على نماذج **بنيتُها لتفشل**. وهي ضرورية ولا تكفي:
نموذجٌ مصنوع ليُرصَد يُرصَد دائماً. السؤال الذي لا تجيب عنه هو السؤال الذي
يقرّر مصير المدقّق عملياً — **كم مرّة يصرخ على نموذج سليم؟**

مدقّق يصرخ يُطفَأ خلال أسبوع، فيصير أسوأ من غيابه. ولأن ذلك عطلٌ لا يظهر إلا
على بيانات حقيقية، تُشغَّل الفحوص هنا على كل نموذج مبنى في المستودع — ١٦٥
نموذجاً موزّعة على تجهيزات المراحل، بينها مخرَجات مولَّدة حيّة.

ما كشفه هذا التشغيل فعلاً
-------------------------
في أوّل تشغيل أطلقت الفحوص الجديدة **١٠٨ بلاغات**. فُحصت واحدةً واحدة، فتبيّن
أن الأغلبية الساحقة أخطاء في **الفحص** لا في النماذج:

  • «باب لا يفتح على شيء» — ٣٣ بلاغاً، كلّها كاذبة. الفحص افترض أن كل فراغ
    ممثَّل كغرفة. في مستودع مولَّد حيّ تشغل الغرف ٨٦٪ من صندوقها المحيط،
    والـ١٤٪ الباقية ممرّات وغلاف لا تُمثَّل غرفاً. **أُسقط الفحص.**

  • «معلّق» — ٤٨ بلاغاً في ٢٤ نموذجاً، كلّها كاذبة. النماذج تمثّل طابقاً
    سفلياً جزئياً (الفندق: أرضيّ ٦٠ م² تحت نمطيّ ١١٠ م²). **أُضيف حارس
    تغطية ٦٠٪.**

  • «نافذة على جدار داخلي» — ٢٢ بلاغاً، ٢١ منها كاذبة. الدالة قبلت الجار على
    الجانبين احتياطاً لاصطلاح ظُنّ غير معلن، بينما acs_bim.py سطر ٣٣٠ يعرّفه
    صراحةً. **صُحّح إلى الحافّة المقصودة وحدها.**

النتيجة: من ١٠٨ بلاغات إلى ٦، ومن ٢٤ نموذجاً إلى ٦ من أصل ١٦٥.

هذه الحزمة تُثبّت ذلك السقف. رفعُه يعني أن فحصاً جديداً بدأ يصرخ على بيانات
سليمة — وهو ما يجب أن يفشل البناء، لا أن يُكتشَف بعد أن يُطفئه أحدهم.
"""
import collections
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_validate as V  # noqa: E402

# البلاغات التي أضافها F-51. الفحوص الثمانية السابقة (بلا إنارة، بلا باب…)
# مطالبُ محتوى تُطلقها التجهيزات المصغّرة بطبيعتها، ولا شأن لها بهذا السقف.
F51_MARKERS = ('النواة', 'معلّق', 'لا يوصل إليه', 'جدار داخلي', 'متراكبتان',
               'غير معرَّف', 'لا يشير إليه', 'مكرّر داخل القالب',
               'غير عددية', 'غير موجب')

# سقفٌ مقيس على الشجرة الحالية، لا رقم متفائل: ٦ بلاغات في ٦ نماذج من ١٦٥،
# كلٌّ منها فُحص يدوياً وثبت أنه رصدٌ صحيح (قالب بلا طابق في تجهيزة اسمها
# spare_template، نافذة داخلية في تجهيزة اسمها windowed، وحيّز معزول في
# تجهيزة عدائية عمداً فيها عرض 1e+21 وعمق 0.0).
MAX_FLAGGED_MODELS = 6
MAX_F51_ISSUES = 6
# وحارسٌ في الاتجاه الآخر: عيّنة أصغر من هذه تعني أن المسح توقّف عن العمل.
MIN_MODELS_SCANNED = 120


def _walk(obj, depth=0, path=''):
    """كل كائن يبدو نموذج مبنى، أينما كان في شجرة التجهيزة."""
    if depth > 6:
        return
    if isinstance(obj, dict):
        if isinstance(obj.get('floors'), dict) and 'levels' in obj:
            yield path or '<root>', obj
        for k, v in obj.items():
            yield from _walk(v, depth + 1, ('%s.%s' % (path, k)) if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, depth + 1, '%s[%d]' % (path, i))


def scan():
    """يعيد (عدد المفحوصة، البلاغات، الاستثناءات)."""
    scanned, flags, blew_up = 0, [], []
    for dirpath, _dirs, files in os.walk(os.path.join(ROOT, 'tests')):
        for fn in sorted(files):
            if not fn.endswith('.json'):
                continue
            full = os.path.join(dirpath, fn)
            try:
                with open(full, encoding='utf-8') as fh:
                    data = json.load(fh)
            except Exception:
                continue                      # ليست تجهيزة نموذج
            rel = os.path.relpath(full, ROOT)
            for path, model in _walk(data):
                scanned += 1
                try:
                    issues, stats = V.validate_building(model)
                except Exception as exc:      # noqa: BLE001
                    blew_up.append('%s :: %s → %s: %s'
                                   % (rel, path, type(exc).__name__, exc))
                    continue
                if not isinstance(issues, list) or not isinstance(stats, dict):
                    blew_up.append('%s :: %s → عقد الإرجاع مكسور' % (rel, path))
                    continue
                for issue in issues:
                    if any(m in issue for m in F51_MARKERS):
                        flags.append((rel, path, issue))
    return scanned, flags, blew_up


SCANNED, FLAGS, BLEW_UP = scan()


class RunsOnEverything(unittest.TestCase):

    def test_the_scan_actually_found_the_corpus(self):
        self.assertGreaterEqual(SCANNED, MIN_MODELS_SCANNED,
                                'المسح وجد %d نموذجاً فقط' % SCANNED)

    def test_not_one_real_model_makes_the_validator_raise(self):
        """المدقّق يبلّغ ولا ينهار. حلقة الإصلاح في acs_understand تستدعيه في
        خمسة مواضع؛ استثناءٌ هناك يوقف التوليد كلّه."""
        self.assertEqual(BLEW_UP, [])


class NoiseCeiling(unittest.TestCase):

    def test_the_new_checks_stay_quiet_on_real_models(self):
        models = {(f, p) for f, p, _ in FLAGS}
        self.assertLessEqual(
            len(models), MAX_FLAGGED_MODELS,
            'ارتفع عدد النماذج الحقيقية التي تُطلق بلاغاً إلى %d:\n%s'
            % (len(models), '\n'.join(sorted('%s :: %s' % m for m in models))))

    def test_the_total_number_of_new_issues_stays_bounded(self):
        self.assertLessEqual(
            len(FLAGS), MAX_F51_ISSUES,
            'ارتفع عدد البلاغات إلى %d:\n%s'
            % (len(FLAGS), '\n'.join('%s :: %s' % (f, i[:110])
                                     for f, _p, i in FLAGS)))

    def test_no_single_check_dominates_the_remaining_noise(self):
        """توزيعٌ يتكتّل في فحص واحد علامةُ افتراضٍ خاطئ فيه — وهو بالضبط ما
        كشف الفحوص الثلاثة المُصلَحة (٣٣ و٤٨ و٢٢ بلاغاً في فحص واحد)."""
        per = collections.Counter()
        for _f, _p, issue in FLAGS:
            for m in F51_MARKERS:
                if m in issue:
                    per[m] += 1
                    break
        for marker, count in per.items():
            self.assertLessEqual(count, 4, 'الفحص «%s» وحده أطلق %d بلاغاً'
                                 % (marker, count))

    def test_the_retired_door_check_has_not_come_back(self):
        self.assertEqual([f for f in FLAGS if 'لا يفتح على شيء' in f[2]], [])


class StillDetects(unittest.TestCase):
    """السقف أعلاه بلا معنى إن كان المدقّق صامتاً لأنه لا يفحص شيئاً."""

    def test_the_corpus_is_not_silent_by_accident(self):
        self.assertGreaterEqual(len(FLAGS), 1)

    def test_a_deliberately_broken_model_is_still_caught(self):
        broken = {
            'meta': {'type': 'residential'}, 'site': {'w': 20, 'd': 25},
            'levels': [{'index': 0, 'template': 'g'},
                       {'index': 1, 'template': 'f1'}],
            'floors': {
                'g': {'rooms': [
                    {'id': 'stair_1', 'rect': [0, 0, 3, 4],
                     'doors': [{'edge': 'E', 'offset': 2}],
                     'points': [{'type': 'light', 'x': 1, 'z': 2}]},
                    {'id': 'corridor', 'rect': [3, 0, 2, 12],
                     'doors': [{'edge': 'N', 'offset': 1}],
                     'points': [{'type': 'light', 'x': 1, 'z': 6}]}]},
                'f1': {'rooms': [
                    {'id': 'stair_1', 'rect': [0.9, 0, 3, 4],
                     'doors': [{'edge': 'E', 'offset': 2}],
                     'points': [{'type': 'light', 'x': 1, 'z': 2}]},
                    {'id': 'corridor', 'rect': [3, 0, 2, 12],
                     'doors': [{'edge': 'N', 'offset': 1}],
                     'points': [{'type': 'light', 'x': 1, 'z': 6}]}]}},
        }
        issues, _ = V.validate_building(broken)
        self.assertTrue([i for i in issues if 'النواة' in i], issues)


if __name__ == '__main__':
    unittest.main(verbosity=2)
