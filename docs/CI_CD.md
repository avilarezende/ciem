# CI/CD — CIEM

## Visão geral

| Workflow | Arquivo | Gatilho | Função |
|----------|---------|---------|--------|
| **CI** | `.github/workflows/ci.yml` | push/PR em `main` ou `develop` | Lint, testes, build Docker, validação compose |
| **CD** | `.github/workflows/cd.yml` | push em `main`, tags `v*` | Publica imagens no GHCR |
| **Dependabot** | `.github/dependabot.yml` | semanal | Atualiza GitHub Actions e pip |

## Imagens publicadas (GHCR)

```
ghcr.io/avilarezende/ciem-core:<tag>
ghcr.io/avilarezende/ciem-portal:<tag>
ghcr.io/avilarezende/ciem-proxy:<tag>
ghcr.io/avilarezende/ciem-module-zabbix:<tag>
ghcr.io/avilarezende/ciem-module-cacti:<tag>
ghcr.io/avilarezende/ciem-module-nagios:<tag>
ghcr.io/avilarezende/ciem-module-topdesk:<tag>
ghcr.io/avilarezende/ciem-module-inventory:<tag>
ghcr.io/avilarezende/ciem-module-syslog:<tag>
```

## Rodar localmente (equivalente ao CI)

```bash
pip install -r requirements-dev.txt
ruff check shared services/core services/modules tests
CONFIG_PATH=./config PYTHONPATH=shared:services/core pytest tests -v
docker compose -f deploy/docker/docker-compose.yml config --quiet
```

## Releases versionadas

```bash
git tag v0.2.0
git push origin v0.2.0
```
