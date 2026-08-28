FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir httpx msal beautifulsoup4
COPY shared /app/shared
COPY services/modules/email_microsoft /app/module
ENV PYTHONPATH=/app
CMD ["python", "-m", "module.main"]
