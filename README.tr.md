# any2llm

any2llm, PDF, Office ve kod dosyalarıyla dolu bir klasörü yapay zekâ sohbetinin sayfa sayfa atıf yapabileceği Markdown’a dönüştürür.

<img src="examples/delivery-dates-chat-demo.gif" width="800" alt="Üç teslimat belgesi iki Markdown ekine dönüşüyor. Yerel sohbet orijinal PDF sayfasına atıf yapıyor ve örnek bu sayfayı doğrulama için gösteriyor.">

```sh
pipx install any2llm
any2llm demo --lang tr
```

[![PyPI](https://img.shields.io/pypi/v/any2llm?color=3776AB&label=PyPI)](https://pypi.org/project/any2llm/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB)](pyproject.toml)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-listed-7c3aed)](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.ahmetemreapo/any2llm)
[![Platform uyumluluğu](https://github.com/ahmetemreapo/any2llm/actions/workflows/platforms.yml/badge.svg)](https://github.com/ahmetemreapo/any2llm/actions/workflows/platforms.yml)
[![MIT lisansı](https://img.shields.io/badge/License-MIT-2E8555)](LICENSE)

[Hızlı başlangıç](#hızlı-başlangıç) · [Örnekler](examples/README.tr.md) · [Claude ve Cursor (MCP)](#claude-cursor-ve-diğer-mcp-uygulamalarında-kullan) · [Belgeler](docs/SPEC.md) · [English](README.md)

## Neden any2llm?

Yapay zekâ sohbetleri belgeleri iyi okur, ama bir cevabın nereden geldiğini kontrol etmek zordur. Çoğu dönüştürücü sayfa numaralarını atar, bu yüzden sohbet onlara atıf yapamaz.

- Her PDF parçası kaynak PDF’in sayfa numarasını taşır, cevabı oradan kontrol edebilirsin.
- Tek çalıştırmada karışık bir klasörü işler: PDF, Word, PowerPoint, Excel (değerler ve formüller), EPUB, HTML, CSV, Markdown ve kaynak kod.
- Büyük klasörler sohbetin bağlam penceresine sığan paketlere bölünür, istem de sohbete bunları hangi sırayla okuyacağını söyler.
- Çıktıyı herhangi bir sohbete ekleyebilir, bir komut satırı aracına aktarabilir ya da Claude ve Cursor’a MCP ile bağlayabilirsin.
- Her şey senin bilgisayarında çalışır. Kimlik bilgisi dosyaları atlanır, olası gizli anahtarlar işaretlenir. Bozuk, şifreli veya ikili dosyalar çalışmayı çökertmek yerine raporlanır.
- Terminal ve üretilen istemler 11 dilde kullanılabilir.

Tedarikçi teklifleri ve hesap tabloları, sözleşme taslakları, makaleler, ders materyalleri, kitaplar ve kod tabanları için kullanılabilir. MarkItDown, Docling, Pandoc veya Repomix’ten farklı olarak PDF sayfa numaralarını sohbet ekinin içinde korur ve atıf isteyen bir istem yazar. Ayrıntılar için [karşılaştırmaya](docs/comparison.md) bak.

## Hızlı başlangıç

1. `any2llm ./belgelerim` komutunu çalıştır. [uv](https://docs.astral.sh/uv/getting-started/installation/) varsa kurulum yapmadan `uvx any2llm ./belgelerim` de çalışır. Ayrıntılar için [Windows, macOS ve Linux kurulum yardımına](docs/install.md) bak.
2. Dosyaları seç. Okunabilir tüm dosyalar seçili gelir. Devam etmek için Enter’a bas.
3. `_llm_pack/` klasöründeki numaralı `.md` dosyalarını ekle ve panoya kopyalanmış istemi yapıştır. Sonra atıf yapılan sayfaları kontrol et.

| Nerede | Çalıştır | Sonuç |
| --- | --- | --- |
| Herhangi bir yapay zekâ sohbeti | `any2llm ./belgeler` | Numaralı Markdown ekleri ve panoda atıf istemi |
| Claude, Cursor ve MCP uygulamaları | `claude mcp add any2llm -- uvx any2llm mcp ~/Documents` | Yapay zekâ klasörünü istediğinde kendisi okur |
| Betikler ve yönlendirme | `any2llm ./belgeler --stdout \| llm "Tüm son tarihleri listele"` | Standart çıktıda tek bir Markdown akışı |

## Kurmadan dene

Hazır çıktı dosyaları [examples/](examples/README.tr.md) altında: teslimat tarihleriyle bir iş örneği ve vize materyaliyle bir öğrenci örneği. Birini yapay zekâ sohbetine ekle, orada yazan soruyu sor ve cevabı orijinal PDF sayfasıyla karşılaştır.

## Herhangi bir yapay zekâ sohbetiyle kullan

```sh
any2llm "./belgeler"           # yolda boşluk varsa tırnakları koru
any2llm ./belgeler -r          # alt klasörleri de ekle
any2llm ./belgeler --task "Tüm ödeme tarihlerini ve kimin ödeyeceğini bul"
```

1. İlk çalıştırmada dili, ayrıntı düzeyini ve çıktı klasörünün açılıp açılmayacağını seç.
2. Dosyaları seç, ardından `_llm_pack/` klasöründeki numaralı Markdown dosyalarını ekle ve istemi yapıştır (`PROMPT.txt` olarak da kaydedilir).
3. Birden fazla paket varsa terminalin gösterdiği yükleme sırasını izle ve aynı sohbette paketler arasında devam kelimesini gönder.

> [!NOTE]
> Modeller çok paketli talimatlara her zaman uymaz. Model devam etmezse son mesajını yeniden gönder ve sıradaki paketin adını yaz. **Önemli atıfları orijinal belgede kontrol et.**

## Claude, Cursor ve diğer MCP uygulamalarında kullan

`any2llm mcp` yerel bir [Model Context Protocol](https://modelcontextprotocol.io) sunucusu çalıştırır. Yapay zekâ iki salt okunur araç kazanır: `list_documents` bir klasörün içeriğini gösterir, `read_documents` ise Markdown’ı PDF sayfa etiketleriyle döndürür ve içerik büyükse paketlere böler. Sunucu, verdiğin klasörün dışını asla okumaz.

Claude Code:

```sh
claude mcp add any2llm -- uvx any2llm mcp ~/Documents
```

<details>
<summary>Claude Desktop, Cursor, Windsurf ve <code>mcpServers</code> dosyası kullanan diğer uygulamalar</summary>

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

Sonra sor: *“Sözleşmeler klasörünü oku ve her fesih maddesini PDF sayfasıyla listele.”*

## Betiklerde ve yönlendirmede kullan

`--stdout`, bölünmemiş tek paketi standart çıktıya yazar. İlerleme ve uyarılar standart hataya gider. Okunabilir tüm dosyaları seçer ve diske hiçbir şey yazmaz.

```sh
any2llm ./sozlesmeler --stdout | claude -p "Hangi sözleşme otomatik yenileniyor? PDF sayfasını belirt."
any2llm ./makaleler -r --stdout | llm "Bu makalelerdeki örneklem büyüklüklerini karşılaştır"
any2llm ./notlar --stdout | pbcopy        # macOS (Linux: wl-copy veya xclip, Windows: clip)
any2llm ./notlar --stdout > notlar-paketi.md
```

<details>
<summary>Tüm komut satırı seçenekleri</summary>

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

## Neler çıkarılır?

| Format | Sonuç |
| --- | --- |
| PDF | Her fiziksel sayfanın metni `<page>` etiketlerinde. Metni olmayan sayfalar işaretlenir, isteğe bağlı OCR bunları okuyabilir. |
| Word (`.docx`) | Paragraflar ve tablolar, belgedeki sırasıyla |
| PowerPoint (`.pptx`) | Metin ve tablolar, slayt slayt |
| Excel (`.xlsx`) | Görünür sayfalar tablo olarak, önbellekteki değerler ve formüllerle |
| EPUB | Bölümler okuma sırasıyla. DRM korumalı kitaplar atlanır. |
| HTML | Kaydedilmiş sayfalar başlık, liste ve tablolarıyla okunur metin olarak. Şablonlar kod olarak kalır. |
| Metin ve kod | Markdown, CSV, JSON, YAML ve kaynak kod, boşluklar korunarak |

Grafikler, görseller ve sayfa düzeni çıkarılmaz. Cevap bir görsele dayanıyorsa orijinali kontrol et.

## Gizlilik, sınırlar ve OCR

- Gizlilik: metin çıkarma ve OCR yerelde çalışır. tiktoken ilk kullanımda sözlüğünü indirebilir. Yaygın kimlik bilgisi dosyaları (`*.pem`, `id_rsa`, `credentials*`, …) atlanır. Çıkarılan metindeki olası gizli anahtarlar işaretlenir ama çıktıda kalır, bu yüzden **yüklemeden önce gözden geçir**. [Güvenlik politikası](SECURITY.md)
- Sınırlar: dosya başına 32 MiB, PDF başına 500 sayfa, Office veya EPUB arşivi başına 128 MiB açılmış boyut ve dosya başına 120 saniye çıkarma süresi. Sohbetinin ek ve bağlam sınırları yine geçerlidir.

<details>
<summary>Taranmış PDF’ler için OCR kurulumu</summary>

Poppler (`pdftoppm`) ve ihtiyacın olan dil verisiyle [Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html) kur, klasörlerini mutlak yol olarak `PATH`’e ekle. İngilizce için `--ocr`, yüklü diğer diller için `--ocr-lang` kullan (örneğin `--ocr-lang tur` veya `eng+tur`). OCR yalnızca okunabilir metni olmayan PDF sayfalarında çalışır ve tanınan sayfalar pakette işaretlenir. Önemli isim ve sayıları taramayla karşılaştır.

</details>

## Katkıda bulun

Hata bildirimleri, örnekler, çeviriler ve kod katkıları memnuniyetle karşılanır. [Katkı rehberiyle](CONTRIBUTING.md) veya [good first issue](https://github.com/ahmetemreapo/any2llm/labels/good%20first%20issue) etiketli bir konuyla başla.

any2llm işine yaradıysa bir yıldız başkalarının da onu bulmasına yardım eder.

## Lisans

[MIT](LICENSE)
