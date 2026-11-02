#!/usr/bin/env bash
# config/content.conf içindeki ZIM dosyalarının en yeni sürümünü indirir ve Kiwix'e ekler.
# Downloads the newest version of each ZIM in config/content.conf and adds it to Kiwix.
# Yarıda kalırsa tekrar çalıştır, kaldığı yerden devam eder. / Re-run to resume.
#
# Kullanım / usage:  sudo ./scripts/download-content.sh [config-dosyası]
# Docker:            docker compose run --rm downloader zims
#   (PREPPER_DOCKER=1 iken root gerekmez, ZIM_ROOT altına yazar ve library.xml'i kiwix-manage ile kurar)
set -uo pipefail

if [ -n "${PREPPER_DOCKER:-}" ]; then
  ZIM_ROOT="${ZIM_ROOT:-/data/zims}"
else
  [ "$EUID" -eq 0 ] || { echo "sudo ile çalıştır / run with sudo" >&2; exit 1; }
  ZIM_ROOT=/library/zims
  mountpoint -q /library || echo "Uyarı / warning: /library ayrı bir disk değil / is not a separate disk (SD kart dolabilir / SD card may fill up)"
fi
CONF="${1:-$(cd "$(dirname "$0")/.." && pwd)/config/content.conf}"
DEST="$ZIM_ROOT/content"
BASE=https://download.kiwix.org/zim

mkdir -p "$DEST"

failed=0
while read -r folder prefix _; do
  case "$folder" in ''|\#*) continue;; esac

  latest=$(curl -fsSL "$BASE/$folder/" | grep -oE "${prefix}_[0-9]{4}-[0-9]{2}[a-z]?\.zim" | sort -u | tail -1)
  if [ -z "$latest" ]; then echo "!! $prefix bulunamadı / not found in $BASE/$folder/"; failed=1; continue; fi

  if [ -f "$DEST/$latest" ]; then echo "== $latest zaten var / already present"; continue; fi

  echo ">> $latest indiriliyor / downloading"
  df -h "$DEST" | tail -1
  if wget -c --progress=dot:giga -O "$DEST/$latest.part" "$BASE/$folder/$latest" < /dev/null; then
    mv "$DEST/$latest.part" "$DEST/$latest"
    echo "OK $latest tamamlandı / done"
    # Eski sürümleri sil / remove older versions of the same ZIM
    for old in "$DEST/${prefix}"_*.zim; do
      [ "$old" != "$DEST/$latest" ] && [ -f "$old" ] && { echo "-- eski sürüm siliniyor / removing $old"; rm -f "$old"; }
    done
  else
    echo "!! $latest indirilemedi / download failed (tekrar çalıştır / re-run to resume)"; failed=1
  fi
done < "$CONF"

echo ">> Kiwix kütüphanesi güncelleniyor / rebuilding Kiwix library"
if command -v iiab-make-kiwix-lib >/dev/null; then
  iiab-make-kiwix-lib
elif command -v kiwix-manage >/dev/null; then
  # Docker: kiwix-serve --monitorLibrary bu dosyayı izler / kiwix-serve watches this file
  tmp="$ZIM_ROOT/library.xml.tmp.$$"
  printf '<?xml version="1.0" encoding="UTF-8" ?>\n<library version="20110515"></library>\n' > "$tmp"
  for z in "$DEST"/*.zim; do
    [ -f "$z" ] && { kiwix-manage "$tmp" add "$z" >/dev/null && echo "+ ${z##*/}" || failed=1; }
  done
  mv "$tmp" "$ZIM_ROOT/library.xml"
else
  echo "!! iiab-make-kiwix-lib yok / not found. Internet-in-a-Box kurulu mu? / is Internet-in-a-Box installed?"; failed=1
fi

exit $failed
