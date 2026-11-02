# Kolibri (çevrimdışı dersler / offline lessons) — /kolibri/ alt yolunda çalışır
FROM python:3.12-slim

ARG KOLIBRI_VERSION=0.19.5
RUN pip install --no-cache-dir "kolibri==${KOLIBRI_VERSION}"

ENV KOLIBRI_HOME=/data \
    KOLIBRI_HTTP_PORT=8080 \
    KOLIBRI_URL_PATH_PREFIX=/kolibri/ \
    KOLIBRI_RUN_MODE=docker \
    HOME=/tmp
VOLUME /data
EXPOSE 8080
CMD ["kolibri", "start", "--foreground"]
