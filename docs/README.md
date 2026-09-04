# Documentação CIEM

Guia para equipes que vão **configurar**, **operar** e **desenvolver** a plataforma.

## Por onde começar

| Perfil | Leia primeiro |
|--------|----------------|
| **Operador / NOC** | [USAGE.md](USAGE.md) → [DASHBOARDS.md](DASHBOARDS.md) |
| **Administrador** | [GETTING_STARTED.md](GETTING_STARTED.md) → [CONFIGURATION.md](CONFIGURATION.md) |
| **DevOps / SRE** | [KUBERNETES.md](KUBERNETES.md) ou [DEPLOYMENT.md](DEPLOYMENT.md) |
| **Desenvolvedor** | [PORTAL.md](PORTAL.md) → [ARCHITECTURE.md](ARCHITECTURE.md) → [MODULES.md](MODULES.md) |

## Mapa da documentação

### Configuração e deploy

| Documento | Conteúdo |
|-----------|----------|
| [GETTING_STARTED.md](GETTING_STARTED.md) | Primeiro deploy em 15 minutos (Docker ou K8s) |
| [CONFIGURATION.md](CONFIGURATION.md) | Referência dos 4 arquivos YAML em `config/` |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Docker Compose, perfis e variáveis de ambiente |
| [KUBERNETES.md](KUBERNETES.md) | Pods, ConfigMaps, Secrets e ordem de aplicação dos YAML |
| [CI_CD.md](CI_CD.md) | GitHub Actions e imagens no GHCR |

### Uso da plataforma

| Documento | Conteúdo |
|-----------|----------|
| [USAGE.md](USAGE.md) | Login, papéis, fluxo diário no portal |
| [PORTAL.md](PORTAL.md) | Telas do portal + mockups para desenvolvimento |
| [DASHBOARDS.md](DASHBOARDS.md) | Painéis Grafana, métricas e o que cada gráfico mostra |
| [PROCESSES.md](PROCESSES.md) | Coleta, alarmes, sessões e auditoria (passo a passo) |

### Componentes

| Documento | Conteúdo |
|-----------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Isolamento, redes e comunicação entre serviços |
| [MODULES.md](MODULES.md) | Coletores Zabbix, Cacti, Nagios, etc. |
| [AUTH.md](AUTH.md) | Usuários locais, admin padrão, LDAP opcional, alterar/excluir senha |
| [AI.md](AI.md) | Provedores de IA, insights no Grafana/portal (config admin) |
| [GRAFANA.md](GRAFANA.md) | Provisionamento técnico do Grafana |
| [GUACAMOLE.md](GUACAMOLE.md) | SSO e provisionamento de conexões |
| [MAINTENANCE.md](MAINTENANCE.md) | Sessões SSH/RDP e `targets.yaml` |

## Mockups do portal (versionamento)

Imagens em `docs/assets/` para alinhar times de produto, UX e desenvolvimento:

| Arquivo | Tela |
|---------|------|
| [ciem-portal-login.jpg](assets/ciem-portal-login.jpg) | Login |
| [ciem-portal-dashboard.jpg](assets/ciem-portal-dashboard.jpg) | Dashboard / visão geral |
| [ciem-portal-alarms.jpg](assets/ciem-portal-alarms.jpg) | Alarmes ativos |
| [ciem-portal-sessions.jpg](assets/ciem-portal-sessions.jpg) | Sessões e Guacamole |
| [ciem-architecture-diagram.jpg](assets/ciem-architecture-diagram.jpg) | Arquitetura ZTNA |

> Ao alterar o portal (`services/portal/`), atualize o mockup correspondente e referencie o PR na descrição da mudança.

## Manifests Kubernetes

YAML prontos em [`deploy/kubernetes/`](../deploy/kubernetes/README.md) — aplique na ordem numérica (`00` → `09`).
