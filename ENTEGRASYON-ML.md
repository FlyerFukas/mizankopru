# Makine öğrenmesi entegrasyonu: hangi sistem, neden, hangi veriyle

Bu belge MizanKöprü'ye gözetimli öğrenmenin **nereye** ve **neden** gireceğini
belirler. Model eğitmek kolaydır; yanlış yere model koymak pahalıdır. Bir
kapanış motorunda yanlış bir tahmin, yanlış bir imzaya dönüşür.

## Değişmeyen kural

**Model hiçbir tutarı değiştirmez.** Konsolide rakamları, kontrol bulgularının
tutarlarını ve oranları Python üretir; bu değişmiyor. Model yalnızca üç iş
yapar:

1. **Öneri üretir** (hesap eşlemesi), insan onaylar.
2. **Sıralar** (bulgu önceliği), listeden hiçbir bulgu silinmez.
3. **Beklenti üretir** (analitik prosedür), fark bir *bulgu* olur, düzeltme değil.

Bu, mevcut `--zeka-kapali` kuralının aynısıdır: model katmanı kapatıldığında
üretilen bütün tutarlar birebir aynı kalmalıdır. Kapatma bayrağı
`--ogrenme-kapali` olacak ve MD5 karşılaştırmasıyla sınanacaktır.

## Kaynaklar

| Kaynak | Ne sağlar | Nerede |
|---|---|---|
| `gozetimli-ogrenme` | Metrikler, çapraz doğrulama stratejileri, sızıntı ölçümü, ağaç/boosting ölçütleri. Saf NumPy, Türkçe, 562 test. | `pip install -e C:\Users\furka\Music\gozetimli-ogrenme` |
| `ML-Kutuphane/regresyon_kiyas.py` | 10 regresörlük kıyas havuzu, Box-Cox hedef dönüşümü, ön işleyici, RandomizedSearchCV. | Regresyon sistemlerinde kopyalanacak |
| `scikit-learn` | Model gövdeleri ve Pipeline. | `pip install scikit-learn` |

`gozetimli-ogrenme` **değerlendirme** tarafını, scikit-learn **model** tarafını
verir. Bu ayrım kasıtlı: modelin kendisi değiştirilebilir bir parça, ama bir
modelin işe yarayıp yaramadığını nasıl ölçtüğümüz projenin omurgasıdır ve
okunabilir olmalıdır.

---

## Sistem 1: Hesap eşleme sınıflandırıcısı: ŞİMDİ

**Problem.** Yeni bir şirketin mizanı geldiğinde yerel hesapların grup planına
eşlenmesi gerekir. Eşleşmeyen hesap askıya (9999) düşer ve kapanış imzalanamaz.
Bugün bu boşluğu ya insan ya da bir LLM çağrısı dolduruyor.

**Neden model.** Alt hesaplar (`120.01 ALICILAR YURTİÇİ`), şirketin kendi açtığı
serbest hesaplar ve farklı hesap planları (SKR04, UK_COA) eşleme tablosunda yer
almaz. Bunların çoğu **adından** anlaşılır. Model çevrimdışı çalışır, maliyeti
sıfırdır ve her eşleme onaylandığında eğitim verisi büyür.

| | |
|---|---|
| Tür | Çok sınıflı sınıflandırma (41 sınıf) |
| Girdi | Hesap adı (metin) + hesap planı + kod öneki |
| Çıktı | Grup kodu + güven + ilk 3 öneri |
| Veri | `yapilandirma/hesap_eslesme.csv`, 304 satır, her sınıfta en az 2 örnek |
| Metrik | **Makro F1** (sınıflar dengesiz, azınlık sınıfı önemli) + ilk-3 doğruluk |
| Bölme | `TabakaliKKat(5, karistir=True)` |
| Taban çizgi | En sık sınıfı tahmin et; model bunu geçmezse kullanılmaz |

**Sızıntı riski ve önlemi.** TF-IDF sözlüğü tüm veriden çıkarılırsa test
katındaki kelimeler eğitimde görülmüş olur. Bu yüzden vektörleştirme
`Pipeline` içinde, çapraz doğrulama döngüsünün **içinde** kalır.
`gozetimli-ogrenme`nin ölçtüğü sahte kazanç bu hatada 20 puana kadar çıkıyor.

**Dürüstlük kısıtı.** Hesap kodunun tamamı özellik olarak verilirse model
tabloyu ezberler; yalnızca ilk iki hane kullanılır. Üç ölçüm yapılır ve üçü
de raporlanır.

### Ölçülen sonuçlar

| Ölçüm | Makro F1 | İç içe CV | Doğruluk | İlk 3 öneri |
|---|---|---|---|---|
| Ad + kod öneki (üretime giren) | 0.589 | 0.582 | 0.681 | 0.808 |
| Yalnızca ad (kod sinyali yokken alt sınır) | 0.324 | 0.319 | 0.418 | 0.641 |
| Taban çizgi (en sık sınıf) | 0.012 | | | |
| **Hiç görülmemiş hesap planı** | **0.095** | | | |

Son satır en önemlisi: hesap planına göre grup bölmesiyle ölçüldüğünde model
neredeyse hiçbir şey bilmiyor. Türkçe TDHP adlarıyla eğitilen bir model
Almanca SKR04 adlarını anlamaz. **Model, eğitildiği plan ailesinin dışında
kullanılamaz;** yeni bir plan için önce o plandan örnek eşleme girilmelidir.
Bu bir kusur değil, sınırın ölçülmüş hâlidir.

İç içe CV ile basit CV arasındaki fark (+0.0069) küçük: hiperparametre seçimi
skoru şişirmiyor. Ezber farkı ise +0.391, yani model eğitim verisini test
verisinden belirgin biçimde iyi biliyor. 245 örnek ve 24 sınıfla beklenen bir
sonuç; öneriler bu yüzden insan onayına bağlı.

**Gerçek test.** Eşleme tablosundan altı hesap geçici olarak kaldırıldı ve
boru hattı çalıştırıldı; beş hesap askıya düştü. Modelin birinci önerisi
beşinde de doğru çıktı. Tabloda hiç bulunmayan on alt hesap adıyla ayrıca
sınandı, dokuzunda birinci öneri doğru.

---

## Sistem 2: Bulgu triyajı: ALTYAPI ŞİMDİ, EĞİTİM VERİ BİRİKİNCE

**Problem.** İlk kontrol turunda 1.902 bulgu çıkmıştı, 1.499'u tek bir testten
ve çoğu gürültüydü. Kapsam daraltmasıyla 130'a indi. Bu daraltmayı bugün insan
yapıyor, her yeni veri setinde yeniden.

**Neden model.** Kullanıcı bir bulguyu "gerçek" ya da "gürültü" diye
işaretledikçe, hangi bulgu deseninin aksiyona dönüştüğü öğrenilebilir.

| | |
|---|---|
| Tür | İkili sınıflandırma |
| Girdi | Test kodu, önem, tutar, hesap grubu, şirket, dönem içi konum |
| Çıktı | "Gerçek bulgu" olasılığı |
| Veri | **Henüz yok.** `cikti/bulgu_etiketleri.csv` ile toplanacak |
| Metrik | **Duyarlılık öncelikli.** Gerçek bir bulguyu kaçırmak, bir gürültüyü listede tutmaktan çok daha pahalıdır |
| Eşik | `esik_tara(..., metrik="kesinlik", en_az_duyarlilik=0.95)` |
| Bölme | `GrupKKat` şirket bazında: aynı şirketin bulguları hem eğitimde hem testte olmamalı |

**Kritik kısıt.** Model bulguyu **silmez**, yalnızca sıralar. Düşük olasılıklı
bulgu listenin altına iner ama listede kalır ve neden aşağıda olduğu yazılır.
Bir denetim aracında modelin "bunu görmene gerek yok" demeye yetkisi yoktur.

**Şimdi yapılan:** etiket toplama altyapısı (`araclar/bulgu_etiketle.py` ve
panelde işaretleme). Model, elde en az birkaç yüz etiket biriktiğinde eğitilir.

---

## Sistem 3: Analitik prosedür, beklenen bakiye: ÇOK DÖNEMLİ VERİ GELİNCE

**Problem.** Bir hesabın bakiyesi geçmiş desenine göre beklenenden çok
sapıyorsa bu bir bulgudur. Denetim standardında adı vardır (ISA 520, analitik
prosedürler) ve bugün elle yapılır.

| | |
|---|---|
| Tür | Regresyon, hesap bazında |
| Girdi | Geçmiş dönem bakiyeleri, mevsimsellik, hasılat gibi sürükleyiciler |
| Çıktı | Beklenen bakiye + tahmin aralığı; gerçekleşen aralık dışındaysa bulgu |
| Veri | **Aynı şirketin en az 12-24 dönemlik mizanı.** Şu an tek dönem var |
| Metrik | sMAPE ve MAE (ölçek bağımsız; hesap büyüklükleri çok farklı) |
| Bölme | **`ZamanSerisiBolme` zorunlu.** KKat burada yanlıştır |

**Neden KKat yanlış.** `gozetimli-ogrenme`nin sızıntı testi bunu ölçüyor: zaman
serisinde K-Fold R²'yi -22.45'ten -0.04'e çıkarıyor, yani modelin işe
yaramadığını gizliyor. Geleceği geçmişe sızdıran bir kapanış aracı, denetimde
savunulamaz.

**Box-Cox uyarısı.** `ML-Kutuphane`nin `HedefDonusturucu`su Box-Cox kullanır ve
negatif değer kabul etmez. Bakiyeler negatif olabilir; burada
`PowerTransformer(method="yeo-johnson")` gerekir. Bu not `OKUBENI.md`de de
yazılı.

---

## Sistem 4: Nakit akışı ve işletme sermayesi tahmini: SONRA

FP&A tarafı. Nakit dönüşüm süresi, alacak ve stok devir günleri zaten
`src/oran.py` tarafından hesaplanıyor; bunların geleceğe projeksiyonu bütçe
verisi ve çok dönemli mizan gerektirir. Sistem 3'ün altyapısı üstüne kurulur.

---

## Sıra ve gerekçesi

| Sıra | Sistem | Neden bu sırada |
|---|---|---|
| 1 | Hesap eşleme | Veri **bugün var**, değeri ölçülebilir, yanlış tahminin maliyeti düşük (insan onaylıyor) |
| 2 | Bulgu triyajı | Etiket toplama bugün başlamalı ki veri birikebilsin |
| 3 | Analitik prosedür | Çok dönemli mizan gerekir; yanlış tahminin maliyeti yüksek, en son |
| 4 | Nakit akışı | 3'ün üstüne kurulur |

## Ölçmeden eklenmez

Her sistem için değişmez kural: **taban çizgisini geçemeyen model projeye
girmez.** Taban çizgi sınıflandırmada en sık sınıf, regresyonda bir önceki
dönemin değeri (naif tahmin). Model bunları geçmiyorsa eklenen karmaşıklık
bedava değildir ve çıkarılır.

Her eğitimin çıktısı `cikti/model_raporu.json` olarak yazılır: hangi veri,
kaç örnek, hangi bölme, hangi metrik, taban çizgiyle karşılaştırma ve aşırı
öğrenme farkı. Bu dosya olmadan bir model üretimde kullanılmaz.
