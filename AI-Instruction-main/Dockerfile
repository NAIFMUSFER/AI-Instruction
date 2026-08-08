# خادم محرّك الفهم — جاهز للنشر (Render / Railway / Fly.io / أي مزوّد يدعم Docker)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY acs_understand.py acs_understand_api.py acs_validate.py acs_layout.py ./
ENV ACS_LLM_MODEL=claude-sonnet-5
EXPOSE 8000
CMD ["sh","-c","uvicorn acs_understand_api:app --host 0.0.0.0 --port ${PORT:-8000}"]
