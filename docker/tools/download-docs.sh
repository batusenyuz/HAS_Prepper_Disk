#!/usr/bin/env bash
# config/docs.conf içindeki PDF belgeleri indirir ve ana sayfa için index.json yazar.
# Downloads the PDFs in config/docs.conf and writes index.json for the homepage.
#   FORCE=1  var olanları yeniden indir / re-download existing files
set -uo pipefail

CONF="${1:-/config/docs.conf}"
DEST="${DOCS_DIR:-/data/docs}"
mkdir -p "$DEST"
tmpd=$(mktemp -d); trap 'rm -rf "$tmpd"' EXIT

trim(){ local s="$1"; s="${s#"${s%%[![:space:]]*}"}"; printf '%s' "${s%"${s##*[![:space:]]}"}"; }
json(){ local s="$1"; s="${s//\\/\\\\}"; s="${s//\"/\\\"}"; printf '"%s"' "$s"; }

failed=0
entries=()
while IFS='|' read -r cat file title desc urls; do
  cat=$(trim "$cat"); case "$cat" in ''|\#*) continue;; esac
  file=$(trim "$file"); title=$(trim "$title"); desc=$(trim "$desc"); urls=$(trim "$urls")
  case "$file" in */*|.*|'') echo "!! geçersiz dosya adı / bad file name: $file"; failed=1; continue;; esac
  out="$DEST/$file"

  if [ -f "$out" ] && [ -z "${FORCE:-}" ]; then
    echo "== $file zaten var / already present"
  else
    echo ">> $file indiriliyor / downloading"
    rm -f "$tmpd"/*; i=0; ok=1
    for u in $urls; do
      i=$((i+1)); p=$(printf '%s/%03d.pdf' "$tmpd" "$i")
      curl -fsSL --retry 3 --retry-delay 5 -m 900 -o "$p" "$u" || { echo "!! indirilemedi / failed: $u"; ok=0; break; }
      head -c 5 "$p" | grep -q '%PDF-' || { echo "!! PDF değil / not a PDF: $u"; ok=0; break; }
    done
    if [ "$ok" = 1 ]; then
      if [ "$i" -gt 1 ]; then pdfunite "$tmpd"/*.pdf "$out.part" || ok=0
      else mv "$tmpd/001.pdf" "$out.part"; fi
    fi
    if [ "$ok" = 1 ]; then mv "$out.part" "$out"; echo "OK $file ($(du -h "$out" | cut -f1))"
    else rm -f "$out.part"; failed=1; fi
  fi

  if [ -f "$out" ]; then
    size=$(du -k "$out" | cut -f1)
    pages=$(pdfinfo "$out" 2>/dev/null | awk '/^Pages:/{print $2}')
    entries+=("{\"cat\":$(json "$cat"),\"file\":$(json "$file"),\"title\":$(json "$title"),\"desc\":$(json "$desc"),\"kb\":$size,\"pages\":${pages:-0}}")
  fi
done < "$CONF"

# MEGEP koleksiyonları (download-megep.py yazar) / MEGEP collections
if [ -f "$DEST/megep.jsonl" ]; then
  while IFS= read -r l; do [ -n "$l" ] && entries+=("$l"); done < "$DEST/megep.jsonl"
fi

{ printf '{"docs":['; (IFS=,; printf '%s' "${entries[*]}"); printf ']}\n'; } > "$DEST/index.json.tmp"
mv "$DEST/index.json.tmp" "$DEST/index.json"
echo ">> $DEST/index.json yazıldı / written (${#entries[@]} belge / docs)"
exit $failed
