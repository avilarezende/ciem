# CI/CD — CIEM

## Visão geral

| Workflow | Arquivo | Gatilho | Função |
|----------|---------|---------|--------|
| **CI** | `.github/workflows/ci.yml` | push/PR em `main` ou `develop` | Lint, testes, build Docker, validação compose |
| **CD** | `.github/workflows/cd.yml` | push em `main`, tags `v*` | Publica imagens no GHCR |
| **Dependabot** | `.github/dependabot.yml` | semanal | Atualiza GitHub Actions e pip |

## Imagens publicadas (GHCR)

```
ghcr.io/rodrigo-rezende/ciem-core:<tag>
ghcr.io/rodrigo-rezende/ciem-portal:<tag>
ghcr.io/rodrigo-rezende/ciem-proxy:<tag>
ghcr.io/rodrigo-rezende/ciem-module-zabbix:<tag>
ghcr.io/rodrigo-rezende/ciem-module-cacti:<tag>
ghcr.io/rodrigo-rezende/ciem-module-nagios:<tag>
ghcr.io/rodrigo-rezende/ciem-module-topdesk:<tag>
ghcr.io/rodrigo-rezende/ciem-module-inventory:<tag>
ghcr.io/rodrigo-rezende/ciem-module-syslog:<tag>
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
