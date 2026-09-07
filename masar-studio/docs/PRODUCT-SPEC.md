# MASAR Studio 4 — Product Specification

## 1. الوعد

مسار يحول طلب المالك إلى **نموذج تصميم قابل للفحص والتعديل والتراجع والتسليم** بدل صورة نهائية غير قابلة للتحرير.

الأولوية: **حفظ الطلب وصحة النموذج → وضوح أثر التعديل → سهولة authoring → جودة العرض والتبادل**.

## 2. الرحلة الأساسية

1. وصف أو مرجع أو مشروع MASAR أو IFC4 مدعوم.
2. عرض ما فُهم مع فصل requested / assumed / derived/imported.
3. تأكيد القرارات المؤثرة قبل إنشاء/استبدال المشروع.
4. Canonical model واحد يقود 2D و3D والجداول والتقرير.
5. تعديل مباشر أو أمر عربي ينتج Candidate لا Commit.
6. فحص locks/geometry/hosts ثم Impact Preview.
7. Cancel أو Commit صريح → Revision جديد.
8. مقارنة نسخ/بدائل/قياس/تعليقات ومراجعة خارجية.
9. تسليم متعدد الصيغ مع حدود كل صيغة مكتوبة.

## 3. Canonical authoring model

كل room قد يحمل:

- rectangle عبر `x/y/w/d`، أو
- `footprint` متعامد غير مستطيل مع bbox متطابق.
- doors canonical.
- windows canonical (`side,width,height,sill,offset,typeId`).

المشروع قد يحمل `authoring` لتعريف wall/window types. هذا الحقل اختياري للمشاريع القديمة؛ defaults تطبق عند القراءة دون ترقية ادعاءات هندسية.

## 4. Authoring 4.0

### Composite walls
- external/internal types.
- طبقات مسماة وسمك لكل طبقة.
- سمك إجمالي مشتق/متحقق.
- تغيير النوع/الطبقات يمر Preview/Commit.

### Windows/doors
- opening identity مستقرة.
- hosted على boundary side.
- fit/boundary checks.
- 2D + 3D + schedule + IFC relationships.

### Orthogonal spaces
- UI يوفر حاليًا عملية L-notch محافظة بدل vertex editor حر.
- area وwall derivation وDXF وIFC تستخدم polygon الحقيقي.
- width/depth المعروضان للمضلع هما bbox وموسومان بذلك.

## 5. أنواع المشروع والتوليد

`villa`, `chalet`, `office`, `warehouse`, `retail`.

المولد الأساسي لا يدعي تلقائيًا توليد شكل معماري حر؛ ينتج baseline deterministic ثم يمكن authoring فوقه. مصعد/مسبح/مواقف عناصر مفاهيمية، والارتدادات الافتراضية layout strategy وليست اشتراطًا حكوميًا.

## 6. أوامر التحرير المدعومة

تشمل rename/move/resize/expand/swap/near/door/window/notch وغيرها من الأوامر المحددة في parser. النص غير القابل للحل يرفض بدل التخمين. AI السحابي، إذا فُعّل، يقترح command فقط؛ لا يملك commit authority.

## 7. Preview وSafe Reflow

- Source model لا يتغير أثناء preview.
- blockers تمنع commit.
- stale preview يرفض.
- locked geometry محمي.
- Safe Reflow يحاول حالات مستطيلة محافظة فقط؛ لا يحرك عنصرًا مثبتًا ولا يعيد تشكيل polygon تلقائيًا.

## 8. Building Model Center

يشتق:

- Spaces.
- Composite Walls.
- Hosted Doors/Windows.
- Slabs.
- Conceptual Roof.
- Site features.

ثم ينتج element schedule وrequirements matrix وauthoring quality results وdelivery-readiness مفاهيمي.

## 9. Quality pack

`masar-authoring-quality-2026.2`:

- versioned.
- `authority=product-heuristic`.
- `compliance=false`.
- checks داخلية مثل host/غلاف النوافذ واتساق طبقات الجدار.
- لا تغير structural/MEP/fire/accessibility/regulatory من unchecked إلى pass.

## 10. IFC4 Authoring Exchange

### Export
ينشئ IFC4 STEP يتضمن hierarchy للمشروع/الموقع/المبنى/الأدوار ومساحات وجدران وبلاطات وسقف تنسيقي وأبواب ونوافذ وفتحات وmaterial layers.

- rectangle → `IfcRectangleProfileDef`.
- orthogonal polygon → `IfcArbitraryClosedProfileDef` + `IfcPolyline`.
- hosted openings → `IfcOpeningElement` + RelVoids/RelFills.

### Import
subset محافظ فقط:

- IFC4.
- `IfcBuildingStorey`.
- `IfcSpace` بملف rectangle أو arbitrary closed polyline متعامد.
- أبواب/نوافذ ذات MASAR tags من export المدعوم.

الاستيراد ينشئ مشروعًا جديدًا بعد acknowledgment صريح. لا يستورد discipline models عامة ولا يخمّن geometry غير مدعومة.

## 11. 2D/3D/DXF

- SVG يرسم footprint الحقيقي ويظهر windows/doors/issues/preview/measurement.
- 3D software presentation يستخدم composite wall thickness ويفرغ hosted openings.
- polygon floors تتحلل إلى خلايا مستطيلة بنفس المساحة.
- DXF يصدر LWPOLYLINE مغلقة بعدد vertices الحقيقي.
- OBJ presentation geometry وليس BIM semantic format.

## 12. History/Review/Persistence

- history append-only مع branch metadata.
- compare revisions.
- SQLite projects مع optimistic concurrency.
- share snapshots ثابتة 1/7/30 يومًا وقابلة للإلغاء.
- المراجع يضيف comment إلى target حقيقي؛ لا يعدل snapshot/model.

## 13. Definition of done لـ4.0

الإصدار يعتبر منجزًا فقط إذا:

- check/build/test/browser gates كلها خضراء.
- standalone بلا external runtime dependencies.
- node tests تغطي authoring/IFC/polygons/windows/security.
- browser flows تغطي UI لهذه المسارات.
- ZIP النهائي نفسه يُفك ويعاد اختباره دون تعديل.
- الحدود الهندسية/الخارجية تبقى معلنة.
