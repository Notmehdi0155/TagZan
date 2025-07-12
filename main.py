from flask import Flask, request
import requests
import os
import time
import subprocess
from threading import Thread

# تنظیمات
TOKEN = "7686139376:AAF0Dt-wMbZk3YsQKd78BFE2vNLEira0KOY"
ADMIN_ID = 6387942633  # آیدی عددی خودت
WEBHOOK_URL = "https://your-app-name.onrender.com/webhook"

app = Flask(__name__)

FILE_DIR = "downloads"
if not os.path.exists(FILE_DIR):
    os.makedirs(FILE_DIR)

def send_message(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def send_video(chat_id, video_path):
    with open(video_path, 'rb') as video:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendVideo", data={"chat_id": chat_id}, files={"video": video})

def download_file(file_id):
    file_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").json()
    file_path = file_info['result']['file_path']
    local_filename = os.path.join(FILE_DIR, os.path.basename(file_path))
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    response = requests.get(file_url)
    with open(local_filename, 'wb') as f:
        f.write(response.content)
    return local_filename

def process_video(input_path, output_path):
    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-vf',
        ("drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
         "text='@JAGH_TEL':fontcolor=white@0.25:fontsize=h/12:x=(w-text_w)/2:"
         "y='if(gte(mod(t\\,60)\\,0)*lte(mod(t\\,60)\\,7)\\,(h-text_h)-(t-mod(t\\,60))*h/7\\, NAN)'"
        ),
        '-c:a', 'copy',
        '-preset', 'veryfast',
        output_path
    ]
    subprocess.run(cmd)

@app.route('/')
def index():
    return 'OK'

@app.route('/webhook', methods=["POST"])
def webhook():
    data = request.get_json()
    if not data or "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]

    if user_id != ADMIN_ID:
        send_message(chat_id, "دسترسی نداری.")
        return "ok"

    if "video" in message:
        file_id = message["video"]["file_id"]
        filepath = download_file(file_id)
        filename = os.path.basename(filepath)
        with open("last_video.txt", "w") as f:
            f.write(filename)
        send_message(chat_id, "✅ ویدیو ذخیره شد. برای افزودن آیدی، دستور /addid رو بزن.")
        return "ok"

    if "text" in message and message["text"] == "/addid":
        if not os.path.exists("last_video.txt"):
            send_message(chat_id, "ویدیویی برای پردازش وجود نداره.")
            return "ok"

        with open("last_video.txt") as f:
            filename = f.read().strip()

        input_path = os.path.join(FILE_DIR, filename)
        output_path = os.path.join(FILE_DIR, "output_" + filename)

        send_message(chat_id, "⌛ در حال افزودن آیدی متحرک به ویدیو...")

        def run_processing():
            process_video(input_path, output_path)
            send_video(chat_id, output_path)
            os.remove(input_path)
            os.remove(output_path)
            os.remove("last_video.txt")

        Thread(target=run_processing).start()

    return "ok"

def set_webhook():
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}")

if __name__ == '__main__':
    set_webhook()
    app.run(host="0.0.0.0", port=10000)
