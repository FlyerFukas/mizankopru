# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ [5a] ORAN: finansal analiz katmanı.

GÖREV
  Konsolide tablodan finansal oranları, dikey analizi ve (birden çok
  dönem varsa) yatay analizi üretir. Kontrol testleri "bir şey yanlış
  mı" diye sorar; bu modül "işler nasıl gidiyor" diye sorar. İkisi
  aynı kapanışın iki yarısıdır.

NEDEN AYRI BİR ADIM
  Oranın kendisi kolaydır, pay ve paydanın hangi hesaplardan geldiği
  zordur. Cari oranı yanlış hesaplayan bir tablo, doğru görünen bir
  sayıyla yanlış karar verdirir. Bu yüzden her oranın payı ve paydası
  çıktıda AYRI KOLONLARDA yazılır: okuyan kişi sayıyı sorgulayabilsin.

TEK DÖNEM UYARISI
  Yatay analiz ve devir hızı karşılaştırması en az iki dönem ister.
  Tek dönemlik veride bu bölümler üretilmez, ATLANDI olarak yazılır.
  Ortalama yerine dönem sonu bakiyesi kullanıldığında devir süreleri
  bir miktar sapar; bu da çıktıda belirtilir.

ÇALIŞTIRMA
  py src/oran.py
ÇIKTI
  cikti/oranlar.csv · cikti/dikey_analiz.csv · cikti/oran_notu.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gunluk import Gunluk, para, tablo_yaz                    # noqa: E402
from sema import ARA_DIZIN, CIKTI_DIZIN, yukle                # noqa: E402

# Oran tanımları. Her biri: (ad, grup, pay_kalemleri, payda_kalemleri,
# birim, iyi_yon, yorum). iyi_yon: +1 yüksek iyi, -1 düşük iyi, 0 nötr.
# Kalem adları grup_hesap_plani.yaml'daki "kalem" alanıyla eşleşir.
BILANCO_KALEMLERI = {
    "donen": ["Dönen varlıklar"],
    "duran": ["Duran varlıklar"],
    "kvyk": ["Kısa vadeli yükümlülükler"],
    "uvyk": ["Uzun vadeli yükümlülükler"],
    "ozkaynak": ["Özkaynaklar"],
}


def yuzde(x: float | None) -> str:
    return "-" if x is None else f"%{x*100:,.1f}".replace(",", ".")


def kat(x: float | None) -> str:
    return "-" if x is None else f"{x:,.2f}".replace(",", "X").replace(
        ".", ",").replace("X", ".")


def gun(x: float | None) -> str:
    return "-" if x is None else f"{x:,.0f} gün".replace(",", ".")


def bol(pay: float, payda: float) -> float | None:
    """Sıfıra bölmek yerine None döner.

    0 yazmak, oranın hesaplanamadığını değil sıfır olduğunu söyler.
    İkisi aynı şey değildir ve karıştırılması yanlış karar verdirir."""
    if payda is None or abs(payda) < 1e-9:
        return None
    return pay / payda


def toparla(konsolide: pd.DataFrame, donem: str) -> dict:
    """Bir dönemin konsolide tablosunu oran hesabına hazır hâle getirir."""
    d = konsolide[konsolide["donem"] == donem]
    kal = lambda ad: float(d[d["kalem"] == ad]["eur_konsolide"].sum())
    grup = lambda kod: float(d[d["grup_kod"] == kod]["eur_konsolide"].sum())

    # Bakiye "borç - alacak" tutulur: varlıklar pozitif, kaynak ve
    # gelirler negatif gelir. Sunumda işaret çevrilir.
    donen = kal("Dönen varlıklar")
    duran = kal("Duran varlıklar")
    kvyk = -kal("Kısa vadeli yükümlülükler")
    uvyk = -kal("Uzun vadeli yükümlülükler")
    ozkaynak_mizan = -kal("Özkaynaklar")

    hasilat = -kal("Hasılat") - kal("Satış iskonto ve iadeleri")
    smm = kal("Satışların maliyeti")
    opex = kal("Faaliyet giderleri")
    finansal = kal("Finansal gelir/gider")
    diger = kal("Diğer gelir/gider")
    vergi = kal("Vergi")

    # Gider kalemleri borç bakiyeli, yani pozitif gelir; gelir kalemleri
    # alacak bakiyeli, yani negatif. Bu yüzden gider için işaret çevirmek
    # yerine doğrudan çıkarmak yeterlidir ve bir gelir kalemi (örneğin
    # net kur farkı geliri) kendiliğinden kârı artırır.
    brut = hasilat - smm
    faaliyet = brut - opex
    net = faaliyet - finansal - diger - vergi

    stok = grup("1030")
    ticari_alacak = grup("1020") + grup("1025")
    nakit = grup("1010")
    ticari_borc = -(grup("2010") + grup("2015"))
    finansal_borc = -(grup("2020") + grup("2510"))
    amortisman = abs(grup("6050"))

    return {
        "donem": donem,
        "donen": donen, "duran": duran, "aktif": donen + duran,
        "kvyk": kvyk, "uvyk": uvyk, "yabanci": kvyk + uvyk,
        "ozkaynak": ozkaynak_mizan + net,   # dönem kârı özkaynağa dahil
        "ozkaynak_mizan": ozkaynak_mizan,
        "stok": stok, "ticari_alacak": ticari_alacak, "nakit": nakit,
        "ticari_borc": ticari_borc, "finansal_borc": finansal_borc,
        "hasilat": hasilat, "smm": smm, "brut": brut,
        "opex": opex, "faaliyet": faaliyet, "amortisman": amortisman,
        "favok": faaliyet + amortisman,
        "finansal": finansal, "vergi": vergi, "net": net,
    }


def oranlari_hesapla(v: dict, y) -> list[dict]:
    """Her oran için ad, değer, pay, payda ve yorum üretir.

    Pay ve payda çıktıda kalır: bir oranı sorgulayan kişi hangi
    hesaplardan geldiğini görmeden ona güvenemez."""
    o: list[dict] = []

    def ekle(grup, ad, deger, pay, payda, bicim, yorum):
        o.append({"grup": grup, "oran": ad, "deger": deger,
                  "pay": round(pay, 2), "payda": round(payda, 2),
                  "bicim": bicim, "yorum": yorum})

    # --- Likidite ---
    ekle("Likidite", "Cari oran", bol(v["donen"], v["kvyk"]),
         v["donen"], v["kvyk"], "kat",
         "Dönen varlıkların kısa vadeli borçları kaç kez karşıladığı. "
         "1'in altı, borçların dönen varlıkla ödenemeyeceğini gösterir.")
    ekle("Likidite", "Asit-test oranı",
         bol(v["donen"] - v["stok"], v["kvyk"]),
         v["donen"] - v["stok"], v["kvyk"], "kat",
         "Stok satılmadan kısa vadeli borcun ödenebilirliği. Stoğu ağır "
         "işletmelerde cari orandan çok daha anlamlıdır.")
    ekle("Likidite", "Nakit oranı", bol(v["nakit"], v["kvyk"]),
         v["nakit"], v["kvyk"], "kat",
         "Yalnızca nakit ve benzerleriyle ödenebilecek kısa vadeli borç payı.")
    ekle("Likidite", "Net işletme sermayesi",
         v["donen"] - v["kvyk"], v["donen"], v["kvyk"], "tutar",
         "Dönen varlık eksi kısa vadeli yükümlülük. Negatifse işletme "
         "kısa vadeli borçla duran varlık finanse ediyor demektir.")

    # --- Kaldıraç ---
    ekle("Kaldıraç", "Borç / aktif", bol(v["yabanci"], v["aktif"]),
         v["yabanci"], v["aktif"], "yuzde",
         "Varlıkların ne kadarının yabancı kaynakla finanse edildiği.")
    ekle("Kaldıraç", "Borç / özkaynak", bol(v["yabanci"], v["ozkaynak"]),
         v["yabanci"], v["ozkaynak"], "kat",
         "Finansal risk göstergesi. Özkaynak negatifse oran anlamsızdır "
         "ve hesaplanmaz.")
    ekle("Kaldıraç", "Özkaynak / aktif", bol(v["ozkaynak"], v["aktif"]),
         v["ozkaynak"], v["aktif"], "yuzde",
         "Özkaynak yeterliliği. TTK 376 değerlendirmesinin tabanı.")
    ekle("Kaldıraç", "Faiz karşılama",
         bol(v["faaliyet"], v["finansal"]) if v["finansal"] > 0 else None,
         v["faaliyet"], max(v["finansal"], 0), "kat",
         "Faaliyet kârının finansman giderini kaç kez karşıladığı. "
         "1'in altı, faizin faaliyetten ödenemediği anlamına gelir.")

    # --- Kârlılık ---
    ekle("Kârlılık", "Brüt marj", bol(v["brut"], v["hasilat"]),
         v["brut"], v["hasilat"], "yuzde",
         "Hasılattan satılan malın maliyeti düşüldükten sonra kalan pay.")
    ekle("Kârlılık", "Faaliyet marjı", bol(v["faaliyet"], v["hasilat"]),
         v["faaliyet"], v["hasilat"], "yuzde",
         "Esas faaliyetin kârlılığı; finansman ve vergi hariç.")
    ekle("Kârlılık", "FAVÖK marjı", bol(v["favok"], v["hasilat"]),
         v["favok"], v["hasilat"], "yuzde",
         "Faaliyet kârı artı amortisman. Nakit üretme gücüne yakın ölçü.")
    ekle("Kârlılık", "Net marj", bol(v["net"], v["hasilat"]),
         v["net"], v["hasilat"], "yuzde",
         "Her 100 birim hasılattan geriye kalan net tutar.")
    ekle("Kârlılık", "Aktif kârlılığı (ROA)", bol(v["net"], v["aktif"]),
         v["net"], v["aktif"], "yuzde",
         "Varlıkların kâr üretme verimi. Dönem sonu aktifiyle hesaplanır.")
    ekle("Kârlılık", "Özkaynak kârlılığı (ROE)",
         bol(v["net"], v["ozkaynak"]),
         v["net"], v["ozkaynak"], "yuzde",
         "Ortağın koyduğu sermayenin getirisi. Özkaynak negatifse "
         "hesaplanmaz; negatif özkaynakta yüksek ROE yanıltıcıdır.")

    # --- Faaliyet döngüsü ---
    # Dönem sonu bakiyesi kullanılır; ortalama bakiye için en az iki
    # dönem gerekir ve bu durum çıktıda belirtilir.
    alacak_gun = bol(v["ticari_alacak"] * 365, v["hasilat"])
    stok_gun = bol(v["stok"] * 365, v["smm"])
    borc_gun = bol(v["ticari_borc"] * 365, v["smm"])
    ekle("Faaliyet döngüsü", "Alacak devir süresi", alacak_gun,
         v["ticari_alacak"], v["hasilat"], "gun",
         "Satıştan tahsilata geçen ortalama gün. Uzaması, tahsil "
         "edilemeyen alacağa ve eksik şüpheli alacak karşılığına işaret eder.")
    ekle("Faaliyet döngüsü", "Stok devir süresi", stok_gun,
         v["stok"], v["smm"], "gun",
         "Stoğun satılana kadar raflarda kaldığı ortalama gün.")
    ekle("Faaliyet döngüsü", "Borç ödeme süresi", borc_gun,
         v["ticari_borc"], v["smm"], "gun",
         "Tedarikçiye ödemenin ortalama gün cinsinden vadesi.")
    if None not in (alacak_gun, stok_gun, borc_gun):
        ekle("Faaliyet döngüsü", "Nakit dönüşüm süresi",
             alacak_gun + stok_gun - borc_gun, 0, 0, "gun",
             "Alacak + stok eksi borç. Nakdin işletmede kaç gün bağlı "
             "kaldığı; işletme sermayesi ihtiyacının doğrudan ölçüsü.")
    return o


def dikey_analiz(v: dict) -> list[dict]:
    """Bilançoda aktif toplamına, gelir tablosunda hasılata oran."""
    satir = []
    for ad, deger in (("Dönen varlıklar", v["donen"]),
                      ("  Nakit ve benzerleri", v["nakit"]),
                      ("  Ticari alacaklar", v["ticari_alacak"]),
                      ("  Stoklar", v["stok"]),
                      ("Duran varlıklar", v["duran"]),
                      ("TOPLAM AKTİF", v["aktif"])):
        satir.append({"bolum": "Bilanço, aktif", "kalem": ad, "tutar": deger,
                      "oran": bol(deger, v["aktif"])})
    for ad, deger in (("Kısa vadeli yükümlülükler", v["kvyk"]),
                      ("  Ticari borçlar", v["ticari_borc"]),
                      ("  Finansal borçlar", v["finansal_borc"]),
                      ("Uzun vadeli yükümlülükler", v["uvyk"]),
                      ("Özkaynaklar (dönem kârı dahil)", v["ozkaynak"]),
                      ("TOPLAM PASİF", v["yabanci"] + v["ozkaynak"])):
        satir.append({"bolum": "Bilanço, pasif", "kalem": ad, "tutar": deger,
                      "oran": bol(deger, v["aktif"])})
    for ad, deger in (("Hasılat", v["hasilat"]),
                      ("Satışların maliyeti", -v["smm"]),
                      ("BRÜT KÂR", v["brut"]),
                      ("Faaliyet giderleri", -v["opex"]),
                      ("FAALİYET KÂRI", v["faaliyet"]),
                      ("FAVÖK", v["favok"]),
                      ("NET KÂR", v["net"])):
        satir.append({"bolum": "Gelir tablosu", "kalem": ad, "tutar": deger,
                      "oran": bol(deger, v["hasilat"])})
    return satir


def yatay_analiz(su: dict, onceki: dict) -> list[dict]:
    """İki dönem arasındaki değişim. Tek dönemde çağrılmaz."""
    alanlar = [("Hasılat", "hasilat"), ("Satışların maliyeti", "smm"),
               ("Brüt kâr", "brut"), ("Faaliyet giderleri", "opex"),
               ("Faaliyet kârı", "faaliyet"), ("FAVÖK", "favok"),
               ("Net kâr", "net"), ("Toplam aktif", "aktif"),
               ("Stoklar", "stok"), ("Ticari alacaklar", "ticari_alacak"),
               ("Özkaynaklar", "ozkaynak")]
    out = []
    for ad, anahtar in alanlar:
        yeni, eski = su[anahtar], onceki[anahtar]
        out.append({"kalem": ad, "onceki": eski, "simdi": yeni,
                    "degisim": yeni - eski, "oran": bol(yeni - eski, abs(eski))})
    return out


def main():
    g = Gunluk("oran")
    y = yukle()

    kaynak = ARA_DIZIN / "konsolide.csv"
    if not kaynak.exists():
        g.hata(f"{kaynak} yok. Önce: py src/cevir.py")
        g.bitir({"durum": "girdi_yok"})
        return

    konsolide = pd.read_csv(kaynak, dtype={"donem": str, "grup_kod": str})
    donemler = sorted(konsolide["donem"].unique())
    son = y.son_donem()
    PB = y.sunum_para_birimi

    v = toparla(konsolide, son)
    oranlar = oranlari_hesapla(v, y)
    dikey = dikey_analiz(v)

    # ---- Yazdır ----
    bicimle = {"kat": kat, "yuzde": yuzde, "gun": gun,
               "tutar": lambda x: para(x, 0)}
    tablo_yaz(f"Finansal oranlar, {son} ({PB})",
              [[o["grup"], o["oran"], bicimle[o["bicim"]](o["deger"]),
                para(o["pay"], 0) if o["payda"] else "",
                para(o["payda"], 0) if o["payda"] else ""]
               for o in oranlar],
              ["Grup", "Oran", "Değer", "Pay", "Payda"])

    tablo_yaz(f"Dikey analiz, {son}",
              [[d["bolum"], d["kalem"], para(d["tutar"], 0), yuzde(d["oran"])]
               for d in dikey],
              ["Bölüm", "Kalem", f"Tutar ({PB})", "Oran"])

    pd.DataFrame(oranlar).to_csv(CIKTI_DIZIN / "oranlar.csv", index=False,
                                 encoding="utf-8-sig")
    pd.DataFrame(dikey).to_csv(CIKTI_DIZIN / "dikey_analiz.csv", index=False,
                               encoding="utf-8-sig")

    # ---- Yatay analiz: en az iki dönem ister ----
    atlanan = []
    yer = donemler.index(son) if son in donemler else -1
    if len(donemler) >= 2 and yer > 0:
        onceki_donem = donemler[yer - 1]
        yatay = yatay_analiz(v, toparla(konsolide, onceki_donem))
        pd.DataFrame(yatay).to_csv(CIKTI_DIZIN / "yatay_analiz.csv",
                                   index=False, encoding="utf-8-sig")
        tablo_yaz(f"Yatay analiz, {onceki_donem} → {son}",
                  [[x["kalem"], para(x["onceki"], 0), para(x["simdi"], 0),
                    para(x["degisim"], 0), yuzde(x["oran"])] for x in yatay],
                  ["Kalem", onceki_donem, son, "Değişim", "Oran"])
    else:
        # Üretilmeyen analiz, sessizce yokmuş gibi davranılmaz.
        atlanan.append({
            "analiz": "Yatay analiz (dönemler arası değişim)",
            "sebep": f"tek dönem yüklendi ({son}); karşılaştırma için en az "
                     f"iki dönemlik mizan gerekir",
            "sonuc": "büyüme, daralma ve trend ölçülemedi"})
        eski = CIKTI_DIZIN / "yatay_analiz.csv"
        if eski.exists():
            eski.unlink()
        g.uyari("Yatay analiz üretilemedi: tek dönem yüklü. Büyüme ve trend "
                "ölçülemez.")
        g.uyari("Devir süreleri dönem sonu bakiyesiyle hesaplandı; ortalama "
                "bakiye için en az iki dönem gerekir, sonuçlar bir miktar "
                "sapabilir.")

    if atlanan:
        (CIKTI_DIZIN / "atlanan_analizler.json").write_text(
            json.dumps(atlanan, ensure_ascii=False, indent=2),
            encoding="utf-8")
    else:
        eski = CIKTI_DIZIN / "atlanan_analizler.json"
        if eski.exists():
            eski.unlink()

    # ---- Kısa not ----
    satirlar = [f"# Finansal analiz notu, {son}", "",
                f"Sunum para birimi: {PB}. Kapsam: "
                f"{', '.join(y.kapsam().get('sirketler', []))}.", ""]
    for grup in ["Likidite", "Kaldıraç", "Kârlılık", "Faaliyet döngüsü"]:
        satirlar.append(f"## {grup}")
        for o in oranlar:
            if o["grup"] != grup:
                continue
            satirlar.append(f"- **{o['oran']}**: "
                            f"{bicimle[o['bicim']](o['deger'])}. {o['yorum']}")
        satirlar.append("")
    if atlanan:
        satirlar.append("## Üretilemeyen analizler")
        for a in atlanan:
            satirlar.append(f"- **{a['analiz']}**: {a['sebep']} "
                            f"({a['sonuc']}).")
    (CIKTI_DIZIN / "oran_notu.md").write_text("\n".join(satirlar),
                                              encoding="utf-8")

    hesaplanan = sum(1 for o in oranlar if o["deger"] is not None)
    g.iyi(f"{hesaplanan}/{len(oranlar)} oran hesaplandı, "
          f"{len(dikey)} dikey analiz satırı üretildi.")
    g.iz("oran_uretildi", donem=son, oran=hesaplanan, dikey=len(dikey),
         yatay=len(donemler) >= 2)
    g.bitir({"oran": hesaplanan, "donem": son})


if __name__ == "__main__":
    main()
