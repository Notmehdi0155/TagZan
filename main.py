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

        elif text == "🔞سوپر" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_video"}
            send("sendMessage", {"chat_id": cid, "text": "ای جان یه سوپر ناب برام بفرست 🍌"})

        elif text == "🖼پست" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_forward"}
            send("sendMessage", {"chat_id": cid, "text": "محتوا رو برا فوروارد کن یادت نره تگ بزنی روش ✅️"})

        elif state.get("step") == "awaiting_video" and "video" in msg:
            users[uid]["step"] = "awaiting_caption"
            users[uid]["file_id"] = msg["video"]["file_id"]
            send("sendMessage", {"chat_id": cid, "text": "منتظر کپشن خوشکلت هستم 💫"})

        elif state.get("step") == "awaiting_caption":
            users[uid]["step"] = "awaiting_cover"
            users[uid]["caption"] = text
            send("sendMessage", {"chat_id": cid, "text": "یه عکس برای پیش نمایش بهم بده 📸"})

        elif state.get("step") == "awaiting_cover" and "photo" in msg:
            file_id = users[uid]["file_id"]
            caption = users[uid]["caption"]
            cover_id = msg["photo"][-1]["file_id"]
            code = gen_code()
            save_file(file_id, code)
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
                "text": "درخواست شما تایید شد✅️",
                "reply_markup": {"keyboard": [[{"text": "🔞سوپر"}], [{"text": "🖼پست"}], [{"text": "🔐 عضویت اجباری"}], [{"text": "📢 ارسالی همگانی"}]], "resize_keyboard": True}
            })

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



# وضعیت موقت برای سوپر ادمین
superadmin_sessions = {}  # user_id: {files: [], step: 'collecting' | 'awaiting_cover' | 'awaiting_caption', cover: None, caption: None}

def reset_superadmin(user_id):
    if user_id in superadmin_sessions:
        del superadmin_sessions[user_id]

def send_admin_menu(chat_id):
    send("sendMessage", {
        "chat_id": chat_id,
        "text": "📤 لطفاً فایل‌های خود را ارسال کنید. سپس روی دکمه 'مرحله بعد' کلیک کنید.",
        "reply_markup": {
            "keyboard": [[{"text": "مرحله بعد"}]],
            "resize_keyboard": True
        }
    })


# ------------ سوپر ادمین آپلود چندفایلی ------------

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        msg = update["message"]
        user_id = msg["from"]["id"]
        text = msg.get("text")
        chat_id = msg["chat"]["id"]

        if user_id in ADMIN_IDS:
            session = superadmin_sessions.setdefault(user_id, {"files": [], "step": "collecting", "cover": None, "caption": None})

            # مرحله دریافت فایل‌ها
            if session["step"] == "collecting":
                if "document" in msg or "video" in msg or "photo" in msg:
                    if "photo" in msg:
                        file_id = msg["photo"][-1]["file_id"]
                    elif "video" in msg:
                        file_id = msg["video"]["file_id"]
                    else:
                        file_id = msg["document"]["file_id"]

                    session["files"].append(file_id)
                    send("sendMessage", {"chat_id": chat_id, "text": "✅ فایل دریافت شد."})
                    return "ok"

                elif text == "مرحله بعد":
                    if not session["files"]:
                        send("sendMessage", {"chat_id": chat_id, "text": "❌ هیچ فایلی ارسال نشده."})
                        return "ok"

                    session["step"] = "awaiting_cover"
                    send("sendMessage", {"chat_id": chat_id, "text": "📥 لطفاً یک عکس برای کاور ارسال کنید."})
                    return "ok"

            # مرحله دریافت کاور
            elif session["step"] == "awaiting_cover":
                if "photo" in msg:
                    session["cover"] = msg["photo"][-1]["file_id"]
                    session["step"] = "awaiting_caption"
                    send("sendMessage", {"chat_id": chat_id, "text": "📝 لطفاً کپشن مورد نظر را بنویسید."})
                    return "ok"
                else:
                    send("sendMessage", {"chat_id": chat_id, "text": "❌ لطفاً فقط عکس ارسال کنید."})
                    return "ok"

            # مرحله دریافت کپشن
            elif session["step"] == "awaiting_caption":
                if text:
                    session["caption"] = text
                    from database import save_collection
                    from utils import gen_code
                    code = gen_code()
                    save_collection(code, session["files"], session["cover"], session["caption"])
                    reset_superadmin(user_id)
                    send("sendMessage", {
                        "chat_id": chat_id,
                        "text": f"✅ فایل‌ها ذخیره شدند.\nلینک مشاهده: https://yourdomain.com/view/{code}"
                    })
                    return "ok"
                else:
                    send("sendMessage", {"chat_id": chat_id, "text": "❌ لطفاً فقط متن بفرستید."})
                    return "ok"

    # اگر پیام عادی بود، ادامه هندلر قبلی اجرا بشه


# --- سوپر ادمین چندفایلی ---
from flask import Flask, request
from utils import gen_code, save_files
import requests

# ذخیره فایل‌ها در حافظه
temp_files = {}
user_states = {}

NEXT_STEP = "next_step"
ADDING_FILES = "adding_files"
SETTING_COVER = "setting_cover"
ADDING_CAPTION = "adding_caption"

TOKEN = "توکن ربات را اینجا قرار دهید"
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

def send_keyboard(chat_id, text, buttons):
    reply_markup = {
        "keyboard": [[{"text": btn}] for btn in buttons],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": text, "reply_markup": reply_markup})

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        user_id = str(chat_id)

        # شروع ارسال فایل
        if text == "سوپر":
            temp_files[user_id] = []
            user_states[user_id] = ADDING_FILES
            send_keyboard(chat_id, "فایل‌ها را یکی‌یکی ارسال کن. وقتی تموم شد دکمه زیر را بزن:", ["📎 مرحله بعد"])
            return "ok"

        # رفتن به مرحله بعد
        if text == "📎 مرحله بعد" and user_states.get(user_id) == ADDING_FILES:
            user_states[user_id] = SETTING_COVER
            requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": "حالا یکی از فایل‌ها را دوباره بفرست تا کاور شود."})
            return "ok"

        # دریافت کاور
        if user_states.get(user_id) == SETTING_COVER:
            file_id = None
            if "photo" in msg:
                file_id = msg["photo"][-1]["file_id"]
            elif "document" in msg:
                file_id = msg["document"]["file_id"]
            elif "video" in msg:
                file_id = msg["video"]["file_id"]
            if file_id:
                user_states[user_id] = ADDING_CAPTION
                user_states[user_id + "_cover"] = file_id
                requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": "کپشن دلخواهت رو بفرست."})
                return "ok"

        # دریافت کپشن
        if user_states.get(user_id) == ADDING_CAPTION:
            caption = text
            file_ids = temp_files.get(user_id, [])
            cover_id = user_states.get(user_id + "_cover")
            code = gen_code()
            save_files(file_ids, code, cover_id, caption)

            link = f"https://t.me/{BOT_USERNAME}?start={code}"
            msg_text = (
    f"✅ فایل‌ها ذخیره شدند.\n"
    f"برای مشاهده کلیک کنید: {link}"
            )

            requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": msg_text})
            user_states.pop(user_id, None)
            user_states.pop(user_id + "_cover", None)
            temp_files.pop(user_id, None)
            return "ok"

        # دریافت فایل‌ها
        if user_states.get(user_id) == ADDING_FILES:
            file_id = None
            if "photo" in msg:
                file_id = msg["photo"][-1]["file_id"]
            elif "document" in msg:
                file_id = msg["document"]["file_id"]
            elif "video" in msg:
                file_id = msg["video"]["file_id"]
            if file_id:
                temp_files[user_id].append(file_id)
                requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": "✅ فایل ثبت شد. می‌تونی فایل بعدی رو بفرستی یا بزنی مرحله بعد."})
                return "ok"

    return "ok"
