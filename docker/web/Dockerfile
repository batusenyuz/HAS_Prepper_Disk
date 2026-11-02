# Web: nginx + HAS_PrepperDisk ana sayfası + çevrimdışı harita görüntüleyici
# Harita kütüphaneleri ve fontlar derleme sırasında indirilir, çalışırken internet gerekmez.
# Map libraries and fonts are fetched at build time; no internet needed at runtime.
FROM alpine:3.22 AS assets
ARG MAPLIBRE_VERSION=5.24.0
ARG PMTILES_JS_VERSION=4.5.0
ARG BASEMAPS_VERSION=5.7.2
RUN apk add --no-cache curl tar
WORKDIR /out/maps
RUN mkdir -p lib assets \
 && curl -fsSL -o lib/maplibre-gl.js  "https://cdn.jsdelivr.net/npm/maplibre-gl@${MAPLIBRE_VERSION}/dist/maplibre-gl.js" \
 && curl -fsSL -o lib/maplibre-gl.css "https://cdn.jsdelivr.net/npm/maplibre-gl@${MAPLIBRE_VERSION}/dist/maplibre-gl.css" \
 && curl -fsSL -o lib/pmtiles.js      "https://cdn.jsdelivr.net/npm/pmtiles@${PMTILES_JS_VERSION}/dist/pmtiles.js" \
 && curl -fsSL -o lib/basemaps.js     "https://cdn.jsdelivr.net/npm/@protomaps/basemaps@${BASEMAPS_VERSION}/dist/basemaps.js" \
 && curl -fsSL https://codeload.github.com/protomaps/basemaps-assets/tar.gz/refs/heads/main \
    | tar xz --strip-components=1 -C assets basemaps-assets-main/fonts basemaps-assets-main/sprites

FROM nginxinc/nginx-unprivileged:1.29-alpine
COPY docker/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=assets /out/maps /usr/share/nginx/html/maps
COPY docker/web/maps/index.html /usr/share/nginx/html/maps/index.html
COPY docker/web/admin/ /usr/share/nginx/html/admin/
COPY www/home/ /usr/share/nginx/html/home/
EXPOSE 8080
