# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ · ÖĞRENME ALTYAPISI

GÖREV
  Gözetimli öğrenme modellerinin ortak iskeleti: kütüphane bağlama, taban
  çizgi karşılaştırması, çapraz doğrulama, model raporu ve model kaydı.
  Her model bu iskeleti kullanır; değerlendirme kuralı tek yerde durur.

DEĞİŞMEYEN KURAL
  Model hiçbir tutarı değiştirmez. Öneri üretir, sıralar, beklenti üretir.
  `--ogrenme-kapali` ile katman kapatıldığında üretilen bütün tutarlar
  birebir aynı kalmalıdır. Bkz. ENTEGRASYON-ML.md.

TABAN ÇİZGİSİNİ GEÇEMEYEN MODEL PROJEYE GİRMEZ
  Sınıflandırmada taban çizgi "en sık sınıfı söyle", regresyonda "bir önceki
  dönemin değerini söyle". Bir model bunu geçmiyorsa eklediği karmaşıklık
  bedava değildir. `rapor_uret()` bu karşılaştırmayı her seferinde yapar ve
  `gecti` alanına yazar.

SIZINTI
  Öğrenen her adım (vektörleştirme, ölçekleme, doldurma, özellik seçimi)
  modelin İÇİNDE, Pipeline olarak durmalıdır. Çapraz doğrulama döngüsünün
  dışında tüm veriye uygulanırsa test katının bilgisi eğitime sızar.
  gozetimli-ogrenme'nin ölçtüğü sahte kazanç bu hatada 20 puana kadar çıkar.

KÜTÜPHANE
  pip install scikit-learn
  pip install -e C:\\Users\\furka\\Music\\gozetimli-ogrenme
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sema import CIKTI_DIZIN, KOK                            # noqa: E402

MODEL_DIZIN = KOK / "modeller"


class OgrenmeYok(Exception):
    """Öğrenme katmanının bağımlılıkları kurulu değil."""


def kutuphane_durumu() -> dict:
    """Hangi bağımlılık var, hangisi yok. Çökmeden söyler."""
    durum = {}
    for ad, paket in (("sklearn", "scikit-learn"),
                      ("gozetimli", "gozetimli-ogrenme"),
                      ("joblib", "joblib")):
        try:
            modul = __import__(ad)
            durum[paket] = getattr(modul, "__version__", "?")
        except ImportError:
            durum[paket] = None
    return durum


def kutuphane_iste():
    """Bağımlılık yoksa ne yapılacağını söyleyerek durur."""
    eksik = [ad for ad, s in kutuphane_durumu().items() if s is None]
    if not eksik:
        return
    raise OgrenmeYok(
        "Öğrenme katmanı için eksik bağımlılık: " + ", ".join(eksik) + "\n\n"
        "Kurulum:\n"
        "    py -m pip install scikit-learn\n"
        "    py -m pip install -e C:\\Users\\furka\\Music\\gozetimli-ogrenme\n\n"
        "Bu katman olmadan boru hattı tam çalışır; yalnızca model önerileri "
        "üretilmez. Üretilen hiçbir tutar değişmez.")


# ======================================================================
# TABAN ÇİZGİLER
# ======================================================================

def taban_cizgi_siniflandirma(y_egitim, y_test) -> dict:
    """En sık sınıfı tahmin eden aptal model.

    Bir sınıflandırıcının gerçek katkısı, bu tahmini ne kadar geçtiğidir.
    Dengesiz bir veri setinde %85 doğruluk, sınıfların %85'i zaten aynıysa
    hiçbir şey öğrenilmediği anlamına gelir."""
    from gozetimli.metrikler.siniflandirma import dogruluk, f1_skoru

    y_egitim = list(y_egitim)
    y_test = np.asarray(list(y_test))
    if not y_egitim:
        return {"dogruluk": 0.0, "makro_f1": 0.0, "sinif": None}
    en_sik = Counter(y_egitim).most_common(1)[0][0]
    tahmin = np.full(len(y_test), en_sik, dtype=object)
    return {
        "dogruluk": float(dogruluk(y_test, tahmin)),
        "makro_f1": float(f1_skoru(y_test, tahmin, ortalama="makro")),
        "sinif": str(en_sik),
    }


def taban_cizgi_regresyon(y_gecmis, y_test) -> dict:
    """Naif tahmin: bir önceki dönemin değeri.

    Zaman serisinde aşılması en zor taban çizgi budur. Geçemeyen bir model,
    geçmişi tekrar etmekten daha kötü demektir."""
    from gozetimli.metrikler.regresyon import mae, rmse, smape

    y_test = np.asarray(list(y_test), dtype=float)
    onceki = float(np.asarray(list(y_gecmis), dtype=float)[-1]) if len(
        list(y_gecmis)) else 0.0
    tahmin = np.full(len(y_test), onceki, dtype=float)
    return {"mae": float(mae(y_test, tahmin)),
            "rmse": float(rmse(y_test, tahmin)),
            "smape": float(smape(y_test, tahmin))}


# ======================================================================
# DEĞERLENDİRME VE RAPOR
# ======================================================================

def ilk_k_dogruluk(model, X, y, k: int = 3) -> float:
    """Doğru sınıf, modelin en olası k tahmini arasında mı?

    Öneri üreten bir sistemde tek tahmin doğruluğu yanıltıcıdır: insan
    üç seçenek arasından seçiyorsa ölçü de bu olmalıdır."""
    if not hasattr(model, "predict_proba"):
        return float("nan")
    olasilik = model.predict_proba(X)
    siniflar = np.asarray(model.classes_)
    ilk_k = np.argsort(-olasilik, axis=1)[:, :k]
    y = np.asarray(list(y))
    isabet = [y[i] in siniflar[ilk_k[i]] for i in range(len(y))]
    return float(np.mean(isabet)) if isabet else 0.0


def rapor_uret(ad: str, *, veri: dict, bolme: str, capraz,
               taban: dict, olcut: str, ek: dict | None = None) -> dict:
    """Bir modelin üretimde kullanılıp kullanılamayacağını belgeler.

    `gecti` alanı tek soruyu cevaplar: model taban çizgiyi geçti mi?
    Geçmediyse `cikti/model_raporu.json` bunu yazar ve model kaydedilmez."""
    ozet = capraz.ozet()
    model_skor = ozet[olcut]["ortalama"]
    taban_skor = float(taban.get(olcut, 0.0))
    asiri = ozet[olcut].get("asiri_ogrenme_farki")

    return {
        "model": ad,
        "zaman": datetime.now().isoformat(timespec="seconds"),
        "veri": veri,
        "bolme": bolme,
        "olcut": olcut,
        "skorlar": ozet,
        "taban_cizgi": taban,
        "model_skoru": model_skor,
        "taban_skoru": taban_skor,
        "kazanc": round(model_skor - taban_skor, 4),
        "gecti": bool(model_skor > taban_skor),
        "asiri_ogrenme_farki": asiri,
        "asiri_ogrenme_uyarisi": bool(asiri is not None and asiri > 0.15),
        **(ek or {}),
    }


def rapor_yaz(rapor: dict, dosya: str = "model_raporu.json") -> Path:
    """Model raporunu diske yazar. Bu dosya olmadan model kullanılmaz."""
    CIKTI_DIZIN.mkdir(parents=True, exist_ok=True)
    yol = CIKTI_DIZIN / dosya
    mevcut = []
    if yol.exists():
        try:
            mevcut = json.loads(yol.read_text(encoding="utf-8"))
            if isinstance(mevcut, dict):
                mevcut = [mevcut]
        except json.JSONDecodeError:
            mevcut = []
    # Aynı modelin eski raporu değil, en son hâli tutulur.
    mevcut = [r for r in mevcut if r.get("model") != rapor.get("model")]
    mevcut.append(rapor)
    yol.write_text(json.dumps(mevcut, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    return yol


def rapor_oku(model_adi: str, dosya: str = "model_raporu.json") -> dict | None:
    yol = CIKTI_DIZIN / dosya
    if not yol.exists():
        return None
    try:
        kayitlar = json.loads(yol.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(kayitlar, dict):
        kayitlar = [kayitlar]
    for r in kayitlar:
        if r.get("model") == model_adi:
            return r
    return None


# ======================================================================
# MODEL KAYDI
# ======================================================================

# GÜVENLİK: joblib, altında pickle kullanır ve pickle açmak KOD ÇALIŞTIRMAKTIR.
# Buradaki dosyalar yalnızca bu makinede, bu boru hattı tarafından üretilir ve
# `modeller/` dizini .gitignore'dadır, depoya girmez. Başka bir yerden gelen
# bir .joblib dosyasını bu dizine KOPYALAMAYIN: güvenilmeyen bir model dosyası
# açıldığı anda içindeki kod çalışır. Model paylaşmanız gerekiyorsa modeli
# değil, onu üreten betiği ve eğitim verisini paylaşın.
def model_kaydet(model, ad: str, rapor: dict) -> Path:
    """Modeli ve raporunu birlikte saklar.

    Rapor modelin yanında durur: bir tahmini sorgulayan kişi, modelin hangi
    veriyle eğitildiğini ve taban çizgiyi geçip geçmediğini görebilmelidir."""
    import joblib

    MODEL_DIZIN.mkdir(parents=True, exist_ok=True)
    yol = MODEL_DIZIN / f"{ad}.joblib"
    joblib.dump({"model": model, "rapor": rapor}, yol)
    return yol


def model_yukle(ad: str):
    """Kayıtlı modeli döner; yoksa (None, None).

    Model yoksa çağıran taraf çökmemeli, öneri üretmemelidir.

    Yalnızca `modeller/` dizininden ve yalnızca ad ile yüklenir; dışarıdan
    yol kabul edilmez. Dizin dışındaki bir dosyayı açmak, güvenilmeyen bir
    pickle açmak demektir (bkz. model_kaydet üstündeki not)."""
    import joblib

    if "/" in ad or "\\" in ad or ad.startswith("."):
        raise ValueError("Model adı bir yol olamaz; yalnızca modeller/ "
                         "dizinindeki adlar yüklenir.")
    yol = MODEL_DIZIN / f"{ad}.joblib"
    if not yol.exists():
        return None, None
    try:
        paket = joblib.load(yol)
    except Exception:
        return None, None
    return paket.get("model"), paket.get("rapor")


def ogrenme_kapali() -> bool:
    """Öğrenme katmanı kapalı mı?

    `--ogrenme-kapali` bayrağı ya da MIZANKOPRU_OGRENME=kapali ortam
    değişkeni. Kapalıyken üretilen bütün tutarlar birebir aynı kalır."""
    import os
    return ("--ogrenme-kapali" in sys.argv
            or os.environ.get("MIZANKOPRU_OGRENME") == "kapali")
