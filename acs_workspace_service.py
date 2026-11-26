"""Connect the authenticated UI to the existing canonical revision aggregate.

Only the trusted parent admits provider geometry. Browser commands contain user
requirements or narrow element changes, never a replacement model or approval
receipt. Derived artifacts always cross the existing frozen-baseline gate.
"""
from __future__ import annotations

import base64
import json
import math
from pathlib import Path
import tempfile

from acs_plan_review import EPS, PlanError, canonical, digest, _geometry
from acs_plan_store_reload import load_workspace
from acs_plan_commands import _command, _view_result
from acs_plan_bridge import carry_roof_for_admission, existing_geometry_verifier

SCHEMA = "acs.connected-workspace/1.0"
OPTIONS = {
    "A": "اقتراح يركز على استثمار المساحة ضمن المتطلبات المؤكدة.",
    "B": "اقتراح يركز على وضوح الحركة وقرب الأنشطة المرتبطة، بلا ادعاء قياس الإنتاجية.",
    "C": "اقتراح يركز على فصل الاستخدامات ومرونة التوسع ضمن القيود المؤكدة.",
}

# Persist only trusted validator categories, never provider text or geometry.
GEOMETRY_MESSAGES = {
    "AREA_EXCEEDS_SITE": "مجموع مساحات الفراغات التي ولّدها النظام أكبر من مساحة الموقع. لا يكفي تغيير مواقعها؛ يلزم مراجعة أحجام الفراغات والتوزيع.",
    "SITE_NOT_SPECIFIED": "أبعاد الموقع في المخطط الناتج غير محددة أو غير صالحة.",
    "DIMENSION_NOT_SPECIFIED": "بعض ارتفاعات المبنى أو سماكات الجدران في المخطط الناتج غير محددة أو غير صالحة.",
    "LEVELS_NOT_SPECIFIED": "المخطط الناتج لا يحدد الأدوار.",
    "INVALID_LEVEL": "تعريف الأدوار أو ربطها بالمخططات غير صالح.",
    "UNREFERENCED_TEMPLATE": "يوجد مخطط دور غير مرتبط بأدوار المبنى.",
    "EMPTY_TEMPLATE": "أحد مخططات الأدوار لا يحتوي فراغات.",
    "INVALID_RECT": "أبعاد أحد الفراغات في المخطط الناتج غير صالحة.",
    "OUTSIDE_SITE": "يوجد فراغ خارج حدود الأرض في المخطط الناتج.",
    "UNRESOLVED_SPACE": "لم يكتمل تخطيط بعض الفراغات؛ لم تُعتمد الأبعاد البديلة.",
    "UNSUPPORTED_NON_RECTANGULAR_SPACE": "يحتوي المخطط فراغًا غير مستطيل لا يدعمه مسار العرض الحالي.",
    "ROOM_OVERLAP": "توجد غرف أو فراغات متداخلة في المخطط الناتج.",
    "NON_FINITE_MEASUREMENT": "تعذّر حساب قياسات صالحة للمخطط الناتج.",
    "EMPTY_MODEL": "المخطط الناتج لا يحتوي مخططات أدوار.",
}


# A paid proposal that finishes after a newer revision was saved (for example a
# manual edit from another tab) is neither discarded nor allowed to replace that
# revision. The receipt keeps it as a separate generated version; the owner then
# chooses explicitly. No choice makes another provider request.
CONFLICT_CODE = "GENERATION_CONFLICT"
GENERATED_VERSION = "generated_version"


class GeneratedVersionConflict(PlanError):
    def __init__(self, building, current_head):
        PlanError.__init__(self, CONFLICT_CODE, geometry_failure_message(CONFLICT_CODE))
        self.building, self.current_head = building, current_head

    def checkpoint(self):
        return {"kind": GENERATED_VERSION, "building": self.building, "current_head": self.current_head}


def generated_version(row):
    """The kept proposal of a conflict receipt, or None."""
    kept = row.get("checkpoint") if isinstance(row, dict) else None
    if (row.get("state") != "FAILED" or row.get("error_code") != CONFLICT_CODE or not isinstance(kept, dict)
            or kept.get("kind") != GENERATED_VERSION or not isinstance(kept.get("building"), dict)):
        return None
    return kept


def adoption_marker(job_id):
    return "task:" + job_id


def geometry_failure_message(code):
    messages = {
        "ACS_TIMEOUT":"انتهت مهلة المعالجة وحالة الطلب لدى المزود غير مؤكدة. احتُفظ بالمراحل؛ لن يبدأ استدعاء مكرر تلقائيًا.",
        "ACS_UPSTREAM_TIMEOUT":"تأخر رد خدمة التوليد وحالة الطلب لدى المزود غير مؤكدة. لم يُعَد إرسال الطلب تلقائيًا.",
        "ACS_UPSTREAM_CONNECTION":"انقطع اتصال خدمة التوليد وحالة الطلب غير مؤكدة. احتُفظ بالمراحل دون إعادة مدفوعة تلقائية.",
        "GENERATION_WORKER_FAILED":"تعذّر إكمال الطلب بسبب خطأ داخلي في الخادم. يمكنك إرساله مرة أخرى.",
        "PROVIDER_OUTCOME_UNKNOWN":"توقفت متابعة المهمة أو أُلغيت. لا يمكن الجزم بأن المزود لم ينفذها؛ لم تُعَد تلقائيًا، ولا تسمح هذه الحالة باستئناف مكرر.",
        "GENERATION_BUSY":"كل مسارات التوليد مشغولة حاليًا. حاول بعد قليل.",
        "ROOF_PREFERENCE_CONFLICT":"أعاد المقترح سطحًا رغم اختيارك إزالة السطح. لم تُحفظ المحاولة وبقيت نسختك السابقة كما هي. يمكنك إعادة تفعيل السطح صراحة من أدوات المخطط إذا أردت إضافته.",
        "STAIR_RESOURCE_LIMIT":"تجاوز تفصيل الدرج الحد المدعوم لهذا الطلب. قلّل عدد الأدوار أو نوى الدرج ثم ابدأ طلبًا جديدًا؛ لم تُحفظ المحاولة ولم يُكرّر استدعاء المزود.",
        "CONTEXT_DETAILS_RESOURCE_LIMIT":"تجاوزت التفاصيل الافتراضية الحد المدعوم لهذا الطلب. قلّل عدد المساحات أو العناصر ثم ابدأ طلبًا جديدًا؛ لم تُحفظ المحاولة ولم يُكرّر استدعاء المزود.",
        "CONTEXT_DETAILS_PROVENANCE_INVALID":"تعذّر التحقق من مصدر التفاصيل الافتراضية؛ لم تُحفظ المحاولة. راجع بيانات المصدر قبل بدء طلب جديد.",
        "RESIDENTIAL_SHELL_ONLY":"المقترح لم يفصل الشقق إلى غرف داخلية. أعد المحاولة مع برنامج الغرف المختار.",
        "RESIDENTIAL_CORE_MISSING":"لم يكتمل اتصال الدرج بين الأدوار في المقترح.",
        "PLAN_DETAIL_INCOMPLETE":"لم يكتمل تفصيل الفتحات. استأنف من آخر مجموعة محفوظة.",
        "PLAN_LAYOUT_INCOMPLETE":"لم يكتمل توزيع الغرف بعد محاولة التصحيح. راجع البرنامج والمساحة، أو استأنف ضمن حد الاستدعاءات المتبقي.",
        "PLAN_SOURCE_READ_MALFORMED":"لم يُعد الذكاء الاصطناعي قراءة صالحة للمخطط حتى بعد إعادة واحدة. لم تُحفظ نسخة، والملف محفوظ؛ أعد القراءة لاحقًا.",
        "PLAN_SOURCE_GEOMETRY_INCOMPLETE":"تعذّر استخراج حدود الغرف دون تداخل بعد مراجعة الصورة. راجع وضوح الصفحة والأبعاد المرجعية ثم أعد القراءة؛ الملف الأصلي محفوظ ولم يُعد ترتيب غرفه تلقائيًا.",
        CONFLICT_CODE:"حُفظ تعديل أحدث أثناء التوليد، فاحتفظنا بالنسخة المولّدة منفصلة دون أن تستبدل تعديلك. اختر ما تريد اعتماده؛ الخيار الآخر يبقى محفوظًا، ولن يُحسب توليد جديد.",
        "STALE_REVISION":"تغيّرت النسخة الحالية أثناء العملية، فلم تُحفظ نتيجتها فوق النسخة الأحدث. افتح آخر نسخة؛ لن يُعاد الطلب تلقائيًا.",
        "OPENING_IDENTITY_INVALID":"بعض أبواب أو نوافذ هذه النسخة بلا معرّف صالح، فلم يبدأ التعديل ولم يُرسل أي طلب إلى مزود النموذج. نسختك بقيت كما هي.",
    }
    if code in messages:
        return messages[code]
    if code in {"ACS_NOT_CONFIGURED","ACS_UPSTREAM_RATE_LIMIT","ACS_UPSTREAM_UNAVAILABLE","ACS_UPSTREAM_AUTH"}:
        return "خدمة التوليد غير متاحة حاليًا. احتُفظ بالمراحل التي اكتملت؛ حاول لاحقًا."
    if code == "ACS_PROVIDER_BUDGET_EXHAUSTED":
        return "بلغ المقترح حد الاستدعاءات الذي وافقت عليه قبل اكتمال المخطط. راجع نطاق الطلب وحد الاستدعاءات قبل بدء محاولة جديدة."
    if code == "INVALID_GEOMETRY":
        return "لم يجتز المخطط فحص الهندسة. تفاصيل هذه المحاولة القديمة غير محفوظة."
    if isinstance(code, str) and code.startswith("PLAN_GEOMETRY_"):
        return GEOMETRY_MESSAGES.get(code[len("PLAN_GEOMETRY_"):])
    from acs_floor_program import FLOOR_NOT_FITTED, floor_name
    if isinstance(code, str) and code.startswith(FLOOR_NOT_FITTED) and code[len(FLOOR_NOT_FITTED):].isdigit():
        return ("لم يكتمل مقترح الذكاء الاصطناعي، وتعذّر على التوزيع البديل الحتمي ترتيب غرف "
                + floor_name(int(code[len(FLOOR_NOT_FITTED):]))
                + " ببرنامجه ومقاساته داخل كتلة المبنى. لم تُحفظ نسخة بأدوار متطابقة. راجع برنامج هذا الدور ومقاساته "
                "أو ارفع حد الاستدعاءات ثم أعد المحاولة.")
    return None


def checked_command(command, allowed):
    _command(command)
    if set(command) - (set(allowed) | {"action"}):
        raise PlanError("INVALID_PLAN_COMMAND", "الطلب يحتوي حقولاً غير مدعومة.")
    return json.loads(canonical(command))


def workspace(store, project_id, actor_id):
    return load_workspace(store, project_id, actor_id=actor_id, verifier=existing_geometry_verifier)


def view(store, project_id, actor_id, revision_id=None):
    ws = workspace(store, project_id, actor_id)
    rid = revision_id or ws.head
    if rid is None:
        return {"schema": SCHEMA, "ok": True, "head": None, "baseline": None, "history": [], "revision_id": None}
    result = _view_result(ws, "state", rid)
    revision = ws.get(rid)
    meta = revision.model.get('meta')
    assumptions = meta.get('assumptions', []) if isinstance(meta,dict) else []
    assumptions = [v[:1000] for v in assumptions if isinstance(v,str)][:64] if isinstance(assumptions,list) else []
    openings = []
    for level in revision.model["levels"]:
        for room in revision.model["floors"][level["template"]]["rooms"]:
            for kind in ("doors", "windows"):
                for opening in room.get(kind, []) or []:
                    edge, offset = opening.get("edge"), opening.get("offset")
                    width = opening.get("width", opening.get("w"))
                    if edge not in {"N", "S", "E", "W"} or any(type(v) not in (int,float) or not math.isfinite(v) for v in (offset,width)) or width <= 0:
                        continue
                    x,z,w,d = room["rect"]
                    if edge in {"N", "S"}:
                        line = [x+offset-width/2,z+(d if edge=="S" else 0),x+offset+width/2,z+(d if edge=="S" else 0)]
                    else:
                        line = [x+(w if edge=="E" else 0),z+offset-width/2,x+(w if edge=="E" else 0),z+offset+width/2]
                    openings.append({"level_index":level["index"],"template":level["template"],"room_id":room["id"],"kind":kind,"line":line})
    report = ws.review(rid)
    findings = [{"code": issue.get("code"),
                 "message": str(issue.get("message") or "")[:1000],
                 "requirement_id": issue.get("requirement_id"),
                 "room_ref": issue.get("room_ref") or issue.get("room")}
                for issue in report.get("issues", [])[:512]]
    # Advisory plot findings are shown with the others but never block approval.
    findings += [{"code": item.get("code"), "severity": "advisory",
                  "message": ("ملاحظة استشارية لا تمنع الاعتماد: " + str(item.get("message") or ""))[:1000],
                  "requirement_id": None, "room_ref": item.get("room_ref")}
                 for item in (report.get("advisories") or [])[:128]]
    result.update({"schema": SCHEMA, "ok": True, "brief": revision.brief,
                   "openings":openings,
                   "planning_assumptions":assumptions,
                   "requirements": json.loads(revision.requirements_json),
                   "review_findings": findings})
    plot = meta.get("acs_plot_rules") if isinstance(meta, dict) else None
    if plot is not None:
        from acs_plot_rules import summary
        result["plot_rules"] = summary(revision.model, plot)
    if isinstance(meta, dict) and isinstance(meta.get("acs_plan_source"), dict):
        from acs_plan_sources import review_view
        result["plan_source"] = review_view(meta)  # original beside the draft, suggested changes
    # Step-01 inputs travel with the revision, so another device restores them.
    import acs_brief_reader as BRIEF
    result["plot_input"] = BRIEF.plot_input(plot)
    result["brief_program"] = BRIEF.usable(meta.get(BRIEF.META_KEY)) if isinstance(meta, dict) and BRIEF.META_KEY in meta else None
    return result


def generation_command(command):
    out = checked_command(command, {"job_id", "brief", "requirements", "expected_head", "option", "confirmed", "max_provider_calls", "source_id", "source_mode", "source_read", "resume_job_id", "plot", "program"})
    if "source_id" in out:
        from acs_plan_sources import identity
        identity(out["source_id"])
        if out.get("source_mode") not in {"preserve", "revise", "complete"}:
            raise PlanError("INVALID_PLAN_SOURCE", "اختر قراءة المخطط كما هو أو طلب تعديله أو إكمال أبوابه.")
        from acs_plan_sources import read_options
        read_options(out)  # floors, confirmed floor count and budget, before any paid call
    elif "source_mode" in out or "source_read" in out:
        raise PlanError("INVALID_PLAN_SOURCE", "اختر ملف مخطط محفوظًا أولًا.")
    if out.get("confirmed") is not True:
        raise PlanError("EXPLICIT_CONFIRMATION_REQUIRED", "راجع المتطلبات وأكدها قبل التوليد.")
    brief, requirements = out.get("brief"), out.get("requirements")
    if not isinstance(brief, str) or not 1 <= len(brief.strip()) <= 60000:
        raise PlanError("DESCRIPTION_REQUIRED", "اكتب وصف المشروع ضمن الحد المسموح.")
    if not isinstance(requirements, list) or not requirements or len(requirements) > 100:
        raise PlanError("INVALID_PROGRAM", "أضف متطلبات مؤكدة للمشروع.")
    if out.get("option") not in OPTIONS:
        raise PlanError("INVALID_OPTION", "اختر البديل A أو B أو C.")
    if type(out.get("max_provider_calls")) is not int or not 1 <= out["max_provider_calls"] <= 12:
        raise PlanError("INVALID_BUDGET", "اختر سقف استدعاءات من 1 إلى 12.")
    expected = out.get("expected_head")
    if expected is not None and (not isinstance(expected, str) or len(expected) > 160):
        raise PlanError("STALE_REVISION", "معرّف النسخة غير صالح.")
    from acs_requirement_metrics import unsupported_metrics
    if unsupported_metrics(requirements):
        raise PlanError("REQUIREMENT_METRIC_NOT_SUPPORTED", "يوجد مقياس متطلب غير مدعوم. راجعه قبل بدء أي استدعاء مدفوع.")
    from acs_plan_projection import _requirements
    from types import SimpleNamespace
    _requirements(SimpleNamespace(requirements_json=canonical(requirements), brief=brief))
    if "plot" in out:
        plot_rules(out)  # preflight: an impossible plot fails before any paid call
    if "program" in out:
        if "source_id" in out:
            raise PlanError("INVALID_BRIEF_PROGRAM", "برنامج الوصف يُستخدم مع توليد مخطط من الوصف، لا مع قراءة ملف مخطط.")
        from acs_brief_reader import confirmed_program
        out["program"] = confirmed_program(out["program"], requirements, brief)
    return out


def plot_rules(command):
    """Resolved plot rules for a described residential generation, or None.

    Deterministic: the worker (prompt) and the parent (stamped revision) derive
    the same block from the same command, so the provider never authors it."""
    if "plot" not in command:
        return None
    import acs_plot_rules as P
    plot = P.validate_input(command["plot"])
    if command.get("source_id"):
        raise PlanError("INVALID_PLOT_RULES", "بيانات الأرض تُستخدم مع توليد مخطط من الوصف، لا مع قراءة ملف مخطط.")
    import acs_understand as U
    if not U._is_residential(U.detect_type(command["brief"])):
        raise PlanError("INVALID_PLOT_RULES", "بيانات الأرض والمواقف مدعومة حاليًا للمشاريع السكنية فقط.")
    program = None
    if command.get("program") is not None:
        import acs_brief_reader as BRIEF
        program = BRIEF.usable(command["program"])  # an invalid program is refused by generation_command
    return P.resolve(plot, command["brief"], command["requirements"], command.get("option"), program=program)


def chat_command(command):
    out = checked_command(command, {"job_id", "expected_head", "notes", "confirmed", "max_provider_calls"})
    if out.get("confirmed") is not True or type(out.get("max_provider_calls")) is not int or not 1 <= out["max_provider_calls"] <= 12:
        raise PlanError("EXPLICIT_CONFIRMATION_REQUIRED", "أكد طلب التعديل وحد الاستدعاءات.")
    notes = out.get("notes")
    if not isinstance(notes, list) or not 1 <= len(notes) <= 30 or any(
        not isinstance(n, dict) or set(n) != {"text"} or not isinstance(n["text"], str)
        or not n["text"].strip() or len(n["text"]) > 6000 for n in notes
    ):
        raise PlanError("INVALID_EDIT", "اكتب طلب تعديل واضحًا ضمن الحد المسموح.")
    from acs_plan_commands import validate_plan_chat_command
    validate_plan_chat_command({"action": "chat_edit", "expected_head": out.get("expected_head"), "notes": out.get("notes")}, actor_id="preflight")
    return out


def job_command(command):
    return chat_command(command) if command.get("action") == "chat_edit" else generation_command(command)


def budgeted_chat_candidate(building, notes, max_provider_calls):
    from acs_plan_chat_job import generate_chat_candidate
    from acs_provider_budget import limited
    with limited(max_provider_calls):
        return generate_chat_candidate(building, notes)


def chat_and_save(store, project_id, actor_id, command, *, on_progress=None):
    command = chat_command(command)
    from acs_plan_chat_orchestration import execute_isolated_persisted_chat_edit
    from acs_generation_job import default_runner
    runner = default_runner()

    class BudgetRunner:
        def run(self, target, kwargs, **controls):
            if on_progress:
                controls["on_progress"] = on_progress
            return runner.run("acs_workspace_service:budgeted_chat_candidate", {
                "building": kwargs["building"], "notes": kwargs["notes"],
                "max_provider_calls": command["max_provider_calls"],
            }, **controls)

    notes = json.loads(canonical(command["notes"]))
    notes[-1]["text"] += "\nمعرّف متابعة التعديل: task:" + command["job_id"]
    result = execute_isolated_persisted_chat_edit(store, project_id, {
        "action": "chat_edit", "expected_head": command["expected_head"], "notes": notes,
    }, actor_id=actor_id, verifier=existing_geometry_verifier, runner=BudgetRunner())
    return result["revision_id"]


def generate_plan_candidate(brief, requirements, option, max_provider_calls, resume=None, used_calls=0, plot=None, program=None):
    """Isolated worker: has no actor, bearer, project, store or approval input.

    ``plot`` is the client's plot block; it is resolved here exactly as the
    parent resolves it before stamping the revision."""
    from acs_plan_bridge import generate_candidate, _reject_provider_authority_changes
    from acs_provider_budget import limited
    from acs_workspace_progress import resuming, emit, planning_policy
    import acs_understand as U
    detected = U.detect_type(brief)
    residential = U._is_residential(detected)
    warehouse = detected == 'warehouse'
    if warehouse:
        from acs_warehouse_generation import PLANNING_SYSTEM as WAREHOUSE_PLANNING_SYSTEM
        from warehouse_program_feasibility import warehouse_requirements_preflight
        preflight = warehouse_requirements_preflight(requirements)
        if not preflight.get('may_generate_layout', True):
            if preflight.get('status') == 'BUILDABLE_ENVELOPE_NOT_VERIFIED':
                raise PlanError(
                    'WAREHOUSE_BUILDABLE_ENVELOPE_NOT_VERIFIED',
                    'مساحة المبنى المستهدفة تستهلك كامل مساحة الموقع في مشروع من دور واحد. '
                    'لا يمكن اعتبار كامل الأرض غلافًا بنائيًا متحققًا أو ترك ساحات التشغيل الخارجية دون مساحة. '
                    'أدخل مساحة مبنى أصغر أو موقعًا أكبر؛ لن يخترع ACS ارتدادات أو أبعادًا تنظيمية.'
                )
            raise PlanError(
                'WAREHOUSE_BUILDING_TARGET_INFEASIBLE',
                'مساحة المبنى المستهدفة لا يمكن احتواؤها حسابيًا ضمن أبعاد الموقع وعدد الأدوار المؤكدة.'
            )
    floor_program = None
    if program is not None and residential:
        import acs_brief_reader as BRIEF
        floor_program = BRIEF.validate_program(program)
    rules = None
    if plot is not None and residential:
        rules = plot_rules({"plot": plot, "brief": brief, "requirements": requirements, "option": option,
                            "program": floor_program})
    # A confirmed apartment program is planned floor by floor from a manifest
    # (acs_floor_program): its rooms reach each planning call with their own
    # zones, so the prompt keeps a short building summary and leaves out the
    # per-floor requirement rows the zones already carry.
    per_floor = None
    if floor_program is not None:
        import acs_floor_program as F
        per_floor = F.manifest(floor_program, brief, requirements, rules)
    shown = requirements if per_floor is None else [
        r for r in requirements if not (isinstance(r, dict) and r.get("metric") in F.PER_LEVEL_METRICS)]
    prompt = brief + "\n\nمتطلبات أكدها المستخدم:\n" + canonical(shown)
    prompt += "\nهدف المقترح " + option + ": " + OPTIONS[option]
    if floor_program is not None:
        prompt += F.prompt_text(floor_program) if per_floor is not None else BRIEF.prompt_summary(floor_program)
    confirmed = {r.get('metric'): r.get('expected') for r in requirements if isinstance(r, dict)}
    if (rules is None and confirmed.get('building_width_m') is not None
            and confirmed.get('building_depth_m') is not None):
        # The building's confirmed size is the envelope; the land is context only.
        prompt += ("\nغلاف المبنى المؤكد: اجعل site.w = " + str(confirmed['building_width_m']) + " وsite.d = "
                   + str(confirmed['building_depth_m']) + " (أبعاد المبنى). أبعاد الأرض "
                   + str(confirmed.get('site_width_m')) + " × " + str(confirmed.get('site_depth_m'))
                   + " مرجع فقط، ولا تملأها بالغرف.")
    if warehouse:
        targets=[r.get('expected') for r in requirements if isinstance(r,dict) and r.get('metric')=='building_target_area_m2']
        target=targets[0] if len(targets)==1 and type(targets[0]) in (int,float) else None
        if target is not None:
            prompt += ("\nقيد برنامج المستودع المؤكد: مساحة المبنى الداخلية المستهدفة = "+str(target)+" م². "
                       "اجعل مجموع مساحات مستطيلات الفراغات في جميع الأدوار المشغولة مساويًا للمساحة المستهدفة. احسب كل دور متكرر واستبعد السطح غير المشغول. "
                       "ساحات الشاحنات والمواقف والدوران الخارجي والتوسع المستقبلي عناصر موقع خارجية وليست غرفًا داخلية. "
                       "لا تخترع setbacks أو أبعاد حريق أو اشتراطات غير معطاة.")
    # One villa or house: the livable-villa rules and the confirmed villa program
    # (step 01 villa fields) join the prompt and the planning policy. Apartment
    # buildings keep exactly their prompt and policy.
    from acs_plot_rules import VILLA, dwelling as brief_dwelling
    villa = residential and brief_dwelling(brief, requirements) == VILLA
    if residential:
        from acs_residential_generation import (ROOM_PROGRAM, ROOM_PROGRAM_PLOT, PLANNING_SYSTEM, prepare_layout,
                                                detail, _canonical_room_roles, VILLA_ROOM_PROGRAM,
                                                SINGLE_DWELLING_PLANNING, villa_program_text)
        prompt += "\n" + (ROOM_PROGRAM if rules is None else ROOM_PROGRAM_PLOT)
        if villa:
            prompt += VILLA_ROOM_PROGRAM + villa_program_text(requirements)
        if resume is None or (isinstance(resume,dict) and resume.get('kind') == 'start'):
            from acs_residential_manifest import manifest
            resume = per_floor or manifest(brief, requirements, rules)
        if rules is not None:
            import acs_plot_rules as P
            levels = (resume or {}).get('envelope', {}).get('levels') if isinstance(resume, dict) else None
            names = list(dict.fromkeys(l['template'] for l in levels or []))
            typical = names[1] if len(names) > 1 and per_floor is None else None
            prompt += "\n" + P.prompt_text(rules, names[0] if names else None, typical)
    policy = PLANNING_SYSTEM if residential else WAREHOUSE_PLANNING_SYSTEM if warehouse else None
    if villa:
        policy += SINGLE_DWELLING_PLANNING
    if residential and rules is not None:
        policy += P.PLANNING_ADDENDUM
    if per_floor is not None:
        policy += F.PLANNING_ADDENDUM
    with limited(max_provider_calls, used_calls) as budget, resuming(resume), planning_policy(policy):
        detailed = isinstance(resume,dict) and resume.get("kind") == "details"
        saved_layout = isinstance(resume,dict) and resume.get("kind") in {"details","layout"}
        result = {"building":resume["building"]} if saved_layout else generate_candidate(prompt)
        _reject_provider_authority_changes({}, result["building"])
        if residential:
            try:
                before_layout = canonical(_canonical_room_roles(result["building"]))
                result["building"] = prepare_layout(result["building"], brief, requirements, budget, plot=rules,
                                                    program=floor_program)
                reuse_details = detailed and canonical(result["building"]) == before_layout
                # A confirmed floor program has no fallback that fits it, so once
                # every floor has its openings the plan is kept as a reviewable
                # draft rather than discarded with the calls already paid for.
                keep = floor_program is not None and not F.is_villa(floor_program, brief, requirements)
                result["building"] = detail(result["building"], brief, budget,
                                            resume.get("done") if reuse_details else None, requirements, plot=rules,
                                            program=floor_program, keep_unresolved=keep)
            except PlanError as exc:
                if exc.code not in {"PLAN_LAYOUT_INCOMPLETE", "PLAN_DETAIL_INCOMPLETE"}:
                    raise
                if floor_program is not None and not F.is_villa(floor_program, brief, requirements):
                    # Never the uniform-flat fallback for a confirmed floor program:
                    # it would draw identical floors. This one fits each floor's
                    # own program or names the floor it could not fit.
                    from acs_floor_layout import propose as propose_floors
                    fallback = propose_floors(floor_program, brief, requirements, rules)
                elif rules is None:
                    from acs_residential_layout import propose
                    fallback = propose(brief, requirements)
                else:
                    from acs_plot_layout import propose as propose_in_envelope
                    fallback = propose_in_envelope(brief, requirements, rules)
                if fallback is None:
                    raise
                result["building"] = fallback
                done = [t+':'+str(i) for t,f in fallback['floors'].items() for i in range(0,len(f['rooms']),24)]
                emit('ROOM_DETAILS',{'kind':'details','building':fallback,'done':done},
                     completed=len(done),total=len(done),provider_calls=budget['used'])
        else:
            if warehouse and target is not None:
                from warehouse_program_feasibility import generated_indoor_area
                from warehouse_soft_area_fit import fit_soft_area
                generated=generated_indoor_area(result['building'])
                if generated is not None and generated > target + EPS:
                    # Provider room rectangles are proposals, not hard requirements.
                    # Fit only their soft area budget deterministically; confirmed
                    # role minima remain hard and fail structured when infeasible.
                    result['building'] = fit_soft_area(result['building'], requirements, target)
            from acs_plan_overlap_repair import repair_overlap
            result["building"] = repair_overlap(result["building"], prompt, budget)
        emit("REVIEW",provider_calls=budget["used"])
    candidate = result["building"]
    if rules is not None:
        import acs_plot_rules as P
        P.stamp(candidate, rules)
    _reject_provider_authority_changes({}, candidate)
    return {"building": candidate, "provider_calls": budget["used"], "stage": "PLAN_DRAFT"}


def _reject_fresh_stair_authority(model):
    """A new provider proposal cannot impersonate trusted default authoring.

    Inspect reserved fields independently of object kind/name aliases. Ordinary
    authored geometry stays admissible; this guard never rewrites an object.
    Only the fresh described-project branch calls it.
    """
    def reject():
        raise PlanError("PROVIDER_AUTHORITY_FIELD", "نسب المقترح تفاصيل افتراضية إلى النظام دون مصدر موثوق؛ لم تُحفظ المحاولة.")
    meta = model.get("meta")
    if isinstance(meta, dict) and {"acs_stairs", "acs_context_details"}.intersection(meta):
        reject()
    levels = model.get("levels")
    for level in levels if isinstance(levels, list) else []:
        if isinstance(level, dict) and {"stair_source_template", "stair_template_instance"}.intersection(level):
            reject()
    floors = model.get("floors")
    for floor in floors.values() if isinstance(floors, dict) else []:
        rooms = floor.get("rooms") if isinstance(floor, dict) else None
        for room in rooms if isinstance(rooms, list) else []:
            objects = room.get("objects") if isinstance(room, dict) else None
            for obj in objects if isinstance(objects, list) else []:
                if isinstance(obj, dict) and {"stair_provenance", "context_detail_provenance"}.intersection(obj):
                    reject()


def generate_and_save(store, project_id, actor_id, command, *, runner=None, on_progress=None):
    command = generation_command(command)
    expected = command.get("expected_head")
    before = workspace(store, project_id, actor_id)
    if before.head != expected:
        raise PlanError("STALE_REVISION", "تغيّرت النسخة. افتح آخر نسخة قبل التوليد.")
    if runner is None:
        from acs_generation_job import default_runner
        runner = default_runner()
    kwargs = {
        k: command[k] for k in ("brief", "requirements", "option", "max_provider_calls")
    }
    if "plot" in command:
        kwargs["plot"] = command["plot"]
    if "program" in command:
        kwargs["program"] = command["program"]
    source_receipt = None
    target = "acs_workspace_service:generate_plan_candidate"
    if command.get("source_id"):
        from acs_plan_sources import read_inputs
        kwargs["plan_source"], source_receipt = read_inputs(store, project_id, command)
        target = "acs_plan_sources:candidate"
    if command.get("resume_job_id"):
        from acs_workspace_http import _read_job, _id
        prior = _read_job(store, project_id, _id(command["resume_job_id"]))
        original = prior.get("resume_command") if prior else None
        bound_keys = ("brief", "requirements", "option", "expected_head", "source_id", "source_mode", "source_read", "plot", "program")
        if not original or any(canonical(original.get(k)) != canonical(command.get(k)) for k in bound_keys):
            raise PlanError("INVALID_RESUME", "تغيّر وصف المهمة أو مرجعها. ابدأ طلبًا جديدًا.")
        kwargs.update(resume=prior.get("checkpoint"), used_calls=prior.get("provider_calls",0))
        if kwargs["used_calls"] >= command["max_provider_calls"]:
            raise PlanError("ACS_PROVIDER_BUDGET_EXHAUSTED", geometry_failure_message("ACS_PROVIDER_BUDGET_EXHAUSTED"))
    controls = {"on_progress":on_progress} if on_progress else {}
    result = runner.run(target, kwargs, request_id=command["job_id"], **controls)
    if not isinstance(result, dict) or not isinstance(result.get("building"), dict):
        raise PlanError("INVALID_PLAN", "لم يعد المزود بمخطط صالح.")
    from acs_plan_bridge import _reject_provider_authority_changes
    _reject_provider_authority_changes({}, result["building"])
    proposal = json.loads(canonical(result["building"]))
    # Re-read after provider work, then append with compare-and-swap. Existing
    # locks apply to every new option, and an approved baseline remains unchanged.
    ws = workspace(store, project_id, actor_id)
    if ws.head != expected:
        raise GeneratedVersionConflict(proposal, ws.head)
    try:
        return _admit_generated(store, project_id, actor_id, command, result["building"], ws,
                                source_receipt=source_receipt, on_progress=on_progress,
                                note=("مقروء من ملفك" if command.get("source_id") else "البديل " + command["option"])
                                + " · " + adoption_marker(command["job_id"]))
    except PlanError as exc:
        if exc.code != "STALE_REVISION":
            raise
        # The head moved between the re-read and the compare-and-swap append.
        raise GeneratedVersionConflict(proposal, None) from None


def _admit_generated(store, project_id, actor_id, command, building, ws, *, source_receipt, on_progress, note):
    """Admit one provider building on top of ``ws.head`` and append it (no provider call)."""
    expected = ws.head
    result = {"building": building}
    # The parent re-derives the plot rules from the validated command: the
    # stamped block never comes from the worker or the provider.
    import acs_plot_rules as P
    P.stamp(result["building"], plot_rules(command))
    import acs_brief_reader as BRIEF
    BRIEF.stamp(result["building"], command.get("program"))
    if source_receipt:
        result["building"].setdefault("meta", {})["acs_plan_source"] = source_receipt
    if on_progress:
        on_progress({"phase":"REVIEW"})
    # The deterministic stair default belongs only to a new described project.
    # Imports, resumed work and every existing revision keep their authored
    # objects and lock context. This runs after stale-head detection and before
    # canonical proposal/approval; it makes no provider request.
    fresh_describe = (expected is None and command.get("expected_head") is None
                     and "source_id" not in command and "resume_job_id" not in command)
    if fresh_describe:
        from acs_stairs import with_default_stairs
        _reject_fresh_stair_authority(result["building"])
        result["building"], _, stair_reason = with_default_stairs(result["building"])
        if stair_reason == "STAIR_RESOURCE_LIMIT":
            raise PlanError(stair_reason, geometry_failure_message(stair_reason))
    # Every generated building receives the same disclosed default roof: a flat
    # deck with a parapet, canonical model data recorded in meta.acs_roof as a
    # system default. It is added after the provider reply, so the provider never
    # authors it and it costs no provider call.
    #   - current head already has the automatic roof -> rebuild it over the new option;
    #   - current head has locked rooms and no roof    -> leave the option as it is,
    #     because room locks freeze levels/meta and a new level would be rejected;
    #   - otherwise (first generation, or an unlocked project) -> add the default.
    import acs_roof
    _head = ws.get(expected) if expected else None
    _head_model = _head.model if _head is not None else None
    if _head_model is not None and acs_roof._auto_roof_levels(_head_model):
        result["building"] = acs_roof.carry_auto_roof(_head_model, result["building"])
    elif _head_model is not None and acs_roof.roof_removed_by_user(_head_model):
        # A provider proposal cannot override the owner's persisted preference.
        # Reject the conflict before proposing/saving; stripping arbitrary roof
        # geometry here could silently remove authored elements or references.
        if acs_roof.has_roof_level(result["building"]):
            raise PlanError("ROOF_PREFERENCE_CONFLICT",
                            geometry_failure_message("ROOF_PREFERENCE_CONFLICT"))
        result["building"] = acs_roof.mark_roof_removed(result["building"])
    elif _head is not None and _head.locked_rooms and not acs_roof.has_roof_level(_head_model):
        pass
    else:
        result["building"], _, _ = acs_roof.with_default_roof(result["building"])
    if fresh_describe:
        from acs_context_details import with_context_details
        result["building"], _, detail_reason = with_context_details(result["building"])
        if detail_reason in {"CONTEXT_DETAILS_RESOURCE_LIMIT", "CONTEXT_DETAILS_PROVENANCE_INVALID"}:
            raise PlanError(detail_reason, geometry_failure_message(detail_reason))
    revision = ws.propose(result["building"], brief=command["brief"], requirements=command["requirements"],
                          expected_head=expected, note=note)
    issues, _ = _geometry(revision.model)
    # Warehouse Design Options are allowed to reach read-only 2D review while
    # vertical engineering facts remain explicitly unknown. Only those three
    # unknowns are deferred; every horizontal/canonical defect remains blocking.
    from warehouse_vertical_stage_gate import draft_geometry_admission
    admission = draft_geometry_admission(revision.model, issues)
    if admission["blocking"]:
        # First blocking category in the canonical validator's deterministic order.
        reason = admission["blocking"][0].get("code")
        code = "PLAN_GEOMETRY_" + reason if reason in GEOMETRY_MESSAGES else "INVALID_GEOMETRY"
        raise PlanError(code, geometry_failure_message(code))
    _view_result(ws, "generate", revision.id)  # stage-aware 2D projection admission before write
    if on_progress:
        on_progress({"phase":"SAVING"})
    store.save_revision(project_id, actor_id=actor_id, revision=revision, expected_head=expected)
    return revision.id


def adopt_generated_version(store, project_id, actor_id, row, expected_head):
    """Owner's explicit choice: append a kept generated version on top of the current head.

    No provider request and no quota: the version was paid for by its job. The
    current head (for example the owner's manual edit) stays in history and can
    be restored. Every canonical gate runs again against the current head
    (provider-authority fields, roof preference, room locks, geometry and 2D
    projection admission). Retrying the same choice returns the same revision.
    """
    kept = generated_version(row)
    original = row.get("resume_command") if isinstance(row.get("resume_command"), dict) else None
    if kept is None or original is None or original.get("action") != "generate":
        raise PlanError("GENERATED_VERSION_NOT_FOUND", "لا توجد نسخة مولّدة محفوظة لهذه المهمة.")
    command = generation_command(dict(original, expected_head=expected_head))
    ws = workspace(store, project_id, actor_id)
    marker = adoption_marker(row["id"])
    for revision in ws.history():
        if (revision.get("note") or "").endswith(marker):
            return revision["revision_id"]
    if expected_head is None or ws.head != expected_head:
        raise PlanError("STALE_REVISION", "تغيّرت النسخة الحالية. افتح آخر نسخة ثم اختر من جديد.")
    from acs_plan_bridge import _reject_provider_authority_changes
    building = json.loads(canonical(kept["building"]))
    _reject_provider_authority_changes({}, building)
    source_receipt = None
    if command.get("source_id"):
        from acs_plan_sources import source_receipt as receipt
        source_receipt = receipt(store, project_id, command)
    return _admit_generated(store, project_id, actor_id, command, building, ws, source_receipt=source_receipt,
                            on_progress=None,
                            note="اعتماد النسخة المولّدة (البديل " + command["option"] + ") بعد تعديل أحدث · " + marker)


def set_roof(store, project_id, actor_id, command):
    """Remove or restore the automatic default roof as a new draft revision.

    No provider call. A user-authored roof is never removed here. Room locks
    freeze the level list, so the change is refused with an explanation while
    any room is locked.
    """
    command = checked_command(command, {"expected_head", "enabled"})
    ws = workspace(store, project_id, actor_id)
    expected = command.get("expected_head")
    if not expected or ws.head != expected:
        raise PlanError("STALE_REVISION", "افتح آخر نسخة قبل التعديل.")
    if type(command.get("enabled")) is not bool:
        raise PlanError("INVALID_PLAN_COMMAND", "حدّد إضافة السطح أو إزالته.")
    import acs_roof
    before = ws.get(expected)
    try:
        if command["enabled"]:
            candidate = acs_roof.restore_default_roof(before.model)
            note = "إضافة السطح الافتراضي"
        else:
            candidate = acs_roof.remove_auto_roof(before.model)
            note = "إزالة السطح الافتراضي"
    except ValueError as exc:
        messages = {"ROOF_LEVEL_EXISTS": "هذه النسخة فيها سطح بالفعل.",
                    "ROOF_NOT_AUTOMATIC": "لا يوجد سطح تلقائي لإزالته. السطح الذي أضفته بنفسك يُعدَّل كأي دور."}
        raise PlanError("INVALID_GEOMETRY", messages.get(str(exc), "تعذّرت إضافة السطح لهذه النسخة."))
    try:
        revision = ws.propose(candidate, brief=before.brief, requirements=json.loads(before.requirements_json),
                              expected_head=expected, note=note)
    except PlanError as exc:
        if exc.code == "LOCK_CONTEXT_CHANGED":
            raise PlanError("LOCK_CONTEXT_CHANGED", "فكّ أقفال الفراغات أولًا: إضافة السطح أو إزالته يغيّر أدوار المبنى.")
        raise
    result = _view_result(ws, "set_roof", revision.id, reference_revision_id=expected)
    store.save_revision(project_id, actor_id=actor_id, revision=revision, expected_head=expected)
    return result


def edit_geometry(store, project_id, actor_id, command):
    command = checked_command(command, {"expected_head", "room_ref", "rect"})
    ws = workspace(store, project_id, actor_id)
    expected = command.get("expected_head")
    if not expected or ws.head != expected:
        raise PlanError("STALE_REVISION", "افتح آخر نسخة قبل التعديل.")
    ref, rect = command.get("room_ref"), command.get("rect")
    if not isinstance(ref, list) or len(ref) != 2 or any(not isinstance(v, str) for v in ref):
        raise PlanError("ROOM_NOT_FOUND", "اختر فراغًا من المخطط.")
    if not isinstance(rect, list) or len(rect) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in rect) or min(rect[2:]) <= 0:
        raise PlanError("INVALID_GEOMETRY", "أدخل موضعًا وأبعادًا صالحة بالمتر.")
    before = ws.get(expected)
    candidate = before.model
    floor = candidate["floors"].get(ref[0])
    room = next((r for r in floor["rooms"] if r["id"] == ref[1]), None) if floor else None
    if room is None:
        raise PlanError("ROOM_NOT_FOUND", "الفراغ غير موجود في هذه النسخة.")
    import acs_roof
    if acs_roof.is_auto_roof_template(candidate, ref[0]):
        raise PlanError("INVALID_GEOMETRY", "السطح يتبع الدور الأخير تلقائيًا. عدّل فراغات الدور الأخير وسيتبعه السطح.")
    room["rect"] = rect
    # Keep the automatic roof over the edited top storey; a removed or
    # user-authored roof is never touched.
    candidate = carry_roof_for_admission(before.model, candidate)
    revision = ws.propose(candidate, brief=before.brief, requirements=json.loads(before.requirements_json),
                          expected_head=expected, note="تعديل أبعاد وموضع " + (room["name"].strip()[:120] if isinstance(room.get("name"), str) and room["name"].strip() else ref[1]))
    result = _view_result(ws, "edit_geometry", revision.id, reference_revision_id=expected)
    store.save_revision(project_id, actor_id=actor_id, revision=revision, expected_head=expected)
    return result


def artifact(store, project_id, actor_id, command):
    command = checked_command(command, {"revision_id", "format", "level_index"})
    ws = workspace(store, project_id, actor_id)
    rid, fmt = command.get("revision_id"), command.get("format")
    if fmt not in {"svg", "dxf", "pdf", "ifc", "gltf", "review"}:
        raise PlanError("INVALID_FORMAT", "صيغة التصدير غير مدعومة.")
    if fmt == "review":
        from tools.acs_plan_review_packet import build_review_packet
        raw = canonical(build_review_packet(ws, rid)).encode("utf-8")
        return {"ok": True, "filename": "acs-review.json", "mime": "application/json", "data_base64": base64.b64encode(raw).decode("ascii")}
    # All other formats must first resolve the exact stored approval receipt.
    ws.handoff(rid)
    with tempfile.TemporaryDirectory(prefix="acs-approved-") as directory:
        path = Path(directory) / ("acs-approved." + fmt)
        level = command.get("level_index")
        if fmt in {"svg", "dxf"}:
            from tools.acs_plan_cad_export import export_approved_cad
            receipt = export_approved_cad(ws, rid, level, path)
        elif fmt == "pdf":
            from tools.acs_plan_pdf_export import export_approved_pdf
            receipt = export_approved_pdf(ws, rid, path)
        elif fmt == "ifc":
            from tools.acs_plan_ifc_export import export_approved_ifc
            receipt = export_approved_ifc(ws, rid, path)
        else:
            from tools.acs_plan_handoff import compile_approved_baseline
            receipt = compile_approved_baseline(ws, rid, path)
        if path.stat().st_size > 12 * 1024 * 1024:
            raise PlanError("INPUT_LIMIT", "ملف التصدير أكبر من حد التسليم المباشر.")
        raw = path.read_bytes()
    return {"ok": True, "revision_id": rid, "filename": path.name, "mime": {
        "svg": "image/svg+xml", "dxf": "application/dxf", "pdf": "application/pdf", "ifc": "application/x-step", "gltf": "model/gltf+json"
    }[fmt], "data_base64": base64.b64encode(raw).decode("ascii"), "receipt": receipt}


class _SnapshotStore:
    """Immutable server-read snapshot for the isolated artifact compiler."""
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def project_state(self, *args, **kwargs):
        raise PlanError("READ_ONLY", "Artifact workers cannot read mutable project state")

    def workspace_snapshot(self, project_id, *, actor_id):
        if project_id != self.snapshot.get("project_id"):
            raise PlanError("PROJECT_ACCESS_DENIED", "Artifact project changed")
        return self.snapshot

    def save_revision(self, *args, **kwargs):
        raise PlanError("READ_ONLY", "Artifact workers cannot write revisions")

    def save_approval(self, *args, **kwargs):
        raise PlanError("READ_ONLY", "Artifact workers cannot approve")


def artifact_from_snapshot(snapshot, command):
    """No access token, provider or database client crosses this worker boundary."""
    try:
        return artifact(_SnapshotStore(snapshot), snapshot["project_id"], "artifact-worker", command)
    except PlanError as exc:
        # Domain validation must survive process isolation. Generic worker errors
        # remain private and are handled by the runner, never copied here.
        return {"ok": False, "artifact_error": {"code": exc.code, "message": str(exc)}}


def isolated_artifact(store, project_id, actor_id, command):
    checked_command(command, {"revision_id", "format", "level_index"})
    snapshot = store.workspace_snapshot(project_id, actor_id=actor_id)
    from acs_generation_job import default_runner
    result = default_runner().run("acs_workspace_service:artifact_from_snapshot", {
        "snapshot": snapshot, "command": command,
    }, timeout_s=60)
    if isinstance(result, dict) and isinstance(result.get("artifact_error"), dict):
        error = result["artifact_error"]
        raise PlanError(error["code"], error["message"])
    return result
