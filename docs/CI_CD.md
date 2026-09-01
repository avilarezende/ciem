# CI/CD — CIEM

## Visão geral

| Workflow | Arquivo | Gatilho | Função |
|----------|---------|---------|--------|
| **CI** | `.github/workflows/ci.yml` | push/PR em `main` ou `develop` | Lint (Ruff), testes (Pytest), build Docker, validação compose |
| **CD** | `.github/workflows/cd.yml` | push em `main`, tags `v*` | Publica imagem no GHCR |
| **Dependabot** | `.github/dependabot.yml` | semanal | Atualiza GitHub Actions e pip |

## CI — Integração contínua

Executa em todo push e Pull Request:

1. **lint-and-test** — qualidade e regressão
2. **docker-build** — garante que o Dockerfile compila e o health check responde
3. **compose-validate** — `docker compose config` sem erros

### Rodar localmente

```bash
pip install -r requirements-dev.txt
ruff check src tests
PYTHONPATH=src pytest tests -v
docker build -t ciem:local .
docker compose config --quiet
```

## CD — Entrega contínua

Após merge em `main`, a imagem é publicada em:

```
ghcr.io/rodrigo-rezende/ciem:main
ghcr.io/rodrigo-rezende/ciem:<sha>
```

### Releases versionadas

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Sincronização GitHub ↔ Cursor Cloud

1. Repositório GitHub: `rodrigo-rezende/ciem`
2. Repositório Origin (Cursor): `rodrigo-rezende/ciem`
3. Espelhamento: `origin repo create-mirrored rodrigo-rezende/ciem`

## Proteção de branch (recomendado)

No GitHub → Settings → Branches → Add rule para `main`:

- Require status checks: `lint-and-test`, `docker-build`, `compose-validate`
- Require pull request reviews (1 aprovador)
