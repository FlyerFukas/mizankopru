# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ · ÖĞRENME KATMANI NÖTR MÜ?

NE SINAR
  Boru hattını önce öğrenme katmanı açık, sonra kapalı çalıştırır ve tutar
  taşıyan bütün çıktıların özetini karşılaştırır. İkisi birebir aynı
  olmalıdır.

NEDEN
  Projenin iddiası şu: model hiçbir tutarı değiştirmez, yalnızca öneri
  üretir ve sıralar. Bu bir iddia olarak kalmamalı, ölçülmelidir. Aynı
  sınamanın yapay zekâ katmanı için yapılanı (`--zeka-kapali`) bu projeyi
  mülakatta anlatılabilir kılan şeydi; öğrenme katmanı da aynı kurala tabi.

  Bir modelin kapanış rakamını sessizce değiştirmesi, denetim aracında
  yapılabilecek en ağır hatadır: imzayı atan kişi neye baktığını bilemez.

ÇALIŞTIRMA
  py araclar/ogrenme_notr_mu.py
ÇIKIŞ KODU
  0 = katman nötr · 1 = tutarlar değişti, kural ihlali
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

from gunluk import Gunluk, tablo_yaz                          # noqa: E402

# Tutar taşıyan çıktılar. Öneri ve rapor dosyaları kasıtlı olarak DIŞARIDA:
# onların değişmesi beklenen davranıştır, tutarların değişmesi değil.
TUTAR_DOSYALARI = [
    ("veri/ara", "mizan.csv"),
    ("veri/ara", "mizan_eslenmis.csv"),
    ("veri/ara", "cevrilmis.csv"),
    ("veri/ara", "konsolide.csv"),
    ("veri/ara", "cevrim_farki.csv"),
    ("cikti", "bulgular.csv"),
    ("cikti", "oranlar.csv"),
    ("cikti", "dikey_analiz.csv"),
]


def parmak_izleri() -> dict[str, str]:
    """Her tutar dosyasının ayrı özeti; hangisinin değiştiği görülebilsin."""
    cikti = {}
    for dizin, ad in TUTAR_DOSYALARI:
        yol = KOK / dizin / ad
        cikti[f"{dizin}/{ad}"] = (
            hashlib.md5(yol.read_bytes()).hexdigest() if yol.exists() else "-")
    return cikti


def boru_calistir(g: Gunluk, ogrenme_kapali: bool) -> bool:
    ortam = dict(os.environ)
    ortam["MIZANKOPRU_OGRENME"] = "kapali" if ogrenme_kapali else "acik"
    durum = "KAPALI" if ogrenme_kapali else "AÇIK"
    g.bilgi(f"Boru hattı çalışıyor, öğrenme katmanı {durum}...")
    sonuc = subprocess.run([sys.executable, str(KOK / "src" / "boru.py")],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=str(KOK), env=ortam,
                           timeout=1800)
    if sonuc.returncode != 0:
        g.hata(f"Boru hattı başarısız (öğrenme {durum}):\n"
               + "\n".join((sonuc.stdout or "").splitlines()[-10:]))
        return False
    return True


def main() -> int:
    g = Gunluk("ogrenme_notr")

    if not boru_calistir(g, ogrenme_kapali=False):
        g.bitir({"durum": "boru_hatasi"})
        return 1
    acik = parmak_izleri()

    if not boru_calistir(g, ogrenme_kapali=True):
        g.bitir({"durum": "boru_hatasi"})
        return 1
    kapali = parmak_izleri()

    satirlar, farkli = [], []
    for ad in acik:
        ayni = acik[ad] == kapali[ad]
        if not ayni:
            farkli.append(ad)
        satirlar.append([ad, acik[ad][:12], kapali[ad][:12],
                         "aynı" if ayni else "FARKLI"])
    tablo_yaz("Öğrenme katmanı açıkken ve kapalıyken tutar dosyaları",
              satirlar, ["Dosya", "Açık", "Kapalı", "Sonuç"])

    if farkli:
        g.hata(f"{len(farkli)} dosya değişti: " + ", ".join(farkli))
        g.hata("KURAL İHLALİ: öğrenme katmanı tutarları etkiliyor. "
               "Model yalnızca öneri üretmeli ve sıralamalıdır.")
        g.bitir({"durum": "ihlal", "farkli": len(farkli)})
        return 1

    g.iyi(f"{len(acik)} tutar dosyasının hepsi birebir aynı. "
          f"Öğrenme katmanı nötr: model hiçbir tutarı değiştirmiyor.")
    g.iz("ogrenme_notr", dosya=len(acik), farkli=0)
    g.bitir({"durum": "notr", "dosya": len(acik)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
