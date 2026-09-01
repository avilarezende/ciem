FROM httpd:2.4-alpine

COPY services/portal/public/ /usr/local/apache2/htdocs/

# Proxy reverso para API core (configurado via proxy principal)
EXPOSE 80
