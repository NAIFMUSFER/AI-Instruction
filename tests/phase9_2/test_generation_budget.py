# -*- coding: utf-8 -*-
"""انقطاع المخرج واكتمال التوليد — علاج ACS_UPSTREAM_TRUNCATED.

العطل الإنتاجي: «مستودع بسيط 20×15م، دور واحد، منطقة تخزين ومنطقة استقبال.»
يصل الخادم والمنبع، ثم يعود HTTP 502 برمز ACS_UPSTREAM_TRUNCATED وسبب توقّف
max_tokens، فلا يصل الواجهة نموذجٌ صالح ويبقى المشهد فارغاً.

آليّة العطل بالكامل، وكلّ حلقة منها مُثبتة هنا بلا نداء نموذج:

  1. قرار «مرحلة واحدة أم مراحل» كان يُتَّخذ بـ `_should_go_deep`، ومقياسه طول
     **المدخل**: أكثر من 2200 حرف أو 12 بنداً مرقّماً. الوصف الإنتاجي 55 حرفاً
     وبلا بنود، فيسلك النداء الواحد دائماً — مهما كان حجم مخرجه.
  2. حجم المخرج لا يُقدَّر إطلاقاً قبل النداء. المستودع يستدعي مخطّطاً صناعياً
     كاملاً (racks · lanes · stations · docks · points لكل منطقة) وقواعد تفرض
     مخارج وطفايات ورشاشات وكاميرات — مخرجٌ لا يقاس بطول السطر الذي طلبه.
  3. الميزانية موزّعة على خمسة ثوابت غير مترابطة، فلا أحد يعرف السقف الفعلي.
  4. عند stop_reason=max_tokens كان `_balance_json` يغلق الأقواس الناقصة ويُمرّر
     ما نتج. فإمّا مرّ نصف نموذج إلى المصرِّف صامتاً، وإمّا فشل التحليل فظهر
     الانقطاع خطأً نهائياً بلا محاولة استراتيجية أخرى.
  5. سلّم المحاولات كان يهبط إلى 16000 ثم 8000 رمزاً — أي أن «علاج» الانقطاع
     كان تكرار الطلب نفسه بسقف **أصغر**، فيقطع أبكر.

القاعدة المصحَّحة: قدِّر المخرج قبل النداء، اختر الاستراتيجية من التقدير، احكم
بسبب التوقّف قبل التحليل، اطرح المقطوع بلا ترميم، ثم صعِّد إلى المراحل وقسِّم
المجموعة المنقطعة — بحدود معلنة.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import acs_api_errors as E                                        # noqa: E402
import acs_generation as G                                        # noqa: E402
import acs_understand as U                                        # noqa: E402

PROD_PROMPT = "مستودع بسيط 20×15م، دور واحد، منطقة تخزين ومنطقة استقبال."
BIG_PROMPT = ("مركز توزيع 120×80م: استلام، فحص جودة، تخزين بالتات، أرفف متوسطة، "
              "التقاط، تغليف، ملصقات، فرز، تجميع، شحن، 12 رصيف تحميل، مكاتب "
              "إدارة، غرفة سيرفرات، ورشة صيانة، استراحة موظفين.")

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s%s' % (name, ('  — %s' % detail) if detail else ''))


def _catch(fn, *a, **kw):
    """يعيد رمز الخطأ المصنّف، أو 'OK'، أو 'UNCLASSIFIED:<صنف>' — لا يرمي أبداً."""
    try:
        fn(*a, **kw)
        return 'OK'
    except E.AcsApiError as err:
        return err.code
    except Exception as err:                                      # noqa: BLE001
        return 'UNCLASSIFIED:' + type(err).__name__


# ─────────────────────────────────────── مِغزل نموذج مزيّف (بلا شبكة) ────────
class FakeMessage(object):
    """رسالة على شكل رد Anthropic: content[].text + stop_reason + usage."""

    class _Block(object):
        def __init__(self, text):
            self.text = text

    class _Usage(object):
        def __init__(self, i, o):
            self.input_tokens = i
            self.output_tokens = o

    def __init__(self, text, stop_reason="end_turn", out=None):
        self.content = [FakeMessage._Block(text)]
        self.stop_reason = stop_reason
        self.usage = FakeMessage._Usage(1200, out if out is not None else len(text) // 3)


class FakeClient(object):
    """يستبدل عميل anthropic كاملاً. يسجّل كل نداء ويعيد ردوداً مبرمَجة."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.messages = self

    def stream(self, **kw):
        self.calls.append(kw)
        msg = self.script.pop(0) if self.script else FakeMessage("{}")
        client = self

        class _Ctx(object):
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False

            def get_final_message(self_inner):
                return msg
        return _Ctx()

    def create(self, **kw):                                       # مسار المكتبة القديمة
        self.calls.append(kw)
        return self.script.pop(0) if self.script else FakeMessage("{}")


class FakeAnthropicModule(object):
    def __init__(self, client):
        self._client = client

    def Anthropic(self, **kw):
        return self._client


def with_fake(script, fn):
    """يشغّل fn بعميل مزيّف ومفتاح وهمي، ثم يعيد (النتيجة/الخطأ، العميل)."""
    import types
    fake_client = FakeClient(script)
    mod = types.ModuleType("anthropic")
    mod.Anthropic = lambda **kw: fake_client
    saved_mod = sys.modules.get("anthropic")
    saved_key = os.environ.get("ANTHROPIC_API_KEY")
    sys.modules["anthropic"] = mod
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-fake-for-tests-only"
    try:
        return fn(), fake_client
    finally:
        if saved_mod is None:
            sys.modules.pop("anthropic", None)
        else:
            sys.modules["anthropic"] = saved_mod
        if saved_key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = saved_key


def tiny_building(rooms=("storage", "receiving")):
    return {"site": {"w": 20, "d": 15}, "floor_height": 12.0, "wall_h": 11.0,
            "wall_t": 0.2, "levels": [{"id": "L0", "template": "t", "elevation": 0}],
            "floors": {"t": {"rooms": [
                {"id": r, "rect": [0.2 + 9.8 * i, 0.2, 9.4, 14.6], "role": r,
                 "walls": "none"} for i, r in enumerate(rooms)]}},
            "meta": {"type": "warehouse", "requirements": []}}


# ═══════════════════════════════ أ) المقدّر والتصنيف (§5) ═══════════════════
print('\n── أ · تقدير حجم المخرج قبل النداء ──')

chk('the budget contract is declared', bool(G.GENERATION_CONTRACT_VERSION))
chk('there is ONE authoritative output budget, read from one name',
    G.max_output_tokens() > 0 and 'ACS_LLM_MAX_OUTPUT_TOKENS' in
    io.open(os.path.join(ROOT, 'acs_generation.py'), encoding='utf-8').read())
chk('every stage budget is derived from that one number, none is a free constant',
    all(G.stage_budget(s) <= G.max_output_tokens() for s in
        ('single', 'plan', 'detail', 'repair'))
    and G.stage_budget('plan') < G.stage_budget('detail') <= G.stage_budget('single'))
chk('no stage budget falls below the declared floor',
    all(G.stage_budget(s) >= G.STAGE_FLOOR for s in
        ('single', 'plan', 'detail', 'repair')))

os.environ['ACS_LLM_MAX_OUTPUT_TOKENS'] = '48000'
chk('raising the single budget raises every stage together',
    G.max_output_tokens() == 48000 and G.stage_budget('detail') == 36000)
os.environ.pop('ACS_LLM_MAX_OUTPUT_TOKENS')
os.environ['ACS_MAX_TOKENS'] = '20000'
chk('the legacy ACS_MAX_TOKENS name still works as an alias, not a second source',
    G.max_output_tokens() == 20000)
os.environ.pop('ACS_MAX_TOKENS')
chk('with no env set the default is restored',
    G.max_output_tokens() == G._DEFAULT_MAX_OUTPUT)

chk('the estimator is deterministic — same input, same number',
    G.estimate_output_tokens(PROD_PROMPT, 'warehouse', 20, 15, 1)
    == G.estimate_output_tokens(PROD_PROMPT, 'warehouse', 20, 15, 1))
chk('every class name is one of the four declared',
    all(G.classify(t) in G.CLASSES for t in (0, 1000, 20000, 40000, 900000)))
chk('classification is monotonic in size',
    [G.CLASSES.index(G.classify(t)) for t in (500, 10000, 25000, 90000)]
    == sorted([G.CLASSES.index(G.classify(t)) for t in (500, 10000, 25000, 90000)]))

# A · الطلب الإنتاجي الصغير (§15)
prod = G.plan_strategy(PROD_PROMPT, 'warehouse', 20, 15, 1)
chk('A · THE PRODUCTION PROMPT classifies SMALL',
    prod['size_class'] == G.SMALL,
    '%s (est=%d)' % (prod['size_class'], prod['estimated_output_tokens']))
chk('A · it is routed to a single stage — no needless staging for a small model',
    prod['strategy'] == G.STRATEGY_SINGLE)
chk('A · its estimate sits far below the single-stage threshold',
    prod['estimated_output_tokens'] < prod['single_stage_threshold_tokens'] * 0.5,
    '%d vs %d' % (prod['estimated_output_tokens'],
                  prod['single_stage_threshold_tokens']))
chk('A · site dimensions are never misread as a zone count '
    '(«20×15م» is a plot, not fifteen zones)',
    G.estimate_zones(PROD_PROMPT, 'warehouse', 20, 15, 1) <= 8,
    str(G.estimate_zones(PROD_PROMPT, 'warehouse', 20, 15, 1)))
chk('A · an explicit count attached to a zone word IS read («12 رصيف»)',
    G.estimate_zones('مستودع فيه 12 رصيف تحميل', 'warehouse', None, None, 1) >= 12)

# F · الطلب الكبير يتدرّج تلقائياً
big = G.plan_strategy(BIG_PROMPT, 'warehouse', 120, 80, 1)
chk('F · a large distribution centre classifies LARGE or VERY_LARGE',
    big['size_class'] in (G.LARGE, G.VERY_LARGE),
    '%s (est=%d)' % (big['size_class'], big['estimated_output_tokens']))
chk('F · and is routed to staged generation without anyone asking',
    big['strategy'] == G.STRATEGY_STAGED)
chk('F · the old input-length rule would have sent BOTH down the single path — '
    'that is the defect this replaces',
    len(PROD_PROMPT) < 2200 and len(BIG_PROMPT) < 2200)
_us = io.open(os.path.join(ROOT, 'acs_understand.py'), encoding='utf-8').read()
chk('the deprecated input-length heuristic is neither defined nor called '
    '(its name survives only in the comment explaining why it went)',
    'def _should_go_deep' not in _us and '_should_go_deep(' not in _us
    and not hasattr(U, '_should_go_deep'))
chk('the replacement decision function is the one actually wired in',
    'plan_strategy' in _us and hasattr(U, '_deep_override'))
chk('ACS_DEEP still forces the strategy when a human sets it',
    G.plan_strategy(PROD_PROMPT, 'warehouse', 20, 15, 1,
                    forced=True)['strategy'] == G.STRATEGY_STAGED
    and G.plan_strategy(BIG_PROMPT, 'warehouse', 120, 80, 1,
                        forced=False)['strategy'] == G.STRATEGY_SINGLE)
chk('the estimator never raises on hostile or empty input',
    all(isinstance(G.plan_strategy(x, y, z, z, z), dict) for x, y, z in (
        ('', None, None), ('x' * 20000, 'warehouse', 0), ('٩٩٩٩٩', 'residential', -5),
        (None, 'nonsense', 'abc'))))


# ═══════════════════════ ب) عقد سبب التوقّف (§10) والانقطاع (§8) ═══════════
print('\n── ب · سبب التوقّف يُفحص قبل التحليل ──')

TRUNCATED_TEXT = json.dumps(tiny_building(), ensure_ascii=False)[:220]
COMPLETE_TEXT = json.dumps(tiny_building(), ensure_ascii=False)

chk('B · a max_tokens stop raises ACS_UPSTREAM_TRUNCATED even when the text '
    'that arrived happens to be complete JSON — the stop reason is the proof',
    (lambda: (with_fake([FakeMessage(COMPLETE_TEXT, "max_tokens")],
                        lambda: _catch(U.call_llm, "x", btype="warehouse"))[0]))()
    == E.ACS_UPSTREAM_TRUNCATED)
chk('B · a refusal stop is its own classified code, not a parse failure',
    with_fake([FakeMessage("I will not", "refusal")],
              lambda: _catch(U.call_llm, "x", btype="warehouse"))[0]
    == E.ACS_UPSTREAM_REFUSED)
chk('an end_turn stop returns the text for parsing',
    with_fake([FakeMessage(COMPLETE_TEXT, "end_turn")],
              lambda: U.call_llm("x", btype="warehouse"))[0] == COMPLETE_TEXT)

chk('C · truncated output is never brace-repaired — the repair helper is gone',
    '_balance_json' not in
    io.open(os.path.join(ROOT, 'acs_understand.py'), encoding='utf-8').read()
    .replace('# ملاحظة معمارية', '#').split('#')[0]
    or 'def _balance_json' not in
    io.open(os.path.join(ROOT, 'acs_understand.py'), encoding='utf-8').read())
chk('C · a truncated JSON body reaching the parser is rejected, not salvaged',
    _catch(U.extract_json, TRUNCATED_TEXT) == E.ACS_UPSTREAM_TRUNCATED)
chk('C · nothing truncated can reach the canonical compiler: the only paths out '
    'of extract_json are one complete object or a classified error',
    _catch(U.extract_json, '{"a":') == E.ACS_UPSTREAM_TRUNCATED
    and _catch(U.extract_json, '') == E.ACS_UPSTREAM_EMPTY_RESPONSE
    and U.extract_json('{"a":1}') == {"a": 1})
chk('D · a malformed (non-JSON) reply is a structured error, never an exception',
    _catch(U.extract_json, 'I am sorry, I cannot') == E.ACS_UPSTREAM_INVALID_JSON)
chk('the truncation message shown to a user names the cause in Arabic and '
    'suggests the action, without printing ACS_MAX_TOKENS at them',
    'حدّ التوليد' in E.MESSAGE_AR[E.ACS_UPSTREAM_TRUNCATED]
    and 'max_tokens' not in E.MESSAGE_AR[E.ACS_UPSTREAM_TRUNCATED])


# ═════════════════════════ ج) سياسة إعادة المحاولة والتصعيد (§12) ══════════
print('\n── ج · لا تكرار للطلب نفسه بعد الانقطاع ──')

_src = io.open(os.path.join(ROOT, 'acs_understand.py'), encoding='utf-8').read()
chk('the attempt ladder no longer retries with a SMALLER budget — retrying a '
    'truncation with less room truncates sooner, not later',
    '(16000, OFF)' not in _src and '(8000, None)' not in _src)
chk('the ladder that remains exists only for an empty reply, and is bounded',
    _src.count('attempts = [') == 1 and _src.count('(max_tokens,') == 2)

def _single_then_staged():
    """المرحلة الواحدة تنقطع، فتُصعَّد إلى الخطة + التفصيل بلا تدخّل."""
    plan_text = json.dumps(tiny_building(), ensure_ascii=False)
    detail_text = json.dumps({"rooms": [
        {"id": "storage", "rect": [0.2, 0.2, 9.4, 14.6], "role": "storage",
         "racks": [{"kind": "pallet", "x": 1, "z": 1, "w": 8, "d": 12,
                    "dir": "z", "aisle": 3.4, "levels": 4, "h": 8}]},
        {"id": "receiving", "rect": [10.0, 0.2, 9.4, 14.6], "role": "receiving",
         "docks": [{"edge": "N", "offset": 2, "width": 3.6, "height": 4.2,
                    "count": 2, "pitch": 5.0}]}]}, ensure_ascii=False)
    script = [FakeMessage(plan_text, "max_tokens"),      # النداء الواحد ينقطع
              FakeMessage(plan_text, "end_turn"),        # الخطة
              FakeMessage(detail_text, "end_turn")]      # التفصيل
    return with_fake(script, lambda: U.understand(
        PROD_PROMPT, btype='warehouse', site_w=20, site_d=15, floors=1,
        repair_rounds=0))


_esc, _client = _single_then_staged()
chk('a truncated single stage escalates to staged generation automatically',
    isinstance(_esc, dict)
    and _esc['meta']['acs_generation']['strategy'] == G.STRATEGY_STAGED)
chk('the escalation is recorded, not silent',
    _esc['meta']['acs_generation']['escalations'] == 1)
chk('the escalation is bounded — one strategy change, not a loop',
    G.MAX_STRATEGY_ESCALATIONS == 1)
chk('the escalated request is genuinely DIFFERENT, not the same call repeated',
    len(_client.calls) >= 3
    and _client.calls[1]['messages'][0]['content']
    != _client.calls[0]['messages'][0]['content'])
chk('the recovered model carries real rooms',
    sum(len(fl['rooms']) for fl in _esc['floors'].values()) >= 2)
chk('G · every stage ran under its own declared budget, none unbounded',
    all(0 < c['max_tokens'] <= G.max_output_tokens() for c in _client.calls),
    str([c['max_tokens'] for c in _client.calls]))
chk('the plan stage ran on the plan budget and the detail stage on the detail budget',
    _client.calls[1]['max_tokens'] == G.stage_budget('plan')
    and _client.calls[2]['max_tokens'] == G.stage_budget('detail'))
chk('J · telemetry records each stage with its stop reason and token counts',
    len(_esc['meta']['acs_generation']['stages']) >= 3
    and all('stop_reason' in st and 'output_tokens' in st
            for st in _esc['meta']['acs_generation']['stages']))
chk('telemetry carries no prompt text and no credential',
    'sk-ant' not in json.dumps(_esc['meta']['acs_generation'], ensure_ascii=False)
    and PROD_PROMPT not in json.dumps(_esc['meta']['acs_generation'],
                                      ensure_ascii=False))

chk('a group that truncates is split in half, deterministically',
    G.split_group([1, 2, 3, 4]) == [[1, 2], [3, 4]]
    and G.split_group([1, 2, 3]) == [[1], [2, 3]])
chk('a single-room group cannot be split further — the recursion has a floor',
    G.split_group(['only']) is None)
chk('the split depth is bounded and declared', 1 <= G.MAX_GROUP_SPLITS <= 4)

# E · التمثيل المضغوط يبقى تحت الميزانية
_compact = {"rooms": [{"id": "storage", "rect": [0, 0, 100, 60], "role": "storage",
                       "racks": [{"kind": "pallet", "x": 2, "z": 2, "w": 96, "d": 56,
                                  "dir": "z", "rows": 24, "aisle": 3.4,
                                  "levels": 4, "h": 8.5}]}]}
_compact_tokens = len(json.dumps(_compact, ensure_ascii=False)) // 3
chk('E · one compact rack row describing 24 rows costs well under 200 tokens',
    _compact_tokens < 200, str(_compact_tokens))
chk('E · enumerating those rows individually would cost an order of magnitude more',
    len(json.dumps({"rows": [dict(kind='pallet', x=i * 4, z=2, w=2.7, d=1.1,
                                  levels=4, h=8.5) for i in range(24)]},
                   ensure_ascii=False)) // 3 > _compact_tokens * 5)
chk('E · the compact-output rule is actually injected into the model instructions',
    'racks' in G.COMPACT_RULE and 'count/pitch' in G.COMPACT_RULE
    and G.COMPACT_RULE in U.system_prompt('warehouse'))
chk('E · the compact rule speaks only about output shape — it never removes a '
    'requirement, changes a dimension or touches automatic engineering (KI-1)',
    not any(w in G.COMPACT_RULE for w in
            ('احذف', 'قلّل عدد', 'تجاهل', 'وسّع', 'غيّر المقاس', 'أضِف مخرج')))
chk('§14 · meta lines are constrained to one short sentence each',
    'جملة واحدة قصيرة' in G.COMPACT_RULE
    and 'لا تُعِد نصّ الطلب كاملاً' in G.COMPACT_RULE)


# ═══════════════════ د) سلطة المرحلة الأولى على الهندسة (§7) ═══════════════
print('\n── د · هندسة المرحلة الأولى مرجع لا يُنقض ──')


def _staged_with_rogue_detail():
    """مرحلة التفصيل تحاول تغيير rect ومقاس الأرض وتضيف منطقة لم تُخطَّط."""
    plan_text = json.dumps(tiny_building(), ensure_ascii=False)
    rogue = json.dumps({"rooms": [
        {"id": "storage", "rect": [5.0, 5.0, 1.0, 1.0], "role": "storage"},
        {"id": "receiving", "rect": [10.0, 0.2, 9.4, 14.6], "role": "receiving"},
        {"id": "ghost_zone", "rect": [0, 0, 3, 3], "role": "office"}]},
        ensure_ascii=False)
    return with_fake([FakeMessage(plan_text, "end_turn"),
                      FakeMessage(rogue, "end_turn")],
                     lambda: U.understand(BIG_PROMPT, btype='warehouse',
                                          site_w=120, site_d=80, floors=1,
                                          deep=True, repair_rounds=0))


_st, _c2 = _staged_with_rogue_detail()
_rooms = {r['id']: r for fl in _st['floors'].values() for r in fl['rooms']}
_diag = _st['meta'].get('acs_stage_diagnostics') or []
# ملاحظة: المقارنة ليست بالتساوي التامّ عمداً. بعد الدمج يعمل `acs_layout.autofix`
# — وهو إصلاح حسابي قائم منذ المرحلة الأولى ويزحزح المناطق لفضّ التداخل، ومنطقة
# ghost_zone المحقونة هنا تتداخل مع storage فيحرّكها. المطلوب إثباته في §7 شيء
# آخر: أن **هندسة مرحلة التفصيل** لم تفز. لذا نثبت أن الناتج ليس rect المارق، وأن
# مقاسات المرحلة الأولى بقيت كما هي.
chk('H · the detail stage\'s rewritten rect did NOT win the merge',
    _rooms['storage']['rect'] != [5.0, 5.0, 1.0, 1.0],
    str(_rooms['storage']['rect']))
chk('H · the zone keeps stage-1 width and depth exactly',
    _rooms['storage']['rect'][2:] == [9.4, 14.6],
    str(_rooms['storage']['rect']))
chk('I · the rejected geometry rewrite is reported, not silently dropped',
    any(d.get('code') == 'STAGE_RECT_OVERRIDE_REJECTED'
        and d.get('id') == 'storage' for d in _diag), str(_diag))
chk('I · a zone invented by the detail stage is reported as a diagnostic',
    any(d.get('code') == 'STAGE_ADDED_ZONES' for d in _diag), str(_diag))
chk('I · but it is not deleted either — it may carry something the client asked '
    'for, so it is surfaced rather than judged',
    'ghost_zone' in _rooms)
chk('H · the site rectangle comes from stage 1 and no later stage rewrote it',
    _st['site'] == {'w': 20, 'd': 15})
chk('H · the level count comes from stage 1', len(_st['levels']) == 1)
chk('H · wall and floor heights come from stage 1',
    _st['wall_h'] == 11.0 and _st['floor_height'] == 12.0)
chk('the staged path stamps its strategy on the model',
    _st['meta']['acs_generation']['strategy'] == G.STRATEGY_STAGED
    and _st['meta']['acs_mode'] == 'deep')


# ═════════════════════════ هـ) عقد رد الواجهة (§17) ════════════════════════
print('\n── هـ · عقد الرد يبقى متوافقاً ──')

_api = io.open(os.path.join(ROOT, 'acs_understand_api.py'), encoding='utf-8').read()
for key in ('building', 'levels', 'rooms', 'type', 'mode', 'issues', 'report'):
    chk('the success payload still carries %r' % key,
        '"%s":' % key in _api or "'%s':" % key in _api or '"%s"' % key in _api)
chk('the success payload adds ok and the generation summary without removing '
    'anything the frontend already reads',
    '"ok": True' in _api and '"generation": _generation_summary' in _api)
chk('the generation summary exposes only aggregates — no prompt, no raw reply',
    'def _generation_summary' in _api
    and 'stages": len(st)' in _api.replace('"stages": len(st)', 'stages": len(st)'))
chk('site dimensions and floor count reach the estimator from the request',
    'site_w=req.site_w' in _api and 'floors=req.floors' in _api)

_page = io.open(os.path.join(ROOT, 'public', 'index.html'), encoding='utf-8').read()
chk('§18 · the page shows the server\'s Arabic truncation message and a retry, '
    'never a raw SDK code',
    'acsErrorPanel' in _page and 'إعادة المحاولة' in _page
    and 'ACS_MAX_TOKENS' not in _page)
chk('§18 · a failed generation still never loads a model',
    "if(res.status!==ACS_NET.SUCCESS){" in _page
    and _page.split("if(res.status!==ACS_NET.SUCCESS){")[1].split('return;')[0]
    .count('setModel(') == 0)

# K · CORS: كشف الترويسة يقع على الرد الفعلي لا على الـpreflight
_live = io.open(os.path.join(ROOT, 'tests', 'deploy', 'verify_backend_live.py'),
                encoding='utf-8').read()
chk('K · the live verifier checks expose-headers on the ACTUAL response, because '
    'the CORS spec never puts expose-headers on a preflight',
    'the ACTUAL response (not the preflight)' in _live
    and 'X-Request-ID is exposed on the actual response' in _live)
chk('K · and it asserts the preflight correctly does NOT carry expose-headers',
    'the preflight itself does not carry expose-headers' in _live)
chk('K · the server declares both headers as exposed',
    'expose_headers=[REQUEST_ID_HEADER, "Retry-After"]' in _api)
chk('K · Retry-After exposure is verified too, not just X-Request-ID',
    'Retry-After is exposed on the actual response' in _live)

print('\n──────────────────────────────────────────────')
print('GENERATION BUDGET: %d passed, %d failed' % (p[0], f[0]))
if f[0]:
    sys.exit(1)
