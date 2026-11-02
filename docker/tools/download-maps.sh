#!/usr/bin/env bash
# config/maps.conf içindeki bölgeleri Protomaps dünya haritasından (PMTiles) keser ve indirir.
# Extracts the regions in config/maps.conf from the Protomaps planet build (PMTiles).
# Sadece gereken parçalar indirilir (HTTP range). Yarıda kalırsa tekrar çalıştır.
# Only the needed byte ranges are fetched. Re-run if interrupted.
#
#   DRY_RUN=1          boyutları göster, indirme / show sizes only
#   FORCE=1            var olan dosyaları yeniden indir / re-download existing files
#   PROTOMAPS_BUILD    örn./e.g. 20261102 (boş: en yeni / empty: newest)
set -uo pipefail

CONF="${1:-/config/maps.conf}"
DEST="${MAPS_DIR:-/data/maps}"
META=https://build-metadata.protomaps.dev/builds.json
mkdir -p "$DEST"

build="${PROTOMAPS_BUILD:-}"
if [ -z "$build" ]; then
  build=$(curl -fsSL "$META" | grep -oE '"key":"[0-9]{8}\.pmtiles"' | grep -oE '[0-9]{8}' | sort | tail -1)
  [ -n "$build" ] || { echo "!! Protomaps derleme listesi alınamadı / could not fetch build list ($META)"; exit 1; }
fi
SRC="https://build.protomaps.com/${build%.pmtiles}.pmtiles"
echo ">> Kaynak / source: $SRC"

failed=0
entries=()
while read -r name bbox maxzoom _; do
  case "$name" in ''|\#*) continue;; esac
  out="$DEST/$name.pmtiles"
  entries+=("{\"name\":\"$name\",\"url\":\"data/$name.pmtiles\",\"bbox\":[$bbox],\"maxzoom\":$maxzoom}")

  if [ -n "${DRY_RUN:-}" ]; then
    echo "== $name  bbox=$bbox  maxzoom=$maxzoom"
    pmtiles extract "$SRC" "$out.dry" --bbox="$bbox" --maxzoom="$maxzoom" --dry-run 2>&1 | grep -iE 'total|size|bytes|tiles' | tail -4
    continue
  fi
  if [ -f "$out" ] && [ -z "${FORCE:-}" ]; then echo "== $name zaten var / already present (FORCE=1 ile yenile / to refresh)"; continue; fi

  echo ">> $name indiriliyor / downloading  bbox=$bbox  maxzoom=$maxzoom"
  df -h "$DEST" | tail -1
  if pmtiles extract "$SRC" "$out.part" --bbox="$bbox" --maxzoom="$maxzoom" --download-threads=4; then
    mv "$out.part" "$out"; echo "OK $name ($(du -h "$out" | cut -f1))"
  else
    rm -f "$out.part"; echo "!! $name indirilemedi / failed (tekrar çalıştır / re-run)"; failed=1
  fi
done < "$CONF"

[ -n "${DRY_RUN:-}" ] && exit 0

# Görüntüleyici bu listeyi okur; ilk satır taban harita / the viewer reads this; first line = base map
{ printf '{"build":"%s","layers":[' "${build%.pmtiles}"; (IFS=,; printf '%s' "${entries[*]}"); printf ']}\n'; } > "$DEST/index.json.tmp"
mv "$DEST/index.json.tmp" "$DEST/index.json"
echo ">> $DEST/index.json yazıldı / written"
exit $failed
