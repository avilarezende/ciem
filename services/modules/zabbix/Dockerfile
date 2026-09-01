FROM python:3.12-slim

WORKDIR /app

COPY shared/ciem_common /app/shared/ciem_common
COPY services/modules/zabbix/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/modules/zabbix/main.py .
COPY services/modules/zabbix/config.example.yaml ./config.example.yaml

ENV PYTHONPATH=/app/shared
ENV CONFIG_PATH=/app/config.yaml

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
