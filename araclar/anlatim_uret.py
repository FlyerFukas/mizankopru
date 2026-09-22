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
  Bu betik ise projeyi HİÇ BİLMEYEN birine, sistemin nasıl çalıştığını
  AŞAMA AŞAMA anlatan bir belge üretir. Jargon açıklanır, her adım günlük
  dille anlatılır, "yapay zekâ mı yapıyor yoksa Python mu" sorusu kanıtla
  cevaplanır.

KENDİ KENDİNE YETER
  Bu belgeyi üretmek için önceden bir çalıştırma gerekmez. Adım listesi
  boru hattının kendisinden, test sayısı yapılandırmadan okunur; anlatımın
  gövdesi kavramsaldır. Böylece hangi veri yüklü olursa olsun (ya da hiç
  yüklü olmasa da) belge üretilir. Canlı çalıştırmanın gerçek rakamları
  panoya ve Excel paketine gömülür; bu belge o rakamların NASIL üretildiğini
  anlatır.

ÇALIŞTIRMA
  py araclar/anlatim_uret.py
ÇIKTI
  cikti/MizanKopru-Nasil-Calisir.pdf
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

from gunluk import Gunluk                              # noqa: E402
from sema import CIKTI_DIZIN, yukle                    # noqa: E402

TARAYICILAR = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
PROFIL = Path(tempfile.gettempdir()) / "mizankopru-pdf-profil"

STIL = """
@page { size: A4; margin: 18mm 16mm 15mm; }
* { box-sizing: border-box; }
body { font: 10.6pt/1.6 "Segoe UI", -apple-system, sans-serif; color: #1a1f26;
       margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1 { font-size: 22pt; margin: 0 0 5pt; color: #0d2b4e; letter-spacing: -.5pt; }
h2 { font-size: 14.5pt; margin: 20pt 0 8pt; color: #0d2b4e;
     border-bottom: 1.8pt solid #0d2b4e; padding-bottom: 4pt; break-after: avoid; }
h3 { font-size: 11.5pt; margin: 14pt 0 5pt; color: #24476e; break-after: avoid; }
h4 { font-size: 10.4pt; margin: 10pt 0 4pt; color: #24476e; break-after: avoid; }
p { margin: 0 0 7pt; }
ul, ol { margin: 0 0 8pt; padding-left: 17pt; }
li { margin: 3pt 0; }
table { width: 100%; border-collapse: collapse; font-size: 9.2pt;
        margin: 7pt 0 10pt; break-inside: avoid; }
table.uzun { break-inside: auto; }
table.uzun tr { break-inside: avoid; }
table.uzun thead { display: table-header-group; }
th { background: #0d2b4e; color: #fff; text-align: left; padding: 5pt 7pt;
     font-weight: 600; font-size: 8.6pt; }
td { padding: 4.2pt 7pt; border-bottom: .5pt solid #d7dde5; vertical-align: top; }
tr:nth-child(even) td { background: #f7f9fc; }
td.sag, th.sag { text-align: right; }
td.ort, th.ort { text-align: center; }
tr.toplam td { font-weight: 700; background: #eef3f9 !important;
               border-top: 1.2pt solid #0d2b4e; }
code { font-family: Consolas, "Cascadia Mono", monospace; font-size: 8.9pt;
       background: #eef2f7; padding: .5pt 3pt; border-radius: 2pt; }
pre { background: #0d2b4e; color: #e8eef6; padding: 9pt 11pt; border-radius: 3pt;
      font: 8.6pt/1.55 Consolas, monospace; break-inside: avoid;
      margin: 7pt 0 10pt; white-space: pre-wrap; }
.kapak { text-align: center; padding-top: 42mm; break-after: page; }
.kapak h1 { font-size: 34pt; margin-bottom: 9pt; }
.kapak .alt { font-size: 14pt; color: #44546a; margin-bottom: 8pt; line-height: 1.5; }
.kapak .soru { font-size: 11pt; color: #5a6b7d; margin: 20pt auto 24pt;
               max-width: 130mm; line-height: 1.7; }
.kapak .kutu { display: inline-block; text-align: left; border: 1pt solid #d7dde5;
               border-radius: 4pt; padding: 13pt 22pt; font-size: 10pt;
               background: #f7f9fc; }
.kapak .kutu b { color: #0d2b4e; }
.ozet { background: #f7f9fc; border-left: 3.5pt solid #0d2b4e; padding: 10pt 14pt;
        margin: 10pt 0 14pt; font-size: 10.2pt; break-inside: avoid; }
.vurgu { background: #eef7f0; border: 1pt solid #b7dfc2; border-radius: 4pt;
         padding: 9pt 13pt; margin: 9pt 0 12pt; break-inside: avoid; }
.uyari { background: #fff8e6; border-left: 3.5pt solid #c88a00; padding: 9pt 13pt;
         margin: 9pt 0 12pt; font-size: 10pt; break-inside: avoid; }
.terim { background: #f4f6f9; border: 1pt solid #dde3ea; border-radius: 4pt;
         padding: 9pt 13pt; margin: 9pt 0 11pt; font-size: 9.6pt;
         break-inside: avoid; }
.terim b { color: #0d2b4e; }
.adim { border: 1pt solid #d7dde5; border-left: 3.5pt solid #24476e;
        border-radius: 3pt; padding: 9pt 13pt; margin: 0 0 10pt;
        break-inside: avoid; }
.adim .no { font-size: 8.4pt; color: #5a6b7d; text-transform: uppercase;
            letter-spacing: .7pt; font-weight: 600; }
.adim h4 { margin: 2pt 0 5pt; font-size: 11.2pt; color: #0d2b4e; }
.adim .ne { margin: 4pt 0; }
.adim .ornek { background: #f7f9fc; border-radius: 3pt; padding: 7pt 10pt;
               margin-top: 6pt; font-size: 9.2pt; }
.katman { border: 1pt solid #cdd8e6; border-left: 3.5pt solid #b3261e;
          border-radius: 3pt; padding: 9pt 13pt; margin: 0 0 10pt;
          background: #fdfbfb; break-inside: avoid; }
.katman h4 { margin: 0 0 4pt; color: #0d2b4e; }
.iyi { color: #166534; font-weight: 600; }
.kotu { color: #9b1c1c; font-weight: 600; }
.kucuk { font-size: 9pt; color: #5a6b7d; }
.izgara { display: grid; grid-template-columns: 1fr 1fr; gap: 10pt; }
.izgara3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 9pt; }
.kart { border: 1pt solid #d7dde5; border-radius: 3pt; padding: 9pt 12pt;
        break-inside: avoid; text-align: center; }
.kart .deger { font-size: 18pt; font-weight: 700; color: #0d2b4e;
               line-height: 1.15; }
.kart .etiket { font-size: 8.4pt; color: #5a6b7d; margin-top: 3pt; }
tr.mor td { background: #f3edfb !important; }
.sayfa { break-before: page; }
.hash { font-family: Consolas, monospace; font-size: 8.2pt; }
"""


def main():
    g = Gunluk("anlatim")
    y = yukle()

    # Adım listesi ve test sayısı CANLI okunuyor: kod değişince belge de
    # değişir, elle güncelleme gerekmez.
    try:
        import boru
        adim_sayisi = len(boru.ADIMLAR)
    except Exception:
        adim_sayisi = 10
    test_sayisi = len(y.kontroller)

    P = []
    A = P.append

    # ================= KAPAK =================
    A(f'''<div class="kapak">
    <h1>MizanKöprü</h1>
    <div class="alt">Bu sistem nasıl çalışıyor?</div>
    <div class="soru">
      Bu belge, projeyi hiç duymamış birine yazıldı. Muhasebe bilmeniz
      gerekmiyor; her terim geçtiği yerde açıklanıyor. Amacı, aracın
      <b>hangi aşamada ne yaptığını</b> tane tane göstermek.<br><br>
      İçinde şu iki sorunun da cevabı var:
      <b>"Ayrıştırmayı yapay zekâ mı yapıyor, yoksa Python mu?"</b> ve
      <b>"Yanlış veri yüklersem ne olur?"</b>
    </div>
    <div class="kutu">
      <b>Hazırlayan:</b> Furkan Akduman<br>
      <b>Tarih:</b> {datetime.now().strftime("%d.%m.%Y")}<br>
      <b>Depo:</b> github.com/FlyerFukas/mizankopru<br>
      <b>Lisans:</b> Ticari olmayan kullanım ücretsiz, işletme kullanımı lisanslı
    </div></div>''')

    # ================= 1. TEK PARAGRAF =================
    A('<h2>1. Tek paragrafta</h2>')
    A(f'''<div class="ozet">Farklı ülkelerdeki şirketlerin muhasebe kayıtları,
    farklı biçimlerde gelir. Bu araç onları okur, tek bir düzene sokar, hepsini
    aynı para birimine çevirir, içlerinde hata ve usulsüzlük arar, finansal
    oranları hesaplar, sonuçları bütçeyle karşılaştırır ve
    <b>"neden hedefin altında kaldık"</b> sorusunu bileşenlerine ayırarak
    cevaplar. En sonunda ürettiği her rakamı, ham dosyayı bağımsız olarak
    yeniden okuyup <b>doğrular</b>. Elle günler süren bu işi, izlenebilir
    <b>{adim_sayisi} adımlık</b> bir hatta bölerek yapar ve attığı her adımı
    kayıt altına alır.</div>''')

    A('''<p>Aşağıdaki bölümler bunu tane tane açıklıyor. Önce problemi
    anlatıyorum, çünkü çözümün neden böyle kurulduğu ancak problemi görünce
    anlaşılıyor. Sonra {n} adımın her birinde ne yapıldığını, ardından bu
    aracı bir kapanış aracı yapan güvenlik katmanlarını ele alıyorum.</p>'''
      .replace("{n}", str(adim_sayisi)))

    # ================= 2. PROBLEM =================
    A('<h2>2. Çözdüğü problem</h2>')

    A('''<div class="terim"><b>Önce üç terim.</b><br>
    <b>Mizan:</b> Bir şirketin tüm hesaplarının o tarihteki bakiyelerini
    gösteren liste. "Kasada ne var, müşteriler ne kadar borçlu, ne kadar satış
    yaptık" sorularının cevabı burada.<br>
    <b>Yevmiye:</b> Tek tek her muhasebe kaydı. Kim, ne zaman, hangi tutarı,
    hangi hesaba yazdı. Mizan bunların toplamıdır.<br>
    <b>Konsolidasyon:</b> Bir gruba bağlı şirketlerin tablolarını tek bir
    tabloda birleştirme işi. Grup şirketlerinin birbirine yaptığı satışlar bu
    sırada silinir, yoksa ciro iki kez sayılır.</div>''')

    A('<h3>Bir ay sonu kapanışı gerçekte nasıl geçer</h3>')
    A('''<p>Diyelim ki Türkiye, Almanya ve İngiltere'de şirketleri olan bir
    grupta çalışıyorsunuz. Her ay başında şunlar oluyor:</p>''')

    A('''<ol>
    <li><b>Dosyalar dağınık gelir.</b> Türkiye'deki şirketler sayıları
    <code>1.234,56</code> biçiminde yazar. Almanya tek dosya gönderir ama
    içinde on iki sekme vardır. İngiltere bir CSV gönderir ve sayıları
    <code>1,234.56</code> biçiminde yazar. Aynı rakam, üç farklı yazım.</li>

    <li><b>Hesap planları farklıdır.</b> Türkiye'de "Kasa" hesabı 100 numaradır,
    Almanya'da 1600, İngiltere'de 1210. Bunları birleştirmek için birinin
    oturup eşleştirme tablosu kurması gerekir.</li>

    <li><b>Kur çevrimi elle yapılır.</b> Türk Lirası ve Sterlin, sunum para
    birimine çevrilmelidir. Hangi kur? Ay sonu kuru mu, ay ortalaması mı?
    Muhasebe standardı ikisini farklı kalemler için ayrı ayrı şart koşar.</li>

    <li><b>Grup içi satışlar silinmelidir.</b> Türkiye'deki fabrika,
    Almanya'daki dağıtıcıya mal sattıysa bu grup için bir satış değildir,
    sadece cebin değişmesidir. Silinmezse ciro şişer.</li>

    <li><b>Sonra biri şunu der:</b> "Bu ay hedefin altında kaldık." Ve kimse
    <b>neden</b> olduğunu söyleyemez. Fiyatı mı tutturamadık? Az mı sattık?
    Yoksa hiçbiri olmadı da sadece döviz kuru mu değişti?</li>
    </ol>''')

    A('''<div class="uyari"><b>Ama en tehlikeli sorun bunların hiçbiri değil.</b>
    Bir kapanış aracının yapabileceği en kötü şey çökmek değildir; çökme fark
    edilir. En kötüsü, <b>yanlış veriden eksiksiz görünen bir rapor</b>
    üretmektir: tablo denktir, toplamlar makuldür, ama rakamlar başka bir
    şeyden gelmektedir. Bu araç bir kez tam bunu yaptı ve o olaydan sonra
    5. bölümdeki üç güvenlik katmanı eklendi. Önce aracın normal işleyişini,
    sonra bu katmanları anlatıyorum.</div>''')

    # ================= 3. SOMUT ÖRNEK =================
    A('<h2 class="sayfa">3. Somut bir örnek: aynı yılın üç okuması</h2>')
    A('''<p>Aracın demo verisinde TR01 adlı bir üretim şirketi var. Enflasyonist
    bir yılın performansı üç şekilde okunabilir. <b>Üçü de aynı veriden geliyor
    ve üçü de doğru:</b></p>''')
    A('''<table>
    <tr><th>Neye bakarsanız</th><th class="sag">Sonuç</th>
      <th>Ne anlama geliyor</th></tr>
    <tr><td>Kaç adet ürün satıldı</td>
      <td class="sag kotu">-12,1%</td>
      <td>Talep daraldı. Daha az mal sattık.</td></tr>
    <tr><td>Türk Lirası cirosu</td>
      <td class="sag iyi">+2,1%</td>
      <td><b>Bütçenin üstünde.</b> Enflasyon fiyatları yukarı taşıdı.</td></tr>
    <tr><td>Sunum para birimi (Euro) cirosu</td>
      <td class="sag kotu">-11,2%</td>
      <td><b>Bütçenin altında.</b> Kur artışı TL'deki kazancı yedi.</td></tr>
    </table>''')

    A('''<p>Türkiye'deki müdür "TL'de bütçeyi tutturduk" der. Grup merkezi
    "Euro'da yüzde on bir altındasınız" der. <b>İkisi de doğru söylüyor.</b>
    Ama aynı toplantıda oturuyorlar ve birbirlerini anlamıyorlar.</p>''')

    A('''<p>Bu aracın işi kimin haklı olduğunu söylemek değil.
    <b>Neyin olduğunu</b> göstermek. Bütçeden gerçekleşene giden yolu parçalara
    böler (demo verisindeki rakamlarla):</p>''')

    A('''<table>
    <tr><th>Kalem</th><th class="sag">Euro</th><th>Açıklama</th></tr>
    <tr class="toplam"><td>Bütçe (yıl başında konan hedef)</td>
      <td class="sag">77,0M</td><td>Kur 38,00 varsayılmıştı</td></tr>
    <tr><td>+ Fiyat etkisi</td><td class="sag iyi">+6,8M</td>
      <td>Fiyatlar bütçelenenden hızlı arttı: <b>lehe</b></td></tr>
    <tr><td>+ Hacim etkisi</td><td class="sag kotu">-6,9M</td>
      <td>Toplam satılan adet düştü: <b>aleyhe</b></td></tr>
    <tr class="toplam"><td>= Kur sabit olsaydı</td>
      <td class="sag">76,8M</td><td>Bütçeye göre yalnızca %0,2 aşağıda</td></tr>
    <tr><td>+ Kur etkisi</td><td class="sag kotu">-5,8M</td>
      <td>Gerçekleşen kur 50,60 oldu</td></tr>
    <tr class="toplam"><td>= Gerçekleşen</td><td class="sag">71,0M</td>
      <td>Bütçeye göre -%7,8</td></tr>
    </table>''')

    A('''<div class="vurgu"><b>Tablonun söylediği şu:</b> Fiyat artışı, hacim
    kaybını neredeyse tamamen karşılamış. Kur sabit kalsaydı şirket bütçeyi
    binde iki farkla tutturmuş olacaktı. Yaklaşık altı milyon Euro'luk açığın
    <b>tamamı kurdan geliyor.</b> Bu bir performans sorunu değil, bir çeviri
    sorunu. Satış ekibini sıkıştırmak yanlış olurdu; konuşulması gereken konu
    kur riskinden korunma (hedging) politikası.</div>''')

    A('''<p class="kucuk">Bu tablonun nasıl üretildiği (fiyat, karışım, hacim,
    kur ayrıştırması) 7. bölümde açıklanıyor. Önce hattın tamamını görelim.</p>''')

    # ================= 4. BORU HATTI =================
    A(f'<h2 class="sayfa">4. Nasıl çalışıyor: {adim_sayisi} adım</h2>')
    A('''<p>Araç, işi bir <b>boru hattına</b> böler. Su borularında olduğu gibi,
    bir adımın çıktısı bir sonraki adımın girdisidir. Her adım kendi başına da
    çalıştırılabilir ve ne yaptığını bir denetim izine kaydeder. Bir adım hata
    verirse sonraki başlamaz: <b>yanlış veriyle devam etmek, hatayı görünmez
    kılar.</b></p>''')

    adimlar = [
        ("Adım 1", "Dosyaları oku ve tek düzene sok",
         "Farklı biçimlerdeki dosyaları (Excel tek sekme, Excel çok sekme, CSV) "
         "açar ve hepsini aynı şemaya çevirir. Farklı kolon adlarını (Borç / "
         "Soll / Debit), farklı tarih ve sayı biçimlerini, dönemin üç ayrı "
         "yerden gelmesini burada tekleştirir.",
         "<b>Neden en kritik adım bu:</b> <code>1.234</code> yazısı Türkçe "
         "biçimde bin iki yüz otuz dört, İngilizce biçimde bir virgül iki üç "
         "dört demektir. Bunu karıştıran bir program çökmez; sessizce bin kat "
         "yanlış rakam üretir ve kimse fark etmez. Araç önce şirketin bildirdiği "
         "biçimi uygular, kararsız kaldığı her durumu sayar ve raporlar. Ayrıca "
         "Excel'in <code>100</code>'ü <code>100.0</code> yapmasına karşı hesap "
         "kodlarını metin olarak korur; bu önlem olmasa binlerce hesap sessizce "
         "eşleşmezdi."),

        ("Adım 2", "Hesapları grup planına eşle",
         "Türkiye'deki 100 numaralı Kasa hesabını, Almanya'daki 1600'ü ve "
         "İngiltere'deki 1210'u aynı grup hesabına bağlar. Eşleme kuralları "
         "koda gömülü değil, düzenlenebilir bir tablodadır.",
         "<b>Eşleşmeyen hesap ATILMAZ.</b> Atılırsa tablo yine denk çıkar, "
         "toplamlar makul görünür, ama o hesabın parası yok olur; ne hata mesajı "
         "olur ne denksizlik. Bunun yerine hesap 9999 'askı' hesabına alınır. "
         "Askıda bakiye varken kapanış imzalanamaz. Böylece kayıp bir görünmez "
         "hata değil, çözülmesi gereken açık bir uyarı olur."),

        ("Adım 3", "Para birimlerini çevir ve grup içini sil",
         "Yerel para tutarları sunum para birimine çevrilir. Muhasebe standardı "
         "(IAS 21) bilanço kalemleri için ay sonu (kapanış) kurunu, gelir "
         "tablosu kalemleri için ay ortalamasını şart koşar. Sonra grup "
         "şirketlerinin birbirine yaptığı satışlar elenir.",
         "<b>Ölçülen bir ayrıntı:</b> Mizan yıl başından bugüne biriken (YTD) "
         "bir tutardır. Gelir tablosu kalemini bu biriken hâliyle tek bir kurla "
         "çevirmek, kurun 36,80'den 50,60'a gittiği bir yılda Ocak'ta kazanılan "
         "geliri de Aralık kuruyla çevirir ve ciroyu sistematik olarak "
         "<b>yaklaşık yüzde on iki küçültür.</b> Araç YTD'den her ayın kendi "
         "hareketini türetip o ayın ortalama kuruyla çevirir. Tek şirket "
         "varsa grup içi eliminasyon kendini kapatır; iki tarafı olmayan bir "
         "işlem elenemez."),

        ("Adım 4", f"Hata ve usulsüzlük ara ({test_sayisi} test)",
         f"{test_sayisi} ayrı iç kontrol testi çalışır. Bilanço denk mi, aynı "
         "fiş iki kez mi kaydedilmiş, bir harcama onay limitini aşmış mı, birisi "
         "limiti aşmamak için işlemi parçalara mı bölmüş, tutarlar uydurma mı "
         "görünüyor (Benford yasası), ortaklarla ilişkili işlemler aşırı mı, "
         "özkaynak TTK 376 sınırının altına mı düşmüş.",
         "<b>Bulgu bir suçlama değil, bir sorudur:</b> 'Bu kayıt neden böyle?' "
         "Araç karar vermez; kanıtı gösterir ve sıraya koyar: hangi fiş, hangi "
         "tutar, hangi kullanıcı, hangi tarih. Her testin gerektirdiği veri "
         "bellidir. Yalnızca mizan yüklüyse yevmiye isteyen testler çalışamaz; "
         "bu testler sessizce atlanmaz, <b>tek tek 'çalıştırılamadı' diye "
         "yazılır</b> ve kapanış hükmü 'imzalanabilir' değil KOŞULLU olur."),

        ("Adım 5a", "Finansal oranları ve dikey analizi çıkar",
         "Kontrol testleri 'bir şey yanlış mı' diye sorar; bu adım 'işler nasıl "
         "gidiyor' diye. Likidite (cari oran, asit-test), kaldıraç (borç / "
         "özkaynak), kârlılık (brüt marj, FAVÖK marjı, özkaynak kârlılığı) ve "
         "faaliyet döngüsü (alacak, stok, borç devir günleri) hesaplanır. Dikey "
         "analiz her kalemi aktife ya da hasılata oranlar.",
         "<b>Her oranın payı ve paydası ayrı kolonda yazılır.</b> Bir oranı "
         "sorgulayan kişi, hangi hesaplardan geldiğini görmeden ona güvenemez. "
         "Hesaplanamayan bir oran (payda sıfırsa) 'sıfır' değil '-' yazılır: "
         "ikisi farklı şeydir ve karıştırılırsa yanlış karar verdirir. Yatay "
         "analiz (dönemler arası büyüme) en az iki dönem ister; tek dönemde "
         "üretilmez ve sebebi yazılır."),

        ("Adım 5b", "Sapmayı bileşenlerine ayır",
         "Üçüncü bölümdeki tabloyu üreten adım. Bütçe ile gerçekleşen "
         "arasındaki farkı fiyat, ürün karışımı, hacim ve kur olarak dörde "
         "böler.",
         "<b>Matematiksel garanti:</b> Bu dört parçanın toplamı, toplam farka "
         "birebir eşittir; artık bir bakiye kalmaz. Araç bunu her çalıştırmada "
         "sayısal olarak sınar. Ayrıştırma ürün bazında miktar ve fiyat ister; "
         "bu veri yoksa adım <b>tahmin üretmez</b>, açıkça atlanır ve neden "
         "yapılamadığı yazılır. Miktar bilinmeden fiyat etkisi ile hacim etkisi "
         "birbirinden ayrılamaz; uydurulmuş bir ayrıştırma yanlış yönetim kararı "
         "doğurur."),

        ("Adım 6a", "Kapanış panosunu üret (HTML)",
         "Tek bir HTML dosyası üretir. Çift tıklayınca tarayıcıda açılır, "
         "internet bağlantısı gerektirmez, e-postayla gönderilebilir.",
         "En üstte tek bir cevap durur: <b>kapanış imzalanabilir mi?</b> "
         "Panonun en tepesinde ayrıca bu çıktının hangi dosyalardan üretildiği "
         "(köken) ve hangi şirketlerin kapsam dışı kaldığı yazılır. Kritik bir "
         "bulgu ya da çalıştırılamayan test varsa hüküm KOŞULLU olur."),

        ("Adım 6b", "Excel konsolidasyon paketini üret",
         "On sayfalık, biçimlendirilmiş bir Excel dosyası: kapak, gelir tablosu, "
         "bilanço, oranlar, sapma köprüsü, bulgu listesi, grup içi mutabakat, "
         "hesap eşleme, kur tablosu ve denetim izi.",
         "<b>Neden hâlâ Excel:</b> Amaç Excel'i ortadan kaldırmak değil, Excel'e "
         "giden yoldaki elle yapılan işi (pivot, VLOOKUP, kur çevirme, "
         "mutabakat) kaldırmak. Dosyayı imzalayacak, denetçiye gönderecek ve "
         "üzerine not alacak kişi Excel'de çalışıyor. Fark şu: bu dosya elle "
         "değil, izlenebilir bir hat üzerinde üretiliyor ve her rakam kaynağına "
         "kadar geri sürülebiliyor."),

        ("Adım 6c", "Askıdaki hesaplara model önerisi (isteğe bağlı)",
         "Adım 2'de askıya düşen bir hesap varsa ve eğitilmiş bir makine "
         "öğrenmesi modeli varsa, bu adım her askıdaki hesap için ilk üç grup "
         "kodu önerisini güvenleriyle yazar. Model ya da askıda hesap yoksa adım "
         "kendini atlar.",
         "<b>Model hiçbir tutarı değiştirmez; yalnızca bir öneri listesi "
         "yazar.</b> Öneriyi eşleme tablosuna girmek insan onayına bağlıdır. Bu "
         "katman 8. bölümde ayrıntılı anlatılıyor."),

        ("Adım 7", "Çıktıları ham dosyayla karşılaştır (çapraz doğrulama)",
         "Boru hattının son adımı kasıtlı olarak bir SINAMADIR. Ham Excel "
         "dosyasını, boru hattının kodunu KULLANMADAN sıfırdan yeniden okur ve "
         "çıktılardaki her ana rakamla karşılaştırır: hesap sayısı, toplam borç "
         "ve alacak, mizan denkliği, hasılat, maliyet, askıda kalan tutar, "
         "üretilen dönem ve şirket sayısı.",
         "<b>Neden bu adım var:</b> Aynı hatayı iki kez yapan bir doğrulama, "
         "doğrulama değildir; bu yüzden sınama boru hattından bağımsız yazıldı. "
         "Bir sınama bile tutmazsa boru hattı hata verir. Çökmeden yanlış sonuç "
         "üreten bir hat, çöken bir hattan daha tehlikelidir; bu adım tam onu "
         "yakalamak için var."),
    ]
    for no, baslik, ne, ornek in adimlar:
        A(f'''<div class="adim"><div class="no">{no}</div>
        <h4>{baslik}</h4><div class="ne">{ne}</div>
        <div class="ornek">{ornek}</div></div>''')

    # ================= 5. GÜVENLİK KATMANLARI =================
    A('<h2 class="sayfa">5. Yanlış veriye karşı üç güvenlik katmanı</h2>')
    A('''<p>2. bölümde değindiğim en tehlikeli hata gerçekten yaşandı. Kullanıcı
    kendi mizanını yükledi; dosya adında tanınan bir şirket kodu bulunmadığı
    için satır <b>sessizce atlandı</b>, boru hattı elinde kalan demo veriyle
    devam etti ve baştan sona <b>başka bir şirketin</b> rakamlarını gösteren,
    eksiksiz görünen bir rapor üretti. Tablo denkti, bulgular tutarlıydı;
    bağımsız incelemede yirmi bulgunun yirmisi de yüklenen dosyayla ilgisiz
    çıktı.</p>''')
    A('''<p>Kök neden tek bir hata değil, birbirini gizleyen altı hataydı. O
    olaydan sonra bu hata sınıfını yakalayan üç katman eklendi:</p>''')

    A('''<div class="katman"><h4>Katman 1. Kaynak doğrulaması (boru hattı
    başlamadan)</h4>
    Hat çalışmaya başlamadan önce girdi klasörü taranır. Tanınmayan bir dosya
    ya da demo ile kullanıcı verisinin karışımı varsa <b>boru hattı hiç
    başlamaz</b> ve ne yapılacağını ekrana yazar. Bilerek devam etmek isteyen
    özel bir bayrak kullanır; o zaman bütün çıktılara 'güvenilmez' damgası
    basılır. Geçersiz bir çalıştırmada önceki çıktılar bir arşiv klasörüne
    taşınır, böylece eski bir pano yanlışlıkla güncel sanılmaz.</div>''')

    A('''<div class="katman"><h4>Katman 2. Köken ve kapsam damgası</h4>
    Her çalıştırma, çıktının hangi dosyalardan üretildiğini bir parmak iziyle
    (SHA-256) kaydeder. Pano ve Excel paketi bu listeyi <b>en üstte</b>
    gösterir. Yapılandırmada tanımlı ama verisi yüklenmemiş şirketler 'kapsam
    dışı' olarak, veri yokluğundan çalıştırılamayan testler tek tek listelenir.
    Böylece bir rapora bakan kişi, onun neyi kapsayıp neyi kapsamadığını
    rakamlara güvenmeden önce görebilir.</div>''')

    A('''<div class="katman"><h4>Katman 3. Çapraz doğrulama (boru hattının son
    adımı)</h4>
    4. bölümde anlatılan Adım 7. Ham dosya, boru hattının kodu kullanılmadan
    yeniden okunur ve çıktılardaki her ana rakamla karşılaştırılır. Bir sınama
    bile tutmazsa hat hata verir. Bu, "çıktıdaki her rakamın ham dosyada
    karşılığı var mı?" sorusunu her çalıştırmada otomatik cevaplar.</div>''')

    A('''<div class="vurgu"><b>Buradaki ilke şu:</b> Eksik veya tanınmayan veri
    sessizce atlanmamalı. Bir adım veri yokluğundan yapılamıyorsa çökmeli değil,
    <b>gerekçesiyle atlanmalı ve çıktıda görünmeli.</b> Bir kapanış aracında
    "bilmiyorum" demek, yanlış bir sayı söylemekten iyidir.</div>''')

    # ================= 6. KONTROL TESTLERİ =================
    A(f'<h2 class="sayfa">6. {test_sayisi} kontrol testi neye bakar</h2>')
    A('''<p>Testler gerektirdikleri veriye göre gruplanır. Elinizde yalnızca
    mizan varsa mizan tabanlı testler çalışır; yevmiye, bütçe ya da grup içi
    mutabakat dosyalarını da yüklerseniz diğerleri devreye girer. Aşağıdaki
    liste testlerin ne aradığını özetliyor.</p>''')

    A('''<h3>Yalnızca mizandan çalışanlar</h3>
    <table class="uzun"><thead><tr><th style="width:30%">Test</th>
    <th>Ne arar</th></tr></thead><tbody>
    <tr><td>Bilanço denkliği</td><td>Borç toplamı alacak toplamına eşit mi;
      değilse mizan eksik ya da bozuk gelmiştir</td></tr>
    <tr><td>Ters bakiye</td><td>Normalde borç bakiye veren bir hesabın alacak
      bakiye vermesi; yanlış kayıt ya da sınıflandırma hatası</td></tr>
    <tr><td>Eşleşmeyen hesap (askı)</td><td>Grup planına bağlanamamış, askıda
      bekleyen ve kapanışı bloke eden hesaplar</td></tr>
    <tr><td>Düzenleyici hesap yönü</td><td>Birikmiş amortisman, karşılık gibi
      (-) hesapların ters yönde bakiye verip varlığı şişirmesi</td></tr>
    <tr><td>Aktif-pasif mutabakatı</td><td>Bilanço ile gelir tablosunun
      birbirini doğrulaması; fark varsa hangisinin yanlış olduğu bilinemez</td></tr>
    <tr><td>7/A maliyet denkliği</td><td>Gider yeri hesaplarının yansıtmayla
      kapanması; kapanmazsa gider ya iki kez sayılmış ya hiç geçmemiştir</td></tr>
    <tr><td>KDV kapanışı</td><td>İndirilecek ve hesaplanan KDV'nin
      mahsuplaşması; mizanın beyanname ile uyumu</td></tr>
    <tr><td>TTK 376 sermaye kaybı</td><td>Özkaynağın, ödenmiş sermayenin yarısı
      ya da üçte ikisinin altına düşmesi (yasal yükümlülük doğar)</td></tr>
    <tr><td>Ortaklarla ilişkili işlem yoğunluğu</td><td>Örtülü sermaye ve
      transfer fiyatlandırması riski; adat faizi gerekebilir</td></tr>
    <tr><td>Kasa bakiyesi makullüğü</td><td>Fiilen kasada olamayacak tutarlar
      (ortağa örtülü aktarım sayılabilir)</td></tr>
    <tr><td>Likidite ve kaldıraç eşikleri</td><td>Cari oran, asit-test ve
      borç / özkaynak oranının eşik dışına çıkması</td></tr>
    <tr><td>Amortisman tutarlılığı</td><td>Amortisman ayrılmaması ya da brüt
      tutarı aşması</td></tr>
    <tr><td>Alacak ve stok devir süresi</td><td>Uzayan tahsilat (şüpheli alacak)
      ya da uzayan stok (değer düşüklüğü) sinyalleri</td></tr>
    </tbody></table>''')

    A('''<h3>Ek dosya gerektirenler</h3>
    <table><thead><tr><th style="width:30%">Test</th>
    <th style="width:22%">Gereken veri</th><th>Ne arar</th></tr></thead><tbody>
    <tr><td>Mükerrer fiş</td><td>Yevmiye</td><td>Aynı kaydın iki kez
      girilmesi</td></tr>
    <tr><td>Dönem kayması (cut-off)</td><td>Yevmiye</td><td>Bir dönemin
      gelir/giderinin başka döneme yazılması</td></tr>
    <tr><td>Mesai dışı kayıt</td><td>Yevmiye</td><td>Gece ve hafta sonu
      girilen, gözden kaçabilecek kayıtlar</td></tr>
    <tr><td>Yetki limiti aşımı</td><td>Yevmiye</td><td>Onay limitini aşan
      harcama fişleri</td></tr>
    <tr><td>Limit parçalama</td><td>Yevmiye</td><td>Limiti aşmamak için bir
      işlemin parçalara bölünmesi</td></tr>
    <tr><td>Benford ilk rakam testi</td><td>Yevmiye</td><td>Tutarların ilk
      rakam dağılımının doğal olmaması (uydurma tutar sinyali)</td></tr>
    <tr><td>Yuvarlak tutar yoğunluğu</td><td>Yevmiye</td><td>Aşırı yuvarlak
      tutar birikmesi (tahmini/uydurma kayıt)</td></tr>
    <tr><td>Görevler ayrılığı</td><td>Yevmiye</td><td>Tek kullanıcının riskli
      işlemleri baştan sona yalnız yapması</td></tr>
    <tr><td>Grup içi eliminasyon farkı</td><td>Grup içi mutabakat</td><td>İki
      tarafın beyanının tutmaması; konsolide bilançoyu şişirir</td></tr>
    <tr><td>Büyük bütçe sapması</td><td>Bütçe</td><td>Bütçeden aşırı sapan
      kalemler</td></tr>
    </tbody></table>''')

    A('''<div class="uyari"><b>Çalışamayan test gizlenmez.</b> Yalnızca mizan
    yüklüyken yevmiye isteyen testler "çalıştırılamadı" olarak raporlanır ve
    kapanış hükmü KOŞULLU olur. "Bulgu çıkmadı" ile "test çalışmadı" bir kapanış
    aracında asla aynı şey değildir.</div>''')

    # ================= 7. FP&A =================
    A('<h2 class="sayfa">7. Sapma köprüsü nasıl kuruluyor</h2>')
    A('''<p>3. bölümdeki tabloyu üreten mantık. "Bütçeden neden saptık" sorusu
    tek bir sayıyla cevaplanamaz; dört ayrı sebebin toplamıdır ve her birinin
    sorumlusu farklıdır:</p>''')
    A('''<table>
    <tr><th style="width:20%">Bileşen</th><th>Ne ölçer</th>
      <th style="width:22%">Sorumlu</th></tr>
    <tr><td><b>Fiyat</b></td><td>Aynı üründen, aynı adette, bütçelenenden farklı
      fiyata satmanın etkisi</td><td>Fiyatlama</td></tr>
    <tr><td><b>Karışım</b></td><td>Ucuz/pahalı ürünler arasındaki satış
      dağılımının değişmesi</td><td>Satış / ürün yönetimi</td></tr>
    <tr><td><b>Hacim</b></td><td>Toplam satılan adedin değişmesi</td>
      <td>Satış / talep</td></tr>
    <tr><td><b>Kur</b></td><td>Yerel para tutarını sunum para birimine çevirmenin
      etkisi</td><td>Hazine (kur riski)</td></tr>
    </table>''')
    A('''<div class="vurgu"><b>Kilit özellik:</b> Fiyat + karışım + hacim
    toplamı, yerel para cinsinden sapmaya <b>birebir eşittir</b> (artık terim
    sıfır). Kur etkisi ise yalnızca çeviriden gelir. Bu eşitlik her çalıştırmada
    sayısal olarak sınanır; tutmayan bir tablo yayımlanmaz. Böylece "hedefin
    altında kaldık" cümlesi, dört ayrı aksiyona ayrışır: fiyatlamayla mı, satış
    ekibiyle mi, yoksa hazineyle mi konuşulmalı.</div>''')

    # ================= 8. AI Mİ PYTHON MU =================
    A('<h2 class="sayfa">8. Ayrıştırmayı yapay zekâ mı yapıyor, Python mu?</h2>')
    A('''<p>Projenin en sık sorulan ve en önemli sorusu. Kısa cevap:</p>''')
    A('''<div class="vurgu" style="text-align:center;font-size:12pt">
    <b>Bütün hesaplamayı Python yapıyor.</b><br>
    Yapay zekâ tek bir sayı bile üretmiyor.</div>''')

    A('<h3>Peki API anahtarı var mı?</h3>')
    A('''<p><b>Evet, var.</b> Projede isteğe bağlı bir yapay zekâ katmanı
    bulunuyor ve Claude API kullanıyor. Anahtar, bilgisayarda <code>.env</code>
    adlı bir dosyada duruyor; kodun içinde değil ve depoya hiç girmiyor. Anahtar
    olmadan da araç <b>eksiksiz çalışıyor</b>, yalnızca yorum metinleri
    üretilmiyor.</p>''')

    A('<h3>O zaman iki "akıllı" katman ne yapıyor?</h3>')
    A('''<p>Aracın öğrenen ya da yorumlayan iki katmanı var: yukarıdaki yapay
    zekâ (dil modeli) katmanı ve 9. bölümdeki makine öğrenmesi katmanı. İkisinin
    de ortak kuralı aynı: <b>sayı üretmezler.</b> Aşağıdaki tablo işi kimin
    yaptığını gösteriyor.</p>''')
    A('''<table>
    <tr><th style="width:38%">İş</th><th class="ort" style="width:18%">Kim</th>
      <th>Açıklama</th></tr>
    <tr><td>Dosyaları okumak, sayıları ayrıştırmak</td>
      <td class="ort"><b>Python</b></td><td>Biçim kuralları kodda yazılı</td></tr>
    <tr><td>Kur çevrimi, konsolidasyon</td><td class="ort"><b>Python</b></td>
      <td>IAS 21 kuralları koda gömülü</td></tr>
    <tr><td>Kontrol testleri, oranlar</td><td class="ort"><b>Python</b></td>
      <td>İstatistik ve karşılaştırma; Benford bile saf matematik</td></tr>
    <tr><td><b>Fiyat / karışım / hacim / kur ayrıştırması</b></td>
      <td class="ort"><b>Python</b></td>
      <td><b>Formüller kodda; toplamları her çalıştırmada sınanıyor</b></td></tr>
    <tr><td>Konsolide tablolar, Excel, pano, çapraz doğrulama</td>
      <td class="ort"><b>Python</b></td><td>Tamamı</td></tr>
    <tr class="mor"><td>Bulunan tabloyu finans diline çevirmek</td>
      <td class="ort">Yapay zekâ</td><td>Hazır sayıları okuyup yorum yazar</td></tr>
    <tr class="mor"><td>Bulguları aciliyete göre sıralamak</td>
      <td class="ort">Yapay zekâ</td><td>Hangisi önce çözülmeli, ne sorulmalı</td></tr>
    <tr class="mor"><td>Eşleşmeyen hesaba karşılık önermek</td>
      <td class="ort">Makine öğr.</td>
      <td>Hesabın <b>adına</b> bakar, sayıya değil; öneri insana sorulur</td></tr>
    </table>''')

    A('''<p>Mor satırlardaki işlerin ortak yanı: hiçbirinde <b>sayı
    üretilmiyor.</b> Yapay zekâ, Python'un hesapladığı rakamları hazır alıp
    onlar hakkında cümle kuruyor; makine öğrenmesi modeli ise yalnızca bir
    metin (hesap adı) alıp bir kategori (grup kodu) öneriyor.</p>''')

    A('<h3>Bunun kanıtı</h3>')
    A('''<p>İddia edilmesi kolay, kanıtlanması gerekir. Araçta iki kapatma
    bayrağı var: yapay zekâ katmanını ve öğrenme katmanını ayrı ayrı
    kapatabiliyorsunuz.</p>''')
    A('<pre>py src/boru.py --zeka-kapali\npy araclar/ogrenme_notr_mu.py</pre>')
    A('''<p>İkinci komut boru hattını önce öğrenme katmanı açık, sonra kapalı
    çalıştırır ve tutar taşıyan bütün çıktı dosyalarının parmak izini
    karşılaştırır. Dosyanın içeriği tek bir karakter değişse parmak izi tümüyle
    başkalaşır. Ölçülen sonuç: <b>bütün dosyalar bit bit aynı.</b></p>''')
    A('''<div class="vurgu"><b>İki katman da kapatıldığında kaybolan tek şey
    yorum ve öneri metinleridir; rakamların hiçbiri değişmez,</b> çünkü onları
    zaten ne yapay zekâ ne de model üretiyordu. Bu bir tercih değil,
    zorunluluktu: bir denetçi "bu rakam nereden geliyor" dediğinde cevabın "bir
    model öyle dedi" olması kabul edilemez; "şu formül, şu veriden, şu kurla"
    olması gerekir. Her yapay zekâ çağrısı ayrıca kayıt altına alınır: hangi
    görev, hangi model, kaç kelime, kaç dolar. Tam bir kapanış çevriminde yapay
    zekâ katmanı yaklaşık yarım dolar harcar; aynı soru ikinci kez sorulursa
    cevap önbellekten gelir ve ücret oluşmaz.</div>''')

    # ================= 9. MAKİNE ÖĞRENMESİ =================
    A('<h2 class="sayfa">9. Makine öğrenmesi katmanı</h2>')
    A('''<p>Araç, eşleşmeyen hesaplar için (Adım 6c) bir makine öğrenmesi modeli
    kullanabilir. Model, hesabın <b>adından</b> ve kodunun ilk iki hanesinden
    grup kodunu tahmin eder. Örneğin "ALICILAR - YURTİÇİ" adını hiç görmemiş
    olsa bile, "Ticari alacaklar" grubunu önerir. Eğitim verisi, projenin kendi
    eşleme tablosudur ve her onaylanan eşlemeyle büyür.</p>''')

    A('''<div class="uyari"><b>Değişmeyen kural:</b> Model hiçbir tutarı
    değiştirmez. Sadece bir <b>öneri</b> üretir; o öneriyi eşleme tablosuna
    girmek insan onayına bağlıdır. 8. bölümdeki nötrlük sınaması bu katman için
    de geçerlidir.</div>''')

    A('<h3>Modelin dürüstlüğü nasıl korunuyor</h3>')
    A('''<p>Bir modelin "işe yarıyor" demesi yetmez; ne kadar yaradığı ve
    <b>nerede yaramadığı</b> ölçülmelidir. Bu araçta üç kural var:</p>''')
    A('''<ul>
    <li><b>Taban çizgiyi geçemeyen model kullanılmaz.</b> "Her zaman en sık
    grubu söyle" diyen aptal bir tahminin ne kadar üstüne çıktığı ölçülür. Model
    bunu geçmiyorsa eklediği karmaşıklık bedava değildir ve çıkarılır.</li>
    <li><b>Sınır açıkça ölçülür.</b> Model, eğitildiği hesap planı ailesinin
    dışında (örneğin Türkçe adlarla eğitilip Almanca bir planla sınandığında)
    neredeyse hiçbir şey bilmiyor. Bu bir kusur olarak gizlenmez; "bu model
    yeni bir hesap planında güvenilmez" diye <b>yazılır.</b></li>
    <li><b>Sızıntıya karşı önlem.</b> Modelin sınav sorularını önceden görmesi
    (test verisinin eğitime karışması) skoru sahte biçimde şişirir. Değerlendirme
    bunu engelleyecek şekilde kurulmuştur ve bu, projenin dayandığı ayrı bir
    Türkçe ölçüm kütüphanesiyle sınanır.</li>
    </ul>''')
    A('''<p class="kucuk">Gerçek bir sınamada, eşleme tablosundan altı hesap
    geçici olarak çıkarıldı ve boru hattı çalıştırıldı; beş hesap askıya düştü
    ve modelin birinci önerisi beşinde de doğru çıktı. Yine de öneriler, yüksek
    başarıda bile insan onayına bağlıdır.</p>''')

    # ================= 10. DOĞRULUK =================
    A('<h2 class="sayfa">10. Doğruluğu nasıl kanıtlanıyor</h2>')
    A('''<p>Bir aracın "hataları buluyorum" demesi yetmez; bunu ölçmek gerekir.
    İki ayrı kanıt var.</p>''')

    A('''<h3>Kasıtlı tuzaklar</h3>
    <p>Demo verisi üretildikten sonra içine <b>on dört kasıtlı hata</b>
    yerleştirilir ve bunların listesi ayrı bir dosyaya yazılır.
    <b>Aracın kendisi o listeyi hiç görmez.</b> Sonra bakılır: kaç tanesini
    buldu? Sonuç <b>on dörtte on dört.</b> Bu sayı, yeni bir test eklendiğinde
    ya da bir eşik değiştirildiğinde tekrar ölçülür; düşerse bir şey bozulmuş
    demektir. Tuzaklar mükerrer fiş, dönem kayması, eliminasyon farkı,
    eşleşmeyen hesap, mesai dışı kayıt, yetki aşımı, limit parçalama, uydurma
    tutar, bilanço denksizliği, eksik dönem, ters bakiye, görevler ayrılığı ve
    iki ayrı sayı/tarih biçimi tuzağını kapsar.</p>''')

    A('''<h3>Ham dosyayla çapraz doğrulama</h3>
    <p>Her çalıştırmada, boru hattının son adımı ham dosyayı bağımsız okuyup
    çıktılarla karşılaştırır (5. bölüm, Katman 3). Gerçek bir mizanda bu
    sınamaların hepsi geçti: hesap sayısı, toplam borç ve alacak, mizan
    denkliği, hasılat, maliyet, faaliyet gideri, askıda kalan tutar ve üretilen
    dönem/şirket sayısı, ham dosyayla bire bir tuttu.</p>''')

    A('''<div class="vurgu"><b>İki kanıtın farkı önemli:</b> Tuzak testi "araç
    bir hatayı yakalıyor mu" diye sorar. Çapraz doğrulama "araç doğru dosyadan
    mı üretiyor" diye sorar. Bir kapanış aracının ikisine de 'evet'
    diyebilmesi gerekir.</div>''')

    # ================= 11. KİMLER + LİSANS =================
    A('<h2>11. Kimler kullanabilir</h2>')
    A('''<p>Araç bir demo veriyle geliyor ama ona bağlı değil. Kendi
    dosyalarınızı bağlamak için <b>kod değil, ayar dosyaları</b> değişir: şirket
    listesi, hesap eşleme tablosu, kur tablosu, kontrol eşikleri. Tanınmayan bir
    mizan için tek komutluk bir araç, dosyanın yapısını ölçüp kaydı kendisi
    üretir.</p>''')
    A('''<table>
    <tr><th style="width:36%">Kim</th><th>Ne için</th></tr>
    <tr><td>Birden fazla şirketi olan gruplar</td>
      <td>Aylık konsolidasyon ve kapanış paketi</td></tr>
    <tr><td>Mali müşavirler, denetim büroları</td>
      <td>Müşteri kayıtlarında hızlı kontrol taraması</td></tr>
    <tr><td>İç denetim birimleri</td>
      <td>Kontrol testlerinin düzenli çalıştırılması</td></tr>
    <tr><td>Finansal planlama (FP&amp;A) ekipleri</td>
      <td>Oran analizi ve bütçe sapmasının ayrıştırılması</td></tr>
    <tr><td>Öğrenciler ve araştırmacılar</td>
      <td>Konsolidasyonun kodda nasıl çalıştığını görmek</td></tr>
    </table>''')
    A('''<div class="uyari"><b>Lisans:</b> Kişisel kullanım, öğrenme, akademik
    araştırma, eğitim kurumları, kamu ve hayır kurumları için ücretsiz. Bir
    işletmede ya da işletme için kullanım (kendi kapanışınızı yapmak dahil)
    ayrı ve ücretli bir lisans gerektirir. Koşullar depodaki
    <code>COMMERCIAL.md</code> dosyasında.</div>''')

    # ================= 12. NASIL BAŞLATILIR =================
    A('<h2>12. Nasıl başlatılır</h2>')
    A('''<p>En kolay yol, tarayıcıda açılan paneli kullanmak. Proje klasöründe:</p>''')
    A('<pre>py src/panel.py</pre>')
    A('''<p>Windows'ta <code>PANEL.bat</code> dosyasına çift tıklamak da aynı
    işi yapar. Panelde yapılabilecekler:</p>''')
    A('''<ul>
    <li>Tüm hattı ya da tek bir adımı çalıştırmak</li>
    <li>Çalışırken çıktıyı canlı izlemek</li>
    <li><b>Kendi Excel dosyalarını sürükleyip bırakmak</b></li>
    <li>Üretilen pano, Excel ve rapor dosyalarını açmak veya indirmek</li>
    </ul>''')
    A('''<p>Panel yalnızca kendi bilgisayarınızda çalışır, ağdan erişilemez.
    Terminali tercih edenler için, demo veriyle sıfırdan bir kapanış paketi
    üreten tek komut:</p>''')
    A('<pre>py src/boru.py --veri-uret</pre>')

    A(f'''<p class="kucuk" style="margin-top:18pt">Bu belge
    <code>py araclar/anlatim_uret.py</code> ile üretildi. Adım listesi boru
    hattının kendisinden, test sayısı yapılandırmadan okundu; anlatım
    kavramsaldır ve herhangi bir çalıştırmaya bağlı değildir. Canlı bir
    çalıştırmanın gerçek rakamları panoya ve Excel paketine gömülür.
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

    if "--html-birak" not in sys.argv:
        gecici.unlink()
    boyut = pdf.stat().st_size / 1024
    g.iyi(f"Tanıtım belgesi üretildi: {pdf}  ({boyut:.0f} KB)")
    g.iz("anlatim_uretildi", dosya=str(pdf), boyut_kb=round(boyut))
    g.bitir({"boyut_kb": round(boyut)})


if __name__ == "__main__":
    main()
