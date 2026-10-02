# CI/CD — CIEM

## Visão geral

| Workflow | Arquivo | Gatilho | Função |
|----------|---------|---------|--------|
| **CI** | `.github/workflows/ci.yml` | push/PR em `main`/`develop`, `workflow_dispatch` | Gitleaks (`.gitleaks.toml`), bandit, pip-audit, lint, testes, build Docker, compose |
| **CD** | `.github/workflows/cd.yml` | push em `main`, tags `v*`, manual | Publica imagens no GHCR (`ghcr.io/avilarezende/ciem-*`) |
| **Dependabot** | `.github/dependabot.yml` | semanal | Atualiza GitHub Actions e pip |

## Sincronizar Origin → GitHub

O Cloud Agent trabalha no remote Origin; o **CI/CD (Actions + GHCR)** roda em `github.com/avilarezende/ciem`.

```bash
# Opção A — token (PAT com scopes: repo, workflow, write:packages)
export GH_TOKEN=ghp_...
chmod +x scripts/sync-github.sh
./scripts/sync-github.sh

# Opção B — gh CLI
gh auth login
./scripts/sync-github.sh
```

Branches publicadas pelo script (quando existirem localmente/`origin`):

- `cursor/fix-gitleaks-tests-a834`
- `cursor/owasp-hardening-a834`

Depois abra/acompanhe PRs em https://github.com/avilarezende/ciem/pulls e o CI em https://github.com/avilarezende/ciem/actions.

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
CONFIG_PATH=./config CIEM_SECRET_KEY=teste CIEM_GRAFANA_TOKEN=teste \
  PYTHONPATH=shared:services/core pytest tests -v

# Equivalente ao job security-scan (bandit)
pip install bandit
bandit -q -r shared services --skip B101,B110,B311

# Validação do compose — a CI fornece chaves dummy obrigatórias (CIEM_SECRET_KEY
# e CIEM_GRAFANA_TOKEN) apenas para validação de sintaxe:
CIEM_SECRET_KEY=ci-dummy CIEM_GRAFANA_TOKEN=ci-dummy \
  docker compose -f deploy/docker/docker-compose.yml config --quiet
```

## Releases versionadas

```bash
git tag v0.2.0
git push origin v0.2.0
```
