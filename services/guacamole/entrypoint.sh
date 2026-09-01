#!/bin/sh
# Provisiona conexões Guacamole a partir de config/targets.yaml e inicia o serviço.
set -eu

CONFIG_PATH="${CONFIG_PATH:-/config}"
OUTPUT_XML="${GUACAMOLE_USER_MAPPING:-/etc/guacamole/user-mapping.xml}"
OUTPUT_PROPS="${GUACAMOLE_PROPERTIES:-/etc/guacamole/guacamole.properties}"

echo "==> CIEM Guacamole — provisionando alvos de ${CONFIG_PATH}/targets.yaml"

export CONFIG_PATH
python3 /opt/ciem/provision.py \
  --config-path "${CONFIG_PATH}" \
  --output "${OUTPUT_XML}" \
  --properties-output "${OUTPUT_PROPS}" \
  ${GUACAMOLE_INCLUDE_OBSERVERS:+--include-observers}

echo "==> Iniciando Guacamole..."
exec /opt/guacamole/bin/entrypoint.sh "$@"
