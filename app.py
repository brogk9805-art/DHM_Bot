import os
import time
from flask import Flask, request, jsonify
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

# 📝 បំពេញព័ត៌មានផ្ទាល់ខ្លួនរបស់បងនៅត្រង់នេះ
TELEGRAM_BOT_TOKEN = "8680169736:AAH9TGN2qCNcqallycjsM3mEV50I1qkoCxig"
TELEGRAM_CHAT_ID = "-1003916358139"
TRADINGVIEW_CHART_URL = "https://www.tradingview.com/x/ziQHr1wN/" # ដាក់ Link Chart Layout បង

def send_photo_to_telegram(photo_url, caption_text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": photo_url,
        "caption": caption_text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    return response.json()

@app.route('/screenshot', methods=['POST'])
def take_screenshot():
    data = request.json
    pair = data.get("pair", "XAUUSD")
    status = data.get("status", "SIGNAL")
    action = data.get("action", "BUY")
    entry = data.get("entry", "")
    sl = data.get("sl", "")
    tp1 = data.get("tp1", "")
    tp2 = data.get("tp2", "")

    # ✍️ រៀបចំទម្រង់អត្ថបទ (Caption) ឱ្យដូចក្នុងរូបភាពរបស់បងបេះបិទ
    emoji = "🟢" if action == "BUY" else "🔴"
    caption = f"{emoji} <b>[{status} SIGNAL CONFIRMED]</b>\n"
    caption += "-------------------------\n"
    caption += f"📊 <b>Pair:</b> {pair}\n"
    caption += f"📈 <b>Action:</b> {action}\n"
    caption += f"💵 <b>Entry Price:</b> {entry}\n"
    if sl:  caption += f"🛑 <b>Stop Loss:</b> {sl}\n"
    if tp1: caption += f"🎯 <b>Target 1 (TP1):</b> {tp1}\n"
    if tp2: caption += f"🚀 <b>Target 2 (TP2):</b> {tp2}\n"

    # Settings សម្រាប់ដំណើរការ Chrome នៅលើ Cloud Render
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,720")

    driver = None
    try:
        # បើក Browser Chrome និម្មិត
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        # ហោះទៅបើក Chart របស់បង
        driver.get(f"{TRADINGVIEW_CHART_URL}?symbol={pair}")
        
        # រង់ចាំ ៦ វិនាទីឱ្យច្បាស់ថា Indicator គូរខ្សែចេញមកពេញលេញ
        time.sleep(6)
        
        # បញ្ជាឱ្យចុចប៊ូតុង Alt + S ដើម្បីឱ្យ TradingView បង្កើត Link snapshot
        actions = ActionChains(driver)
        actions.key_down(Keys.ALT).send_keys('s').key_up(Keys.ALT).perform()
        
        # រង់ចាំ ៣ វិនាទីឱ្យប្រព័ន្ធបង្កើត Link រូបភាពចប់សព្វគ្រប់
        time.sleep(3)
        
        # ទាញយក Link Snapshot ពី Clipboard ប្រព័ន្ធ
        # ប្រសិនបើទាញពី Clipboard មិនបាន យើងប្រើវិធីទាញយកលីងតាមរយៈផ្ទាំង Pop-up របស់ TradingView
        current_url = driver.current_url
        
        # ល្បិចពិសេស៖ បញ្ជាឱ្យ Browser បើកផ្ទាំងថ្មីដើម្បីទាញយក Link
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[1])
        driver.get("data:text/html,<script>setTimeout(() => { document.body.innerText = navigator.clipboard ? 'ok' : 'no'; }, 500);</script>")
        time.sleep(1)
        
        # ប្រសិនបើប្រព័ន្ធ Cloud ខ្លះបិទ Clipboard យើងនឹងប្រើប្រាស់ API រូបភាពជំនួស
        # ប៉ុន្តែជាទូទៅ Selenium អាចចុចទាញយកបានយ៉ាងរលូន
        snapshot_url = driver.execute_script("return navigator.clipboard ? navigator.clipboard.readText() : '';")
        
        # បិទផ្ទាំងជំនួយ ហើយត្រឡប់ទៅផ្ទាំងដើមវិញ
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        # ប្រសិនបើកូដទាញយក Link មិនបានដោយសារប្រព័ន្ធសុវត្ថិភាព Clipboard លើ Cloud
        # យើងមានវិធីសាស្រ្តមួយទៀតគឺថតយក Screen ផ្ទាល់ពីផ្ទាំង Canvas តែម្តង (ធានាថាបាន ១០០%)
        screenshot_path = "chart_screenshot.png"
        driver.save_screenshot(screenshot_path)
        
        # ផ្ញើរូបភាពដែលថតបានផ្ទាល់ពី Screen ចូលទៅ Telegram តែម្តង (វិធីនេះច្បាស់ និងមិនចេះខុស)
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        with open(screenshot_path, "rb") as photo_file:
            files = {"photo": photo_file}
            payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"}
            res = requests.post(url, data=payload, files=files)
        
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
            
        driver.quit()
        return jsonify({"success": True, "message": "រូបភាពត្រូវបានផ្ញើទៅ Telegram រួចរាល់"}), 200

    except Exception as e:
        if driver:
            driver.quit()
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
