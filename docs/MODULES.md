# Módulos Coletores

Cada módulo é um **serviço independente** que coleta dados de um sistema de monitoramento existente via sua interface web/API. O CIEM não substitui esses sistemas — apenas consulta e agrega os dados.

## Princípios

1. **Isolamento** — cada módulo roda em container/pod separado
2. **Independência** — módulos não se comunicam entre si
3. **Ativação seletiva** — habilite apenas o que precisa em `config/modules.yaml` **ou no portal**
4. **Coleta direta** — dados vêm dos sistemas existentes, não do CIEM

## Configuração pelo portal (admin)

1. Login como administrador  
2. Sidebar **Configuração** → seção **Módulos**  
3. Ative o **switch** do módulo desejado  
4. Com o módulo **ON**, o formulário exibe campos de opções (URL, credenciais, filtros, etc.)  
5. **Salvar** — persiste `enabled` e `options` em `config/modules.yaml`  

Observers veem o efeito (alarmes, dashboards, status ONLINE/OFFLINE), mas **não** alteram a configuração.

Campos típicos por módulo estão descritos abaixo e espelhados em `services/portal/public/js/portal.js` (`MODULE_FIELDS`).

## Módulos disponíveis

| Módulo | Container | Porta | Sistema | Protocolo |
|--------|-----------|-------|---------|-----------|
| zabbix | module-zabbix | 8101 | Zabbix | JSON-RPC API |
| cacti | module-cacti | 8102 | Cacti | Web API |
| nagios | module-nagios | 8103 | Nagios/Nagios XI | REST API |
| topdesk | module-topdesk | 8104 | TOPdesk | REST API |
| inventory | module-inventory | 8105 | Inventário genérico | REST API |
| syslog | module-syslog | 8106 | Syslog centralizado | REST API / arquivo |

## Formato de resposta normalizado

Todos os módulos retornam o mesmo formato JSON:

```json
{
  "module": "zabbix",
  "timestamp": "2026-09-01T19:00:00+00:00",
  "status": "ok",
  "active_alarms": [
    {
      "id": "zabbix-problem-12345",
      "severity": "critical",
      "message": "Link principal IFS indisponível",
      "source": "zabbix",
      "timestamp": "2026-09-01T18:55:00+00:00"
    }
  ],
  "history_events": [
    {
      "id": "zabbix-host-100",
      "event_type": "host",
      "message": "Host monitorado: servidor-web-01",
      "timestamp": "2026-09-01T19:00:00+00:00"
    }
  ]
}
```

## Configuração por módulo

### Zabbix

```yaml
# config/modules.yaml
zabbix:
  enabled: true
  options:
    url: "https://zabbix.exemplo.local"
    username: "ciem-collector"
    password: "senha"
    verify_ssl: true
    problem_limit: 50
```

Coleta: hosts monitorados, triggers ativos, problemas em aberto.

### Cacti

```yaml
cacti:
  enabled: true
  options:
    url: "https://cacti.exemplo.local"
    username: "admin"
    password: "senha"
    verify_ssl: true
```

Coleta: dispositivos de rede, gráficos de performance.

### Nagios / Nagios XI

```yaml
nagios:
  enabled: true
  options:
    url: "https://nagios.exemplo.local"
    api_key: "sua-chave-api"
    verify_ssl: true
```

Coleta: status de hosts (UP/DOWN), serviços com problemas.

### TOPdesk

```yaml
topdesk:
  enabled: true
  options:
    url: "https://topdesk.exemplo.local"
    username: "ciem"
    application_password: "senha-app"
```

Coleta: chamados abertos, incidentes recentes.

### Inventory

```yaml
inventory:
  enabled: true
  options:
    url: "https://inventory.exemplo.local/api/v1/assets"
    api_key: "chave"
    verify_ssl: true
```

Coleta: ativos de rede via API REST genérica.

### Syslog

```yaml
syslog:
  enabled: true
  options:
    url: "https://graylog.exemplo.local/api/search"
    api_key: "chave"
    # OU arquivo local:
    file_path: "/var/log/syslog"
    severity_filter: ["warning", "error", "critical"]
```

Coleta: eventos de syslog com severidade filtrada.

## Ativar/desativar módulos

### Via YAML

```yaml
# config/modules.yaml
modules:
  zabbix:
    enabled: true    # ← ativo
  cacti:
    enabled: false   # ← desativado (container não inicia)
```

### Via Docker Compose

```bash
# Apenas Zabbix e Nagios
docker compose --profile core --profile module-zabbix --profile module-nagios up -d
```

### Via Kubernetes

Aplique apenas os Deployments dos módulos desejados em `deploy/kubernetes/`.

## Desenvolvimento de novos módulos

1. Crie diretório em `services/modules/seu-modulo/`
2. Implemente `CollectorModule` de `shared/ciem_common/collector.py`
3. Use `create_collector_app()` para expor `/health` e `/collect`
4. Adicione entrada em `config/modules.yaml`
5. Adicione serviço em `deploy/docker/docker-compose.yml`

```python
# services/modules/seu-modulo/main.py
from ciem_common import CollectorModule, create_collector_app, CollectResponse

class SeuModuloCollector(CollectorModule):
    name = "seu-modulo"
    async def collect(self) -> CollectResponse:
        # ... coleta dados do sistema externo
        return CollectResponse(module=self.name, status="ok", ...)

app = create_collector_app(SeuModuloCollector(config))
```

## Testar módulo isoladamente

```bash
cd services/modules/zabbix
pip install -r requirements.txt
export PYTHONPATH=../../../shared
uvicorn main:app --port 8101
curl http://localhost:8101/health
curl -X POST http://localhost:8101/collect
```
