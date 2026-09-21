# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ [0] KAYNAK: veri kaynağı doğrulama ve köken kaydı.

NEDEN VAR
  Bu modül bir hatanın sonucunda yazıldı. Sistem, tanıyamadığı bir dosyayı
  sessizce atlıyor ve boru hattına devam ediyordu. Kullanıcı kendi mizanını
  yükleyip çalıştırdığında, dosya "şirket kodu tanınmadı" diye atlandı,
  dizinde duran demo veri işlendi ve ortaya kullanıcının verisiyle hiçbir
  ilgisi olmayan, ama tamamen inandırıcı görünen bir kapanış paketi çıktı.

  Finansal bir araçta bu, hata sınıflarının en tehlikelisidir: yanlış cevap
  değil, BAŞKA BİR SORUNUN doğru cevabı. Kullanıcı bunu fark edemez, çünkü
  çıktı kusursuz görünür.

KURAL
  Girdi dizinindeki HER dosya ya tanınır ya da boru hattı DURUR.
  Sessiz atlama yoktur. Kısmi işleme yoktur. Bir dosya okunamıyorsa
  sebebi söylenir ve ne yapılacağı gösterilir.

KÖKEN KAYDI
  Her çalıştırma, hangi dosyalardan beslendiğini parmak izleriyle
  veri/ara/koken.json dosyasına yazar. Panodan Excel'e kadar bütün
  çıktılar bu kaydı taşır; "bu rapor hangi veriden üretildi" sorusunun
  cevabı artık belgeye basılıdır.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gunluk import dosya_parmak_izi                    # noqa: E402
from sema import ARA_DIZIN, VERI_DIZIN                 # noqa: E402

GIRDI = VERI_DIZIN / "girdi"
KOKEN_DOSYASI = ARA_DIZIN / "koken.json"

IZINLI_UZANTI = {".xlsx", ".xls", ".csv"}

# Demo veri üretecinin ürettiği dosyaların imzası. Kullanıcının kendi
# dosyalarından ayırt etmek için kullanılır; ikisinin karışması, çıktının
# hangi veriden geldiğini belirsizleştirir.
DEMO_DESENI = re.compile(r"^(TR01|TR02|DE01|UK01)_.+\.(xlsx|csv)$", re.I)


class KaynakHatasi(Exception):
    """Veri kaynağı doğrulanamadı. Boru hattı BAŞLAMAMALIDIR."""


@dataclass
class Dosya:
    ad: str
    yol: str
    boyut_kb: int
    parmak: str
    tip: str | None = None          # mizan / yevmiye / butce / satis / grup_ici
    sirket: str | None = None
    demo_mu: bool = False
    tanindi: bool = False
    neden: str = ""                 # tanınmadıysa sebebi


@dataclass
class Rapor:
    zaman: str
    dizin: str
    dosyalar: list[Dosya] = field(default_factory=list)
    demo_sayisi: int = 0
    kullanici_sayisi: int = 0
    taninmayan: list[Dosya] = field(default_factory=list)
    sorunlar: list[str] = field(default_factory=list)

    @property
    def toplam(self) -> int:
        return len(self.dosyalar)

    @property
    def gecerli(self) -> bool:
        return not self.sorunlar

    def veri_seti_adi(self) -> str:
        if self.demo_sayisi and not self.kullanici_sayisi:
            return "demo"
        if self.kullanici_sayisi and not self.demo_sayisi:
            return "kullanici"
        if self.demo_sayisi and self.kullanici_sayisi:
            return "KARISIK"
        return "bos"


def tara(y, dosya_tipi_fn, sirket_bul_fn) -> Rapor:
    """Girdi dizinini tarar ve her dosyayı sınıflandırır.

    dosya_tipi_fn / sirket_bul_fn: topla.py'deki tanıma işlevleri.
    Buraya parametre olarak geçilir ki tanıma mantığı tek yerde kalsın.
    """
    r = Rapor(zaman=datetime.now().isoformat(timespec="seconds"), dizin=str(GIRDI))
    if not GIRDI.exists():
        r.sorunlar.append(f"Girdi dizini yok: {GIRDI}")
        return r

    kodlar = list(y.sirketler)
    for yol in sorted(GIRDI.iterdir()):
        if yol.is_dir() or yol.name.startswith("."):
            continue
        d = Dosya(ad=yol.name, yol=str(yol),
                  boyut_kb=round(yol.stat().st_size / 1024),
                  parmak=dosya_parmak_izi(yol))

        if yol.suffix.lower() not in IZINLI_UZANTI:
            d.neden = (f"desteklenmeyen uzantı '{yol.suffix}' "
                       f"(kabul edilenler: {', '.join(sorted(IZINLI_UZANTI))})")
            r.taninmayan.append(d); r.dosyalar.append(d); continue

        d.demo_mu = bool(DEMO_DESENI.match(yol.name))
        d.tip = dosya_tipi_fn(yol.name)
        d.sirket = sirket_bul_fn(yol.name, kodlar)

        if d.tip is None:
            d.neden = ("veri tipi anlaşılmadı: dosya adında mizan / yevmiye / "
                       "butce / satis / grup_ici anahtar kelimelerinden biri yok")
        elif d.sirket is None:
            d.neden = (f"şirket kodu anlaşılmadı: dosya adında tanımlı şirket "
                       f"kodlarından ({', '.join(kodlar)}) hiçbiri geçmiyor")
        else:
            d.tanindi = True

        if not d.tanindi:
            r.taninmayan.append(d)
        elif d.demo_mu:
            r.demo_sayisi += 1
        else:
            r.kullanici_sayisi += 1
        r.dosyalar.append(d)

    # ---- Doğrulama kuralları ----
    if r.toplam == 0:
        r.sorunlar.append("Girdi dizini boş. İşlenecek dosya yok.")

    if r.taninmayan:
        r.sorunlar.append(
            f"{len(r.taninmayan)} dosya tanınmadı. Bunlar SESSİZCE ATLANMAZ: "
            f"tanınmayan bir dosya varken üretilen çıktı, kullanıcının "
            f"verisini içermediği hâlde eksiksiz görünür.")

    if r.demo_sayisi and r.kullanici_sayisi:
        r.sorunlar.append(
            f"Girdi dizininde HEM demo verisi ({r.demo_sayisi} dosya) HEM de "
            f"başka dosyalar ({r.kullanici_sayisi} dosya) var. Hangi veri "
            f"setinden rapor üretileceği belirsiz; ikisi karıştırılırsa çıktı "
            f"anlamsız olur.")

    return r


def rapor_yaz(r: Rapor, g=None) -> None:
    """Tarama sonucunu konsola basar."""
    yaz = g.bilgi if g else print
    yaz(f"Girdi dizini: {r.dizin}")
    yaz(f"  {r.toplam} dosya · veri seti: {r.veri_seti_adi()} "
        f"(demo {r.demo_sayisi}, diğer {r.kullanici_sayisi}, "
        f"tanınmayan {len(r.taninmayan)})")
    if r.taninmayan:
        (g.uyari if g else print)("Tanınmayan dosyalar:")
        for d in r.taninmayan:
            yaz(f"    {d.ad}  ({d.boyut_kb} KB)")
            yaz(f"      sebep: {d.neden}")


def dogrula(r: Rapor, zorla: bool = False, g=None) -> None:
    """Sorun varsa KaynakHatasi fırlatır. zorla=True yalnızca kullanıcı
    riski bilerek kabul ettiğinde geçilir ve çıktılara damgalanır."""
    if r.gecerli:
        return
    satirlar = ["", "=" * 70, "VERİ KAYNAĞI DOĞRULANAMADI", "=" * 70]
    for s in r.sorunlar:
        satirlar.append(f"  · {s}")
    if r.taninmayan:
        satirlar.append("")
        satirlar.append("  Tanınmayan dosyalar:")
        for d in r.taninmayan:
            satirlar.append(f"    - {d.ad}")
            satirlar.append(f"      {d.neden}")
    satirlar += ["", "  NE YAPILMALI", "  " + "-" * 66]

    if r.taninmayan:
        satirlar += [
            "  Kendi mizanınızı işletmek istiyorsanız, dosya için bir şirket",
            "  profili oluşturun. Tek komut yeter:",
            "",
            "      py araclar/profil_olustur.py \"veri/girdi/DOSYA_ADI\"",
            "",
            "  Bu araç dosyayı açar, şirket adını, dönemi, para birimini ve",
            "  hesap planını tespit eder, yapılandırmayı üretir ve dosyayı",
            "  tanınacak şekilde adlandırır.",
        ]
    if r.demo_sayisi and r.kullanici_sayisi:
        satirlar += [
            "",
            "  Demo verisiyle kendi verinizi ayırın. Demo dosyaları silmek için:",
            "",
            "      py araclar/girdi_temizle.py --demo",
            "",
            "  Kendi dosyalarınızı silmek için: --kullanici",
        ]
    satirlar += [
        "",
        "  Riski bilerek yine de devam etmek isterseniz (ÖNERİLMEZ):",
        "",
        "      py src/boru.py --kaynak-zorla",
        "",
        "  Bu durumda üretilen bütün çıktılara 'EKSİK VERİ' damgası basılır.",
        "=" * 70, "",
    ]
    metin = "\n".join(satirlar)
    if zorla:
        if g:
            g.uyari("KAYNAK DOĞRULAMASI ZORLA GEÇİLDİ. Çıktılar damgalanacak.")
            for s in r.sorunlar:
                g.uyari(f"  {s}")
        return
    raise KaynakHatasi(metin)


def koken_yaz(r: Rapor, zorlandi: bool = False) -> dict:
    """Köken kaydını diske yazar ve döndürür. Çıktılar bunu okur."""
    kayit = {
        "zaman": r.zaman,
        "dizin": r.dizin,
        "veri_seti": r.veri_seti_adi(),
        "dosya_sayisi": r.toplam,
        "demo_sayisi": r.demo_sayisi,
        "kullanici_sayisi": r.kullanici_sayisi,
        "taninmayan_sayisi": len(r.taninmayan),
        "zorlandi": zorlandi,
        "guvenilir": r.gecerli and not zorlandi,
        "sorunlar": r.sorunlar,
        "dosyalar": [
            {"ad": d.ad, "parmak": d.parmak, "kb": d.boyut_kb,
             "tip": d.tip, "sirket": d.sirket, "demo": d.demo_mu,
             "tanindi": d.tanindi, "neden": d.neden}
            for d in r.dosyalar
        ],
    }
    ARA_DIZIN.mkdir(parents=True, exist_ok=True)
    KOKEN_DOSYASI.write_text(
        json.dumps(kayit, ensure_ascii=False, indent=2), encoding="utf-8")
    return kayit


def koken_oku() -> dict | None:
    """Çıktı üreticileri bunu çağırır. Yoksa None."""
    if not KOKEN_DOSYASI.exists():
        return None
    try:
        return json.loads(KOKEN_DOSYASI.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def koken_ozeti(k: dict | None) -> str:
    """Çıktılara basılacak tek satırlık köken özeti."""
    if not k:
        return "Köken kaydı yok: bu çıktının hangi veriden üretildiği bilinmiyor."
    ad = {"demo": "sentetik demo verisi", "kullanici": "kullanıcı verisi",
          "KARISIK": "KARIŞIK (demo + kullanıcı)", "bos": "boş"}.get(
              k["veri_seti"], k["veri_seti"])
    s = (f"Kaynak: {ad} · {k['dosya_sayisi']} dosya · "
         f"okuma {k['zaman'][:16].replace('T', ' ')}")
    if not k.get("guvenilir", True):
        s += "  ⚠ EKSİK VERİ: doğrulama zorla geçildi"
    return s


if __name__ == "__main__":
    from gunluk import Gunluk, tablo_yaz
    from sema import yukle
    import topla as T

    g = Gunluk("kaynak")
    y = yukle()
    r = tara(y, T.dosya_tipi, T.sirket_bul)
    rapor_yaz(r, g)
    tablo_yaz("Dosya sınıflandırması",
              [[d.ad[:42], d.tip or "-", d.sirket or "-",
                "demo" if d.demo_mu else ("kullanıcı" if d.tanindi else "-"),
                "tamam" if d.tanindi else "TANINMADI"]
               for d in r.dosyalar],
              ["Dosya", "Tip", "Şirket", "Küme", "Durum"], max_satir=60)
    try:
        dogrula(r, g=g)
        g.iyi("Veri kaynağı doğrulandı.")
    except KaynakHatasi as e:
        print(e)
        g.hata("Doğrulama başarısız.")
    koken_yaz(r)
    g.bitir({"dosya": r.toplam, "taninmayan": len(r.taninmayan),
             "gecerli": r.gecerli})
