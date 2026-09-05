# Dashboards Grafana — o que cada painel mostra

O CIEM provisiona **13 dashboards** na pasta **CIEM** do Grafana (`grafana/dashboards/`).

No dia a dia do NOC, abra-os pelo **Navegador HTML5** do portal (sidebar **Navegador** → atalho Grafana), sem sair do CIEM. Detalhes: [GRAFANA.md](GRAFANA.md) · [PORTAL.md](PORTAL.md).

## Visão geral dos dashboards

### Plataforma (6)

| Dashboard | UID | Para quê |
|-----------|-----|----------|
| **Visão Geral NOC** | `ciem-overview` | Painel principal: alarmes em destaque, módulos, sessões, insights IA |
| **Insights IA** | `ciem-insights` | Análise de alarmes/logs por provedor de IA (visível a todos quando ativo) |
| **Alarmes Ativos** | `ciem-alarms` | Somente problemas **em andamento** — ação imediata |
| **Histórico de Eventos** | `ciem-history` | Eventos passados (separado dos ativos) |
| **Módulos Coletores** | `ciem-modules` | Saúde e latência de cada coletor |
| **Sessões e Auditoria** | `ciem-sessions` | Alvos de manutenção + log de sessões |

### Por módulo (6)

| Dashboard | UID | Fonte de dados |
|-----------|-----|----------------|
| CIEM — Zabbix | `ciem-mod-zabbix` | Problemas e hosts Zabbix |
| CIEM — Cacti | `ciem-mod-cacti` | Dispositivos Cacti |
| CIEM — Nagios | `ciem-mod-nagios` | Hosts/serviços Nagios XI |
| CIEM — TOPdesk | `ciem-mod-topdesk` | Chamados abertos |
| CIEM — Inventário | `ciem-mod-inventory` | Ativos do inventário |
| CIEM — Syslog | `ciem-mod-syslog` | Eventos de log |

Cada dashboard de módulo filtra alarmes e histórico **apenas daquele coletor**.

## Painéis típicos (Visão Geral NOC)

| Painel | Tipo | Significado |
|--------|------|-------------|
| Alarmes críticos | Stat / tabela | Contagem `severity=critical` |
| Alarmes warning | Stat | Contagem `severity=warning` |
| Módulos online | Gauge | `ciem_module_up == 1` |
| Tabela de alarmes | Infinity (API) | `GET /grafana/alarms` |
| Histórico recente | Tabela | `GET /grafana/history` |
| Sessões ativas | Stat | Métrica `ciem_active_sessions` |

## Fontes de dados

| Datasource | Origem | Uso |
|------------|--------|-----|
| **CIEM-Prometheus** | `GET /api/metrics` | Gauges de alarmes, módulos, sessões |
| **CIEM-API** | `GET /grafana/*` | Tabelas JSON via plugin Infinity |

Header obrigatório na API Infinity: `X-Grafana-Token: <CIEM_GRAFANA_TOKEN>`

## Métricas Prometheus

```
ciem_active_alarms{severity="critical|high|warning|info"}
ciem_module_up{module="zabbix|cacti|nagios|topdesk|inventory|syslog"}
ciem_maintenance_targets{status="enabled|disabled"}
ciem_active_sessions
```

Atualizadas quando o Prometheus (ou Grafana) faz scrape em `/metrics`.

## Endpoints da API para Grafana

| Endpoint | Conteúdo |
|----------|----------|
| `/grafana/alarms` | Alarmes agregados |
| `/grafana/history` | Histórico agregado |
| `/grafana/modules` | Status dos coletores |
| `/grafana/sessions` | Auditoria |
| `/grafana/targets` | Alvos de manutenção |
| `/grafana/modules/{nome}/alarms` | Alarmes de um módulo |
| `/grafana/modules/{nome}/history` | Histórico de um módulo |
| `/grafana/modules-list` | Mapa módulo → UID do dashboard |
| `/grafana/insights` | Pacote completo de insights de IA |
| `/grafana/insights/table` | Insights achatados (tabela Infinity) |
| `/grafana/insights/charts` | Séries sugeridas pela IA |

## Quando usar portal vs Grafana

| Necessidade | Onde |
|-------------|------|
| Triagem rápida | Portal → Alarmes |
| Correlação entre módulos | Grafana → Visão Geral NOC |
| Detalhe de um sistema | Dashboard do módulo (`ciem-mod-*`) |
| Tendência / histórico longo | Grafana → Histórico de Eventos |
| Insights / recomendações de IA | Portal → Insights IA ou Grafana → `ciem-insights` |
| Auditoria de acesso | Grafana → Sessões ou Portal → Sessões |

## Regenerar dashboards

Após alterar o gerador:

```bash
python3 scripts/generate-grafana-dashboards.py
git add grafana/dashboards/
```

Provisionamento automático: `grafana/provisioning/dashboards/ciem.yml`

Mais detalhes técnicos: [GRAFANA.md](GRAFANA.md)
