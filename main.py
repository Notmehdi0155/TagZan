from flask import Flask, request
import requests
import os
import subprocess
from threading import Thread
import uuid
import time

# ----------- تنظیمات اصلی ------------
TOKEN = "7686139376:AAF0Dt-wMbZk3YsQKd78BFE2vNLEira0KOY"
ADMIN_ID = 6387942633
WEBHOOK_URL = "https://tagzan.onrender.com/webhook"

app = Flask(__name__)
FILE_DIR = "downloads"
os.makedirs(FILE_DIR, exist_ok=True)
user_last_file = {}

# ---------- ابزارهای کمکی ----------
def send_message(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text})

def send_video(chat_id, video_path):
    with open(video_path, 'rb') as video:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendVideo", data={"chat_id": chat_id, "supports_streaming": True}, files={"video": video})

def download_file(file_id, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    r = requests.get(url).json()
    if 'result' not in r:
        send_message(chat_id, "⚠️ خطا در دریافت فایل. لطفاً ویدیو را دوباره فوروارد کنید یا به صورت فایل بفرستید.")
        return None

    file_path = r['result']['file_path']
    local_path = os.path.join(FILE_DIR, os.path.basename(file_path))
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    try:
        with requests.get(file_url, stream=True) as res:
            res.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in res.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return local_path
    except Exception as e:
        app.logger.error(f"❌ خطا در دانلود فایل: {e}")
        return None

# ---------- پردازش ویدیو ----------
def process_video(input_path, output_path):
    filter_text = (
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "text='@JAGH_TEL':fontcolor=white@0.25:fontsize=h/12:x=(w-text_w)/2:"
        "y='if(gte(mod(t-20\\,45)\\,0)*lte(mod(t-20\\,45)\\,5)\\,(h+text_h)-(mod(t-20\\,45))*((h+text_h)/5)\\,NAN)'"
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
        app.logger.error(f"❌ خطا در پردازش ویدیو: {e}")
        return False

def queue_job(chat_id, input_path):
    output_path = input_path.replace(".mp4", f"_tagged_{uuid.uuid4().hex}.mp4")

    def job():
        send_message(chat_id, "🎬 در حال افزودن تگ متحرک... لطفاً منتظر بمانید.")
        success = process_video(input_path, output_path)
        if success:
            send_video(chat_id, output_path)
        else:
            send_message(chat_id, "❌ خطا در پردازش ویدیو.")
        for f in [input_path, output_path]:
            if os.path.exists(f): os.remove(f)
        user_last_file.pop(chat_id, None)

    Thread(target=job).start()

@app.route('/')
def index():
    return 'ربات فعال است'

@app.route('/webhook', methods=["POST"])
def webhook():
    data = request.get_json()
    if not data: return "ok"
    msg = data.get("message") or data.get("edited_message")
    if not msg: return "ok"

    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text = msg.get("text", "")

    if user_id != ADMIN_ID:
        send_message(chat_id, "⛔ شما اجازه دسترسی ندارید.")
        return "ok"

    if text == "/start":
        send_message(chat_id, "🎥 لطفاً ویدیوی خود را فوروارد کنید. سپس /tag را بفرستید.")
        return "ok"

    if text == "/tag":
        if chat_id in user_last_file:
            queue_job(chat_id, user_last_file[chat_id])
        else:
            send_message(chat_id, "📭 لطفاً ابتدا یک ویدیو ارسال کنید.")
        return "ok"

    file_id = None
    if "video" in msg:
        file_id = msg["video"]["file_id"]
    elif "document" in msg and msg["document"].get("mime_type", "").startswith("video"):
        file_id = msg["document"]["file_id"]

    # اگر پیام فورواردی بود، ربات آن را به خودش copy می‌کند و از فایل جدید استفاده می‌کند
    if file_id and "forward_origin" in msg:
        copy_resp = requests.post(f"https://api.telegram.org/bot{TOKEN}/copyMessage", json={
            "chat_id": ADMIN_ID,
            "from_chat_id": chat_id,
            "message_id": msg["message_id"]
        }).json()

        if copy_resp.get("ok"):
            new_file_id = copy_resp["result"].get("video", {}).get("file_id") or \
                           copy_resp["result"].get("document", {}).get("file_id")
            if new_file_id:
                file_id = new_file_id

    if file_id:
        path = download_file(file_id, chat_id)
        if path:
            user_last_file[chat_id] = path
            send_message(chat_id, "✅ ویدیو ذخیره شد. برای افزودن تگ /tag را بفرست.")
        return "ok"

    return "ok"

def set_webhook():
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}")

if __name__ == '__main__':
    set_webhook()
    app.run(host="0.0.0.0", port=10000)
    
