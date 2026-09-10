#!/usr/bin/env python3
from pathlib import Path


def rep(path, old, new):
    p=Path(path); src=p.read_text(encoding="utf-8")
    if src.count(old)!=1:
        raise SystemExit("marker mismatch in %s: %d" % (path,src.count(old)))
    p.write_text(src.replace(old,new,1),encoding="utf-8")

p="acs_understand.py"
rep(p,
'''- الهدف كتلة منزل/فيلا قابلة للقراءة، لا صندوقاً بحجم قطعة الأرض.

"""''',
'''- الهدف كتلة منزل/فيلا قابلة للقراءة، لا صندوقاً بحجم قطعة الأرض.
- في العمائر: اجعل كتلة الأدوار المتكررة مصطفّة منطقياً فوق الكتلة التي تحتها. لا تنشئ بلاطات أو غرفاً علوية معلّقة خارج المسقط السفلي إلا إذا طلب العميل بروزاً/كابولياً صراحةً.
- لا تجعل الواجهة صفاً عشوائياً من فتحات صغيرة: اجمع فتحات الغرف الخارجية بإيقاع واضح، واجعل باب المدخل الرئيسي مميزاً عن أبواب الغرف الداخلية.
- الشرفات/التراسات لا تُضاف لمجرد تحسين الشكل؛ إن طلبها العميل فاجعلها متصلة بفراغ داخلي ومحمولة ضمن كتلة مقروءة.

"""''')

quality_code=r'''
def _residential_plan_quality_issues(building, description):
    # Geometry-only gate: no regulatory values and no guessed code requirements.
    import acs_validate as V
    bt=str((building.get("meta") or {}).get("type") or "residential")
    if not _is_residential(bt): return []
    all_issues,_=V.validate_building(building)
    keys=("تتداخل", "خارج حدود", "معلّق", "غير متطابق رأسياً", "rect غير صالح",
          "عرض أو عمق غير موجب", "بلا غرف")
    out=[x for x in all_issues if any(k in x for k in keys)]
    text=str(description or "").lower()
    explicit=any(k in text for k in ("cantilever","overhang","كابولي","كابول","بروز معلّق","بروز علوي"))
    if explicit: return out[:16]
    floors=building.get("floors") or {}; levels=building.get("levels") or []
    ordered=sorted([lv for lv in levels if lv.get("template") in floors],
                   key=lambda lv: float(lv.get("index",0) or 0))
    def bbox(t):
        rects=[r.get("rect") for r in (floors.get(t,{}).get("rooms") or [])
               if isinstance(r.get("rect"),list) and len(r.get("rect"))==4]
        if not rects: return None
        xs=[float(r[0]) for r in rects]; zs=[float(r[1]) for r in rects]
        xe=[float(r[0])+float(r[2]) for r in rects]; ze=[float(r[1])+float(r[3]) for r in rects]
        return (min(xs),min(zs),max(xe),max(ze))
    for lo,up in zip(ordered,ordered[1:]):
        if lo.get("template")==up.get("template"): continue
        a,b=bbox(lo.get("template")),bbox(up.get("template"))
        if not a or not b: continue
        excursion=max(a[0]-b[0],a[1]-b[1],b[2]-a[2],b[3]-a[3],0.0)
        if excursion>1.20:
            out.append("الكتلة السكنية العلوية في القالب '%s' تتجاوز مسقط القالب '%s' أسفلها حتى %.2f م بلا طلب صريح لبروز/كابولي — أعد محاذاة الغرف العلوية فوق الكتلة المبنية مع الحفاظ على البرنامج." %
                       (up.get("template"),lo.get("template"),excursion))
    return out[:16]


def _repair_residential_plan(description, building, issues, model=None, request_id=None,
                             strategy=None):
    prompt=(
      "هذه خطة مناطق سكنية قبل مرحلة التفصيل. أصلح هندسة الخطة فقط وأعد Building JSON كاملاً فقط.\n"
      "لا تحذف غرفة طلبها العميل، لا تضف برنامجاً جديداً، ولا تغيّر أسماء/أعداد المتطلبات. "
      "حافظ على site وlevels وعدد الأدوار. عدّل rect وتوزيع الغرف/الممرات والنواة فقط بقدر حل المشاكل. "
      "لا تنشئ بروزاً أو كابولياً لم يطلبه العميل.\nالمشاكل:\n"
      + "\n".join("- "+x for x in issues)
      + "\n\nطلب العميل:\n"+description
      + "\n\nالخطة الحالية:\n"+json.dumps(building,ensure_ascii=False))
    raw=call_llm(prompt,model=model,max_tokens=G.stage_budget("plan"),truncate=False,
                 btype=str((building.get("meta") or {}).get("type") or "residential"),
                 user_msg="",stage="plan",request_id=request_id,strategy=strategy)
    return validate(extract_json(raw))

'''
rep(p,"def understand_deep(description, model=None, group_size=None, workers=None,",
    quality_code+"\ndef understand_deep(description, model=None, group_size=None, workers=None,")

rep(p,
'''    plan_rooms = []
    for tmpl, fdef in (building.get("floors") or {}).items():''',
'''    # Staged residential requests used to log plan defects only after all detail
    # calls had already run. Repair the compact spatial plan first; warehouses are
    # deliberately outside this policy.
    if _is_residential(btype):
        q0=_residential_plan_quality_issues(building, description)
        if q0:
            print("[ACS-RES-Q] plan quality: %d spatial issue(s) — repair before detail." % len(q0))
            try:
                fixed=_repair_residential_plan(desc, building, q0, model=model,
                                               request_id=request_id,
                                               strategy=(strategy_plan or {}).get("strategy"))
                q1=_residential_plan_quality_issues(fixed, description)
                if len(q1)<len(q0):
                    building=fixed
                    building.setdefault("meta",{}).setdefault("acs_stage_diagnostics",[]).append(
                        {"code":"RESIDENTIAL_PLAN_REPAIRED","before":len(q0),"after":len(q1)})
                    print("[ACS-RES-Q] plan repair accepted: %d -> %d." % (len(q0),len(q1)))
                else:
                    building.setdefault("meta",{}).setdefault("acs_stage_diagnostics",[]).append(
                        {"code":"RESIDENTIAL_PLAN_REPAIR_REJECTED","before":len(q0),"after":len(q1)})
                    print("[ACS-RES-Q] plan repair rejected: no measured improvement.")
            except Exception as exc:
                building.setdefault("meta",{}).setdefault("acs_stage_diagnostics",[]).append(
                    {"code":"RESIDENTIAL_PLAN_REPAIR_FAILED","error":type(exc).__name__})
                print("[ACS-RES-Q] plan repair failed — original plan retained: %s" % type(exc).__name__)

    plan_rooms = []
    for tmpl, fdef in (building.get("floors") or {}).items():''')

# Regression tests are source-level and deterministic; they make no paid provider call.
t=Path("tests/remediation/test_residential_quality.py")
s=t.read_text(encoding="utf-8")
append='''\nchk("residential rule forbids unrequested upper-floor cantilevers",\n    "لا تنشئ بلاطات أو غرفاً علوية معلّقة" in rule)\nchk("staged residential generation has a pre-detail plan quality gate",\n    hasattr(U, "_residential_plan_quality_issues") and hasattr(U, "_repair_residential_plan"))\n\n# A shifted upper floor is flagged unless the user explicitly requested a cantilever.\n_b={"meta":{"type":"apartment"},"site":{"w":30,"d":30},"levels":[\n {"index":0,"template":"g"},{"index":1,"template":"u"}],"floors":{\n "g":{"rooms":[{"id":"living","rect":[5,5,10,10],"doors":[]}]},\n "u":{"rooms":[{"id":"bed","rect":[8,5,10,10],"doors":[]}]}}}\n_q=U._residential_plan_quality_issues(_b,"عمارة سكنية دورين")\nchk("large unrequested upper-floor excursion is detected",\n    any("بلا طلب صريح" in x for x in _q))\n_q2=U._residential_plan_quality_issues(_b,"عمارة سكنية مع بروز كابولي 3 متر")\nchk("explicit cantilever intent suppresses the added massing complaint",\n    not any("بلا طلب صريح" in x for x in _q2))\n'''
if "staged residential generation has a pre-detail plan quality gate" not in s:
    t.write_text(s+append,encoding="utf-8")

print("residential quality v2 transform applied")
