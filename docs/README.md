# Documentação CIEM

Guia para equipes que vão **configurar**, **operar** e **desenvolver** a plataforma.

## Novidades recentes

Resumo das funções adicionadas ao portal (LDAP, usuários locais, switches de módulos com formulário, insights de IA): **[CHANGELOG_FEATURES.md](CHANGELOG_FEATURES.md)**.

## Por onde começar

| Perfil | Leia primeiro |
|--------|----------------|
| **Operador / NOC** | [USAGE.md](USAGE.md) → [DASHBOARDS.md](DASHBOARDS.md) → [AI.md](AI.md) (se insights ativos) |
| **Administrador** | [GETTING_STARTED.md](GETTING_STARTED.md) → [CONFIGURATION.md](CONFIGURATION.md) → [AUTH.md](AUTH.md) → [AI.md](AI.md) |
| **DevOps / SRE** | [KUBERNETES.md](KUBERNETES.md) ou [DEPLOYMENT.md](DEPLOYMENT.md) |
| **Desenvolvedor** | [PORTAL.md](PORTAL.md) → [ARCHITECTURE.md](ARCHITECTURE.md) → [MODULES.md](MODULES.md) |

## Mapa da documentação

### Configuração e deploy

| Documento | Conteúdo |
|-----------|----------|
| [GETTING_STARTED.md](GETTING_STARTED.md) | Primeiro deploy em 15 minutos (Docker ou K8s) |
| [CONFIGURATION.md](CONFIGURATION.md) | Referência dos YAML em `config/` (main, modules, auth, ai, targets) |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Docker Compose, perfis e variáveis de ambiente |
| [KUBERNETES.md](KUBERNETES.md) | Pods, ConfigMaps, Secrets e ordem de aplicação dos YAML |
| [CI_CD.md](CI_CD.md) | GitHub Actions e imagens no GHCR |

### Uso da plataforma

| Documento | Conteúdo |
|-----------|----------|
| [USAGE.md](USAGE.md) | Login, papéis, fluxo diário, configuração pelo portal |
| [PORTAL.md](PORTAL.md) | Telas do portal + mockups + checklist de PR |
| [DASHBOARDS.md](DASHBOARDS.md) | Painéis Grafana (incl. Insights IA), métricas |
| [PROCESSES.md](PROCESSES.md) | Coleta, auth/LDAP, alarmes, sessões, IA, auditoria |

### Componentes

| Documento | Conteúdo |
|-----------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Isolamento, redes e comunicação entre serviços |
| [MODULES.md](MODULES.md) | Coletores + configuração via portal (switch e opções) |
| [AUTH.md](AUTH.md) | Usuários locais, admin padrão, LDAP opcional, senha/exclusão |
| [AI.md](AI.md) | Provedores de IA, insights no Grafana/portal (config admin) |
| [CHANGELOG_FEATURES.md](CHANGELOG_FEATURES.md) | Resumo das funções recentes do portal |
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
