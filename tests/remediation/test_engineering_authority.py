# -*- coding: utf-8 -*-
"""F-01 — سلطة التغيير الهندسي: لا تغيير صامت.

يعيد إنتاج العيب ثم يثبت زواله:

  كان `acs_layout.autofix` يُستدعى في أربعة مواضع من مسار التوليد ويكتب في
  النموذج مباشرة: يُزيح الغرف، ويرصّها صفّياً، ويقلّصها حتى 44%، ويخترع أبواباً
  وكواشف دخان ومرشّات وأفياشاً ومفاتيح. القائمة `added` التي تبني الإفصاح كانت
  شيفرة ميّتة لا يقرأها أحد، والتقرير المُعاد كان يُطبع أو يُهمَل. فالمستخدم يرى
  نموذجاً يظنّه تصميمه وقد غُيّرت أبعاده وأُضيفت إليه عناصر سلامة لم يطلبها.

الأقسام:
  أ) السجلّ الآليّ نفسه: كل تغيير مصنَّف، ولا تغيير خارج السجلّ.
  ب) الحالات الثماني المطلوبة A–H.
  ج) التطبيعات الآمنة: محدودة، موثّقة المصدر، ولا تستبدل قيمة ذكرها المستخدم.
  د) لا مسار إيداع تلقائي، ولا مسار كتابة ثانٍ.
  هـ) تكافؤ البصمة مع بوّابة التأليف، والإفصاح لا يُمحى.
"""
import ast
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_authoring as A                                         # noqa: E402
import acs_engineering_approval as AP                             # noqa: E402
import acs_engineering_authority as EA                            # noqa: E402
import acs_layout as L                                            # noqa: E402

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s%s' % (name, ('  — %s' % detail) if detail else ''))


def rd(rel):
    with open(os.path.join(ROOT, rel), 'r', encoding='utf-8') as fh:
        return fh.read()


def canon(model):
    return json.dumps(model, ensure_ascii=False, sort_keys=True)


def mk(rooms, w=20.0, d=16.0, btype='villa', meta=None, **extra):
    m = {"meta": dict({"name": "t", "type": btype}, **(meta or {})),
         "site": {"w": w, "d": d},
         "floor_height": 3.2, "wall_h": 3.0, "wall_t": 0.15,
         "levels": [{"index": 0, "name": "ground", "template": "g"}],
         "floors": {"g": {"rooms": copy.deepcopy(rooms)}}}
    m.update(extra)
    return m


VALID = mk([{"id": "living", "rect": [0.0, 0.0, 6.0, 5.0]},
            {"id": "bed", "rect": [7.0, 0.0, 5.0, 4.0]}])
OVERLAP = mk([{"id": "living", "rect": [0.0, 0.0, 8.0, 6.0]},
              {"id": "bed", "rect": [4.0, 2.0, 7.0, 6.0]}], w=12.0, d=10.0)


def plan_of(model):
    m = copy.deepcopy(model)
    proj = A.create_project(m, "bld_0", source="TEST", actor_id="tester")
    plan = EA.plan(proj["model"], base_revision=proj["current_revision"])
    return proj, plan


def pick(plan, change_id):
    return [x for x in plan["proposals"] if x["type"] == change_id]


# ═════════════════════════════════════════════════════ أ) السجلّ الآليّ ═════
print('\n── أ · السجلّ الآليّ للتغييرات ──')

SPEC = EA.SPEC
chk('the registry declares a schema and a version',
    bool(SPEC.get('schema')) and bool(SPEC.get('version')))
chk('the registry declares exactly the two allowed classes',
    tuple(SPEC['classes']) == ('SAFE_NORMALIZATION', 'ENGINEERING_PROPOSAL'))
chk('every rule carries the six mandatory fields',
    all(all(k in r for k in ('change_id', 'source_module', 'class',
                             'changes_canonical_model', 'reason',
                             'requires_user_confirmation', 'provenance_required'))
        for r in SPEC['rules']),
    str([r.get('change_id') for r in SPEC['rules']
         if 'provenance_required' not in r]))
chk('every rule requires provenance',
    all(r['provenance_required'] is True for r in SPEC['rules']))
chk('every engineering proposal requires user confirmation',
    all(r['requires_user_confirmation'] is True
        for r in SPEC['rules'] if r['class'] == 'ENGINEERING_PROPOSAL'))
chk('no safe normalisation asks for confirmation, by construction',
    all(r['requires_user_confirmation'] is False
        for r in SPEC['rules'] if r['class'] == 'SAFE_NORMALIZATION'))
chk('every declared change id is unique',
    len({r['change_id'] for r in SPEC['rules']}) == len(SPEC['rules']))


def _raises(fn, exc):
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


chk('an unregistered change id raises rather than passing silently',
    _raises(lambda: EA.classify('NOT_A_DECLARED_CHANGE'), KeyError))
chk('a safe rule can never be turned into a proposal object',
    _raises(lambda: EA.proposal('LAYOUT_ROUND_RECT', ['x'], {}, {}), ValueError))

# كل تغيير يجريه المصلِح موسوم بمعرّف مسجَّل — يُثبَت تشغيلاً لا نصّاً
_rec = EA.Recorder()
L.autofix(copy.deepcopy(OVERLAP), authority=EA.AUTHORITY_APPLY, recorder=_rec)
chk('the layout engine emits at least one recorded change on a broken model',
    len(_rec.events) > 0, str(len(_rec.events)))
chk('every recorded change carries a registered change id',
    all(e['change_id'] in EA.RULES for e in _rec.events),
    str(sorted({e['change_id'] for e in _rec.events
                if e['change_id'] not in EA.RULES})))
chk('the safety and security additions are classified as proposals, never safe',
    all(EA.RULES[c]['class'] == 'ENGINEERING_PROPOSAL'
        for c in ('LAYOUT_ADD_SMOKE_DETECTOR', 'LAYOUT_ADD_SPRINKLER',
                  'LAYOUT_ADD_DOOR', 'FLS_ADD_EXIT', 'SEC_ADD_CAMERA',
                  'LAYOUT_PROPORTIONAL_SHRINK', 'LAYOUT_SHELF_PACK',
                  'LAYOUT_RESOLVE_OVERLAPS', 'LAYOUT_CLAMP_TO_SITE')))

# ═══════════════════════════════════════════ ب) الحالات المطلوبة A–H ═══════
print('\n── ب · الحالات الثماني ──')


def case(name, model, change_id, approve_types=None, expect_commit=True):
    """قالب واحد لكل حالة: اقتراح موجود، البصمة ثابتة، الرفض لا يغيّر شيئاً،
    والاعتماد ينتج مراجعة واحدة طبيعية."""
    proj, plan = plan_of(model)
    before_hash = proj["model_hash"]
    before_canon = canon(proj["model"])
    hits = pick(plan, change_id)
    chk('%s · a proposal of type %s exists' % (name, change_id),
        len(hits) > 0, str(sorted({x["type"] for x in plan["proposals"]})))
    if not hits:
        return
    prop = hits[0]
    chk('%s · the proposal claims no engineering authority' % name,
        prop["engineering_authority"] is False
        and prop["requires_explicit_confirmation"] is True
        and prop["committed"] is False
        and prop["source"] == "SYSTEM")
    chk('%s · the proposal records provenance and a base revision' % name,
        prop["provenance"]["change_id"] == change_id
        and prop["base_revision"] == proj["current_revision"]
        and prop["model_hash_before"] == before_hash)
    chk('%s · the proposal carries a before and an after state' % name,
        isinstance(prop["before"], dict) and isinstance(prop["after"], dict)
        and (prop["before"] or prop["after"]))
    chk('%s · planning left the canonical model byte-identical' % name,
        canon(proj["model"]) == before_canon
        and EA.model_hash(proj["model"]) == before_hash)

    rejected = AP.reject(proj, plan["proposals"], [prop["proposal_id"]])
    chk('%s · rejecting leaves the model identical' % name,
        canon(rejected["project"]["model"]) == before_canon
        and rejected["model_hash"] == before_hash
        and rejected["committed"] is False)

    ids = [x["proposal_id"] for x in plan["proposals"]
           if x["type"] in (approve_types or [change_id])]
    res = AP.approve(proj, plan["proposals"], ids, actor_id="tester",
                     created_at="2026-01-01T00:00:00Z")
    if not expect_commit:
        chk('%s · the proposal is reported but cannot be committed by the system'
            % name, res.get("committed") is not True)
        return
    chk('%s · approving commits through the authoring path' % name,
        res.get("committed") is True,
        json.dumps(res.get("issues"), ensure_ascii=False)[:300])
    if not res.get("committed"):
        return
    np_ = res["project"]
    chk('%s · approving created exactly one new revision' % name,
        len(np_["history"]) == len(proj["history"]) + 1
        and np_["current_revision"] != proj["current_revision"],
        '%d -> %d' % (len(proj["history"]), len(np_["history"])))
    chk('%s · the parent project is untouched after the commit' % name,
        canon(proj["model"]) == before_canon)
    chk('%s · the commit is audited' % name,
        len(np_.get("audit_log") or []) > len(proj.get("audit_log") or []))
    chk('%s · the committed model actually differs from the parent' % name,
        canon(np_["model"]) != before_canon)


# A — توسيع الأرض: مجموع الغرف يتجاوز الأرض فعلاً
# غرف متجاورة بلا تداخل، ومجموع مساحاتها (81 م²) يتجاوز سعة الأرض (73.6 م²):
# البديل غير الهدّام هو توسيع الأرض بدل تقليص الغرف.
TIGHT = mk([{"id": "living", "rect": [0.0, 0.0, 9.0, 3.0]},
            {"id": "bed", "rect": [0.0, 3.0, 9.0, 3.0]},
            {"id": "kitchen", "rect": [0.0, 6.0, 9.0, 3.0]}], w=10.0, d=8.0)
case('A site expansion', TIGHT, 'LAYOUT_SITE_EXPANSION')

# B — توسيع ممرّ صناعي
AISLE = mk([{"id": "forklift_aisle", "rect": [0.0, 0.0, 20.0, 2.0]},
            {"id": "rack_zone", "rect": [0.0, 4.0, 20.0, 8.0]}],
           w=30.0, d=25.0, btype='warehouse')
case('B aisle resize', AISLE, 'LAYOUT_AISLE_WIDTH')

# C — إضافة مخرج
case('C exit addition', VALID, 'FLS_ADD_EXIT')

# D — إضافة كاشف دخان
case('D smoke detector', VALID, 'LAYOUT_ADD_SMOKE_DETECTOR')

# E — إضافة مرشّة
SPRINK = mk([{"id": "storage_zone", "rect": [0.0, 0.0, 40.0, 30.0],
              "walls": "none", "role": "storage"}],
            w=60.0, d=40.0, btype='warehouse')
case('E sprinkler', SPRINK, 'LAYOUT_ADD_SPRINKLER')

# F — تغيير أبعاد منطقة
case('F zone resize', OVERLAP, 'LAYOUT_PROPORTIONAL_SHRINK',
     approve_types=['LAYOUT_RESOLVE_OVERLAPS', 'LAYOUT_SHELF_PACK',
                    'LAYOUT_PROPORTIONAL_SHRINK', 'LAYOUT_CLAMP_TO_SITE'])

# G — تغيير عدد الكاميرات
case('G camera count', VALID, 'SEC_ADD_CAMERA')

# H — تصحيح تداخل الغرف
case('H room overlap', OVERLAP, 'LAYOUT_RESOLVE_OVERLAPS',
     approve_types=['LAYOUT_RESOLVE_OVERLAPS', 'LAYOUT_SHELF_PACK',
                    'LAYOUT_PROPORTIONAL_SHRINK', 'LAYOUT_CLAMP_TO_SITE'])

print('\n── ب2 · الفتحات والنقاط تُقترَح ولا تُطبَّق ──')
NARROW = mk([{"id": "wc", "rect": [0.0, 0.0, 1.2, 1.2],
              "doors": [{"edge": "N", "width": 3.0}]}])
_, plan_open = plan_of(NARROW)
chk('openings_are_proposed · a door too wide for its edge becomes a proposal',
    len(pick(plan_open, 'LAYOUT_OPENING_WIDTH_FIT')) > 0
    or len(pick(plan_open, 'LAYOUT_OPENING_OFFSET_SET')) > 0,
    str(sorted({x["type"] for x in plan_open["proposals"]})))

STRAY = mk([{"id": "hall", "rect": [0.0, 0.0, 5.0, 4.0],
             "points": [{"type": "camera", "x": 99.0, "z": 99.0},
                        {"type": "outlet", "x": 1.0, "z": 1.0, "height": 1.9}]}])
_, plan_pts = plan_of(STRAY)
chk('points_are_proposed · a point outside its room becomes a proposal',
    len(pick(plan_pts, 'LAYOUT_POINT_CLAMP')) > 0)
chk('points_are_proposed · overwriting a user-stated height becomes a proposal',
    len(pick(plan_pts, 'LAYOUT_POINT_HEIGHT_STANDARD')) > 0)

_, plan_gap = plan_of(VALID)
chk('code_gaps_are_proposed · extinguisher and assembly gaps are proposed',
    len(pick(plan_gap, 'FLS_ADD_EXTINGUISHER')) > 0
    and len(pick(plan_gap, 'FLS_ADD_ASSEMBLY_POINT')) > 0)

# ══════════════════════════════════════════════ ج) التطبيعات الآمنة ════════
print('\n── ج · التطبيعات الآمنة وحدها تُكتب ──')

m_defaults = mk([{"id": "a", "rect": [0.0, 0.0, 4.0, 4.0]}])
for k in ("floor_height", "wall_h", "wall_t"):
    m_defaults.pop(k, None)
applied = EA.apply_safe_normalisations(m_defaults)
chk('defaults_never_overwrite · an absent structural constant is filled',
    m_defaults["floor_height"] == 3.2 and m_defaults["wall_h"] == 3.0)
chk('defaults_never_overwrite · the fill records its provenance',
    (m_defaults["meta"]["acs_provenance"]["system_defaults"]["floor_height"]
     ["source"]) == "system_default")

m_stated = mk([{"id": "a", "rect": [0.0, 0.0, 4.0, 4.0]}], floor_height=4.7)
EA.apply_safe_normalisations(m_stated)
chk('defaults_never_overwrite · a user-stated value is never replaced',
    m_stated["floor_height"] == 4.7)
chk('defaults_never_overwrite · nothing is recorded when nothing was filled',
    "acs_provenance" not in (m_stated.get("meta") or {}))

m_round = mk([{"id": "a", "rect": [0.0, 0.0, 4.001, 4.0]}])
EA.apply_safe_normalisations(m_round)
chk('safe_rounding_is_bounded · a sub-tolerance value is canonicalised',
    m_round["floors"]["g"]["rooms"][0]["rect"][2] == 4.0)
m_big = mk([{"id": "a", "rect": [0.0, 0.0, 4.4, 4.0]}])
EA.apply_safe_normalisations(m_big)
chk('safe_rounding_is_bounded · a value beyond the tolerance is left alone',
    m_big["floors"]["g"]["rooms"][0]["rect"][2] == 4.4)
chk('safe_rounding_is_bounded · the declared tolerance is half a centimetre',
    float(EA.classify('LAYOUT_ROUND_RECT')['tolerance_m']) <= 0.005)

# التخطيط لا يغيّر البصمة على نموذج مطبَّع أصلاً
proj_v, plan_v = plan_of(VALID)
chk('model_hash_unchanged_before_approval · planning is hash-neutral',
    plan_v["unchanged"] is True
    and plan_v["model_hash_before"] == plan_v["model_hash_after"])
chk('model_hash_unchanged_before_approval · autofix defaults to PROPOSE',
    L.autofix(copy.deepcopy(VALID))["applied"] is False)
chk('model_hash_unchanged_before_approval · the default authority is declared',
    EA.health_status()["default_authority"] == "PROPOSE")

_m = copy.deepcopy(VALID)
_before = canon(_m)
L.autofix(_m)
chk('model_hash_unchanged_before_approval · a default autofix call writes nothing',
    canon(_m) == _before)

# ═══════════════════════════════════════ د) لا مسار إيداع تلقائي ═══════════
print('\n── د · لا مسار كتابة ثانٍ ولا إيداع تلقائي ──')

UNDERSTAND_SRC = rd('acs_understand.py')
chk('no generation path calls the layout autofixer any more',
    'L.autofix' not in UNDERSTAND_SRC and 'autofix(' not in UNDERSTAND_SRC)
chk('the generation pipeline does not import the layout engine at all',
    'import acs_layout' not in UNDERSTAND_SRC)

LAYOUT_SRC = rd('acs_layout.py')
_tree = ast.parse(LAYOUT_SRC)
_autofix = [n for n in ast.walk(_tree)
            if isinstance(n, ast.FunctionDef) and n.name == 'autofix']
chk('autofix declares an explicit authority argument', len(_autofix) == 1
    and any(a.arg == 'authority' for a in _autofix[0].args.args))
chk('the default authority argument is PROPOSE',
    'authority=AUTHORITY_PROPOSE' in LAYOUT_SRC)
chk('an unknown authority mode is refused rather than assumed',
    _raises(lambda: L.autofix(copy.deepcopy(VALID), authority='WHATEVER'),
            ValueError))

AUTH_SRC = rd('acs_engineering_authority.py')
chk('the planning layer never imports the authoring layer',
    'import acs_authoring' not in AUTH_SRC)
APPROVE_SRC = rd('acs_engineering_approval.py')
chk('approval routes through commit_transaction and nothing else',
    'commit_transaction' in APPROVE_SRC
    and 'A.commit_transaction' in APPROVE_SRC)
chk('there is no implicit approve-all',
    AP.approve(proj_v, plan_v["proposals"], [])["committed"] is False)
chk('an unknown proposal id is refused',
    AP.approve(proj_v, plan_v["proposals"],
               ["prop:0000000000000000"])["committed"] is False)

_stale = [dict(x, base_revision="rev:deadbeefdeadbeef")
          for x in plan_v["proposals"]]
chk('a proposal computed against another revision is refused as stale',
    AP.approve(proj_v, _stale,
               [_stale[0]["proposal_id"]]).get("issues", [{}])[0].get("code")
    == "STALE_BASE_REVISION")

REG = json.loads(rd('acs_engineering_changes.json'))
chk('the registry states the single mutation path explicitly',
    'commit_transaction' in REG['single_mutation_path'])
chk('the registry states that the system holds no engineering authority',
    'engineering_authority=false' in REG['authority_note'])
chk('the health status reports no auto-commit path',
    EA.health_status()["auto_commit_path"] is False)

# ══════════════════════════ هـ) تكافؤ البصمة والإفصاح ══════════════════════
print('\n── هـ · تكافؤ البصمة والإفصاح ──')

for name, model in (('valid', VALID), ('overlap', OVERLAP), ('aisle', AISLE)):
    chk('the planning hash equals the authoring gate hash (%s)' % name,
        EA.model_hash(model) == A.model_hash(model, "building", "bld_0"))

chk('disclosure_is_never_wiped · strict mode preserves what the generator added',
    'acs_engineering_disclosure' in UNDERSTAND_SRC
    and '_preserve_added_disclosure' in UNDERSTAND_SRC)
_disc = {"meta": {"added": ["مصعد", "سلّم طوارئ"], "strict": True}}
U = __import__('acs_understand')
U._preserve_added_disclosure(_disc)
chk('disclosure_is_never_wiped · the list survives in an explicit field',
    _disc["meta"]["acs_engineering_disclosure"]["ai_added"] ==
    ["مصعد", "سلّم طوارئ"])

# PROJECT_ELEMENT_IDS — النسخة العميقة تحمي المُدخَل
import acs_project as PJ                                          # noqa: E402
_src = copy.deepcopy(VALID)
_snapshot = canon(_src)
PJ.to_project(_src, "bld_0")
chk('ids_never_mutate_input · to_project does not mutate the caller model',
    canon(_src) == _snapshot,
    'PROJECT_ELEMENT_IDS is declared changes_canonical_model=false')

_stage = REG['rules']
chk('stage_merge_is_pre_canonical · the stage merge is declared pre-canonical',
    all(r['changes_canonical_model'] is False
        for r in _stage if r['change_id'] == 'UNDERSTAND_STAGE_MERGE'))

print('\n' + '─' * 62)
print('ENGINEERING AUTHORITY: %d passed, %d failed' % (p[0], f[0]))
sys.exit(1 if f[0] else 0)
