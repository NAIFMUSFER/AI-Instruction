# -*- coding: utf-8 -*-
"""tests/remediation/test_autofix_propose_boundary.py — F-52.

العطل الذي تقفله هذه الحزمة
---------------------------
`acs_layout.autofix` وضعه الافتراضي AUTHORITY_PROPOSE، ووثيقته كانت تقول:

    «لا يُكتَب حرف في النموذج الهندسي. يُحسَب ما كان سيتغيّر على نسخة.»

القياس على ١٦٥ نموذج مبنى حقيقياً في هذا المستودع: **يكتب في ١٠٨ منها**.

المصدر ليس خطأً في التنفيذ. `acs_engineering_authority.plan` يستدعيه، وعقده
يعلن صراحةً أنه يطبّق SAFE_NORMALIZATION **على الكائن الممرَّر** — لأن البصمة
المرجعية يجب أن تكون بصمة النموذج القانوني نفسه، وإلا صار معنى `unchanged`
ملتبساً (وW1-B في plan_with_model يشرح ما ترتّب على ذلك حين انتقل الحساب إلى
عامل منفصل). وثيقة plan كانت دقيقة؛ وثيقة autofix لم تكن.

وهذا أخطر موضع للتناقض: من يقرأ وثيقة المدخل الافتراضي يظنّ نموذجه سليماً،
وهو ليس كذلك في ثلثَي الحالات. وهو النمط الرابع من نوعه في هذا المستودع بعد
KI-13 (نصّ يقول «قائم» بعد الإغلاق) وKI-14 (OPEN وCLOSED في ملفّ واحد)
وKI-12: **الكود يُصحَّح بالاختبارات، والسرد لا يُصحّحه شيء.**

ما تفعله هذه الحزمة
-------------------
لا تمنع الكتابة — هي مقصودة ومُعلَنة في العقد الصحيح. بل **تحدّها**: تُشغّل
وضع الاقتراح على كل نموذج في المستودع وتفشل إن مسّ حقلاً خارج القائمة
المقيسة. الوعد النثري صار قيداً؛ ولو جعل تعديلٌ لاحق وضعَ الاقتراح ينقل
جداراً أو يضيف فتحة، يسقط البناء بدل أن يُكتشَف الأمر في مشروع عميل.
"""
import collections
import copy
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_layout as L  # noqa: E402

# الحقول التي يُسمح لوضع الاقتراح بمسّها — مقيسةٌ على المجموعة، لا مُتمنّاة.
# مفاتيح نظام ناقصة تُملأ بقيمة افتراضية موثّقة المصدر، وسجلّ ذلك المصدر.
ALLOWED_EXACT = {'wall_t', 'wall_h', 'floor_height', 'meta', 'meta.acs_provenance'}
# ورقم هندسي واحد: إحداثيات المستطيل، تدويراً لا نقلاً. الحدّ أدناه يفرض ذلك.
ROUNDING_TOLERANCE = 0.005
MIN_MODELS_SCANNED = 120


def _walk(obj, depth=0, path=''):
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


def _changed_paths(a, b, path=''):
    """مسارات الاختلاف، بفهرس القوائم مطوياً إلى [] ليصير التجميع ممكناً."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) | set(b):
            sub = ('%s.%s' % (path, k)) if path else str(k)
            if k not in a:
                out.append(sub)
            elif k not in b:
                out.append(sub + '(-)')
            else:
                out += _changed_paths(a[k], b[k], sub)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(path + '(len)')
        for x, y in zip(a, b):
            out += _changed_paths(x, y, path + '[]')
    elif a != b:
        out.append(path)
    return out


def corpus():
    out = []
    for dirpath, _dirs, files in os.walk(os.path.join(ROOT, 'tests')):
        for fn in sorted(files):
            if not fn.endswith('.json'):
                continue
            full = os.path.join(dirpath, fn)
            try:
                with open(full, encoding='utf-8') as fh:
                    data = json.load(fh)
            except Exception:
                continue
            for path, model in _walk(data):
                out.append((os.path.relpath(full, ROOT), path, model))
    return out


MODELS = corpus()
TOUCHED = collections.Counter()
VIOLATIONS = []          # حقل خارج القائمة
RECT_MOVES = []          # rect تغيّر بأكثر من تدوير
WROTE = 0

for _f, _p, _m in MODELS:
    _before = copy.deepcopy(_m)
    try:
        L.autofix(_m)                       # الوضع الافتراضي: الاقتراح
    except Exception:                       # noqa: BLE001 — الانهيار شأن حزمة أخرى
        continue
    _paths = _changed_paths(_before, _m)
    if _paths:
        WROTE += 1
    for _c in _paths:
        _leaf = _c.replace('[]', '')
        TOUCHED[_c] += 1
        if _c.endswith('rect[]') or _leaf.endswith('rect'):
            continue                        # يُفحَص بدقّة أدناه
        if not any(_leaf == a or _leaf.endswith('.' + a) for a in ALLOWED_EXACT):
            VIOLATIONS.append((_f, _p, _c))
    for _t, _fl in (_m.get('floors') or {}).items():
        _rooms = _fl.get('rooms') or []
        _old = ((_before.get('floors') or {}).get(_t) or {}).get('rooms') or []
        for _i, _r in enumerate(_rooms):
            if _i >= len(_old):
                continue
            _rb, _ra = _old[_i].get('rect'), _r.get('rect')
            if not _rb or not _ra or _rb == _ra:
                continue
            for _v0, _v1 in zip(_rb, _ra):
                try:
                    if abs(float(_v1) - float(_v0)) > ROUNDING_TOLERANCE:
                        RECT_MOVES.append((_f, _p, _r.get('id'), _rb, _ra))
                        break
                except (TypeError, ValueError):
                    RECT_MOVES.append((_f, _p, _r.get('id'), _rb, _ra))
                    break


class TheCorpusIsReal(unittest.TestCase):

    def test_enough_models_were_scanned(self):
        self.assertGreaterEqual(len(MODELS), MIN_MODELS_SCANNED)

    def test_propose_mode_really_does_write(self):
        """الحزمة كلّها بلا معنى إن لم تعد الكتابة تحدث.

        إن صار هذا صفراً فقد تغيّر عقد plan فعلاً — وهو خبر سارّ يستحق
        تحديث الوثيقة، لا اختباراً يمرّ صامتاً على قياس بطل."""
        self.assertGreater(WROTE, 0)


class TheBoundaryHolds(unittest.TestCase):

    def test_propose_mode_touches_nothing_outside_the_measured_set(self):
        self.assertEqual(
            VIOLATIONS[:12], [],
            'وضع الاقتراح كتب في حقل خارج الحدّ المُعلَن (%d حالة):\n%s'
            % (len(VIOLATIONS),
               '\n'.join('%s :: %s → %s' % v for v in VIOLATIONS[:12])))

    def test_rect_is_only_ever_rounded_never_moved(self):
        """أهمّ توكيد هنا. تدوير 24.90548… إلى 24.91 تطبيع ميكانيكي؛ تحريك
        الجدار نصف متر شيء آخر تماماً — ووضعُ الاقتراح لا يُفترَض به أن يفعله
        بحال."""
        self.assertEqual(
            RECT_MOVES[:6], [],
            'وضع الاقتراح حرّك هندسة، لا دوّرها (%d حالة):\n%s'
            % (len(RECT_MOVES),
               '\n'.join('%s :: %s / %s: %s → %s' % r for r in RECT_MOVES[:6])))

    def test_no_room_or_opening_is_added_or_removed(self):
        added = [c for c in TOUCHED if c.endswith('(len)') or c.endswith('(-)')]
        self.assertEqual(added, [],
                         'وضع الاقتراح غيّر عدد عناصر قائمة: %s' % added)


class TheDocstringMatchesTheMeasurement(unittest.TestCase):
    """النمط الذي تكرّر أربع مرّات في هذا المستودع: الكود يُصحَّح بالاختبارات
    والسرد لا يُصحّحه شيء. هذا الصنف يربط الاثنين."""

    def test_the_docstring_no_longer_claims_nothing_is_written(self):
        """الجملة القديمة تبقى في الوثيقة عمداً — محفوظةً للسجلّ داخل ملاحظة
        التصحيح. ما يُمنَع هو ورودها **دعوى قائمة**. فيُشترط أن كل ظهور لها
        مسبوقٌ بعلامة التصحيح، لا أن تختفي."""
        doc = L.autofix.__doc__ or ''
        claim = 'لا يُكتَب حرف في النموذج الهندسي'
        marker = 'كان هذا النصّ يقول'
        idx, seen = doc.find(claim), 0
        while idx >= 0:
            seen += 1
            head = doc[max(0, idx - 60):idx]
            self.assertIn(marker, head,
                          'الجملة القديمة ترد دعوى قائمة، لا اقتباساً مصحَّحاً')
            idx = doc.find(claim, idx + 1)
        self.assertEqual(seen, 1, 'الاقتباس المصحَّح يرد مرّة واحدة لا %d' % seen)

    def test_the_docstring_names_the_declared_exception(self):
        doc = L.autofix.__doc__ or ''
        self.assertIn('SAFE_NORMALIZATION', doc)

    def test_the_docstring_lists_every_field_the_measurement_found(self):
        doc = L.autofix.__doc__ or ''
        for field in ('wall_t', 'wall_h', 'floor_height', 'acs_provenance', 'rect'):
            self.assertIn(field, doc, 'الوثيقة لا تذكر %s' % field)


if __name__ == '__main__':
    unittest.main(verbosity=2)
