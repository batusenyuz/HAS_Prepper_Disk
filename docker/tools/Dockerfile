# İndirici / downloader: kiwix-manage (Kiwix imajından) + pmtiles + bash/curl/wget
ARG KIWIX_VERSION=3.8.2
FROM ghcr.io/kiwix/kiwix-serve:${KIWIX_VERSION}

ARG PMTILES_VERSION=1.31.2
ARG TARGETARCH
USER root
RUN apk add --no-cache bash curl wget coreutils grep sed tzdata ca-certificates poppler-utils python3 \
 && case "${TARGETARCH:-arm64}" in \
      amd64) a=x86_64 ;; arm64) a=arm64 ;; *) echo "desteklenmeyen mimari: $TARGETARCH" >&2; exit 1 ;; \
    esac \
 && curl -fsSL "https://github.com/protomaps/go-pmtiles/releases/download/v${PMTILES_VERSION}/go-pmtiles_${PMTILES_VERSION}_Linux_${a}.tar.gz" \
    | tar xz -C /usr/local/bin pmtiles \
 && pmtiles version

COPY entrypoint.sh download-maps.sh download-docs.sh download-megep.py /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/download-maps.sh /usr/local/bin/download-docs.sh

ENV PREPPER_DOCKER=1 ZIM_ROOT=/data/zims MAPS_DIR=/data/maps DOCS_DIR=/data/docs HOME=/tmp
USER 1001
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["help"]
