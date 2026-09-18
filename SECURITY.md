# Güvenlik Politikası

MizanKöprü finansal veri işleyen bir araçtır. Kendi başına ağa bir şey açmaz ve
bir servis çalıştırmaz, ama işlediği veri hassastır ve isteğe bağlı bir dış API
çağrısı yapar. Bu belge neyin nasıl korunduğunu ve bir zafiyeti nasıl
bildireceğinizi anlatır.

## Zafiyet bildirimi

Bir güvenlik açığı bulduysanız **herkese açık issue açmayın.**

GitHub üzerinden özel bildirim kullanın:
**Security → Report a vulnerability**
(`https://github.com/FlyerFukas/mizankopru/security/advisories/new`)

Bildiriminizde şunlar yardımcı olur: etkilenen dosya ve sürüm, yeniden üretme
adımları, gözlemlenen ve beklenen davranış, etkinin kapsamı. Yanıt süresi
7 gündür; bu proje bir ekip tarafından değil tek kişi tarafından
sürdürülmektedir.

## Sırların yönetimi

- **API anahtarı kodda yoktur ve olmayacaktır.** `src/zeka.py` anahtarı sırasıyla
  `ANTHROPIC_API_KEY` ortam değişkeninden ve proje kökündeki `.env` dosyasından
  arar. Başka hiçbir yerden okumaz.
- `.env` ve `*.key` `.gitignore` içindedir. Depoya bir katkı göndermeden önce
  `git check-ignore -v .env` ile doğrulayın.
- Depoda örnek olarak yalnızca `.env.ornek` bulunur ve içinde gerçek bir değer
  yoktur.
- Anahtarınız sızdıysa önce [Anthropic Console](https://console.anthropic.com/)
  üzerinden iptal edin, sonra yenisini üretin. Git geçmişinden silmek tek başına
  yeterli değildir — anahtar bir kez yayımlandıysa yakılmış sayılır.

## Veri gizliliği

- Motor **tamamen yereldir**. Mizan, yevmiye, bütçe ve satış verisi hiçbir yere
  gönderilmez; tüm işleme diskte yapılır.
- Tek istisna yapay zekâ katmanıdır. Açıkken Claude API'ye gönderilenler:
  hesap kodları ve adları, kontrol bulgusu özetleri ve toplulaştırılmış sapma
  rakamları. **Yevmiye satırları, fiş içerikleri ve kişi adları gönderilmez.**
  Ne gönderildiğini tam olarak görmek için `gunluk/zeka_onbellek/` altındaki
  JSON dosyalarını açın — her istem olduğu gibi orada durur.
- Katmanı tamamen kapatmak için: `py src/boru.py --zeka-kapali`, ya da
  `yapilandirma/zeka.yaml` içindeki `gorevler` girdilerini `false` yapın.
  Kapalıyken motorun ürettiği hiçbir rakam değişmez.
- Üretilen veri (`veri/girdi/`, `veri/ara/`), çıktılar (`cikti/`) ve günlükler
  (`gunluk/`) `.gitignore` içindedir. Bunlar gerçek şirket verisi içerebilir;
  yanlışlıkla commit edilmemesi için bilinçli olarak dışarıda bırakılmıştır.

## Denetim izi

`gunluk/denetim_izi.jsonl` her adımın girdi/çıktı parmak izini, her yapay zekâ
çağrısının istem ve yanıt özetini tutar. Bu dosya bir güvenlik kaydı değil bir
**denetim** kaydıdır; erişim kontrolü içermez. Gerçek veriyle çalışıyorsanız
`gunluk/` dizinini de şirket verisi gibi koruyun.

## Bağımlılıklar

Çalışma zamanı bağımlılıkları: `pandas`, `numpy`, `openpyxl`, `xlsxwriter`,
`PyYAML`, `anthropic` (isteğe bağlı). Hepsi yaygın kullanılan paketlerdir ve
sürümleri sabitlenmemiştir — üretim ortamında kullanacaksanız kendi
`requirements.txt` dosyanızda sabitleyin.

**Girdi dosyaları güvenilmez kabul edilmelidir.** Motor `.xlsx` ve `.csv` okur;
bu dosyalar dış kaynaklardan geliyorsa açmadan önce taranmalıdır. `openpyxl`
formül çalıştırmaz, ancak kötü biçimlendirilmiş bir dosya bellek tüketebilir.

## Kapsam dışı

Aşağıdakiler bu projenin tehdit modelinde değildir:

- Çok kullanıcılı erişim kontrolü — araç tek kullanıcının kendi makinesinde
  çalışır
- Verinin diskte şifrelenmesi — işletim sistemi düzeyinde çözülmelidir
- Üretilen `.xlsx` ve `.html` dosyalarının paylaşımdan sonraki güvenliği
- Yapay zekâ modelinin çıktısının doğruluğu — yorum metinleri insan
  gözetimi gerektirir ve hiçbir rakamın kaynağı değildir
