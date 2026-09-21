# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ. BORU HATTI: tüm adımları sırayla çalıştıran orkestratör.

KULLANIM
  py src/boru.py                  tüm boru hattı (mevcut veri/girdi ile)
  py src/boru.py --veri-uret      önce sentetik demo veriyi de üret
  py src/boru.py --baslangic esle  belirtilen adımdan itibaren
  py src/boru.py --zeka-kapali    yapay zekâ katmanını atla (rakamlar değişmez)

TASARIM
  Her adım ayrı bir süreç olarak çalışır. Bir adım hata verirse boru hattı
  DURUR, yanlış veriyle bir sonraki adıma geçmek, hatayı görünmez kılar.
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
    # Son adım kasıtlı olarak bir SINAMA: ham dosyayı boru hattından
    # bağımsız yeniden okur ve çıktılardaki rakamlarla karşılaştırır.
    # Çökmeden yanlış sonuç üreten bir boru hattı, çöken bir boru
    # hattından daha tehlikelidir; bu adım onu yakalamak için var.
    ("capraz",  "araclar/capraz_dogrula.py",
     "[7] Çapraz doğrulama: ham dosya ↔ çıktı"),
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
    ayrıstirici.add_argument("--kaynak-zorla", action="store_true",
                             help="Kaynak doğrulama uyarılarını görmezden gel "
                                  "(demo ve kullanıcı verisi karışıksa bile "
                                  "devam et). Sonuçlar güvenilmezdir.")
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
    if getattr(a, "kaynak_zorla", False):
        ortam["MIZANKOPRU_KAYNAK_ZORLA"] = "1"
        g.uyari("Yapay zekâ katmanı KAPALI, yorum metinleri üretilmeyecek. "
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
            g.hata(f"[{ad}] başarısız, boru hattı durduruldu.\n{cikti}")
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

    # ---- Bu çalıştırma neyi işledi ----
    # En sık ve en pahalı hata sınıfı, kullanıcının yüklediği dosya yerine
    # başka bir veriden üretilmiş çıktıya bakmaktır. Boru hattı bittiğinde
    # köken ve kapsam ekranda tekrar yazılır.
    import json as _json
    koken_yolu = KOK / "veri" / "ara" / "koken.json"
    if koken_yolu.exists():
        kk = _json.loads(koken_yolu.read_text(encoding="utf-8"))
        g.bilgi("")
        g.bilgi("Bu çıktılar ŞU dosyalardan üretildi:")
        for dd in kk.get("dosyalar", []):
            g.bilgi(f"    {dd.get('ad')}  ({dd.get('tip')}, "
                    f"{dd.get('sirket') or '-'}, {dd.get('kb', 0)} KB, "
                    f"parmak {dd.get('parmak', '')[:12]})")
        vs = kk.get("veri_seti")
        if vs == "demo":
            g.uyari("Bu bir DEMO VERİ çalıştırmasıdır, gerçek kapanış değildir.")
        elif vs == "KARISIK":
            g.uyari("KARIŞIK kaynak: demo ve kullanıcı dosyaları bir arada "
                    "işlendi. Rakamlar güvenilir DEĞİLDİR.")
        if not kk.get("guvenilir", True):
            g.uyari("Kaynak doğrulaması zorlanarak geçildi; sonuçlara "
                    "güvenilemez.")
    kapsam_yolu = KOK / "veri" / "ara" / "kapsam.json"
    if kapsam_yolu.exists():
        kp = _json.loads(kapsam_yolu.read_text(encoding="utf-8"))
        g.bilgi(f"Kapsam: {', '.join(kp.get('sirketler', []))} · "
                f"{', '.join(kp.get('donemler', []))}")
        if kp.get("kapsam_disi"):
            g.uyari("Kapsam dışı (verisi yüklenmedi, çıktılarda YOK): "
                    + ", ".join(kp["kapsam_disi"]))
    atlanan_sayisi = 0
    atl_yolu = CIKTI_DIZIN / "atlanan_testler.json"
    if atl_yolu.exists():
        at = _json.loads(atl_yolu.read_text(encoding="utf-8"))
        atlanan_sayisi = len(at)
        if at:
            g.uyari(f"{len(at)} kontrol testi veri yokluğundan çalıştırılamadı: "
                    + ", ".join(a.get("kod", "") for a in at))
            g.uyari("Bu testlerin kapsadığı riskler DENETLENMEMİŞTİR.")

    # ---- Kapanış durumu ----
    import pandas as pd
    bulgu_yolu = CIKTI_DIZIN / "bulgular.csv"
    if bulgu_yolu.exists():
        b = pd.read_csv(bulgu_yolu, encoding="utf-8-sig")
        kritik = int((b["onem"] == "kritik").sum())
        g.bilgi("")
        if kritik:
            g.uyari(f"KAPANIŞ İMZALANAMAZ, {kritik} kritik bulgu açık "
                    f"(toplam {len(b)} bulgu). Ayrıntı: cikti/pano.html")
        elif atlanan_sayisi:
            g.uyari(f"KOŞULLU: çalıştırılan testlerde kritik bulgu yok "
                    f"({len(b)} bulgu toplam), ancak {atlanan_sayisi} test "
                    f"veri eksikliğinden çalıştırılamadı. Kapanış yalnızca "
                    f"yüklenen verinin kapsadığı riskler için temizdir.")
        else:
            g.iyi(f"Kritik bulgu yok, kapanış imzalanabilir "
                  f"({len(b)} bulgu toplam).")

    g.bilgi(f"\nToplam süre: {toplam:.1f} sn")
    g.bitir({"adim": len(plan), "toplam_sure_sn": round(toplam, 1)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
