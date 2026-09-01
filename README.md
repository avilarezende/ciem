# CIEM

**Cloud Infrastructure & Environment Management**

[![CI](https://github.com/rodrigo-rezende/ciem/actions/workflows/ci.yml/badge.svg)](https://github.com/rodrigo-rezende/ciem/actions/workflows/ci.yml)
[![CD](https://github.com/rodrigo-rezende/ciem/actions/workflows/cd.yml/badge.svg)](https://github.com/rodrigo-rezende/ciem/actions/workflows/cd.yml)

API leve em Python para gerenciar ambientes de nuvem, validar configurações e expor métricas de saúde de infraestrutura. Projetado para integração com **Cursor Cloud Agents**, **GitHub** e pipelines de entrega contínua.

## Recursos

- API REST com FastAPI
- Validação de ambientes e snapshots
- Health checks e métricas Prometheus
- Containerização com Docker
- CI/CD com GitHub Actions (lint, testes, build, publicação no GHCR)
- Suporte a Cursor Cloud Agent (`environment.json`)

## Início rápido

### Pré-requisitos

- Python 3.12+
- Docker e Docker Compose (opcional)

### Desenvolvimento local

```bash
git clone https://github.com/rodrigo-rezende/ciem.git
cd ciem
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn ciem.main:app --reload --app-dir src
```

Acesse: **http://localhost:8000/docs**

### Docker

```bash
docker compose up -d --build
curl http://localhost:8000/health
```

## Estrutura

```
src/ciem/          # Código-fonte da API
tests/             # Testes automatizados
.github/workflows/ # CI/CD
docs/              # Documentação
```

## CI/CD

| Workflow | Gatilho | Função |
|----------|---------|--------|
| **CI** | push/PR em `main` ou `develop` | Ruff, Pytest, build Docker |
| **CD** | push em `main`, tags `v*` | Publica imagem no GHCR |

Detalhes: [docs/CI_CD.md](docs/CI_CD.md)

## Cursor Cloud Agent

Este repositório inclui configuração para Cloud Agents. Após clonar:

```bash
pip install -r requirements-dev.txt
```

## Licença

MIT
