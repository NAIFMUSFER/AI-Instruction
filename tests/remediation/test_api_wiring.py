# -*- coding: utf-8 -*-
"""ربط طبقة الـAPI بأهدافها — التحقّق الذي لا يقوم به الفحص النصّي.

يعيد إنتاج عيباً حقيقياً وقع أثناء هذا التصحيح نفسه:

  حين صار التوليد يعمل في عملية مستقلّة، لم تعد الدالّة تُمرَّر ككائن بل صار
  الهدف نصّاً "module:function" مع قاموس وسائط. كُتِب الوسيط باسم `text` بينما
  توقيع `acs_understand.understand` يسمّيه `description`. الشيفرة تُترجَم،
  و`py_compile` ينجح، والفحص النصّي (AST) يرى النداء موجوداً — ولا شيء من ذلك
  يكشف أن كل طلب توليد كان سيرتفع بـ TypeError عند أوّل استدعاء حقيقي.

الدرس المُقنَّن هنا: كل هدف يُحلّ فعلاً، وكل قاموس وسائط يُربَط فعلاً بالتوقيع
عبر inspect.Signature.bind_partial. fastapi غير مثبّتة في هذا الصندوق، لذا يُقرأ
الملفّ بـ AST ثم تُختبَر الأهداف والوسائط تشغيلاً.
"""
import ast
import importlib
import inspect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s%s' % (name, ('  — %s' % detail) if detail else ''))


API_PATH = os.path.join(ROOT, 'acs_understand_api.py')
with open(API_PATH, 'r', encoding='utf-8') as fh:
    API_SRC = fh.read()
TREE = ast.parse(API_SRC)


def _dict_keys(node):
    """أسماء المفاتيح من dict(...) أو من حرفيّ {...}."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id == 'dict':
        return [k.arg for k in node.keywords if k.arg]
    if isinstance(node, ast.Dict):
        return [k.value for k in node.keys if isinstance(k, ast.Constant)]
    return None


# ثوابت الوحدة: اسم -> حرفيّ. أهداف run_job صارت أسماءً مسمّاة لا سلاسل
# مبعثرة (نقطةُ ضبطٍ واحدة لـ«أي وحدة تنفّذ التوليد»)، فيُحلّ الاسم خطوةً
# واحدة إلى حرفيّه. العقد لم يضعف: الهدف ما زال يجب أن يكون قابلاً للحلّ
# **ساكناً** إلى "module:function"، وما زال يُستورَد ويُربَط فعلاً أدناه.
MODULE_CONSTANTS = {}
for _n in TREE.body:
    if isinstance(_n, ast.Assign) and len(_n.targets) == 1 \
            and isinstance(_n.targets[0], ast.Name) \
            and isinstance(_n.value, ast.Constant) \
            and isinstance(_n.value.value, str):
        MODULE_CONSTANTS[_n.targets[0].id] = _n.value.value


def _as_target(node, locals_map):
    """حرفيّ الهدف من عقدة: سلسلةً مباشرةً، أو اسماً يُحلّ إلى سلسلة."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in MODULE_CONSTANTS:
            return MODULE_CONSTANTS[node.id]
        v = locals_map.get(node.id)
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            return v.value
    return None


# خريطة الإسنادات المحلّية داخل كل دالّة: name -> عقدة القيمة
def _local_assignments(fn_node):
    out = {}
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            out[n.targets[0].id] = n.value
    return out


print('\n── أ · كل هدف run_job يُحلّ فعلاً وكل وسيط يُربَط فعلاً ──')

calls = []
for fn in ast.walk(TREE):
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
    locals_map = _local_assignments(fn)
    for node in ast.walk(fn):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'run_job'):
            continue
        target = _as_target(node.args[0], locals_map) if node.args else None
        keys = None
        if len(node.args) > 1:
            arg = node.args[1]
            keys = _dict_keys(arg)
            if keys is None and isinstance(arg, ast.Name):
                keys = _dict_keys(locals_map.get(arg.id))
        calls.append((fn.name, target, keys, node.lineno))

chk('every generation route reaches a job target',
    len(calls) >= 4, str([(c[0], c[1]) for c in calls]))
chk('every run_job target resolves STATICALLY to a "module:function" string '
    '(a literal, or a module constant holding one — never a computed value)',
    all(isinstance(c[1], str) and ':' in c[1] for c in calls),
    str([c[1] for c in calls]))
chk('the named targets are real module constants, and each names the module '
    'that actually implements generation',
    all(v.startswith('acs_') and ':' in v
        for k, v in MODULE_CONSTANTS.items() if k.startswith('TARGET_')),
    str({k: v for k, v in MODULE_CONSTANTS.items() if k.startswith('TARGET_')}))
chk('every run_job keyword set is statically resolvable',
    all(c[2] is not None for c in calls),
    str([(c[0], c[3]) for c in calls if c[2] is None]))

for route, target, keys, line in calls:
    if not isinstance(target, str) or ':' not in target:
        continue
    mod_name, fn_name = target.split(':', 1)
    try:
        mod = importlib.import_module(mod_name)
    except Exception as exc:                                      # noqa: BLE001
        chk('%s · the target module %s imports' % (route, mod_name), False,
            type(exc).__name__)
        continue
    chk('%s · the target module %s imports' % (route, mod_name), True)
    fn = getattr(mod, fn_name, None)
    chk('%s · %s exists and is callable' % (route, target),
        callable(fn))
    if not callable(fn):
        continue
    sig = inspect.signature(fn)
    if keys is None:
        continue
    try:
        sig.bind_partial(**{k: None for k in keys})
        ok, detail = True, ''
    except TypeError as exc:
        ok, detail = False, '%s (line %d) — %s' % (str(sig), line, exc)
    chk('%s · every keyword binds to %s' % (route, target), ok, detail)
    required = [n for n, prm in sig.parameters.items()
                if prm.default is inspect._empty
                and prm.kind in (prm.POSITIONAL_OR_KEYWORD, prm.KEYWORD_ONLY)]
    missing = [n for n in required if n not in (keys or [])]
    chk('%s · every required parameter of %s is supplied' % (route, target),
        not missing, str(missing))

print('\n── ب · لا مسار توليد يستعمل المسار غير القابل للإلغاء ──')

bounded = [n for n in ast.walk(TREE)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
           and n.func.id == 'run_bounded']
chk('no route calls the legacy uncancellable run_bounded',
    len(bounded) == 0, str([n.lineno for n in bounded]))

routes = {n.name for n in ast.walk(TREE)
          if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
          and any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                  and d.func.attr in ('get', 'post') for d in n.decorator_list)}
chk('every documented endpoint is still present',
    {'root', 'health', 'ready', 'version', 'understand', 'edit',
     'understand_image', 'understand_pdf'} <= routes, str(sorted(routes)))

import acs_cpu_pool as _CPUP
# W1-B: المعالج ينادي `ea_plan_model` — نفس الوحدة، ونفس `plan()` داخلها،
# لكنه يعيد النموذج المُطبَّع معه. كلا الهدفين يبقيان معلنَين، والمقيس هنا أن
# المعالج يستعمل الهدف الذي **يُرجِع** النموذج، لا الذي يترك تطبيعاته في العامل.
chk('the engineering planner is reachable through the declared cpu-pool target',
    _CPUP.TARGETS.get('ea_plan') == ('acs_engineering_authority', 'plan')
    and _CPUP.TARGETS.get('ea_plan_model')
        == ('acs_engineering_authority', 'plan_with_model')
    and 'await _validate("ea_plan_model"' in API_SRC)
chk('the target the handler uses is the one that returns the normalised model',
    'await _validate("ea_plan"' not in API_SRC.replace(
        'await _validate("ea_plan_model"', ''))
chk('and no handler calls the planner synchronously any more (KI-14)',
    'EA.plan(' not in API_SRC and 'EA.flat_diff(' not in API_SRC)
print('\n── ج · وحدات التصحيح مستوردة ومستعملة فعلاً ──')
for mod, alias, use in (('acs_logging', 'LOGGING', 'LOG.'),
                        ('acs_rate_limit', 'RL', 'RL.'),
                        ('acs_upload_security', 'UPLOAD', 'UPLOAD.'),
                        # KI-14/F-46: مخطّط سلطة التغيير لم يعد يُستدعى
                        # مباشرةً — نداؤه المتزامن كان يوقف الحلقة ١٫٦ ثانية
                        # على نموذج تحت السقف. صار يمرّ بمجمّع العمليات،
                        # فالمرساة استعمالٌ مباشر باقٍ، ومسار المجمّع
                        # يُتحقَّق منه في الفحصين التاليين.
                        ('acs_engineering_authority', 'EA', 'EA.health_status'),
                        ('acs_generation_job', 'JOBS', 'JOBS.'),
                        ('acs_build_info', 'BUILD', 'BUILD.build_info')):
    chk('%s is imported' % mod, ('import %s as %s' % (mod, alias)) in API_SRC)
    chk('%s is actually used' % mod, use in API_SRC)
    try:
        importlib.import_module(mod)
        ok = True
    except Exception as exc:                                      # noqa: BLE001
        ok = False
    chk('%s imports cleanly on its own' % mod, ok)

print('\n── د · كل دالّة يستدعيها الـAPI من وحدات التصحيح موجودة فعلاً ──')
# نداءات ALIAS.function(...) — تُحلّ على الوحدة الحقيقية بدل الاكتفاء بوجود النصّ
ALIASES = {'RL': 'acs_rate_limit', 'UPLOAD': 'acs_upload_security',
           'EA': 'acs_engineering_authority', 'JOBS': 'acs_generation_job',
           'BUILD': 'acs_build_info', 'LOGGING': 'acs_logging'}
seen = set()
for node in ast.walk(TREE):
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
            and node.value.id in ALIASES:
        seen.add((node.value.id, node.attr))
chk('the api references at least one symbol per remediation module',
    {a for a, _ in seen} >= set(ALIASES), str(sorted({a for a, _ in seen})))
for alias, attr in sorted(seen):
    mod = importlib.import_module(ALIASES[alias])
    chk('%s.%s exists in %s' % (alias, attr, ALIASES[alias]),
        hasattr(mod, attr))

print('\n── هـ · كل اسمٍ تلمسه الاختبارات على وحدة الـAPI موجودٌ فيها ──')
# العطل الذي أوجب هذا القسم:
#   tests/phase9_2/test_backend_contract.py كان ينادي `API._hits.clear()`.
#   أزال تصحيحُ F-04 ذلك القاموس ونقل العدّ إلى acs_rate_limit، فصار النداء
#   AttributeError يُسقط الملفّ كلّه — ووظيفةَ CI معه.
#   ولم يظهر سنةً كاملة لأن القسم كان يموت قبله بسطرٍ واحد على
#   TypeError من TestClient. عطلٌ يختبئ خلف عطل.
#
# الفحص ساكن عمداً: يقرأ الشجرة النحوية لوحدة الـAPI ولا يستوردها، فيعمل هنا
# حيث fastapi غير مثبّتة — أي في البيئة نفسها التي أخفت العطل.
API_TOP = set()
for node in TREE.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        API_TOP.add(node.name)
    elif isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                API_TOP.add(t.id)
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        API_TOP.add(node.target.id)
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        for a in node.names:
            API_TOP.add(a.asname or a.name.split('.')[0])
    elif isinstance(node, (ast.If, ast.Try)):
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assign):
                for t in sub.targets:
                    if isinstance(t, ast.Name):
                        API_TOP.add(t.id)
            elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                API_TOP.add(sub.name)

chk('the api module exposes a non-trivial top-level surface',
    len(API_TOP) > 30, str(len(API_TOP)))

CONSUMERS = ['tests/phase9_2/test_backend_contract.py']
touched = 0
for rel in CONSUMERS:
    path = os.path.join(ROOT, rel)
    chk(rel + ' exists', os.path.exists(path))
    if not os.path.exists(path):
        continue
    tree = ast.parse(open(path, encoding='utf-8').read(), rel)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                and node.value.id == 'API':
            names.add(node.attr)
    chk(rel + ' really does reach into the api module', len(names) >= 4,
        str(sorted(names)))
    for attr in sorted(names):
        touched += 1
        chk('%s uses API.%s — and acs_understand_api defines it'
            % (rel.split("/")[-1], attr), attr in API_TOP,
            'not a module-level name in acs_understand_api.py')

print('  · %d API attribute reference(s) checked statically, no import needed'
      % touched)

print('\n' + '─' * 62)
print('API WIRING: %d passed, %d failed' % (p[0], f[0]))
sys.exit(1 if f[0] else 0)
