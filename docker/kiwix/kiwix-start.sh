#!/bin/sh
# /data içindeki ZIM'lerden library.xml üretir ve kiwix-serve'ü /kiwix altında başlatır.
# Builds library.xml from the ZIMs in /data and serves them under /kiwix.
# --monitorLibrary sayesinde indirici library.xml'i güncellediğinde yeniden başlatma gerekmez.
set -eu
cd /data
LIB=/data/library.xml

if [ ! -f "$LIB" ]; then
  tmp="$LIB.tmp.$$"
  printf '<?xml version="1.0" encoding="UTF-8" ?>\n<library version="20110515"></library>\n' > "$tmp"
  for z in /data/content/*.zim /data/*.zim; do
    [ -f "$z" ] && kiwix-manage "$tmp" add "$z" >/dev/null && echo "+ $z"
  done
  mv "$tmp" "$LIB"
fi

exec /usr/local/bin/kiwix-serve --port=8080 --urlRootLocation=/kiwix \
  --library --monitorLibrary --threads=4 "$LIB"
