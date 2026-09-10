# -*- coding: utf-8 -*-
"""tests/remediation/test_validate_topology.py — F-51.

العطل الذي تقفله هذه الحزمة
---------------------------
`acs_validate.validate_building` كان يمرّ على `b["floors"]` قالباً قالباً ولا
يقرأ `b["levels"]` إطلاقاً. فئتان كاملتان من الأعطال كانتا غير مرئيتين بالبناء:

  • الرأسية — عمود درج/مصعد لا يتطابق بين الأدوار، طابق يشير إلى قالب غير
    معرَّف، حيّز معلّق بلا ما يسنده أسفله.
  • الطوبولوجية — فراغ لا يوصل إليه، باب يفتح على لا شيء، نافذة على جدار
    داخلي، فتحتان متراكبتان على الحافّة نفسها.

مراجعة مستقلّة لمخرَج ACS لشاليه ثلاثة أدوار رصدت ٢٢ مشكلة بينما أعلن المدقّق
«٠ مشاكل»؛ أخطرها — عمود درج غير متطابق رأسياً، وفراغات بلا وصول — من هاتين
الفئتين بالضبط.

الخاصّية المقابلة، والأهمّ: **لا إنذار كاذب**. مدقّق يصرخ على نموذج سليم
يُطفَأ بعد أسبوع، فيصير أسوأ من غيابه. لذلك كل فحص هنا مزدوج: نموذج معطوب
يجب أن يُرصَد، ونموذج سليم يقابله يجب أن يمرّ صامتاً.

الحدّ لم يتغيّر: هندسة وطوبولوجيا فقط. §7 يثبت أن لا عتبة تنظيمية ولا كمّية
مطلوبة دخلت من هنا — تلك مهامّ مراجعة يكشفها acs_engineering_authority بحالة
NOT_EVALUATED.
"""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_validate as V  # noqa: E402


def clean():
    """نموذج دورين سليم: نواة متطابقة، ممرّ موصول، نوافذ على الواجهة."""
    return {
        "meta": {"type": "residential"},
        "site": {"w": 20, "d": 25},
        "levels": [{"index": 0, "template": "g"}, {"index": 1, "template": "f1"}],
        "floors": {
            "g": {"rooms": [
                {"id": "stair_1", "rect": [0, 0, 3, 4],
                 "doors": [{"edge": "E", "offset": 2}],
                 "points": [{"type": "light", "x": 1.5, "z": 2}]},
                {"id": "corridor", "rect": [3, 0, 2, 12],
                 "doors": [{"edge": "N", "offset": 1}],
                 "points": [{"type": "light", "x": 1, "z": 6}]},
                {"id": "majlis", "rect": [5, 0, 6, 5],
                 "doors": [{"edge": "W", "offset": 2}],
                 "windows": [{"edge": "N", "offset": 3}],
                 "points": [{"type": "light", "x": 3, "z": 2}]},
            ]},
            "f1": {"rooms": [
                {"id": "stair_1", "rect": [0, 0, 3, 4],
                 "doors": [{"edge": "E", "offset": 2}],
                 "points": [{"type": "light", "x": 1.5, "z": 2}]},
                {"id": "corridor", "rect": [3, 0, 2, 12],
                 "doors": [{"edge": "N", "offset": 1}],
                 "points": [{"type": "light", "x": 1, "z": 6}]},
                {"id": "bed_1", "rect": [5, 0, 5, 5],
                 "doors": [{"edge": "W", "offset": 2}],
                 "windows": [{"edge": "N", "offset": 2}],
                 "points": [{"type": "light", "x": 2, "z": 2}]},
            ]},
        },
    }


def issues_of(model):
    issues, _stats = V.validate_building(model)
    return issues


def matching(model, *needles):
    """المخالفات التي تحوي كل الكلمات المطلوبة — لا مطابقة نصّ حرفي."""
    return [s for s in issues_of(model)
            if all(n in s for n in needles)]


class NoFalsePositives(unittest.TestCase):
    """§0 — النموذج السليم يمرّ صامتاً، وإلا فكل ما بعده بلا قيمة."""

    def test_clean_two_storey_model_produces_no_issue_at_all(self):
        self.assertEqual(issues_of(clean()), [])

    def test_the_fixture_is_not_vacuous(self):
        m = clean()
        self.assertEqual(len(m["levels"]), 2)
        self.assertEqual(sum(len(f["rooms"]) for f in m["floors"].values()), 6)


class VerticalIntegrity(unittest.TestCase):
    """§1 — ما لا يستطيع قالبٌ معزول أن يراه."""

    def test_level_pointing_at_an_undefined_template_is_reported(self):
        m = clean()
        m["levels"].append({"index": 2, "template": "roof_that_does_not_exist"})
        self.assertTrue(matching(m, "غير معرَّف"))

    def test_template_no_level_references_is_reported(self):
        m = clean()
        m["floors"]["orphan"] = {"rooms": [
            {"id": "x", "rect": [0, 0, 2, 2],
             "doors": [{"edge": "N", "offset": 1}],
             "points": [{"type": "light", "x": 1, "z": 1}]}]}
        self.assertTrue(matching(m, "'orphan'", "لا يشير إليه"))

    def test_duplicate_level_index_is_reported(self):
        m = clean()
        m["levels"][1]["index"] = 0
        self.assertTrue(matching(m, "مكرّر"))

    def test_misaligned_vertical_core_is_reported_with_the_offset(self):
        """العطل الأصلي: عمود الدرج ينزاح ٩٠ سم بين الدورين."""
        m = clean()
        m["floors"]["f1"]["rooms"][0]["rect"] = [0.9, 0, 3, 4]
        found = matching(m, "النواة", "stair_1")
        self.assertTrue(found)
        self.assertIn("0.90", found[0])       # الفرق مذكور بالرقم لا بالوصف

    def test_a_core_within_tolerance_is_not_reported(self):
        """٢ سم انزياحٌ تقريبٌ في التمثيل، لا عطلٌ إنشائي."""
        m = clean()
        m["floors"]["f1"]["rooms"][0]["rect"] = [0.02, 0, 3, 4]
        self.assertEqual(matching(m, "النواة"), [])

    def test_a_room_with_nothing_beneath_it_is_reported_as_unsupported(self):
        m = clean()
        m["floors"]["f1"]["rooms"].append(
            {"id": "bed_2", "rect": [14, 18, 4, 5],
             "doors": [{"edge": "W", "offset": 2}],
             "points": [{"type": "light", "x": 2, "z": 2}]})
        self.assertTrue(matching(m, "bed_2", "معلّق"))

    def test_a_partial_lower_template_silences_the_support_check(self):
        """الحارس الذي أضافته القياسات.

        كثير من النماذج تمثّل طابقاً سفلياً جزئياً — سيناريو اختبار، أو دوراً
        لم يُفصَّل بعد. حينها يبدو كل حيّز في الأعلى معلّقاً وليس كذلك: على
        النماذج الحقيقية كان ذلك ٤٨ بلاغاً في ٢٤ نموذجاً، كلّها كاذبة. دون
        تغطية ٦٠٪ لا شيء يميّز «نموذج ناقص» عن «بروز مقصود» عن «عطل»،
        والصمت أصدق من ترجيحٍ بلا سند."""
        m = clean()
        m["floors"]["g"]["rooms"] = [m["floors"]["g"]["rooms"][0]]   # الدرج وحده
        self.assertEqual(matching(m, "معلّق"), [])

    def test_but_a_complete_lower_template_still_reports(self):
        """والحارس لا يبتلع الحالة الحقيقية: بلاطة سفلية كاملة تُبلّغ."""
        m = clean()
        m["floors"]["f1"]["rooms"].append(
            {"id": "bed_2", "rect": [14, 18, 4, 5],
             "doors": [{"edge": "W", "offset": 2}],
             "points": [{"type": "light", "x": 2, "z": 2}]})
        self.assertTrue(matching(m, "معلّق"))

    def test_an_outdoor_terrace_overhang_is_not_called_unsupported(self):
        """الشرفة تبرز عمداً — لا تُعامَل معاملة الغرفة المعلّقة."""
        m = clean()
        m["floors"]["f1"]["rooms"].append(
            {"id": "terrace", "rect": [14, 18, 4, 5]})
        self.assertEqual(matching(m, "terrace", "معلّق"), [])

    def test_a_single_level_model_triggers_no_vertical_check(self):
        m = clean()
        m["levels"] = [{"index": 0, "template": "g"}]
        del m["floors"]["f1"]
        self.assertEqual(matching(m, "النواة"), [])
        self.assertEqual(matching(m, "معلّق"), [])


class Topology(unittest.TestCase):
    """§2 — الأبواب والنوافذ والوصول."""

    def test_an_isolated_room_is_reported_as_unreachable(self):
        m = clean()
        m["floors"]["g"]["rooms"].append(
            {"id": "store", "rect": [14, 14, 4, 4],
             "doors": [{"edge": "E", "offset": 2}],
             "points": [{"type": "light", "x": 2, "z": 2}]})
        self.assertTrue(matching(m, "store", "لا يوصل إليه"))

    def test_no_door_onto_nothing_check_exists_any_more(self):
        """أُسقط بالقياس، لا بالرأي.

        كُتب فحصٌ يبلّغ عن باب على حافّة بلا حيّز مجاور وليست على حدّ الأرض.
        على ١٦٥ نموذجاً حقيقياً في هذا المستودع أطلق ٣٣ بلاغاً، **كلّها
        كاذبة**: في مستودع مولَّد حيّ تشغل الغرف ٨٦٪ من صندوقها المحيط،
        والباقي ممرّات وغلاف لا تُمثَّل غرفاً — فالباب يفتح على ممرّ حقيقي.
        الافتراض الخاطئ كان «كل فراغ ممثَّل كغرفة»، وهو لا يصحّ هنا.

        هذا الاختبار يمنع عودته. الإشارة التي ظُنّ أنه يحملها — «هذا الحيّز
        معزول» — يحملها فحص الوصول بلا ذلك الافتراض."""
        m = clean()
        m["floors"]["g"]["rooms"].append(
            {"id": "store", "rect": [14, 14, 4, 4],
             "doors": [{"edge": "E", "offset": 2}],
             "points": [{"type": "light", "x": 2, "z": 2}]})
        self.assertEqual(matching(m, "لا يفتح على شيء"), [])

    def test_a_window_on_an_internal_wall_is_reported_with_its_neighbour(self):
        m = clean()
        # majlis في [5,0,6,5] و corridor في [3,0,2,12]: الجدار المشترك هو W.
        m["floors"]["g"]["rooms"][2]["windows"] = [{"edge": "W", "offset": 2}]
        found = matching(m, "majlis", "جدار داخلي")
        self.assertTrue(found)
        self.assertIn("corridor", found[0])

    def test_a_window_is_judged_by_its_own_edge_not_the_opposite_one(self):
        """الاصطلاح من acs_bim.py سطر ٣٣٠: N على z و S على z+d.

        نسخةٌ أولى قبلت الجانبين احتياطاً، فأبلغت عن نافذة على واجهة خارجية
        لمجرّد أن غرفةً تلامس الجدار **المقابل**. على النماذج الحقيقية كان
        ذلك ٢١ إنذاراً كاذباً من أصل ٢٢. الجار هنا على W وحده، والنافذة على
        E تطلّ على الخارج."""
        m = clean()
        m["floors"]["g"]["rooms"][2]["windows"] = [{"edge": "E", "offset": 2}]
        self.assertEqual(matching(m, "majlis", "جدار داخلي"), [])

    def test_two_overlapping_openings_on_one_edge_are_reported(self):
        m = clean()
        m["floors"]["g"]["rooms"][2]["windows"] = [
            {"edge": "N", "offset": 3.0, "width": 1.2},
            {"edge": "N", "offset": 3.4, "width": 1.2}]
        self.assertTrue(matching(m, "متراكبتان"))

    def test_openings_that_merely_sit_side_by_side_are_not_reported(self):
        m = clean()
        m["floors"]["g"]["rooms"][2]["windows"] = [
            {"edge": "N", "offset": 1.0, "width": 1.2},
            {"edge": "N", "offset": 3.0, "width": 1.2}]
        self.assertEqual(matching(m, "متراكبتان"), [])


class MalformedInput(unittest.TestCase):
    """§3 — مدخل مشوّه يُبلَّغ عنه ولا يُسقط الفحص."""

    def test_a_non_finite_coordinate_is_reported_not_raised(self):
        m = clean()
        m["floors"]["g"]["rooms"][1]["rect"] = [3, float("nan"), 2, 12]
        self.assertTrue(matching(m, "غير عددية"))

    def test_a_non_positive_extent_is_reported(self):
        m = clean()
        m["floors"]["g"]["rooms"][1]["rect"] = [3, 0, 0, 12]
        self.assertTrue(matching(m, "غير موجب"))

    def test_a_duplicate_room_id_inside_one_template_is_reported(self):
        m = clean()
        dup = copy.deepcopy(m["floors"]["g"]["rooms"][2])
        dup["rect"] = [11, 6, 4, 4]
        m["floors"]["g"]["rooms"].append(dup)
        self.assertTrue(matching(m, "مكرّر داخل القالب"))

    def test_every_malformed_variant_still_returns_a_list_and_stats(self):
        for mutate in (
                lambda m: m["floors"]["g"].__setitem__("rooms", []),
                lambda m: m.__setitem__("levels", []),
                lambda m: m.__setitem__("floors", {}),
                lambda m: m["levels"][0].__setitem__("template", None),
                lambda m: m["levels"][0].__setitem__("index", None)):
            m = clean()
            mutate(m)
            issues, stats = V.validate_building(m)
            self.assertIsInstance(issues, list)
            self.assertIsInstance(stats, dict)


class BoundedOutput(unittest.TestCase):
    """§4 — التقرير للنموذج ليصلح، لا لِيُغرَق."""

    def test_no_single_check_floods_the_report(self):
        m = clean()
        for i in range(60):
            m["floors"]["g"]["rooms"].append(
                {"id": "iso_%d" % i, "rect": [14, 0.5 + i * 0.4, 2, 0.3],
                 "doors": [{"edge": "E", "offset": 1}],
                 "points": [{"type": "light", "x": 1, "z": 0.15}]})
        unreachable = matching(m, "لا يوصل إليه")
        self.assertLessEqual(len(unreachable), V.PER_CHECK_CAP)
        self.assertGreaterEqual(len(unreachable), 1)

    def test_format_issues_truncates_and_says_so(self):
        txt = V.format_issues(["مخالفة %d" % i for i in range(100)], limit=10)
        self.assertIn("و 90 مخالفة أخرى", txt)
        self.assertEqual(txt.count("\n- "), 10)


class DeterminismAndBoundary(unittest.TestCase):
    """§5…§7 — الثبات، والحدّ الذي لا يُتجاوَز."""

    def test_the_same_model_yields_the_same_issues_every_time(self):
        m = clean()
        m["floors"]["f1"]["rooms"][0]["rect"] = [0.9, 0, 3, 4]
        first = issues_of(copy.deepcopy(m))
        for _ in range(4):
            self.assertEqual(issues_of(copy.deepcopy(m)), first)

    def test_validation_never_mutates_the_model_it_is_given(self):
        m = clean()
        m["floors"]["f1"]["rooms"][0]["rect"] = [0.9, 0, 3, 4]
        before = copy.deepcopy(m)
        V.validate_building(m)
        self.assertEqual(m, before)

    def test_no_regulatory_threshold_enters_any_issue_text(self):
        """§7 — الحدّ. مخالفةٌ تقول «الكود يتطلّب» تكون قد اخترعت مصدراً."""
        m = clean()
        m["floors"]["f1"]["rooms"][0]["rect"] = [0.9, 0, 3, 4]
        m["floors"]["g"]["rooms"].append(
            {"id": "store", "rect": [14, 14, 4, 4],
             "doors": [{"edge": "E", "offset": 2}],
             "points": [{"type": "light", "x": 2, "z": 2}]})
        forbidden = ("الكود", "SBC", "IBC", "NFPA", "يتطلّب الكود", "مطابق",
                     "معتمد", "compliant", "code requires")
        text = " ".join(issues_of(m))
        self.assertTrue(text, "الحالة عبثية إن لم تُنتج مخالفات")
        for word in forbidden:
            self.assertNotIn(word, text)

    def test_strict_mode_keeps_geometry_and_topology_checks(self):
        """`strict` يوقف مطالبة المحتوى، لا فحص الهندسة."""
        m = clean()
        m["meta"]["strict"] = True
        m["floors"]["f1"]["rooms"][0]["rect"] = [0.9, 0, 3, 4]
        self.assertTrue(matching(m, "النواة"))
        # وفي الوقت نفسه لا مطالبة بمحتوى
        self.assertEqual(matching(m, "بلا إنارة"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
