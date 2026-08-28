FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir httpx pyyaml beautifulsoup4 lxml
COPY shared /app/shared
COPY services/modules/sources/collectors /app/collectors
COPY services/modules/sources/main.py /app/main.py
COPY config /app/config
ENV PYTHONPATH=/app
ENV CONFIG_PATH=/app/config
CMD ["python", "main.py"]
