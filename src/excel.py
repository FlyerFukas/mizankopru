# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ [6b] EXCEL: konsolidasyon paketi.

GÖREV
  Kapanış paketini finansçının çalıştığı biçimde üretir: formatlı, çok
  sayfalı, filtrelenebilir, dondurulmuş başlıklı bir .xlsx.

NEDEN EXCEL
  Excel'i ortadan kaldırmak bu projenin amacı değil. Amaç, Excel'e giden
  yoldaki elle yapılan işi (pivot, VLOOKUP, kur çevirme, mutabakat)
  ortadan kaldırmak. Kapanış paketi yine Excel olarak çıkar, çünkü onu
  imzalayacak, denetçiye gönderecek ve üzerinde not alacak olan orada
  çalışır. Fark şu: bu dosya elle değil, izlenebilir bir boru hattıyla
  üretilir ve her rakam kaynağına kadar geri sürülebilir.

ÇALIŞTIRMA
  py src/excel.py
ÇIKTI
  cikti/konsolidasyon_paketi.xlsx
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import xlsxwriter

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gunluk import Gunluk, dosya_parmak_izi           # noqa: E402
from sema import ARA_DIZIN, CIKTI_DIZIN, KOK, yukle   # noqa: E402


class Paket:
    """xlsxwriter sarmalayıcı, biçimleri bir kez tanımlar, sayfaları yazar."""

    def __init__(self, yol: Path):
        self.kitap = xlsxwriter.Workbook(str(yol), {"nan_inf_to_errors": True})
        b = self.kitap.add_format
        self.b = {
            "baslik": b({"bold": True, "font_size": 16, "font_color": "#0d2b4e"}),
            "altbaslik": b({"font_size": 10, "font_color": "#5a6b7d"}),
            "bolum": b({"bold": True, "font_size": 12, "font_color": "#0d2b4e",
                        "bottom": 2, "border_color": "#0d2b4e"}),
            "th": b({"bold": True, "font_size": 9, "bg_color": "#0d2b4e",
                     "font_color": "white", "align": "left", "valign": "vcenter",
                     "text_wrap": True, "border": 1, "border_color": "#0d2b4e"}),
            "metin": b({"font_size": 10, "border": 1, "border_color": "#d7dde5"}),
            "metin_kucuk": b({"font_size": 9, "border": 1, "border_color": "#d7dde5",
                              "text_wrap": True, "valign": "top"}),
            "sayi": b({"font_size": 10, "num_format": "#,##0", "border": 1,
                       "border_color": "#d7dde5"}),
            "sayi2": b({"font_size": 10, "num_format": "#,##0.00", "border": 1,
                        "border_color": "#d7dde5"}),
            "yuzde": b({"font_size": 10, "num_format": "0.0%", "border": 1,
                        "border_color": "#d7dde5"}),
            "kur": b({"font_size": 10, "num_format": "#,##0.000000", "border": 1,
                      "border_color": "#d7dde5"}),
            "toplam": b({"bold": True, "font_size": 10, "num_format": "#,##0",
                         "top": 2, "bottom": 6, "border_color": "#0d2b4e",
                         "bg_color": "#eef3f9"}),
            "toplam_metin": b({"bold": True, "font_size": 10, "top": 2, "bottom": 6,
                               "border_color": "#0d2b4e", "bg_color": "#eef3f9"}),
            "kritik": b({"font_size": 9, "bg_color": "#fde8e8", "font_color": "#9b1c1c",
                         "bold": True, "border": 1, "border_color": "#d7dde5"}),
            "yuksek": b({"font_size": 9, "bg_color": "#fef3c7", "font_color": "#92400e",
                         "border": 1, "border_color": "#d7dde5"}),
            "orta": b({"font_size": 9, "bg_color": "#e0f2fe", "font_color": "#075985",
                       "border": 1, "border_color": "#d7dde5"}),
            "dusuk": b({"font_size": 9, "bg_color": "#f1f5f9", "font_color": "#475569",
                        "border": 1, "border_color": "#d7dde5"}),
            "iyi": b({"font_size": 10, "num_format": "#,##0", "font_color": "#166534",
                      "border": 1, "border_color": "#d7dde5"}),
            "kotu": b({"font_size": 10, "num_format": "#,##0", "font_color": "#9b1c1c",
                       "border": 1, "border_color": "#d7dde5"}),
            "not": b({"font_size": 9, "font_color": "#5a6b7d", "italic": True,
                      "text_wrap": True, "valign": "top"}),
        }

    def sayfa(self, ad: str, genislikler: list[float], baslik: str = "",
              aciklama: str = ""):
        s = self.kitap.add_worksheet(ad)
        for i, g in enumerate(genislikler):
            s.set_column(i, i, g)
        satir = 0
        if baslik:
            s.write(0, 0, baslik, self.b["baslik"])
            satir = 1
        if aciklama:
            s.merge_range(satir, 0, satir, max(len(genislikler) - 1, 1),
                          aciklama, self.b["not"])
            s.set_row(satir, 28)
            satir += 1
        return s, satir + 1

    def tablo_basligi(self, s, satir: int, basliklar: list[str]) -> int:
        for i, b in enumerate(basliklar):
            s.write(satir, i, b, self.b["th"])
        s.set_row(satir, 30)
        s.freeze_panes(satir + 1, 0)
        s.autofilter(satir, 0, satir, len(basliklar) - 1)
        return satir + 1

    def kapat(self):
        self.kitap.close()


def main():
    g = Gunluk("excel")
    y = yukle()
    son = y.son_donem()

    oku = lambda p, **kw: pd.read_csv(p, dtype={"donem": str, **kw})

    def oku_varsa(p, **kw):
        """Yüklenmemiş veri paketi çökertmemeli, sayfası atlanmalı.

        Boş dönmek ile eski bir dosyayı okumak arasındaki fark, kullanıcının
        yüklemediği veriden üretilmiş rakam görüp görmemesidir."""
        if not Path(p).exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(p, dtype={"donem": str, **kw},
                               encoding="utf-8-sig")
        except pd.errors.EmptyDataError:
            return pd.DataFrame()

    konsolide = oku(ARA_DIZIN / "konsolide.csv", grup_kod=str)
    cevrilmis = oku(ARA_DIZIN / "cevrilmis.csv", grup_kod=str)
    cevrim_farki = oku(ARA_DIZIN / "cevrim_farki.csv")
    grup_ici = oku_varsa(ARA_DIZIN / "grup_ici.csv")
    bulgular = oku_varsa(CIKTI_DIZIN / "bulgular.csv")
    kopru = oku_varsa(CIKTI_DIZIN / "sapma_koprusu.csv")
    eslesmeyenler = oku_varsa(ARA_DIZIN / "eslesmeyenler.csv",
                              yerel_hesap_kod=str)
    oranlar = oku_varsa(CIKTI_DIZIN / "oranlar.csv")
    dikey = oku_varsa(CIKTI_DIZIN / "dikey_analiz.csv")
    atlanan_analiz = json.loads(
        (CIKTI_DIZIN / "atlanan_analizler.json").read_text(encoding="utf-8"))         if (CIKTI_DIZIN / "atlanan_analizler.json").exists() else []
    if bulgular.empty:
        bulgular = pd.DataFrame(columns=["test_kod", "onem", "sirket_kod",
                                         "donem", "nesne", "tutar_eur",
                                         "aciklama"])

    # Bu çalıştırmanın kökeni ve kapsamı: her sayfanın üstünde görünür.
    koken = json.loads((ARA_DIZIN / "koken.json").read_text(encoding="utf-8")) \
        if (ARA_DIZIN / "koken.json").exists() else {}
    kapsam = y.kapsam()
    kapsam_sirket = kapsam.get("sirketler") or sorted(y.sirketler)
    kapsam_disi = kapsam.get("kapsam_disi") or []
    atlanan = json.loads(
        (CIKTI_DIZIN / "atlanan_testler.json").read_text(encoding="utf-8")) \
        if (CIKTI_DIZIN / "atlanan_testler.json").exists() else []

    PB = y.sunum_para_birimi

    hedef = CIKTI_DIZIN / "konsolidasyon_paketi.xlsx"
    P = Paket(hedef)
    B = P.b

    ks = konsolide[konsolide["donem"] == son]
    kal = lambda ad: -ks[ks["kalem"] == ad]["eur_konsolide"].sum()
    hasilat, smm = kal("Hasılat"), kal("Satışların maliyeti")
    opex, fin, vergi = kal("Faaliyet giderleri"), kal("Finansal gelir/gider"), kal("Vergi")
    diger = kal("Diğer gelir/gider")
    maliyet_741 = kal("Maliyet muhasebesi")   # 7/A, net sıfır olmalı
    brut, faaliyet = hasilat + smm, hasilat + smm + opex
    net = faaliyet + fin + diger + vergi
    kritik = int((bulgular["onem"] == "kritik").sum())

    # ================= 1. KAPAK =================
    s, r = P.sayfa("Kapak", [30, 26, 22, 22, 18],
                   "KONSOLİDASYON PAKETİ",
                   f"{y.grup['ad']} · konsolide dönem {son} · sunum para birimi "
                   f"{y.sunum_para_birimi} · {len(y.sirketler)} tüzel kişilik. "
                   f"Bu dosya py src/excel.py ile üretilmiştir; elle düzenlenmemelidir.")
    s.write(r, 0, "KAPANIŞ DURUMU", B["bolum"]); r += 1
    if kritik:
        s.write(r, 0, f"İMZALANAMAZ, {kritik} kritik bulgu açık", B["kritik"])
        s.write(r, 1, "Açık testler: " + ", ".join(
            sorted(bulgular[bulgular["onem"] == "kritik"]["test_kod"].unique())),
            B["metin"])
    elif atlanan:
        s.write(r, 0, f"KOŞULLU, {len(atlanan)} test çalıştırılamadı",
                B["kritik"])
        s.write(r, 1, "Çalıştırılan testlerde kritik bulgu yok. Yüklenmeyen "
                      "veri nedeniyle atlanan testlerin kapsadığı riskler "
                      "denetlenmemiştir (aşağıdaki listeye bakın).", B["metin"])
    else:
        s.write(r, 0, "Kritik bulgu yok, imzalanabilir", B["iyi"])
    r += 2

    s.write(r, 0, "ÖZET", B["bolum"]); r += 1
    ozet_satirlar = [
        ("Konsolide hasılat", hasilat, "sayi"),
        ("Brüt kâr", brut, "sayi"),
        ("Faaliyet kârı", faaliyet, "iyi" if faaliyet > 0 else "kotu"),
        ("Net kâr", net, "iyi" if net > 0 else "kotu"),
        ("Brüt marj", brut / hasilat if hasilat else 0.0, "yuzde"),
        ("Faaliyet marjı", faaliyet / hasilat if hasilat else 0.0, "yuzde"),
        ("Net marj", net / hasilat if hasilat else 0.0, "yuzde"),
        ("Kontrol bulgusu", len(bulgular), "sayi"),
        ("  kritik", kritik, "sayi"),
        ("  yüksek", int((bulgular["onem"] == "yuksek").sum()), "sayi"),
    ]
    for ad, deger, bic in ozet_satirlar:
        s.write(r, 0, ad, B["metin"])
        s.write_number(r, 1, float(deger), B[bic])
        r += 1
    r += 1

    s.write(r, 0, "BU PAKET HANGİ DOSYALARDAN ÜRETİLDİ", B["bolum"]); r += 1
    if koken.get("dosyalar"):
        r = P.tablo_basligi(s, r, ["Dosya", "Tür", "Şirket", "Boyut (KB)",
                                   "Parmak izi (SHA-256)"])
        for d in koken["dosyalar"]:
            s.write(r, 0, d.get("ad", ""), B["metin"])
            s.write(r, 1, d.get("tip", "") or "", B["metin"])
            s.write(r, 2, d.get("sirket", "") or "", B["metin"])
            s.write_number(r, 3, int(d.get("kb", 0)), B["sayi"])
            s.write(r, 4, d.get("parmak", ""), B["metin_kucuk"])
            r += 1
        gercek = koken.get("veri_seti") == "kullanici"
        s.write(r, 0, "Kaynak", B["metin"])
        s.write(r, 1, "kullanıcı verisi" if gercek
                else str(koken.get("veri_seti", "?")).upper() + " VERİSİ",
                B["metin"] if gercek else B["kritik"])
        r += 1
        s.write(r, 0, "Okuma zamanı", B["metin"])
        s.write(r, 1, koken.get("zaman", ""), B["metin"]); r += 1
        if not koken.get("guvenilir", True):
            s.write(r, 0, "UYARI", B["kritik"])
            s.write(r, 1, "Kaynak doğrulaması zorlanarak geçildi; bu paketteki "
                          "rakamlara güvenilemez.", B["metin"]); r += 1
        r += 1
    else:
        s.write(r, 0, "Köken kaydı yok (veri/ara/koken.json bulunamadı)",
                B["kritik"]); r += 2

    s.write(r, 0, "KAPSAM", B["bolum"]); r += 1
    r = P.tablo_basligi(s, r, ["Şirket", "Ünvan", "Ülke", "Para birimi",
                               "Hesap planı"])
    for kod in kapsam_sirket:
        sir = y.sirketler.get(kod)
        if sir is None:
            continue
        s.write(r, 0, kod, B["metin"]); s.write(r, 1, sir.ad, B["metin"])
        s.write(r, 2, sir.ulke, B["metin"])
        s.write(r, 3, sir.fonksiyonel_para_birimi, B["metin"])
        s.write(r, 4, sir.hesap_plani, B["metin"])
        r += 1
    r += 1
    s.write(r, 0, "Sahiplik oranı", B["metin"])
    s.write(r, 1, ", ".join(f"{k} %{y.sirketler[k].sahiplik_orani*100:.0f}"
                            for k in kapsam_sirket if k in y.sirketler),
            B["metin"])
    r += 2

    if kapsam_disi:
        s.write(r, 0, "KAPSAM DIŞI", B["bolum"]); r += 1
        s.write(r, 0, ", ".join(kapsam_disi), B["kritik"])
        s.write(r, 1, "Yapılandırmada tanımlı, ancak bu çalıştırmada verisi "
                      "yüklenmedi. Bu paket onları İÇERMEZ.", B["metin"])
        r += 2

    if atlanan:
        s.write(r, 0, "ÇALIŞTIRILAMAYAN KONTROL TESTLERİ", B["bolum"]); r += 1
        r = P.tablo_basligi(s, r, ["Test", "Ad", "Neden atlandı", "", ""])
        for a in atlanan:
            s.write(r, 0, a.get("kod", ""), B["metin"])
            s.write(r, 1, a.get("ad", ""), B["metin"])
            s.write(r, 2, a.get("sebep", ""), B["metin"])
            r += 1
        s.write(r, 0, "UYARI", B["kritik"])
        s.write(r, 1, "Bu testlerin kapsadığı riskler DENETLENMEMİŞTİR; "
                      "bulgu çıkmaması risk yok demek değildir.", B["metin"])
        r += 1

    # ================= 2. GELİR TABLOSU =================
    s, r = P.sayfa("Gelir tablosu", [34, 18, 18, 14],
                   f"KONSOLİDE GELİR TABLOSU, {son} YTD",
                   "Gelir tablosu kalemleri IAS 21 uyarınca her ayın kendi "
                   "ortalama kuruyla çevrilip biriktirilmiştir. YTD tutarı tek "
                   "kurla çevirmek TR şirketlerinde ~%12 hata üretir.")
    r = P.tablo_basligi(s, r, ["Kalem", f"Konsolide ({y.sunum_para_birimi})",
                               "Şirketler toplamı", "Hasılata oran"])
    for ad, deger, kalin in [("Hasılat", hasilat, False),
                             ("Satışların maliyeti", smm, False),
                             ("BRÜT KÂR", brut, True),
                             ("Faaliyet giderleri", opex, False),
                             ("FAALİYET KÂRI", faaliyet, True),
                             ("Finansal gelir/gider", fin, False),
                             ("Diğer gelir/gider", diger, False),
                             ("Vergi", vergi, False),
                             ("NET KÂR", net, True)]:
        brut_toplam = -ks[ks["kalem"] == ad]["eur_brut"].sum() if not kalin else None
        s.write(r, 0, ad, B["toplam_metin"] if kalin else B["metin"])
        s.write_number(r, 1, float(deger), B["toplam"] if kalin else B["sayi"])
        if brut_toplam is not None:
            s.write_number(r, 2, float(brut_toplam), B["sayi"])
        else:
            s.write(r, 2, "", B["toplam"])
        s.write_number(r, 3, float(deger / hasilat) if hasilat else 0.0,
                       B["toplam"] if kalin else B["yuzde"])
        r += 1
    if abs(maliyet_741) > 1:
        r += 1
        s.write(r, 0, "7/A maliyet hesapları net bakiyesi", B["metin"])
        s.write_number(r, 1, float(maliyet_741), B["kritik"])
        s.write(r, 2, "Yansıtma hesapları gider hesaplarını kapatmamış; "
                      "maliyet aktarımı eksik.", B["metin_kucuk"])
        r += 1

    # ================= 3. BİLANÇO =================
    b = ks[ks["tur"] == "B"]
    s, r = P.sayfa("Bilanço", [34, 18, 18],
                   f"KONSOLİDE BİLANÇO, {son}",
                   "Bilanço kalemleri kapanış kuruyla çevrilmiştir. Çevrim "
                   "farkı özkaynakta 3090 hesabında toplanır. Askı hesabında "
                   "bakiye varken kapanış imzalanmamalıdır.")
    r = P.tablo_basligi(s, r, ["Kalem", f"Konsolide ({y.sunum_para_birimi})",
                               "Şirketler toplamı"])
    for ad in ["Dönen varlıklar", "Duran varlıklar", "Kısa vadeli yükümlülükler",
               "Uzun vadeli yükümlülükler", "Özkaynaklar", "Askı"]:
        alt = b[b["kalem"] == ad]
        if alt.empty:
            continue
        isaret = 1 if ad.endswith("varlıklar") or ad == "Askı" else -1
        deger = alt["eur_konsolide"].sum() * isaret
        bicim = B["kritik"] if (ad == "Askı" and abs(deger) > 1) else B["sayi"]
        s.write(r, 0, ad, B["metin"])
        s.write_number(r, 1, float(deger), bicim)
        s.write_number(r, 2, float(alt["eur_brut"].sum() * isaret), B["sayi"])
        r += 1
    r += 1
    varlik = float(b[b["kalem"].isin(["Dönen varlıklar",
                                      "Duran varlıklar"])]["eur_konsolide"].sum())
    kaynak = float(-b[b["kalem"].isin(["Kısa vadeli yükümlülükler",
                                       "Uzun vadeli yükümlülükler",
                                       "Özkaynaklar"])]["eur_konsolide"].sum())
    s.write(r, 0, "TOPLAM VARLIKLAR", B["toplam_metin"])
    s.write_number(r, 1, varlik, B["toplam"]); r += 1
    s.write(r, 0, "Kaynaklar (dönem kârı hariç)", B["metin"])
    s.write_number(r, 1, kaynak, B["sayi"]); r += 1
    s.write(r, 0, "Dönem net kârı (mizanda 690 kapatılmamış)", B["metin"])
    s.write_number(r, 1, float(net), B["sayi"]); r += 1
    s.write(r, 0, "TOPLAM KAYNAKLAR", B["toplam_metin"])
    s.write_number(r, 1, kaynak + float(net), B["toplam"]); r += 1
    fark = varlik - (kaynak + float(net))
    s.write(r, 0, "Denklik farkı (0 olmalı)", B["metin"])
    s.write_number(r, 1, fark, B["sayi"] if abs(fark) < 1 else B["kritik"])

    # ================= 3b. ORANLAR VE DİKEY ANALİZ =================
    if not oranlar.empty:
        s, r = P.sayfa("Oranlar", [26, 14, 18, 18, 62],
                       f"FİNANSAL ORANLAR VE DİKEY ANALİZ, {son}",
                       "Her oranın payı ve paydası yanında yazılıdır: bir "
                       "oranı sorgulayan kişi hangi hesaplardan geldiğini "
                       "görmeden ona güvenemez. Boş değer, oranın "
                       "hesaplanamadığını gösterir, sıfır olduğunu değil.")
        simdiki = None
        for x in oranlar.itertuples():
            if x.grup != simdiki:
                simdiki = x.grup
                s.write(r, 0, str(x.grup).upper(), B["bolum"]); r += 1
                r = P.tablo_basligi(s, r, ["Oran", "Değer", f"Pay ({PB})",
                                           f"Payda ({PB})", "Ne anlama gelir"])
            s.write(r, 0, str(x.oran), B["metin"])
            if pd.isna(x.deger):
                s.write(r, 1, "hesaplanamadı", B["metin_kucuk"])
            elif x.bicim == "yuzde":
                s.write_number(r, 1, float(x.deger), B["yuzde"])
            elif x.bicim == "tutar":
                s.write_number(r, 1, float(x.deger), B["sayi"])
            else:
                s.write_number(r, 1, float(x.deger), B["sayi2"])
            if x.payda:
                s.write_number(r, 2, float(x.pay), B["sayi"])
                s.write_number(r, 3, float(x.payda), B["sayi"])
            s.write(r, 4, str(x.yorum), B["metin_kucuk"])
            r += 1
        r += 1

        if atlanan_analiz:
            s.write(r, 0, "ÜRETİLEMEYEN ANALİZLER", B["bolum"]); r += 1
            for a in atlanan_analiz:
                s.write(r, 0, a.get("analiz", ""), B["kritik"])
                s.write(r, 1, a.get("sebep", ""), B["metin"])
                s.write(r, 4, a.get("sonuc", ""), B["metin_kucuk"])
                r += 1
            r += 1

        if not dikey.empty:
            bolum = None
            for x in dikey.itertuples():
                if x.bolum != bolum:
                    bolum = x.bolum
                    s.write(r, 0, f"DİKEY ANALİZ, {str(bolum).upper()}",
                            B["bolum"]); r += 1
                    r = P.tablo_basligi(s, r, ["Kalem", f"Tutar ({PB})",
                                               "Oran", "", ""])
                kalin = str(x.kalem).isupper()
                s.write(r, 0, str(x.kalem),
                        B["toplam_metin"] if kalin else B["metin"])
                s.write_number(r, 1, float(x.tutar),
                               B["toplam"] if kalin else B["sayi"])
                if not pd.isna(x.oran):
                    s.write_number(r, 2, float(x.oran),
                                   B["toplam"] if kalin else B["yuzde"])
                r += 1

    # ================= 4. SAPMA KÖPRÜSÜ =================
    if kopru.empty:
        # Ürün bazında miktar ve fiyat olmadan fiyat/karışım/hacim
        # ayrıştırması matematiksel olarak YAPILAMAZ. Boş sayfa yerine
        # neden üretilemediği yazılır; uydurulmuş bir ayrıştırma yanlış
        # yönetim kararı üretir.
        s, r = P.sayfa("Sapma köprüsü", [40, 70],
                       "HASILAT SAPMA KÖPRÜSÜ, ÜRETİLEMEDİ",
                       "Bu adım atlandı; aşağıdaki veri yüklenmediği için "
                       "fiyat / karışım / hacim ayrıştırması yapılamaz.")
        for etiket, deger in [
                ("Durum", "ÜRETİLMEDİ"),
                ("Gereken veri", "Ürün kodu, miktar ve birim fiyat içeren "
                                 "fiili ve bütçe satış dosyaları"),
                ("Neden tahmin edilmedi", "Miktar bilinmeden fiyat etkisi "
                                          "ile hacim etkisi birbirinden "
                                          "ayrılamaz.")]:
            s.write(r, 0, etiket, B["metin"])
            s.write(r, 1, deger, B["kritik"] if etiket == "Durum"
                    else B["metin"])
            r += 1
    else:
        t = kopru[["butce_eur", "fiyat_eur", "karisim_eur", "hacim_eur",
                   "kur_etkisi_eur", "fiili_eur"]].sum()
        s, r = P.sayfa("Sapma köprüsü", [30, 18, 14, 16, 16, 16, 16, 16],
                       "HASILAT SAPMA KÖPRÜSÜ, 2025",
                       "Fiyat + karışım + hacim toplamı yerel para sapmasına birebir "
                       "eşittir (artık terim yok, her çalıştırmada sınanır). Kur etkisi "
                       "= fiili yerel tutar × (gerçekleşen kur − bütçe kuru). Bütçe kuru "
                       "")
        s.write(r, 0, "GRUP TOPLAMI", B["bolum"]); r += 1
        r = P.tablo_basligi(s, r, ["Kalem", PB, "Bütçeye oran"])
        for ad, deger, kalin in [("Bütçe (bütçe kuruyla)", t["butce_eur"], True),
                                 ("  + Fiyat etkisi", t["fiyat_eur"], False),
                                 ("  + Karışım etkisi", t["karisim_eur"], False),
                                 ("  + Hacim etkisi", t["hacim_eur"], False),
                                 ("= Sabit kurda fiili",
                                  t["butce_eur"] + t["fiyat_eur"] + t["karisim_eur"]
                                  + t["hacim_eur"], True),
                                 ("  + Kur etkisi", t["kur_etkisi_eur"], False),
                                 ("Fiili (gerçekleşen kurla)", t["fiili_eur"], True)]:
            s.write(r, 0, ad, B["toplam_metin"] if kalin else B["metin"])
            s.write_number(r, 1, float(deger), B["toplam"] if kalin else
                           (B["iyi"] if deger >= 0 else B["kotu"]))
            s.write_number(r, 2, float(deger / t["butce_eur"]),
                           B["toplam"] if kalin else B["yuzde"])
            r += 1
        r += 2

        s.write(r, 0, "ŞİRKET BAZINDA", B["bolum"]); r += 1
        ozet = kopru.groupby("sirket_kod", as_index=False).agg(
            butce=("butce_eur", "sum"), fiili=("fiili_eur", "sum"),
            fiyat=("fiyat_eur", "sum"), karisim=("karisim_eur", "sum"),
            hacim=("hacim_eur", "sum"), kur=("kur_etkisi_eur", "sum"),
            mb=("miktar_butce", "sum"), mf=("miktar_fiili", "sum"),
            fy=("fiili_yerel", "sum"), by=("butce_yerel", "sum"))
        r = P.tablo_basligi(s, r, ["Şirket", f"Bütçe {PB}", "PB", "Fiyat",
                                   "Karışım", "Hacim", "Kur", f"Fiili {PB}"])
        for x in ozet.itertuples():
            sir = y.sirketler[x.sirket_kod]
            s.write(r, 0, f"{x.sirket_kod} {sir.ad}", B["metin"])
            s.write_number(r, 1, float(x.butce), B["sayi"])
            s.write(r, 2, sir.fonksiyonel_para_birimi, B["metin"])
            for i, v in enumerate([x.fiyat, x.karisim, x.hacim, x.kur]):
                s.write_number(r, 3 + i, float(v), B["iyi"] if v >= 0 else B["kotu"])
            s.write_number(r, 7, float(x.fiili), B["sayi"])
            r += 1
        r += 2

        s.write(r, 0, "AYNI YIL, ÜÇ FARKLI OKUMA", B["bolum"]); r += 1
        r = P.tablo_basligi(s, r, ["Şirket", "Para birimi", "Miktar Δ",
                                   "Yerel ciro Δ", f"{PB} ciro Δ", "Not"])
        for x in ozet.itertuples():
            sir = y.sirketler[x.sirket_kod]
            dm = (x.mf / x.mb - 1) if x.mb else 0
            dy = (x.fy / x.by - 1) if x.by else 0
            de = (x.fiili / x.butce - 1) if x.butce else 0
            s.write(r, 0, x.sirket_kod, B["metin"])
            s.write(r, 1, sir.fonksiyonel_para_birimi, B["metin"])
            for i, v in enumerate([dm, dy, de]):
                s.write_number(r, 2 + i, float(v), B["yuzde"])
            s.write(r, 5, "Yerelde hedef üstü, sunum para biriminde hedef altı, "
                          "fark kur çevriminden" if dy > 0 > de else "", B["metin_kucuk"])
            r += 1

    # ================= 5. KONTROL BULGULARI =================
    s, r = P.sayfa("Kontrol bulguları", [8, 26, 10, 9, 10, 26, 15, 62],
                   f"İÇ KONTROL BULGULARI, {len(bulgular)} bulgu",
                   "Her bulgu bir iddia değil bir sorudur: 'bu kayıt neden böyle?'. "
                   "Kanıt sütunu hangi fiş, hangi tutar, hangi kullanıcı olduğunu "
                   "taşır. Karar imzayı atacak olanındır.")
    r = P.tablo_basligi(s, r, ["Test", "Test adı", "Önem", "Şirket", "Dönem",
                               "Nesne", f"Tutar {PB}", "Açıklama"])
    for x in bulgular.itertuples():
        bic = B[x.onem]
        s.write(r, 0, x.test_kod, bic)
        s.write(r, 1, x.test_ad, B["metin_kucuk"])
        s.write(r, 2, x.onem, bic)
        s.write(r, 3, x.sirket_kod, B["metin_kucuk"])
        s.write(r, 4, x.donem, B["metin_kucuk"])
        s.write(r, 5, str(x.nesne), B["metin_kucuk"])
        s.write_number(r, 6, float(x.tutar_eur), B["sayi"])
        s.write(r, 7, str(x.aciklama), B["metin_kucuk"])
        r += 1

    # ================= 6. GRUP İÇİ MUTABAKAT =================
    s, r = P.sayfa("Grup içi mutabakat", [12, 12, 10, 22, 16, 16, 14, 12],
                   "GRUP İÇİ MUTABAKAT",
                   "Her çift için iki tarafın beyanı sunum para birimine "
                   "çevrilip karşılaştırılır. Tolerans dışı fark konsolide "
                   "bilançoyu doğrudan şişirir ya da eksiltir (K08).")
    r = P.tablo_basligi(s, r, ["Satıcı", "Alıcı", "Dönem", "Tür",
                               f"Alacak ({PB})", f"Borç ({PB})", "Fark", "Durum"])
    kayit = {}
    for x in grup_ici.itertuples():
        if x.sirket_kod not in y.sirketler or x.karsi_sirket not in y.sirketler:
            continue
        pb = y.sirketler[x.sirket_kod].fonksiyonel_para_birimi
        kayit[(x.sirket_kod, x.karsi_sirket, x.donem, x.yon)] = (
            x.tutar * y.kur(x.donem, pb, "kapanis"), x.tur)
    gorulmus = set()
    for (a, bb, donem, yon), (eur_a, tur) in sorted(kayit.items()):
        if yon != "alacak":
            continue
        anahtar = (a, bb, donem)
        if anahtar in gorulmus:
            continue
        gorulmus.add(anahtar)
        karsi = kayit.get((bb, a, donem, "borc"))
        eur_b = karsi[0] if karsi else 0.0
        fark = eur_a - eur_b
        taban = max(abs(eur_a), abs(eur_b), 1)
        tamam = abs(fark) <= 1000 and abs(fark) / taban <= 0.005
        s.write(r, 0, a, B["metin"]); s.write(r, 1, bb, B["metin"])
        s.write(r, 2, donem, B["metin"]); s.write(r, 3, tur, B["metin"])
        s.write_number(r, 4, float(eur_a), B["sayi"])
        s.write_number(r, 5, float(eur_b), B["sayi"])
        s.write_number(r, 6, float(fark), B["sayi"] if tamam else B["kotu"])
        s.write(r, 7, "tamam" if tamam else "FARK", B["metin"] if tamam else B["kritik"])
        r += 1

    # ================= 7. HESAP EŞLEME =================
    s, r = P.sayfa("Hesap eşleme", [12, 14, 34, 12, 30, 16],
                   "HESAP PLANI KÖPRÜSÜ",
                   "Yerel hesap planlarının grup planına eşlenmesi. Askıdaki "
                   "hesaplar (aşağıda) grup planında karşılığı bulunmayan, "
                   "konsolidasyondan sessizce düşebilecek kalemlerdir.")
    if not eslesmeyenler.empty:
        s.write(r, 0, "ASKIDAKİ HESAPLAR. KAPANIŞ ÖNCESİ ÇÖZÜLMELİ", B["bolum"])
        r += 1
        r = P.tablo_basligi(s, r, ["Şirket", "Plan", "Yerel hesap", "Dönem",
                                   "Aralık", f"Bakiye {PB}"])
        for x in eslesmeyenler.itertuples():
            s.write(r, 0, x.sirket_kod, B["kritik"])
            s.write(r, 1, x.hesap_plani, B["metin"])
            s.write(r, 2, f"{x.yerel_hesap_kod}  {x.yerel_hesap_ad}", B["metin"])
            s.write_number(r, 3, int(x.donem_sayisi), B["sayi"])
            s.write(r, 4, f"{x.ilk_donem} → {x.son_donem}", B["metin"])
            s.write_number(r, 5, float(x.bakiye_eur), B["kotu"])
            r += 1
        r += 2
    s.write(r, 0, "TAM EŞLEME TABLOSU", B["bolum"]); r += 1
    r = P.tablo_basligi(s, r, ["Plan", "Yerel kod", "Yerel ad", "Grup kodu",
                               "Grup hesabı", "Not"])
    for x in y.eslesme.itertuples():
        s.write(r, 0, x.plan_kodu, B["metin_kucuk"])
        s.write(r, 1, str(x.yerel_kod), B["metin_kucuk"])
        s.write(r, 2, x.yerel_ad, B["metin_kucuk"])
        s.write(r, 3, x.grup_kod, B["metin_kucuk"])
        s.write(r, 4, y.grup_hesaplari[x.grup_kod]["ad"], B["metin_kucuk"])
        s.write(r, 5, getattr(x, "_5", "") or "", B["metin_kucuk"])
        r += 1

    # ================= 8. KUR VE ÇEVRİM =================
    s, r = P.sayfa("Kur ve çevrim", [12, 12, 16, 16, 16, 22],
                   "KUR TABLOSU VE ÇEVRİM FARKI",
                   "Bilanço kapanış, gelir tablosu ortalama kurla çevrilir. "
                   "Bütçe kuru yıl başında sabitlenmiştir ve kur etkisini "
                   "izole etmek için kullanılır.")
    r = P.tablo_basligi(s, r, ["Dönem", "Para birimi", "Kapanış kuru",
                               "Ortalama kur", "Bütçe kuru", "Kaynak"])
    for x in y.kurlar.itertuples():
        s.write(r, 0, x.donem, B["metin"]); s.write(r, 1, x.para_birimi, B["metin"])
        s.write_number(r, 2, float(x.kapanis_kuru), B["kur"])
        s.write_number(r, 3, float(x.ortalama_kur), B["kur"])
        s.write_number(r, 4, float(x.butce_kuru), B["kur"])
        s.write(r, 5, x.kaynak, B["metin_kucuk"])
        r += 1
    r += 2
    s.write(r, 0, "ÇEVRİM FARKI vs VERİ HATASI", B["bolum"]); r += 1
    s.merge_range(r, 0, r, 5,
                  "Yerel mizan zaten denk değilse o denksizlik çevrim farkıyla "
                  "karışır ve bir veri hatası 'kur farkı' adı altında özkaynağa "
                  "gömülüp kaybolur. Bu tablo ikisini ayırır.", B["not"])
    s.set_row(r, 28); r += 1
    r = P.tablo_basligi(s, r, ["Dönem", "Şirket", "Yerel denksizlik",
                               f"Veri hatası {PB}", f"Saf çevrim farkı {PB}", ""])
    for x in cevrim_farki[cevrim_farki["donem"] == son].itertuples():
        s.write(r, 0, x.donem, B["metin"]); s.write(r, 1, x.sirket_kod, B["metin"])
        s.write_number(r, 2, float(x.yerel_denksizlik),
                       B["kotu"] if abs(x.yerel_denksizlik) > 0.01 else B["sayi2"])
        s.write_number(r, 3, float(x.veri_hatasi_eur), B["sayi"])
        s.write_number(r, 4, float(x.cevrim_farki_eur), B["sayi"])
        s.write(r, 5, "VERİ HATASI. K01" if abs(x.yerel_denksizlik) > 0.01 else "",
                B["kritik"] if abs(x.yerel_denksizlik) > 0.01 else B["metin"])
        r += 1

    # ================= 9. DENETİM İZİ =================
    s, r = P.sayfa("Denetim izi", [18, 14, 12, 12, 20, 20],
                   "DENETİM İZİ",
                   "Boru hattının her adımı girdi/çıktı parmak izi bırakır. "
                   "Yapay zekâ çağrılarının istem ve yanıt parmak izleri de "
                   "kaydedilir, 'bu yorumu kim yazdı' sorusunun cevabı burada.")
    izler = []
    iz_yolu = KOK / "gunluk" / "denetim_izi.jsonl"
    if iz_yolu.exists():
        for satir in iz_yolu.read_text(encoding="utf-8").splitlines():
            try:
                izler.append(json.loads(satir))
            except json.JSONDecodeError:
                pass
    s.write(r, 0, "BORU HATTI ADIMLARI", B["bolum"]); r += 1
    r = P.tablo_basligi(s, r, ["Adım", "Süre (sn)", "Uyarı", "Hata", "Zaman", ""])
    gorulen = {}
    for a in izler:
        if a.get("olay") == "adim_bitti":
            gorulen[a["adim"]] = a
    for ad in ["veri_uret", "topla", "esle", "cevir", "kontrol", "sapma",
               "pano", "excel"]:
        a = gorulen.get(ad)
        if not a:
            continue
        s.write(r, 0, ad, B["metin"])
        s.write_number(r, 1, float(a["sure_sn"]), B["sayi2"])
        s.write_number(r, 2, int(a["uyari"]), B["sayi"])
        s.write_number(r, 3, int(a["hata"]), B["sayi"])
        s.write(r, 4, str(a["zaman"])[:19], B["metin_kucuk"])
        r += 1
    r += 2
    s.write(r, 0, "YAPAY ZEKÂ ÇAĞRILARI", B["bolum"]); r += 1
    r = P.tablo_basligi(s, r, ["Görev", "Model", "Girdi token", "Çıktı token",
                               "Maliyet USD", "İstem parmak izi"])
    toplam_maliyet = 0.0
    for c in izler:
        if c.get("olay") != "zeka_cagri":
            continue
        toplam_maliyet += c.get("maliyet_usd", 0)
        s.write(r, 0, c["gorev"], B["metin"])
        s.write(r, 1, c["model"], B["metin_kucuk"])
        s.write_number(r, 2, int(c["girdi_token"]), B["sayi"])
        s.write_number(r, 3, int(c["cikti_token"]), B["sayi"])
        s.write_number(r, 4, float(c["maliyet_usd"]), B["sayi2"])
        s.write(r, 5, c.get("istem_parmak", ""), B["metin_kucuk"])
        r += 1
    s.write(r, 0, "TOPLAM", B["toplam_metin"])
    s.write(r, 4, toplam_maliyet, B["toplam"])
    r += 2
    s.write(r, 0, "Yapılandırma parmak izleri", B["bolum"]); r += 1
    for ad in ["sirketler.yaml", "grup_hesap_plani.yaml", "hesap_eslesme.csv",
               "kurlar.csv", "kontroller.yaml"]:
        s.write(r, 0, ad, B["metin"])
        s.write(r, 1, dosya_parmak_izi(KOK / "yapilandirma" / ad), B["metin_kucuk"])
        r += 1

    P.kapat()
    boyut = hedef.stat().st_size / 1024
    g.iyi(f"Excel paketi üretildi: {hedef}  ({boyut:.0f} KB, {len(P.kitap.worksheets())} sayfa)")
    g.iz("excel_uretildi", dosya=str(hedef), sayfa=10, bulgu=len(bulgular))
    g.bitir({"sayfa": 10, "boyut_kb": round(boyut)})


if __name__ == "__main__":
    main()
