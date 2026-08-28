"""Coletores de fontes para RAG."""

from collectors.cacti import collect_cacti
from collectors.grafana import collect_grafana
from collectors.popse_site import collect_popse_site
from collectors.zabbix import collect_zabbix

COLLECTORS = {
    "popse_site": collect_popse_site,
    "zabbix": collect_zabbix,
    "cacti": collect_cacti,
    "grafana": collect_grafana,
}
