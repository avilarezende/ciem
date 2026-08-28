FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir httpx python-telegram-bot==21.9
COPY shared /app/shared
COPY services/modules/telegram /app/module
ENV PYTHONPATH=/app
CMD ["python", "-m", "module.main"]
