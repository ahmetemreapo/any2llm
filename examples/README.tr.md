# Örnekler

Bu klasörde gerçek çıktı dosyaları duruyor. Birini yapay zekâ sohbetine ekle ve sayfa atıflarını kendin kontrol et. [English](README.md)

> [!TIP]
> GitHub eki metin olarak açarsa dosya görünümünün üstündeki indirme okuyla (↓) orijinal `.md` dosyasını kaydet.

## Sor ve kontrol et örneği: 17 sayfalık kira sözleşmesi

Kurgusal bir kira sözleşmesi (her bölümü ayrı sayfada olan bir PDF) ve binanın kuralları (metin). [Kaynak dosyalara göz at](lease/). Sözleşme [`make_lease_example.py`](make_lease_example.py) ile üretilir. Tüm isimler ve tutarlar uydurmadır. Dosyalar İngilizcedir.

Yerel bir modele sor:

```sh
any2llm ask examples/lease "Taşınmak için kaç ay önceden haber vermem gerekiyor ve depozitomu ne zaman geri alırım?"
```

Başka bir sohbetten gelen cevabı kontrol et. [`lease-chat-answer.md`](lease-chat-answer.md), içine iki hata bilerek konmuş bir örnek cevaptır: bir alıntı 14. sayfa yerine 12. sayfayı gösteriyor, bir başkası da "30 days" ifadesini "14 days" yapıyor.

```sh
any2llm check examples/lease examples/lease-chat-answer.md --lang tr
```

<details>
<summary>Beklenen sonuç</summary>

```text
✗  4 kaynaktan 2 tanesi orijinal belgelerle eşleşiyor
  ✗ [lease-agreement.pdf, p. 12] alıntı belirtilen sayfada değil, 14. sayfada
      "the Tenant may end the lease with three months' written notice"
  ✗ [lease-agreement.pdf, p. 6] alıntı bu kaynakta bulunamadı
      "The deposit is refunded within 14 days after the Tenant returns the keys"
  ✓ [lease-agreement.pdf, p. 8] alıntı belirtilen yerde bulundu
  ✓ [house-rules.txt] alıntı belirtilen yerde bulundu
✗ ile işaretli kısımlara güvenmeden önce orijinal sayfaları açın.
```

</details>

README'deki animasyon bu iki çalıştırmadan [`render_ask_demo.py`](render_ask_demo.py) ile üretilir.

## İş örneği: teslimat tarihleri

Bir tedarikçi teklifi (PDF), teslimat çizelgesi (Excel) ve toplantı notu (metin). [Kaynak dosyalara göz at](delivery-dates/).

1. [Teslimat tarihleri ekini](delivery-dates-pack/batch_01_of_1.md?plain=1) indir ve yapay zekâ sohbetine ekle.
2. Ekle birlikte şu soruyu gönder:

   > Pilot ve ana sevkiyat tarihlerini listele. Her tarih için Excel sayfasına ve orijinal PDF’in sayfasına atıf yap. Metni okunamayan sayfa varsa belirt.

3. [Orijinal tedarikçi teklifinin](https://raw.githubusercontent.com/ahmetemreapo/any2llm/main/examples/delivery-dates/supplier-offer.pdf#page=1) 1. ve 3. sayfalarını kontrol et.

<details>
<summary>Beklenen cevap</summary>

| Sevkiyat | Teslimat tarihi | Kaynaklar |
| --- | --- | --- |
| Pilot | 12 Mart 2027 | `delivery-schedule.xlsx`, Schedule sayfası ve `supplier-offer.pdf`, 1. sayfa |
| Ana | 26 Mart 2027 | `delivery-schedule.xlsx`, Schedule sayfası ve `supplier-offer.pdf`, 3. sayfa |

Paket, metni görsel içinde olduğu için 2. sayfayı işaretler. Navlun notunu okumak için orijinal sayfayı aç.

</details>

## Öğrenci örneği: vizeye hazırlık

Araştırma Yöntemleri için dört dosya (PDF, PowerPoint, Word ve Excel) tek ekte, [üretilen sohbet istemiyle](midterm/tr/PROMPT.txt) birlikte.

1. [Vizeye hazırlık ekini](midterm/tr/batch_01_of_1.md?plain=1) indir ve yapay zekâ sohbetine ekle.
2. Ekle birlikte şu soruyu gönder:

   > Ölçüm planı hangi araştırma desenine uyuyor? Her sınıfta neyin ölçüldüğünü Excel sayfasına, desenin tanımını da orijinal PDF’in sayfasına atıf yaparak açıkla.

3. Tanımı [orijinal PDF’in 2. sayfasından](https://raw.githubusercontent.com/ahmetemreapo/any2llm/main/src/any2llm/demo_assets/tr/ara%C5%9Ft%C4%B1rma-desenleri.pdf#page=2) kontrol et.

<details>
<summary>Beklenen cevap</summary>

Plan, eşdeğer olmayan karşılaştırma gruplu ön test–son test yarı deneysel desene uyuyor. Rastgele atama yapılmamış iki mevcut sınıfa etkinlikten önce ve sonra aynı 10 soruluk terim testi uygulanıyor. Sekiz dakika boyunca A sınıfı terimleri hafızadan hatırlıyor, B sınıfı ise terimleri yeniden okuyor. `ölçüm-planı.xlsx` dosyasındaki Ölçüm Planı sayfasına ve `araştırma-desenleri.pdf` dosyasının 2. sayfasına bak.

</details>

Aynı örneği kendi bilgisayarında `any2llm demo --lang tr --no-open` ile çalıştırabilirsin.
