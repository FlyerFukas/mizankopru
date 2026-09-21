# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ · BULGU ETİKETLEME (Sistem 2'nin veri toplama ayağı)

GÖREV
  Kontrol testlerinin ürettiği bulguları "gerçek" ya da "gürültü" diye
  işaretlemeyi sağlar. Biriken etiketler, bulgu triyajı modelinin eğitim
  verisidir.

NEDEN ÖNCE VERİ TOPLAMA
  İlk kontrol turunda 1.902 bulgu çıkmıştı, 1.499'u tek bir testten ve
  çoğu gürültüydü. Kapsam daraltmasıyla 130'a indi. Bu daraltmayı bugün
  insan yapıyor, her yeni veri setinde yeniden. Hangi bulgu deseninin
  aksiyona dönüştüğü ancak geri bildirimle öğrenilebilir; model olmadan
  önce etiket gerekir.

ETİKET NE DEĞİLDİR
  "Gürültü" demek bulgunun silinmesi değildir. Etiket yalnızca gelecekteki
  SIRALAMAYI etkiler. Bir denetim aracında hiçbir bulgu listeden çıkmaz.

ÇALIŞTIRMA
  py araclar/bulgu_etiketle.py --listele
  py araclar/bulgu_etiketle.py --etiket K20:gercek K18:gurultu
  py araclar/bulgu_etiketle.py --durum
ÇIKTI
  cikti/bulgu_etiketleri.csv (birikimli, çalıştırmalar arası korunur)
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

from gunluk import Gunluk, para, tablo_yaz                    # noqa: E402
from sema import CIKTI_DIZIN                                  # noqa: E402

ETIKET_DOSYASI = CIKTI_DIZIN / "bulgu_etiketleri.csv"
GECERLI = {"gercek", "gurultu", "belirsiz"}

# Model eğitimi için gereken en az etiket. Bunun altında eğitilen bir
# sınıflandırıcı, etiketleyicinin o günkü ruh hâlini öğrenir.
ASGARI_ETIKET = 150


def bulgu_kimligi(r) -> str:
    """Bir bulguyu çalıştırmalar arasında tanıyan kararlı kimlik.

    Bulgular her çalıştırmada yeniden üretilir; satır numarası kimlik
    olamaz. Test kodu, şirket, dönem ve nesnenin birleşimi aynı bulguyu
    aynı bulgu yapar."""
    ham = "|".join(str(getattr(r, alan, ""))
                   for alan in ("test_kod", "sirket_kod", "donem", "nesne"))
    return hashlib.sha256(ham.encode("utf-8")).hexdigest()[:16]


def bulgulari_oku() -> pd.DataFrame:
    yol = CIKTI_DIZIN / "bulgular.csv"
    if not yol.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(yol, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def etiketleri_oku() -> pd.DataFrame:
    if not ETIKET_DOSYASI.exists():
        return pd.DataFrame(columns=["kimlik", "test_kod", "sirket_kod",
                                     "donem", "nesne", "tutar_eur", "onem",
                                     "etiket", "gerekce", "zaman"])
    try:
        return pd.read_csv(ETIKET_DOSYASI, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=["kimlik", "etiket"])


def listele(g: Gunluk):
    bulgular = bulgulari_oku()
    if bulgular.empty:
        g.uyari("cikti/bulgular.csv yok ya da boş. Önce: py src/boru.py")
        g.bitir({"durum": "bulgu_yok"})
        return
    etiketler = etiketleri_oku()
    etiketli = set(etiketler["kimlik"]) if not etiketler.empty else set()

    satirlar = []
    for r in bulgular.itertuples():
        kimlik = bulgu_kimligi(r)
        mevcut = ""
        if kimlik in etiketli:
            mevcut = etiketler.loc[etiketler["kimlik"] == kimlik,
                                   "etiket"].iloc[0]
        satirlar.append([kimlik, r.test_kod, r.onem, str(r.nesne)[:32],
                         para(r.tutar_eur, 0), mevcut or "-"])
    tablo_yaz("Bulgular ve mevcut etiketleri", satirlar,
              ["Kimlik", "Test", "Önem", "Nesne", "Tutar", "Etiket"])
    g.bilgi("Etiketlemek için:")
    g.bilgi('    py araclar/bulgu_etiketle.py --etiket <kimlik>:gercek '
            '<kimlik>:gurultu')
    g.bilgi('    py araclar/bulgu_etiketle.py --etiket K20:gercek   '
            '(test kodu da kabul edilir, o testin tüm bulgularını etiketler)')
    g.bitir({"bulgu": len(bulgular), "etiketli": len(etiketli)})


def etiketle(g: Gunluk, istekler: list[str]):
    bulgular = bulgulari_oku()
    if bulgular.empty:
        g.hata("cikti/bulgular.csv yok ya da boş.")
        g.bitir({"durum": "bulgu_yok"})
        return

    bulgular["bulgu_kimlik"] = [bulgu_kimligi(r)
                                for r in bulgular.itertuples()]
    etiketler = etiketleri_oku()
    yeni, hatali = [], []

    for istek in istekler:
        if ":" not in istek:
            hatali.append(f"{istek} (biçim: <kimlik|test_kodu>:<etiket>)")
            continue
        hedef, etiket = istek.rsplit(":", 1)
        etiket = etiket.strip().lower()
        if etiket not in GECERLI:
            hatali.append(f"{istek} (etiket {sorted(GECERLI)} olmalı)")
            continue
        secim = bulgular[(bulgular["bulgu_kimlik"] == hedef)
                         | (bulgular["test_kod"] == hedef)]
        if secim.empty:
            hatali.append(f"{istek} (eşleşen bulgu yok)")
            continue
        for r in secim.itertuples():
            yeni.append({
                "kimlik": r.bulgu_kimlik, "test_kod": r.test_kod,
                "sirket_kod": r.sirket_kod, "donem": r.donem,
                "nesne": r.nesne, "tutar_eur": r.tutar_eur, "onem": r.onem,
                "etiket": etiket, "gerekce": "",
                "zaman": datetime.now().isoformat(timespec="seconds"),
            })

    for h in hatali:
        g.uyari(f"Atlandı: {h}")
    if not yeni:
        g.hata("Hiçbir etiket uygulanmadı.")
        g.bitir({"eklenen": 0})
        return

    yeni_df = pd.DataFrame(yeni)
    if not etiketler.empty:
        # Aynı bulgu yeniden etiketlenirse son karar geçerlidir.
        etiketler = etiketler[~etiketler["kimlik"].isin(yeni_df["kimlik"])]
    birlesik = pd.concat([etiketler, yeni_df], ignore_index=True)
    CIKTI_DIZIN.mkdir(parents=True, exist_ok=True)
    birlesik.to_csv(ETIKET_DOSYASI, index=False, encoding="utf-8-sig")

    g.iyi(f"{len(yeni)} bulgu etiketlendi. Toplam etiket: {len(birlesik)}")
    durum_yaz(g, birlesik)
    g.bitir({"eklenen": len(yeni), "toplam": len(birlesik)})


def durum_yaz(g: Gunluk, etiketler: pd.DataFrame | None = None):
    if etiketler is None:
        etiketler = etiketleri_oku()
    if etiketler.empty:
        g.bilgi("Henüz etiket yok.")
        g.bilgi(f"Bulgu triyajı modeli için en az {ASGARI_ETIKET} etiket "
                f"gerekiyor; altında eğitilen bir model, etiketleyicinin "
                f"o günkü kararlarını ezberler.")
        return

    dagilim = etiketler["etiket"].value_counts().to_dict()
    tablo_yaz("Etiket dağılımı",
              [[k, str(v)] for k, v in sorted(dagilim.items())],
              ["Etiket", "Adet"])
    kullanilabilir = int(sum(v for k, v in dagilim.items()
                             if k in ("gercek", "gurultu")))
    g.bilgi(f"Model eğitimi için kullanılabilir etiket: {kullanilabilir} / "
            f"{ASGARI_ETIKET}")
    if kullanilabilir < ASGARI_ETIKET:
        g.uyari(f"Yetersiz. {ASGARI_ETIKET - kullanilabilir} etiket daha "
                f"gerekiyor. Model bu eşiğin altında EĞİTİLMEZ.")
    else:
        az = min(dagilim.get("gercek", 0), dagilim.get("gurultu", 0))
        if az < 30:
            g.uyari(f"Sınıflardan biri yalnızca {az} örnekli. Dengesiz "
                    f"veride duyarlılık düşer; daha çok azınlık örneği "
                    f"gerekir.")
        else:
            g.iyi("Eşik aşıldı, bulgu triyajı modeli eğitilebilir.")


def main():
    g = Gunluk("bulgu_etiketle")
    argv = sys.argv[1:]
    if "--etiket" in argv:
        i = argv.index("--etiket")
        etiketle(g, argv[i + 1:])
    elif "--durum" in argv:
        durum_yaz(g)
        g.bitir({"durum": "ozet"})
    else:
        listele(g)


if __name__ == "__main__":
    main()
