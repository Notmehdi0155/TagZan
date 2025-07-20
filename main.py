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

# ------------------ ابزار ارسال ------------------
def send(method, data):
    response = requests.post(f"{URL}/{method}", json=data).json()
    print(f"Response from {method}: {response}")
    return response

def delete(chat_id, message_id):
    send("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

# ------------------ بررسی عضویت کانال ------------------
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

# ------------------ پینگ ------------------
def ping():
    while pinging:
        try:
            requests.get(WEBHOOK_URL)
        except:
            pass
        time.sleep(PING_INTERVAL)

threading.Thread(target=ping, daemon=True).start()

# ------------------ بررسی خروج کاربران ------------------
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

# ------------------ روت ها ------------------
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

        # ذخیره کاربر برای ارسال همگانی
        save_user_id(uid)

        # ---------- /start با کد ----------
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
                sent = send("sendVideo", {"chat_id": cid, "video": file_id})
                if "result" in sent:
                    mid = sent["result"]["message_id"]
                    send("sendMessage", {"chat_id": cid, "text": "⚠️این محتوا تا ۲۰ ثانیه دیگر پاک میشود "})
                    threading.Timer(20, delete, args=(cid, mid)).start()
                active_users.add(uid)
            return "ok"

        if text == "/start":
            send("sendMessage", {"chat_id": cid, "text": "سلام خوش اومدی عزیزم واسه دریافت فایل مد نظرت از کانال @hottof روی دکمه مشاهده بزن ♥️"})

        elif text == "/panel" and uid in ADMIN_IDS:
            kb = {"keyboard": [[{"text": "🔞سوپر"}], [{"text": "🖼پست"}], [{"text": "🔐 عضویت اجباری"}], [{"text": "📢 ارسالی همگانی"}]], "resize_keyboard": True}
            send("sendMessage", {"chat_id": cid, "text": "سلام آقا مدیر 🔱", "reply_markup": kb})

        elif text == "🔐 عضویت اجباری" and uid in ADMIN_IDS:
            channels = get_channels()
            lines = ["📋 لیست کانال‌های عضویت اجباری:"] + [f"🔗 {ch}" for ch in channels] if channels else ["❌ هیچ کانالی ثبت نشده"]
            lines.append("\n➕ برای اضافه کردن: `+https://t.me/...`\n➖ برای حذف: `-https://t.me/...`")
            send("sendMessage", {"chat_id": cid, "text": "\n".join(lines), "parse_mode": "Markdown"})

        elif uid in ADMIN_IDS and text.startswith("+https://t.me/"):
            add_channel(text[1:])
            send("sendMessage", {"chat_id": cid, "text": "✅ کانال اضافه شد."})

        elif uid in ADMIN_IDS and text.startswith("-https://t.me/"):
            remove_channel(text[1:])
            send("sendMessage", {"chat_id": cid, "text": "🗑 کانال حذف شد."})

        elif text == "📢 ارسالی همگانی" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_broadcast"}
            send("sendMessage", {"chat_id": cid, "text": "پیام مورد نظر برای ارسال همگانی را بفرستید (عکس یا متن همراه با کپشن)."})

        elif state.get("step") == "awaiting_broadcast":
            users.pop(uid)
            user_ids = get_all_user_ids()
            if "photo" in msg:
                photo_id = msg["photo"][-1]["file_id"]
                caption = msg.get("caption", "")
                for user_id in user_ids:
                    send("sendPhoto", {"chat_id": user_id, "photo": photo_id, "caption": caption})
            elif "text" in msg:
                for user_id in user_ids:
                    send("sendMessage", {"chat_id": user_id, "text": msg["text"]})
            send("sendMessage", {"chat_id": cid, "text": "✅ پیام به همه کاربران ارسال شد."})

        # ✅ این قسمت جدید است
        elif text == "🔞سوپر" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_files", "files": []}
            send("sendMessage", {"chat_id": cid, "text": "میتونی چندتا فایل برام بفرستی 📂\nوقتی تموم شد بزن ⏭ مرحله بعد", "reply_markup": {"keyboard": [[{"text": "⏭ مرحله بعد"}]], "resize_keyboard": True}})

        elif state.get("step") == "awaiting_files":
            if "document" in msg or "video" in msg or "photo" in msg:
                file = msg.get("document") or msg.get("video") or msg.get("photo")[-1]
                users[uid]["files"].append(file["file_id"])
                send("sendMessage", {"chat_id": cid, "text": "✅ فایل ذخیره شد. فایل بعدی رو بفرست یا مرحله بعد رو بزن."})
            elif text == "⏭ مرحله بعد":
                users[uid]["step"] = "awaiting_caption"
                send("sendMessage", {"chat_id": cid, "text": "حالا کپشن رو بفرست ✍️"})

        elif state.get("step") == "awaiting_caption":
            users[uid]["step"] = "awaiting_cover"
            users[uid]["caption"] = text
            send("sendMessage", {"chat_id": cid, "text": "یه عکس برای کاور بفرست 📸"})

        elif state.get("step") == "awaiting_cover" and "photo" in msg:
            cover_id = msg["photo"][-1]["file_id"]
            caption = users[uid]["caption"]
            files = users[uid]["files"]
            code = gen_code()
            for f in files:
                save_file(f, code)
            link = f"<a href='https://t.me/Up_jozve_bot?start={code}'>مشاهده</a>\n\n{CHANNEL_TAG}"
            send("sendPhoto", {
                "chat_id": cid,
                "photo": cover_id,
                "caption": caption + "\n\n" + link,
                "parse_mode": "HTML"
            })
            users.pop(uid)
            send("sendMessage", {
                "chat_id": cid,
                "text": "✅ ذخیره شد و آماده شد برای استفاده کاربرا",
                "reply_markup": {"keyboard": [[{"text": "🔞سوپر"}], [{"text": "🖼پست"}], [{"text": "🔐 عضویت اجباری"}], [{"text": "📢 ارسالی همگانی"}]], "resize_keyboard": True}
            })

        elif text == "🖼پست" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_forward"}
            send("sendMessage", {"chat_id": cid, "text": "محتوا رو برا فوروارد کن یادت نره تگ بزنی روش ✅️"})

        elif state.get("step") == "awaiting_forward" and ("video" in msg or "photo" in msg):
            users[uid]["step"] = "awaiting_post_caption"
            users[uid]["post_msg"] = msg
            send("sendMessage", {"chat_id": cid, "text": "یه کپشن خوشکل بزن حال کنم 😁"})

        elif state.get("step") == "awaiting_post_caption":
            post_msg = users[uid]["post_msg"]
            caption = text + "\n\n" + CHANNEL_TAG
            if "video" in post_msg:
                fid = post_msg["video"]["file_id"]
                send("sendVideo", {"chat_id": cid, "video": fid, "caption": caption})
            else:
                fid = post_msg["photo"][-1]["file_id"]
                send("sendPhoto", {"chat_id": cid, "photo": fid, "caption": caption})
            users[uid]["step"] = "awaiting_forward"
            send("sendMessage", {"chat_id": cid, "text": "بفرما اینم درخواستت ✅️ آماده ام پست بعدی رو بفرستی ارباب🔥"})

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
                        sent = send("sendVideo", {"chat_id": cid, "video": file_id})
                        if "result" in sent:
                            content_mid = sent["result"]["message_id"]
                            send("sendMessage", {
                                "chat_id": cid,
                                "text": "⚠️ این محتوا تا ۲۰ ثانیه دیگر پاک می‌شود"
                            })
                            threading.Timer(20, delete, args=(cid, content_mid)).start()
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
