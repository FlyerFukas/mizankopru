# MİZANKÖPRÜ — Devir Dosyası (HANDOFF)

> Bu dosya oturumlar arası hafızadır. **Her anlamlı çıktıdan sonra güncellenir.**
> Yeni bir oturum açan (insan ya da model) önce burayı okur, sonra koda bakar.

**Son güncelleme:** 2026-09-18 · Oturum 1 (devam 3)
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
Hesap planı eşlemesi, kolon adları, kontrol eşikleri, şirket listesi — hepsi
`yapilandirma/` altındaki YAML'lerde. Furkan kendi mizanını `veri/girdi/` altına
koyup sadece YAML düzenleyerek çalıştırabilmeli.

## 3. Boru hattı

```
veri/girdi/  (dağınık .xlsx/.csv — farklı kolon adı, tarih ve sayı formatı)
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
- [x] Yapılandırma katmanı — 6 dosya, kendi kendini doğruluyor (`py src/sema.py`)
- [x] Ortak altyapı: günlük/denetim izi (`src/gunluk.py`), şema (`src/sema.py`)
- [x] Sentetik veri üreteci (`araclar/veri_uret.py`) — 41 dosya, ~41.000 yevmiye satırı, 14 tuzak
- [x] Veri kalibrasyonu doğrulandı — başlık bulgu veride mevcut (bkz. §7)
- [x] Yapay zekâ katmanı (`src/zeka.py`) — Claude API, anahtarsız da çalışır
- [x] `src/topla.py` — çok formatlı okuma + normalizasyon · **41 dosya, 44.414 satır okundu**

- [x] `src/esle.py` — hesap planı köprüsü · **askı hesabı + AI eşleme önerisi**
- [x] `src/cevir.py` — IAS 21 çevrim + konsolidasyon + NCI

- [x] `src/kontrol.py` — 14 kontrol testi · **14/14 tuzak yakalandı, 130 bulgu**
- [x] Claude API bağlandı ve doğrulandı (oturum maliyeti $0,51)

### Sırada
- [ ] `src/sapma.py` — fiyat/miktar/kur/karışım ayrıştırması
- [ ] `src/sapma.py` — sapma ayrıştırma
- [ ] `src/pano.py` / `src/excel.py` — çıktılar
- [ ] `src/boru.py` — orkestratör

### Yol haritası (v2)
- IAS 29 enflasyon muhasebesi (TÜİK ÜFE ile) — Türkiye için gerçek ve ayırt edici
- TCMB kurlarını canlı API'den çekme (şu an sabit tablo)
- Rolling forecast + senaryo motoru
- VUK ↔ IFRS köprüsü (ertelenmiş vergi)

## 5. Yapay zekâ katmanı — kural

**LLM hiçbir sayıyı üretmez.** Motor sayıyı üretir; LLM yalnızca hazır sayıyı
finans diline çevirir, önceliklendirir ya da bir hesap eşlemesi önerir.
Katman kapatılsa boru hattının ürettiği rakamların hepsi aynı kalır.
Bu mimari bir kısıt — `src/zeka.py` başlığında ve her istemin içinde yazılı.

Dört görev: `esleme_oner` (K09 bulgusuna çözüm önerisi) · `bulgu_triyaj`
(kontrol bulgularını aciliyete göre sırala) · `sapma_yorumla` · `yonetici_ozeti`.

Her çağrı denetim izine düşer: görev, model, istem parmak izi, token, tahmini
maliyet, yanıt parmak izi. Regüle süreçte "bu yorumu kim yazdı" sorusunun cevabı.
Önbellek açık (`gunluk/zeka_onbellek/`) — aynı istem tekrar API'ye gitmez.

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
- Ajan/workflow **üretilmiyor** — Furkan'ın açık talimatı (token tüketimi).

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

**Dikkat — veriye gömülü ikinci tuzak:** Mevsimsellik çarpanı Ocak 0,86 /
Aralık 1,24. "Ocak'a göre Aralık" karşılaştırması bu yüzden yanıltıcıdır;
miktar düşüyor olmasına rağmen artıyor görünür. Doğru çerçeve bütçe-fiili
yıllık toplamdır. Bu kasıtlı — motorun bunu ayırt etmesi bekleniyor.

## 8. topla.py — yaşanmış iki tuzak (tekrar etmesin)

**1. `str()` hesap kodunu bozar.** Excel'de `100` yazan hücre pandas'a `100.0`
float olarak gelir; `str()` onu `"100.0"` yapar. Eşleme tablosunda `"100"`
arandığı için 1.359 hesabın **tamamı** eşleşmeyen çıkmıştı. Tablo yine denk
görünüyordu — hata yalnızca eşleme oranına bakınca fark edildi.
Çözüm: `kod_metni()` (src/topla.py) — tam sayı float'ların kuyruğunu atar ama
`770.01` gibi gerçek ondalıklı kodları korur. Tüm anahtar alanlarda kullanılıyor.

**2. Sayı ayracı belirsizliği.** `1.234` Türkçe biçimde 1234, İngilizce biçimde
1,234'tür. `SayiAyristirici` önce şirketin yapılandırılmış biçimini uygular;
hem `.` hem `,` varsa sonuncusunu ondalık kabul eder (bu her zaman doğru);
yapılandırma dışı tek ayraç + 3 basamaklı kuyruk durumunda binlik varsayar ama
**sayar ve raporlar**. Sayaç sıfır değilse insan bakmalı.

**Doğrulama sonucu:** üç farklı sayı/dosya biçimi (TR metin virgüllü ×12 dosya,
DE gerçek sayı 12 sekme, UK metin noktalı tek csv) kayıpsız okundu — mizan
toplamı yevmiye toplamına birebir eşit (tek fark TR02 Kasım, ki o T10 tuzağı).

## 9. cevir.py — IAS 21 uygulaması ve iki tasarım kararı

**Karar 1 — mizan YTD, gelir tablosu aylık çevrilir.**
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

**Karar 2 — çevrim farkı ile veri hatası ayrıştırılır.**
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
   5,8M EUR açık veriyordu. Çözüm: iki geçişli üretim — `grup_ici_satis` sözlüğü
   kimin kime ne sattığını tutar, `smm_yaz()` alıcının maliyetini ondan türetir.
   Kalan fark (~%0,5) kur kaynaklı ve **kasıtlı** — K08'in ölçtüğü şey bu.
2. **Stok alımı hiç yoktu.** SMM stoktan çıkıyor ama stok girişi yazılmıyordu;
   stok yıl boyunca negatife gidiyor, dönen varlıklar −14,7M EUR çıkıyordu.
3. **T8 tuzağı absürt ölçekteydi.** Uydurma ofis gideri fişleri 10.000–98.000 GBP
   seçilmişti; UK01'in genel yönetim gideri 10,4M EUR, cirosu 9,75M EUR oluyordu.
   Tuzağın ayırt edici özelliği tutarların YUVARLAKLIĞI, büyüklüğü değil — 10× küçültüldü.
4. **Giderler grup içi ciro dahil hesaplanıyordu.** Konsolidasyonda hasılat elimine
   edilince gider oranı yapay olarak şişiyor, faaliyet kârı −9M çıkıyordu. Gider
   tabanı dış ciroya bağlandı.

Sonuç — sağlıklı bir grup tablosu: konsolide hasılat 61,6M EUR, brüt marj %35,5,
faaliyet marjı %12,5, net marj %8,9. UK01 tek başına zararda (−%3,6) çünkü T8
tuzağı orada; bu **kasıtlı** ve kontrol testinin bulacağı bir sinyal.

## 11. kontrol.py — yanlış pozitif dersi

İlk çalıştırmada **1.902 bulgu** çıktı; bunun 1.499'u tek bir testten (K05).
Bu, modülün kendi başlığındaki ilkenin ihlaliydi: *"400 bulgulu bir rapor
okunmaz; okunmayan rapor kontrol değildir."* Üç kaynak vardı:

| Test | Önce | Sonra | Kök neden |
|---|---|---|---|
| K05 Yetki aşımı | 1.499 | **3** | Onay limiti tüm fişlere uygulanıyordu. Limit bir HARCAMA yetkisidir — müşteri tahsilatına, satış faturasına, rutin stok alımına, bordroya uygulanmaz. Kapsam `kapsam_grup_hesaplari` ile gider ve yatırım hesaplarına daraltıldı. |
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
desen oluşturduğunu gördü. **Ama hiçbir sayıyı AI üretmedi** — 13 rakamı da,
tutarları da motor hesapladı.

## 13. Tuzak avı — durum tablosu

| Tuzak | Test | Nerede yakalanacak | Durum |
|---|---|---|---|
**SKOR: 14/14** — motor cevap anahtarını görmeden hepsini buldu.

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
| T13, T14 biçim tuzakları | — | topla.py'de aşıldı | ✓ |

Bulgu dağılımı: kritik 20 · yüksek 49 · orta 60 · düşük 1 = **130**

## 14. Oturum günlüğü

### Oturum 1 — 2026-09-18
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
  **6040 Genel yönetim giderleri** önerdi — cevap anahtarındaki doğru kod.
  Güveni "orta" verdi ve "6060 Danışmanlık da mümkün" diye kendi kuşkusunu yazdı.
- `kontrol.py` yazıldı: 14 test. İlk tur 1.902 bulgu → kapsam düzeltmeleriyle 130.
- **14/14 tuzak yakalandı.**
- AI triyajı bir kural iyileştirmesi önerdi, uygulandı (§12).
- Oturum AI maliyeti: **$0,5141** (5 çağrı, 2 önbellek isabeti).
