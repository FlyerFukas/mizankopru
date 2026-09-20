# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ. Günlük ve denetim izi altyapısı.

Neden ayrı bir modül: Regüle bir süreçte "sonuç doğru mu" sorusu kadar
"bu sonuca nasıl varıldı" sorusu da denetlenir. Boru hattının her adımı
buraya girdi/çıktı parmak izini bırakır; denetçi geriye doğru yürüyebilir.

Her scriptin ilk satırı: from gunluk import Gunluk  (ya da baslat())
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# --- Windows konsolu cp1254 ile açılıyor; Türkçe çıktı için UTF-8'e zorla -----
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8")
    except Exception:
        pass

KOK = Path(__file__).resolve().parent.parent
GUNLUK_DIZIN = KOK / "gunluk"
GUNLUK_DIZIN.mkdir(exist_ok=True)

DENETIM_IZI = GUNLUK_DIZIN / "denetim_izi.jsonl"

_RENK = {
    "bilgi": "", "iyi": "", "uyari": "", "hata": "", "baslik": "",
}


def _simdi() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def dosya_parmak_izi(yol: Path | str) -> str:
    """Dosyanın SHA-256'sının ilk 16 hanesi. Girdi değişti mi sorusunun cevabı."""
    yol = Path(yol)
    if not yol.exists():
        return "YOK"
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()[:16]


def veri_parmak_izi(nesne) -> str:
    """DataFrame ya da herhangi bir nesnenin içerik parmak izi."""
    try:
        import pandas as pd
        if isinstance(nesne, pd.DataFrame):
            ham = pd.util.hash_pandas_object(nesne, index=True).values.tobytes()
            return hashlib.sha256(ham).hexdigest()[:16]
    except Exception:
        pass
    return hashlib.sha256(repr(nesne).encode("utf-8")).hexdigest()[:16]


class Gunluk:
    """Bir boru hattı adımının günlüğü + denetim izi kaydı.

    Kullanım:
        g = Gunluk("topla")
        g.bilgi("...")
        g.iz("okundu", dosya="x.xlsx", satir=1200)
        g.bitir(ozet={"satir": 1200})
    """

    def __init__(self, adim: str, sessiz: bool = False):
        self.adim = adim
        self.sessiz = sessiz
        self.baslangic = time.time()
        self.olaylar: list[dict] = []
        self.uyarilar = 0
        self.hatalar = 0
        self.dosya = GUNLUK_DIZIN / f"{adim}.log"
        self._yaz_dosya(f"\n{'='*70}\n{_simdi()}  ADIM: {adim}\n{'='*70}")
        self.baslik(f"[{adim}]")

    # --- konsol ---------------------------------------------------------
    def _cikti(self, isaret: str, mesaj: str):
        if not self.sessiz:
            print(f"{isaret} {mesaj}", flush=True)
        self._yaz_dosya(f"{_simdi()}  {isaret} {mesaj}")

    def _yaz_dosya(self, satir: str):
        with open(self.dosya, "a", encoding="utf-8") as f:
            f.write(satir + "\n")

    def baslik(self, mesaj: str):
        self._cikti("»", mesaj)

    def bilgi(self, mesaj: str):
        self._cikti(" ", mesaj)

    def iyi(self, mesaj: str):
        self._cikti(" +", mesaj)

    def uyari(self, mesaj: str):
        self.uyarilar += 1
        self._cikti(" !", mesaj)

    def hata(self, mesaj: str):
        self.hatalar += 1
        self._cikti(" X", mesaj)

    # --- denetim izi ----------------------------------------------------
    def iz(self, olay: str, **alanlar):
        """Denetim izine bir olay yaz. Serbest alanlar JSON'a olduğu gibi girer."""
        kayit = {"zaman": _simdi(), "adim": self.adim, "olay": olay, **alanlar}
        self.olaylar.append(kayit)
        with open(DENETIM_IZI, "a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False, default=str) + "\n")

    def bitir(self, ozet: dict | None = None) -> dict:
        sure = time.time() - self.baslangic
        sonuc = {
            "adim": self.adim,
            "sure_sn": round(sure, 2),
            "uyari": self.uyarilar,
            "hata": self.hatalar,
            "ozet": ozet or {},
        }
        self.iz("adim_bitti", **sonuc)
        durum = "HATA" if self.hatalar else ("UYARI" if self.uyarilar else "TAMAM")
        self._cikti("»", f"[{self.adim}] {durum}, {sure:.2f} sn"
                         + (f" · {self.uyarilar} uyarı" if self.uyarilar else "")
                         + (f" · {self.hatalar} hata" if self.hatalar else ""))
        return sonuc


def tablo_yaz(baslik: str, satirlar: list[list], basliklar: list[str], max_satir: int = 30):
    """Konsola hizalı tablo basar. Pano/Excel öncesi hızlı göz kontrolü için."""
    if not satirlar:
        print(f"\n{baslik}: (boş)")
        return
    kolonlar = list(zip(*([basliklar] + [[str(h) for h in s] for s in satirlar])))
    genislik = [max(len(str(h)) for h in k) for k in kolonlar]
    print(f"\n{baslik}")
    print("  " + "  ".join(str(b).ljust(g) for b, g in zip(basliklar, genislik)))
    print("  " + "  ".join("-" * g for g in genislik))
    for s in satirlar[:max_satir]:
        print("  " + "  ".join(str(h).ljust(g) for h, g in zip(s, genislik)))
    if len(satirlar) > max_satir:
        print(f"  ... ({len(satirlar) - max_satir} satır daha)")


def para(deger, basamak: int = 0) -> str:
    """Türk finans biçimi: binlik nokta, ondalık virgül."""
    try:
        d = float(deger)
    except (TypeError, ValueError):
        return "-"
    metin = f"{abs(d):,.{basamak}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return f"-{metin}" if d < 0 else metin


def hata_yakala(fn):
    """Boru hattı adımlarını sarmalar: beklenmeyen hata denetim izine düşer."""
    def sarmal(*a, **k):
        try:
            return fn(*a, **k)
        except Exception as e:
            with open(DENETIM_IZI, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "zaman": _simdi(), "olay": "cokme",
                    "fonksiyon": fn.__name__, "hata": str(e),
                    "iz": traceback.format_exc()[-2000:],
                }, ensure_ascii=False) + "\n")
            print(f"\n X ÇÖKME [{fn.__name__}]: {e}", file=sys.stderr)
            raise
    return sarmal
