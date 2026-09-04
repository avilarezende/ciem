# Autenticação e Autorização

O CIEM combina **usuários locais** (sempre disponíveis) e **LDAP/Active Directory** (opcional).

## Princípios

1. **Usuários locais têm prioridade** — o login tenta `local_users` antes do LDAP.
2. **LDAP é opcional** — se não configurar (ou deixar `enabled: false`), o sistema usa só usuários locais.
3. **Admin padrão independente do LDAP** — o usuário `admin` em `config/auth.yaml` existe e autentica mesmo com LDAP ativo.

## Papéis (roles)

| Papel | Código | Permissões |
|-------|--------|-----------|
| **Observador** | `observer` | Visualiza dashboards, alarmes ativos, histórico de eventos |
| **Administrador** | `admin` | Tudo do observador + configura módulos, LDAP, usuários, sessões e auditoria |

## Usuário admin padrão

| Campo | Valor padrão |
|-------|----------------|
| Usuário | `admin` |
| Senha | `admin123` |
| Papel | `admin` |

> **Altere a senha imediatamente em produção.**

### Alterar a senha do admin

**Pelo portal (recomendado):**

1. Login como `admin`
2. **Configuração** → seção **Usuários locais**
3. Em `admin` → **Alterar senha**
4. Informe a nova senha

**Pelo arquivo / CLI:**

```bash
export PYTHONPATH=shared
python -c "from ciem_common.auth import hash_password; print(hash_password('nova_senha_segura'))"
```

Cole o hash em `config/auth.yaml`:

```yaml
local_users:
  - username: admin
    password_hash: "SAL_HEX$DIGEST_HEX"
    role: admin
    enabled: true
```

Reinicie o `ciem-core` (ou o pod) após editar o YAML manualmente.

### Excluir o usuário admin

- Só é permitido se existir **outro** administrador local ativo.
- Crie um segundo admin no portal → depois exclua ou desabilite o `admin` antigo.
- A API/portal bloqueia a exclusão do **último** admin com mensagem de erro.

### Desabilitar sem excluir

Use **Desabilitar** no portal (ou `enabled: false` no YAML). Também é bloqueado se for o último admin ativo.

## Usuários locais

Definidos em `config/auth.yaml` e gerenciáveis em **Configuração** no portal:

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

### Credenciais padrão (desenvolvimento)

| Usuário | Senha | Papel |
|---------|-------|-------|
| admin | admin123 | admin |
| observador | observer123 | observer |

### Operações no portal

| Ação | Onde |
|------|------|
| Criar usuário | Formulário **Novo usuário local** |
| Alterar senha | Botão **Alterar senha** |
| Habilitar/desabilitar | Botão **Desabilitar** / **Habilitar** |
| Excluir | Botão **Excluir** (não remove o último admin) |

### API

```bash
# Listar auth (admin)
curl -H "Authorization: Bearer ciem-admin" https://ciem.exemplo.local/api/config/auth

# Criar usuário
curl -X POST -H "Authorization: Bearer ciem-admin" -H "Content-Type: application/json" \
  -d '{"username":"ops","password":"segredo","role":"observer"}' \
  https://ciem.exemplo.local/api/config/auth/users

# Alterar senha
curl -X PUT -H "Authorization: Bearer ciem-admin" -H "Content-Type: application/json" \
  -d '{"password":"nova_senha"}' \
  https://ciem.exemplo.local/api/config/auth/users/admin

# Excluir
curl -X DELETE -H "Authorization: Bearer ciem-admin" \
  https://ciem.exemplo.local/api/config/auth/users/observador
```

## LDAP / Active Directory

Configure no portal (**Configuração → LDAP**) ou em `config/auth.yaml`.

### Campos principais

| Campo | Descrição |
|-------|-----------|
| `enabled` | Liga/desliga autenticação LDAP |
| `host` / `port` | Servidor e porta |
| `use_ssl` | LDAPS (TLS) |
| `server_url` | URL completa (opcional; senão montada de host/port) |
| `domain` | Domínio AD/LDAP |
| `base_dn` | Base DN de busca |
| `uid_attribute` | Atributo de login (`uid`, `sAMAccountName`, …) |
| `user_filter` | Filtro (`%s` = username), ex.: `(uid=%s)` |
| `bind_dn` / `bind_password` | Conta de serviço |
| `ca_cert_path` | Certificado CA / cadeia |
| `client_cert_path` | Certificado cliente (opcional) |
| `verify_ssl` | Validar certificado do servidor |
| `group_role_mapping` | Grupo LDAP → papel CIEM |
| `default_role` | Papel se não houver grupo mapeado |

### Exemplo YAML

```yaml
ldap:
  enabled: false
  host: "ldap.exemplo.local"
  port: 636
  use_ssl: true
  server_url: "ldaps://ldap.exemplo.local:636"
  domain: "exemplo.local"
  base_dn: "ou=usuarios,dc=exemplo,dc=local"
  uid_attribute: "uid"
  user_filter: "(uid=%s)"
  bind_dn: "cn=ciem-service,ou=servicos,dc=exemplo,dc=local"
  bind_password: ""
  ca_cert_path: "/etc/ciem/certs/ldap-ca.crt"
  client_cert_path: ""
  display_name_attribute: "cn"
  group_role_mapping:
    "cn=ciem-admins,ou=grupos,dc=exemplo,dc=local": admin
    "cn=ciem-observers,ou=grupos,dc=exemplo,dc=local": observer
  default_role: observer
  verify_ssl: true
```

### Fluxo de login

```
1. Usuário informa login/senha
2. CIEM autentica em local_users (admin, observador, etc.)
3. Se falhar e ldap.enabled=true → tenta LDAP
4. Sucesso → token de sessão
```

Se LDAP **não** estiver configurado ou estiver desabilitado, apenas usuários locais autenticam.

### Variáveis de ambiente

```bash
LDAP_BIND_PASSWORD=senha-do-servico
```

> A integração de bind LDAP em runtime pode ser completada em versões futuras; os apontamentos já são persistidos e editáveis pelo portal.

## API de login

```bash
curl -X POST https://ciem.exemplo.local/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

```json
{
  "token": "ciem-admin",
  "username": "admin",
  "role": "admin",
  "display_name": "admin"
}
```

## Segurança

- Senhas locais: PBKDF2-SHA256 (260.000 iterações)
- HTTPS no proxy (certificado wildcard)
- Último admin local protegido contra exclusão/desabilitação
- Preferir `ldaps://` e `ca_cert_path` em produção

## Proteção de endpoints

| Endpoint | Papel mínimo |
|----------|-------------|
| `GET /health` | Público |
| `POST /auth/login` | Público |
| `GET /alarms/active` | observer |
| `GET /config/modules` | observer |
| `PUT /config/modules/{nome}` | admin |
| `GET /config/auth` | admin |
| `PUT /config/auth/ldap` | admin |
| `POST/PUT/DELETE /config/auth/users...` | admin |
| `POST /sessions/start` | admin |
