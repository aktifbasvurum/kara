# vpn_manager.py
import os
import sys
import glob
import random
import subprocess
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = BASE_DIR / "vpn_configs"
CREDENTIALS_FILE = BASE_DIR / "credentials.txt"

class VPNManager:
    def __init__(self, max_queries: int = 2000, max_failures: int = 5):
        self.max_queries = max_queries
        self.max_failures = max_failures
        self.query_count = 0
        self.failure_count = 0
        self.current_process = None
        self.current_config = None
        self.lock = threading.Lock()
        self.configs = []
        self._load_and_patch_configs()

    def _load_and_patch_configs(self):
        """vpn_configs klasorundeki tum ovpn dosyalarini bulur ve auth-user-pass yolunu ayarlar."""
        if not CONFIGS_DIR.exists():
            CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
            
        ovpn_files = list(CONFIGS_DIR.glob("*.ovpn"))
        if not ovpn_files:
            print(f"[VPN] UYARI: {CONFIGS_DIR} icinde hic .ovpn dosyasi bulunamadi!")
            return

        cred_str = str(CREDENTIALS_FILE).replace("\\", "/")
        for f in ovpn_files:
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                new_lines = []
                replaced = False
                for line in content.splitlines():
                    if line.strip().startswith("auth-user-pass"):
                        new_lines.append(f"auth-user-pass {cred_str}")
                        replaced = True
                    else:
                        new_lines.append(line)
                if not replaced:
                    new_lines.append(f"auth-user-pass {cred_str}")
                f.write_text("\n".join(new_lines), encoding="utf-8")
            except Exception:
                pass
        self.configs = ovpn_files
        print(f"[VPN] {len(self.configs)} adet VPN sunucu konfigurasyonu hazirlandi.")

    def stop(self):
        with self.lock:
            if self.current_process:
                print("[VPN] Eski baglanti kesiliyor...")
                try:
                    if sys.platform == "win32":
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.current_process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        subprocess.run(["taskkill", "/F", "/IM", "openvpn.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        self.current_process.terminate()
                        self.current_process.wait(timeout=3)
                except Exception:
                    pass
                self.current_process = None
                time.sleep(2)

    def change_country(self, reason="Periyodik Degisim"):
        with self.lock:
            self.stop()
            if not self.configs:
                self._load_and_patch_configs()
            if not self.configs:
                print("[VPN] HATA: Baglanacak .ovpn dosyasi yok! Lutfen vpn_configs klasorune dosya atin.")
                return False

            # Rastgele bir sunucu sec
            available = [c for c in self.configs if c != self.current_config] or self.configs
            chosen = random.choice(available)
            self.current_config = chosen

            print(f"\n[VPN DEGISIMI] Neden: {reason}")
            print(f"[VPN] Yeni Sunucuya Baglaniliyor: {chosen.name}...")

            # OpenVPN binary yolunu bul
            openvpn_bin = "openvpn"
            if sys.platform == "win32":
                default_path = Path(r"C:\Program Files\OpenVPN\bin\openvpn.exe")
                if default_path.exists():
                    openvpn_bin = str(default_path)

            cmd = [openvpn_bin, "--config", str(chosen)]
            # Arka planda calistir
            try:
                if sys.platform == "win32":
                    self.current_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    self.current_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                self.query_count = 0
                self.failure_count = 0
                print("[VPN] Baglantinin oturmasi icin 5 saniye bekleniyor...")
                time.sleep(5)
                return True
            except Exception as e:
                print(f"[VPN] OpenVPN baslatma hatasi: {e}")
                return False

    def record_query(self):
        with self.lock:
            self.query_count += 1
            if self.query_count % 100 == 0:
                print(f"[VPN] Yapilan sorgu sayisi: {self.query_count}/{self.max_queries}")
            if self.query_count >= self.max_queries:
                print(f"\n[VPN] {self.max_queries} sorgu kotasi doldu! Ulke degistiriliyor...")
                threading.Thread(target=self.change_country, args=("2000 Sorgu Kotasi Doldu",)).start()

    def record_success(self):
        with self.lock:
            self.failure_count = 0

    def record_failure(self):
        with self.lock:
            self.failure_count += 1
            print(f"[VPN] Ust uste baglanti hatasi sayisi: {self.failure_count}/{self.max_failures}")
            if self.failure_count >= self.max_failures:
                print(f"\n[VPN] {self.max_failures} defa ust uste baglanti hatasi alindi! Ulke degistiriliyor...")
                threading.Thread(target=self.change_country, args=("5 Defa Ust Uste Hata",)).start()

# Global nesne
vpn_bot = VPNManager()
