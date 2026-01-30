# app.py
from flask import Flask, render_template, request, jsonify
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

# --- ฟังก์ชันดึงน้ำจากกรมชลฯ (API) ---
def get_dam_data_api(dam_name):
    print(f"กำลังดึงข้อมูลเขื่อน: {dam_name}...")
    thai_zone = ZoneInfo("Asia/Bangkok")
    now = datetime.now(thai_zone)
    date_str = now.strftime('%Y-%m-%d')
    
    try:
        # ยิงตรงไปกรมชลฯ (Python ทำได้ ไม่ติด CORS)
        url = f'https://app.rid.go.th/reservoir/api/dam/public/{date_str}'
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return None
            
        json_data = response.json()
        
        if 'data' not in json_data:
            return None

        # ค้นหาชื่อเขื่อน (Logic เดิมของคุณ)
        search_name = dam_name.replace("เขื่อน", "").strip()
        
        for region in json_data['data']:
            if 'dam' in region:
                for dam in region['dam']:
                    if search_name in dam['name']:
                        return {
                            'percent_storage': dam['percent_storage'],
                            'storage': dam['storage'],
                            'capacity': dam['capacity']
                        }
    except Exception as e:
        print(f"Error fetching API: {e}")
        return None
    return None

# --- ฟังก์ชันดึงฝนด้วย Selenium (Web Scraping) ---
def get_rain_forecast_selenium(province):
    print(f"กำลังดึงพยากรณ์อากาศจังหวัด: {province}...")
    url = f"https://www.tmd.go.th/weatherForecast7DaysWidget?province={province}"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage") # <--- ต้องเพิ่มบรรทัดนี้
    chrome_options.add_argument("--disable-gpu")           # <--- ต้องเพิ่มบรรทัดนี้
    
    try:
        # ติดตั้ง Driver อัตโนมัติ (ไม่ต้องโหลดเอง)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(url)
        time.sleep(1.5) # รอโหลดนิดนึง
        
        # เข้า iframe
        try:
            iframe = driver.find_element(By.CSS_SELECTOR, "iframe#widget")
            driver.switch_to.frame(iframe)
        except:
            pass # บางทีมันอาจจะไม่มี iframe ถ้าเน็ตช้า

        # ดึง % ฝน
        elements = driver.find_elements(By.XPATH, "//div[contains(text(), 'ฝน')]")
        rain_probs = []
        
        for el in elements:
            text = el.text
            match = re.search(r"(\d+)%", text)
            if match:
                rain_probs.append(int(match.group(1)))
        
        driver.quit()

        if not rain_probs:
            return 30, 1 # ถ้าหาไม่เจอจริงๆ ให้คืนค่า Default (กันระบบล่ม)
            
        # หาค่าสูงสุด (Logic เดิม)
        max_rain = max(rain_probs)
        days_ahead = rain_probs.index(max_rain)
            
        return max_rain, days_ahead

    except Exception as e:
        print(f"Selenium Error: {e}")
        try:
            driver.quit()
        except:
            pass
        return 40, 1 # คืนค่า Default กรณี Error

# --- Route เชื่อมต่อหน้าเว็บ ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    # รับค่าจากหน้าเว็บ (JS ส่งมา)
    data = request.json
    dam_name = data.get('dam_name')
    province = data.get('province')
    
    # 1. ดึงข้อมูลน้ำ (API)
    dam_data = get_dam_data_api(dam_name)
    
    # 2. ดึงข้อมูลฝน (Selenium)
    rain_percent, days_ahead = get_rain_forecast_selenium(province)
    
    if not dam_data:
        return jsonify({'error': 'ไม่พบข้อมูลเขื่อนในวันนี้ (ระบบกรมชลฯ อาจขัดข้อง)'}), 500

    # 3. วิเคราะห์ผล (Logic เดิม)
    dam_percent = dam_data['percent_storage']
    target_storage = dam_data['capacity'] * 0.5
    
    advice = ""
    status = "normal"

    if rain_percent > 50:
        if dam_percent >= 70:
            advice = f"⚠️ วิกฤต: น้ำสูง ({dam_percent}%) และมีแนวโน้มฝนตกหนัก แนะนำให้ระบายน้ำเหลือ {target_storage:,.0f} ล้าน ลบ.ม."
            status = "danger"
        else:
            advice = "เฝ้าระวัง: มีโอกาสฝนตกหนัก แต่ระดับน้ำยังรับได้"
    else:
        if dam_percent >= 70:
            advice = f"⚠️ เตือนภัย: น้ำสูง ({dam_percent}%) เกินเกณฑ์ ควรพร่องน้ำออกให้เหลือ {target_storage:,.0f} ล้าน ลบ.ม."
            status = "danger"
        else:
            advice = "✅ ปกติ: ปริมาณน้ำและฝนอยู่ในเกณฑ์ควบคุมได้"

    # ส่งผลลัพธ์กลับไปที่หน้าเว็บ
    return jsonify({
        'rain_percent': rain_percent,
        'days_ahead': days_ahead,
        'dam_percent': dam_percent,
        'storage': dam_data['storage'],
        'advice': advice,
        'status': status
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)