# ใช้ Python เวอร์ชั่นเบาๆ
FROM python:3.9-slim

# 1. ติดตั้ง Google Chrome และ Dependencies ที่จำเป็น
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. ตั้งค่าโฟลเดอร์งาน
WORKDIR /app

# 3. ก๊อปปี้ไฟล์ในเครื่องเราขึ้นไปบน Server
COPY . /app

# 4. ติดตั้ง Python Library
RUN pip install --no-cache-dir -r requirements.txt

# 5. คำสั่งรันโปรแกรม (ใช้ gunicorn เพื่อความเสถียรบน server)
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app", "--timeout", "120"]