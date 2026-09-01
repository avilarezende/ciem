# Manifests Kubernetes — CIEM

Aplique na **ordem numérica**. Documentação completa: [docs/KUBERNETES.md](../../docs/KUBERNETES.md).

## Arquivos

| Arquivo | Recursos |
|---------|----------|
| `00-namespace.yaml` | Namespace `ciem` |
| `01-configmap.yaml` | ConfigMap com stubs YAML (substitua pelos seus) |
| `02-secrets.example.yaml` | Modelo de Secrets — copie para `02-secrets.yaml` |
| `03-core.yaml` | Deployment + Service `ciem-core` |
| `04-portal.yaml` | Deployment + Service `ciem-portal` |
| `05-modules.yaml` | 6 coletores (porta 8080) |
| `06-grafana.yaml` | Grafana + provisioning via ConfigMap |
| `07-guacamole.yaml` | guacamole + guacd |
| `08-storage.yaml` | PVCs (auditoria, Grafana, gravações) |
| `09-ingress.yaml` | Ingress TLS e rotas |

## Quick start

```bash
# 1. Config real
kubectl apply -f 00-namespace.yaml
kubectl create configmap ciem-config -n ciem \
  --from-file=main.yaml=../../config/main.yaml \
  --from-file=modules.yaml=../../config/modules.yaml \
  --from-file=auth.yaml=../../config/auth.yaml \
  --from-file=targets.yaml=../../config/targets.yaml

# 2. Secrets (edite antes)
cp 02-secrets.example.yaml 02-secrets.yaml
kubectl apply -f 02-secrets.yaml

# 3. Stack
kubectl apply -f 03-core.yaml -f 04-portal.yaml -f 05-modules.yaml \
  -f 06-grafana.yaml -f 07-guacamole.yaml -f 08-storage.yaml -f 09-ingress.yaml
```

## Imagens (GHCR)

```
ghcr.io/avilarezende/ciem-core:main
ghcr.io/avilarezende/ciem-portal:main
ghcr.io/avilarezende/ciem-module-zabbix:main
ghcr.io/avilarezende/ciem-module-cacti:main
ghcr.io/avilarezende/ciem-module-nagios:main
ghcr.io/avilarezende/ciem-module-topdesk:main
ghcr.io/avilarezende/ciem-module-inventory:main
ghcr.io/avilarezende/ciem-module-syslog:main
```

Grafana e Guacamole usam imagens upstream (`grafana/grafana`, `guacamole/guacd`) + build custom do repositório para Guacamole.
