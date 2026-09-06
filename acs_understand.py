# -*- coding: utf-8 -*-
# =============================================================================
# acs_understand.py  --  ACS Understanding Layer (LLM)  وصف طبيعي → Building JSON
# محرّك الفهم: يحوّل كرّاسة/وصف مبنى بلغة طبيعية (عربي/إنجليزي) إلى نموذج ACS
# المنظّم (Building JSON) الذي يبنيه المترجم acs_compiler.py إلى 3D.
#
# يستخدم Claude عبر Anthropic Messages API. اضبط:
#   export ANTHROPIC_API_KEY=sk-ant-...
#   export ACS_LLM_MODEL=claude-...        (راجع docs.claude.com لأحدث معرّف)
#
# التشغيل:
#   python3 acs_understand.py وصف.txt  out.json         # من ملف نصّي
#   python3 acs_understand.py --pdf كراسة.pdf out.json   # من PDF (يستخرج النص)
# ثم:  python3 acs_compiler.py out.json model.gltf
# =============================================================================

import os
import re
import sys
import json
import time
import threading

import acs_api_errors as E                     # عقد الأخطاء الموحّد (رموز + تصنيف)
import acs_generation as G                     # ميزانية المخرج واستراتيجية التوليد
import acs_plan_chunks as PC                   # عقد الخطّة المحدود والتقطيع (KI-24)
import acs_logging as LOGGING                  # سجلّ إنتاج منظَّم (F-18) — قناة التليمتري
import acs_provider as PROV                    # حلّ المزوّد: اسم/مفتاح/عنوان/نموذج

# سجلّ هذه الوحدة. كل حدث سطر JSON واحد بحقول معلنة، والحجب بالاسم يمنع
# دخول وصف الزائر أو المفتاح أو الرد الخام إلى السجلّ.
LOG = LOGGING.StructuredLogger(service="ACS Understanding Engine")

# ---------------------------------------------------------------------------
# 1) مخطّط البيانات المختصر (يُحقن في التعليمات)
# ---------------------------------------------------------------------------
try:
    import acs_programs as _programs           # سجل البرامج — المصدر الوحيد للحقيقة
    _INDUSTRIAL = _programs.INDUSTRIAL
except Exception:                              # احتياط: يبقى الملف صالحاً منفرداً
    _programs = None
    _INDUSTRIAL = {"warehouse", "industrial", "factory", "logistics"}


def _is_industrial(bt):
    return str(bt or "").lower() in _INDUSTRIAL


SCHEMA_BRIEF = r"""
Building JSON (كل الأبعاد بالمتر):
{
  "meta": {"name": str, "city": str, "north": "-Z"},
  "site": {"w": float,  // عرض الأرض شرق-غرب (محور X)
           "d": float}, // عمق الأرض شمال-جنوب (محور Z؛ z=0 = الواجهة الشمالية)
  "floor_height": float, "wall_h": float, "wall_t": float,
  "levels": [ {"index": int, "name": str, "template": str} ],  // index 0 = الأسفل
  "floors": { "<template>": { "rooms": [ Room ] } }
}
Room = {
  "id": str,                 // معرّف إنجليزي فريد (majlis, master_bed ...)
  "rect": [x, z, w, d],      // ركن أدنى (x,z) + عرض w على X + عمق d على Z
  "wall_h": float?,          // اختياري (سور السطح مثلاً 1.1)
  "wall_color":   "#RRGGBB"?,   // لون/دهان جدران هذه الغرفة وحدها (اختياري)
  "floor_color":  "#RRGGBB"?,   // لون أرضية هذه الغرفة (اختياري)
  "ceiling_color":"#RRGGBB"?,   // لون سقف هذه الغرفة (اختياري)
  "doors":   [ {"id":str?,"edge":"N|S|E|W","offset":float,"width":float,"height":float,"material":"wood|oak|glass"?,"color":"#RRGGBB"?} ],
  "windows": [ {"id":str?,"edge":"N|S|E|W","offset":float,"width":float,"sill":float,"height":float} ],
  "points":  [ {"type": PointType, "x":float, "z":float, "height":float?} ],  // x,z داخل الغرفة من ركنها
  "furniture":[ {"name":str,"x":float,"z":float,"w":float,"d":float,"h":float,"mat":"furn|furn_soft|counter|tv"} ],
  "objects": [ {"kind":str,"name":str?,"x":float,"z":float,"y":float?,
                "w":float?,"d":float?,"h":float?,"rot":deg?,"color":"#RRGGBB"?,
                "count":int?,"pitch":float?,"dir":"x|z"?} ]
}

**"objects" — أي شيء يذكره العميل يُبنى هنا، ولا يُسقَط بند أبداً.**
kind معروف (يُبنى بمجسّم مناسب): person · worker · visitor · engineer · child ·
  robot · amr · cobot · forklift · reachtruck · car · van · truck · trailer ·
  stairs(درج) · elevator(مصعد) · column(عمود) · railing · barrier ·
  tree · palm · plant · planter · sofa · armchair · bed · bed_single · table ·
  dining · desk · chair · wardrobe · cabinet · fridge · oven · washer · sink ·
  toilet · bath · counter · tv · rug · curtain · shelf · pallet · box · crate · sign
ويقبل الأسماء العربية مباشرةً (عامل، روبوت، رافعة شوكية، سيارة، درج، مصعد، عمود،
شجرة، نخلة، كنبة، سرير، طاولة، ثلاثة كراسي…).
**أي كائن غير موجود في القائمة**: اكتبه بـkind باسمه كما ذكره العميل مع w/d/h تقديرية —
يُبنى بمجسّم بأبعاده ويُسجَّل في التقرير. لا تتجاهل أي عنصر طلبه العميل بحجّة عدم وجود نوع له.
التكرار: "count" مع "pitch" و"dir" يكرّر العنصر (٦ عمال بتباعد ٢م، ١٢ سيارة في الموقف…).
PointType ∈ outlet(فيش 40سم) · switch(مفتاح 120سم) · network(RJ45) · usb · tv(شاشة) · ev ·
            light(نجفة/سقف) · spot(سبوت) · camera(كاميرا) · ac(تكييف) · vent · smoke(دخان) · sprinkler(رشاش) · exit
"""

# ---------------------------------------------------------------------------
# 1-ب) امتداد المخطّط للمباني الصناعية/اللوجستية — عناصر مضغوطة
#      سطر واحد هنا يولّد مئات القطع في العارض، فلا ينقطع مخرج النموذج.
# ---------------------------------------------------------------------------
SCHEMA_INDUSTRIAL = r"""
امتداد إلزامي للمستودعات/المصانع — استخدم هذه الحقول بدل تعداد آلاف القطع يدوياً:

Room يقبل إضافةً لما سبق:
  "role": نوع المنطقة الوظيفي — receiving | crossdock | qc | storage | shelf | bin |
          picking | wave | zone_pick | robot | packing | labeling | consolidation |
          sorting | shipping | dispatch | office | admin | it | maintenance | staff |
          circulation | aisle | safety
  "walls": "none"   ← الافتراضي لمناطق التشغيل: المنطقة تُحدَّد بدهان أرضي ملوّن لا بجدران
           "low"(1.1م حاجز) | "half"(1.8م) | "glass"(زجاج للمكاتب المطلّة) | "full"(جدار كامل)
  "racks":    [ {"kind":"pallet|shelf|bin|flow|mezz|cage","x":,"z":,"w":,"d":,
                 "dir":"x|z","rows":int?,"aisle":float,"levels":int,"h":float} ]
              ← صف رفوف متكرّر تلقائياً عبر كامل w×d. لا تكتب كل رفّ على حدة أبداً.
  "lanes":    [ {"kind":"forklift|pedestrian|amr|one_way|conveyor|zone|fire",
                 "x":,"z":,"w":,"d":,"dir":"x|z","arrow":bool?,"reverse":bool?,"h":float?} ]
              ← دهان أرضي + أسهم اتجاه؛ و conveyor يبني سيراً ناقلاً بقوائم وحواجز وإيقاف طوارئ.
  "stations": [ {"kind":"pack|inspect|label|qa|sort|void|desk|charger|locker|wrap",
                 "x":,"z":,"count":int,"pitch":float,"dir":"x|z"} ]
              ← صف محطات متكرّر (طاولة + شاشة + طابعة حسب النوع).
  "docks":    [ {"edge":"N|S|E|W","offset":,"width":3.6,"height":4.2,"count":int,"pitch":float} ]
              ← أرصفة تحميل: فتحة + باب منزلق + لوح تسوية + مصدّات.

PointType إضافية (معدات): scanner · printer · scale · monitor · ptl(pick-to-light) · charger ·
  robot(AMR) · forklift · palletjack · cage · pallet · diverter · chute · bin · server · locker ·
  extinguisher · hydrant · eyewash · assembly(نقطة تجمّع) · gate(بوابة أمنية) · estop · sign(لوحة منطقة)

قاعدة الغلاف: أضِف منطقة id="envelope" برُكن [0,0,site.w,site.d] و"walls":"full" وارتفاع
المستودع الصافي — هي جدران المبنى الخارجية، ولا تُحسب متداخلة مع المناطق داخلها.
"""



# ---------------------------------------------------------------------------
# 2) قواعد المعرفة (جداول الأبواب/النوافذ الافتراضية — كود سعودي شائع)
# ---------------------------------------------------------------------------
KNOWLEDGE = r"""
قواعد التخطيط (استنتج مواضع معقولة عندما يعطي الوصف المقاسات فقط):
- نظام الإحداثيات: X شرق (العرض)، Z جنوب (العمق)، z=0 الواجهة الشمالية. المتر وحدة القياس.
- ابقَ ضمن مسطح البناء (site). لا تسمح بأي تداخل بين مستطيلات الغرف.
- توزيع منطقي: غرف الاستقبال (مجلس/صالة) على الواجهة الشمالية بنوافذ N (إطلالة الشارع)؛
  غرف النوم في العمق الجنوبي بنوافذ S؛ المطبخ قرب الصالة؛ الحمامات/دورات المياه داخلية مجمّعة بلا نوافذ خارجية أو بنافذة صغيرة؛
  ممر (corridor) يربط الغرف؛ البلكونة على واجهة خارجية.
- الغرف الملامسة لمحيط المبنى فقط لها نوافذ خارجية.

عروض الأبواب الافتراضية (جدول الأبواب):
  مدخل عمارة زجاج 2.4 (مصراعان) · باب شقة 1.0 خشب · غرف داخلية 0.9 · حمامات 0.8 · مطبخ 0.9 (خشب+زجاج) ·
  بلكونة 1.6 (زجاج منزلق) · خادمة 0.8 · درج هروب 1.0 معدني · غرف خدمات 0.9 · مصعد 0.8. الارتفاع 2.1 (مداخل 2.4).
  كل غرفة تحصل على باب واحد على الأقل نحو الممر أو الحيّز المجاور.

النوافذ الافتراضية (جدول النوافذ) [width,height,sill]:
  مجلس/صالة 1.6×2.0 sill 0.9 · غرف نوم 1.4×1.5 sill 1.0 · مطبخ 1.0×1.2 sill 1.1 ·
  حمامات 0.6×0.6 sill 1.6 · خادمة 0.9×1.0 sill 0.9 · منور 0.9×0.6 sill 1.4.

نقاط الكهرباء/الإنارة (وزّعها بالأعداد المذكورة في الوصف؛ وإلا استخدم كثافة معقولة):
  فيش على 40سم موزّعة حول الجدران · مفتاح عند الباب 120سم · شبكة/تلفزيون على جدار واحد ·
  إنارة: نجفة مركزية + سبوتات سقفية · كاميرا في زاوية قرب السقف · تكييف فوق النافذة/بالسقف ·
  كاشف دخان بالسقف وسط الغرفة · رشاش حريق في الممرات والمخازن · Exit عند مخارج الطوارئ.

الألوان والتشطيبات (مهم):
- عندما يُذكر لون لغرفة أو لجدار غرفة، ضَع الحقل على تلك الغرفة وحدها: "wall_color" للجدران،
  "floor_color" للأرضية، "ceiling_color" للسقف، و"color" داخل كائن الباب للباب. لا تغيّر غرفاً أخرى.
- إن كان اللون مطلوباً في دور واحد فقط وكان قالب الدور مشتركاً بين عدّة أدوار (levels تحمل نفس template)،
  فانسخ القالب باسم جديد (مثال "typical__F2") واربطه بذلك الـlevel وحده، ثم لوّن الغرفة فيه.
- جدول الألوان بالاسم → HEX: أخضر #22c55e · زيتوني #6b8e23 · أحمر #e11d48 · عنابي #7b1f2b ·
  وردي #f472b6 · برتقالي #f97316 · أزرق #2563eb · سماوي #38bdf8 · كحلي #1e293b · تركوازي #14b8a6 ·
  أصفر #facc15 · ذهبي #d4af37 · بني #6b4423 · بيج #e3d5b8 · كريمي #f2e8d5 · رمادي #8b8f96 ·
  أبيض #f5f5f2 · أسود #17181b · بنفسجي #8b5cf6 · ترابي #a89078.
  «فاتح» = خلط اللون بالأبيض، و«غامق/داكن» = تغميقه.
- بلا لون مذكور: لا تضع هذه الحقول إطلاقاً (يبقى التشطيب الافتراضي).

المستويات: إن ذُكر "قبو" أضِف level parking؛ "أرضي" لوبي/حارس/خدمات/شقق؛ "أدوار متكررة N" كرّر قالب typical؛ "سطح" خزانات/شمسية/تكييف/مخرج درج.

**إلزامي — تفتيت الغرف**: لا تُنشئ حيّزاً عاماً واحداً كبيراً باسم مثل apt_a أو unit أو "شقة".
كل شقة تُفكَّك إلى غرفها الفعلية المسمّاة، كلٌّ بمستطيلها الخاص وجدرانها:
majlis, living, kitchen, master_bed, bed2, bed3, master_bath, guest_wc, corridor, laundry, maid, balcony …
أي حيّز مغلق تتجاوز مساحته 30 م² يجب أن يكون غرفة وظيفية واحدة (مجلس/صالة/موقف)، لا شقة كاملة.
الغرف المتجاورة تتلامس ولا تتداخل؛ اجمعها بحيث تملأ مسطح الدور بشكل منطقي.
"""

# ---------------------------------------------------------------------------
# 3) مثال مرجعي مختصر (few-shot) — يعلّم الصيغة الدقيقة
# ---------------------------------------------------------------------------
FEWSHOT_IN = "المجلس 4.5×5.0م على الواجهة الشمالية، باب خشب، نافذة تطل شمالاً، 6 أفياش، منفذا USB، نقطة شبكة، شاشة 85 بوصة، نجفة، حساس دخان، مخرج تكييف."
FEWSHOT_OUT = {
  "id": "majlis", "rect": [0.3, 0.3, 4.5, 5.0],
  "doors": [{"edge": "E", "offset": 2.5, "width": 0.9, "height": 2.1, "material": "wood"}],
  "windows": [{"edge": "N", "offset": 2.25, "width": 1.6, "sill": 0.9, "height": 2.0}],
  "points": [
    {"type": "outlet", "x": 1.1, "z": 4.75}, {"type": "outlet", "x": 2.25, "z": 4.75},
    {"type": "outlet", "x": 3.4, "z": 4.75}, {"type": "outlet", "x": 4.25, "z": 1.7},
    {"type": "outlet", "x": 4.25, "z": 3.3}, {"type": "outlet", "x": 4.25, "z": 2.5},
    {"type": "usb", "x": 1.5, "z": 0.35}, {"type": "usb", "x": 3.0, "z": 0.35},
    {"type": "network", "x": 0.3, "z": 2.5}, {"type": "tv", "x": 2.25, "z": 0.3},
    {"type": "light", "x": 2.25, "z": 2.5}, {"type": "smoke", "x": 2.25, "z": 2.5},
    {"type": "ac", "x": 2.25, "z": 0.2}
  ],
  "furniture": [
    {"name": "sofa", "x": 2.25, "z": 0.6, "w": 3.6, "d": 0.8, "h": 0.8, "mat": "furn_soft"},
    {"name": "table", "x": 2.25, "z": 2.5, "w": 1.4, "d": 0.9, "h": 0.4, "mat": "furn"}
  ]
}

KNOWLEDGE_WAREHOUSE = r"""
قواعد المستودعات ومراكز التوزيع (تجارة إلكترونية) — التزم بها حرفياً:

تدفّق العمل (يحدّد ترتيب المناطق من الشمال z=0 إلى الجنوب z=D):
  استلام/أرصفة واردة → تفريغ سريع → تجهيز وارد مرقّم → فحص جودة → (كروس دوك للسريع) →
  تخزين (بالتات/أرفف/صناديق) → التقاط (دفعات/موجات/مناطق/روبوت) → تغليف → ملصقات وتحقّق →
  فرز آلي → تجميع طلبات → تجهيز شحن حسب الناقل → أرصفة صادرة.
اجعل المسافة بين الاستلام والشحن أقصر ما يمكن، وضع الأصناف سريعة الدوران (Class A) أقرب لمنطقة الالتقاط.

أبعاد قياسية إلزامية:
- رصيف تحميل: عرض 3.5–3.7 م، ارتفاع باب 4.0–4.5 م، تباعد بين مراكز الأرصفة 4.0–6.5 م،
  ومساحة مناورة أمامه ≥ 12 م.
- ممر رافعة شوكية بين رفوف البالتات ≥ 3.4 م (اتجاهان ≥ 4.5 م). ممر خدمة أرفف يدوي ≥ 1.2 م.
- ممر مشاة ≥ 1.2 م بخطوط صفراء ومفصول عن مسار الرافعات والروبوت.
- مسار AMR ≥ 1.0 م للاتجاه الواحد، مع محطات شحن على طرف المسار.
- رفّ بالتات: عمق 1.1 م، طول الخانة 2.7 م، 4 مستويات، ارتفاع 8–9 م.
- رفّ متوسط: عمق 0.6 م، خانة 1.2 م، 5 مستويات، ارتفاع 2.4 م.
- صناديق صغيرة: عمق 0.45 م، خانة 0.9 م، 6 مستويات، ارتفاع 2.1 م.
- محطة تغليف: 1.8×0.9 م وتباعد 2.6 م، مع ميزان وطابعة ملصقات وشاشة تحقّق.
- سير ناقل: عرض 0.8–1.0 م على ارتفاع 0.85–0.95 م، حواجز جانبية، وإيقاف طوارئ كل ≤ 12 م.
- ارتفاع صافٍ للمستودع 10–14 م (اجعل wall_h بهذا المدى، والمكاتب الداخلية 3.0–3.2 م).

سلامة وأمن (إلزامي):
- طفاية لكل ≈1000 م² وعلى كل مخرج، وحنفيات حريق على المحيط، ورشاشات سقفية في كل منطقة تخزين.
- ≥ 4 مخارج طوارئ موزّعة، ونقطة تجمّع (assembly) خارج مسارات الرافعات.
- كاميرات على كل رصيف وعلى الممرات الرئيسية والبوابات (لا تقل عن 6).
- بوابات أمنية (gate) عند مداخل المشاة، وعين غسيل (eyewash) في الصيانة ومناطق المواد.

الترميز اللوني الصناعي (استخدمه في wall_color للمناطق أو اتركه ليُشتقّ من role):
  تخزين أزرق · التقاط أخضر · تغليف برتقالي · استلام تركوازي · فرز/شحن بنفسجي ·
  سلامة أحمر · ممرات صفراء · إدارة رمادي.

المكاتب والخدمات: مكتب مراقبة المخزون بزجاج مطلّ على الصالة، غرفة سيرفرات WMS مغلقة بتكييف
مستقل، غرفة اجتماعات، استراحة موظفين، خزائن ملابس، وورشة صيانة — كلها "walls":"full" أو
"glass" وارتفاع 3.0–3.2 م، ولها أبواب وأفياش ومفاتيح وإنارة وكاشف دخان كالغرف العادية.

**مهم جداً**: مناطق التشغيل تُكتب "walls":"none" — المستودع صالة واحدة مفتوحة تحت سقف واحد،
والمناطق تُميَّز بدهان أرضي ولوحات معلّقة، لا بجدران بين كل منطقة وأخرى.
**ولا تعدّد القطع يدوياً**: صفّ رفوف واحد في "racks" يولّد مئات الأرفف والبالتات تلقائياً.
"""


# ---------------------------------------------------------------------------
# قاعدة الأولوية: وصف العميل يعلو على كل قالب أو افتراض
# ---------------------------------------------------------------------------
STRICT_RULE = (
    "\n\n**وضع الالتزام الحرفي مفعّل**: لا تُضِف أي عنصر أو منطقة أو نقطة لم يذكرها العميل "
    "صراحةً — ولا حتى لضرورة كود. اترك meta.added فارغة. نفّذ وصفه كما هو بالضبط، لا أكثر ولا أقل."
)

PRIORITY_RULE = r"""
════════ قاعدة الأولوية (تعلو على كل ما يليها) ════════
١. وصف العميل هو المرجع. نفّذ **كل** ما ذكره حرفياً: الأسماء، الأعداد، المقاسات،
   الارتفاعات، المواقع، الاتجاهات، الألوان، والتفاصيل مهما دقّت. لا تحذف بنداً ولا
   تختصره ولا تستبدله بما تراه «أفضل».
٢. ما لم يذكره العميل فقط تملأه بالقواعد المرجعية أدناه. القواعد **افتراضات**، لا أوامر.
٣. إذا خالف وصف العميل أي قاعدة مرجعية (مقاس، ترتيب، توزيع، تسمية) — **اتّبع العميل**،
   ولو بدا غير معتاد. لا تفرض تخطيطاً جاهزاً ولا ترتيباً نموذجياً على وصفٍ يخالفه.
٤. إن طلب عنصراً لا يوجد له حقل في المخطّط، فمثّله بأقرب تركيب متاح — وأوّلها
   "objects" التي تقبل **أي** كائن باسمه وأبعاده (بشر، روبوتات، مركبات، أثاث،
   درج، مصعد، أعمدة، نباتات، معدات، أي شيء) — أو منطقة/rack/lane/station/point،
   وسمِّه باسمه الذي ذكره العميل، وسجّله في meta.extras مع شرح كيف مُثِّل.
   العناصر الحيّة (أشخاص/عمال/زوّار) تُضاف حين يطلب العميل مشهداً مأهولاً أو مقياساً بشرياً.
٥. لا تضف من عندك مناطق كبيرة لم تُطلب. الإضافات المسموحة فقط: ما يستلزمه الكود
   (سلامة، مخارج، إنارة) أو ما يجعل ما طلبه العميل قابلاً للتشغيل — واذكرها في meta.added.
٦. قبل الإخراج: راجع الوصف بنداً بنداً وتأكد أن لكل بند ما يقابله في النموذج.
════════════════════════════════════════════════════════

"""

REQUIREMENTS_RULE = r"""
أضِف في meta الحقول التالية لإثبات التغطية:
  "requirements": [ {"req":"نصّ البند كما ورد في طلب العميل (مختصراً)",
                     "where":"معرّف المنطقة/العنصر الذي نُفِّذ فيه",
                     "how":"جملة قصيرة: كيف نُفِّذ"} ]   ← بنداً بنداً لكل ما طلبه
  "extras":  [ "عنصر طلبه العميل ومُثِّل بطريقة بديلة — مع الشرح" ]
  "added":   [ "ما أضفته أنت ولم يطلبه العميل صراحةً (إعداد افتراضي/استنتاج)" ]
لا تترك requirements فارغة، ولا تُدرج فيها بنداً لم تنفّذه فعلاً.

قواعد صدق المصدر (إلزامية):
- لا تُدرج في requirements إلا ما ذكره العميل فعلاً في نصّه. أي شيء أضفته من
  عندك أو استنتجته يذهب إلى added — لا إلى requirements.
- الأعداد في requirements يجب أن تطابق ما ذكره العميل حرفياً. إن أضاف النموذج
  مستويات تقنية (سطح/بيت درج) فلا تَعُدّها ضمن أدوار طلبها العميل.
- ممنوع منعاً باتاً ادّعاء مطابقة أي كود أو معيار: لا تكتب "وفق الكود" ولا
  "متطلّب كود" ولا "مطابق للكود" ولا ما يعادلها بأي لغة. لا يوجد محرّك تحقّق
  أكواد في هذه المرحلة. صِف ما أضفته وصفاً محايداً: "إعداد افتراضي" أو
  "أضافه النظام".
- لا تدّعِ ربطاً رأسياً أو اتصالاً هندسياً (مثل "يربط الطوابق") — النموذج يمثّل
  الدرج/المصعد بصرياً فقط ولا يتحقّق من الاتصال بين المستويات.
"""


def detect_type(text, explicit=None):
    """يكشف برنامج المبنى من الوصف — يفوّض إلى سجل البرامج (المصدر الوحيد للحقيقة).

    نفس المنطق الموزون السابق (قاطعة=٣، محتملة=١، وحارس يمنع اعتبار "رفوف تخزين"
    في وصف سكني مستودعاً)، لكنه صار مشتركاً حرفياً مع الواجهة عبر acs_programs.json
    فلا تتناقض نتيجة المسار المحلي مع مسار الذكاء.
    """
    return _programs.detect_type(text, explicit)


def system_prompt(btype="residential"):
    industrial = _is_industrial(btype)
    schema = SCHEMA_BRIEF + (SCHEMA_INDUSTRIAL if industrial else "") + G.COMPACT_RULE
    know = KNOWLEDGE_WAREHOUSE if industrial else KNOWLEDGE
    head = ("أنت مهندس مستودعات ولوجستيات خبير (Warehouse / Fulfilment Center Design). "
            if industrial else
            "أنت مهندس معماري وكهربائي خبير. ")
    tail = ("أخرج كائن Building JSON كاملاً واحداً يغطي **كل** بند ورد في الطلب بلا استثناء. "
            "قبل الإخراج راجع الطلب بنداً بنداً وتأكد أن لكل بند منطقة أو عنصراً يقابله. "
            if industrial else
            "أخرج كائن Building JSON كاملاً واحداً يغطي كل الأدوار والغرف الموصوفة. ")
    ex = ""
    if not industrial:
        ex = ("مثال لغرفة واحدة:\nالمدخل:\n" + FEWSHOT_IN + "\nالمخرج:\n" +
              json.dumps(FEWSHOT_OUT, ensure_ascii=False) + "\n\n")
    return (
        head + "مهمتك تحويل وصف مبنى بلغة طبيعية (عربي/إنجليزي) "
        "إلى نموذج ACS المنظّم بصيغة JSON فقط — بلا أي شرح أو نص خارج الـJSON.\n\n"
        + PRIORITY_RULE +
        "التزم حرفياً بهذا المخطّط (صيغة الإخراج):\n" + schema + "\n"
        "قواعد مرجعية — تُستخدم فقط لما لم يذكره العميل:\n" + know + "\n" + ex + tail +
        "استنتج المواضع والاتجاهات عند غياب الإحداثيات. تأكد ألا تتداخل المناطق وأن تبقى ضمن الأرض. "
        "أعِد JSON صالحاً فقط."
    )

# ---------------------------------------------------------------------------
# 4) استخراج نص PDF (اختياري)
# ---------------------------------------------------------------------------
def pdf_to_text(path):
    try:
        import pypdf
        r = pypdf.PdfReader(path)
        return "\n".join((p.extract_text() or "") for p in r.pages)
    except Exception as e:
        raise RuntimeError("تعذّر قراءة PDF (ثبّت pypdf): %s" % e)

# ---------------------------------------------------------------------------
# 5) نداء Claude
# ---------------------------------------------------------------------------
def clean_key(raw):
    """يستخرج مفتاح API نظيفاً حتى لو التصق به نص/فراغ عند اللصق (سبب شائع لخطأ 400)."""
    raw = (raw or "").strip().strip('"').strip("'")
    m = re.search(r"sk-ant-[A-Za-z0-9_\-]+", raw)
    return m.group(0) if m else raw


MAX_DESC_CHARS = int(os.environ.get("ACS_MAX_DESC", "120000"))   # حد طول الوصف المُرسل


# ---------------------------------------------------------------------------
# تعليمات قراءة المخططات المرسومة (رؤية)
# ---------------------------------------------------------------------------
def vision_prompt(btype="residential"):
    return (
        "أنت مهندس معماري خبير في قراءة المخططات التنفيذية (Floor Plans).\n"
        "ستُعطى صورة/صور مخطط معماري (قد تكون بالعربية). حوّلها إلى نموذج ACS المنظّم "
        "بصيغة JSON فقط — بلا أي شرح أو نص خارج الـJSON.\n\n"
        "طريقة القراءة:\n"
        "- اقرأ أسماء الغرف المكتوبة على المخطط (مجلس رجال، صالة، طعام، مطبخ، غرفة نوم، "
        "دورة مياه، مصلّى، غرفة السائق، مصعد، درج، موقف…) واجعل كل غرفة عنصر Room مستقلاً.\n"
        "- استنتج أبعاد كل غرفة من نِسَبها على المخطط ومن أرقام الأبعاد إن ظهرت. "
        "إن أُعطيت أبعاد الأرض في الطلب فاجعل مجموع التخطيط متوافقاً معها.\n"
        "- حافظ على المواضع النسبية كما في المخطط: ما في أعلى الصورة يكون z صغيراً (شمال)، "
        "وما في أسفلها z كبيراً (جنوب)؛ اليسار x صغير واليمين x كبير.\n"
        "- ارسم الأبواب حيث تظهر فتحات/أقواس الأبواب، والنوافذ على الجدران الخارجية.\n"
        "- أضِف نقاط الكهرباء والإنارة والتكييف والسلامة بكثافة معقولة لكل غرفة "
        "(فيش 40سم، مفتاح 120سم، إنارة سقفية، كاشف دخان، مخرج تكييف).\n"
        "- أضِف أثاثاً مبسّطاً مطابقاً لما يظهر في المخطط (كنب، سرير، طاولة طعام، مطبخ).\n"
        "- لا تدع الغرف تتداخل، وابقِ الجميع داخل حدود site.\n\n"
        + PRIORITY_RULE + "\nالتزم حرفياً بهذا المخطّط:\n"
        + SCHEMA_BRIEF + (SCHEMA_INDUSTRIAL if _is_industrial(btype) else "")
        + "\n" + (KNOWLEDGE_WAREHOUSE if _is_industrial(btype) else KNOWLEDGE) + "\n"
        "أعِد كائن Building JSON واحداً كاملاً وصالحاً فقط."
    )


def understand_images(images, site_w=None, site_d=None, floors=None, model=None,
                      repair_rounds=None, notes="", strict=False, btype=None,
                      request_id=None):
    """images: قائمة (media_type, base64). يقرأ المخطط بالرؤية ويعيد Building JSON مُتحقَّقاً."""
    import acs_validate as V
    hint = []
    if site_w and site_d:
        hint.append("أبعاد الأرض/مسطح البناء: العرض %.1f م (محور X) × العمق %.1f م (محور Z)."
                    % (float(site_w), float(site_d)))
    if floors:
        hint.append("عدد الأدوار المطلوبة: %d (كرّر قالب الدور مع levels)." % int(floors))
    if notes:
        hint.append("ملاحظات المستخدم: " + notes)
    if strict:
        hint.append(STRICT_RULE)

    content = [{"type": "image",
                "source": {"type": "base64", "media_type": mt, "data": b64}}
               for (mt, b64) in images]
    content.append({"type": "text", "text":
                    "اقرأ هذا المخطط وحوّله إلى Building JSON كامل.\n" + "\n".join(hint)})

    vt = detect_type((notes or "") + " " + " ".join(hint), btype)
    building = validate(extract_json(call_llm(None, model=model, content=content,
                                             btype=vt, stage="vision",
                                             request_id=request_id)))
    building.setdefault("meta", {}).setdefault("type", vt)
    if strict:
        building["meta"]["strict"] = True
    issues, stats = V.validate_building(building)
    print("[ACS-VISION] قراءة المخطط: %d مخالفة · %s" % (len(issues), stats))

        # F-01: المصلِح الحسابي لم يعد يكتب في النموذج. ما كان يغيّره صار
        # اقتراحاً يُحسَب في طبقة الـAPI عبر acs_engineering_authority.plan
        # ويُعرَض على المستخدم. النموذج المعروض هنا هو مخرج التوليد نفسه.
    print("[ACS-VISION] لا إصلاح تلقائي: %d مخالفة تُعرَض ولا تُصلَّح صامتاً" % len(issues))

    building.setdefault("meta", {})["acs_issues"] = len(issues)
    building["meta"].setdefault("source", "plan-image")
    return building


# ---------------------------------------------------------------------------
# تليمتري التوليد (F-13) — أرقام وتصنيفات فقط، لا نصّ زائر ولا مفتاح ولا رد خام
# ---------------------------------------------------------------------------
def _env_str(name, default=""):
    v = os.environ.get(name, default)
    return v.strip() if isinstance(v, str) else default


def _env_float(name, default=None):
    """رقم من البيئة بلا انفجار عند القيمة الفارغة أو التالفة.

    القيمة الفارغة في ملفّ البيئة تعني «غير مضبوط»، لا صفراً: `float("")` يرفع
    ValueError عند الإقلاع — وهو صنف عطل قائم في المستودع لا نزيد عليه."""
    raw = _env_str(name, "")
    if not raw:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _env_int(name, default):
    raw = _env_str(name, "")
    if not raw:
        return default
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default


def _env_flag(name, default=False):
    raw = _env_str(name, "").lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _estimated_cost_usd(input_tokens, output_tokens):
    """تكلفة تقديرية **فقط** إن صرّح المشغّل بالتسعيرة في البيئة.

    التسعيرة تتغيّر بتغيّر عقد المزوّد والنموذج. رقمٌ نخترعه من جدول مدفون يظهر
    في لوحة التكلفة كأنه فاتورة. غياب الضبط ⇒ غياب الحقل: لا صفر ولا تخمين."""
    pin = _env_float("ACS_PRICE_INPUT_PER_MTOK", None)
    pout = _env_float("ACS_PRICE_OUTPUT_PER_MTOK", None)
    if pin is None and pout is None:
        return None
    cost = (((input_tokens or 0) / 1000000.0) * (pin or 0.0)
            + ((output_tokens or 0) / 1000000.0) * (pout or 0.0))
    return round(cost, 6)


def _emit_generation_telemetry(tel, stage, model=None, strategy=None,
                               request_id=None, duration_ms=None, success=True,
                               error_code=None, upstream_class=None,
                               chunk_index=None, chunk_count=None):
    """حدث تليمتري واحد لكل نداء توليد — نجح أو فشل (F-13).

    القناة `StructuredLogger.generation` تُسقط أي حقل غير معلن، فلا يمرّ منها
    وصف زائر ولا مفتاح ولا رد خام حتى لو مُرِّر خطأً."""
    try:
        tel = tel or {}
        stop = tel.get("stop_reason")
        attempts = tel.get("attempts")
        fields = {
            "strategy": strategy,
            "model": tel.get("model") or model,
            "stages": stage,
            "input_tokens": tel.get("input_tokens"),
            "output_tokens": tel.get("output_tokens"),
            "stop_reason": stop,
            "max_output_tokens": tel.get("max_output_tokens"),
            "duration_ms": duration_ms,
            "retries": (max(0, int(attempts) - 1)
                        if isinstance(attempts, int) else 0),
            # W2-E: بلوغ السقف بلوغٌ له سواء وصل نصفُ JSON أم لم يصل حرف.
            "truncated": bool(stop == "max_tokens"
                              or error_code in E.CEILING_CODES),
            "upstream_class": upstream_class,
            "success": bool(success),
            "error_code": error_code,
            # F-50 · ما يجعل رفض المزوّد قابلاً للتشخيص من السجلّ وحده.
            "sdk_version": tel.get("sdk_version"),
            "transport": tel.get("transport"),
            "thinking_sent": tel.get("thinking_sent"),
            "requested_max_tokens": tel.get("requested_max_tokens"),
            "budget_clamped": tel.get("budget_clamped"),
            "provider_error_type": tel.get("provider_error_type"),
            "provider_param": tel.get("provider_param"),
            "provider_limit": tel.get("provider_limit"),
            "provider_detail": tel.get("provider_detail"),
            # هجرة المزوّد — بلا هذه الحقول لا يفرّق سجلّ الإنتاج بين عطلٍ عند
            # deepseek وعطلٍ عند anthropic، ولا يُعرف هل ردّ البديل أم الأساسي.
            "provider": tel.get("provider"),
            "provider_model": tel.get("provider_model"),
            "provider_base_host": tel.get("provider_base_host"),
            "fallback_attempted": tel.get("fallback_attempted"),
            "fallback_provider": tel.get("fallback_provider"),
            "fallback_reason": tel.get("fallback_reason"),
            "fallback_success": tel.get("fallback_success"),
            # W2-A · محاسبة الرد: أين ذهبت رموز المخرجات فعلاً.
            "output_chars": tel.get("output_chars"),
            "chars_per_output_token": tel.get("chars_per_output_token"),
            "content_blocks": tel.get("content_blocks"),
            "content_block_types": tel.get("content_block_types"),
            "text_blocks": tel.get("text_blocks"),
            "nontext_blocks": tel.get("nontext_blocks"),
            "text_block_chars": tel.get("text_block_chars"),
            "cache_read_input_tokens": tel.get("cache_read_input_tokens"),
            "cache_creation_input_tokens": tel.get("cache_creation_input_tokens"),
            "reasoning_tokens": tel.get("reasoning_tokens"),
            # W2-D · محاولةٌ لم تُرسَل لأنها مطابقة بايتاً لما أُرسل.
            "retry_skipped_reason": tel.get("retry_skipped_reason"),
            "retries_skipped": tel.get("retries_skipped"),
            # W2-E · بأيّ دلالةٍ حُكِم على الرد. بلا هذا الحقل يبقى
            # «لماذا صُعِّد هذا الطلب ولم يُصعَّد ذاك؟» بلا جواب.
            "response_semantic": tel.get("response_semantic"),
        }
        # KI-24/F-38: موضع الشريحة في السلسلة. بلا هذين الحقلين لا يمكن نسب
        # عطلٍ إلى شريحة بعينها في سجلّ الإنتاج.
        if chunk_index is not None:
            fields["chunk_index"] = int(chunk_index)
        if chunk_count is not None:
            fields["chunk_count"] = int(chunk_count)
        # معرّف الطلب يُمرَّر من المتّصل أو لا يظهر. معرّف مخترَع لا يطابق سجلّ
        # الطلب أسوأ من غيابه: يوهم بربطٍ غير موجود.
        if request_id:
            fields["request_id"] = request_id
        cost = _estimated_cost_usd(tel.get("input_tokens"),
                                   tel.get("output_tokens"))
        if cost is not None:
            fields["estimated_cost_usd"] = cost
        return LOG.generation(**fields)
    except Exception:                     # التليمتري لا يُسقط توليداً ناجحاً
        return None


def call_llm(description, model=None, max_tokens=None, truncate=True, content=None,
             btype=None, user_msg=None, stage="single", telemetry=None,
             request_id=None, strategy=None, chunk_index=None, chunk_count=None):
    """نداء النموذج + حدث تليمتري واحد له مهما كانت النتيجة (F-13).

    التوقيع الأصلي محفوظ حرفياً؛ `request_id` و`strategy` وسيطان اختياريان
    يمرّرهما المتّصل إن كانا لديه. لا يُخترَع معرّف طلب هنا."""
    tel = telemetry if telemetry is not None else {}
    t0 = time.time()

    def _ms():
        return int((time.time() - t0) * 1000)

    try:
        text = _call_llm_impl(description, model=model, max_tokens=max_tokens,
                              truncate=truncate, content=content, btype=btype,
                              user_msg=user_msg, stage=stage, telemetry=tel)
    except E.AcsApiError as err:
        up = err.upstream if isinstance(getattr(err, "upstream", None), dict) else {}
        _emit_generation_telemetry(tel, stage, model=model, strategy=strategy,
                                   request_id=request_id, duration_ms=_ms(),
                                   success=False, error_code=err.code,
                                   upstream_class=(up or {}).get("kind"),
                                   chunk_index=chunk_index,
                                   chunk_count=chunk_count)
        raise
    except Exception as err:                                  # noqa: BLE001
        _emit_generation_telemetry(tel, stage, model=model, strategy=strategy,
                                   request_id=request_id, duration_ms=_ms(),
                                   success=False,
                                   upstream_class=type(err).__name__,
                                   chunk_index=chunk_index,
                                   chunk_count=chunk_count)
        raise
    _emit_generation_telemetry(tel, stage, model=model, strategy=strategy,
                               request_id=request_id, duration_ms=_ms(),
                               success=True, chunk_index=chunk_index,
                               chunk_count=chunk_count)
    return text


def _sdk_version():
    """نسخة anthropic المثبّتة — للتليمتري وحده. لا تُسقط النداء إن غابت."""
    try:
        import anthropic
        v = getattr(anthropic, "__version__", None)
        if v:
            return str(v)
    except Exception:                                             # noqa: BLE001
        pass
    try:
        from importlib import metadata
        return str(metadata.version("anthropic"))
    except Exception:                                             # noqa: BLE001
        return "unknown"


def _sdk_supports(client, param):
    """هل يقبل عميل anthropic المثبَّت هذا الوسيط؟ سؤالٌ يُسأل مرّة قبل النداء.

    F-31: العطل الإنتاجي كان إرسال `thinking` إلى anthropic==0.40 — نسخةٌ لا
    تعرفه، وتوقيعها keyword-only صريح بلا **kwargs. النتيجة TypeError من ربط
    الوسائط، قبل أي بايت شبكة، ثم يُصنَّف «عطل غير مصنّف من مزوّد النموذج».

    الفحص بالاستبطان لا بالنسخة: رقم النسخة يخدع (رزم مُعاد توزيعها، تفريعات،
    وسطاء متوافقون)، أمّا التوقيع فهو ما ستربط به بايثون فعلاً. ووجود
    **kwargs في التوقيع يعني قبولاً غير محدود، فيُعدّ دعماً.
    """
    import inspect
    for name in ("stream", "create"):
        fn = getattr(getattr(client, "messages", None), name, None)
        if fn is None:
            continue
        try:
            sig = inspect.signature(fn)
        except (TypeError, ValueError):                           # noqa: PERF203
            continue                       # لا يمكن استبطانه: جرّب الآخر
        params = sig.parameters
        if param in params:
            return True
        if any(p.kind == inspect.Parameter.VAR_KEYWORD
               for p in params.values()):
            return True
    return False


def _classify_call_error(exc, attempts=None, sdk_version=None,
                         provider="anthropic"):
    """يفصل العطل المحلّي عن عطل المزوّد قبل أي تصنيف upstream.

    F-33: TypeError من ربط الوسائط عطلٌ في تكامل هذا الخادم مع المكتبة — لا
    شأن للمزوّد به، ولم يصل إليه بايت واحد. تصنيفه ACS_UPSTREAM_UNKNOWN كان
    يكذب على المستخدم (502 «عطل من مزوّد النموذج») ويُسمّم قياس أعطال المزوّد
    لدى المشغّل، ويرسل من يبحث عن السبب إلى الجهة الخطأ تماماً.

    الحدّ دقيق: TypeError الصادر عن ربط الوسائط وحده. TypeError من داخل
    الشبكة أو التحليل يبقى على تصنيفه القديم، فلا يتحوّل عطل مزوّد حقيقيّ إلى
    «عطل محلّي» بالخطأ المعاكس.
    """
    if isinstance(exc, E.AcsApiError):
        return exc
    if isinstance(exc, TypeError):
        text = str(exc)
        binding = ("unexpected keyword argument" in text
                   or "required keyword-only argument" in text
                   or "required positional argument" in text
                   or "got multiple values for" in text
                   or "takes no arguments" in text)
        if binding:
            # اسم الوسيط المخالف — معرّف برمجيّ لا محتوى مستخدم، فآمن للسجلّ.
            bad = None
            m = re.search(r"keyword argument '([A-Za-z_][A-Za-z0-9_]*)'", text)
            if m:
                bad = m.group(1)
            return E.AcsApiError(
                E.ACS_INTEGRATION_ERROR,
                upstream={"provider": provider, "kind": "TypeError",
                          "fault": "local_integration",
                          "parameter": bad,
                          "sdk_version": sdk_version or _sdk_version(),
                          "attempts": attempts})
    return E.classify_upstream(exc, attempts=attempts, provider=provider)


#: نوع الكتلة يُنقّى إلى معرّف خالص. اسم النوع معرّفٌ برمجيّ لا محتوى، لكن
#: التنقية تجعل ذلك خاصيّةً مضمونة لا افتراضاً عن سلوك المزوّد.
_BLOCK_TYPE_RE = re.compile(r"[^A-Za-z0-9_]")


def _block_type(block):
    """اسم نوع كتلة الرد — معرّفٌ وحده، ولا شيء من محتواها."""
    raw = getattr(block, "type", None)
    if not isinstance(raw, str) or not raw:
        raw = type(block).__name__
    return _BLOCK_TYPE_RE.sub("", str(raw))[:32] or "unknown"


def _block_accounting(blocks):
    """W2-A: أين ذهبت رموز المخرجات — بالبنية لا بالتخمين.

    السؤال الذي لا يستطيع السجلّ الحاليّ الإجابة عنه: نداءٌ يُبلَّغ عنه
    `out_tokens=16000` و`out_chars=0`. أين ذهبت الستّة عشر ألفاً؟ الاستخراج
    القائم `getattr(b, "text", None)` يُبقي الكتل النصّية وحدها ويُسقط ما عداها
    **صامتاً** — وتلك الكتل استهلكت الميزانية. فإن كان المزوّد يعيد كتل تفكير
    أو كتلاً بلا نصّ، فهذا الفراغ في المحاسبة هو ما يخفيها. وإن لم يكن يفعل،
    فالقياس يقول ذلك أيضاً — وهو ما يمنع بناء W2-C على فرضية.

    يُسجَّل: العدد، والأنواع بأسمائها، وكم كتلةً نصّية وكم غير نصّية، وأطوال
    النصّ لكل كتلة. لا يُسجَّل: نصّ، ولا محتوى كتلة، ولا توجيه، ولا نموذج
    مبنى، ولا مفتاح.
    """
    counts = {}
    lens = []
    text_blocks = 0
    for b in blocks or ():
        t = _block_type(b)
        counts[t] = counts.get(t, 0) + 1
        tx = getattr(b, "text", None)
        if isinstance(tx, str):
            text_blocks += 1
            lens.append(len(tx))
        else:
            lens.append(0)
    total = len(blocks or ())
    return {"content_blocks": total,
            "content_block_types": ",".join(
                "%s:%d" % (k, v) for k, v in sorted(counts.items())) or "none",
            "text_blocks": text_blocks,
            "nontext_blocks": max(0, total - text_blocks),
            "text_block_chars": ",".join(str(n) for n in lens[:24]) or "none"}


def _usage_extras(usage):
    """حقول الاستخدام الإضافية إن أعلنها المزوّد — أرقامٌ وحدها.

    `input_tokens` غير موثوق به بذاته: مقيس حيّاً أن محاولةً مطابقةً بايتاً
    للأولى أُبلغ عنها 60 رمز مدخل مقابل 5692. تسجيل حقول الكاش يفصل «ذاكرة
    مؤقّتة أصابت» عن «محاسبة غير موثوقة» بدل الخلط بينهما.
    """
    out = {}
    for name in ("cache_read_input_tokens", "cache_creation_input_tokens",
                 "reasoning_tokens"):
        v = getattr(usage, name, None)
        if isinstance(v, int):
            out[name] = v
    return out


def _request_fingerprint(kw):
    """بصمة مستقرّة لطلبٍ واحد — للمقارنة وحدها، لا للتسجيل.

    W2-D: تُبنى من الوسائط كما ستُرسَل بالضبط. لا تُطبَع ولا تُسجَّل ولا تخرج
    من العملية: وظيفتها الوحيدة أن تُجيب «هل أُرسل هذا الطلب حرفياً من قبل؟»
    قبل دفع ميزانيةٍ ثانية عليه.
    """
    import hashlib
    try:
        canon = json.dumps(kw, sort_keys=True, ensure_ascii=False, default=repr)
    except Exception:                                             # noqa: BLE001
        canon = repr(sorted(kw.items(), key=lambda kv: str(kv[0])))
    return hashlib.sha256(canon.encode("utf-8", "replace")).hexdigest()


def _sdk_accepts_base_url():
    """هل يقبل بانِ العميل المثبَّت الوسيط base_url؟ استبطانٌ لا رقم نسخة.

    هذا هو المفصل كلّه في هجرة المزوّد: deepseek يُنادى عبر مكتبة anthropic
    نفسها بتبديل نقطة النهاية وحدها. مكتبةٌ لا تقبل base_url ستتجاهله بصمت لو
    مُرِّر عبر **kwargs غير موجودة، أو ترفع TypeError — وفي الحالتين ينتهي
    الطلب إلى api.anthropic.com بمفتاح deepseek. هذا ليس «تدهوراً لطيفاً»:
    إنه إرسال اعتماد مزوّد إلى مزوّد آخر. لذلك يُفحَص قبل النداء ويُرفض.
    """
    try:
        import anthropic
        import inspect
        sig = inspect.signature(anthropic.Anthropic.__init__)
    except Exception:                                             # noqa: BLE001
        return False
    params = sig.parameters
    if "base_url" in params:
        return True
    return any(p.kind == inspect.Parameter.VAR_KEYWORD
               for p in params.values())


def _build_client(cfg, timeout_s):
    """عميلٌ مضبوطٌ على نقطة نهاية المزوّد المحلول. لا يخمّن ولا يتساهل."""
    import anthropic
    if not cfg.ok:
        # ضبطٌ ناقص: عطل مشغّل معلن باسم المتغيّر، لا عطل منبع.
        if cfg.state == PROV.MISSING_BASE_URL:
            raise E.AcsApiError(
                E.ACS_INTEGRATION_ERROR,
                "المزوّد %s يحتاج نقطة نهاية صريحة ولم تُضبط (%s)."
                % (cfg.provider, ", ".join(cfg.missing)),
                upstream={"provider": cfg.provider, "kind": "missing_base_url",
                          "fault": "local_integration"})
        raise E.AcsApiError(E.ACS_UPSTREAM_NOT_CONFIGURED)

    kw = {"api_key": cfg.api_key}
    if cfg.base_url:
        if not _sdk_accepts_base_url():
            # لا رجوع صامت إلى نقطة النهاية الافتراضية: انظر _sdk_accepts_base_url.
            raise E.AcsApiError(
                E.ACS_INTEGRATION_ERROR,
                "المكتبة المثبّتة لا تقبل base_url، فلا يمكن مناداة المزوّد %s."
                % cfg.provider,
                upstream={"provider": cfg.provider, "kind": "base_url_unsupported",
                          "fault": "local_integration",
                          "parameter": "base_url",
                          "sdk_version": _sdk_version()})
        kw["base_url"] = cfg.base_url
    try:
        return anthropic.Anthropic(timeout=timeout_s, **kw)
    except TypeError:                      # مكتبة قديمة بلا وسيط timeout
        return anthropic.Anthropic(**kw)


def _call_llm_impl(description, model=None, max_tokens=None, truncate=True,
                   content=None, btype=None, user_msg=None, stage="single",
                   telemetry=None):
    """content اختياري: قائمة بلوكات (نص/صور) للرؤية. وإلا يُرسل description كنص.

    `telemetry` قاموس اختياري يُملأ بالقياسات الآمنة (لا نصّ الزائر ولا مفتاح):
    stage · stop_reason · input_tokens · output_tokens · max_output_tokens ·
    completion_chars · attempts · complete.
    """
    tel = telemetry if telemetry is not None else {}
    tel.setdefault("stage", stage)
    tel.setdefault("complete", False)
    try:
        import anthropic                                          # noqa: F401
    except Exception:
        raise E.AcsApiError(E.ACS_NOT_CONFIGURED, "مكتبة anthropic غير مثبّتة على الخادم.")

    sdk_ver = _sdk_version()
    tel["sdk_version"] = sdk_ver               # يفرّق عطل التكامل عن عطل المزوّد
    max_tokens = int(max_tokens or G.stage_budget("single"))
    model_override = (model or "").strip() or None

    # مهلة صريحة على نداء المنبع: بلا هذا يعلّق العامل حتى تقتله البوّابة
    # فيرى العميل انقطاعاً بلا جسد رد — وهو ما لا يمكن تصنيفه ولا عرضه.
    timeout_s = float(os.environ.get("ACS_UPSTREAM_TIMEOUT_S", "600"))

    if content is not None:
        msgs = [{"role": "user", "content": content}]
        sys_p = vision_prompt(btype or "residential")
    else:
        desc = description.strip()
        # لا نقتطع أبداً في جولة الإصلاح (truncate=False) لئلا يصل النموذج مبتوراً
        if truncate and len(desc) > MAX_DESC_CHARS:
            desc = desc[:MAX_DESC_CHARS] + "\n\n[تم اقتطاع بقية الوصف]"
        default_msg = ("حوّل طلب العميل التالي إلى Building JSON كامل ينفّذ **كل** بند فيه.\n"
                       + REQUIREMENTS_RULE + "\nطلب العميل:\n\n")
        msgs = [{"role": "user", "content": (default_msg if user_msg is None else user_msg) + desc}]
        sys_p = system_prompt(btype or detect_type(desc))

    def _attempt(cfg):
        """نداءٌ كاملٌ على مزوّدٍ واحد محلول. يعيد النصّ أو يرفع AcsApiError.

        كلّ ما بداخله كان جسد `_call_llm_impl` قبل هجرة المزوّد، حرفياً: سلّم
        المحاولتين، وعقد سبب التوقّف، والتليمتري. المتغيّر الوحيد أن المفتاح
        والنموذج ونقطة النهاية تأتي من `cfg` بدل قراءة المحيط هنا.
        """
        model = model_override or cfg.model
        client = _build_client(cfg, timeout_s)
        # ما سيُسجَّل: أيّ مزوّد ونموذج ومضيف خدم هذا النداء فعلاً.
        tel["model"] = model
        tel["provider"] = cfg.provider
        tel["provider_model"] = model
        tel["provider_base_host"] = cfg.base_host

        supports_thinking = _sdk_supports(client, "thinking")

        def _build_kw(mt, thinking):
            """وسائط الطلب — تُبنى مرّةً، فتُبصَم ويُنادى بها الشيءُ نفسه.

            W2-D: كانت تُبنى داخل `_call` فلا يمكن مقارنة طلبين قبل إرسالهما.
            فصلُها يجعل «هل هذا الطلب مطابقٌ لطلبٍ أُرسل؟» سؤالاً يُجاب قبل الدفع.

            F-31: `thinking` يُرسَل **فقط** إذا كانت النسخة المثبّتة تعرفه.
            anthropic==0.40 المثبّتة في requirements.txt لا تعرفه إطلاقاً — أُضيف
            لاحقاً — وتوقيعها keyword-only صريح بلا **kwargs، فكان إرساله يرفع
            TypeError من ربط الوسائط في بايثون قبل أي اتصال بالشبكة. على نسخة لا
            تعرف «التفكير الموسّع» أصلاً، إغفالُ الوسيط هو بالضبط ما يعنيه
            `{"type": "disabled"}`: لا سلوك يُفقَد.
            """
            kw = dict(model=model, max_tokens=mt, system=sys_p, messages=msgs)
            if thinking is not None and supports_thinking:
                kw["thinking"] = thinking
            return kw

        def _call(kw):
            """ينفّذ وسائط مبنيّة سلفاً. البثّ أوّلاً، وcreate لمكتبة بلا stream."""
            try:
                with client.messages.stream(**kw) as s:
                    return s.get_final_message()
            except AttributeError:
                tel["transport"] = "create"      # F-50: أيّ مسار سلكه النداء
                # F-32: الرجوع إلى create() مقصور على «مكتبة بلا stream()» وحدها.
                # كان TypeError مشمولاً هنا أيضاً، فكان وسيطٌ لا تعرفه المكتبة
                # يُعاد إرساله حرفياً إلى create() فيفشل الفشل نفسه — تكرارٌ مضمون
                # الفشل يمحو أثر السبب. خطأ الوسائط ليس «مكتبة قديمة بلا بثّ»:
                # يُترك ليصنَّف عطلاً محلياً في _classify_call_error.
                return client.messages.create(**kw)

        # سلّم محاولات مقصور على حالة واحدة: رد **بلا نصّ إطلاقاً**، وسببها المعروف
        # أنّ "التفكير الموسّع" ابتلع الميزانية كلّها (stop=max_tokens مع out_chars=0).
        # لا يُستعمل هذا السلّم لعلاج الانقطاع: تكرار الطلب نفسه بميزانية أقلّ يقطع
        # المخرج أبكر لا أمتن. الانقطاع يعالجه تغيير الاستراتيجية في understand().
        OFF = {"type": "disabled"}
        attempts = [
            (max_tokens, OFF),                   # الأفضل: بلا تفكير، سقف كامل
            (max_tokens, None),                  # افتراضي النموذج
        ]

        # §8 إعادة المحاولة محدودة وللأعطال العابرة وحدها. مفتاح مرفوض أو نموذج غير
        # موجود لا يُصلحه التكرار: يستهلك دقائق ورصيداً ثم يعطي الرسالة نفسها متأخّرة.
        text = ""; stop = "?"; last_err = None; tried = 0
        backoff = float(os.environ.get("ACS_UPSTREAM_BACKOFF_S", "2"))
        # W2-D: بصمات الطلبات المُرسَلة فعلاً في هذا النداء. سلّم المحاولات وُضع
        # ليغيّر **إعداد التفكير** وحده؛ ومع anthropic==0.40 لا يُرسَل `thinking`
        # إطلاقاً (KI-23/F-31)، فالمحاولتان تبنيان الوسائط نفسها حرفياً. إعادةُ
        # إرسال طلبٍ مطابقٍ بايتاً لطلبٍ فشل هي دفعُ ميزانيةٍ كاملةٍ ثانيةً على
        # نتيجةٍ معروفة سلفاً — مقيس حيّاً: 16000 ثم 16000 رمزاً، ونفس
        # `stop=max_tokens` ونفس `out_chars=0`.
        # القاعدة عامّة لا مخصّصة: تُقارَن البصمة، فإن اختلف الطلب فعلاً — نسخة
        # SDK تعرف `thinking`، أو سقفٌ مختلف — أُرسِل كما كان.
        sent_fingerprints = set()
        for mt, think in attempts:
            tried += 1
            # F-50: يُسجَّل ما **طُلب** قبل النداء. كان max_output_tokens يُملأ بعد
            # نجاح الرد وحده، فسجلُّ الرفض يقول max_output_tokens=null — أي أن
            # أهمّ رقمٍ في تشخيص رفض 400 كان يغيب عن كل نداء فاشل بالضبط.
            tel["requested_max_tokens"] = int(mt)
            tel.setdefault("max_output_tokens", int(mt))
            tel["thinking_sent"] = bool(think is not None and supports_thinking)
            tel["transport"] = cfg.transport
            kw = _build_kw(mt, think)
            fp = _request_fingerprint(kw)
            if fp in sent_fingerprints:
                tel["retry_skipped_reason"] = "identical_request"
                tel["retries_skipped"] = int(tel.get("retries_skipped") or 0) + 1
                print("[ACS-LLM] retry skipped: request is byte-identical to "
                      "one already sent (stage=%s max_tokens=%s thinking=%s "
                      "sdk=%s) — it cannot produce a different result and would "
                      "cost another full budget" % (stage, mt,
                                                    "off" if think else "default",
                                                    sdk_ver))
                tried -= 1                    # لم يُرسَل شيء: لا تُحتسَب محاولة
                continue
            sent_fingerprints.add(fp)
            try:
                msg = _call(kw)
            except Exception as e:
                # F-33: العطل المحلّي يُفصَل عن عطل المزوّد هنا، لا بعد أن يصير 502.
                err = _classify_call_error(e, attempts=tried,
                                           sdk_version=sdk_ver,
                                           provider=cfg.provider)
                last_err = err
                up = err.upstream if isinstance(err.upstream, dict) else {}
                # F-50: حقول المزوّد الآمنة تُنقَل إلى التليمتري، فيصل السجلّ سببُ
                # الرفض لا اسم صنف الاستثناء وحده.
                tel["provider_error_type"] = up.get("error_type")
                tel["provider_param"] = up.get("param") or up.get("parameter")
                tel["provider_limit"] = up.get("limit")
                tel["provider_detail"] = up.get("detail")
                print("[ACS-LLM] call failed (stage=%s provider=%s host=%s "
                      "model=%s max_tokens=%s thinking=%s sdk=%s transport=%s)"
                      " -> %s%s%s%s"
                      % (stage, cfg.provider, cfg.base_host or "default", model,
                         mt, "off" if think else "default", sdk_ver,
                         tel.get("transport"), err.code,
                         (" param=%s" % tel["provider_param"])
                         if tel.get("provider_param") else "",
                         (" provider_limit=%s" % up.get("limit"))
                         if up.get("limit") else "",
                         (" detail=%s" % up.get("detail"))
                         if up.get("detail") else ""))
                if not err.retryable:
                    raise err                 # عطل دائم: أعلِنه فوراً بلا تكرار
                if tried < len(attempts) and backoff > 0:
                    time.sleep(min(backoff * tried, 15))
                continue

            blocks = list(msg.content or [])
            parts = [getattr(b, "text", None) for b in blocks]
            text = "".join(p for p in parts if p)
            stop = getattr(msg, "stop_reason", "?")
            usage = getattr(msg, "usage", None)
            # W2-A: محاسبة كتل الرد — أنواعٌ وأعدادٌ وأطوال، لا محتوى.
            acct = _block_accounting(blocks)
            tel.update({"stop_reason": stop,
                        "output_tokens": getattr(usage, "output_tokens", None),
                        "input_tokens": getattr(usage, "input_tokens", None),
                        "max_output_tokens": mt,
                        "completion_chars": len(text),
                        "output_chars": len(text),
                        "attempts": tried,
                        "thinking": "off" if think else "default"})
            tel.update(acct)
            tel.update(_usage_extras(usage))
            # النسبة الحاسمة في W2: كم حرفاً مرئياً مقابل كل رمز مخرج. هي التي
            # تقول إن كانت رموزُ المخرج وكيلاً عن حجم JSON أم لا.
            _ot = tel.get("output_tokens")
            tel["chars_per_output_token"] = (
                round(len(text) / float(_ot), 4) if isinstance(_ot, int) and _ot > 0
                else None)
            print("[ACS-LLM] stage=%s provider=%s host=%s model=%s thinking=%s "
                  "max_tokens=%s stop=%s out_chars=%d out_tokens=%s in_tokens=%s "
                  "blocks=%d types=%s text_blocks=%d nontext_blocks=%d "
                  "chars_per_out_token=%s%s"
                  % (stage, cfg.provider, cfg.base_host or "default", model,
                     "off" if think else "default", mt, stop, len(text),
                     tel["output_tokens"], tel["input_tokens"],
                     acct["content_blocks"], acct["content_block_types"],
                     acct["text_blocks"], acct["nontext_blocks"],
                     tel.get("chars_per_output_token"),
                     "".join(" %s=%s" % (k, v)
                             for k, v in sorted(_usage_extras(usage).items()))))

            if text.strip():
                break           # وصل نصّ — الحكم على اكتماله بعد الحلقة
            print("[ACS-LLM] رد بلا نص — أجرّب إعداداً آخر…")

        # ── W2-E · دلالة الرد قبل أي تحليل ───────────────────────────────────
        # كان الحكم هنا ثنائياً: «فيه نصّ» ثمّ فحصُ سبب التوقّف. فردٌّ استهلك
        # ميزانيته كلّها في كتلة تفكير (0 حرف، 16000 رمزاً، stop=max_tokens)
        # كان يُصنَّف EMPTY_RESPONSE — وصفٌ كاذب، ورمزٌ لا يُشطَر ولا يُصعَّد،
        # فينتهي الطلب 502 بلا محاولة تعافٍ واحدة. الدلالة الآن مُشتقّة من
        # محاسبة الكتل (W2-A) بدالّة خالصة مختبَرة على القيم المقيسة حيّاً.
        sem, code = E.classify_response(stop, len(text),
                                        tel.get("text_blocks") or 0,
                                        tel.get("nontext_blocks") or 0)
        tel["response_semantic"] = sem

        # الأسبقيّة كما كانت حرفياً: بلا نصّ مرئي، عطلٌ عابر مصنَّف يعلو أي حكم
        # على شكل الرد. تغييرها هنا كان سيبتلع 529 من محاولةٍ تالية.
        if (sem in (E.RESP_EMPTY, E.RESP_NO_VISIBLE_OUTPUT)
                and isinstance(last_err, E.AcsApiError)):
            raise last_err                # آخر عطل عابر مصنّف: أوضح من العموم
        if sem == E.RESP_EMPTY:
            raise E.AcsApiError(
                code,
                "أعاد النموذج رداً فارغاً في كل المحاولات (آخر stop_reason=%s)." % stop,
                upstream={"provider": cfg.provider, "kind": "empty_text",
                          "attempts": tried})
        if sem == E.RESP_NO_VISIBLE_OUTPUT:
            # ردٌّ وصل وكلّف ميزانيةً كاملة ولم يحمل حرفاً. تمييزه عن «الفارغ»
            # هو ما يجعله دليلَ بلوغ سقفٍ يستدعي الشطر والتصعيد (E.CEILING_CODES).
            print("[ACS-LLM] استُهلكت الميزانية في محتوى غير مرئي — "
                  "blocks=%s types=%s out_tokens=%s out_chars=0 — "
                  "يُعامَل معاملة بلوغ السقف لا معاملة الرد الفارغ."
                  % (tel.get("content_blocks"), tel.get("content_block_types"),
                     tel.get("output_tokens")))
            raise E.AcsApiError(
                code,
                "استهلك النموذج سقف المخرج (%d رمزاً) في محتوى غير مرئي في "
                "المرحلة %s ولم يُعِد نصّاً." % (tel.get("max_output_tokens") or 0,
                                               stage),
                upstream={"provider": cfg.provider, "kind": "no_visible_output",
                          "attempts": tried})

        # ── عقد سبب التوقّف (§10): الحكم قبل التحليل، لا بعده ────────────────
        # سبب التوقّف يثبت الاكتمال من عدمه بذاته. تحليل نصّ يُعرف سلفاً أنه مبتور
        # هدرٌ في أحسن الأحوال، وقبولُ نصفِ نموذجٍ في أسوئها — وهو ما كان يحدث:
        # كان `_balance_json` يغلق الأقواس الناقصة فيمرّ نموذج ناقص إلى المصرِّف.
        if sem == E.RESP_TRUNCATED:
            print("[ACS-LLM] انقطع المخرج عند سقف الرموز — يُطرَح ولا يُحلَّل ولا يُرمَّم.")
            raise E.AcsApiError(
                code,
                "انقطع رد النموذج عند سقف المخرج (%d رمزاً) في المرحلة %s."
                % (tel.get("max_output_tokens") or 0, stage),
                upstream={"provider": cfg.provider, "kind": "max_tokens",
                          "attempts": tried})
        if sem == E.RESP_REFUSED:
            raise E.AcsApiError(code,
                                upstream={"provider": cfg.provider,
                                          "kind": "refusal",
                                          "attempts": tried})
        if stop not in ("end_turn", "stop_sequence", "?", None):
            print("[ACS-LLM] سبب توقّف غير معروف: %r — يُعامَل معاملة المكتمل ثم "
                  "يحكم عليه المحلّل." % stop)
        tel["complete"] = True
        return text

    # ── المزوّد الأساسي، ثم بديلٌ واحدٌ محدود عند سببٍ مسموح وحده ──────────────
    # «محدود» هنا حرفيّة: محاولةٌ واحدة على مزوّدٍ واحد، والبديل نفسه لا يُحوَّل
    # منه إلى ثالث ولا يعود إلى الأوّل. لا حلقة، ولا عودٌ ذاتيّ، ولا تصعيد.
    primary_cfg = PROV.primary()
    tel["fallback_attempted"] = False
    try:
        return _attempt(primary_cfg)
    except E.AcsApiError as err:
        fb = PROV.fallback()
        allowed, reason = PROV.should_fallback(err.code, fb)
        tel["fallback_reason"] = reason
        if not allowed:
            # سببُ الامتناع يُسجَّل أيضاً: «لم يقع تحويل» و«لا بديل مضبوط»
            # خبران مختلفان، وخلطهما يجعل ضبطاً معطّلاً يبدو سياسةً مقصودة.
            raise
        print("[ACS-LLM] provider fallback: %s -> %s (%s, %s)"
              % (primary_cfg.provider, fb.provider, err.code, reason))
        tel["fallback_attempted"] = True
        tel["fallback_provider"] = fb.provider
        tel["fallback_success"] = False
        # التليمتري يُنظَّف من آثار فشل الأساسي حتى لا يُنسب إلى البديل.
        for k in ("provider_error_type", "provider_param", "provider_limit",
                  "provider_detail", "stop_reason", "output_tokens",
                  "input_tokens", "completion_chars"):
            tel.pop(k, None)
        out = _attempt(fb)                 # يرفع بنفسه إن فشل — ولا يُحوَّل ثانيةً
        tel["fallback_success"] = True
        return out


# ملاحظة معمارية (§8): كانت هنا `_balance_json` تغلق الأقواس الناقصة في مخرج
# مقطوع لتُنقذ «ما أمكن». حُذفت عمداً ولا تُعاد: نصفُ نموذجٍ مغلَقٍ بالأقواس يمرّ
# التحقّق البنيوي الخفيف ثم يصل المصرِّف مبتوراً — مبنى بلا مناطق أو بغرف ناقصة
# يُعرَض على المستخدم كأنه ناتج صحيح. المخرج المقطوع يُطرَح، والعلاج تغيير
# الاستراتيجية لا ترميم النصّ.

# ---------------------------------------------------------------------------
# 6) استخراج + تحقّق JSON
# ---------------------------------------------------------------------------
def scan_top_level_json(raw):
    """مسح حتمي واعٍ بالسلاسل لكل كائن JSON **في المستوى الأعلى** وحده.

    لماذا لا `raw.find('{')` مع `raw.rfind('}')`، ولا نمط أقواس نصّي؟ لأن كليهما
    يقتطع من أول قوس إلى آخر قوس فيبتلع ما بين كائنين — فإن أعاد النموذج كائناً
    ثم سطر شرح فيه قوس، صار المقتطع كائنين مُلصقين وانفجر
    `json.JSONDecodeError: Extra data`. هذا بعينه ما أسقط /v1/understand.

    ولماذا لا `raw_decode` من كل `{`؟ لأن الكائن الخارجي إن كان مقطوعاً فشل فكّه،
    فينزلق المؤشّر إلى قوس **داخلي** فيُحسَب كائناً أعلى-مستوى زوراً، فيُقرأ
    مخرج مبتور واحد على أنه عدّة كائنات. نتتبّع العمق بأنفسنا فلا ننزل أبداً.

    يعيد (objects, malformed, truncated):
      objects   : قائمة (start, end, obj) لكل مدى متوازن فُكّ ترميزه بنجاح
      malformed : عدد المديات المتوازنة التي رفضها json (تلف داخلي)
      truncated : True إن انتهى النصّ وقوس أعلى-مستوى ما يزال مفتوحاً
    """
    objects, malformed = [], 0
    depth = 0
    start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(raw):
        if esc:
            esc = False
            continue
        if in_str:
            if ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch in "{[":
            if depth == 0 and ch == "{":
                start = i
            depth += 1
        elif ch in "}]":
            if depth == 0:
                continue                       # قوس إغلاق يتيم في نصّ سردي
            depth -= 1
            if depth == 0 and start >= 0:
                span = raw[start:i + 1]
                try:
                    objects.append((start, i + 1, json.loads(span)))
                except ValueError:
                    malformed += 1
                start = -1
    return objects, malformed, (depth > 0)


RAW_DUMP_DIR_DEFAULT = "acs_raw_dumps"
RAW_DUMP_KEEP_DEFAULT = 5


def raw_dump_enabled():
    """الحفظ الخام اشتراك صريح، ومطفأ افتراضياً — في الإنتاج وغيره.

    الرد الخام هو مخرج النموذج عن وصف الزائر: قد يحمل أسماءه وأرقامه وعنوان
    مشروعه. حفظه على قرص الخادم بلا طلب صريح احتفاظٌ ببيانات لم يأذن بها أحد.
    `ACS_ENV=production` لا يغيّر القاعدة: يبقى مطفأً ما لم يُضبط المتغيّر."""
    return _env_flag("ACS_RAW_DUMP_ENABLED", False)


def raw_dump_status():
    """حالة الحفظ الخام — للفحص والصحّة. لا يعيد مساراً ولا محتوى."""
    return {"enabled": raw_dump_enabled(),
            "env": LOGGING.ENV,
            "keep": max(1, _env_int("ACS_RAW_DUMP_KEEP", RAW_DUMP_KEEP_DEFAULT)),
            "dir_mode": "0o700", "file_mode": "0o600",
            "path_exposed_to_client": False}


def _raw_dump_dir():
    return _env_str("ACS_RAW_DUMP_DIR", "") or RAW_DUMP_DIR_DEFAULT


def _rotate_raw_dumps(directory, keep):
    """يُبقي أحدث `keep` ملفّاً ويحذف ما قبلها — لا نموّ بلا حدّ على القرص."""
    try:
        names = [n for n in os.listdir(directory) if n.startswith("raw_")]
        paths = [os.path.join(directory, n) for n in names]
        paths = [p for p in paths if os.path.isfile(p)]
        paths.sort(key=lambda p: (os.path.getmtime(p), p))
        for old in paths[:max(0, len(paths) - keep)]:
            try:
                os.remove(old)
            except OSError:
                pass
    except OSError:
        pass


def _save_raw(text):
    """يحفظ الرد الخام لتشخيص الخادم — باشتراك صريح وحده.

    مطفأ افتراضياً؛ يكتب في مجلّد مقصور (0o700) بملفّ 0o600 عبر `os.open`،
    ويُبقي عدداً محدوداً من الملفّات. المسار لا يُذكر أبداً في رد العميل ولا
    في السجلّ. التعقيم `E.redact` يبقى مطبَّقاً على المحتوى كما كان."""
    if not raw_dump_enabled():
        return None
    directory = _raw_dump_dir()
    keep = max(1, _env_int("ACS_RAW_DUMP_KEEP", RAW_DUMP_KEEP_DEFAULT))
    try:
        os.makedirs(directory, mode=0o700, exist_ok=True)
        try:
            os.chmod(directory, 0o700)
        except OSError:
            pass
        name = "raw_%s_%s.txt" % (time.strftime("%Y%m%dT%H%M%S", time.gmtime()),
                                  os.urandom(4).hex())
        path = os.path.join(directory, name)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags, 0o600)
        try:
            os.write(fd, E.redact(text).encode("utf-8"))
        finally:
            os.close(fd)
        _rotate_raw_dumps(directory, keep)
        # لا مسار في السجلّ: اسم الملفّ ليس سرّاً لكنه ليس معلومة تشخيص أيضاً.
        LOG.warn("raw_dump_written", stage="extract_json", kept=keep,
                 chars=len(text or ""))
        return path
    except Exception:                                          # noqa: BLE001
        return None


def extract_json(raw):
    """رد النموذج → كائن واحد. أي غموض يُرفَع كخطأ مصنّف، لا كتخمين صامت."""
    text = (raw or "").strip()
    if not text:
        raise E.AcsApiError(E.ACS_UPSTREAM_EMPTY_RESPONSE)

    found, malformed, truncated = scan_top_level_json(text)
    if len(found) > 1:
        first, second = found[0], found[1]
        _save_raw(text)
        print("[ACS-JSON] رد فيه %d كائن أعلى-مستوى؛ الأول %d..%d والتالي عند %d"
              % (len(found), first[0], first[1], second[0]))
        raise E.AcsApiError(
            E.ACS_UPSTREAM_TRAILING_JSON,
            "رد النموذج يحوي أكثر من كائن JSON أعلى-مستوى (الأول ينتهي عند %d "
            "والتالي يبدأ عند %d). لن نخمّن أيّهما النموذج."
            % (first[1], second[0]),
            upstream={"provider": "anthropic", "kind": "trailing_json"})
    if len(found) == 1:
        return found[0][2]

    # لا كائن مكتمل. لا ترميم: مخرج مقطوع نتيجتُه خطأ معلن، لا نموذج ناقص صامت.
    _save_raw(text)
    code = (E.ACS_UPSTREAM_TRUNCATED if (truncated or malformed)
            else E.ACS_UPSTREAM_INVALID_JSON)
    raise E.AcsApiError(
        code, E.MESSAGE_AR[code] + " قصّر الوصف أو ارفع ACS_MAX_TOKENS.",
        upstream={"provider": "anthropic", "kind": "unparsable_response"})

def validate(building):
    """تحقّق بنيوي خفيف + إصلاحات أمان (بلا اعتماد خارجي).

    KI-25/F-41: هنا يُفرَض عقد المستويات. هذه الدالة هي المصبّ الوحيد لكل
    مسارات التوليد (النداء الواحد، الخطّة القديمة، الخطّة المحدودة، الإصلاح،
    الملاحظات)، فوضعُ العقد فيها يعني أن `index` لا يعتمد على طاعة النموذج
    لتوجيهٍ ما. مستوىً بلا index يجعل العارض يبني المبنى عند NaN: هندسةٌ
    موجودة وعدّادٌ صحيح ولا بكسل واحد — وهو عطل KI-25 بالحرف.
    """
    assert isinstance(building.get("site"), dict), "site مفقود"
    building.setdefault("floor_height", 3.2); building.setdefault("wall_h", 3.0); building.setdefault("wall_t", 0.15)
    assert building.get("levels"), "levels مفقود"
    assert building.get("floors"), "floors مفقود"
    for tmpl, fdef in building["floors"].items():
        for r in fdef.get("rooms", []):
            assert "rect" in r and len(r["rect"]) == 4, "غرفة بلا rect صحيح: %s" % r.get("id")
    lv, lv_issues = PC.normalise_levels(building.get("levels"), building.get("floors"))
    if lv:
        building["levels"] = lv
    if lv_issues:
        diag = building.setdefault("meta", {}).setdefault("acs_stage_diagnostics", [])
        for i in lv_issues:
            if i not in diag:
                diag.append(i)
    # Assign identity at admission, before users can reference array positions.
    # This adds metadata only; no dimension/source is invented or reclassified.
    from acs_opening_identity import stabilise_opening_ids
    stabilise_opening_ids(building)
    return building

def call_llm_repair(description, building, issues, model=None,
                    request_id=None, strategy=None):
    """يُعيد النموذج لإصلاح المخالفات المكتشفة (حلقة التحقّق والإصلاح)."""
    import acs_validate as V
    fix_prompt = (
        "هذا نموذج Building JSON أنتجته سابقاً، وبه مخالفات هندسية.\n"
        "أصلحها كلها وأعِد **النموذج الكامل** بصيغة JSON فقط (بلا شرح).\n"
        "حافظ على ما هو صحيح، وعالج الآتي:\n\n"
        + V.format_issues(issues) +
        "\n\nالنموذج الحالي:\n" + json.dumps(building, ensure_ascii=False)
    )
    # سقف أعلى: المخرج المُصلَح بحجم النموذج كاملاً
    mt = G.stage_budget("repair")
    bt = str((building.get("meta") or {}).get("type") or detect_type(description))
    return call_llm(fix_prompt, model=model, max_tokens=mt, truncate=False, btype=bt,
                    user_msg="", stage="repair", request_id=request_id,
                    strategy=strategy)


def apply_notes(building, notes, model=None):
    """ينفّذ ملاحظات المهندس (تعديل/نقل/أبعاد/حذف/إضافة) على النموذج الحالي."""
    import acs_validate as V
    from acs_opening_identity import stabilise_opening_ids
    # Stage a versioned copy before showing an existing model to the provider.
    # The input and its old revisions remain untouched even if the reply fails.
    building = json.loads(json.dumps(building))
    stabilise_opening_ids(building)
    lines = []
    for i, n in enumerate(notes, 1):
        lines.append("%d. [%s] الطبقة: %s · الدور: %s · الغرفة: %s\n   المطلوب: %s"
                     % (i, n.get("kind", "تعديل"), n.get("layer", "-"),
                        n.get("floor", "-"), n.get("room", "-"), n.get("text", "")))
    prompt = (
        "هذا نموذج Building JSON قائم. نفّذ طلبات التعديل التالية من المهندس بدقّة، "
        "وأعِد **النموذج الكامل** بصيغة JSON فقط (بلا شرح).\n"
        "لا تغيّر ما لم يُطلب تغييره. حافظ على معرّفات الغرف غير المتأثرة كما هي.\n"
        "حافظ على id لكل باب ونافذة موجودة وكتلة _opening_identity كما هي. "
        "للإضافات الجديدة فقط اختر id نصياً فريداً؛ لا تعِد ترقيم العناصر عند حذف أو نقل عنصر.\n"
        "كل ملاحظة تذكر «الغرفة» و«الدور» — طبّقها على تلك الغرفة في ذلك الدور فقط.\n"
        "طلبات الألوان: استخدم wall_color / floor_color / ceiling_color على الغرفة المعنيّة وحدها "
        "(وcolor داخل كائن الباب للأبواب)، بصيغة #RRGGBB حسب جدول الألوان أعلاه. "
        "وإن كان قالب الدور مشتركاً بين عدّة levels فانسخه باسم جديد للدور المطلوب وحده قبل التلوين.\n\n"
        "طلبات التعديل:\n" + "\n".join(lines) +
        "\n\nالنموذج الحالي:\n" + json.dumps(building, ensure_ascii=False)
    )
    mt = int(os.environ.get("ACS_MAX_TOKENS_REPAIR", "48000"))
    bt = str((building.get("meta") or {}).get("type") or "residential")
    raw = extract_json(call_llm(prompt, model=model, max_tokens=mt, truncate=False,
                               btype=bt, user_msg=""))
    if raw.get("_opening_identity") != building["_opening_identity"]:
        raise E.AcsApiError(E.ACS_UPSTREAM_INVALID_JSON,
                            "تعذر الحفاظ على معرّفات عناصر النموذج؛ لم يُطبّق التعديل.")
    # validate() rejects missing/duplicate identities in a migrated model.
    out = validate(raw)
    out.setdefault("meta", {}).setdefault("type", bt)

    issues, stats = V.validate_building(out)
    print("[ACS-EDIT] بعد التعديل: %d مخالفة · %s" % (len(issues), stats))
        # F-01: المصلِح الحسابي لم يعد يكتب في النموذج. ما كان يغيّره صار
        # اقتراحاً يُحسَب في طبقة الـAPI عبر acs_engineering_authority.plan
        # ويُعرَض على المستخدم. النموذج المعروض هنا هو مخرج التوليد نفسه.
    print("[ACS-EDIT] لا إصلاح تلقائي: %d مخالفة تُعرَض ولا تُصلَّح صامتاً" % len(issues))
    out.setdefault("meta", {})["acs_issues"] = len(issues)
    return out


# ---------------------------------------------------------------------------
# 7) التوليد على مرحلتين — الحلّ الجذري لمشكلة «التنفيذ ناقص»
#    مرحلة 1: خطة المناطق فقط (مخرج صغير لا ينقطع أبداً).
#    مرحلة 2: تفصيل كل مجموعة مناطق في نداء مستقل بالتوازي، ثم الدمج.
#    النتيجة: لا سقف عملي لحجم الطلب — كل بند يأخذ نصيبه من المخرج.
# ---------------------------------------------------------------------------
PLAN_MSG = (
    "اقرأ طلب العميل التالي كاملاً ثم أعِد **خطة المناطق فقط** بصيغة JSON.\n"
    "لا تكتب أي تفاصيل داخلية الآن (لا racks ولا points ولا stations ولا lanes ولا furniture) — "
    "فقط الهيكل:\n"
    '{ "meta":{... , "requirements":[...], "extras":[...], "added":[...]},\n'
    '  "site":{...}, "floor_height":, "wall_h":, "wall_t":,\n'
    '  "levels":[...], "floors":{"<tmpl>":{"rooms":[ {"id","rect","role","walls","wall_h"?,'
    '"brief":"ما يجب أن يحتويه هذا الحيّز بالضبط حسب طلب العميل — انقل أرقامه وأسماءه كما ذكرها"} ]}} }\n\n'
    + REQUIREMENTS_RULE +
    "\n**شرط القبول**: راجع الطلب بنداً بنداً، وتأكد أن لكل بند منطقةً تقابله وسطراً في "
    "requirements. المناطق وأعدادها وأسماؤها تأتي من طلب العميل لا من قالب جاهز — "
    "إن طلب ثلاث مناطق فثلاث، وإن طلب أربعين فأربعون.\n"
    "طلب العميل:\n\n")

DETAIL_MSG = (
    "هذه خطة معتمدة لمبنى، ومطلوب منك الآن **تفصيل المناطق المذكورة أدناه فقط**.\n"
    "أعِد JSON بهذا الشكل حصراً: {\"rooms\":[ Room كامل لكل منطقة مطلوبة ]}\n"
    "احتفظ بنفس id ونفس rect بالضبط، وأضِف كل التفاصيل: racks · lanes · stations · docks · "
    "points · furniture · doors · windows.\n"
    "**الأعداد والمقاسات تأتي من طلب العميل أولاً** (حقل brief في كل منطقة ينقل ما طلبه) — "
    "والقياسات المرجعية تُستخدم فقط لما لم يحدّده. إن ذكر العميل عدداً (١٢ محطة، ٨ أرصفة، "
    "٦ مستويات رفّ) فالتزمه بالضبط لا تقريباً.\n"
    "لا تُخرج مناطق أخرى ولا شرحاً.\n\n")


OUTLINE_MSG = (
    "اقرأ طلب العميل التالي كاملاً ثم أعِد **بيان المناطق** فقط بصيغة JSON.\n"
    "هذه أصغر مرحلة في التوليد: لا مستطيلات، ولا أبعاد لكل منطقة، ولا نثر، ولا "
    "تفاصيل داخلية إطلاقاً. المطلوب حصراً:\n"
    '{ "site":{"w":,"d":}, "floor_height":, "wall_h":, "wall_t":,\n'
    # KI-25: «index» ليس زينة. العارض يشتقّ ارتفاع كل دور منه (baseY = index ×‏
    # floor_height) ويشتقّ مفتاح طبقته منه (F0 · F1 …). بيانٌ بلا index يبني
    # المبنى كلّه عند إحداثيّة غير معرَّفة. أُسقط سهواً حين ضاق هذا التوجيه في
    # KI-24، وصار كل مبنى كبير يُبنى ولا يُعرَض. مُعاد هنا، ومحروسٌ في
    # validate() فلا يعود يعتمد على طاعة النموذج للتوجيه.
    '  "levels":[{"index":0,"id":"L0","name":"","template":""}],  '
    '// index عدد صحيح يبدأ من صفر للأسفل، ويزيد واحداً لكل دور فوقه\n'
    '  "zones":[ {"id":"معرّف قصير بالإنجليزية","role":"دور الحيّز",'
    '"template":"اسم قالب الدور"} ] }\n\n'
    "**شرط القبول**: راجع الطلب بنداً بنداً. لكل حيّز طلبه العميل سطرٌ واحد في "
    "zones — إن طلب ثلاثة فثلاثة، وإن طلب أربعين فأربعون. لا تدمج حيّزين ولا "
    "تحذف واحداً ولا تضف من قالب جاهز. السطر لا يتجاوز بضع كلمات: التفاصيل "
    "والمقاسات تأتي في مرحلة تالية.\n"
    "طلب العميل:\n\n")

PLAN_CHUNK_MSG = (
    "هذا بيان معتمد لمبنى، ومطلوب منك الآن **هندسة المناطق المذكورة أدناه فقط**.\n"
    "أعِد JSON بهذا الشكل حصراً: {\"rooms\":[ {\"id\",\"rect\":[x,y,w,d],"
    "\"role\",\"walls\",\"brief\"} ]}\n"
    "احتفظ بنفس id بالضبط لكل منطقة مطلوبة، ولا تُخرج منطقة غير مذكورة.\n"
    "الحقل brief سطر واحد لا يتجاوز %d حرفاً: ينقل أعداد العميل وأسماءه لهذا "
    "الحيّز وحده (مثال: «١٢ محطة تغليف، ٦ مستويات رفّ»). لا تُعِد كتابة الطلب "
    "فيه، ولا تكتب تفاصيل داخلية (لا racks ولا points ولا furniture) — تلك "
    "مرحلة تالية.\n"
    "المستطيلات داخل حدود الأرض ولا تتداخل.\n\n" % PC.BRIEF_MAX_CHARS)


def _outline(description, model=None, btype="residential", telemetry=None,
             request_id=None):
    """المرحلة الصغرى: بيان المناطق وحده (F-35).

    مخرجها ≈ ٢٤ رمزاً للمنطقة مقيسةً، وسقفها مشتقّ من السعة المعلنة
    (MAX_BUILDING_ZONES) لأنها المرحلة الوحيدة التي لا يمكن شطرها: قبلها لا
    يعرف الخادم شيئاً يُقسَم عليه. هذا البيان هو مرساة الحتمية: بعده يعرف
    الخادم عدد المناطق وترتيبها وأسماءها، فيصير التقطيع محسوباً لا مخمَّناً.
    """
    mt = PC.outline_budget()
    raw = extract_json(call_llm(description, model=model, max_tokens=mt,
                                btype=btype, user_msg=OUTLINE_MSG,
                                stage=PC.STAGE_OUTLINE, telemetry=telemetry,
                                request_id=request_id,
                                strategy=G.STRATEGY_STAGED))
    zones, issues = PC.normalise_outline(raw)
    envelope = {}
    if isinstance(raw, dict):
        for key in ("site", "floor_height", "wall_h", "wall_t", "levels", "meta"):
            if key in raw:
                envelope[key] = raw[key]
    return zones, envelope, issues


def _plan_chunk(description, chunk, zones_by_id, model=None, btype=None,
                telemetry=None, request_id=None):
    """شريحة واحدة من الخطّة — مخرجها محدود سلفاً بحجم الشريحة (F-36)."""
    ask = [{"id": z, "role": (zones_by_id.get(z) or {}).get("role", "")}
           for z in chunk["zone_ids"]]
    body = (PLAN_CHUNK_MSG
            + "المناطق المطلوب هندستها الآن (%d منطقة):\n" % len(ask)
            + json.dumps(ask, ensure_ascii=False)
            + "\n\nالطلب الأصلي كاملاً (خذ منه ما يخصّ هذه المناطق):\n"
            + description)
    txt = call_llm(body, model=model, max_tokens=chunk["budget"], truncate=False,
                   btype=btype, user_msg="", stage=PC.STAGE_PLAN_CHUNK,
                   telemetry=telemetry, request_id=request_id,
                   strategy=G.STRATEGY_STAGED, chunk_index=chunk["index"],
                   chunk_count=chunk.get("chunk_count"))
    return PC.validate_chunk(chunk, extract_json(txt))


def _plan_chunk_split(description, chunk, zones_by_id, model, btype, results,
                      stages, request_id=None, depth=0, rate=None):
    """شريحة خطّة واحدة، وإن بلغت سقفها شُطرت وأُعيدت — لا رُفع سقفها (F-39).

    يعيد كلفة المنطقة المقيسة بعد هذه الشريحة، لتُشتقّ منها أحجام ما بعدها.

    حجم الشريحة محسوب من تقدير يفترض أن النموذج يحترم سقف `brief`. الافتراض
    معقول لكنه **غير مضمون**، والاتّكال على مخرجٍ غير مضمون هو نفسه خطأ العطل
    الأصلي. فإن بلغت شريحة سقفها رغم الحساب، لا يُعاد النداء كما هو (يعطي
    الانقطاع نفسه ويحرق نداءً) ولا يُرفع السقف (يؤجّل العطل إلى مبنى أكبر):
    تُشطر الشريحة نصفين — طلبٌ مختلف فعلاً، نصف المناطق ⇒ نصف المخرج مهما
    أطال النموذج نثره.

    الشطر مشروط بدليل بلوغ السقف (stop_reason=max_tokens) لا بمجرّد رمز
    الخطأ: رداً مشوّهاً لسببٍ آخر شطرُه يحرق نداءين ولا يصلح شيئاً — فذاك
    يُنسب إلى PLAN_CHUNK_FAILED مباشرةً.

    العمق محدود بـ MAX_CHUNK_SPLITS وحجم الشريحة بـ MIN_CHUNK_ZONES. عند
    بلوغ أيّهما تُنسَب الشريحة إلى PLAN_CHUNK_FAILED وتُحَلّ مناطقها بمستطيل
    مشتقّ حتميّاً — لا دوران ولا حذف منطقة طلبها العميل.

    الهوية محفوظة: `index` من البيان و`part` من الشطر، والدمج يرتّب بترتيب
    البيان لا بترتيب الوصول، فالشطر لا يغيّر بايتاً واحداً من المخرج النهائي.
    """
    ctel = {}
    n_chunks = chunk.get("chunk_count")
    label = "%d%s" % (chunk["index"] + 1, chunk.get("part") and
                      ("." + chunk["part"]) or "")
    try:
        rooms, iss = _plan_chunk(description, chunk, zones_by_id, model=model,
                                 btype=btype, telemetry=ctel,
                                 request_id=request_id)
        stages.append(_safe_stage(ctel, chunk["count"], PC.STAGE_PLAN_CHUNK,
                                  chunk["index"]))
        results.append((chunk, rooms, iss))
        # W2-C: `rooms` هي المناطق التي اجتازت validate_chunk فعلاً —
        # «المحتوى المكتمل المتحقَّق منه» الذي يطلبه التفويض. عند المزوّد
        # الوكيل تُهمَل هذه الوسائط تماماً ويبقى الحساب كما كان.
        return PC.measured_zone_rate(ctel.get("output_tokens"), chunk["count"],
                                     rate,
                                     visible_chars=ctel.get("output_chars"),
                                     completed_zones=len(rooms))
    except E.AcsApiError as err:
        stages.append(_safe_stage(ctel, chunk["count"], PC.STAGE_PLAN_CHUNK,
                                  chunk["index"], err.code))
        hit_ceiling = (err.code in E.CEILING_CODES
                       and ctel.get("stop_reason") == "max_tokens")
        if hit_ceiling:
            # عند مزوّدٍ رموزُ مخرجه محتوىً: بلغ السقف ⇒ الكلفة الحقيقية
            # للمنطقة **لا تقلّ** عن السقف مقسوماً على عددها. حدٌّ أدنى
            # تصغر به كل شريحة بعدها. سلوكٌ قائم لم يُمَسّ.
            #
            # W2-C: وعند مزوّدٍ ليست كذلك، هذا هو بالضبط الاستنتاج الذي
            # كذّبه القياس الحيّ: 16000 رمزاً و0 حرف لا تقول إن المنطقة
            # تكلّف 4000 رمزاً — تقول إن الميزانية ذهبت إلى غير المحتوى.
            # فيُمرَّر ما وصل مرئياً وعددُ ما اكتمل (صفر هنا: لم يُتحقَّق من
            # منطقة واحدة)، وتقرّر الدالّة أن لا قياس ⇒ لا تصغير.
            # الانقطاع يعالجه الشطر أدناه — طلبٌ مختلف فعلاً.
            rate = PC.measured_zone_rate(ctel.get("max_output_tokens")
                                         or chunk["budget"],
                                         chunk["count"], rate,
                                         visible_chars=ctel.get("output_chars"),
                                         completed_zones=0)
        halves = PC.split_chunk(chunk, depth) if hit_ceiling else []
        if not halves:
            # نسبة عطل صريحة: الشريحة رقم كذا فشلت بالرمز كذا. لا يُسقط الباقي.
            print("[ACS-PLAN] شريحة %s/%s ✗ %s — مناطقها تُحَلّ حتميّاً وتُعلَن."
                  % (label, n_chunks, err.code))
            results.append((chunk, [], [{"code": "PLAN_CHUNK_FAILED",
                                         "chunk": chunk["index"],
                                         "part": chunk.get("part", ""),
                                         "depth": depth,
                                         "error_code": err.code}]))
            return rate
    print("[ACS-PLAN] شريحة %s/%s بلغت سقفها (%d منطقة) → تُشطر %s (عمق %d)."
          % (label, n_chunks, chunk["count"],
             "+".join(str(h["count"]) for h in halves), depth + 1))
    results.append((chunk, [], [{"code": "PLAN_CHUNK_SPLIT",
                                 "chunk": chunk["index"],
                                 "part": chunk.get("part", ""),
                                 "depth": depth + 1,
                                 "zones": chunk["count"],
                                 "into": [h["count"] for h in halves]}]))
    for half in halves:
        rate = _plan_chunk_split(description, half, zones_by_id, model, btype,
                                 results, stages, request_id=request_id,
                                 depth=depth + 1, rate=rate)
    return rate


def _plan_bounded(description, model=None, btype="residential", stages=None,
                  request_id=None, strategy_plan=None):
    """الخطّة عبر مراحل محدودة: بيان ← شرائح ← دمج حتميّ (KI-24).

    لا نداء هنا يعتمد على مخرج غير محدود: البيان مسقوف بكلفة معلومة للمنطقة،
    وكل شريحة مسقوفة بحجم محسوب من ميزانيتها. عطل شريحة يُنسب إليها ولا يُسقط
    التوليد: مناطقها تُحَلّ بمستطيل مشتقّ حتميّاً وتُعلَن PLAN_ZONE_UNRESOLVED.

    الشرائح تُقتطع **أثناء التنفيذ** لا دفعةً واحدة (F-40): كلفة المنطقة
    المقيسة من كل ردٍّ مكتمل تُغذّي حجم ما بعده، والحمل الذي قد يبلغ سقفه
    يسبقه نداءٌ استكشافيّ صغير يقيس قبل الالتزام. التخطيط المسبق يبقى محسوباً
    للتليمتري وللتقرير — لكن التنفيذ لا يلتزم بتقدير كذّبه القياس.
    """
    stages = stages if stages is not None else []
    otel = {}
    try:
        zones, envelope, issues = _outline(description, model=model, btype=btype,
                                           telemetry=otel, request_id=request_id)
        stages.append(_safe_stage(otel, len(zones), PC.STAGE_OUTLINE))
    except E.AcsApiError as err:
        stages.append(_safe_stage(otel, 0, PC.STAGE_OUTLINE, 0, err.code))
        raise
    if not zones:
        raise E.AcsApiError(E.ACS_UPSTREAM_INVALID_JSON,
                            "لم يُعِد النموذج أي منطقة في مرحلة البيان.",
                            upstream={"provider": "anthropic",
                                      "kind": "empty_outline"})

    chunking = PC.plan_chunks(zones)
    zones_by_id = {z["id"]: z for z in zones}
    print("[ACS-PLAN] بيان %d منطقة → %d شريحة × %d منطقة مبدئياً "
          "(سقف الشريحة %d رمزاً؛ الحجم يُعاد اشتقاقه من القياس)"
          % (len(zones), chunking["chunk_count"], chunking["chunk_size"],
             chunking["budget"]))

    results = []
    pending = PC.group_by_template(zones)
    rate = None
    index = 0
    capped = 0
    while pending:
        if index >= PC.MAX_PLAN_CHUNKS:
            # لا قصّ صامت: ما بقي يُعلَن عدداً، ومناطقه تُحَلّ حتميّاً في الدمج.
            capped = len(pending)
            print("[ACS-PLAN] ⚠ بلغ سقف الشرائح (%d) و%d منطقة بلا هندسة —"
                  " تُحَلّ حتميّاً وتُعلَن." % (PC.MAX_PLAN_CHUNKS, capped))
            break
        chunk, pending = PC.next_chunk(pending, index, rate=rate)
        if chunk is None:
            break
        index += 1
        # عدد الشرائح لا يُعرَف سلفاً في المسار المتكيّف. المُعلَن في التليمتري
        # **إسقاط حيّ** بأفضل معرفة الآن، لا رقم مخطَّط كذّبه القياس: المنفَّذ
        # + ما تسعه بقيّة المناطق بالحجم الحالي. يبقى الرقم مفهوماً للمشغّل
        # ولا يدّعي يقيناً لا يملكه.
        projected = index + -(-len(pending) // max(1, PC.chunk_size_for(rate=rate)))
        rate = _plan_chunk_split(
            description, dict(chunk, chunk_count=projected),
            zones_by_id, model, btype, results, stages,
            request_id=request_id, depth=0, rate=rate)

    building, merge_issues = PC.merge_plan(zones, results, envelope)
    building.setdefault("meta", {})["acs_plan_report"] = PC.plan_report(
        strategy_plan, zones, chunking, results, executed=index,
        measured_zone_tokens=rate, capped_zones=capped)
    for i in issues:
        building["meta"].setdefault("acs_stage_diagnostics", []).append(i)
    return validate(building)


def _plan(description, model=None, btype="residential", telemetry=None,
          request_id=None):
    mt = G.stage_budget("plan")
    out = validate(extract_json(call_llm(description, model=model, max_tokens=mt,
                                         btype=btype, user_msg=PLAN_MSG,
                                         stage="plan", telemetry=telemetry,
                                         request_id=request_id,
                                         strategy=G.STRATEGY_STAGED)))
    return out


def _detail_group(description, plan_ctx, rooms, model, btype, telemetry=None,
                  request_id=None):
    mt = G.stage_budget("detail")
    body = (DETAIL_MSG + "سياق الخطة (للاتّساق فقط):\n" + plan_ctx +
            "\n\nالمناطق المطلوب تفصيلها الآن:\n" +
            json.dumps(rooms, ensure_ascii=False) +
            "\n\nالطلب الأصلي كاملاً (نفّذ منه ما يخصّ هذه المناطق):\n" + description)
    txt = call_llm(body, model=model, max_tokens=mt, truncate=False, btype=btype,
                   user_msg="", stage="detail", telemetry=telemetry,
                   request_id=request_id, strategy=G.STRATEGY_STAGED)
    data = extract_json(txt)
    return data.get("rooms") or (data if isinstance(data, list) else [])


def _detail_group_split(description, plan_ctx, rooms, model, btype, depth=0,
                        stages=None, request_id=None):
    """§12: مجموعة انقطع مخرجها تُقسَّم قسمين ويُعاد تفصيلها — لا تُعاد كما هي.

    إعادة النداء نفسه بعد انقطاع تعطي الانقطاع نفسه وتحرق نداءً. التقسيم يغيّر
    الطلب فعلاً: نصف المناطق ⇒ نصف المخرج. العمق محدود بـ MAX_GROUP_SPLITS،
    وعند بلوغه يُرفع الخطأ مصنّفاً بدل الدوران.
    """
    tel = {}
    try:
        out = _detail_group(description, plan_ctx, rooms, model, btype,
                            telemetry=tel, request_id=request_id)
        if stages is not None:
            stages.append(_safe_stage(tel, len(rooms), "detail", depth))
        return out
    except E.AcsApiError as err:
        if stages is not None:
            stages.append(_safe_stage(tel, len(rooms), "detail", depth, err.code))
        # W2-E: الشرط دليلُ بلوغ السقف لا رمزٌ بعينه. ردٌّ استهلك ميزانيته
        # في محتوى غير مرئي بلغ السقف تماماً كما يبلغه نصٌّ مقطوع.
        if err.code not in E.CEILING_CODES or depth >= G.MAX_GROUP_SPLITS:
            raise
        halves = G.split_group(rooms)
        if not halves:
            raise
        print("[ACS-DEEP] انقطعت مجموعة من %d منطقة — تُقسَم إلى %d+%d (عمق %d)."
              % (len(rooms), len(halves[0]), len(halves[1]), depth + 1))
        out = []
        for half in halves:
            out.extend(_detail_group_split(description, plan_ctx, half, model,
                                           btype, depth + 1, stages,
                                           request_id=request_id) or [])
        return out


def _safe_stage(tel, n_rooms, stage, depth=0, error=None):
    """قياس مرحلة واحدة — أرقام فقط. لا نصّ زائر ولا مفتاح ولا محتوى رد."""
    return {"stage": stage, "depth": depth, "zones": n_rooms,
            "stop_reason": tel.get("stop_reason"),
            "input_tokens": tel.get("input_tokens"),
            "output_tokens": tel.get("output_tokens"),
            "max_output_tokens": tel.get("max_output_tokens"),
            "completion_chars": tel.get("completion_chars"),
            "parsed": bool(tel.get("complete")) and error is None,
            "error": error}



def _preserve_added_disclosure(building):
    """ينقل meta.added إلى إفصاح صريح بدل محوه (F-01).

    الوضع الصارم يعني ألّا يضيف النظام شيئاً — لا أن يُخفي ما أضافه المولّد.
    المحو القديم كان يفقد المعلومة الوحيدة التي تُخبر المستخدم بما لم يطلبه."""
    meta = building.setdefault("meta", {})
    added = meta.get("added") or []
    if added:
        disc = meta.setdefault("acs_engineering_disclosure", {})
        prev = list(disc.get("ai_added") or [])
        for item in added:
            if item not in prev:
                prev.append(item)
        disc["ai_added"] = prev
        disc["note"] = ("عناصر أضافها المولّد ولم يطلبها الوصف — تُعرَض للمراجعة "
                        "ولا تُعدّ جزءاً من نيّة التصميم.")
    meta["added"] = []
    return building

def understand_deep(description, model=None, group_size=None, workers=None,
                    strict=False, btype=None, stages=None, request_id=None,
                    strategy_plan=None):
    """توليد على مراحل مع تفصيل متوازٍ — للطلبات التي لا يسعها نداء واحد."""
    import acs_validate as V
    btype = detect_type(description, btype)
    stages = stages if stages is not None else []
    print("[ACS-DEEP] نوع المبنى: %s" % btype)

    desc = description + (STRICT_RULE if strict else "")

    # KI-24/F-37: أي مسار للخطّة؟ القرار محسوب قبل النداء لا بعد انقطاعه.
    #
    # المقدّر يقدّر النموذج **النهائي**؛ ما لم يكن يُقدَّر قطّ هو مخرج **الخطّة**
    # نفسها. وهو ما انقطع في الإنتاج: est_out=34437 لخمسين منطقة، وسقف مرحلة
    # plan ‏16000، ولا حارس بينهما. هنا يُقدَّر مخرج الخطّة صراحةً ويُقارن
    # بسقفه مع هامش الأمان نفسه المستعمل في التقطيع.
    _sp = strategy_plan if isinstance(strategy_plan, dict) else None
    _zones_est = int((_sp or {}).get("estimated_zones")
                     or G.estimate_zones(description, btype))
    _plan_est = PC.estimate_plan_chunk_tokens(_zones_est, requirements=40)
    _plan_cap = int(PC.plan_chunk_budget() * PC.CHUNK_SAFETY)
    _bounded = _plan_est > _plan_cap
    print("[ACS-PLAN] تقدير مخرج الخطّة %d رمزاً · سقف آمن %d · المسار: %s"
          % (_plan_est, _plan_cap, "شرائح محدودة" if _bounded else "خطّة واحدة"))

    if _bounded:
        building = _plan_bounded(desc, model=model, btype=btype, stages=stages,
                                 request_id=request_id, strategy_plan=_sp)
    else:
        _ptel = {}
        try:
            building = _plan(desc, model=model, btype=btype, telemetry=_ptel,
                             request_id=request_id)
            stages.append(_safe_stage(_ptel, 0, "plan"))
        except E.AcsApiError as err:
            stages.append(_safe_stage(_ptel, 0, "plan", 0, err.code))
            # F-37: انقطاع الخطّة لم يكن له مسار تعافٍ إطلاقاً — تصعيد «واحد ←
            # مراحل» يعالج النداء الواحد، وتقسيم المجموعة يعالج التفصيل،
            # والخطّة بينهما بلا حارس فيسقط الطلب كلّه بـ502. الآن تُعاد
            # بشرائح محدودة مرّة واحدة: طلبٌ مختلف فعلاً لا تكرارٌ للطلب نفسه.
            if err.code not in E.CEILING_CODES:
                raise
            print("[ACS-PLAN] بلغت الخطّة سقفها (%s) — إعادة بشرائح محدودة."
                  % err.code)
            building = _plan_bounded(desc, model=model, btype=btype,
                                     stages=stages, request_id=request_id,
                                     strategy_plan=_sp)
    plan_rooms = []
    for tmpl, fdef in (building.get("floors") or {}).items():
        for r in (fdef.get("rooms") or []):
            plan_rooms.append((tmpl, r))
    print("[ACS-DEEP] الخطة: %d منطقة في %d قالب"
          % (len(plan_rooms), len(building.get("floors") or {})))

    gs = int(group_size or os.environ.get("ACS_GROUP_SIZE", "5"))
    wk = int(workers or os.environ.get("ACS_WORKERS", "4"))
    ctx = json.dumps({"site": building.get("site"), "wall_h": building.get("wall_h"),
                      "zones": [{"id": r.get("id"), "rect": r.get("rect"),
                                 "role": r.get("role")} for _, r in plan_rooms]},
                     ensure_ascii=False)

    groups = []
    for tmpl in (building.get("floors") or {}):
        rs = [r for t, r in plan_rooms if t == tmpl]
        for i in range(0, len(rs), gs):
            groups.append((tmpl, rs[i:i + gs]))
    cap = int(os.environ.get("ACS_MAX_GROUPS", "14"))
    if len(groups) > cap:
        print("[ACS-DEEP] ⚠ %d مجموعة > السقف %d — تُفصَّل الأولى ويبقى الباقي بالخطة."
              % (len(groups), cap))
        groups = groups[:cap]
    print("[ACS-DEEP] تفصيل %d مجموعة بالتوازي (%d عامل)…" % (len(groups), wk))

    import concurrent.futures as cf
    results = {}

    _slock = threading.Lock()

    def work(k):
        tmpl, rs = groups[k]
        local = []
        try:
            det = _detail_group_split(desc, ctx, rs, model, btype, 0, local,
                                      request_id=request_id)
            print("[ACS-DEEP] مجموعة %d/%d ✓ (%d منطقة)" % (k + 1, len(groups), len(det)))
            return tmpl, det
        except Exception as e:
            # المرحلة الأولى تبقى: منطقة بهيكلها الصحيح بلا تفاصيل أصدق من لا شيء،
            # وأصدق من نصف تفصيل مبتور. ويُسجَّل ذلك في القياسات لا يُبتلع صامتاً.
            print("[ACS-DEEP] مجموعة %d/%d ✗ %s — تبقى بخطتها بلا تفاصيل."
                  % (k + 1, len(groups), str(e)[:160]))
            return tmpl, rs
        finally:
            with _slock:
                stages.extend(local)

    with cf.ThreadPoolExecutor(max_workers=max(1, wk)) as ex:
        for tmpl, det in ex.map(work, range(len(groups))):
            results.setdefault(tmpl, []).extend(det or [])

    for tmpl, det in results.items():
        by_id = {str(r.get("id")): r for r in det if isinstance(r, dict) and r.get("rect")}
        merged = []
        for r in (building["floors"][tmpl].get("rooms") or []):
            rid = str(r.get("id"))
            new = by_id.pop(rid, None)
            if new:
                # §7: هندسة المرحلة الأولى مرجع. أي rect مخالف من مرحلة التفصيل
                # يُطرَح ويُسجَّل، ولا يُعاد كتابة موضع منطقة في الخفاء.
                if new.get("rect") and list(new["rect"]) != list(r.get("rect") or []):
                    building.setdefault("meta", {}).setdefault(
                        "acs_stage_diagnostics", []).append(
                        {"code": "STAGE_RECT_OVERRIDE_REJECTED",
                         "template": tmpl, "id": rid})
                new["rect"] = r.get("rect", new.get("rect"))     # الخطة تحكم المواضع
                new.pop("brief", None)
                merged.append(new)
            else:
                r.pop("brief", None); merged.append(r)
        # §7: مناطق لم تكن في الخطة. لا تُحذف (قد تحمل بنداً طلبه العميل) ولا
        # تُدمَج صامتة: تُقبل ويُعلَن عنها في meta كتشخيص صريح.
        if by_id:
            extra = sorted(by_id.keys())
            print("[ACS-DEEP] ⚠ التفصيل أضاف %d منطقة خارج الخطة: %s"
                  % (len(extra), ", ".join(extra[:8])))
            building.setdefault("meta", {}).setdefault(
                "acs_stage_diagnostics", []).append(
                {"code": "STAGE_ADDED_ZONES", "template": tmpl, "ids": extra[:32]})
        merged.extend(by_id.values())
        building["floors"][tmpl]["rooms"] = merged

    building.setdefault("meta", {})["type"] = building["meta"].get("type", btype)
    building["meta"]["acs_mode"] = "deep"
    if strict:
        building["meta"]["strict"] = True
        # F-01: الوضع الصارم لا يمحو إفصاح النموذج عمّا أضافه. القائمة تُنقَل إلى
        # حقل إفصاح صريح بدل أن تُفقَد، فيبقى للمستخدم ما يراجعه ويحذفه.
        _preserve_added_disclosure(building)
    reqs = building["meta"].get("requirements") or []
    print("[ACS-DEEP] تقرير التغطية: %d بند من طلب العميل" % len(reqs))
    issues, stats = V.validate_building(building)
    print("[ACS-DEEP] بعد الدمج: %d مخالفة · %s" % (len(issues), stats))
        # F-01: المصلِح الحسابي لم يعد يكتب في النموذج. ما كان يغيّره صار
        # اقتراحاً يُحسَب في طبقة الـAPI عبر acs_engineering_authority.plan
        # ويُعرَض على المستخدم. النموذج المعروض هنا هو مخرج التوليد نفسه.
    print("[ACS-DEEP] لا إصلاح تلقائي: %d مخالفة تُعرَض ولا تُصلَّح صامتاً" % len(issues))
    building["meta"]["acs_issues"] = len(issues)
    return building


def _deep_override():
    """ACS_DEEP: True يفرض المراحل، False يفرض النداء الواحد، None يترك التقدير.

    كان هنا سابقاً `_should_go_deep` يحكم بطول **المدخل** (>2200 حرفاً أو ١٢ بنداً
    مرقّماً). ذلك المقياس هو أصل العطل الإنتاجي: «مستودع بسيط 20×15م…» وصفٌ من
    ٥٥ حرفاً، فيمرّ دائماً في مسار النداء الواحد مهما كان مخرجه — وحجم المخرج
    لا يُقاس بطول المدخل. الحكم صار لـ acs_generation.plan_strategy.
    """
    mode = os.environ.get("ACS_DEEP", "auto").lower()
    if mode in ("1", "on", "always", "true"):
        return True
    if mode in ("0", "off", "never", "false"):
        return False
    return None


FATAL_UPSTREAM = (E.ACS_UPSTREAM_NOT_CONFIGURED, E.ACS_UPSTREAM_AUTH,
                  E.ACS_UPSTREAM_PERMISSION, E.ACS_UPSTREAM_MODEL_REJECTED,
                  E.ACS_UPSTREAM_REFUSED, E.ACS_NOT_CONFIGURED)


def understand(description, model=None, repair_rounds=None, deep=None, strict=False,
               btype=None, site_w=None, site_d=None, floors=None, request_id=None):
    """وصف → Building JSON كامل، أو خطأ مصنّف. لا نموذج ناقص بينهما.

    القرار قبل النداء (§5/§6): يُقدَّر حجم المخرج حتمياً ويُصنَّف الطلب، فتُختار
    المرحلة الواحدة للصغير والمراحل للكبير. القرار بعد الانقطاع (§12): لا يُعاد
    الطلب نفسه — تُرفَّع الاستراتيجية إلى المراحل مرّة واحدة، ثم تُقسَّم المجموعة
    المنقطعة. وإن بقي الانقطاع، خطأ معلن لا نصف نموذج.
    """
    import acs_validate as V
    btype = detect_type(description, btype)
    forced = deep if deep is not None else _deep_override()
    plan = G.plan_strategy(description, btype, site_w, site_d, floors, forced=forced)
    stages = []
    print("[ACS-PLAN] class=%s est_out=%d zones=%d budget=%d -> %s (%s)"
          % (plan["size_class"], plan["estimated_output_tokens"],
             plan["estimated_zones"], plan["max_output_tokens"],
             plan["strategy"], plan["reason"]))

    def _stamp(b, strategy, escalations):
        m = b.setdefault("meta", {})
        m["acs_mode"] = "deep" if strategy == G.STRATEGY_STAGED else "single"
        m["acs_generation"] = {
            "contract": plan["contract"],
            "strategy": strategy,
            "size_class": plan["size_class"],
            "estimated_output_tokens": plan["estimated_output_tokens"],
            "estimated_zones": plan["estimated_zones"],
            "max_output_tokens": plan["max_output_tokens"],
            "single_stage_threshold_tokens": plan["single_stage_threshold_tokens"],
            "escalations": escalations,
            "stages": stages[:24]}
        return b

    if plan["strategy"] == G.STRATEGY_STAGED:
        return _stamp(understand_deep(description, model=model, strict=strict,
                                      btype=btype, stages=stages,
                                      request_id=request_id,
                                      strategy_plan=plan),
                      G.STRATEGY_STAGED, 0)

    # F-19: `int(os.environ.get("ACS_REPAIR_ROUNDS", "1"))` كان يرفع ValueError
    # على القيمة الفارغة — و.env.example يشحن هذا المتغيّر فارغاً. الخطأ يقع
    # داخل عملية التوليد فيُصنَّف upstream ويصل المستخدم 502 «عطل من مزوّد
    # النموذج» عن خطأ ضبط محلّي بحت. _env_int في هذا الملفّ يتحمّل الفراغ أصلاً.
    rounds = (int(repair_rounds) if repair_rounds is not None
              else _env_int("ACS_REPAIR_ROUNDS", 1))

    _tel = {}
    try:
        building = validate(extract_json(call_llm(
            description + (STRICT_RULE if strict else ""), model=model, btype=btype,
            max_tokens=G.stage_budget("single"), stage="single", telemetry=_tel,
            request_id=request_id, strategy=plan["strategy"])))
        stages.append(_safe_stage(_tel, plan["estimated_zones"], "single"))
    except E.AcsApiError as err:
        stages.append(_safe_stage(_tel, plan["estimated_zones"], "single", 0, err.code))
        # §12: انقطاع المرحلة الواحدة يُعالَج بتغيير الاستراتيجية مرّة واحدة —
        # لا بإعادة النداء نفسه، ولا بترميم النصّ المقطوع.
        # W2-E: العطل المُقاس حيّاً كان NO_VISIBLE_OUTPUT في المرحلة الواحدة،
        # فلم يُصعَّد أصلاً ووصل المستخدم 502 بلا محاولة تعافٍ. بلوغ السقف
        # بلوغٌ للسقف أياً كان ما مُلئ به.
        if (err.code in E.CEILING_CODES
                and G.MAX_STRATEGY_ESCALATIONS >= 1 and forced is None):
            print("[ACS-PLAN] بلغ النداء الواحد سقفه (%s) — تصعيد إلى "
                  "التوليد على مراحل." % err.code)
            return _stamp(understand_deep(description, model=model, strict=strict,
                                          btype=btype, stages=stages,
                                          request_id=request_id,
                                          strategy_plan=plan),
                          G.STRATEGY_STAGED, 1)
        raise
    building.setdefault("meta", {}).setdefault("type", btype)
    if strict:
        building["meta"]["strict"] = True
        # F-01: الوضع الصارم لا يمحو إفصاح النموذج عمّا أضافه. القائمة تُنقَل إلى
        # حقل إفصاح صريح بدل أن تُفقَد، فيبقى للمستخدم ما يراجعه ويحذفه.
        _preserve_added_disclosure(building)
    issues, stats = V.validate_building(building)
    print("[ACS-CHECK] جولة 0 (%s): %d مخالفة · %s" % (btype, len(issues), stats))

    for i in range(rounds):
        if not issues:
            break
        print("[ACS-CHECK] إرسال %d مخالفة للإصلاح (جولة %d)…" % (len(issues), i + 1))
        try:
            fixed = validate(extract_json(call_llm_repair(
                description, building, issues, model=model,
                request_id=request_id, strategy=plan["strategy"])))
        except Exception as e:
            print("[ACS-CHECK] فشل الإصلاح (%s) — نُبقي النموذج السابق." % str(e)[:200])
            break
        new_issues, new_stats = V.validate_building(fixed)
        print("[ACS-CHECK] جولة %d: %d مخالفة · %s" % (i + 1, len(new_issues), new_stats))
        if len(new_issues) <= len(issues):      # تحسّن أو تعادل → اعتمده
            building, issues = fixed, new_issues
        else:
            print("[ACS-CHECK] النتيجة أسوأ — نُبقي السابق.")
            break

    # ── لا إصلاح حسابي صامت (F-01) ──
        # F-01: المصلِح الحسابي لم يعد يكتب في النموذج. ما كان يغيّره صار
        # اقتراحاً يُحسَب في طبقة الـAPI عبر acs_engineering_authority.plan
        # ويُعرَض على المستخدم. النموذج المعروض هنا هو مخرج التوليد نفسه.
    print("[ACS-CHECK] لا إصلاح تلقائي: %d مخالفة تُعرَض ولا تُصلَّح صامتاً" % len(issues))

    building.setdefault("meta", {})["acs_issues"] = len(issues)
    if issues:
        print("[ACS-CHECK] مخالفات متبقية (%d). أمثلة:\n%s"
              % (len(issues), V.format_issues(issues, 8)))
    return _stamp(building, G.STRATEGY_SINGLE, 0)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return
    model = None
    if "--model" in args:
        i = args.index("--model"); model = args[i+1]; del args[i:i+2]
    if args and args[0] == "--pdf":
        text = pdf_to_text(args[1]); out = args[2] if len(args) > 2 else "building.json"
    else:
        text = open(args[0], encoding="utf-8").read(); out = args[1] if len(args) > 1 else "building.json"
    print("[ACS] understanding %d chars via LLM ..." % len(text))
    building = understand(text, model=model)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(building, f, ensure_ascii=False, indent=1)
    nr = sum(len(fd.get("rooms", [])) for fd in building["floors"].values())
    print("[ACS] OK -> %s  (levels=%d, rooms=%d)" % (out, len(building["levels"]), nr))
    print("[ACS] ثم:  python3 acs_compiler.py %s model.gltf" % out)

if __name__ == "__main__":
    main()
