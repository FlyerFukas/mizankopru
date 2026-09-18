# -*- coding: utf-8 -*-
# MizanKöprü — çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ — [1] TOPLA: çok formatlı okuma ve normalizasyon.

GÖREV
  veri/girdi/ altındaki dağınık ERP çıktılarını tek şemaya indirir:
  farklı dosya biçimi (xlsx tek sekme / xlsx çok sekme / csv), farklı kolon adı
  (Borç / Soll / Debit), farklı sayı biçimi (1.234,56 / 1,234.56), farklı tarih
  biçimi ve dönemin üç ayrı yerden gelmesi (dosya adı / sekme adı / kolon).

EN TEHLİKELİ HATA
  Sayı biçimini yanlış okumak. "1.234" Türkçe biçimde bin iki yüz otuz dört,
  İngilizce biçimde bir virgül iki üç dört. Bu hatayı yapan boru hattı çöker
  değil — sessizce 1000 kat yanlış rakam üretir. Bu yüzden sayı ayrıştırıcı
  önce şirketin yapılandırılmış biçimini uygular, sonuç belirsizse
  sezgisel çözümler ve HER BELİRSİZ DURUMU raporlar.

ÇALIŞTIRMA
  py src/topla.py
ÇIKTI
  veri/ara/{mizan,yevmiye,butce,satis,grup_ici}.csv
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gunluk import Gunluk, dosya_parmak_izi, para, tablo_yaz      # noqa: E402
from sema import (ARA_DIZIN, VERI_DIZIN, BUTCE_KOLONLARI,          # noqa: E402
                  GRUP_ICI_KOLONLARI, MIZAN_KOLONLARI,
                  SATIS_KOLONLARI, YEVMIYE_KOLONLARI, yukle)

GIRDI = VERI_DIZIN / "girdi"

# Dosya adından veri tipini tanımak için anahtar kelimeler.
# Yeni bir ERP'nin dosya adlandırması buraya eklenir.
DOSYA_DESENLERI = {
    "mizan":    ["mizan", "saldenliste", "salden", "trial_balance", "trialbalance"],
    "yevmiye":  ["yevmiye", "buchungsjournal", "journal", "nominal_activity"],
    "butce":    ["butce", "bütçe", "budget", "plan_"],
    "satis":    ["satis_detay", "satış", "sales", "umsatz", "satis"],
    "grup_ici": ["grup_ici", "intercompany", "mutabakat", "verbundene"],
}

TARIH_DENEMELERI = ["%d.%m.%Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y",
                    "%d.%m.%y", "%Y/%m/%d", "%d-%m-%Y"]

DONEM_DESENI = re.compile(r"(20\d{2})[-_/.]?(0[1-9]|1[0-2])")


# ======================================================================
# SAYI VE TARİH AYRIŞTIRMA
# ======================================================================

class SayiAyristirici:
    """Metin hâlindeki tutarları güvenle sayıya çevirir.

    Şirketin yapılandırılmış biçimi önceliklidir. Yapılandırma bir sonuç
    vermiyorsa sezgisel çalışır ve belirsiz her durumu sayar — sayaç
    sıfır değilse rapora düşer ve insanın bakması gerekir."""

    def __init__(self, ondalik: str = ",", binlik: str = "."):
        self.ondalik = ondalik
        self.binlik = binlik
        self.belirsiz = 0
        self.basarisiz = 0
        self.ornekler: list[str] = []

    def __call__(self, deger) -> float:
        if deger is None:
            return 0.0
        if isinstance(deger, (int, float)):
            return 0.0 if pd.isna(deger) else float(deger)

        metin = str(deger).strip()
        if not metin or metin.lower() in ("nan", "none", "-", ""):
            return 0.0

        eksi = metin.startswith("-") or (metin.startswith("(") and metin.endswith(")"))
        metin = metin.strip("()-+ ").replace("\xa0", "").replace(" ", "")
        # Para birimi simgeleri ve harfler
        metin = re.sub(r"[^\d.,]", "", metin)
        if not metin:
            return 0.0

        nokta, virgul = metin.rfind("."), metin.rfind(",")

        if nokta >= 0 and virgul >= 0:
            # İkisi de var: sonuncusu ondalık ayracıdır. Biçim ne derse desin,
            # bu tespit her zaman doğrudur.
            ondalik = "." if nokta > virgul else ","
            binlik = "," if ondalik == "." else "."
            sayi = metin.replace(binlik, "").replace(ondalik, ".")
        elif nokta >= 0 or virgul >= 0:
            ayrac = "." if nokta >= 0 else ","
            kuyruk = len(metin) - metin.rfind(ayrac) - 1
            if ayrac == self.ondalik:
                sayi = metin.replace(self.binlik, "").replace(self.ondalik, ".")
            elif ayrac == self.binlik:
                sayi = metin.replace(self.binlik, "")
            elif kuyruk == 3:
                # Yapılandırma dışı bir ayraç, tam 3 basamak: binlik varsayıyoruz.
                # Gerçekten ondalıksa 1000 kat hata olur — bu yüzden sayılıyor.
                self.belirsiz += 1
                if len(self.ornekler) < 5:
                    self.ornekler.append(str(deger))
                sayi = metin.replace(ayrac, "")
            else:
                sayi = metin.replace(ayrac, ".")
        else:
            sayi = metin

        try:
            d = float(sayi)
        except ValueError:
            self.basarisiz += 1
            if len(self.ornekler) < 5:
                self.ornekler.append(str(deger))
            return 0.0
        return -d if eksi else d


def kod_metni(deger) -> str:
    """Hesap kodu / ürün kodu gibi ANAHTAR alanları metne çevirir.

    Excel'de "100" yazan bir hücre pandas'a float olarak gelir ve düz str()
    onu "100.0" yapar. Eşleme tablosunda "100" aradığımız için bu, hesabın
    sessizce eşleşmemesine yol açar — tablo yine denk görünür, kalem kaybolur.
    Hesap planındaki "770.01" gibi gerçek ondalıklı kodlar korunmalı, o yüzden
    yalnızca tam sayı olan float'ların kuyruğu atılır."""
    if deger is None:
        return ""
    if isinstance(deger, float):
        if pd.isna(deger):
            return ""
        if deger.is_integer():
            return str(int(deger))
        return repr(deger).rstrip("0").rstrip(".")
    if isinstance(deger, int):
        return str(deger)
    metin = str(deger).strip()
    if metin.lower() in ("nan", "none"):
        return ""
    # "100.0" biçiminde metne dönmüş tam sayılar
    if re.fullmatch(r"-?\d+\.0+", metin):
        return metin.split(".")[0]
    return metin


def tarih_ayristir(deger, tercih: str | None = None):
    """Tarihi çözer. Şirketin bildirdiği biçim önce denenir."""
    if deger is None or (isinstance(deger, float) and pd.isna(deger)):
        return None
    if isinstance(deger, datetime):
        return deger.date()
    if hasattr(deger, "year") and hasattr(deger, "month"):
        return deger
    metin = str(deger).strip()
    if not metin:
        return None
    sira = ([tercih] if tercih else []) + [b for b in TARIH_DENEMELERI if b != tercih]
    for bicim in sira:
        try:
            return datetime.strptime(metin[:19].split(" ")[0], bicim).date()
        except (ValueError, TypeError):
            continue
    try:
        return pd.to_datetime(metin, dayfirst=True).date()
    except Exception:
        return None


def donem_normalize(deger) -> str | None:
    """Herhangi bir kaynaktan gelen dönem bilgisini YYYY-MM'e indirger."""
    if deger is None:
        return None
    metin = str(deger).strip()
    e = DONEM_DESENI.search(metin)
    if e:
        return f"{e.group(1)}-{e.group(2)}"
    t = tarih_ayristir(metin)
    return f"{t.year}-{t.month:02d}" if t else None


# ======================================================================
# KOLON EŞLEŞTİRME
# ======================================================================

def kolon_bul(df: pd.DataFrame, adaylar: list[str]) -> str | None:
    """Girdi kolonlarını büyük/küçük harf ve boşluk duyarsız eşleştirir."""
    normal = {str(k).strip().lower().replace("  ", " "): k for k in df.columns}
    for aday in adaylar:
        a = aday.strip().lower()
        if a in normal:
            return normal[a]
    # Kısmi eşleşme — son çare
    for aday in adaylar:
        a = aday.strip().lower()
        for norm, asil in normal.items():
            if a in norm or norm in a:
                return asil
    return None


def kolonlari_esle(df: pd.DataFrame, harita: dict, g: Gunluk,
                   kaynak: str) -> tuple[dict, list[str]]:
    """İç alan adı → girdi kolon adı sözlüğü ve bulunamayanların listesi."""
    bulunan, eksik = {}, []
    for ic_ad, adaylar in harita.items():
        k = kolon_bul(df, adaylar)
        if k is None:
            eksik.append(ic_ad)
        else:
            bulunan[ic_ad] = k
    return bulunan, eksik


# ======================================================================
# DOSYA KEŞFİ
# ======================================================================

def dosya_tipi(ad: str) -> str | None:
    kucuk = ad.lower()
    # Uzun desenler önce denenir ki "satis_detay" > "satis" olsun
    for tip, desenler in DOSYA_DESENLERI.items():
        for d in sorted(desenler, key=len, reverse=True):
            if d in kucuk:
                return tip
    return None


def sirket_bul(ad: str, sirket_kodlari: list[str]) -> str | None:
    kucuk = ad.lower()
    for kod in sirket_kodlari:
        if kod.lower() in kucuk:
            return kod
    return None


def dosyalari_kesfet(y, g: Gunluk) -> dict[str, list[tuple[Path, str]]]:
    kodlar = list(y.sirketler)
    bulunan = defaultdict(list)
    taninmayan = []
    for yol in sorted(GIRDI.iterdir()):
        if yol.name.startswith(".") or yol.is_dir():
            continue
        if yol.suffix.lower() not in (".xlsx", ".xls", ".csv"):
            taninmayan.append(f"{yol.name} (desteklenmeyen uzantı)")
            continue
        tip, sirket = dosya_tipi(yol.name), sirket_bul(yol.name, kodlar)
        if tip is None:
            taninmayan.append(f"{yol.name} (veri tipi tanınmadı)")
            continue
        if sirket is None:
            taninmayan.append(f"{yol.name} (şirket kodu tanınmadı)")
            continue
        bulunan[tip].append((yol, sirket))
        g.iz("dosya_kesfedildi", dosya=yol.name, tip=tip, sirket=sirket,
             boyut=yol.stat().st_size, parmak=dosya_parmak_izi(yol))
    for t in taninmayan:
        g.uyari(f"Atlandı: {t}")
    return bulunan


def sayfalari_oku(yol: Path) -> list[tuple[str, pd.DataFrame]]:
    """Dosyayı (sekme adı, DataFrame) çiftleri olarak açar.
    CSV tek parça, çok sekmeli Excel her sekme ayrı."""
    if yol.suffix.lower() == ".csv":
        for kodlama in ("utf-8-sig", "utf-8", "cp1254", "latin-1"):
            try:
                return [("", pd.read_csv(yol, dtype=object, encoding=kodlama))]
            except (UnicodeDecodeError, UnicodeError):
                continue
        return [("", pd.read_csv(yol, dtype=object, encoding="utf-8",
                                 encoding_errors="replace"))]
    kitap = pd.read_excel(yol, sheet_name=None, dtype=object)
    return list(kitap.items())


# ======================================================================
# OKUYUCULAR
# ======================================================================

def oku_mizan(y, dosyalar, g: Gunluk) -> pd.DataFrame:
    satirlar = []
    for yol, sirket in dosyalar:
        s = y.sirketler[sirket]
        harita = y.kolon_eslesme["mizan"].get(s.hesap_plani) or \
            y.kolon_eslesme["mizan"].get("*")
        ay = SayiAyristirici(s.bicim.get("ondalik_ayrac", ","),
                             s.bicim.get("binlik_ayrac", "."))
        dosya_donemi = donem_normalize(yol.stem)

        for sekme, df in sayfalari_oku(yol):
            if df.empty:
                continue
            bulunan, eksik = kolonlari_esle(df, harita, g, yol.name)
            if eksik:
                g.uyari(f"{yol.name}[{sekme}]: eksik kolon {eksik} — atlandı")
                continue

            # Dönem üç yerden gelebilir: sekme adı, dosya adı, kolon
            donem_kolonu = kolon_bul(df, ["Dönem", "Period", "Periode", "Ay", "Donem"])
            sekme_donemi = donem_normalize(sekme)

            for _, satir in df.iterrows():
                kod = kod_metni(satir[bulunan["yerel_hesap_kod"]])
                if not kod:
                    continue
                donem = (donem_normalize(satir[donem_kolonu]) if donem_kolonu
                         else None) or sekme_donemi or dosya_donemi
                if donem is None:
                    continue
                borc = ay(satir[bulunan["borc"]])
                alacak = ay(satir[bulunan["alacak"]])
                satirlar.append({
                    "sirket_kod": sirket, "donem": donem,
                    "yerel_hesap_kod": kod,
                    "yerel_hesap_ad": str(satir[bulunan["yerel_hesap_ad"]]).strip(),
                    "borc": borc, "alacak": alacak, "bakiye": borc - alacak,
                    "para_birimi": s.fonksiyonel_para_birimi,
                    "kaynak_dosya": yol.name,
                })
        _ayristirici_raporu(ay, yol.name, g)
    return pd.DataFrame(satirlar, columns=MIZAN_KOLONLARI)


def oku_yevmiye(y, dosyalar, g: Gunluk) -> pd.DataFrame:
    satirlar = []
    for yol, sirket in dosyalar:
        s = y.sirketler[sirket]
        harita = y.kolon_eslesme["yevmiye"].get(s.hesap_plani) or \
            y.kolon_eslesme["yevmiye"].get("*")
        ay = SayiAyristirici(s.bicim.get("ondalik_ayrac", ","),
                             s.bicim.get("binlik_ayrac", "."))
        tb = s.bicim.get("tarih_bicimi")

        for sekme, df in sayfalari_oku(yol):
            if df.empty:
                continue
            bulunan, eksik = kolonlari_esle(df, harita, g, yol.name)
            kritik = [a for a in ("fis_no", "yerel_hesap_kod", "borc", "alacak") if a in eksik]
            if kritik:
                g.uyari(f"{yol.name}[{sekme}]: kritik kolon eksik {kritik} — atlandı")
                continue
            if eksik:
                g.uyari(f"{yol.name}[{sekme}]: isteğe bağlı kolon eksik {eksik}")

            for _, satir in df.iterrows():
                fis_t = tarih_ayristir(satir.get(bulunan.get("fis_tarihi")), tb)
                if fis_t is None:
                    continue
                borc = ay(satir[bulunan["borc"]])
                alacak = ay(satir[bulunan["alacak"]])
                satirlar.append({
                    "sirket_kod": sirket,
                    "donem": f"{fis_t.year}-{fis_t.month:02d}",
                    "fis_no": kod_metni(satir[bulunan["fis_no"]]),
                    "fis_tarihi": fis_t,
                    "belge_tarihi": tarih_ayristir(
                        satir.get(bulunan.get("belge_tarihi")), tb) or fis_t,
                    "yerel_hesap_kod": kod_metni(satir[bulunan["yerel_hesap_kod"]]),
                    "borc": borc, "alacak": alacak,
                    "aciklama": str(satir.get(bulunan.get("aciklama"), "")).strip(),
                    "kullanici": str(satir.get(bulunan.get("kullanici"), "")).strip(),
                    "kayit_zamani": satir.get(bulunan.get("kayit_zamani")),
                    "masraf_merkezi": str(satir.get(bulunan.get("masraf_merkezi"), "")).strip(),
                    "para_birimi": s.fonksiyonel_para_birimi,
                    "kaynak_dosya": yol.name,
                })
        _ayristirici_raporu(ay, yol.name, g)
    return pd.DataFrame(satirlar, columns=YEVMIYE_KOLONLARI)


def oku_butce(y, dosyalar, g: Gunluk) -> pd.DataFrame:
    satirlar = []
    for yol, sirket in dosyalar:
        s = y.sirketler[sirket]
        harita = y.kolon_eslesme["butce"]["*"]
        ay = SayiAyristirici(s.bicim.get("ondalik_ayrac", ","),
                             s.bicim.get("binlik_ayrac", "."))
        for sekme, df in sayfalari_oku(yol):
            if df.empty:
                continue
            bulunan, eksik = kolonlari_esle(df, harita, g, yol.name)
            if [a for a in ("yerel_hesap_kod", "tutar", "donem") if a in eksik]:
                g.uyari(f"{yol.name}[{sekme}]: bütçe kolonları eksik {eksik} — atlandı")
                continue
            for _, satir in df.iterrows():
                donem = donem_normalize(satir[bulunan["donem"]])
                if donem is None:
                    continue
                satirlar.append({
                    "sirket_kod": sirket, "donem": donem,
                    "yerel_hesap_kod": kod_metni(satir[bulunan["yerel_hesap_kod"]]),
                    "tutar": ay(satir[bulunan["tutar"]]),
                    "masraf_merkezi": str(satir.get(bulunan.get("masraf_merkezi"), "")).strip(),
                    "para_birimi": s.fonksiyonel_para_birimi,
                    "kaynak_dosya": yol.name,
                })
        _ayristirici_raporu(ay, yol.name, g)
    return pd.DataFrame(satirlar, columns=BUTCE_KOLONLARI)


def oku_satis(y, dosyalar, g: Gunluk) -> pd.DataFrame:
    satirlar = []
    for yol, sirket in dosyalar:
        s = y.sirketler[sirket]
        harita = y.kolon_eslesme["satis"]["*"]
        ay = SayiAyristirici(s.bicim.get("ondalik_ayrac", ","),
                             s.bicim.get("binlik_ayrac", "."))
        for sekme, df in sayfalari_oku(yol):
            if df.empty:
                continue
            bulunan, eksik = kolonlari_esle(df, harita, g, yol.name)
            if [a for a in ("urun_kod", "miktar", "tutar", "donem") if a in eksik]:
                g.uyari(f"{yol.name}[{sekme}]: satış kolonları eksik {eksik} — atlandı")
                continue
            # Sekme adı senaryoyu belirler: Fiili / Butce
            senaryo = "butce" if sekme.strip().lower().startswith(("but", "büt", "bud", "plan")) \
                else "fiili"
            for _, satir in df.iterrows():
                donem = donem_normalize(satir[bulunan["donem"]])
                if donem is None:
                    continue
                satirlar.append({
                    "sirket_kod": sirket, "donem": donem,
                    "urun_kod": kod_metni(satir[bulunan["urun_kod"]]),
                    "urun_ad": str(satir.get(bulunan.get("urun_ad"), "")).strip(),
                    "kategori": str(satir.get(bulunan.get("kategori"), "")).strip(),
                    "miktar": ay(satir[bulunan["miktar"]]),
                    "birim_fiyat": ay(satir.get(bulunan.get("birim_fiyat"), 0)),
                    "tutar": ay(satir[bulunan["tutar"]]),
                    "musteri_tipi": str(satir.get(bulunan.get("musteri_tipi"), "")).strip(),
                    "para_birimi": s.fonksiyonel_para_birimi,
                    "senaryo": senaryo, "kaynak_dosya": yol.name,
                })
        _ayristirici_raporu(ay, yol.name, g)
    return pd.DataFrame(satirlar, columns=SATIS_KOLONLARI)


def oku_grup_ici(y, dosyalar, g: Gunluk) -> pd.DataFrame:
    satirlar = []
    for yol, sirket in dosyalar:
        s = y.sirketler[sirket]
        harita = y.kolon_eslesme["grup_ici"]["*"]
        ay = SayiAyristirici(s.bicim.get("ondalik_ayrac", ","),
                             s.bicim.get("binlik_ayrac", "."))
        for sekme, df in sayfalari_oku(yol):
            if df.empty:
                continue
            bulunan, eksik = kolonlari_esle(df, harita, g, yol.name)
            if [a for a in ("karsi_sirket", "donem", "tutar") if a in eksik]:
                g.uyari(f"{yol.name}[{sekme}]: grup içi kolonları eksik {eksik} — atlandı")
                continue
            for _, satir in df.iterrows():
                donem = donem_normalize(satir[bulunan["donem"]])
                if donem is None:
                    continue
                satirlar.append({
                    "sirket_kod": sirket,
                    "karsi_sirket": kod_metni(satir[bulunan["karsi_sirket"]]),
                    "donem": donem,
                    "tur": str(satir.get(bulunan.get("tur"), "")).strip(),
                    "yon": str(satir.get(bulunan.get("yon"), "")).strip().lower(),
                    "tutar": ay(satir[bulunan["tutar"]]),
                    "para_birimi": s.fonksiyonel_para_birimi,
                    "kaynak_dosya": yol.name,
                })
        _ayristirici_raporu(ay, yol.name, g)
    return pd.DataFrame(satirlar, columns=GRUP_ICI_KOLONLARI)


def _ayristirici_raporu(ay: SayiAyristirici, dosya: str, g: Gunluk):
    if ay.basarisiz:
        g.uyari(f"{dosya}: {ay.basarisiz} tutar sayıya çevrilemedi, 0 yazıldı. "
                f"Örnek: {ay.ornekler[:3]}")
    if ay.belirsiz:
        g.uyari(f"{dosya}: {ay.belirsiz} tutarda ayraç belirsizdi (3 basamaklı kuyruk), "
                f"binlik varsayıldı. Örnek: {ay.ornekler[:3]}")


# ======================================================================
def main():
    g = Gunluk("topla")
    y = yukle()
    g.bilgi(y.ozet())

    if not GIRDI.exists() or not any(GIRDI.iterdir()):
        g.hata(f"Girdi dizini boş: {GIRDI}")
        g.bilgi("Önce demo veriyi üret:  py araclar/veri_uret.py")
        g.bitir({"durum": "girdi_yok"})
        return

    dosyalar = dosyalari_kesfet(y, g)
    g.iyi(f"{sum(len(v) for v in dosyalar.values())} dosya keşfedildi: "
          + ", ".join(f"{k}={len(v)}" for k, v in sorted(dosyalar.items())))

    okuyucular = {"mizan": oku_mizan, "yevmiye": oku_yevmiye, "butce": oku_butce,
                  "satis": oku_satis, "grup_ici": oku_grup_ici}

    ozet = []
    for tip, okuyucu in okuyucular.items():
        if not dosyalar.get(tip):
            g.uyari(f"{tip}: hiç dosya yok")
            continue
        df = okuyucu(y, dosyalar[tip], g)
        hedef = ARA_DIZIN / f"{tip}.csv"
        df.to_csv(hedef, index=False, encoding="utf-8")
        tutar_kolonu = next((k for k in ("borc", "tutar") if k in df.columns), None)
        ozet.append([tip, f"{len(df):,}", df["sirket_kod"].nunique(),
                     df["donem"].nunique() if "donem" in df else "-",
                     para(df[tutar_kolonu].sum(), 0) if tutar_kolonu else "-"])
        g.iz("normalize_edildi", tip=tip, satir=len(df), hedef=hedef.name)

    tablo_yaz("Normalize edilen veri", ozet,
              ["Tip", "Satır", "Şirket", "Dönem", "Toplam (yerel, karışık pb)"])

    # --- Kapsama kontrolü: hangi şirket-dönem hiç gelmemiş? ---
    mizan = pd.read_csv(ARA_DIZIN / "mizan.csv", dtype={"donem": str})
    beklenen = {(s, d) for s in y.sirketler for d in y.donemler()}
    gelen = set(zip(mizan["sirket_kod"], mizan["donem"]))
    eksik = sorted(beklenen - gelen)
    if eksik:
        g.uyari(f"Mizanı hiç gelmeyen {len(eksik)} şirket-dönem: {eksik}")
        g.iz("eksik_donem", liste=[f"{s}/{d}" for s, d in eksik])
    else:
        g.iyi("Tüm şirket-dönem kombinasyonlarının mizanı geldi.")

    g.bitir({"tip": len(ozet), "eksik_donem": len(eksik)})


if __name__ == "__main__":
    main()
