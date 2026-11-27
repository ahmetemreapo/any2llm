<div align="center">

<img src="docs/assets/banner.svg" width="100%" alt="any2llm: PDF, Word ve Excel dosyaları sayfa etiketli Markdown’a dönüşüyor, yapay zekâ sohbeti sayfa atıfıyla cevap veriyor.">

### Belgelerini yapay zekâya sor, her cevabın hangi sayfadan geldiğini gör.

PDF · Word · PowerPoint · Excel · EPUB · HTML · kod → ChatGPT, Claude, Gemini, yerel modeller ve MCP uygulamaları için Markdown

[**Hızlı başlangıç**](#-hızlı-başlangıç) · [**60 saniyede dene**](#-60-saniyede-dene-kurulum-yok) · [**Claude ve Cursor (MCP)**](#-claude-cursor-ve-diğer-mcp-uygulamalarında-kullan) · [**Belgeler**](docs/SPEC.md) · [**English**](README.md)

[![PyPI](https://img.shields.io/pypi/v/any2llm?color=3776AB&label=PyPI)](https://pypi.org/project/any2llm/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB)](pyproject.toml)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-listed-7c3aed)](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.ahmetemreapo/any2llm)
[![Platform uyumluluğu](https://github.com/ahmetemreapo/any2llm/actions/workflows/platforms.yml/badge.svg)](https://github.com/ahmetemreapo/any2llm/actions/workflows/platforms.yml)
[![MIT lisansı](https://img.shields.io/badge/License-MIT-2E8555)](LICENSE)

<img src="examples/delivery-dates-chat-demo.gif" width="800" alt="Üç teslimat belgesi iki Markdown ekine dönüşüyor. Yerel sohbet orijinal PDF sayfasına atıf yapıyor ve örnek bu sayfayı doğrulama için gösteriyor.">

</div>

## 🤔 Neden any2llm?

Yapay zekâ sohbetleri belgeleri iyi okur, ta ki bir cevabı kontrol etmen gerekene kadar. *Bu hangi sayfada yazıyordu? Taranmış sayfa okundu mu ki?* Çoğu dönüştürücü sayfa numaralarını atar. Bu yüzden sohbet onlara atıf yapamaz, sen de doğrulayamazsın.

any2llm bütün bir klasörü **her PDF sayfa numarasını koruyan** Markdown’a paketler, **okuyamadığı sayfaları işaretler** ve yapay zekâdan **kaynak göstermesini isteyen** istemi hazırlar.

- 📑 **Kontrol edebileceğin atıflar.** Her PDF parçası bir `<page number="3">` etiketinin içindedir. Yapay zekâ sayfayı belirtir, sen orijinali açarsın.
- 🗂️ **Karışık klasörler tek seferde.** PDF, Word, PowerPoint, Excel (değerler *ve* formüller), EPUB, HTML, CSV, Markdown ve kaynak kod.
- ✂️ **Her bağlam penceresine sığar.** Token bütçeli paketler ve sohbeti bunlarda sırayla gezdiren bir istem.
- 🔌 **Her yerde çalışır.** Herhangi bir sohbete ekle, bir komut satırı aracına aktar ya da Claude ve Cursor’a MCP ile bağla.
- 🔒 **Yerel ve dikkatli.** Her şey senin bilgisayarında çalışır. Kimlik bilgisi dosyaları atlanır, olası gizli anahtarlar işaretlenir. Bozuk, şifreli veya ikili dosyalar çalışmayı çökertmek yerine raporlanır.
- 🌍 **11 dil** desteği: terminal ve üretilen istemler için.

## 🚀 Hızlı başlangıç

**1. Çalıştır.** [uv](https://docs.astral.sh/uv/getting-started/installation/) varsa kurulum gerekmez:

```sh
uvx any2llm ./belgelerim
```

<sub>Kalıcı kurulum mu istiyorsun? `pipx install any2llm` (Python 3.11+). [Windows, macOS ve Linux için kurulum yardımı](docs/install.md)</sub>

**2. Dosyaları seç.** Okunabilir tüm dosyalar seçili gelir. Devam etmek için Enter’a bas.

**3. Sohbet et.** `_llm_pack/` klasöründeki numaralı `.md` dosyalarını ekle ve panoya kopyalanmış istemi yapıştır. Sonra atıf yapılan sayfaları kontrol et.

### Kullanım şeklini seç

| | Çalıştır | Sonuç |
| --- | --- | --- |
| 💬 **Herhangi bir yapay zekâ sohbeti** | `any2llm ./belgeler` | Numaralı Markdown ekleri ve panoda atıf istemi |
| 🔌 **Claude, Cursor ve MCP uygulamaları** | `claude mcp add any2llm -- uvx any2llm mcp ~/Documents` | Yapay zekâ klasörünü istediğinde kendisi okur |
| 🧰 **Betikler ve yönlendirme** | `any2llm ./belgeler --stdout \| llm "Tüm son tarihleri listele"` | Standart çıktıda tek bir Markdown akışı |

## 🧪 60 saniyede dene (kurulum yok)

Gerçek çıktı dosyaları bu repoda duruyor. Birini en sevdiğin yapay zekâ sohbetine ekle ve sayfa atıflarını kendin gör.

> [!TIP]
> GitHub eki metin olarak açarsa dosya görünümünün üstündeki indirme okuyla (↓) orijinal `.md` dosyasını kaydet.

### 💼 İş örneği: teslimat tarihleri

Bir tedarikçi teklifi (PDF), teslimat çizelgesi (Excel) ve toplantı notu (metin). [Kaynak dosyalara göz at](examples/delivery-dates/).

1. [Teslimat tarihleri ekini](examples/delivery-dates-pack/batch_01_of_1.md?plain=1) **↓** ile indir ve yapay zekâ sohbetine ekle.
2. Ekle birlikte şu soruyu gönder:

   > Pilot ve ana sevkiyat tarihlerini listele. Her tarih için Excel sayfasına ve orijinal PDF’in sayfasına atıf yap. Metni okunamayan sayfa varsa belirt.

3. [Orijinal tedarikçi teklifinin](https://raw.githubusercontent.com/ahmetemreapo/any2llm/main/examples/delivery-dates/supplier-offer.pdf#page=1) 1. ve 3. sayfalarını kontrol et.

<details>
<summary><b>Beklenen cevap</b></summary>

| Sevkiyat | Teslimat tarihi | Kaynaklar |
| --- | --- | --- |
| Pilot | 12 Mart 2027 | `delivery-schedule.xlsx`, **Schedule** sayfası ve `supplier-offer.pdf`, **1. sayfa** |
| Ana | 26 Mart 2027 | `delivery-schedule.xlsx`, **Schedule** sayfası ve `supplier-offer.pdf`, **3. sayfa** |

Paket, metni görsel içinde olduğu için 2. sayfayı işaretler. Navlun notunu okumak için orijinal sayfayı aç.

</details>

### 🎓 Öğrenci örneği: vizeye hazırlık

Araştırma Yöntemleri için dört dosya (PDF, PowerPoint, Word ve Excel) tek ekte, üstelik [üretilen sohbet istemiyle](examples/midterm/tr/PROMPT.txt) birlikte.

1. [Vizeye hazırlık ekini](examples/midterm/tr/batch_01_of_1.md?plain=1) **↓** ile indir ve yapay zekâ sohbetine ekle.
2. Ekle birlikte şu soruyu gönder:

   > Ölçüm planı hangi araştırma desenine uyuyor? Her sınıfta neyin ölçüldüğünü Excel sayfasına, desenin tanımını da orijinal PDF’in sayfasına atıf yaparak açıkla.

3. Tanımı [orijinal PDF’in 2. sayfasından](https://raw.githubusercontent.com/ahmetemreapo/any2llm/main/src/any2llm/demo_assets/tr/ara%C5%9Ft%C4%B1rma-desenleri.pdf#page=2) kontrol et.

<details>
<summary><b>Beklenen cevap</b></summary>

Plan, **eşdeğer olmayan karşılaştırma gruplu ön test–son test yarı deneysel desene** uyuyor. Rastgele atama yapılmamış iki mevcut sınıfa etkinlikten önce ve sonra aynı 10 soruluk terim testi uygulanıyor. Sekiz dakika boyunca A sınıfı terimleri hafızadan hatırlıyor, B sınıfı ise terimleri yeniden okuyor. `ölçüm-planı.xlsx` dosyasındaki **Ölçüm Planı** sayfasına ve `araştırma-desenleri.pdf` dosyasının **2. sayfasına** bak.

</details>

Aynı örneği kendi bilgisayarında `any2llm demo --lang tr --no-open` ile çalıştırabilirsin.

## 👥 Kimler için?

| Çalıştığın alan | Örnek kullanım |
| --- | --- |
| 💼 Ofis ve finans kayıtları | Tedarikçi teklifindeki ve hesap tablosundaki tarihleri karşılaştır. |
| ⚖️ Hukuki belgeler | Sözleşme taslaklarındaki maddeleri karşılaştır, alıntıyı orijinal PDF’te kontrol et. |
| 🔬 Araştırma | Makalelerdeki yöntemleri özetle, bir tanımı kaynak sayfasında kontrol et. |
| 🎓 Ders materyali | Slaytları, okumaları ve çalışma kâğıdını alıştırma sorularına dönüştür. |
| 📚 Kitaplar ve uzun metinler | Bir EPUB’ı veya kaydedilmiş web sayfalarını paketle, bölüm bölüm özet iste. |
| 💻 Yazılım ve dokümantasyon | Bir ayarın kaynak kodda ve teknik notlarda nasıl kullanıldığını sor. |

## 💬 Herhangi bir yapay zekâ sohbetiyle kullan

```sh
any2llm "./belgeler"           # yolda boşluk varsa tırnakları koru
any2llm ./belgeler -r          # alt klasörleri de ekle
any2llm ./belgeler --task "Tüm ödeme tarihlerini ve kimin ödeyeceğini bul"
```

1. İlk çalıştırmada dili, ayrıntı düzeyini ve çıktı klasörünün açılıp açılmayacağını seç.
2. Dosyaları seç, ardından `_llm_pack/` klasöründeki numaralı Markdown dosyalarını ekle ve istemi yapıştır (`PROMPT.txt` olarak da kaydedilir).
3. Birden fazla paket varsa terminalin gösterdiği yükleme sırasını izle ve aynı sohbette paketler arasında devam kelimesini gönder.

> [!NOTE]
> Modeller çok paketli talimatlara her zaman uymaz. Model devam etmezse son mesajını yeniden gönder ve sıradaki paketin adını yaz. Önemli atıfları orijinal belgede kontrol et.

## 🔌 Claude, Cursor ve diğer MCP uygulamalarında kullan

`any2llm mcp` yerel bir [Model Context Protocol](https://modelcontextprotocol.io) sunucusu çalıştırır. Yapay zekâ iki salt okunur araç kazanır: `list_documents` bir klasörün içeriğini gösterir, `read_documents` ise Markdown’ı PDF sayfa etiketleriyle döndürür ve içerik büyükse paketlere böler. Sunucu, verdiğin klasörün dışını asla okumaz.

**Claude Code**

```sh
claude mcp add any2llm -- uvx any2llm mcp ~/Documents
```

<details>
<summary><b>Claude Desktop, Cursor, Windsurf ve <code>mcpServers</code> dosyası kullanan diğer uygulamalar</b></summary>

```json
{
  "mcpServers": {
    "any2llm": {
      "command": "uvx",
      "args": ["any2llm", "mcp", "/Users/sen/Belgeler"]
    }
  }
}
```

Uygulama `uvx` komutunu bulamazsa tam yolunu kullan (macOS ve Linux’ta `which uvx`, Windows’ta `where uvx`). pipx ile kurduysan `"command": "any2llm"` ve `"args": ["mcp", "/Users/sen/Belgeler"]` yaz. Taranmış sayfaları okumak için klasörden sonra `--ocr` veya `--ocr-lang tur` ekle.

</details>

Sonra sadece sor: *“Sözleşmeler klasörünü oku ve her fesih maddesini PDF sayfasıyla listele.”*

## 🧰 Betiklerde ve yönlendirmede kullan

`--stdout`, bölünmemiş tek paketi standart çıktıya yazar. İlerleme ve uyarılar standart hataya gider. Okunabilir tüm dosyaları seçer ve diske hiçbir şey yazmaz.

```sh
any2llm ./sozlesmeler --stdout | claude -p "Hangi sözleşme otomatik yenileniyor? PDF sayfasını belirt."
any2llm ./makaleler -r --stdout | llm "Bu makalelerdeki örneklem büyüklüklerini karşılaştır"
any2llm ./notlar --stdout | pbcopy        # macOS (Linux: wl-copy veya xclip, Windows: clip)
any2llm ./notlar --stdout > notlar-paketi.md
```

<details>
<summary><b>Tüm komut satırı seçenekleri</b></summary>

| Seçenek | Etkisi |
| --- | --- |
| `-r`, `--recursive` | Alt klasörleri de ekle |
| `-y`, `--yes` | Okunabilir tüm dosyaları sormadan seç |
| `--stdout` | Bölünmemiş tek paketi standart çıktıya yaz |
| `--task METİN` | Sorunu üretilen isteme ekle |
| `--max-tokens SAYI` | Paket başına token bütçesi |
| `--lang KOD` | Terminal ve istem dili: `en`, `zh`, `hi`, `es`, `fr`, `ar`, `bn`, `pt`, `ru`, `ur`, `tr` |
| `--ocr`, `--ocr-lang DİL` | Metni çıkarılamayan PDF sayfalarına OCR uygula (örneğin `tur` veya `eng+tur`) |
| `--exclude GLOB` | Eşleşen yolları atla (tekrarlanabilir). Kök `.gitignore` kuralları da uygulanır. |
| `-o KLASÖR`, `--output KLASÖR` | Çıktı klasörü (varsayılan `_llm_pack`) |
| `--details` | Atlanan tüm dosyaları listele |
| `--plain` | Onay kutuları yerine numaralı menüler |
| `--no-open` | Çıktı klasörünü açma |
| `--include-sensitive` | Kimlik bilgisi gibi görünen dosyaları da ekle |
| `setup`, `demo`, `mcp [KLASÖR]` | Ayarları değiştir, örneği çalıştır veya MCP sunucusunu başlat |

Tam başvuru: [docs/SPEC.md](docs/SPEC.md#command-line-options)

</details>

## 📄 Neler çıkarılır?

| Format | Sonuç |
| --- | --- |
| **PDF** | Her fiziksel sayfanın metni `<page>` etiketlerinde. Metni olmayan sayfalar işaretlenir, isteğe bağlı OCR bunları okuyabilir. |
| **Word** (`.docx`) | Paragraflar ve tablolar, belgedeki sırasıyla |
| **PowerPoint** (`.pptx`) | Metin ve tablolar, slayt slayt |
| **Excel** (`.xlsx`) | Görünür sayfalar tablo olarak, önbellekteki değerler *ve* formüllerle |
| **EPUB** | Bölümler okuma sırasıyla. DRM korumalı kitaplar atlanır. |
| **HTML** | Kaydedilmiş sayfalar başlık, liste ve tablolarıyla okunur metin olarak. Şablonlar kod olarak kalır. |
| **Metin ve kod** | Markdown, CSV, JSON, YAML ve kaynak kod, boşluklar korunarak |

Grafikler, görseller ve sayfa düzeni çıkarılmaz. Cevap bir görsele dayanıyorsa orijinali kontrol et.

## ⚖️ Farkı ne?

Aşağıdaki araçlar içinde PDF sayfa numaralarını sohbet eklerinin *içinde* koruyan ve atıf isteyip çok paketli sohbeti yöneten bir istem yazan tek araç any2llm.

| Araç | PDF sayfa numaraları | Çıktıyı bölme | OCR | Sohbet talimatları |
| --- | --- | --- | --- | --- |
| **any2llm** | ✅ Markdown’da sayfa etiketleri | ✅ Token bütçeli paketler | İsteğe bağlı yerel Tesseract | ✅ Atıf istemi ve devam mesajları |
| MarkItDown | — | — | Eklentiyle görüntü modeli | — |
| Docling | Belge kaynak bilgisinde | Token bütçeli JSONL parçaları | Yapılandırılabilir motorlar | — |
| Pandoc | — | Bölüm bazlı HTML parçaları | — | — |
| Repomix | — | Boyuta göre numaralı dosyalar | — | Kullanıcının yazdığı talimat dosyası |

<details>
<summary>Kaynaklar</summary>

Tire, bu kaynakların tarif etmediği bir özelliği gösterir.

- MarkItDown ([README](https://github.com/microsoft/markitdown/blob/main/README.md), [OCR eklentisi](https://github.com/microsoft/markitdown/tree/main/packages/markitdown-ocr))
- Docling ([formatlar ve parçalar](https://docling-project.github.io/docling/usage/supported_formats/), [sayfa kaynak bilgisi](https://docling-project.github.io/docling/reference/docling_document/#docling_core.types.doc.ProvenanceItem), [OCR motorları](https://docling-project.github.io/docling/getting_started/installation/#ocr-engines))
- Pandoc ([girdi formatları](https://pandoc.org/MANUAL.html#option--from), [parçalı HTML](https://pandoc.org/MANUAL.html#chunked-html))
- Repomix ([hızlı başlangıç](https://repomix.com/guide/), [çıktıyı bölme](https://repomix.com/guide/configuration), [özel talimatlar](https://repomix.com/guide/custom-instructions))

</details>

## 🔒 Gizlilik, sınırlar ve OCR

- **Gizlilik.** Metin çıkarma ve OCR yerelde çalışır. tiktoken ilk kullanımda sözlüğünü indirebilir. Yaygın kimlik bilgisi dosyaları (`*.pem`, `id_rsa`, `credentials*`, …) atlanır. Çıkarılan metindeki olası gizli anahtarlar işaretlenir ama çıktıda kalır, bu yüzden yüklemeden önce gözden geçir. [Güvenlik politikası](SECURITY.md)
- **Sınırlar.** Dosya başına 32 MiB, PDF başına 500 sayfa, Office veya EPUB arşivi başına 128 MiB açılmış boyut ve dosya başına 120 saniye çıkarma süresi. Sohbetinin ek ve bağlam sınırları yine geçerlidir.

<details>
<summary><b>Taranmış PDF’ler için OCR kurulumu</b></summary>

Poppler (`pdftoppm`) ve ihtiyacın olan dil verisiyle [Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html) kur, klasörlerini mutlak yol olarak `PATH`’e ekle. İngilizce için `--ocr`, yüklü diğer diller için `--ocr-lang` kullan (örneğin `--ocr-lang tur` veya `eng+tur`). OCR yalnızca okunabilir metni olmayan PDF sayfalarında çalışır ve tanınan sayfalar pakette işaretlenir. Önemli isim ve sayıları taramayla karşılaştır.

</details>

## 🤝 Katkıda bulun

Hata bildirimleri, örnekler, çeviriler ve kod katkıları memnuniyetle karşılanır. [Katkı rehberiyle](CONTRIBUTING.md) veya [good first issue](https://github.com/ahmetemreapo/any2llm/labels/good%20first%20issue) etiketli bir konuyla başla.

any2llm işine yaradıysa bir ⭐ başkalarının da onu bulmasına yardım eder.

## 📜 Lisans

[MIT](LICENSE)
