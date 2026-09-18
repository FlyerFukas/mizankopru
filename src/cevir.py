# -*- coding: utf-8 -*-
"""
MİZANKÖPRÜ — [3] ÇEVİR: IAS 21 kur çevrimi ve konsolidasyon.

IAS 21 KURALI
  Bilanço kalemleri   → dönem sonu (KAPANIŞ) kuru
  Gelir tablosu kalemleri → işlem tarihindeki kur, pratikte dönem ORTALAMA kuru
  Aradaki fark        → özkaynakta "yabancı para çevrim farkları" (CTA)

NEDEN AYLIK ÇEVİRMEK ZORUNLU
  Mizan YTD gelir. Gelir tablosu kalemini YTD hâliyle tek bir kurla çevirmek,
  EUR/TRY'nin 36,80'den 50,60'a gittiği bir yılda Ocak'ta kazanılan geliri de
  Aralık kuruyla çevirir — ciroyu sistematik olarak küçültür. Doğrusu:
  her ayın kendi hareketini o ayın ortalama kuruyla çevirip biriktirmek.
  Bu modül YTD'den aylık hareketi türetip öyle çevirir.

ÜÇ SENARYO
  eur_gercek : fiili tutar, gerçekleşen kurla        → gerçek sonuç
  eur_sabit  : fiili tutar, BÜTÇE kuruyla            → kur etkisi ayıklanmış
  Bütçe zaten bütçe kuruyla çevrilir.
  Kur etkisi   = eur_gercek - eur_sabit
  İş performansı = eur_sabit - bütçe
  Bu ayrım olmadan "hedefin altında kaldık" cümlesi kimin sorumluluğunu
  gösterdiğini söyleyemez.

ÇALIŞTIRMA
  py src/cevir.py
ÇIKTI
  veri/ara/cevrilmis.csv (şirket bazında) · konsolide.csv (grup)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gunluk import Gunluk, para, tablo_yaz          # noqa: E402
from sema import ARA_DIZIN, yukle                    # noqa: E402

CEVRIM_FARKI_HESABI = "3090"


def aylik_harekete_cevir(mizan: pd.DataFrame, y, g: Gunluk) -> pd.DataFrame:
    """YTD mizandan aylık hareketi türetir.

    Grup hesabı bazında toplar (bir grup hesabına birden çok yerel hesap
    eşlenebilir), sonra dönem sırasına göre fark alır. Bir dönem hiç
    gelmemişse (TR02 Kasım gibi) o dönem atlanır ve hareket bir sonraki
    döneme birikir — bu doğru davranıştır, YTD kümülatiftir; ama o ayın
    ayrı analizi yapılamaz, K10 bunu bulgu olarak yazar."""
    donemler = y.donemler()
    ozet = (mizan.groupby(["sirket_kod", "donem", "grup_kod"], as_index=False)
                 .agg(borc=("borc", "sum"), alacak=("alacak", "sum"),
                      bakiye=("bakiye", "sum")))

    parcalar = []
    for (sirket, grup_kod), alt in ozet.groupby(["sirket_kod", "grup_kod"]):
        s = alt.set_index("donem").reindex(donemler)
        s["sirket_kod"] = sirket
        s["grup_kod"] = grup_kod
        gelmis = s["bakiye"].notna()
        # Gelmeyen dönemi bir öncekiyle doldur ki fark 0 çıksın, hareket
        # bir sonraki gelen döneme biriksin
        s[["borc", "alacak", "bakiye"]] = s[["borc", "alacak", "bakiye"]].ffill().fillna(0.0)
        s["veri_var"] = gelmis.values
        s["bakiye_aylik"] = s["bakiye"].diff().fillna(s["bakiye"])
        parcalar.append(s.reset_index(names="donem"))

    df = pd.concat(parcalar, ignore_index=True)
    df = df.rename(columns={"bakiye": "bakiye_ytd"})
    # Hiç hareket görmemiş satırları at
    return df[(df["bakiye_ytd"].abs() > 0.005) |
              (df["bakiye_aylik"].abs() > 0.005)].copy()


def cevir(df: pd.DataFrame, y, g: Gunluk) -> pd.DataFrame:
    """IAS 21 çevrimi — üç senaryo birden."""
    pb = {k: s.fonksiyonel_para_birimi for k, s in y.sirketler.items()}
    df = df.copy()
    df["para_birimi"] = df["sirket_kod"].map(pb)
    df["tur"] = df["grup_kod"].map(lambda k: y.grup_hesaplari[k]["tur"])
    df["grup_ad"] = df["grup_kod"].map(lambda k: y.grup_hesaplari[k]["ad"])
    df["kalem"] = df["grup_kod"].map(lambda k: y.grup_hesaplari[k]["kalem"])
    df["elimine"] = df["grup_kod"].map(
        lambda k: bool(y.grup_hesaplari[k].get("elimine")))
    df["kur_tipi"] = df["tur"].map({"B": "kapanis", "G": "ortalama"})

    df["kur_gercek"] = [y.kur(d, p, t) for d, p, t
                        in zip(df["donem"], df["para_birimi"], df["kur_tipi"])]
    df["kur_sabit"] = [y.kur(d, p, "butce") for d, p
                       in zip(df["donem"], df["para_birimi"])]

    bilanco = df["tur"] == "B"

    # Bilanço: YTD bakiye × kapanış kuru
    df.loc[bilanco, "eur_gercek"] = (df.loc[bilanco, "bakiye_ytd"]
                                     * df.loc[bilanco, "kur_gercek"])
    df.loc[bilanco, "eur_sabit"] = (df.loc[bilanco, "bakiye_ytd"]
                                    * df.loc[bilanco, "kur_sabit"])
    df.loc[bilanco, "eur_aylik"] = (df.loc[bilanco, "bakiye_aylik"]
                                    * df.loc[bilanco, "kur_gercek"])

    # Gelir tablosu: AYLIK hareket × o ayın ortalama kuru, sonra biriktir
    gt = ~bilanco
    df.loc[gt, "eur_aylik"] = df.loc[gt, "bakiye_aylik"] * df.loc[gt, "kur_gercek"]
    df.loc[gt, "eur_aylik_sabit"] = (df.loc[gt, "bakiye_aylik"]
                                     * df.loc[gt, "kur_sabit"])
    df = df.sort_values(["sirket_kod", "grup_kod", "donem"])
    for kaynak, hedef in (("eur_aylik", "eur_gercek"),
                          ("eur_aylik_sabit", "eur_sabit")):
        birikmis = (df[gt].groupby(["sirket_kod", "grup_kod"])[kaynak].cumsum())
        df.loc[gt, hedef] = birikmis
    df["eur_aylik_sabit"] = df["eur_aylik_sabit"].fillna(
        df["bakiye_aylik"] * df["kur_sabit"])
    return df


def cevrim_farki_ekle(df: pd.DataFrame, y, g: Gunluk) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Çevrim sonrası bilanço denk gelmez; fark özkaynağa yazılır.

    ÖNEMLİ: yerel mizan zaten denk değilse (UK01'de olduğu gibi) o denksizlik
    çevrim farkıyla karışır. Burada ikisi ayrıştırılır — aksi hâlde bir veri
    hatası 'kur çevrim farkı' adı altında özkaynağa gömülür ve kaybolur."""
    satirlar, rapor = [], []
    for (sirket, donem), alt in df.groupby(["sirket_kod", "donem"]):
        pb = y.sirketler[sirket].fonksiyonel_para_birimi
        kapanis = y.kur(donem, pb, "kapanis")

        yerel_denksizlik = alt["bakiye_ytd"].sum()          # normalde 0
        cevrilmis_toplam = alt["eur_gercek"].sum()
        veri_hatasi_eur = yerel_denksizlik * kapanis
        saf_cevrim_farki = cevrilmis_toplam - veri_hatasi_eur

        rapor.append({
            "sirket_kod": sirket, "donem": donem,
            "yerel_denksizlik": round(yerel_denksizlik, 2),
            "veri_hatasi_eur": round(veri_hatasi_eur, 2),
            "cevrim_farki_eur": round(saf_cevrim_farki, 2),
            "cevrilmis_toplam_eur": round(cevrilmis_toplam, 2),
        })

        if abs(saf_cevrim_farki) > 0.005:
            satirlar.append({
                "sirket_kod": sirket, "donem": donem,
                "grup_kod": CEVRIM_FARKI_HESABI,
                "grup_ad": y.grup_hesaplari[CEVRIM_FARKI_HESABI]["ad"],
                "tur": "B", "kalem": y.grup_hesaplari[CEVRIM_FARKI_HESABI]["kalem"],
                "elimine": False, "para_birimi": pb, "kur_tipi": "hesaplanan",
                "veri_var": True,
                "bakiye_ytd": 0.0, "bakiye_aylik": 0.0,
                "borc": 0.0, "alacak": 0.0,
                "kur_gercek": kapanis, "kur_sabit": y.kur(donem, pb, "butce"),
                "eur_gercek": -saf_cevrim_farki,
                "eur_sabit": 0.0,
                "eur_aylik": 0.0, "eur_aylik_sabit": 0.0,
            })

    if satirlar:
        df = pd.concat([df, pd.DataFrame(satirlar)], ignore_index=True)
        g.iyi(f"{len(satirlar)} şirket-dönem için çevrim farkı "
              f"{CEVRIM_FARKI_HESABI}'a yazıldı")
    return df, pd.DataFrame(rapor)


def konsolide_et(df: pd.DataFrame, y, g: Gunluk) -> pd.DataFrame:
    """Grup konsolidesi: şirketleri topla, grup içi kalemleri elimine et,
    azınlık payını (NCI) ayrı göster."""
    satirlar = []
    for (donem, grup_kod), alt in df.groupby(["donem", "grup_kod"]):
        h = y.grup_hesaplari[grup_kod]
        elimine = bool(h.get("elimine"))
        toplam = alt["eur_gercek"].sum()
        toplam_sabit = alt["eur_sabit"].sum()
        satirlar.append({
            "donem": donem, "grup_kod": grup_kod, "grup_ad": h["ad"],
            "tur": h["tur"], "kalem": h["kalem"], "elimine": elimine,
            "eur_brut": toplam, "eur_sabit_brut": toplam_sabit,
            # Eliminasyona tabi kalemler konsolidede sıfırlanır
            "eur_konsolide": 0.0 if elimine else toplam,
            "eur_sabit_konsolide": 0.0 if elimine else toplam_sabit,
            "sirket_sayisi": alt["sirket_kod"].nunique(),
        })
    k = pd.DataFrame(satirlar)

    # Azınlık payı — tam konsolide edilen ama %100 sahip olunmayan şirketler
    nci = []
    for kod, s in y.sirketler.items():
        if s.sahiplik_orani >= 1.0:
            continue
        alt = df[(df["sirket_kod"] == kod) & (df["tur"] == "G")]
        for donem, grp in alt.groupby("donem"):
            # Gelir tablosu bakiyesi borç-alacak; net kâr = -(toplam)
            net_kar = -grp["eur_gercek"].sum()
            nci.append({"donem": donem, "sirket_kod": kod,
                        "sahiplik_orani": s.sahiplik_orani,
                        "net_kar_eur": round(net_kar, 2),
                        "azinlik_payi_eur": round(net_kar * (1 - s.sahiplik_orani), 2)})
    if nci:
        pd.DataFrame(nci).to_csv(ARA_DIZIN / "azinlik_payi.csv",
                                 index=False, encoding="utf-8")
        toplam_nci = sum(x["azinlik_payi_eur"] for x in nci
                         if x["donem"] == max(d["donem"] for d in nci))
        g.bilgi(f"Azınlık payı hesaplandı: "
                + ", ".join(f"{k} %{(1-y.sirketler[k].sahiplik_orani)*100:.0f}"
                            for k in {x['sirket_kod'] for x in nci})
                + f" · son dönem NCI {para(toplam_nci, 0)} EUR")
    return k


def main():
    g = Gunluk("cevir")
    y = yukle()
    g.bilgi(y.ozet())

    kaynak = ARA_DIZIN / "mizan_eslenmis.csv"
    if not kaynak.exists():
        g.hata(f"{kaynak} yok. Önce: py src/topla.py && py src/esle.py")
        g.bitir({"durum": "girdi_yok"})
        return

    mizan = pd.read_csv(kaynak, dtype={"donem": str, "yerel_hesap_kod": str,
                                       "grup_kod": str})
    g.bilgi(f"{len(mizan):,} eşlenmiş mizan satırı okundu (YTD)")

    aylik = aylik_harekete_cevir(mizan, y, g)
    g.iyi(f"YTD'den aylık hareket türetildi: {len(aylik):,} şirket-dönem-hesap satırı")

    cevrilmis = cevir(aylik, y, g)
    cevrilmis, fark_raporu = cevrim_farki_ekle(cevrilmis, y, g)
    cevrilmis.to_csv(ARA_DIZIN / "cevrilmis.csv", index=False, encoding="utf-8")
    fark_raporu.to_csv(ARA_DIZIN / "cevrim_farki.csv", index=False, encoding="utf-8")

    # ---- Neden aylık çevirmek gerektiğinin kanıtı ----
    g.bilgi("")
    hasilat = cevrilmis[(cevrilmis["kalem"] == "Hasılat")
                        & (cevrilmis["donem"] == y.donemler()[-1])]
    kanit = []
    for kod, s in y.sirketler.items():
        alt = hasilat[hasilat["sirket_kod"] == kod]
        if alt.empty:
            continue
        yerel_ytd = -alt["bakiye_ytd"].sum()
        dogru = -alt["eur_gercek"].sum()
        pb = s.fonksiyonel_para_birimi
        yanlis = yerel_ytd * y.kur(y.donemler()[-1], pb, "ortalama")
        kanit.append([kod, pb, para(yerel_ytd, 0), para(dogru, 0), para(yanlis, 0),
                      f"{(yanlis/dogru - 1)*100:+.1f}%" if dogru else "-"])
    tablo_yaz("Aylık çevrim neden şart — yıllık hasılat (2025 YTD)", kanit,
              ["Şirket", "PB", "Yerel YTD", "DOĞRU (aylık kur)",
               "YANLIŞ (tek kur)", "Hata"])

    # ---- Çevrim farkı ve veri hatası ayrımı ----
    son = fark_raporu[fark_raporu["donem"] == y.donemler()[-1]]
    tablo_yaz("Çevrim farkı vs veri hatası (yıl sonu)",
              [[r.sirket_kod, para(r.yerel_denksizlik, 2),
                para(r.veri_hatasi_eur, 2), para(r.cevrim_farki_eur, 0)]
               for r in son.itertuples()],
              ["Şirket", "Yerel denksizlik", "Veri hatası EUR", "Saf çevrim farkı EUR"])
    hatali = son[son["yerel_denksizlik"].abs() > 0.01]
    if not hatali.empty:
        g.uyari(f"{len(hatali)} şirkette yerel mizan denk değil — "
                f"bu bir VERİ HATASI, kur farkı değil. K01 bulgu yazacak: "
                f"{list(hatali['sirket_kod'])}")

    konsolide = konsolide_et(cevrilmis, y, g)
    konsolide.to_csv(ARA_DIZIN / "konsolide.csv", index=False, encoding="utf-8")

    # ---- Konsolide gelir tablosu (yıl sonu) ----
    son_donem = y.donemler()[-1]
    ks = konsolide[konsolide["donem"] == son_donem]
    satirlar = []
    for kalem in ["Hasılat", "Satışların maliyeti", "Faaliyet giderleri",
                  "Finansal gelir/gider", "Vergi"]:
        alt = ks[ks["kalem"] == kalem]
        brut = -alt["eur_brut"].sum()
        kons = -alt["eur_konsolide"].sum()
        satirlar.append([kalem, para(brut, 0), para(kons, 0),
                         para(kons - brut, 0)])
    hasilat_k = -ks[ks["kalem"] == "Hasılat"]["eur_konsolide"].sum()
    smm_k = -ks[ks["kalem"] == "Satışların maliyeti"]["eur_konsolide"].sum()
    fg_k = -ks[ks["kalem"] == "Faaliyet giderleri"]["eur_konsolide"].sum()
    satirlar.append(["— BRÜT KÂR", "", para(hasilat_k + smm_k, 0), ""])
    satirlar.append(["— FAALİYET KÂRI", "", para(hasilat_k + smm_k + fg_k, 0), ""])
    tablo_yaz(f"Konsolide gelir tablosu {son_donem} YTD (EUR)", satirlar,
              ["Kalem", "Şirketler toplamı", "Konsolide", "Eliminasyon"])

    elimine_toplam = -ks[ks["elimine"]]["eur_brut"].sum()
    g.bilgi(f"\nGrup içi eliminasyon: {para(abs(elimine_toplam), 0)} EUR "
            f"({len(y.elimine_hesaplar())} hesap)")
    g.bilgi(f"Konsolide hasılat {son_donem}: {para(hasilat_k, 0)} EUR")

    g.bitir({"cevrilmis_satir": len(cevrilmis), "konsolide_satir": len(konsolide),
             "cevrim_farki_kayit": len(fark_raporu)})


if __name__ == "__main__":
    main()
