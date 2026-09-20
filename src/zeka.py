# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ. Yapay zekâ katmanı (Claude API).

ÇEKİRDEK İLKE
  LLM hiçbir sayıyı üretmez, hesaplamaz, tahmin etmez.
  Motor sayıyı üretir; LLM yalnızca hazır sayıyı finans diline çevirir,
  önceliklendirir ya da bir eşleme önerir. Bu ayrım pazarlama cümlesi değil,
  mimari bir kısıttır: regüle bir süreçte rakamın kaynağı denetlenebilir olmalıdır.

  Bu yüzden her istem (prompt) LLM'e sayıları HAZIR verir ve
  "hesaplama yapma" talimatını taşır. Yorum katmanı kapatılsa bile
  boru hattının ürettiği tüm rakamlar aynı kalır.

DENETİM İZİ
  Her çağrı gunluk/denetim_izi.jsonl'a yazılır: hangi görev, hangi model,
  istemin parmak izi, token sayısı, tahmini maliyet, yanıtın parmak izi.
  "Bu yorumu kim yazdı" sorusunun cevabı dosyada durur.

ANAHTAR
  Kod içinde API anahtarı YOKTUR. Sırasıyla aranır:
    1) ANTHROPIC_API_KEY ortam değişkeni
    2) proje kökündeki .env dosyası
  Anahtar yoksa katman sessizce devre dışı kalır; boru hattı çalışmaya devam eder.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import yaml

KOK = Path(__file__).resolve().parent.parent
ONBELLEK_DIZIN = KOK / "gunluk" / "zeka_onbellek"
ONBELLEK_DIZIN.mkdir(parents=True, exist_ok=True)

# 1M token başına USD, yapilandirma/zeka.yaml'dan geçersiz kılınabilir
VARSAYILAN_FIYAT = {"claude-opus-5": (5.0, 25.0),
                    "claude-sonnet-5": (2.0, 10.0),
                    "claude-haiku-4-5": (1.0, 5.0)}

ORTAK_TALIMAT = (
    "Sen bir grup şirketinin finansal kontrol ve FP&A ekibine yardım eden "
    "kıdemli bir finans uzmanısın. Türkçe yazarsın.\n\n"
    "MUTLAK KURALLAR:\n"
    "1. Sana verilen sayıların DIŞINDA hiçbir sayı üretme, hesaplama yapma, "
    "tahmin etme veya yuvarlama. Bir sayıya ihtiyaç duyup elinde yoksa "
    "'veri yok' de.\n"
    "2. Verilen sayıları yeniden hesaplayıp doğrulamaya çalışma; onlar "
    "denetlenmiş bir motordan geliyor.\n"
    "3. Emin olmadığın bir nedensellik kurma. 'Muhtemelen', 'olabilir' gibi "
    "ifadelerle belirsizliği açıkça işaretle.\n"
    "4. Kısa yaz. Süsleme, giriş cümlesi, özetin özeti yok."
)


def _env_oku(yol: Path) -> dict:
    """Bağımlılık eklemeden basit .env okuyucu."""
    degerler = {}
    if not yol.exists():
        return degerler
    for satir in yol.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#") or "=" not in satir:
            continue
        ad, _, deger = satir.partition("=")
        degerler[ad.strip()] = deger.strip().strip('"').strip("'")
    return degerler


class Zeka:
    """Claude API sarmalayıcısı. Anahtar yoksa aktif=False olur ve
    her çağrı None döner, çağıran taraf buna göre davranır."""

    def __init__(self, y=None, g=None):
        self.y = y
        self.g = g
        self.ayar = self._ayar_yukle()
        self.model = self.ayar.get("model", "claude-opus-5")
        self.onbellek_aktif = self.ayar.get("onbellek", True)
        self.istatistik = {"cagri": 0, "onbellek": 0, "girdi_token": 0,
                           "cikti_token": 0, "maliyet_usd": 0.0}

        anahtar = os.environ.get("ANTHROPIC_API_KEY") or \
            _env_oku(KOK / ".env").get("ANTHROPIC_API_KEY")

        self.aktif = False
        self.istemci = None
        self.neden = ""
        if not anahtar:
            self.neden = "ANTHROPIC_API_KEY bulunamadı (.env veya ortam değişkeni)"
            return
        try:
            import anthropic
            self.istemci = anthropic.Anthropic(api_key=anahtar, timeout=120.0)
            self.aktif = True
        except ImportError:
            self.neden = "anthropic paketi kurulu değil (pip install anthropic)"
        except Exception as e:
            self.neden = f"İstemci kurulamadı: {e}"

    # ---------------------------------------------------------------
    def _ayar_yukle(self) -> dict:
        yol = KOK / "yapilandirma" / "zeka.yaml"
        if yol.exists():
            with open(yol, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _maliyet(self, girdi: int, cikti: int) -> float:
        fiyat = self.ayar.get("fiyat", {}).get(self.model)
        if fiyat:
            gf, cf = fiyat["girdi"], fiyat["cikti"]
        else:
            gf, cf = VARSAYILAN_FIYAT.get(self.model, (5.0, 25.0))
        return girdi / 1e6 * gf + cikti / 1e6 * cf

    def _onbellek_yol(self, anahtar: str) -> Path:
        return ONBELLEK_DIZIN / f"{anahtar}.json"

    # ---------------------------------------------------------------
    def cagir(self, gorev: str, istem: str, sema: dict | None = None,
              azami_token: int = 4000) -> dict | str | None:
        """Tek çağrı. sema verilirse doğrulanmış sözlük, yoksa metin döner.
        Anahtar yoksa ya da çağrı başarısızsa None döner, çağıran taraf
        yorum katmanı olmadan devam edebilmeli."""
        if not self.aktif:
            return None

        imza = hashlib.sha256(
            f"{self.model}|{gorev}|{istem}|{json.dumps(sema, sort_keys=True)}"
            .encode("utf-8")).hexdigest()[:20]

        if self.onbellek_aktif:
            yol = self._onbellek_yol(imza)
            if yol.exists():
                self.istatistik["onbellek"] += 1
                if self.g:
                    self.g.iz("zeka_onbellek", gorev=gorev, imza=imza)
                return json.loads(yol.read_text(encoding="utf-8"))["yanit"]

        try:
            istek = dict(
                model=self.model,
                max_tokens=azami_token,
                system=ORTAK_TALIMAT,
                thinking={"type": "adaptive"},
                messages=[{"role": "user", "content": istem}],
            )
            if sema:
                istek["output_config"] = {"format": {"type": "json_schema",
                                                     "schema": sema}}
            yanit = self.istemci.messages.create(**istek)
        except Exception as e:
            if self.g:
                self.g.uyari(f"Zeka çağrısı başarısız ({gorev}): {type(e).__name__}: {e}")
                self.g.iz("zeka_hata", gorev=gorev, hata=str(e)[:400])
            return None

        metin = "".join(b.text for b in yanit.content if b.type == "text")
        sonuc: dict | str
        if sema:
            try:
                sonuc = json.loads(metin)
            except json.JSONDecodeError:
                if self.g:
                    self.g.uyari(f"Zeka yanıtı JSON değil ({gorev})")
                return None
        else:
            sonuc = metin.strip()

        gt, ct = yanit.usage.input_tokens, yanit.usage.output_tokens
        maliyet = self._maliyet(gt, ct)
        self.istatistik["cagri"] += 1
        self.istatistik["girdi_token"] += gt
        self.istatistik["cikti_token"] += ct
        self.istatistik["maliyet_usd"] += maliyet

        if self.g:
            self.g.iz("zeka_cagri", gorev=gorev, model=self.model, imza=imza,
                      girdi_token=gt, cikti_token=ct, maliyet_usd=round(maliyet, 5),
                      istem_parmak=hashlib.sha256(istem.encode()).hexdigest()[:16],
                      yanit_parmak=hashlib.sha256(metin.encode()).hexdigest()[:16],
                      yanit_uzunluk=len(metin))

        if self.onbellek_aktif:
            self._onbellek_yol(imza).write_text(
                json.dumps({"gorev": gorev, "model": self.model,
                            "istem": istem, "yanit": sonuc},
                           ensure_ascii=False, indent=2),
                encoding="utf-8")
        return sonuc

    # =================================================================
    # GÖREVLER
    # =================================================================

    ESLEME_SEMASI = {
        "type": "object",
        "properties": {
            "oneriler": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "yerel_kod": {"type": "string"},
                        "onerilen_grup_kod": {"type": "string"},
                        "guven": {"type": "string", "enum": ["yuksek", "orta", "dusuk"]},
                        "gerekce": {"type": "string"},
                    },
                    "required": ["yerel_kod", "onerilen_grup_kod", "guven", "gerekce"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["oneriler"],
        "additionalProperties": False,
    }

    def esleme_oner(self, eslesmeyenler: list[dict], grup_plani: list[dict]) -> list[dict]:
        """Eşleşmeyen yerel hesaplar için grup hesabı önerir (K09 bulgusuna çözüm).

        Bu, LLM'in en güvenli ve en faydalı kullanımı: sayı değil, AD eşleştiriyor.
        Öneri doğrudan uygulanmaz, hesap_eslesme_onerisi.csv'ye yazılır,
        insan onaylayıp yapılandırmaya alır."""
        if not eslesmeyenler:
            return []
        plan_metni = "\n".join(
            f"  {h['kod']}  {h['ad']}  ({'Bilanço' if h['tur']=='B' else 'Gelir tablosu'}, {h['kalem']})"
            for h in grup_plani)
        hesap_metni = "\n".join(
            f"  şirket={e['sirket_kod']} plan={e['hesap_plani']} "
            f"kod={e['yerel_hesap_kod']} ad=\"{e['yerel_hesap_ad']}\" "
            f"bakiye_yonu={'borç' if e.get('bakiye',0)>=0 else 'alacak'}"
            for e in eslesmeyenler)
        istem = (
            "Aşağıdaki yerel hesaplar grup hesap planı eşleme tablosunda bulunamadı. "
            "Her biri için en uygun grup hesabını öner.\n\n"
            f"GRUP HESAP PLANI:\n{plan_metni}\n\n"
            f"EŞLEŞMEYEN YEREL HESAPLAR:\n{hesap_metni}\n\n"
            "Hesap adının dili farklı olabilir (Türkçe/Almanca/İngilizce). "
            "Bakiye yönü ipucu verir: gider hesapları borç, gelir hesapları alacak bakiye verir. "
            "Emin olamadığın yerde guven='dusuk' yaz ve gerekçede neyin belirsiz olduğunu söyle. "
            "Gerekçe tek cümle olsun."
        )
        sonuc = self.cagir("esleme_oner", istem, sema=self.ESLEME_SEMASI)
        return sonuc["oneriler"] if sonuc else []

    TRIYAJ_SEMASI = {
        "type": "object",
        "properties": {
            "siralama": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "bulgu_no": {"type": "integer"},
                        "aciliyet": {"type": "string",
                                     "enum": ["hemen", "kapanis_oncesi", "takip"]},
                        "neden": {"type": "string"},
                        "atilacak_adim": {"type": "string"},
                    },
                    "required": ["bulgu_no", "aciliyet", "neden", "atilacak_adim"],
                    "additionalProperties": False,
                },
            },
            "genel_degerlendirme": {"type": "string"},
        },
        "required": ["siralama", "genel_degerlendirme"],
        "additionalProperties": False,
    }

    def bulgu_triyaj(self, bulgular: list[dict]) -> dict | None:
        """Kontrol bulgularını aciliyet sırasına koyar ve her biri için
        somut bir adım önerir. Bulgunun kendisini değiştirmez."""
        if not bulgular:
            return None
        metin = "\n".join(
            f"  [{i}] {b['test_kod']} {b['test_ad']} · önem={b['onem']} · "
            f"{b['sirket_kod']} {b['donem']} · tutar={b.get('tutar_eur', 0):,.0f} EUR · "
            f"{b['aciklama']}"
            for i, b in enumerate(bulgular))
        istem = (
            "Ay sonu kapanışında aşağıdaki iç kontrol bulguları çıktı. "
            "Kapanışı imzalayacak kontrolörün hangi sırayla ilgilenmesi gerektiğini belirle.\n\n"
            f"BULGULAR:\n{metin}\n\n"
            "Aciliyet tanımları: 'hemen' = kapanış rakamını değiştirir ya da suistimal "
            "şüphesi taşır; 'kapanis_oncesi' = imzadan önce açıklığa kavuşmalı; "
            "'takip' = süreç iyileştirmesi, bu ayın rakamını bozmaz.\n"
            "Her bulgu için 'atilacak_adim' somut ve tek cümle olsun "
            "(kime ne sorulacak, hangi belge istenecek gibi). "
            "'genel_degerlendirme' en fazla 3 cümle: bu ayki kontrol ortamının durumu."
        )
        return self.cagir("bulgu_triyaj", istem, sema=self.TRIYAJ_SEMASI, azami_token=8000)

    def sapma_yorumla(self, ozet: str) -> str | None:
        """Motorun ürettiği sapma köprüsünü CFO diline çevirir.
        `ozet` içinde tüm sayılar hazır; LLM sadece anlatır."""
        istem = (
            "Aşağıda bütçe-fiili sapmasının bileşenlerine ayrıştırılmış hâli var. "
            "Ayrıştırmayı motor yaptı; sen sadece yorumla.\n\n"
            f"{ozet}\n\n"
            "Yaz:\n"
            "1. Tek cümlelik başlık bulgu, bir yöneticinin aklında kalacak cümle.\n"
            "2. En fazla 4 madde: her biri bir sapma bileşenini açıklasın, "
            "bileşenin adını ve verilen sayıyı kullansın.\n"
            "3. 'Dikkat' başlığı altında en fazla 2 madde: bu tablodan yanlış "
            "okunabilecek şey ne, hangi sonuca atlanmamalı.\n"
            "Toplam 200 kelimeyi geçme. Verilen sayıların dışına çıkma."
        )
        return self.cagir("sapma_yorumla", istem, azami_token=3000)

    def yonetici_ozeti(self, paket: str) -> str | None:
        """Kapanış paketinin yönetici özeti."""
        istem = (
            "Aşağıda bir grup şirketinin ay sonu konsolidasyon paketinin "
            "sayısal özeti var. CFO'ya sunulacak kapanış notunu yaz.\n\n"
            f"{paket}\n\n"
            "Yapı:\n"
            "- 'Sonuç', 2 cümle: dönemin özeti.\n"
            "- 'Rakamlar ne diyor', en fazla 4 madde.\n"
            "- 'Kontrol ortamı', en fazla 3 madde, bulgulardan.\n"
            "- 'Karar bekleyen', en fazla 3 madde, yönetimin karar vermesi gerekenler.\n"
            "300 kelimeyi geçme. Verilen sayıların dışına çıkma, yeni sayı üretme."
        )
        return self.cagir("yonetici_ozeti", istem, azami_token=4000)

    # ---------------------------------------------------------------
    def ozet(self) -> str:
        if not self.aktif:
            return f"Zeka katmanı KAPALI, {self.neden}"
        i = self.istatistik
        return (f"Zeka katmanı açık ({self.model}) · {i['cagri']} çağrı, "
                f"{i['onbellek']} önbellek · "
                f"{i['girdi_token']:,}→{i['cikti_token']:,} token · "
                f"~${i['maliyet_usd']:.4f}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from gunluk import Gunluk

    g = Gunluk("zeka")
    z = Zeka(g=g)
    g.bilgi(z.ozet())
    if z.aktif:
        yanit = z.cagir("baglanti_sinamasi",
                        "Sadece şu kelimeyi yaz, başka hiçbir şey yazma: BAGLANTI_TAMAM",
                        azami_token=2000)
        if yanit and "BAGLANTI_TAMAM" in yanit:
            g.iyi(f"API bağlantısı çalışıyor. Yanıt: {yanit}")
        else:
            g.uyari(f"Beklenmeyen yanıt: {yanit!r}")
        g.bilgi(z.ozet())
    else:
        g.uyari("Anahtar yok, .env dosyasına ANTHROPIC_API_KEY=... satırını ekle.")
        g.bilgi("Motor bu katman olmadan da tam çalışır; sadece yorum metinleri üretilmez.")
    g.bitir(z.istatistik)
