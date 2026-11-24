# any2llm

[English](README.md) · Türkçe kullanım rehberi

Dosyalarını yapay zekâ sohbetine ekleyebileceğin daha az sayıda dosyada topla ve cevabı orijinal PDF’ten kontrol et.

**Vizeye hazırlık · 4 kaynak dosya → 1 sohbet eki**

## Kurmadan dene

1. **[Örnek paketi indir](https://raw.githubusercontent.com/ahmetemreapo/any2llm/refs/heads/main/examples/midterm/tr/batch_01_of_1.md)** ve sohbetteki ataç ya da + düğmesinden `batch_01_of_1.md` dosyasını ekle. Metin açılırsa bağlantıya basılı tutup dosyayı kaydet veya [paketi GitHub’da görüntüle](examples/midterm/tr/batch_01_of_1.md?plain=1) ve indirme okuna (↓) dokun.
2. **Şu soruyu kopyala, sohbete yapıştır ve dosyayla birlikte gönder.**

   > Ölçüm planı hangi araştırma desenine uyuyor? Her sınıfta neyin ölçüldüğünü Excel sayfasına, desenin tanımını da orijinal PDF’in sayfasına atıf yaparak açıkla.

3. **Cevabı [orijinal PDF’in 2. sayfasından](https://raw.githubusercontent.com/ahmetemreapo/any2llm/refs/heads/main/src/any2llm/demo_assets/tr/ara%C5%9Ft%C4%B1rma-desenleri.pdf#page=2) kontrol et.** PDF ilk sayfada açılırsa ikinci sayfaya kaydır.

<details>
<summary>Beklenen cevap</summary>

Plan, **eşdeğer olmayan karşılaştırma gruplu ön test–son test yarı deneysel desene** uyuyor. Rastgele atama yapılmamış iki mevcut sınıfa da etkinlikten önce ve sonra aynı 10 soruluk terim testi uygulanıyor. Sekiz dakika boyunca A sınıfı terimleri hafızadan hatırlamaya çalışıyor, B sınıfı ise terimleri yeniden okuyor ([ölçüm-planı.xlsx](src/any2llm/demo_assets/tr/%C3%B6l%C3%A7%C3%BCm-plan%C4%B1.xlsx), **Ölçüm Planı** sayfası). Bu düzen, `araştırma-desenleri.pdf` dosyasının **2. sayfasındaki** tanıma uyuyor.

</details>

Örnekte Araştırma Yöntemleri vizesi için hazırlanmış dört özgün belge var. [PDF ders notu](src/any2llm/demo_assets/tr/ara%C5%9Ft%C4%B1rma-desenleri.pdf), [PowerPoint sunusu](src/any2llm/demo_assets/tr/%C3%B6l%C3%A7%C3%BCm-ve-yanl%C4%B1l%C4%B1k.pptx), [Word çalışma listesi](src/any2llm/demo_assets/tr/%C3%A7al%C4%B1%C5%9Fma-listesi.docx) ve [Excel ölçüm planı](src/any2llm/demo_assets/tr/%C3%B6l%C3%A7%C3%BCm-plan%C4%B1.xlsx) aynı dersle ilgili. Denemek için yukarıdaki soru yeterli. Komutla üretilen sohbet talimatlarının tamamını [`PROMPT.txt`](examples/midterm/tr/PROMPT.txt) dosyasında görebilirsin.

any2llm dosyaları bilgisayarında hazırlar. Hazır dosyaları seçtiğin sohbet hizmetine sen yüklersin. Ek sayısının azalması, yapay zekânın bir seferde okuyabileceği metin miktarını artırmaz.

## Kur ve Türkçe demoyu çalıştır

Python 3.11 veya üstü, Git ve [pipx](https://pipx.pypa.io/stable/how-to/install-pipx.html) kuruluysa terminale şu komutu yaz.

```sh
pipx install git+https://github.com/ahmetemreapo/any2llm.git@main
```

Terminal `any2llm` komutunu bulamazsa `pipx ensurepath` çalıştır ve terminali kapatıp yeniden aç. pipx kullanmıyorsan [kaynak klasöründen kurulum](#kaynak-klasöründen-kurulum) adımlarını izle. GitHub’daki `v0.1.0` sürümü, komutlu demo eklenmeden önce yayımlandı.

```sh
any2llm demo --lang tr
```

Örnek belgeler kurulumla gelir. Komut her çalıştığında bulunduğun yerde yeni bir `any2llm-demo-tr-*` klasörü açar. Terminal tam yolu gösterir ve sohbete hangi dosyayı ekleyeceğini, hangi metni yapıştıracağını söyler.

Yukarıdaki indirilebilir dosyaları `midterm-pack-tr` adlı yeni bir klasörde yeniden üretmek için şu komutu kullan.

```sh
any2llm demo --lang tr --no-open -o ./midterm-pack-tr
```

## Kendi dosyalarını hazırla

1. Terminali aç. Aşağıdaki örnekte `./ders-notlarım` yerine kendi klasörünün yolunu yaz. Yol boşluk içeriyorsa tırnakları bırak.

   ```sh
   any2llm "./ders-notlarım" --lang tr
   ```

2. İlk çalıştırmada ayar ekranı açılırsa dil olarak Türkçeyi seç, sonra dosyaların nasıl bir araya getirileceğini ve sonuç klasörünün açılıp açılmayacağını belirle. Ayarları daha sonra `any2llm setup` komutuyla değiştirebilirsin.
3. Ok tuşlarıyla dosyalar arasında gez ve boşluk tuşuyla seçimi değiştir. Enter seçimi onaylar. `--plain` numaralı menü açar, `-r` alt klasörleri de tarar, `-y` okunabilir dosyaları otomatik seçer. `any2llm ./demo` adı `demo` olan kendi klasörünü tarar.
4. Varsayılan çıktı, belge klasörünün içindeki `_llm_pack` klasörüdür. Başka bir konum için `-o sohbet_dosyaları` ekle. Terminal çıktı klasörünü ve eklerin adını gösterir.
5. `batch_*.md` dosyalarını sohbete ekle. Panoya kopyalanan talimatı yapıştır. Kopyalanmadıysa `PROMPT.txt` dosyasındaki metnin tamamını al. Birden çok ek varsa terminaldeki sırayı ve devam komutunu izle.

Terminal ve sohbet talimatları 11 dili destekler. Dil kodları `en`, `zh`, `hi`, `es`, `fr`, `ar`, `bn`, `pt`, `ru`, `ur` ve `tr`. `--lang tr` o çalıştırmada kayıtlı dil tercihinin yerine geçer. Tüm seçenekler için `any2llm --lang tr --help` çalıştır.

## Gizlilik ve okuma sınırları

- Metin çıkarma ve OCR bilgisayarında çalışır. Kullandığın sohbet hizmetine göndermeden önce hazırlanan dosyaları gözden geçir. Araç bazı parola ve anahtar dosyalarını atlar, metinde tanıdığı anahtar biçimlerini haber verir. Çıkarılan metin olduğu gibi pakette kalır. Token sayımı için tiktoken, sözlüğü önbellekte yoksa indirebilir.
- PDF’te metin ve fiziksel sayfa numarası korunur. Word ve PowerPoint’te metin ve tablolar, Excel’de hücre değerleri veya formüller, düz metin ve kod dosyalarında kaynak metin alınır. Bozuk, parolalı ve okunamayan belgeler atlanır. Tüm atlamaları görmek için `--details` ekle.
- Terminal, bir PDF sayfasında metin okuyamadığında veya yalnızca bir bölümünü okuyabildiğinde hangi sayfaya bakacağını söyler. Şekiller, grafikler ve görseller metin okunmuş olsa bile pakette eksik kalabilir. Araç bu kayıpları her zaman algılayamaz. Cevap bir görsele dayanıyorsa orijinal belgeyi aç.
- Tek kaynak dosyası en fazla 32 MiB, bir PDF en fazla 500 sayfa, bir Office dosyasının açılmış içeriği en fazla 128 MiB olabilir. Araç dosya başına 120 saniyeye kadar işlem yapar. Sohbet hizmetinin yükleme ve metin sınırları ayrıca geçerlidir.

### Taranmış PDF’leri okuma (OCR)

OCR, taranmış sayfalardaki yazıyı metne çevirir. Kullanmak için Poppler’i (`pdftoppm`) ve Tesseract’ı kur, kurulum klasörlerini tam yollarıyla `PATH` değişkenine ekle. Türkçe için Tesseract’ın `tur`, İngilizce için `eng` dil verisini kur. Kurulu dilleri `tesseract --list-langs` ile görebilirsin.

```sh
any2llm "./ders-notlarım" --lang tr --ocr
any2llm "./ders-notlarım" --lang tr --ocr-lang tur+eng
```

`--ocr` İngilizce tanıma yapar. `--ocr-lang tur+eng` Türkçe ve İngilizceyi birlikte kullanır. `--lang tr` ise terminal ve sohbet talimatlarının dilini seçer. OCR yalnızca metni çıkarılamayan PDF sayfalarında çalışır. Önemli adları ve sayıları orijinal sayfadan doğrula.

## Küçük teknik örnek

[Teslim tarihleri örneği](examples/delivery-dates/) bir PDF teklif, bir Excel çizelgesi ve bir toplantı notundan oluşur. Kaynak kod klasöründe şu komutu çalıştır.

```sh
any2llm examples/delivery-dates -y --no-open --lang tr --task "Teslim tarihlerini bir tabloda listele ve her tarih için kaynak belirt."
```

İlk kullanımda ayar ekranı açılırsa Türkçeyi seç ve diğer ayarları onayla. `examples/delivery-dates/_llm_pack` içindeki `batch_01_of_1.md` dosyasını ekle ve `PROMPT.txt` içindeki metni sohbete yapıştır.

**Beklenen cevap** Pilot teslimat 12 Mart 2027, ana teslimat 26 Mart 2027. Kaynaklar `delivery-schedule.xlsx` dosyasındaki `Schedule` sayfası ile `supplier-offer.pdf` dosyasının sırasıyla 1. ve 3. sayfalarıdır.

Terminalde şu uyarıyı görürsün. Pakette sonraki sayfanın numarası 3 olarak kalır.

```text
Orijinal PDF’i kontrol edin (supplier-offer.pdf, sayfa 2). Metin okunamadı.
```

## Kaynak klasöründen kurulum

Python 3.11 veya üstü ve Git gerekir. Git ile kaynak klasörünü al ve terminalde aç.

```sh
git clone https://github.com/ahmetemreapo/any2llm.git
cd any2llm
```

**Windows PowerShell**

```powershell
py -3 -m venv "$env:USERPROFILE\.any2llm-env"
& "$env:USERPROFILE\.any2llm-env\Scripts\python.exe" -m pip install .
$env:Path = "$env:USERPROFILE\.any2llm-env\Scripts;$env:Path"
any2llm --lang tr --help
```

`py` komutu yoksa ilk satırda `py -3` yerine `python` yaz. Her yeni terminalde `$env:Path` satırını yeniden çalıştır.

**macOS ve Linux**

```sh
python3 -m venv "$HOME/.any2llm-env"
"$HOME/.any2llm-env/bin/python" -m pip install .
. "$HOME/.any2llm-env/bin/activate"
any2llm --lang tr --help
```

Her yeni terminalde etkinleştirme satırını yeniden çalıştır. Linux’ta `venv` bulunamıyorsa dağıtımın Python venv ve pip paketlerini kur.
