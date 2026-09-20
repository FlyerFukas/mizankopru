# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ. Yapılandırma yükleyici ve iç veri şeması.

Motorun tek doğruluk kaynağı burası. Boru hattının hiçbir adımı
YAML/CSV dosyasını doğrudan okumaz; hepsi Yapilandirma nesnesinden geçer.
Böylece yapılandırma bir kez doğrulanır ve tutarsızlık adım adım değil,
en başta yakalanır.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml

KOK = Path(__file__).resolve().parent.parent
AYAR_DIZIN = KOK / "yapilandirma"
VERI_DIZIN = KOK / "veri"
CIKTI_DIZIN = KOK / "cikti"
ARA_DIZIN = KOK / "veri" / "ara"     # adımlar arası saklama

for _d in (CIKTI_DIZIN, ARA_DIZIN):
    _d.mkdir(parents=True, exist_ok=True)


# ===================== İÇ VERİ ŞEMASI =====================
# Boru hattının her adımı bu kolon adlarını kullanır. Girdi dosyasının
# kolonu ne olursa olsun topla.py burada tanımlı adlara çevirir.

MIZAN_KOLONLARI = [
    "sirket_kod", "donem", "yerel_hesap_kod", "yerel_hesap_ad",
    "borc", "alacak", "bakiye", "para_birimi", "kaynak_dosya",
]

YEVMIYE_KOLONLARI = [
    "sirket_kod", "donem", "fis_no", "fis_tarihi", "belge_tarihi",
    "yerel_hesap_kod", "borc", "alacak", "aciklama", "kullanici",
    "kayit_zamani", "masraf_merkezi", "para_birimi", "kaynak_dosya",
]

BUTCE_KOLONLARI = [
    "sirket_kod", "donem", "yerel_hesap_kod", "tutar",
    "masraf_merkezi", "para_birimi", "kaynak_dosya",
]

SATIS_KOLONLARI = [
    "sirket_kod", "donem", "urun_kod", "urun_ad", "kategori",
    "miktar", "birim_fiyat", "tutar", "musteri_tipi",
    "para_birimi", "senaryo", "kaynak_dosya",      # senaryo: fiili | butce
]

GRUP_ICI_KOLONLARI = [
    "sirket_kod", "karsi_sirket", "donem", "tur", "yon",
    "tutar", "para_birimi", "kaynak_dosya",
]

BULGU_KOLONLARI = [
    "test_kod", "test_ad", "onem", "sirket_kod", "donem",
    "nesne", "tutar_eur", "aciklama", "kanit",
]

ONEM_SIRASI = {"kritik": 0, "yuksek": 1, "orta": 2, "dusuk": 3}


@dataclass
class Sirket:
    kod: str
    ad: str
    ulke: str
    fonksiyonel_para_birimi: str
    hesap_plani: str
    sahiplik_orani: float
    faaliyet: str
    hiperenflasyon: bool
    bicim: dict = field(default_factory=dict)


class YapilandirmaHatasi(Exception):
    pass


class Yapilandirma:
    """Tüm ayar dosyalarını yükler, tutarlılığını doğrular, erişim sağlar."""

    def __init__(self, dizin: Path | str = AYAR_DIZIN):
        self.dizin = Path(dizin)
        self._yukle()
        self.dogrula()

    # ---------------------------------------------------------------
    def _yaml(self, ad: str) -> dict:
        yol = self.dizin / ad
        if not yol.exists():
            raise YapilandirmaHatasi(f"Ayar dosyası bulunamadı: {yol}")
        with open(yol, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _csv(self, ad: str) -> pd.DataFrame:
        yol = self.dizin / ad
        if not yol.exists():
            raise YapilandirmaHatasi(f"Ayar dosyası bulunamadı: {yol}")
        return pd.read_csv(yol, dtype=str, encoding="utf-8-sig").fillna("")

    def _yukle(self):
        s = self._yaml("sirketler.yaml")
        self.grup = s["grup"]
        self.sunum_para_birimi = s["grup"]["sunum_para_birimi"]
        self.sirketler = {
            x["kod"]: Sirket(
                kod=x["kod"], ad=x["ad"], ulke=x["ulke"],
                fonksiyonel_para_birimi=x["fonksiyonel_para_birimi"],
                hesap_plani=x["hesap_plani"],
                sahiplik_orani=float(x["sahiplik_orani"]),
                faaliyet=x.get("faaliyet", ""),
                hiperenflasyon=bool(x.get("hiperenflasyon", False)),
                bicim=x.get("bicim", {}),
            )
            for x in s["sirketler"]
        }
        self.grup_ici_iliskiler = s.get("grup_ici_iliskiler", [])

        gp = self._yaml("grup_hesap_plani.yaml")
        self.grup_hesaplari = {h["kod"]: h for h in gp["hesaplar"]}
        self.gelir_tablosu_duzeni = gp["gelir_tablosu_duzeni"]
        self.bilanco_duzeni = gp["bilanco_duzeni"]

        self.eslesme = self._csv("hesap_eslesme.csv")
        # (plan_kodu, yerel_kod) -> grup_kod  hızlı sözlük
        self.eslesme_sozluk = {
            (r.plan_kodu, str(r.yerel_kod).strip()): r.grup_kod
            for r in self.eslesme.itertuples()
        }

        k = self._csv("kurlar.csv")
        for kolon in ("kapanis_kuru", "ortalama_kur", "butce_kuru"):
            if kolon in k.columns:
                k[kolon] = k[kolon].astype(float)
        if "butce_kuru" not in k.columns:      # eski kurlar.csv ile geriye uyum
            k["butce_kuru"] = k["kapanis_kuru"]
        self.kurlar = k
        self.kur_sozluk = {
            (r.donem, r.para_birimi):
                {"kapanis": r.kapanis_kuru, "ortalama": r.ortalama_kur,
                 "butce": r.butce_kuru}
            for r in k.itertuples()
        }

        kt = self._yaml("kontroller.yaml")
        self.kontrol_genel = kt["genel"]
        self.kontroller = {t["kod"]: t for t in kt["testler"]}

        self.kolon_eslesme = self._yaml("kolon_eslesme.yaml")

    # ---------------------------------------------------------------
    def dogrula(self):
        """Ayar dosyaları arası tutarlılık. Hatayı en başta yakala."""
        sorunlar = []

        gecerli_grup = set(self.grup_hesaplari)
        hedefler = set(self.eslesme["grup_kod"])
        if hedefler - gecerli_grup:
            sorunlar.append(
                "hesap_eslesme.csv, grup planında olmayan koda işaret ediyor: "
                f"{sorted(hedefler - gecerli_grup)}")

        planlar_kullanilan = {s.hesap_plani for s in self.sirketler.values()}
        planlar_tanimli = set(self.eslesme["plan_kodu"])
        if planlar_kullanilan - planlar_tanimli:
            sorunlar.append(
                "Şirketlerin kullandığı hesap planı eşleme tablosunda yok: "
                f"{sorted(planlar_kullanilan - planlar_tanimli)}")

        pb_gerekli = {s.fonksiyonel_para_birimi for s in self.sirketler.values()}
        pb_gerekli.add(self.sunum_para_birimi)
        pb_tanimli = set(self.kurlar["para_birimi"])
        if pb_gerekli - pb_tanimli:
            sorunlar.append(
                f"kurlar.csv'de eksik para birimi: {sorted(pb_gerekli - pb_tanimli)}")

        for kod, lim in self.kontrol_genel.get("onay_limitleri", {}).items():
            if kod not in self.sirketler:
                sorunlar.append(f"kontroller.yaml'da tanımsız şirket kodu: {kod}")
            elif lim["para_birimi"] != self.sirketler[kod].fonksiyonel_para_birimi:
                sorunlar.append(
                    f"{kod} onay limiti {lim['para_birimi']} ama şirketin fonksiyonel "
                    f"para birimi {self.sirketler[kod].fonksiyonel_para_birimi}")

        for iliski in self.grup_ici_iliskiler:
            for rol in ("satici", "alici"):
                if iliski[rol] not in self.sirketler:
                    sorunlar.append(f"grup_ici_iliskiler'de tanımsız şirket: {iliski[rol]}")

        if sorunlar:
            raise YapilandirmaHatasi(
                "Yapılandırma tutarsız:\n  - " + "\n  - ".join(sorunlar))

    # ---------------------------------------------------------------
    # Erişim yardımcıları
    def grup_kodu(self, plan: str, yerel_kod: str) -> str | None:
        return self.eslesme_sozluk.get((plan, str(yerel_kod).strip()))

    def kur(self, donem: str, para_birimi: str, tip: str = "kapanis") -> float:
        """1 birim para_birimi kaç sunum para birimi eder.

        tip:
          kapanis. IAS 21, bilanço kalemleri (dönem sonu kuru)
          ortalama. IAS 21, gelir tablosu kalemleri (dönem içi ortalama)
          butce, bütçe yapılırken yıl başında sabitlenen kur.
                     Fiiliyi bu kurla çevirmek kur etkisini izole eder
                     (sabit kur / constant currency).
        """
        anahtar = (donem, para_birimi)
        if anahtar not in self.kur_sozluk:
            raise YapilandirmaHatasi(f"Kur bulunamadı: {donem} {para_birimi}")
        kurlar = self.kur_sozluk[anahtar]
        if tip not in kurlar:
            raise YapilandirmaHatasi(f"Bilinmeyen kur tipi: {tip}")
        return kurlar[tip]

    def aski_hesabi(self) -> str:
        """Grup planına eşlenemeyen satırların düştüğü askı hesabı."""
        for kod, h in self.grup_hesaplari.items():
            if h.get("aski"):
                return kod
        return "9999"

    def cevrim_tipi(self, grup_kod: str) -> str:
        """IAS 21: bilanço kalemleri kapanış, gelir tablosu ortalama kur."""
        h = self.grup_hesaplari.get(grup_kod)
        if h is None:
            return "kapanis"
        return "kapanis" if h["tur"] == "B" else "ortalama"

    def sunum_isareti(self, grup_kod: str) -> int:
        """Bakiye borç-alacak olarak tutulur; sunumda alacak bakiyeli
        hesapların işareti çevrilir ki hasılat pozitif görünsün."""
        h = self.grup_hesaplari.get(grup_kod)
        return -1 if (h and h["yon"] == -1) else 1

    def donemler(self) -> list[str]:
        return sorted(self.kurlar["donem"].unique())

    def elimine_hesaplar(self) -> set[str]:
        return {k for k, h in self.grup_hesaplari.items() if h.get("elimine")}

    def ozet(self) -> str:
        return (f"{self.grup['ad']} · sunum {self.sunum_para_birimi} · "
                f"{len(self.sirketler)} şirket · {len(self.grup_hesaplari)} grup hesabı · "
                f"{len(self.eslesme)} eşleme · {len(self.donemler())} dönem · "
                f"{len(self.kontroller)} kontrol testi")


def yukle() -> Yapilandirma:
    return Yapilandirma()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from gunluk import Gunluk, tablo_yaz

    g = Gunluk("sema")
    y = yukle()
    g.iyi("Yapılandırma tutarlı.")
    g.bilgi(y.ozet())
    tablo_yaz("Şirketler",
              [[s.kod, s.ad, s.fonksiyonel_para_birimi, s.hesap_plani,
                f"%{s.sahiplik_orani*100:.0f}", "evet" if s.hiperenflasyon else "hayır"]
               for s in y.sirketler.values()],
              ["Kod", "Ad", "Para", "Plan", "Pay", "Hiperenf."])
    tablo_yaz("Eliminasyona tabi grup hesapları",
              [[k, y.grup_hesaplari[k]["ad"]] for k in sorted(y.elimine_hesaplar())],
              ["Kod", "Ad"])
    g.bitir({"sirket": len(y.sirketler), "grup_hesap": len(y.grup_hesaplari)})
