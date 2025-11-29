# 👻 Ghosty

## Görüntü İşleme ile Temassız Bilgisayar Kontrolü

<img width="512" height="468" alt="ghosty (2)" src="https://github.com/user-attachments/assets/269ce4f0-4e18-483d-905f-715cf9045cb2" />

## Websitesine Göz Atmayı Unutmayın
https://ghosty-lilac.vercel.app

## 🚀 Proje Hakkında ve Özellikler

**Ghosty**, standart bir web kamerasını kullanarak el hareketlerinizi düşük gecikmeli, profesyonel bir giriş cihazına dönüştüren yenilikçi bir uygulamadır.

### Çekirdek Özellikler

* **Düşük Gecikmeli Thread Mimarisi:** Kamera görüntüsü (30 FPS) ve fare hareket motoru (**200 Hz**) tamamen ayrılmıştır. Bu sayede imleç hareketi kamera hızına takılmaz, daima akıcıdır.
* **Zero-Drift Tıklama (Smart Freeze):** Tıklama jesti başladığı anda imleci milisaniyeler öncesindeki stabil konuma geri sarar ve kilitler. Bu, parmak kapanmasından kaynaklanan kaymayı tamamen yok eder.
* **Adaptif Stabilizasyon:** El titremelerini kesmek için **Hareketli Ortalama (Moving Average)** filtresi kullanılır. 
* **Güvenli Hata Yönetimi:** Uygulama, kamera bulunamazsa veya bağlantı koparsa çökmez, kullanıcıya net bir uyarı verir ve kendini güvenle sonlandırır (RAM şişmesini önler).
* **Kişiselleştirme:** Tıklama kombinasyonları ve hassasiyet ayarları arayüzden değiştirilebilir.

---

## ⚙️ Teknik Mimari ve Çalışma Mantığı

Ghosty, kararlılığı artırmak için **Çift İş Parçacıklı (Dual-Threaded)** bir mimari kullanır ve Windows donanımıyla doğrudan etkileşime girer.

### Kullanılan Temel Teknolojiler
| Teknoloji | Görev | Önemi |
| :--- | :--- | :--- |
| **MediaPipe Hands** | **AI Motoru.** El tespiti ve 21 eklem noktasının takibi. | |
| **Python `ctypes`** | **Düşük Seviyeli Kontrol.** Windows API'sine (user32.dll) doğrudan erişim ve fare hareket emri gönderme. | Hız ve Gecikme Azaltma. |
| **`threading`** | **Performans.** Görüntü işleme ve fare kontrol yükünü ayırma. | |
| **Tkinter / ttk** | **Arayüz.** Ayar paneli ve minimize/restore etme. | |

### Mimari Akış
1.  **Vision Thread (Yavaş):** MediaPipe, kameradan gelen parmak konumunu tespit eder. Titremeyi azaltmak için **Hareketli Ortalama (Moving Average)** filtresi uygular ve sonucu Mouse Thread'e gönderir.
2.  **Mouse Thread (Hızlı):** Bağımsız olarak 200 Hz hızında çalışır. Temizlenmiş hedef koordinatları okur ve **Adaptif Yumuşatma** ile imleci akıcı bir şekilde ekranda hareket ettirir.
3.  **Güvenlik:** `cap.isOpened()` kontrolleri, uygulamanın kamera yokluğunda veya kopmalarda çökmesini önler.

---

## 🖱️ Kullanım Kılavuzu

Uygulama arka planda (Headless) çalışırken tüm kontrol el hareketleriyle sağlanır.

| Eylem | Hareket (Varsayılan) | Açıklama |
| :--- | :--- | :--- |
| **İmleç Kontrolü** | İşaret parmağını (Index Finger) hareket ettirme. | İmleç, parmağın stabil ortalama konumunu takip eder. |
| **Tek Tık** | Başparmak + İşaret/Orta Parmağı **hızla** birleştirip ayırma. | Smart Freeze ile kesin isabet sağlanır. |
| **Çift Tık** | Tek tık hareketini **0.4 saniye içinde** iki kez tekrarlama. | |
| **Sürükle (Drag)** | Tıklama hareketini **0.45 saniyeden uzun** süre kapalı tutma. | |
| **Uygulamayı Kapatma** | İki elin İşaret Parmaklarını birbirine değdirip **1 saniye** tutma. | Uygulamayı tamamen sonlandırır ve ayar penceresini geri yükler. |

---

## ⚠️ Kritik Uyarılar

* **Platform Kısıtlaması:** Bu uygulama yalnızca **Windows 10/11** üzerinde çalışır.
* **Anti-Cheat Riski:** Fare girdisini taklit etme mekanizması nedeniyle, bu uygulamayı rekabetçi online oyunlarda **ASLA kullanmayın.** Hesap yasağı riski yüksektir.
