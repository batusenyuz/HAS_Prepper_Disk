#!/usr/bin/env python3
"""config/megep.conf içindeki MEB MEGEP modüllerini indirir, her koleksiyon için
bir index.html ve ana sayfa için DEST/megep.jsonl yazar.

Downloads the MEB MEGEP modules listed in config/megep.conf, writes an index.html
per collection and DEST/megep.jsonl for the homepage. Existing files are skipped
(FORCE=1 re-downloads). Module URLs are looked up from MEGEP's live module list.
"""
import html, http.cookiejar, json, os, re, subprocess, sys, unicodedata
import urllib.parse, urllib.request

BASE = "https://megep.meb.gov.tr/"
ENC = "iso-8859-9"
CONF = sys.argv[1] if len(sys.argv) > 1 else "/config/megep.conf"
DEST = os.environ.get("DOCS_DIR", "/data/docs")
FORCE = bool(os.environ.get("FORCE"))

cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def fetch(url, data=None, timeout=300):
    body = urllib.parse.urlencode(data, encoding=ENC).encode() if data else None
    with op.open(url, body, timeout=timeout) as r:
        return r.read()


def norm(s):
    s = unicodedata.normalize("NFC", s).replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"\s+", " ", s).strip()


def module_index():
    """MEGEP modül arama formu boş aramada tüm modülleri döndürür: {ad: pdf_url}."""
    page = fetch(BASE + "?page=moduller").decode(ENC, "replace")
    form = {m.group(1): html.unescape(m.group(2)) for m in re.finditer(
        r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', page)}
    # Bir alan/ders seçili gönderilince sunucu tüm modülleri doğru PDF yollarıyla döndürüyor;
    # boş aramada yollar eksik geliyor. / With a field selected the server returns every
    # module with correct PDF paths; an empty search returns broken paths.
    form.update({"ctl10$drpModulAlanListe": "16", "ctl10$hdnAlanId": "16",
                 "ctl10$drpDersListe": "351", "ctl10$hdnDersId": "351",
                 "ctl10$txtModulAd": "", "ctl10$txtModulKod": "", "ctl10$btnAra": "Ara"})
    res = fetch(BASE + "?page=moduller", form).decode(ENC, "replace")
    i = res.find('id="ctl10_grdModulListe"')
    table = res[i:res.find("</table>", i)]
    out = {}
    for row in re.findall(r'<tr class="tr[12]">(.*?)</tr>', table, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        link = re.search(r"href='([^']+\.pdf)'", row, re.I)
        if tds and link:
            name = html.unescape(re.sub(r"<[^>]+>|\s+", " ", tds[0])).strip()
            path = html.unescape(link.group(1))
            if "/moduller_pdf/" not in path:  # bozuk yol / broken path
                path = path.replace("mte_program_modul/", "mte_program_modul/moduller_pdf/", 1)
            out[norm(name)] = (name, urllib.parse.urljoin(BASE, urllib.parse.quote(path)))
    return out


def parse_conf(path):
    cols, cur = [], None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            folder, cat, title, desc = [p.strip() for p in line[1:].split("|", 3)]
            if not re.fullmatch(r"[a-z0-9-]+", folder):
                sys.exit(f"!! geçersiz klasör adı / bad folder name: {folder}")
            cur = {"folder": folder, "cat": cat, "title": title, "desc": desc, "mods": []}
            cols.append(cur)
        elif cur:
            cur["mods"].append(line)
    return cols


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|]+', "-", s).strip() + ".pdf"


def pages(path):
    try:
        info = subprocess.run(["pdfinfo", path], capture_output=True, text=True, timeout=60).stdout
        m = re.search(r"^Pages:\s+(\d+)", info, re.M)
        return int(m.group(1)) if m else 0
    except Exception:
        return 0


def write_index(col, files):
    e = html.escape
    rows = "\n".join(
        f'<tr><td><a href="{urllib.parse.quote(f)}">{e(n)}</a></td><td>{p}</td><td>{kb // 1024 or 1} MB</td></tr>'
        for n, f, kb, p in files)
    doc = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(col['title'])}</title>
<style>body{{margin:0;background:#E5E5E5;font:12px Verdana,Tahoma,Arial,sans-serif}}.w{{max-width:860px;margin:0 auto;padding:12px}}
.b{{background:#fff;border:1px solid #98AAB1;padding:12px}}h1{{font-size:16px;margin:0 0 6px}}a{{color:#006699;text-decoration:none}}a:hover{{color:#DD6900}}
table{{width:100%;border-collapse:collapse;margin-top:10px}}th{{background:#006699;color:#FFA34F;text-align:left;padding:6px}}
td{{padding:6px;border-top:1px solid #D1D7DC}}td+td,th+th{{text-align:right;white-space:nowrap}}</style></head>
<body><div class="w"><div class="b"><a href="/home/">&larr; Ana Sayfa</a>
<h1>{e(col['title'])}</h1><div>{e(col['desc'])}</div>
<table><tr><th>Modül</th><th>Sayfa</th><th>Boyut</th></tr>
{rows}
</table><p style="color:#555">Kaynak: T.C. Millî Eğitim Bakanlığı, MEGEP modülleri (megep.meb.gov.tr).</p></div></div></body></html>"""
    with open(os.path.join(DEST, col["folder"], "index.html"), "w", encoding="utf-8") as f:
        f.write(doc)


def main():
    cols = parse_conf(CONF)
    print(">> MEGEP modül listesi alınıyor / fetching module list", flush=True)
    try:
        idx = module_index()
    except Exception as ex:
        idx = {}
        print(f"!! MEGEP listesi alınamadı / module list failed: {ex}", flush=True)
    print(f"   {len(idx)} modül / modules", flush=True)
    failed, entries = 0, []
    for col in cols:
        d = os.path.join(DEST, col["folder"])
        os.makedirs(d, exist_ok=True)
        files = []
        for mod in col["mods"]:
            fn = safe_name(mod)
            out = os.path.join(d, fn)
            if not os.path.exists(out) or FORCE:
                hit = idx.get(norm(mod))
                if not hit:
                    print(f"!! {mod}: MEGEP listesinde yok / not in MEGEP list", flush=True)
                    failed = 1
                    continue
                try:
                    # Diğer indirmeler gibi curl ile / download with curl like the other steps
                    subprocess.run(["curl", "-fsSL", "--retry", "3", "--retry-delay", "5", "-m", "900",
                                    "-o", out + ".part", hit[1]], check=True)
                    with open(out + ".part", "rb") as f:
                        if not f.read(5).startswith(b"%PDF-"):
                            raise ValueError("PDF değil / not a PDF")
                    os.replace(out + ".part", out)
                    print(f"OK {col['folder']}/{fn} ({os.path.getsize(out) // 1024} KB)", flush=True)
                except Exception as ex:
                    if os.path.exists(out + ".part"):
                        os.remove(out + ".part")
                    print(f"!! {mod}: {ex}", flush=True)
                    failed = 1
                    continue
            files.append((mod, fn, os.path.getsize(out) // 1024, pages(out)))
        if files:
            write_index(col, files)
            entries.append({"cat": col["cat"], "title": col["title"], "desc": col["desc"],
                            "url": f"/belgeler/{col['folder']}/", "count": len(files),
                            "kb": sum(f[2] for f in files), "pages": sum(f[3] for f in files)})
        print(f"== {col['folder']}: {len(files)}/{len(col['mods'])} modül", flush=True)
    with open(os.path.join(DEST, "megep.jsonl.tmp"), "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(os.path.join(DEST, "megep.jsonl.tmp"), os.path.join(DEST, "megep.jsonl"))
    sys.exit(failed)


if __name__ == "__main__":
    main()
