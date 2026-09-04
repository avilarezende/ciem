# Guia de uso — CIEM

Manual para operadores de NOC e administradores que usam o portal no dia a dia.

## Acesso

1. Abra `https://<seu-dominio>/`  
2. Entre com usuário local (`config/auth.yaml`) ou LDAP (se o admin tiver habilitado)  
3. O token fica no navegador até **Sair** ou expiração da sessão  

Credenciais padrão de desenvolvimento: `admin` / `admin123` (altere em produção — ver [AUTH.md](AUTH.md)).

### URLs dos serviços

| Serviço | URL | Quem acessa |
|---------|-----|-------------|
| Portal | `/` | Todos autenticados |
| API | `/api/` | Integrações (Bearer token) |
| Grafana | `/grafana/` | Todos autenticados (via proxy) |
| Guacamole | `/guacamole/` | Admin (SSO a partir do portal) |

## Fluxo diário recomendado

```
1. Login no portal
2. Dashboard → módulos ONLINE, banner de alarmes e status de Insights IA (se ativo)
3. Alarmes → triagem por severidade (critical primeiro)
4. Grafana / Insights IA → análise detalhada, tendências e recomendações
5. (Admin) Sessões → conectar no alvo e executar manutenção
6. (Admin) Auditoria → confirmar registro da sessão
7. (Admin) Configuração → módulos, usuários/LDAP ou provedor de IA conforme necessário
```

## Por papel

### Observer (visualização)

- Monitorar dashboard e alarmes  
- Consultar histórico de eventos  
- Abrir Grafana e, **se a IA estiver habilitada**, ver insights/recomendações  
- **Não** inicia sessões remotas nem altera configuração  

### Admin (operação e configuração)

- Tudo do observer  
- Iniciar sessão Guacamole (todos os alvos ou por alvo)  
- Consultar log de auditoria  
- **Configuração** no portal:
  - Usuários locais (criar, alterar senha, desabilitar, excluir)
  - LDAP / AD (servidor, porta, SSL, domínio, UID, bind, certificados)
  - Módulos coletores (switch + formulário de URL/credenciais/opções)
  - Inteligência Artificial (URL, API key, modelo; resultados ficam visíveis a todos)

## Operações comuns

### Verificar saúde dos coletores

**Portal:** Dashboard → cards dos módulos (verde = ONLINE)  

**API:**

```bash
curl -H "Authorization: Bearer ciem-admin" \
  https://ciem.exemplo.local/api/modules/status
```

### Forçar coleta de um módulo

```bash
curl -X POST -H "Authorization: Bearer ciem-admin" \
  https://ciem.exemplo.local/api/modules/zabbix/collect
```

### Listar alarmes ativos

**Portal:** aba **Alarmes**  

**API:** `GET /api/alarms/active`  

### Abrir Grafana / Insights IA

- Barra superior **Grafana** ou `/grafana/`  
- No portal embutido: aba **Insights IA** (quando habilitado pelo admin)  
- Credenciais Grafana padrão: `admin` / `admin` (altere via `.env` ou Secret)

Detalhes de IA: [AI.md](AI.md).

### Conectar em servidor (admin)

1. Aba **Sessões**  
2. **Conectar** no alvo desejado (ou **Abrir Guacamole** para lista completa)  
3. SSO redireciona sem pedir senha novamente  
4. Ao encerrar, a sessão é registrada em auditoria  

### Habilitar ou configurar um módulo (admin)

1. **Configuração → Módulos coletores**  
2. Ative o switch do módulo  
3. Preencha o formulário (URL, usuário/senha ou API key, opções)  
4. **Salvar** — grava em `config/modules.yaml`  

Alternativa: editar o YAML e reiniciar o serviço do módulo (Docker/K8s). Ver [MODULES.md](MODULES.md).

### Gerenciar usuários e LDAP (admin)

1. **Configuração → Usuários locais** — criar, alterar senha, excluir  
2. **Configuração → LDAP** — habilitar e preencher apontamentos  
3. Admin padrão `admin` continua válido mesmo com LDAP ativo  

Guia completo: [AUTH.md](AUTH.md).

### Ativar Insights de IA (admin)

1. **Configuração → Inteligência Artificial**  
2. Habilitar e preencher URL, API key e modelo  
3. **Salvar** → opcionalmente **Gerar insights agora**  
4. Todos os usuários passam a ver os resultados no portal/Grafana  

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
| Módulo OFFLINE | URL/credencial errada | Revisar formulário em Configuração ou `modules.yaml`; logs do container |
| Sem alarmes | Módulo desabilitado ou fonte sem problemas | Ativar módulo; `POST /api/modules/{nome}/collect` |
| Guacamole 403 | Usuário não é admin | Login como admin |
| Grafana vazio | Token Infinity incorreto | Confira `CIEM_GRAFANA_TOKEN` no core e Grafana |
| Insights “desabilitados” | IA off ou só admin configurou depois | Admin habilita em Configuração → IA |
| Não consegue excluir `admin` | É o último administrador local | Crie outro admin antes |

Mais detalhes: [DEPLOYMENT.md](DEPLOYMENT.md), [CHANGELOG_FEATURES.md](CHANGELOG_FEATURES.md).
