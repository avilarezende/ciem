#!/usr/bin/env sh
# Sobe o núcleo: postgres + ollama + engine + web
set -e
docker compose --profile core up -d --build
echo "Aguardando engine..."
sleep 10
echo "Baixando modelo Ollama (primeira execução)..."
docker compose exec ollama ollama pull "${OLLAMA_MODEL:-llama3.2:3b}" || true
echo "Conversador disponível em http://localhost:${WEB_PORT:-8080}"
