FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir httpx fastapi uvicorn
COPY shared /app/shared
COPY services/modules/whatsapp /app/module
ENV PYTHONPATH=/app
CMD ["python", "-m", "module.main"]
