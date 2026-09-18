# -*- coding: utf-8 -*-
# MizanKöprü — çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ — [5] SAPMA: bütçe-fiili köprüsü ve bileşen ayrıştırması.

SORU
  "Hedefin altında kaldık" cümlesi tek başına hiçbir şey söylemez.
  Fiyatı mı tutturamadık, adedi mi satamadık, ürün karışımı mı bozuldu,
  yoksa hiçbiri olmadı da sadece kur mu değişti? Dördü dört ayrı sorumluluk,
  dört ayrı aksiyon. Bu modül tek bir sapmayı bu dörde ayırır.

AYRIŞTIRMA (matematiksel olarak tam — artık terim yok)

  Yerel para cinsinden, ürün bazında:
    Fiyat etkisi   = Σ (P_fiili,i − P_bütçe,i) × Q_fiili,i
    Karışım etkisi = Σ [Q_fiili,i − ΣQ_fiili × W_bütçe,i] × P_bütçe,i
    Hacim etkisi   = (ΣQ_fiili − ΣQ_bütçe) × P_bütçe_ortalama
      W_bütçe,i = ürünün bütçedeki miktar payı
    Toplam = Fiyat + Karışım + Hacim   (özdeşlik, aşağıda sayısal olarak doğrulanır)

  Sunum para birimine geçerken:
    Kur etkisi = Fiili_yerel × (gerçekleşen_kur − bütçe_kuru)
    Toplam EUR sapması = Kur etkisi + Yerel sapma × bütçe_kuru

  Her ay kendi kuruyla hesaplanır, sonra toplanır. Yıllık tek kur kullanmak
  enflasyonist bir para biriminde ayrıştırmayı bozar.

LLM'İN ROLÜ
  Hiçbiri. Yukarıdaki dört rakamı motor üretir. Yapay zekâ yalnızca hazır
  tabloyu okuyup finans diline çevirir (zeka.sapma_yorumla).

ÇALIŞTIRMA
  py src/sapma.py
ÇIKTI
  cikti/sapma_koprusu.csv · cikti/sapma_kalem.csv · cikti/sapma_yorumu.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gunluk import Gunluk, para, tablo_yaz          # noqa: E402
from sema import ARA_DIZIN, CIKTI_DIZIN, yukle      # noqa: E402
from zeka import Zeka                                # noqa: E402


def ayristir_bir_donem(fiili: pd.DataFrame, butce: pd.DataFrame) -> dict:
    """Tek bir şirket-dönem için fiyat/karışım/hacim ayrıştırması (yerel para).

    fiili ve butce: urun_kod, miktar, birim_fiyat kolonlarını taşır.
    Dönen sözlükteki üç bileşenin toplamı, toplam sapmaya birebir eşittir.
    """
    f = fiili.set_index("urun_kod")
    b = butce.set_index("urun_kod")
    urunler = sorted(set(f.index) | set(b.index))

    Qf = {u: float(f["miktar"].get(u, 0.0)) for u in urunler}
    Qb = {u: float(b["miktar"].get(u, 0.0)) for u in urunler}
    Pf = {u: float(f["birim_fiyat"].get(u, 0.0)) for u in urunler}
    Pb = {u: float(b["birim_fiyat"].get(u, 0.0)) for u in urunler}
    # Bütçede olmayan yeni ürün: bütçe fiyatı yoksa fiili fiyat referans alınır,
    # böylece o ürünün tamamı hacim/karışım etkisine yazılır, fiyat etkisine değil.
    for u in urunler:
        if Pb[u] == 0.0:
            Pb[u] = Pf[u]

    Qf_top, Qb_top = sum(Qf.values()), sum(Qb.values())
    butce_tutar = sum(Qb[u] * Pb[u] for u in urunler)
    fiili_tutar = sum(Qf[u] * Pf[u] for u in urunler)
    Pb_ort = (butce_tutar / Qb_top) if Qb_top else 0.0

    fiyat = sum((Pf[u] - Pb[u]) * Qf[u] for u in urunler)
    karisim = sum((Qf[u] - Qf_top * (Qb[u] / Qb_top if Qb_top else 0.0)) * Pb[u]
                  for u in urunler)
    hacim = (Qf_top - Qb_top) * Pb_ort

    return {
        "butce_yerel": butce_tutar, "fiili_yerel": fiili_tutar,
        "miktar_butce": Qb_top, "miktar_fiili": Qf_top,
        "fiyat_etkisi": fiyat, "karisim_etkisi": karisim, "hacim_etkisi": hacim,
        "artik": fiili_tutar - butce_tutar - (fiyat + karisim + hacim),
    }


def koprü_kur(y, kayit: dict, donem: str, sirket: str) -> dict:
    """Yerel bileşenleri sunum para birimine taşır ve kur etkisini ekler."""
    pb = y.sirketler[sirket].fonksiyonel_para_birimi
    kur_b = y.kur(donem, pb, "butce")
    kur_g = y.kur(donem, pb, "ortalama")
    yerel_sapma = kayit["fiili_yerel"] - kayit["butce_yerel"]
    return {
        **kayit,
        "kur_butce": kur_b, "kur_gercek": kur_g,
        "butce_eur": kayit["butce_yerel"] * kur_b,
        "fiili_eur": kayit["fiili_yerel"] * kur_g,
        "fiili_eur_sabit_kur": kayit["fiili_yerel"] * kur_b,
        "fiyat_eur": kayit["fiyat_etkisi"] * kur_b,
        "karisim_eur": kayit["karisim_etkisi"] * kur_b,
        "hacim_eur": kayit["hacim_etkisi"] * kur_b,
        "kur_etkisi_eur": kayit["fiili_yerel"] * (kur_g - kur_b),
        "yerel_sapma": yerel_sapma,
    }


def koprü_kur_dogrula(df: pd.DataFrame, g: Gunluk) -> bool:
    """Ayrıştırmanın özdeşliğini sayısal olarak sınar.
    Bir sapma köprüsünün ilk şartı, toplamının tutmasıdır."""
    yerel_artik = df["artik"].abs().max()
    eur_toplam = (df["butce_eur"] + df["fiyat_eur"] + df["karisim_eur"]
                  + df["hacim_eur"] + df["kur_etkisi_eur"])
    eur_artik = (eur_toplam - df["fiili_eur"]).abs().max()
    tamam = yerel_artik < 0.5 and eur_artik < 0.5
    if tamam:
        g.iyi(f"Ayrıştırma özdeşliği doğrulandı — en büyük artık: "
              f"yerel {yerel_artik:.4f}, EUR {eur_artik:.4f}")
    else:
        g.hata(f"AYRIŞTIRMA TUTMUYOR — yerel artık {yerel_artik:.2f}, "
               f"EUR artık {eur_artik:.2f}. Köprü güvenilmez.")
    return tamam


def kalem_sapmasi(y, cevrilmis: pd.DataFrame, butce: pd.DataFrame) -> pd.DataFrame:
    """Gelir tablosu kalemi bazında bütçe-fiili, kur etkisi ayrıştırılmış."""
    son = y.donemler()[-1]
    gt = cevrilmis[(cevrilmis["tur"] == "G")].copy()

    fiili = (gt.groupby(["sirket_kod", "donem", "grup_kod"], as_index=False)
               .agg(yerel=("bakiye_aylik", "sum")))
    b = butce.copy()
    butce_ozet = (b.groupby(["sirket_kod", "donem", "grup_kod"], as_index=False)
                   .agg(yerel_b=("tutar", "sum")))

    birlesik = fiili.merge(butce_ozet, on=["sirket_kod", "donem", "grup_kod"],
                           how="outer").fillna({"yerel": 0.0, "yerel_b": 0.0})
    birlesik = birlesik[birlesik["grup_kod"].isin(y.grup_hesaplari)]

    satirlar = []
    for r in birlesik.itertuples():
        h = y.grup_hesaplari[r.grup_kod]
        isaret = -1 if h["yon"] == -1 else 1
        pb = y.sirketler[r.sirket_kod].fonksiyonel_para_birimi
        kur_b = y.kur(r.donem, pb, "butce")
        kur_g = y.kur(r.donem, pb, "ortalama")
        # Bütçe dosyası tutarları mutlak yazar; sunum işareti grup planından gelir
        f_yerel = r.yerel * isaret
        b_yerel = r.yerel_b
        satirlar.append({
            "sirket_kod": r.sirket_kod, "donem": r.donem, "grup_kod": r.grup_kod,
            "grup_ad": h["ad"], "kalem": h["kalem"],
            "butce_eur": b_yerel * kur_b,
            "fiili_eur": f_yerel * kur_g,
            "fiili_eur_sabit_kur": f_yerel * kur_b,
            "kur_etkisi_eur": f_yerel * (kur_g - kur_b),
            "is_sapmasi_eur": (f_yerel - b_yerel) * kur_b,
        })
    df = pd.DataFrame(satirlar)
    df["toplam_sapma_eur"] = df["fiili_eur"] - df["butce_eur"]
    return df


def main():
    g = Gunluk("sapma")
    y = yukle()
    z = Zeka(y=y, g=g)
    g.bilgi(y.ozet())

    kaynak = ARA_DIZIN / "satis.csv"
    if not kaynak.exists():
        g.hata(f"{kaynak} yok. Önce: py src/topla.py")
        g.bitir({"durum": "girdi_yok"})
        return

    satis = pd.read_csv(kaynak, dtype={"donem": str, "urun_kod": str})
    cevrilmis = pd.read_csv(ARA_DIZIN / "cevrilmis.csv",
                            dtype={"donem": str, "grup_kod": str})
    butce = pd.read_csv(ARA_DIZIN / "butce_eslenmis.csv",
                        dtype={"donem": str, "grup_kod": str})
    g.bilgi(f"{len(satis):,} satış satırı · "
            f"{satis['senaryo'].value_counts().to_dict()}")

    # ---- Şirket-dönem bazında ayrıştırma ----
    kayitlar = []
    for (sirket, donem), grup in satis.groupby(["sirket_kod", "donem"]):
        f = grup[grup["senaryo"] == "fiili"]
        b = grup[grup["senaryo"] == "butce"]
        if f.empty and b.empty:
            continue
        ham = ayristir_bir_donem(f, b)
        kayitlar.append({"sirket_kod": sirket, "donem": donem,
                         **koprü_kur(y, ham, donem, sirket)})
    kopru = pd.DataFrame(kayitlar)
    kopru.to_csv(CIKTI_DIZIN / "sapma_koprusu.csv", index=False, encoding="utf-8-sig")

    if not koprü_kur_dogrula(kopru, g):
        g.uyari("Köprü doğrulaması başarısız — sonuçlar yayımlanmamalı.")

    # ---- Şirket bazında yıllık köprü ----
    ozet = kopru.groupby("sirket_kod", as_index=False).agg(
        butce_eur=("butce_eur", "sum"), fiili_eur=("fiili_eur", "sum"),
        fiyat=("fiyat_eur", "sum"), karisim=("karisim_eur", "sum"),
        hacim=("hacim_eur", "sum"), kur=("kur_etkisi_eur", "sum"),
        miktar_b=("miktar_butce", "sum"), miktar_f=("miktar_fiili", "sum"),
        fiili_yerel=("fiili_yerel", "sum"), butce_yerel=("butce_yerel", "sum"))

    tablo_yaz("HASILAT SAPMA KÖPRÜSÜ — 2025 yılı, şirket bazında (EUR)",
              [[r.sirket_kod, para(r.butce_eur, 0), para(r.fiyat, 0),
                para(r.karisim, 0), para(r.hacim, 0), para(r.kur, 0),
                para(r.fiili_eur, 0),
                f"{(r.fiili_eur/r.butce_eur - 1)*100:+.1f}%"]
               for r in ozet.itertuples()],
              ["Şirket", "Bütçe", "+Fiyat", "+Karışım", "+Hacim", "+Kur",
               "= Fiili", "Sapma"])

    t = ozet[["butce_eur", "fiyat", "karisim", "hacim", "kur", "fiili_eur"]].sum()
    g.bilgi("")
    tablo_yaz("GRUP TOPLAMI — köprü",
              [["Bütçe (bütçe kuruyla)", para(t["butce_eur"], 0), ""],
               ["  + Fiyat etkisi", para(t["fiyat"], 0),
                f"{t['fiyat']/t['butce_eur']*100:+.1f}%"],
               ["  + Karışım etkisi", para(t["karisim"], 0),
                f"{t['karisim']/t['butce_eur']*100:+.1f}%"],
               ["  + Hacim etkisi", para(t["hacim"], 0),
                f"{t['hacim']/t['butce_eur']*100:+.1f}%"],
               ["  = Sabit kurda fiili",
                para(t["butce_eur"] + t["fiyat"] + t["karisim"] + t["hacim"], 0), ""],
               ["  + Kur etkisi", para(t["kur"], 0),
                f"{t['kur']/t['butce_eur']*100:+.1f}%"],
               ["Fiili (gerçekleşen kurla)", para(t["fiili_eur"], 0),
                f"{(t['fiili_eur']/t['butce_eur']-1)*100:+.1f}%"]],
              ["Kalem", "EUR", "Bütçeye oran"])

    # ---- Yerel para vs sunum para birimi çelişkisi ----
    celiski = []
    for r in ozet.itertuples():
        pb = y.sirketler[r.sirket_kod].fonksiyonel_para_birimi
        yerel_sapma = (r.fiili_yerel / r.butce_yerel - 1) * 100 if r.butce_yerel else 0
        eur_sapma = (r.fiili_eur / r.butce_eur - 1) * 100 if r.butce_eur else 0
        miktar_sapma = (r.miktar_f / r.miktar_b - 1) * 100 if r.miktar_b else 0
        celiski.append([r.sirket_kod, pb, f"{miktar_sapma:+.1f}%",
                        f"{yerel_sapma:+.1f}%", f"{eur_sapma:+.1f}%",
                        "ÇELİŞKİ" if yerel_sapma > 0 > eur_sapma else ""])
    tablo_yaz("Aynı şirket, iki para birimi, iki farklı hikâye", celiski,
              ["Şirket", "PB", "Miktar Δ", "Yerel ciro Δ", "EUR ciro Δ", ""])

    # ---- Gelir tablosu kalemi bazında sapma ----
    kalem = kalem_sapmasi(y, cevrilmis, butce)
    kalem.to_csv(CIKTI_DIZIN / "sapma_kalem.csv", index=False, encoding="utf-8-sig")
    kalem_ozet = (kalem.groupby("kalem", as_index=False)
                       .agg(butce=("butce_eur", "sum"), fiili=("fiili_eur", "sum"),
                            is_sapmasi=("is_sapmasi_eur", "sum"),
                            kur=("kur_etkisi_eur", "sum"),
                            toplam=("toplam_sapma_eur", "sum")))
    sira = ["Hasılat", "Satışların maliyeti", "Faaliyet giderleri",
            "Finansal gelir/gider", "Vergi"]
    kalem_ozet["_s"] = kalem_ozet["kalem"].map({k: i for i, k in enumerate(sira)})
    kalem_ozet = kalem_ozet.sort_values("_s").dropna(subset=["_s"])
    tablo_yaz("GELİR TABLOSU SAPMASI — kur etkisi ayrıştırılmış (EUR)",
              [[r.kalem, para(r.butce, 0), para(r.fiili, 0), para(r.toplam, 0),
                para(r.is_sapmasi, 0), para(r.kur, 0)]
               for r in kalem_ozet.itertuples()],
              ["Kalem", "Bütçe", "Fiili", "Toplam sapma", "İş sapması", "Kur etkisi"])

    # ---- Mutabakat: köprü ile gelir tablosu neden farklı? ----
    # Köprü satış detayından (brüt fatura tutarı), gelir tablosu mizandan gelir.
    # İkisi arasındaki fark tesadüf değildir; açıklanmadan iki rakam yan yana
    # sunulamaz. Fark genellikle iade/iskontonun hasılat hesabına doğrudan
    # yazılmasından doğar — bu aynı zamanda bir sınıflandırma bulgusudur.
    gt_hasilat = cevrilmis[(cevrilmis["tur"] == "G")
                           & (cevrilmis["kalem"] == "Hasılat")]
    mizan_hasilat = -gt_hasilat["eur_aylik"].sum()
    kopru_hasilat = float(t["fiili_eur"])
    fark = kopru_hasilat - mizan_hasilat
    iskonto = -cevrilmis[cevrilmis["grup_kod"] == "4090"]["eur_aylik"].sum()
    tablo_yaz("MUTABAKAT — satış detayı ile gelir tablosu arasındaki fark",
              [["Köprü fiili (satış detayı, brüt fatura)", para(kopru_hasilat, 0), ""],
               ["Gelir tablosu hasılatı (mizan)", para(mizan_hasilat, 0), ""],
               ["FARK", para(fark, 0),
                f"%{abs(fark)/mizan_hasilat*100:.1f}" if mizan_hasilat else ""],
               ["  bunun 4090 iade/iskonto hesabından", para(iskonto, 0), ""],
               ["  hasılat hesabına DOĞRUDAN yazılan iade",
                para(fark - iskonto, 0), "sınıflandırma hatası — bkz. K11"]],
              ["Kalem", "EUR", "Not"])
    if abs(fark - iskonto) > 1000:
        g.uyari(f"{para(fark - iskonto, 0)} EUR tutarındaki iade, 4090 yerine "
                f"doğrudan hasılat hesabına yazılmış. İki tablo bu yüzden "
                f"farklı; K11 bunu ters bakiye olarak da işaretledi.")

    # ---- Yapay zekâ yorumu ----
    if z.aktif and z.ayar.get("gorevler", {}).get("sapma_yorumla", True):
        metin = ["HASILAT KÖPRÜSÜ (grup, 2025, EUR):",
                 f"  Bütçe (bütçe kuru EUR/TRY 38,00 sabit): {t['butce_eur']:,.0f}",
                 f"  Fiyat etkisi: {t['fiyat']:+,.0f}",
                 f"  Karışım etkisi: {t['karisim']:+,.0f}",
                 f"  Hacim etkisi: {t['hacim']:+,.0f}",
                 f"  Kur etkisi: {t['kur']:+,.0f}",
                 f"  Fiili: {t['fiili_eur']:,.0f}",
                 "", "ŞİRKET BAZINDA (miktar Δ / yerel ciro Δ / EUR ciro Δ):"]
        for satir in celiski:
            metin.append(f"  {satir[0]} ({satir[1]}): {satir[2]} / {satir[3]} / {satir[4]}"
                         + ("  ← yerelde hedef üstü, EUR'da hedef altı" if satir[5] else ""))
        metin += ["", "GELİR TABLOSU (bütçe / fiili / iş sapması / kur etkisi, EUR):"]
        for r in kalem_ozet.itertuples():
            metin.append(f"  {r.kalem}: {r.butce:,.0f} / {r.fiili:,.0f} / "
                         f"{r.is_sapmasi:+,.0f} / {r.kur:+,.0f}")
        metin.append("")
        metin.append("NOT: Gerçekleşen EUR/TRY yıl sonunda 50,60 oldu; bütçe 38,00 "
                     "varsaymıştı. TR şirketlerinde enflasyon fiyatları bütçelenenden "
                     "hızlı artırdı, satılan adet ise düştü.")
        yorum = z.sapma_yorumla("\n".join(metin))
        if yorum:
            yol = CIKTI_DIZIN / "sapma_yorumu.md"
            yol.write_text(f"# Sapma yorumu — 2025\n\n{yorum}\n", encoding="utf-8")
            g.bilgi("\n" + "─" * 74)
            print(yorum)
            g.bilgi("─" * 74)
            g.bilgi(f"Yorum dosyası: {yol}")
    else:
        g.bilgi(f"Sapma yorumu atlandı — {z.neden or 'yapılandırmada kapalı'}")

    g.bitir({"kopru_satir": len(kopru), "kalem_satir": len(kalem),
             "zeka": z.istatistik})


if __name__ == "__main__":
    main()
