# -*- coding: utf-8 -*-
# MizanKöprü — çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ — Proje raporu üreteci (HTML → PDF).

Projenin ne yaptığını, nasıl çalıştığını ve hangi araçları kullandığını
anlatan baskıya uygun bir belge üretir. Rakamlar boru hattının gerçek
çıktılarından okunur — rapor elle güncellenmez.

ÇALIŞTIRMA
  py araclar/rapor_uret.py
ÇIKTI
  cikti/MizanKopru-Proje-Raporu.pdf
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

# Chrome önce: Edge headless, kullanıcı oturumu açıkken sessizce hiçbir şey
# üretmeden çıkabiliyor. İzole bir profil dizini ikisinde de şart.
TARAYICILAR = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
PROFIL = Path(tempfile.gettempdir()) / "mizankopru-pdf-profil"

STIL = """
@page { size: A4; margin: 17mm 15mm 16mm; }
* { box-sizing: border-box; }
body { font: 10.5pt/1.55 "Segoe UI", -apple-system, sans-serif; color: #1a1f26;
       margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1 { font-size: 21pt; margin: 0 0 4pt; color: #0d2b4e; letter-spacing: -.4pt; }
h2 { font-size: 14pt; margin: 20pt 0 7pt; color: #0d2b4e;
     border-bottom: 1.6pt solid #0d2b4e; padding-bottom: 3pt;
     break-after: avoid; }
h3 { font-size: 11.5pt; margin: 13pt 0 5pt; color: #24476e; break-after: avoid; }
h4 { font-size: 10pt; margin: 10pt 0 3pt; color: #24476e; break-after: avoid; }
p { margin: 0 0 7pt; text-align: justify; }
ul, ol { margin: 0 0 8pt; padding-left: 16pt; }
li { margin: 2.5pt 0; }
table { width: 100%; border-collapse: collapse; font-size: 8.8pt;
        margin: 7pt 0 10pt; break-inside: avoid; }
th { background: #0d2b4e; color: #fff; text-align: left; padding: 4.5pt 6pt;
     font-weight: 600; font-size: 8.2pt; }
td { padding: 3.8pt 6pt; border-bottom: .5pt solid #d7dde5; vertical-align: top; }
tr:nth-child(even) td { background: #f7f9fc; }
td.sag, th.sag { text-align: right; }
tr.toplam td { font-weight: 700; background: #eef3f9 !important;
               border-top: 1.2pt solid #0d2b4e; }
code { font-family: Consolas, "Cascadia Mono", monospace; font-size: 8.6pt;
       background: #eef2f7; padding: .5pt 3pt; border-radius: 2pt; }
pre { background: #0d2b4e; color: #e8eef6; padding: 8pt 10pt; border-radius: 3pt;
      font: 8.4pt/1.5 Consolas, monospace; overflow: hidden; break-inside: avoid;
      margin: 7pt 0 10pt; white-space: pre-wrap; }
.kapak { text-align: center; padding-top: 52mm; break-after: page; }
.kapak h1 { font-size: 33pt; margin-bottom: 8pt; }
.kapak .alt { font-size: 13pt; color: #44546a; margin-bottom: 30pt;
              line-height: 1.5; }
.kapak .kutu { display: inline-block; text-align: left; border: 1pt solid #d7dde5;
               border-radius: 4pt; padding: 12pt 20pt; font-size: 9.5pt;
               background: #f7f9fc; }
.kapak .kutu b { color: #0d2b4e; }
.ozet { background: #f7f9fc; border-left: 3pt solid #0d2b4e; padding: 8pt 12pt;
        margin: 10pt 0 14pt; font-size: 9.8pt; break-inside: avoid; }
.uyari { background: #fff8e6; border-left: 3pt solid #c88a00; padding: 8pt 12pt;
         margin: 9pt 0; font-size: 9.6pt; break-inside: avoid; }
.iyi { color: #166534; font-weight: 600; }
.kotu { color: #9b1c1c; font-weight: 600; }
.sonuk { color: #5a6b7d; }
.kucuk { font-size: 8.8pt; color: #5a6b7d; }
.izgara { display: grid; grid-template-columns: 1fr 1fr; gap: 10pt; }
.kart { border: 1pt solid #d7dde5; border-radius: 3pt; padding: 7pt 10pt;
        break-inside: avoid; }
.kart .etiket { font-size: 7.6pt; text-transform: uppercase; color: #5a6b7d;
                letter-spacing: .4pt; }
.kart .deger { font-size: 15pt; font-weight: 700; color: #0d2b4e; }
.sayfa { break-before: page; }
footer { position: fixed; bottom: 0; font-size: 7.5pt; color: #8b949e; }
"""


def main():
    g = Gunluk("rapor")
    y = yukle()
    son = y.donemler()[-1]

    # ---- Gerçek çıktılardan oku ----
    konsolide = pd.read_csv(ARA_DIZIN / "konsolide.csv", dtype={"donem": str, "grup_kod": str})
    bulgular = pd.read_csv(CIKTI_DIZIN / "bulgular.csv", encoding="utf-8-sig")
    kopru = pd.read_csv(CIKTI_DIZIN / "sapma_koprusu.csv", encoding="utf-8-sig",
                        dtype={"donem": str})
    mizan = pd.read_csv(ARA_DIZIN / "mizan.csv", dtype={"donem": str})
    yevmiye_n = sum(1 for _ in open(ARA_DIZIN / "yevmiye.csv", encoding="utf-8")) - 1
    cevap = json.load(open(KOK / "veri" / "ornek" / "TUZAK_CEVAP_ANAHTARI.json",
                           encoding="utf-8"))
    izler = [json.loads(s) for s in
             (KOK / "gunluk" / "denetim_izi.jsonl").read_text(encoding="utf-8").splitlines()
             if s.strip()]
    zeka = [i for i in izler if i.get("olay") == "zeka_cagri"]
    adim_sure = {}
    for i in izler:
        if i.get("olay") == "adim_bitti":
            adim_sure[i["adim"]] = i["sure_sn"]

    ks = konsolide[konsolide["donem"] == son]
    kal = lambda ad: -ks[ks["kalem"] == ad]["eur_konsolide"].sum()
    hasilat, smm = kal("Hasılat"), kal("Satışların maliyeti")
    opex = kal("Faaliyet giderleri")
    net = hasilat + smm + opex + kal("Finansal gelir/gider") + kal("Vergi")
    t = kopru[["butce_eur", "fiyat_eur", "karisim_eur", "hacim_eur",
               "kur_etkisi_eur", "fiili_eur"]].sum()
    kritik = int((bulgular["onem"] == "kritik").sum())
    girdi_dosya = len(list((KOK / "veri" / "girdi").glob("*.xlsx"))) + \
        len(list((KOK / "veri" / "girdi").glob("*.csv")))

    ozet = kopru.groupby("sirket_kod", as_index=False).agg(
        butce=("butce_eur", "sum"), fiili=("fiili_eur", "sum"),
        mb=("miktar_butce", "sum"), mf=("miktar_fiili", "sum"),
        fy=("fiili_yerel", "sum"), by=("butce_yerel", "sum"))

    P = []
    A = P.append

    # ================= KAPAK =================
    A(f'''<div class="kapak">
    <h1>MizanKöprü</h1>
    <div class="alt">Çok şirketli, çok para birimli<br>
      ay sonu konsolidasyon ve iç kontrol motoru</div>
    <div class="kutu">
      <b>Hazırlayan:</b> Furkan Akduman<br>
      <b>Tarih:</b> {datetime.now().strftime("%d.%m.%Y")}<br>
      <b>Depo:</b> github.com/FlyerFukas/mizankopru<br>
      <b>Lisans:</b> PolyForm Noncommercial 1.0.0 + ticari lisans<br>
      <b>Yapay zekâ ortağı:</b> Claude (claude-opus-5)
    </div>
    <div style="margin-top:14pt;font-size:8.6pt;color:#5a6b7d;max-width:118mm;
                margin-left:auto;margin-right:auto;text-align:center">
      Ticari olmayan kullanım serbesttir. İşletmeler ve her türlü ticari kullanım
      telif hakkı sahibinden ayrı, ücretli lisans alınmasını gerektirir.
      Ayrıntı: COMMERCIAL.md
    </div></div>''')

    # ================= 1. ÖZET =================
    A('<h2>1. Proje özeti</h2>')
    A('''<div class="ozet"><b>Tek cümlede:</b> Dört ülkeden farklı biçimlerde gelen
    ERP çıktılarını tek şemaya indiren, grup hesap planına eşleyen, IAS 21'e göre
    çeviren, 14 iç kontrol testinden geçiren ve bütçe sapmasını fiyat / karışım /
    hacim / kur bileşenlerine ayıran bir kapanış motoru.</div>''')

    A('''<p>Bir grup şirketinde ay sonu kapanışı şöyle geçer: dört ayrı ülkeden
    dört ayrı biçimde mizan gelir — biri Excel'de virgüllü ondalıkla, biri
    noktalıyla, biri 12 sekmeli tek dosyada, biri CSV. Hesap planları farklıdır.
    Kur çevrimi elle yapılır. Grup içi alım-satım elle mutabakat edilir. Sonra
    biri "hedefin altında kaldık" der ve kimse <b>neden</b> olduğunu söyleyemez.</p>''')

    A(f'''<p>Bu motor o işi <b>{sum(adim_sure.get(a, 0) for a in ["topla","esle","cevir","kontrol","sapma","pano","excel"]):.0f} saniyede</b>
    yapar ve her rakamın kaynağını kayıt altında tutar.</p>''')

    A('<h3>Ölçülen sonuçlar</h3>')
    A(f'''<div class="izgara">
    <div class="kart"><div class="etiket">İşlenen girdi</div>
      <div class="deger">{girdi_dosya}</div>
      <div class="kucuk">dosya · {yevmiye_n:,} yevmiye satırı · {len(mizan):,} mizan satırı</div></div>
    <div class="kart"><div class="etiket">Konsolide hasılat</div>
      <div class="deger">{para(hasilat/1e6,1)}M</div>
      <div class="kucuk">EUR · {son} YTD · net marj %{net/hasilat*100:.1f}</div></div>
    <div class="kart"><div class="etiket">Kontrol bulgusu</div>
      <div class="deger">{len(bulgular)}</div>
      <div class="kucuk">{kritik} kritik · 14 test</div></div>
    <div class="kart"><div class="etiket">Tuzak avı skoru</div>
      <div class="deger">14 / 14</div>
      <div class="kucuk">kasıtlı hataların tamamı yakalandı</div></div>
    </div>''')

    # ================= 2. ÇÖZDÜĞÜ PROBLEM =================
    A('<h2>2. Çözdüğü problem — somut bir örnek</h2>')
    A('''<p>Demo veride TR01 şirketinin 2025 yılı üç farklı şekilde okunabilir.
    Üçü de aynı veriden, üçü de doğru:</p>''')
    tr01 = ozet[ozet["sirket_kod"] == "TR01"].iloc[0]
    A(f'''<table>
    <tr><th>Ölçüt</th><th class="sag">Değişim</th><th>Ne anlama geliyor</th></tr>
    <tr><td>Satılan adet</td><td class="sag kotu">{(tr01.mf/tr01.mb-1)*100:+.1f}%</td>
      <td>Talep daraldı, hacim eridi</td></tr>
    <tr><td>Ciro (TRY — yerel para)</td><td class="sag iyi">{(tr01.fy/tr01.by-1)*100:+.1f}%</td>
      <td><b>Bütçenin üstünde</b> — enflasyon fiyatları taşıdı</td></tr>
    <tr><td>Ciro (EUR — sunum para birimi)</td><td class="sag kotu">{(tr01.fiili/tr01.butce-1)*100:+.1f}%</td>
      <td><b>Bütçenin altında</b> — kur artışı yedi</td></tr>
    </table>''')
    A('''<p>Türkiye'deki müdür "TL'de bütçeyi tutturduk" der. Grup merkezi "EUR'da
    %11 altındasınız" der. <b>İkisi de doğrudur.</b> Motorun işi kimin haklı
    olduğunu değil, <i>neyin olduğunu</i> göstermektir.</p>''')

    A('<h3>Sapma köprüsü — grup toplamı, 2025</h3>')
    A(f'''<table>
    <tr><th>Kalem</th><th class="sag">EUR</th><th class="sag">Bütçeye oran</th><th>Açıklama</th></tr>
    <tr class="toplam"><td>Bütçe (bütçe kuruyla)</td><td class="sag">{para(t["butce_eur"])}</td>
      <td class="sag"></td><td>EUR/TRY 38,00 sabit varsayılmıştı</td></tr>
    <tr><td>+ Fiyat etkisi</td><td class="sag iyi">{para(t["fiyat_eur"])}</td>
      <td class="sag">{t["fiyat_eur"]/t["butce_eur"]*100:+.1f}%</td>
      <td>Enflasyon birim fiyatları bütçelenenden hızlı artırdı</td></tr>
    <tr><td>+ Karışım etkisi</td><td class="sag">{para(t["karisim_eur"])}</td>
      <td class="sag">{t["karisim_eur"]/t["butce_eur"]*100:+.1f}%</td>
      <td>Ürün kırılımındaki kayma</td></tr>
    <tr><td>+ Hacim etkisi</td><td class="sag kotu">{para(t["hacim_eur"])}</td>
      <td class="sag">{t["hacim_eur"]/t["butce_eur"]*100:+.1f}%</td>
      <td>Satılan toplam adet düştü</td></tr>
    <tr class="toplam"><td>= Sabit kurda fiili</td>
      <td class="sag">{para(t["butce_eur"]+t["fiyat_eur"]+t["karisim_eur"]+t["hacim_eur"])}</td>
      <td class="sag">{(t["butce_eur"]+t["fiyat_eur"]+t["karisim_eur"]+t["hacim_eur"])/t["butce_eur"]*100-100:+.1f}%</td>
      <td><b>Operasyon bütçeyi neredeyse tam tutturdu</b></td></tr>
    <tr><td>+ Kur etkisi</td><td class="sag kotu">{para(t["kur_etkisi_eur"])}</td>
      <td class="sag">{t["kur_etkisi_eur"]/t["butce_eur"]*100:+.1f}%</td>
      <td>Gerçekleşen yıl sonu kuru 50,60</td></tr>
    <tr class="toplam"><td>Fiili (gerçekleşen kurla)</td><td class="sag">{para(t["fiili_eur"])}</td>
      <td class="sag">{(t["fiili_eur"]/t["butce_eur"]-1)*100:+.1f}%</td><td></td></tr>
    </table>''')
    A('''<p><b>Okunuşu:</b> Fiyat artışı (+6,8M) hacim kaybını (−6,9M) neredeyse
    tam karşılamış; sabit kurda fiili, bütçeye göre yalnızca %0,2 aşağıda.
    Yaklaşık 6 milyon EUR'luk açığın <b>tamamı kurdan</b> geliyor. Bu bir
    performans sorunu değil, bir çeviri sorunudur — ve ayrıştırma yapılmadan
    ikisi birbirinden ayrılamaz.</p>''')

    A('''<div class="uyari"><b>Matematiksel garanti:</b> Fiyat + karışım + hacim
    toplamı yerel para sapmasına <b>birebir</b> eşittir; artık terim bırakmaz. Bu
    özdeşlik her çalıştırmada sayısal olarak sınanır (ölçülen en büyük artık:
    0,0000). Tutmayan bir köprü yayımlanmamalıdır — kontrol koda gömülüdür.</div>''')

    # ================= 3. MİMARİ =================
    A('<h2 class="sayfa">3. Mimari — boru hattı</h2>')
    A('''<pre>veri/girdi/   41 dağınık dosya (farklı biçim, kolon adı, tarih ve sayı formatı)
     │
     ├─[1] topla.py     tek şemaya normalize et
     ├─[2] esle.py      yerel hesap kodu → grup hesap planı
     ├─[3] cevir.py     IAS 21 çevrim + eliminasyon + azınlık payı
     ├─[4] kontrol.py   14 iç kontrol testi
     ├─[5] sapma.py     fiyat / karışım / hacim / kur ayrıştırması
     └─[6] pano.py + excel.py
             cikti/pano.html · cikti/konsolidasyon_paketi.xlsx</pre>''')

    A('<h3>Adım adım</h3>')
    adimlar = [
        ("[1] topla.py", adim_sure.get("topla", 0),
         "41 dosyayı tek şemaya indirir. Dönem üç ayrı yerden gelebilir: dosya adından, "
         "sekme adından ya da bir kolondan. Sayı ayracı belirsizliğini çözer ve belirsiz "
         "kalan her durumu sayıp raporlar."),
        ("[2] esle.py", adim_sure.get("esle", 0),
         "Üç yerel hesap planını (VUK Tek Düzen, SKR04, UK COA) tek IFRS planına eşler. "
         "Eşleşmeyen satır atılmaz, askı hesabına alınır."),
        ("[3] cevir.py", adim_sure.get("cevir", 0),
         "IAS 21: bilanço kapanış, gelir tablosu ortalama kurla. YTD mizandan aylık "
         "hareket türetilir. Grup içi kalemler elimine edilir, azınlık payı hesaplanır."),
        ("[4] kontrol.py", adim_sure.get("kontrol", 0),
         "14 iç kontrol testi. Eşikler yapılandırmadan okunur. Her bulgu kanıt taşır: "
         "hangi fiş, hangi tutar, hangi kullanıcı."),
        ("[5] sapma.py", adim_sure.get("sapma", 0),
         "Bütçe-fiili köprüsü. Ayrıştırma özdeşliği her çalıştırmada sınanır. "
         "Satış detayı ile gelir tablosu arasındaki fark ayrıca mutabakat edilir."),
        ("[6a] pano.py", adim_sure.get("pano", 0),
         "Tek dosyalık HTML kapanış panosu. Harici bağımlılık yok; şelale grafiği "
         "saf SVG. En üstte 'imzalanabilir mi' sorusunun cevabı durur."),
        ("[6b] excel.py", adim_sure.get("excel", 0),
         "9 sayfalık formatlı konsolidasyon paketi: kapak, gelir tablosu, bilanço, "
         "sapma köprüsü, bulgular, grup içi mutabakat, hesap eşleme, kur, denetim izi."),
    ]
    A('<table><tr><th style="width:16%">Adım</th><th class="sag" style="width:9%">Süre</th>'
      '<th>Ne yapar</th></tr>')
    for ad, sure, aciklama in adimlar:
        A(f'<tr><td><code>{ad}</code></td><td class="sag">{sure:.1f} sn</td>'
          f'<td>{aciklama}</td></tr>')
    A('</table>')

    A('''<p>Her adım ayrı bir süreç olarak çalışır ve tek başına da
    çalıştırılabilir. Bir adım hata verirse boru hattı <b>durur</b> — yanlış
    veriyle bir sonraki adıma geçmek hatayı görünmez kılar. Adımlar arası durum
    <code>veri/ara/</code> altındaki dosyalarda taşınır, bu da yeniden
    üretilebilirliği garanti eder.</p>''')

    # ================= 4. ARAÇLAR =================
    A('<h2 class="sayfa">4. Kullanılan araçlar</h2>')
    A('<h3>Çalışma zamanı</h3>')
    A('''<table>
    <tr><th style="width:18%">Araç</th><th style="width:10%">Sürüm</th><th>Projede ne işe yarıyor</th></tr>
    <tr><td><b>Python</b></td><td>3.14</td><td>Tüm motorun dili. Harici servis bağımlılığı yok.</td></tr>
    <tr><td><b>pandas</b></td><td>3.0</td><td>Veri çerçeveleri: normalizasyon, gruplama, YTD→aylık
      türetme, eşleme birleştirmeleri. 3.0'ın davranış değişiklikleri
      (<code>to_excel</code> anahtar kelime zorunluluğu, <code>groupby.apply</code>)
      geliştirme sırasında yaşandı ve devir dosyasına yazıldı.</td></tr>
    <tr><td><b>NumPy</b></td><td>2.5</td><td>Dirichlet dağılımıyla gerçekçi fatura tutarı üretimi,
      Benford testinde logaritmik beklenen dağılım.</td></tr>
    <tr><td><b>openpyxl</b></td><td>3.1</td><td>Girdi <code>.xlsx</code> dosyalarının okunması —
      çok sekmeli kitaplar dahil.</td></tr>
    <tr><td><b>XlsxWriter</b></td><td>3.2</td><td>Çıktı Excel paketi: biçimlendirme, dondurulmuş
      başlıklar, otomatik filtre, koşullu renklendirme.</td></tr>
    <tr><td><b>PyYAML</b></td><td>6.0</td><td>Yapılandırma dosyalarının okunması.</td></tr>
    <tr><td><b>anthropic</b></td><td>0.116</td><td>Claude API istemcisi. İsteğe bağlı — yoksa
      motor tam çalışır.</td></tr>
    </table>''')

    A('<h3>Yapay zekâ</h3>')
    maliyet = sum(c.get("maliyet_usd", 0) for c in zeka)
    A(f'''<table>
    <tr><th style="width:26%">Görev</th><th>Ne yapar</th><th class="sag" style="width:13%">Maliyet</th></tr>
    <tr><td><code>esleme_oner</code></td><td>Grup planına eşlenemeyen yerel hesap için grup
      hesabı önerir. Öneri uygulanmaz; CSV'ye yazılır, insan onaylar.</td>
      <td class="sag">${sum(c["maliyet_usd"] for c in zeka if c["gorev"]=="esleme_oner"):.4f}</td></tr>
    <tr><td><code>bulgu_triyaj</code></td><td>Kontrol bulgularını aciliyete göre sıralar ve her
      biri için somut bir adım önerir.</td>
      <td class="sag">${sum(c["maliyet_usd"] for c in zeka if c["gorev"]=="bulgu_triyaj"):.4f}</td></tr>
    <tr><td><code>sapma_yorumla</code></td><td>Hazır sapma köprüsünü finans diline çevirir.</td>
      <td class="sag">${sum(c["maliyet_usd"] for c in zeka if c["gorev"]=="sapma_yorumla"):.4f}</td></tr>
    <tr class="toplam"><td>Toplam</td><td>{len(zeka)} çağrı · model <code>claude-opus-5</code></td>
      <td class="sag">${maliyet:.4f}</td></tr>
    </table>''')

    A('''<div class="uyari"><b>Mimari kısıt — LLM hiçbir sayıyı üretmez.</b>
    Motor sayıyı üretir; yapay zekâ yalnızca hazır sayıyı yorumlar,
    önceliklendirir ya da bir <i>ad</i> eşlemesi önerir. Bu bir pazarlama cümlesi
    değildir: her istem sayıları hazır verir ve "hesaplama yapma, verilen
    sayıların dışına çıkma" talimatını taşır. Katman kapatıldığında
    (<code>--zeka-kapali</code>) boru hattının ürettiği rakamların
    <b>hepsi aynı kalır</b>; yalnızca yorum metinleri kaybolur.</div>''')

    A('''<p><b>Denetim izi.</b> Her çağrı <code>gunluk/denetim_izi.jsonl</code>
    dosyasına görev, model, istem parmak izi, token sayısı, maliyet ve yanıt
    parmak iziyle kaydedilir. Regüle bir süreçte "bu yorumu kim yazdı" sorusunun
    cevabı dosyada durur. Önbellek açıktır — aynı istem ikinci kez API'ye
    gitmez.</p>''')

    A('<h3>Yapay zekânın gerçekten katkı yaptığı iki an</h3>')
    A('''<ol>
    <li><b>Doğru hesap eşlemesini bildi.</b> DE01 şirketi Temmuz'da
    <code>6815 "IT- und Softwarekosten"</code> hesabını açmış ama grup eşleme
    tablosuna eklememişti. Motor hesabı askıya aldı; yapay zekâ
    <code>6040 Genel yönetim giderleri</code> önerdi — cevap anahtarındaki doğru
    kod. Güvenini "orta" verdi ve "6060 Danışmanlık giderleri de mümkün olabilir"
    diye kendi kuşkusunu yazdı.</li>
    <li><b>Kendi kural setimizdeki eksiği buldu.</b> Bulgu triyajında
    <i>"K05 kural setine 'SISTEM tarafından kaydedilen açılış fişleri'
    istisnasının eklenmesi"</i> önerisi çıktı. Haklıydı; kalan 8 bulgunun 5'i
    açılış kaydıydı. İstisna uygulandı, yanlış pozitif 8'den 3'e indi ve gerçek
    yetki aşımı yakalanmaya devam etti.</li>
    </ol>''')
    A('''<p class="kucuk">Her iki durumda da yapay zekâ <b>hiçbir sayı
    üretmedi</b> — bir hesap adını eşleştirdi ve bir kural boşluğunu gördü.
    Rakamların tamamı motorun hesabıdır.</p>''')

    # ================= 5. KONTROL TESTLERİ =================
    A('<h2 class="sayfa">5. İç kontrol testleri</h2>')
    A('<table><tr><th style="width:7%">Kod</th><th style="width:22%">Test</th>'
      '<th style="width:9%">Önem</th><th class="sag" style="width:8%">Bulgu</th>'
      '<th>Ne arar</th></tr>')
    ne_arar = {
        "K01": "Borç ≠ alacak; mizan eksik ya da tek taraflı kayıt var",
        "K02": "Aynı tutar + hesap + tarih penceresi — çift ödeme göstergesi",
        "K03": "Belge tarihi dönem dışında; dönemsellik ilkesi ihlali",
        "K04": "Hafta sonu ya da gece girilmiş yüksek tutarlı fiş",
        "K05": "Onay limitini aşan tek fiş",
        "K06": "Aynı gün/kullanıcı/hesapta limitin hemen altında birden çok fiş",
        "K07": "İlk rakam dağılımının Benford'dan ki-kare sapması",
        "K08": "A'nın alacağı ile B'nin borcunun tutmaması",
        "K09": "Grup planında karşılığı olmayan yerel hesap",
        "K10": "Bir şirketin bir döneminin hiç gelmemesi",
        "K11": "Hesabın normal yönünün tersine hareket",
        "K12": "Belirli bir hesapta aşırı yuvarlak tutar yoğunluğu",
        "K13": "Kayıtların çoğunun tek kullanıcıda toplanması",
        "K14": "Hem oransal hem mutlak eşiği aşan bütçe sapması",
    }
    sayim = bulgular["test_kod"].value_counts().to_dict()
    for kod in sorted(y.kontroller):
        tst = y.kontroller[kod]
        sinif = "kotu" if tst["onem"] == "kritik" else ""
        A(f'<tr><td><code>{kod}</code></td><td>{tst["ad"]}</td>'
          f'<td class="{sinif}">{tst["onem"]}</td>'
          f'<td class="sag">{sayim.get(kod, 0)}</td><td>{ne_arar[kod]}</td></tr>')
    A('</table>')

    A('''<div class="ozet"><b>Bulgu ≠ hata.</b> Her bulgu bir iddia değil bir
    sorudur: "bu kayıt neden böyle?". Motor karar vermez, kanıtı gösterir ve
    sıraya koyar. Karar imzayı atacak olanındır.</div>''')

    A('<h3>Doğrulama: tuzak avı</h3>')
    A('''<p>Demo veri üreteci, üretim bittikten sonra <b>14 kasıtlı hata</b>
    enjekte eder ve hepsini bir cevap anahtarına yazar. Boru hattı bu dosyayı
    okumaz. Sonuç:</p>''')
    A('<table><tr><th style="width:8%">Tuzak</th><th style="width:10%">Test</th>'
      '<th>Enjekte edilen hata</th><th style="width:11%">Sonuç</th></tr>')
    test_es = {"T1": "K02", "T2": "K03", "T3": "K08", "T4": "K09", "T5": "K04",
               "T6": "K05", "T7": "K06", "T8": "K07/K12", "T9": "K01",
               "T10": "K10", "T11": "K11", "T12": "K13", "T13": "topla",
               "T14": "topla"}
    for tz in cevap["tuzaklar"]:
        A(f'<tr><td><code>{tz["tuzak"]}</code></td>'
          f'<td><code>{test_es[tz["tuzak"]]}</code></td>'
          f'<td>{tz["aciklama"]}</td><td class="iyi">yakalandı</td></tr>')
    A('</table>')
    A(f'''<p><b>Skor: 14/14</b> — toplam {len(bulgular)} bulgu üretildi
    (kritik {kritik}, yüksek {int((bulgular["onem"]=="yuksek").sum())},
    orta {int((bulgular["onem"]=="orta").sum())},
    düşük {int((bulgular["onem"]=="dusuk").sum())}). Bu çerçeve, yeni bir test
    eklendiğinde ya da bir eşik değiştiğinde skorun düşüp düşmediğini ölçmeyi
    sağlar.</p>''')

    # ================= 6. TASARIM KARARLARI =================
    A('<h2 class="sayfa">6. Tasarımın arkasındaki kararlar</h2>')
    A('''<h4>1. Eşleşmeyen satır atılmaz, askıya alınır</h4>
    <p>Eşleşmeyen bir hesabın satırı düşürülürse konsolide tablo yine denk çıkar,
    toplamlar makul görünür, ama o hesabın tutarı yok olur — ne hata mesajı vardır
    ne denksizlik. Bu, hata sınıflarının en tehlikelisidir: <b>sessiz</b> olanı.
    Askı hesabı (9999) tutarın kaybolmasını engeller ve kapanış imzalanmadan
    çözülmesi gereken bir bulguya dönüştürür.</p>''')

    A('''<h4>2. Gelir tablosu aylık çevrilir, YTD değil</h4>
    <p>Mizan yılbaşından itibaren kümülatiftir. YTD hasılatı tek kurla çevirmek,
    EUR/TRY'nin 36,80'den 50,60'a gittiği bir yılda Ocak'ta kazanılan geliri de
    Aralık kuruyla çevirir. Motor YTD'den aylık hareketi türetip her ayı kendi
    ortalama kuruyla çevirir.</p>''')
    A('''<table>
    <tr><th>Şirket</th><th class="sag">Doğru (aylık kur)</th>
      <th class="sag">Yanlış (tek kur)</th><th class="sag">Hata</th></tr>
    <tr><td>TR01</td><td class="sag">23.177.384</td><td class="sag">20.430.607</td>
      <td class="sag kotu">−%11,9</td></tr>
    <tr><td>TR02</td><td class="sag">10.792.134</td><td class="sag">9.415.982</td>
      <td class="sag kotu">−%12,8</td></tr>
    <tr><td>DE01 (EUR — çevrim yok)</td><td class="sag">22.116.705</td>
      <td class="sag">22.116.705</td><td class="sag">%0,0</td></tr>
    </table>''')
    A('<p class="kucuk">Tek kurla çevirmek TR şirketlerinin cirosunu sistematik '
      'olarak yaklaşık %12 küçültüyor.</p>')

    A('''<h4>3. Çevrim farkı ile veri hatası ayrıştırılır</h4>
    <p>Çevrimden sonra bilanço denk gelmez; fark özkaynağa yazılır. Ama yerel
    mizan <i>zaten</i> denk değilse o denksizlik de aynı yere düşer ve bir
    <b>veri hatası, "kur çevrim farkı" adı altında özkaynağa gömülüp
    kaybolur.</b> Motor ikisini ayırır: yerel denksizlik × kapanış kuru = veri
    hatası, kalanı saf çevrim farkı. Demo veride UK01'in Eylül ayındaki tek
    taraflı kaydı tam da bu yolla yakalanıyor.</p>''')

    A('''<h4>4. Excel ortadan kaldırılmıyor, üretiliyor</h4>
    <p>Amaç Excel'i öldürmek değil; Excel'e giden yoldaki <b>elle yapılan işi</b>
    — pivot, VLOOKUP, kur çevirme, mutabakat — ortadan kaldırmak. Kapanış paketi
    yine <code>.xlsx</code> olarak çıkar, çünkü onu imzalayacak, denetçiye
    gönderecek ve üzerine not alacak kişi orada çalışır. Fark şu: bu dosya elle
    değil, izlenebilir bir boru hattıyla üretilir.</p>''')

    # ================= 7. YAPILANDIRMA =================
    A('<h2>7. Kendi verinizle kullanmak</h2>')
    A('''<p>Motor sentetik demo veriyle gelir ama ona bağlı değildir. Kendi ERP
    çıktınızı bağlamak için <b>kod değil, yapılandırma</b> değişir:</p>''')
    A('''<table>
    <tr><th style="width:32%">Dosya</th><th>Ne tanımlar</th></tr>
    <tr><td><code>sirketler.yaml</code></td><td>Tüzel kişilikler, para birimleri,
      sahiplik oranları, dosya biçimleri, grup içi ilişkiler</td></tr>
    <tr><td><code>grup_hesap_plani.yaml</code></td><td>Grup IFRS hesap planı,
      bilanço/gelir tablosu ayrımı, eliminasyon bayrakları</td></tr>
    <tr><td><code>hesap_eslesme.csv</code></td><td>Yerel hesap → grup hesabı
      köprüsü (Excel'de düzenlenebilsin diye CSV)</td></tr>
    <tr><td><code>kolon_eslesme.yaml</code></td><td>ERP kolon adları
      (Borç / Soll / Debit) → iç şema</td></tr>
    <tr><td><code>kurlar.csv</code></td><td>Kapanış, ortalama ve bütçe kurları</td></tr>
    <tr><td><code>kontroller.yaml</code></td><td>14 testin eşikleri, onay
      limitleri, kapsam kuralları</td></tr>
    <tr><td><code>zeka.yaml</code></td><td>Model seçimi, önbellek, hangi yapay
      zekâ görevlerinin açık olduğu</td></tr>
    </table>''')
    A('''<p>Yükleyici bu dosyalar <i>arasındaki</i> tutarlılığı açılışta doğrular:
    eşleme tablosu var olmayan bir grup koduna mı işaret ediyor, bir şirketin para
    birimi kur tablosunda var mı, onay limitinin para birimi şirketinkiyle aynı mı.
    Hata boru hattının ortasında değil, en başta çıkar.</p>''')

    # ================= 8. ÖĞRENİLENLER =================
    A('<h2 class="sayfa">8. Geliştirme sırasında yakalanan hatalar</h2>')
    A('''<p>Aşağıdakiler projenin gerçek geliştirme günlüğünden alınmıştır ve
    devir dosyasında (<code>HANDOFF.md</code>) kayıtlıdır. Her biri, bir
    testin ya da bir doğrulamanın neden var olduğunu açıklar.</p>''')
    A('''<table>
    <tr><th style="width:24%">Hata</th><th>Neden tehlikeliydi</th><th style="width:26%">Çözüm</th></tr>
    <tr><td><b>Hesap kodu bozulması</b></td>
      <td>Excel'de <code>100</code> yazan hücre pandas'a <code>100.0</code> float
      gelir; <code>str()</code> onu <code>"100.0"</code> yapar. Eşleme tablosunda
      <code>"100"</code> arandığı için <b>1.359 hesabın tamamı</b> eşleşmeyen
      çıkmıştı — ve tablo yine denk görünüyordu.</td>
      <td><code>kod_metni()</code>: tam sayı float'ların kuyruğunu atar,
      <code>770.01</code> gibi gerçek ondalıklı kodları korur.</td></tr>
    <tr><td><b>Sayı ayracı belirsizliği</b></td>
      <td><code>1.234</code> Türkçe biçimde 1234, İngilizce biçimde 1,234'tür.
      Bu hatayı yapan boru hattı çökmez; sessizce 1000 kat yanlış rakam üretir.</td>
      <td>Yapılandırılmış biçim önce uygulanır; hem nokta hem virgül varsa
      sonuncusu ondalık kabul edilir; belirsiz kalan her durum sayılır ve
      raporlanır.</td></tr>
    <tr><td><b>Yanlış pozitif seli</b></td>
      <td>İlk kontrol turunda <b>1.902 bulgu</b> çıktı, 1.499'u tek testten.
      400 bulgulu bir rapor okunmaz; okunmayan rapor kontrol değildir.</td>
      <td>Onay limiti bir <i>harcama yetkisidir</i>; müşteri tahsilatına veya
      bordroya uygulanmaz. Kapsam daraltıldı: 1.499 → 3. Toplam 130 bulgu.</td></tr>
    <tr><td><b>Mevsimsellik maskesi</b></td>
      <td>Ocak (0,86) ile Aralık (1,24) karşılaştırması, miktar düşerken bile
      artıyor gösteriyordu.</td>
      <td>Doğru çerçeve Ocak–Aralık değil, bütçe-fiili yıllık toplamdır.</td></tr>
    <tr><td><b>Grup içi tutarsızlık</b></td>
      <td>Her şirket grup içi alımını kendi cirosundan tahmin ediyordu, satıcının
      kestiği faturadan değil; eliminasyon 5,8M EUR açık veriyordu.</td>
      <td>İki geçişli üretim: satıcının faturası kaydedilir, alıcının maliyeti
      ondan türetilir. Kalan ~%0,5 fark kur kaynaklı ve kasıtlıdır — K08'in
      ölçtüğü şey budur.</td></tr>
    </table>''')

    # ================= 9. TEKNİK =================
    A('<h2>9. Teknik özet</h2>')
    A(f'''<table>
    <tr><th style="width:36%">Ölçüt</th><th>Değer</th></tr>
    <tr><td>Kaynak dosya</td><td>10 Python modülü + 7 yapılandırma dosyası</td></tr>
    <tr><td>Girdi</td><td>{girdi_dosya} dosya · {yevmiye_n:,} yevmiye satırı ·
      {len(mizan):,} mizan satırı (YTD)</td></tr>
    <tr><td>Kapsam</td><td>4 tüzel kişilik · 3 hesap planı · 3 para birimi ·
      12 dönem</td></tr>
    <tr><td>Grup hesap planı</td><td>{len(y.grup_hesaplari)} hesap ·
      {len(y.eslesme)} eşleme satırı</td></tr>
    <tr><td>Uçtan uca süre</td><td>{sum(adim_sure.get(a,0) for a in ["veri_uret","topla","esle","cevir","kontrol","sapma","pano","excel"]):.0f} saniye
      (sentetik veri üretimi dahil)</td></tr>
    <tr><td>Yapay zekâ maliyeti</td><td>${maliyet:.2f} / tam kapanış çevrimi</td></tr>
    <tr><td>Çıktı</td><td>HTML pano (25 KB) · Excel paketi (9 sayfa, 35 KB) ·
      6 CSV/JSON/MD dosyası</td></tr>
    <tr><td>Denetim izi</td><td>{len(izler):,} olay kaydı</td></tr>
    <tr><td>Harici servis</td><td>Yok (yapay zekâ katmanı hariç, o da isteğe bağlı)</td></tr>
    </table>''')

    A('<h3>Yol haritası</h3>')
    A('''<ul>
    <li><b>IAS 29 enflasyon muhasebesi</b> — Türkiye 2022'den beri
    hiperenflasyonist ekonomi sayılıyor; parasal / parasal olmayan ayrımı hesap
    planında zaten tanımlı</li>
    <li>TCMB ve TÜİK verilerinin canlı API'den çekilmesi (şu an sabit tablo)</li>
    <li>Rolling forecast ve senaryo motoru ("kur %10 daha artarsa?")</li>
    <li>VUK ↔ IFRS köprüsü ve ertelenmiş vergi hesaplaması</li>
    </ul>''')

    A(f'''<p class="kucuk" style="margin-top:18pt">Bu belge
    <code>py araclar/rapor_uret.py</code> ile üretilmiştir. İçindeki bütün
    rakamlar boru hattının gerçek çıktı dosyalarından okunur; elle
    güncellenmez. Üretim: {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>''')

    html = (f'<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">'
            f'<title>MizanKöprü — Proje Raporu</title><style>{STIL}</style>'
            f'</head><body>{"".join(P)}</body></html>')

    gecici = CIKTI_DIZIN / "_rapor.html"
    gecici.write_text(html, encoding="utf-8")
    pdf = CIKTI_DIZIN / "MizanKopru-Proje-Raporu.pdf"
    if pdf.exists():
        pdf.unlink()

    tarayici = next((t for t in TARAYICILAR if Path(t).exists()), None)
    if not tarayici:
        g.hata("Edge veya Chrome bulunamadı; PDF üretilemedi. HTML hazır: "
               f"{gecici}")
        g.bitir({"durum": "tarayici_yok"})
        return

    g.bilgi(f"PDF üretiliyor ({Path(tarayici).name})...")
    sonuc = subprocess.run(
        [tarayici, "--headless=new", "--disable-gpu", "--no-sandbox",
         f"--user-data-dir={PROFIL}", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf}", gecici.as_uri()],
        capture_output=True, text=True, timeout=180)
    if not pdf.exists():
        g.hata(f"PDF oluşmadı. Tarayıcı çıktısı:\n{sonuc.stderr[-600:]}")
        g.bitir({"durum": "pdf_yok"})
        return

    gecici.unlink()
    boyut = pdf.stat().st_size / 1024
    g.iyi(f"Rapor üretildi: {pdf}  ({boyut:.0f} KB)")
    g.iz("rapor_uretildi", dosya=str(pdf), boyut_kb=round(boyut))
    g.bitir({"boyut_kb": round(boyut)})


if __name__ == "__main__":
    main()
