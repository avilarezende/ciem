FROM httpd:2.4-alpine

RUN sed -i \
    's/#LoadModule proxy_module/LoadModule proxy_module/' \
    /usr/local/apache2/conf/httpd.conf && \
    sed -i \
    's/#LoadModule proxy_http_module/LoadModule proxy_http_module/' \
    /usr/local/apache2/conf/httpd.conf

COPY apache/000-default.conf /usr/local/apache2/conf/extra/popse.conf
COPY public/ /usr/local/apache2/htdocs/

RUN echo 'Include conf/extra/popse.conf' >> /usr/local/apache2/conf/httpd.conf

EXPOSE 80
