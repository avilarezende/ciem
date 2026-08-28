# Guia de configuração

Referência de todos os arquivos e variáveis que precisam ser preenchidos antes do deploy.

## Arquivos de configuração

| Arquivo | Montado no Docker? | O que preencher |
|---------|-------------------|-----------------|
| `.env` | Sim (via `env_file`) | Credenciais e escolha do provedor LLM |
| `config/clients.yaml` | Sim (volume) | Instituições clientes e links monitorados |
| `config/modules.yaml` | Sim | Módulos ativos (canais e fontes RAG) |
| `config/sources.yaml` | Sim | Parâmetros não sensíveis das fontes |

## Provedor de IA (`LLM_PROVIDER`)

| Valor | Quando usar | Variáveis obrigatórias |
|-------|-------------|------------------------|
| `ollama` | Desenvolvimento, sem custo, on-premise | `OLLAMA_HOST`, `OLLAMA_MODEL` |
| `gemini` | Produção leve com tier gratuito Google | `GEMINI_API_KEY` |
| `openai` | Produção com modelos OpenAI | `OPENAI_API_KEY` |
| `azure` | Ambiente corporativo Microsoft | `AZURE_OPENAI_*` (todas) |
| `grok` | Modelos xAI Grok | `GROK_API_KEY` |

Altere `LLM_PROVIDER` no `.env` e reinicie o container `engine`.

## Fontes de monitoração

### Zabbix

| Variável | Descrição |
|----------|-----------|
| `ZABBIX_URL` | URL base do servidor (ex.: `https://zabbix.pop-se.rnp.br`) |
| `ZABBIX_USER` | Usuário com permissão de API |
| `ZABBIX_PASSWORD` | Senha do usuário |
| `ZABBIX_MAINTENANCE_DAYS` | Quantos dias à frente buscar manutenções (padrão: 30) |

Ative em `config/modules.yaml` → `fontes_rag.zabbix.enabled: true` e suba `--profile sources`.

### Cacti

| Variável | Descrição |
|----------|-----------|
| `CACTI_URL` | URL base do Cacti |
| `CACTI_USER` | Usuário web com acesso a hosts/gráficos |
| `CACTI_PASSWORD` | Senha |

### Grafana

| Variável | Descrição |
|----------|-----------|
| `GRAFANA_URL` | URL base do Grafana |
| `GRAFANA_API_KEY` | Service Account Token com leitura de alertas/anotações |
| `GRAFANA_ANNOTATION_DAYS` | Janela de anotações em dias |

## Instituições (`config/clients.yaml`)

Para cada instituição conectada ao PoP-SE:

```yaml
- sigla: SIGLA          # identificador curto (IFS, UFS...)
  nome: "Nome completo"
  aliases: [...]        # como o usuário pode se referir
  links_monitorados:
    - zabbix_host: "..." # deve existir no Zabbix
```

## Checklist de deploy

- [ ] `.env` criado a partir de `.env.example`
- [ ] `POSTGRES_PASSWORD` alterado
- [ ] `LLM_PROVIDER` definido e API key configurada (se remoto)
- [ ] `config/clients.yaml` com instituições reais
- [ ] Fontes necessárias habilitadas em `config/modules.yaml`
- [ ] Credenciais Zabbix/Cacti/Grafana no `.env` (se aplicável)
- [ ] `docker compose --profile core --profile sources up -d`

## Logos

Os logos oficiais foram obtidos de https://www.pop-se.rnp.br:

- `services/web/public/assets/logo-popse.png` — PoP-SE PRO RNP
- `services/web/public/assets/logo-rnp.png` — RNP

Fonte: `/assets/img/POP_SE_PRORNP_RGB_PNG.png` e `/assets/img/rnp-logo-pegb.png`
