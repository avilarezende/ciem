
## SSO com o Portal CIEM

O Guacamole **não exige login separado** quando acessado pelo portal CIEM.

### Fluxo SSO

```
Admin no Portal → POST /api/sso/guacamole → Token SSO
       ↓
GET /api/sso/guacamole/login?token=... → Cookie ciem_sso
       ↓
Proxy nginx (auth_request) → Header X-CIEM-User → Guacamole
```

1. Admin clica **Conectar** em um alvo no portal
2. CIEM gera token SSO assinado (5 min)
3. Nova aba abre `/api/sso/guacamole/login?token=...`
4. Cookie `ciem_sso` é definido e usuário é redirecionado à conexão
5. Proxy valida cookie via `/sso/validate` e passa `X-CIEM-User` ao Guacamole
6. Guacamole autentica via **auth-header** e carrega conexões do `user-mapping.xml`

### API SSO

```bash
# Gerar sessão SSO para alvo específico
curl -X POST https://ciem.local/api/sso/guacamole \
  -H "Authorization: Bearer ciem-admin" \
  -H "Content-Type: application/json" \
  -d '{"target_id": "rtr-core-01"}'

# Abrir Guacamole com todos os alvos
curl -X POST https://ciem.local/api/sso/guacamole \
  -H "Authorization: Bearer ciem-admin" \
  -d '{}'
```

### Configuração

| Variável | Padrão | Função |
|----------|--------|--------|
| `CIEM_SECRET_KEY` | change-me | Assina tokens SSO |
| `CIEM_SSO_TTL` | 300 | Validade do token (segundos) |

### Extensões Guacamole

- `guacamole-auth-header` — autentica via `X-CIEM-User`
- `guacamole-auth-file` — conexões em `user-mapping.xml`

## Provisionamento automático

O Guacamole é provisionado automaticamente a partir de `config/targets.yaml` ao iniciar o container.

### Como funciona

1. `entrypoint.sh` executa `provision.py`
2. Lê `config/targets.yaml` e `config/auth.yaml`
3. Gera `/etc/guacamole/user-mapping.xml` com conexões SSH/RDP/VNC
4. Administradores CIEM recebem acesso a todos os alvos habilitados

### Regenerar manualmente

```bash
docker compose -f deploy/docker/docker-compose.yml exec guacamole \
  python3 /opt/ciem/provision.py --config-path /config
```

### Gravação de sessões

Todas as sessões SSH são gravadas em `/recordings` com:
- Transcript de comandos (`typescript`)
- Metadados: usuário, data, hora

Configure em `config/main.yaml`:

```yaml
guacamole:
  record_commands: true
  record_rdp_video: false
```

### Chaves SSH

Monte chaves em `./keys/` e referencie em `config/targets.yaml`:

```yaml
credentials:
  rtr-core-01:
    username: "admin"
    ssh_key_path: "/etc/ciem/keys/rtr-core-01.pem"
```

### Observadores

Por padrão, apenas admins CIEM têm conexões Guacamole. Para incluir observadores:

```bash
GUACAMOLE_INCLUDE_OBSERVERS=true docker compose --profile guacamole up -d
```
