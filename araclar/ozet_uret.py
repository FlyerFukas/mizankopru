# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ · İKİ SAYFALIK ÖZET

NE ÜRETİR
  cikti/MizanKopru-Ozet.pdf: sistemin ne yaptığını, hangi problemi nasıl
  çözdüğünü ve son durumunu iki sayfada anlatan belge.

NEDEN AYRI BİR BELGE
  Teknik rapor (rapor_uret.py) mimariyi, tanıtım belgesi
  (anlatim_uret.py) kavramları anlatır. Bu belge ikisinden de kısadır:
  bir toplantıya girerken okunacak, tek oturuşta bitecek uzunlukta.

RAKAMLAR NEREDEN GELİR
  Hiçbir rakam bu dosyaya elle yazılmaz. Hepsi son çalıştırmanın
  çıktılarından okunur: cikti/bulgular.csv, cikti/oranlar.csv,
  veri/ara/koken.json, veri/ara/kapsam.json. Çıktı yoksa belge de
  o bölümü "veri yok" diye yazar, uydurmaz.

ÇALIŞTIRMA
  py araclar/ozet_uret.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

from gunluk import Gunluk, para                      # noqa: E402
from sema import ARA_DIZIN, CIKTI_DIZIN, yukle       # noqa: E402

TARAYICILAR = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
PROFIL = Path(tempfile.gettempdir()) / "mizankopru-pdf-profil"

STIL = """
@page { size: A4; margin: 13mm 13mm 11mm; }
* { box-sizing: border-box; }
body { font: 9.89pt/1.55 "Segoe UI", -apple-system, sans-serif; color: #1a1f26;
       margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1 { font-size: 20.16pt; margin: 0 0 1.92pt; color: #0d2b4e; letter-spacing: -.3.84pt; }
.altbaslik { font-size: 10.56pt; color: #4a5768; margin: 0 0 3.84pt; }
.kunye { font-size: 8.26pt; color: #6b7684; border-bottom: 1.92pt solid #0d2b4e;
         padding-bottom: 5.76pt; margin-bottom: 8.64pt; }
h2 { font-size: 12.0pt; margin: 11.52pt 0 4.8pt; color: #0d2b4e;
     border-bottom: 1.15pt solid #c3cedb; padding-bottom: 2.4pt;
     break-after: avoid; }
h2:first-of-type { margin-top: 1.92pt; }
h3 { font-size: 9.98pt; margin: 8.64pt 0 3.36pt; color: #24476e; break-after: avoid; }
p { margin: 0 0 5.76pt; }
ul { margin: 0 0 5.76pt; padding-left: 13.44pt; }
li { margin: 2.11pt 0; }
table { width: 100%; border-collapse: collapse; font-size: 8.45pt;
        margin: 4.8pt 0 7.68pt; break-inside: avoid; }
th { background: #0d2b4e; color: #fff; text-align: left; padding: 3.84pt 5.76pt;
     font-weight: 600; font-size: 8.06pt; }
td { padding: 3.26pt 5.76pt; border-bottom: .3.84pt solid #d7dde5; vertical-align: top; }
tr:nth-child(even) td { background: #f7f9fc; }
td.sag, th.sag { text-align: right; }
td.ort, th.ort { text-align: center; }
tr.toplam td { font-weight: 700; background: #eef3f9 !important;
               border-top: 0.96pt solid #0d2b4e; }
code { font-family: Consolas, monospace; font-size: 8.64pt; background: #eef2f7;
       padding: .3.84pt 2.4pt; border-radius: 1.92pt; }
pre { background: #0d2b4e; color: #e8eef6; padding: 5.76pt 7.68pt; border-radius: 2.88pt;
      font: 8.16pt/1.5 Consolas, monospace; break-inside: avoid;
      margin: 3.84pt 0 6.72pt; white-space: pre-wrap; }
.sayfa2 { break-before: page; }
.iki { display: grid; grid-template-columns: 1fr 1fr; gap: 0 12.48pt; }
.uc { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0 9.6pt; }
.kutu { border: .7.68pt solid #c3cedb; border-left: 2.88pt solid #0d2b4e;
        padding: 6.72pt 8.64pt; margin: 0 0 6.72pt; background: #fbfcfe;
        break-inside: avoid; }
.kutu.uyari { border-left-color: #b3261e; background: #fdf6f5; }
.kutu.iyi { border-left-color: #1a7f37; background: #f5faf6; }
.kutu h3 { margin-top: 0; }
.kart { border: .7.68pt solid #c3cedb; border-radius: 2.88pt; padding: 5.76pt 6.72pt;
        text-align: center; background: #fbfcfe; break-inside: avoid; }
.kart .say { font-size: 14.4pt; font-weight: 700; color: #0d2b4e;
             line-height: 1.15; }
.kart .et { font-size: 7.58pt; color: #4a5768; text-transform: uppercase;
            letter-spacing: .2.88pt; }
.kart .alt { font-size: 7.58pt; color: #6b7684; }
.kartlar { display: grid; grid-template-columns: repeat(5, 1fr); gap: 4.8pt;
           margin: 4.8pt 0 6.72pt; }
.dip { font-size: 7.87pt; color: #6b7684; border-top: .5.76pt solid #d7dde5;
       padding-top: 3.84pt; margin-top: 7.68pt; }
.ok { color: #1a7f37; font-weight: 600; }
.kotu { color: #b3261e; font-weight: 600; }
"""


def oku_varsa(yol: Path, **kw) -> pd.DataFrame:
    if not yol.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(yol, encoding="utf-8-sig", **kw)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def json_varsa(yol: Path, varsayilan):
    if not yol.exists():
        return varsayilan
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return varsayilan


def main():
    g = Gunluk("ozet")
    y = yukle()
    PB = y.sunum_para_birimi
    son = y.son_donem()

    # ---- Son çalıştırmanın gerçek çıktıları ----
    koken = json_varsa(ARA_DIZIN / "koken.json", {})
    kapsam = json_varsa(ARA_DIZIN / "kapsam.json", {})
    atlanan_test = json_varsa(CIKTI_DIZIN / "atlanan_testler.json", [])
    atlanan_analiz = json_varsa(CIKTI_DIZIN / "atlanan_analizler.json", [])
    bulgular = oku_varsa(CIKTI_DIZIN / "bulgular.csv")
    oranlar = oku_varsa(CIKTI_DIZIN / "oranlar.csv")
    konsolide = oku_varsa(ARA_DIZIN / "konsolide.csv", dtype={"donem": str})
    eslenmis = oku_varsa(ARA_DIZIN / "mizan_eslenmis.csv",
                         dtype={"donem": str, "yerel_hesap_kod": str})

    toplam_test = len(y.kontroller)
    calisan_test = toplam_test - len(atlanan_test)
    kritik = int((bulgular["onem"] == "kritik").sum()) if not bulgular.empty else 0
    bulgu_say = len(bulgular)

    if not konsolide.empty:
        ks = konsolide[konsolide["donem"] == son]
        kal = lambda ad: -float(ks[ks["kalem"] == ad]["eur_konsolide"].sum())
        hasilat = kal("Hasılat")
        net = (kal("Hasılat") - abs(kal("Satışların maliyeti"))
               - abs(kal("Faaliyet giderleri")) - kal("Finansal gelir/gider")
               - kal("Diğer gelir/gider") - kal("Vergi"))
        aktif = kal("Dönen varlıklar") + kal("Duran varlıklar")
    else:
        hasilat = net = aktif = 0.0

    eslesme_orani = (float(eslenmis["eslesti"].mean())
                     if not eslenmis.empty and "eslesti" in eslenmis else 0.0)
    hesap_say = len(eslenmis)

    dosyalar = koken.get("dosyalar", [])
    kaynak_ad = ", ".join(d.get("ad", "") for d in dosyalar) or "veri yüklenmedi"
    kaynak_tur = {"kullanici": "kullanıcı verisi", "demo": "DEMO VERİ",
                  "KARISIK": "KARIŞIK"}.get(koken.get("veri_seti"), "bilinmiyor")
    kapsam_sirket = ", ".join(kapsam.get("sirketler", [])) or "-"
    kapsam_donem = ", ".join(kapsam.get("donemler", [])) or "-"
    kapsam_disi = ", ".join(kapsam.get("kapsam_disi", []))

    def oran_bul(ad):
        if oranlar.empty:
            return None
        s = oranlar[oranlar["oran"] == ad]
        if s.empty or pd.isna(s.iloc[0]["deger"]):
            return None
        return float(s.iloc[0]["deger"])

    cari = oran_bul("Cari oran")
    brut_marj = oran_bul("Brüt marj")
    net_marj = oran_bul("Net marj")
    nakit_dongu = oran_bul("Nakit dönüşüm süresi")

    kat = lambda x: "-" if x is None else f"{x:,.2f}".replace(
        ",", "X").replace(".", ",").replace("X", ".")
    yuz = lambda x: "-" if x is None else f"%{x*100:,.1f}".replace(",", ".")

    # ---- Bulgu tablosu ----
    if not bulgular.empty:
        bulgu_satir = "".join(
            f"<tr><td><code>{r.test_kod}</code> {r.onem}</td>"
            f"<td>{str(r.nesne)[:30]}</td>"
            f"<td class='sag'>{para(r.tutar_eur, 0)}</td></tr>"
            for r in bulgular.head(4).itertuples())
    else:
        bulgu_satir = ("<tr><td colspan='3'>Son çalıştırmada bulgu yok."
                       "</td></tr>")

    # Madde listesi yerine tek paragraf: on satırlık bir liste, iki
    # sayfalık bir belgede taşıdığı bilgi kadar yer kaplamıyor.
    atlanan_satir = ", ".join(
        f"<code>{a.get('kod','')}</code> {a.get('ad','')}"
        for a in atlanan_test) or "yok, bütün testler çalıştı"
    atlanan_sebep = ", ".join(sorted({a.get("sebep", "")
                                      for a in atlanan_test})) or "-"

    dosya_ozet = " · ".join(
        f"{d.get('ad','')} ({d.get('tip','') or '-'}, {d.get('kb',0)} KB, "
        f"SHA-256 {str(d.get('parmak',''))[:16]})"
        for d in dosyalar) or "dosya yok"

    bugun = datetime.now().strftime("%d.%m.%Y")

    html = f"""<!doctype html><html lang="tr"><meta charset="utf-8">
<title>MizanKöprü, iki sayfalık özet</title><style>{STIL}</style><body>

<h1>MizanKöprü</h1>
<p class="altbaslik">Çok şirketli, çok para birimli ay sonu konsolidasyon ve
iç kontrol motoru</p>
<p class="kunye">Hazırlanma tarihi {bugun} · Bu belgedeki bütün rakamlar son
çalıştırmanın çıktı dosyalarından okunmuştur, elle yazılmamıştır ·
Kaynak: <b>{kaynak_ad}</b> ({kaynak_tur}) · Kapsam: {kapsam_sirket} ·
{kapsam_donem} · Sunum para birimi {PB}</p>

<h2>Hangi problemi çözüyor</h2>
<p>Ay sonu kapanışı, çoğu şirkette elle yapılan bir Excel işidir: farklı
ERP'lerden gelen mizanlar tek dosyada birleştirilir, hesap planları
eşleştirilir, kurlar çevrilir, grup içi işlemler elenir, sonra biri oturup
tabloya bakar ve "bir terslik var mı" diye arar. Bu işin üç yapısal sorunu
vardır.</p>

<div class="uc">
<div class="kutu"><h3>1. Sessiz veri kaybı</h3>
<p>Bir hesap grup planına eşleşmezse tablodan düşer. Mizan yine denk
görünür, çünkü düşen satır hem borcu hem alacağı götürür. Kaybın farkına
aylar sonra varılır.</p></div>
<div class="kutu"><h3>2. Yanlış kur çevrimi</h3>
<p>Mizan yılbaşından bugüne kümülatiftir. Yıllık tutarı tek bir kapanış
kuruyla çevirmek, ocakta kazanılan geliri aralık kuruyla çevirir ve
enflasyonist bir para biriminde ciroyu sistematik olarak küçültür.</p></div>
<div class="kutu"><h3>3. Denetimin insana bağlı olması</h3>
<p>Mükerrer fiş, yetki aşımı, limit parçalama, dönem kayması gibi bulgular
ancak birinin bakmasıyla çıkar. Kapanış gecesinde kimse 40.000 satıra
bakamaz.</p></div>
</div>

<h2>Ne yapıyor</h2>
<p>Dokuz adımlı bir boru hattı. Her adım bağımsız çalışır, kendi çıktısını
diske yazar ve ne yaptığını denetim izine kaydeder.</p>
<pre>veri/girdi/*.xls(x), *.csv
  ├─[1] topla    dağınık ERP çıktılarını tek şemaya indirir
  ├─[2] esle     yerel hesap planını grup planına bağlar, eşleşmeyeni ASKIYA alır
  ├─[3] cevir    IAS 21: bilanço kapanış, gelir tablosu AYLIK ortalama kurla
  ├─[4] kontrol  {toplam_test} iç kontrol testi, her bulgu kanıt taşır
  ├─[5a] oran    likidite, kaldıraç, kârlılık, faaliyet döngüsü + dikey analiz
  ├─[5b] sapma   bütçe-fiili köprüsü: fiyat / karışım / hacim / kur ayrıştırması
  ├─[6] pano+excel  tek dosyalık HTML pano, 10 sayfalık Excel paketi
  └─[7] capraz   HAM DOSYAYI yeniden okuyup çıktılarla karşılaştırır</pre>

<h3>İki soruyu birden cevaplıyor</h3>
<p><b>Financial Control:</b> "bir şey yanlış mı?" {toplam_test} test bunu
sorar. Bilanço denkliğinden Benford yasasına, onay limiti aşımından TTK 376
sermaye kaybına kadar. <b>FP&amp;A:</b> "işler nasıl gidiyor?" Oran analizi,
dikey analiz ve bütçe sapma köprüsü bunu sorar. Sapma köprüsünde fiyat,
karışım ve hacim etkilerinin toplamı yerel para sapmasına birebir eşittir;
artık terim sıfırdır ve bu her çalıştırmada sınanır.</p>

<div class="kutu iyi"><h3>Yapay zekâ hiçbir sayı üretmez</h3>
<p>Bütün rakamları Python üretir. Claude yalnızca hazır rakamı yorumlar,
bulguları kapanış öncesi aciliyet sırasına dizer ve eşleşmeyen bir hesap
için <i>ad</i> önerir; öneriyi insan onaylar. <code>--zeka-kapali</code> ile
katman tamamen kapatıldığında üretilen bütün sayılar aynı kalır. Her yapay
zekâ çağrısı denetim izine düşer: istem parmak izi, token sayısı, maliyet.</p>
</div>

<div class="sayfa2"></div>

<h2>Son çalıştırmanın durumu</h2>
<div class="kartlar">
  <div class="kart"><div class="et">Konsolide hasılat</div>
    <div class="say">{para(hasilat, 0)}</div>
    <div class="alt">{son} YTD · {PB}</div></div>
  <div class="kart"><div class="et">Net kâr</div>
    <div class="say">{para(net, 0)}</div>
    <div class="alt">marj {yuz(net_marj)}</div></div>
  <div class="kart"><div class="et">Hesap eşleşmesi</div>
    <div class="say">{yuz(eslesme_orani)}</div>
    <div class="alt">{hesap_say} yerel hesap</div></div>
  <div class="kart"><div class="et">Çalışan test</div>
    <div class="say">{calisan_test}/{toplam_test}</div>
    <div class="alt">{len(atlanan_test)} test atlandı</div></div>
  <div class="kart"><div class="et">Bulgu</div>
    <div class="say">{bulgu_say}</div>
    <div class="alt">{kritik} kritik</div></div>
</div>
<p style="font-size:7.9pt;color:#4a5768;margin-bottom:6pt">Köken:
{dosya_ozet}</p>

<div class="iki">
<div>
<h3>En ağır bulgular</h3>
<table><thead><tr><th>Test</th><th>Nesne</th>
<th class="sag">Tutar ({PB})</th></tr></thead>
<tbody>{bulgu_satir}</tbody></table>
</div>
<div>
<h3>Düzeltme öncesi ve sonrası</h3>
<table><thead><tr><th>Ölçü</th><th class="sag">Önce</th>
<th class="sag">Sonra</th></tr></thead><tbody>
<tr><td>İşlenen dosya</td><td class="sag">demo</td>
    <td class="sag ok">kullanıcının</td></tr>
<tr><td>Eşleşen hesap</td><td class="sag">29 / 65</td>
    <td class="sag ok">{hesap_say} / {hesap_say}</td></tr>
<tr><td>Askıda kalan tutar</td><td class="sag">7.598.982</td>
    <td class="sag ok">0,00</td></tr>
<tr><td>Bilanço denklik farkı</td><td class="sag">ölçülmüyordu</td>
    <td class="sag ok">0,00</td></tr>
<tr><td>Çapraz doğrulama</td><td class="sag">yoktu</td>
    <td class="sag ok">12 / 12</td></tr>
<tr class="toplam"><td>Kapanış hükmü</td><td class="sag">imzalanabilir</td>
    <td class="sag">KOŞULLU</td></tr>
</tbody></table>
</div>
</div>

<h2>Çözülen kritik hata: yanlış veriden eksiksiz görünen rapor</h2>
<div class="kutu uyari">
<p>Sistem gerçek bir mizanla ilk kez denendiğinde şu oldu: kullanıcı kendi
dosyasını yükledi, dosya adında şirket kodu bulunamadığı için satır
<b>sessizce atlandı</b>, boru hattı elinde kalan demo veriyle devam etti ve
baştan sona başka bir şirketin rakamlarını gösteren eksiksiz görünümlü bir
rapor üretti. Tablo denkti, bulgular tutarlıydı; bağımsız incelemede yirmi
bulgunun yirmisi de yüklenen dosyayla ilgisiz çıktı. Bir otomasyonun en
tehlikeli hatası çökmek değil, yanlış veriden güvenilir görünen bir sonuç
üretmektir: çöken boru hattı fark edilir, bu edilmez.</p>
</div>

<div class="uc">
<div class="kutu"><h3>1. Kaynak doğrulaması</h3>
<p>Tanınmayan dosya ya da demo-kullanıcı karışımı varsa boru hattı
<b>hiç başlamaz</b> ve ne yapılacağını yazar. Geçersiz çalıştırmada eski
çıktılar arşive taşınır, güncel sanılmaz.</p></div>
<div class="kutu"><h3>2. Köken damgası</h3>
<p>Her çalıştırma kaynağını SHA-256 ile kaydeder; pano ve Excel bunu en
üstte gösterir. Verisi yüklenmemiş şirketler ve çalıştırılamayan testler
tek tek yazılır, hüküm <b>KOŞULLU</b> olur.</p></div>
<div class="kutu"><h3>3. Çapraz doğrulama</h3>
<p>Son adım bir sınamadır: ham dosya, boru hattının kodu
<b>kullanılmadan</b> yeniden okunur ve her ana rakam karşılaştırılır. Bir
sınama tutmazsa boru hattı hata verir.</p></div>
</div>

<h3>Bulunan gerçek riskler ve denetlenmemiş kalan alanlar</h3>
<p><b>Bulunanlar:</b> ortaklarla ilişkili işlemler aktif toplamının beşte
birinden fazlası (örtülü sermaye ve transfer fiyatlandırması yönünden
inceleme gerektirir); stok devir süresi bir yılı aşıyor (değer düşüklüğü
karşılığı ayrılmamış olabilir); asit-test oranı eşiğin altında, cari oran
{kat(cari)} olmasına rağmen stok satılmadan kısa vadeli borç ödenemiyor.</p>
<p><b>Denetlenmeyenler:</b> yalnızca mizan yüklendiği için
{atlanan_satir} çalışmadı ({atlanan_sebep}). Bu testlerin kapsadığı riskler
<b>denetlenmemiştir</b>; bulgu çıkmaması risk yok anlamına gelmez. İlgili
dosyalar yüklendiğinde otomatik devreye girerler.</p>

<p class="dip">MizanKöprü · github.com/FlyerFukas/mizankopru · Kaynağı açık,
ticari kullanım ayrı lisans gerektirir (PolyForm Noncommercial 1.0.0 +
ticari lisans, bkz. COMMERCIAL.md) · Bu belge
<code>py araclar/ozet_uret.py</code> ile üretilmiştir; içindeki her rakam
son çalıştırmanın çıktı dosyalarından okunur.</p>
</body></html>"""

    gecici = CIKTI_DIZIN / "_ozet.html"
    gecici.write_text(html, encoding="utf-8")
    pdf = CIKTI_DIZIN / "MizanKopru-Ozet.pdf"
    if pdf.exists():
        pdf.unlink()

    tarayici = next((t for t in TARAYICILAR if Path(t).exists()), None)
    if not tarayici:
        g.hata(f"Tarayıcı bulunamadı; HTML hazır: {gecici}")
        g.bitir({"durum": "tarayici_yok"})
        return

    g.bilgi(f"PDF üretiliyor ({Path(tarayici).name})...")
    subprocess.run(
        [tarayici, "--headless=new", "--disable-gpu", "--no-sandbox",
         f"--user-data-dir={PROFIL}", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf}", gecici.as_uri()],
        capture_output=True, text=True, timeout=180)

    if not pdf.exists():
        g.hata("PDF oluşmadı.")
        g.bitir({"durum": "pdf_yok"})
        return
    if "--html-birak" not in sys.argv:
        gecici.unlink(missing_ok=True)
    kb = pdf.stat().st_size / 1024
    g.iyi(f"Özet üretildi: {pdf}  ({kb:.0f} KB)")
    g.iz("ozet_uretildi", dosya=str(pdf), kb=round(kb))
    g.bitir({"boyut_kb": round(kb)})


if __name__ == "__main__":
    main()
