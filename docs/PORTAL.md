# Portal CIEM — guia visual e de desenvolvimento

O portal (`services/portal/`) é uma SPA estática servida pelo proxy em `/`. Use os mockups abaixo para alinhar UX, produto e desenvolvimento.

## Interface atual (ergonomia NOC)

Layout com **sidebar** à esquerda e **workspace** à direita:

- Tipografia: DM Sans + IBM Plex Mono  
- Tema escuro NOC com accent teal  
- Login brand-first (marca CIEM em destaque)  
- Espaço dedicado a **KPIs**, **gráficos** e **insights**  

### Login

![Tela de login](assets/ciem-portal-login.jpg)

- Campos: usuário e senha  
- Autenticação: `POST /api/auth/login` → token Bearer em `localStorage`  
- Aceita usuários locais e LDAP (se habilitado)  
- Erros exibidos abaixo do formulário  

### Visão geral (dashboard)

![Dashboard](assets/ciem-portal-dashboard.jpg)

- Chip de alarmes ativos no cabeçalho (atalho para Alarmes)  
- **KPIs**: críticos, warnings, total de alarmes, módulos online  
- **Gráfico de severidade** (canvas) + legenda  
- **Insights** (preview; abre Análise completa)  
- Grade de **coletores** com status online/indisponível/desabilitado  
- Dados: `GET /api/modules/status`, `GET /api/alarms/active`, `GET /api/insights`  

### Alarmes ativos

![Alarmes](assets/ciem-portal-alarms.jpg)

- Lista agregada de todos os módulos habilitados  
- Severidade destacada: critical / high / warning / info  
- Endpoint: `GET /api/alarms/active`  

### Análise (todos os papéis)

![Análise](assets/ciem-portal-analysis.jpg)

Painel com abas segmentadas e área ampla para gráfico + detalhe:

| Aba | Conteúdo |
|-----|----------|
| Resumo | KPIs + visão consolidada + status de IA |
| Insights IA | Resumo, cards e gráficos sugeridos (se habilitado) |
| Alarmes | Distribuição de severidade + lista |
| Módulos | Saúde dos coletores |
| Histórico | Volume por fonte + eventos |
| Sessões | Auditoria (somente admin) |

Link externo para Grafana: `/grafana/`.

### Sessões de manutenção (admin)

![Sessões](assets/ciem-portal-sessions.jpg)

- Botão **Abrir Guacamole** — SSO sem novo login (`POST /api/sso/guacamole`)  
- Lista de alvos de `config/targets.yaml` com **Conectar** por alvo  
- Auditoria: `GET /api/sessions/audit`  

### Configuração (admin)

Navegação lateral em seções (uma tarefa por vez):

1. **Usuários** — CRUD local; admin padrão marcado; alterar senha / habilitar / excluir  
2. **LDAP** — apontamentos opcionais (host, porta, SSL, bind, filtros, certificados)  
3. **Inteligência Artificial** — provedor, URL, API key, modelo; **Gerar insights agora**  
4. **Módulos** — switch por coletor; com ON, formulário de URL/credenciais e salvar  

Persistência: `config/auth.yaml`, `config/ai.yaml`, `config/modules.yaml`.

## Navegação

| Item da sidebar | Papel | Função |
|-----------------|-------|--------|
| Visão geral | Todos | KPIs, gráfico, insights, coletores |
| Alarmes | Todos | Problemas em andamento |
| Histórico | Todos | Últimos eventos agregados |
| Análise | Todos | Gráficos + detalhe filtrado + insights |
| Sessões | Admin | Guacamole + auditoria |
| Configuração | Admin | Usuários, LDAP, IA, módulos |
| Sair | Todos | Remove token e volta ao login |

## Papéis

| Papel | O que vê |
|-------|----------|
| **observer** | Visão geral, Alarmes, Histórico, Análise (incl. insights se ativos) |
| **admin** | Tudo + Sessões + Configuração completa |

## Estrutura do código

```
services/portal/public/
├── index.html      # Layout (login + sidebar + painéis)
├── css/style.css   # Tema escuro NOC / ergonomia
└── js/portal.js    # API client, auth, gráficos, config
```

## Desenvolvimento e versionamento

1. **Branch** — `cursor/portal-<descricao>` ou fluxo do time  
2. **Mockup** — se a UI mudar de forma visível, atualize o JPG em `docs/assets/`  
3. **PR** — inclua screenshot ou diff do mockup  
4. **Teste manual** — login com `admin` / `admin123`  

### Checklist de PR (portal)

- [ ] Login e logout funcionam  
- [ ] Observer não vê Sessões nem Configuração  
- [ ] Chip de alarmes reflete contagem real  
- [ ] Análise: abas e gráfico renderizam  
- [ ] SSO Guacamole abre sem duplicar `/api` na URL  
- [ ] Configuração: usuários, LDAP, módulos (switch+opções), IA  
- [ ] Insights visíveis ao observer quando IA habilitada  
- [ ] Mockup atualizado em `docs/assets/` (se aplicável)  

## Customização

| Item | Onde alterar |
|------|----------------|
| Cores / fontes | `services/portal/public/css/style.css` |
| Textos e painéis | `services/portal/public/index.html` |
| Chamadas API | `services/portal/public/js/portal.js` |
| Nome da plataforma | `config/main.yaml` |

## Limitações atuais

- Bind LDAP em runtime pode depender do ambiente; apontamentos são persistidos (ver [AUTH.md](AUTH.md))  
- Coleta periódica depende do agendador ([PROCESSES.md](PROCESSES.md)); o portal consulta sob demanda  
- API keys de IA não devem ser versionadas em repositório público  

Documentação relacionada: [AUTH.md](AUTH.md) · [AI.md](AI.md) · [MODULES.md](MODULES.md) · [USAGE.md](USAGE.md)
