# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ [2] EŞLE: yerel hesap planı → grup hesap planı köprüsü.

GÖREV
  Üç farklı yerel hesap planındaki (VUK Tek Düzen, SKR04, UK COA) kodları
  tek bir IFRS sunum planına indirger. Eşleşmeyenleri ATMAZ, askı hesabına
  alır, çünkü atılan satır bilançoyu yine denk gösterir ve hata görünmez olur.

NEDEN EN TEHLİKELİ ADIM
  Bir yerel hesap eşleşmezse ve satır düşürülürse: konsolide tablo denk çıkar,
  toplamlar makul görünür, ama o hesabın tutarı yok olmuştur. Ne bir hata mesajı
  vardır ne de bir denksizlik. Bu yüzden burada üç şey birden yapılır:
    1. Eşleşmeyen satır askıya (9999) alınır, tutar kaybolmaz
    2. Askıdaki tutar ve etkilediği dönem sayısı raporlanır
    3. Yapay zekâ katmanı açıksa her eşleşmeyen hesap için bir grup hesabı
       ÖNERİLİR, öneri doğrudan uygulanmaz, insan onayına gider

ÇALIŞTIRMA
  py src/esle.py
ÇIKTI
  veri/ara/mizan_eslenmis.csv · butce_eslenmis.csv · eslesmeyenler.csv
  cikti/hesap_eslesme_onerisi.csv  (zeka katmanı açıksa)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gunluk import Gunluk, para, tablo_yaz            # noqa: E402
from sema import ARA_DIZIN, CIKTI_DIZIN, yukle        # noqa: E402
from zeka import Zeka                                  # noqa: E402


def eslestir(df: pd.DataFrame, y, g: Gunluk, etiket: str) -> pd.DataFrame:
    """Her satıra grup_kod, grup_ad, tur, kalem ekler.
    Eşleşmeyenler askı hesabına alınır ve işaretlenir."""
    aski = y.aski_hesabi()
    plan_sozluk = {k: s.hesap_plani for k, s in y.sirketler.items()}

    df = df.copy()
    df["hesap_plani"] = df["sirket_kod"].map(plan_sozluk)
    df["grup_kod"] = [
        y.grup_kodu(plan, kod) or aski
        for plan, kod in zip(df["hesap_plani"], df["yerel_hesap_kod"])
    ]
    df["eslesti"] = df["grup_kod"] != aski
    df["grup_ad"] = df["grup_kod"].map(lambda k: y.grup_hesaplari[k]["ad"])
    df["tur"] = df["grup_kod"].map(lambda k: y.grup_hesaplari[k]["tur"])
    df["kalem"] = df["grup_kod"].map(lambda k: y.grup_hesaplari[k]["kalem"])
    df["elimine"] = df["grup_kod"].map(
        lambda k: bool(y.grup_hesaplari[k].get("elimine")))

    n_yok = int((~df["eslesti"]).sum())
    if n_yok:
        g.uyari(f"{etiket}: {n_yok:,} satır eşleşmedi, askı hesabına ({aski}) alındı")
    else:
        g.iyi(f"{etiket}: tüm satırlar eşleşti")
    g.iz("eslestirildi", tablo=etiket, satir=len(df), eslesmeyen=n_yok)
    return df


def eslesmeyen_ozeti(mizan: pd.DataFrame, y) -> pd.DataFrame:
    """Eşleşmeyen hesapları hesap bazında özetler, insanın bakacağı liste."""
    yok = mizan[~mizan["eslesti"]]
    if yok.empty:
        return pd.DataFrame(columns=["sirket_kod", "hesap_plani", "yerel_hesap_kod",
                                     "yerel_hesap_ad", "donem_sayisi", "ilk_donem",
                                     "son_donem", "bakiye", "bakiye_eur"])
    satirlar = []
    for (sirket, plan, kod), grup in yok.groupby(
            ["sirket_kod", "hesap_plani", "yerel_hesap_kod"]):
        pb = y.sirketler[sirket].fonksiyonel_para_birimi
        bakiye = grup["bakiye"].sum()
        # Kaba bir büyüklük göstergesi: son dönemin kapanış kuruyla
        son = grup["donem"].max()
        satirlar.append({
            "sirket_kod": sirket, "hesap_plani": plan, "yerel_hesap_kod": kod,
            "yerel_hesap_ad": grup["yerel_hesap_ad"].iloc[0],
            "donem_sayisi": grup["donem"].nunique(),
            "ilk_donem": grup["donem"].min(), "son_donem": son,
            "bakiye": round(bakiye, 2),
            "bakiye_eur": round(bakiye * y.kur(son, pb, "kapanis"), 2),
        })
    return pd.DataFrame(satirlar).sort_values("bakiye_eur",
                                              key=abs, ascending=False)


def oneri_uret(eslesmeyenler: pd.DataFrame, y, z: Zeka, g: Gunluk) -> pd.DataFrame | None:
    """Eşleşmeyen her hesap için grup hesabı önerisi ister.
    Öneri UYGULANMAZ, csv'ye yazılır, insan onaylayıp
    yapilandirma/hesap_eslesme.csv'ye taşır."""
    if eslesmeyenler.empty:
        return None
    if not z.aktif:
        g.bilgi(f"Eşleme önerisi atlandı, {z.neden}")
        g.bilgi("  Anahtar eklenirse bu hesaplar için otomatik öneri üretilir.")
        return None

    girdi = eslesmeyenler.rename(columns={"bakiye": "bakiye"}).to_dict("records")
    plan = [{"kod": k, "ad": h["ad"], "tur": h["tur"], "kalem": h["kalem"]}
            for k, h in y.grup_hesaplari.items() if not h.get("aski")]
    oneriler = z.esleme_oner(girdi, plan)
    if not oneriler:
        g.uyari("Zeka katmanı öneri üretemedi.")
        return None

    df = pd.DataFrame(oneriler)
    # Önerilen kodun gerçekten var olduğunu doğrula. LLM uydurmuş olabilir
    df["gecerli_kod"] = df["onerilen_grup_kod"].isin(y.grup_hesaplari)
    uydurma = df[~df["gecerli_kod"]]
    if not uydurma.empty:
        g.uyari(f"{len(uydurma)} öneri grup planında olmayan koda işaret etti, "
                f"işaretlendi: {list(uydurma['onerilen_grup_kod'])}")
    df = df.merge(
        eslesmeyenler[["yerel_hesap_kod", "sirket_kod", "yerel_hesap_ad",
                       "hesap_plani", "bakiye_eur"]],
        left_on="yerel_kod", right_on="yerel_hesap_kod", how="left")
    return df


def main():
    g = Gunluk("esle")
    y = yukle()
    z = Zeka(y=y, g=g)
    g.bilgi(y.ozet())
    g.bilgi(z.ozet())

    gerekli = ARA_DIZIN / "mizan.csv"
    if not gerekli.exists():
        g.hata(f"{gerekli} yok. Önce: py src/topla.py")
        g.bitir({"durum": "girdi_yok"})
        return

    mizan = pd.read_csv(ARA_DIZIN / "mizan.csv",
                        dtype={"donem": str, "yerel_hesap_kod": str})
    butce = pd.read_csv(ARA_DIZIN / "butce.csv",
                        dtype={"donem": str, "yerel_hesap_kod": str})

    mizan = eslestir(mizan, y, g, "mizan")
    butce = eslestir(butce, y, g, "bütçe")

    mizan.to_csv(ARA_DIZIN / "mizan_eslenmis.csv", index=False, encoding="utf-8")
    butce.to_csv(ARA_DIZIN / "butce_eslenmis.csv", index=False, encoding="utf-8")

    # ---- Eşleşme kapsaması ----
    ozet = []
    for kod, s in y.sirketler.items():
        alt = mizan[mizan["sirket_kod"] == kod]
        hesap = alt["yerel_hesap_kod"].nunique()
        hesap_yok = alt[~alt["eslesti"]]["yerel_hesap_kod"].nunique()
        borc = alt["borc"].sum()
        borc_yok = alt[~alt["eslesti"]]["borc"].sum()
        ozet.append([kod, s.hesap_plani, f"{hesap:,}", f"{hesap_yok:,}",
                     f"%{(1 - hesap_yok / hesap) * 100:.1f}" if hesap else "-",
                     para(borc_yok, 0),
                     f"%{borc_yok / borc * 100:.3f}" if borc else "-"])
    tablo_yaz("Eşleşme kapsaması", ozet,
              ["Şirket", "Plan", "Hesap", "Eşleşmeyen", "Kapsama",
               "Askıdaki borç", "Payı"])

    eslesmeyenler = eslesmeyen_ozeti(mizan, y)
    eslesmeyenler.to_csv(ARA_DIZIN / "eslesmeyenler.csv", index=False,
                         encoding="utf-8-sig")

    if not eslesmeyenler.empty:
        tablo_yaz("Askıdaki hesaplar, kapanış imzalanmadan çözülmeli",
                  [[r.sirket_kod, r.hesap_plani, r.yerel_hesap_kod,
                    str(r.yerel_hesap_ad)[:34], r.donem_sayisi,
                    f"{r.ilk_donem}→{r.son_donem}", para(r.bakiye_eur, 0)]
                   for r in eslesmeyenler.itertuples()],
                  ["Şirket", "Plan", "Kod", "Ad", "Dönem", "Aralık", "Bakiye EUR"])

        oneri = oneri_uret(eslesmeyenler, y, z, g)
        if oneri is not None:
            yol = CIKTI_DIZIN / "hesap_eslesme_onerisi.csv"
            oneri.to_csv(yol, index=False, encoding="utf-8-sig")
            tablo_yaz("Yapay zekâ eşleme önerisi (UYGULANMADI, insan onayı bekler)",
                      [[r.yerel_kod, str(r.yerel_hesap_ad)[:26],
                        r.onerilen_grup_kod,
                        y.grup_hesaplari.get(r.onerilen_grup_kod, {}).get("ad", "?")[:26],
                        r.guven, str(r.gerekce)[:52]]
                       for r in oneri.itertuples()],
                      ["Yerel", "Yerel ad", "Öneri", "Grup hesabı", "Güven", "Gerekçe"])
            g.bilgi(f"Öneri dosyası: {yol}")
            g.bilgi("  Onaylarsan satırları yapilandirma/hesap_eslesme.csv'ye taşı "
                    "ve py src/esle.py'yi tekrar çalıştır.")

    # ---- Grup hesabı bazında toplam (gözle kontrol) ----
    son_donem = mizan["donem"].max()
    son = mizan[mizan["donem"] == son_donem]
    kalem_ozet = (son.groupby(["tur", "kalem"], as_index=False)["bakiye"]
                    .agg(["sum", "count"]).reset_index())
    g.bilgi(f"\n{son_donem} döneminde {len(son):,} mizan satırı, "
            f"{son['grup_kod'].nunique()} grup hesabına indi "
            f"({son['yerel_hesap_kod'].nunique()} yerel hesaptan).")

    g.bitir({"mizan_satir": len(mizan), "butce_satir": len(butce),
             "eslesmeyen_hesap": len(eslesmeyenler),
             "zeka": z.istatistik})


if __name__ == "__main__":
    main()
