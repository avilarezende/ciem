# Autenticação e Autorização

O CIEM suporta dois métodos de autenticação: **usuários locais** e **LDAP/Active Directory**.

## Papéis (roles)

| Papel | Código | Permissões |
|-------|--------|-----------|
| **Observador** | `observer` | Visualiza dashboards, alarmes ativos, histórico de eventos |
| **Administrador** | `admin` | Tudo do observador + configura módulos, inicia sessões de manutenção, gerencia usuários, acessa auditoria |

## Usuários locais

Definidos em `config/auth.yaml`:

```yaml
local_users:
  - username: admin
    password_hash: "salt$digest"   # PBKDF2-SHA256
    role: admin
    enabled: true

  - username: observador
    password_hash: "salt$digest"
    role: observer
    enabled: true
```

### Gerar hash de senha

```bash
export PYTHONPATH=shared
python -c "from ciem_common.auth import hash_password; print(hash_password('minha_senha'))"
```

Cole o resultado no campo `password_hash`.

### Credenciais padrão (desenvolvimento)

| Usuário | Senha | Papel |
|---------|-------|-------|
| admin | admin123 | admin |
| observador | observer123 | observer |

> Altere imediatamente em produção!

## LDAP / Active Directory

```yaml
ldap:
  enabled: true
  server_url: "ldaps://ldap.exemplo.local:636"
  base_dn: "ou=usuarios,dc=exemplo,dc=local"
  user_filter: "(uid=%s)"
  bind_dn: "cn=ciem-service,ou=servicos,dc=exemplo,dc=local"
  bind_password: ""              # ou LDAP_BIND_PASSWORD no .env
  display_name_attribute: "cn"
  group_role_mapping:
    "cn=ciem-admins,ou=grupos,dc=exemplo,dc=local": admin
    "cn=ciem-observers,ou=grupos,dc=exemplo,dc=local": observer
  default_role: observer
  verify_ssl: true
```

### Fluxo LDAP

1. Usuário informa login/senha no portal
2. CIEM tenta autenticação local primeiro
3. Se falhar e LDAP habilitado, consulta o servidor LDAP
4. Mapeia grupos LDAP → papéis CIEM via `group_role_mapping`
5. Retorna token de sessão

### Variáveis de ambiente LDAP

```bash
LDAP_BIND_PASSWORD=senha-do-servico
```

## API de autenticação

### Login

```bash
curl -X POST https://ciem.exemplo.local/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

Resposta:
```json
{
  "token": "ciem-admin",
  "username": "admin",
  "role": "admin",
  "display_name": "admin"
}
```

### Usar token

```bash
curl https://ciem.exemplo.local/api/alarms/active \
  -H "Authorization: Bearer ciem-admin"
```

## Segurança

- Senhas locais armazenadas como hash PBKDF2-SHA256 (260.000 iterações)
- Comunicação via HTTPS (certificado wildcard no proxy)
- Tokens simples para desenvolvimento — em produção, considere JWT com expiração
- LDAP via `ldaps://` recomendado
- Sessões de manutenção auditadas independentemente da autenticação

## Proteção de endpoints

| Endpoint | Papel mínimo |
|----------|-------------|
| `GET /health` | Público |
| `GET /alarms/active` | observer |
| `GET /history` | observer |
| `GET /config/modules` | observer |
| `GET /config/main` | admin |
| `POST /sessions/start` | admin |
| `GET /sessions/audit` | admin |
