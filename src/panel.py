# -*- coding: utf-8 -*-
# MizanKöprü — çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ — PANEL: yerel web arayüzü.

GÖREV
  Boru hattını terminal yerine tarayıcıdan çalıştırmak. Her adım bir kart,
  her çalıştırma canlı log, her çıktı tıklanabilir bir bağlantı. Kendi Excel
  dosyalarını sürükle-bırak ile yükleyip üzerinde çalıştırmak da buradan.

NEDEN EK KÜTÜPHANE YOK
  Python'un kendi http.server'ı yetiyor. Flask/FastAPI eklemek, aracı
  kullanacak finansçının önüne bir kurulum adımı daha koyardı. Panel
  `py src/panel.py` ile açılır, başka hiçbir şey gerekmez.

GÜVENLİK
  Sunucu yalnızca 127.0.0.1'e bağlanır — ağdan erişilemez. Yüklenen dosya
  adları temizlenir, yalnızca .xlsx/.xls/.csv kabul edilir ve hedef dizinin
  dışına yazılamaz.

ÇALIŞTIRMA
  py src/panel.py            varsayılan port 8765, tarayıcı otomatik açılır
  py src/panel.py --port 9000
  py src/panel.py --tarayici-acma
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import queue
import re
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

# Windows konsolu cp1254 ile açılıyor; kutu çizgileri ve Türkçe karakterler
# aksi hâlde UnicodeEncodeError veriyor. gunluk.py bunu kendi içinde yapar
# ama panel onu içe aktarmadan da çalışabilmeli.
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8")
    except Exception:
        pass

GIRDI = KOK / "veri" / "girdi"
CIKTI = KOK / "cikti"
GUNLUK = KOK / "gunluk"
SABLON = KOK / "src" / "panel_sablon.html"

IZINLI_UZANTI = {".xlsx", ".xls", ".csv"}
AZAMI_DOSYA_MB = 40

ADIMLAR = [
    ("veri_uret", "araclar/veri_uret.py", "Demo veri",
     "Sentetik ERP verisi üretir — 4 şirket, 41 dosya, 14 kasıtlı tuzak. "
     "Kendi verinizi yüklediyseniz bunu ÇALIŞTIRMAYIN: girdi dizinini temizler."),
    ("topla", "src/topla.py", "[1] Topla",
     "Dağınık dosyaları tek şemaya indirir. Farklı kolon adı, sayı ve tarih "
     "biçimi, çok sekmeli kitaplar burada normalize edilir."),
    ("esle", "src/esle.py", "[2] Eşle",
     "Yerel hesap kodlarını grup hesap planına bağlar. Eşleşmeyen hesap "
     "atılmaz, askıya alınır."),
    ("cevir", "src/cevir.py", "[3] Çevir",
     "IAS 21 kur çevrimi, grup içi eliminasyon ve azınlık payı. Gelir tablosu "
     "her ayın kendi ortalama kuruyla çevrilir."),
    ("kontrol", "src/kontrol.py", "[4] Kontrol",
     "14 iç kontrol testi. Bilanço denkliğinden Benford'a, limit parçalamadan "
     "görevler ayrılığına."),
    ("sapma", "src/sapma.py", "[5] Sapma",
     "Bütçe-fiili köprüsü: fiyat / karışım / hacim / kur ayrıştırması. "
     "Özdeşlik her çalıştırmada sınanır."),
    ("pano", "src/pano.py", "[6a] Pano",
     "Tek dosyalık HTML kapanış panosu."),
    ("excel", "src/excel.py", "[6b] Excel",
     "9 sayfalık konsolidasyon paketi."),
    ("rapor", "araclar/rapor_uret.py", "Rapor (PDF)",
     "12 sayfalık proje raporu. Rakamlar güncel çıktı dosyalarından okunur."),
]
ADIM_SOZLUK = {a[0]: a for a in ADIMLAR}

CIKTI_DOSYALARI = [
    ("pano.html", "Kapanış panosu", "HTML"),
    ("konsolidasyon_paketi.xlsx", "Konsolidasyon paketi", "Excel · 9 sayfa"),
    ("MizanKopru-Proje-Raporu.pdf", "Proje raporu", "PDF · 12 sayfa"),
    ("bulgular.csv", "Kontrol bulguları", "CSV"),
    ("sapma_koprusu.csv", "Sapma köprüsü", "CSV"),
    ("sapma_yorumu.md", "Sapma yorumu", "Markdown"),
    ("bulgu_triyaji.json", "Bulgu triyajı", "JSON"),
    ("hesap_eslesme_onerisi.csv", "Eşleme önerisi", "CSV"),
]


# ======================================================================
# ÇALIŞTIRICI
# ======================================================================

class Calistirici:
    """Boru hattı adımlarını arka planda çalıştırır, çıktıyı abonelere akıtır."""

    def __init__(self):
        self.kilit = threading.Lock()
        self.aktif: str | None = None
        self.surec: subprocess.Popen | None = None
        self.aboneler: list[queue.Queue] = []
        self.gecmis: list[dict] = []
        self.iptal = False

    # --- yayın ---
    def abone_ol(self) -> queue.Queue:
        k = queue.Queue(maxsize=2000)
        with self.kilit:
            self.aboneler.append(k)
        return k

    def abonelikten_cik(self, k: queue.Queue):
        with self.kilit:
            if k in self.aboneler:
                self.aboneler.remove(k)

    def yayinla(self, tur: str, **alanlar):
        olay = {"tur": tur, "zaman": time.time(), **alanlar}
        with self.kilit:
            hedefler = list(self.aboneler)
        for k in hedefler:
            try:
                k.put_nowait(olay)
            except queue.Full:
                pass

    # --- çalıştırma ---
    def mesgul(self) -> bool:
        return self.aktif is not None

    def calistir(self, adimlar: list[str]) -> tuple[bool, str]:
        if self.mesgul():
            return False, f"Zaten çalışıyor: {self.aktif}"
        bilinmeyen = [a for a in adimlar if a not in ADIM_SOZLUK]
        if bilinmeyen:
            return False, f"Bilinmeyen adım: {bilinmeyen}"
        self.iptal = False
        threading.Thread(target=self._zincir, args=(adimlar,), daemon=True).start()
        return True, "başladı"

    def durdur(self) -> bool:
        self.iptal = True
        s = self.surec
        if s and s.poll() is None:
            try:
                s.terminate()
                return True
            except Exception:
                return False
        return False

    def _zincir(self, adimlar: list[str]):
        toplam_basla = time.time()
        self.yayinla("zincir_basladi", adimlar=adimlar)
        for i, ad in enumerate(adimlar, 1):
            if self.iptal:
                self.yayinla("satir", metin="\n⨯ Kullanıcı tarafından durduruldu.",
                             seviye="hata")
                break
            if not self._tek(ad, i, len(adimlar)):
                self.yayinla("satir",
                             metin=f"\n⨯ [{ad}] başarısız — zincir durduruldu.",
                             seviye="hata")
                break
        self.aktif = None
        self.yayinla("zincir_bitti", sure=round(time.time() - toplam_basla, 1))

    def _tek(self, ad: str, sira: int, toplam: int) -> bool:
        _, betik, baslik, _ = ADIM_SOZLUK[ad]
        self.aktif = ad
        basla = time.time()
        self.yayinla("adim_basladi", adim=ad, baslik=baslik, sira=sira, toplam=toplam)
        self.yayinla("satir",
                     metin=f"\n{'─'*62}\n▶ [{sira}/{toplam}] {baslik}  ({betik})\n{'─'*62}",
                     seviye="baslik")

        ortam = dict(os.environ)
        ortam["PYTHONIOENCODING"] = "utf-8"
        ortam["PYTHONUNBUFFERED"] = "1"
        try:
            self.surec = subprocess.Popen(
                [sys.executable, "-u", str(KOK / betik)],
                cwd=str(KOK), env=ortam, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                errors="replace", bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception as e:
            self.yayinla("satir", metin=f"Başlatılamadı: {e}", seviye="hata")
            self.aktif = None
            return False

        uyari = hata = 0
        for satir in self.surec.stdout:
            satir = satir.rstrip("\n")
            seviye = "bilgi"
            if satir.lstrip().startswith("!"):
                seviye, uyari = "uyari", uyari + 1
            elif satir.lstrip().startswith(("X", "⨯")) or "Traceback" in satir:
                seviye, hata = "hata", hata + 1
            elif satir.lstrip().startswith("+"):
                seviye = "iyi"
            self.yayinla("satir", metin=satir, seviye=seviye)

        kod = self.surec.wait()
        self.surec = None
        sure = round(time.time() - basla, 1)
        basarili = kod == 0
        kayit = {"adim": ad, "baslik": baslik, "sure": sure, "basarili": basarili,
                 "uyari": uyari, "hata": hata,
                 "zaman": datetime.now().strftime("%H:%M:%S")}
        self.gecmis = [g for g in self.gecmis if g["adim"] != ad] + [kayit]
        self.yayinla("adim_bitti", **kayit)
        self.aktif = None
        return basarili


CALISTIRICI = Calistirici()


# ======================================================================
# DURUM
# ======================================================================

def guvenli_ad(ad: str) -> str | None:
    """Dosya adını temizler. Dizin geçişi ve beklenmedik uzantı reddedilir."""
    ad = os.path.basename(ad.replace("\\", "/")).strip()
    if not ad or ad.startswith("."):
        return None
    ad = re.sub(r'[<>:"|?*\x00-\x1f]', "_", ad)
    if Path(ad).suffix.lower() not in IZINLI_UZANTI:
        return None
    return ad


def anahtar_durumu() -> dict:
    try:
        from zeka import Zeka
        z = Zeka()
        ayar = z.ayar
        return {"var": z.aktif, "model": z.model if z.aktif else None,
                "neden": "" if z.aktif else z.neden,
                "onbellek": bool(ayar.get("onbellek", True))}
    except Exception as e:
        return {"var": False, "model": None, "neden": str(e)[:120],
                "onbellek": False}


def girdi_durumu() -> dict:
    if not GIRDI.exists():
        return {"dosya": 0, "boyut_mb": 0, "liste": [], "demo_mu": False}
    dosyalar = [d for d in sorted(GIRDI.iterdir())
                if d.is_file() and d.suffix.lower() in IZINLI_UZANTI]
    toplam = sum(d.stat().st_size for d in dosyalar)
    # Demo verisi mi, kullanıcının kendi dosyaları mı?
    demo = sum(1 for d in dosyalar
               if re.match(r"^(TR01|TR02|DE01|UK01)_", d.name)) >= 4
    return {
        "dosya": len(dosyalar),
        "boyut_mb": round(toplam / 1e6, 2),
        "demo_mu": demo,
        "liste": [{"ad": d.name, "kb": round(d.stat().st_size / 1024),
                   "zaman": datetime.fromtimestamp(d.stat().st_mtime)
                   .strftime("%d.%m %H:%M")}
                  for d in dosyalar[:120]],
    }


def cikti_durumu() -> list[dict]:
    sonuc = []
    for ad, baslik, tur in CIKTI_DOSYALARI:
        y = CIKTI / ad
        if y.exists():
            st = y.stat()
            sonuc.append({"ad": ad, "baslik": baslik, "tur": tur, "var": True,
                          "kb": round(st.st_size / 1024),
                          "zaman": datetime.fromtimestamp(st.st_mtime)
                          .strftime("%d.%m.%Y %H:%M")})
        else:
            sonuc.append({"ad": ad, "baslik": baslik, "tur": tur, "var": False})
    return sonuc


def bulgu_ozeti() -> dict | None:
    y = CIKTI / "bulgular.csv"
    if not y.exists():
        return None
    try:
        import pandas as pd
        b = pd.read_csv(y, encoding="utf-8-sig")
        s = b["onem"].value_counts().to_dict()
        return {"toplam": len(b), "kritik": int(s.get("kritik", 0)),
                "yuksek": int(s.get("yuksek", 0)), "orta": int(s.get("orta", 0)),
                "dusuk": int(s.get("dusuk", 0))}
    except Exception:
        return None


def yapilandirma_ozeti() -> dict:
    try:
        from sema import yukle
        y = yukle()
        return {"gecerli": True, "ozet": y.ozet(),
                "sirket": [{"kod": k, "ad": s.ad, "pb": s.fonksiyonel_para_birimi,
                            "plan": s.hesap_plani}
                           for k, s in y.sirketler.items()],
                "sunum_pb": y.sunum_para_birimi,
                "donem": [y.donemler()[0], y.donemler()[-1]]}
    except Exception as e:
        return {"gecerli": False, "hata": str(e)[:400]}


def tam_durum() -> dict:
    return {
        "proje": "MizanKöprü",
        "kok": str(KOK),
        "anahtar": anahtar_durumu(),
        "girdi": girdi_durumu(),
        "ciktilar": cikti_durumu(),
        "bulgu": bulgu_ozeti(),
        "yapilandirma": yapilandirma_ozeti(),
        "adimlar": [{"ad": a, "baslik": b, "aciklama": c, "betik": s}
                    for a, s, b, c in ADIMLAR],
        "gecmis": CALISTIRICI.gecmis,
        "calisiyor": CALISTIRICI.aktif,
    }


# ======================================================================
# HTTP
# ======================================================================

class Sunucu(BaseHTTPRequestHandler):
    server_version = "MizanKopruPanel"

    def log_message(self, bicim, *args):
        pass                                   # konsolu kirletme

    # --- yardımcılar ---
    def _json(self, nesne, kod=200):
        govde = json.dumps(nesne, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(govde)

    def _govde(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def _dosya(self, yol: Path, indir=False):
        if not yol.exists() or not yol.is_file():
            self._json({"hata": "dosya yok"}, 404)
            return
        tur = mimetypes.guess_type(yol.name)[0] or "application/octet-stream"
        if yol.suffix.lower() in (".csv", ".md", ".json", ".html"):
            tur += "; charset=utf-8"
        veri = yol.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(veri)))
        if indir:
            self.send_header("Content-Disposition",
                             f'attachment; filename="{yol.name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(veri)

    # --- GET ---
    def do_GET(self):
        p = urlparse(self.path)
        yol = unquote(p.path)

        if yol in ("/", "/index.html"):
            if not SABLON.exists():
                self._json({"hata": f"şablon yok: {SABLON}"}, 500)
                return
            govde = SABLON.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(govde)))
            self.end_headers()
            self.wfile.write(govde)
            return

        if yol == "/api/durum":
            self._json(tam_durum())
            return

        if yol == "/api/akis":
            self._akis()
            return

        if yol.startswith("/cikti/"):
            ad = os.path.basename(yol[len("/cikti/"):])
            indir = "indir=1" in (p.query or "")
            self._dosya(CIKTI / ad, indir=indir)
            return

        if yol.startswith("/gunluk/"):
            ad = os.path.basename(yol[len("/gunluk/"):])
            self._dosya(GUNLUK / ad)
            return

        self._json({"hata": "bulunamadı"}, 404)

    def _akis(self):
        """Sunucu-gönderimli olaylar (SSE) — canlı log akışı."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        k = CALISTIRICI.abone_ol()
        try:
            self.wfile.write(b": baglandi\n\n")
            self.wfile.flush()
            while True:
                try:
                    olay = k.get(timeout=15)
                    paket = json.dumps(olay, ensure_ascii=False, default=str)
                    self.wfile.write(f"data: {paket}\n\n".encode("utf-8"))
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")     # bağlantıyı canlı tut
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            CALISTIRICI.abonelikten_cik(k)

    # --- POST ---
    def do_POST(self):
        yol = unquote(urlparse(self.path).path)

        if yol == "/api/calistir":
            g = self._govde()
            adimlar = g.get("adimlar") or ([g["adim"]] if g.get("adim") else [])
            if not adimlar:
                self._json({"tamam": False, "mesaj": "adım belirtilmedi"}, 400)
                return
            tamam, mesaj = CALISTIRICI.calistir(adimlar)
            self._json({"tamam": tamam, "mesaj": mesaj}, 200 if tamam else 409)
            return

        if yol == "/api/durdur":
            self._json({"tamam": CALISTIRICI.durdur()})
            return

        if yol == "/api/yukle":
            self._yukle()
            return

        if yol == "/api/girdi-temizle":
            silinen = 0
            if GIRDI.exists():
                for d in GIRDI.iterdir():
                    if d.is_file() and d.suffix.lower() in IZINLI_UZANTI:
                        d.unlink()
                        silinen += 1
            CALISTIRICI.yayinla(
                "satir", metin=f"⌫ Girdi dizini temizlendi — {silinen} dosya silindi.",
                seviye="uyari")
            self._json({"tamam": True, "silinen": silinen})
            return

        if yol == "/api/girdi-sil":
            ad = guvenli_ad(self._govde().get("ad", ""))
            if not ad:
                self._json({"tamam": False, "mesaj": "geçersiz ad"}, 400)
                return
            hedef = GIRDI / ad
            if hedef.exists():
                hedef.unlink()
            self._json({"tamam": True})
            return

        self._json({"hata": "bulunamadı"}, 404)

    def _yukle(self):
        """Sürükle-bırak yükleme. Dosyalar base64 olarak JSON gövdede gelir —
        multipart ayrıştırıcıya (Python 3.13'te kaldırılan cgi modülü) gerek
        kalmaz ve bağımlılık eklenmez."""
        g = self._govde()
        dosyalar = g.get("dosyalar") or []
        GIRDI.mkdir(parents=True, exist_ok=True)
        yazilan, atlanan = [], []
        for d in dosyalar:
            ad = guvenli_ad(str(d.get("ad", "")))
            if not ad:
                atlanan.append({"ad": d.get("ad", "?"),
                                "neden": "yalnızca .xlsx, .xls ve .csv kabul edilir"})
                continue
            try:
                ham = base64.b64decode(d.get("veri", ""), validate=True)
            except Exception:
                atlanan.append({"ad": ad, "neden": "içerik çözülemedi"})
                continue
            if len(ham) > AZAMI_DOSYA_MB * 1_000_000:
                atlanan.append({"ad": ad,
                                "neden": f"{AZAMI_DOSYA_MB} MB sınırı aşıldı"})
                continue
            hedef = (GIRDI / ad).resolve()
            if GIRDI.resolve() not in hedef.parents:
                atlanan.append({"ad": ad, "neden": "hedef dizin dışı"})
                continue
            hedef.write_bytes(ham)
            yazilan.append({"ad": ad, "kb": round(len(ham) / 1024)})

        if yazilan:
            CALISTIRICI.yayinla(
                "satir",
                metin=f"⇪ {len(yazilan)} dosya yüklendi: "
                      + ", ".join(x["ad"] for x in yazilan[:6])
                      + (" …" if len(yazilan) > 6 else ""),
                seviye="iyi")
        for a in atlanan:
            CALISTIRICI.yayinla("satir",
                                metin=f"⨯ {a['ad']} atlandı — {a['neden']}",
                                seviye="uyari")
        self._json({"tamam": True, "yazilan": yazilan, "atlanan": atlanan})


# ======================================================================
def main():
    ap = argparse.ArgumentParser(description="MizanKöprü paneli")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--tarayici-acma", action="store_true")
    a = ap.parse_args()

    for d in (GIRDI, CIKTI, GUNLUK):
        d.mkdir(parents=True, exist_ok=True)

    try:
        sunucu = ThreadingHTTPServer(("127.0.0.1", a.port), Sunucu)
    except OSError as e:
        print(f"\n  Port {a.port} kullanılamıyor: {e}")
        print(f"  Başka bir port deneyin:  py src/panel.py --port {a.port + 1}\n")
        return 1

    adres = f"http://127.0.0.1:{a.port}/"
    print()
    print("  ┌────────────────────────────────────────────────┐")
    print("  │  MİZANKÖPRÜ PANELİ                             │")
    print("  ├────────────────────────────────────────────────┤")
    print(f"  │  {adres:<44}  │")
    print("  │                                                │")
    print("  │  Kapatmak için bu pencerede Ctrl+C             │")
    print("  └────────────────────────────────────────────────┘")
    print()
    d = girdi_durumu()
    print(f"  Girdi   : {d['dosya']} dosya, {d['boyut_mb']} MB"
          + ("  (demo verisi)" if d["demo_mu"] else
             "  (kendi verileriniz)" if d["dosya"] else "  — boş"))
    ak = anahtar_durumu()
    print(f"  Zeka    : {'açık · ' + str(ak['model']) if ak['var'] else 'kapalı'}")
    yp = yapilandirma_ozeti()
    print(f"  Ayarlar : {yp['ozet'] if yp['gecerli'] else 'HATA — ' + yp.get('hata','')}")
    print()

    if not a.tarayici_acma:
        threading.Timer(0.6, lambda: webbrowser.open(adres)).start()
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\n  Panel kapatıldı.\n")
        CALISTIRICI.durdur()
        sunucu.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
