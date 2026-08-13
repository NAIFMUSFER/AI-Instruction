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

import acs_api_errors as E                     # عقد الأخطاء الموحّد (رموز + تصنيف)

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
  "doors":   [ {"edge":"N|S|E|W","offset":float,"width":float,"height":float,"material":"wood|oak|glass"?,"color":"#RRGGBB"?} ],
  "windows": [ {"edge":"N|S|E|W","offset":float,"width":float,"sill":float,"height":float} ],
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
    schema = SCHEMA_BRIEF + (SCHEMA_INDUSTRIAL if industrial else "")
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
                      repair_rounds=None, notes="", strict=False, btype=None):
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
    building = validate(extract_json(call_llm(None, model=model, content=content, btype=vt)))
    building.setdefault("meta", {}).setdefault("type", vt)
    if strict:
        building["meta"]["strict"] = True
    issues, stats = V.validate_building(building)
    print("[ACS-VISION] قراءة المخطط: %d مخالفة · %s" % (len(issues), stats))

    try:
        import acs_layout as L
        rep = L.autofix(building)
        issues, stats = V.validate_building(building)
        print("[ACS-FIX] إصلاح حسابي: حُرّكت %d غرفة · تداخل متبقٍ %d · %s"
              % (rep["moved"], rep["remaining"], "؛ ".join(rep["tight"]) or "المساحات تسع"))
        print("[ACS-VISION] بعد الإصلاح: %d مخالفة · %s" % (len(issues), stats))
    except Exception as e:
        print("[ACS-FIX] تخطّي: %s" % str(e)[:200])

    building.setdefault("meta", {})["acs_issues"] = len(issues)
    building["meta"].setdefault("source", "plan-image")
    return building


def call_llm(description, model=None, max_tokens=None, truncate=True, content=None,
             btype=None, user_msg=None):
    """content اختياري: قائمة بلوكات (نص/صور) للرؤية. وإلا يُرسل description كنص."""
    try:
        import anthropic
    except Exception:
        raise E.AcsApiError(E.ACS_NOT_CONFIGURED, "مكتبة anthropic غير مثبّتة على الخادم.")
    model = (model or os.environ.get("ACS_LLM_MODEL", "claude-sonnet-5")).strip()
    max_tokens = int(max_tokens or os.environ.get("ACS_MAX_TOKENS", "32000"))
    api_key = clean_key(os.environ.get("ANTHROPIC_API_KEY"))
    if not api_key:
        raise E.AcsApiError(E.ACS_UPSTREAM_NOT_CONFIGURED)

    # مهلة صريحة على نداء المنبع: بلا هذا يعلّق العامل حتى تقتله البوّابة
    # فيرى العميل انقطاعاً بلا جسد رد — وهو ما لا يمكن تصنيفه ولا عرضه.
    timeout_s = float(os.environ.get("ACS_UPSTREAM_TIMEOUT_S", "600"))
    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=timeout_s)
    except TypeError:                      # مكتبة قديمة بلا وسيط timeout
        client = anthropic.Anthropic(api_key=api_key)
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

    def _call(mt, thinking):
        """يستخدم البثّ (streaming) — مطلوب للمخرجات الكبيرة، ويعمل مع الصغيرة أيضاً."""
        kw = dict(model=model, max_tokens=mt, system=sys_p, messages=msgs)
        if thinking is not None:
            kw["thinking"] = thinking
        try:
            with client.messages.stream(**kw) as s:
                return s.get_final_message()
        except (AttributeError, TypeError):
            return client.messages.create(**kw)   # مكتبة قديمة

    # سلّم محاولات: أهمّها تعطيل "التفكير الموسّع" الذي قد يبتلع كل الميزانية
    # ويترك النص فارغاً (stop=max_tokens مع out_chars=0).
    OFF = {"type": "disabled"}
    attempts = [
        (max_tokens, OFF),          # الأفضل: بلا تفكير، سقف عالٍ
        (max_tokens, None),         # افتراضي النموذج
        (max(max_tokens, 32000), None),
        (16000, OFF),
        (8000, None),
    ]

    # §8 إعادة المحاولة محدودة وللأعطال العابرة وحدها. مفتاح مرفوض أو نموذج غير
    # موجود لا يُصلحه التكرار: يستهلك دقائق ورصيداً ثم يعطي الرسالة نفسها متأخّرة.
    text = ""; stop = "?"; last_err = None; tried = 0
    backoff = float(os.environ.get("ACS_UPSTREAM_BACKOFF_S", "2"))
    for mt, think in attempts:
        tried += 1
        try:
            msg = _call(mt, think)
        except Exception as e:
            err = E.classify_upstream(e, attempts=tried)
            last_err = err
            print("[ACS-LLM] call failed (max_tokens=%s, thinking=%s) -> %s"
                  % (mt, "off" if think else "default", err.code))
            if not err.retryable:
                raise err                     # عطل دائم: أعلِنه فوراً بلا تكرار
            if tried < len(attempts) and backoff > 0:
                time.sleep(min(backoff * tried, 15))
            continue

        parts = [getattr(b, "text", None) for b in (msg.content or [])]
        text = "".join(p for p in parts if p)
        stop = getattr(msg, "stop_reason", "?")
        out_tok = getattr(getattr(msg, "usage", None), "output_tokens", "?")
        print("[ACS-LLM] model=%s thinking=%s max_tokens=%s stop=%s out_chars=%d out_tokens=%s"
              % (model, "off" if think else "default", mt, stop, len(text), out_tok))

        if text.strip():
            break               # نجحنا
        print("[ACS-LLM] رد بلا نص — أجرّب إعداداً آخر…")

    if not text.strip():
        if isinstance(last_err, E.AcsApiError):
            raise last_err                    # آخر عطل عابر مصنّف: أوضح من العموم
        raise E.AcsApiError(
            E.ACS_UPSTREAM_EMPTY_RESPONSE,
            "أعاد النموذج رداً فارغاً في كل المحاولات (آخر stop_reason=%s)." % stop,
            upstream={"provider": "anthropic", "kind": "empty_text",
                      "attempts": tried})

    if stop == "max_tokens":
        # المخرج انقطع — نحاول إغلاق الأقواس الناقصة لإنقاذ ما أمكن
        text = _balance_json(text)
        print("[ACS-LLM] تحذير: انقطع المخرج (max_tokens) — حاولنا إصلاحه. "
              "لنتيجة كاملة: قصّر الوصف أو ارفع ACS_MAX_TOKENS.")
    return text


def _balance_json(s):
    """ينقذ JSON مقطوع: يقصّ عند آخر عنصر مكتمل ثم يغلق الأقواس بترتيبها الصحيح."""
    try:
        json.loads(s)
        return s                      # سليم أصلاً
    except Exception:
        pass

    # امسح حالة المكدّس عند كل موضع
    stacks = []                       # (index, tuple(stack)) بعد كل قوس إغلاق
    stack = []; in_str = False; esc = False
    for i, ch in enumerate(s):
        if esc:
            esc = False; continue
        if in_str:
            if ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        if ch == '"':
            in_str = True; continue
        if ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack: stack.pop()
            stacks.append((i, tuple(stack)))

    # جرّب القصّ عند كل إغلاق من النهاية للبداية
    for i, st in reversed(stacks[-4000:]):
        cand = s[:i + 1].rstrip().rstrip(",")
        cand += "".join(reversed(st))
        try:
            json.loads(cand)
            return cand
        except Exception:
            continue
    return s

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


def _save_raw(text):
    """يحفظ الرد الخام لتشخيص الخادم. لا يُذكر مساره أبداً في رد العميل."""
    try:
        with open(os.environ.get("ACS_RAW_DUMP", "last_llm_response.txt"),
                  "w", encoding="utf-8") as f:
            f.write(E.redact(text))
    except Exception:
        pass


def extract_json(raw, _repaired=False):
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

    # لا كائن مكتمل: الاحتمال الأول انقطاع المخرج. إصلاح حتمي واحد ثم نُعلن العجز.
    if not _repaired:
        fixed = _balance_json(text)
        if fixed != text and len(scan_top_level_json(fixed)[0]) == 1:
            print("[ACS-JSON] رد مقطوع — أُصلح بإغلاق الأقواس المتبقّية.")
            return extract_json(fixed, _repaired=True)
    _save_raw(text)
    code = (E.ACS_UPSTREAM_TRUNCATED if (truncated or malformed)
            else E.ACS_UPSTREAM_INVALID_JSON)
    raise E.AcsApiError(
        code, E.MESSAGE_AR[code] + " قصّر الوصف أو ارفع ACS_MAX_TOKENS.",
        upstream={"provider": "anthropic", "kind": "unparsable_response"})

def validate(building):
    """تحقّق بنيوي خفيف + إصلاحات أمان (بلا اعتماد خارجي)."""
    assert isinstance(building.get("site"), dict), "site مفقود"
    building.setdefault("floor_height", 3.2); building.setdefault("wall_h", 3.0); building.setdefault("wall_t", 0.15)
    assert building.get("levels"), "levels مفقود"
    assert building.get("floors"), "floors مفقود"
    for tmpl, fdef in building["floors"].items():
        for r in fdef.get("rooms", []):
            assert "rect" in r and len(r["rect"]) == 4, "غرفة بلا rect صحيح: %s" % r.get("id")
    return building

def call_llm_repair(description, building, issues, model=None):
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
    mt = int(os.environ.get("ACS_MAX_TOKENS_REPAIR", "48000"))
    bt = str((building.get("meta") or {}).get("type") or detect_type(description))
    return call_llm(fix_prompt, model=model, max_tokens=mt, truncate=False, btype=bt, user_msg="")


def apply_notes(building, notes, model=None):
    """ينفّذ ملاحظات المهندس (تعديل/نقل/أبعاد/حذف/إضافة) على النموذج الحالي."""
    import acs_validate as V
    lines = []
    for i, n in enumerate(notes, 1):
        lines.append("%d. [%s] الطبقة: %s · الدور: %s · الغرفة: %s\n   المطلوب: %s"
                     % (i, n.get("kind", "تعديل"), n.get("layer", "-"),
                        n.get("floor", "-"), n.get("room", "-"), n.get("text", "")))
    prompt = (
        "هذا نموذج Building JSON قائم. نفّذ طلبات التعديل التالية من المهندس بدقّة، "
        "وأعِد **النموذج الكامل** بصيغة JSON فقط (بلا شرح).\n"
        "لا تغيّر ما لم يُطلب تغييره. حافظ على معرّفات الغرف غير المتأثرة كما هي.\n"
        "كل ملاحظة تذكر «الغرفة» و«الدور» — طبّقها على تلك الغرفة في ذلك الدور فقط.\n"
        "طلبات الألوان: استخدم wall_color / floor_color / ceiling_color على الغرفة المعنيّة وحدها "
        "(وcolor داخل كائن الباب للأبواب)، بصيغة #RRGGBB حسب جدول الألوان أعلاه. "
        "وإن كان قالب الدور مشتركاً بين عدّة levels فانسخه باسم جديد للدور المطلوب وحده قبل التلوين.\n\n"
        "طلبات التعديل:\n" + "\n".join(lines) +
        "\n\nالنموذج الحالي:\n" + json.dumps(building, ensure_ascii=False)
    )
    mt = int(os.environ.get("ACS_MAX_TOKENS_REPAIR", "48000"))
    bt = str((building.get("meta") or {}).get("type") or "residential")
    out = validate(extract_json(call_llm(prompt, model=model, max_tokens=mt, truncate=False,
                                         btype=bt, user_msg="")))
    out.setdefault("meta", {}).setdefault("type", bt)

    issues, stats = V.validate_building(out)
    print("[ACS-EDIT] بعد التعديل: %d مخالفة · %s" % (len(issues), stats))
    try:
        import acs_layout as L
        L.autofix(out)
        issues, stats = V.validate_building(out)
        print("[ACS-EDIT] بعد الإصلاح الحسابي: %d مخالفة · %s" % (len(issues), stats))
    except Exception as e:
        print("[ACS-EDIT] تخطّي الإصلاح: %s" % str(e)[:200])
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


def _plan(description, model=None, btype="residential"):
    mt = int(os.environ.get("ACS_MAX_TOKENS_PLAN", "16000"))
    out = validate(extract_json(call_llm(description, model=model, max_tokens=mt,
                                         btype=btype, user_msg=PLAN_MSG)))
    return out


def _detail_group(description, plan_ctx, rooms, model, btype):
    mt = int(os.environ.get("ACS_MAX_TOKENS_DETAIL", "24000"))
    body = (DETAIL_MSG + "سياق الخطة (للاتّساق فقط):\n" + plan_ctx +
            "\n\nالمناطق المطلوب تفصيلها الآن:\n" +
            json.dumps(rooms, ensure_ascii=False) +
            "\n\nالطلب الأصلي كاملاً (نفّذ منه ما يخصّ هذه المناطق):\n" + description)
    txt = call_llm(body, model=model, max_tokens=mt, truncate=False, btype=btype, user_msg="")
    data = extract_json(txt)
    return data.get("rooms") or (data if isinstance(data, list) else [])


def understand_deep(description, model=None, group_size=None, workers=None, strict=False, btype=None):
    """توليد على مرحلتين مع تفصيل متوازٍ — للطلبات الضخمة."""
    import acs_validate as V
    btype = detect_type(description, btype)
    print("[ACS-DEEP] نوع المبنى: %s" % btype)

    desc = description + (STRICT_RULE if strict else "")
    building = _plan(desc, model=model, btype=btype)
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

    def work(k):
        tmpl, rs = groups[k]
        try:
            det = _detail_group(desc, ctx, rs, model, btype)
            print("[ACS-DEEP] مجموعة %d/%d ✓ (%d منطقة)" % (k + 1, len(groups), len(det)))
            return tmpl, det
        except Exception as e:
            print("[ACS-DEEP] مجموعة %d/%d ✗ %s — نُبقي الخطة الأولية." % (k + 1, len(groups), str(e)[:160]))
            return tmpl, rs

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
                new["rect"] = r.get("rect", new.get("rect"))     # الخطة تحكم المواضع
                new.pop("brief", None)
                merged.append(new)
            else:
                r.pop("brief", None); merged.append(r)
        merged.extend(by_id.values())                            # مناطق أضافها التفصيل
        building["floors"][tmpl]["rooms"] = merged

    building.setdefault("meta", {})["type"] = building["meta"].get("type", btype)
    building["meta"]["acs_mode"] = "deep"
    if strict:
        building["meta"]["strict"] = True
        building["meta"]["added"] = []
    reqs = building["meta"].get("requirements") or []
    print("[ACS-DEEP] تقرير التغطية: %d بند من طلب العميل" % len(reqs))
    issues, stats = V.validate_building(building)
    print("[ACS-DEEP] بعد الدمج: %d مخالفة · %s" % (len(issues), stats))
    try:
        import acs_layout as L
        L.autofix(building)
        issues, stats = V.validate_building(building)
        print("[ACS-DEEP] بعد الإصلاح الحسابي: %d مخالفة · %s" % (len(issues), stats))
    except Exception as e:
        print("[ACS-DEEP] تخطّي الإصلاح: %s" % str(e)[:200])
    building["meta"]["acs_issues"] = len(issues)
    return building


def _should_go_deep(description):
    mode = os.environ.get("ACS_DEEP", "auto").lower()
    if mode in ("1", "on", "always", "true"):
        return True
    if mode in ("0", "off", "never", "false"):
        return False
    d = description or ""
    # طلب طويل، أو مرقّم ببنود كثيرة، أو مبنى صناعي = مخرج أكبر من نداء واحد
    bullets = len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", d))
    return len(d) > 2200 or bullets >= 12


def understand(description, model=None, repair_rounds=None, deep=None, strict=False, btype=None):
    """وصف → Building JSON، مع حلقة تحقّق وإصلاح ذاتي.
    الطلبات الكبيرة تُوجَّه تلقائياً إلى التوليد على مرحلتين حتى لا يُقطع أي بند."""
    import acs_validate as V
    if deep if deep is not None else _should_go_deep(description):
        try:
            return understand_deep(description, model=model, strict=strict, btype=btype)
        except E.AcsApiError as e:
            # عطل دائم (مفتاح/صلاحية/نموذج مرفوض) لا يُصلحه تبديل المسار — لا تُخفِه
            # خلف مسار ثانٍ يفشل بنفس السبب بعد دقائق.
            if e.code in (E.ACS_UPSTREAM_NOT_CONFIGURED, E.ACS_UPSTREAM_AUTH,
                          E.ACS_UPSTREAM_PERMISSION, E.ACS_UPSTREAM_MODEL_REJECTED,
                          E.ACS_NOT_CONFIGURED):
                raise
            print("[ACS-DEEP] فشل المسار العميق (%s) — نعود للنداء الواحد." % e.code)
        except Exception as e:
            print("[ACS-DEEP] فشل المسار العميق (%s) — نعود للنداء الواحد." % str(e)[:200])

    btype = detect_type(description, btype)
    rounds = int(repair_rounds if repair_rounds is not None
                 else os.environ.get("ACS_REPAIR_ROUNDS", "1"))

    building = validate(extract_json(call_llm(
        description + (STRICT_RULE if strict else ""), model=model, btype=btype)))
    building.setdefault("meta", {}).setdefault("type", btype)
    if strict:
        building["meta"]["strict"] = True
        building["meta"]["added"] = []
    issues, stats = V.validate_building(building)
    print("[ACS-CHECK] جولة 0 (%s): %d مخالفة · %s" % (btype, len(issues), stats))

    for i in range(rounds):
        if not issues:
            break
        print("[ACS-CHECK] إرسال %d مخالفة للإصلاح (جولة %d)…" % (len(issues), i + 1))
        try:
            fixed = validate(extract_json(call_llm_repair(description, building, issues, model=model)))
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

    # ── إصلاح حسابي نهائي: التداخلات والفتحات والنقاط (بلا LLM، مجاني ومضمون) ──
    try:
        import acs_layout as L
        rep = L.autofix(building)
        issues, stats = V.validate_building(building)
        print("[ACS-FIX] إصلاح حسابي: حُرّكت %d غرفة · تداخل متبقٍ %d · %s"
              % (rep["moved"], rep["remaining"], "؛ ".join(rep["tight"]) or "المساحات تسع"))
        print("[ACS-CHECK] بعد الإصلاح الحسابي: %d مخالفة · %s" % (len(issues), stats))
    except Exception as e:
        print("[ACS-FIX] تخطّي الإصلاح الحسابي: %s" % str(e)[:200])

    building.setdefault("meta", {})["acs_issues"] = len(issues)
    if issues:
        print("[ACS-CHECK] مخالفات متبقية (%d). أمثلة:\n%s"
              % (len(issues), V.format_issues(issues, 8)))
    return building

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
