# خادم محرّك الفهم — جاهز للنشر (Render / Railway / Fly.io / أي مزوّد يدعم Docker)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY acs_understand.py acs_understand_api.py acs_validate.py acs_layout.py ./
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
ENV ACS_LLM_MODEL=claude-sonnet-5
EXPOSE 8000
CMD ["sh","-c","uvicorn acs_understand_api:app --host 0.0.0.0 --port ${PORT:-8000}"]
