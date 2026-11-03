# HAS_PrepperDisk — Docker kurulumu

**[Türkçe](#türkçe) · [English](#english)**

---

## Türkçe

Raspberry Pi'ye Internet-in-a-Box kurmak yerine aynı çevrimdışı arşivi **Docker** ile, herhangi bir Linux makinede (Pi 4/5 arm64 ya da x86_64) çalıştırır. İşletim sistemine dokunmaz: hostname değişmez, ağ ayarları değişmez.

| Servis | Adres | Ne yapar |
|---|---|---|
| `web` (nginx) | `http://<sunucu>/home` | HAS_PrepperDisk ana sayfası, harita görüntüleyici, proxy |
| `kiwix` | `/kiwix/` | Wikipedia ve diğer ZIM dosyaları (resmi `kiwix-serve` imajı) |
| `kolibri` | `/kolibri/` | Çevrimdışı dersler |
| haritalar | `/maps/` | Protomaps (OpenStreetMap) vektör haritaları, MapLibre ile |
| `downloader` | — | ZIM ve harita indirici (tek seferlik, `docker compose run`) |

Docker kurulumunda **olmayanlar:** Wi-Fi hotspot ve captive portal (bunlar işletim sisteminin ağ ayarlarıdır) ve IIAB yönetim paneli. Hotspot istiyorsan host üzerinde NetworkManager ile kurabilirsin (aşağıya bak). İçerik yönetimi komut satırından yapılır, `/admin` sayfası komutları listeler.

### Kurulum

```bash
git clone https://github.com/batusenyuz/HAS_Prepper_Disk.git
cd HAS_Prepper_Disk
cp .env.example .env        # DATA_DIR'i büyük diskine yönlendir
mkdir -p "$(grep ^DATA_DIR .env | cut -d= -f2)"/{zims/content,maps,kolibri}
docker compose up -d --build
```

`DATA_DIR` klasörünün sahibi `.env` içindeki `PUID`/`PGID` kullanıcısı olmalı (`id -u` ile öğren). Klasör izni en az `755` olmalı.

### İçerik indirme

```bash
# Kütüphane: config/content.conf (varsayılan ~150 GB)
docker compose run --rm downloader zims

# Türkçe PDF belgeler (AFAD, Sağlık Bakanlığı, Hesperian...): config/docs.conf
docker compose run --rm downloader docs

# Haritalar: config/maps.conf. Önce boyutlara bak:
docker compose run --rm downloader maps-size
docker compose run --rm downloader maps
```

- İndirmeler yarıda kalırsa aynı komutu tekrar çalıştır. ZIM'ler kaldığı yerden devam eder, haritalar baştan iner.
- Türkçe belgeler `/belgeler/` altında sunulur ve ana sayfada ilgili bölümün başında **TR** olarak listelenir. Yeni belge eklemek için `config/docs.conf` dosyasına bir satır ekle.
- Yeni ZIM'ler birkaç saniye içinde Kiwix'te görünür, yeniden başlatma gerekmez (`--monitorLibrary`).
- Haritalar her hafta yenilenen Protomaps dünya derlemesinden kesilir. Sadece gereken parçalar indirilir. Belirli bir derlemeyi sabitlemek için `.env` içinde `PROTOMAPS_BUILD=20261102` kullan. Haritaları yenilemek için: `docker compose run --rm -e FORCE=1 downloader maps`.
- Uzun indirmeleri SSH kopsa da sürsün diye `tmux` / `screen` içinde ya da `nohup` ile çalıştır.

### Güncelleme

```bash
git pull
docker compose pull && docker compose up -d --build
```

### İsteğe bağlı: Pi üzerinde hotspot

Docker kurulumu ağ ayarlarına dokunmaz. Pi'nin kendi Wi-Fi'ı ile yayın yapmak istersen (NetworkManager'lı Raspberry Pi OS):

```bash
sudo nmcli device wifi hotspot ifname wlan0 con-name prepper-ap ssid HAS_PrepperDisk password "en-az-8-karakter"
sudo nmcli connection modify prepper-ap connection.autoconnect yes
```

Hotspot'a bağlanan cihazlar ana sayfayı `http://10.42.0.1/home` adresinden açar.

### Sorun giderme

- **`permission denied` / ZIM yazılamıyor:** `DATA_DIR` sahibi `PUID:PGID` değil. `sudo chown -R 1000:1000 <DATA_DIR>` çalıştır.
- **Port 80 dolu:** `.env` içinde `HTTP_PORT=8080` yap.
- **Kütüphane boş görünüyor:** `docker compose logs kiwix` çıktısına bak. `library.xml`'i silip `docker compose restart kiwix` ile yeniden üretebilirsin.
- **Harita sayfası "Henüz harita indirilmedi" diyor:** `docker compose run --rm downloader maps` çalıştır. `DATA_DIR/maps/index.json` oluşmalı.
- **Kitap koleksiyonları sürekli yükleniyor:** iPhone Safari'nin gizli sekmesinde açma (bkz. README).

---

## English

Runs the same offline archive with **Docker** on any Linux host (Pi 4/5 arm64 or x86_64) instead of installing Internet-in-a-Box on the OS. The hostname and network settings are left alone.

Services: `web` (nginx, homepage, map viewer, reverse proxy), `kiwix` (official `kiwix-serve` image under `/kiwix/`), `kolibri` (`/kolibri/`), offline vector maps (Protomaps + MapLibre under `/maps/`), and a one-shot `downloader`. Not included: Wi-Fi hotspot, captive portal and the IIAB admin console.

```bash
cp .env.example .env                       # point DATA_DIR at a big disk
docker compose up -d --build               # open http://<host>/home
docker compose run --rm downloader zims    # ZIMs from config/content.conf
docker compose run --rm downloader docs    # Turkish PDFs from config/docs.conf
docker compose run --rm downloader maps-size
docker compose run --rm downloader maps    # regions from config/maps.conf
```

`DATA_DIR` must be owned by `PUID:PGID` from `.env`. Re-run a download command to resume it. New ZIMs appear in Kiwix within seconds.
