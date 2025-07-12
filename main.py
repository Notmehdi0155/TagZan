from flask import Flask, request
import requests
import os
import subprocess
from threading import Thread
import sys

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
    file_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").json()

    if 'result' not in file_info:
        print("❌ خطا در دریافت اطلاعات فایل:", file_info)
        return None

    file_path = file_info['result']['file_path']
    local_path = os.path.join(FILE_DIR, os.path.basename(file_path))
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    with open(local_path, 'wb') as f:
        f.write(requests.get(file_url).content)
    return local_path

# ---------- پردازش ویدیو ----------
def process_video(input_path, output_path):
    filter_text = (
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "text='@JAGH_TEL':fontcolor=white@0.25:fontsize=h/12:x=(w-text_w)/2:"
        "y='if(gte(t\\,20)*lte(mod(t-20\\,45)\\,5)\\,h-(mod(t-20\\,45))*h/5\\,if(lte(mod(t-20\\,45)\\,10)\\,-text_h+(mod(t-25\\,45))*h/5\\,NAN))'"
    )
    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-vf', filter_text,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-movflags', '+faststart',
        '-c:a', 'copy',
        output_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("⚠️ خطا در ffmpeg:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)

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
        if os.path.exists("last_video.txt"):
            os.remove("last_video.txt")
        send_message(chat_id, "✅ ربات ریست شد. لطفاً ویدیو را بفرستید.")
        return "ok"

    if "video" in message:
        file_id = message["video"]["file_id"]
        filepath = download_file(file_id)
        if not filepath:
            send_message(chat_id, "❌ خطا در دریافت فایل. لطفاً دوباره تلاش کنید.")
            return "ok"
        with open("last_video.txt", "w") as f:
            f.write(filepath)
        send_message(chat_id, "✅ ویدیو ذخیره شد. برای افزودن آیدی، دستور /addid را بزن.")
        return "ok"

    if text == "/addid":
        if not os.path.exists("last_video.txt"):
            send_message(chat_id, "❌ هیچ ویدیویی برای پردازش یافت نشد.")
            return "ok"
        with open("last_video.txt") as f:
            input_path = f.read().strip()
        output_path = input_path.replace(".mp4", "_tagged.mp4")

        send_message(chat_id, "⌛ در حال پردازش و افزودن آیدی متحرک...")

        def run():
            try:
                process_video(input_path, output_path)
                send_video(chat_id, output_path)
            except Exception as e:
                send_message(chat_id, f"❌ خطا در پردازش: {e}")
            finally:
                if os.path.exists(input_path): os.remove(input_path)
                if os.path.exists(output_path): os.remove(output_path)
                if os.path.exists("last_video.txt"): os.remove("last_video.txt")

        Thread(target=run).start()

    return "ok"

# ---------- تنظیم Webhook در اجرا ----------
def set_webhook():
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}")

if __name__ == '__main__':
    set_webhook()
    app.run(host="0.0.0.0", port=10000)
