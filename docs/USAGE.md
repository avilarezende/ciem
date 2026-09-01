# Guia de uso — CIEM

Manual para operadores de NOC e administradores que usam o portal no dia a dia.

## Acesso

1. Abra `https://<seu-dominio>/`  
2. Entre com usuário e senha configurados em `config/auth.yaml`  
3. O token fica no navegador até **Sair** ou expiração da sessão  

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
2. Dashboard → verificar módulos ONLINE e banner de alarmes
3. Alarmes → triagem por severidade (critical primeiro)
4. Grafana → análise detalhada / tendências
5. (Admin) Sessões → conectar no alvo e executar manutenção
6. (Admin) Auditoria → confirmar registro da sessão
```

## Por papel

### Observer (visualização)

- Monitorar dashboard e alarmes  
- Consultar histórico de eventos  
- Abrir Grafana para gráficos e tabelas  
- **Não** inicia sessões remotas nem altera configuração  

### Admin (operação)

- Tudo do observer  
- Iniciar sessão Guacamole (todos os alvos ou por alvo)  
- Consultar log de auditoria  
- Ver estado dos módulos em Configuração  
- Editar YAML no repositório / ConfigMap (não no portal)  

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

### Abrir Grafana

Clique em **Grafana** na barra superior ou acesse `/grafana/`.  
Credenciais Grafana padrão: `admin` / `admin` (altere via `.env` ou Secret).

### Conectar em servidor (admin)

1. Aba **Sessões**  
2. **Conectar** no alvo desejado (ou **Abrir Guacamole** para lista completa)  
3. SSO redireciona sem pedir senha novamente  
4. Ao encerrar, a sessão é registrada em auditoria  

## Habilitar ou desabilitar um módulo

1. Edite `config/modules.yaml` → `enabled: true/false`  
2. **Docker:** `docker compose ... up -d` (recria apenas o módulo se usar profile isolado)  
3. **Kubernetes:** atualize ConfigMap e `kubectl rollout restart deployment/module-<nome> -n ciem`  

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
| Módulo OFFLINE | URL/credencial errada em `modules.yaml` | Ver logs: `docker logs module-zabbix` |
| Sem alarmes | Módulo desabilitado ou fonte sem problemas | `POST /api/modules/{nome}/collect` |
| Guacamole 403 | Usuário não é admin | Login como admin |
| Grafana vazio | Token Infinity incorreto | Confira `CIEM_GRAFANA_TOKEN` no core e Grafana |

Mais detalhes: [DEPLOYMENT.md](DEPLOYMENT.md) (troubleshooting).
