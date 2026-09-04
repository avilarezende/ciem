# Portal CIEM — guia visual e de desenvolvimento

O portal (`services/portal/`) é uma SPA estática servida pelo proxy em `/`. Use os mockups abaixo para alinhar UX, produto e desenvolvimento entre times.

## Mockups (referência visual)

### Login

![Tela de login](assets/ciem-portal-login.jpg)

- Campos: usuário e senha  
- Autenticação: `POST /api/auth/login` → token Bearer em `localStorage`  
- Aceita usuários locais e LDAP (se habilitado)  
- Erros exibidos abaixo do formulário  

### Dashboard — visão geral

![Dashboard](assets/ciem-portal-dashboard.jpg)

- Banner vermelho quando há alarmes ativos (link para painel Alarmes)  
- Grade de módulos: status **ONLINE** / **OFFLINE**, última coleta  
- Indicação de Insights IA (ativo/desabilitado)  
- Dados: `GET /api/modules/status`, `GET /api/alarms/active`, `GET /api/insights`  

### Alarmes ativos

![Alarmes](assets/ciem-portal-alarms.jpg)

- Lista agregada de todos os módulos habilitados  
- Severidade: `critical`, `warning`, `info`  
- Endpoint: `GET /api/alarms/active`  

### Sessões de manutenção (admin)

![Sessões](assets/ciem-portal-sessions.jpg)

- Botão **Abrir Guacamole** — SSO sem novo login  
- Lista de alvos de `config/targets.yaml` com **Conectar** por alvo  
- Auditoria: `GET /api/sessions/audit`  

## Navegação

| Aba | Papel | Função |
|-----|-------|--------|
| Dashboard | Todos | Status dos módulos + resumo de alarmes + status IA |
| Alarmes | Todos | Problemas em andamento |
| Histórico | Todos | Últimos eventos agregados |
| Sessões | Admin | Guacamole + auditoria |
| Configuração | Admin | Usuários, LDAP, módulos (switch+opções), provedor de IA |
| Grafana | Todos | Visão NOC embutida + abas (incl. Insights IA) / link `/grafana/` |
| Sair | Todos | Remove token e volta ao login |

## Papéis

| Papel | O que vê |
|-------|----------|
| **observer** | Dashboard, Alarmes, Histórico, Grafana, Insights IA (somente leitura, se habilitado) |
| **admin** | Tudo + Sessões + Configuração completa |

## Configuração (somente admin)

A aba **Configuração** concentra:

1. **Usuários locais** — CRUD; admin padrão protegido (não excluir o último admin)  
2. **LDAP / Active Directory** — apontamentos (host, porta, SSL, URL, domain, base DN, uid, filtros, bind, certificados)  
3. **Inteligência Artificial** — switch + campos de provedor (URL, API key, modelo, …); ao salvar com `enabled`, insights ficam públicos  
4. **Módulos coletores** — switch por módulo; com ON, formulário de opções/credenciais; persistência em `config/modules.yaml`  

Documentação: [AUTH.md](AUTH.md), [AI.md](AI.md), [MODULES.md](MODULES.md).

## Estrutura do código

```
services/portal/public/
├── index.html      # Layout e painéis
├── css/style.css   # Tema escuro NOC
└── js/portal.js    # API client, auth, renderização
```

## Desenvolvimento e versionamento

1. **Branch** — use `feature/portal-<descricao>` ou o fluxo do time  
2. **Mockup** — se a UI mudar de forma visível, atualize o JPG em `docs/assets/`  
3. **PR** — inclua screenshot ou diff do mockup na descrição  
4. **Teste manual** — login com `admin` / `admin123` no profile `core`  

### Checklist de PR (portal)

- [ ] Login e logout funcionam  
- [ ] Observer não vê abas admin  
- [ ] Banner de alarmes reflete contagem real  
- [ ] Links Grafana e Guacamole abrem com SSO (admin)  
- [ ] Configuração: usuários locais (criar/alterar senha/excluir) e LDAP (salvar apontamentos)  
- [ ] Configuração: switch de módulos + formulário de opções ao ativar  
- [ ] Configuração: Insights IA (admin ativa + URL/API key/modelo; observer só vê resultados)  
- [ ] Mockup atualizado em `docs/assets/` (se aplicável)  

## Customização

| Item | Onde alterar |
|------|----------------|
| Cores / fontes | `services/portal/public/css/style.css` |
| Textos e painéis | `services/portal/public/index.html` |
| Chamadas API | `services/portal/public/js/portal.js` |
| Nome da plataforma | `config/main.yaml` → `platform_name` |

## Limitações atuais

- Bind LDAP em runtime pode ser stub conforme ambiente; apontamentos já são persistidos e editáveis (ver [AUTH.md](AUTH.md))  
- Coleta periódica em background depende do agendador documentado em [PROCESSES.md](PROCESSES.md); o portal dispara consultas sob demanda  
- API keys de IA não devem ser versionadas em repositório público  
