# CIEM — Centro Integrado de Estatística e Manutenção

[![CI](https://github.com/avilarezende/ciem/actions/workflows/ci.yml/badge.svg)](https://github.com/avilarezende/ciem/actions/workflows/ci.yml)

Plataforma **ZTNA** para manutenção de redes: agrega Zabbix, Cacti, Nagios, TOPdesk, inventário e syslog em um portal unificado, com Grafana, sessões remotas auditadas via Guacamole, autenticação local/LDAP e insights opcionais de IA.

![Dashboard CIEM](docs/assets/ciem-portal-dashboard.jpg)

## Funções do portal (administração)

| Função | Quem configura | Quem consome |
|--------|----------------|--------------|
| **Usuários locais** + admin padrão | Admin | Todos (login) |
| **LDAP / Active Directory** (opcional) | Admin | Usuários do diretório |
| **Módulos coletores** (switch + URL/credenciais) | Admin | Todos (alarmes/dashboards) |
| **Insights de IA** (URL, API key, modelo) | Admin | Todos, quando habilitado |
| **Sessões Guacamole** + auditoria | Admin | — |

Resumo das novidades: [docs/CHANGELOG_FEATURES.md](docs/CHANGELOG_FEATURES.md) · Auth: [docs/AUTH.md](docs/AUTH.md) · IA: [docs/AI.md](docs/AI.md)

## Comece aqui

| Eu quero… | Documento |
|-----------|-----------|
| **Subir pela primeira vez** | [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) |
| **Usar o portal (observer)** | [docs/MANUAL_USER.md](docs/MANUAL_USER.md) |
| **Administrar o portal** | [docs/MANUAL_ADMIN.md](docs/MANUAL_ADMIN.md) |
| **Fluxo diário NOC** | [docs/USAGE.md](docs/USAGE.md) |
| **Configurar LDAP / usuários** | [docs/AUTH.md](docs/AUTH.md) |
| **Ativar insights de IA** | [docs/AI.md](docs/AI.md) |
| **Deploy em Kubernetes** | [docs/KUBERNETES.md](docs/KUBERNETES.md) → [`deploy/kubernetes/`](deploy/kubernetes/README.md) |
| **Entender dashboards Grafana** | [docs/DASHBOARDS.md](docs/DASHBOARDS.md) |
| **Ver fluxos (coleta, SSO, auditoria)** | [docs/PROCESSES.md](docs/PROCESSES.md) |
| **Desenvolver o portal (mockups)** | [docs/PORTAL.md](docs/PORTAL.md) |
| **Índice completo** | [docs/README.md](docs/README.md) |

## Início rápido (Docker)

```bash
git clone https://github.com/avilarezende/ciem.git
cd ciem
cp .env.example .env
# Opcional: edite config/*.yaml — ou configure pelo portal após o login admin
# (módulos, LDAP, usuários locais, provedor de IA)

docker compose -f deploy/docker/docker-compose.yml --profile core --profile modules --profile grafana up -d --build
```

| Serviço | URL | Dev |
|---------|-----|-----|
| Portal | `https://localhost/` | `admin` / `admin123` (altere em produção) |
| Grafana | `https://localhost/grafana/` | `admin` / `admin` |
| API | `https://localhost/api/health` | — |

Após o login admin: sidebar **Configuração** (seções Usuários, LDAP, IA e Módulos). Operadores usam **Visão geral** e **Análise** para KPIs, gráficos e insights.

## Início rápido (Kubernetes)

```bash
kubectl apply -f deploy/kubernetes/00-namespace.yaml
# Configure ConfigMap e Secrets — ver docs/KUBERNETES.md
kubectl apply -f deploy/kubernetes/
```

YAML numerados (`00`–`09`): namespace, config, secrets, core, portal, módulos, Grafana, Guacamole, storage, ingress.

## Mockups do portal (times e versionamento)

Referência visual em `docs/assets/` para alinhar produto, UX e desenvolvimento:

| Imagem | Tela |
|--------|------|
| [login](docs/assets/ciem-portal-login.jpg) | Autenticação (brand-first) |
| [dashboard](docs/assets/ciem-portal-dashboard.jpg) | Visão geral (KPIs + gráfico + insights) |
| [alarmes](docs/assets/ciem-portal-alarms.jpg) | Alarmes ativos |
| [análise](docs/assets/ciem-portal-analysis.jpg) | Análise (abas + gráfico) |
| [sessões](docs/assets/ciem-portal-sessions.jpg) | Guacamole + auditoria |
| [configuração](docs/assets/ciem-config-interface.png) | Configuração por seções (admin) |
| [arquitetura](docs/assets/ciem-architecture-diagram.jpg) | Fluxo ZTNA |

## Arquitetura

![Arquitetura](docs/assets/ciem-architecture-diagram.jpg)

Cada componente (core, portal, módulos, Grafana, Guacamole) roda em **container/pod isolado**. Detalhes: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Documentação

| Área | Documentos |
|------|----------------|
| **Configuração** | [CONFIGURATION.md](docs/CONFIGURATION.md), [AUTH.md](docs/AUTH.md), [AI.md](docs/AI.md) |
| **Deploy** | [DEPLOYMENT.md](docs/DEPLOYMENT.md), [KUBERNETES.md](docs/KUBERNETES.md), [CI_CD.md](docs/CI_CD.md) |
| **Operação** | [USAGE.md](docs/USAGE.md), [PROCESSES.md](docs/PROCESSES.md), [MAINTENANCE.md](docs/MAINTENANCE.md) |
| **Visualização** | [DASHBOARDS.md](docs/DASHBOARDS.md), [GRAFANA.md](docs/GRAFANA.md) |
| **Desenvolvimento** | [PORTAL.md](docs/PORTAL.md), [MODULES.md](docs/MODULES.md) |
| **Novidades** | [CHANGELOG_FEATURES.md](docs/CHANGELOG_FEATURES.md) |

## Módulos coletores

Ative em `config/modules.yaml` **ou** no portal (**Configuração → Módulos coletores**): switch + URL/credenciais.

| Módulo | Fonte |
|--------|-------|
| zabbix | Zabbix API |
| cacti | Cacti web |
| nagios | Nagios XI |
| topdesk | TOPdesk API |
| inventory | API REST |
| syslog | Arquivo / API |

## Desenvolvimento

```bash
pip install -r requirements-dev.txt
export PYTHONPATH=shared:services/core CONFIG_PATH=./config
ruff check shared services/core services/modules tests
pytest tests -v
```

## Licença

MIT — [LICENSE](LICENSE).
