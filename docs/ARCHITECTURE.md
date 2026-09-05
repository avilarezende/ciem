# Arquitetura do CIEM

## Visão geral

O **CIEM** (Centro Integrado de Estatística e Manutenção) é uma plataforma ZTNA que combina:

1. **Coleta** — dados de sistemas de monitoramento existentes (sem dependência do CIEM)
2. **Portal** — interface web para admin e observer (KPIs, Análise, **Navegador HTML5**, configuração por seções)
3. **Visualização** — Grafana (também embutido no Navegador do portal), alarmes, histórico e Insights de IA
4. **Autenticação** — usuários locais (prioritários) + LDAP/AD opcional
5. **Insights de IA** — provedor OpenAI-compatible opcional (config só admin; resultados para todos)
6. **Manutenção** — sessões SSH/RDP/VNC via Guacamole (iframe do Navegador ou nova aba) com auditoria completa

## Princípio de isolamento

> Cada sistema suportado roda em **container/pod separado**, assim como o core, o proxy e o Guacamole.

Isso garante:
- **Contenção** — falha em um módulo não afeta os demais
- **Segurança** — credenciais de cada sistema ficam isoladas
- **Flexibilidade** — ative apenas os módulos necessários

![Arquitetura](assets/ciem-architecture-diagram.png)

## Componentes

```mermaid
graph TB
    subgraph "Rede Externa"
        ADMIN[Usuários admin/observer]
        LDAP[LDAP / Active Directory]
        AI[Provedor de IA]
        EXT_ZBX[Zabbix]
        EXT_CAC[Cacti]
        EXT_NAG[Nagios]
        EXT_TD[TOPdesk]
        EXT_INV[Inventory]
        EXT_SYS[Syslog]
        TARGETS[Servidores/Roteadores/Switches]
    end

    subgraph "CIEM — Proxy (isolado)"
        PROXY[Nginx SSL / ZTNA]
    end

    subgraph "CIEM — Core e Portal (isolados)"
        PORTAL[Portal Web + Navegador HTML5]
        CORE[Core API]
    end

    subgraph "CIEM — Visualização (isolado)"
        GRAF[Grafana + Insights IA]
    end

    subgraph "CIEM — Manutenção (isolado)"
        GUAC[Guacamole]
        GUACD[guacd]
    end

    subgraph "CIEM — Módulos (cada um isolado)"
        MOD_ZBX[module-zabbix]
        MOD_CAC[module-cacti]
        MOD_NAG[module-nagios]
        MOD_TD[module-topdesk]
        MOD_INV[module-inventory]
        MOD_SYS[module-syslog]
    end

    ADMIN -->|HTTPS| PROXY
    PROXY --> PORTAL
    PROXY --> CORE
    PROXY --> GRAF
    PROXY --> GUAC

    CORE --> MOD_ZBX & MOD_CAC & MOD_NAG & MOD_TD & MOD_INV & MOD_SYS
    CORE -.->|auth opcional| LDAP
    CORE -.->|insights opcional| AI
    MOD_ZBX -->|API| EXT_ZBX
    MOD_CAC -->|Web| EXT_CAC
    MOD_NAG -->|API| EXT_NAG
    MOD_TD -->|API| EXT_TD
    MOD_INV -->|REST| EXT_INV
    MOD_SYS -->|REST/File| EXT_SYS

    GRAF -->|Dados agregados| CORE
    GUAC --> GUACD
    GUACD -->|SSH/RDP| TARGETS
    CORE -->|Auditoria| AUDIT[(audit.jsonl)]
```

## Fluxo de dados

### 1. Coleta (módulos → core)

```
Sistema externo → Módulo coletor → POST /collect → Core API → Grafana
```

- Cada módulo consulta a interface web/API do sistema externo
- Retorna JSON normalizado: `active_alarms[]` + `history_events[]`
- O core agrega dados de todos os módulos habilitados

### 2. Visualização (Portal + Grafana)

- **Portal** — Visão geral (KPIs/gráfico), **Navegador HTML5**, Alarmes, Histórico e Análise
- **Navegador HTML5** — iframe same-origin para `/grafana/` e (admin) SSO Guacamole / URLs de módulos; fallback ↗ se o destino bloquear embedding
- **Insights de IA** — quando habilitados pelo admin, visíveis a todos no portal e no Grafana
- **Grafana** — dashboards NOC provisionados em `grafana/dashboards/` (também via Navegador)

### 3. Autenticação

```
Login → usuários locais (prioridade) → LDAP/AD (se habilitado)
```

- Admin configura LDAP e usuários em **Configuração** no portal
- Papéis: `admin` (config + sessões) e `observer` (somente leitura/análise)

### 4. Manutenção (Guacamole → alvos)

```
Admin → Portal (Navegador ou Sessões) → Core API SSO → Guacamole → guacd → Equipamento
                                                         ↓
                                                   audit.jsonl (sessão registrada)
```

O admin pode abrir o Guacamole **no Navegador HTML5** do portal ou em **nova aba**.

Cada sessão registra:
- Quem acessou (usuário)
- Quando (data/hora início e fim)
- O quê (comandos executados)
- Quanto tempo (duração em segundos)
- Para onde (hostname/IP do alvo)

## Redes Docker

| Rede | Acesso | Serviços |
|------|--------|----------|
| `ciem-front` | Externa (via proxy) | proxy, portal |
| `ciem-back` | Interna (isolada) | core, módulos, grafana, guacamole |

## Decisões de design

| Decisão | Motivo |
|---------|--------|
| Módulos sem dependência entre si | Ativar/desativar sem impacto |
| Configuração via YAML comentado | Flexível para qualquer cliente |
| Proxy em instância separada | Terminação SSL centralizada |
| Coleta direta dos sistemas existentes | CIEM não substitui monitoramento |
| Sem vínculo organizacional | Configuração livre por IP/domínio |

## Portas internas

| Serviço | Porta | Rede |
|---------|-------|------|
| ciem-core | 8000 | ciem-back |
| ciem-portal | 80 | ciem-front/back |
| ciem-proxy | 80, 443 | ciem-front |
| grafana | 3000 | ciem-back |
| guacamole | 8080 | ciem-back |
| module-zabbix | 8101 | ciem-back |
| module-cacti | 8102 | ciem-back |
| module-nagios | 8103 | ciem-back |
| module-topdesk | 8104 | ciem-back |
| module-inventory | 8105 | ciem-back |
| module-syslog | 8106 | ciem-back |
