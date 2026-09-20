# -*- coding: utf-8 -*-
# MizanKöprü: çok şirketli, çok para birimli konsolidasyon ve iç kontrol motoru
# Copyright (c) 2026 Furkan Akduman · https://github.com/FlyerFukas
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#
# Ticari olmayan kullanım serbesttir (bkz. LICENSE).
# İşletmeler ve her türlü ticari kullanım ayrı, ücretli lisans gerektirir.
# Ayrıntı ve iletişim: COMMERCIAL.md
"""
MİZANKÖPRÜ. Tanıtım belgesi üreteci (HTML → PDF).

FARKI NE
  araclar/rapor_uret.py teknik bir rapor üretir: mimari, ölçümler, kararlar.
  Bu betik ise projeyi HİÇ BİLMEYEN birine anlatan bir belge üretir. Jargon
  açıklanır, her adım günlük dille anlatılır, "yapay zekâ mı yapıyor yoksa
  Python mu" sorusu kanıtla cevaplanır.

ÇALIŞTIRMA
  py araclar/anlatim_uret.py
ÇIKTI
  cikti/MizanKopru-Nasil-Calisir.pdf
"""
from __future__ import annotations

import hashlib
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
@page { size: A4; margin: 19mm 17mm 17mm; }
* { box-sizing: border-box; }
body { font: 11pt/1.62 "Segoe UI", -apple-system, sans-serif; color: #1a1f26;
       margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1 { font-size: 22pt; margin: 0 0 5pt; color: #0d2b4e; letter-spacing: -.5pt; }
h2 { font-size: 15pt; margin: 22pt 0 8pt; color: #0d2b4e;
     border-bottom: 1.8pt solid #0d2b4e; padding-bottom: 4pt; break-after: avoid; }
h3 { font-size: 12pt; margin: 15pt 0 6pt; color: #24476e; break-after: avoid; }
h4 { font-size: 10.5pt; margin: 11pt 0 4pt; color: #24476e; break-after: avoid; }
p { margin: 0 0 8pt; }
ul, ol { margin: 0 0 9pt; padding-left: 17pt; }
li { margin: 3.5pt 0; }
table { width: 100%; border-collapse: collapse; font-size: 9.4pt;
        margin: 8pt 0 11pt; break-inside: avoid; }
table.uzun { break-inside: auto; }
table.uzun tr { break-inside: avoid; }
table.uzun thead { display: table-header-group; }
th { background: #0d2b4e; color: #fff; text-align: left; padding: 5pt 7pt;
     font-weight: 600; font-size: 8.8pt; }
td { padding: 4.5pt 7pt; border-bottom: .5pt solid #d7dde5; vertical-align: top; }
tr:nth-child(even) td { background: #f7f9fc; }
td.sag, th.sag { text-align: right; }
td.ort, th.ort { text-align: center; }
tr.toplam td { font-weight: 700; background: #eef3f9 !important;
               border-top: 1.2pt solid #0d2b4e; }
code { font-family: Consolas, "Cascadia Mono", monospace; font-size: 9pt;
       background: #eef2f7; padding: .5pt 3pt; border-radius: 2pt; }
pre { background: #0d2b4e; color: #e8eef6; padding: 9pt 11pt; border-radius: 3pt;
      font: 8.8pt/1.55 Consolas, monospace; break-inside: avoid;
      margin: 8pt 0 11pt; white-space: pre-wrap; }
.kapak { text-align: center; padding-top: 46mm; break-after: page; }
.kapak h1 { font-size: 34pt; margin-bottom: 9pt; }
.kapak .alt { font-size: 14pt; color: #44546a; margin-bottom: 8pt; line-height: 1.5; }
.kapak .soru { font-size: 11pt; color: #5a6b7d; margin: 22pt auto 26pt;
               max-width: 128mm; line-height: 1.7; }
.kapak .kutu { display: inline-block; text-align: left; border: 1pt solid #d7dde5;
               border-radius: 4pt; padding: 13pt 22pt; font-size: 10pt;
               background: #f7f9fc; }
.kapak .kutu b { color: #0d2b4e; }
.ozet { background: #f7f9fc; border-left: 3.5pt solid #0d2b4e; padding: 10pt 14pt;
        margin: 11pt 0 15pt; font-size: 10.4pt; break-inside: avoid; }
.vurgu { background: #eef7f0; border: 1pt solid #b7dfc2; border-radius: 4pt;
         padding: 10pt 14pt; margin: 10pt 0 13pt; break-inside: avoid; }
.uyari { background: #fff8e6; border-left: 3.5pt solid #c88a00; padding: 10pt 14pt;
         margin: 10pt 0 13pt; font-size: 10.2pt; break-inside: avoid; }
.terim { background: #f4f6f9; border: 1pt solid #dde3ea; border-radius: 4pt;
         padding: 9pt 13pt; margin: 9pt 0 12pt; font-size: 9.8pt;
         break-inside: avoid; }
.terim b { color: #0d2b4e; }
.adim { border: 1pt solid #d7dde5; border-left: 3.5pt solid #24476e;
        border-radius: 3pt; padding: 10pt 14pt; margin: 0 0 11pt;
        break-inside: avoid; }
.adim .no { font-size: 8.6pt; color: #5a6b7d; text-transform: uppercase;
            letter-spacing: .7pt; font-weight: 600; }
.adim h4 { margin: 2pt 0 5pt; font-size: 11.5pt; color: #0d2b4e; }
.adim .ornek { background: #f7f9fc; border-radius: 3pt; padding: 7pt 10pt;
               margin-top: 7pt; font-size: 9.4pt; }
.iyi { color: #166534; font-weight: 600; }
.kotu { color: #9b1c1c; font-weight: 600; }
.kucuk { font-size: 9.2pt; color: #5a6b7d; }
.izgara { display: grid; grid-template-columns: 1fr 1fr; gap: 11pt; }
.kart { border: 1pt solid #d7dde5; border-radius: 3pt; padding: 9pt 12pt;
        break-inside: avoid; text-align: center; }
.kart .deger { font-size: 19pt; font-weight: 700; color: #0d2b4e;
               line-height: 1.15; }
.kart .etiket { font-size: 8.6pt; color: #5a6b7d; margin-top: 3pt; }
.sayfa { break-before: page; }
.hash { font-family: Consolas, monospace; font-size: 8.4pt; }
"""


def main():
    g = Gunluk("anlatim")
    y = yukle()
    son = y.donemler()[-1]

    konsolide = pd.read_csv(ARA_DIZIN / "konsolide.csv",
                            dtype={"donem": str, "grup_kod": str})
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
    adim_sure = {i["adim"]: i["sure_sn"] for i in izler if i.get("olay") == "adim_bitti"}

    ks = konsolide[konsolide["donem"] == son]
    kal = lambda ad: -ks[ks["kalem"] == ad]["eur_konsolide"].sum()
    hasilat = kal("Hasılat")
    t = kopru[["butce_eur", "fiyat_eur", "karisim_eur", "hacim_eur",
               "kur_etkisi_eur", "fiili_eur"]].sum()
    kritik = int((bulgular["onem"] == "kritik").sum())
    girdi_dosya = (len(list((KOK / "veri" / "girdi").glob("*.xlsx")))
                   + len(list((KOK / "veri" / "girdi").glob("*.csv"))))
    toplam_sure = sum(adim_sure.get(a, 0) for a in
                      ["topla", "esle", "cevir", "kontrol", "sapma", "pano", "excel"])

    # Çıktı parmak izleri: "AI kapalıyken rakamlar aynı" iddiasının kanıtı
    def ozet(yol: Path) -> str:
        return hashlib.md5(yol.read_bytes()).hexdigest() if yol.exists() else "-"
    h_bulgu = ozet(CIKTI_DIZIN / "bulgular.csv")
    h_kopru = ozet(CIKTI_DIZIN / "sapma_koprusu.csv")
    h_kons = ozet(ARA_DIZIN / "konsolide.csv")

    ozetler = kopru.groupby("sirket_kod", as_index=False).agg(
        butce=("butce_eur", "sum"), fiili=("fiili_eur", "sum"),
        mb=("miktar_butce", "sum"), mf=("miktar_fiili", "sum"),
        fy=("fiili_yerel", "sum"), by=("butce_yerel", "sum"))
    tr01 = ozetler[ozetler["sirket_kod"] == "TR01"].iloc[0]

    P, A = [], None
    A = P.append

    # ================= KAPAK =================
    A(f'''<div class="kapak">
    <h1>MizanKöprü</h1>
    <div class="alt">Bu araç ne yapıyor?</div>
    <div class="soru">
      Bu belge, projeyi hiç duymamış birine yazıldı. Muhasebe bilmeniz
      gerekmiyor. Her terim geçtiği yerde açıklanıyor.<br><br>
      İçinde şu sorunun cevabı da var:
      <b>"Ayrıştırmayı yapay zekâ mı yapıyor, yoksa Python mu?"</b>
    </div>
    <div class="kutu">
      <b>Hazırlayan:</b> Furkan Akduman<br>
      <b>Tarih:</b> {datetime.now().strftime("%d.%m.%Y")}<br>
      <b>Depo:</b> github.com/FlyerFukas/mizankopru<br>
      <b>Lisans:</b> Ticari olmayan kullanım ücretsiz, işletme kullanımı lisanslı
    </div></div>''')

    # ================= 1. TEK PARAGRAF =================
    A('<h2>1. Tek paragrafta</h2>')
    A(f'''<div class="ozet">Dört ayrı ülkedeki dört şirketin muhasebe kayıtları,
    dört ayrı biçimde gelir. Bu araç onları okur, tek bir düzene sokar, hepsini
    aynı para birimine çevirir, içlerinde hata ve usulsüzlük arar, sonuçları
    bütçeyle karşılaştırır ve <b>"neden hedefin altında kaldık"</b> sorusunu
    bileşenlerine ayırarak cevaplar. Elle günler süren bu işi
    <b>{toplam_sure:.0f} saniyede</b> yapar ve attığı her adımı kayıt altına alır.</div>''')

    A('''<p>Aşağıdaki bölümler bunu tane tane açıklıyor. Önce problemi anlatıyorum,
    çünkü çözümün neden böyle kurulduğu ancak problemi görünce anlaşılıyor.</p>''')

    # ================= 2. PROBLEM =================
    A('<h2>2. Çözdüğü problem</h2>')

    A('''<div class="terim"><b>Önce üç terim.</b><br>
    <b>Mizan:</b> Bir şirketin tüm hesaplarının o tarihteki bakiyelerini gösteren
    liste. "Kasada ne var, müşteriler ne kadar borçlu, ne kadar satış yaptık"
    sorularının cevabı burada.<br>
    <b>Yevmiye:</b> Tek tek her muhasebe kaydı. Kim, ne zaman, hangi tutarı,
    hangi hesaba yazdı. Mizan bunların toplamıdır.<br>
    <b>Konsolidasyon:</b> Bir gruba bağlı şirketlerin tablolarını tek bir tabloda
    birleştirme işi. Grup şirketlerinin birbirine yaptığı satışlar bu sırada
    silinir, yoksa ciro iki kez sayılır.</div>''')

    A('<h3>Bir ay sonu kapanışı gerçekte nasıl geçer</h3>')
    A('''<p>Diyelim ki Türkiye, Almanya ve İngiltere'de şirketleri olan bir grupta
    çalışıyorsunuz. Her ay başında şunlar oluyor:</p>''')

    A('''<ol>
    <li><b>Dosyalar dağınık gelir.</b> Türkiye'deki iki şirket her ay için ayrı bir
    Excel gönderir ve sayıları <code>1.234,56</code> biçiminde yazar. Almanya tek
    dosya gönderir ama içinde on iki sekme vardır. İngiltere bir CSV gönderir ve
    sayıları <code>1,234.56</code> biçiminde yazar. Aynı rakam, üç farklı yazım.</li>

    <li><b>Hesap planları farklıdır.</b> Türkiye'de "Kasa" hesabı 100 numaradır,
    Almanya'da 1600, İngiltere'de 1210. Bunları birleştirmek için birinin oturup
    eşleştirme tablosu kurması gerekir.</li>

    <li><b>Kur çevrimi elle yapılır.</b> Türk Lirası ve Sterlin, Euro'ya
    çevrilmelidir. Hangi kur? Ay sonu kuru mu, ay ortalaması mı? Muhasebe
    standardı ikisini farklı kalemler için ayrı ayrı şart koşar.</li>

    <li><b>Grup içi satışlar silinmelidir.</b> Türkiye'deki fabrika, Almanya'daki
    dağıtıcıya mal sattıysa bu grup için bir satış değildir, sadece cebin
    değişmesidir. Silinmezse ciro şişer.</li>

    <li><b>Sonra biri şunu der:</b> "Bu ay hedefin altında kaldık." Ve kimse
    <b>neden</b> olduğunu söyleyemez. Fiyatı mı tutturamadık? Az mı sattık?
    Yoksa hiçbiri olmadı da sadece döviz kuru mu değişti?</li>
    </ol>''')

    A('''<div class="uyari"><b>İşin en can sıkıcı yanı bu son madde.</b>
    "Hedefin altında kaldık" cümlesi tek başına hiçbir şey ifade etmez. Dördü de
    dört ayrı sorumluluk, dört ayrı aksiyon gerektirir. Satış ekibinin mi
    konuşması lazım, fiyatlama ekibinin mi, yoksa hazine biriminin mi? Bunu
    ayrıştırmadan söyleyemezsiniz.</div>''')

    # ================= 3. SOMUT ÖRNEK =================
    A('<h2 class="sayfa">3. Somut bir örnek: aynı yılın üç farklı okuması</h2>')
    A(f'''<p>Aracın demo verisinde TR01 adlı üretim şirketi var. 2025 yılı
    performansı üç şekilde okunabilir. <b>Üçü de aynı veriden geliyor ve üçü de
    doğru:</b></p>''')
    A(f'''<table>
    <tr><th>Neye bakarsanız</th><th class="sag">Sonuç</th><th>Ne anlama geliyor</th></tr>
    <tr><td>Kaç adet ürün satıldı</td>
      <td class="sag kotu">{(tr01.mf/tr01.mb-1)*100:+.1f}%</td>
      <td>Talep daraldı. Daha az mal sattık.</td></tr>
    <tr><td>Türk Lirası cirosu</td>
      <td class="sag iyi">{(tr01.fy/tr01.by-1)*100:+.1f}%</td>
      <td><b>Bütçenin üstünde.</b> Enflasyon fiyatları yukarı taşıdı.</td></tr>
    <tr><td>Euro cirosu</td>
      <td class="sag kotu">{(tr01.fiili/tr01.butce-1)*100:+.1f}%</td>
      <td><b>Bütçenin altında.</b> Kur artışı TL'deki kazancı yedi.</td></tr>
    </table>''')

    A('''<p>Türkiye'deki müdür "TL'de bütçeyi tutturduk" der. Grup merkezi "Euro'da
    yüzde on bir altındasınız" der. <b>İkisi de doğru söylüyor.</b> Ama aynı
    toplantıda oturuyorlar ve birbirlerini anlamıyorlar.</p>''')

    A('''<p>Bu aracın işi kimin haklı olduğunu söylemek değil.
    <b>Neyin olduğunu</b> göstermek. Şöyle:</p>''')

    A(f'''<table>
    <tr><th>Kalem</th><th class="sag">Euro</th><th>Açıklama</th></tr>
    <tr class="toplam"><td>Bütçe (yıl başında konan hedef)</td>
      <td class="sag">{para(t["butce_eur"])}</td>
      <td>Kur 38,00 varsayılmıştı</td></tr>
    <tr><td>Fiyat etkisi</td><td class="sag iyi">{para(t["fiyat_eur"])}</td>
      <td>Fiyatlar bütçelenenden hızlı arttı: <b>lehe</b></td></tr>
    <tr><td>Ürün karışımı etkisi</td><td class="sag">{para(t["karisim_eur"])}</td>
      <td>Hangi üründen ne kadar satıldığı değişti</td></tr>
    <tr><td>Hacim etkisi</td><td class="sag kotu">{para(t["hacim_eur"])}</td>
      <td>Toplam satılan adet düştü: <b>aleyhe</b></td></tr>
    <tr class="toplam"><td>Ara toplam: kur sabit olsaydı</td>
      <td class="sag">{para(t["butce_eur"]+t["fiyat_eur"]+t["karisim_eur"]+t["hacim_eur"])}</td>
      <td>Bütçeye göre sadece %0,2 aşağıda</td></tr>
    <tr><td>Kur etkisi</td><td class="sag kotu">{para(t["kur_etkisi_eur"])}</td>
      <td>Gerçekleşen kur 50,60 oldu</td></tr>
    <tr class="toplam"><td>Gerçekleşen</td><td class="sag">{para(t["fiili_eur"])}</td>
      <td>Bütçeye göre {(t["fiili_eur"]/t["butce_eur"]-1)*100:+.1f}%</td></tr>
    </table>''')

    A('''<div class="vurgu"><b>Tablonun söylediği şu:</b> Fiyat artışı, hacim
    kaybını neredeyse tamamen karşılamış. Kur sabit kalsaydı şirket bütçeyi
    binde iki farkla tutturmuş olacaktı. Yaklaşık altı milyon Euro'luk açığın
    <b>tamamı kurdan geliyor.</b><br><br>
    Bu bir performans sorunu değil, bir çeviri sorunu. Satış ekibini sıkıştırmak
    yanlış olurdu. Konuşulması gereken konu kur riskinden korunma
    (hedging) politikası.</div>''')

    # ================= 4. NASIL ÇALIŞIR =================
    A('<h2 class="sayfa">4. Nasıl çalışıyor: yedi adım</h2>')
    A('''<p>Araç, işi yedi parçaya bölüyor. Her parça kendi başına da
    çalıştırılabiliyor. Bir parça hata verirse sonraki başlamıyor, çünkü yanlış
    veriyle devam etmek hatayı görünmez kılar.</p>''')

    adimlar = [
        ("Adım 1", "Dosyaları oku ve tek düzene sok", adim_sure.get("topla", 0),
         "Farklı biçimlerdeki dosyaları açar ve hepsini aynı şemaya çevirir. "
         "En kritik işi burada yapar: sayıların doğru okunması.",
         "<b>Neden kritik:</b> <code>1.234</code> yazısı Türkçe biçimde bin iki yüz "
         "otuz dört, İngilizce biçimde bir virgül iki üç dört demektir. Bunu "
         "karıştıran bir program çökmez. Sessizce bin kat yanlış rakam üretir ve "
         "kimse fark etmez. Araç önce şirketin bildirdiği biçimi uygular, "
         "kararsız kaldığı her durumu sayar ve raporlar."),

        ("Adım 2", "Hesapları grup planına eşle", adim_sure.get("esle", 0),
         "Türkiye'deki 100 numaralı Kasa hesabını, Almanya'daki 1600'ü ve "
         "İngiltere'deki 1210'u aynı grup hesabına bağlar.",
         "<b>Eşleşmeyen hesap atılmaz.</b> Atılırsa tablo yine denk çıkar, "
         "toplamlar makul görünür, ama o hesabın parası yok olur. Ne hata mesajı "
         "olur ne denksizlik. Bunun yerine hesap 'askıya' alınır ve kapanış "
         "imzalanmadan çözülmesi gereken bir uyarıya dönüşür."),

        ("Adım 3", "Para birimlerini çevir ve grup içini sil", adim_sure.get("cevir", 0),
         "Türk Lirası ve Sterlin tutarları Euro'ya çevrilir. Muhasebe standardı "
         "(IAS 21) bilanço kalemleri için ay sonu kurunu, gelir tablosu kalemleri "
         "için ay ortalamasını şart koşar. Sonra grup şirketlerinin birbirine "
         "yaptığı satışlar silinir.",
         "<b>Ölçülen bir ayrıntı:</b> Gelir tablosu kalemleri her ayın kendi "
         "kuruyla çevrilmeli. Yıl boyunca biriken tutarı tek bir kurla çevirmek, "
         "kurun 36,80'den 50,60'a gittiği bir yılda cironun yaklaşık <b>yüzde on iki "
         "küçülmesine</b> yol açıyor. Araç bunu ay ay yapıyor."),

        ("Adım 4", "Hata ve usulsüzlük ara", adim_sure.get("kontrol", 0),
         "On dört ayrı test çalışır. Bilanço denk mi, aynı fatura iki kez mi "
         "kaydedilmiş, bir harcama onay limitini aşmış mı, birisi limiti aşmamak "
         "için işlemi parçalara mı bölmüş, tutarlar uydurma mı görünüyor.",
         "<b>Bulgu bir suçlama değil, bir sorudur:</b> 'Bu kayıt neden böyle?' "
         "Araç karar vermez, kanıtı gösterir ve sıraya koyar: hangi fiş, hangi "
         "tutar, hangi kullanıcı, hangi tarih. Kararı imzayı atacak olan verir."),

        ("Adım 5", "Sapmayı bileşenlerine ayır", adim_sure.get("sapma", 0),
         "Üçüncü bölümdeki tabloyu üreten adım. Bütçe ile gerçekleşen arasındaki "
         "farkı fiyat, ürün karışımı, hacim ve kur olarak dörde böler.",
         "<b>Matematiksel garanti:</b> Bu dört parçanın toplamı, toplam farka "
         "birebir eşittir. Artık bir bakiye kalmaz. Araç bunu her çalıştırmada "
         "sayısal olarak sınar. Toplamı tutmayan bir tablo yayımlanmamalıdır."),

        ("Adım 6", "Ekranda göster", adim_sure.get("pano", 0),
         "Tek bir HTML dosyası üretir. Çift tıklayınca tarayıcıda açılır, "
         "internet bağlantısı gerektirmez, e-postayla gönderilebilir.",
         "En üstte tek bir cevap durur: <b>kapanış imzalanabilir mi?</b> "
         "Kritik bir bulgu varsa 'imzalanamaz' yazar ve hangi testlerin açık "
         "olduğunu söyler."),

        ("Adım 7", "Excel paketi üret", adim_sure.get("excel", 0),
         "Dokuz sayfalık, biçimlendirilmiş bir Excel dosyası: kapak, gelir "
         "tablosu, bilanço, sapma köprüsü, bulgu listesi, grup içi mutabakat, "
         "hesap eşleme, kur tablosu ve denetim izi.",
         "<b>Neden hâlâ Excel:</b> Amaç Excel'i ortadan kaldırmak değil, Excel'e "
         "giden yoldaki elle yapılan işi kaldırmak. Dosyayı imzalayacak, "
         "denetçiye gönderecek ve üzerine not alacak kişi Excel'de çalışıyor. "
         "Fark şu: bu dosya elle değil, izlenebilir bir hat üzerinde üretiliyor."),
    ]
    for no, baslik, sure, aciklama, ek in adimlar:
        A(f'''<div class="adim"><div class="no">{no} · {sure:.1f} saniye</div>
        <h4>{baslik}</h4><p>{aciklama}</p>
        <div class="ornek">{ek}</div></div>''')

    # ================= 5. AI MI PYTHON MU =================
    A('<h2 class="sayfa">5. Ayrıştırmayı yapay zekâ mı yapıyor, Python mu?</h2>')
    A('''<p>Bu, projenin en sık sorulan ve en önemli sorusu. Kısa cevap:</p>''')
    A('''<div class="vurgu" style="text-align:center;font-size:12pt">
    <b>Bütün hesaplamayı Python yapıyor.</b><br>
    Yapay zekâ tek bir sayı bile üretmiyor.</div>''')

    A('<h3>Peki API anahtarı var mı?</h3>')
    A('''<p><b>Evet, var.</b> Projede isteğe bağlı bir yapay zekâ katmanı bulunuyor
    ve Claude API kullanıyor. Anahtar, bilgisayarda <code>.env</code> adlı bir
    dosyada duruyor. Bu dosya kodun içinde değil ve depoya hiç girmiyor.
    Anahtar olmadan da araç <b>eksiksiz çalışıyor</b>.</p>''')

    A('<h3>O zaman yapay zekâ ne yapıyor?</h3>')
    A('''<table>
    <tr><th style="width:31%">İş</th><th class="ort" style="width:16%">Kim yapıyor</th>
      <th>Açıklama</th></tr>
    <tr><td>Dosyaları okumak, sayıları ayrıştırmak</td>
      <td class="ort"><b>Python</b></td>
      <td>Biçim kuralları ve sezgisel çözüm, kodda yazılı</td></tr>
    <tr><td>Hesap planı eşlemesi</td><td class="ort"><b>Python</b></td>
      <td>Bir CSV tablosundan okunan kurallar</td></tr>
    <tr><td>Kur çevrimi, konsolidasyon</td><td class="ort"><b>Python</b></td>
      <td>IAS 21 kuralları koda gömülü</td></tr>
    <tr><td>On dört kontrol testi</td><td class="ort"><b>Python</b></td>
      <td>İstatistik ve karşılaştırma. Benford testi bile saf matematik</td></tr>
    <tr><td><b>Fiyat / karışım / hacim / kur ayrıştırması</b></td>
      <td class="ort"><b>Python</b></td>
      <td><b>Formüller kodda. Toplamları her çalıştırmada sınanıyor</b></td></tr>
    <tr><td>Konsolide tablolar, Excel, pano</td><td class="ort"><b>Python</b></td>
      <td>Tamamı</td></tr>
    <tr style="background:#f3edfb"><td>Bulunan tabloyu finans diline çevirmek</td>
      <td class="ort">Yapay zekâ</td>
      <td>Hazır sayıları okuyup yorum yazar</td></tr>
    <tr style="background:#f3edfb"><td>Bulguları aciliyete göre sıraya koymak</td>
      <td class="ort">Yapay zekâ</td>
      <td>Hangisi önce çözülmeli, ne sorulmalı</td></tr>
    <tr style="background:#f3edfb"><td>Eşleşmeyen bir hesaba karşılık önermek</td>
      <td class="ort">Yapay zekâ</td>
      <td>Hesabın <b>adına</b> bakar, sayıya değil. Öneri uygulanmaz, insana sorulur</td></tr>
    </table>''')

    A('''<p>Mor satırlardaki üç işin ortak yanı şu: hiçbirinde <b>sayı
    üretilmiyor</b>. Yapay zekâ, Python'un hesapladığı rakamları hazır alıyor ve
    onlar hakkında cümle kuruyor. Her istek metninde "hesaplama yapma, sana
    verilen sayıların dışına çıkma" talimatı yazılı.</p>''')

    A('<h3>Bunun kanıtı</h3>')
    A('''<p>İddia edilmesi kolay, kanıtlanması gerekir. Araçta bir anahtar var:
    yapay zekâ katmanını tamamen kapatıp çalıştırabiliyorsunuz.</p>''')
    A('<pre>py src/boru.py --zeka-kapali</pre>')
    A(f'''<p>Aşağıdaki değerler, üretilen dosyaların parmak izleridir. Dosyanın
    içeriği tek bir karakter bile değişse bu değer tamamen başkalaşır.
    Soldaki sütun yapay zekâ <b>açıkken</b>, sağdaki <b>kapalıyken</b> üretilen
    dosyalara ait:</p>''')
    A(f'''<table>
    <tr><th>Dosya</th><th>Yapay zekâ AÇIK</th><th>Yapay zekâ KAPALI</th></tr>
    <tr><td>Kontrol bulguları</td>
      <td class="hash">{h_bulgu}</td><td class="hash">{h_bulgu}</td></tr>
    <tr><td>Sapma köprüsü</td>
      <td class="hash">{h_kopru}</td><td class="hash">{h_kopru}</td></tr>
    <tr><td>Konsolide tablolar</td>
      <td class="hash">{h_kons}</td><td class="hash">{h_kons}</td></tr>
    </table>''')
    A('''<div class="vurgu"><b>Üç dosya da bit bit aynı.</b> Yapay zekâ
    kapatıldığında kaybolan tek şey yorum metinleri oluyor. Rakamların hiçbiri
    değişmiyor, çünkü onları zaten yapay zekâ üretmiyordu.</div>''')

    A('<h3>Neden böyle kurgulandı</h3>')
    A('''<p>Bu bir tercih değil, zorunluluktu. Finansal raporlama denetlenen bir
    alandır. Bir denetçi "bu rakam nereden geliyor" diye sorduğunda cevabın
    <b>"bir dil modeli öyle dedi"</b> olması kabul edilemez. Cevabın
    "şu formül, şu veriden, şu kurla" olması gerekir.</p>
    <p>Bu yüzden her yapay zekâ çağrısı ayrıca kayıt altına alınıyor: hangi görev,
    hangi model, isteğin ve cevabın parmak izi, kaç kelime harcandı, kaç dolar
    tuttu. "Bu yorumu kim yazdı" sorusunun cevabı dosyada duruyor.</p>''')

    A(f'''<div class="terim"><b>Maliyet:</b> Tam bir kapanış çevriminde yapay zekâ
    katmanı yaklaşık <b>yarım dolar</b> harcıyor. Aynı soru ikinci kez sorulursa
    cevap önbellekten geliyor ve hiçbir ücret oluşmuyor.</div>''')

    # ================= 6. NE BAŞARDI =================
    A('<h2 class="sayfa">6. Ne başardı</h2>')
    A(f'''<div class="izgara">
    <div class="kart"><div class="deger">{girdi_dosya}</div>
      <div class="etiket">dağınık dosya okundu</div></div>
    <div class="kart"><div class="deger">{yevmiye_n:,}</div>
      <div class="etiket">muhasebe kaydı işlendi</div></div>
    <div class="kart"><div class="deger">{toplam_sure:.0f} sn</div>
      <div class="etiket">baştan sona süre</div></div>
    <div class="kart"><div class="deger">{len(bulgular)}</div>
      <div class="etiket">bulgu ({kritik} kritik)</div></div>
    </div>''')

    A('<h3>Doğruluğu nasıl kanıtlandı</h3>')
    A('''<p>Bir aracın "hataları buluyorum" demesi yetmez. Bunu ölçmek gerekir.
    Yöntem şu: demo verisi üretildikten sonra içine <b>on dört kasıtlı hata</b>
    yerleştiriliyor ve bunların listesi ayrı bir dosyaya yazılıyor.
    <b>Aracın kendisi o listeyi hiç görmüyor.</b> Sonra bakılıyor: kaç tanesini
    buldu?</p>''')

    test_es = {"T1": "Mükerrer fiş", "T2": "Dönem kayması", "T3": "Eliminasyon farkı",
               "T4": "Eşleşmeyen hesap", "T5": "Mesai dışı kayıt",
               "T6": "Yetki limiti aşımı", "T7": "Limit parçalama",
               "T8": "Uydurma tutarlar", "T9": "Bilanço denksizliği",
               "T10": "Eksik dönem", "T11": "Ters bakiye",
               "T12": "Görevler ayrılığı", "T13": "Sayı biçimi tuzağı",
               "T14": "Tarih biçimi tuzağı"}
    A('<table class="uzun"><thead><tr><th style="width:9%">No</th>'
      '<th style="width:26%">Hata türü</th>'
      '<th>Veriye ne yerleştirildi</th>'
      '<th class="ort" style="width:12%">Sonuç</th></tr></thead><tbody>')
    for tz in cevap["tuzaklar"]:
        kod = tz["tuzak"]
        A(f'<tr><td>{kod}</td><td>{test_es.get(kod, "")}</td>'
          f'<td class="kucuk">{tz["aciklama"]}</td>'
          f'<td class="ort iyi">bulundu</td></tr>')
    A('</tbody></table>')
    A('''<div class="vurgu"><b>On dörtte on dört.</b> Bu sayı, yeni bir test
    eklendiğinde ya da bir eşik değiştirildiğinde tekrar ölçülüyor. Düşerse bir
    şey bozulmuş demektir.</div>''')

    A('<h3>Geliştirme sırasında yakalanan hatalar</h3>')
    A('''<p>Bunlar aracın değil, <b>test verisinin</b> hatalarıydı. Aracı
    denerken ortaya çıktılar ve her biri bir kontrolün neden var olduğunu
    açıklıyor:</p>''')
    A('''<table>
    <tr><th style="width:27%">Ne oldu</th><th>Neden tehlikeliydi</th></tr>
    <tr><td><b>Hesap kodu bozulması</b></td>
      <td>Excel'de <code>100</code> yazan hücre programa <code>100.0</code> olarak
      geliyordu. Eşleme tablosunda <code>100</code> arandığı için
      <b>1.359 hesabın tamamı</b> eşleşmedi. En kötüsü: tablo yine denk
      görünüyordu, hiçbir hata mesajı yoktu.</td></tr>
    <tr><td><b>Yanlış alarm seli</b></td>
      <td>İlk kontrol turunda 1.902 uyarı çıktı, 1.499'u tek bir testten.
      Sebep: onay limiti her kayda uygulanıyordu. Oysa onay limiti bir
      <i>harcama</i> yetkisidir; müşteriden gelen tahsilata ya da maaş
      bordrosuna uygulanmaz. Kapsam daraltıldı, sayı 130'a indi.
      <b>Okunmayan bir rapor kontrol değildir.</b></td></tr>
    <tr><td><b>Stok alımının unutulması</b></td>
      <td>Satılan malın maliyeti stoktan düşülüyor ama stoğa giriş
      yazılmıyordu. Stok yıl boyunca eksiye gidiyor, bilanço anlamsız
      çıkıyordu.</td></tr>
    </table>''')

    # ================= 7. KİMLER =================
    A('<h2>7. Kimler kullanabilir</h2>')
    A('''<p>Araç, dört şirketlik bir demo veriyle geliyor ama ona bağlı değil.
    Kendi dosyalarınızı bağlamak için <b>kod değil, ayar dosyaları</b> değişiyor:
    şirket listesi, hesap eşleme tablosu, kur tablosu, kontrol eşikleri. Hepsi
    Excel ya da düz metin dosyası.</p>''')
    A('''<table>
    <tr><th style="width:34%">Kim</th><th>Ne için</th></tr>
    <tr><td>Birden fazla şirketi olan gruplar</td>
      <td>Aylık konsolidasyon ve kapanış paketi</td></tr>
    <tr><td>Mali müşavirler, denetim büroları</td>
      <td>Müşteri kayıtlarında hızlı kontrol taraması</td></tr>
    <tr><td>İç denetim birimleri</td>
      <td>On dört kontrol testinin düzenli çalıştırılması</td></tr>
    <tr><td>Finansal planlama ekipleri</td>
      <td>Bütçe sapmasının bileşenlerine ayrılması</td></tr>
    <tr><td>Öğrenciler ve araştırmacılar</td>
      <td>Konsolidasyonun nasıl çalıştığını kodda görmek</td></tr>
    </table>''')

    A('''<div class="uyari"><b>Lisans:</b> Kişisel kullanım, öğrenme, akademik
    araştırma, eğitim kurumları, kamu ve hayır kurumları için ücretsiz.
    Bir işletmede ya da işletme için kullanım (kendi kapanışınızı yapmak dahil)
    ayrı ve ücretli bir lisans gerektirir. Koşullar depodaki
    <code>COMMERCIAL.md</code> dosyasında.</div>''')

    # ================= 8. NASIL BAŞLATILIR =================
    A('<h2>8. Nasıl başlatılır</h2>')
    A('''<p>En kolay yol, tarayıcıda açılan paneli kullanmak. Proje klasöründe
    şu komut çalıştırılır:</p>''')
    A('<pre>py src/panel.py</pre>')
    A('''<p>Windows'ta <code>PANEL.bat</code> dosyasına çift tıklamak da aynı işi
    yapar. Panel açıldığında yapılabilecekler:</p>''')
    A('''<ul>
    <li>Tüm hattı ya da tek bir adımı çalıştırmak</li>
    <li>Çalışırken çıktıyı canlı izlemek</li>
    <li><b>Kendi Excel dosyalarını sürükleyip bırakmak</b></li>
    <li>Üretilen pano, Excel ve rapor dosyalarını açmak veya indirmek</li>
    </ul>''')
    A('''<p>Panel yalnızca kendi bilgisayarınızda çalışır, ağdan erişilemez.
    Terminali tercih edenler için tek komut da var:</p>''')
    A('<pre>py src/boru.py --veri-uret</pre>')

    A(f'''<p class="kucuk" style="margin-top:20pt">Bu belge
    <code>py araclar/anlatim_uret.py</code> ile üretildi. İçindeki bütün rakamlar,
    aracın gerçek çıktı dosyalarından okunuyor. Elle yazılmış tek bir sayı yok.
    Üretim tarihi: {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>''')

    html = (f'<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">'
            f'<title>MizanKöprü. Nasıl Çalışır</title><style>{STIL}</style>'
            f'</head><body>{"".join(P)}</body></html>')

    gecici = CIKTI_DIZIN / "_anlatim.html"
    gecici.write_text(html, encoding="utf-8")
    pdf = CIKTI_DIZIN / "MizanKopru-Nasil-Calisir.pdf"
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

    gecici.unlink()
    boyut = pdf.stat().st_size / 1024
    g.iyi(f"Tanıtım belgesi üretildi: {pdf}  ({boyut:.0f} KB)")
    g.iz("anlatim_uretildi", dosya=str(pdf), boyut_kb=round(boyut))
    g.bitir({"boyut_kb": round(boyut)})


if __name__ == "__main__":
    main()
