from flask import Flask, request
import requests
import threading
import time
from config import BOT_TOKEN, WEBHOOK_URL, ADMIN_IDS, CHANNEL_TAG, PING_INTERVAL
from database import save_file, get_file, get_channels, add_channel, remove_channel, get_all_user_ids, save_user_id
from utils import gen_code

app = Flask(__name__)
URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
users = {}
pinging = True
active_users = set()

def send(method, data):
    response = requests.post(f"{URL}/{method}", json=data).json()
    print(f"Response from {method}: {response}")
    return response

def delete(chat_id, message_id):
    send("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

def is_joined(user_id, channel_link):
    try:
        username = channel_link.split("/")[-1]
        r = requests.get(f"{URL}/getChatMember", params={
            "chat_id": f"@{username}",
            "user_id": user_id
        }).json()
        return r.get("result", {}).get("status") in ["member", "administrator", "creator"]
    except:
        return False

def get_user_unjoined_channels(user_id):
    return [ch for ch in get_channels() if not is_joined(user_id, ch)]

def make_force_join_markup(channels, code):
    buttons = [[{"text": f"📢 کانال {i+1}", "url": ch}] for i, ch in enumerate(channels)]
    buttons.append([{"text": "✅ عضو شدم", "callback_data": f"checksub_{code}"}])
    return {"inline_keyboard": buttons}

def ping():
    while pinging:
        try:
            requests.get(WEBHOOK_URL)
        except:
            pass
        time.sleep(PING_INTERVAL)

threading.Thread(target=ping, daemon=True).start()

def monitor_subscriptions():
    while True:
        for uid in list(active_users):
            unjoined = get_user_unjoined_channels(uid)
            if unjoined:
                send("sendMessage", {
                    "chat_id": uid,
                    "text": "🚫 شما از کانال خارج شدی. لطفاً دوباره عضو شو.",
                    "reply_markup": make_force_join_markup(unjoined, "dummy")
                })
                active_users.remove(uid)
        time.sleep(1)

threading.Thread(target=monitor_subscriptions, daemon=True).start()

@app.route("/")
def index():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        msg = update["message"]
        uid = msg["from"]["id"]
        cid = msg["chat"]["id"]
        mid = msg["message_id"]
        text = msg.get("text", "")
        state = users.get(uid, {})

        save_user_id(uid)

        if text.startswith("/start "):
            code = text.split("/start ")[1]
            file_id = get_file(code)
            if file_id:
                unjoined = get_user_unjoined_channels(uid)
                if unjoined:
                    send("sendMessage", {
                        "chat_id": cid,
                        "text": "⛔️ برای دریافت فایل، ابتدا در کانال‌های زیر عضو شو:",
                        "reply_markup": make_force_join_markup(unjoined, code)
                    })
                    return "ok"
                if "|" in file_id:
                    message_ids = []
                    for fid in file_id.split("|"):
                        sent = send("sendDocument", {"chat_id": cid, "document": fid})
                        if sent and "result" in sent:
                            message_ids.append(sent["result"]["message_id"])
                    warn = send("sendMessage", {"chat_id": cid, "text": "⚠️ این محتوا تا ۲۰ ثانیه دیگر پاک می‌شود"})
                    if "result" in warn:
                        message_ids.append(warn["result"]["message_id"])
                    for mid in message_ids:
                        threading.Timer(20, delete, args=(cid, mid)).start()
                else:
                    sent = send("sendVideo", {"chat_id": cid, "video": file_id})
                    if "result" in sent:
                        mid = sent["result"]["message_id"]
                        warn = send("sendMessage", {"chat_id": cid, "text": "⚠️ این محتوا تا ۲۰ ثانیه دیگر پاک میشود"})
                        threading.Timer(20, delete, args=(cid, mid)).start()
                        if "result" in warn:
                            threading.Timer(20, delete, args=(cid, warn["result"]["message_id"])).start()
                active_users.add(uid)
            return "ok"

        if text == "/start":
            send("sendMessage", {"chat_id": cid, "text": "سلام خوش اومدی عزیزم واسه دریافت فایل مد نظرت از کانال @hottof روی دکمه مشاهده بزن ♥️"})

        elif text == "/panel" and uid in ADMIN_IDS:
            kb = {"keyboard": [[{"text": "🔞سوپر"}], [{"text": "🖼پست"}], [{"text": "🔐 عضویت اجباری"}], [{"text": "📢 ارسالی همگانی"}]], "resize_keyboard": True}
            send("sendMessage", {"chat_id": cid, "text": "سلام آقا مدیر 🔱", "reply_markup": kb})

        elif text == "🔞سوپر" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_super_files", "files": []}
            send("sendMessage", {"chat_id": cid, "text": "همه فایل‌هاتو بفرست. هر وقت تموم شد، بنویس مرحله بعد."})

        elif state.get("step") == "awaiting_super_files":
            if text.strip() == "مرحله بعد":
                if not state["files"]:
                    send("sendMessage", {"chat_id": cid, "text": "⛔️ هنوز فایلی نفرستادی."})
                else:
                    users[uid]["step"] = "awaiting_caption"
                    send("sendMessage", {"chat_id": cid, "text": "حالا کپشنتو بفرست ✍️"})
            elif any(k in msg for k in ["video", "photo", "document", "audio"]):
                fid = msg.get("video", msg.get("photo", msg.get("document", msg.get("audio")))) or {}
                if isinstance(fid, list):
                    fid = fid[-1]
                file_id = fid.get("file_id")
                if file_id:
                    users[uid]["files"].append(file_id)
                    send("sendMessage", {"chat_id": cid, "text": "✅ فایل ذخیره شد. ادامه بده یا بنویس مرحله بعد."})
            else:
                send("sendMessage", {"chat_id": cid, "text": "⚠️ فقط فایل رسانه‌ای (عکس، ویدیو، پی‌دی‌اف...) مجازه."})

        elif state.get("step") == "awaiting_caption":
            users[uid]["caption"] = text
            users[uid]["step"] = "awaiting_cover"
            send("sendMessage", {"chat_id": cid, "text": "اکنون عکس کاور را بفرست 📸"})

        elif state.get("step") == "awaiting_cover" and "photo" in msg:
            code = gen_code()
            file_ids = users[uid]["files"]
            all_files = "|".join(file_ids)
            save_file(all_files, code)
            link = f"<a href='https://t.me/Up_jozve_bot?start={code}'>مشاهده</a>\n\n{CHANNEL_TAG}"
            send("sendPhoto", {
                "chat_id": cid,
                "photo": msg["photo"][-1]["file_id"],
                "caption": users[uid]["caption"] + "\n\n" + link,
                "parse_mode": "HTML"
            })
            users.pop(uid)
            send("sendMessage", {
                "chat_id": cid,
                "text": "درخواست شما تایید شد✅️",
                "reply_markup": {"keyboard": [[{"text": "🔞سوپر"}], [{"text": "🖼پست"}], [{"text": "🔐 عضویت اجباری"}], [{"text": "📢 ارسالی همگانی"}]], "resize_keyboard": True}
            })

        elif text == "📢 ارسالی همگانی" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_broadcast"}
            send("sendMessage", {
                "chat_id": cid,
                "text": "پیام مورد نظر برای ارسال همگانی را بفرستید (عکس یا متن همراه با کپشن). برای بازگشت، /panel را بزن.",
                "reply_markup": {"keyboard": [[{"text": "🔙 بازگشت"}]], "resize_keyboard": True}
            })

        elif text == "🔙 بازگشت" and state.get("step") == "awaiting_broadcast":
            users.pop(uid, None)
            send("sendMessage", {
                "chat_id": cid,
                "text": "به پنل برگشتی ⬅️",
                "reply_markup": {"keyboard": [[{"text": "🔞سوپر"}], [{"text": "🖼پست"}], [{"text": "🔐 عضویت اجباری"}], [{"text": "📢 ارسالی همگانی"}]], "resize_keyboard": True}
            })

        elif state.get("step") == "awaiting_broadcast":
            if not any(k in msg for k in ["photo", "text"]):
                send("sendMessage", {"chat_id": cid, "text": "⚠️ فقط متن یا عکس قابل ارسال است. یا /panel را بزن برای بازگشت."})
                return "ok"

            users.pop(uid, None)
            user_ids = get_all_user_ids()
            if "photo" in msg:
                photo_id = msg["photo"][-1]["file_id"]
                caption = msg.get("caption", "")
                for user_id in user_ids:
                    send("sendPhoto", {"chat_id": user_id, "photo": photo_id, "caption": caption})
            elif "text" in msg:
                for user_id in user_ids:
                    send("sendMessage", {"chat_id": user_id, "text": msg["text"]})
            send("sendMessage", {
                "chat_id": cid,
                "text": "✅ پیام به همه کاربران ارسال شد.",
                "reply_markup": {"keyboard": [[{"text": "🔞سوپر"}], [{"text": "🖼پست"}], [{"text": "🔐 عضویت اجباری"}], [{"text": "📢 ارسالی همگانی"}]], "resize_keyboard": True}
            })

    elif "callback_query" in update:
        cq = update["callback_query"]
        uid = cq["from"]["id"]
        cid = cq["message"]["chat"]["id"]
        mid = cq["message"]["message_id"]
        data = cq["data"]

        if data.startswith("checksub_"):
            code = data.split("_")[1]
            unjoined = get_user_unjoined_channels(uid)
            if not unjoined:
                send("deleteMessage", {"chat_id": cid, "message_id": mid})
                if code != "dummy":
                    file_id = get_file(code)
                    if file_id:
                        if "|" in file_id:
                            message_ids = []
                            for fid in file_id.split("|"):
                                sent = send("sendDocument", {"chat_id": cid, "document": fid})
                                if sent and "result" in sent:
                                    message_ids.append(sent["result"]["message_id"])
                            warn = send("sendMessage", {"chat_id": cid, "text": "⚠️ این محتوا تا ۲۰ ثانیه دیگر پاک می‌شود"})
                            if "result" in warn:
                                message_ids.append(warn["result"]["message_id"])
                            for mid in message_ids:
                                threading.Timer(20, delete, args=(cid, mid)).start()
                        else:
                            sent = send("sendVideo", {"chat_id": cid, "video": file_id})
                            if "result" in sent:
                                content_mid = sent["result"]["message_id"]
                                warn = send("sendMessage", {"chat_id": cid, "text": "⚠️ این محتوا تا ۲۰ ثانیه دیگر پاک می‌شود"})
                                threading.Timer(20, delete, args=(cid, content_mid)).start()
                                if "result" in warn:
                                    threading.Timer(20, delete, args=(cid, warn["result"]["message_id"])).start()
                        active_users.add(uid)
                    else:
                        send("sendMessage", {"chat_id": cid, "text": "❗ فایل یافت نشد."})
                else:
                    send("sendMessage", {"chat_id": cid, "text": "🙏 ممنون که هوامونو داری ❤️"})
            else:
                send("answerCallbackQuery", {
                    "callback_query_id": cq["id"],
                    "text": "❌ هنوز عضو همه کانال‌ها نیستی!",
                    "show_alert": True
                })

    return "ok"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
