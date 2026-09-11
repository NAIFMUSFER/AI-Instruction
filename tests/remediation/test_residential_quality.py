# -*- coding: utf-8 -*-
"""Regression: residential plot != footprint, while industrial prompts stay isolated."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import acs_understand as U  # noqa: E402

passed = 0

def chk(name, condition):
    global passed
    if not condition:
        raise AssertionError(name)
    passed += 1
    print("PASS", name)

rule = U.RESIDENTIAL_MASSING_RULE
chk("rule explicitly distinguishes plot boundary from building footprint",
    "قطعة الأرض" in rule and "ليس أمراً بأن يغطي المبنى كامل القطعة" in rule)
chk("rule preserves requested outdoor programme",
    all(x in rule for x in ("حوش", "مسبح", "حديقة", "مواقف")))
chk("rule refuses invented regulatory geometry",
    "لا تخترع نسبة بناء" in rule and "ارتداداً نظامياً" in rule)
chk("old fill-the-entire-floor instruction is gone",
    "تملأ مسطح الدور" not in U.KNOWLEDGE)
chk("base residential knowledge now names site as the plot boundary",
    "site هي حدود **قطعة الأرض**" in U.KNOWLEDGE)

for bt in ("residential", "villa", "apartment"):
    prompt = U.system_prompt(bt)
    chk(f"{bt} receives residential massing rule", rule in prompt)

for bt in ("warehouse", "factory", "industrial", "logistics"):
    prompt = U.system_prompt(bt)
    chk(f"{bt} does not receive residential massing rule", rule not in prompt)

for bt in ("office", "hotel", "hospital", "school", "retail"):
    prompt = U.system_prompt(bt)
    chk(f"{bt} generic non-residential prompt is not reclassified as housing",
        rule not in prompt)

chk("program classifier recognizes every residential program used by the rule",
    all(U._is_residential(x) for x in ("residential", "villa", "apartment")))
chk("program classifier excludes warehouse",
    not U._is_residential("warehouse"))

print(f"RESIDENTIAL QUALITY CONTRACT: {passed} passed, 0 failed")

chk("residential rule forbids unrequested upper-floor cantilevers",
    "لا تنشئ بلاطات أو غرفاً علوية معلّقة" in rule)
chk("staged residential generation has a pre-detail plan quality gate",
    hasattr(U, "_residential_plan_quality_issues") and hasattr(U, "_repair_residential_plan"))

# A shifted upper floor is flagged unless the user explicitly requested a cantilever.
_b={"meta":{"type":"apartment"},"site":{"w":30,"d":30},"levels":[
 {"index":0,"template":"g"},{"index":1,"template":"u"}],"floors":{
 "g":{"rooms":[{"id":"living","rect":[5,5,10,10],"doors":[]}]},
 "u":{"rooms":[{"id":"bed","rect":[8,5,10,10],"doors":[]}]}}}
_q=U._residential_plan_quality_issues(_b,"عمارة سكنية دورين")
chk("large unrequested upper-floor excursion is detected",
    any("بلا طلب صريح" in x for x in _q))
_q2=U._residential_plan_quality_issues(_b,"عمارة سكنية مع بروز كابولي 3 متر")
chk("explicit cantilever intent suppresses the added massing complaint",
    not any("بلا طلب صريح" in x for x in _q2))
