# ใช้ Python 3.9 แบบ Slim (เบาและทำงานไว)
FROM python:3.9-slim

# 1. ติดตั้งเครื่องมือพื้นฐานที่จำเป็น
# เราต้องใช้ wget เพื่อโหลด Chrome และ unzip
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 2. ติดตั้ง Google Chrome (แบบโหลดไฟล์ .deb ตรงๆ)
# วิธีนี้แก้ปัญหาเรื่อง Key และ Repository เก่าที่ทำให้ Error 127
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && apt-get clean

# 3. ตั้งค่าโฟลเดอร์งาน
WORKDIR /app

# 4. ก๊อปปี้ไฟล์โปรเจคทั้งหมดเข้าไป
COPY . /app

# 5. ติดตั้ง Library Python (Flask, Selenium, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# 6. คำสั่งรัน Server
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app", "--timeout", "120"]
