#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot transformer for the audited residential-quality branch.

It refuses to edit when any expected source fragment has drifted. The workflow
that invokes it deletes this file before committing the resulting product code.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_one(rel, old, new):
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{rel}: expected one source fragment, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("updated", rel)


# ---------------------------------------------------------------------------
# 1) Generation: plot boundary is not automatically the residential footprint.
# ---------------------------------------------------------------------------
replace_one(
    "acs_understand.py",
    '''def _is_industrial(bt):\n    return str(bt or "").lower() in _INDUSTRIAL\n\n\nSCHEMA_BRIEF = r"""''',
    '''def _is_industrial(bt):\n    return str(bt or "").lower() in _INDUSTRIAL\n\n\ndef _is_residential(bt):\n    """Residential massing applies only to programs classified residential."""\n    if _programs is not None:\n        try:\n            p = _programs.program(bt)\n            if p:\n                return p.get("categories") == "residential"\n        except Exception:\n            pass\n    return str(bt or "").lower() in {"residential", "villa", "apartment"}\n\n\nSCHEMA_BRIEF = r"""''')

replace_one(
    "acs_understand.py",
    '- ابقَ ضمن مسطح البناء (site). لا تسمح بأي تداخل بين مستطيلات الغرف.',
    '- site هي حدود **قطعة الأرض** وليست بصمة المبنى تلقائياً. أبقِ كل الهندسة داخلها، ولا تسمح بأي تداخل بين مستطيلات الغرف.')

replace_one(
    "acs_understand.py",
    '''الغرف المتجاورة تتلامس ولا تتداخل؛ اجمعها بحيث تملأ مسطح الدور بشكل منطقي.\n"""\n''',
    '''الغرف المتجاورة تتلامس ولا تتداخل؛ اجمعها داخل بصمة مبنى مدمجة ومقروءة، ولا تمدّدها إلى حدود site لمجرّد أن المساحة متاحة.\n"""\n\nRESIDENTIAL_MASSING_RULE = r"""\nقاعدة الكتلة السكنية — تطبّق على residential / villa / apartment فقط:\n- `site` هو حد قطعة الأرض، وليس أمراً بأن يغطي المبنى كامل القطعة.\n- إذا لم يطلب العميل صراحةً بناءً يغطي الأرض، لا تمد الغرف أو البلاطات لملء `site` ولا تجعل كل واجهة على حد الأرض.\n- اشتق بصمة مبنى مدمجة من الغرف والممرات المطلوبة فقط. المساحة الباقية تبقى خارج كتلة المبنى؛ لا تحوّلها إلى غرفة ولا تضف لها وظيفة لم يطلبها العميل.\n- لا تخترع نسبة بناء أو ارتداداً نظامياً أو رقماً تنظيمياً. عند غياب هذه القيم يكفي ألّا توسّع الكتلة بلا سبب.\n- إذا طلب العميل حوشاً أو فناءً أو مسبحاً أو حديقةً أو مواقف خارجية، احفظ لها مساحة فعلية ولا تبتلعها الغرف أو البلاطات.\n- عند تعدد الأدوار حافظ على نواة الدرج/المصعد رأسياً، ولا توسّع الدور العلوي تلقائياً لمجرّد وجود أرض فارغة أسفله.\n- اجعل المدخل الرئيسي مقروءاً من واجهة خارجية، وغرف المجلس/المعيشة والنوم ذات واجهات ونوافذ خارجية مناسبة عندما لم يحدد العميل خلاف ذلك.\n- الهدف كتلة منزل/فيلا قابلة للقراءة، لا صندوقاً بحجم قطعة الأرض.\n\n"""\n''')

replace_one(
    "acs_understand.py",
    '''def system_prompt(btype="residential"):\n    industrial = _is_industrial(btype)\n    schema = SCHEMA_BRIEF + (SCHEMA_INDUSTRIAL if industrial else "") + G.COMPACT_RULE\n    know = KNOWLEDGE_WAREHOUSE if industrial else KNOWLEDGE\n''',
    '''def system_prompt(btype="residential"):\n    industrial = _is_industrial(btype)\n    residential = _is_residential(btype)\n    schema = SCHEMA_BRIEF + (SCHEMA_INDUSTRIAL if industrial else "") + G.COMPACT_RULE\n    know = KNOWLEDGE_WAREHOUSE if industrial else KNOWLEDGE\n    massing = RESIDENTIAL_MASSING_RULE if residential else ""\n''')

replace_one(
    "acs_understand.py",
    '''        + PRIORITY_RULE +\n        "التزم حرفياً بهذا المخطّط (صيغة الإخراج):\\n" + schema + "\\n"\n''',
    '''        + PRIORITY_RULE + massing +\n        "التزم حرفياً بهذا المخطّط (صيغة الإخراج):\\n" + schema + "\\n"\n''')


# ---------------------------------------------------------------------------
# 2) Frontend: expose the existing single lazy-loader without opening a panel.
#    Dynamic import ownership remains in panels-entry.js only.
# ---------------------------------------------------------------------------
replace_one(
    "public/app/ui/panels-entry.js",
    '''  window.ACS.panelEntryPoints = () => ({\n    workspace: 'acsOpenWorkspace',\n    panels: GENERATED_PANELS.map((p) => ({ ns: p.ns, button: p.button })),\n  });\n  /* حالة التأجيل مقروءة من الخارج — لا يُستنتَج التحميل من وجود اللوحة. */\n''',
    '''  window.ACS.panelEntryPoints = () => ({\n    workspace: 'acsOpenWorkspace',\n    panels: GENERATED_PANELS.map((p) => ({ ns: p.ns, button: p.button })),\n  });\n  /* تحميلٌ بلا فتح لوحة: يستخدم نفس المالك الوحيد لنداءات import()، كي تستطيع\n     جودة السكن تهيئة طبقة العرض بعد التوليد من غير وميض واجهة أو مدخل ثانٍ. */\n  window.ACS.ensureLayer = (ns) => loadLayer(ns);\n  /* حالة التأجيل مقروءة من الخارج — لا يُستنتَج التحميل من وجود اللوحة. */\n''')

replace_one(
    "public/app/main.js",
    "import './ui/panels-entry.js';\n",
    "import './ui/panels-entry.js';\n/* Residential visual-quality policy. It runs after the panel lazy-loader exists. */\nimport './ui/residential-quality.js';\n")


residential_js = r'''/* ============================================================================
   Residential Quality Pass
   ------------------------
   Presentation only. The canonical Building JSON is never changed here.
   Residential/villa/apartment models get the already-shipped PBR pipeline and
   architectural window detailing automatically after a successful model load.
   Industrial/warehouse models are deliberately outside this policy.
   ========================================================================= */

const ACS_RESIDENTIAL_TYPES = new Set(['residential', 'villa', 'apartment']);
let ACS_RQ_SEQ = 0;
let ACS_RQ_AUTO_ACTIVE = false;
let ACS_RQ_LAST = null;

function acsResidentialType(building) {
  const meta = (building && building.meta) || {};
  return String(meta.type || '').trim().toLowerCase();
}

function acsIsResidential(building) {
  return ACS_RESIDENTIAL_TYPES.has(acsResidentialType(building));
}

function acsResidentialAfterPaint(fn) {
  if (typeof requestAnimationFrame === 'function') {
    requestAnimationFrame(() => requestAnimationFrame(fn));
  } else {
    Promise.resolve().then(fn);
  }
}

function acsRestoreOwnedResidentialPresentation() {
  if (!ACS_RQ_AUTO_ACTIVE || typeof window === 'undefined') return false;
  const A = window.ACS || {};
  try { if (A.adRestore) A.adRestore(); } catch (e) { /* presentation only */ }
  try { if (A.pbrRestore) A.pbrRestore(); } catch (e) { /* presentation only */ }
  ACS_RQ_AUTO_ACTIVE = false;
  return true;
}

async function acsApplyResidentialQuality(building, token) {
  const ownToken = (token === undefined) ? ++ACS_RQ_SEQ : token;
  if (ownToken !== ACS_RQ_SEQ) return { applied: false, stale: true };

  /* A new model must not inherit the previous model's automatic presentation. */
  acsRestoreOwnedResidentialPresentation();

  const type = acsResidentialType(building);
  if (!acsIsResidential(building)) {
    ACS_RQ_LAST = { applied: false, type, reason: 'not_residential' };
    return ACS_RQ_LAST;
  }

  const A = (typeof window !== 'undefined' && window.ACS) ? window.ACS : {};
  const mobile = (typeof window !== 'undefined' && window.innerWidth <= 820);
  let pbrApplied = false;
  let detailApplied = false;
  const issues = [];

  try {
    if (A.pbr && typeof A.pbr.config === 'function'
        && typeof A.pbrApply === 'function'
        && typeof A.pbrCaps === 'function'
        && typeof A.pbrBounds === 'function') {
      const pbr = A.pbr.config(
        mobile ? 'MEDIUM' : 'HIGH',
        'CLEAR_NOON',
        'REALISTIC',
        'SKY',
        null,
        null,
        A.pbrCaps(),
        A.pbrBounds(),
      );
      if (pbr && pbr.valid && ownToken === ACS_RQ_SEQ) {
        const result = A.pbrApply(pbr.config);
        pbrApplied = !!(result && result.applied);
        if (pbrApplied && typeof A.pbrCameraPreset === 'function') {
          A.pbrCameraPreset('EXTERIOR_HERO');
        }
      }
    }

    /* Frames/reveals are already implemented in the lazy architectural layer.
       Load it through panels-entry's single loader without opening its panel. */
    if (typeof A.ensureLayer === 'function' && ownToken === ACS_RQ_SEQ) {
      await A.ensureLayer('archdetail');
      if (ownToken !== ACS_RQ_SEQ) return { applied: false, stale: true };
      if (A.archdetail && typeof A.archdetail.config === 'function'
          && typeof A.adApply === 'function'
          && typeof A.adModelSummary === 'function') {
        const ad = A.archdetail.config(
          'DETAIL_HIGH',
          'REALISTIC',
          'NONE',
          'STAGING_REQUESTED_ONLY',
          'EXTERIOR_HERO_CORNER',
          'CLEAR_SKY',
          null,
          mobile,
          [],
          A.adModelSummary(),
        );
        if (ad && ad.valid && ownToken === ACS_RQ_SEQ) {
          const result = A.adApply(ad.config);
          detailApplied = !!(result && result.applied);
        }
      }
    }
  } catch (err) {
    issues.push(String((err && err.message) || err).slice(0, 160));
  }

  ACS_RQ_AUTO_ACTIVE = pbrApplied || detailApplied;
  ACS_RQ_LAST = {
    applied: ACS_RQ_AUTO_ACTIVE,
    type,
    pbr: pbrApplied,
    architectural_detail: detailApplied,
    mobile,
    issues,
  };
  return ACS_RQ_LAST;
}

function acsScheduleResidentialQuality(building) {
  const token = ++ACS_RQ_SEQ;
  acsResidentialAfterPaint(() => {
    if (token === ACS_RQ_SEQ) acsApplyResidentialQuality(building, token);
  });
  return token;
}

function acsWireResidentialQuality() {
  if (typeof window === 'undefined') return false;
  window.ACS = window.ACS || {};
  const A = window.ACS;

  /* Public setModel stays synchronous and preserves its return value. */
  if (typeof A.setModel === 'function' && !A.setModel.__acsResidentialQuality) {
    const original = A.setModel;
    const wrapped = function residentialSetModel(building) {
      acsRestoreOwnedResidentialPresentation();
      const result = original.apply(this, arguments);
      acsScheduleResidentialQuality(building);
      return result;
    };
    wrapped.__acsResidentialQuality = true;
    wrapped.__acsOriginal = original;
    A.setModel = wrapped;
  }

  /* Server generation uses the module-local setModel, so observe the generation
     promise itself and enhance only when the active model reference changed. */
  const gen = (typeof document !== 'undefined') ? document.getElementById('genLLM') : null;
  if (gen && typeof gen.onclick === 'function' && !gen.__acsResidentialQuality) {
    const originalGenerate = gen.onclick;
    gen.onclick = function residentialGenerateClick(ev) {
      const before = (A.exportModel && A.exportModel()) || null;
      const result = originalGenerate.call(this, ev);
      Promise.resolve(result).then(() => {
        const after = (A.exportModel && A.exportModel()) || null;
        if (after && after !== before) acsScheduleResidentialQuality(after);
      }, () => { /* generation owns its own error UI */ });
      return result;
    };
    gen.__acsResidentialQuality = true;
  }

  A.residentialQuality = {
    isResidential: acsIsResidential,
    apply: (building) => acsApplyResidentialQuality(building),
    restore: acsRestoreOwnedResidentialPresentation,
    state: () => ACS_RQ_LAST ? Object.assign({}, ACS_RQ_LAST) : null,
  };
  return true;
}

acsWireResidentialQuality();
'''
(ROOT / "public/app/ui/residential-quality.js").write_text(residential_js, encoding="utf-8")
print("created public/app/ui/residential-quality.js")


residential_py_test = r'''# -*- coding: utf-8 -*-
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
'''
(ROOT / "tests/remediation/test_residential_quality.py").write_text(residential_py_test, encoding="utf-8")
print("created tests/remediation/test_residential_quality.py")


residential_js_test = r'''\'use strict\';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.resolve(__dirname, '..', '..');
const SRC = fs.readFileSync(path.join(ROOT, 'public/app/ui/residential-quality.js'), 'utf8');
let passed = 0;
function chk(name, value) {
  assert.ok(value, name); passed++; console.log('PASS ' + name);
}

async function flush() {
  await Promise.resolve(); await Promise.resolve(); await new Promise(r => setTimeout(r, 0));
}

(async () => {
  let current = null;
  let pbrApply = 0, detailApply = 0, ensure = 0, camera = null;
  let pbrRestore = 0, adRestore = 0;
  const pbrCalls = [], adCalls = [];
  const generatedVilla = {meta:{type:'villa'},site:{w:20,d:25},levels:[],floors:{}};

  const ACS = {
    setModel(building) { current = building; return 'SET_OK'; },
    exportModel() { return current; },
    pbr: { config(...args) {
      pbrCalls.push(args);
      return {valid:true, config:{writes_to_model:false}};
    }},
    pbrCaps() { return {webgl2:true}; },
    pbrBounds() { return {cx:0,cy:1,cz:0,radius:10,min_y:0}; },
    pbrApply() { pbrApply++; return {applied:true}; },
    pbrCameraPreset(name) { camera = name; return {applied:true}; },
    pbrRestore() { pbrRestore++; return {restored:true}; },
    adRestore() { adRestore++; return true; },
    async ensureLayer(ns) {
      ensure++;
      assert.equal(ns, 'archdetail');
      ACS.archdetail = {config(...args) {
        adCalls.push(args);
        return {valid:true,config:{writes_to_model:false,detail:{effective:'DETAIL_HIGH'}}};
      }};
      ACS.adModelSummary = () => ({exterior_walls:4,windows:6});
      ACS.adApply = () => { detailApply++; return {applied:true}; };
      return true;
    },
  };

  const genButton = {onclick: async function () { current = generatedVilla; }};
  const context = {
    window:{ACS,innerWidth:1280},
    document:{getElementById:id=>id==='genLLM'?genButton:null},
    requestAnimationFrame:fn=>fn(),
    Promise, Set, String, Object, console,
  };
  vm.runInNewContext(SRC, context, {filename:'residential-quality.js'});

  chk('public setModel keeps its synchronous return contract',
      context.window.ACS.setModel({meta:{type:'villa'}}) === 'SET_OK');
  await flush();
  chk('villa automatically receives the shipped PBR presentation', pbrApply === 1);
  chk('desktop residential quality asks for HIGH PBR quality', pbrCalls[0][0] === 'HIGH');
  chk('PBR uses the declared realistic/noon/sky path',
      pbrCalls[0][1] === 'CLEAR_NOON' && pbrCalls[0][2] === 'REALISTIC' && pbrCalls[0][3] === 'SKY');
  chk('residential presentation uses the hero exterior camera', camera === 'EXTERIOR_HERO');
  chk('architectural detail is loaded through the existing lazy owner', ensure === 1);
  chk('architectural detail is applied after PBR', detailApply === 1);
  chk('detail request is HIGH + REALISTIC without inventing user facade intent',
      adCalls[0][0] === 'DETAIL_HIGH' && adCalls[0][1] === 'REALISTIC'
      && Array.isArray(adCalls[0][8]) && adCalls[0][8].length === 0);

  const beforeWarehousePbr = pbrApply, beforeWarehouseEnsure = ensure;
  context.window.ACS.setModel({meta:{type:'warehouse'}});
  await flush();
  chk('warehouse never receives residential PBR automatically', pbrApply === beforeWarehousePbr);
  chk('warehouse never loads residential architectural detail automatically', ensure === beforeWarehouseEnsure);
  chk('leaving residential mode restores only the presentation that this policy owned',
      pbrRestore >= 1 && adRestore >= 1);

  context.window.innerWidth = 390;
  context.window.ACS.setModel({meta:{type:'apartment'}});
  await flush();
  chk('mobile residential presentation uses MEDIUM PBR quality',
      pbrCalls[pbrCalls.length - 1][0] === 'MEDIUM');
  chk('mobile flag is passed to architectural detail so its declared fallback applies',
      adCalls[adCalls.length - 1][7] === true);

  const pbrBeforeGenerated = pbrApply;
  current = {meta:{type:'warehouse'}};
  await genButton.onclick();
  await flush();
  chk('server-generation path is observed even though it uses module-local setModel',
      pbrApply === pbrBeforeGenerated + 1);
  chk('the enhancer never mutates the generated canonical object',
      generatedVilla.meta.type === 'villa' && generatedVilla.site.w === 20);
  chk('diagnostic state reports presentation only after a residential model',
      context.window.ACS.residentialQuality.state().applied === true);
  chk('classifier is narrow: office is not silently treated as residential',
      context.window.ACS.residentialQuality.isResidential({meta:{type:'office'}}) === false);

  console.log(`RESIDENTIAL PRESENTATION: ${passed} passed, 0 failed`);
})().catch(err => { console.error(err); process.exitCode = 1; });
'''.replace("\\'use strict\\';", "'use strict';")
(ROOT / "tests/remediation/test_residential_presentation.js").write_text(residential_js_test, encoding="utf-8")
print("created tests/remediation/test_residential_presentation.js")


# ---------------------------------------------------------------------------
# 3) Make both regressions mandatory in the existing CI gates.
# ---------------------------------------------------------------------------
replace_one(
    ".github/workflows/ci.yml",
    '''                   tests/remediation/test_concurrency.js \\\n                   tests/remediation/test_persistence.js\n''',
    '''                   tests/remediation/test_concurrency.js \\\n                   tests/remediation/test_persistence.js \\\n                   tests/remediation/test_residential_presentation.js\n''')

replace_one(
    ".github/workflows/ci.yml",
    '''                   tests/remediation/test_plan_chunking.py \\\n                   tests/remediation/test_generation_spatial_context.py \\\n                   tests/remediation/test_event_loop.py \\\n''',
    '''                   tests/remediation/test_plan_chunking.py \\\n                   tests/remediation/test_generation_spatial_context.py \\\n                   tests/remediation/test_residential_quality.py \\\n                   tests/remediation/test_event_loop.py \\\n''')

print("residential quality transformation complete")
