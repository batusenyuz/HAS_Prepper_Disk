# İşletme katmanı üretici / business layer builder: OSM -> osmium -> tippecanoe (PMTiles)
FROM debian:trixie-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends osmium-tool tippecanoe python3 curl ca-certificates tzdata \
 && rm -rf /var/lib/apt/lists/*
COPY build-pois.sh pois.py /opt/prepper/
RUN chmod +x /opt/prepper/build-pois.sh
ENV MAPS_DIR=/data/maps HOME=/tmp
ENTRYPOINT ["/opt/prepper/build-pois.sh"]
