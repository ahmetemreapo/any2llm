# Örnekler

Bu klasörde gerçek çıktı dosyaları duruyor. Birini yapay zekâ sohbetine ekle ve sayfa atıflarını kendin kontrol et. [English](README.md)

> [!TIP]
> GitHub eki metin olarak açarsa dosya görünümünün üstündeki indirme okuyla (↓) orijinal `.md` dosyasını kaydet.

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
