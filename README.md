# SecurityBridgeAI - SAP Security Log Analysis Agent

SecurityBridgeAI, SAP güvenlik loglarını analiz etmek, tehditleri belirlemek ve yöneticilere doğal dilde (Türkçe) rapor sunmak için geliştirilmiş, **Llama 3.1 LLM** destekli akıllı bir ajandır.

Proje, kullanıcıların teknik sorgu dilleri (SQL, Elasticsearch DSL) bilmesine gerek kalmadan, sadece Türkçe soru sorarak karmaşık veri analizleri yapmasına olanak tanır.

## 🚀 Özellikler

-   **Türkçe Doğal Dil Desteği:** "En çok hata alan kullanıcı kim?", "Geçen haftaya göre risk durumu nedir?" gibi soruları anlar.
-   **Akıllı Aggregation:** Kullanıcı bazlı, terminal bazlı veya listener (alarm kodu) bazlı gruplamaları otomatik algılar.
-   **Trend Analizi:** "Artış", "değişim", "trend" gibi kavramları anlayarak zaman eksenli analiz (günlük/haftalık grafik) yapar.
-   **Dinamik Şema:** Veritabanındaki güncel kullanıcı, sistem ve program isimlerini öğrenerek sorguları buna göre optimize eder.
-   **Önceliklendirme:** Alarm kodlarını (Örn: 1079) kritiklik seviyesine göre sınıflandırır ve raporlar.

## 📂 Proje Yapısı

### Ana Dizin
-   **`ingest_data.py`**: Excel formatındaki SAP loglarını okuyup Elasticsearch'e indexleyen script. Tarih/Saat birleştirme ve veri temizliği yapar.
-   **`priority_config.json`**: Alarm kodlarının ve aksiyonların kritiklik seviyelerini (Kritik, Yüksek, Orta, Düşük) belirleyen ayar dosyası.
-   **`requirements.txt`**: Projenin çalışması için gereken Python kütüphaneleri.
-   **`docker-compose.yml`**: Elasticsearch ve Kibana'yı ayağa kaldırmak için konteyner konfigürasyonu.

### Kaynak Kodları (`src/`)
-   **`main.py`**: Ajanı başlatan, kullanıcıdan girdi alan ve ekrana basan ana CLI uygulaması.
-   **`agent.py`**: Ajanın beyni. LLM istemcisi, veritabanı istemcisi ve şema yöneticisini koordine eder. "Soru -> Sorgu -> Sonuç -> Cevap" döngüsünü yönetir.
-   **`llm_client.py`**: Ollama (Llama 3.1) ile iletişim kuran modül. Hatalara karşı `retry` mekanizması ve JSON temizleme fonksiyonları içerir.
-   **`db_client.py`**: Elasticsearch ile iletişim kuran modül. Sorguları çalıştırır ve sonuçları döner.
-   **`prompts.py`**: LLM'e ne yapması gerektiğini anlatan "System Prompt"ları içerir. Ajanın zekası (Logic) büyük ölçüde buradaki Few-Shot örneklerinde saklıdır.
-   **`schema.py`**: Veritabanındaki benzersiz değerleri (Users, Programs, Systems) çekerek LLM'e "Grounding" (Gerçek veriye dayandırma) sağlar.
-   **`app_config.py`**: Sabit ayarlar (Elasticsearch adresi, Index adı, Model ismi vb.).

## 🛠️ Kurulum ve Çalıştırma

1.  **Gereksinimler:**
    -   Docker & Docker Compose
    -   Python 3.10+
    -   [Ollama](https://ollama.com/) ve `llama3.1:8b` modeli (`ollama pull llama3.1:8b`)

2.  **Veritabanını Başlat:**
    ```bash
    docker-compose up -d
    ```

3.  **Veriyi Yükle (İlk Kurulum):**
    ```bash
    python ingest_data.py
    ```

4.  **Ajanı Çalıştır:**
    ```bash
    python src/main.py
    ```

## 🧠 Nasıl Çalışır?

1.  **Soru:** Kullanıcı "En çok zafiyet üreten terminal hangisi?" diye sorar.
2.  **Anlama:** `agent.py`, soruyu ve veritabanı şemasını (`schema.py`) alıp `llm_client.py` üzerinden modele gönderir.
3.  **Sorgu Üretimi:** Model, `prompts.py` içindeki kurallara göre soruyu Elasticsearch JSON sorgusuna çevirir. (Örn: `terms` aggregation ile `Listener` alanını saydırır, `desc` sıralar).
4.  **Çalıştırma:** JSON sorgusu Elasticsearch'te çalıştırılır.
5.  **Cevaplama:** Çıkan ham JSON sonucu tekrar modele gönderilir ve model bunu "Bu terminal X adet zafiyet üretmiştir" şeklinde Türkçeye çevirir.

## 📝 Lisans
Bu proje özel kullanım içindir.
