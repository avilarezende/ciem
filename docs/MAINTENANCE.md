# Manutenção Remota — Sessões ZTNA

O CIEM permite que administradores de sistema conectem-se a servidores, roteadores e switches na **rede de gerência restrita** via sessões criptografadas (SSL) gerenciadas pelo proxy.

## Como funciona

```
Sysadmin → Portal CIEM → Proxy SSL → Guacamole → guacd → Equipamento (SSH/RDP/VNC)
                                              ↓
                                        audit.jsonl
```

1. Admin autentica no portal CIEM
2. Seleciona alvo de manutenção (definido em `config/targets.yaml`)
3. CIEM inicia sessão via Guacamole
4. Conexão criptografada através do proxy (certificado wildcard)
5. Toda a sessão é registrada: quem, quando, comandos, duração

## Protocolos suportados

| Protocolo | Porta padrão | Uso típico |
|-----------|-------------|------------|
| SSH | 22 | Linux, roteadores, switches |
| RDP | 3389 | Windows Server |
| VNC | 5900 | Ambientes gráficos |

## Configurar alvos

Em `config/targets.yaml`:

```yaml
targets:
  - id: rtr-core-01
    name: "Roteador Core"
    hostname: "10.10.0.1"
    port: 22
    protocol: ssh
    description: "Roteador core — VLANs de gerência"
    tags: [roteador, core]
    enabled: true

  - id: srv-win-ad
    name: "Controlador de Domínio"
    hostname: "10.10.2.5"
    port: 3389
    protocol: rdp
    enabled: true

credentials:
  rtr-core-01:
    username: "admin"
    ssh_key_path: "/etc/ciem/keys/rtr-core-01.pem"

  srv-win-ad:
    username: "administrador"
    password: ""    # ou use vault externo
```

## Auditoria de sessões

Cada sessão gera um registro em `data/audit/sessions.jsonl`:

```json
{
  "session_id": "sess-20260901143000-admin",
  "user": "admin",
  "target_host": "rtr-core-01",
  "protocol": "ssh",
  "started_at": "2026-09-01T14:30:00+00:00",
  "ended_at": "2026-09-01T15:15:00+00:00",
  "commands": ["show ip route", "show interfaces status"],
  "duration_seconds": 2700.0,
  "logged_at": "2026-09-01T15:15:01+00:00"
}
```

### Consultar auditoria via API

```bash
curl https://ciem.exemplo.local/api/sessions/audit \
  -H "Authorization: Bearer ciem-admin"
```

### Configuração de gravação

Em `config/main.yaml`:

```yaml
guacamole:
  record_commands: true       # Gravar comandos SSH (recomendado)
  record_rdp_video: false     # Gravar vídeo RDP (requer mais disco)
  max_session_minutes: 480    # Limite de 8 horas por sessão
```

## Rede de gerência

Sub-redes permitidas (configurável em `main.yaml`):

```yaml
management_network:
  allowed_subnets:
    - 10.0.0.0/8
    - 172.16.0.0/12
    - 192.168.0.0/16
  allowed_protocols:
    - ssh
    - rdp
    - vnc
```

## API de sessões

### Iniciar sessão

```bash
curl -X POST https://ciem.exemplo.local/api/sessions/start \
  -H "Authorization: Bearer ciem-admin" \
  -H "Content-Type: application/json" \
  -d '{"target_id": "rtr-core-01", "protocol": "ssh"}'
```

Resposta:
```json
{
  "session_id": "sess-20260901143000-admin",
  "status": "started",
  "guacamole_url": "/guacamole/#/client/sess-20260901143000-admin"
}
```

### Encerrar sessão

```bash
curl -X POST https://ciem.exemplo.local/api/sessions/end \
  -H "Authorization: Bearer ciem-admin" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "sess-...", "commands": ["show ip route"]}'
```

## Segurança

- Apenas usuários com papel **admin** podem iniciar sessões
- Conexões passam pelo proxy com SSL/TLS (certificado wildcard)
- guacd roda em container isolado na rede interna
- Credenciais de alvos nunca expostas ao frontend
- Registro completo para compliance e auditoria

## Chaves SSH

Monte chaves SSH via volume Docker:

```yaml
# docker-compose.yml
volumes:
  - ./keys:/etc/ciem/keys:ro
```

Ou via Kubernetes Secret:

```bash
kubectl create secret generic ciem-ssh-keys \
  --from-file=rtr-core-01.pem=./keys/rtr-core-01.pem \
  -n ciem
```
