# Grafana — Dashboards CIEM

O CIEM provisiona automaticamente **13 dashboards** (6 da plataforma incluindo Insights IA + 6 por módulo + visão de módulos).

## Dashboards por módulo

Cada sistema de monitoramento tem um dashboard dedicado:

| Módulo | Dashboard UID | URL |
|--------|---------------|-----|
| Zabbix | `ciem-mod-zabbix` | `/grafana/d/ciem-mod-zabbix` |
| Cacti | `ciem-mod-cacti` | `/grafana/d/ciem-mod-cacti` |
| Nagios | `ciem-mod-nagios` | `/grafana/d/ciem-mod-nagios` |
| TOPdesk | `ciem-mod-topdesk` | `/grafana/d/ciem-mod-topdesk` |
| Inventário | `ciem-mod-inventory` | `/grafana/d/ciem-mod-inventory` |
| Syslog | `ciem-mod-syslog` | `/grafana/d/ciem-mod-syslog` |

Cada dashboard exibe alarmes ativos e histórico **apenas daquele módulo**.

### Regenerar dashboards

```bash
python3 scripts/generate-grafana-dashboards.py
```

### Endpoints por módulo

| Endpoint | Dados |
|----------|-------|
| `GET /grafana/modules/{nome}/data` | Coleta completa do módulo |
| `GET /grafana/modules/{nome}/alarms` | Alarmes ativos do módulo |
| `GET /grafana/modules/{nome}/history` | Histórico do módulo |
| `GET /grafana/modules-list` | Lista de módulos e UIDs dos dashboards |

## Dashboards disponíveis

| Dashboard | UID | Função |
|-----------|-----|--------|
| **Visão Geral NOC** | `ciem-overview` | Painel principal com alarmes em destaque (+ painel Insights IA) |
| **Insights IA** | `ciem-insights` | Análise de alarmes/logs por provedor de IA (visível a todos quando ativo) |
| **Alarmes Ativos** | `ciem-alarms` | Problemas em andamento (ação imediata) |
| **Histórico de Eventos** | `ciem-history` | O que já aconteceu (separado dos ativos) |
| **Módulos Coletores** | `ciem-modules` | Saúde de Zabbix, Cacti, Nagios, etc. |
| **Sessões e Auditoria** | `ciem-sessions` | Alvos de manutenção + log de sessões |

Acesse: `https://seu-dominio/grafana/` → pasta **CIEM**

## Fontes de dados provisionadas

| Datasource | Tipo | Uso |
|------------|------|-----|
| **CIEM-Prometheus** | Prometheus | Métricas agregadas (`/metrics`) |
| **CIEM-API** | Infinity | Tabelas com dados da API (`/grafana/*`) |

## Métricas Prometheus

O CIEM Core exporta em `/metrics`:

```
ciem_active_alarms{severity="critical|high|warning|info"}
ciem_module_up{module="zabbix|cacti|..."}
ciem_maintenance_targets{status="enabled|disabled"}
ciem_active_sessions
```

## Endpoints internos para Grafana

Protegidos por header `X-Grafana-Token` (padrão: `ciem-grafana-internal`):

| Endpoint | Dados |
|----------|-------|
| `GET /grafana/alarms` | Alarmes ativos agregados |
| `GET /grafana/history` | Histórico de eventos |
| `GET /grafana/modules` | Status dos módulos |
| `GET /grafana/sessions` | Auditoria de sessões |
| `GET /grafana/targets` | Alvos de manutenção |

Configure o token em `.env`:

```bash
CIEM_GRAFANA_TOKEN=seu-token-seguro
```

## Plugin necessário

O Grafana instala automaticamente o plugin **Infinity Datasource** via:

```yaml
GF_INSTALL_PLUGINS: yesoreyeram-infinity-datasource
```

## Personalização

Dashboards em `grafana/dashboards/*.json` — edite e reinicie o Grafana ou aguarde o reload (30s).

Provisionamento em `grafana/provisioning/`.

## Alarmes em destaque

O dashboard **Visão Geral NOC** exibe:
- Banner vermelho com contagem de alarmes críticos
- Tabela de alarmes ativos com cores por severidade
- Gráfico de tendência por severidade
- Status dos módulos em bar gauge

O dashboard **Histórico** é separado e mostra apenas eventos passados.
