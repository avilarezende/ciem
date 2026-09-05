# Primeiros passos — CIEM

Este guia leva você do clone ao portal funcionando. Para Kubernetes, siga também [KUBERNETES.md](KUBERNETES.md).

## Pré-requisitos

| Ambiente | Requisito |
|----------|-----------|
| **Docker** | Docker Compose v2, 4 GB RAM livres |
| **Kubernetes** | Cluster 1.25+, Ingress NGINX, certificado TLS |
| **Produção** | Certificado wildcard, DNS apontando para o proxy/ingress |

## 1. Obter o código

```bash
git clone https://github.com/avilarezende/ciem.git
cd ciem
cp .env.example .env
```

## 2. Configurar (ordem recomendada)

Edite os YAML em `config/` — todos comentados em português.

### `config/main.yaml`

- `platform_name` — nome no portal e Grafana  
- `proxy.public_domain` — domínio do certificado wildcard  
- `audit_log_path` — onde gravar auditoria de sessões  

### `config/modules.yaml`

Ative apenas os coletores que você usa:

```yaml
zabbix:
  enabled: true
  options:
    url: "https://zabbix.sua-rede.local"
    username: "${ZABBIX_USERNAME}"
    password: "${ZABBIX_PASSWORD}"
```

Credenciais sensíveis podem ir no `.env` (veja `.env.example`).

### `config/auth.yaml`

Usuários locais para o portal (PBKDF2). Padrão de desenvolvimento:

| Usuário | Senha | Papel |
|---------|-------|-------|
| `admin` | `admin123` | admin |
| `observador` | `observer123` | observer |

**Altere em produção.** No portal: sidebar **Configuração → Usuários → Alterar senha**.  
Detalhes (LDAP, exclusão do admin, CLI): [AUTH.md](AUTH.md).

### `config/ai.yaml`

Insights de IA (opcional). Só admin configura; com `enabled: true`, todos veem os resultados. Ver [AI.md](AI.md).

### `config/targets.yaml`

Alvos de manutenção (SSH/RDP/VNC) para o Guacamole — veja [MAINTENANCE.md](MAINTENANCE.md).

## 3. Subir com Docker Compose

```bash
# Mínimo: portal + API + proxy
docker compose -f deploy/docker/docker-compose.yml --profile core up -d --build

# + coletores + Grafana
docker compose -f deploy/docker/docker-compose.yml \
  --profile core --profile modules --profile grafana up -d --build

# Stack completa (inclui Guacamole)
docker compose -f deploy/docker/docker-compose.yml --profile full up -d --build
```

Coloque certificados em `deploy/docker/certs/` (ou monte via volume conforme [DEPLOYMENT.md](DEPLOYMENT.md)).

## 4. Subir com Kubernetes

```bash
# Revise Secrets e domínio em deploy/kubernetes/02-secrets.example.yaml
kubectl apply -f deploy/kubernetes/
```

Detalhes: [KUBERNETES.md](KUBERNETES.md) e [deploy/kubernetes/README.md](../deploy/kubernetes/README.md).

## 5. Validar

| Verificação | Comando / URL |
|-------------|----------------|
| API saudável | `curl -k https://ciem.exemplo.local/api/health` |
| Portal | `https://ciem.exemplo.local/` |
| Grafana | `https://ciem.exemplo.local/grafana/` |
| Módulos | Login → Dashboard → cards **ONLINE** |

## 6. Próximos passos

1. Login como `admin` → sidebar **Configuração**: alterar senha; (opcional) LDAP, módulos e IA  
2. [USAGE.md](USAGE.md) — uso diário (Visão geral, Análise, papéis)  
3. [AUTH.md](AUTH.md) — usuários locais, LDAP, exclusão do admin  
4. [AI.md](AI.md) — insights de IA (se for usar)  
5. [DASHBOARDS.md](DASHBOARDS.md) — painéis Grafana  
6. [CHANGELOG_FEATURES.md](CHANGELOG_FEATURES.md) — resumo das funções recentes  
7. [PROCESSES.md](PROCESSES.md) — coleta, alarmes e sessões remotas  

## Desenvolvimento local (sem Docker)

```bash
pip install -r requirements-dev.txt
export PYTHONPATH=shared:services/core
export CONFIG_PATH=./config
uvicorn app.main:app --app-dir services/core --reload --port 8000
```

Portal estático: sirva `services/portal/public/` ou use o profile `core` do Compose.
