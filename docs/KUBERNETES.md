# Kubernetes — deploy do CIEM

Manifests para subir a plataforma em pods isolados, espelhando a arquitetura Docker Compose.

## Pré-requisitos

- Cluster Kubernetes 1.25+
- `kubectl` configurado
- Ingress Controller (NGINX recomendado)
- Secret TLS wildcard (`ciem-wildcard-tls`)
- Imagens no GHCR (publicadas pelo workflow CD): `ghcr.io/avilarezende/ciem-*`

## Ordem de aplicação

Aplique os arquivos **na ordem numérica**:

```bash
kubectl apply -f deploy/kubernetes/00-namespace.yaml
kubectl apply -f deploy/kubernetes/01-configmap.yaml
# Edite e aplique secrets (não versione senhas reais):
kubectl apply -f deploy/kubernetes/02-secrets.example.yaml
kubectl apply -f deploy/kubernetes/03-core.yaml
kubectl apply -f deploy/kubernetes/04-portal.yaml
kubectl apply -f deploy/kubernetes/05-modules.yaml
kubectl apply -f deploy/kubernetes/06-grafana.yaml
kubectl apply -f deploy/kubernetes/07-guacamole.yaml
kubectl apply -f deploy/kubernetes/08-storage.yaml
kubectl apply -f deploy/kubernetes/09-ingress.yaml
```

Ou tudo de uma vez (após configurar Secrets):

```bash
kubectl apply -f deploy/kubernetes/
```

## Personalizar antes do deploy

### 1. ConfigMap (`01-configmap.yaml`)

Substitua os stubs pelos conteúdos reais de `config/`:

```bash
kubectl create configmap ciem-config -n ciem \
  --from-file=main.yaml=config/main.yaml \
  --from-file=modules.yaml=config/modules.yaml \
  --from-file=auth.yaml=config/auth.yaml \
  --from-file=targets.yaml=config/targets.yaml \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 2. Secrets (`02-secrets.example.yaml`)

| Secret | Uso |
|--------|-----|
| `ciem-secrets` | `CIEM_SECRET_KEY`, `CIEM_GRAFANA_TOKEN`, credenciais Zabbix, etc. |
| `ciem-wildcard-tls` | Certificado TLS do Ingress |
| `grafana-admin` | Senha admin Grafana |

Copie o exemplo e preencha:

```bash
cp deploy/kubernetes/02-secrets.example.yaml deploy/kubernetes/02-secrets.yaml
# edite valores em base64
kubectl apply -f deploy/kubernetes/02-secrets.yaml
```

> **Não commite** `02-secrets.yaml` com valores reais — use Sealed Secrets ou vault do cluster.

### 3. Ingress (`09-ingress.yaml`)

Altere `ciem.exemplo.local` para seu domínio e confira paths:

| Path | Serviço |
|------|---------|
| `/api` | ciem-core:8000 |
| `/grafana` | grafana:3000 |
| `/guacamole` | guacamole:8080 |
| `/` | ciem-portal:80 |

## Arquitetura de pods

```
Namespace: ciem
├── ciem-core          (API ZTNA)
├── ciem-portal        (SPA)
├── module-zabbix      (coletor, porta 8080)
├── module-cacti
├── module-nagios
├── module-topdesk
├── module-inventory
├── module-syslog
├── grafana
├── guacamole + guacd
└── PVC: ciem-audit-pvc, grafana-data-pvc, guacamole-recordings-pvc
```

O **proxy SSL** em produção costuma ser o próprio Ingress; para paridade com Docker, use um Deployment nginx separado ou service mesh.

## Comunicação interna

O core resolve módulos por DNS de cluster:

```
http://module-zabbix:8080/collect
http://module-cacti:8080/collect
...
```

Confirme que os Services em `05-modules.yaml` usam porta **8080** (não 8101).

## Verificação pós-deploy

```bash
kubectl get pods -n ciem
kubectl logs -n ciem deployment/ciem-core --tail=50
kubectl port-forward -n ciem svc/ciem-core 8000:8000
curl http://localhost:8000/health
```

## Atualizar configuração

```bash
# Recriar ConfigMap a partir dos YAML locais
kubectl create configmap ciem-config -n ciem --from-file=config/ \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl rollout restart deployment -n ciem -l app.kubernetes.io/part-of=ciem-ztna
```

## Escalar

| Componente | Replicas sugeridas |
|------------|-------------------|
| ciem-core | 1–2 (stateless; compartilhe PVC de auditoria com ReadWriteMany se >1) |
| Módulos | 1 cada (stateless) |
| grafana | 1 |
| guacamole + guacd | 1 cada |

## Rancher

Metadados do catálogo: [deploy/rancher/catalog.yaml](../rancher/catalog.yaml)

## Referências

- [GETTING_STARTED.md](../docs/GETTING_STARTED.md)  
- [CONFIGURATION.md](../docs/CONFIGURATION.md)  
- [PROCESSES.md](../docs/PROCESSES.md)  
