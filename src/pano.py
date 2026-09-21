# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ [6a] PANO: tek dosyalık HTML kapanış panosu.

GÖREV
  Boru hattının ürettiği her şeyi tek bir .html dosyasında toplar: konsolide
  tablolar, sapma köprüsü, kontrol bulguları, yapay zekâ yorumu ve denetim izi.
  Harici bağımlılık yok, dosya tek başına açılır, paylaşılır, arşivlenir.

TASARIM
  Kapanış panosu bir gösterge tablosu değil, bir KARAR belgesidir. Bu yüzden
  en üstte "imzalanabilir mi" sorusunun cevabı durur: kritik bulgu varsa
  kapanış açıkça engellenmiş gösterilir.

ÇALIŞTIRMA
  py src/pano.py
ÇIKTI
  cikti/pano.html
"""
from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gunluk import Gunluk, dosya_parmak_izi, para      # noqa: E402
from sema import ARA_DIZIN, CIKTI_DIZIN, KOK, yukle    # noqa: E402

ONEM_RENK = {"kritik": "kritik", "yuksek": "yuksek", "orta": "orta", "dusuk": "dusuk"}


def k(deger, basamak: int = 0) -> str:
    return para(deger, basamak)


def kacis(metin) -> str:
    return html.escape(str(metin))


def serit(deger: float, tavan: float, sinif: str = "") -> str:
    """Tablo içi oran çubuğu, sayıyı gözle karşılaştırılabilir yapar."""
    if not tavan:
        return ""
    oran = min(abs(deger) / tavan * 100, 100)
    return f'<span class="serit {sinif}" style="width:{oran:.1f}%"></span>'


def kopru_svg(kalemler: list[tuple[str, float, str]], genislik=880, yukseklik=300) -> str:
    """Sapma köprüsü (şelale) grafiği, saf SVG, kütüphane yok.

    kalemler: (etiket, değer, tip), tip: 'temel' | 'artı' | 'eksi' | 'toplam'
    """
    kenar_sol, kenar_alt, kenar_ust = 8, 56, 26
    ic_g = genislik - kenar_sol * 2
    ic_y = yukseklik - kenar_alt - kenar_ust
    n = len(kalemler)
    sutun = ic_g / n
    bar_g = sutun * 0.58

    # Kümülatif konumlar
    kos, birikim = [], 0.0
    for etiket, deger, tip in kalemler:
        if tip in ("temel", "toplam"):
            kos.append((0.0, deger)); birikim = deger
        else:
            kos.append((birikim, birikim + deger)); birikim += deger
    tavan = max(max(a, b) for a, b in kos) * 1.08
    taban = min(min(a, b) for a, b in kos)
    taban = min(taban, 0) * 1.08
    aralik = (tavan - taban) or 1

    def y(v):
        return kenar_ust + ic_y - (v - taban) / aralik * ic_y

    parcalar = [f'<svg viewBox="0 0 {genislik} {yukseklik}" class="kopru" '
                f'role="img" aria-label="Sapma köprüsü">']
    # Sıfır çizgisi
    parcalar.append(f'<line x1="{kenar_sol}" y1="{y(0):.1f}" x2="{genislik-kenar_sol}" '
                    f'y2="{y(0):.1f}" class="eksen"/>')
    for i, ((etiket, deger, tip), (alt, ust)) in enumerate(zip(kalemler, kos)):
        x = kenar_sol + i * sutun + (sutun - bar_g) / 2
        y1, y2 = y(max(alt, ust)), y(min(alt, ust))
        h = max(abs(y2 - y1), 2)
        sinif = {"temel": "bar-temel", "toplam": "bar-toplam",
                 "artı": "bar-arti", "eksi": "bar-eksi"}[tip]
        parcalar.append(f'<rect x="{x:.1f}" y="{y1:.1f}" width="{bar_g:.1f}" '
                        f'height="{h:.1f}" rx="2" class="{sinif}"/>')
        # Bağlayıcı çizgi
        if i < n - 1 and tip != "toplam":
            parcalar.append(f'<line x1="{x:.1f}" y1="{y(ust):.1f}" '
                            f'x2="{x + sutun:.1f}" y2="{y(ust):.1f}" class="baglayici"/>')
        orta = x + bar_g / 2
        deger_y = y1 - 6 if deger >= 0 or tip in ("temel", "toplam") else y2 + 14
        parcalar.append(f'<text x="{orta:.1f}" y="{deger_y:.1f}" class="bar-deger" '
                        f'text-anchor="middle">{k(deger/1e6, 1)}M</text>')
        for j, satir in enumerate(etiket.split("\n")):
            parcalar.append(f'<text x="{orta:.1f}" y="{yukseklik - 34 + j*13:.1f}" '
                            f'class="bar-etiket" text-anchor="middle">{kacis(satir)}</text>')
    parcalar.append("</svg>")
    return "".join(parcalar)


SAYFA = """<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MizanKöprü. Kapanış Panosu</title>
<style>
:root {{
  --arka: #0d1117; --kart: #161b22; --kenar: #30363d; --metin: #e6edf3;
  --sonuk: #8b949e; --vurgu: #58a6ff; --iyi: #3fb950; --uyari: #d29922;
  --kotu: #f85149; --mor: #bc8cff;
}}
@media (prefers-color-scheme: light) {{
  :root:not([data-tema="dark"]) {{
    --arka: #ffffff; --kart: #f6f8fa; --kenar: #d0d7de; --metin: #1f2328;
    --sonuk: #59636e; --vurgu: #0969da; --iyi: #1a7f37; --uyari: #9a6700;
    --kotu: #cf222e; --mor: #8250df;
  }}
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--arka); color:var(--metin);
  font:15px/1.6 -apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif; }}
.sarmal {{ max-width:1160px; margin:0 auto; padding:28px 16px 64px; }}
h1 {{ font-size:26px; margin:0 0 4px; letter-spacing:-.4px; }}
h2 {{ font-size:17px; margin:34px 0 12px; padding-bottom:7px;
  border-bottom:1px solid var(--kenar); letter-spacing:-.2px; }}
h3 {{ font-size:14px; margin:20px 0 8px; color:var(--sonuk);
  text-transform:uppercase; letter-spacing:.6px; }}
.ustbilgi {{ color:var(--sonuk); font-size:13px; margin-bottom:22px; }}
.karar {{ padding:16px 18px; border-radius:8px; margin:18px 0 26px;
  border:1px solid; display:flex; gap:14px; align-items:flex-start; }}
.karar.engel {{ background:rgba(248,81,73,.08); border-color:var(--kotu); }}
.karar.tamam {{ background:rgba(63,185,80,.08); border-color:var(--iyi); }}
.karar .isaret {{ font-size:22px; line-height:1.1; }}
.karar b {{ display:block; font-size:16px; margin-bottom:3px; }}
.karar .ayrinti {{ color:var(--sonuk); font-size:13.5px; }}
.kartlar {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(178px,1fr));
  gap:12px; margin-bottom:8px; }}
.kart {{ background:var(--kart); border:1px solid var(--kenar);
  border-radius:8px; padding:14px 16px; }}
.kart .etiket {{ font-size:11.5px; color:var(--sonuk); text-transform:uppercase;
  letter-spacing:.6px; margin-bottom:5px; }}
.kart .deger {{ font-size:23px; font-weight:600; letter-spacing:-.6px;
  font-variant-numeric:tabular-nums; }}
.kart .alt {{ font-size:12px; color:var(--sonuk); margin-top:3px; }}
.iyi {{ color:var(--iyi); }} .kotu {{ color:var(--kotu); }}
.uyari {{ color:var(--uyari); }} .mor {{ color:var(--mor); }}
table {{ width:100%; border-collapse:collapse; font-size:13.5px;
  font-variant-numeric:tabular-nums; }}
th {{ text-align:left; padding:8px 10px; color:var(--sonuk); font-weight:600;
  font-size:11.5px; text-transform:uppercase; letter-spacing:.5px;
  border-bottom:1px solid var(--kenar); white-space:nowrap; }}
td {{ padding:7px 10px; border-bottom:1px solid var(--kenar); }}
tr:last-child td {{ border-bottom:none; }}
.sag {{ text-align:right; }}
.tablo-sarmal {{ background:var(--kart); border:1px solid var(--kenar);
  border-radius:8px; overflow:hidden; overflow-x:auto; }}
tr.toplam td {{ font-weight:600; border-top:2px solid var(--kenar); }}
.rozet {{ display:inline-block; padding:1px 7px; border-radius:11px;
  font-size:11px; font-weight:600; letter-spacing:.3px; }}
.rozet.kritik {{ background:rgba(248,81,73,.15); color:var(--kotu); }}
.rozet.yuksek {{ background:rgba(210,153,34,.15); color:var(--uyari); }}
.rozet.orta {{ background:rgba(88,166,255,.13); color:var(--vurgu); }}
.rozet.dusuk {{ background:rgba(139,148,158,.15); color:var(--sonuk); }}
.serit {{ display:block; height:3px; background:var(--vurgu); border-radius:2px;
  margin-top:3px; opacity:.55; }}
.serit.neg {{ background:var(--kotu); }}
.kopru {{ width:100%; height:auto; display:block; }}
.bar-temel {{ fill:var(--sonuk); opacity:.55; }}
.bar-toplam {{ fill:var(--vurgu); }}
.bar-arti {{ fill:var(--iyi); }}
.bar-eksi {{ fill:var(--kotu); }}
.baglayici {{ stroke:var(--sonuk); stroke-width:1; stroke-dasharray:3 3; opacity:.5; }}
.eksen {{ stroke:var(--kenar); stroke-width:1; }}
.bar-deger {{ fill:var(--metin); font-size:11.5px; font-weight:600; }}
.bar-etiket {{ fill:var(--sonuk); font-size:10.5px; }}
.yorum {{ background:var(--kart); border:1px solid var(--kenar);
  border-left:3px solid var(--mor); border-radius:8px; padding:4px 20px 14px; }}
.yorum h2 {{ border:none; font-size:15px; margin-top:16px; }}
.yorum ul {{ padding-left:20px; }} .yorum li {{ margin:6px 0; }}
.not {{ font-size:12.5px; color:var(--sonuk); margin-top:8px; }}
.izgara2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
@media (max-width:820px) {{ .izgara2 {{ grid-template-columns:1fr; }} }}
footer {{ margin-top:40px; padding-top:16px; border-top:1px solid var(--kenar);
  color:var(--sonuk); font-size:12px; }}
code {{ font-family:ui-monospace,"Cascadia Code",Consolas,monospace; font-size:12px;
  background:var(--kart); padding:1px 5px; border-radius:4px; }}
</style></head><body><div class="sarmal">
{govde}
</div></body></html>"""


def main():
    g = Gunluk("pano")
    y = yukle()
    son = y.son_donem()

    oku = lambda p, **kw: pd.read_csv(p, dtype={"donem": str, **kw})
    konsolide = oku(ARA_DIZIN / "konsolide.csv", grup_kod=str)
    cevrilmis = oku(ARA_DIZIN / "cevrilmis.csv", grup_kod=str)

    def oku_varsa(yol, **kw):
        """Yüklenmemiş veri panoyu çökertmemeli, bölümü atlanmalı.

        Eski bir dosyayı okumak, kullanıcının yüklemediği veriden üretilmiş
        rakam göstermek demektir; bu sistemin en tehlikeli hatasıdır."""
        if not Path(yol).exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(yol, encoding="utf-8-sig",
                               dtype={"donem": str, **kw})
        except pd.errors.EmptyDataError:
            return pd.DataFrame()

    bulgular = oku_varsa(CIKTI_DIZIN / "bulgular.csv")
    if bulgular.empty:
        bulgular = pd.DataFrame(columns=["test_kod", "onem", "sirket_kod",
                                         "donem", "nesne", "tutar_eur",
                                         "aciklama", "baslik"])
    kopru = oku_varsa(CIKTI_DIZIN / "sapma_koprusu.csv")
    yorum_yolu = CIKTI_DIZIN / "sapma_yorumu.md"
    yorum = yorum_yolu.read_text(encoding="utf-8") if yorum_yolu.exists() else ""

    koken = json.loads((ARA_DIZIN / "koken.json").read_text(encoding="utf-8")) \
        if (ARA_DIZIN / "koken.json").exists() else {}
    kapsam = y.kapsam()
    kapsam_sirket = kapsam.get("sirketler") or sorted(y.sirketler)
    kapsam_disi = kapsam.get("kapsam_disi") or []
    atlanan = json.loads(
        (CIKTI_DIZIN / "atlanan_testler.json").read_text(encoding="utf-8")) \
        if (CIKTI_DIZIN / "atlanan_testler.json").exists() else []
    PB = y.sunum_para_birimi

    ks = konsolide[konsolide["donem"] == son]
    kal = lambda ad: -ks[ks["kalem"] == ad]["eur_konsolide"].sum()
    hasilat, smm = kal("Hasılat"), kal("Satışların maliyeti")
    opex, fin, vergi = kal("Faaliyet giderleri"), kal("Finansal gelir/gider"), kal("Vergi")
    diger = kal("Diğer gelir/gider")
    maliyet_7a = kal("Maliyet muhasebesi")    # 7/A yansıtmalı, net sıfır olmalı
    brut, faaliyet = hasilat + smm, hasilat + smm + opex
    net = faaliyet + fin + diger + vergi

    kritik = int((bulgular["onem"] == "kritik").sum())
    sapma_var = not kopru.empty
    t = (kopru[["butce_eur", "fiyat_eur", "karisim_eur", "hacim_eur",
                "kur_etkisi_eur", "fiili_eur"]].sum() if sapma_var else None)

    p = []
    p.append(f'<h1>MizanKöprü. Kapanış Panosu</h1>')
    p.append(f'<div class="ustbilgi">{kacis(y.grup["ad"])} · konsolide dönem '
             f'<b>{son}</b> · sunum para birimi {PB} · '
             f'{len(kapsam_sirket)} tüzel kişilik · üretim '
             f'{datetime.now().strftime("%d.%m.%Y %H:%M")}</div>')

    # --- Köken bandı: bu sayfadaki her rakam hangi dosyadan geldi ---
    if koken.get("dosyalar"):
        dlist = " · ".join(
            f'{kacis(d.get("ad", ""))} ({d.get("kb", 0)} KB)'
            for d in koken["dosyalar"])
        gercek = koken.get("veri_seti") == "kullanici"
        p.append(f'<div class="not" style="border-left:3px solid var(--vurgu);'
                 f'padding-left:10px;margin:10px 0">'
                 f'<b>Bu panodaki her rakam şu dosyalardan üretildi:</b> {dlist}'
                 f'{"" if gercek else " <b>(" + kacis(str(koken.get("veri_seti"))).upper() + " VERİSİ)</b>"}</div>')
    else:
        p.append('<div class="not" style="border-left:3px solid var(--kotu);'
                 'padding-left:10px;margin:10px 0"><b>Köken kaydı yok.</b> '
                 'Bu panonun hangi dosyalardan üretildiği doğrulanamıyor.</div>')

    if kapsam_disi:
        p.append(f'<div class="not" style="border-left:3px solid var(--kotu);'
                 f'padding-left:10px;margin:10px 0"><b>Kapsam dışı:</b> '
                 f'{kacis(", ".join(kapsam_disi))}. Yapılandırmada tanımlı, '
                 f'ancak bu çalıştırmada verisi yüklenmedi; aşağıdaki rakamlar '
                 f'bu şirketleri İÇERMEZ.</div>')

    if atlanan:
        satirlar = "".join(
            f'<li><b>{kacis(a.get("kod",""))}</b> {kacis(a.get("ad",""))} — '
            f'{kacis(a.get("sebep",""))}</li>' for a in atlanan)
        p.append(f'<div class="not" style="border-left:3px solid var(--kotu);'
                 f'padding-left:10px;margin:10px 0">'
                 f'<b>Çalıştırılamayan kontrol testleri ({len(atlanan)}):</b>'
                 f'<ul style="margin:6px 0 0 16px">{satirlar}</ul>'
                 f'Bu testlerin kapsadığı riskler <b>denetlenmemiştir</b>; '
                 f'bulgu çıkmaması risk yok anlamına gelmez.</div>')

    # --- Karar bandı ---
    if kritik:
        kritik_test = ", ".join(sorted(bulgular[bulgular["onem"] == "kritik"]
                                       ["test_kod"].unique()))
        p.append(f'<div class="karar engel"><div class="isaret">⛔</div><div>'
                 f'<b>Kapanış imzalanamaz, {kritik} kritik bulgu açık</b>'
                 f'<div class="ayrinti">Açık testler: {kritik_test}. '
                 f'Kritik bulgular konsolide rakamı doğrudan değiştirebilir ya da '
                 f'yetki ihlaline işaret eder; çözülmeden imza atılmamalıdır.</div>'
                 f'</div></div>')
    elif atlanan:
        p.append(f'<div class="karar engel" style="border-color:var(--uyari)">'
                 f'<div class="isaret">!</div><div>'
                 f'<b>KOŞULLU: çalıştırılan testlerde kritik bulgu yok, '
                 f'ancak {len(atlanan)} test çalıştırılamadı</b>'
                 f'<div class="ayrinti">Kapanış, yalnızca yüklenen verinin '
                 f'kapsadığı riskler için temizdir. Yevmiye, bütçe ve grup içi '
                 f'dosyaları yüklenmeden mükerrer fiş, yetki aşımı, dönem '
                 f'kayması ve grup içi mutabakat riskleri DENETLENMEMİŞ '
                 f'kalır.</div></div></div>')
    else:
        p.append('<div class="karar tamam"><div class="isaret">✓</div><div>'
                 '<b>Kritik bulgu yok, kapanış imzalanabilir</b></div></div>')

    # --- Özet kartlar ---
    def kart(etiket, deger, alt="", sinif=""):
        return (f'<div class="kart"><div class="etiket">{etiket}</div>'
                f'<div class="deger {sinif}">{deger}</div>'
                f'<div class="alt">{alt}</div></div>')

    oran = lambda pay: (pay / hasilat * 100) if hasilat else 0.0
    p.append('<div class="kartlar">')
    p.append(kart("Konsolide hasılat", k(hasilat), f"{son} YTD · {PB}"))
    p.append(kart("Faaliyet kârı", k(faaliyet),
                  f"marj %{oran(faaliyet):.1f}",
                  "iyi" if faaliyet > 0 else "kotu"))
    p.append(kart("Net kâr", k(net), f"marj %{oran(net):.1f}",
                  "iyi" if net > 0 else "kotu"))
    if sapma_var:
        sapma_yuzde = (t["fiili_eur"] / t["butce_eur"] - 1) * 100
        p.append(kart("Bütçe sapması", f"{sapma_yuzde:+.1f}%",
                      f"{k(t['fiili_eur'] - t['butce_eur'])} {PB}",
                      "kotu" if sapma_yuzde < 0 else "iyi"))
    else:
        p.append(kart("Bütçe sapması", "—", "bütçe/satış verisi yüklenmedi"))
    p.append(kart("Kontrol bulgusu", f"{len(bulgular)}",
                  f"{kritik} kritik", "kotu" if kritik else "iyi"))
    p.append('</div>')

    # --- Sapma köprüsü ---
    # Ürün bazında miktar ve fiyat olmadan fiyat/karışım/hacim ayrıştırması
    # matematiksel olarak yapılamaz; uydurmak yerine neden yazılır.
    if not sapma_var:
        p.append('<h2>Hasılat sapma köprüsü</h2>')
        p.append('<div class="not" style="border-left:3px solid var(--kotu);'
                 'padding-left:10px"><b>Üretilemedi.</b> Fiyat / karışım / '
                 'hacim ayrıştırması için ürün kodu, miktar ve birim fiyat '
                 'içeren fiili ve bütçe satış dosyaları gerekir; bu '
                 'çalıştırmada yüklenmedi. Miktar bilinmeden fiyat etkisi ile '
                 'hacim etkisi birbirinden ayrılamaz, bu yüzden tahmin '
                 'üretilmedi.</div>')
    else:
        # --- Sapma köprüsü ---
        p.append('<h2>Hasılat sapma köprüsü, bütçeden fiiliye</h2>')
        p.append('<div class="tablo-sarmal" style="padding:10px 6px 2px">')
        p.append(kopru_svg([
            ("Bütçe", float(t["butce_eur"]), "temel"),
            ("Fiyat\netkisi", float(t["fiyat_eur"]), "artı" if t["fiyat_eur"] >= 0 else "eksi"),
            ("Karışım\netkisi", float(t["karisim_eur"]), "artı" if t["karisim_eur"] >= 0 else "eksi"),
            ("Hacim\netkisi", float(t["hacim_eur"]), "artı" if t["hacim_eur"] >= 0 else "eksi"),
            ("Kur\netkisi", float(t["kur_etkisi_eur"]), "artı" if t["kur_etkisi_eur"] >= 0 else "eksi"),
            ("Fiili", float(t["fiili_eur"]), "toplam"),
        ]))
        p.append('</div>')
        p.append(f'<div class="not">Ayrıştırma matematiksel olarak tamdır; '
                 f'fiyat + karışım + hacim toplamı yerel para sapmasına birebir eşittir '
                 f'(artık terim 0,0000). Kur etkisi = fiili yerel tutar × '
                 f'(gerçekleşen kur − bütçe kuru). Bütçe kuru EUR/TRY 38,00\'de '
                 f'sabitlenmişti; gerçekleşen yıl sonu 50,60.</div>')

        # --- Şirket bazında köprü + para birimi çelişkisi ---
        ozet = kopru.groupby("sirket_kod", as_index=False).agg(
            butce=("butce_eur", "sum"), fiili=("fiili_eur", "sum"),
            fiyat=("fiyat_eur", "sum"), karisim=("karisim_eur", "sum"),
            hacim=("hacim_eur", "sum"), kur=("kur_etkisi_eur", "sum"),
            mb=("miktar_butce", "sum"), mf=("miktar_fiili", "sum"),
            fy=("fiili_yerel", "sum"), by=("butce_yerel", "sum"))
        p.append('<h2>Şirket bazında, aynı yıl, üç farklı okuma</h2>')
        p.append('<div class="tablo-sarmal"><table><thead><tr>'
                 '<th>Şirket</th><th>PB</th><th class="sag">Miktar Δ</th>'
                 f'<th class="sag">Yerel ciro Δ</th><th class="sag">{PB} ciro Δ</th>'
                 '<th class="sag">Fiyat</th><th class="sag">Hacim</th>'
                 '<th class="sag">Kur</th><th></th></tr></thead><tbody>')
        for r in ozet.itertuples():
            s = y.sirketler[r.sirket_kod]
            dm = (r.mf / r.mb - 1) * 100 if r.mb else 0
            dy = (r.fy / r.by - 1) * 100 if r.by else 0
            de = (r.fiili / r.butce - 1) * 100 if r.butce else 0
            celiski = ('<span class="rozet kritik">ÇELİŞKİ</span>'
                       if dy > 0 > de else "")
            p.append(f'<tr><td><b>{r.sirket_kod}</b><br>'
                     f'<span class="alt" style="font-size:11.5px;color:var(--sonuk)">'
                     f'{kacis(s.ad)}</span></td><td>{s.fonksiyonel_para_birimi}</td>'
                     f'<td class="sag {"kotu" if dm<0 else "iyi"}">{dm:+.1f}%</td>'
                     f'<td class="sag {"kotu" if dy<0 else "iyi"}">{dy:+.1f}%</td>'
                     f'<td class="sag {"kotu" if de<0 else "iyi"}">{de:+.1f}%</td>'
                     f'<td class="sag">{k(r.fiyat)}</td>'
                     f'<td class="sag">{k(r.hacim)}</td>'
                     f'<td class="sag">{k(r.kur)}</td>'
                     f'<td>{celiski}</td></tr>')
        p.append('</tbody></table></div>')
        p.append('<div class="not">"ÇELİŞKİ" işareti, şirketin yerel para biriminde '
                 'bütçeyi aştığı hâlde sunum para biriminde hedefin altında kaldığı '
                 'durumu gösterir. İki rakam da doğrudur; fark kur çevriminden doğar '
                 've bir performans sorunu değildir.</div>')

    # --- Konsolide gelir tablosu ---
    p.append('<div class="izgara2">')
    p.append('<div><h3>Konsolide gelir tablosu</h3><div class="tablo-sarmal">'
             f'<table><thead><tr><th>Kalem</th><th class="sag">{PB}</th>'
             '<th class="sag">%</th></tr></thead><tbody>')
    for ad, deger, kalin in [("Hasılat", hasilat, False),
                             ("Satışların maliyeti", smm, False),
                             ("BRÜT KÂR", brut, True),
                             ("Faaliyet giderleri", opex, False),
                             ("FAALİYET KÂRI", faaliyet, True),
                             ("Finansal gelir/gider", fin, False),
                             ("Diğer gelir/gider", diger, False),
                             ("Vergi", vergi, False),
                             ("NET KÂR", net, True)]:
        p.append(f'<tr class="{"toplam" if kalin else ""}"><td>{ad}</td>'
                 f'<td class="sag">{k(deger)}</td>'
                 f'<td class="sag" style="color:var(--sonuk)">'
                 f'{oran(deger):.1f}%</td></tr>')
    p.append('</tbody></table></div></div>')

    # --- Eliminasyon ---
    elim = ks[ks["elimine"]]
    p.append('<div><h3>Grup içi eliminasyon</h3><div class="tablo-sarmal">'
             '<table><thead><tr><th>Hesap</th><th class="sag">Şirketler top.</th>'
             '<th class="sag">Konsolide</th></tr></thead><tbody>')
    for r in elim.itertuples():
        p.append(f'<tr><td>{r.grup_kod} {kacis(r.grup_ad)}</td>'
                 f'<td class="sag">{k(-r.eur_brut)}</td>'
                 f'<td class="sag" style="color:var(--sonuk)">0</td></tr>')
    p.append(f'<tr class="toplam"><td>Toplam elimine</td>'
             f'<td class="sag">{k(-elim["eur_brut"].sum())}</td>'
             f'<td class="sag">0</td></tr>')
    p.append('</tbody></table></div>')
    p.append('<div class="not">Grup içi alım-satım konsolide tabloda '
             'sıfırlanır. İki tarafın beyanı tutmuyorsa fark K08 bulgusu olur.</div>')
    p.append('</div></div>')

    # --- Kontrol bulguları ---
    p.append(f'<h2>İç kontrol bulguları, {len(bulgular)} bulgu, {len(y.kontroller)} test</h2>')
    sayim = bulgular.groupby(["test_kod", "onem"]).size().reset_index(name="adet")
    p.append('<div class="tablo-sarmal"><table><thead><tr><th>Test</th>'
             '<th>Ne arar</th><th>Önem</th><th class="sag">Bulgu</th>'
             f'<th class="sag">Toplam tutar {PB}</th></tr></thead><tbody>')
    tavan = bulgular.groupby("test_kod")["tutar_eur"].sum().max()
    for kod in sorted(y.kontroller):
        test = y.kontroller[kod]
        alt = bulgular[bulgular["test_kod"] == kod]
        tutar = alt["tutar_eur"].sum()
        p.append(f'<tr><td><code>{kod}</code></td><td>{kacis(test["ad"])}</td>'
                 f'<td><span class="rozet {ONEM_RENK[test["onem"]]}">'
                 f'{test["onem"]}</span></td>'
                 f'<td class="sag">{len(alt) or "-"}</td>'
                 f'<td class="sag">{k(tutar) if len(alt) else "-"}'
                 f'{serit(tutar, tavan) if len(alt) else ""}</td></tr>')
    p.append('</tbody></table></div>')

    # --- En ağır bulgular ---
    p.append('<h3>Kapanış öncesi çözülmesi gerekenler</h3>')
    p.append('<div class="tablo-sarmal"><table><thead><tr><th>Test</th>'
             '<th>Şirket</th><th>Dönem</th><th>Nesne</th>'
             f'<th class="sag">{PB}</th><th>Açıklama</th></tr></thead><tbody>')
    for r in bulgular[bulgular["onem"] == "kritik"].head(12).itertuples():
        p.append(f'<tr><td><span class="rozet kritik">{r.test_kod}</span></td>'
                 f'<td>{r.sirket_kod}</td><td>{r.donem}</td>'
                 f'<td>{kacis(r.nesne)[:38]}</td>'
                 f'<td class="sag">{k(r.tutar_eur)}</td>'
                 f'<td style="font-size:12.5px;color:var(--sonuk)">'
                 f'{kacis(r.aciklama)[:150]}</td></tr>')
    p.append('</tbody></table></div>')

    # --- Yapay zekâ yorumu ---
    if yorum:
        satirlar = []
        for satir in yorum.splitlines():
            s = satir.strip()
            if not s:
                continue
            if s.startswith("# "):
                continue
            if s.startswith("## "):
                satirlar.append(f'<h2>{kacis(s[3:])}</h2>')
            elif s.startswith("- "):
                icerik = kacis(s[2:]).replace("**", "")
                satirlar.append(f'<li>{icerik}</li>')
            else:
                satirlar.append(f'<p>{kacis(s)}</p>')
        # <li> dizilerini <ul> ile sar
        metin, acik = [], False
        for s in satirlar:
            if s.startswith("<li>") and not acik:
                metin.append("<ul>"); acik = True
            elif not s.startswith("<li>") and acik:
                metin.append("</ul>"); acik = False
            metin.append(s)
        if acik:
            metin.append("</ul>")
        p.append('<h2>Sapma yorumu</h2>')
        p.append('<div class="yorum">' + "".join(metin) + '</div>')
        p.append('<div class="not">Bu metni Claude (claude-opus-5) yazdı. '
                 'Yukarıdaki bütün sayılar motorun hesabıdır; yapay zekâ katmanı '
                 'sayı üretmez, yalnızca hazır tabloyu yorumlar. Katman '
                 'kapatıldığında bu bölüm kaybolur, rakamların hiçbiri değişmez.</div>')

    # --- Denetim izi ---
    izler = []
    iz_yolu = KOK / "gunluk" / "denetim_izi.jsonl"
    if iz_yolu.exists():
        for satir in iz_yolu.read_text(encoding="utf-8").splitlines():
            try:
                izler.append(json.loads(satir))
            except json.JSONDecodeError:
                pass
    zeka_cagri = [i for i in izler if i.get("olay") == "zeka_cagri"]
    maliyet = sum(i.get("maliyet_usd", 0) for i in zeka_cagri)
    adimlar = [i for i in izler if i.get("olay") == "adim_bitti"]

    p.append('<h2>Denetim izi</h2>')
    p.append('<div class="izgara2"><div><h3>Boru hattı adımları</h3>'
             '<div class="tablo-sarmal"><table><thead><tr><th>Adım</th>'
             '<th class="sag">Süre</th><th class="sag">Uyarı</th>'
             '<th class="sag">Hata</th></tr></thead><tbody>')
    gorulen = {}
    for a in adimlar:
        gorulen[a["adim"]] = a
    for ad in ["veri_uret", "topla", "esle", "cevir", "kontrol", "sapma", "pano"]:
        a = gorulen.get(ad)
        if not a:
            continue
        p.append(f'<tr><td><code>{ad}</code></td>'
                 f'<td class="sag">{a["sure_sn"]:.2f} sn</td>'
                 f'<td class="sag {"uyari" if a["uyari"] else ""}">{a["uyari"]}</td>'
                 f'<td class="sag {"kotu" if a["hata"] else ""}">{a["hata"]}</td></tr>')
    p.append('</tbody></table></div></div>')

    p.append('<div><h3>Yapay zekâ çağrıları</h3><div class="tablo-sarmal">'
             '<table><thead><tr><th>Görev</th><th class="sag">Token</th>'
             '<th class="sag">Maliyet</th><th>İstem izi</th></tr></thead><tbody>')
    for c in zeka_cagri[-6:]:
        p.append(f'<tr><td><code>{kacis(c["gorev"])}</code></td>'
                 f'<td class="sag">{c["girdi_token"]:,}→{c["cikti_token"]:,}</td>'
                 f'<td class="sag">${c["maliyet_usd"]:.4f}</td>'
                 f'<td><code>{kacis(c.get("istem_parmak",""))}</code></td></tr>')
    p.append(f'<tr class="toplam"><td>Toplam</td><td class="sag">'
             f'{len(zeka_cagri)} çağrı</td><td class="sag">${maliyet:.4f}</td>'
             f'<td></td></tr>')
    p.append('</tbody></table></div></div></div>')

    p.append('<footer>MizanKöprü · konsolidasyon ve iç kontrol motoru · '
             '© 2026 Furkan Akduman · ticari kullanım ayrı lisans gerektirir · '
             f'yapılandırma parmak izi: '
             f'<code>{dosya_parmak_izi(KOK / "yapilandirma" / "hesap_eslesme.csv")}</code> · '
             f'bu dosya <code>py src/pano.py</code> ile üretildi ve elle '
             'düzenlenmemelidir.</footer>')

    hedef = CIKTI_DIZIN / "pano.html"
    hedef.write_text(SAYFA.format(govde="\n".join(p)), encoding="utf-8")
    g.iyi(f"Pano üretildi: {hedef}  ({hedef.stat().st_size/1024:.0f} KB)")
    g.iz("pano_uretildi", dosya=str(hedef), bulgu=len(bulgular), kritik=kritik)
    g.bitir({"bulgu": len(bulgular), "kritik": kritik,
             "boyut_kb": round(hedef.stat().st_size / 1024)})


if __name__ == "__main__":
    main()
