# Implantação — Docker, Kubernetes e Rancher

O CIEM suporta três modos de implantação. O administrador escolhe conforme a infraestrutura disponível.

## Docker Compose (recomendado para início)

### Perfis disponíveis

| Perfil | Serviços incluídos |
|--------|-------------------|
| `core` | proxy + core + portal |
| `modules` | todos os módulos coletores |
| `module-zabbix` | apenas Zabbix |
| `module-cacti` | apenas Cacti |
| `grafana` | Grafana |
| `guacamole` | Guacamole + guacd |
| `full` | tudo |

### Comandos

```bash
# Mínimo viável
docker compose -f deploy/docker/docker-compose.yml --profile core up -d --build

# Core + módulos específicos
docker compose -f deploy/docker/docker-compose.yml \
  --profile core --profile module-zabbix --profile module-nagios up -d --build

# Plataforma completa
docker compose -f deploy/docker/docker-compose.yml --profile full up -d --build

# Verificar saúde
curl -k https://localhost/api/health
docker compose -f deploy/docker/docker-compose.yml ps
```

### Certificados SSL

```bash
mkdir -p certs
# Copie seu certificado wildcard:
cp /caminho/wildcard.crt certs/
cp /caminho/wildcard.key certs/
```

Para desenvolvimento (certificado autoassinado):

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/wildcard.key -out certs/wildcard.crt \
  -subj "/CN=ciem.local"
```

## Kubernetes

Manifests numerados em [`deploy/kubernetes/`](../deploy/kubernetes/README.md). **Guia completo:** [KUBERNETES.md](KUBERNETES.md).

### Pré-requisitos

- Cluster Kubernetes 1.25+
- Ingress controller (nginx recomendado)
- Certificado wildcard como Secret TLS

### Instalação

```bash
kubectl apply -f deploy/kubernetes/00-namespace.yaml

kubectl create configmap ciem-config -n ciem \
  --from-file=config/main.yaml \
  --from-file=config/modules.yaml \
  --from-file=config/auth.yaml \
  --from-file=config/targets.yaml

cp deploy/kubernetes/02-secrets.example.yaml deploy/kubernetes/02-secrets.yaml
# Edite secrets e aplique (não commite 02-secrets.yaml)
kubectl apply -f deploy/kubernetes/02-secrets.yaml

kubectl apply -f deploy/kubernetes/03-core.yaml \
  -f deploy/kubernetes/04-portal.yaml \
  -f deploy/kubernetes/05-modules.yaml \
  -f deploy/kubernetes/06-grafana.yaml \
  -f deploy/kubernetes/07-guacamole.yaml \
  -f deploy/kubernetes/08-storage.yaml \
  -f deploy/kubernetes/09-ingress.yaml

kubectl get pods -n ciem
kubectl logs -f deployment/ciem-core -n ciem
```

### Escalar módulos individualmente

Cada módulo é um Deployment em `05-modules.yaml`. Para desabilitar um módulo, defina `enabled: false` em `modules.yaml` e escale para zero:

```bash
kubectl scale deployment/module-cacti -n ciem --replicas=0
```

## Rancher

1. Acesse Rancher → **Apps & Marketplace**
2. Adicione repositório Git: `https://github.com/avilarezende/ciem`
3. Selecione o chart em `deploy/kubernetes/`
4. Configure valores:
   - `config.main.platform_name`: CIEM
   - `modules.zabbix.enabled`: true
   - `proxy.public_domain`: ciem.sua-rede.local
5. Deploy

Veja `deploy/rancher/catalog.yaml` para metadados do catálogo.

## Variáveis de ambiente

| Variável | Serviço | Descrição |
|----------|---------|-----------|
| `CONFIG_PATH` | core, módulos | Caminho dos YAMLs |
| `CIEM_SECRET_KEY` | core | Chave secreta da API |
| `GRAFANA_ADMIN_USER` | grafana | Usuário admin Grafana |
| `GRAFANA_ADMIN_PASSWORD` | grafana | Senha admin Grafana |
| `ZABBIX_URL` | module-zabbix | URL do Zabbix |
| `ZABBIX_USERNAME` | module-zabbix | Usuário Zabbix |
| `ZABBIX_PASSWORD` | module-zabbix | Senha Zabbix |
| `LDAP_BIND_PASSWORD` | core | Senha bind LDAP |

## Atualização

```bash
# Docker Compose
docker compose -f deploy/docker/docker-compose.yml --profile full pull
docker compose -f deploy/docker/docker-compose.yml --profile full up -d --build

# Kubernetes
kubectl rollout restart deployment/ciem-core -n ciem
kubectl rollout restart deployment/module-zabbix -n ciem
```

## Backup

Arquivos importantes para backup:

| Dado | Localização |
|------|------------|
| Configuração | `config/*.yaml` |
| Auditoria de sessões | volume `ciem-audit` |
| Dados Grafana | volume `grafana-data` |
| Certificados | `certs/` |
| Chaves SSH | `keys/` |

## Troubleshooting

```bash
# Logs do core
docker compose -f deploy/docker/docker-compose.yml logs ciem-core

# Testar módulo isolado (porta interna 8080)
curl http://module-zabbix:8080/health
curl -X POST http://module-zabbix:8080/collect

# Verificar rede interna
docker compose -f deploy/docker/docker-compose.yml exec ciem-core \
  python -c "import httpx; print(httpx.get('http://module-zabbix:8080/health').json())"
```
