# OPENVPNHALKBANK Bot Kullanım Kılavuzu (Çocuk gibi açıklama)

## 1. Nedir bu bot?
Bu program, internet üzerinden bir "VPN" (Sanal Özel Ağ) açıp kapatarak, botun farklı ülkelerden internete bağlanmasını sağlar. Böylece "kişilik" gibi davranabilir.

## 2. Nereye koyduk?
`C:\Users\user\Desktop\OPENVPNHALKBANK` klasörünün içine tüm bot dosyaları (kara‑bot ve **vpn_manager.py**) yerleştirildi.

## 3. Nasıl çalıştırılır?
1. **OpenVPN** programını bilgisayarına kur. (İndir: https://openvpn.net/community-downloads/ )
2. **ProtonVPN** veya başka bir VPN sağlayıcısından `.ovpn` dosyalarını al ve `C:\vpn\proton\` klasörüne koy. (Her dosya bir ülke için.)
3. `vpn_manager.py` dosyasını açıp aşağıdaki gibi ayarla (dosyadaki örnekleri kendine göre değiştir):
```python
configs = [
    r"C:\vpn\proton\US-LosAngeles.ovpn",
    r"C:\vpn\proton\DE-Frankfurt.ovpn",
    r"C:\vpn\proton\JP-Tokyo.ovpn",
]

vpn = VPNManager(config_paths=configs, max_queries=2000, max_failures=5)
vpn.start()
```
4. Botun ana dosyasını (`halk.py` ya da `main.py`) **Python** ile çalıştır:
```powershell
python halk.py   # ya da botun ana dosyası neyse onu
```
5. Bot bir iş yapınca (örneğin bir mesaj gönderdiğinde) **başarılı** olduğunu söylemek için:
```python
vpn.record_success()
```
   Eğer bir hata olursa (bağlantı koptuysa) **başarısız** diyorsun:
```python
vpn.record_failure()
```
   Bu sayede 2000 başarılı işlemden sonra ya da 5 kez üst üste hata alındığında otomatik başka bir ülkeye geçer.

## 4. En basit test
Botu başlatmadan önce terminalde şunu çalıştır:
```powershell
ping 8.8.8.8
```
Internet bağlanıyorsa `Reply from ...` görürsün.
Bot çalıştıktan sonra aynı komutu tekrar yap; eğer VPN üzerinden gidiyorsa IP değişmiş olacaktır.

## 5. Windows'ta otomatik başlatmak (isteğe bağlı)
Task Scheduler (Görev Zamanlayıcı) kullanarak `python C:\Users\user\Desktop\OPENVPNHALKBANK\vpn_manager.py` komutunu bilgisayar açıldığında çalıştırabilirsin.

---
**İpucu:** Botun çalıştığı klasörde `requirements.txt` varsa `pip install -r requirements.txt` ile gerekli paketleri kur.
