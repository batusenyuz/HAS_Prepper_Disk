#!/usr/bin/env python3
"""osmium export (GeoJSONSeq) çıktısını işletme noktalarına çevirir.

Girdi: OSM işletmeleri (nokta + alan). Çıktı:
  - points.geojsonseq : tippecanoe için noktalar (kategori, Türkçe tür, iletişim, saat, adres)
  - search/<xx>.json  : internetsiz isim araması için kelime başı 2 harfe göre kovalar
  - meta.json         : sayılar

Converts osmium GeoJSONSeq output into business points for tippecanoe, an offline
name-search index split into 2-letter buckets, and meta.json with counts.
"""
import json, os, re, sys, unicodedata
from collections import Counter, defaultdict

SRC, OUT_POINTS, OUT_DIR = sys.argv[1:4]

# ----------------------------------------------------------------------------- kategoriler
# (anahtar, değer veya None=hepsi) -> kategori. İlk eşleşen kazanır.
CATS = {
    "acil":      "Acil Durum ve Toplanma",
    "saglik":    "Sağlık",
    "gida":      "Gıda ve Market",
    "yakit":     "Akaryakıt ve Gaz",
    "tamir":     "Hırdavat ve Tamir",
    "para":      "Banka, ATM ve PTT",
    "yeme":      "Yeme İçme",
    "konaklama": "Konaklama",
    "kamu":      "Kamu, Okul ve İbadet",
    "diger":     "Diğer İşletmeler",
}
RULES = [
    ("emergency", None, "acil"),
    ("amenity", {"police", "fire_station", "shelter", "drinking_water", "water_point", "toilets",
                 "emergency_service", "ranger_station"}, "acil"),
    ("man_made", {"water_well", "water_tap"}, "acil"),
    ("healthcare", None, "saglik"),
    ("amenity", {"pharmacy", "hospital", "clinic", "doctors", "dentist", "veterinary",
                 "nursing_home", "blood_bank"}, "saglik"),
    ("shop", {"medical_supply", "optician", "hearing_aids", "chemist", "herbalist"}, "saglik"),
    ("amenity", {"fuel", "charging_station"}, "yakit"),
    ("shop", {"gas", "fuel"}, "yakit"),
    ("shop", {"supermarket", "convenience", "bakery", "butcher", "greengrocer", "deli", "dairy",
              "beverages", "water", "frozen_food", "seafood", "spices", "nuts", "confectionery",
              "pastry", "cheese", "general", "food", "farm", "health_food", "tea", "coffee",
              "wholesale", "kiosk", "variety_store", "department_store"}, "gida"),
    ("amenity", {"marketplace"}, "gida"),
    ("craft", None, "tamir"),
    ("shop", {"hardware", "doityourself", "car_repair", "tyres", "car_parts", "electrical", "trade",
              "motorcycle", "motorcycle_repair", "bicycle", "mobile_phone", "electronics", "computer",
              "appliance", "locksmith", "paint", "building_materials", "plumbing", "tools", "glaziery",
              "energy", "lighting", "agrarian", "garden_centre", "repair", "car", "battery",
              "outdoor", "sports", "fishing", "hunting", "camping"}, "tamir"),
    ("amenity", {"bank", "atm", "bureau_de_change", "post_office", "money_transfer", "payment_centre"}, "para"),
    ("amenity", {"restaurant", "cafe", "fast_food", "food_court", "bar", "pub", "ice_cream", "biergarten"}, "yeme"),
    ("tourism", {"hotel", "motel", "guest_house", "hostel", "camp_site", "apartment", "chalet", "caravan_site"}, "konaklama"),
    ("amenity", {"townhall", "courthouse", "school", "university", "college", "kindergarten",
                 "place_of_worship", "library", "community_centre", "social_facility",
                 "social_centre", "public_building", "prison", "embassy"}, "kamu"),
    ("office", {"government"}, "kamu"),
    ("shop", None, "diger"),
    ("office", None, "diger"),
    ("amenity", None, "diger"),
    ("tourism", None, "diger"),
]
# İşletme sayılmayan / gürültü olan nesneler / not businesses (noise)
SKIP = {
    "amenity": {"bench", "waste_basket", "waste_disposal", "recycling", "parking", "parking_space",
                "parking_entrance", "bicycle_parking", "motorcycle_parking", "vending_machine",
                "clock", "grit_bin", "hunting_stand", "bbq", "post_box", "telephone", "fountain",
                "lounger", "photo_booth", "letter_box", "loading_dock", "smoking_area", "give_box",
                "table", "shower", "watering_place", "bicycle_rental", "taxi", "bus_station",
                "ferry_terminal", "car_wash", "car_sharing", "boat_rental", "car_rental",
                "kneipp_water_cure", "dressing_room", "picnic_table", "trolley_bay", "feeding_place",
                "animal_shelter"},
    "tourism": {"information", "viewpoint", "artwork", "attraction", "picnic_site", "yes"},
    "shop": {"vacant", "no", "disused"},
}
# Öncelik: düşük zoomda da gösterilecekler / shown from lower zooms
Z10 = {("amenity", "hospital"), ("amenity", "pharmacy"), ("amenity", "fuel"), ("amenity", "police"),
       ("amenity", "fire_station"), ("emergency", "assembly_point"), ("emergency", "ambulance_station"),
       ("healthcare", "hospital"), ("shop", "gas")}
Z12 = {"acil", "saglik", "yakit", "gida", "para"}

# ----------------------------------------------------------------------------- Türkçe türler
TR = {
    "assembly_point": "Afet toplanma alanı", "ambulance_station": "Ambulans istasyonu",
    "defibrillator": "Defibrilatör (AED)", "fire_hydrant": "Yangın musluğu", "siren": "Siren",
    "phone": "Acil telefon", "fire_extinguisher": "Yangın söndürücü", "life_ring": "Can simidi",
    "police": "Polis / Jandarma", "fire_station": "İtfaiye", "shelter": "Barınak",
    "drinking_water": "İçme suyu", "water_point": "Su noktası", "toilets": "Tuvalet",
    "water_well": "Su kuyusu", "water_tap": "Su musluğu / çeşme",
    "pharmacy": "Eczane", "hospital": "Hastane", "clinic": "Klinik / Sağlık merkezi",
    "doctors": "Doktor", "dentist": "Diş hekimi", "veterinary": "Veteriner",
    "nursing_home": "Huzurevi", "blood_bank": "Kan merkezi", "medical_supply": "Medikal",
    "optician": "Optik", "chemist": "Kozmetik / Parfümeri", "herbalist": "Aktar",
    "laboratory": "Laboratuvar", "physiotherapist": "Fizyoterapi", "centre": "Sağlık merkezi",
    "fuel": "Akaryakıt istasyonu", "charging_station": "Elektrikli araç şarj", "gas": "Tüp gaz",
    "supermarket": "Süpermarket", "convenience": "Bakkal / Market", "bakery": "Fırın",
    "butcher": "Kasap", "greengrocer": "Manav", "deli": "Şarküteri", "dairy": "Süt ürünleri",
    "beverages": "İçecek", "water": "Su bayii", "frozen_food": "Dondurulmuş gıda",
    "seafood": "Balıkçı", "spices": "Baharatçı", "nuts": "Kuruyemiş", "confectionery": "Şekerci",
    "pastry": "Pastane", "cheese": "Peynirci", "general": "Genel mağaza", "farm": "Çiftlik ürünleri",
    "tea": "Çay", "coffee": "Kahve", "wholesale": "Toptancı", "kiosk": "Büfe",
    "variety_store": "Tuhafiye / Ucuzluk", "department_store": "Büyük mağaza", "marketplace": "Pazar yeri",
    "hardware": "Hırdavat", "doityourself": "Yapı market", "car_repair": "Oto tamir",
    "tyres": "Lastikçi", "car_parts": "Oto yedek parça", "electrical": "Elektrik malzemesi",
    "trade": "Yapı malzemesi", "motorcycle": "Motosiklet", "motorcycle_repair": "Motosiklet tamiri",
    "bicycle": "Bisiklet", "mobile_phone": "Cep telefonu", "electronics": "Elektronik",
    "computer": "Bilgisayar", "appliance": "Beyaz eşya", "locksmith": "Çilingir",
    "paint": "Boya", "building_materials": "Yapı malzemesi", "plumbing": "Sıhhi tesisat malzemesi",
    "tools": "Alet edevat", "glaziery": "Camcı", "energy": "Enerji", "lighting": "Aydınlatma",
    "agrarian": "Zirai malzeme", "garden_centre": "Fidanlık", "repair": "Tamirci", "car": "Oto galeri",
    "battery": "Akü", "outdoor": "Kamp / Outdoor", "sports": "Spor", "fishing": "Balıkçılık malzemesi",
    "hunting": "Av malzemesi", "camping": "Kamp malzemesi",
    "electrician": "Elektrikçi", "plumber": "Tesisatçı", "carpenter": "Marangoz",
    "hvac": "Isıtma / klima", "metal_construction": "Demirci / Kaynakçı", "builder": "İnşaat ustası",
    "shoemaker": "Ayakkabı tamircisi", "tailor": "Terzi", "key_cutter": "Anahtarcı",
    "glazier": "Camcı", "painter": "Boyacı", "roofer": "Çatı ustası", "stonemason": "Taş ustası",
    "blacksmith": "Demirci", "electronics_repair": "Elektronik tamiri",
    "bank": "Banka", "atm": "ATM", "bureau_de_change": "Döviz bürosu", "post_office": "PTT",
    "money_transfer": "Para transferi", "payment_centre": "Ödeme noktası",
    "restaurant": "Restoran", "cafe": "Kafe", "fast_food": "Hızlı yemek", "food_court": "Yemek alanı",
    "bar": "Bar", "pub": "Bar", "ice_cream": "Dondurmacı",
    "hotel": "Otel", "motel": "Motel", "guest_house": "Pansiyon", "hostel": "Hostel",
    "camp_site": "Kamp alanı", "apartment": "Apart", "chalet": "Dağ evi", "caravan_site": "Karavan alanı",
    "townhall": "Belediye / Muhtarlık", "courthouse": "Adliye", "school": "Okul",
    "university": "Üniversite", "college": "Yüksekokul", "kindergarten": "Anaokulu",
    "place_of_worship": "İbadethane", "library": "Kütüphane", "community_centre": "Toplum merkezi",
    "social_facility": "Sosyal tesis", "government": "Kamu kurumu", "prison": "Cezaevi",
    "embassy": "Büyükelçilik",
    "clothes": "Giyim", "shoes": "Ayakkabı", "hairdresser": "Kuaför / Berber", "beauty": "Güzellik",
    "jewelry": "Kuyumcu", "furniture": "Mobilya", "florist": "Çiçekçi", "books": "Kitapçı",
    "stationery": "Kırtasiye", "gift": "Hediyelik", "toys": "Oyuncak", "pet": "Pet shop",
    "car_wash": "Oto yıkama", "dry_cleaning": "Kuru temizleme", "laundry": "Çamaşırhane",
    "travel_agency": "Seyahat acentesi", "estate_agent": "Emlakçı", "lawyer": "Avukat",
    "accountant": "Muhasebe", "insurance": "Sigorta", "company": "Şirket", "copyshop": "Fotokopi",
    "photo": "Fotoğrafçı", "tobacco": "Tütün", "alcohol": "Tekel", "cosmetics": "Kozmetik",
    "textiles": "Kumaş", "fabric": "Kumaş", "houseware": "Züccaciye", "mall": "AVM",
    "lottery": "Piyango bayi", "bag": "Çanta",
    "interior_decoration": "Dekorasyon", "carpet": "Halı", "kitchen": "Mutfak", "bathroom_furnishing": "Banyo",
    "music": "Müzik", "funeral_directors": "Cenaze hizmetleri",
    "driving_school": "Sürücü kursu", "language_school": "Dil kursu", "training": "Kurs",
    "theatre": "Tiyatro", "cinema": "Sinema", "nightclub": "Gece kulübü", "events_venue": "Düğün salonu",
}


def kind_of(tags):
    for key, vals, cat in RULES:
        v = tags.get(key)
        if v and v not in SKIP.get(key, ()) and (vals is None or v in vals):
            return key, v, cat
    return None


def point_of(geom):
    t, c = geom["type"], geom["coordinates"]
    if t == "Point":
        return c
    if t == "Polygon":
        ring = c[0]
    elif t == "MultiPolygon":
        ring = max((p[0] for p in c), key=len)
    elif t == "LineString":
        return c[len(c) // 2]
    else:
        return None
    pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    return [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)]


FOLD = str.maketrans("çğıöşüâîûÇĞİÖŞÜ", "cgiosuaiucgiosu")


def fold(s):
    s = s.replace("İ", "i").replace("I", "ı").lower().translate(FOLD)
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def words(s):
    return [w for w in re.split(r"[^0-9a-z]+", fold(s)) if len(w) >= 2]


def addr(tags):
    street = " ".join(x for x in (tags.get("addr:street"), tags.get("addr:housenumber")) if x)
    area = " / ".join(dict.fromkeys(x for x in (tags.get("addr:neighbourhood") or tags.get("addr:suburb"),
                                                 tags.get("addr:district"), tags.get("addr:city") or
                                                 tags.get("addr:province")) if x))
    return ", ".join(x for x in (street, area) if x)


def main():
    os.makedirs(os.path.join(OUT_DIR, "search"), exist_ok=True)
    buckets = defaultdict(list)
    counts = Counter()
    n = 0
    with open(SRC, encoding="utf-8") as src, open(OUT_POINTS, "w", encoding="utf-8") as out:
        for line in src:
            line = line.strip().lstrip("\x1e")
            if not line:
                continue
            f = json.loads(line)
            tags = f.get("properties") or {}
            k = kind_of(tags)
            if not k or not f.get("geometry"):
                continue
            key, val, cat = k
            pt = point_of(f["geometry"])
            if not pt:
                continue
            lon, lat = round(pt[0], 6), round(pt[1], 6)
            label = TR.get(val) or val.replace("_", " ").capitalize()
            name = tags.get("name:tr") or tags.get("name") or tags.get("brand") or ""
            osm = (tags.get("@type", "")[:1] + str(tags.get("@id", ""))) if tags.get("@id") else ""
            p = {"n": name, "k": label, "c": cat, "t": f"{key}={val}"}
            for dst, srcs in (("ph", ("phone", "contact:phone", "contact:mobile", "mobile")),
                              ("oh", ("opening_hours",)), ("w", ("website", "contact:website")),
                              ("br", ("brand", "operator"))):
                for s in srcs:
                    if tags.get(s):
                        p[dst] = tags[s][:120]
                        break
            a = addr(tags)
            if a:
                p["a"] = a[:160]
            if osm:
                p["id"] = osm
            mz = 10 if (key, val) in Z10 else 12 if cat in Z12 else 14
            out.write(json.dumps({"type": "Feature", "tippecanoe": {"minzoom": mz},
                                  "properties": p, "geometry": {"type": "Point", "coordinates": [lon, lat]}},
                                 ensure_ascii=False, separators=(",", ":")) + "\n")
            n += 1
            counts[cat] += 1
            rec = [name or label, round(lon, 5), round(lat, 5), cat, label]
            # Her kayıt bir kovaya bir kez girer / each record goes into a bucket once
            for b in {w[:2] for w in words(name) + words(label)}:
                buckets[b].append(rec)
    for b, rows in buckets.items():
        with open(os.path.join(OUT_DIR, "search", f"{b}.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))
    meta = {"count": n, "cats": [{"id": c, "name": CATS[c], "count": counts[c]} for c in CATS]}
    with open(os.path.join(OUT_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print(f"   {n} işletme / businesses; {len(buckets)} arama kovası / search buckets", flush=True)
    for c in CATS:
        print(f"   {CATS[c]:28} {counts[c]:>8}", flush=True)


if __name__ == "__main__":
    main()
