@echo off
copy /Y .env.example .env 2>nul
docker compose --profile core up -d --build
echo Aguardando servicos...
timeout /t 15 /nobreak >nul
docker compose exec ollama ollama pull llama3.2:3b
echo Conversador disponivel em http://localhost:8080
