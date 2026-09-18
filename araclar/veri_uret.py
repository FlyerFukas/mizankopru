# -*- coding: utf-8 -*-
"""
MİZANKÖPRÜ — Sentetik ERP veri üreteci.

NE ÜRETİR
  veri/girdi/ altına, dört şirketin 2025 yılı ERP çıktılarını gerçek hayattaki
  dağınıklığıyla üretir: farklı dosya biçimi, farklı kolon adı, farklı tarih ve
  sayı biçimi, farklı hesap planı.

NASIL ÜRETİR
  Önce bir işletme modeli kurar (ürün, miktar, fiyat, maliyet, gider), sonra bunu
  YEVMİYEYE çevirir, mizanı yevmiyeden toplar. Gerçek hayatta akış da budur;
  tersi yapılırsa mizan ile yevmiye birbirini tutmaz.

TUZAKLAR
  Üretim bittikten sonra 14 kasıtlı hata enjekte edilir ve hepsi
  veri/ornek/TUZAK_CEVAP_ANAHTARI.json dosyasına yazılır. Motorun işi bunları
  bulmak; cevap anahtarı sadece doğrulama içindir, boru hattı onu okumaz.

ÇALIŞTIRMA
  py araclar/veri_uret.py
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

from gunluk import Gunluk, para, tablo_yaz          # noqa: E402
from sema import yukle                               # noqa: E402

TOHUM = 42
GIRDI = KOK / "veri" / "girdi"
ORNEK = KOK / "veri" / "ornek"
GIRDI.mkdir(parents=True, exist_ok=True)
ORNEK.mkdir(parents=True, exist_ok=True)

DONEMLER = [f"2025-{a:02d}" for a in range(1, 13)]

# Bütçe yapılırken varsayılan kur — yıl başında sabitlenmiş.
# Gerçekleşen EUR/TRY yıl sonunda 50,60 oldu. Aradaki fark FP&A'nın
# açıklamak zorunda olduğu en büyük sapma kalemi.
BUTCE_KURU = {"TRY": 1 / 38.00, "EUR": 1.0, "GBP": 1.195}


# ======================================================================
# İŞLETME MODELİ
# ======================================================================

URUN_KATALOGU = {
    "TR01": [  # Üretici — ürettiğini hem yurt içinde hem gruba satar
        ("UR-101", "Endüstriyel Vana DN50", "Vana", 14500, 820),
        ("UR-102", "Endüstriyel Vana DN80", "Vana", 21800, 460),
        ("UR-103", "Aktüatör Seti A", "Aktüatör", 38400, 310),
        ("UR-104", "Aktüatör Seti B", "Aktüatör", 52700, 165),
        ("UR-201", "Bağlantı Flanşı 4\"", "Bağlantı", 3250, 2400),
        ("UR-202", "Bağlantı Flanşı 6\"", "Bağlantı", 4900, 1500),
        ("UR-301", "Sensör Modülü S1", "Elektronik", 9800, 980),
        ("UR-302", "Sensör Modülü S2", "Elektronik", 16200, 540),
    ],
    "TR02": [  # Perakende — TR01'den alır, yurt içinde satar
        ("PR-101", "Vana Servis Paketi", "Servis", 19800, 640),
        ("PR-102", "Aktüatör Servis Paketi", "Servis", 46500, 240),
        ("PR-201", "Yedek Parça Kiti", "Yedek Parça", 5400, 1850),
        ("PR-202", "Bakım Sarf Seti", "Yedek Parça", 2100, 3100),
        ("PR-301", "Kurulum Hizmeti", "Hizmet", 28000, 190),
    ],
    "DE01": [  # Distribütör — EUR
        ("DE-401", "Ventil DN50 (EU)", "Vana", 520, 780),
        ("DE-402", "Ventil DN80 (EU)", "Vana", 780, 430),
        ("DE-403", "Aktuator Set A (EU)", "Aktüatör", 1380, 295),
        ("DE-501", "Flansch 4\" (EU)", "Bağlantı", 118, 2250),
        ("DE-601", "Sensormodul S1 (EU)", "Elektronik", 352, 910),
    ],
    "UK01": [  # Satış ofisi — GBP
        ("UK-701", "Valve DN50 (UK)", "Vana", 448, 410),
        ("UK-702", "Valve DN80 (UK)", "Vana", 672, 225),
        ("UK-703", "Actuator Set A (UK)", "Aktüatör", 1190, 150),
        ("UK-801", "Sensor Module S1 (UK)", "Elektronik", 303, 480),
    ],
}

# Aylık mevsimsellik çarpanı (Oca..Ara) — yaz durgunluğu, yıl sonu itişi
MEVSIMSELLIK = [0.86, 0.90, 1.04, 1.02, 1.06, 0.98, 0.82, 0.78, 1.08, 1.12, 1.10, 1.24]

# İşletmenin GERÇEKLEŞEN seyri — projenin başlık bulgusu buradan doğar.
# TR şirketlerinde fiyat enflasyonla uçuyor (yıllık ~%68), miktar eriyor (~-%18).
# Sonuç: TL cirosu bütçeyi AŞIYOR, ama aynı ciro EUR'ya çevrildiğinde
# yerinde sayıyor. Ayrıştırma yapılmazsa bu "büyüme" diye raporlanır.
SIRKET_DINAMIGI = {
    #          aylık fiyat artışı, aylık miktar değişimi, SMM oranı, personel/ciro
    "TR01": {"fiyat": 0.0480, "miktar": -0.0180, "smm": 0.615, "personel": 0.092},
    "TR02": {"fiyat": 0.0460, "miktar": -0.0220, "smm": 0.720, "personel": 0.078},
    "DE01": {"fiyat": 0.0022, "miktar": 0.0085, "smm": 0.685, "personel": 0.105},
    "UK01": {"fiyat": 0.0028, "miktar": 0.0015, "smm": 0.705, "personel": 0.128},
}

# BÜTÇE varsayımları — yıl başında ne beklenmişti.
# TR için yıllık %25 enflasyon ve hafif hacim büyümesi öngörülmüştü;
# ikisi de tutmadı. Bütçe kuru da EUR/TRY 38'de sabitlenmişti (BUTCE_KURU).
BUTCE_VARSAYIMI = {
    "TR01": {"fiyat": 0.0188, "miktar": 0.0060},   # enflasyon %25/yıl, hacim +%7
    "TR02": {"fiyat": 0.0188, "miktar": 0.0080},
    "DE01": {"fiyat": 0.0020, "miktar": 0.0110},
    "UK01": {"fiyat": 0.0025, "miktar": 0.0070},
}

# Ortalama satış faturası tutarı (şirketin fonksiyonel para biriminde).
# Fatura ADEDİ buradan türetilir — ciroyu tek kalemde yazmak yerine
# gerçek bir satış hacmi üretmek için. Benford ve mükerrer testleri
# ancak yeterli gözlem varsa anlamlıdır.
ORT_FATURA = {"TR01": 200_000, "TR02": 120_000, "DE01": 4_500, "UK01": 1_800}

KULLANICILAR = {
    "TR01": ["a.yilmaz", "m.demir", "s.kaya", "e.ozturk", "SISTEM"],
    "TR02": ["b.sahin", "SISTEM"],                 # tek kişi — görevler ayrılığı zayıf
    "DE01": ["k.mueller", "j.schmidt", "SYSTEM"],
    "UK01": ["j.smith", "r.patel", "SYSTEM"],
}

MASRAF_MERKEZLERI = ["MM-URETIM", "MM-SATIS", "MM-IDARI", "MM-LOJISTIK"]


# ======================================================================
# YARDIMCILAR
# ======================================================================

def donem_gunleri(donem: str) -> tuple[date, date]:
    yil, ay = map(int, donem.split("-"))
    ilk = date(yil, ay, 1)
    son = date(yil + (ay == 12), (ay % 12) + 1, 1) - timedelta(days=1)
    return ilk, son


def sayi_metni(deger: float, ondalik: str, binlik: str, basamak: int = 2) -> str:
    """ERP export'larının klasik davranışı: sayıyı metin olarak yazmak."""
    metin = f"{abs(deger):,.{basamak}f}"           # 1,234.56
    metin = metin.replace(",", "\x00").replace(".", ondalik).replace("\x00", binlik)
    return f"-{metin}" if deger < 0 else metin


class YerelPlan:
    """Grup hesap kodundan o şirketin yerel hesap koduna çevirir.
    Bir grup hesabına birden çok yerel hesap eşliyse rastgele seçer —
    gerçek mizanlarda da kayıtlar alt hesaplara dağılır."""

    def __init__(self, y, plan_kodu: str, rnd: random.Random):
        self.plan = plan_kodu
        self.rnd = rnd
        self.harita: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for r in y.eslesme.itertuples():
            if r.plan_kodu == plan_kodu:
                self.harita[r.grup_kod].append((str(r.yerel_kod), r.yerel_ad))

    def var_mi(self, grup_kod: str) -> bool:
        return grup_kod in self.harita

    def kod(self, grup_kod: str) -> str:
        secenek = self.harita.get(grup_kod)
        if not secenek:
            raise KeyError(f"{self.plan} planında {grup_kod} karşılığı yok")
        return self.rnd.choice(secenek)[0]

    def ad(self, yerel_kod: str) -> str:
        for liste in self.harita.values():
            for k, a in liste:
                if k == yerel_kod:
                    return a
        return "?"


# ======================================================================
# ÜRETEÇ
# ======================================================================

class VeriUretici:
    def __init__(self, y, g: Gunluk):
        self.y = y
        self.g = g
        self.rnd = random.Random(TOHUM)
        self.rng = np.random.default_rng(TOHUM)
        self.fisler: dict[str, list[dict]] = {}       # sirket -> yevmiye satırları
        self.satislar: dict[str, list[dict]] = {}
        self.butceler: dict[str, list[dict]] = {}
        self.grup_ici: list[dict] = []
        self.aylik_ciro: dict[tuple[str, str], float] = {}
        # (satici, alici, donem) -> tutar, SATICININ para biriminde
        self.grup_ici_satis: dict[tuple[str, str, str], float] = {}
        self.tuzaklar: list[dict] = []
        self._fis_sayaci: dict[str, int] = defaultdict(int)
        # Eşleme tablosunda bulunmayan ama ERP'de gerçek adı olan hesaplar
        self.ozel_hesap_adlari: dict[tuple[str, str], str] = {}

    # ---------------- fiş altyapısı ----------------
    def _yeni_fis_no(self, sirket: str, donem: str) -> str:
        self._fis_sayaci[sirket] += 1
        return f"{donem.replace('-', '')}-{self._fis_sayaci[sirket]:05d}"

    def _rastgele_zaman(self, gun: date, mesai_ici: bool = True) -> datetime:
        """Fişin TARİHİ hafta sonuna düşebilir (satış olur), ama muhasebe
        KAYDI hafta içi mesai saatinde girilir. İkisini ayırmazsak normal
        kayıtların üçte biri 'hafta sonu anomalisi' sayılır ve K04 testi
        gürültüye boğulur."""
        kayit_gunu = gun
        while kayit_gunu.weekday() >= 5:          # Cumartesi/Pazar
            kayit_gunu += timedelta(days=1)
        if mesai_ici:
            saat = self.rnd.randint(8, 18)
        else:
            saat = self.rnd.choice([1, 2, 3, 4, 22, 23])
        return datetime(kayit_gunu.year, kayit_gunu.month, kayit_gunu.day,
                        saat, self.rnd.randint(0, 59), self.rnd.randint(0, 59))

    def fis_kaydet(self, sirket: str, donem: str, tutar: float,
                   borc_grup: str, alacak_grup: str, aciklama: str,
                   plan: YerelPlan, gun: date | None = None,
                   belge_gun: date | None = None, kullanici: str | None = None,
                   mesai_ici: bool = True, fis_no: str | None = None,
                   masraf_merkezi: str | None = None) -> str:
        """Çift taraflı tek fiş yazar: bir borç, bir alacak satırı."""
        ilk, son = donem_gunleri(donem)
        if gun is None:
            gun = ilk + timedelta(days=self.rnd.randint(0, (son - ilk).days))
        if belge_gun is None:
            belge_gun = gun - timedelta(days=self.rnd.randint(0, 5))
        if kullanici is None:
            kullanici = self.rnd.choice(KULLANICILAR[sirket])
        if fis_no is None:
            fis_no = self._yeni_fis_no(sirket, donem)
        if masraf_merkezi is None:
            masraf_merkezi = self.rnd.choice(MASRAF_MERKEZLERI)

        zaman = self._rastgele_zaman(gun, mesai_ici)
        tutar = round(tutar, 2)
        ortak = dict(sirket_kod=sirket, donem=donem, fis_no=fis_no,
                     fis_tarihi=gun, belge_tarihi=belge_gun, aciklama=aciklama,
                     kullanici=kullanici, kayit_zamani=zaman,
                     masraf_merkezi=masraf_merkezi)
        self.fisler[sirket].append(
            {**ortak, "yerel_hesap_kod": plan.kod(borc_grup), "borc": tutar, "alacak": 0.0})
        self.fisler[sirket].append(
            {**ortak, "yerel_hesap_kod": plan.kod(alacak_grup), "borc": 0.0, "alacak": tutar})
        return fis_no

    # ---------------- satış ve bütçe ----------------
    def satis_uret(self, sirket: str, senaryo: str) -> pd.DataFrame:
        """senaryo: 'fiili' gerçekleşen, 'butce' yıl başı planı."""
        din = SIRKET_DINAMIGI[sirket] if senaryo == "fiili" else BUTCE_VARSAYIMI[sirket]
        satirlar = []
        for t, donem in enumerate(DONEMLER):
            for kod, ad, kategori, fiyat0, miktar0 in URUN_KATALOGU[sirket]:
                fiyat = fiyat0 * (1 + din["fiyat"]) ** t
                miktar = miktar0 * (1 + din["miktar"]) ** t * MEVSIMSELLIK[t]
                if senaryo == "fiili":
                    # Gerçekleşende gürültü var; bütçe pürüzsüz.
                    fiyat *= 1 + self.rng.normal(0, 0.012)
                    miktar *= 1 + self.rng.normal(0, 0.055)
                miktar = max(1, round(miktar))
                fiyat = round(fiyat, 2)
                satirlar.append({
                    "sirket_kod": sirket, "donem": donem, "urun_kod": kod,
                    "urun_ad": ad, "kategori": kategori, "miktar": miktar,
                    "birim_fiyat": fiyat, "tutar": round(miktar * fiyat, 2),
                    "musteri_tipi": self.rnd.choice(["Bayi", "Kurumsal", "Perakende"]),
                    "senaryo": senaryo,
                })
        return pd.DataFrame(satirlar)

    def butce_uret(self, sirket: str, satis_butce: pd.DataFrame,
                   plan: YerelPlan) -> pd.DataFrame:
        """Gelir tablosu bütçesi — satış bütçesinden türetilir."""
        din = SIRKET_DINAMIGI[sirket]
        satirlar = []
        aylik_ciro = satis_butce.groupby("donem")["tutar"].sum()
        for donem, ciro in aylik_ciro.items():
            kalemler = [
                ("4010", ciro * 0.62), ("4020", ciro * 0.13), ("4025", ciro * 0.25),
                ("5010", -ciro * din["smm"] * 0.75), ("5025", -ciro * din["smm"] * 0.25),
                ("6010", -ciro * din["personel"]),
                ("6020", -ciro * 0.021), ("6030", -ciro * 0.034),
                ("6040", -ciro * 0.028), ("6050", -ciro * 0.018),
                ("6060", -ciro * 0.011),
                ("7020", -ciro * 0.015), ("7010", ciro * 0.004),
                ("8010", -ciro * 0.020),
            ]
            for grup_kod, tutar in kalemler:
                if not plan.var_mi(grup_kod):
                    continue
                satirlar.append({
                    "sirket_kod": sirket, "donem": donem,
                    "yerel_hesap_kod": plan.kod(grup_kod),
                    "tutar": round(abs(tutar), 2),
                    "masraf_merkezi": self.rnd.choice(MASRAF_MERKEZLERI),
                })
        return pd.DataFrame(satirlar)

    # ---------------- ana üretim ----------------
    def sirket_uret(self, sirket: str):
        s = self.y.sirketler[sirket]
        plan = YerelPlan(self.y, s.hesap_plani, self.rnd)
        self.fisler[sirket] = []
        din = SIRKET_DINAMIGI[sirket]

        fiili = self.satis_uret(sirket, "fiili")
        butce_satis = self.satis_uret(sirket, "butce")
        self.satislar[sirket] = pd.concat([fiili, butce_satis], ignore_index=True)
        self.butceler[sirket] = self.butce_uret(sirket, butce_satis, plan)

        # Açılış kaydı — sermaye ve duran varlık
        acilis = fiili[fiili["donem"] == DONEMLER[0]]["tutar"].sum()
        self.fis_kaydet(sirket, DONEMLER[0], acilis * 2.4, "1010", "3010",
                        "Açılış — sermaye", plan, gun=date(2025, 1, 1),
                        kullanici="SISTEM")
        self.fis_kaydet(sirket, DONEMLER[0], acilis * 1.8, "1510", "1010",
                        "Açılış — duran varlık alımı", plan, gun=date(2025, 1, 2),
                        kullanici="SISTEM")
        self.fis_kaydet(sirket, DONEMLER[0], acilis * 0.9, "1030", "2010",
                        "Açılış — stok", plan, gun=date(2025, 1, 3), kullanici="SISTEM")

        for t, donem in enumerate(DONEMLER):
            ay_ciro = fiili[fiili["donem"] == donem]["tutar"].sum()
            ilk, son = donem_gunleri(donem)

            self.aylik_ciro[(sirket, donem)] = ay_ciro

            # --- Satış: yurt içi / yurt dışı ---
            # Fatura adedi ortalama fatura tutarından türetilir; gerçek bir
            # şirkette ayda yüzlerce fatura kesilir, tek kalemde ciro yazılmaz.
            grup_ici_payi = sum(i.get("satici_ciro_payi", 0.05)
                                for i in self.y.grup_ici_iliskiler
                                if i["satici"] == sirket)
            dis_payi = 1.0 - grup_ici_payi
            paylar = {"4010": (dis_payi * 0.83, ORT_FATURA[sirket]),
                      "4020": (dis_payi * 0.17, ORT_FATURA[sirket] * 2.4)}  # ihracat: az sayıda büyük fatura
            for grup_kod, (pay, ort_fatura) in paylar.items():
                if not plan.var_mi(grup_kod):
                    continue
                tutar_toplam = ay_ciro * pay
                adet = int(np.clip(round(tutar_toplam / ort_fatura), 2, 260))
                for tutar in self._parcala(tutar_toplam, adet):
                    self.fis_kaydet(sirket, donem, tutar, "1020", grup_kod,
                                    f"Satış faturası — {donem}", plan)

            # --- Grup içi satış: alıcı bazında ayrı ayrı ---
            # Kimin kime ne sattığı KAYDEDİLİR; alıcının maliyet kaydı
            # ikinci geçişte (smm_yaz) bu tutardan türetilir. Aksi hâlde
            # satıcının hasılatı ile alıcının maliyeti tutmaz ve
            # konsolidasyonda eliminasyon denk gelmez.
            iliskiler = [i for i in self.y.grup_ici_iliskiler
                         if i["satici"] == sirket]
            grup_ici_toplam = 0.0
            if iliskiler and plan.var_mi("4025"):
                for i in iliskiler:
                    pay_tutar = ay_ciro * i.get("satici_ciro_payi", 0.05)
                    grup_ici_toplam += pay_tutar
                    self.grup_ici_satis[(sirket, i["alici"], donem)] = pay_tutar
                    adet = int(np.clip(round(pay_tutar / (ORT_FATURA[sirket] * 4.0)), 2, 40))
                    for tutar in self._parcala(pay_tutar, adet):
                        self.fis_kaydet(sirket, donem, tutar, "1025", "4025",
                                        f"Grup içi satış — {i['alici']}", plan)

            # --- Faaliyet giderleri ---
            # Gider tabanı DIŞ cirodur: bir distribütöre toplu fatura keserken
            # kendi müşterine yaptığın pazarlama/satış giderini yapmazsın.
            # Grup içi ciro üzerinden gider yazmak, konsolidasyonda hasılat
            # elimine edilince gider oranını yapay olarak şişirir.
            gider_tabani = ay_ciro * dis_payi
            # adet = o gider kaleminde ayda kaç ayrı belge/fatura oluştuğu
            giderler = [
                ("6010", din["personel"], "Personel gideri", 3),      # maaş, SGK, ek ödeme
                ("6020", 0.021, "Kira gideri", 2),
                ("6030", 0.034, "Pazarlama gideri", 14),
                ("6040", 0.028, "Genel yönetim gideri", 26),          # küçük tutarlı, çok belgeli
                ("6060", 0.011, "Danışmanlık gideri", 5),
            ]
            for grup_kod, oran, aciklama, adet in giderler:
                if not plan.var_mi(grup_kod):
                    continue
                toplam = gider_tabani * oran * (1 + self.rng.normal(0, 0.08))
                karsi = "2030" if grup_kod == "6010" else "2010"
                for tutar in self._parcala(toplam, adet):
                    self.fis_kaydet(sirket, donem, tutar, grup_kod, karsi, aciklama, plan)

            # --- Amortisman, faiz, vergi ---
            self.fis_kaydet(sirket, donem, ay_ciro * 0.018, "6050", "1520",
                            "Amortisman", plan, gun=son, kullanici="SISTEM")
            self.fis_kaydet(sirket, donem, ay_ciro * 0.015, "7020", "2020",
                            "Kredi faizi", plan, gun=son)
            self.fis_kaydet(sirket, donem, ay_ciro * 0.004, "1010", "7010",
                            "Mevduat faizi", plan, gun=son)
            self.fis_kaydet(sirket, donem, ay_ciro * 0.020, "8010", "2040",
                            "Kurumlar vergisi karşılığı", plan, gun=son,
                            kullanici="SISTEM")

            # --- Tahsilat ve ödemeler (her biri ayrı banka hareketi) ---
            for tutar in self._parcala(ay_ciro * 0.85, 48):
                self.fis_kaydet(sirket, donem, tutar, "1010", "1020",
                                "Müşteri tahsilatı", plan)
            for tutar in self._parcala(ay_ciro * 0.62, 34):
                self.fis_kaydet(sirket, donem, tutar, "2010", "1010",
                                "Tedarikçi ödemesi", plan)
            self.fis_kaydet(sirket, donem, ay_ciro * din["personel"] * 0.95,
                            "2030", "1010", "Maaş ödemesi", plan,
                            gun=ilk + timedelta(days=4), kullanici="SISTEM")

    def _parcala(self, toplam: float, adet: int) -> list[float]:
        """Toplamı gerçekçi biçimde parçalara böler (eşit değil)."""
        if adet <= 1:
            return [toplam]
        agirlik = self.rng.dirichlet(np.ones(adet) * 2.2)
        return [float(toplam * a) for a in agirlik]

    # ---------------- satılan malın maliyeti (2. geçiş) ----------------
    def smm_yaz(self):
        """Tüm şirketler üretildikten SONRA çalışır.

        Alıcının grup içi alım maliyeti, satıcının ona kestiği faturadan
        türetilir — kendi cirosundan tahmin edilmez. Kur çevrimi yüzünden
        iki taraf kuruşu kuruşuna tutmaz; işte K08 testinin ölçtüğü şey
        tam olarak bu farkın kabul edilebilir bantta kalıp kalmadığıdır."""
        pb = {k: s.fonksiyonel_para_birimi for k, s in self.y.sirketler.items()}
        for sirket, s in self.y.sirketler.items():
            plan = YerelPlan(self.y, s.hesap_plani, self.rnd)
            din = SIRKET_DINAMIGI[sirket]
            for donem in DONEMLER:
                ay_ciro = self.aylik_ciro.get((sirket, donem), 0.0)
                if ay_ciro <= 0:
                    continue
                smm_toplam = ay_ciro * din["smm"]

                # Bu şirkete grup içinden gelen alımlar, alıcının parasına çevrilir
                grup_ici_alim = 0.0
                for (satici, alici, d), tutar in self.grup_ici_satis.items():
                    if alici != sirket or d != donem:
                        continue
                    grup_ici_alim += tutar * self.y.kur(d, pb[satici]) / self.y.kur(d, pb[sirket])

                if grup_ici_alim > 0 and plan.var_mi("5025"):
                    for tutar in self._parcala(grup_ici_alim, 3):
                        self.fis_kaydet(sirket, donem, tutar, "5025", "2015",
                                        "Grup içi alım maliyeti", plan)
                # Kalanı dışarıdan alınmıştır; en az cironun %5'i kadar dış alım kalsın
                dis_alim = max(smm_toplam - grup_ici_alim, ay_ciro * 0.05)
                # ÖNCE stok girişi, SONRA satıldıkça maliyete geçiş.
                # Sadece maliyet yazıp alım kaydetmemek stok hesabını
                # yıl boyunca negatife sürükler — bilanço anlamsızlaşır.
                for tutar in self._parcala(dis_alim * 1.03, 6):
                    self.fis_kaydet(sirket, donem, tutar, "1030", "2010",
                                    "Stok alımı", plan)
                for tutar in self._parcala(dis_alim, 4):
                    self.fis_kaydet(sirket, donem, tutar, "5010", "1030",
                                    "SMM — stok çıkışı", plan)

    # ---------------- grup içi mutabakat ----------------
    def grup_ici_uret(self):
        """Mutabakat dosyaları — iki taraf da aynı işlemi kendi parasında bildirir.

        Tutarlar smm_yaz ile aynı kaynaktan (grup_ici_satis) gelir, böylece
        mutabakat dosyası muhasebe kayıtlarıyla tutarlıdır. T3 tuzağı bu
        tutarlılığı tek bir dönemde kasıtlı olarak bozar."""
        pb = {k: s.fonksiyonel_para_birimi for k, s in self.y.sirketler.items()}
        tur_sozluk = {(i["satici"], i["alici"]): i["tur"]
                      for i in self.y.grup_ici_iliskiler}
        for (satici, alici, donem), tutar in sorted(self.grup_ici_satis.items()):
            kur_s = self.y.kur(donem, pb[satici])
            kur_a = self.y.kur(donem, pb[alici])
            self.grup_ici.append({
                "sirket_kod": satici, "karsi_sirket": alici, "donem": donem,
                "tur": tur_sozluk.get((satici, alici), "Mal satışı"),
                "yon": "alacak", "tutar": round(tutar, 2)})
            self.grup_ici.append({
                "sirket_kod": alici, "karsi_sirket": satici, "donem": donem,
                "tur": tur_sozluk.get((satici, alici), "Mal satışı"),
                "yon": "borc", "tutar": round(tutar * kur_s / kur_a, 2)})

    # ==================================================================
    # TUZAKLAR
    # ==================================================================
    def tuzak_kaydet(self, kod, test, aciklama, detay):
        self.tuzaklar.append({"tuzak": kod, "beklenen_test": test,
                              "aciklama": aciklama, "detay": detay})

    def tuzaklari_ek(self):
        g = self.g
        y = self.y

        # --- T1: Mükerrer fiş (K02) --------------------------------------
        hedef = [f for f in self.fisler["TR01"]
                 if f["donem"] in ("2025-03", "2025-10") and f["borc"] > 0
                 and "Satış" not in f["aciklama"]]
        secilen = self.rnd.sample(hedef, 3)
        detaylar = []
        for f in secilen:
            es = [x for x in self.fisler["TR01"] if x["fis_no"] == f["fis_no"]]
            for satir in es:
                kopya = dict(satir)
                kopya["fis_no"] = satir["fis_no"] + "-K"
                kopya["kayit_zamani"] = satir["kayit_zamani"] + timedelta(days=1)
                self.fisler["TR01"].append(kopya)
            detaylar.append({"fis_no": f["fis_no"] + "-K", "donem": f["donem"],
                             "tutar": max(f["borc"], f["alacak"])})
        self.tuzak_kaydet("T1", "K02", "TR01'de 3 fiş birebir kopyalandı", detaylar)

        # --- T2: Dönem kayması / cut-off (K03) ---------------------------
        aralik = [f for f in self.fisler["DE01"] if f["donem"] == "2025-12"]
        fis_nolar = list({f["fis_no"] for f in aralik})
        secilen = self.rnd.sample(fis_nolar, 5)
        for f in self.fisler["DE01"]:
            if f["fis_no"] in secilen:
                f["belge_tarihi"] = date(2026, 1, self.rnd.randint(4, 18))
        self.tuzak_kaydet("T2", "K03",
                          "DE01 Aralık kapanışına 5 fiş, belge tarihi Ocak 2026 olduğu hâlde alındı",
                          [{"fis_no": x} for x in secilen])

        # --- T3: Grup içi eliminasyon farkı (K08) ------------------------
        # Haziran'da DE01, TR01'e olan borcunu eksik kaydetti.
        for kayit in self.grup_ici:
            if (kayit["sirket_kod"] == "DE01" and kayit["karsi_sirket"] == "TR01"
                    and kayit["donem"] == "2025-06"):
                eski = kayit["tutar"]
                kayit["tutar"] = round(eski * 0.82, 2)
                self.tuzak_kaydet("T3", "K08",
                                  "DE01'in TR01'e Haziran borcu %18 eksik kaydedildi",
                                  [{"donem": "2025-06", "dogru": eski, "kayitli": kayit["tutar"]}])

        # --- T4: Hesap planı kayması (K09) -------------------------------
        # DE01 Temmuz'da yeni bir gider hesabı açtı (BT ve yazılım giderlerini
        # "diğer faaliyet giderleri"nden ayırmak için) ama grup merkezine
        # haber vermedi. Hesap gerçek bir ad taşır — eşleme önerisi de zaten
        # ancak hesabın adına bakarak yapılabilir.
        sayac = 0
        for f in self.fisler["DE01"]:
            if f["yerel_hesap_kod"] == "6800" and f["donem"] >= "2025-07":
                f["yerel_hesap_kod"] = "6815"
                f["aciklama"] = "IT- und Softwarekosten"
                sayac += 1
        self.ozel_hesap_adlari[("DE01", "6815")] = "IT- und Softwarekosten"
        self.tuzak_kaydet("T4", "K09",
                          "DE01 Temmuz'da 6815 'IT- und Softwarekosten' hesabını açtı, "
                          "grup eşleme tablosuna eklenmedi",
                          [{"yerel_kod": "6815", "ad": "IT- und Softwarekosten",
                            "satir": sayac, "ilk_donem": "2025-07",
                            "dogru_grup_kod": "6040"}])

        # --- T5: Mesai dışı kayıt (K04) ----------------------------------
        hedef = [f for f in self.fisler["TR02"] if f["borc"] > 0][-40:]
        secilen = self.rnd.sample(hedef, 6)
        detaylar = []
        for f in secilen:
            z = f["kayit_zamani"]
            yeni = z.replace(hour=self.rnd.choice([2, 3, 23]))
            # bir kısmını pazar gününe kaydır
            while yeni.weekday() != 6:
                yeni += timedelta(days=1)
            for satir in self.fisler["TR02"]:
                if satir["fis_no"] == f["fis_no"]:
                    satir["kayit_zamani"] = yeni
            detaylar.append({"fis_no": f["fis_no"], "zaman": str(yeni)})
        self.tuzak_kaydet("T5", "K04", "TR02'de 6 fiş pazar günü ve gece saatlerinde girildi",
                          detaylar)

        # --- T6: Yetki limiti aşımı (K05) --------------------------------
        limit = y.kontrol_genel["onay_limitleri"]["TR01"]["tek_fis_limiti"]
        plan = YerelPlan(y, "VUK_TDHP", self.rnd)
        detaylar = []
        for donem, carpan in [("2025-05", 1.35), ("2025-09", 1.62)]:
            tutar = limit * carpan
            fis_no = self.fis_kaydet("TR01", donem, tutar, "6060", "2010",
                                     "Danışmanlık — proje bedeli", plan,
                                     kullanici="m.demir")
            detaylar.append({"fis_no": fis_no, "donem": donem, "tutar": tutar,
                             "limit": limit})
        self.tuzak_kaydet("T6", "K05", "TR01'de onay limitini aşan 2 tekil fiş", detaylar)

        # --- T7: Limit parçalama / splitting (K06) -----------------------
        limit2 = y.kontrol_genel["onay_limitleri"]["TR02"]["tek_fis_limiti"]
        plan2 = YerelPlan(y, "VUK_TDHP", self.rnd)
        gun = date(2025, 8, 14)
        detaylar = []
        for i in range(4):
            tutar = limit2 * self.rnd.uniform(0.88, 0.97)
            fis_no = self.fis_kaydet("TR02", "2025-08", tutar, "6040", "2010",
                                     "Ofis tadilat işi — kısmi hakediş", plan2,
                                     gun=gun, kullanici="b.sahin")
            detaylar.append({"fis_no": fis_no, "tutar": round(tutar, 2)})
        self.tuzak_kaydet("T7", "K06",
                          f"TR02'de aynı gün ({gun}) limitin hemen altında 4 fiş — limit {limit2:,.0f} TRY",
                          detaylar)

        # --- T8: Benford sapması + yuvarlak tutar (K07, K12) -------------
        # UK01'in ofis gideri hesabına elle uydurulmuş, yuvarlak tutarlar.
        plan3 = YerelPlan(y, "UK_COA", self.rnd)
        detaylar = []
        for donem in DONEMLER:
            for _ in range(11):
                # Uydurma tutarların ayırt edici özelliği YUVARLAKLIĞI, büyüklüğü değil.
                # UK01'in ofis gideri ölçeğinde kalmalı, yoksa şirketi batırır.
                tutar = float(self.rnd.choice([1000, 2000, 3000, 5000, 8000,
                                               9000, 9500, 9800]))
                self.fis_kaydet("UK01", donem, tutar, "6040", "2010",
                                "Office costs — sundry", plan3, kullanici="r.patel",
                                masraf_merkezi="MM-IDARI")
                detaylar.append({"donem": donem, "tutar": tutar})
        self.tuzak_kaydet("T8", "K07/K12",
                          "UK01 ofis gideri hesabına 132 adet uydurma, yuvarlak tutarlı fiş",
                          [{"adet": len(detaylar), "hesap_rolu": "6040 → UK 7500"}])

        # --- T9: Bilanço denkliği bozuk (K01) ----------------------------
        # UK01 Eylül'de tek taraflı bir kayıt — mizan denk gelmiyor.
        tek_taraf = sorted(
            (f for f in self.fisler["UK01"]
             if f["donem"] == "2025-09" and f["alacak"] > 0),
            key=lambda f: -f["alacak"])[:15]
        # Fark edilebilir bir tutar olmalı; kuruşluk bir denksizlik
        # gerçek hayatta yuvarlama farkı sanılıp geçilir.
        kurban = self.rnd.choice(tek_taraf)
        self.fisler["UK01"].remove(kurban)
        self.tuzak_kaydet("T9", "K01",
                          "UK01 Eylül mizanında tek taraflı kayıt — borç/alacak denkliği bozuk",
                          [{"donem": "2025-09", "fis_no": kurban["fis_no"],
                            "kayip_alacak": kurban["alacak"]}])

        # --- T10: Eksik dönem (K10) --------------------------------------
        # TR02'nin Kasım mizanı hiç gönderilmedi (geç kapanış).
        self.eksik_mizan = {("TR02", "2025-11")}
        self.tuzak_kaydet("T10", "K10",
                          "TR02'nin Kasım 2025 mizan dosyası hiç üretilmedi (geç kapanış)",
                          [{"sirket": "TR02", "donem": "2025-11"}])

        # --- T11: Ters bakiye (K11) --------------------------------------
        # TR01'de büyük bir iade, yurt içi satış hesabını borç bakiyeye düşürüyor.
        plan4 = YerelPlan(y, "VUK_TDHP", self.rnd)
        ay_ciro = self.satislar["TR01"]
        ay_ciro = ay_ciro[(ay_ciro["senaryo"] == "fiili")
                          & (ay_ciro["donem"] == "2025-02")]["tutar"].sum()
        tutar = ay_ciro * 0.78
        fis_no = self.fis_kaydet("TR01", "2025-02", tutar, "4010", "1020",
                                 "Toplu satış iadesi — kalite reddi", plan4,
                                 kullanici="a.yilmaz")
        self.tuzak_kaydet("T11", "K11",
                          "TR01 Şubat'ta yurt içi satış hesabı iade nedeniyle borç bakiye verdi",
                          [{"fis_no": fis_no, "tutar": round(tutar, 2)}])

        # --- T12: Görevler ayrılığı (K13) --------------------------------
        # TR02'de zaten tek kullanıcı var; onu belirginleştir.
        for f in self.fisler["TR02"]:
            if f["kullanici"] != "SISTEM" and self.rnd.random() < 0.94:
                f["kullanici"] = "b.sahin"
        self.tuzak_kaydet("T12", "K13",
                          "TR02'de kayıtların neredeyse tamamı tek kullanıcı (b.sahin) tarafından girildi",
                          [{"sirket": "TR02", "kullanici": "b.sahin"}])

        # --- T13 ve T14: biçim tuzakları (dosya yazımında uygulanır) -----
        self.tuzak_kaydet("T13", "topla.py",
                          "Sayı biçimi şirkete göre değişiyor: TR/DE '1.234,56' metin, "
                          "UK '1,234.56' metin, DE01 mizanı gerçek sayı",
                          [{"TR01": "metin, virgül ondalık"},
                           {"UK01": "metin, nokta ondalık"}])
        self.tuzak_kaydet("T14", "topla.py",
                          "Tarih biçimi ve dosya düzeni şirkete göre değişiyor: "
                          "TR aylık ayrı xlsx, DE tek xlsx 12 sekme, UK tek csv",
                          [{"TR": "%d.%m.%Y"}, {"DE": "%Y-%m-%d"}, {"UK": "%m/%d/%Y"}])

        g.iyi(f"{len(self.tuzaklar)} tuzak enjekte edildi.")

    # ==================================================================
    # MİZAN — yevmiyeden topla
    # ==================================================================
    def mizan_uret(self, sirket: str) -> pd.DataFrame:
        """Mizan = YILBAŞINDAN İTİBAREN KÜMÜLATİF (YTD) borç/alacak toplamı.

        Gerçek bir mizan dönem hareketini değil, o tarihe kadarki toplamı
        gösterir. Bu ayrım motorun işini doğrudan etkiler:
          - Bilanço kalemi zaten kümülatif bakiyedir, doğrudan kullanılır.
          - Gelir tablosu kalemi ise AYLIK tutara çevrilmelidir
            (YTD(t) - YTD(t-1)), çünkü IAS 21'de her ayın geliri o ayın
            ortalama kuruyla çevrilir — yıllık YTD'yi tek kurla çevirmek
            enflasyonist bir para biriminde büyük hata üretir.
        """
        df = pd.DataFrame(self.fisler[sirket])
        plan = YerelPlan(self.y, self.y.sirketler[sirket].hesap_plani, self.rnd)
        aylik = (df.groupby(["donem", "yerel_hesap_kod"], as_index=False)
                   [["borc", "alacak"]].sum())

        parcalar = []
        for kod, grup in aylik.groupby("yerel_hesap_kod"):
            s = (grup.set_index("donem")[["borc", "alacak"]]
                     .reindex(DONEMLER, fill_value=0.0)
                     .cumsum()
                     .reset_index(names="donem"))
            s["yerel_hesap_kod"] = kod
            parcalar.append(s)
        ozet = pd.concat(parcalar, ignore_index=True)

        # Hesap henüz hiç hareket görmediyse mizanda görünmez
        ozet = ozet[(ozet["borc"].abs() + ozet["alacak"].abs()) > 0.005].copy()

        ozet["yerel_hesap_ad"] = [
            self.ozel_hesap_adlari.get((sirket, k)) or plan.ad(k)
            for k in ozet["yerel_hesap_kod"]]
        ozet["sirket_kod"] = sirket
        return ozet.sort_values(["donem", "yerel_hesap_kod"])[
            ["sirket_kod", "donem", "yerel_hesap_kod",
             "yerel_hesap_ad", "borc", "alacak"]]


# ======================================================================
# DOSYA YAZIMI — her şirket kendi biçiminde
# ======================================================================

def yaz_tr(u: VeriUretici, sirket: str, mizan: pd.DataFrame, g: Gunluk) -> int:
    """TR şirketleri: her ay ayrı .xlsx, sayılar METİN (1.234,56), tarih gg.aa.yyyy."""
    n = 0
    for donem in DONEMLER:
        if (sirket, donem) in getattr(u, "eksik_mizan", set()):
            continue
        alt = mizan[mizan["donem"] == donem]
        if alt.empty:
            continue
        cikti = pd.DataFrame({
            "Hesap Kodu": alt["yerel_hesap_kod"],
            "Hesap Adı": alt["yerel_hesap_ad"],
            "Borç": [sayi_metni(v, ",", ".") for v in alt["borc"]],
            "Alacak": [sayi_metni(v, ",", ".") for v in alt["alacak"]],
        })
        yol = GIRDI / f"{sirket}_mizan_{donem}.xlsx"
        cikti.to_excel(yol, index=False, sheet_name="Mizan")
        n += 1
    return n


def yaz_de(u: VeriUretici, sirket: str, mizan: pd.DataFrame, g: Gunluk) -> int:
    """DE01: tek .xlsx, her ay bir sekme, sayılar gerçek sayı, tarih ISO."""
    yol = GIRDI / f"{sirket}_Summen_und_Saldenliste_2025.xlsx"
    with pd.ExcelWriter(yol, engine="openpyxl") as yazici:
        for donem in DONEMLER:
            alt = mizan[mizan["donem"] == donem]
            if alt.empty:
                continue
            pd.DataFrame({
                "Konto": alt["yerel_hesap_kod"],
                "Kontobezeichnung": alt["yerel_hesap_ad"],
                "Soll": alt["borc"].round(2),
                "Haben": alt["alacak"].round(2),
            }).to_excel(yazici, index=False, sheet_name=donem)
    return 1


def yaz_uk(u: VeriUretici, sirket: str, mizan: pd.DataFrame, g: Gunluk) -> int:
    """UK01: tek .csv, dönem kolonu içinde, sayılar METİN (1,234.56)."""
    cikti = pd.DataFrame({
        "Period": mizan["donem"],
        "Nominal Code": mizan["yerel_hesap_kod"],
        "Name": mizan["yerel_hesap_ad"],
        "Debit": [sayi_metni(v, ".", ",") for v in mizan["borc"]],
        "Credit": [sayi_metni(v, ".", ",") for v in mizan["alacak"]],
    })
    cikti.to_csv(GIRDI / f"{sirket}_trial_balance_2025.csv",
                 index=False, encoding="utf-8-sig")
    return 1


YEVMIYE_BASLIK = {
    "VUK_TDHP": {"fis_no": "Fiş No", "fis_tarihi": "Fiş Tarihi",
                 "belge_tarihi": "Belge Tarihi", "yerel_hesap_kod": "Hesap Kodu",
                 "borc": "Borç", "alacak": "Alacak", "aciklama": "Açıklama",
                 "kullanici": "Kullanıcı", "kayit_zamani": "Kayıt Zamanı",
                 "masraf_merkezi": "Masraf Merkezi"},
    "SKR04": {"fis_no": "Belegnummer", "fis_tarihi": "Buchungsdatum",
              "belge_tarihi": "Belegdatum", "yerel_hesap_kod": "Konto",
              "borc": "Soll", "alacak": "Haben", "aciklama": "Buchungstext",
              "kullanici": "Benutzer", "kayit_zamani": "Erfassungszeit",
              "masraf_merkezi": "Kostenstelle"},
    "UK_COA": {"fis_no": "Transaction No", "fis_tarihi": "Posting Date",
               "belge_tarihi": "Document Date", "yerel_hesap_kod": "Nominal Code",
               "borc": "Debit", "alacak": "Credit", "aciklama": "Details",
               "kullanici": "User", "kayit_zamani": "Created At",
               "masraf_merkezi": "Cost Centre"},
}


def yaz_yevmiye(u: VeriUretici, sirket: str, g: Gunluk) -> int:
    s = u.y.sirketler[sirket]
    bicim = s.bicim
    basliklar = YEVMIYE_BASLIK[s.hesap_plani]
    df = pd.DataFrame(u.fisler[sirket]).sort_values(["donem", "fis_no"])

    metin_sayi = sirket in ("TR01", "TR02", "UK01")
    cikti = pd.DataFrame({
        basliklar["fis_no"]: df["fis_no"],
        basliklar["fis_tarihi"]: [d.strftime(bicim["tarih_bicimi"]) for d in df["fis_tarihi"]],
        basliklar["belge_tarihi"]: [d.strftime(bicim["tarih_bicimi"]) for d in df["belge_tarihi"]],
        basliklar["yerel_hesap_kod"]: df["yerel_hesap_kod"],
        basliklar["aciklama"]: df["aciklama"],
        basliklar["borc"]: ([sayi_metni(v, bicim["ondalik_ayrac"], bicim["binlik_ayrac"])
                             for v in df["borc"]] if metin_sayi else df["borc"].round(2)),
        basliklar["alacak"]: ([sayi_metni(v, bicim["ondalik_ayrac"], bicim["binlik_ayrac"])
                               for v in df["alacak"]] if metin_sayi else df["alacak"].round(2)),
        basliklar["kullanici"]: df["kullanici"],
        basliklar["kayit_zamani"]: [z.strftime("%Y-%m-%d %H:%M:%S") for z in df["kayit_zamani"]],
        basliklar["masraf_merkezi"]: df["masraf_merkezi"],
    })
    ad = {"TR01": "TR01_yevmiye_2025", "TR02": "TR02_yevmiye_2025",
          "DE01": "DE01_Buchungsjournal_2025", "UK01": "UK01_nominal_activity_2025"}[sirket]
    if sirket == "UK01":
        cikti.to_csv(GIRDI / f"{ad}.csv", index=False, encoding="utf-8-sig")
    else:
        cikti.to_excel(GIRDI / f"{ad}.xlsx", index=False, sheet_name="Yevmiye")
    return len(cikti)


def yaz_butce_satis(u: VeriUretici, sirket: str, g: Gunluk):
    s = u.y.sirketler[sirket]
    b = u.butceler[sirket]
    kolon = {"VUK_TDHP": ("Hesap Kodu", "Dönem", "Bütçe", "Masraf Merkezi"),
             "SKR04": ("Konto", "Periode", "Budget", "Kostenstelle"),
             "UK_COA": ("Nominal Code", "Period", "Budget", "Cost Centre")}[s.hesap_plani]
    pd.DataFrame({
        kolon[0]: b["yerel_hesap_kod"], kolon[1]: b["donem"],
        kolon[2]: b["tutar"].round(2), kolon[3]: b["masraf_merkezi"],
    }).to_excel(GIRDI / f"{sirket}_butce_2025.xlsx", index=False, sheet_name="Butce")

    sa = u.satislar[sirket]
    kol = {"VUK_TDHP": ("Ürün Kodu", "Ürün Adı", "Kategori", "Miktar",
                        "Birim Fiyat", "Tutar", "Müşteri Tipi", "Dönem"),
           "SKR04": ("Artikelnummer", "Artikel", "Warengruppe", "Menge",
                     "Einzelpreis", "Betrag", "Kundengruppe", "Periode"),
           "UK_COA": ("SKU", "Product Name", "Category", "Qty",
                      "Unit Price", "Net Value", "Customer Type", "Period")}[s.hesap_plani]
    with pd.ExcelWriter(GIRDI / f"{sirket}_satis_detay_2025.xlsx",
                        engine="openpyxl") as yazici:
        for senaryo, sekme in (("fiili", "Fiili"), ("butce", "Butce")):
            alt = sa[sa["senaryo"] == senaryo]
            pd.DataFrame({
                kol[0]: alt["urun_kod"], kol[1]: alt["urun_ad"], kol[2]: alt["kategori"],
                kol[3]: alt["miktar"], kol[4]: alt["birim_fiyat"].round(2),
                kol[5]: alt["tutar"].round(2), kol[6]: alt["musteri_tipi"],
                kol[7]: alt["donem"],
            }).to_excel(yazici, index=False, sheet_name=sekme)


def yaz_grup_ici(u: VeriUretici, g: Gunluk):
    df = pd.DataFrame(u.grup_ici)
    for sirket, alt in df.groupby("sirket_kod"):
        pd.DataFrame({
            "Karşı Şirket": alt["karsi_sirket"], "Dönem": alt["donem"],
            "Tür": alt["tur"], "Yön": alt["yon"], "Tutar": alt["tutar"].round(2),
        }).to_excel(GIRDI / f"{sirket}_grup_ici_mutabakat_2025.xlsx",
                    index=False, sheet_name="GrupIci")


# ======================================================================
def main():
    g = Gunluk("veri_uret")
    y = yukle()
    g.bilgi(y.ozet())

    # Eski girdileri temizle — üretim tekrar edilebilir olmalı
    for eski in GIRDI.glob("*"):
        eski.unlink()
    g.bilgi(f"Girdi dizini temizlendi: {GIRDI}")

    u = VeriUretici(y, g)

    for kod in y.sirketler:
        u.sirket_uret(kod)
        g.iyi(f"{kod}: {len(u.fisler[kod]):,} yevmiye satırı üretildi")
    u.smm_yaz()
    g.iyi("Satılan malın maliyeti yazıldı (grup içi alımlar satıcının faturasından)")
    u.grup_ici_uret()
    g.iyi(f"Grup içi mutabakat: {len(u.grup_ici)} satır")

    u.tuzaklari_ek()

    ozet_satir = []
    for kod in y.sirketler:
        mizan = u.mizan_uret(kod)
        yazici = {"TR01": yaz_tr, "TR02": yaz_tr, "DE01": yaz_de, "UK01": yaz_uk}[kod]
        dosya = yazici(u, kod, mizan, g)
        yev = yaz_yevmiye(u, kod, g)
        yaz_butce_satis(u, kod, g)
        # Mizan YTD olduğu için denklik SON dönemde kontrol edilir
        son = mizan[mizan["donem"] == DONEMLER[-1]]
        fark = round(son["borc"].sum() - son["alacak"].sum(), 2)
        ozet_satir.append([kod, dosya, f"{yev:,}", f"{len(mizan):,}",
                           para(son["borc"].sum(), 0), para(fark, 2)])
        u.g.iz("sirket_uretildi", sirket=kod, yevmiye_satir=yev,
               mizan_satir=len(mizan), denklik_farki=fark)
    yaz_grup_ici(u, g)

    with open(ORNEK / "TUZAK_CEVAP_ANAHTARI.json", "w", encoding="utf-8") as f:
        json.dump({"tohum": TOHUM, "uretim": str(datetime.now()),
                   "tuzaklar": u.tuzaklar}, f, ensure_ascii=False, indent=2, default=str)

    tablo_yaz("Üretim özeti",
              ozet_satir,
              ["Şirket", "Mizan dosya", "Yevmiye satır", "Mizan satır",
               "Yıl sonu YTD borç", "Denklik farkı"])

    dosyalar = sorted(GIRDI.glob("*"))
    toplam_mb = sum(d.stat().st_size for d in dosyalar) / 1e6
    g.bilgi(f"\nveri/girdi/ → {len(dosyalar)} dosya, {toplam_mb:.1f} MB")
    g.bilgi(f"Cevap anahtarı: veri/ornek/TUZAK_CEVAP_ANAHTARI.json ({len(u.tuzaklar)} tuzak)")
    g.bitir({"dosya": len(dosyalar), "tuzak": len(u.tuzaklar)})


if __name__ == "__main__":
    main()
