# CI/CD — Conversador PoP-SE

## Visão geral

| Workflow | Arquivo | Gatilho | Função |
|----------|---------|---------|--------|
| **CI** | `.github/workflows/ci.yml` | push/PR em `main` ou `develop` | Lint (Ruff), testes (Pytest), build Docker, validação compose |
| **CD** | `.github/workflows/cd.yml` | push em `main`, tags `v*` | Publica imagens no GHCR |
| **Dependabot** | `.github/dependabot.yml` | semanal | Atualiza GitHub Actions e pip |

## CI — Integração contínua

Executa em todo Pull Request:

1. **lint-and-test** — qualidade e regressão
2. **docker-build** — garante que Dockerfiles compilam
3. **compose-validate** — `docker compose config` sem erros

### Rodar localmente (equivalente ao CI)

```bash
pip install -r requirements-dev.txt
ruff check services/engine shared tests
PYTHONPATH=services/engine:shared:services/modules/sources CONFIG_PATH=./config pytest tests -v
docker compose config --quiet
```

## CD — Entrega contínua

Após merge em `main`, imagens são publicadas em:

```
ghcr.io/<owner>/conversador-pop-se-engine:<tag>
ghcr.io/<owner>/conversador-pop-se-web:<tag>
ghcr.io/<owner>/conversador-pop-se-module-sources:<tag>
```

### Usar imagem publicada em produção

```yaml
# docker-compose.override.yml (exemplo)
services:
  engine:
    image: ghcr.io/SEU-USUARIO/conversador-pop-se-engine:main
```

### Releases versionadas

```bash
git tag v0.2.0
git push origin v0.2.0
```

O CD publica tags semver no GHCR.

## Branching sugerido

- `main` — estável, deployável
- `develop` — integração de features
- `feature/*` — branches de trabalho

## Proteção de branch (recomendado)

No GitHub → Settings → Branches → Add rule para `main`:

- Require status checks: `lint-and-test`, `docker-build`, `compose-validate`
- Require pull request reviews (1 aprovador)

## Manutenção por terceiros

1. Fork ou clone do repositório
2. Leia `CONTRIBUTING.md` e `docs/CONFIGURATION.md`
3. Configure `.env` local (nunca commitar)
4. Abra PRs pequenos com descrição clara
