#!/usr/bin/env bash
# docker compose run --rm downloader <komut / command>
set -euo pipefail

case "${1:-help}" in
  zims)        shift; exec bash /scripts/download-content.sh "${1:-/config/content.conf}" ;;
  maps)        shift; exec download-maps.sh "${1:-/config/maps.conf}" ;;
  docs)        rc=0; python3 /usr/local/bin/download-megep.py /config/megep.conf || rc=1
               download-docs.sh /config/docs.conf || rc=1; exit $rc ;;
  maps-size)   shift; DRY_RUN=1 exec download-maps.sh "${1:-/config/maps.conf}" ;;
  all)         rc=0  # biri hata verse de diğeri çalışsın / keep going if one step fails
               bash /scripts/download-content.sh /config/content.conf || rc=1
               python3 /usr/local/bin/download-megep.py /config/megep.conf || rc=1
               download-docs.sh /config/docs.conf || rc=1
               download-maps.sh /config/maps.conf || rc=1; exit $rc ;;
  sh|bash)     exec bash ;;
  *) cat <<'EOF'
Kullanım / usage:  docker compose run --rm downloader <komut>

  zims       config/content.conf içindeki ZIM'leri indir/güncelle (Kiwix)
             download/update the ZIMs listed in config/content.conf
  maps       config/maps.conf içindeki harita bölgelerini indir (Protomaps)
             download the map regions in config/maps.conf
  docs       config/docs.conf + config/megep.conf Türkçe PDF belgeleri indir
             download the Turkish PDFs in config/docs.conf and config/megep.conf
  maps-size  haritaları indirmeden boyutlarını göster / show map sizes without downloading
  all        zims + docs + maps
  sh         kabuk aç / open a shell
EOF
  ;;
esac
