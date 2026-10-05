FROM python:3.12-slim@sha256:02108f5d322dd89f1c9e552442c25acb0543dfdbc455693a5599624f20d9155d

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/shared:/app/services/core

COPY shared/ ./shared/
COPY config/ ./config/
COPY services/core/ ./services/core/

RUN --mount=type=secret,id=egress_ca \
    if [ -f /run/secrets/egress_ca ]; then export PIP_CERT=/run/secrets/egress_ca; fi; \
    pip install --no-cache-dir --require-hashes -r services/core/requirements.lock

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "services/core"]
