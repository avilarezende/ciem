FROM python:3.12-slim@sha256:02108f5d322dd89f1c9e552442c25acb0543dfdbc455693a5599624f20d9155d

WORKDIR /app

COPY shared/ciem_common /app/shared/ciem_common
COPY services/modules/cacti/requirements.lock .
RUN --mount=type=secret,id=egress_ca \
    if [ -f /run/secrets/egress_ca ]; then export PIP_CERT=/run/secrets/egress_ca; fi; \
    pip install --no-cache-dir --require-hashes -r requirements.lock

COPY services/modules/cacti/main.py .
COPY services/modules/cacti/config.example.yaml ./config.example.yaml

ENV PYTHONPATH=/app/shared
ENV CONFIG_PATH=/app/config.yaml

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
