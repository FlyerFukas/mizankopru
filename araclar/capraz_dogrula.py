# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ · ÇAPRAZ DOĞRULAMA

NE İŞE YARAR
  Boru hattının ürettiği rakamları, HAM dosyayı boru hattından bağımsız
  olarak yeniden okuyarak sınar. Boru hattının kendi kodunu kullanmaz;
  ham Excel'i sıfırdan okur, TDHP mantığıyla toplar ve çıktılarla
  karşılaştırır.

NEDEN GEREKLİ
  Bir otomasyonun en tehlikeli hatası çökmek değil, yanlış veriden
  eksiksiz görünen bir sonuç üretmektir. Böyle bir hata yaşandı: kullanıcı
  bir mizan yükledi, dosya tanınmadığı için sessizce atlandı, boru hattı
  elindeki demo veriyle devam etti ve rapor tamamen başka bir şirketin
  rakamlarını gösterdi. Bu betik, o hata sınıfının tekrarını yakalamak
  için vardır: çıktıdaki her ana rakamın ham dosyada karşılığı var mı?

ÇALIŞTIRMA
  py araclar/capraz_dogrula.py
ÇIKIŞ KODU
  0 = tüm sınamalar geçti · 1 = en az bir sınama başarısız
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

from gunluk import Gunluk, para, tablo_yaz          # noqa: E402
from sema import ARA_DIZIN, CIKTI_DIZIN, yukle      # noqa: E402

TOLERANS = 0.01          # 1 kuruş


def ham_oku(yol: Path, bicim: dict) -> pd.DataFrame:
    """Ham mizanı boru hattının kodunu KULLANMADAN okur.

    Kasıtlı olarak topla.py'den bağımsız yazıldı: aynı hatayı iki kez
    yapan bir doğrulama, doğrulama değildir."""
    ham = pd.read_excel(yol, sheet_name=bicim.get("sekme", 0), header=None)
    bas = int(bicim["baslik_satiri"])
    d = ham.iloc[bas + 1:].copy()
    cikti = pd.DataFrame({
        "kod": d.iloc[:, int(bicim["kolon_kod"])],
        "ad": d.iloc[:, int(bicim["kolon_ad"])],
        "borc": pd.to_numeric(d.iloc[:, int(bicim["kolon_borc"])],
                              errors="coerce"),
        "alacak": pd.to_numeric(d.iloc[:, int(bicim["kolon_alacak"])],
                                errors="coerce"),
    })
    cikti["kod"] = cikti["kod"].map(
        lambda x: "" if pd.isna(x)
        else (str(int(x)) if isinstance(x, float) and x == int(x) else str(x).strip()))
    # Yalnızca ana hesap satırları: alt kırılımları toplamak çift sayımdır.
    desen = bicim.get("ana_hesap_deseni", r"^\d{3}$")
    cikti = cikti[cikti["kod"].str.match(desen, na=False)]
    cikti[["borc", "alacak"]] = cikti[["borc", "alacak"]].fillna(0.0)
    return cikti.reset_index(drop=True)


def main() -> int:
    g = Gunluk("capraz")
    y = yukle()

    koken_yolu = ARA_DIZIN / "koken.json"
    if not koken_yolu.exists():
        g.hata("veri/ara/koken.json yok. Önce boru hattını çalıştırın: "
               "py src/boru.py")
        g.bitir({"durum": "koken_yok"})
        return 1
    koken = json.loads(koken_yolu.read_text(encoding="utf-8"))

    mizanlar = [d for d in koken["dosyalar"]
                if d.get("tip") == "mizan" and d.get("tanindi")]
    if not mizanlar:
        g.hata("Köken kaydında tanınmış mizan dosyası yok.")
        g.bitir({"durum": "mizan_yok"})
        return 1

    g.bilgi("Çıktılar şu dosyalardan üretildiğini iddia ediyor:")
    for d in mizanlar:
        g.bilgi(f"    {d['ad']}  ({d['sirket']}, {d['kb']} KB)")

    # ---- 1. HAM DOSYAYI BAĞIMSIZ OKU ----
    ham_toplam = {"borc": 0.0, "alacak": 0.0, "satir": 0}
    ham_hesaplar: dict[str, float] = {}
    for d in mizanlar:
        yol = Path(d["yol"]) if d.get("yol") else (KOK / "veri" / "girdi" / d["ad"])
        if not yol.exists():
            g.hata(f"Ham dosya bulunamadı: {yol}")
            g.bitir({"durum": "ham_yok"})
            return 1
        sir = y.sirketler[d["sirket"]]
        ham = ham_oku(yol, sir.mizan_bicimi)
        ham_toplam["borc"] += float(ham["borc"].sum())
        ham_toplam["alacak"] += float(ham["alacak"].sum())
        ham_toplam["satir"] += len(ham)
        for r in ham.itertuples():
            ham_hesaplar[r.kod] = (ham_hesaplar.get(r.kod, 0.0)
                                   + float(r.borc) - float(r.alacak))

    # ---- 2. BORU HATTININ OKUDUĞU ----
    mizan = pd.read_csv(ARA_DIZIN / "mizan.csv",
                        dtype={"donem": str, "yerel_hesap_kod": str})
    boru_toplam = {"borc": float(mizan["borc"].sum()),
                   "alacak": float(mizan["alacak"].sum()),
                   "satir": len(mizan)}

    # ---- 3. SINAMALAR ----
    sinamalar: list[tuple[str, float, float, bool, str]] = []

    def sina(ad: str, ham_deger: float, boru_deger: float, birim: str = ""):
        gecti = abs(ham_deger - boru_deger) <= TOLERANS
        sinamalar.append((ad, ham_deger, boru_deger, gecti, birim))

    sina("Ham dosyadaki ana hesap sayısı",
         ham_toplam["satir"], boru_toplam["satir"], "adet")
    sina("Toplam borç", ham_toplam["borc"], boru_toplam["borc"],
         y.sunum_para_birimi)
    sina("Toplam alacak", ham_toplam["alacak"], boru_toplam["alacak"],
         y.sunum_para_birimi)

    # Mizan denkliği: ham dosyanın kendi içinde
    sina("Mizan denkliği (borç − alacak)",
         ham_toplam["borc"] - ham_toplam["alacak"], 0.0, y.sunum_para_birimi)

    # Hesap bazında: hiçbir bakiye yolda kaybolmamalı
    boru_hesaplar = (mizan.groupby("yerel_hesap_kod")["bakiye"].sum().to_dict())
    kayip = [(k, v) for k, v in ham_hesaplar.items()
             if abs(v - boru_hesaplar.get(k, 0.0)) > TOLERANS]
    sina("Bakiyesi boru hattında değişen hesap sayısı", 0, len(kayip), "adet")

    # ---- 4. GELİR TABLOSU: ham TDHP toplamı vs konsolide çıktı ----
    konsolide = pd.read_csv(ARA_DIZIN / "konsolide.csv",
                            dtype={"donem": str, "grup_kod": str})
    son = y.son_donem()
    ks = konsolide[konsolide["donem"] == son]
    kal = lambda ad: -float(ks[ks["kalem"] == ad]["eur_konsolide"].sum())

    ham_grup = lambda on: -sum(v for k, v in ham_hesaplar.items()
                               if k.startswith(on))
    # 60 = satışlar, 61 = satış indirimleri → net hasılat
    sina("Hasılat (ham 60x + 61x)", ham_grup("60") + ham_grup("61"),
         kal("Hasılat") + kal("Satış iskonto ve iadeleri")
         if "Satış iskonto ve iadeleri" in set(ks["kalem"]) else kal("Hasılat"),
         y.sunum_para_birimi)
    sina("Satışların maliyeti (ham 62x)", ham_grup("62"),
         kal("Satışların maliyeti"), y.sunum_para_birimi)
    sina("Faaliyet giderleri (ham 63x)", ham_grup("63"),
         kal("Faaliyet giderleri"), y.sunum_para_birimi)

    # ---- 4b. KAPSAM: uydurma dönem ya da şirket üretilmemeli ----
    # Yapılandırmadaki dönem listesi bir TAKVİMDİR, bir veri beyanı
    # değil. Onu veri sanan bir boru hattı, yüklenmemiş her dönem için
    # satır üretip bir önceki dönemin bakiyesini kopyalar. Tek bir
    # 2018-12 mizanı yüklendiğinde konsolide tabloda 12 tane uydurma
    # 2025 dönemi oluşmuştu; bu sınama onu yakalar.
    ham_donem = sorted(mizan["donem"].dropna().unique())
    kons_donem = sorted(konsolide["donem"].dropna().unique())
    sina("Konsolide tablodaki dönem sayısı",
         len(ham_donem), len(kons_donem), "adet")
    fazla_donem = [d for d in kons_donem if d not in ham_donem]
    sina("Yüklenmemiş olduğu hâlde üretilen dönem", 0, len(fazla_donem),
         "adet")
    ham_sirket = sorted(mizan["sirket_kod"].dropna().unique())
    kons_sirket = sorted(konsolide["sirket_kod"].dropna().unique())         if "sirket_kod" in konsolide.columns else ham_sirket
    fazla_sirket = [s for s in kons_sirket if s not in ham_sirket]
    sina("Yüklenmemiş olduğu hâlde üretilen şirket", 0, len(fazla_sirket),
         "adet")

    # ---- 5. ASKI: hiçbir tutar sessizce düşmemeli ----
    cevrilmis = pd.read_csv(ARA_DIZIN / "cevrilmis.csv",
                            dtype={"donem": str, "grup_kod": str})
    aski = float(cevrilmis[cevrilmis["grup_kod"] == "9999"]["eur_gercek"].sum())
    sina("Askıda kalan tutar (9999)", 0.0, aski, y.sunum_para_birimi)

    # ---- 6. RAPOR ----
    satirlar = []
    for ad, hd, bd, gecti, birim in sinamalar:
        bicimle = (lambda v: f"{v:,.0f}".replace(",", ".")
                   if birim == "adet" else para(v, 2))
        satirlar.append([ad, bicimle(hd), bicimle(bd),
                         "GEÇTİ" if gecti else "KALDI"])
    tablo_yaz("Çapraz doğrulama: ham dosya ↔ boru hattı çıktısı", satirlar,
              ["Sınama", "Ham dosya", "Boru hattı", "Sonuç"])

    if fazla_donem:
        g.hata("Yüklenmemiş dönemler için satır üretilmiş: "
               + ", ".join(fazla_donem))
    if fazla_sirket:
        g.hata("Yüklenmemiş şirketler için satır üretilmiş: "
               + ", ".join(fazla_sirket))
    if kayip:
        g.uyari(f"Bakiyesi değişen {len(kayip)} hesap:")
        for k, v in kayip[:15]:
            g.uyari(f"    {k}: ham {para(v, 2)} → boru "
                    f"{para(boru_hesaplar.get(k, 0.0), 2)}")

    kalan = [s for s in sinamalar if not s[3]]
    if kalan:
        g.hata(f"{len(kalan)} sınama BAŞARISIZ. Çıktılar ham dosyayla "
               f"tutarlı değil, kullanılmamalıdır.")
        g.bitir({"durum": "hata", "kalan": len(kalan),
                 "toplam": len(sinamalar)})
        return 1

    g.iyi(f"{len(sinamalar)}/{len(sinamalar)} sınama geçti. Çıktılardaki "
          f"rakamlar ham dosyadan bağımsız olarak doğrulandı.")
    g.bitir({"durum": "tamam", "sinama": len(sinamalar)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
