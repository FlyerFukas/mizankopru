# -*- coding: utf-8 -*-
"""
MİZANKÖPRÜ — [4] KONTROL: iç kontrol testleri.

GÖREV
  Konsolidasyona giren veriyi 14 testten geçirir ve bulgu listesi üretir.
  Testlerin eşikleri yapilandirma/kontroller.yaml'da; kod değişmeden
  şirket politikasına göre ayarlanır.

TASARIM İLKESİ — BULGU ≠ HATA
  Her bulgu bir iddia değil, bir sorudur: "bu kayıt neden böyle?".
  Motor karar vermez, kanıtı gösterir ve sıraya koyar. Kararı imzayı
  atacak olan verir. Bu yüzden her bulgu 'kanit' alanı taşır — hangi fiş,
  hangi tutar, hangi kullanıcı.

YANLIŞ POZİTİF
  Eşikler kasten muhafazakâr: az sayıda gerçek bulgu, çok sayıda gürültüden
  iyidir. 400 bulgulu bir rapor okunmaz; okunmayan rapor kontrol değildir.

ÇALIŞTIRMA
  py src/kontrol.py
ÇIKTI
  cikti/bulgular.csv · cikti/bulgu_triyaji.json (zeka katmanı açıksa)
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gunluk import Gunluk, para, tablo_yaz                    # noqa: E402
from sema import ARA_DIZIN, BULGU_KOLONLARI, CIKTI_DIZIN, ONEM_SIRASI, yukle  # noqa: E402
from zeka import Zeka                                          # noqa: E402

# Benford yasası — ilk rakamın beklenen dağılımı
BENFORD = {d: np.log10(1 + 1 / d) for d in range(1, 10)}


def donem_sinirlari(donem: str):
    yil, ay = map(int, donem.split("-"))
    ilk = datetime(yil, ay, 1).date()
    son = (datetime(yil + (ay == 12), (ay % 12) + 1, 1) - timedelta(days=1)).date()
    return ilk, son


class Kontrolcu:
    def __init__(self, y, g: Gunluk):
        self.y = y
        self.g = g
        self.bulgular: list[dict] = []
        self.calisan: list[str] = []
        self.atlanan: list[tuple[str, str]] = []

    # ---------------------------------------------------------------
    def bulgu(self, kod: str, sirket: str, donem: str, nesne: str,
              tutar_eur: float, aciklama: str, kanit=None):
        test = self.y.kontroller[kod]
        self.bulgular.append({
            "test_kod": kod, "test_ad": test["ad"], "onem": test["onem"],
            "sirket_kod": sirket, "donem": donem, "nesne": nesne,
            "tutar_eur": round(float(tutar_eur), 2), "aciklama": aciklama,
            "kanit": json.dumps(kanit, ensure_ascii=False, default=str) if kanit else "",
        })

    def aktif(self, kod: str) -> bool:
        t = self.y.kontroller.get(kod)
        if not t or not t.get("aktif", True):
            self.atlanan.append((kod, "yapılandırmada kapalı"))
            return False
        return True

    def esik(self, kod: str, ad: str, varsayilan=None):
        return self.y.kontroller[kod].get("esikler", {}).get(ad, varsayilan)

    def eur(self, tutar, donem: str, sirket: str, tip: str = "ortalama") -> float:
        pb = self.y.sirketler[sirket].fonksiyonel_para_birimi
        return float(tutar) * self.y.kur(donem, pb, tip)

    # =================================================================
    # K01 — Bilanço denkliği
    # =================================================================
    def k01(self, mizan: pd.DataFrame):
        if not self.aktif("K01"):
            return
        tol = self.esik("K01", "tolerans", 0.01)
        for sirket, alt in mizan.groupby("sirket_kod"):
            bozuk = []
            for donem, d in alt.groupby("donem"):
                fark = d["borc"].sum() - d["alacak"].sum()
                if abs(fark) > tol:
                    bozuk.append((donem, fark))
            if not bozuk:
                continue
            # Mizan YTD'dir: bir kez bozulunca sonraki dönemler de bozuk görünür.
            # Bulgu ilk bozulan döneme yazılır, süre açıklamada verilir.
            ilk_donem, ilk_fark = bozuk[0]
            self.bulgu("K01", sirket, ilk_donem, "mizan",
                       self.eur(ilk_fark, ilk_donem, sirket, "kapanis"),
                       f"Borç-alacak denkliği {ilk_donem}'de bozuldu "
                       f"({para(ilk_fark, 2)} {self.y.sirketler[sirket].fonksiyonel_para_birimi}) "
                       f"ve {len(bozuk)} dönem boyunca taşındı. Mizan eksik ya da "
                       f"tek taraflı kayıt var; üstüne kurulan her rakam şüpheli.",
                       {"bozuk_donemler": [b[0] for b in bozuk],
                        "ilk_fark": round(ilk_fark, 2),
                        "son_fark": round(bozuk[-1][1], 2)})
        self.calisan.append("K01")

    # =================================================================
    # K02 — Mükerrer fiş
    # =================================================================
    def k02(self, yevmiye: pd.DataFrame):
        if not self.aktif("K02"):
            return
        asgari = self.esik("K02", "asgari_tutar", 1000)
        pencere = self.esik("K02", "gun_penceresi", 3)

        fis = (yevmiye.groupby(["sirket_kod", "fis_no"], as_index=False)
                      .agg(donem=("donem", "first"),
                           tarih=("fis_tarihi", "first"),
                           borc=("borc", "sum"),
                           kullanici=("kullanici", "first"),
                           aciklama=("aciklama", "first"),
                           hesaplar=("yerel_hesap_kod",
                                     lambda s: "|".join(sorted(set(s))))))
        fis = fis[fis["borc"] >= asgari].copy()
        fis["imza"] = (fis["sirket_kod"] + "§" + fis["borc"].round(2).astype(str)
                       + "§" + fis["hesaplar"])

        for imza, grup in fis.groupby("imza"):
            if len(grup) < 2:
                continue
            grup = grup.sort_values("tarih")
            tarihler = pd.to_datetime(grup["tarih"]).tolist()
            for i in range(1, len(grup)):
                if (tarihler[i] - tarihler[i - 1]).days > pencere:
                    continue
                a, b = grup.iloc[i - 1], grup.iloc[i]
                self.bulgu("K02", b["sirket_kod"], b["donem"],
                           f"fiş {a['fis_no']} ↔ {b['fis_no']}",
                           self.eur(b["borc"], b["donem"], b["sirket_kod"]),
                           f"Aynı tutar ({para(b['borc'], 2)}) ve aynı hesaplarla "
                           f"{(tarihler[i] - tarihler[i-1]).days} gün arayla iki fiş. "
                           f"Açıklama: \"{str(b['aciklama'])[:60]}\"",
                           {"fis_1": a["fis_no"], "fis_2": b["fis_no"],
                            "tarih_1": str(a["tarih"]), "tarih_2": str(b["tarih"]),
                            "tutar": round(b["borc"], 2),
                            "hesaplar": b["hesaplar"],
                            "kullanici": b["kullanici"]})
        self.calisan.append("K02")

    # =================================================================
    # K03 — Dönem kayması (cut-off)
    # =================================================================
    def k03(self, yevmiye: pd.DataFrame):
        if not self.aktif("K03"):
            return
        asgari = self.esik("K03", "asgari_tutar", 5000)
        fis = (yevmiye.groupby(["sirket_kod", "fis_no"], as_index=False)
                      .agg(donem=("donem", "first"),
                           belge=("belge_tarihi", "first"),
                           fis_t=("fis_tarihi", "first"),
                           borc=("borc", "sum"),
                           aciklama=("aciklama", "first"),
                           kullanici=("kullanici", "first")))
        fis = fis[fis["borc"] >= asgari]
        for r in fis.itertuples():
            if pd.isna(r.belge):
                continue
            belge = pd.to_datetime(r.belge).date()
            ilk, son = donem_sinirlari(r.donem)
            if belge > son:
                gun = (belge - son).days
                self.bulgu("K03", r.sirket_kod, r.donem, f"fiş {r.fis_no}",
                           self.eur(r.borc, r.donem, r.sirket_kod),
                           f"Belge tarihi {belge} — kaydedildiği dönemden {gun} gün SONRA. "
                           f"Gelecek döneme ait bir belge bu dönemin sonucuna girmiş.",
                           {"fis_no": r.fis_no, "belge_tarihi": str(belge),
                            "fis_tarihi": str(r.fis_t), "donem_sonu": str(son),
                            "gun_farki": gun, "tutar": round(r.borc, 2),
                            "kullanici": r.kullanici})
            elif belge < ilk - timedelta(days=45):
                gun = (ilk - belge).days
                self.bulgu("K03", r.sirket_kod, r.donem, f"fiş {r.fis_no}",
                           self.eur(r.borc, r.donem, r.sirket_kod),
                           f"Belge tarihi {belge} — kayıttan {gun} gün önce. "
                           f"Geç kaydedilmiş bir belge; ait olduğu dönemi etkiler.",
                           {"fis_no": r.fis_no, "belge_tarihi": str(belge),
                            "gecikme_gun": gun, "tutar": round(r.borc, 2)})
        self.calisan.append("K03")

    # =================================================================
    # K04 — Mesai dışı kayıt
    # =================================================================
    def k04(self, yevmiye: pd.DataFrame):
        if not self.aktif("K04"):
            return
        asgari_eur = self.esik("K04", "asgari_tutar", 50000)
        genel = self.y.kontrol_genel
        bas = int(str(genel["mesai_saatleri"]["baslangic"]).split(":")[0])
        bit = int(str(genel["mesai_saatleri"]["bitis"]).split(":")[0])
        gunler = set(genel.get("calisma_gunleri", [1, 2, 3, 4, 5]))

        fis = (yevmiye.groupby(["sirket_kod", "fis_no"], as_index=False)
                      .agg(donem=("donem", "first"),
                           zaman=("kayit_zamani", "first"),
                           borc=("borc", "sum"),
                           kullanici=("kullanici", "first"),
                           aciklama=("aciklama", "first")))
        for r in fis.itertuples():
            if pd.isna(r.zaman):
                continue
            try:
                z = pd.to_datetime(r.zaman)
            except Exception:
                continue
            eur = self.eur(r.borc, r.donem, r.sirket_kod)
            if eur < asgari_eur:
                continue
            hafta_sonu = (z.weekday() + 1) not in gunler
            mesai_disi = z.hour < bas or z.hour >= bit
            if not (hafta_sonu or mesai_disi):
                continue
            neden = []
            if hafta_sonu:
                neden.append(["Pazartesi", "Salı", "Çarşamba", "Perşembe",
                              "Cuma", "Cumartesi", "Pazar"][z.weekday()])
            if mesai_disi:
                neden.append(f"saat {z.hour:02d}:{z.minute:02d}")
            self.bulgu("K04", r.sirket_kod, r.donem, f"fiş {r.fis_no}", eur,
                       f"{para(eur, 0)} EUR tutarındaki fiş {' ve '.join(neden)} "
                       f"girilmiş. Kaydeden: {r.kullanici}.",
                       {"fis_no": r.fis_no, "kayit_zamani": str(z),
                        "kullanici": r.kullanici, "tutar_yerel": round(r.borc, 2),
                        "aciklama": str(r.aciklama)[:80]})
        self.calisan.append("K04")

    # =================================================================
    # K05 — Yetki limiti aşımı
    # =================================================================
    def k05(self, yevmiye: pd.DataFrame):
        if not self.aktif("K05"):
            return
        limitler = self.y.kontrol_genel.get("onay_limitleri", {})
        kapsam = set(self.esik("K05", "kapsam_grup_hesaplari", []) or [])

        borc_satir = yevmiye[yevmiye["borc"] > 0].copy()
        if kapsam:
            # Fişin borç tarafı harcama yetkisi gerektiren bir hesaba mı gidiyor?
            planlar = {k: s.hesap_plani for k, s in self.y.sirketler.items()}
            borc_satir["grup_kod"] = [
                self.y.grup_kodu(planlar.get(s, ""), h) or ""
                for s, h in zip(borc_satir["sirket_kod"],
                                borc_satir["yerel_hesap_kod"])]
            kapsamli = borc_satir[borc_satir["grup_kod"].isin(kapsam)]
            gecerli = set(zip(kapsamli["sirket_kod"], kapsamli["fis_no"]))
        else:
            gecerli = None

        fis = (borc_satir.groupby(["sirket_kod", "fis_no"], as_index=False)
                         .agg(donem=("donem", "first"), borc=("borc", "sum"),
                              kullanici=("kullanici", "first"),
                              aciklama=("aciklama", "first"),
                              tarih=("fis_tarihi", "first")))
        haric = {u.upper() for u in (self.esik("K05", "haric_kullanicilar", []) or [])}
        for r in fis.itertuples():
            if gecerli is not None and (r.sirket_kod, r.fis_no) not in gecerli:
                continue
            if str(r.kullanici).upper() in haric:
                continue
            lim = limitler.get(r.sirket_kod)
            if not lim or r.borc <= lim["tek_fis_limiti"]:
                continue
            asim = r.borc / lim["tek_fis_limiti"]
            self.bulgu("K05", r.sirket_kod, r.donem, f"fiş {r.fis_no}",
                       self.eur(r.borc, r.donem, r.sirket_kod),
                       f"Tek fiş {para(r.borc, 0)} {lim['para_birimi']} — onay limitinin "
                       f"{asim:.2f} katı (limit {para(lim['tek_fis_limiti'], 0)}). "
                       f"Kaydeden: {r.kullanici}. Açıklama: \"{str(r.aciklama)[:50]}\"",
                       {"fis_no": r.fis_no, "tutar": round(r.borc, 2),
                        "limit": lim["tek_fis_limiti"], "kat": round(asim, 2),
                        "kullanici": r.kullanici, "tarih": str(r.tarih)})
        self.calisan.append("K05")

    # =================================================================
    # K06 — Limit parçalama (splitting)
    # =================================================================
    def k06(self, yevmiye: pd.DataFrame):
        if not self.aktif("K06"):
            return
        limitler = self.y.kontrol_genel.get("onay_limitleri", {})
        alt_oran = self.esik("K06", "limit_orani_alt", 0.70)
        asgari_adet = self.esik("K06", "asgari_adet", 2)

        borc = yevmiye[yevmiye["borc"] > 0]
        fis = (borc.groupby(["sirket_kod", "fis_no"], as_index=False)
                   .agg(donem=("donem", "first"), tarih=("fis_tarihi", "first"),
                        tutar=("borc", "sum"), kullanici=("kullanici", "first"),
                        hesap=("yerel_hesap_kod", "first"),
                        aciklama=("aciklama", "first")))
        for (sirket, tarih, kullanici, hesap), grup in fis.groupby(
                ["sirket_kod", "tarih", "kullanici", "hesap"]):
            lim = limitler.get(sirket)
            if not lim:
                continue
            L = lim["tek_fis_limiti"]
            bantta = grup[(grup["tutar"] >= L * alt_oran) & (grup["tutar"] <= L)]
            if len(bantta) < asgari_adet:
                continue
            toplam = bantta["tutar"].sum()
            donem = bantta["donem"].iloc[0]
            self.bulgu("K06", sirket, donem, f"{kullanici} · {tarih} · hesap {hesap}",
                       self.eur(toplam, donem, sirket),
                       f"Aynı gün, aynı kullanıcı ve hesapta limitin %{alt_oran*100:.0f}-100 "
                       f"bandında {len(bantta)} fiş; toplam {para(toplam, 0)} "
                       f"{lim['para_birimi']} (limit {para(L, 0)}). Tek işlem bölünmüş "
                       f"olabilir — aşımın kendisinden daha ciddi bir sinyal.",
                       {"fis_nolar": list(bantta["fis_no"]),
                        "tutarlar": [round(t, 2) for t in bantta["tutar"]],
                        "limit": L, "kullanici": kullanici, "hesap": hesap,
                        "tarih": str(tarih),
                        "aciklama": str(bantta["aciklama"].iloc[0])[:60]})
        self.calisan.append("K06")

    # =================================================================
    # K07 — Benford ilk rakam testi
    # =================================================================
    def k07(self, yevmiye: pd.DataFrame):
        if not self.aktif("K07"):
            return
        asgari = self.esik("K07", "asgari_gozlem", 100)
        kritik = self.esik("K07", "ki_kare_kritik", 20.09)

        borc = yevmiye[yevmiye["borc"] > 0].copy()
        borc["ilk_rakam"] = (borc["borc"].abs().astype(str)
                             .str.replace(r"[^1-9]", "", regex=True).str[:1])
        borc = borc[borc["ilk_rakam"] != ""]
        borc["ilk_rakam"] = borc["ilk_rakam"].astype(int)

        for (sirket, hesap), grup in borc.groupby(["sirket_kod", "yerel_hesap_kod"]):
            n = len(grup)
            if n < asgari:
                continue
            gozlenen = Counter(grup["ilk_rakam"])
            ki_kare = sum((gozlenen.get(d, 0) - n * BENFORD[d]) ** 2 / (n * BENFORD[d])
                          for d in range(1, 10))
            if ki_kare <= kritik:
                continue
            sapma = sorted(
                ((d, gozlenen.get(d, 0) / n, BENFORD[d]) for d in range(1, 10)),
                key=lambda x: -(abs(x[1] - x[2])))[:3]
            donem = grup["donem"].max()
            self.bulgu("K07", sirket, donem, f"hesap {hesap}",
                       self.eur(grup["borc"].sum(), donem, sirket),
                       f"İlk rakam dağılımı Benford'dan sapıyor (χ²={ki_kare:.1f}, "
                       f"kritik {kritik}, n={n:,}). En sapan rakamlar: "
                       + ", ".join(f"{d}: %{g*100:.0f} (beklenen %{b*100:.0f})"
                                   for d, g, b in sapma)
                       + ". Tutarlar elle üretilmiş olabilir.",
                       {"hesap": hesap, "gozlem": n, "ki_kare": round(ki_kare, 2),
                        "dagilim": {str(d): gozlenen.get(d, 0) for d in range(1, 10)}})
        self.calisan.append("K07")

    # =================================================================
    # K08 — Grup içi eliminasyon farkı
    # =================================================================
    def k08(self, grup_ici: pd.DataFrame):
        if not self.aktif("K08"):
            return
        tol_mutlak = self.esik("K08", "tolerans_mutlak", 1000)
        tol_oran = self.esik("K08", "tolerans_oran", 0.005)

        # Her (A,B,dönem) çifti için iki tarafın beyanını EUR'da karşılaştır
        kayit = {}
        for r in grup_ici.itertuples():
            if r.sirket_kod not in self.y.sirketler or r.karsi_sirket not in self.y.sirketler:
                continue
            eur = self.eur(r.tutar, r.donem, r.sirket_kod, "kapanis")
            kayit[(r.sirket_kod, r.karsi_sirket, r.donem, r.yon)] = (eur, r.tutar)

        gorulmus = set()
        for (a, b, donem, yon), (eur_a, yerel_a) in kayit.items():
            if yon != "alacak":
                continue
            anahtar = tuple(sorted([a, b])) + (donem,)
            if anahtar in gorulmus:
                continue
            gorulmus.add(anahtar)
            karsi = kayit.get((b, a, donem, "borc"))
            if karsi is None:
                self.bulgu("K08", a, donem, f"{a} → {b}", eur_a,
                           f"{a}, {b}'den {para(eur_a, 0)} EUR alacak bildiriyor ama "
                           f"{b} tarafında karşılık bir borç kaydı YOK.",
                           {"satici": a, "alici": b, "alacak_eur": round(eur_a, 2),
                            "borc_eur": None})
                continue
            eur_b, yerel_b = karsi
            fark = eur_a - eur_b
            taban = max(abs(eur_a), abs(eur_b), 1)
            if abs(fark) <= tol_mutlak and abs(fark) / taban <= tol_oran:
                continue
            self.bulgu("K08", a, donem, f"{a} ↔ {b}", abs(fark),
                       f"{a}'nın alacağı {para(eur_a, 0)} EUR, {b}'nin borcu "
                       f"{para(eur_b, 0)} EUR — {para(abs(fark), 0)} EUR "
                       f"(%{abs(fark)/taban*100:.1f}) fark. Konsolide bilanço bu kadar "
                       f"şişer ya da eksilir.",
                       {"satici": a, "alici": b,
                        "alacak_eur": round(eur_a, 2), "borc_eur": round(eur_b, 2),
                        "fark_eur": round(fark, 2),
                        "fark_oran": round(abs(fark) / taban, 4)})
        self.calisan.append("K08")

    # =================================================================
    # K09 — Eşleşmeyen hesap
    # =================================================================
    def k09(self, eslesmeyenler: pd.DataFrame):
        if not self.aktif("K09"):
            return
        for r in eslesmeyenler.itertuples():
            self.bulgu("K09", r.sirket_kod, r.son_donem,
                       f"hesap {r.yerel_hesap_kod} ({r.hesap_plani})",
                       abs(r.bakiye_eur),
                       f"\"{r.yerel_hesap_ad}\" grup hesap planına eşlenmiyor; "
                       f"{r.donem_sayisi} dönemdir ({r.ilk_donem}→{r.son_donem}) "
                       f"askıda ve {para(abs(r.bakiye_eur), 0)} EUR taşıyor. "
                       f"Eşleşmeyen hesap konsolidasyondan sessizce düşer — tablo "
                       f"yine denk görünür.",
                       {"yerel_kod": r.yerel_hesap_kod, "ad": r.yerel_hesap_ad,
                        "plan": r.hesap_plani, "donem_sayisi": r.donem_sayisi,
                        "bakiye_yerel": r.bakiye, "bakiye_eur": r.bakiye_eur})
        self.calisan.append("K09")

    # =================================================================
    # K10 — Eksik dönem
    # =================================================================
    def k10(self, mizan: pd.DataFrame, yevmiye: pd.DataFrame):
        if not self.aktif("K10"):
            return
        beklenen = {(s, d) for s in self.y.sirketler for d in self.y.donemler()}
        gelen = set(zip(mizan["sirket_kod"], mizan["donem"]))
        for sirket, donem in sorted(beklenen - gelen):
            jk = yevmiye[(yevmiye["sirket_kod"] == sirket)
                         & (yevmiye["donem"] == donem)]
            islem = len(jk)
            hacim = self.eur(jk["borc"].sum(), donem, sirket) if islem else 0.0
            self.bulgu("K10", sirket, donem, "mizan dosyası", hacim,
                       f"{sirket} şirketinin {donem} mizanı hiç gelmedi"
                       + (f", ama yevmiyesinde {islem:,} satır ve {para(hacim, 0)} EUR "
                          f"işlem hacmi var. Sadece mizana bakan bir konsolidasyon "
                          f"bu ayı yok sayar." if islem else "."),
                       {"yevmiye_satir": islem, "hacim_eur": round(hacim, 2)})
        self.calisan.append("K10")

    # =================================================================
    # K11 — Ters bakiye
    # =================================================================
    def k11(self, cevrilmis: pd.DataFrame):
        if not self.aktif("K11"):
            return
        asgari = self.esik("K11", "asgari_tutar", 10000)
        for r in cevrilmis.itertuples():
            h = self.y.grup_hesaplari.get(r.grup_kod)
            if not h or h.get("hesaplanan") or h.get("aski"):
                continue
            hareket = getattr(r, "bakiye_aylik", 0.0)
            if pd.isna(hareket) or hareket == 0:
                continue
            # yon=1 borç bakiyeli hesap, yon=-1 alacak bakiyeli
            ters = (h["yon"] == 1 and hareket < 0) or (h["yon"] == -1 and hareket > 0)
            if not ters:
                continue
            eur = abs(self.eur(hareket, r.donem, r.sirket_kod))
            if eur < asgari:
                continue
            beklenen = "borç" if h["yon"] == 1 else "alacak"
            self.bulgu("K11", r.sirket_kod, r.donem,
                       f"{r.grup_kod} {h['ad']}", eur,
                       f"Normalde {beklenen} bakiye veren hesap bu dönem ters yönde "
                       f"{para(eur, 0)} EUR hareket etti. Yanlış hesaba kayıt, "
                       f"büyük bir iade ya da sınıflandırma hatası olabilir.",
                       {"grup_kod": r.grup_kod, "beklenen_yon": beklenen,
                        "hareket_yerel": round(hareket, 2)})
        self.calisan.append("K11")

    # =================================================================
    # K12 — Yuvarlak tutar yoğunluğu
    # =================================================================
    def k12(self, yevmiye: pd.DataFrame):
        if not self.aktif("K12"):
            return
        yuv = self.esik("K12", "yuvarlaklik", 1000)
        esik = self.esik("K12", "pay_esigi", 0.25)
        asgari = self.esik("K12", "asgari_gozlem", 20)

        borc = yevmiye[yevmiye["borc"] > 0].copy()
        borc["yuvarlak"] = (borc["borc"] % yuv).abs() < 0.005

        # Şirketin genel yuvarlaklık oranı taban kabul edilir; anomali ondan sapmadır
        taban = borc.groupby("sirket_kod")["yuvarlak"].mean().to_dict()
        for (sirket, hesap), grup in borc.groupby(["sirket_kod", "yerel_hesap_kod"]):
            if len(grup) < asgari:
                continue
            pay = grup["yuvarlak"].mean()
            t = taban.get(sirket, 0.0)
            if pay < esik or pay < max(3 * t, 0.05):
                continue
            donem = grup["donem"].max()
            self.bulgu("K12", sirket, donem, f"hesap {hesap}",
                       self.eur(grup[grup["yuvarlak"]]["borc"].sum(), donem, sirket),
                       f"Kayıtların %{pay*100:.0f}'i tam {yuv:,.0f}'in katı "
                       f"({grup['yuvarlak'].sum():,}/{len(grup):,}); şirket geneli "
                       f"%{t*100:.1f}. Gerçek ticari işlem nadiren tam yuvarlaktır — "
                       f"tahmini ya da uydurma kayıt sinyali.",
                       {"hesap": hesap, "gozlem": len(grup),
                        "yuvarlak_adet": int(grup["yuvarlak"].sum()),
                        "pay": round(pay, 3), "sirket_tabani": round(t, 4)})
        self.calisan.append("K12")

    # =================================================================
    # K13 — Görevler ayrılığı
    # =================================================================
    def k13(self, yevmiye: pd.DataFrame):
        if not self.aktif("K13"):
            return
        esik = self.esik("K13", "pay_esigi", 0.90)
        asgari = self.esik("K13", "asgari_gozlem", 30)

        fis = yevmiye.drop_duplicates(subset=["sirket_kod", "fis_no"])
        # Otomatik sistem kayıtları görevler ayrılığı ihlali sayılmaz
        insan = fis[~fis["kullanici"].str.upper().isin(["SISTEM", "SYSTEM", ""])]
        for sirket, grup in insan.groupby("sirket_kod"):
            if len(grup) < asgari:
                continue
            sayim = grup["kullanici"].value_counts()
            pay = sayim.iloc[0] / len(grup)
            if pay < esik:
                continue
            donem = grup["donem"].max()
            self.bulgu("K13", sirket, donem, f"kullanıcı {sayim.index[0]}",
                       self.eur(grup["borc"].sum(), donem, sirket),
                       f"Elle girilen {len(grup):,} fişin %{pay*100:.0f}'i tek kişi "
                       f"({sayim.index[0]}) tarafından kaydedilmiş. Diğer kullanıcılar: "
                       + (", ".join(f"{k} ({v})" for k, v in sayim.iloc[1:4].items())
                          or "yok")
                       + ". Kaydeden ile onaylayan ayrışmıyor.",
                       {"baskin_kullanici": sayim.index[0], "pay": round(pay, 3),
                        "fis_sayisi": len(grup),
                        "dagilim": sayim.head(5).to_dict()})
        self.calisan.append("K13")

    # =================================================================
    # K14 — Büyük bütçe sapması
    # =================================================================
    def k14(self, cevrilmis: pd.DataFrame, butce: pd.DataFrame):
        if not self.aktif("K14"):
            return
        oran_esik = self.esik("K14", "oran_esigi", 0.10)
        mutlak_esik = self.esik("K14", "mutlak_esik", 100000)
        son = self.y.donemler()[-1]

        fiili = (cevrilmis[(cevrilmis["donem"] == son) & (cevrilmis["tur"] == "G")]
                 .groupby(["sirket_kod", "grup_kod"], as_index=False)["eur_gercek"].sum())
        # Bütçe yerel para, yıl başında sabitlenen bütçe kuruyla çevrilir
        b = butce.copy()
        b["eur"] = [self.eur(t, d, s, "butce")
                    for t, d, s in zip(b["tutar"], b["donem"], b["sirket_kod"])]
        butce_ozet = b.groupby(["sirket_kod", "grup_kod"], as_index=False)["eur"].sum()

        birlesik = fiili.merge(butce_ozet, on=["sirket_kod", "grup_kod"], how="outer")
        birlesik[["eur_gercek", "eur"]] = birlesik[["eur_gercek", "eur"]].fillna(0.0)

        for r in birlesik.itertuples():
            h = self.y.grup_hesaplari.get(r.grup_kod)
            if not h:
                continue
            isaret = -1 if h["yon"] == -1 else 1
            f = r.eur_gercek * isaret        # sunum işareti
            bt = r.eur * 1.0
            if abs(bt) < 1:
                continue
            sapma = f - bt
            oran = sapma / abs(bt)
            if abs(oran) < oran_esik or abs(sapma) < mutlak_esik:
                continue
            yon = "üstünde" if sapma > 0 else "altında"
            self.bulgu("K14", r.sirket_kod, son, f"{r.grup_kod} {h['ad']}",
                       abs(sapma),
                       f"Fiili {para(f, 0)} EUR, bütçe {para(bt, 0)} EUR — "
                       f"%{abs(oran)*100:.0f} {yon} ({para(abs(sapma), 0)} EUR). "
                       f"Açıklama gerekiyor.",
                       {"grup_kod": r.grup_kod, "fiili_eur": round(f, 2),
                        "butce_eur": round(bt, 2), "sapma_eur": round(sapma, 2),
                        "oran": round(oran, 4)})
        self.calisan.append("K14")


# ======================================================================
def main():
    g = Gunluk("kontrol")
    y = yukle()
    z = Zeka(y=y, g=g)
    g.bilgi(y.ozet())
    g.bilgi(z.ozet())

    gerekli = ARA_DIZIN / "cevrilmis.csv"
    if not gerekli.exists():
        g.hata(f"{gerekli} yok. Önce: py src/topla.py && py src/esle.py && py src/cevir.py")
        g.bitir({"durum": "girdi_yok"})
        return

    oku = lambda ad, **k: pd.read_csv(ARA_DIZIN / ad, dtype={"donem": str, **k})
    mizan = oku("mizan.csv", yerel_hesap_kod=str)
    yevmiye = oku("yevmiye.csv", yerel_hesap_kod=str, fis_no=str)
    cevrilmis = oku("cevrilmis.csv", grup_kod=str)
    butce = oku("butce_eslenmis.csv", grup_kod=str, yerel_hesap_kod=str)
    grup_ici = oku("grup_ici.csv")
    eslesmeyenler = pd.read_csv(ARA_DIZIN / "eslesmeyenler.csv",
                                dtype={"yerel_hesap_kod": str}, encoding="utf-8-sig")
    yevmiye["kullanici"] = yevmiye["kullanici"].fillna("").astype(str)
    g.bilgi(f"{len(yevmiye):,} yevmiye · {len(mizan):,} mizan · "
            f"{len(cevrilmis):,} çevrilmiş satır okundu")

    k = Kontrolcu(y, g)
    k.k01(mizan)
    k.k02(yevmiye)
    k.k03(yevmiye)
    k.k04(yevmiye)
    k.k05(yevmiye)
    k.k06(yevmiye)
    k.k07(yevmiye)
    k.k08(grup_ici)
    k.k09(eslesmeyenler)
    k.k10(mizan, yevmiye)
    k.k11(cevrilmis)
    k.k12(yevmiye)
    k.k13(yevmiye)
    k.k14(cevrilmis, butce)

    bulgular = pd.DataFrame(k.bulgular, columns=BULGU_KOLONLARI)
    if not bulgular.empty:
        bulgular["_sira"] = bulgular["onem"].map(ONEM_SIRASI)
        bulgular = (bulgular.sort_values(["_sira", "tutar_eur"],
                                         ascending=[True, False])
                            .drop(columns="_sira").reset_index(drop=True))
    bulgular.to_csv(CIKTI_DIZIN / "bulgular.csv", index=False, encoding="utf-8-sig")

    # ---- Test çalıştırma özeti ----
    sayim = bulgular["test_kod"].value_counts().to_dict() if not bulgular.empty else {}
    tablo_yaz("Kontrol testleri",
              [[kod, y.kontroller[kod]["ad"], y.kontroller[kod]["onem"],
                "çalıştı" if kod in k.calisan else "ATLANDI",
                f"{sayim.get(kod, 0):,}"]
               for kod in sorted(y.kontroller)],
              ["Kod", "Test", "Önem", "Durum", "Bulgu"])

    if bulgular.empty:
        g.iyi("Hiçbir testte bulgu çıkmadı.")
        g.bitir({"bulgu": 0})
        return

    onem_sayim = bulgular["onem"].value_counts().to_dict()
    g.bilgi(f"\nToplam {len(bulgular):,} bulgu — "
            + " · ".join(f"{o}: {onem_sayim.get(o, 0)}"
                         for o in ["kritik", "yuksek", "orta", "dusuk"]
                         if onem_sayim.get(o)))

    tablo_yaz("En ağır 18 bulgu",
              [[r.test_kod, r.onem[:6], r.sirket_kod, r.donem,
                str(r.nesne)[:30], para(r.tutar_eur, 0), str(r.aciklama)[:58]]
               for r in bulgular.head(18).itertuples()],
              ["Test", "Önem", "Şirket", "Dönem", "Nesne", "Tutar EUR", "Açıklama"])

    # ---- Yapay zekâ triyajı ----
    if z.aktif and y.kontroller and z.ayar.get("gorevler", {}).get("bulgu_triyaj", True):
        kritikler = bulgular[bulgular["onem"].isin(["kritik", "yuksek"])].head(25)
        triyaj = z.bulgu_triyaj(kritikler.to_dict("records"))
        if triyaj:
            with open(CIKTI_DIZIN / "bulgu_triyaji.json", "w", encoding="utf-8") as f:
                json.dump(triyaj, f, ensure_ascii=False, indent=2)
            sira = {x["bulgu_no"]: x for x in triyaj["siralama"]}
            tablo_yaz("Yapay zekâ triyajı — kapanış öncesi sıra",
                      [[sira[i]["aciliyet"], kritikler.iloc[i]["test_kod"],
                        kritikler.iloc[i]["sirket_kod"],
                        str(sira[i]["atilacak_adim"])[:78]]
                       for i in sorted(sira, key=lambda i: (
                           {"hemen": 0, "kapanis_oncesi": 1, "takip": 2}
                           .get(sira[i]["aciliyet"], 3)))
                       if i < len(kritikler)],
                      ["Aciliyet", "Test", "Şirket", "Atılacak adım"])
            g.bilgi(f"\nGenel değerlendirme: {triyaj['genel_degerlendirme']}")
    else:
        g.bilgi(f"Triyaj atlandı — {z.neden or 'yapılandırmada kapalı'}")

    g.bilgi(f"\nBulgular: {CIKTI_DIZIN / 'bulgular.csv'}")
    g.bitir({"bulgu": len(bulgular), "kritik": onem_sayim.get("kritik", 0),
             "zeka": z.istatistik})


if __name__ == "__main__":
    main()
