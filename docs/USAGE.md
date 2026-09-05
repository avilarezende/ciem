# Guia de uso — CIEM

Manual para operadores de NOC e administradores no dia a dia do portal.

## Acesso

1. Abra `https://<seu-dominio>/`  
2. Entre com usuário local (`config/auth.yaml`) ou LDAP (se o admin tiver habilitado)  
3. O token permanece no navegador até **Sair** ou expiração da sessão  

Credenciais padrão de desenvolvimento: `admin` / `admin123` e `observador` / `observer123` (altere em produção — ver [AUTH.md](AUTH.md)).

Manuais dedicados: [MANUAL_USER.md](MANUAL_USER.md) (observer) · [MANUAL_ADMIN.md](MANUAL_ADMIN.md) (administrador).

### URLs dos serviços

| Serviço | URL | Quem acessa |
|---------|-----|-------------|
| Portal | `/` | Todos autenticados |
| API | `/api/` | Integrações (Bearer token) |
| Grafana | `/grafana/` | Todos autenticados (via proxy) |
| Guacamole | `/guacamole/` | Admin (SSO a partir do portal) |

## Navegação do portal

A barra lateral organiza o trabalho:

| Item | Papel | Uso |
|------|-------|-----|
| **Visão geral** | Todos | KPIs, gráfico, insights, coletores; lembretes flutuantes |
| **Navegador** | Todos | Browser HTML5: Grafana embutido, URLs; admin também Guacamole/módulos |
| **Alarmes** | Todos | Triagem dos problemas ativos |
| **Histórico** | Todos | Últimos eventos agregados |
| **Análise** | Todos | Gráficos + detalhe por aba (resumo, insights IA, alarmes, módulos, histórico) |
| **Wiki** (aba lateral) | Todos | Documentação colaborativa dos serviços (Markdown) |
| **Calendário** (aba lateral) | Todos | Agenda compartilhada Google/Microsoft |
| **Sessões** | Admin | Guacamole SSO + auditoria |
| **Configuração** | Admin | Usuários, LDAP, IA e módulos (seções) |

## Fluxo diário recomendado

```
1. Login no portal
2. Visão geral → KPIs, gráfico, coletores, chip de alarmes e lembretes do turno
3. Alarmes → triagem (critical / high primeiro)
4. Análise → insights IA (se ativo) e detalhe filtrado
5. Navegador → Grafana (ou URL) sem sair do portal
6. Wiki / Calendário → consultar serviços ou agenda compartilhada
7. (Admin) Sessões → conectar no alvo (navegador ou nova aba)
8. (Admin) Configuração → usuários/LDAP, módulos ou provedor de IA conforme necessário
```

## Por papel

### Observer (visualização)

- Monitorar visão geral e alarmes  
- Consultar histórico  
- Usar **Análise** (gráficos e insights, se a IA estiver habilitada)  
- Usar o **Navegador**, **Wiki**, **Calendário** e **Lembretes**  
- **Não** inicia sessões remotas nem altera configuração  

### Admin (operação e configuração)

- Tudo do observer  
- **Sessões** — Guacamole no navegador do portal ou em nova aba + auditoria  
- Excluir páginas da **Wiki** quando necessário  
- **Configuração** em seções:
  - Usuários locais (criar, alterar senha, desabilitar, excluir)
  - LDAP / AD (servidor, porta, SSL, domínio, UID, bind, certificados)
  - Inteligência Artificial (URL, API key, modelo; resultados ficam visíveis a todos)
  - Módulos coletores (switch + formulário de URL/credenciais/opções)

## Operações comuns

### Verificar saúde dos coletores

**Portal:** Visão geral → cards dos módulos (verde = online)

**API:**

```bash
curl -H "Authorization: Bearer <token>" \
  https://ciem.exemplo.local/api/modules/status
```

### Forçar coleta de um módulo

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  https://ciem.exemplo.local/api/modules/zabbix/collect
```

### Listar alarmes ativos

**Portal:** sidebar **Alarmes** (ou chip no cabeçalho)

**API:** `GET /api/alarms/active`

### Usar Análise e Insights IA

1. Sidebar **Análise**  
2. Abas: Resumo · Insights IA · Alarmes · Módulos · Histórico  
3. Grafana externo: `/grafana/` (ou link no painel Análise)  

Detalhes de IA: [AI.md](AI.md).

### Conectar em servidor (admin)

1. Sidebar **Sessões**  
2. **Conectar** no alvo desejado (ou **Abrir Guacamole** para a lista completa)  
3. SSO redireciona sem pedir senha novamente  
4. Ao encerrar, a sessão é registrada em auditoria  

### Habilitar ou configurar um módulo (admin)

1. **Configuração → Módulos**  
2. Ative o switch do módulo  
3. Preencha o formulário (URL, usuário/senha ou API key, opções)  
4. **Salvar** — grava em `config/modules.yaml`  

Ver [MODULES.md](MODULES.md).

### Gerenciar usuários e LDAP (admin)

1. **Configuração → Usuários** — criar, alterar senha, excluir  
2. **Configuração → LDAP** — habilitar e preencher apontamentos  
3. Admin padrão `admin` continua válido mesmo com LDAP ativo  

Guia: [AUTH.md](AUTH.md).

### Ativar Insights de IA (admin)

1. **Configuração → Inteligência Artificial**  
2. Habilitar e preencher URL, API key e modelo  
3. **Salvar** → opcionalmente **Gerar insights agora**  
4. Todos passam a ver resultados na Visão geral e em Análise  

## Credenciais de desenvolvimento

| Sistema | Usuário | Senha |
|---------|---------|-------|
| Portal | `admin` | `admin123` |
| Portal (observer) | `observador` | `observer123` |
| Grafana | `admin` | `admin` |

> Troque todas as senhas antes de expor à internet.

## Problemas frequentes

| Sintoma | Causa provável | Ação |
|---------|----------------|------|
| Módulo indisponível | URL/credencial errada | Revisar **Configuração → Módulos** ou `modules.yaml` |
| Sem alarmes | Módulo desabilitado ou fonte limpa | Ativar módulo; forçar collect via API |
| Guacamole 403 | Usuário não é admin | Login como admin |
| Grafana vazio | Token Infinity incorreto | Conferir `CIEM_GRAFANA_TOKEN` |
| Insights “desabilitados” | IA off | Admin habilita em **Configuração → IA** |
| Não exclui `admin` | É o último administrador local | Crie outro admin antes |
| Sessão abre URL inválida | Prefixo `/api` duplicado | Atualize o portal (SSO já devolve `/api/...`) |

Mais detalhes: [DEPLOYMENT.md](DEPLOYMENT.md), [PORTAL.md](PORTAL.md), [CHANGELOG_FEATURES.md](CHANGELOG_FEATURES.md).
