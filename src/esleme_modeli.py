# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ · HESAP EŞLEME SINIFLANDIRICISI (Sistem 1)

GÖREV
  Yerel hesap ADINDAN grup hesap kodunu tahmin eder. Eşleme tablosunda
  karşılığı bulunmayan bir hesap için insan onayına sunulacak öneri üretir.

NEDEN GEREKLİ
  Alt hesaplar (120.01 ALICILAR YURTİÇİ), şirketin kendi açtığı serbest
  hesaplar ve farklı hesap planları eşleme tablosunda yer almaz. Bugün bu
  boşluğu insan ya da bir LLM çağrısı dolduruyor. Model çevrimdışı çalışır,
  maliyeti sıfırdır ve her onaylanan eşlemeyle eğitim verisi büyür.

İKİ MODEL, İKİ SORU
  ad+kod    : hesap adı artı kodun ilk iki hanesi. ÜRETİME GİREN MODEL.
              Askıdaki bir hesabın kodu vardır (120.01 gibi), yalnızca
              eşleme tablosunda tam karşılığı yoktur; ilk iki hane TDHP'de
              güçlü bir sinyaldir (1 dönen varlık, 6 gelir tablosu...).
  ad        : yalnızca hesap adından tahmin. Kod önekinin anlamsız olduğu
              durumda (standart dışı ERP kodları) modelin düşeceği alt
              sınır. Referans olarak ölçülür ve raporlanır.
  Üçüncü bir ölçüm, hesap planı bazında grup bölmesiyle "hiç görülmemiş
  bir hesap planı" senaryosunu sınar. Üç sayı da raporlanır; iyi görüneni
  seçip diğerlerini saklamak modelin gerçek sınırını gizlemek olur.

SIZINTI
  TF-IDF sözlüğü Pipeline içindedir; çapraz doğrulama döngüsünün her katında
  yalnızca o katın eğitim verisinden çıkarılır. Sözlüğü tüm veriden çıkarmak
  test katındaki kelimeleri eğitimde görülmüş yapar ve skoru şişirir.

MODEL HİÇBİR TUTARI DEĞİŞTİRMEZ
  Çıktısı bir ÖNERİDİR. Eşleme tablosuna yazılması insan onayına bağlıdır.

ÇALIŞTIRMA
  py src/esleme_modeli.py            # eğit, ölç, raporla, kaydet
  py src/esleme_modeli.py --oner     # askıdaki hesaplar için öneri üret
ÇIKTI
  cikti/model_raporu.json · modeller/esleme.joblib
  cikti/esleme_model_onerisi.csv  (--oner ile)
"""
from __future__ import annotations

import sys
from pathlib import Path

from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gunluk import Gunluk, tablo_yaz                          # noqa: E402
from sema import ARA_DIZIN, CIKTI_DIZIN, yukle                # noqa: E402
import ogrenme as O                                           # noqa: E402

MODEL_ADI = "esleme"
TOHUM = 42

# Bir sınıfın çapraz doğrulamaya girebilmesi için gereken en az örnek.
# TabakaliKKat, k kattan az örneği olan sınıfı bölemez.
ASGARI_ORNEK = 5


def ozellik_cercevesi(d: pd.DataFrame, kod_kullan: bool) -> pd.DataFrame:
    """Ham eşleme tablosunu model girdisine çevirir.

    Metin alanı hesap adıdır. Kod kullanılıyorsa kodun ilk iki hanesi
    metne bir belirteç olarak eklenir; ham kodun tamamı ASLA verilmez,
    çünkü model o zaman tabloyu ezberler ve görmediği hesapta çalışmaz."""
    metin = d["yerel_ad"].fillna("").astype(str).str.strip()
    if kod_kullan:
        onek = d["yerel_kod"].fillna("").astype(str).str[:2]
        metin = "kod" + onek + " " + metin
    return pd.DataFrame({"metin": metin, "plan": d["plan_kodu"].astype(str)})


# İç içe çapraz doğrulamada denenecek ayarlar. Az veri (245 örnek) ve çok
# özellik (binlerce karakter n-gramı) olduğu için asıl mesele düzenlileştirme
# gücüdür: C küçüldükçe model ezberlemekten uzaklaşır.
IZGARA = [
    {"C": c, "ngram": n, "min_df": m}
    for c in (0.5, 1.0, 5.0)
    for n in ((2, 4), (2, 5))
    for m in (1, 2)
]


def boru_hatti_kur(kod_kullan: bool, C: float = 1.0,
                   ngram: tuple = (2, 5), min_df: int = 1):
    """Vektörleştirme + sınıflandırıcı, tek Pipeline.

    Öğrenen her adım burada: çapraz doğrulama bu nesneyi her katta
    yeniden eğitir, böylece test katının hiçbir bilgisi eğitime sızmaz."""
    from sklearn.compose import ColumnTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    # Karakter n-gramı, Türkçe ekler ve kısaltmalar yüzünden kelime
    # n-gramından daha dayanıklı: "ALICILAR" ile "ALICILAR-YURTİÇİ"
    # kelime düzeyinde farklı, karakter düzeyinde yakındır.
    metin_vekt = TfidfVectorizer(analyzer="char_wb", ngram_range=ngram,
                                 min_df=min_df, sublinear_tf=True,
                                 lowercase=True)
    donusum = ColumnTransformer([
        ("metin", metin_vekt, "metin"),
        ("plan", OneHotEncoder(handle_unknown="ignore"), ["plan"]),
    ])
    return Pipeline([
        ("donusum", donusum),
        ("model", LogisticRegression(max_iter=2000, C=C,
                                     class_weight="balanced",
                                     random_state=TOHUM)),
    ])


def veriyi_hazirla(y, g: Gunluk):
    """Eşleme tablosunu eğitim verisine çevirir, seyrek sınıfları ayırır."""
    d = y.eslesme.copy()
    d = d[(d["yerel_ad"].astype(str).str.strip() != "")
          & (d["grup_kod"].astype(str).str.strip() != "")]

    sayim = d["grup_kod"].value_counts()
    yeterli = sayim[sayim >= ASGARI_ORNEK].index
    seyrek = sayim[sayim < ASGARI_ORNEK]

    egitilebilir = d[d["grup_kod"].isin(yeterli)].reset_index(drop=True)
    if len(seyrek):
        # Bu sınıflar atılmıyor, yalnızca ÖLÇÜMÜN dışında tutuluyor:
        # 5 katlı tabakalı bölme 5'ten az örnekli sınıfı bölemez. Son
        # model yine tüm veriyle eğitiliyor, öneri üretebiliyor.
        g.uyari(f"{len(seyrek)} grup kodunda {ASGARI_ORNEK}'ten az örnek var; "
                f"çapraz doğrulama ölçümünün dışında tutuldu "
                f"(son model yine hepsiyle eğitiliyor).")
        g.bilgi("    " + ", ".join(f"{k}({v})" for k, v in seyrek.items()))
    return d.reset_index(drop=True), egitilebilir, seyrek.to_dict()


def ilk_k_oof(model, X, y, bolucu, k: int = 3) -> float:
    """Doğru sınıfın, örneği GÖRMEMİŞ bir modelin ilk k önerisinde
    bulunma oranı.

    Her katta sınıf kümesi farklı olabilir (seyrek sınıf o katın eğitim
    verisinde hiç bulunmayabilir), bu yüzden sıralama kat modelinin kendi
    `classes_` dizisiyle yapılır."""
    from gozetimli.dogrulama.capraz import klonla

    y = np.asarray(list(y))
    isabet = np.zeros(len(y), dtype=bool)
    for egitim_idx, test_idx in bolucu.bol(X, y):
        kat = klonla(model)
        kat.fit(X.iloc[egitim_idx], y[egitim_idx])
        olasilik = kat.predict_proba(X.iloc[test_idx])
        siniflar = np.asarray(kat.classes_)
        ilk_k = np.argsort(-olasilik, axis=1)[:, :k]
        for sira, indeks in enumerate(test_idx):
            isabet[indeks] = y[indeks] in siniflar[ilk_k[sira]]
    return float(np.mean(isabet))


def olc(ad: str, kod_kullan: bool, egitilebilir: pd.DataFrame, g: Gunluk):
    """Bir modeli çapraz doğrulamayla ölçer ve raporunu üretir."""
    from gozetimli.dogrulama.bolme import TabakaliKKat
    from gozetimli.dogrulama.capraz import (capraz_dogrula,
                                             ic_ice_capraz_dogrula)
    from gozetimli.metrikler.siniflandirma import dogruluk, f1_skoru

    X = ozellik_cercevesi(egitilebilir, kod_kullan)
    yv = egitilebilir["grup_kod"].to_numpy()

    bolucu = TabakaliKKat(5, karistir=True, tohum=TOHUM)
    makro_f1 = lambda a, b: f1_skoru(a, b, ortalama="makro")

    # Hiperparametre seçimi İÇ İÇE çapraz doğrulamayla ölçülür. Ayarı tüm
    # veri üzerinde CV ile seçip aynı CV skorunu "modelin başarısı" diye
    # raporlamak, seçim sürecinin bilgisini skora sızdırır.
    ic_ice_skor, secilen_ayarlar = ic_ice_capraz_dogrula(
        lambda **par: boru_hatti_kur(kod_kullan, **par), X, yv,
        dis_bolucu=bolucu,
        ic_bolucu=TabakaliKKat(3, karistir=True, tohum=TOHUM),
        izgara=IZGARA, metrik=makro_f1)
    en_sik_ayar = Counter(tuple(sorted(a.items()))
                          for a in secilen_ayarlar).most_common(1)[0][0]
    ayar = dict(en_sik_ayar)

    sonuc = capraz_dogrula(
        boru_hatti_kur(kod_kullan, **ayar), X, yv, bolucu=bolucu,
        metrikler={"makro_f1": makro_f1, "dogruluk": dogruluk},
        egitim_skoru=True)

    # Taban çizgi aynı bölmeyle ölçülür: karşılaştırma ancak aynı
    # koşullarda anlamlıdır.
    taban_f1, taban_dog = [], []
    for egitim_idx, test_idx in bolucu.bol(X, yv):
        t = O.taban_cizgi_siniflandirma(yv[egitim_idx], yv[test_idx])
        taban_f1.append(t["makro_f1"])
        taban_dog.append(t["dogruluk"])
    taban = {"makro_f1": float(np.mean(taban_f1)),
             "dogruluk": float(np.mean(taban_dog)),
             "kural": "en sık grup kodunu söyle"}

    # İlk 3 öneri doğruluğu: insan üç seçenek arasından seçiyor, ölçü de
    # bu olmalı. Kendi out-of-fold döngümüzle hesaplanıyor, çünkü
    # gozetimli-ogrenme'nin capraz_tahmin(olasilik=True) fonksiyonu
    # predict_proba[:, 1] döndürür; bu ikili sınıflandırma içindir ve
    # 24 sınıflı bir problemde anlamsızdır.
    ilk3 = ilk_k_oof(boru_hatti_kur(kod_kullan, **ayar), X, yv, bolucu, k=3)

    return O.rapor_uret(
        f"{MODEL_ADI}_{ad}",
        veri={"kaynak": "yapilandirma/hesap_eslesme.csv",
              "ornek": int(len(egitilebilir)),
              "sinif": int(len(np.unique(yv))),
              "ozellik": "hesap adı" + (" + kod öneki (2 hane)"
                                        if kod_kullan else "")},
        bolme="TabakaliKKat(5, karistir=True, tohum=42)",
        capraz=sonuc, taban=taban, olcut="makro_f1",
        ek={"ilk3_dogruluk": round(ilk3, 4),
            "ic_ice_cv_makro_f1": round(float(np.mean(ic_ice_skor)), 4),
            "ic_ice_cv_std": round(float(np.std(ic_ice_skor, ddof=1)), 4),
            "secilen_ayar": ayar,
            "secim_sizintisi": round(
                float(np.mean(sonuc.kat_skorlari["makro_f1"]))
                - float(np.mean(ic_ice_skor)), 4)}), sonuc, ayar


def plan_disi_olc(tum: pd.DataFrame, g: Gunluk) -> dict:
    """Hiç görülmemiş bir hesap planında model ne yapar?

    Rastgele bölme, aynı hesap planından benzer hesapları hem eğitime hem
    teste koyar ve modeli olduğundan iyi gösterir. GrupKKat ile bölme
    hesap planına göre yapılırsa model, eğitimde HİÇ görmediği bir planla
    sınanır. Skorun düşük çıkması bir kusur değil, modelin nerede
    kullanılamayacağının ölçüsüdür."""
    from gozetimli.dogrulama.bolme import GrupKKat
    from gozetimli.dogrulama.capraz import capraz_dogrula
    from gozetimli.metrikler.siniflandirma import dogruluk, f1_skoru

    planlar = tum["plan_kodu"].astype(str)
    if planlar.nunique() < 2:
        return {"durum": "tek plan var, ölçülemedi"}

    # Grup bölmesinde her katın eğitim tarafında hedef sınıfların bir kısmı
    # hiç bulunmayabilir; bu gerçek senaryonun kendisidir.
    X = ozellik_cercevesi(tum, kod_kullan=True)
    yv = tum["grup_kod"].to_numpy()
    kat = min(planlar.nunique(), 3)
    # GrupKKat, grup etiketlerinde .item() çağırır; pandas'tan gelen object
    # dtype dizide elemanlar düz Python str olduğu için bu çağrı çöker.
    # Grupları tam sayıya çevirmek hem bu sorunu aşar hem de bölmenin
    # anlamını değiştirmez.
    grup_no = pd.factorize(planlar)[0]
    try:
        sonuc = capraz_dogrula(
            boru_hatti_kur(True), X, yv,
            bolucu=GrupKKat(kat), gruplar=grup_no,
            metrikler={"makro_f1": lambda a, b: f1_skoru(a, b,
                                                         ortalama="makro"),
                       "dogruluk": dogruluk})
    except Exception as e:
        return {"durum": f"ölçülemedi: {type(e).__name__}: {e}"}

    ozet = sonuc.ozet()
    return {"bolme": f"GrupKKat({kat}) · gruplar = hesap planı",
            "makro_f1": ozet["makro_f1"]["ortalama"],
            "dogruluk": ozet["dogruluk"]["ortalama"],
            "katlar": ozet["makro_f1"]["katlar"]}


def egit(g: Gunluk):
    y = yukle()
    tum, egitilebilir, seyrek = veriyi_hazirla(y, g)
    g.bilgi(f"{len(tum)} eşleme, {tum['grup_kod'].nunique()} grup kodu. "
            f"Ölçüme giren: {len(egitilebilir)} satır, "
            f"{egitilebilir['grup_kod'].nunique()} sınıf.")

    raporlar = []
    ayarlar = {}
    for ad, kod_kullan in (("ad", False), ("ad_kod", True)):
        rapor, _, ayar = olc(ad, kod_kullan, egitilebilir, g)
        O.rapor_yaz(rapor)
        raporlar.append((ad, kod_kullan, rapor))
        ayarlar[ad] = ayar

    tablo_yaz(
        "Hesap eşleme modeli, çapraz doğrulama (5 kat, tabakalı)",
        [[ad,
          f"{r['model_skoru']:.4f}",
          f"{r['ic_ice_cv_makro_f1']:.4f}",
          f"{r['secim_sizintisi']:+.4f}",
          f"{r['taban_skoru']:.4f}",
          f"{r['skorlar']['dogruluk']['ortalama']:.4f}",
          f"{r['ilk3_dogruluk']:.4f}",
          f"{r['asiri_ogrenme_farki']:+.4f}",
          "GEÇTİ" if r["gecti"] else "KALDI"]
         for ad, _, r in raporlar],
        ["Özellik", "Makro F1", "İç içe CV", "Seçim sız.", "Taban F1",
         "Doğruluk", "İlk 3", "Ezber farkı", "Sonuç"])
    g.bilgi("İç içe CV, hiperparametre seçiminin sızıntısı ayıklanmış "
            "dürüst skordur; 'Seçim sız.' ikisi arasındaki farktır.")
    for ad, _, r in raporlar:
        g.bilgi(f"    {ad}: seçilen ayar {r['secilen_ayar']}")

    # Hiç görülmemiş bir hesap planında ne olur?
    plan_disi = plan_disi_olc(tum, g)
    if "makro_f1" in plan_disi:
        g.uyari(f"Hiç görülmemiş hesap planında makro F1 "
                f"{plan_disi['makro_f1']:.4f} ({plan_disi['bolme']}). "
                f"Model, eğitildiği plan ailesinin dışında güvenilir DEĞİLDİR; "
                f"yeni bir plan için önce o plandan örnek eşleme girilmelidir.")
    else:
        g.bilgi(f"Plan dışı ölçüm: {plan_disi.get('durum')}")

    # Üretime giren model: ad + kod öneki. Askıdaki hesabın kodu vardır,
    # yalnızca eşleme tablosunda tam karşılığı yoktur; ilk iki haneyi
    # kullanmamak eldeki bilgiyi boşa harcamak olurdu.
    secilen = next(r for ad, _, r in raporlar if ad == "ad_kod")
    secilen["plan_disi_olcum"] = plan_disi
    O.rapor_yaz(secilen)
    if not secilen["gecti"]:
        g.uyari("Model taban çizgiyi geçemedi, KAYDEDİLMEDİ. "
                "Eklenen karmaşıklık bedava değildir.")
        g.bitir({"durum": "gecemedi"})
        return None

    if secilen["asiri_ogrenme_uyarisi"]:
        g.uyari(f"Ezber farkı {secilen['asiri_ogrenme_farki']:+.3f}: model "
                f"eğitim verisini test verisinden belirgin biçimde iyi "
                f"biliyor. Öneriler insan onayı olmadan uygulanmamalı.")

    # Son model TÜM veriyle eğitilir; ölçüm dışında bırakılan seyrek
    # sınıflar da öneri havuzuna girsin.
    son_model = boru_hatti_kur(kod_kullan=True, **ayarlar["ad_kod"])
    son_model.fit(ozellik_cercevesi(tum, True), tum["grup_kod"].to_numpy())
    yol = O.model_kaydet(son_model, MODEL_ADI, secilen)
    g.iyi(f"Model kaydedildi: {yol}")
    g.bilgi(f"Makro F1 {secilen['model_skoru']:.3f} "
            f"(taban {secilen['taban_skoru']:.3f}), "
            f"ilk 3 öneri doğruluğu {secilen['ilk3_dogruluk']:.3f}")
    g.iz("esleme_modeli_egitildi", **{k: secilen[k] for k in
                                      ("model_skoru", "taban_skoru",
                                       "kazanc", "gecti")})
    g.bitir({"makro_f1": secilen["model_skoru"],
             "kazanc": secilen["kazanc"],
             "seyrek_sinif": len(seyrek)})
    return son_model


def oner(g: Gunluk, ilk_k: int = 3):
    """Askıda kalan hesaplar için öneri üretir. Hiçbir şeyi uygulamaz."""
    model, rapor = O.model_yukle(MODEL_ADI)
    if model is None:
        g.hata("Eğitilmiş model yok. Önce: py src/esleme_modeli.py")
        g.bitir({"durum": "model_yok"})
        return

    yol = ARA_DIZIN / "eslesmeyenler.csv"
    if not yol.exists():
        g.uyari(f"{yol} yok; askıda hesap kalmamış olabilir. "
                f"Önce boru hattını çalıştırın.")
        g.bitir({"durum": "girdi_yok"})
        return
    try:
        eks = pd.read_csv(yol, encoding="utf-8-sig",
                          dtype={"yerel_hesap_kod": str})
    except pd.errors.EmptyDataError:
        eks = pd.DataFrame()
    if eks.empty:
        g.iyi("Askıda hesap yok, öneri gerekmiyor.")
        g.bitir({"oneri": 0})
        return

    y = yukle()
    X = ozellik_cercevesi(pd.DataFrame({
        "yerel_ad": eks["yerel_hesap_ad"],
        "yerel_kod": eks["yerel_hesap_kod"],
        "plan_kodu": eks.get("hesap_plani", "VUK_TDHP"),
    }), kod_kullan=True)

    olasilik = model.predict_proba(X)
    siniflar = np.asarray(model.classes_)
    satirlar = []
    for i, r in enumerate(eks.itertuples()):
        sira = np.argsort(-olasilik[i])[:ilk_k]
        kayit = {"sirket_kod": r.sirket_kod,
                 "yerel_hesap_kod": r.yerel_hesap_kod,
                 "yerel_hesap_ad": r.yerel_hesap_ad,
                 "bakiye": getattr(r, "bakiye", None)}
        for sira_no, j in enumerate(sira, 1):
            kod = str(siniflar[j])
            kayit[f"oneri{sira_no}"] = kod
            kayit[f"oneri{sira_no}_ad"] = y.grup_hesaplari.get(
                kod, {}).get("ad", "")
            kayit[f"oneri{sira_no}_guven"] = round(float(olasilik[i][j]), 4)
        satirlar.append(kayit)

    cikti = pd.DataFrame(satirlar)
    hedef = CIKTI_DIZIN / "esleme_model_onerisi.csv"
    cikti.to_csv(hedef, index=False, encoding="utf-8-sig")

    tablo_yaz("Model önerileri (İNSAN ONAYI GEREKİR)",
              [[r["yerel_hesap_kod"], str(r["yerel_hesap_ad"])[:30],
                f"{r['oneri1']} {str(r['oneri1_ad'])[:20]}",
                f"%{r['oneri1_guven']*100:.0f}",
                f"{r['oneri2']} / {r['oneri3']}"]
               for r in satirlar[:15]],
              ["Kod", "Yerel ad", "1. öneri", "Güven", "2. / 3."])

    g.uyari("Bu öneriler yapılandırmaya YAZILMADI. Model bir öneri üretir, "
            "eşleme tablosuna girmesi insan onayına bağlıdır.")
    if rapor:
        g.bilgi(f"Modelin ölçülmüş başarısı: makro F1 "
                f"{rapor['model_skoru']:.3f}, ilk 3 öneri doğruluğu "
                f"{rapor.get('ilk3_dogruluk', float('nan')):.3f}")
    g.iyi(f"{len(satirlar)} öneri yazıldı: {hedef}")
    g.bitir({"oneri": len(satirlar)})


def main():
    g = Gunluk("esleme_modeli")
    if O.ogrenme_kapali():
        g.bilgi("Öğrenme katmanı kapalı (--ogrenme-kapali). Atlandı.")
        g.bitir({"durum": "kapali"})
        return
    try:
        O.kutuphane_iste()
    except O.OgrenmeYok as e:
        g.hata(str(e))
        g.bitir({"durum": "kutuphane_yok"})
        return

    if "--oner" in sys.argv:
        oner(g)
    else:
        egit(g)


if __name__ == "__main__":
    main()
