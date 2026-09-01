
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
