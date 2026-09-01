# CIEM — Centro Integrado de Estatística e Manutenção

[![CI](https://github.com/avilarezende/ciem/actions/workflows/ci.yml/badge.svg)](https://github.com/avilarezende/ciem/actions/workflows/ci.yml)

Plataforma **ZTNA** para manutenção de redes: agrega Zabbix, Cacti, Nagios, TOPdesk, inventário e syslog em um portal unificado, com Grafana e sessões remotas auditadas via Guacamole.

![Dashboard CIEM](docs/assets/ciem-portal-dashboard.jpg)

## Comece aqui

| Eu quero… | Documento |
|-----------|-----------|
| **Subir pela primeira vez** | [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) |
| **Usar o portal no dia a dia** | [docs/USAGE.md](docs/USAGE.md) |
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
# Edite config/modules.yaml, config/auth.yaml, config/targets.yaml

docker compose -f deploy/docker/docker-compose.yml --profile core --profile modules --profile grafana up -d --build
```

| Serviço | URL | Dev |
|---------|-----|-----|
| Portal | `https://localhost/` | `admin` / `admin123` |
| Grafana | `https://localhost/grafana/` | `admin` / `admin` |
| API | `https://localhost/api/health` | — |

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
| [login](docs/assets/ciem-portal-login.jpg) | Autenticação |
| [dashboard](docs/assets/ciem-portal-dashboard.jpg) | Visão geral NOC |
| [alarmes](docs/assets/ciem-portal-alarms.jpg) | Alarmes ativos |
| [sessões](docs/assets/ciem-portal-sessions.jpg) | Guacamole + auditoria |
| [arquitetura](docs/assets/ciem-architecture-diagram.jpg) | Fluxo ZTNA |

## Arquitetura

![Arquitetura](docs/assets/ciem-architecture-diagram.jpg)

Cada componente (core, portal, módulos, Grafana, Guacamole) roda em **container/pod isolado**. Detalhes: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Documentação

| Área | Documentos |
|------|----------------|
| **Configuração** | [CONFIGURATION.md](docs/CONFIGURATION.md), [AUTH.md](docs/AUTH.md) |
| **Deploy** | [DEPLOYMENT.md](docs/DEPLOYMENT.md), [KUBERNETES.md](docs/KUBERNETES.md), [CI_CD.md](docs/CI_CD.md) |
| **Operação** | [USAGE.md](docs/USAGE.md), [PROCESSES.md](docs/PROCESSES.md), [MAINTENANCE.md](docs/MAINTENANCE.md) |
| **Visualização** | [DASHBOARDS.md](docs/DASHBOARDS.md), [GRAFANA.md](docs/GRAFANA.md) |
| **Desenvolvimento** | [PORTAL.md](docs/PORTAL.md), [MODULES.md](docs/MODULES.md) |

## Módulos coletores

Ative em `config/modules.yaml`:

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
