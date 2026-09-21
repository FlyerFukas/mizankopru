# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ [1] TOPLA: çok formatlı okuma ve normalizasyon.

GÖREV
  veri/girdi/ altındaki dağınık ERP çıktılarını tek şemaya indirir:
  farklı dosya biçimi (xlsx tek sekme / xlsx çok sekme / csv), farklı kolon adı
  (Borç / Soll / Debit), farklı sayı biçimi (1.234,56 / 1,234.56), farklı tarih
  biçimi ve dönemin üç ayrı yerden gelmesi (dosya adı / sekme adı / kolon).

EN TEHLİKELİ HATA
  Sayı biçimini yanlış okumak. "1.234" Türkçe biçimde bin iki yüz otuz dört,
  İngilizce biçimde bir virgül iki üç dört. Bu hatayı yapan boru hattı çöker
  değil, sessizce 1000 kat yanlış rakam üretir. Bu yüzden sayı ayrıştırıcı
  önce şirketin yapılandırılmış biçimini uygular, sonuç belirsizse
  sezgisel çözümler ve HER BELİRSİZ DURUMU raporlar.

ÇALIŞTIRMA
  py src/topla.py
ÇIKTI
  veri/ara/{mizan,yevmiye,butce,satis,grup_ici}.csv
"""
from __future__ import annotations

import re
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gunluk import Gunluk, dosya_parmak_izi, para, tablo_yaz      # noqa: E402
from sema import (ARA_DIZIN, CIKTI_DIZIN, VERI_DIZIN,             # noqa: E402
                  BUTCE_KOLONLARI, GRUP_ICI_KOLONLARI, MIZAN_KOLONLARI,
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
    vermiyorsa sezgisel çalışır ve belirsiz her durumu sayar, sayaç
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
                # Gerçekten ondalıksa 1000 kat hata olur, bu yüzden sayılıyor.
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
    sessizce eşleşmemesine yol açar, tablo yine denk görünür, kalem kaybolur.
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
    # Kısmi eşleşme, son çare
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

def _oku_mizan_olculmus(y, yol: Path, sirket: str, g: Gunluk) -> list[dict]:
    """Kolon ADLARIYLA eşleştirilemeyen mizanları, profil_olustur.py'nin
    ÖLÇTÜĞÜ yerleşimle okur.

    Hiyerarşik mizanlarda (1 → 10 → 100 → 100.01 → 100.01.001) her seviye
    bir altındakilerin toplamıdır. Hepsi alınırsa aynı tutar birkaç kez
    sayılır; bu yüzden yalnızca ana_hesap_deseni'ne uyan satırlar alınır."""
    s = y.sirketler[sirket]
    b = s.mizan_bicimi
    ay = SayiAyristirici(s.bicim.get("ondalik_ayrac", ","),
                         s.bicim.get("binlik_ayrac", "."))
    sekme = b.get("sekme", 0)
    try:
        df = pd.read_excel(yol, sheet_name=sekme, header=None, dtype=object)
    except Exception as e:
        g.hata(f"{yol.name}: okunamadı ({type(e).__name__}: {e})")
        return []

    bas = int(b.get("baslik_satiri", 0))
    k_kod = int(b["kolon_kod"]); k_ad = int(b["kolon_ad"])
    k_borc = int(b["kolon_borc"]); k_alacak = int(b["kolon_alacak"])
    desen = re.compile(b.get("ana_hesap_deseni", r"^\d+$"))
    sabit_donem = b.get("sabit_donem")
    donem_kolonu = b.get("kolon_donem")

    satirlar, atlanan, toplanan = [], 0, 0
    for i in range(bas + 1, len(df)):
        try:
            kod = kod_metni(df.iat[i, k_kod])
        except IndexError:
            continue
        if not kod:
            continue
        if not desen.match(kod):
            atlanan += 1            # gruplama ya da alt kırılım satırı
            continue
        donem = (donem_normalize(df.iat[i, int(donem_kolonu)])
                 if donem_kolonu is not None else None) or sabit_donem
        if donem is None:
            continue
        borc = ay(df.iat[i, k_borc])
        alacak = ay(df.iat[i, k_alacak])
        if abs(borc) + abs(alacak) < 0.005:
            continue
        satirlar.append({
            "sirket_kod": sirket, "donem": donem, "yerel_hesap_kod": kod,
            "yerel_hesap_ad": str(df.iat[i, k_ad]).strip(),
            "borc": borc, "alacak": alacak, "bakiye": borc - alacak,
            "para_birimi": s.fonksiyonel_para_birimi, "kaynak_dosya": yol.name,
        })
        toplanan += 1

    g.bilgi(f"{yol.name}: ölçülmüş yerleşimle okundu · sekme '{sekme}', "
            f"başlık satırı {bas} · {toplanan} ana hesap alındı, "
            f"{atlanan} gruplama/kırılım satırı atlandı (mükerrer sayımı önlemek için)")
    _ayristirici_raporu(ay, yol.name, g)

    # Denklik hemen burada sınanır: yanlış kolon seçilmişse en erken belirti budur
    for donem in sorted({x["donem"] for x in satirlar}):
        alt = [x for x in satirlar if x["donem"] == donem]
        fark = sum(x["borc"] for x in alt) - sum(x["alacak"] for x in alt)
        if abs(fark) > 1.0:
            g.uyari(f"{yol.name} [{donem}]: borç-alacak farkı {para(fark, 2)} "
                    f"{s.fonksiyonel_para_birimi}. Kolon seçimi yanlış olabilir "
                    f"(yapilandirma/sirketler.yaml → {sirket} → mizan_bicimi).")
    return satirlar


def oku_mizan(y, dosyalar, g: Gunluk) -> pd.DataFrame:
    satirlar = []
    for yol, sirket in dosyalar:
        # Ölçülmüş yerleşim tanımlıysa onu kullan
        if y.sirketler[sirket].mizan_bicimi:
            satirlar += _oku_mizan_olculmus(y, yol, sirket, g)
            continue
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
                g.uyari(f"{yol.name}[{sekme}]: eksik kolon {eksik}, atlandı")
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
                g.uyari(f"{yol.name}[{sekme}]: kritik kolon eksik {kritik}, atlandı")
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
                g.uyari(f"{yol.name}[{sekme}]: bütçe kolonları eksik {eksik}, atlandı")
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
                g.uyari(f"{yol.name}[{sekme}]: satış kolonları eksik {eksik}, atlandı")
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
                g.uyari(f"{yol.name}[{sekme}]: grup içi kolonları eksik {eksik}, atlandı")
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
def bayatlat(g) -> int:
    """Geçersiz çalıştırma sonrası eski çıktıları arşive taşır.

    Silmez: oradaki rakamlar bir zamanlar doğruydu ve denetim izinin
    parçası. Ama cikti/ kökünde bırakılırsa güncel sanılır; bu sistemin
    tek ciddi hata sınıfı tam olarak budur."""
    hedef = CIKTI_DIZIN / "bayat"
    tasinacak = [f for f in CIKTI_DIZIN.glob("*")
                 if f.is_file()
                 and f.name not in ("NEDEN_BAYAT.txt", ".gitkeep")]
    if not tasinacak:
        return 0
    hedef.mkdir(parents=True, exist_ok=True)
    damga = datetime.now().strftime("%Y%m%d_%H%M%S")
    klasor = hedef / damga
    klasor.mkdir(exist_ok=True)
    for f in tasinacak:
        f.replace(klasor / f.name)
    (CIKTI_DIZIN / "NEDEN_BAYAT.txt").write_text(f"""\
Bu klasördeki çıktılar, kaynak doğrulaması BAŞARISIZ olan bir
çalıştırma sırasında bayatladı ve cikti/bayat/{damga}/ altına taşındı.

Onlar önceki bir çalıştırmanın sonucudur; ŞU ANDA veri/girdi/ içinde
duran dosyaları YANSITMAZ.

Güncel çıktı üretmek için önce kaynak sorununu giderin:
    py araclar/profil_olustur.py "veri/girdi/DOSYA_ADI"
sonra:
    py src/boru.py
""", encoding="utf-8")
    return len(tasinacak)


def main():
    g = Gunluk("topla")
    y = yukle()
    g.bilgi(y.ozet())

    if not GIRDI.exists() or not any(GIRDI.iterdir()):
        g.hata(f"Girdi dizini boş: {GIRDI}")
        g.bilgi("Önce demo veriyi üret:  py araclar/veri_uret.py")
        g.bitir({"durum": "girdi_yok"})
        return

    # ---- KAYNAK DOĞRULAMASI ----
    # Tanınmayan bir dosya varken devam etmek, kullanıcının verisini
    # içermeyen ama eksiksiz görünen bir rapor üretir. Bu yüzden burada
    # durulur; --kaynak-zorla ile geçilirse çıktılara damga basılır.
    import kaynak as K
    zorla = ("--kaynak-zorla" in sys.argv
             or os.environ.get("MIZANKOPRU_KAYNAK_ZORLA") == "1")
    rapor = K.tara(y, dosya_tipi, sirket_bul)
    K.rapor_yaz(rapor, g)
    try:
        K.dogrula(rapor, zorla=zorla, g=g)
    except K.KaynakHatasi as e:
        print(e)
        K.koken_yaz(rapor, zorlandi=False)
        # Önceki çalıştırmanın çıktıları yerinde kalırsa, hata mesajını
        # kaçıran bir kullanıcı panoyu açıp GÜNCEL sanır. Bunlar arşive
        # taşınır: silmek de yanlış olur, oradaki rakamlar bir zamanlar
        # doğruydu ve hâlâ okunabilir olmalı.
        tasinan = bayatlat(g)
        if tasinan:
            g.uyari(f"Önceki çalıştırmanın {tasinan} çıktısı "
                    f"cikti/bayat/ altına taşındı; yanlışlıkla güncel "
                    f"sanılmasın diye.")
        g.hata("Boru hattı durduruldu: veri kaynağı doğrulanamadı.")
        g.bitir({"durum": "kaynak_gecersiz",
                 "taninmayan": len(rapor.taninmayan)})
        raise SystemExit(2)
    # Önceki çalıştırmanın ara dosyaları silinir. Silinmezse, bu sefer
    # yüklenmemiş bir veri tipinin ESKİ dosyası yerinde kalır ve sonraki
    # adımlar onu bu çalıştırmanın verisi sanar. Kullanıcı tek bir mizan
    # yüklemişken 42.000 satırlık eski bir yevmiyenin işlenmesi tam olarak
    # böyle olur.
    # SIRA ÖNEMLİ: temizlik köken kaydından ÖNCE yapılır, aksi hâlde bu
    # çalıştırmanın köken kaydı kendi temizliğinde siliniyor.
    eski = list(ARA_DIZIN.glob("*.csv")) + [ARA_DIZIN / "kapsam.json",
                                            ARA_DIZIN / "koken.json"]
    silinen = 0
    for f in eski:
        if f.exists():
            f.unlink(); silinen += 1
    if silinen:
        g.bilgi(f"Önceki çalıştırmadan kalan {silinen} ara dosya silindi "
                f"(eski verinin yenisine karışmaması için)")

    # Doğrulama geçildi: önceki başarısız çalıştırmanın bayat damgası kalkar.
    bayat_damga = CIKTI_DIZIN / "NEDEN_BAYAT.txt"
    if bayat_damga.exists():
        bayat_damga.unlink()

    koken = K.koken_yaz(rapor, zorlandi=zorla)
    g.iz("koken", **{k: v for k, v in koken.items() if k != "dosyalar"})

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

    # --- Kapsam ve eksiklik ---
    # Bu çalıştırmanın kapsamı YÜKLENEN VERİDİR, yapılandırma değil.
    # Yapılandırmada tanımlı ama hiç dosyası gelmemiş bir şirket "eksik"
    # değil, bu çalıştırmada "kapsam dışı"dır. Eksiklik yalnızca kapsam
    # içindeki şirketlerin ara dönemlerinde anlamlıdır: veri yollayan bir
    # şirketin bir ayının atlanması gerçek bir bulgudur (K10).
    mizan = pd.read_csv(ARA_DIZIN / "mizan.csv", dtype={"donem": str})
    kapsam_sirket = sorted(mizan["sirket_kod"].unique())
    kapsam_donem = sorted(mizan["donem"].unique())
    kapsam_disi = sorted(set(y.sirketler) - set(kapsam_sirket))

    g.bilgi("")
    g.iyi(f"Bu çalıştırmanın kapsamı: {len(kapsam_sirket)} şirket "
          f"({', '.join(kapsam_sirket)}) · {len(kapsam_donem)} dönem "
          f"({kapsam_donem[0]}"
          + (f" → {kapsam_donem[-1]}" if len(kapsam_donem) > 1 else "") + ")")
    if kapsam_disi:
        g.bilgi(f"Kapsam dışı (yapılandırmada var, verisi yüklenmedi): "
                f"{', '.join(kapsam_disi)}")

    # Kapsam içi şirketlerin ARA dönemlerindeki boşluklar gerçek eksikliktir
    eksik = []
    for s in kapsam_sirket:
        donemler = sorted(mizan[mizan["sirket_kod"] == s]["donem"].unique())
        if len(donemler) < 2:
            continue
        tum = [d for d in y.donemler() if donemler[0] <= d <= donemler[-1]]
        eksik += [(s, d) for d in tum if d not in donemler]
    if eksik:
        g.uyari(f"Kapsam içinde mizanı gelmeyen {len(eksik)} şirket-dönem: "
                f"{eksik[:12]}" + (" ..." if len(eksik) > 12 else ""))
        g.iz("eksik_donem", liste=[f"{s}/{d}" for s, d in eksik])
    else:
        g.iyi("Kapsam içindeki her şirket-dönem için mizan var.")

    # Kapsamı sonraki adımlar için kaydet
    import json as _json
    (ARA_DIZIN / "kapsam.json").write_text(_json.dumps({
        "sirketler": kapsam_sirket, "donemler": kapsam_donem,
        "kapsam_disi": kapsam_disi,
        "veri_tipleri": [t for t in okuyucular if dosyalar.get(t)],
        "eksik_donem": [f"{s}/{d}" for s, d in eksik],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    g.bitir({"tip": len(ozet), "eksik_donem": len(eksik)})


if __name__ == "__main__":
    main()
