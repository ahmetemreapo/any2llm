# any2llm

**Belgelerine sor. Cevabı sayfa numarasıyla al, her alıntının gerçekten o sayfada olduğunun kanıtıyla birlikte.**

Yapay zekâ sohbetleri, cümle 14. sayfadayken "12. sayfa" der ya da sözleşmende hiç geçmeyen "14 günlük" bir süreyi
alıntılar. any2llm; PDF, Word, Excel, PowerPoint ve EPUB dosyalarıyla dolu bir klasörü senin bilgisayarında okur,
yerel bir modelle cevaplar ve ardından her alıntıyı orijinal sayfayla karşılaştırır.

<img src="examples/ask-and-check-demo.gif" width="800" alt="any2llm ask, 17 sayfalık bir kira sözleşmesiyle ilgili soruyu yerel bir modelle yaklaşık beş saniyede cevaplıyor. İki alıntı da 14. ve 6. sayfalarda doğrulanıyor. Ardından any2llm check başka bir sohbetten gelen cevabı inceliyor: bir alıntının 12. değil 14. sayfada olduğunu, sayısı değiştirilmiş bir alıntının ise sözleşmede bulunmadığını gösteriyor.">

```sh
pipx install any2llm             # ya da: uvx any2llm …
ollama pull qwen3:4b-instruct    # herhangi bir yerel model olur
any2llm ask demo --lang tr       # araçla gelen örnek dosyalar hakkında soru sor
```

[![PyPI](https://img.shields.io/pypi/v/any2llm?color=3776AB&label=PyPI)](https://pypi.org/project/any2llm/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB)](pyproject.toml)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-listed-7c3aed)](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.ahmetemreapo/any2llm)
[![Claude Code eklentisi](https://img.shields.io/badge/Claude_Code-plugin-d97757)](#claude-code-eklentisi)
[![Platform uyumluluğu](https://github.com/ahmetemreapo/any2llm/actions/workflows/platforms.yml/badge.svg)](https://github.com/ahmetemreapo/any2llm/actions/workflows/platforms.yml)
[![MIT lisansı](https://img.shields.io/badge/License-MIT-2E8555)](LICENSE)

[Yerel modeller](#yerel-bir-modelle-sor) · [Herhangi bir sohbetin cevabını kontrol et](#herhangi-bir-sohbetin-cevabını-kontrol-et) · [Claude Code](#claude-code-eklentisi) · [MCP](#claude-desktop-cursor-ve-diğer-mcp-uygulamalarında-kullan) · [Örnekler](examples/README.tr.md) · [English](README.md)

## Sana uyan yolu seç

| Kullandığın | Çalıştır | Sonuç |
| --- | --- | --- |
| Ollama, LM Studio veya llama.cpp | `any2llm ask ./belgeler "Ödeme ne zaman?"` | Yerel modelinden cevap, her alıntısı kontrol edilmiş olarak |
| ChatGPT, Claude, Gemini ya da herhangi bir sohbet | Cevabı kopyala, sonra `any2llm check ./belgeler` | Her alıntı için: bulundu, başka sayfada ya da dosyalarında yok |
| Claude Code | `/plugin install any2llm --marketplace ahmetemreapo/any2llm` | Claude klasörünü okur ve cevaplamadan önce kendi kaynaklarını kontrol eder |
| Claude Desktop, Cursor, diğer MCP uygulamaları | `uvx any2llm mcp ~/Belgeler` | Belgeleri listeleme, okuma ve kontrol etme araçları |
| Herhangi bir sohbet, elle | `any2llm ./belgeler` | Numaralı Markdown ekleri ve panoda kaynak isteyen bir istem |
| Betikler | `any2llm ./belgeler --stdout \| llm "Tüm son tarihleri listele"` | Standart çıktıda tek bir Markdown akışı |

## Farkı ne?

- **Her alıntı kontrol edilir.** Bir kaynak, kısa bir alıntı ve kaynağından oluşur: `"aynen kelimeler" [sozlesme.pdf, s. 7]`. any2llm alıntıyı o sayfada arar. 9. sayfadaysa sana 9. sayfada olduğunu söyler. Bir sayı değiştiyse, cümlenin geri kalanı tutsa bile kontrolden geçmez.
- **Model belgenin tamamını okur.** Yerel "dosyalarınla sohbet et" araçları belgeleri genelde parçalara bölüp modele yalnızca ilgili görünen birkaç parçayı verir, bu sırada sayfa numaraları da çoğu zaman kaybolur. any2llm ise modele metnin tamamını `<page number="N">` etiketleriyle verir. Klasör modelin bağlamından büyükse bölüm bölüm okur ve her bölümden alıntıları toplar. Toplanan her alıntı, dosyandaki asıl cümlesiyle eşleştirilir. Böylece son cevap modelin yeniden yazdıklarından değil, gerçek cümlelerden kurulur.
- **Modelinin gerçek bağlamını kullanır.** Ollama, istek daha fazlasını istemedikçe [24 GB'tan az belleği olan GPU'larda modellere yalnızca 4k token bağlam verir](https://docs.ollama.com/context-length). any2llm her istekte bağlam boyutunu ayarlar ve bölümleri buna göre böler. Böylece uzun bir belgenin başı sessizce kaybolmaz.
- **Hiçbir şey bilgisayarından çıkmaz.** Metin çıkarma, OCR, model ve kontrol yerelde çalışır. `--api` ile uzak bir sunucu verirsen any2llm bir şey göndermeden önce seni uyarır.
- **Karışık klasörleri okur.** PDF (taranmış sayfalar için isteğe bağlı OCR ile), Word, PowerPoint, Excel (değerler ve formüller), EPUB, HTML, CSV, Markdown ve kaynak kod. Kimlik bilgisi dosyaları atlanır. Bozuk ya da şifreli dosyalar çalışmayı çökertmek yerine raporlanır.
- **11 dil konuşur.** Terminal ve istemler English, 中文, हिन्दी, Español, Français, العربية, বাংলা, Português, Русский, اردو ve Türkçe dillerinde.

## Yerel bir modelle sor

```sh
any2llm ask ./sozlesmeler "Hangi sözleşmeler otomatik yenileniyor ve kaç gün önceden bildirim gerekiyor?"
any2llm ask ./ders-notlari -r                 # soru yoksa döngü içinde sormaya devam et
any2llm ask demo --lang tr                    # örnek: slaytlar, bir PDF, bir Word dosyası ve bir tablo
```

any2llm bu bilgisayardaki model sunucusunu kendisi bulur: 11434 portunda Ollama, 1234'te LM Studio veya 8080'de llama.cpp. `--model` vermezsen en son kurulan sohbet modelini kullanır.

| Seçenek | Etkisi |
| --- | --- |
| `--model AD` | Modeli seç, örneğin `--model qwen3:8b` |
| `--context TOKEN` | İstek başına bağlam boyutu (Ollama'da varsayılan 8192, modelin üst sınırını aşmaz) |
| `--api URL` | OpenAI uyumlu herhangi bir sunucu, örneğin `--api http://localhost:1234/v1`. Anahtar gerekiyorsa `ANY2LLM_API_KEY` ayarla. |
| `-r`, `--exclude GLOB`, `--ocr` | Paketlemedeki gibi: alt klasörler, atlanacak yollar ve taranmış sayfalar için OCR |
| `--no-check` | Kaynak kontrolünü atla |

**Hangi model?** Küçük instruct modeller alıntı biçimine iyi uyar. Laptop RTX 4050 (6 GB) üzerinde `qwen3:4b-instruct`, 17 sayfalık örnek kira sözleşmesiyle ilgili soruları komut satırından 5 ila 7 saniyede cevapladı. [`examples/eval_lease.py`](examples/eval_lease.py) ona 9 beklenen bilgi içeren beş soru soruyor: bir kez 8.192 token bağlamla, bir kez de sözleşmeyi üç bölümde okumak zorunda kaldığı 2.048 token'la. İki ayarın üçer turunda da her cevapta 9 bilginin hepsi vardı ve 9 kaynağın hepsi kontrolden geçti. Düşünen (thinking) modeller de çalışır ama daha yavaştır. any2llm onların akıl yürütmesini cevaptan ayrı tutar.

## Herhangi bir sohbetin cevabını kontrol et

Kontrol edilmiş kaynaklar için sohbet değiştirmen gerekmez.

1. `any2llm ./belgeler` çalıştır. Panoya koyduğu istem, sohbetten alıntıları `"aynen kelimeler" [dosya, s. N]` biçiminde ister.
2. Dosyaları ekle ve istemi ChatGPT, Claude, Gemini ya da yerel bir sohbete yapıştır.
3. Cevabı kopyala ve `any2llm check ./belgeler` çalıştır. Pano otomatik okunur. İstersen bir dosya da verebilirsin (`any2llm check ./belgeler cevap.md`) ya da cevabı komuta yönlendirebilirsin.

```text
✗  4 kaynaktan 2 tanesi orijinal belgelerle eşleşiyor
  ✗ [lease-agreement.pdf, p. 12] alıntı belirtilen sayfada değil, 14. sayfada
  ✗ [lease-agreement.pdf, p. 6] alıntı bu kaynakta bulunamadı
      "The deposit is refunded within 14 days after the Tenant returns the keys"
  ✓ [lease-agreement.pdf, p. 8] alıntı belirtilen yerde bulundu
  ✓ [house-rules.txt] alıntı belirtilen yerde bulundu
```

Çıkış kodu yalnızca tüm kaynaklar doğrulandığında 0 olur, `--json` ise makinenin okuyabileceği bir rapor yazar. Bu da kontrolü betiklerde ve CI'da kullanmayı kolaylaştırır.

<details>
<summary>Ne eşleşme sayılır?</summary>

- Büyük/küçük harf, satır sonları, tirelenme, kıvrık tırnaklar, tireler ve tablo çizgileri dikkate alınmaz. Alıntının içindeki üç nokta (`…`) aradaki metni atlayabilir.
- Küçük bir kelime farkı olan uzun bir alıntı *küçük farklarla bulundu* olarak raporlanır. Değişmiş bir sayı, tarih ya da tutar her zaman kontrolden kalır.
- Kaynaklar köşeli parantez veya normal parantez kullanabilir, birden çok kaynak listeleyebilir (`[a.pdf, s. 2; b.xlsx]`), sayfa aralığı verebilir (`s. 3–5`) ya da başka dillerin sayfa kısaltmalarını kullanabilir (`p. 3`, `стр. 4`, `第3页`).
- Alıntısı olmayan bir kaynak *kontrol edilecek alıntı yok* olarak listelenir. Kontrol, alıntıların belirtilen yerde olduğunu doğrular. Akıl yürütmeyi ya da hesaplamayı değerlendirmez.

</details>

## Claude Code eklentisi

```text
/plugin install any2llm --marketplace ahmetemreapo/any2llm
```

Eski Claude Code sürümlerinde önce `/plugin marketplace add ahmetemreapo/any2llm`, sonra `/plugin install any2llm@any2llm` çalıştır.

Sonra düz cümleyle sor, örneğin *"./kira klasöründeki sözleşme evcil hayvanlar ve taşınma hakkında ne diyor?"* Skill klasörü any2llm ile çıkarır, alıntılı bir cevap taslağı yazar, taslağı `any2llm check` ile kontrol eder, kalan hataları düzeltir ve her alıntının kontrol edildiğini söyleyen bir satırla bitirir. Örnek kira sözleşmesiyle yapılan bir denemede Claude 10 kaynak yazdı, 10'u da kontrolden geçti. Skill için PATH'te `any2llm`, `uvx` veya `pipx` olmalı.

Skill [Agent Skills](https://agentskills.io) biçimini izler, bu yüzden [`plugin/skills/any2llm`](plugin/skills/any2llm/SKILL.md) klasörünü skill destekleyen başka bir ajana da kopyalayabilirsin.

## Claude Desktop, Cursor ve diğer MCP uygulamalarında kullan

`any2llm mcp`, üç araçlı yerel ve salt okunur bir [Model Context Protocol](https://modelcontextprotocol.io) sunucusu başlatır: `list_documents`, `read_documents` (sayfa etiketli Markdown, paketler halinde) ve `check_citations`. Sunucu modele cevaplamadan önce taslağını kontrol etmesini söyler ve verdiğin klasörün dışını asla okumaz.

```sh
claude mcp add any2llm -- uvx any2llm mcp ~/Belgeler
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

Uygulama `uvx`'i bulamazsa tam yolunu kullan (macOS ve Linux'ta `which uvx`, Windows'ta `where uvx`). pipx ile kurduysan `"command": "any2llm"` ve `"args": ["mcp", "/Users/sen/Belgeler"]` kullan. Taranmış sayfaları okumak için klasörden sonra `--ocr` veya `--ocr-lang tur` ekle.

</details>

## Dosyaları herhangi bir sohbete ekle

```sh
any2llm "./belgeler"          # yolda boşluk varsa tırnakları koru
any2llm ./belgeler -r         # alt klasörleri de ekle
any2llm ./belgeler --task "Tüm ödeme son tarihlerini ve kimin ödeyeceğini bul"
```

1. İlk çalıştırmada dilini, ayrıntı düzeyini ve çıktı klasörünün açılıp açılmayacağını seç.
2. Dosyaları seç, `_llm_pack/` içindeki numaralı Markdown dosyalarını ekle ve istemi yapıştır (`PROMPT.txt` olarak da kaydedilir).
3. Birden çok paket varsa terminalin yazdığı yükleme sırasını izle ve aynı sohbette paketler arasında devam kelimesini gönder.
4. Son cevabı kopyala ve `any2llm check ./belgeler` çalıştır.

Hiçbir şey kurmadan bir sohbette denemek istersen hazır çıktılar [examples/](examples/README.tr.md) klasöründe.

## Betiklerde ve yönlendirmelerde kullan

`--stdout`, bölünmemiş tek paketi standart çıktıya yazar, ilerleme ve uyarıları standart hataya gönderir. Okunabilir tüm dosyaları seçer ve diske hiçbir şey yazmaz.

```sh
any2llm ./sozlesmeler --stdout | claude -p "Hangi sözleşme otomatik yenileniyor? PDF sayfasını belirt."
any2llm ./makaleler -r --stdout | llm "Bu makalelerdeki örneklem büyüklüklerini karşılaştır"
any2llm ./notlar --stdout > notlar-paketi.md
```

<details>
<summary>Tüm komut satırı seçenekleri</summary>

| Seçenek | Etkisi |
| --- | --- |
| `-r`, `--recursive` | Alt klasörleri ekle |
| `-y`, `--yes` | Okunabilir tüm dosyaları sormadan seç |
| `--stdout` | Bölünmemiş tek paketi standart çıktıya yaz |
| `--task METİN` | Sorunu üretilen isteme ekle |
| `--max-tokens SAYI` | Paket başına token sınırı |
| `--lang KOD` | Terminal ve istem dili: `en`, `zh`, `hi`, `es`, `fr`, `ar`, `bn`, `pt`, `ru`, `ur`, `tr` |
| `--ocr`, `--ocr-lang DİL` | Metin çıkarılamayan PDF sayfalarında OCR (örneğin `eng+tur`) |
| `--exclude GLOB` | Eşleşen yolları atla (tekrarlanabilir). Kök `.gitignore` kuralları da uygulanır. |
| `-o DİZİN`, `--output DİZİN` | Çıktı klasörü (varsayılan `_llm_pack`) |
| `--details` | Atlanan her dosyayı listele |
| `--plain` | Onay kutuları yerine numaralı menüler |
| `--no-open`, `--no-clipboard` | Çıktı klasörünü açma ya da istemi panoya kopyalama |
| `--include-sensitive` | Kimlik bilgisine benzeyen dosyaları da ekle |
| `ask`, `check`, `mcp`, `setup`, `demo` | Yerel modele sor, cevabı kontrol et, MCP sunucusunu başlat, ayarları değiştir ya da örneği çalıştır |
| `--version` | Sürümü yaz |

Tam başvuru: [docs/SPEC.md](docs/SPEC.md#command-line-options)

</details>

## Neler çıkarılır?

| Biçim | Sonuç |
| --- | --- |
| PDF | Her fiziksel sayfanın metni `<page>` etiketleri içinde. Metni olmayan sayfalar işaretlenir, isteğe bağlı OCR bunları okuyabilir. |
| Word (`.docx`) | Paragraflar ve tablolar, belgedeki sırayla |
| PowerPoint (`.pptx`) | Metin ve tablolar, slayt slayt |
| Excel (`.xlsx`) | Görünür sayfalar tablo olarak, önbellekteki değerler ve formüllerle |
| EPUB | Okuma sırasına göre bölümler. DRM korumalı kitaplar atlanır. |
| HTML | Kaydedilmiş sayfalar başlık, liste ve tablolarıyla okunabilir metin olarak. Şablonlar kod olarak kalır. |
| Metin ve kod | Markdown, CSV, JSON, YAML ve kaynak kod, boşluklar korunarak |

Grafikler, görseller ve sayfa düzeni çıkarılmaz. Cevap bir görsele dayanıyorsa orijinale bak.

## Gizlilik, sınırlar ve OCR

- Gizlilik: metin çıkarma, OCR, yerel modeller ve kontrol senin bilgisayarında çalışır. tiktoken ilk kullanımda sözlüğünü indirebilir. Yaygın kimlik bilgisi dosyaları (`*.pem`, `id_rsa`, `credentials*`, …) atlanır. Çıkarılan metindeki olası gizli anahtarlar işaretlenir ama çıktıda kalır, bu yüzden **bulut bir sohbete yüklemeden önce çıktıyı gözden geçir**. [Güvenlik politikasına](SECURITY.md) bak.
- Sınırlar: dosya başına en fazla 32 MiB, PDF başına 500 sayfa, Office veya EPUB arşivi başına sıkıştırılmamış 128 MiB ve dosya başına 120 saniye çıkarma süresi. Sohbetinin ek ve bağlam sınırları yine geçerlidir.

<details>
<summary>Taranmış PDF'ler için OCR kurulumu</summary>

Poppler (`pdftoppm`) ve ihtiyacın olan dil verileriyle [Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html) kur, klasörlerini mutlak yol olarak `PATH`'e ekle. İngilizce için `--ocr`, kurulu dilleri seçmek için `--ocr-lang` kullan, örneğin `--ocr-lang eng+tur`. OCR yalnızca kullanılabilir metni olmayan PDF sayfalarında çalışır ve tanınan sayfalar pakette işaretlenir. Önemli isim ve sayıları taramayla karşılaştır.

</details>

## Sık sorulanlar

**ChatGPT veya Claude PDF'lerimi zaten okuyamıyor mu?** Okuyabiliyor, onları kullanmaya devam edebilirsin. `any2llm check`, alıntılarından hangilerinin gerçekten dosyalarında ve hangi sayfada olduğunu gösterir. any2llm, çoğu sohbetin tek seferde alamadığı durumları da karşılar: onlarca dosya, Excel formülleri, EPUB'lar, taranmış sayfalar ve çevrimdışı çalışan modeller.

**Bu sadece RAG değil mi?** Vektör veritabanı ve embedding yok. Model metnin tamamını, gerekirse bölüm bölüm okur. Cevap da kontrol edebileceğin alıntılara bağlanır.

**✓ cevabın doğru olduğu anlamına mı gelir?** Alıntılanan kelimelerin belirtilen sayfada olduğu anlamına gelir. Alıntıyı oku ve modelin ondan çıkardığı sonuçlara, örneğin topladığı bir tutara, kendin de bak.

## Katkı

Hata bildirimleri, örnekler, çeviriler ve kod memnuniyetle karşılanır. [Katkı rehberiyle](CONTRIBUTING.md) ya da [good first issue](https://github.com/ahmetemreapo/any2llm/labels/good%20first%20issue) etiketli bir issue ile başla.

any2llm senin için yanlış bir kaynağı yakaladıysa bir yıldız, başkalarının da onu bulmasına yardım eder.

## Lisans

[MIT](LICENSE)
