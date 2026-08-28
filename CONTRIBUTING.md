# Contribuindo com o Conversador PoP-SE

Obrigado por contribuir! Este guia ajuda novos mantenedores a trabalhar no projeto com segurança e consistência.

## Pré-requisitos

- Docker e Docker Compose
- Python 3.12+ (para testes locais)
- Conta GitHub com acesso ao repositório

## Configuração local

```bash
git clone https://github.com/SEU-USUARIO/conversador-pop-se.git
cd conversador-pop-se
cp .env.example .env
# Edite .env e config/*.yaml conforme docs/CONFIGURATION.md

docker compose --profile core up -d --build
docker compose exec ollama ollama pull llama3.2:3b
```

## Testes e lint

```bash
pip install -r requirements-dev.txt
export PYTHONPATH=services/engine:shared:services/modules/sources
export CONFIG_PATH=./config
pytest tests -v
ruff check services/engine shared tests
```

## Fluxo de trabalho Git

1. Crie uma branch a partir de `main`: `git checkout -b feature/minha-mudanca`
2. Faça commits pequenos e descritivos em português ou inglês
3. Abra Pull Request — o template guia a revisão
4. Aguarde o **CI** (lint, testes, build Docker) passar
5. Após merge em `main`, o **CD** publica imagens no GitHub Container Registry (GHCR)

## Publicar no GitHub (primeira vez)

```bash
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/conversador-pop-se.git
git push -u origin main
```

Substitua `SEU-USUARIO` pelo seu usuário GitHub.

## Secrets recomendados (GitHub → Settings → Secrets)

| Secret | Uso |
|--------|-----|
| *(nenhum obrigatório para CI básico)* | CI usa `GITHUB_TOKEN` automaticamente |
| `GEMINI_API_KEY` etc. | Apenas se adicionar testes de integração com APIs reais |

## Adicionar módulo novo

1. Crie pasta em `services/modules/<nome>/`
2. Registre em `config/modules.yaml` e `docker-compose.yml` (profile)
3. Documente variáveis em `.env.example`
4. Atualize `docs/MODULES.md`

## Código de conduta

Mantenha comunicação respeitosa. O bot em produção deve ser polido — o time de desenvolvimento também.
