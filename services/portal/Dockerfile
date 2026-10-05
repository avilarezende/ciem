FROM httpd:2.4-alpine@sha256:3440c39d8d6f54fa9ad2549e5a60c19ddd435faadc29c1ad28aa795f71888889

COPY services/portal/public/ /usr/local/apache2/htdocs/

# Proxy reverso para API core (configurado via proxy principal)
EXPOSE 80
