# -*- coding: utf-8 -*-
"""
MİZANKÖPRÜ — BORU HATTI: tüm adımları sırayla çalıştıran orkestratör.

KULLANIM
  py src/boru.py                  tüm boru hattı (mevcut veri/girdi ile)
  py src/boru.py --veri-uret      önce sentetik demo veriyi de üret
  py src/boru.py --baslangic esle  belirtilen adımdan itibaren
  py src/boru.py --zeka-kapali    yapay zekâ katmanını atla (rakamlar değişmez)

TASARIM
  Her adım ayrı bir süreç olarak çalışır. Bir adım hata verirse boru hattı
  DURUR — yanlış veriyle bir sonraki adıma geçmek, hatayı görünmez kılar.
  Adımlar arası durum veri/ara/ altındaki dosyalarda taşınır; her adım tek
  başına da çalıştırılabilir (yeniden üretilebilirlik).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gunluk import Gunluk, tablo_yaz                  # noqa: E402
from sema import ARA_DIZIN, CIKTI_DIZIN, KOK, yukle   # noqa: E402

ADIMLAR = [
    ("topla",   "src/topla.py",   "[1] Çok formatlı okuma ve normalizasyon"),
    ("esle",    "src/esle.py",    "[2] Yerel hesap planı → grup planı köprüsü"),
    ("cevir",   "src/cevir.py",   "[3] IAS 21 çevrim, eliminasyon, azınlık payı"),
    ("kontrol", "src/kontrol.py", "[4] 14 iç kontrol testi"),
    ("sapma",   "src/sapma.py",   "[5] Bütçe-fiili köprüsü ve ayrıştırma"),
    ("pano",    "src/pano.py",    "[6a] HTML kapanış panosu"),
    ("excel",   "src/excel.py",   "[6b] Excel konsolidasyon paketi"),
]


def calistir(betik: str, g: Gunluk, ortam: dict | None = None) -> tuple[bool, float, str]:
    basla = time.time()
    try:
        sonuc = subprocess.run(
            [sys.executable, str(KOK / betik)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=str(KOK), env=ortam, timeout=900)
    except subprocess.TimeoutExpired:
        return False, time.time() - basla, "Zaman aşımı (900 sn)"
    sure = time.time() - basla
    if sonuc.returncode != 0:
        kuyruk = (sonuc.stderr or sonuc.stdout or "").strip().splitlines()
        return False, sure, "\n".join(kuyruk[-12:])
    return True, sure, sonuc.stdout


def main():
    ayrıstirici = argparse.ArgumentParser(
        description="MizanKöprü boru hattı")
    ayrıstirici.add_argument("--veri-uret", action="store_true",
                             help="önce sentetik demo veriyi üret")
    ayrıstirici.add_argument("--baslangic", default=None,
                             help="bu adımdan itibaren çalıştır")
    ayrıstirici.add_argument("--zeka-kapali", action="store_true",
                             help="yapay zekâ katmanını atla")
    a = ayrıstirici.parse_args()

    g = Gunluk("boru")
    y = yukle()
    g.bilgi(y.ozet())

    import os
    ortam = dict(os.environ)
    if a.zeka_kapali:
        ortam["ANTHROPIC_API_KEY"] = ""
        ortam["MIZANKOPRU_ZEKA"] = "kapali"
        g.uyari("Yapay zekâ katmanı KAPALI — yorum metinleri üretilmeyecek. "
                "Boru hattının ürettiği rakamların hiçbiri değişmez.")

    plan = list(ADIMLAR)
    if a.baslangic:
        adlar = [x[0] for x in ADIMLAR]
        if a.baslangic not in adlar:
            g.hata(f"Bilinmeyen adım: {a.baslangic}. Seçenekler: {', '.join(adlar)}")
            return 1
        plan = plan[adlar.index(a.baslangic):]

    if a.veri_uret:
        plan.insert(0, ("veri_uret", "araclar/veri_uret.py",
                        "[0] Sentetik ERP demo verisi (14 tuzakla)"))

    g.bilgi(f"{len(plan)} adım çalıştırılacak\n")
    sonuclar, toplam = [], 0.0
    for i, (ad, betik, aciklama) in enumerate(plan, 1):
        print(f"  [{i}/{len(plan)}] {aciklama} ... ", end="", flush=True)
        tamam, sure, cikti = calistir(betik, g, ortam)
        toplam += sure
        uyari = cikti.count("\n !") if tamam else 0
        print(f"{'tamam' if tamam else 'HATA'}  ({sure:.1f} sn"
              + (f", {uyari} uyarı" if uyari else "") + ")")
        sonuclar.append([ad, aciklama[:46], "tamam" if tamam else "HATA",
                         f"{sure:.1f}", uyari])
        g.iz("boru_adim", adim=ad, basarili=tamam, sure_sn=round(sure, 2),
             uyari=uyari)
        if not tamam:
            g.hata(f"[{ad}] başarısız — boru hattı durduruldu.\n{cikti}")
            tablo_yaz("Boru hattı (yarıda kesildi)", sonuclar,
                      ["Adım", "İş", "Durum", "Süre", "Uyarı"])
            g.bitir({"durum": "hata", "kirilan_adim": ad})
            return 1

    tablo_yaz("Boru hattı", sonuclar, ["Adım", "İş", "Durum", "Süre sn", "Uyarı"])

    # ---- Üretilen dosyalar ----
    ciktilar = []
    for ad in ["pano.html", "konsolidasyon_paketi.xlsx", "bulgular.csv",
               "sapma_koprusu.csv", "sapma_kalem.csv", "sapma_yorumu.md",
               "bulgu_triyaji.json", "hesap_eslesme_onerisi.csv"]:
        yol = CIKTI_DIZIN / ad
        if yol.exists():
            ciktilar.append([ad, f"{yol.stat().st_size/1024:.0f} KB"])
    tablo_yaz("Çıktılar (cikti/)", ciktilar, ["Dosya", "Boyut"])

    # ---- Kapanış durumu ----
    import pandas as pd
    bulgu_yolu = CIKTI_DIZIN / "bulgular.csv"
    if bulgu_yolu.exists():
        b = pd.read_csv(bulgu_yolu, encoding="utf-8-sig")
        kritik = int((b["onem"] == "kritik").sum())
        g.bilgi("")
        if kritik:
            g.uyari(f"KAPANIŞ İMZALANAMAZ — {kritik} kritik bulgu açık "
                    f"(toplam {len(b)} bulgu). Ayrıntı: cikti/pano.html")
        else:
            g.iyi(f"Kritik bulgu yok — kapanış imzalanabilir "
                  f"({len(b)} bulgu toplam).")

    g.bilgi(f"\nToplam süre: {toplam:.1f} sn")
    g.bitir({"adim": len(plan), "toplam_sure_sn": round(toplam, 1)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
