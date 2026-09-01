FROM nginx:1.27-alpine

COPY services/proxy/nginx.conf /etc/nginx/conf.d/default.conf

# Certificados montados via volume: /etc/ciem/certs/
EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80 || exit 1
