from flask import Flask, request
import requests
import os
import subprocess
from threading import Thread
import sys
import uuid

# ----------- تنظیمات اصلی ------------
TOKEN = "7686139376:AAF0Dt-wMbZk3YsQKd78BFE2vNLEira0KOY"
ADMIN_ID = 6387942633
WEBHOOK_URL = "https://tagzan.onrender.com/webhook"

app = Flask(__name__)
FILE_DIR = "downloads"
os.makedirs(FILE_DIR, exist_ok=True)

# ---------- ابزارهای کمکی ----------
def send_message(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def send_video(chat_id, video_path):
    with open(video_path, 'rb') as video:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendVideo",
            data={"chat_id": chat_id, "supports_streaming": True},
            files={"video": video}
        )

def download_file(file_id):
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    response = requests.get(url)
    try:
        file_info = response.json()
    except Exception as e:
        print("❌ خطا در parsing JSON:", response.text)
        return None

    if 'result' not in file_info:
        print("❌ پاسخ ناقص دریافت شد:", file_info)
        return None

    file_path = file_info['result']['file_path']
    local_path = os.path.join(FILE_DIR, os.path.basename(file_path))
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    try:
        video_data = requests.get(file_url)
        if video_data.status_code != 200:
            print(f"❌ خطا در دانلود فایل از تلگرام: کد {video_data.status_code}")
            return None
        with open(local_path, 'wb') as f:
            f.write(video_data.content)
        return local_path
    except Exception as e:
        print("❌ خطا در ذخیره‌سازی فایل:", e)
        return None

# ---------- پردازش ویدیو ----------
def process_video(input_path, output_path):
    filter_text = (
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "text='@JAGH_TEL':fontcolor=white@0.25:fontsize=h/12:x=(w-text_w)/2:"
        "y='if(gte(t\\,20)*lte(mod(t-20\\,45)\\,5)\\,h-(mod(t-20\\,45))*h/5\\,if(lte(mod(t-20\\,45)\\,10)\\,-text_h+(mod(t-25\\,45))*h/5\\,NAN))'"
    )
    cmd = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error',
        '-i', input_path,
        '-vf', filter_text,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-threads', '1',
        '-movflags', '+faststart',
        '-c:a', 'copy',
        output_path
    ]
    try:
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        print(f"خطا در پردازش ویدیو: {e}")
        return False

# ---------- صف پردازش ----------
def queue_job(chat_id, file_path):
    temp_id = uuid.uuid4().hex
    output_path = file_path.replace(".mp4", f"_tagged_{temp_id}.mp4")

    def job():
        send_message(chat_id, "⌛ در حال پردازش... لطفاً صبور باشید.")
        success = process_video(file_path, output_path)
        if success:
            send_video(chat_id, output_path)
        else:
            send_message(chat_id, "❌ خطا در پردازش ویدیو. لطفاً ویدیوی کوتاه‌تر یا سبک‌تری امتحان کنید.")
        for path in [file_path, output_path]:
            if os.path.exists(path): os.remove(path)

    Thread(target=job).start()

# ---------- هندل وبهوک ----------
@app.route('/')
def index():
    return 'ربات فعال است'

@app.route('/webhook', methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return "ok"

    message = data.get("message") or data.get("edited_message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]

    if user_id != ADMIN_ID:
        send_message(chat_id, "⛔ شما اجازه دسترسی ندارید.")
        return "ok"

    text = message.get("text", "")

    if text == "/start":
        send_message(chat_id, "✅ ربات آماده است. لطفاً ویدیو را بفرستید.")
        return "ok"

    if "video" in message:
        file_id = message["video"]["file_id"]
        filepath = download_file(file_id)
        if not filepath:
            send_message(chat_id, "❌ خطا در دریافت فایل. لطفاً دوباره تلاش کنید.")
            return "ok"
        send_message(chat_id, "📥 ویدیو دریافت شد. وارد صف پردازش شد.")
        queue_job(chat_id, filepath)
        return "ok"

    return "ok"

# ---------- تنظیم Webhook در اجرا ----------
def set_webhook():
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}")

if __name__ == '__main__':
    set_webhook()
    app.run(host="0.0.0.0", port=10000)
