# تصحيح دلالة السطح في IFC — 2026-11-11

الحالة عند إعداد هذا التقرير: تنفيذ واختبارات محلية في الفرع `claude/acs-roof-ifc-semantics-20261111`، فوق `ad45ef1992c85a4aa5309cd1adc12c265d55fff1`. لم يُرفع هذا التعديل بعد، ولا رقم PR له في هذا التقرير. تحقق CI منتظر، والتعديل غير منشور. نتائج CI السابقة تخص الإصدار السابق، وليست قبولًا لهذا التغيير.

## الخلل المثبت وسبب التغيير

كان `acs_bim.py` يحوّل كل مستوى canonical إلى `IfcBuildingStorey` وكل مستطيل غرفة إلى `IfcSpace`، ويسقط `kind: roof` وكون السطح غير مشغول. في شاهد دور واحد وغرفة مساحتها12م² وسطح افتراضي، أصبح ملف IFC يحتوي دورين وفراغين، بينما بقي scorecard الصحيح دورًا واحدًا ومساحة12م². لم يحمل IFC خصائص تميز السطح أو تستثنيه من المساحة. هذا تعارض في دلالة التصدير مع قرار المالك، وليس دليلًا على فساد حسابات المساحة الداخلية.

السلوك كان موصوفًا في القسم7 من `PRESENTATION-AND-CI-REPAIR.md`، لكن وصفه لا يشكل استثناءً معتمدًا من قرار أن السطح ليس دورًا. الاختبارات السابقة تحققت من هندسة فراغات السطح دون اختبار هذه الدلالة.

أُجري الاختبار الجديد قبل إصلاح الإنتاج: ثلاثة أساليب اختبار، مع16 فشلًا و13 خطأً بين الحالات الفرعية. يحفظ `acs-roof-ifc-before.log` النتيجة الأصلية. النسخة النهائية تضم أربعة أساليب؛ الرابع يضيف فحص حدود الأسطح المتكررة والسالبة. لا ندعي أن عدد الاختبارات قبل التغيير وبعده متطابق.

وأُعيد تشغيل القارئ المستقل الحالي مقابل `acs_bim.py` و`tools/acs_plan_ifc_export.py` المحمّلين في الذاكرة من commit الأساس `ad45ef1`: فشل بسبب وجود `IfcBuildingStorey` إضافي. هذه مقارنة جزئية لوحدتين تاريخيتين باستخدام التبعيات المشتركة الحالية، وليست checkout تاريخيًا كاملًا أو تشغيلًا منشورًا. هاشا الوحدتين ونطاق المقارنة في `acs-roof-ifc-reader-before.log`.

## السلوك الجديد وحدوده

- وحده `kind: "roof"` الصريح يغيّر التصنيف؛ اسم المستوى أو القالب `roof` لا يمنح استثناءً.
- يمثل كل مستطيل سطح `IfcSpatialZone` من نوع `USERDEFINED`، مع `ObjectType=ACS_UNOCCUPIED_ROOF_REFERENCE`. تحفظ المنطقة معرّف المصدر وGUID وحدود المستطيل والمنسوب. تربطها بالمبنى علاقة `IfcRelReferencedInSpatialStructure`، ولا تدخل في تجميع الأدوار أو احتواء الفراغات.
- تضم `ACS_RoofReference` خصائص `LevelKind=roof` و`IsOccupied=false` و`CountsInFloorArea=false`، ومعرّفي العنصر والمستوى الأصليين. لا ينشأ `IfcRoof` مادي أو مقدار مساحة مبنية.
- يبقى اسم API التوافقي `SPACES_ONLY`. يوضح manifest والreceipt المحتوى الفعلي: `SPACES_AND_UNOCCUPIED_ROOF_REFERENCES`، مع عدد مستقل لمستويات السطح ومراجعه. `level_count` و`space_count` يستثنيان الأسطح.
- الارتفاع المعلن الموجب يعطي امتدادًا مرجعيًا مجسمًا. الصفر المعلن يعطي `IfcFaceBasedSurfaceModel` مستويًا، دون epsilon أو ارتفاع بديل. سطح helper القديم الذي لا يحفظ ارتفاعًا ويحمل `walls: none` وسجل المصدر الافتراضي يعطي مرجع بصمة مستويًا فقط؛ لا تتحول عبارة المصدر إلى حقيقة هندسية عن ارتفاع الدروة.
- تميز exchange وPset وmanifest وreceipt بين الحالتين: `ReferenceGeometry=FOOTPRINT_SURFACE` و`CanonicalHeightDeclared=false` للمرجع بلا ارتفاع معلن؛ الصفر الصريح يحمل `CanonicalHeightDeclared=true`. السياسة العامة `REFERENCE_EXTENT_ONLY_NOT_STRUCTURAL`. `None` الصريح والقيم غير الصالحة والأبعاد المجهولة الأخرى لا تتحول إلى أبعاد مفترضة.
- يرفض `ALL` و`LEVELS` و`ENVELOPE_ONLY` إذا شمل الاختيار سطحًا صريحًا، وكذلك `SPACES_ONLY` مع `include_spaces=false` وسطح مختار. لا ملف ولا manifest عند الرفض؛ توجد رسالة عربية توجه إلى التصدير المرجعي المدعوم. اختيار مستويات عادية فقط يبقى مدعومًا. لا تُسقط جدران السطح أو بلاطاته أو عناصره المعمارية صامتًا.

هذا تمثيل مرجعي مفاهيمي، وليس سطحًا ماديًا كاملًا أو IFC معماريًا كاملًا. لا يثبت تصميم الدروة أو البلاطة أو التصريف أو العزل أو الوصول أو السلامة الإنشائية. تؤكد اختبارات المسار المعتمد ثبات canonical والهاش؛ لا يعدل التصدير النموذج أو الموافقة أو أقفال المصدر.

## الملفات التي تعالج السبب

| الملف | التغيير |
|---|---|
| `acs_bim.py` | فصل roof levels/references عن الأدوار والفراغات؛ التحقق من القيم؛ كتابة المناطق والأسطح المستوية والعلاقات والخصائص؛ فصل أعداد manifest |
| `tools/build_bim_browser.py` و`public/app/generated/bim.js` | المصدر والمخرج المولد للتصنيف نفسه والرفض نفسه وبيانات التصدير نفسها في المتصفح |
| `tools/acs_plan_ifc_export.py` | الحفاظ على اسم النطاق التوافقي ونقل وصف المحتوى وسياسة الارتفاع وبيانات المراجع إلى receipt المرتبط بالمراجعة |
| `test_roof_ifc_semantics.py` و`roof_ifc_exchange_parity.js` |31 حالة مشتركة بين Python وJavaScript، وفحص metadata ورفض القيم غير الصالحة، وحدود الأسطح السالبة والمتكررة |
| `test_stair_ifc_reader.py` | عد الأدوار والفراغات والمراجع مستقلًا؛ GUID والعلاقة والخصائص؛ جميع حدود الفراغات والأسطح باقية بـ`places=6` |
| `test_geometry_independent_readers.py` | فحص السطح المعلن دون اعتماد بادئة الاسم، وإضافة حالة فعلية لسطح مستوٍ تجمع الصفر الصريح وارتفاع helper غير المعلن |

## نتائج التحقق المحلي

| الاختبار | النتيجة |
|---|---:|
| `test_roof_ifc_semantics.py` |4 أساليب ناجحة؛31 حالة مشتركة Python/JS، إضافة إلى فحوص الأعداد غير المنتهية |
| `test_stair_ifc_reader.py` |1 ناجح؛2 `IfcBuildingStorey` و50 `IfcSpace` و25 `IfcSpatialZone` |
| `test_geometry_independent_readers.py` |5 ناجحة، تشمل قراءة سطح الصفر الفعلي وتطابق `minZ` و`maxZ` مع منسوبه |
| `tests/phase8/test_bim.py` |526 assertion ناجحة |
| `test_stair_ifc_boundary.py` |8 ناجحة |
| `test_plan_ifc_export.py` |7 ناجحة |
| `test_connected_workspace.py` |34 ناجحة |
| `test_bim_space_precision.py` |2 ناجحتان |
| `test_residential_layout_fallback.py` |7 ناجحة |

تحققت مقارنة إضافية من تطابق **ملفات IFC نفسها بايتًا ببايت** في27 حالة: تسع عينات غير سطحية، في `ALL` و`SPACES_ONLY` و`LEVELS` المختار. لا تشمل هذه المطابقة كامل نتيجة التصدير أو manifest؛ بيانات النطاق والسياسة الجديدة تغير metadata وهاش الإعداد عمدًا. المقارنة تستخدم وحدة `acs_bim.py` من الأساس مع التبعيات الحالية؛ نطاقها موثق في سجلها.

القارئ الفعلي: IfcOpenShell `0.9.0.post1`. ثبتت الحزمة مع Shapely `2.2.0` وLark `1.3.1` في `/tmp/acs-roof-ifc-reader` فقط. بقيت pins وبيئة `.venv` المشتركة دون تعديل. استخدمت البيئة الموجودة NumPy `2.4.4` وezdxf `1.4.4` وpypdf `6.21.4` وPython `3.12.14`. أمر القارئين: `PYTHONPATH=/tmp/acs-roof-ifc-reader:. .venv/bin/python TEST_PATH`؛ الاختبارات العادية: `env -u PYTHONPATH .venv/bin/python TEST_PATH`.

هذه اختبارات محلية بمشروعات مصطنعة وردود حتمية، بلا استدعاء مزود مدفوع. لا تثبت جودة توليد AI حي أو عرضًا بصريًا أو نشرًا. لا skips ولا تخفيف لدقة الحدود؛ تحقق CI والنشر منفصلان وما زالا منتظرين لهذا التعديل.

## السجلات والمراجع

[manifest الأدلة](evidence/roof-ifc/manifest.json) يحفظ بصمات الملفات الثمانية المختبرة، ونسخ12 سجلًا، والنسخ الفعلية للتبعيات. لكل سجل هاش الأصل وهاش النسخة المحفوظة. لا يُسمح بالتطبيع إلا لمسافات/علامات tab النهائية قبل نهاية السطر، ويذكر manifest إن حدث؛ لا تحذف نتيجة أو رسالة فشل.

المراجع الأولية التي استند إليها اختيار النوع والعلاقة:

- [buildingSMART IFC4 FINAL — IfcSpatialZone](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcproductextension/lexical/ifcspatialzone.htm): منطقة لها placement وshape مستقلان؛ `USERDEFINED` يتطلب `ObjectType`.
- [buildingSMART IFC4 FINAL — IfcRelReferencedInSpatialStructure](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcproductextension/lexical/ifcrelreferencedinspatialstructure.htm): مرجع مكاني غير هرمي؛ `IfcSpatialZone` ليس `IfcSpatialStructureElement`، والعلاقة هنا تشير إليه من المبنى.

تعذر الفتح المباشر للصفحتين برمز403؛ استرجعت محتوياتهما من فهرس البحث للصفحات الرسمية. تضاف قراءة IfcOpenShell الفعلية للملفات المسلسلة إلى هذا الأساس المرجعي؛ لا يوجد ادعاء اعتماد جميع تطبيقات IFC المستهدفة.
