# -*- coding: utf-8 -*-
"""Regression: residential plot != footprint, and actual spatial findings reach repair."""
import copy
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import acs_understand as U  # noqa: E402
import acs_validate as V  # noqa: E402

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

# Exercise the REAL validator; a mocked Arabic message would miss contract drift.
_overlap={"meta":{"type":"residential","strict":True},
          "site":{"w":30,"d":30},"levels":[{"index":0,"template":"g"}],
          "floors":{"g":{"rooms":[
              {"id":"living","rect":[2,2,6,6]},
              {"id":"kitchen","rect":[5,3,5,4]}]}}}
_before=copy.deepcopy(_overlap)
_issues,_=V.validate_building(_overlap)
_overlap_issues=[issue for issue in _issues if "تداخل بين" in issue]
chk("actual geometry validator detects the overlapping room fixture",bool(_overlap_issues))
for bt in ("residential","villa","apartment"):
    _case=copy.deepcopy(_overlap)
    _case["meta"]["type"]=bt
    _review=U._residential_plan_quality_issues(_case,"تصميم سكني")
    chk(f"{bt}: actual overlap findings reach the residential repair gate",
        all(issue in _review for issue in _overlap_issues))
chk("quality review does not mutate the input model",_overlap==_before)

_touching=copy.deepcopy(_overlap)
_touching["floors"]["g"]["rooms"][1]["rect"]=[8,2,5,4]
chk("touching room edges do not become false overlap findings",
    not any("تداخل بين" in issue for issue in U._residential_plan_quality_issues(_touching,"سكني")))

_warehouse=copy.deepcopy(_overlap)
_warehouse["meta"]["type"]="warehouse"
chk("warehouse remains outside the residential repair policy",
    U._residential_plan_quality_issues(_warehouse,"مستودع")==[])

_shell=copy.deepcopy(_touching)
_shell["floors"]["g"]["rooms"].append({"id":"building_shell","rect":[0,0,20,20]})
chk("intentional envelope containment is not flagged as a room overlap",
    not any("تداخل بين" in issue for issue in U._residential_plan_quality_issues(_shell,"سكني")))

_stacked=copy.deepcopy(_touching)
_stacked["floors"]["u"]=copy.deepcopy(_stacked["floors"]["g"])
_stacked["levels"].append({"index":1,"template":"u"})
chk("rooms on separate floor templates are not compared as same-floor overlaps",
    not any("تداخل بين" in issue for issue in U._residential_plan_quality_issues(_stacked,"سكني")))

# The terminal summary must include every assertion above, not only the original subset.
print(f"RESIDENTIAL QUALITY CONTRACT: {passed} passed, 0 failed")
