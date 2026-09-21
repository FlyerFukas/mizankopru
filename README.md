# MizanKöprü

**Çok şirketli, çok para birimli ay sonu konsolidasyon ve iç kontrol motoru.**

Dağınık ERP çıktılarını tek şemaya indirir, grup hesap planına eşler, IAS 21'e göre
çevirir, 24 iç kontrol testinden geçirir ve bütçe sapmasını **fiyat / karışım /
hacim / kur** bileşenlerine ayırır. Çıktı: tek dosyalık HTML kapanış panosu ve
formatlı Excel konsolidasyon paketi.

> *A month-end consolidation and internal-control engine for multi-entity,
> multi-currency groups. Normalizes messy ERP exports, maps local charts of
> accounts to a group IFRS chart, applies IAS 21 translation, runs 14 internal
> control tests, and decomposes budget variance into price / mix / volume / FX.
> Documentation is in Turkish.*

> ### ⚖️ Lisans: önce bunu okuyun
>
> Kaynak kodu açıktır, **ticari kullanım serbest değildir.**
>
> | Kullanım | Durum |
> |---|---|
> | Kişisel, öğrenme, hobi, araştırma | **ücretsiz** |
> | Üniversite, kamu, hayır kurumu | **ücretsiz** |
> | Bir işletmede ya da işletme için | **ayrı, ücretli lisans gerekir** |
> | Müşteriye hizmet üretirken, ürüne gömerek, yeniden satarak | **ayrı, ücretli lisans gerekir** |
>
> [PolyForm Noncommercial 1.0.0](LICENSE) + ticari lisans. Koşullar, kapsam ve
> iletişim: **[COMMERCIAL.md](COMMERCIAL.md)**
>
> *Source-available, not open source. Commercial use requires a paid license.
> See [COMMERCIAL.md](COMMERCIAL.md).*

---

## Çözdüğü problem

Bir grup şirketinde ay sonu kapanışı şöyle geçer: dört ayrı ülkeden dört ayrı
biçimde mizan gelir, biri Excel'de virgüllü, biri noktalı, biri 12 sekmeli, biri
CSV. Hesap planları farklıdır. Kur çevrimi elle yapılır. Grup içi alım-satım elle
mutabakat edilir. Sonra biri "hedefin altında kaldık" der ve kimse **neden**
olduğunu söyleyemez.

Bu motor o işi 42 saniyede yapar ve her rakamın kaynağını kayıt altında tutar.

### Somut bir örnek

Demo veride TR01 şirketi için 2025 yılı üç farklı şekilde okunur:

| Ölçüt | Değişim |
|---|---|
| Satılan adet | **−%12,1** |
| Ciro (TRY, yerel para) | **+%2,1**, bütçenin üstünde |
| Ciro (EUR, sunum para birimi) | **−%11,2**, bütçenin altında |

Türkiye'deki müdür "TL'de bütçeyi tutturduk" der. Grup merkezi "EUR'da %11
altındasınız" der. **İkisi de doğrudur.** Motorun işi kimin haklı olduğunu değil,
*neyin olduğunu* göstermektir:

```
Bütçe (bütçe kuruyla)        77.035.451 EUR
  + Fiyat etkisi             +6.808.114        enflasyon fiyatları taşıdı
  + Karışım etkisi              −76.906
  + Hacim etkisi             −6.923.589        satılan adet eridi
  = Sabit kurda fiili         76.843.071        bütçeye göre −%0,2
  + Kur etkisi               −5.812.928        EUR/TRY 38,00 → 50,60
  Fiili                       71.030.142        −%7,8
```

Fiyat artışı hacim kaybını neredeyse tam karşılamış. 6 milyon EUR'luk açığın
tamamı kurdan geliyor. Bu bir performans sorunu değil, çeviri sorunudur.
Ayrıştırma yapılmadan bu iki şey birbirinden ayrılamaz.

---

## Boru hattı

```
veri/girdi/   41 dağınık dosya: farklı biçim, kolon adı, tarih ve sayı formatı
     │        (panelden sürükle-bırak ile de yüklenebilir)
     │
     ├─[1] topla.py    tek şemaya normalize et           44.000 satır
     ├─[2] esle.py     yerel hesap → grup hesap planı    eşleşmeyen = askıya
     ├─[3] cevir.py    IAS 21 çevrim + eliminasyon + NCI
     ├─[4] kontrol.py  24 iç kontrol testi               130 bulgu
     ├─[5a] oran.py   18 finansal oran + dikey analiz
     ├─[6c] esleme_modeli.py --oner   askıdaki hesaplara model önerisi
     └─[7] capraz_dogrula.py   ham dosya ↔ çıktı, 12 sınama
     ├─[5] sapma.py    fiyat/karışım/hacim/kur ayrıştırması
     └─[6] pano.py + excel.py
             cikti/pano.html · cikti/konsolidasyon_paketi.xlsx
```

## Panel (önerilen kullanım)

```bash
py src/panel.py
```

Tarayıcıda açılan yerel bir arayüz. Terminale hiç dönmeden:

- Her adımı tek tek ya da tüm boru hattını çalıştırma
- **Canlı çıktı akışı**: hangi adım nerede, ne kadar sürdü, kaç uyarı çıktı
- **Kendi Excel dosyalarınızı sürükle-bırak ile yükleme** (`.xlsx`, `.xls`, `.csv`)
- Üretilen çıktıları açma ve indirme
- Yapılandırma, anahtar ve bulgu durumunun tek bakışta görünmesi

Panel yalnızca `127.0.0.1` üzerinde çalışır, ağdan erişilemez. Windows'ta
`PANEL.bat` dosyasına çift tıklamak da yeterlidir.

## Belgeler

| Belge | Kime |
|---|---|
| Bu README | Teknik okuyucu, hızlı bakış |
| `py araclar/anlatim_uret.py` → **Nasıl Çalışır** (11 sayfa PDF) | Projeyi hiç bilmeyen biri. Jargon açıklanır, "yapay zekâ mı yapıyor Python mu" sorusu kanıtla cevaplanır |
| `py araclar/rapor_uret.py` → **Proje Raporu** (12 sayfa PDF) | Mimari, ölçümler, tasarım kararları |
| [HANDOFF.md](HANDOFF.md) | Geliştirme günlüğü: her kararın gerekçesi ve yaşanmış tuzaklar |

## Komut satırı

Tek komutla:

```bash
py src/boru.py --veri-uret
```

Her adım tek başına da çalışır (`py src/topla.py`), durum `veri/ara/` altında
taşınır. Bir adım hata verirse boru hattı **durur**. Yanlış veriyle devam etmek
hatayı görünmez kılar.

---

## Kurulum

```bash
pip install pandas numpy openpyxl xlsxwriter pyyaml anthropic xlrd
```

Yapılandırmayı örnekten oluşturun. `sirketler.yaml` depoya dahil değildir,
çünkü gerçek şirket adlarını ve mizan kolon düzenlerini içerir:

```bash
cp yapilandirma/sirketler.ornek.yaml yapilandirma/sirketler.yaml
```

Python 3.11+. Yapay zekâ katmanı isteğe bağlıdır:

```bash
cp .env.ornek .env     # içine ANTHROPIC_API_KEY=... yaz
```

Anahtar yoksa motor **tam çalışır**, sadece yorum metinleri üretilmez.
Ürettiği rakamların hiçbiri değişmez.

---

## Makine öğrenmesi katmanı

Hesap eşleme önerisi bir sınıflandırıcıyla üretilir: hesap adından ve kodun
ilk iki hanesinden grup kodu tahmin edilir. Eğitim verisi projenin kendi
eşleme tablosudur ve her onaylanan eşlemeyle büyür.

**Model hiçbir tutarı değiştirmez.** Öneri üretir, sıralar, beklenti üretir.
`araclar/ogrenme_notr_mu.py` bunu her seferinde sınar: boru hattı öğrenme
katmanı açık ve kapalı iki kez çalıştırılır, tutar taşıyan sekiz dosyanın
özeti karşılaştırılır. Hepsi birebir aynı olmalıdır.

Ölçülen başarı ve **sınırı**, hangi sistemin neden seçildiği ve sıradakiler:
[ENTEGRASYON-ML.md](ENTEGRASYON-ML.md).

```bash
py -m pip install scikit-learn
py -m pip install -e ../gozetimli-ogrenme   # değerlendirme kütüphanesi
py src/esleme_modeli.py                     # eğit ve ölç
py src/esleme_modeli.py --oner              # askıdaki hesaplara öneri
py araclar/ogrenme_notr_mu.py               # katman nötr mü?
```

Bu katman isteğe bağlıdır: kütüphaneler kurulu değilse boru hattı tam
çalışır, yalnızca öneri üretilmez.

---

## Yanlış veriyle çalışmaya karşı üç katman

Bir konsolidasyon motorunun en tehlikeli hatası çökmek değil, **yanlış
veriden eksiksiz görünen bir rapor üretmektir**. Bu proje o hatayı bir kez
yaptı: kullanıcı kendi mizanını yükledi, dosya adı tanınmadığı için sessizce
atlandı, boru hattı elindeki demo veriyle devam etti ve rapor baştan sona
başka bir şirketin rakamlarını gösterdi. Tablo denkti, bulgular tutarlıydı,
tek sorun verinin kullanıcıya ait olmamasıydı.

Üç katman bunu engeller:

**1. Kaynak doğrulaması (`src/kaynak.py`).** Boru hattı başlamadan önce
`veri/girdi/` taranır. Tanınmayan bir dosya varsa ya da demo ile kullanıcı
dosyaları karışıksa **boru hattı başlamaz**; ekrana ne yapılacağı yazılır.
Bilerek devam etmek isteyen `--kaynak-zorla` kullanır, o zaman bütün
çıktılara damga basılır. Geçersiz bir çalıştırmada önceki çıktılar
`cikti/bayat/` altına taşınır, böylece eski bir pano güncel sanılmaz.

**2. Köken ve kapsam damgası.** Her çalıştırma `veri/ara/koken.json` yazar:
hangi dosya, kaç KB, SHA-256 parmak izi. Pano ve Excel paketi bu listeyi
en üstte gösterir. Yapılandırmada tanımlı ama verisi yüklenmemiş şirketler
"kapsam dışı" olarak ayrıca yazılır. Veri yokluğundan çalıştırılamayan
kontrol testleri tek tek listelenir ve kapanış hükmü `KOŞULLU` olur:
temiz sonuç ile denetlenmemiş risk birbirine karışmaz.

**3. Çapraz doğrulama (`araclar/capraz_dogrula.py`).** Boru hattının son
adımı bir sınamadır: ham Excel dosyası, boru hattının kodu **kullanılmadan**
sıfırdan yeniden okunur ve çıktılardaki her ana rakamla karşılaştırılır.
Hesap sayısı, toplam borç, toplam alacak, mizan denkliği, hesap bazında
bakiye, hasılat, satışların maliyeti, faaliyet giderleri ve askıda kalan
tutar. Bir sınama bile tutmazsa boru hattı hata verir.

```
Çapraz doğrulama: ham dosya ↔ boru hattı çıktısı
  Sınama                                       Ham dosya      Boru hattı     Sonuç
  Ham dosyadaki ana hesap sayısı               65             65             GEÇTİ
  Toplam borç                                  97.019.382,88  97.019.382,88  GEÇTİ
  Toplam alacak                                97.019.382,88  97.019.382,88  GEÇTİ
  Mizan denkliği (borç − alacak)               0,00           0,00           GEÇTİ
  Bakiyesi boru hattında değişen hesap sayısı  0              0              GEÇTİ
  Hasılat (ham 60x + 61x)                      11.451.042,54  11.451.042,54  GEÇTİ
  Askıda kalan tutar (9999)                    0,00           0,00           GEÇTİ
```

---

## Kendi verinle kullanmak

Motor sentetik demo veriyle gelir ama ona bağlı değildir. Kendi ERP çıktını
bağlamak için **kod değil, yapılandırma** değişir:

| Dosya | Ne tanımlar |
|---|---|
| `yapilandirma/sirketler.yaml` | Tüzel kişilikler, para birimleri, sahiplik oranları, dosya biçimleri, grup içi ilişkiler |
| `yapilandirma/grup_hesap_plani.yaml` | Grup IFRS hesap planı, bilanço/gelir tablosu ayrımı, eliminasyon bayrakları |
| `yapilandirma/hesap_eslesme.csv` | Yerel hesap → grup hesabı köprüsü (Excel'de düzenlenebilir) |
| `yapilandirma/kolon_eslesme.yaml` | ERP kolon adları (`Borç` / `Soll` / `Debit`) → iç şema |
| `yapilandirma/kurlar.csv` | Kapanış, ortalama ve bütçe kurları |
| `yapilandirma/kontroller.yaml` | 14 testin eşikleri, onay limitleri, kapsam kuralları |
| `yapilandirma/zeka.yaml` | Model seçimi, önbellek, hangi AI görevleri açık |

`sema.py` bu dosyalar **arasındaki** tutarlılığı açılışta doğrular: eşleme tablosu
var olmayan bir grup koduna mı işaret ediyor, bir şirketin para birimi kur
tablosunda var mı, onay limitinin para birimi şirketinkiyle aynı mı. Hata boru
hattının ortasında değil, en başta çıkar.

---

## İç kontrol testleri

| Kod | Test | Ne arar |
|---|---|---|
| K01 | Bilanço denkliği | Borç ≠ alacak; mizan eksik ya da tek taraflı kayıt var |
| K02 | Mükerrer fiş | Aynı tutar + hesap + tarih penceresi çift ödeme |
| K03 | Dönem kayması | Belge tarihi dönem dışında; dönemsellik ihlali |
| K04 | Mesai dışı kayıt | Hafta sonu / gece girilmiş yüksek tutarlı fiş |
| K05 | Yetki limiti aşımı | Onay limitini aşan tek fiş |
| K06 | Limit parçalama | Aynı gün/kullanıcı/hesapta limitin hemen altında birden çok fiş |
| K07 | Benford | İlk rakam dağılımının ki-kare sapması uydurma tutar |
| K08 | Eliminasyon farkı | A'nın alacağı ile B'nin borcunun tutmaması |
| K09 | Eşleşmeyen hesap | Grup planında karşılığı olmayan yerel hesap |
| K10 | Eksik dönem | Bir şirketin bir dönemi hiç gelmemiş |
| K11 | Ters bakiye | Hesabın normal yönünün tersine hareket |
| K12 | Yuvarlak tutar | Belirli bir hesapta aşırı yuvarlak tutar yoğunluğu |
| K13 | Görevler ayrılığı | Kayıtların çoğunun tek kullanıcıda toplanması |
| K14 | Büyük bütçe sapması | Hem oransal hem mutlak eşiği aşan sapma |

**Bulgu ≠ hata.** Her bulgu bir iddia değil bir sorudur: *"bu kayıt neden böyle?"*.
Motor karar vermez, kanıtı gösterir ve sıraya koyar hangi fiş, hangi tutar,
hangi kullanıcı. Karar imzayı atacak olanındır.

### Doğrulama: tuzak avı

Demo veri üreteci, üretim bittikten sonra **14 kasıtlı hata** enjekte eder ve
hepsini `veri/ornek/TUZAK_CEVAP_ANAHTARI.json` dosyasına yazar. Boru hattı bu
dosyayı okumaz. Son durum:

**14/14 tuzak yakalandı** 130 bulgu (kritik 20, yüksek 49, orta 60, düşük 1).

Bu, motorun kendi kendini sınaması için kurulmuş bir çerçevedir: yeni bir test
eklendiğinde ya da bir eşik değiştiğinde skorun düşüp düşmediği ölçülebilir.

---

## Yapay zekâ katmanı

Dört görev: eşleşmeyen hesaba grup hesabı önerisi, kontrol bulgularının aciliyet
triyajı, sapma köprüsünün finans diline çevrilmesi, yönetici özeti.

**Çekirdek kısıt LLM hiçbir sayıyı üretmez.** Motor sayıyı üretir; LLM yalnızca
hazır sayıyı yorumlar, önceliklendirir ya da bir *ad* eşlemesi önerir. Bu bir
pazarlama cümlesi değil mimari bir kısıttır:

- Her istem sayıları **hazır** verir ve *"hesaplama yapma, verilen sayıların
  dışına çıkma"* talimatını taşır.
- Katman kapatıldığında (`--zeka-kapali`) boru hattının ürettiği rakamların
  **hepsi aynı kalır**; sadece yorum metinleri kaybolur.
- Öneriler doğrudan uygulanmaz. Hesap eşleme önerisi
  `cikti/hesap_eslesme_onerisi.csv`'ye yazılır, insan onaylayıp yapılandırmaya
  taşır. Önerilen kodun grup planında gerçekten var olduğu ayrıca doğrulanır.

**Denetim izi.** Her çağrı `gunluk/denetim_izi.jsonl`'a görev, model, istem parmak
izi, token sayısı, maliyet ve yanıt parmak iziyle kaydedilir. Regüle bir süreçte
*"bu yorumu kim yazdı"* sorusunun cevabı dosyada durur. Önbellek açıktır aynı
istem ikinci kez API'ye gitmez.

Model: `claude-opus-5` (yapılandırmadan değiştirilebilir). Tam bir kapanış
çevriminin AI maliyeti ~$0,50.

---

## Neden bu tasarım

Kodun içine gömülü üç karar, projenin çoğunu açıklar:

**1. Eşleşmeyen satır atılmaz, askıya alınır.** Eşleşmeyen bir hesabın satırı
düşürülürse konsolide tablo yine denk çıkar, toplamlar makul görünür, ama o
hesabın tutarı yok olur ne hata mesajı vardır ne denksizlik. Askı hesabı (9999)
tutarın kaybolmasını engeller ve kapanış imzalanmadan çözülmesi gereken bir
bulguya dönüştürür.

**2. Gelir tablosu aylık çevrilir, YTD değil.** Mizan kümülatiftir. YTD hasılatı
tek kurla çevirmek, EUR/TRY'nin 36,80'den 50,60'a gittiği bir yılda Ocak'ta
kazanılan geliri de Aralık kuruyla çevirir. Motor YTD'den aylık hareketi türetip
her ayı kendi ortalama kuruyla çevirir. Ölçülen fark TR şirketlerinde **%12**
tek kurla çevirmek ciroyu sistematik olarak küçültür.

**3. Çevrim farkı ile veri hatası ayrıştırılır.** Çevrimden sonra bilanço denk
gelmez; fark özkaynağa yazılır. Ama yerel mizan zaten denk değilse o denksizlik de
aynı yere düşer ve bir **veri hatası "kur çevrim farkı" adı altında özkaynağa
gömülüp kaybolur.** Motor ikisini ayırır: yerel denksizlik × kapanış kuru = veri
hatası, kalanı saf çevrim farkı.

---

## Excel'i öldürmüyor, üretiyor

Bu projenin amacı Excel'i ortadan kaldırmak değil. Amaç, Excel'e giden yoldaki
**elle yapılan işi** pivot, VLOOKUP, kur çevirme, mutabakat ortadan
kaldırmak. Kapanış paketi yine `.xlsx` olarak çıkar, çünkü onu imzalayacak,
denetçiye gönderecek ve üzerine not alacak olan kişi orada çalışır.

Fark: bu dosya elle değil, izlenebilir bir boru hattıyla üretilir ve her rakam
kaynağına kadar geri sürülebilir.

`cikti/konsolidasyon_paketi.xlsx` 9 sayfa: kapak ve kapanış durumu, gelir
tablosu, bilanço, sapma köprüsü, kontrol bulguları, grup içi mutabakat, hesap
eşleme, kur ve çevrim farkı, denetim izi.

---

## Yol haritası

- [ ] **IAS 29 enflasyon muhasebesi** Türkiye 2022'den beri hiperenflasyonist
      ekonomi sayılıyor; parasal/parasal olmayan ayrımı hesap planında zaten var
- [ ] TCMB ve TÜİK verilerini canlı API'den çekme (şu an sabit tablo)
- [ ] Rolling forecast ve senaryo motoru ("kur %10 daha artarsa?")
- [ ] VUK ↔ IFRS köprüsü ve ertelenmiş vergi
- [ ] Panelden yapılandırma düzenleme (şu an dosyadan)

---

## Teknik notlar

- Python 3.14 · pandas 3.0 · openpyxl · xlsxwriter · PyYAML · anthropic
- Harici servis bağımlılığı yok (AI katmanı hariç ve o da isteğe bağlı)
- Windows'ta konsol UTF-8'e zorlanır (`gunluk.py`); cp1254 Türkçe çıktıyı bozuyor
- Demo veri sabit tohumla (`TOHUM = 42`) üretilir tekrar üretilebilir
- `veri/girdi/`, `veri/ara/`, `cikti/` ve `gunluk/` depoda tutulmaz; hepsi
  `py src/boru.py --veri-uret` ile yeniden üretilir

## Lisans

**Çift lisanslı.** Kaynak kodu herkese açıktır; bu, serbestçe
ticarileştirilebileceği anlamına gelmez.

### Ücretsiz [PolyForm Noncommercial 1.0.0](LICENSE)

Kişisel öğrenme ve deneme, hobi projeleri, akademik araştırma, eğitim kurumları,
kamu kurumları, hayır kurumları. İzin almanıza gerek yok. Tek yükümlülük:
yazılımı başkasına verirken lisans metnini ve telif bildirimini birlikte vermek.

### Ücretli ticari lisans gerekir

Bir şirketin operasyonlarında kullanmak (kendi kapanışınızı yapmak dahil),
müşterilere hizmet üretirken kullanmak, bir ürüne/SaaS'a gömmek, yeniden satmak.
Ölçüt niyet değil bağlamdır: kâr amacı güden bir organizasyon içinde ya da onun
için yapılan kullanım ticaridir.

Lisans biçimleri (kurum içi, yıllık abonelik, hizmet sağlayıcı, OEM, kaynak kodu
devri), fiyatlandırma ve iletişim: **[COMMERCIAL.md](COMMERCIAL.md)** ·
Pazarlığa açıktır.

Projenin mimarisi ve kaynak kodu **Furkan Akduman**'a aittir.

Katkıda bulunmak isterseniz [CONTRIBUTING.md](CONTRIBUTING.md) çift lisans
modeli nedeniyle katkılarda telif devri gerekiyor, gerekçesi orada yazılı.

Güvenlik bildirimi için [SECURITY.md](SECURITY.md)
