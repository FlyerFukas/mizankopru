# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ: şirket profili oluşturucu.

NE YAPAR
  Tanınmayan bir mizan dosyasını açar, içinden şirket adını, dönemi, para
  birimini, başlık satırını, kolon yerleşimini ve hesap planını TESPİT EDER;
  sonra bu bilgilerle yapılandırmayı üretir ve dosyayı sistemin tanıyacağı
  bir adla kaydeder.

NEDEN GEREKLİ
  Boru hattı tanımadığı hiçbir dosyayı işlemez (bkz. src/kaynak.py). Bu
  bilinçli bir kısıt: tanınmayan dosyayı sessizce atlamak, kullanıcının
  verisini içermeyen ama eksiksiz görünen bir rapor üretir. Bu araç o
  kısıtın çözüm yolu.

TASARIM
  Hiçbir şey tahmin edilip sessizce uygulanmaz. Araç ne bulduğunu gösterir,
  neden öyle karar verdiğini söyler ve emin olmadığı yeri işaretler.
  Yapılandırmayı yazmadan önce onay ister (--uygula ile atlanabilir).

ÇALIŞTIRMA
  py araclar/profil_olustur.py "veri/girdi/mizan 2018 nilsan son.xls"
  py araclar/profil_olustur.py "..." --kod NILSAN --uygula
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

from gunluk import Gunluk, para, tablo_yaz              # noqa: E402
from sema import AYAR_DIZIN, VERI_DIZIN, yukle          # noqa: E402

GIRDI = VERI_DIZIN / "girdi"

# Mizan başlık satırını bulmak için aranan sütun adları
KOD_ADLARI = ["hesap kodu", "hesap no", "hesapkodu", "konto", "nominal code",
              "account code", "hesap"]
AD_ADLARI = ["hesap adı", "hesap adi", "açıklama", "aciklama", "unvan",
             "kontobezeichnung", "name", "account name"]
BORC_ADLARI = ["borç", "borc", "soll", "debit", "borç tutarı"]
ALACAK_ADLARI = ["alacak", "haben", "credit", "alacak tutarı"]
BORC_BAKIYE = ["borç bakiyesi", "borc bakiyesi", "borç bakiye"]
ALACAK_BAKIYE = ["alacak bakiyesi", "alacak bakiye"]

PARA_ISARETLERI = {
    "TL": "TRY", "TRY": "TRY", "₺": "TRY", "TÜRK LİRASI": "TRY",
    "EUR": "EUR", "€": "EUR", "AVRO": "EUR", "EURO": "EUR",
    "USD": "USD", "$": "USD", "DOLAR": "USD",
    "GBP": "GBP", "£": "GBP", "STERLIN": "GBP",
}


def sadelestir(metin: str) -> str:
    """Türkçe karakterleri ASCII'ye indirger; dosya adı ve kod üretmek için."""
    metin = str(metin).replace("İ", "I").replace("ı", "i").replace("Ş", "S") \
        .replace("ş", "s").replace("Ğ", "G").replace("ğ", "g") \
        .replace("Ü", "U").replace("ü", "u").replace("Ö", "O") \
        .replace("ö", "o").replace("Ç", "C").replace("ç", "c")
    metin = unicodedata.normalize("NFKD", metin)
    return "".join(c for c in metin if not unicodedata.combining(c))


def hucre(x) -> str:
    return "" if pd.isna(x) else str(x).strip()


def sayi(x) -> float:
    """Metin ya da sayı hâlindeki tutarı float'a çevirir."""
    if pd.isna(x):
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    m = re.sub(r"[^\d.,\-]", "", str(x))
    if not m:
        return 0.0
    n, v = m.rfind("."), m.rfind(",")
    if n >= 0 and v >= 0:
        ond = "." if n > v else ","
        m = m.replace("," if ond == "." else ".", "").replace(ond, ".")
    elif v >= 0 and len(m) - v - 1 != 3:
        m = m.replace(",", ".")
    elif v >= 0:
        m = m.replace(",", "")
    try:
        return float(m)
    except ValueError:
        return 0.0


class Tespit:
    """Bir mizan dosyasını inceleyip yapısını çıkarır."""

    def __init__(self, yol: Path, g: Gunluk):
        self.yol = yol
        self.g = g
        self.notlar: list[str] = []
        self.uyarilar: list[str] = []

    def oku(self):
        try:
            kitap = pd.read_excel(self.yol, sheet_name=None, header=None, dtype=object)
        except Exception as e:
            raise SystemExit(f"Dosya açılamadı: {type(e).__name__}: {e}")
        # En çok dolu hücreye sahip sekmeyi seç
        self.sekme, self.df = max(
            ((ad, d) for ad, d in kitap.items() if not d.empty),
            key=lambda x: x[1].notna().sum().sum())
        self.notlar.append(
            f"{len(kitap)} sekme bulundu, en dolu olanı seçildi: '{self.sekme}' "
            f"({self.df.shape[0]} satır × {self.df.shape[1]} kolon)")
        return self

    # ---------------- başlık ve kolonlar ----------------
    def baslik_bul(self):
        """HESAP KODU / HESAP ADI gibi sütun adlarını taşıyan satırı bulur."""
        en_iyi, puan_en = None, 0
        for i in range(min(40, len(self.df))):
            satir = [hucre(x).lower() for x in self.df.iloc[i]]
            puan = 0
            if any(a in satir for a in KOD_ADLARI):
                puan += 3
            if any(a in satir for a in AD_ADLARI):
                puan += 2
            if any(a in satir for a in BORC_ADLARI):
                puan += 2
            if any(a in satir for a in ALACAK_ADLARI):
                puan += 2
            if puan > puan_en:
                en_iyi, puan_en = i, puan
        if en_iyi is None or puan_en < 5:
            raise SystemExit(
                "Başlık satırı bulunamadı. Dosyada 'HESAP KODU', 'HESAP ADI', "
                "'BORÇ', 'ALACAK' benzeri sütun adları aranıyor.\n"
                "Dosyanın ilk satırlarında bu adlar yoksa, mizan biçimini "
                "yapilandirma/sirketler.yaml içinde elle tanımlamanız gerekir.")
        self.baslik_satiri = en_iyi
        self.notlar.append(f"Başlık satırı: {en_iyi} (eşleşme puanı {puan_en})")

        satir = [hucre(x).lower() for x in self.df.iloc[en_iyi]]

        def bul(adaylar, tekrar=0):
            """tekrar=0 ilk eşleşme; mizanlarda BORÇ birden çok blokta geçer."""
            sayac = 0
            for k, v in enumerate(satir):
                if v in adaylar:
                    if sayac == tekrar:
                        return k
                    sayac += 1
            return None

        self.k_kod = bul(KOD_ADLARI)
        self.k_ad = bul(AD_ADLARI)
        self.k_borc = bul(BORC_ADLARI)
        self.k_alacak = bul(ALACAK_ADLARI)
        eksik = [a for a, v in [("hesap kodu", self.k_kod), ("hesap adı", self.k_ad),
                                ("borç", self.k_borc), ("alacak", self.k_alacak)]
                 if v is None]
        if eksik:
            raise SystemExit(f"Şu sütunlar bulunamadı: {', '.join(eksik)}")
        self.notlar.append(
            f"Kolonlar: kod={self.k_kod}, ad={self.k_ad}, "
            f"borç={self.k_borc}, alacak={self.k_alacak}")

        # Aynı başlıklar birden çok blokta tekrar ediyorsa uyar
        if satir.count(satir[self.k_borc]) > 1:
            self.uyarilar.append(
                f"'{satir[self.k_borc]}' başlığı {satir.count(satir[self.k_borc])} "
                f"kez geçiyor (çok bloklu mizan). İlk blok kullanıldı; "
                f"yanlış blok seçilmişse kolon numaralarını elle düzeltin.")
        return self

    # ---------------- şirket, dönem, para birimi ----------------
    def ustbilgi_oku(self):
        ust = []
        for i in range(self.baslik_satiri):
            ust += [hucre(x) for x in self.df.iloc[i] if hucre(x)]
        self.ustbilgi = ust

        # Şirket adı: şirket türü kısaltması içeren en uzun satır
        tur = re.compile(r"(A\.?Ş|LTD|ŞTİ|STI|SAN|TİC|TIC|GMBH|LTD|INC|A\.S)", re.I)
        adaylar = [s for s in ust if tur.search(s) and len(s) > 8
                   and not re.search(r"tarih|dönem|donem|sayfa", s, re.I)]
        self.sirket_adi = max(adaylar, key=len) if adaylar else ""
        if not self.sirket_adi:
            self.uyarilar.append(
                "Şirket adı dosyadan okunamadı; --ad ile elle verin.")
        else:
            self.notlar.append(f"Şirket adı: {self.sirket_adi}")

        # Dönem: gg/aa/yyyy aralığı ya da tek yıl
        self.donem, self.donem_kaynak = None, ""
        birlesik = " | ".join(ust)
        ar = re.search(r"(\d{2})[./](\d{2})[./](\d{4})\s*[-–]\s*"
                       r"(\d{2})[./](\d{2})[./](\d{4})", birlesik)
        if ar:
            self.donem = f"{ar.group(6)}-{ar.group(5)}"
            self.donem_kaynak = (f"tarih aralığı {ar.group(1)}.{ar.group(2)}."
                                 f"{ar.group(3)} - {ar.group(4)}.{ar.group(5)}."
                                 f"{ar.group(6)} → bitiş ayı alındı")
        else:
            yil = re.search(r"\b(20\d{2})\b", birlesik)
            if yil:
                self.donem = f"{yil.group(1)}-12"
                self.donem_kaynak = f"yalnızca yıl ({yil.group(1)}) bulundu, Aralık varsayıldı"
                self.uyarilar.append(
                    f"Dönem yalnızca yıldan çıkarıldı ({self.donem}). "
                    f"Yanlışsa --donem ile düzeltin.")
        if self.donem:
            self.notlar.append(f"Dönem: {self.donem} ({self.donem_kaynak})")
        else:
            self.uyarilar.append("Dönem bulunamadı; --donem ile verin (örn. 2018-12).")

        # Para birimi
        self.para = None
        for s in ust:
            for isaret, kod in PARA_ISARETLERI.items():
                if re.search(rf"\b{re.escape(isaret)}\b", s, re.I):
                    self.para = kod
                    self.notlar.append(f"Para birimi: {kod} ('{s[:30]}' satırından)")
                    break
            if self.para:
                break
        if not self.para:
            self.para = "TRY"
            self.uyarilar.append("Para birimi bulunamadı, TRY varsayıldı.")
        return self

    # ---------------- hesaplar ve hiyerarşi ----------------
    def hesaplari_coz(self):
        v = self.df.iloc[self.baslik_satiri + 1:].copy()
        kod = v[self.k_kod].map(hucre)
        gecerli = kod.str.match(r"^\d[\d.]*$", na=False)
        v = v[gecerli]
        self.satir_sayisi = len(v)

        kodlar = v[self.k_kod].map(hucre)
        # Hiyerarşi: hangi uzunluk kaç kez geçiyor
        ana_uzunluk = {}
        for k in kodlar:
            ana = k.split(".")[0]
            ana_uzunluk[len(ana)] = ana_uzunluk.get(len(ana), 0) + 1
        self.hiyerarsi = ana_uzunluk

        # Ana hesap seviyesi: kırılımsız kodların en uzun hâli.
        # VUK Tek Düzen'de bu 3 hanedir; hiyerarşik mizanda 1 ve 2 haneliler
        # gruplama satırıdır ve toplanırsa aynı para birkaç kez sayılır.
        kirilimsiz = [k for k in kodlar if "." not in k]
        uzunluklar = sorted({len(k) for k in kirilimsiz})
        self.ana_seviye = max(uzunluklar) if uzunluklar else 3
        self.desen = rf"^\d{{{self.ana_seviye}}}$"

        ana = v[kodlar.str.match(self.desen)]
        self.ana_sayisi = len(ana)
        self.borc = sum(sayi(x) for x in ana[self.k_borc])
        self.alacak = sum(sayi(x) for x in ana[self.k_alacak])
        self.fark = self.borc - self.alacak
        self.denk = abs(self.fark) < max(1.0, abs(self.borc) * 1e-9)

        self.notlar.append(
            f"Hiyerarşi: " + ", ".join(f"{u} hane × {n}" for u, n
                                       in sorted(ana_uzunluk.items()))
            + f" → ana hesap seviyesi {self.ana_seviye} hane")
        if not self.denk:
            self.uyarilar.append(
                f"Ana hesap seviyesinde borç ({self.borc:,.2f}) ile alacak "
                f"({self.alacak:,.2f}) denk DEĞİL; fark {self.fark:,.2f}. "
                f"Kolon seçimi yanlış olabilir ya da mizanın kendisi bozuk.")

        # Hesap planı tahmini: kodların grup planına eşleşme oranı
        y = yukle()
        self.plan, self.plan_oran = None, 0.0
        ana_kodlar = [hucre(x) for x in ana[self.k_kod]]
        for plan in sorted(set(y.eslesme["plan_kodu"])):
            es = sum(1 for k in ana_kodlar if y.grup_kodu(plan, k))
            oran = es / len(ana_kodlar) if ana_kodlar else 0
            if oran > self.plan_oran:
                self.plan, self.plan_oran = plan, oran
        self.notlar.append(
            f"Hesap planı: {self.plan} (ana hesapların %{self.plan_oran*100:.0f}'i eşleşti)")
        if self.plan_oran < 0.5:
            self.uyarilar.append(
                f"Hesap planı eşleşmesi düşük (%{self.plan_oran*100:.0f}). "
                f"Eşleşmeyen hesaplar askıya alınacak ve K09 bulgusu üretecek.")
        self.eslesmeyen = [k for k in ana_kodlar if not y.grup_kodu(self.plan, k)]
        return self


def kod_uret(ad: str, mevcut: set[str]) -> str:
    """Şirket adından kısa, benzersiz bir kod türetir."""
    temiz = re.sub(r"[^A-Z0-9 ]", " ", sadelestir(ad).upper())
    atla = {"A", "S", "AS", "LTD", "STI", "SAN", "TIC", "VE", "GMBH", "INC",
            "SANAYI", "TICARET", "LIMITED", "SIRKETI", "MAMULLERI", "A.S"}
    kelimeler = [k for k in temiz.split() if k and k not in atla and len(k) > 1]
    kod = (kelimeler[0][:6] if kelimeler else "SIRKET").upper()
    taban, n = kod, 2
    while kod in mevcut:
        kod = f"{taban}{n}"; n += 1
    return kod


def main():
    ap = argparse.ArgumentParser(
        description="Tanınmayan bir mizan dosyası için şirket profili oluşturur")
    ap.add_argument("dosya", help="mizan dosyasının yolu")
    ap.add_argument("--kod", help="şirket kodu (verilmezse addan türetilir)")
    ap.add_argument("--ad", help="şirket ünvanı (dosyadan okunamazsa)")
    ap.add_argument("--donem", help="dönem, örn. 2018-12")
    ap.add_argument("--para", help="para birimi, örn. TRY")
    ap.add_argument("--uygula", action="store_true",
                    help="onay sormadan yapılandırmayı yaz")
    a = ap.parse_args()

    g = Gunluk("profil")
    yol = Path(a.dosya)
    if not yol.exists():
        yol = KOK / a.dosya
    if not yol.exists():
        g.hata(f"Dosya bulunamadı: {a.dosya}")
        return 1

    g.bilgi(f"İncelenen dosya: {yol.name}")
    t = Tespit(yol, g).oku().baslik_bul().ustbilgi_oku().hesaplari_coz()

    y = yukle()
    ad = a.ad or t.sirket_adi or yol.stem
    kod = (a.kod or kod_uret(ad, set(y.sirketler))).upper()
    donem = a.donem or t.donem
    para = (a.para or t.para).upper()

    if not donem:
        g.hata("Dönem belirlenemedi. --donem 2018-12 gibi verin.")
        return 1

    # ---- Tespit raporu ----
    print()
    tablo_yaz("TESPİT EDİLENLER", [
        ["Şirket ünvanı", ad[:52]],
        ["Şirket kodu", kod + ("  (addan türetildi)" if not a.kod else "")],
        ["Dönem", f"{donem}  ({t.donem_kaynak})" if t.donem_kaynak else donem],
        ["Para birimi", para],
        ["Hesap planı", f"{t.plan}  (%{t.plan_oran*100:.0f} eşleşme)"],
        ["Sekme", t.sekme],
        ["Başlık satırı", str(t.baslik_satiri)],
        ["Kolonlar", f"kod={t.k_kod}, ad={t.k_ad}, borç={t.k_borc}, alacak={t.k_alacak}"],
        ["Toplam hesap satırı", f"{t.satir_sayisi:,}"],
        ["Ana hesap seviyesi", f"{t.ana_seviye} hane → {t.ana_sayisi} hesap"],
        ["Borç toplamı", f"{para_bicim(t.borc)} {para}"],
        ["Alacak toplamı", f"{para_bicim(t.alacak)} {para}"],
        ["Denklik", "DENK" if t.denk else f"DENK DEĞİL (fark {para_bicim(t.fark)})"],
        ["Eşleşmeyen hesap", f"{len(t.eslesmeyen)} adet"
         + (f" · {', '.join(t.eslesmeyen[:8])}" if t.eslesmeyen else "")],
    ], ["Alan", "Değer"])

    print()
    for n in t.notlar:
        g.bilgi(f"  {n}")
    for u in t.uyarilar:
        g.uyari(f"  {u}")

    print()
    g.bilgi("YAPILACAKLAR")
    hedef_ad = f"{kod}_mizan_{donem}{yol.suffix.lower()}"
    print(f"  1. yapilandirma/sirketler.yaml → '{kod}' şirketi eklenecek")
    print(f"     (mizan biçimi: sekme '{t.sekme}', başlık satırı {t.baslik_satiri},")
    print(f"      ana hesap deseni {t.desen})")
    print(f"  2. yapilandirma/kurlar.csv → {donem} / {para} satırı eklenecek"
          if (donem, para) not in y.kur_sozluk else
          f"  2. kurlar.csv zaten {donem}/{para} içeriyor, dokunulmayacak")
    print(f"  3. Dosya yeniden adlandırılacak:")
    print(f"     {yol.name}")
    print(f"     → {hedef_ad}")

    if not a.uygula:
        print()
        cevap = input("  Uygulansın mı? (e/H): ").strip().lower()
        if cevap not in ("e", "evet", "y", "yes"):
            g.bilgi("Vazgeçildi, hiçbir dosya değiştirilmedi.")
            return 0

    # ---- 1. sirketler.yaml ----
    sy = AYAR_DIZIN / "sirketler.yaml"
    metin = sy.read_text(encoding="utf-8")
    if f'kod: "{kod}"' in metin:
        g.uyari(f"'{kod}' zaten sirketler.yaml içinde, atlandı.")
    else:
        blok = f'''
  - kod: "{kod}"
    ad: "{ad}"
    ulke: "TR"
    fonksiyonel_para_birimi: "{para}"
    hesap_plani: "{t.plan}"
    sahiplik_orani: 1.00
    faaliyet: ""
    hiperenflasyon: {"true" if para == "TRY" else "false"}
    bicim:
      ondalik_ayrac: ","
      binlik_ayrac: "."
      tarih_bicimi: "%d.%m.%Y"
      kodlama: "utf-8"
    # Bu blok profil_olustur.py tarafından üretildi. Dosyanın yapısı
    # tahmin edilmedi, ölçüldü: başlık satırı ve kolon numaraları
    # gerçek dosyadan okundu.
    mizan_bicimi:
      sekme: "{t.sekme}"
      baslik_satiri: {t.baslik_satiri}
      kolon_kod: {t.k_kod}
      kolon_ad: {t.k_ad}
      kolon_borc: {t.k_borc}
      kolon_alacak: {t.k_alacak}
      # Hiyerarşik mizanda yalnızca bu desene uyan satırlar toplanır.
      # 1 ve 2 haneli satırlar gruplama toplamıdır; dahil edilirse
      # aynı tutar birkaç kez sayılır.
      # Regex tek tırnak içinde yazılır: YAML'da çift tırnaklı bir
      # dizgide \d geçersiz kaçış sayılır ve dosya okunamaz hâle gelir.
      ana_hesap_deseni: '{t.desen}'
      sabit_donem: "{donem}"
'''
        metin = metin.replace("\n# Grup içi işlem çiftleri",
                              blok + "\n# Grup içi işlem çiftleri")
        sy.write_text(metin, encoding="utf-8")
        g.iyi(f"sirketler.yaml: '{kod}' eklendi")

    # ---- 2. kurlar.csv ----
    import csv
    ky = AYAR_DIZIN / "kurlar.csv"
    satirlar = list(csv.DictReader(open(ky, encoding="utf-8-sig")))
    varsa = any(s["donem"] == donem and s["para_birimi"] == para for s in satirlar)
    if varsa:
        g.bilgi(f"kurlar.csv: {donem}/{para} zaten var")
    else:
        sunum = y.sunum_para_birimi
        kur = "1.00000000" if para == sunum else ""
        if not kur:
            g.uyari(f"{para} → {sunum} kuru bilinmiyor; 1.0 yazıldı. "
                    f"Gerçek kuru kurlar.csv'de düzeltin.")
            kur = "1.00000000"
        satirlar.append({"donem": donem, "para_birimi": para,
                         "kapanis_kuru": kur, "ortalama_kur": kur,
                         "butce_kuru": kur, "kaynak": "profil_olustur (elle doğrulayın)"})
        with open(ky, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["donem", "para_birimi", "kapanis_kuru",
                                              "ortalama_kur", "butce_kuru", "kaynak"])
            w.writeheader(); w.writerows(satirlar)
        g.iyi(f"kurlar.csv: {donem}/{para} eklendi")

    # ---- 3. dosyayı yeniden adlandır ----
    hedef = GIRDI / hedef_ad
    GIRDI.mkdir(parents=True, exist_ok=True)
    if yol.resolve() != hedef.resolve():
        if hedef.exists():
            hedef.unlink()
        shutil.move(str(yol), str(hedef))
        g.iyi(f"Dosya taşındı: {hedef.name}")

    print()
    g.iyi("Profil hazır. Şimdi çalıştırabilirsiniz:")
    print()
    print("    py src/kaynak.py          (doğrulamayı görmek için)")
    print("    py src/boru.py            (boru hattını çalıştırmak için)")
    print()
    g.bitir({"sirket": kod, "donem": donem, "ana_hesap": t.ana_sayisi,
             "denk": t.denk})
    return 0


def para_bicim(d: float) -> str:
    return para(d, 2)


if __name__ == "__main__":
    sys.exit(main())
