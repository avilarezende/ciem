FROM guacamole/guacamole:1.5.5

USER root

# Extensões: arquivo (conexões) + header (SSO via X-CIEM-User)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates python3 \
    && curl -fsSL \
      "https://archive.apache.org/dist/guacamole/1.5.5/binary/guacamole-auth-file-1.5.5.tar.gz" \
      | tar -xz -C /tmp \
    && curl -fsSL \
      "https://archive.apache.org/dist/guacamole/1.5.5/binary/guacamole-auth-header-1.5.5.tar.gz" \
      | tar -xz -C /tmp \
    && cp /tmp/guacamole-auth-file-1.5.5/guacamole-auth-file-1.5.5.jar /etc/guacamole/extensions/ \
    && cp /tmp/guacamole-auth-header-1.5.5/guacamole-auth-header-1.5.5.jar /etc/guacamole/extensions/ \
    && rm -rf /tmp/guacamole-auth-file-* /tmp/guacamole-auth-header-* \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY shared/ /opt/ciem/shared/
COPY services/guacamole/provision.py /opt/ciem/provision.py
COPY services/guacamole/entrypoint.sh /opt/ciem/entrypoint.sh

RUN chmod +x /opt/ciem/entrypoint.sh \
    && mkdir -p /etc/guacamole /recordings \
    && chown -R guacamole:guacamole /etc/guacamole /recordings

ENV PYTHONPATH=/opt/ciem/shared \
    CONFIG_PATH=/config \
    GUACD_HOSTNAME=guacd

VOLUME ["/config", "/etc/ciem/keys", "/recordings"]

USER guacamole

EXPOSE 8080

ENTRYPOINT ["/opt/ciem/entrypoint.sh"]
