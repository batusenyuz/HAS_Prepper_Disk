#!/usr/bin/env bash
# OpenStreetMap'ten tüm işletmeleri çıkarıp haritaya katman olarak hazırlar.
# Extracts every business from OpenStreetMap and builds a map layer + offline search.
#
#   docker compose run --rm pois
#   POI_PBF_URL  bölge dosyası / region extract (varsayılan / default: Geofabrik Türkiye)
#   FORCE=1      bölge dosyasını yeniden indir / re-download the region extract
set -euo pipefail

URL="${POI_PBF_URL:-https://download.geofabrik.de/europe/turkey-latest.osm.pbf}"
DEST="${MAPS_DIR:-/data/maps}"
WORK="$DEST/pois-work"
OUT="$DEST/pois"
mkdir -p "$WORK"
PBF="$WORK/region.osm.pbf"

say(){ printf '\n>> %s\n' "$*"; }

if [ -f "$PBF" ] && [ -z "${FORCE:-}" ]; then
  say "Bölge dosyası var / region extract present ($(du -h "$PBF" | cut -f1)); FORCE=1 ile yenile / to refresh"
else
  say "OSM bölge dosyası indiriliyor / downloading $URL"
  curl -fL --retry 3 -C - -o "$PBF.part" "$URL"
  mv "$PBF.part" "$PBF"
fi

say "İşletmeler ayıklanıyor / filtering businesses (osmium)"
osmium tags-filter "$PBF" \
  nwr/shop nwr/amenity nwr/craft nwr/office nwr/healthcare nwr/emergency \
  nwr/tourism=hotel,motel,guest_house,hostel,camp_site,apartment,chalet,caravan_site \
  nwr/man_made=water_well,water_tap \
  -o "$WORK/filtered.osm.pbf" --overwrite
osmium export "$WORK/filtered.osm.pbf" -f geojsonseq --geometry-types=point,polygon \
  -a type,id --format-option print_record_separator=false \
  -o "$WORK/export.geojsonseq" --overwrite

say "Kategoriler ve arama dizini / categories and search index"
rm -rf "$OUT.new"; mkdir -p "$OUT.new"
python3 /opt/prepper/pois.py "$WORK/export.geojsonseq" "$WORK/points.geojsonseq" "$OUT.new"

say "Harita katmanı / map layer (tippecanoe)"
# z14'te her işletme vardır; daha düşük zoomlarda sadece önemli olanlar (pois.py minzoom).
# Every business is in z14 tiles; lower zooms only carry important ones (minzoom in pois.py).
tippecanoe -o "$OUT.new/pois.pmtiles" -l pois -z14 -Z10 -r1 -P \
  --no-feature-limit --no-tile-size-limit --force --quiet \
  -n "HAS_PrepperDisk işletmeler" -A '© OpenStreetMap' "$WORK/points.geojsonseq"

date -u +%Y-%m-%dT%H:%MZ > "$OUT.new/date.txt"
python3 - "$OUT.new/meta.json" "$PBF" <<'EOF'
import json, os, sys, time
p = sys.argv[1]; m = json.load(open(p))
m["date"] = open(os.path.join(os.path.dirname(p), "date.txt")).read().strip()
m["source"] = os.environ.get("POI_PBF_URL", "https://download.geofabrik.de/europe/turkey-latest.osm.pbf")
json.dump(m, open(p, "w"), ensure_ascii=False)
EOF
rm -rf "$OUT.old"; [ -d "$OUT" ] && mv "$OUT" "$OUT.old"; mv "$OUT.new" "$OUT"; rm -rf "$OUT.old"
rm -f "$WORK/filtered.osm.pbf" "$WORK/export.geojsonseq" "$WORK/points.geojsonseq"
say "Bitti / done: $OUT ($(du -sh "$OUT" | cut -f1))"
