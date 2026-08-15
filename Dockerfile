# خادم محرّك الفهم — جاهز للنشر (Render / Railway / Fly.io / أي مزوّد يدعم Docker)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY acs_understand.py acs_understand_api.py acs_validate.py acs_layout.py ./
# عقد الأخطاء الموحّد وعقد ميزانية المخرج — بلا هذين لا تقلع الواجهة (ImportError)
# وacs_plan_chunks عقد الخطّة المحدود (KI-24): يستورده acs_understand مباشرةً.
COPY acs_api_errors.py acs_generation.py acs_plan_chunks.py acs_provider.py ./
# سجل البرامج (المصدر الوحيد للحقيقة) وطبقة المشروع — لازمة للتشغيل
COPY acs_programs.py acs_programs.json acs_project.py acs_relations.py acs_navigation.py acs_egress.py acs_distance.py ./
# سجلّ محرّك القواعد (بلا محتوى تنظيمي) — بيانات لا شيفرة
COPY acs_rules.py acs_rules.json ./
# خط استيراد المصادر والتحقّق من الحزم (تجهيزات اصطناعية فقط)
COPY acs_ingest.py acs_ingest.json acs_sources.json ./
# طبقة الإشغال النظامي وسياق الكود (تصنيفات اصطناعية فقط)
COPY acs_occupancy.py acs_occupancy.json ./
# تثبيت النتائج على مراجعة النموذج (تقنين + SHA-256)
COPY acs_revision.py acs_revision.json ./
# مصرِّف الهندسة المعمارية وغلاف المبنى (هندسة فقط — لا إنشاء ولا كود)
COPY acs_arch.py acs_arch.json ./
# النموذج الإنشائي (تمثيل فقط — لا تصميم ولا أحمال ولا مطابقة كود)
COPY acs_struct.py acs_struct.json ./
# أنظمة الكهروميكانيك (تمثيل فقط — لا تصميم ولا حسابات ولا مطابقة كود)
COPY acs_mep.py acs_mep.json ./
# الحريق وسلامة الأرواح (تمثيل وطوبولوجيا فقط — لا محرّك حريق ولا مطابقة)
COPY acs_fls.py acs_fls.json ./
# التنسيق بين التخصّصات (كشف وتتبّع فقط — لا إصلاح تلقائي ولا إعادة تصميم)
COPY acs_coord.py acs_coord.json ./
# العرض البصري والتقديم (تصوير يحفظ الهندسة — لا تعديل هندسي ولا توليد هندسة)
COPY acs_visual.py acs_visual.json ./
# ── طبقات المعالجة المضافة في تصحيح ثقة الإنتاج ──
# سلطة التغيير الهندسي: السجلّ الآليّ ومحرّك الاقتراحات (F-01)
COPY acs_engineering_authority.py acs_engineering_changes.json ./
# أمن الرفع (F-05/F-19)، الحدّ الموزّع (F-04)، إلغاء التوليد (F-06)
# KI-14/F-46: مجمّع العمل الحاسوبيّ — بلا هذا الملفّ لا يقلع الخادم.
COPY acs_upload_security.py acs_rate_limit.py acs_generation_job.py acs_cpu_pool.py ./
# السجلّ المنظَّم (F-18) وأصل البناء (provenance)
COPY acs_logging.py acs_build_info.py ./

ENV ACS_LLM_MODEL=claude-sonnet-5
# F-25: بلا هذا يبقى ACS_ENV = "development" في الإنتاج، فيصير IS_PRODUCTION
# في acs_logging مساوياً False، وSTACK_TRACES = not IS_PRODUCTION أي True —
# فيُطبع أثر الاستدعاء كاملاً في سجلّ الإنتاج عند كل عطل غير معالَج، وهو
# بالضبط ما ادّعى F-18 إغلاقه. ويمنع أيضاً acs_rate_limit من رفع
# PRODUCTION_WITHOUT_DISTRIBUTED_BACKEND حين يعمل الحدّ على ذاكرة العملية وحدها.
ENV ACS_ENV=production
# F-26: بلا USER كانت كل عملية داخل الحاوية تعمل بـuid 0 — python:3.11-slim
# لا يحدّد مستخدماً. لا شيء هنا يحتاج الجذر بعد انتهاء pip install.
RUN useradd --create-home --uid 10001 acs && chown -R acs:acs /app
USER acs
EXPOSE 8000
CMD ["sh","-c","uvicorn acs_understand_api:app --host 0.0.0.0 --port ${PORT:-8000}"]
