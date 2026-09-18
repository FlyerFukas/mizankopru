# Katkı Rehberi

Katkıya açığım. Ancak bu projenin çift lisans modeli, katkılar konusunda
alışıldık açık kaynak projelerinden **farklı bir kural** gerektiriyor. Bir satır
kod göndermeden önce bunu okuyun.

---

## Neden özel bir kural var

MizanKöprü iki lisansla dağıtılıyor: ticari olmayan kullanım için
[PolyForm Noncommercial 1.0.0](LICENSE), işletmeler için ayrı ve ücretli bir
ticari lisans ([COMMERCIAL.md](COMMERCIAL.md)).

Bir yazılımı ticari lisansla satabilmek için **o yazılımın tamamının telif
hakkına sahip olmak** gerekir. Kabul edilen bir katkının telifi katkıda
bulunanda kalırsa, proje sahibi o satırları ticari lisansa dahil edemez — ve
model çalışmaz.

Bu, katkınızın değersiz görüldüğü anlamına gelmez. Tam tersi: kodunuzun
satılabilir bir ürünün parçası olmasının yasal önkoşulu.

---

## Katkı Beyanı (DCO benzeri)

Bir pull request açarak aşağıdakileri beyan etmiş olursunuz:

1. Gönderdiğiniz katkı **sizin özgün eserinizdir**; başka bir kaynaktan
   kopyalanmamıştır. Başka bir kaynaktan alınan bir bölüm varsa, kaynağını ve
   lisansını PR açıklamasında belirtirsiniz.
2. Katkınız üzerindeki **mali hakları** (işleme, çoğaltma, yayma, temsil, umuma
   iletim — FSEK m.21-25) proje sahibi **Furkan Akduman**'a devredersiniz; ya da
   bu mümkün değilse, proje sahibine katkı üzerinde **süresiz, geri alınamaz,
   dünya çapında, alt lisans verilebilir ve münhasır olmayan** bir kullanım
   hakkı tanırsınız — **ticari lisanslama dahil.**
3. Bu devrin/iznin karşılığında bir ücret talep etmezsiniz.
4. İşvereniniz varsa ve katkı çalışma saatlerinizde veya işverenin
   ekipmanıyla üretildiyse, bu devri yapmaya yetkili olduğunuzu teyit
   etmiş olursunuz.

Bu beyanı PR açıklamasına şu satırı ekleyerek onaylayın:

```
Katkı Beyanı: CONTRIBUTING.md'deki koşulları okudum ve kabul ediyorum.
```

Bu satırı içermeyen pull request'ler birleştirilmez. Kişisel bir güvensizlik
değil; modelin çalışması için gereken belgedir.

---

## Katkı kabul edilmeyen durumlar

- **Beyan satırı yoksa** — yukarıdaki sebep
- **Kaynağı belirsiz kod** — başka bir projeden alınmış olabilecek, lisansı
  bilinmeyen bölümler
- **Copyleft lisanslı koddan türetilmiş katkı** (GPL, AGPL, LGPL) — bu
  lisanslar türev eserin de aynı lisansla dağıtılmasını zorunlu kılar ve
  ticari lisanslamayı imkânsız hâle getirir
- **Yeni bağımlılık ekleyen ve lisansı izin verici olmayan** katkılar
  (mevcut bağımlılıkların hepsi BSD/MIT'tir, bu bilinçli bir tercihtir)

---

## Önce konuşalım

Büyük bir değişiklik planlıyorsanız **önce bir issue açın.** Reddedilecek bir
işe emek harcamanızı istemem. Küçük düzeltmeler (yazım hatası, açık bir bug,
belge iyileştirmesi) için doğrudan PR açabilirsiniz.

Özellikle ilgilendiğim katkılar:

- **Yeni ERP adaptörleri** — Logo, Mikro, Netsis, SAP, Nebim gibi Türkiye'de
  yaygın sistemlerin çıktıları için `yapilandirma/kolon_eslesme.yaml` girdileri
- **Yeni iç kontrol testleri** — `kontrol.py` içindeki desene uygun
- **IAS 29 enflasyon muhasebesi** — yol haritasındaki en büyük madde
- **Yeni hesap planları** — farklı ülkelerin yerel planları için eşleme tabloları

---

## Teknik beklentiler

- **Türkçe adlandırma.** Değişken, fonksiyon ve dosya adları Türkçe
  (`bakiye_ytd`, `kod_metni`, `sapma.py`). Kod tabanı bu konuda tutarlı.
- **Açıklama neden'i anlatsın.** Ne yaptığı koddan zaten okunuyor. Yorumlar
  *neden öyle yapıldığını* ve hangi tuzağı önlediğini anlatmalı.
- **Boru hattı bozulmasın.** PR'dan önce çalıştırın:
  ```
  py src/boru.py --veri-uret
  ```
  Yedi adım da tamam dönmeli.
- **Tuzak skoru düşmesin.** Demo veride 14 kasıtlı hata var ve motor hepsini
  buluyor. Bir testi ya da eşiği değiştiriyorsanız skorun hâlâ 14/14 olduğunu
  ve toplam bulgu sayısının gürültüye boğulmadığını PR'da belirtin.
- **Yeni kaynak dosyalara telif başlığı ekleyin** — mevcut dosyalardaki
  SPDX bloğunu kopyalayın.

---

## Katkıda bulunanlar

Kabul edilen katkılar `TESEKKURLER.md` dosyasında adınızla anılır. Telif
devri, emeğin görünmez olması anlamına gelmez.
