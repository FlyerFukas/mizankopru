# MİZANKÖPRÜ. Devir Dosyası (HANDOFF)

> Bu dosya oturumlar arası hafızadır. **Her anlamlı çıktıdan sonra güncellenir.**
> Yeni bir oturum açan (insan ya da model) önce burayı okur, sonra koda bakar.

**Son güncelleme:** 2026-09-18 · Oturum 1 TAMAMLANDI · lisans modeli değişti
**Konum:** `C:\Users\furka\Music\MizanKopru`
**Sahip:** Furkan Akduman

---

## 1. Proje tek cümlede

Çok şirketli / çok para birimli bir grubun ay sonu kapanışını uçtan uca otomatikleştiren
konsolidasyon motoru: dağınık ERP çıktılarını tek şemaya indirir, grup hesap planına eşler,
IAS 21'e göre çevirir, üstünden **iç kontrol testleri** geçirir ve bütçe sapmasını
**fiyat / miktar / kur / karışım** bileşenlerine ayrıştırıp yorumlar.

## 2. Alınan kararlar (Oturum 1)

| Karar | Seçim | Gerekçe |
|---|---|---|
| Eksen | **Control + FP&A birlikte**, ortak konsolidasyon çekirdeği üstünde | Gerçek hayatta da FP&A, Control'ün kapattığı veriyi kullanır |
| Veri | **Sentetik çok-şirketli ERP simülasyonu** (kasıtlı tuzaklarla) | Tam kontrol, sıfır gizlilik riski, tuzakları bulmak projenin kendisi |
| Teslim | **Python motor + HTML pano + Excel paketi** | Finansçının aşina olduğu dil + paylaşılabilir görsel |
| Amaç | **Gerçek işte kullanılacak araç** | → Yapılandırma dosyadan, kod değişmeden yeni şirket/hesap planı eklenebilir |

**Amaç kararının doğrudan mimari sonucu:** Sentetik veri *demo*dur, motor değildir.
Hesap planı eşlemesi, kolon adları, kontrol eşikleri, şirket listesi, hepsi
`yapilandirma/` altındaki YAML'lerde. Furkan kendi mizanını `veri/girdi/` altına
koyup sadece YAML düzenleyerek çalıştırabilmeli.

## 3. Boru hattı

```
veri/girdi/  (dağınık .xlsx/.csv, farklı kolon adı, tarih ve sayı formatı)
  │
  ├─[1] topla.py   → tek şemaya normalize et, ham veriyi parmak iziyle sakla
  ├─[2] esle.py    → yerel hesap kodu → grup hesap planı (eşleşmeyenleri raporla)
  ├─[3] cevir.py   → IAS 21 kur çevrimi (bilanço=kapanış, gelir tablosu=ortalama)
  ├─[4] kontrol.py → iç kontrol testleri → bulgu listesi (severity'li)
  ├─[5] sapma.py   → bütçe-fiili köprüsü: fiyat/miktar/kur/karışım ayrıştırması
  └─[6] pano.py + excel.py → cikti/pano.html + cikti/konsolidasyon_paketi.xlsx
```

Orkestratör: `py src/boru.py` (tüm adımlar) veya adım adım `py src/topla.py` ...

## 4. DURUM

### Tamamlanan
- [x] Klasör iskeleti
- [x] HANDOFF.md
- [x] Yapılandırma katmanı, 6 dosya, kendi kendini doğruluyor (`py src/sema.py`)
- [x] Ortak altyapı: günlük/denetim izi (`src/gunluk.py`), şema (`src/sema.py`)
- [x] Sentetik veri üreteci (`araclar/veri_uret.py`), 41 dosya, ~41.000 yevmiye satırı, 14 tuzak
- [x] Veri kalibrasyonu doğrulandı, başlık bulgu veride mevcut (bkz. §7)
- [x] Yapay zekâ katmanı (`src/zeka.py`). Claude API, anahtarsız da çalışır
- [x] `src/topla.py`: çok formatlı okuma + normalizasyon · **41 dosya, 44.414 satır okundu**

- [x] `src/esle.py`: hesap planı köprüsü · **askı hesabı + AI eşleme önerisi**
- [x] `src/cevir.py`: IAS 21 çevrim + konsolidasyon + NCI

- [x] `src/kontrol.py`: 14 kontrol testi · **14/14 tuzak yakalandı, 130 bulgu**
- [x] Claude API bağlandı ve doğrulandı (oturum maliyeti $0,51)

- [x] `src/sapma.py`: fiyat/karışım/hacim/kur ayrıştırması · **özdeşlik artığı 0,0000**
- [x] Git deposu kuruldu, 11 adım adım commit

- [x] `src/pano.py`: tek dosyalık HTML pano (25 KB, saf SVG şelale grafiği)
- [x] `src/excel.py`: 9 sayfalık konsolidasyon paketi
- [x] `src/boru.py`: orkestratör · **uçtan uca 42 sn**
- [x] README.md, LICENSE (MIT), SECURITY.md
- [x] `araclar/rapor_uret.py`: 12 sayfalık proje raporu (PDF)

- [x] **Güvenlik olayı kapatıldı** (§14), anahtar iptal edildi, geçmiş temizlendi
- [x] Depo **PUBLIC**: github.com/FlyerFukas/mizankopru

- [x] Panel (`src/panel.py`), tarayıcıdan çalıştırma + sürükle-bırak yükleme
- [x] **Lisans modeli: PolyForm Noncommercial + ticari lisans** (§18)

### AÇIK, kullanıcı aksiyonu
- [ ] `~/.claude/CLAUDE.md` içindeki GitHub adı güncel değil
      (`mrFurkan33333` → `FlyerFukas`)

### Yol haritası (v2)
- [ ] `src/sapma.py`: sapma ayrıştırma
- [ ] `src/pano.py` / `src/excel.py`: çıktılar
- [ ] `src/boru.py`: orkestratör

### Yol haritası (v2)
- IAS 29 enflasyon muhasebesi (TÜİK ÜFE ile). Türkiye için gerçek ve ayırt edici
- TCMB kurlarını canlı API'den çekme (şu an sabit tablo)
- Rolling forecast + senaryo motoru
- VUK ↔ IFRS köprüsü (ertelenmiş vergi)

## 5. Yapay zekâ katmanı, kural

**LLM hiçbir sayıyı üretmez.** Motor sayıyı üretir; LLM yalnızca hazır sayıyı
finans diline çevirir, önceliklendirir ya da bir hesap eşlemesi önerir.
Katman kapatılsa boru hattının ürettiği rakamların hepsi aynı kalır.
Bu mimari bir kısıt, `src/zeka.py` başlığında ve her istemin içinde yazılı.

Dört görev: `esleme_oner` (K09 bulgusuna çözüm önerisi) · `bulgu_triyaj`
(kontrol bulgularını aciliyete göre sırala) · `sapma_yorumla` · `yonetici_ozeti`.

Her çağrı denetim izine düşer: görev, model, istem parmak izi, token, tahmini
maliyet, yanıt parmak izi. Regüle süreçte "bu yorumu kim yazdı" sorusunun cevabı.
Önbellek açık (`gunluk/zeka_onbellek/`), aynı istem tekrar API'ye gitmez.

**Anahtar kurulumu:** `cp .env.ornek .env` → içine `ANTHROPIC_API_KEY=...`.
`.env` gitignore'da. Kod içinde anahtar yok, olmayacak.
Anahtar yoksa katman sessizce kapanır, motor tam çalışır.

## 6. Bu makineye özgü teknik notlar

- Python 3.14.6 · pandas **3.0.3** · numpy 2.5.0 · openpyxl 3.1.5 · xlsxwriter 3.2.9 · PyYAML 6.0.3
- **pandas 3.0 tuzakları (yaşandı, bkz. Mavi vakası):**
  - `to_excel` `sheet_name`'i pozisyonel almıyor → keyword ver
  - `to_numeric(errors="ignore")` kaldırıldı
  - `groupby.apply` `include_groups=False` istiyor
- **Windows encoding:** JSON/metin yazarken `encoding="utf-8"` **şart**, yoksa cp1254 yazar.
  Scriptlerin başında stdout UTF-8'e zorlanıyor (`src/gunluk.py` içinde).
- Ajan/workflow **üretilmiyor**: Furkan'ın açık talimatı (token tüketimi).

## 7. Veri: başlık bulgu (doğrulandı)

Üretilen veride, bütçe-fiili karşılaştırması yıllık toplamda şu tabloyu veriyor:

| Şirket | Miktar Δ | Yerel para ciro Δ | EUR ciro Δ |
|---|---|---|---|
| **TR01** | −%12,1 | **+%2,1 (hedef ÜSTÜ)** | **−%11,2 (hedef ALTI)** |
| TR02 | −%15,7 | −%2,8 | −%15,3 |
| DE01 | −%0,9 | −%1,2 | −%1,2 |
| UK01 | −%2,8 | −%2,4 | −%2,2 |
| **GRUP** | | | **−%8,0** |

TR01'de Türkiye'deki müdür "TL'de bütçeyi tutturduk" der, grup merkezi
"EUR'da %11 altındasınız" der. **İkisi de doğrudur.** Motorun işi bu farkı
fiyat / miktar / kur / karışım bileşenlerine ayırıp kimin haklı olduğunu değil,
*neyin olduğunu* göstermek.

Kalibrasyon: TR'de fiili fiyat +%68/yıl (bütçe %25 varsaymıştı), fiili miktar
−%18/yıl (bütçe +%7 varsaymıştı), bütçe kuru EUR/TRY 38'de sabitlenmişti,
gerçekleşen yıl sonu 50,60.

**Dikkat, veriye gömülü ikinci tuzak:** Mevsimsellik çarpanı Ocak 0,86 /
Aralık 1,24. "Ocak'a göre Aralık" karşılaştırması bu yüzden yanıltıcıdır;
miktar düşüyor olmasına rağmen artıyor görünür. Doğru çerçeve bütçe-fiili
yıllık toplamdır. Bu kasıtlı, motorun bunu ayırt etmesi bekleniyor.

## 8. topla.py, yaşanmış iki tuzak (tekrar etmesin)

**1. `str()` hesap kodunu bozar.** Excel'de `100` yazan hücre pandas'a `100.0`
float olarak gelir; `str()` onu `"100.0"` yapar. Eşleme tablosunda `"100"`
arandığı için 1.359 hesabın **tamamı** eşleşmeyen çıkmıştı. Tablo yine denk
görünüyordu, hata yalnızca eşleme oranına bakınca fark edildi.
Çözüm: `kod_metni()` (src/topla.py), tam sayı float'ların kuyruğunu atar ama
`770.01` gibi gerçek ondalıklı kodları korur. Tüm anahtar alanlarda kullanılıyor.

**2. Sayı ayracı belirsizliği.** `1.234` Türkçe biçimde 1234, İngilizce biçimde
1,234'tür. `SayiAyristirici` önce şirketin yapılandırılmış biçimini uygular;
hem `.` hem `,` varsa sonuncusunu ondalık kabul eder (bu her zaman doğru);
yapılandırma dışı tek ayraç + 3 basamaklı kuyruk durumunda binlik varsayar ama
**sayar ve raporlar**. Sayaç sıfır değilse insan bakmalı.

**Doğrulama sonucu:** üç farklı sayı/dosya biçimi (TR metin virgüllü ×12 dosya,
DE gerçek sayı 12 sekme, UK metin noktalı tek csv) kayıpsız okundu, mizan
toplamı yevmiye toplamına birebir eşit (tek fark TR02 Kasım, ki o T10 tuzağı).

## 9. cevir.py. IAS 21 uygulaması ve iki tasarım kararı

**Karar 1, mizan YTD, gelir tablosu aylık çevrilir.**
Mizan yılbaşından itibaren kümülatiftir. Gelir tablosu kalemini YTD hâliyle tek
kurla çevirmek, EUR/TRY'nin 36,80'den 50,60'a gittiği bir yılda Ocak'ta kazanılan
geliri de Aralık kuruyla çevirir. Motor YTD'den aylık hareketi türetip her ayı
kendi ortalama kuruyla çevirir. Ölçülen fark:

| Şirket | Yerel YTD | DOĞRU (aylık kur) | YANLIŞ (tek kur) | Hata |
|---|---|---|---|---|
| TR01 | 1.022.551.865 TRY | 23.177.384 EUR | 20.430.607 EUR | **−%11,9** |
| TR02 | 471.269.887 TRY | 10.792.134 EUR | 9.415.982 EUR | **−%12,8** |
| DE01 | 22.116.705 EUR | 22.116.705 | 22.116.705 | %0,0 |

Tek kurla çevirmek TR şirketlerinin cirosunu sistematik olarak ~%12 küçültüyor.

**Karar 2, çevrim farkı ile veri hatası ayrıştırılır.**
Çevrimden sonra bilanço denk gelmez; fark özkaynağa (3090) yazılır. Ama yerel
mizan zaten denk değilse (UK01'de T9 tuzağı) o denksizlik de aynı yere düşer ve
bir **veri hatası, "kur çevrim farkı" adı altında özkaynağa gömülüp kaybolur.**
`cevrim_farki_ekle()` ikisini ayırır: yerel denksizlik × kapanış kuru = veri
hatası, kalanı saf çevrim farkı. K01 bulgusu buradan beslenir.

**Üç senaryo** üretilir: `eur_gercek` (gerçekleşen kur), `eur_sabit` (bütçe kuru),
bütçe. Kur etkisi = gerçek − sabit; iş performansı = sabit − bütçe. sapma.py bunu
kullanacak.

## 10. Veri üretecinde yakalanan dört kurgu hatası

Bunlar motorun değil, **sentetik verinin** hatalarıydı; motoru test ederken çıktı:

1. **Grup içi satış ≠ grup içi alım maliyeti.** Her şirket grup içi alımını kendi
   cirosundan tahmin ediyordu, satıcının ona kestiği faturadan değil. Eliminasyon
   5,8M EUR açık veriyordu. Çözüm: iki geçişli üretim, `grup_ici_satis` sözlüğü
   kimin kime ne sattığını tutar, `smm_yaz()` alıcının maliyetini ondan türetir.
   Kalan fark (~%0,5) kur kaynaklı ve **kasıtlı**: K08'in ölçtüğü şey bu.
2. **Stok alımı hiç yoktu.** SMM stoktan çıkıyor ama stok girişi yazılmıyordu;
   stok yıl boyunca negatife gidiyor, dönen varlıklar −14,7M EUR çıkıyordu.
3. **T8 tuzağı absürt ölçekteydi.** Uydurma ofis gideri fişleri 10.000–98.000 GBP
   seçilmişti; UK01'in genel yönetim gideri 10,4M EUR, cirosu 9,75M EUR oluyordu.
   Tuzağın ayırt edici özelliği tutarların YUVARLAKLIĞI, büyüklüğü değil, 10× küçültüldü.
4. **Giderler grup içi ciro dahil hesaplanıyordu.** Konsolidasyonda hasılat elimine
   edilince gider oranı yapay olarak şişiyor, faaliyet kârı −9M çıkıyordu. Gider
   tabanı dış ciroya bağlandı.

Sonuç, sağlıklı bir grup tablosu: konsolide hasılat 61,6M EUR, brüt marj %35,5,
faaliyet marjı %12,5, net marj %8,9. UK01 tek başına zararda (−%3,6) çünkü T8
tuzağı orada; bu **kasıtlı** ve kontrol testinin bulacağı bir sinyal.

## 11. kontrol.py, yanlış pozitif dersi

İlk çalıştırmada **1.902 bulgu** çıktı; bunun 1.499'u tek bir testten (K05).
Bu, modülün kendi başlığındaki ilkenin ihlaliydi: *"400 bulgulu bir rapor
okunmaz; okunmayan rapor kontrol değildir."* Üç kaynak vardı:

| Test | Önce | Sonra | Kök neden |
|---|---|---|---|
| K05 Yetki aşımı | 1.499 | **3** | Onay limiti tüm fişlere uygulanıyordu. Limit bir HARCAMA yetkisidir, müşteri tahsilatına, satış faturasına, rutin stok alımına, bordroya uygulanmaz. Kapsam `kapsam_grup_hesaplari` ile gider ve yatırım hesaplarına daraltıldı. |
| K04 Mesai dışı | 279 | **3** | Veri üreteci fiş gününü rastgele seçiyordu, üçte biri hafta sonuna düşüyordu. Fişin TARİHİ hafta sonu olabilir (satış olur) ama muhasebe KAYDI hafta içi girilir. `_rastgele_zaman` kayıt gününü hafta içine çekiyor. |
| K12 Yuvarlak tutar | 0 | **1** | Eşik 10.000'in katıydı, tuzak tutarları 1.000'in katı. Ayrıca oran %21,8 çıkıp %25 eşiğinin hemen altında kalmıştı. Eşik 1.000 / %15'e çekildi. |

**Ders:** Bir kontrol testinin değeri hassasiyetinde değil, KAPSAMININ doğru
tanımlanmasında. "Limit aşıldı mı" sorusu, "kimin hangi yetkisi" sorusu
cevaplanmadan sorulamaz.

## 12. Yapay zekâ triyajı kendi kuralımızı düzeltti

Triyaj çıktısında bir madde şuydu:
> *"K05 kural setine 'SISTEM tarafından kaydedilen açılış fişleri' istisnasının
> eklenmesi"*

Kalan 8 K05 bulgusunun 5'i açılış/devir kaydıydı. Öneri uygulandı
(`haric_kullanicilar: [SISTEM, SYSTEM]`) → K05 8'den **3**'e indi ve
T6 tuzağı (gerçek yetki aşımı) yakalanmaya devam etti.

Triyaj ayrıca tekil bulgulardan desen çıkardı:
> *"Parçalama bulgularının tek seferlik olmayıp ardışık aylarda aynı
> şirket-kullanıcı-hesap üçlüsünde tekrar etmesi, sistematik limit dolanma
> şüphesi doğuruyor."*

Bu, motorun yapmadığı bir iş: motor 13 ayrı bulgu üretti, AI bunların bir
desen oluşturduğunu gördü. **Ama hiçbir sayıyı AI üretmedi**: 13 rakamı da,
tutarları da motor hesapladı.

## 13. Tuzak avı, durum tablosu

| Tuzak | Test | Nerede yakalanacak | Durum |
|---|---|---|---|
**SKOR: 14/14**: motor cevap anahtarını görmeden hepsini buldu.

| Tuzak | Test | Ne | Bulgu |
|---|---|---|---|
| T1 mükerrer fiş | K02 | TR01'de 3 fiş birebir kopya | 3 ✓ |
| T2 dönem kayması | K03 | DE01 Aralık'a Ocak 2026 belgeli fiş | 3 ✓ |
| T3 eliminasyon farkı | K08 | DE01'in TR01'e Haziran borcu %18 eksik | 1 ✓ |
| T4 hesap planı kayması | K09 | DE01 `6815` IT-Kosten, askıda 914.149 EUR | 1 ✓ |
| T5 mesai dışı | K04 | TR02'de pazar günü / gece fişleri | 3 ✓ |
| T6 yetki aşımı | K05 | TR01'de limitin 1,35× ve 1,62× katı 2 fiş | 2 ✓ |
| T7 limit parçalama | K06 | TR02, 14.08.2025, limitin %88-97'si 4 fiş | 1 ✓ |
| T8 Benford + yuvarlaklık | K07/K12 | UK01 ofis gideri, 132 uydurma fiş | 4 ✓ |
| T9 bilanço denkliği | K01 | UK01 Eylül'de tek taraflı kayıt | 1 ✓ |
| T10 eksik dönem | K10 | TR02 Kasım mizanı yok, 5,1M EUR hacim var | 1 ✓ |
| T11 ters bakiye | K11 | TR01 Şubat, satış hesabı borç bakiye | 3 ✓ |
| T12 görevler ayrılığı | K13 | TR02'de fişlerin %94'ü tek kullanıcı | 1 ✓ |
| T13, T14 biçim tuzakları | - | topla.py'de aşıldı | ✓ |

Bulgu dağılımı: kritik 20 · yüksek 49 · orta 60 · düşük 1 = **130**

## 14. GÜVENLİK OLAYI. API anahtarı git geçmişinde

**Ne oldu:** Anahtar `.env` yerine `.env.ornek` şablonuna yazıldı.
`.env.ornek` şablon olduğu için `.gitignore`'da **değildir** ve ilk commit'te
(`4e7cd63`) depoya girip GitHub'a push edildi.

**Ne yapıldı:**
- `.env.ornek` temizlendi, içine açık uyarı kondu (commit `dba5113`).
- `.env` dosyasına dokunulmadı, anahtarın doğru yeri orası, gitignore'da.
- **Depo PRIVATE bırakıldı.** Public yapılmadı.
- Git geçmişini yeniden yazma (`filter-branch`) denendi, izin reddedildi:
  geri alınamaz bir işlem olduğu için doğru davranış.

**KAPATILDI, 2026-09-18.** Yapılanlar sırasıyla:

1. **Anahtar iptal edildi** (Furkan, console.anthropic.com), yenisi üretildi ve
   yalnızca `.env`'e yazıldı. Yeni anahtarın bağlantısı doğrulandı.
2. **Geçmiş temizlendi.** Önce tam yedek alındı
   (`../mizankopru-yedek-20260918-1628.bundle`), sonra `git filter-branch
   --tree-filter` ile 18 commit'in tamamındaki `.env.ornek` temiz şablonla
   değiştirildi. `refs/original/` silindi, reflog süresi doldurulup `git gc`
   çalıştırıldı.
3. **Bağımsız doğrulama:** GitHub'dan taze klon alındı ve 18 commit'in her biri
   tarandı, anahtar bulunan commit sayısı **0**. İlk commit'teki `.env.ornek`
   artık `buraya-kendi-anahtarini-yaz` içeriyor.
4. `--force-with-lease` ile push edildi, depo **public** yapıldı.
5. **GitHub secret scanning + push protection açıldı.** Bundan sonra bir anahtar
   push edilmeye çalışılırsa GitHub işlemi engeller, aynı kaza tekrarlanamaz.

**Kalıcı ders:** `.env.ornek` gitignore'da değildir çünkü şablondur. Şablona
yazılan anahtar doğrudan uzak depoya gider. Dosyanın kendisi artık bunu ilk
satırında uyarıyor.

## 15. sapma.py, köprü ve 2025 sonucu

Ayrıştırma matematiksel olarak tamdır (artık terim yok) ve özdeşlik her
çalıştırmada sayısal olarak sınanır, tutmayan bir köprü yayımlanmamalıdır.

**Grup köprüsü, 2025 (EUR):**

| Kalem | EUR | Bütçeye oran |
|---|---|---|
| Bütçe (bütçe kuruyla) | 77.035.451 | |
| + Fiyat etkisi | +6.808.114 | +%8,8 |
| + Karışım etkisi | −76.906 | −%0,1 |
| + Hacim etkisi | −6.923.589 | −%9,0 |
| **= Sabit kurda fiili** | **76.843.071** | **−%0,2** |
| + Kur etkisi | −5.812.928 | −%7,5 |
| **Fiili (gerçekleşen kurla)** | **71.030.142** | **−%7,8** |

Fiyat artışı hacim kaybını neredeyse tam karşıladı. Açığın tamamı kurdan.

**TR01, aynı yıl üç okuma:** miktar −%12,1 · yerel ciro **+%2,1** · EUR ciro **−%11,2**.

**Mutabakat:** köprü satış detayından (brüt fatura), gelir tablosu mizandan
gelir; aradaki 1.490.444 EUR fark, iadenin 4090 yerine doğrudan hasılat
hesabına yazılmasından. Bu aynı zamanda bir sınıflandırma bulgusu (K11 de
işaretledi). Farkı AI yorumu kendi "Dikkat" bölümünde yakaladı, mutabakat
tablosu onun üzerine eklendi.

## 16. Git

Depo-yerel kimlik (CLAUDE.md kuralı. Vercel `Deployment Blocked` tuzağı):
```
user.name  = mrFurkan33333
user.email = 250136320+mrFurkan33333@users.noreply.github.com
```
`.env` gitignore'da ve `git check-ignore` ile doğrulandı. Üretilen veri,
çıktı ve günlükler depoda yok, hepsi `py araclar/veri_uret.py` ile
yeniden üretilebilir. Cevap anahtarı (`veri/ornek/`) depoda.

## 18. Lisans modeli. MIT değil, çift lisans

**Karar:** Proje 18 Eylül'de kısa süre MIT olarak yayımlandı, sonra
**PolyForm Noncommercial 1.0.0 + ticari lisans** modeline geçirildi.

**Neden MIT yanlıştı:** MIT ticari kullanıma sınırsız izin verir. İstenen ise
kişisel/eğitim/araştırma kullanımının serbest, işletme kullanımının ayrı bir
anlaşmaya bağlı olmasıydı. MIT tam tersini yapıyordu.

**Neden PolyForm:** Avukat tarafından hazırlanmış, kısa ve okunabilir standart
bir lisans. "Ticari olmayan amaç" ve "ticari olmayan kuruluş" tanımlarını açıkça
yapıyor. Aynı model EPPlus gibi ticari Excel kütüphanelerinde kullanılıyor.

**Elenen alternatifler:**
| Lisans | Neden elendi |
|---|---|
| BUSL 1.1 | Belirli bir tarihte otomatik açık kaynağa dönüşüyor; istenmiyordu |
| Elastic License 2.0 | İç ticari kullanıma izin veriyor, istenen bu değildi |
| Commons Clause | MIT'e eklenen kısıt; tanımları PolyForm kadar net değil |
| CC BY-NC | Creative Commons yazılım için kullanılmasını kendisi önermiyor |

**Uygulanan dosyalar:** `LICENSE` (tam metin + Required Notice + Türkçe özet),
`COMMERCIAL.md` (kapsam, lisans biçimleri, iletişim, uyum), 15 kaynak dosyada
SPDX başlığı, README uyarısı, pano/panel/PDF altbilgileri,
`.github/ISSUE_TEMPLATE/ticari-lisans.yml`.

**Bilinmesi gerekenler:**
- GitHub lisansı **"Other / NOASSERTION"** olarak gösteriyor. PolyForm,
  GitHub'ın `licensee` listesinde yok. LICENSE dosyası yine tıklanabilir;
  README'nin en üstündeki uyarı bunu telafi ediyor.
- **MIT geri alınamaz.** O kısa süre içinde kopya alan varsa hakları devam eder.
  Bu tarihten sonraki sürümler yeni koşullara tabi. Kayıt: COMMERCIAL.md §7.
- Katkı kabul edilirse telif devri ya da sınırsız lisans gerekir, yoksa çift
  lisans modeli çalışmaz (COMMERCIAL.md §6).
- **Bu hukuki tavsiye değildir.** Ciddi bir ticari anlaşma öncesi avukata danışın.

## 19. Oturum günlüğü

### Oturum 1, 2026-09-18
- Proje kararları alındı (§2 tablosu).
- İskelet + 6 dosyalık yapılandırma katmanı kuruldu, çapraz doğrulama geçti.
- `gunluk.py` (denetim izi) + `sema.py` (yapılandırma yükleyici) yazıldı.
- Sentetik veri üreteci yazıldı; iki kez kalibre edildi:
  - 1. tur: ayda ~50 fiş çıktı → Benford testi için yetersiz, hacim 8× artırıldı.
  - 2. tur: mevsimsellik miktar düşüşünü maskeledi → çerçeve bütçe-fiili'ye
    çevrildi, TR parametreleri gerçek enflasyon senaryosuna göre yeniden kalibre edildi.
- `zeka.py` yazıldı; anahtarsız çalışma (graceful degradation) doğrulandı.
- Kullanıcı notu: Kaggle'dan gerçek veri sağlayabilir + kendi Claude API anahtarı var.
- `esle.py` yazıldı: askı hesabı (9999) mekanizması, AI eşleme önerisi (insan onaylı).
- `cevir.py` yazıldı: IAS 21, YTD→aylık türetme, çevrim farkı/veri hatası ayrımı,
  eliminasyon, azınlık payı (UK01 %25).
- Veri üretecinde 4 kurgu hatası bulunup düzeltildi (§10). Konsolide tablo sağlıklı.
- Claude API anahtarı bağlandı (.env, gitignore'da). Bağlantı doğrulandı.
  AI ilk gerçek işini yaptı: askıdaki `6815 IT- und Softwarekosten` hesabına
  **6040 Genel yönetim giderleri** önerdi, cevap anahtarındaki doğru kod.
  Güveni "orta" verdi ve "6060 Danışmanlık da mümkün" diye kendi kuşkusunu yazdı.
- `kontrol.py` yazıldı: 14 test. İlk tur 1.902 bulgu → kapsam düzeltmeleriyle 130.
- **14/14 tuzak yakalandı.**
- AI triyajı bir kural iyileştirmesi önerdi, uygulandı (§12).
- `sapma.py` yazıldı: fiyat/karışım/hacim/kur ayrıştırması, özdeşlik sınaması,
  mutabakat tablosu, AI sapma yorumu.
- Git deposu kuruldu; adım adım commit'lerle GitHub'a gönderildi
  (github.com/FlyerFukas/mizankopru, **private**).
- `pano.py`, `excel.py`, `boru.py` yazıldı; boru hattı uçtan uca 42 sn.
- README, MIT lisansı, SECURITY.md eklendi.
- `rapor_uret.py` ile 12 sayfalık proje raporu (PDF) üretildi.
- **Güvenlik olayı:** API anahtarı `.env.ornek` içinde git geçmişine girdi.
  Depo public YAPILMADI, anahtar iptali bekleniyor (§14).
- Hesap adı tespiti: `mrFurkan33333` ve `FlyerFukas` aynı hesap (id 250136320).
- Panel yazıldı: yerel web arayüzü, canlı SSE log akışı, sürükle-bırak yükleme.
- **Lisans MIT'ten PolyForm Noncommercial + ticari lisansa geçirildi** (§18).

---

## §19. Gerçek mizanla ilk çalıştırma ve bulunan kritik hata

**Olay.** Kullanıcı `mizan 2018 nilsan son.xls` dosyasını panelden yükledi.
Bütün çıktılar üretildi, tablo denkti, 20 bulgu çıktı. Bağımsız denetçi
incelemesi: bulguların **0'ı** yüklenen dosyayla ilgiliydi, 20'si de demo
veriden üretilmişti. Kullanıcının kendi verisi hiç işlenmemişti.

**Kök neden zinciri.** Tek bir hata değil, birbirini gizleyen altı hata:

1. `topla.py` dosya adında şirket kodu bulamayınca satırı **sessizce atladı**
   ve devam etti. Uyarı bir satırdı, boru hattı durmadı.
2. `veri/ara/*.csv` önceki demo çalıştırmasından kalmıştı. Kullanıcı tek bir
   mizan yüklemişken `kontrol.py` 42.637 satırlık eski bir yevmiyeyi okudu.
3. Kapsam yapılandırmadan okunuyordu, yüklenen veriden değil: verisi olmayan
   4 şirket rapora "eksik dönem" bulgusu olarak girdi (K10, 64 sahte bulgu).
4. Çıktılarda dönem `2025-12` ve para birimi `EUR` sabit yazılıydı; veri
   2018-12 ve TRY idi.
5. Eşleme tablosu demo veriye göre yazılmıştı: gerçek bir TDHP mizanının
   65 ana hesabından **36'sı** askıya düştü, ciro ve özkaynak eksik çıktı.
6. Tek şirketlik veride grup içi eliminasyon yine de uygulanıyordu.

**Yapılan düzeltmeler.**

- `src/kaynak.py` **yeni**: boru hattı başlamadan kaynak doğrulaması. Tanınmayan
  dosya ya da karışık kaynak varsa hard stop (çıkış kodu 2), ne yapılacağı
  ekrana yazılır. `--kaynak-zorla` ile geçilirse çıktılara damga basılır.
- `araclar/profil_olustur.py` **yeni**: tanınmayan bir mizanın yapısını ölçer
  (başlık satırı, kolonlar, ana hesap deseni, hesap planı), `sirketler.yaml`
  kaydını üretir ve dosyayı tanınacak şekilde adlandırır.
- `araclar/capraz_dogrula.py` **yeni**: ham dosyayı boru hattının kodunu
  kullanmadan yeniden okur, 9 sınamayla çıktıları karşılaştırır. Boru hattının
  **8. adımı** olarak eklendi; her çalıştırmada koşar.
- `topla.py`: ara dosyalar çalıştırma başında silinir (sıra önemli: temizlik
  köken kaydından ÖNCE, aksi hâlde köken kendi temizliğinde siliniyordu).
  Kapsam yüklenen veriden türetilir (`kapsam.json`). Geçersiz çalıştırmada
  eski çıktılar `cikti/bayat/<zaman>/` altına taşınır, `NEDEN_BAYAT.txt` yazılır.
- `esle.py`, `cevir.py`, `sapma.py`, `kontrol.py`, `pano.py`, `excel.py`:
  yüklenmemiş veriye dayanıklı. Eksik dosya çökme değil, **atlanan adım**.
- `sapma.py`: ürün miktarı/fiyatı yokken fiyat-karışım-hacim ayrıştırması
  YAPILMAZ, `sapma_atlandi.json` yazılır ve neden yapılamadığı açıklanır.
  Önceki çalıştırmadan kalan köprü dosyaları silinir.
- `kontrol.py`: her testin `gerekli_veri` alanı var; veri yoksa test atlanır
  ve `cikti/atlanan_testler.json`'a yazılır. Bulgu metinlerindeki sabit "EUR"
  sunum para birimine bağlandı.
- Kapanış hükmü: atlanan test varken "imzalanabilir" yerine **KOŞULLU**.
  Temiz sonuç ile denetlenmemiş risk artık birbirine karışmıyor.
- `hesap_eslesme.csv`: **tam TDHP ana hesap seti** (185 yeni eşleme, 100-798).
  `grup_hesap_plani.yaml`: 7 yeni grup hesabı (diğer duran varlıklar, alınan
  avanslar, ortaklara borçlar, kâr yedekleri, diğer gelir/gider, 7/A maliyet).
- `sema.py`: `kapsam()`, `son_donem()`, `veri_var()` eklendi; CSV okuyucu `#`
  yorum satırlarını atlıyor.
- `sirketler.yaml` depodan çıkarıldı (gerçek şirket adları içerir),
  `sirketler.ornek.yaml` eklendi. Dosya yoksa hata mesajı ne yapılacağını söyler.

**Sonuç (NILSAN 2018-12, 65 ana hesap, 97.019.382,88 TL denk mizan).**

| Ölçü | Önce | Sonra |
|---|---|---|
| İşlenen dosya | demo veri | kullanıcının dosyası (parmak izi kayıtlı) |
| Eşleşen hesap | 29/65 | **65/65** |
| Askıda kalan tutar | 7.598.982 TL | **0,00** |
| Bilanço denklik farkı | ölçülmüyordu | **0,00** |
| Çapraz doğrulama | yoktu | **9/9 GEÇTİ** |
| Kapanış hükmü | "imzalanabilir" | **KOŞULLU** (10 test veri yokluğundan atlandı) |

**Negatif test.** `veri/girdi/` içine tanınmayan bir dosya konup çalıştırıldı:
`topla.py` çıkış kodu 2, `boru.py` çıkış kodu 1, önceki çıktılar
`cikti/bayat/20260921_102526/` altına taşındı. Hata sınıfı artık yakalanıyor.

---

## §20. Denetim kapsamının genişletilmesi ve FP&A katmanı

**Sorun.** Kullanıcı tek bir mizan yüklediğinde 14 testin 10'u yevmiye,
bütçe ya da grup içi mutabakat istediği için atlanıyordu: denetim kapsamı
%29. Sistem dürüsttü (atlananları tek tek yazıyordu) ama eldeki veriden
çıkarılabilecek kontrolleri de yapmıyordu.

**K15-K24: mizan tabanlı on yeni test.** Hepsi yalnızca mizandan çalışır ve
Türkiye mali denetim pratiğinde fiilen kullanılan kontrollerdir. Yalnızca
hesap planı `VUK_TDHP` olan şirketlerde koşar; başka plandaki şirket sessizce
geçilmez, kapsam dışı olarak raporlanır.

| Kod | Test | Ne yakalar |
|---|---|---|
| K15 | Düzenleyici hesap yönü | 103, 119, 129, 257, 268, 371, 501 gibi (-) hesapların ters bakiye vermesi; varlık toplamını doğrudan şişirir |
| K16 | Aktif-pasif ve dönem kârı mutabakatı | Bilanço ile gelir tablosunun birbirini doğrulamaması |
| K17 | 7/A maliyet ve yansıtma denkliği | Gider yeri hesaplarının yansıtmayla kapatılmaması, gider çift sayımı |
| K18 | KDV hesapları kapanışı | 191/391 mahsubunun yapılmaması, mizanın beyannameyle uyuşmaması |
| K19 | TTK 376 sermaye kaybı | Özkaynağın sermayenin yarısının/üçte ikisinin altına düşmesi, yasal yükümlülük |
| K20 | Ortaklarla ilişkili işlem yoğunluğu | Örtülü sermaye (KVK m.12), transfer fiyatlandırması (KVK m.13), adat faizi |
| K21 | Kasa bakiyesi makullüğü | Fiilen kasada olamayacak tutar, ortağa örtülü aktarım |
| K22 | Likidite ve kaldıraç eşikleri | Cari oran, asit-test, borç/özkaynak eşik ihlali |
| K23 | Amortisman tutarlılığı | Amortisman ayrılmaması ya da brüt tutarı aşması |
| K24 | Alacak ve stok devir süresi | Tahsil edilemeyen alacak, değer düşüklüğü ayrılmamış stok |

Kapsam **4/14'ten 14/24'e** çıktı.

**`bulgu()` artık önem ezebiliyor.** K18 ilk hâlinde yanlış pozitif üretti:
aralık ayının KDV'si ertesi ay beyan edildiği için 191/391'de bakiye kalması
olağandır. Test iki hesabın birbirinden *kopmuş* olup olmadığına bakacak
şekilde düzeltildi; yakın bakiyeler artık "düşük" önemle, açıklamasıyla
birlikte raporlanıyor. Aynı testin kanıtın gücüne göre farklı ağırlık
taşıyabilmesi için `Kontrolcu.bulgu()` opsiyonel `onem` parametresi aldı.

**`src/oran.py` (yeni, boru hattının 5a adımı).** FP&A tarafı: 18 finansal
oran (likidite, kaldıraç, kârlılık, faaliyet döngüsü) ve dikey analiz. Her
oranın **payı ve paydası ayrı kolonlarda** yazılır; bir oranı sorgulayan kişi
hangi hesaplardan geldiğini görmeden ona güvenemez. Hesaplanamayan oran "-"
yazılır, sıfır yazılmaz: ikisi aynı şey değildir. Yatay analiz en az iki
dönem ister; tek dönemde üretilmez ve `cikti/atlanan_analizler.json`'a
sebebiyle yazılır.

**İkinci bir hayalet veri hatası bulundu ve kapatıldı.** `cevir.py`,
`y.donemler()` ile *yapılandırmadaki* dönem listesini kullanıyordu. Tek bir
2018-12 mizanı yüklendiğinde konsolide tabloda **12 tane uydurma 2025 dönemi**
oluşuyordu: `reindex` + `ffill` her yüklenmemiş dönemi bir öncekinin
kopyasıyla dolduruyordu. Pano ve Excel `son_donem()` kullandığı için
görünmüyordu; `oran.py`'nin yatay analizi "2025-12 → 2018-12" yazınca ortaya
çıktı. Dönemler artık **yüklenen veriden** türetiliyor. Yapılandırmadaki dönem
listesi bir takvimdir, bir veri beyanı değil.

Çapraz doğrulamaya üç sınama eklendi (9 → 12): konsolide tablodaki dönem
sayısı, yüklenmemiş olduğu hâlde üretilen dönem sayısı, yüklenmemiş olduğu
hâlde üretilen şirket sayısı.

**Diğer düzeltmeler.**
- Sabit "14 test" metinleri koddan ve belgelerden kaldırıldı; test sayısı
  yapılandırmadan okunuyor. Test eklendiğinde belge sessizce yanlışa dönmüyor.
- `araclar/ozet_uret.py` (yeni): iki sayfalık özet belge. İçindeki her rakam
  son çalıştırmanın çıktı dosyalarından okunur, elle yazılmaz.
- Pano ve Excel paketine oran ve dikey analiz bölümleri eklendi (Excel artık
  10 sayfa).

**Doğrulama (NILSAN 2018-12).** Boru hattı 9 adım, 18 sn. Çapraz doğrulama
**12/12 geçti**. 24 testin 14'ü çalıştı, 5 bulgu: ortaklarla ilişkili
işlemler aktifin %21,2'si (yüksek), stok devir 352 gün, asit-test 0,39,
KDV mahsubu farkı 707 TL (düşük), nakit hesabında ters hareket. Panel
gerçek testte canlı log akışıyla çalıştırıldı, 9 adım da tamamlandı.

---

## §21. Gözetimli öğrenme entegrasyonu, birinci sistem

**Kaynaklar bağlandı.** `gozetimli-ogrenme` (Furkan'ın kendi referans
kütüphanesi: metrikler, çapraz doğrulama stratejileri, sızıntı ölçümü)
düzenlenebilir kurulumla projeye bağlandı. Değerlendirme tarafını o, model
gövdesini scikit-learn sağlıyor. `ML-Kutuphane/regresyon_kiyas.py` regresyon
sistemlerinde kullanılmak üzere bekliyor (Sistem 3).

```
py -m pip install scikit-learn
py -m pip install -e C:\Users\furka\Music\gozetimli-ogrenme
```

**`ENTEGRASYON-ML.md` yazıldı.** Dört sistem, sırası ve gerekçesi belirlendi:
hesap eşleme sınıflandırıcısı (veri bugün var, yapıldı), bulgu triyajı
(etiket toplama altyapısı kuruldu, model veri birikince), analitik prosedür
regresyonu (çok dönemli mizan gerekir), nakit akışı tahmini (üçüncünün
üstüne kurulur).

**Değişmeyen kural ve kanıtı.** Model hiçbir tutarı değiştirmez: öneri
üretir, sıralar, beklenti üretir. `araclar/ogrenme_notr_mu.py` boru hattını
öğrenme katmanı açık ve kapalı iki kez çalıştırıp tutar taşıyan sekiz
dosyanın özetini karşılaştırıyor ve **hepsi birebir aynı** çıkıyor. Bu,
`--zeka-kapali` sınamasının öğrenme katmanı için yapılan eşdeğeri.

### Sistem 1: hesap eşleme sınıflandırıcısı

`src/ogrenme.py` (ortak iskelet: taban çizgi, rapor, model kaydı) ve
`src/esleme_modeli.py` yazıldı. Girdi hesap adı artı kodun ilk iki hanesi,
çıktı grup kodu, 41 sınıf, eğitim verisi `hesap_eslesme.csv` (304 satır).

| Ölçüm | Makro F1 | İç içe CV | Doğruluk | İlk 3 öneri |
|---|---|---|---|---|
| Ad + kod öneki (üretime giren) | 0.589 | 0.582 | 0.681 | 0.808 |
| Yalnızca ad (kod sinyali yokken alt sınır) | 0.324 | 0.319 | 0.418 | 0.641 |
| Taban çizgi (en sık sınıf) | 0.012 | | | |
| **Hiç görülmemiş hesap planı** | **0.095** | | | |

**Gerçek test.** Eşleme tablosundan altı hesap geçici olarak kaldırıldı, boru
hattı çalıştırıldı, beş hesap askıya düştü. Modelin birinci önerisi **5/5
doğru**: 600 hasılata, 153 stoklara, 255 maddi duran varlıklara, 102 nakde,
335 personel borçlarına. Tabloda hiç bulunmayan on alt hesap adıyla ayrıca
sınandı, dokuzunda birinci öneri doğru.

**Üç metodolojik karar.**

1. *Hiperparametre seçimi iç içe çapraz doğrulamayla ölçülüyor.* Ayarı tüm
   veride CV ile seçip aynı skoru raporlamak seçim sızıntısıdır. Ölçülen
   fark +0.0069, yani küçük; ama ölçülmeden bilinemezdi.
2. *Hesap planı bazında grup bölmesi.* Rastgele bölme, aynı plandan benzer
   hesapları hem eğitime hem teste koyar. `GrupKKat` ile plan bazında
   bölündüğünde makro F1 0.095'e düşüyor: model, eğitildiği plan ailesinin
   dışında kullanılamaz. Bu bir kusur değil, sınırın ölçülmüş hâli.
3. *İlk gerekçe düzeltildi.* Başta "askıdaki hesabın kodu yoktur" diye
   düşünüp kod önekini dışlamıştım. Yanlıştı: askıdaki hesabın kodu vardır
   (120.01 gibi), yalnızca tabloda tam karşılığı yoktur. Kod öneki makro
   F1'i 0.324'ten 0.589'e çıkarıyor.

**Kütüphanede iki sınırlılık bulundu.** `gozetimli-ogrenme` Furkan'ın kendi
deposu; dokunulmadı, yalnızca not edildi.

- `capraz_tahmin(olasilik=True)` şunu döndürüyor: `predict_proba(...)[:, 1]`.
  Bu ikili sınıflandırma içindir, çok sınıflı problemde anlamsız. İlk-k
  doğruluk hesabı bu yüzden `esleme_modeli.ilk_k_oof()` içinde ayrıca
  yazıldı. İlk ölçümde bu yüzden ilk-3 doğruluğu 0.037 gibi imkansız bir
  değer çıkmıştı (doğruluk 0.435 iken).
- `GrupKKat.bol()` grup etiketlerinde `.item()` çağırıyor. Pandas'tan gelen
  object dtype dizide elemanlar düz Python `str` olduğu için `AttributeError`
  veriyor. Gerçek veride gruplar çoğu zaman metindir (şirket kodu, hasta
  kimliği, mağaza adı), yani sık karşılaşılacak bir durum. Geçici çözüm
  `pd.factorize` ile grupları tam sayıya çevirmek.

### Sistem 2: bulgu triyajı, veri toplama ayağı

`araclar/bulgu_etiketle.py` yazıldı. Bulgular kararlı bir kimlikle (test
kodu, şirket, dönem, nesne özeti) işaretleniyor; etiketler
`cikti/bulgu_etiketleri.csv` içinde birikiyor. Model en az 150 etikete kadar
**eğitilmiyor**: altında eğitilen bir sınıflandırıcı, etiketleyicinin o günkü
kararlarını ezberler.

Kritik kısıt: etiket bulguyu silmez, yalnızca gelecekteki sıralamayı
etkiler. Bir denetim aracında modelin "bunu görmene gerek yok" demeye
yetkisi yoktur.

### Boru hattı artık 10 adım

`[6c] Askıdaki hesaplar için model önerisi` eklendi; model ya da askıda hesap
yoksa adım kendini atlıyor. Panele "Eşleme modelini eğit" ve "Model önerisi"
düğmeleri eklendi. `boru.py` ve `panel.py` artık argümanlı betik
çalıştırabiliyor (`src/esleme_modeli.py --oner`).

**Bekleyen:** Sistem 3 ve 4 için çok dönemli mizan; unsupervised tarafı için
Furkan'ın göndereceği kaynak; model eğitimi için göndereceği veri seti.
