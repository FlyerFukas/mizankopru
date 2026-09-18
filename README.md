# MizanKöprü

**Çok şirketli, çok para birimli ay sonu konsolidasyon ve iç kontrol motoru.**

Dağınık ERP çıktılarını tek şemaya indirir, grup hesap planına eşler, IAS 21'e göre
çevirir, 14 iç kontrol testinden geçirir ve bütçe sapmasını **fiyat / karışım /
hacim / kur** bileşenlerine ayırır. Çıktı: tek dosyalık HTML kapanış panosu ve
formatlı Excel konsolidasyon paketi.

> *A month-end consolidation and internal-control engine for multi-entity,
> multi-currency groups. Normalizes messy ERP exports, maps local charts of
> accounts to a group IFRS chart, applies IAS 21 translation, runs 14 internal
> control tests, and decomposes budget variance into price / mix / volume / FX.
> Documentation is in Turkish.*

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
| Ciro (TRY, yerel para) | **+%2,1** — bütçenin üstünde |
| Ciro (EUR, sunum para birimi) | **−%11,2** — bütçenin altında |

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
tamamı kurdan geliyor — bu bir performans sorunu değil, çeviri sorunudur.
Ayrıştırma yapılmadan bu iki şey birbirinden ayrılamaz.

---

## Boru hattı

```
veri/girdi/   41 dağınık dosya — farklı biçim, kolon adı, tarih ve sayı formatı
     │
     ├─[1] topla.py    tek şemaya normalize et           44.000 satır
     ├─[2] esle.py     yerel hesap → grup hesap planı    eşleşmeyen = askıya
     ├─[3] cevir.py    IAS 21 çevrim + eliminasyon + NCI
     ├─[4] kontrol.py  14 iç kontrol testi               130 bulgu
     ├─[5] sapma.py    fiyat/karışım/hacim/kur ayrıştırması
     └─[6] pano.py + excel.py
             cikti/pano.html · cikti/konsolidasyon_paketi.xlsx
```

Tek komutla:

```bash
py src/boru.py --veri-uret
```

Her adım tek başına da çalışır (`py src/topla.py`), durum `veri/ara/` altında
taşınır. Bir adım hata verirse boru hattı **durur** — yanlış veriyle devam etmek
hatayı görünmez kılar.

---

## Kurulum

```bash
pip install pandas numpy openpyxl xlsxwriter pyyaml anthropic
```

Python 3.11+. Yapay zekâ katmanı isteğe bağlıdır:

```bash
cp .env.ornek .env     # içine ANTHROPIC_API_KEY=... yaz
```

Anahtar yoksa motor **tam çalışır**, sadece yorum metinleri üretilmez.
Ürettiği rakamların hiçbiri değişmez.

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
| K02 | Mükerrer fiş | Aynı tutar + hesap + tarih penceresi — çift ödeme |
| K03 | Dönem kayması | Belge tarihi dönem dışında; dönemsellik ihlali |
| K04 | Mesai dışı kayıt | Hafta sonu / gece girilmiş yüksek tutarlı fiş |
| K05 | Yetki limiti aşımı | Onay limitini aşan tek fiş |
| K06 | Limit parçalama | Aynı gün/kullanıcı/hesapta limitin hemen altında birden çok fiş |
| K07 | Benford | İlk rakam dağılımının ki-kare sapması — uydurma tutar |
| K08 | Eliminasyon farkı | A'nın alacağı ile B'nin borcunun tutmaması |
| K09 | Eşleşmeyen hesap | Grup planında karşılığı olmayan yerel hesap |
| K10 | Eksik dönem | Bir şirketin bir dönemi hiç gelmemiş |
| K11 | Ters bakiye | Hesabın normal yönünün tersine hareket |
| K12 | Yuvarlak tutar | Belirli bir hesapta aşırı yuvarlak tutar yoğunluğu |
| K13 | Görevler ayrılığı | Kayıtların çoğunun tek kullanıcıda toplanması |
| K14 | Büyük bütçe sapması | Hem oransal hem mutlak eşiği aşan sapma |

**Bulgu ≠ hata.** Her bulgu bir iddia değil bir sorudur: *"bu kayıt neden böyle?"*.
Motor karar vermez, kanıtı gösterir ve sıraya koyar — hangi fiş, hangi tutar,
hangi kullanıcı. Karar imzayı atacak olanındır.

### Doğrulama: tuzak avı

Demo veri üreteci, üretim bittikten sonra **14 kasıtlı hata** enjekte eder ve
hepsini `veri/ornek/TUZAK_CEVAP_ANAHTARI.json` dosyasına yazar. Boru hattı bu
dosyayı okumaz. Son durum:

**14/14 tuzak yakalandı** — 130 bulgu (kritik 20, yüksek 49, orta 60, düşük 1).

Bu, motorun kendi kendini sınaması için kurulmuş bir çerçevedir: yeni bir test
eklendiğinde ya da bir eşik değiştiğinde skorun düşüp düşmediği ölçülebilir.

---

## Yapay zekâ katmanı

Dört görev: eşleşmeyen hesaba grup hesabı önerisi, kontrol bulgularının aciliyet
triyajı, sapma köprüsünün finans diline çevrilmesi, yönetici özeti.

**Çekirdek kısıt — LLM hiçbir sayıyı üretmez.** Motor sayıyı üretir; LLM yalnızca
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
*"bu yorumu kim yazdı"* sorusunun cevabı dosyada durur. Önbellek açıktır — aynı
istem ikinci kez API'ye gitmez.

Model: `claude-opus-5` (yapılandırmadan değiştirilebilir). Tam bir kapanış
çevriminin AI maliyeti ~$0,50.

---

## Neden bu tasarım

Kodun içine gömülü üç karar, projenin çoğunu açıklar:

**1. Eşleşmeyen satır atılmaz, askıya alınır.** Eşleşmeyen bir hesabın satırı
düşürülürse konsolide tablo yine denk çıkar, toplamlar makul görünür, ama o
hesabın tutarı yok olur — ne hata mesajı vardır ne denksizlik. Askı hesabı (9999)
tutarın kaybolmasını engeller ve kapanış imzalanmadan çözülmesi gereken bir
bulguya dönüştürür.

**2. Gelir tablosu aylık çevrilir, YTD değil.** Mizan kümülatiftir. YTD hasılatı
tek kurla çevirmek, EUR/TRY'nin 36,80'den 50,60'a gittiği bir yılda Ocak'ta
kazanılan geliri de Aralık kuruyla çevirir. Motor YTD'den aylık hareketi türetip
her ayı kendi ortalama kuruyla çevirir. Ölçülen fark TR şirketlerinde **%12** —
tek kurla çevirmek ciroyu sistematik olarak küçültür.

**3. Çevrim farkı ile veri hatası ayrıştırılır.** Çevrimden sonra bilanço denk
gelmez; fark özkaynağa yazılır. Ama yerel mizan zaten denk değilse o denksizlik de
aynı yere düşer ve bir **veri hatası "kur çevrim farkı" adı altında özkaynağa
gömülüp kaybolur.** Motor ikisini ayırır: yerel denksizlik × kapanış kuru = veri
hatası, kalanı saf çevrim farkı.

---

## Excel'i öldürmüyor, üretiyor

Bu projenin amacı Excel'i ortadan kaldırmak değil. Amaç, Excel'e giden yoldaki
**elle yapılan işi** — pivot, VLOOKUP, kur çevirme, mutabakat — ortadan
kaldırmak. Kapanış paketi yine `.xlsx` olarak çıkar, çünkü onu imzalayacak,
denetçiye gönderecek ve üzerine not alacak olan kişi orada çalışır.

Fark: bu dosya elle değil, izlenebilir bir boru hattıyla üretilir ve her rakam
kaynağına kadar geri sürülebilir.

`cikti/konsolidasyon_paketi.xlsx` — 9 sayfa: kapak ve kapanış durumu, gelir
tablosu, bilanço, sapma köprüsü, kontrol bulguları, grup içi mutabakat, hesap
eşleme, kur ve çevrim farkı, denetim izi.

---

## Yol haritası

- [ ] **IAS 29 enflasyon muhasebesi** — Türkiye 2022'den beri hiperenflasyonist
      ekonomi sayılıyor; parasal/parasal olmayan ayrımı hesap planında zaten var
- [ ] TCMB ve TÜİK verilerini canlı API'den çekme (şu an sabit tablo)
- [ ] Rolling forecast ve senaryo motoru ("kur %10 daha artarsa?")
- [ ] VUK ↔ IFRS köprüsü ve ertelenmiş vergi

---

## Teknik notlar

- Python 3.14 · pandas 3.0 · openpyxl · xlsxwriter · PyYAML · anthropic
- Harici servis bağımlılığı yok (AI katmanı hariç ve o da isteğe bağlı)
- Windows'ta konsol UTF-8'e zorlanır (`gunluk.py`); cp1254 Türkçe çıktıyı bozuyor
- Demo veri sabit tohumla (`TOHUM = 42`) üretilir — tekrar üretilebilir
- `veri/girdi/`, `veri/ara/`, `cikti/` ve `gunluk/` depoda tutulmaz; hepsi
  `py src/boru.py --veri-uret` ile yeniden üretilir

## Lisans

[MIT](LICENSE) · Güvenlik bildirimi için [SECURITY.md](SECURITY.md)
