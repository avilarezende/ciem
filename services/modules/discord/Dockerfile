FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir httpx discord.py==2.4.0
COPY shared /app/shared
COPY services/modules/discord /app/module
ENV PYTHONPATH=/app
CMD ["python", "-m", "module.main"]
