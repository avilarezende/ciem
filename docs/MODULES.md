# Módulos — Conversador PoP-SE

## Canais

| Módulo | Ativação | Variáveis |
|--------|----------|-----------|
| Web | `core` (padrão) | — |
| Telegram | `docker compose --profile telegram up` | `TELEGRAM_BOT_TOKEN` |
| Discord | `--profile discord` | `DISCORD_BOT_TOKEN` |
| WhatsApp | `--profile whatsapp` | `WHATSAPP_API_URL`, `WHATSAPP_API_TOKEN` |

## Fontes RAG

| Fonte | Status | Método |
|-------|--------|--------|
| Site PoP-SE | Implementado | HTTP crawler |
| Zabbix | **Implementado** | JSON-RPC API (manutenções + problemas) |
| Cacti | **Implementado** | Login web + extração hosts/gráficos |
| Grafana | **Implementado** | API (anotações + alertas) |
| E-mail Microsoft | Implementado | Graph API |
| MRTG | Stub | — |
| Topdesk | Stub | — |

Para habilitar coletores:

```bash
docker compose --profile core --profile sources up -d
docker compose --profile core --profile email up -d
```

## Adicionar nova fonte

1. Registrar em `config/modules.yaml` → `fontes_rag`
2. Adicionar bloco em `config/sources.yaml`
3. Implementar função `collect_<nome>()` em `services/modules/sources/main.py`
4. Mapear para coleção RAG: `operacional`, `institucional` ou `manutencoes`
